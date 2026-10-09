# logger.py
# =============================================================================
# 统一操作日志模块
#   - 输出格式：JSON Lines（每行一个 JSON 对象，UTF-8，便于机器解析）
#   - 落盘目录：<项目根>/logs/
#   - 滚动策略：每周一个文件（周一 00:00 切分），另设 SIZE_LIMIT 兜底防爆
#   - 文件命名：写入期间为 .open.log，滚动/关闭时重命名为
#               <起始时间>__<结束时间>.log（例如
#               2026-10-05_000000__2026-10-12_000000.log）
#   - 必备字段：ts（毫秒，2 位小数）、op（操作账号）、action（操作内容）
# =============================================================================
import os
import sys
import json
import time
import uuid
import atexit
import threading
import traceback
from contextvars import ContextVar
from datetime import datetime, timedelta

# -----------------------------------------------------------------------------
# 配置
# -----------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(BASE_DIR, "logs")

LOG_ENABLED = True          # 总开关，可通过 config.yaml 的 logging.enabled 覆盖
ROTATE_SECONDS = 7 * 24 * 3600   # 每周一个文件
ROTATE_WEEKDAY = 0               # 0 = 周一（Python 的 weekday() 语义）
SIZE_LIMIT = 8 * 1024 * 1024     # 8MB 兜底：万一单周写入异常放大，也强制切分
KEEP_FILES = 0                   # >0 时只保留最近 N 个已归档文件，0 表示永久保留
TS_FORMAT = "%Y-%m-%d %H:%M:%S"  # 日志内时间戳主体

ACTION_LABELS = {
    "QUERY": "查询",
    "CREATE": "新增",
    "UPDATE": "修改",
    "DELETE": "删除",
    "EXPORT": "导出",
    "LOGIN": "登录",
    "LOGOUT": "登出",
    "ACCESS": "访问",
    "INIT": "初始化",
    "ERROR": "异常",
    "AI": "AI调用",
    "RENAME": "改名",
    "PASSWORD": "改密",
}

# 读取日志的模块黑名单：避免「查看日志」这个动作本身再写一条访问日志，形成自我循环
READ_PATH_PREFIXES = ("/api/logs",)

# -----------------------------------------------------------------------------
# 请求上下文：由 server.py 的中间件写入，供业务日志自动带上操作账号与来源 IP
# -----------------------------------------------------------------------------
_request_ctx: ContextVar[dict] = ContextVar("bill_log_ctx", default={})


def set_request_context(**kwargs) -> None:
    """写入当前请求上下文（account / ip / path / method / ua）"""
    ctx = dict(_request_ctx.get() or {})
    for k, v in kwargs.items():
        if v is not None:
            ctx[k] = v
    _request_ctx.set(ctx)


def get_request_context() -> dict:
    return _request_ctx.get() or {}


def clear_request_context() -> None:
    _request_ctx.set({})


def current_account(default: str = "anonymous") -> str:
    """当前操作账号：优先取请求上下文，其次取线程内的显式绑定"""
    ctx = get_request_context()
    acc = ctx.get("account")
    if acc:
        return str(acc)
    return _thread_state.account or default


def current_ip(default: str = "-") -> str:
    ctx = get_request_context()
    return str(ctx.get("ip") or default)


# -----------------------------------------------------------------------------
# 时间工具
# -----------------------------------------------------------------------------
def _now() -> datetime:
    return datetime.now()


def format_ts(dt: datetime) -> str:
    """时间戳精确到 0.01 秒，例如 2026-10-09 22:42:42.15"""
    return f"{dt.strftime(TS_FORMAT)}.{dt.microsecond // 10000:02d}"


def _period_start(dt: datetime) -> datetime:
    """返回 dt 所属周期的起点（本周一 00:00:00）"""
    monday = dt - timedelta(days=(dt.weekday() - ROTATE_WEEKDAY) % 7)
    return monday.replace(hour=0, minute=0, second=0, microsecond=0)


def _period_end(start: datetime) -> datetime:
    return start + timedelta(seconds=ROTATE_SECONDS)


def _stamp(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d_%H%M%S")


def _final_name(start: datetime, end: datetime) -> str:
    return f"{_stamp(start)}__{_stamp(end)}.log"


def _open_name(start: datetime) -> str:
    return f"{_stamp(start)}.open.log"


# -----------------------------------------------------------------------------
# 写入器
# -----------------------------------------------------------------------------
class _ThreadState(threading.local):
    def __init__(self):
        self.account = None


_thread_state = _ThreadState()


class OperationLogger:
    """进程内单例：串行化写入，保证多线程下 JSON Lines 不被撕裂"""

    def __init__(self, log_dir: str = LOG_DIR, enabled: bool = True):
        self.log_dir = log_dir
        self.enabled = enabled
        self._lock = threading.RLock()
        self._fh = None
        self._period_start = None
        self._bytes = 0
        self._counter = 0

    # ---------------- 对外：绑定账号 ----------------
    def bind_account(self, account):
        """在非请求线程（如启动自检）中显式指定操作账号"""
        _thread_state.account = account

    # ---------------- 内部：文件管理 ----------------
    def _finalize_current_locked(self, end_dt: datetime = None):
        """关闭当前句柄并把 .open.log 改名为 起始__结束.log

        end_dt 语义：
          - 传 None 表示「正常整周期结束」，结束时间取该周期的理论收尾点；
          - 传入具体时间表示「提前中断」（进程退出/体积兜底），取该时间；
        无论哪种情况都会做一次下限保护，绝不让结束时间早于起始时间。
        """
        if self._fh is None:
            return
        start = self._period_start
        try:
            self._fh.flush()
            self._fh.close()
        except Exception:
            pass
        self._fh = None
        self._bytes = 0

        if start is None:
            return
        open_path = os.path.join(self.log_dir, _open_name(start))
        if not os.path.exists(open_path):
            return

        # 空文件（开了句柄但一条都没写成）直接丢弃，避免留下一堆无意义的空日志
        try:
            if os.path.getsize(open_path) == 0:
                os.remove(open_path)
                return
        except OSError:
            pass

        if end_dt is None:
            end = _period_end(start)
        else:
            end = end_dt
        # 下限保护：异常情况下（如系统时钟回拨）结束时间也不得早于起始时间
        if end < start:
            end = start

        final_path = os.path.join(self.log_dir, _final_name(start, end))
        try:
            if os.path.exists(final_path):
                # 同周期因体积被切成多段时，追加序号避免互相覆盖
                index = 2
                while True:
                    candidate = os.path.join(
                        self.log_dir,
                        f"{_stamp(start)}__{_stamp(end)}__part{index}.log"
                    )
                    if not os.path.exists(candidate):
                        final_path = candidate
                        break
                    index += 1
            os.replace(open_path, final_path)
        except Exception as e:
            print(f"[Logger Warning] 日志文件重命名失败: {e}", file=sys.stderr)
        self._prune_locked()

    def _prune_locked(self):
        if KEEP_FILES <= 0:
            return
        try:
            names = sorted(
                n for n in os.listdir(self.log_dir)
                if n.endswith(".log") and not n.endswith(".open.log")
            )
            for name in names[:-KEEP_FILES]:
                os.remove(os.path.join(self.log_dir, name))
        except Exception:
            pass

    def _ensure_open_locked(self, now: datetime):
        start = _period_start(now)
        size_rollover = self._fh is not None and self._bytes >= SIZE_LIMIT
        week_rollover = self._fh is not None and start != self._period_start

        if not (self._fh is None or size_rollover or week_rollover):
            return

        if size_rollover and start == self._period_start:
            # 体积兜底提前切分：结束时间就是当前时刻
            self._finalize_current_locked(end_dt=now)
            os.makedirs(self.log_dir, exist_ok=True)
            self._period_start = start
            open_path = os.path.join(self.log_dir, _open_name(start))
            self._fh = open(open_path, "a", encoding="utf-8")
            self._bytes = os.path.getsize(open_path)
            return

        # 跨周自然滚动：上一周期已完整走完，结束时间取该周期的理论收尾点
        self._finalize_current_locked(end_dt=_period_end(self._period_start) if self._period_start else None)
        os.makedirs(self.log_dir, exist_ok=True)
        self._period_start = start
        open_path = os.path.join(self.log_dir, _open_name(start))
        self._fh = open(open_path, "a", encoding="utf-8")
        self._bytes = os.path.getsize(open_path) if os.path.exists(open_path) else 0

    # ---------------- 对外：写日志 ----------------
    def log(self, action: str, op: str = None, **fields):
        """写一条日志。action 为操作内容简述，fields 为任意补充字段。"""
        if not LOG_ENABLED or not self.enabled:
            return
        # 防止「查看日志」自身产生新的访问日志而无限自增
        if str(fields.get("path") or get_request_context().get("path") or "").startswith("/api/logs"):
            return
        now = _now()
        record = {
            "ts": format_ts(now),
            "op": op if op else current_account(),
            "action": action,
        }
        ctx = get_request_context()
        if ctx.get("ip"):
            record["ip"] = ctx["ip"]
        if ctx.get("method"):
            record["method"] = ctx["method"]
        if ctx.get("path"):
            record["path"] = ctx["path"]
        for k, v in fields.items():
            if v is None or v == "":
                continue
            record[k] = v

        try:
            line = json.dumps(record, ensure_ascii=False, default=str)
        except Exception:
            line = json.dumps(
                {"ts": record["ts"], "op": record["op"], "action": str(action),
                 "note": "日志字段序列化失败"},
                ensure_ascii=False,
            )

        with self._lock:
            try:
                self._ensure_open_locked(now)
                self._fh.write(line + "\n")
                self._fh.flush()
                self._bytes += len(line.encode("utf-8")) + 1
                self._counter += 1
            except Exception as e:
                print(f"[Logger Error] 日志写入失败: {e}", file=sys.stderr)

    def trace_id(self) -> str:
        return uuid.uuid4().hex[:12]

    # ---------------- 对外：归档与退出 ----------------
    def flush(self):
        with self._lock:
            if self._fh is not None:
                try:
                    self._fh.flush()
                except Exception:
                    pass

    def close(self):
        with self._lock:
            # 进程退出/服务关闭属于「提前中断」，结束时间取实际关闭时刻
            self._finalize_current_locked(end_dt=_now())

    def current_file(self):
        """当前活跃日志文件的路径（未写入时为 None）"""
        with self._lock:
            if self._fh is None or self._period_start is None:
                return None
            return os.path.join(self.log_dir, _open_name(self._period_start))


logger = OperationLogger(LOG_DIR, LOG_ENABLED)


# -----------------------------------------------------------------------------
# 便捷函数
# -----------------------------------------------------------------------------
def log(action: str, op: str = None, **fields):
    logger.log(action, op=op, **fields)


def log_db(op_type: str, table: str, detail: str = "", **fields):
    """数据库业务日志：op_type 形如 QUERY / CREATE / UPDATE / DELETE / EXPORT"""
    label = ACTION_LABELS.get(op_type, op_type)
    text = f"{label} {table}"
    if detail:
        text += f"：{detail}"
    logger.log(text, op_type=op_type, table=table, **fields)


def bind_account(account):
    logger.bind_account(account)


def trace_id() -> str:
    return logger.trace_id()


def flush():
    logger.flush()


def close():
    logger.close()


def current_log_file():
    return logger.current_file()


# -----------------------------------------------------------------------------
# 配置加载与退出钩子
# -----------------------------------------------------------------------------
def configure_from_config(cfg: dict) -> None:
    """从 config.yaml 的 logging 节点读取配置（缺省即使用本模块默认值）"""
    global ROTATE_SECONDS, SIZE_LIMIT, KEEP_FILES, LOG_ENABLED
    node = (cfg or {}).get("logging") or {}
    if not isinstance(node, dict):
        return

    if "enabled" in node:
        LOG_ENABLED = bool(node["enabled"])
        logger.enabled = LOG_ENABLED

    if node.get("dir"):
        custom_dir = str(node["dir"]).strip()
        logger.log_dir = custom_dir if os.path.isabs(custom_dir) else os.path.join(BASE_DIR, custom_dir)

    days = node.get("rotate_days")
    if days:
        try:
            ROTATE_SECONDS = max(1, int(days)) * 24 * 3600
        except Exception:
            pass

    size_mb = node.get("size_limit_mb")
    if size_mb:
        try:
            SIZE_LIMIT = max(1, int(size_mb)) * 1024 * 1024
        except Exception:
            pass

    keep = node.get("keep_files")
    if keep is not None:
        try:
            KEEP_FILES = max(0, int(keep))
        except Exception:
            pass

    if node.get("ts_precision") == "ms":
        # 预留：本模块固定输出 0.01 秒精度
        pass


def _init_from_yaml():
    """尽量从 config.yaml 读取日志配置；失败不影响主流程"""
    try:
        import yaml
    except Exception:
        return
    config_path = os.path.join(BASE_DIR, "config.yaml")
    if not os.path.exists(config_path):
        return
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
        configure_from_config(cfg if isinstance(cfg, dict) else {})
    except Exception as e:
        print(f"[Logger Warning] 读取日志配置失败，使用默认配置: {e}", file=sys.stderr)


_init_from_yaml()
atexit.register(logger.close)


def _install_signal_handlers():
    """收到 SIGTERM/SIGINT（Ctrl+C、容器停止）时先归档日志，再走原有行为

    uvicorn 的正常关闭会触发 lifespan，但被强杀时不会；这里兜一层，
    保证日志文件仍能以「起始__结束」的形式落盘，而不是留下 .open.log。
    """
    import signal

    def _make_handler(sig, previous):
        def _handler(signum, frame):
            try:
                logger.close()
            except Exception:
                pass
            if callable(previous) and previous not in (
                signal.SIG_DFL, signal.SIG_IGN, None
            ):
                previous(signum, frame)
            elif previous == signal.SIG_DFL:
                signal.signal(signum, signal.SIG_DFL)
                os.kill(os.getpid(), signum)
        return _handler

    for name in ("SIGTERM", "SIGINT"):
        sig = getattr(signal, name, None)
        if sig is None:
            continue
        try:
            previous = signal.getsignal(sig)
            signal.signal(sig, _make_handler(sig, previous))
        except (ValueError, OSError):
            # 非主线程或平台不支持时静默跳过
            pass


def install_signal_handlers():
    try:
        _install_signal_handlers()
    except Exception:
        pass


def install_excepthook():
    """把未捕获异常也记入日志，便于事后回溯"""
    original = sys.excepthook

    def _hook(exc_type, exc_value, exc_tb):
        try:
            log(
                f"未捕获异常：{exc_type.__name__}: {exc_value}",
                op_type="ERROR",
                table="process",
                traceback="".join(traceback.format_exception(exc_type, exc_value, exc_tb))[-2000:],
            )
            logger.close()
        except Exception:
            pass
        original(exc_type, exc_value, exc_tb)

    sys.excepthook = _hook
