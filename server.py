# server.py
import os
import sqlite3
import time
from typing import Optional
from urllib.parse import quote
from contextlib import asynccontextmanager
from fastapi import FastAPI, Query, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, JSONResponse

# 引入项目核心模块
import analyze
import logger as oplog
from db_manager import DB_PATH, db_router
from ai_assistant import ai_router
from log_router import log_router
from auth import (
    auth_router,
    init_auth_db,
    get_user_from_request,
    require_user,
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
JSON_OUTPUT = os.path.join(STATIC_DIR, "expense_data.json")

# 免登录即可访问的路径（登录页及其自有资源 / 登录接口）
PUBLIC_PATHS = {
    "/login.html",
    "/favicon.ico",
    "/api/auth/login",
}

# 操作日志相关接口自身不写访问日志，避免日志查看动作把日志越写越大
LOG_PATH_PREFIX = "/api/logs"

# 不记录访问日志的静态资源后缀（图片、字体等噪音较大，且非业务操作）
STATIC_LOG_EXCLUDE_EXT = {
    ".ico", ".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp",
    ".woff", ".woff2", ".ttf", ".eot", ".map",
}


def _client_ip(request: Request) -> str:
    """取出真实来源 IP，兼容反向代理"""
    fwd = request.headers.get("x-forwarded-for", "")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "-"


def _summarize_query(request: Request) -> str:
    """把查询参数压缩成一行摘要，写进访问日志的 detail 字段"""
    raw = request.url.query
    if not raw:
        return ""
    text = raw if len(raw) <= 300 else raw[:300] + "…(截断)"
    return text


def ensure_db_initialized():
    """自检并初始化 SQLite 数据库、表结构及常用索引"""
    # 保证 static 目录存在，防止写入 JSON 缓存时报错
    if not os.path.exists(STATIC_DIR):
        os.makedirs(STATIC_DIR, exist_ok=True)

    print(f">>> [System Init] 检查数据库状态: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 创建核心流水表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            日期 TEXT NOT NULL,
            时间 TEXT DEFAULT '12:00',
            交易类型 TEXT NOT NULL,
            分类 TEXT NOT NULL,
            品名 TEXT NOT NULL,
            实际金额 REAL NOT NULL,
            支付账户 TEXT DEFAULT '',
            目标账户 TEXT DEFAULT '',
            备注 TEXT DEFAULT ''
        )
    """)

    # 创建核心查询索引，加速范围和分类查询
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_expenses_date ON expenses(日期)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_expenses_category ON expenses(分类)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_expenses_type ON expenses(交易类型)")

    conn.commit()
    conn.close()
    print(">>> [System Init] 数据库与数据表自检就绪。")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI 生命周期管理器：在应用启动时统一执行自检与预分析"""
    # 0. 日志系统自检：确保 logs/ 目录存在并写入一条启动记录
    os.makedirs(oplog.LOG_DIR, exist_ok=True)
    oplog.install_excepthook()
    oplog.install_signal_handlers()
    oplog.log(
        f"服务启动：日志目录 {oplog.LOG_DIR}，滚动周期 "
        f"{oplog.ROTATE_SECONDS // 86400} 天/文件，"
        f"单文件上限 {oplog.SIZE_LIMIT // 1024 // 1024} MB",
        op="system", op_type="INIT", table="system",
    )

    # 1. 自检并建立空库/空表
    ensure_db_initialized()

    # 2. 初始化账号库（首次部署自动植入管理员 admin / 123456）
    init_auth_db()

    # 3. 尝试执行一次初始分析生成中间态 JSON（空数据时会自动容错）
    try:
        analyze.run_analysis_from_db(
            db_path=DB_PATH,
            monthly_budget=2300.0,
            json_path=JSON_OUTPUT
        )
        print(">>> [System Init] 初始账单聚合缓存同步完成。")
    except Exception as e:
        print(f">>> [System Warning] 首次聚合缓存生成跳过（可能暂无数据）: {e}")

    yield
    # 4. 服务关闭：把当前日志文件归档重命名（起止时间）后落盘
    oplog.log("服务关闭：日志文件即将归档", op="system", op_type="INIT", table="system")
    oplog.close()


app = FastAPI(
    title="AI财务分析与 SQLite 数据库系统",
    lifespan=lifespan
)

# 允许跨域
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def operation_logger(request: Request, call_next):
    """统一操作日志中间件

    对所有 HTTP 请求记录：时间戳（0.01 秒精度）、操作账号、操作内容
    （方法 + 路径 + 查询参数）、来源 IP、响应状态码与耗时。

    该中间件注册在 auth_gate 之前，因此请求先经过日志记录、再由鉴权闸门
    处理，未登录被拦截的请求同样会留下访问记录。
    """
    path = request.url.path

    # 日志接口自身、静态资源噪音不记录，避免日志自我膨胀
    if path.startswith(LOG_PATH_PREFIX) or os.path.splitext(path)[1].lower() in STATIC_LOG_EXCLUDE_EXT:
        return await call_next(request)

    started = time.perf_counter()
    user = get_user_from_request(request)
    account = user["username"] if user else "anonymous"

    # 把请求上下文写入 ContextVar，业务函数内的日志会自动带上账号与来源
    token = oplog._request_ctx.set({})
    oplog.set_request_context(
        account=account, ip=_client_ip(request),
        method=request.method, path=path,
    )
    response = None
    try:
        response = await call_next(request)

        elapsed = (time.perf_counter() - started) * 1000
        status = response.status_code

        # 静态页面/资源只记录到「页面访问」粒度，接口请求记录得完整一些
        if path.startswith("/api/"):
            action = f"访问接口 {request.method} {path}"
            if status >= 500:
                action = f"接口异常 {request.method} {path}"
            elif status in (401, 403):
                action = f"访问被拒绝 {request.method} {path}"
        else:
            action = f"访问页面 {request.method} {path}"

        # 此时上下文仍然有效，ip / method / path 会自动带上
        oplog.log(
            action,
            op=account,
            op_type="ACCESS",
            result="success" if status < 400 else ("denied" if status in (401, 403) else "failed"),
            status_code=status,
            elapsed_ms=round(elapsed, 2),
            detail=_summarize_query(request),
            user_agent=(request.headers.get("user-agent", "") or "")[:120] or None,
        )
    except Exception as e:
        elapsed = (time.perf_counter() - started) * 1000
        oplog.log(
            f"请求处理异常：{request.method} {path} -> {type(e).__name__}: {e}",
            op=account, op_type="ERROR", result="exception",
            status_code=500, elapsed_ms=round(elapsed, 2), detail=_summarize_query(request),
        )
        raise
    finally:
        # 必须等 call_next 完全结束、本中间件的日志也写完之后再重置上下文，
        # 否则日志会丢失 ip / method / path
        oplog._request_ctx.reset(token)

    return response


@app.middleware("http")
async def auth_gate(request, call_next):
    """统一登录闸门：未登录不得访问任何页面与数据接口"""
    path = request.url.path

    # 放行登录页、站点图标与登录接口，以及浏览器的 OPTIONS 预检
    if request.method == "OPTIONS" or path in PUBLIC_PATHS:
        return await call_next(request)

    # 根路径：已登录进看板，未登录去登录页
    if path == "/":
        if get_user_from_request(request) is not None:
            return RedirectResponse("/dashboard.html", status_code=302)
        return RedirectResponse("/login.html", status_code=302)

    if get_user_from_request(request) is None:
        # 数据接口返回 401，由前端跳转登录页；页面请求直接重定向
        if path.startswith("/api/"):
            return JSONResponse({"detail": "未登录或登录已过期，请重新登录"}, status_code=401)
        return RedirectResponse(
            f"/login.html?next={quote(path)}", status_code=302
        )

    return await call_next(request)


# 挂载路由模块（除登录相关接口外，一律要求已登录）
app.include_router(auth_router)
app.include_router(db_router, dependencies=[Depends(require_user)])
app.include_router(ai_router, dependencies=[Depends(require_user)])
app.include_router(log_router, dependencies=[Depends(require_user)])


# 查询数据库里已有所有月份（格式如 ["2026-09", "2026-10"]）
@app.get("/api/months")
def get_available_months(_user: dict = Depends(require_user)):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT DISTINCT substr(日期, 1, 7) as ym FROM expenses WHERE 日期 LIKE '____-__%' ORDER BY ym DESC"
    )
    months = [row[0] for row in cursor.fetchall()]
    conn.close()
    return months


# 联动分析接口：支持指定年份月份与自定义预算（合并修正了原本重复定义的问题）
@app.post("/api/refresh_analysis")
def trigger_refresh(
    year: Optional[int] = Query(None),
    month: Optional[int] = Query(None),
    year_month: Optional[str] = Query(None),
    monthly_budget: Optional[float] = Query(2300.0),
    _user: dict = Depends(require_user),
):
    # 兼容旧调用方的 year_month 参数（如 "2026-09"），拆分为年份与月份
    if (year is None or month is None) and year_month:
        parsed_year, parsed_month = analyze.parse_year_month_arg(year_month)
        if year is None:
            year = parsed_year
        if month is None:
            month = parsed_month

    # 选定具体月份时按月份隔离缓存文件，避免 2026-09 与 2027-09 等不同年份互相覆盖
    target_path = JSON_OUTPUT
    label = "全部"
    if year is not None and month is not None:
        target_path = analyze.build_month_json_path(JSON_OUTPUT, year, month)
        label = f"{year}-{month:02d}"

    data = analyze.run_analysis_from_db(
        db_path=DB_PATH,
        monthly_budget=monthly_budget,
        json_path=target_path,
        year=year,
        month=month,
    )
    if data:
        oplog.log(
            f"重新生成分析缓存：[{label}]，预算基线 ¥{monthly_budget}",
            op=_user.get("username", "system"), op_type="ACCESS",
            table="expenses", label=label, monthly_budget=monthly_budget,
        )
        return {
            "status": "success",
            "message": f"[{label}] 分析已重新生成，预算基线: ¥{monthly_budget}",
        }
    return {"status": "empty", "message": "该月份无数据或数据库为空"}

@app.get("/api/wordcloud")
def get_wordcloud_api(
    year: Optional[int] = Query(None),
    month: Optional[int] = Query(None),
    year_month: Optional[str] = Query(None),
    top_n: int = Query(80),
    _user: dict = Depends(require_user),
):
  """获取支出品名的词云统计数据（支持按频次/按金额，可指定核算年月）"""
  # 兼容旧调用方的 year_month 参数（如 "2026-09"），拆分为年份与月份
  if (year is None or month is None) and year_month:
      parsed_year, parsed_month = analyze.parse_year_month_arg(year_month)
      if year is None:
          year = parsed_year
      if month is None:
          month = parsed_month
  return analyze.generate_wordcloud_data(DB_PATH, top_n=top_n, year=year, month=month)

# -----------------------------------------------------------------------------
# 静态资源：登录页公开，其余全部需要登录（由 auth_gate 中间件拦截）
# -----------------------------------------------------------------------------
_ALLOWED_PAGE_EXT = {".html", ".htm"}


class AuthStaticFiles(StaticFiles):
    """在 StaticFiles 之上补一层鉴权：未登录只能拿到登录页"""

    async def get_response(self, path: str, scope):
        rel = path.lstrip("/")

        # 登录页及其自有资源（样式/脚本）无需登录
        if rel in {"login.html", "favicon.ico"} or rel == "":
            return await super().get_response(path, scope)

        request = Request(scope)
        if get_user_from_request(request) is None:
            ext = os.path.splitext(rel)[1].lower()
            if ext in _ALLOWED_PAGE_EXT or ext == "":
                return RedirectResponse(
                    f"/login.html?next={quote('/' + rel)}", status_code=302
                )
            return JSONResponse({"detail": "未登录或登录已过期，请重新登录"}, status_code=401)

        return await super().get_response(path, scope)


app.mount("/", AuthStaticFiles(directory=STATIC_DIR, html=True), name="static")


if __name__ == "__main__":
    import uvicorn

    print("\n" + "=" * 60)
    print("服务正在启动中...")
    print("  🔐 登录入口:   http://localhost:8000/login.html")
    print("  👉 图表看板:   http://localhost:8000/dashboard.html")
    print("  👉 记账管理页: http://localhost:8000/manager.html")
    print("  默认管理员:    admin / 123456（首次启动自动创建，请及时修改）")
    print("=" * 60 + "\n")

    uvicorn.run(app, host="0.0.0.0", port=8000)