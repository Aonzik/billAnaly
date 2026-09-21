# ai_assistant.py
import json
import os
import sqlite3
import yaml
from typing import Optional
from fastapi import APIRouter, HTTPException
from openai import OpenAI
from pydantic import BaseModel

ai_router = APIRouter(prefix="/api/ai", tags=["AI Assistant API"])

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.yaml")
DB_PATH = os.path.join(BASE_DIR, "bills.db")


def load_config() -> dict:
    """动态读取 YAML 配置，支持免重启热更新"""
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            print(f"[AI Error] 读取 config.yaml 异常: {e}")
    return {}


def get_task_config(task_name: str) -> tuple[dict, str]:
    """获取指定任务的配置项，并格式化全局 user_habits 为文本"""
    cfg = load_config()
    tasks_cfg = cfg.get("ai_tasks", {})
    task_cfg = tasks_cfg.get(task_name, {})

    # 获取公共消费画像并拼接为 Markdown 列表
    habits_list = tasks_cfg.get("user_habits", [])
    habits_text = "\n".join([f"- {h}" for h in habits_list]) if habits_list else "暂无特殊习惯记录。"

    return task_cfg, habits_text


# 读取底层服务基础配置（API Key / Base URL / Model）
cfg_init = load_config()
ds_cfg = cfg_init.get("deepseek", {})
DEEPSEEK_API_KEY = ds_cfg.get("api_key", os.getenv("DEEPSEEK_API_KEY", "")).strip()
DEEPSEEK_BASE_URL = ds_cfg.get("base_url", "https://api.deepseek.com")
DEEPSEEK_MODEL = ds_cfg.get("model", "deepseek-flash")

client = (
    OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)
    if DEEPSEEK_API_KEY and DEEPSEEK_API_KEY != "你的_DEEPSEEK_API_KEY"
    else None
)

# 映射字典：代号 -> 自然语言文本
TYPE_DICT = {
    "EX": "支出",
    "IN": "收入",
    "AP": "收回",
    "AR": "垫付",
    "TR": "转移",
}

ACC_DICT = {
    "VX": "微信",
    "AL": "支付宝",
    "BK": "银行卡",
    "TC": "交通卡",
    "HB": "花呗",
}


def format_acc(account_val: str) -> str:
    if not account_val:
        return ""
    val_clean = str(account_val).strip()
    return ACC_DICT.get(val_clean, val_clean)


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def format_records_to_text(rows: list[dict]) -> str:
    """将数据库行数据转换为紧凑格式的流水文本"""
    expense_lines = ["[日期时间] 交易类型 | 消费分类 | 品名 | 实际金额(RMB) | 源账户@目标账户 (备注:备注)"]
    for r in rows:
        time_str = f" {r['时间']}" if r.get("时间") else ""
        remark_str = f" (备注:{r['备注']})" if r.get("备注") else ""
        raw_type = str(r.get("交易类型", "")).strip()
        type_str = TYPE_DICT.get(raw_type, raw_type)
        pay_acc_str = format_acc(r.get("支付账户", ""))
        target_val = format_acc(r.get("目标账户", ""))
        merchant_str = f"@{target_val}" if target_val else ""

        expense_lines.append(
            f"[{r['日期']}{time_str}] {type_str} | {r['分类']} | {r['品名']} | {r['实际金额']} | {pay_acc_str}{merchant_str}{remark_str}"
        )
    return "\n".join(expense_lines)


# =========================================================================
# 功能 1：消费习惯诊断与财务私教建议（dashboard 悬浮球）
# =========================================================================
@ai_router.get("/diagnose")
def analyze_financial_habits():
    if not client:
        return {"advice": "❌ 后端错误：OpenAI 客户端未初始化，请检查 API Key 配置。"}

    json_path = os.path.join(BASE_DIR, "static", "expense_data.json")
    if not os.path.exists(json_path):
        alt_path = os.path.join(BASE_DIR, "expense_data.json")
        if os.path.exists(alt_path):
            json_path = alt_path
        else:
            return {"advice": f"❌ 未找到账单缓存数据文件: {json_path}，请先重新计算生成一次！"}

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        top_merchants_detail = [
            {"商户名称": m.get("name", ""), "频次": m.get("count"), "总额": m.get("amount")}
            for m in data.get("top_merchants", [])[:3]
        ]

        context_summary_dict = {
            "花呗下月待还": data.get("hb", {}).get("need_pay"),
            "月总预算": data.get("budget", {}).get("monthly_budget"),
            "扣除房租等固定支出后日均可用": data.get("budget", {}).get("daily_total_budget"),
            "剩余天数建议可用日均": data.get("budget", {}).get("dynamic_safe_budget"),
            "安全日均基线": data.get("budget", {}).get("safe_daily_baseline"),
            "拿铁因子（严格限定为饮食*分类的零食饮品）": {
                "累计金额": data.get("latte", {}).get("cost"),
                "饮品部分": data.get("latte", {}).get("drinks_cost"),
                "零食部分": data.get("latte", {}).get("snacks_cost"),
            },
            "高频复购商户前三": top_merchants_detail,
        }

        # 动态读取 YAML 中的 diagnose 节点
        task_cfg, habits_text = get_task_config("diagnose")
        template = task_cfg.get(
            "prompt_template",
            "数据：\n{context_summary}\n\n习惯：\n{user_habits}\n\n请给出诊断。",
        )

        user_prompt = template.format(
            context_summary=json.dumps(context_summary_dict, ensure_ascii=False, indent=2),
            user_habits=habits_text,
        )

        messages = []
        if task_cfg.get("system_prompt"):
            messages.append({"role": "system", "content": task_cfg["system_prompt"]})
        messages.append({"role": "user", "content": user_prompt})

        response = client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=messages,
            temperature=task_cfg.get("temperature", 0.6),
            max_tokens=task_cfg.get("max_tokens", 2048),
            extra_body={"thinking": {"type": "disabled"}},
        )

        reply_text = (response.choices[0].message.content or "").strip()
        return {"advice": reply_text if reply_text else "生成超时或未获取到正文，请重试。"}

    except Exception as e:
        return {"advice": f"❌ DeepSeek 调用异常: {str(e)}"}


# =========================================================================
# 功能 2：自然语言/语音转文字后结构化提取账单条目（manager 悬浮球）
# =========================================================================
class VoiceInputReq(BaseModel):
    text: str


@ai_router.post("/parse_expense")
def parse_natural_language_expense(req: VoiceInputReq):
    """提取单笔记账条目保持低温解析"""
    if not client:
        raise HTTPException(status_code=500, detail="未配置 DEEPSEEK_API_KEY")

    prompt = f"""请将用户的记账口语解析为严格的 JSON 格式。
用户口语输入："{req.text}"

字段必须且仅能包含以下各项：
- "日期": 标准 "YYYY-MM-DD" 格式。若未提及具体日期则填今日；
- "时间": "HH:MM" 格式，未提及填 "12:00"；
- "交易类型": 必须是以下之一: "EX"(支出), "IN"(收入), "AR"(垫付), "AP"(收回), "TR"(转移/花呗还款)；
- "分类": 常见分类（如 饮食、饮食*、交通、日居、娱乐、周边、居住 等。注意：非正餐的零食、奶茶、咖啡归为 "饮食*"，正餐和矿泉水归为 "饮食"）；
- "品名": 具体的物品或服务名称；
- "实际金额": 纯浮点数（必须大于0）；
- "支付账户": 必须提取为标准代码之一: "VX"(微信), "AL"(支付宝), "BK"(银行卡), "TC"(交通卡), "HB"(花呗) 或自定义人名；
- "目标账户": 商户或收款方名称，未提及填空字符串；
- "备注": 补充细节，未提及填空字符串。

必须直接输出标准合法 JSON 对象，不要用 markdown 格式包裹，不要有任何多余文字。"""

    response = client.chat.completions.create(
        model=DEEPSEEK_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
    )
    content = response.choices[0].message.content.strip()
    if content.startswith("```"):
        content = content.replace("```json", "").replace("```", "").strip()

    try:
        return json.loads(content)
    except Exception:
        raise HTTPException(status_code=400, detail=f"解析大模型返回失败: {content}")


# =========================================================================
# 功能 3：智能问答悬浮球（Chat with Your Bill）
# =========================================================================
class ChatQueryReq(BaseModel):
    query: str


@ai_router.post("/chat")
def chat_with_bills(req: ChatQueryReq):
    if not client:
        raise HTTPException(status_code=500, detail="未配置 DEEPSEEK_API_KEY")

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 日期, 时间, 交易类型, 分类, 品名, 实际金额, 支付账户, 目标账户, 备注 
        FROM expenses 
        ORDER BY 日期 ASC, 时间 ASC, id ASC 
        LIMIT 200
    """)
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()

    if not rows:
        return {"answer": "当前数据库中暂无消费记录可供查询。"}

    compact_records = format_records_to_text(rows)

    # 动态读取 YAML 中的 chat 节点
    task_cfg, habits_text = get_task_config("chat")
    template = task_cfg.get(
        "prompt_template",
        "流水：\n{records}\n\n习惯：\n{user_habits}\n\n用户提问：{user_query}",
    )

    user_prompt = template.format(
        records=compact_records,
        user_habits=habits_text,
        user_query=req.query,
    )

    messages = []
    if task_cfg.get("system_prompt"):
        messages.append({"role": "system", "content": task_cfg["system_prompt"]})
    messages.append({"role": "user", "content": user_prompt})

    response = client.chat.completions.create(
        model=DEEPSEEK_MODEL,
        messages=messages,
        temperature=task_cfg.get("temperature", 0.3),
        max_tokens=task_cfg.get("max_tokens", 2048),
        extra_body={"thinking": {"type": "disabled"}},
    )
    reply_text = (response.choices[0].message.content or "").strip()
    return {"answer": reply_text or "未能输出回答，请重试。"}


# =========================================================================
# 功能 4：月度账单精读
# =========================================================================
@ai_router.get("/deep_read")
def deep_read_monthly_expenses(year_month: str = "2026-09"):
    if not client:
        raise HTTPException(status_code=500, detail="未配置 DEEPSEEK_API_KEY")

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT 日期, 时间, 交易类型, 分类, 品名, 实际金额, 支付账户, 目标账户, 备注 
        FROM expenses 
        WHERE 日期 LIKE ? 
        ORDER BY 日期 ASC, 时间 ASC, id ASC
        """,
        (f"{year_month}%",),
    )
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()

    if not rows:
        return {"report": f"⚠️ 账单数据库中未检索到 {year_month} 的消费记录。"}

    raw_records_text = format_records_to_text(rows)

    # 动态读取 YAML 中的 deep_read 节点
    task_cfg, habits_text = get_task_config("deep_read")
    template = task_cfg.get(
        "prompt_template",
        "月份：{year_month}，共 {record_count} 笔。\n流水：\n{records}\n\n习惯：\n{user_habits}",
    )

    user_prompt = template.format(
        year_month=year_month,
        record_count=len(rows),
        records=raw_records_text,
        user_habits=habits_text,
    )

    messages = []
    if task_cfg.get("system_prompt"):
        messages.append({"role": "system", "content": task_cfg["system_prompt"]})
    messages.append({"role": "user", "content": user_prompt})

    try:
        response = client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=messages,
            temperature=task_cfg.get("temperature", 0.3),
            max_tokens=task_cfg.get("max_tokens", 4096),
            extra_body={"thinking": {"type": "disabled"}},
        )
        return {"report": response.choices[0].message.content.strip()}
    except Exception as e:
        return {"report": f"❌ 精读生成失败: {str(e)}"}