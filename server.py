# server.py
import os
import sqlite3
from typing import Optional
from fastapi import Query
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# 1. 引入另外两个独立文件的核心功能
import analyze
from db_manager import DB_PATH, db_router, init_db
from ai_assistant import ai_router

app = FastAPI(title="AI财务分析与 SQLite 数据库系统")

# 允许跨域
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
JSON_OUTPUT = os.path.join(STATIC_DIR, "expense_data.json")

# 2. 挂载 db_manager 的路由
app.include_router(db_router)
#  挂载 ai_assistant 的路由
app.include_router(ai_router)

# 3. 查询数据库里已有所有月份（格式如 ["2026-09", "2026-10"]）
@app.get("/api/months")
def get_available_months():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # 提取日期字段的前 7 位 YYYY-MM
    cursor.execute("SELECT DISTINCT substr(日期, 1, 7) as ym FROM expenses WHERE 日期 LIKE '____-__%' ORDER BY ym DESC")
    months = [row[0] for row in cursor.fetchall()]
    conn.close()
    return months

# 4. 修改现有的联动分析接口，支持指定月份
@app.post("/api/refresh_analysis")
def trigger_refresh(
    year_month: Optional[str] = Query(None),
    monthly_budget: Optional[float] = Query(2300.0) # 接收自定义预算
):
    data = analyze.run_analysis_from_db(
        db_path=DB_PATH,
        monthly_budget=monthly_budget, # 传入自定义预算
        json_path=JSON_OUTPUT,
        year_month=year_month
    )
    if data:
        return {
            "status": "success", 
            "message": f"[{year_month or '全部'}] 分析已重新生成，预算基线: ¥{monthly_budget}"
        }
    return {"status": "empty", "message": "该月份无数据"}


# 5. 联动接口：通知分析程序从 SQLite 读取最新数据并刷新报表
@app.post("/api/refresh_analysis")
def trigger_refresh():
    data = analyze.run_analysis_from_db(
        db_path=DB_PATH,
        monthly_budget=2300,
        json_path=JSON_OUTPUT,
    )
    if data:
        return {"status": "success", "message": "图表数据已重新同步"}
    return {"status": "empty", "message": "数据库暂无账单数据"}


# 6. 挂载静态文件目录 (dashboard.html, manager.html)
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")

if __name__ == "__main__":
    import uvicorn

    # 初始化建表
    init_db()

    # 如果数据库尚不存在，可以解开下行将 Excel 导入一次：
    # import_excel_to_sqlite(r"D:\files\账单\2609.xlsx")

    # 启动时先计算一次生成最新的 JSON
    analyze.run_analysis_from_db(
        db_path=DB_PATH, monthly_budget=2300, json_path=JSON_OUTPUT
    )

    print("\n" + "=" * 60)
    print("服务已启动：")
    print("  👉 图表看板:   http://localhost:8000/dashboard.html")
    print("  👉 记账管理页: http://localhost:8000/manager.html")
    print("=" * 60 + "\n")

    uvicorn.run(app, host="0.0.0.0", port=8000)