# db_manager.py
import os
import re
import sqlite3
import io
import urllib.parse
import pandas as pd
from fastapi.responses import StreamingResponse
from typing import Optional
from fastapi import APIRouter, HTTPException
import pandas as pd
from pydantic import BaseModel

import logger as oplog

db_router = APIRouter(prefix="/api/db", tags=["Database GUI API"])
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bills.db")
TABLE = "expenses"


def describe_expense(item) -> str:
    """把一条账单压缩成单行摘要，便于写入日志"""
    parts = []
    if getattr(item, "日期", None):
        day = str(item.日期)
        if getattr(item, "时间", None):
            day += f" {item.时间}"
        parts.append(day)
    if getattr(item, "交易类型", None):
        parts.append(f"类型={item.交易类型}")
    if getattr(item, "分类", None):
        parts.append(f"分类={item.分类}")
    if getattr(item, "品名", None):
        parts.append(f"品名={item.品名}")
    if getattr(item, "实际金额", None) is not None:
        parts.append(f"金额={item.实际金额}")
    if getattr(item, "支付账户", None):
        parts.append(f"支付={item.支付账户}")
    if getattr(item, "目标账户", None):
        parts.append(f"目标={item.目标账户}")
    if getattr(item, "结算状态", None):
        parts.append(f"结算={item.结算状态}")
    return " ".join(parts)


def get_db():
    # ---- 操作日志：建立数据库连接（每次读写前的取连接动作）----
    oplog.log_db("QUERY", "connection", f"打开数据库连接 {os.path.basename(DB_PATH)}", db=os.path.basename(DB_PATH))
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            日期 TEXT NOT NULL,
            时间 TEXT DEFAULT '',
            交易类型 TEXT DEFAULT 'EX',
            分类 TEXT NOT NULL,
            品名 TEXT NOT NULL,
            实际金额 REAL NOT NULL,
            支付账户 TEXT DEFAULT 'VX',
            目标账户 TEXT DEFAULT '',
            结算状态 TEXT DEFAULT '已结算',
            备注 TEXT DEFAULT ''
        )
    """)
    conn.commit()
    conn.close()


class ExpenseItem(BaseModel):
    日期: str
    时间: Optional[str] = ""
    交易类型: str = "EX"
    分类: str
    品名: str
    实际金额: float
    支付账户: Optional[str] = "VX"
    目标账户: Optional[str] = ""
    结算状态: Optional[str] = "已结算"
    备注: Optional[str] = ""


class ExpenseUpdateItem(BaseModel):
    日期: Optional[str] = None
    时间: Optional[str] = None
    交易类型: Optional[str] = None
    分类: Optional[str] = None
    品名: Optional[str] = None
    实际金额: Optional[float] = None
    支付账户: Optional[str] = None
    目标账户: Optional[str] = None
    备注: Optional[str] = None


@db_router.get("/expenses")
def list_expenses(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    category: Optional[str] = None,
    pay_acc: Optional[str] = None,
    sort_order: Optional[str] = "desc",
    exact_category: Optional[bool] = False,
    # ======= 新增参数 =======
    trans_type: Optional[str] = None,       # 交易类型 (EX/IN/AP/AR/TR)
    merchant: Optional[str] = None,         # 目标账户/商户
    min_amount: Optional[float] = None,     # 最低金额
    max_amount: Optional[float] = None,     # 最高金额
    name: Optional[str] = None              # 品名关键字
):
    conn = get_db()
    cursor = conn.cursor()

    query = "SELECT * FROM expenses WHERE 1=1"
    params = []

    # 1. 日期筛选
    if start_date and start_date.strip():
        query += " AND 日期 >= ?"
        params.append(start_date.strip())
    if end_date and end_date.strip():
        query += " AND 日期 <= ?"
        params.append(end_date.strip())

    # 2. 分类筛选
    if category and category.strip():
        cat_val = category.strip()
        if exact_category:
            query += " AND 分类 = ?"
            params.append(cat_val)
        else:
            query += " AND 分类 LIKE ?"
            params.append(f"%{cat_val}%")

    # 3. 源账户筛选
    if pay_acc and pay_acc.strip():
        query += " AND (支付账户 = ? OR 支付账户 LIKE ?)"
        params.extend([pay_acc.strip(), f"%{pay_acc.strip()}%"])

    # ======= 4. 新增：交易类型精准匹配 =======
    if trans_type and trans_type.strip():
        query += " AND 交易类型 = ?"
        params.append(trans_type.strip())

    # ======= 5. 新增：品名模糊搜索 =======
    if name and name.strip():
        query += " AND 品名 LIKE ?"
        params.append(f"%{name.strip()}%")

    # ======= 6. 新增：目标账户模糊匹配 =======
    if merchant and merchant.strip():
        query += " AND 目标账户 LIKE ?"
        params.append(f"%{merchant.strip()}%")

    # ======= 7. 新增：金额范围筛选 =======
    if min_amount is not None:
        query += " AND 实际金额 >= ?"
        params.append(min_amount)
    if max_amount is not None:
        query += " AND 实际金额 <= ?"
        params.append(max_amount)

    # 8. 排序方向
    direction = "ASC" if str(sort_order).strip().lower() == "asc" else "DESC"
    query += f" ORDER BY 日期 {direction}, 时间 {direction}, id {direction}"

    cursor.execute(query, params)
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()

    # ---- 操作日志：查询 bills.db/expenses ----
    oplog.log_db(
        "QUERY",
        TABLE,
        f"筛选账单，命中 {len(rows)} 条",
        filters={k: v for k, v in {
            "start_date": start_date, "end_date": end_date,
            "category": category, "exact_category": exact_category if category else None,
            "pay_acc": pay_acc, "trans_type": trans_type, "merchant": merchant,
            "name": name, "min_amount": min_amount, "max_amount": max_amount,
            "sort_order": direction,
        }.items() if v not in (None, "")},
        result_count=len(rows),
    )
    return rows


@db_router.post("/expenses")
def add_expense(item: ExpenseItem):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO expenses (日期, 时间, 交易类型, 分类, 品名, 实际金额, 支付账户, 目标账户, 结算状态, 备注)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
        (
            item.日期,
            item.时间,
            item.交易类型,
            item.分类,
            item.品名,
            item.实际金额,
            item.支付账户,
            item.目标账户,
            item.结算状态,
            item.备注,
        ),
    )
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()

    # ---- 操作日志：新增账单条目 ----
    oplog.log_db(
        "CREATE", TABLE,
        f"新增账单：{describe_expense(item)}",
        row_id=new_id,
        fields=item.model_dump(),
    )
    return {"status": "success", "id": new_id}


@db_router.put("/expenses/{item_id}")
def update_expense(item_id: int, item: ExpenseUpdateItem):
    conn = get_db()
    cursor = conn.cursor()

    # 先取出修改前的原值，日志里记录「从什么变成什么」才可追溯
    before = cursor.execute(
        "SELECT * FROM expenses WHERE id = ?", (item_id,)
    ).fetchone()

    fields = []
    values = []
    for k, v in item.model_dump(exclude_unset=True).items():
        if v is not None:
            fields.append(f"{k} = ?")
            values.append(v)

    if not fields:
        conn.close()
        oplog.log_db("UPDATE", TABLE, f"修改账单 id={item_id}：未提交任何变更", row_id=item_id)
        return {"status": "no_changes"}

    values.append(item_id)
    sql = f"UPDATE expenses SET {', '.join(fields)} WHERE id = ?"
    cursor.execute(sql, values)
    affected = cursor.rowcount
    conn.commit()
    conn.close()

    # ---- 操作日志：修改账单条目（逐字段记录 旧值 -> 新值）----
    changes = {}
    for k in item.model_dump(exclude_unset=True):
        if before is not None and dict(before).get(k) != getattr(item, k, None):
            changes[k] = {
                "from": dict(before).get(k) if before is not None else None,
                "to": getattr(item, k, None),
            }
    change_text = "，".join(f"{k}: {v['from']} -> {v['to']}" for k, v in changes.items())
    oplog.log_db(
        "UPDATE", TABLE,
        f"修改账单 id={item_id}：{change_text or '值未发生实际变化'}",
        row_id=item_id,
        matched=affected,
        changes=changes,
    )
    return {"status": "success", "matched": affected}


@db_router.delete("/expenses/{item_id}")
def delete_expense(item_id: int):
    conn = get_db()
    cursor = conn.cursor()

    # 删除前留存整条记录的快照，用于事后审计与恢复
    snapshot = cursor.execute(
        "SELECT * FROM expenses WHERE id = ?", (item_id,)
    ).fetchone()

    cursor.execute("DELETE FROM expenses WHERE id = ?", (item_id,))
    affected = cursor.rowcount
    conn.commit()
    conn.close()

    # ---- 操作日志：删除账单条目 ----
    oplog.log_db(
        "DELETE", TABLE,
        f"删除账单 id={item_id}"
        + (f"：{dict(snapshot).get('日期', '')} {dict(snapshot).get('分类', '')} "
           f"{dict(snapshot).get('品名', '')} 金额={dict(snapshot).get('实际金额', '')}" if snapshot else "（记录不存在）"),
        row_id=item_id,
        matched=affected,
        deleted_snapshot=dict(snapshot) if snapshot else None,
    )
    return {"status": "deleted", "matched": affected}


@db_router.get("/export_excel")
def export_expenses_to_excel(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    category: Optional[str] = None,
    pay_acc: Optional[str] = None,
    trans_type: Optional[str] = None,
    merchant: Optional[str] = None,
    min_amount: Optional[float] = None,
    max_amount: Optional[float] = None,
    name: Optional[str] = None,
    exact_category: Optional[bool] = False,
    sort_order: Optional[str] = "desc"
):
    """根据前端当前生效的筛选条件，导出符合条件的条目为 Excel"""
    # 1. 复用 list_expenses 的查询逻辑获取过滤后的字典列表
    rows = list_expenses(
        start_date=start_date,
        end_date=end_date,
        category=category,
        pay_acc=pay_acc,
        sort_order=sort_order,
        exact_category=exact_category,
        trans_type=trans_type,
        merchant=merchant,
        min_amount=min_amount,
        max_amount=max_amount,
        name=name
    )

    df = pd.DataFrame(rows)
    if df.empty:
        # 空表兜底
        df = pd.DataFrame(columns=["id", "日期", "时间", "交易类型", "分类", "品名", "实际金额", "支付账户", "目标账户", "结算状态", "备注"])

    # 规范化列名导出
    df = df.rename(columns={"支付账户": "源账户", "实际金额": "金额"})

    # 2. 写入内存流
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="账单明细")
    output.seek(0)

    # 3. 触发浏览器原生下载弹窗
    filename = "账单筛选导出.xlsx"
    encoded_filename = urllib.parse.quote(filename)
    headers = {
        "Content-Disposition": f"attachment; filename*=utf-8''{encoded_filename}"
    }

    # ---- 操作日志：导出 Excel ----
    oplog.log_db(
        "EXPORT", TABLE,
        f"导出账单 Excel（{len(rows)} 条）",
        result_count=len(rows),
        filename=filename,
    )

    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers
    )