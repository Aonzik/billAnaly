# server.py
import os
import sqlite3
from typing import Optional
from contextlib import asynccontextmanager
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# 引入项目核心模块
import analyze
from db_manager import DB_PATH, db_router
from ai_assistant import ai_router

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
JSON_OUTPUT = os.path.join(STATIC_DIR, "expense_data.json")


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
    # 1. 自检并建立空库/空表
    ensure_db_initialized()

    # 2. 尝试执行一次初始分析生成中间态 JSON（空数据时会自动容错）
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
    # 3. 服务关闭时的清理动作（如需）写在 yield 之后


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

# 挂载路由模块
app.include_router(db_router)
app.include_router(ai_router)


# 查询数据库里已有所有月份（格式如 ["2026-09", "2026-10"]）
@app.get("/api/months")
def get_available_months():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT DISTINCT substr(日期, 1, 7) as ym FROM expenses WHERE 日期 LIKE '____-__%' ORDER BY ym DESC"
    )
    months = [row[0] for row in cursor.fetchall()]
    conn.close()
    return months


# 联动分析接口：支持指定月份与自定义预算（合并修正了原本重复定义的问题）
@app.post("/api/refresh_analysis")
def trigger_refresh(
    year_month: Optional[str] = Query(None),
    monthly_budget: Optional[float] = Query(2300.0),
):
    data = analyze.run_analysis_from_db(
        db_path=DB_PATH,
        monthly_budget=monthly_budget,
        json_path=JSON_OUTPUT,
        year_month=year_month,
    )
    if data:
        return {
            "status": "success",
            "message": f"[{year_month or '全部'}] 分析已重新生成，预算基线: ¥{monthly_budget}",
        }
    return {"status": "empty", "message": "该月份无数据或数据库为空"}

@app.get("/api/wordcloud")
def get_wordcloud_api():
  """获取全量支出品名的词云统计数据（支持按频次/按金额）"""
  return analyze.generate_wordcloud_data(DB_PATH, top_n=80)

# 挂载静态资源
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")


if __name__ == "__main__":
    import uvicorn

    print("\n" + "=" * 60)
    print("服务正在启动中...")
    print("  👉 图表看板:   http://localhost:8000/dashboard.html")
    print("  👉 记账管理页: http://localhost:8000/manager.html")
    print("=" * 60 + "\n")

    uvicorn.run(app, host="0.0.0.0", port=8000)