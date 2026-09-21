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

# 1. 动态加载 config.yaml
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.yaml")


def load_config() -> dict:
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            print(f"[AI Error] 读取 config.yaml 异常: {e}")
    return {}


cfg = load_config()
ds_cfg = cfg.get("deepseek", {})

# 2. 读取配置，支持环境变量与默认值兜底
DEEPSEEK_API_KEY = ds_cfg.get(
    "api_key", os.getenv("DEEPSEEK_API_KEY", "")
).strip()
DEEPSEEK_BASE_URL = ds_cfg.get("base_url", "https://api.deepseek.com")
DEEPSEEK_MODEL = ds_cfg.get("model", "deepseek-flash")

client = (
    OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)
    if DEEPSEEK_API_KEY != "你的_DEEPSEEK_API_KEY"
    else None
)
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bills.db")

# 1. 映射字典：代号 -> 易于大模型精准理解的自然语言文本
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
    """账户转换辅助函数：如果是代号则转中文，若原本是文本/人名则保持原样"""
    if not account_val:
        return ""
    val_clean = str(account_val).strip()
    return ACC_DICT.get(val_clean, val_clean)


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# =========================================================================
# 功能 1：消费习惯诊断与财务私教建议（dashboard 悬浮球）
# =========================================================================
# ai_assistant.py 中的 /diagnose 函数完全替换为以下代码：

@ai_router.get("/diagnose")
def analyze_financial_habits():
    print("\n" + "="*50)
    print(">>> [AI Debug] 1. 开始处理 /api/ai/diagnose 请求")
    
    # 1. 验证客户端与 API Key
    if not client:
        print(">>> [AI Error] client 对象为空，未初始化！")
        return {"advice": "❌ 后端错误：OpenAI 客户端未初始化，请检查 API Key 配置。"}
    
    print(f">>> [AI Debug] 2. 检查 API Key: {client.api_key[:8]}******")

    # 2. 使用绝对路径读取 static/expense_data.json
    current_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(current_dir, "static", "expense_data.json")
    print(f">>> [AI Debug] 3. 正在读取文件: {json_path}")

    if not os.path.exists(json_path):
        # 兼容备用路径：看看是不是直接在根目录
        alt_path = os.path.join(current_dir, "expense_data.json")
        if os.path.exists(alt_path):
            json_path = alt_path
        else:
            print(f">>> [AI Error] 找不到数据文件！请确认 {json_path} 是否存在")
            return {"advice": f"❌ 未找到账单缓存数据文件: {json_path}，请先重新计算生成一次！"}

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        print(">>> [AI Debug] 4. 账单缓存数据读取成功！")

        # 提取前三商户并尝试补充其主要买的品类/品名
        top_merchants_detail = []
        for m in data.get("top_merchants", [])[:3]:
            m_name = m.get("name", "")
            top_merchants_detail.append({
                "商户名称": m_name,
                "频次": m.get("count"),
                "总额": m.get("amount")
            })

        context_summary = {
            "花呗下月待还": data.get("hb", {}).get("need_pay"),
            "月总预算": data.get("budget", {}).get("monthly_budget"),
            "扣除房租等固定支出后日均可用": data.get("budget", {}).get("daily_total_budget"),
            "剩余天数建议可用日均": data.get("budget", {}).get("dynamic_safe_budget"),
            "安全日均基线": data.get("budget", {}).get("safe_daily_baseline"),
            "拿铁因子（严格限定为饮食*分类的零食饮品）": {
                "累计金额": data.get("latte", {}).get("cost"),
                "饮品部分": data.get("latte", {}).get("drinks_cost"),
                "零食部分": data.get("latte", {}).get("snacks_cost")
            },
            "高频复购商户前三": top_merchants_detail,
            "个人消费习惯特别说明": [
                "「猛火炒饭」是正餐（平价快餐），不属于拿铁因子或零食！",
                "「优特卖」主要是批量采购低价临期零食饮品，是拿铁因子的主要来源。"
                "用户习惯饮用怡宝、哇哈哈等灌装纯净水，属于硬性饮水需求，不计入拿铁因子。"
            ]
        }

        prompt = f"""你是一位敏锐、幽默且切中要害的日常财务顾问。以下是用户本月的核心账单数据和消费习惯特征：
{json.dumps(context_summary, ensure_ascii=False, indent=2)}

【特别提示与准则】：
1. 区分“正餐”与“拿铁因子”
2. 拿铁因子主要聚焦在零食和含糖饮品（优特卖等），分析应着重于这类无意识的小额糖分/零食消耗。

请分 3 点给出务实、犀利但不刻板的诊断（300字以内）：
1. 预算水位预警（指出日均压缩现状与花呗预留）；
2. 拿铁因子成瘾度分析（聚焦零食饮品）；
3. 针对性的省钱建议。"""

        print(">>> [AI Debug] 5. 正在向 DeepSeek 服务器发送请求 (模型: deepseek-flash)...")
        response = client.chat.completions.create(
            model="deepseek-flash",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.6,
            max_tokens=2048,  # 必须设大，防止思考过程消耗完 token 配额
            extra_body={"thinking": {"type": "disabled"}}
        )
        
        msg = response.choices[0].message
        
        # 1. 优先获取正式回答内容
        final_content = (msg.content or "").strip()
        
        # 2. 如果 content 为空，判断是否是被 reasoning 截断
        if not final_content:
            reasoning = getattr(msg, "reasoning_content", "") or ""
            print(f">>> [AI Warning] 正式内容为空！检测到思考链长度: {len(reasoning)}")
            # 如果触发了截断，提示用户调大 max_tokens
            reply_text = "生成超时或 Token 额度不足，未获取到完整正文，请重试。"
        else:
            reply_text = final_content

        print(">>> [AI Debug] 6. 解析完成！正式回答内容长度:", len(reply_text))
        print(">>> [AI Debug] 正文预览:", reply_text[:100])
        print("="*50 + "\n")
        
        return {"advice": reply_text}

    except Exception as e:
        import traceback
        err_detail = traceback.format_exc()
        print(">>> [AI Error] 捕获到运行时异常:")
        print(err_detail)
        print("="*50 + "\n")
        return {"advice": f"❌ DeepSeek 调用异常: {str(e)}"}


# =========================================================================
# 功能 2：自然语言/语音转文字后结构化提取账单条目（manager 悬浮球）
# =========================================================================
class VoiceInputReq(BaseModel):
    text: str  # 浏览器语音转文字或手打的口语，如 "今天下午在优特卖买了包薯片和可乐花了15块5用微信付的"


@ai_router.post("/parse_expense")
def parse_natural_language_expense(req: VoiceInputReq):
    """将口语文本解析为符合数据库约束的标准 JSON 格式"""
    if not client:
        raise HTTPException(status_code=500, detail="未配置 DEEPSEEK_API_KEY")

    prompt = f"""请将用户的记账口语解析为严格的 JSON 格式。当前年份为 2026 年。
用户口语输入："{req.text}"

字段必须且仅能包含以下各项：
- "日期": 标准 "YYYY-MM-DD" 格式。若未提及具体日期则填今日（如不确定填 "2026-09-20"）；
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
        model="deepseek-flash",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,  # 极低随机性确保结构稳定
    )
    content = response.choices[0].message.content.strip()
    if content.startswith("```"):
        content = content.replace("```json", "").replace("```", "").strip()

    try:
        parsed_data = json.loads(content)
        return parsed_data
    except Exception as e:
        raise HTTPException(
            status_code=400, detail=f"解析大模型返回失败: {content}"
        )


# =========================================================================
# 功能 3：智能问答悬浮球（Chat with Your Bill）
# =========================================================================
class ChatQueryReq(BaseModel):
    query: str  # 用户问题


@ai_router.post("/chat")
def chat_with_bills(req: ChatQueryReq):
    """支持用户任意自然语言提问，结合 SQLite 中的数据进行推理和精确解答"""
    if not client:
        raise HTTPException(status_code=500, detail="未配置 DEEPSEEK_API_KEY")

    # 从 SQLite 中提取近期全部记录并转化为紧凑文本
    conn = get_db_connection()
    cursor = conn.cursor()
    # 补充提取“时间”字段，按时间升序排列便于 AI 理清消费脉络
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
    # 紧凑序列化流水（含表头说明与中文语义转换）
    expense_lines = [
        "[日期时间] 交易类型 | 消费分类 | 品名 | 实际金额(RMB) | 源账户@目标账户 (备注:备注)"
    ]
    for r in rows:
        time_str = f" {r['时间']}" if r.get("时间") else ""
        remark_str = f" (备注:{r['备注']})" if r.get("备注") else ""
        # 1. 交易类型转中文
        raw_type = str(r.get("交易类型", "")).strip()
        type_str = TYPE_DICT.get(raw_type, raw_type)
        # 2. 支付账户转中文
        pay_acc_str = format_acc(r.get("支付账户", ""))
        # 3. 目标账户转中文
        target_val = format_acc(r.get("目标账户", ""))
        merchant_str = f"@{target_val}" if target_val else ""
        expense_lines.append(
            f"[{r['日期']}{time_str}] {type_str} | {r['分类']} | {r['品名']} | {r['实际金额']} | {pay_acc_str}{merchant_str}{remark_str}"
        )
    compact_records = "\n".join(expense_lines)

    prompt = f"""你是账单系统的专属数据管家。以下是用户近期的真实消费明细流水（最多200条）：
{compact_records}

用户提问："{req.query}"

请根据上述账单流水精确回答用户的问题。要求：
1. 涉及计算时必须准确（如算总额、占比、均价）；
2. 答案直接切入主题，条理清晰，言简意赅。
注意：转移、垫付、收回等非消费行为不属于实际消费"""

    response = client.chat.completions.create(
        model="deepseek-flash",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=2048,
        extra_body={"thinking": {"type": "disabled"}}
    )
    msg = response.choices[0].message
    reply_text = (msg.content or "").strip()
    if not reply_text:
        reply_text = "抱歉，由于模型思考过程超出长度限制，未能输出回答，请重试。"
        
    return {"answer": reply_text}


# 月度账单精读
@ai_router.get("/deep_read")
def deep_read_monthly_expenses(year_month: str = "2026-09"):
    """将指定月份的全部流水喂给 DeepSeek 进行全量精读与行为学洞察"""
    if not client:
        raise HTTPException(
            status_code=500, detail="未配置 DEEPSEEK_API_KEY"
        )

    conn = get_db_connection()
    cursor = conn.cursor()
    # 提取选定月份的所有流水（按时间顺序排序，方便 AI 捕捉时间脉络）
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

    # 紧凑序列化流水
    expense_lines = ["[日期时间] 交易类型 | 消费分类 | 品名 | 实际金额(RMB) | 源账户@目标账户 (备注:备注)"]
    for r in rows:
        time_str = f" {r['时间']}" if r["时间"] else ""
        remark_str = f" (备注:{r['备注']})" if r["备注"] else ""
        # 1. 交易类型转中文（兜底保持原字符串）
        raw_type = str(r.get("交易类型", "")).strip()
        type_str = TYPE_DICT.get(raw_type, raw_type)

        # 2. 支付账户转中文
        pay_acc_str = format_acc(r.get("支付账户", ""))

        # 3. 目标账户转中文（如果是 AL/VX 等代号转成中文，如果是人名/商户名直接保留）
        target_val = format_acc(r.get("目标账户", ""))
        merchant_str = f"@{target_val}" if target_val else ""

        expense_lines.append(
            f"[{r['日期']}{time_str}] {type_str} | {r['分类']} | {r['品名']} | {r['实际金额']} | {pay_acc_str}{merchant_str}{remark_str}"
        )

    raw_records_text = "\n".join(expense_lines)

    prompt = f"""你是一位敏锐的行为财务学专家。以下是用户在 【{year_month}】 月份的【全部完整消费流水（共 {len(rows)} 笔）】：
{raw_records_text}

【你的任务】：请通读每一笔消费，做一份全景式的「消费行为深度精读审计报告」。

请包含以下维度（使用清晰的 Markdown 标题与要点排版，言辞犀利、具体，直接点名具体商品与金额）：
1. **时间节律与情绪消费捕获**：通读每笔时间与日期，指出是否存在深夜冲动消费（如22点后）、周末放纵开销，或某些固定时段的无意识花销习惯。
2. **微小流失洞察（隐形刺客）**：找出单笔金额很小（<15元）但出现极其高频、不知不觉吞噬预算的商品或行为特征。
3. **聪明省钱点赞**：指出流水中体现出哪些极致性价比的省钱操作（如代金券、平价快餐、折扣临期囤货等），予以肯定。
4. **异常脉冲账目排查**：单笔大额或不合常规节奏的支出复盘，分析其对整月预算的冲击。
5. **下月精准靶向调整建议**：给出 2~3 条可立即执行、不严重降低生活质量的靶向减负动作。
注意：转移、垫付、收回等非消费行为不计入消费分析，但请在报告中标注出来。"""

    try:
        response = client.chat.completions.create(
            model="deepseek-flash",
            messages=[
                {
                    "role": "system",
                    "content": "你是一位客观敏锐的个人财务审计师，请直接输出结构严整、见解深刻的 Markdown 报告。",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=4096,
            extra_body={"thinking": {"type": "disabled"}},  # 关闭思考链，极速直出
        )
        return {"report": response.choices[0].message.content.strip()}
        # return {"report": prompt}  # 临时返回 prompt 以便调试
    except Exception as e:
        return {"report": f"❌ 精读生成失败: {str(e)}"}