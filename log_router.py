# log_router.py
# =============================================================================
# 日志查看模块（仅管理员）
#   - GET /api/logs/files   列出 logs/ 下的日志文件
#   - GET /api/logs/read    读取指定日志文件的尾部若干行
#   - GET /api/logs/download 下载单个日志文件
#
# 注意：本模块的所有路径都以 /api/logs 开头，logger 内部对这些路径有自抑制
# 保护，浏览日志这个动作本身不会再写入新的访问日志，避免日志自我膨胀。
# =============================================================================
import os
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse

import logger as oplog
from auth import require_admin

log_router = APIRouter(prefix="/api/logs", tags=["Logs API"])

LOG_DIR = oplog.LOG_DIR


def _safe_path(filename: str) -> str:
    """只允许访问日志目录下的 .log 文件，杜绝路径穿越"""
    name = os.path.basename((filename or "").strip())
    if not name or not name.endswith(".log"):
        raise HTTPException(status_code=400, detail="非法的日志文件名")
    path = os.path.join(LOG_DIR, name)
    real_dir = os.path.realpath(LOG_DIR)
    if os.path.realpath(path)[: len(real_dir)] != real_dir:
        raise HTTPException(status_code=400, detail="非法的日志文件路径")
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail=f"日志文件不存在：{name}")
    return path


@log_router.get("/files")
def list_log_files(admin: dict = Depends(require_admin)):
    """列出全部日志文件，附带体积与起止时间（从文件名解析）"""
    if not os.path.isdir(LOG_DIR):
        return {"dir": LOG_DIR, "files": [], "current": None}

    files = []
    for name in os.listdir(LOG_DIR):
        if not name.endswith(".log"):
            continue
        path = os.path.join(LOG_DIR, name)
        try:
            stat = os.stat(path)
        except OSError:
            continue

        start = end = None
        if "__" in name:
            left, right = name[:-4].split("__", 1)
            start, end = left, right
        else:
            start = name[:-4].replace(".open", "")

        files.append({
            "name": name,
            "size": stat.st_size,
            "size_human": _human(stat.st_size),
            "start": start,
            "end": end,
            "active": name.endswith(".open.log"),
            "modified": __import__("time").strftime("%Y-%m-%d %H:%M:%S", __import__("time").localtime(stat.st_mtime)),
        })

    # 活跃文件排最前，其余按名称倒序（即时间倒序）
    files.sort(key=lambda f: (not f["active"], f["name"]), reverse=False)
    files.sort(key=lambda f: (not f["active"],))
    archived = sorted([f for f in files if not f["active"]], key=lambda f: f["name"], reverse=True)
    active = [f for f in files if f["active"]]
    ordered = active + archived

    return {"dir": LOG_DIR, "files": ordered, "total": len(ordered)}


def _human(size: int) -> str:
    if size < 1024:
        return f"{size} B"
    if size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    return f"{size / 1024 / 1024:.2f} MB"


@log_router.get("/read")
def read_log_file(
    filename: Optional[str] = Query(None, description="日志文件名，缺省表示当前活跃文件"),
    lines: int = Query(200, ge=1, le=5000),
    keyword: Optional[str] = Query(None, description="关键字过滤（对账号/操作内容等做包含匹配）"),
    admin: dict = Depends(require_admin),
):
    """读取日志文件尾部若干行（默认 200 行），支持关键字过滤"""
    if filename:
        path = _safe_path(filename)
    else:
        path = oplog.current_log_file()
        if not path or not os.path.isfile(path):
            # 尚未写入任何日志时，回退到最新的归档文件
            candidates = sorted(
                (os.path.join(LOG_DIR, n) for n in os.listdir(LOG_DIR) if n.endswith(".log")),
                reverse=True,
            ) if os.path.isdir(LOG_DIR) else []
            if not candidates:
                return {"file": None, "lines": [], "truncated": False, "total": 0}
            path = candidates[0]

    try:
        oplog.flush()
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            all_lines = f.read().splitlines()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"日志读取失败: {e}")

    total = len(all_lines)
    selected = all_lines
    if keyword and keyword.strip():
        kw = keyword.strip()
        selected = [ln for ln in selected if kw in ln]
    truncated = len(selected) > lines
    tail = selected[-lines:]

    return {
        "file": os.path.basename(path),
        "lines": tail,
        "truncated": truncated,
        "total": total,
        "matched": len(selected),
    }


@log_router.get("/download")
def download_log_file(
    filename: str = Query(..., description="要下载的日志文件名"),
    admin: dict = Depends(require_admin),
):
    path = _safe_path(filename)
    oplog.flush()
    return FileResponse(path, media_type="application/octet-stream", filename=filename)
