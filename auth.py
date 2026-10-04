# auth.py
# =============================================================================
# 身份验证与账号管理模块
#   - 密码使用「随机盐 + PBKDF2-HMAC-SHA256」哈希存储，绝不保存明文
#   - 会话令牌仅保存 SHA256 摘要，浏览器侧通过 HttpOnly Cookie 携带
#   - 首次部署自动创建管理员账号 admin / 123456
# =============================================================================
import os
import time
import hmac
import hashlib
import secrets
import sqlite3
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
AUTH_DB_PATH = os.path.join(BASE_DIR, "users.db")

COOKIE_NAME = "bill_auth"
SESSION_TTL = 7 * 24 * 3600          # 会话有效期：7 天
PBKDF2_ITERATIONS = 120_000          # 哈希迭代次数
PBKDF2_ALGO = "sha256"
SALT_BYTES = 16

DEFAULT_ADMIN_USERNAME = "admin"
DEFAULT_ADMIN_PASSWORD = "123456"

auth_router = APIRouter(prefix="/api/auth", tags=["Auth API"])


# -----------------------------------------------------------------------------
# 数据库
# -----------------------------------------------------------------------------
def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(AUTH_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _now_str() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")


def init_auth_db() -> None:
    """建表并在库为空时植入默认管理员账号（幂等，可重复调用）"""
    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            username      TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            role          TEXT NOT NULL DEFAULT 'user',
            created_by    TEXT DEFAULT '',
            created_at    TEXT NOT NULL
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS sessions (
            token_hash TEXT PRIMARY KEY,
            user_id    INTEGER NOT NULL,
            created_at REAL NOT NULL,
            expires_at REAL NOT NULL
        )
        """
    )
    cur.execute("CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id)")

    total = cur.execute("SELECT COUNT(*) AS c FROM users").fetchone()["c"]
    if total == 0:
        salt, pwd_hash = hash_password(DEFAULT_ADMIN_PASSWORD)
        cur.execute(
            "INSERT INTO users (username, password_hash, role, created_by, created_at)"
            " VALUES (?, ?, 'admin', 'system', ?)",
            (DEFAULT_ADMIN_USERNAME, f"{salt}${pwd_hash}", _now_str()),
        )
        print(
            f">>> [Auth Init] 已创建默认管理员账号：{DEFAULT_ADMIN_USERNAME} / "
            f"{DEFAULT_ADMIN_PASSWORD}（请登录后尽快修改密码）"
        )

    conn.commit()
    conn.close()


# -----------------------------------------------------------------------------
# 密码哈希（盐 + PBKDF2）
# -----------------------------------------------------------------------------
def hash_password(password: str, salt: Optional[str] = None):
    """返回 (salt_hex, hash_hex)。同一密码每次结果不同（随机盐）。"""
    if salt is None:
        salt = secrets.token_hex(SALT_BYTES)
    digest = hashlib.pbkdf2_hmac(
        PBKDF2_ALGO,
        password.encode("utf-8"),
        salt.encode("utf-8"),
        PBKDF2_ITERATIONS,
    )
    return salt, digest.hex()


def verify_password(password: str, stored: str) -> bool:
    """校验明文密码与库中 'salt$hash' 是否匹配（恒定时间比较）"""
    if not stored or "$" not in stored:
        return False
    salt, expected = stored.split("$", 1)
    _, actual = hash_password(password, salt)
    return hmac.compare_digest(actual, expected)


# -----------------------------------------------------------------------------
# 会话令牌
# -----------------------------------------------------------------------------
def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_session(user_id: int) -> str:
    """创建会话，返回原始令牌（仅此一次出现，库中只存摘要）"""
    token = secrets.token_urlsafe(32)
    now = time.time()
    conn = get_conn()
    # 顺手清理过期会话，避免表无限膨胀
    conn.execute("DELETE FROM sessions WHERE expires_at < ?", (now,))
    conn.execute(
        "INSERT INTO sessions (token_hash, user_id, created_at, expires_at) VALUES (?, ?, ?, ?)",
        (_hash_token(token), user_id, now, now + SESSION_TTL),
    )
    conn.commit()
    conn.close()
    return token


def drop_session(token: str) -> None:
    if not token:
        return
    conn = get_conn()
    conn.execute("DELETE FROM sessions WHERE token_hash = ?", (_hash_token(token),))
    conn.commit()
    conn.close()


def drop_user_sessions(user_id: int) -> None:
    conn = get_conn()
    conn.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()


def _token_from_headers(headers) -> Optional[str]:
    """从 Authorization: Bearer xxx 或 Cookie 中提取令牌"""
    auth = headers.get("authorization", "") or ""
    if auth.lower().startswith("bearer "):
        token = auth[7:].strip()
        if token:
            return token

    cookie = headers.get("cookie", "") or ""
    for part in cookie.split(";"):
        part = part.strip()
        if part.startswith(COOKIE_NAME + "="):
            token = part[len(COOKIE_NAME) + 1 :].strip()
            if token:
                return token
    return None


def get_user_by_token(token: Optional[str]) -> Optional[dict]:
    if not token:
        return None
    conn = get_conn()
    row = conn.execute(
        """
        SELECT u.id, u.username, u.role, s.expires_at
          FROM sessions s
          JOIN users u ON u.id = s.user_id
         WHERE s.token_hash = ?
        """,
        (_hash_token(token),),
    ).fetchone()
    conn.close()
    if row is None or row["expires_at"] < time.time():
        return None
    return {"id": row["id"], "username": row["username"], "role": row["role"]}


def get_user_from_request(request: Request) -> Optional[dict]:
    return get_user_by_token(_token_from_headers(request.headers))


# -----------------------------------------------------------------------------
# FastAPI 依赖
# -----------------------------------------------------------------------------
def require_user(request: Request) -> dict:
    user = get_user_from_request(request)
    if user is None:
        raise HTTPException(status_code=401, detail="未登录或登录已过期，请重新登录")
    return user


def require_admin(user: dict = Depends(require_user)) -> dict:
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="仅管理员可执行此操作")
    return user


# -----------------------------------------------------------------------------
# 请求体模型
# -----------------------------------------------------------------------------
class LoginBody(BaseModel):
    username: str
    password: str


class CreateUserBody(BaseModel):
    username: str
    password: str


class ChangeUsernameBody(BaseModel):
    new_username: str
    current_password: str


class ChangePasswordBody(BaseModel):
    current_password: str
    new_password: str
    confirm_password: str


# -----------------------------------------------------------------------------
# 接口：登录 / 登出 / 当前用户
# -----------------------------------------------------------------------------
@auth_router.post("/login")
def login(body: LoginBody, response: Response):
    username = (body.username or "").strip()
    if not username or not body.password:
        raise HTTPException(status_code=400, detail="账号和密码不能为空")

    conn = get_conn()
    row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    conn.close()

    if row is None or not verify_password(body.password, row["password_hash"]):
        raise HTTPException(status_code=401, detail="账号或密码错误")

    token = create_session(row["id"])
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        max_age=SESSION_TTL,
        httponly=True,
        samesite="lax",
        path="/",
    )
    return {"status": "success", "token": token, "username": row["username"], "role": row["role"]}


@auth_router.post("/logout")
def logout(request: Request, response: Response):
    drop_session(_token_from_headers(request.headers))
    response.delete_cookie(COOKIE_NAME, path="/")
    return {"status": "success"}


@auth_router.get("/me")
def me(user: dict = Depends(require_user)):
    return user


# -----------------------------------------------------------------------------
# 接口：管理员账号管理
# -----------------------------------------------------------------------------
@auth_router.get("/users")
def list_users(admin: dict = Depends(require_admin)):
    conn = get_conn()
    rows = conn.execute(
        "SELECT id, username, role, created_by, created_at FROM users ORDER BY id"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@auth_router.post("/users")
def create_user(body: CreateUserBody, admin: dict = Depends(require_admin)):
    username = (body.username or "").strip()
    if not username:
        raise HTTPException(status_code=400, detail="账号名不能为空")
    if not body.password:
        raise HTTPException(status_code=400, detail="密码不能为空")

    conn = get_conn()
    exists = conn.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
    if exists:
        conn.close()
        raise HTTPException(status_code=400, detail=f"账号「{username}」已存在")

    salt, pwd_hash = hash_password(body.password)
    conn.execute(
        "INSERT INTO users (username, password_hash, role, created_by, created_at)"
        " VALUES (?, ?, 'user', ?, ?)",
        (username, f"{salt}${pwd_hash}", admin["username"], _now_str()),
    )
    conn.commit()
    conn.close()
    return {"status": "success", "username": username}


@auth_router.delete("/users/{user_id}")
def delete_user(user_id: int, admin: dict = Depends(require_admin)):
    if user_id == admin["id"]:
        raise HTTPException(status_code=400, detail="不能删除当前登录的账号")

    conn = get_conn()
    target = conn.execute("SELECT id, role FROM users WHERE id = ?", (user_id,)).fetchone()
    if target is None:
        conn.close()
        raise HTTPException(status_code=404, detail="账号不存在")

    if target["role"] == "admin":
        admin_count = conn.execute(
            "SELECT COUNT(*) AS c FROM users WHERE role = 'admin'"
        ).fetchone()["c"]
        if admin_count <= 1:
            conn.close()
            raise HTTPException(status_code=400, detail="系统需保留至少一个管理员账号")

    conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()
    return {"status": "success"}


# -----------------------------------------------------------------------------
# 接口：修改自己的账号名 / 密码
# -----------------------------------------------------------------------------
@auth_router.put("/me/username")
def change_username(body: ChangeUsernameBody, user: dict = Depends(require_user)):
    new_username = (body.new_username or "").strip()
    if not new_username:
        raise HTTPException(status_code=400, detail="新账号名不能为空")
    if not body.current_password:
        raise HTTPException(status_code=400, detail="请输入当前密码以确认身份")

    conn = get_conn()
    row = conn.execute("SELECT * FROM users WHERE id = ?", (user["id"],)).fetchone()
    if row is None or not verify_password(body.current_password, row["password_hash"]):
        conn.close()
        raise HTTPException(status_code=400, detail="当前密码错误")

    if new_username == row["username"]:
        conn.close()
        return {"status": "success", "username": new_username}

    dup = conn.execute(
        "SELECT id FROM users WHERE username = ? AND id != ?", (new_username, user["id"])
    ).fetchone()
    if dup:
        conn.close()
        raise HTTPException(status_code=400, detail=f"账号名「{new_username}」已被占用")

    conn.execute("UPDATE users SET username = ? WHERE id = ?", (new_username, user["id"]))
    conn.commit()
    conn.close()
    return {"status": "success", "username": new_username}


@auth_router.put("/me/password")
def change_password(body: ChangePasswordBody, user: dict = Depends(require_user)):
    if not body.new_password:
        raise HTTPException(status_code=400, detail="新密码不能为空")
    if body.new_password != body.confirm_password:
        raise HTTPException(status_code=400, detail="两次输入的新密码不一致")

    conn = get_conn()
    row = conn.execute("SELECT * FROM users WHERE id = ?", (user["id"],)).fetchone()
    if row is None or not verify_password(body.current_password, row["password_hash"]):
        conn.close()
        raise HTTPException(status_code=400, detail="当前密码错误")

    salt, pwd_hash = hash_password(body.new_password)
    conn.execute(
        "UPDATE users SET password_hash = ? WHERE id = ?",
        (f"{salt}${pwd_hash}", user["id"]),
    )
    conn.commit()
    conn.close()

    # 密码已变更，强制所有会话（含当前）下线，要求重新登录
    drop_user_sessions(user["id"])
    return {"status": "success", "message": "密码修改成功，请使用新密码重新登录"}
