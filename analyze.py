# analyze.py —— 直接对 bills.db 中的指定条目进行分析（无 pandas 依赖）
import calendar
import json
import os
import re
import sys
import sqlite3
import unicodedata
from collections import defaultdict

import yaml
import jieba
import matplotlib.pyplot as plt
import numpy as np

# 设置 Matplotlib 中文字体支持
plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "Arial Unicode MS"]
plt.rcParams["axes.unicode_minus"] = False


def load_system_config(config_file: str = "config.yaml") -> dict:
    """安全读取 YAML 配置文件，带兜底保障"""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(base_dir, config_file)

    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                cfg = yaml.safe_load(f)
                return cfg if isinstance(cfg, dict) else {}
        except Exception as e:
            print(f"[Warning] 读取 {config_file} 失败: {e}，将使用系统默认配置。")
    return {}


def extract_item_quantity(name_str):
    """提取商品数量（匹配 (x24)、（x24）、*24 等，未标注默认为 1）"""
    pattern = r"[\(（\s]*[xX*×](\d+)[\)）\s]*"
    match = re.search(pattern, str(name_str))
    return int(match.group(1)) if match else 1


def pad_chinese(text, width):
    """根据东亚字符真实终端显示宽度补齐空格，确保中英混排严格对齐"""
    text = str(text)
    disp_width = sum(
        2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in text
    )
    padding = max(0, width - disp_width)
    return text + " " * padding


def parse_year_month_from_date(raw_str):
    """从完整日期字符串解析 (year, month)，解析失败返回 (None, None)。
    支持 2026-09-01 / 2026-9-1 / 26-09-01 / 2026/9/1 / 20260901 / 260901 / 0901 等格式。"""
    raw = str(raw_str).strip()
    sep_match = re.search(r"^(\d{2,4})[-/.]([0-1]?\d)[-/.]([0-3]?\d)", raw)
    if sep_match:
        year = int(sep_match.group(1))
        if year < 100:
            year += 2000
        return year, int(sep_match.group(2))
    if raw.isdigit():
        if len(raw) == 8:      # 20260901 -> 年 2026, 月 09
            return int(raw[:4]), int(raw[4:6])
        if len(raw) == 6:      # 260901   -> 年 2026, 月 09
            return 2000 + int(raw[:2]), int(raw[2:4])
        if len(raw) == 4:      # 0901     -> 只有月日，年份未知
            return None, int(raw[:2])
    return None, None


def parse_year_month_arg(value):
    """解析 '2026-09' / '2026-9' / '2026/09' / '202609' 形式的年月参数为 (year, month)，失败返回 (None, None)"""
    raw = str(value).strip()
    m = re.match(r"^(\d{2,4})[-/](\d{1,2})$", raw)
    if m:
        year = int(m.group(1))
        if year < 100:
            year += 2000
        return year, int(m.group(2))
    if raw.isdigit() and len(raw) == 6:   # 202609
        return int(raw[:4]), int(raw[4:6])
    return None, None


def build_month_json_path(base_path, year, month):
    """按月份隔离的 JSON 缓存路径，如 static/expense_data.json -> static/expense_data_2026-09.json"""
    directory = os.path.dirname(base_path)
    name = f"expense_data_{int(year)}-{int(month):02d}.json"
    return os.path.join(directory, name) if directory else name

# =========================================================================
# 词云清洗规则与统计引擎
# =========================================================================
# 过滤助词、交易通道、无实际商品特征的杂词
WORDCLOUD_STOP_WORDS = {
    "微信", "支付宝", "支付", "支出", "账单", "退款", "购买", "消费",
    "商品", "代金券", "优惠券", "红包", "其他", "备注", "单人", "这个"
}

def clean_product_name(text: str) -> str:
    """清洗商品名中的规格、容量、包装数量（如 100ml, 300ml, .5L, x24 等）"""
    text = str(text)
    # 1. 剔除包装倍数（如 x24, *12, X6, ×2 等）
    text = re.sub(r"(?i)[xX*×]\s*\d+|\d+\s*[xX*×]", " ", text)
    # 2. 剔除容量与重量单位（如 100ml, 300ML, .5L, 1.5l, 500g, 2kg, 500毫升等）
    text = re.sub(r"(?i)\.?\d+(\.\d+)?\s*(ml|l|g|kg|oz|升|毫升|克|千克|斤|两|'')", " ", text)
    # 3. 剔除残余的纯数字和孤立量词（如 24瓶, 1箱, 2盒 等）
    text = re.sub(r"\d+\s*(瓶|罐|包|盒|份|个|支|箱|袋|听|块|片|粒|条|h)", " ", text)
    # 4. 剔除剩余的孤立小数或数字
    text = re.sub(r"[\(（].*?[\)）]", " ", text)
    return text.strip()

def generate_wordcloud_data(db_path: str = "bills.db", top_n: int = 80, year=None, month=None) -> dict:
    """提取实际支出(EX)，清洗后分词并生成频次与金额双加权数据；指定 year/month 时仅统计该月份，否则覆盖全量历史"""
    rows = []
    if os.path.exists(db_path):
        # 默认从 bills.db 全量读取跨月份历史；指定年月时只统计该月份的记录
        conn = sqlite3.connect(db_path)
        try:
            cursor = conn.cursor()
            sql = "SELECT 品名, 实际金额 FROM expenses WHERE 交易类型 = 'EX' AND 品名 IS NOT NULL AND 品名 != ''"
            params = []
            if year is not None and month is not None:
                sql += " AND 日期 LIKE ?"
                params.append(f"{int(year)}-{int(month):02d}%")
            cursor.execute(sql, params)
            rows = cursor.fetchall()
        finally:
            conn.close()

    # 注册自定义专有名词与停用词
    cfg = load_system_config()
    custom_words = cfg.get("custom_words", [])
    stop_words = cfg.get("stop_words", [])
    WORDCLOUD_STOP_WORDS.update(stop_words)
    for w in custom_words:
        w_clean = str(w).strip()
        if w_clean:
            # 动态提升该词词频，强制 jieba 不对其进行拆解
            jieba.add_word(w_clean)

    freq_dict = defaultdict(int)
    amount_dict = defaultdict(float)

    for item_name, amount in rows:
        cleaned_text = clean_product_name(item_name)
        if not cleaned_text:
            continue

        amt = float(amount or 0.0)
        tokens = jieba.lcut(cleaned_text)

        # 过滤逻辑
        valid_words = []
        for w in set(tokens):
            w_clean = w.strip()
            # 1. 过滤：单字不计
            if len(w_clean) <= 1:
                continue
            # 2. 过滤：凡是包含任何数字的词（如 300g, 50ml, 104g, .5L, x24），直接秒杀剔除！
            if re.search(r"\d", w_clean):
                continue
            # 3. 过滤：纯符号、纯英文字母残留、停用词
            if re.match(r"^[\W_]+$", w_clean) or re.match(r"^[a-zA-Z]+$", w_clean):
                continue
            if w_clean in WORDCLOUD_STOP_WORDS:
                continue
            valid_words.append(w_clean)

        for w in valid_words:
            freq_dict[w] += 1
            amount_dict[w] += amt
    # 按频次排序
    sorted_by_freq = sorted(freq_dict.items(), key=lambda x: x[1], reverse=True)[:top_n]
    by_freq_data = [{"name": k, "value": v} for k, v in sorted_by_freq if v > 0]
    # 按金额排序
    sorted_by_amount = sorted(amount_dict.items(), key=lambda x: x[1], reverse=True)[:top_n]
    by_amount_data = [{"name": k, "value": round(v, 2)} for k, v in sorted_by_amount if v > 0]

    return {"by_freq": by_freq_data, "by_amount": by_amount_data}

# =========================================================================
# 1. 核心计算层（直接消费从 bills.db 查询出的条目列表）
# =========================================================================
def process_expense_data(rows, monthly_budget=2300, current_day=None, year=None, month=None):
    """
    清洗并计算账单数据。rows 为从 bills.db 查询出的条目列表（list[dict]）。
    year / month 用于跨年份准确计算当月天数；缺省时自动从首条记录日期解析。
    """
    if rows is None:
        raise ValueError("必须提供数据库条目列表 rows")

    # 是否显式指定了核算年月（用于花呗还款的当月口径判定）
    month_scoped = year is not None and month is not None

    recs = []
    for row in rows:
        rec = {
            "日期": str(row.get("日期") or "").strip(),
            "时间": str(row.get("时间") or "").strip(),
            "交易类型": str(row.get("交易类型") or "").strip(),
            "分类": str(row.get("分类") or "").strip(),
            "品名": str(row.get("品名") or "").strip(),
            "支付账户": str(row.get("支付账户") or "").strip(),
            "目标账户": str(row.get("目标账户") or "").strip(),
            "结算状态": str(row.get("结算状态") or "").strip(),
        }
        try:
            rec["实际金额"] = float(row.get("实际金额") or 0.0)
        except (TypeError, ValueError):
            rec["实际金额"] = 0.0
        rec["件数"] = extract_item_quantity(rec["品名"])
        recs.append(rec)

    def is_accident(r):
        """识别“意外”非日常消费事件"""
        return ("意外" in r["交易类型"]) or bool(re.search(r"赔偿|意外", r["分类"]))

    def is_rent(r):
        """识别房租"""
        return (
            ("房租" in r["分类"])
            or ("房租" in r["品名"])
            or (("住房" in r["分类"] or "居家" in r["分类"]) and ("押金" in r["品名"]))
        )

    # (0) 总览数据
    # 1. 按交易类型汇总金额 (严格基于用户定义: AR=垫付, AP=收回, EX=支出, IN=收入)
    type_sums = defaultdict(float)
    for r in recs:
        type_sums[r["交易类型"]] += r["实际金额"]
    ex_val = type_sums.get("EX", 0.0)  # 支出
    in_val = type_sums.get("IN", 0.0)  # 收入
    ar_val = type_sums.get("AR", 0.0)  # 垫付
    ap_val = type_sums.get("AP", 0.0)  # 收回
    # 2. 按照公式计算三大核心财务指标
    monthly_total_expense = round(ex_val + ar_val - ap_val, 2)  # SUM(EX + AR - AP)
    monthly_net_growth = round(in_val - ex_val - ar_val + ap_val, 2)  # SUM(IN - EX - AR + AP)
    pending_recovery = round(ar_val - ap_val, 2)  # SUM(AR - AP)

    rent_total = sum(
        r["实际金额"] for r in recs if r["交易类型"] == "EX" and is_rent(r)
    )

    # (1) 花呗
    hb_spent = sum(r["实际金额"] for r in recs if r["支付账户"] == "HB")

    def is_current_month_repay(r):
        """判定当期花呗还款：指定月份时只认品名含当月月份号（如 10月花呗还款）且目标账户为 HB 的记录，
        避免把本月还上个月的钱（如 9月花呗还款）计入本期；全量分析时保持原有统计口径"""
        if r["交易类型"] != "TR" or "花呗还款" not in r["品名"]:
            return False
        if not month_scoped:
            return True
        if r["目标账户"] != "HB":
            return False
        m = re.search(r"(\d{1,2})\s*月", r["品名"])
        return m is not None and int(m.group(1)) == int(month)

    hb_repaid = sum(r["实际金额"] for r in recs if is_current_month_repay(r))
    hb_need_pay = hb_spent - hb_repaid

    # (2) 意外损益
    accident_rows = [r for r in recs if is_accident(r)]
    accident_in = sum(
        r["实际金额"] for r in accident_rows if r["交易类型"] == "IN"
    )
    accident_out = sum(
        r["实际金额"] for r in accident_rows if r["交易类型"] == "EX"
    )

    # (3) 拿铁因子
    regular_ex = [r for r in recs if r["交易类型"] == "EX" and not is_accident(r)]
    latte_rows = [r for r in regular_ex if r["分类"] == "饮食*"]

    drink_pattern = r"奶茶|茶|咖啡|可乐|雪碧|水|冰城|拿铁|饮|乳|蜜雪|库迪"
    drinks = [
        r for r in latte_rows if re.search(drink_pattern, r["品名"], re.IGNORECASE)
    ]
    snacks = [
        r for r in latte_rows if not re.search(drink_pattern, r["品名"], re.IGNORECASE)
    ]

    latte_stats = {
        "count": len(latte_rows),
        "items": sum(r["件数"] for r in latte_rows),
        "cost": sum(r["实际金额"] for r in latte_rows),
        "drinks_count": len(drinks),
        "drinks_items": sum(r["件数"] for r in drinks),
        "drinks_cost": sum(r["实际金额"] for r in drinks),
        "snacks_count": len(snacks),
        "snacks_items": sum(r["件数"] for r in snacks),
        "snacks_cost": sum(r["实际金额"] for r in snacks),
    }

    # (4) 商户复购榜
    # 读取配置文件中的剔除列表，若读取失败则使用默认值兜底
    config = load_system_config()
    default_non_merchants = ["HB", "VX", "AL", "BK", "TC", "腾讯"]
    non_merchants = config.get("non_merchants", default_non_merchants)
    # 确保比较时做去空白处理
    non_merchants = {str(item).strip() for item in non_merchants}

    merchant_map = {}
    for r in regular_ex:
        if r["目标账户"] in non_merchants:
            continue
        m = merchant_map.setdefault(
            r["目标账户"], {"orders": set(), "amount": 0.0, "items": 0}
        )
        m["orders"].add(f"{r['日期']}_{r['时间']}")
        m["amount"] += r["实际金额"]
        m["items"] += r["件数"]

    merchant_stats = sorted(
        merchant_map.items(),
        key=lambda kv: (-len(kv[1]["orders"]), -kv[1]["amount"]),
    )[:5]

    top_merchants = [
        {
            "name": name,
            "count": len(st["orders"]),
            "amount": st["amount"],
            "items": st["items"],
        }
        for name, st in merchant_stats
    ]

    # (5) 动态预算：每日净支出计算 (EX + AR - AP)
    daily_ex = defaultdict(float)
    daily_ar = defaultdict(float)
    daily_ap = defaultdict(float)
    for r in recs:
        if is_rent(r) or is_accident(r):
            continue
        if r["交易类型"] == "EX":
            daily_ex[r["日期"]] += r["实际金额"]
        elif r["交易类型"] == "AR":
            daily_ar[r["日期"]] += r["实际金额"]
        elif r["交易类型"] == "AP":
            daily_ap[r["日期"]] += r["实际金额"]

    # 按照严格财务对冲公式：EX + AR - AP
    all_dates = sorted(set(daily_ex) | set(daily_ar) | set(daily_ap))
    daily_net = [(d, daily_ex[d] + daily_ar[d] - daily_ap[d]) for d in all_dates]

    # 确定核算年份与月份：显式传入优先，否则沿用首条记录的日期（跨年份安全）
    if year is None or month is None:
        parsed_year, parsed_month = (None, None)
        if recs and recs[0]["日期"]:
            parsed_year, parsed_month = parse_year_month_from_date(recs[0]["日期"])
        if year is None:
            year = parsed_year
        if month is None:
            month = parsed_month
    if year is None:
        import datetime

        year = datetime.date.today().year
    if month is None:
        month = 9

    days_in_month = calendar.monthrange(int(year), int(month))[1]

    if current_day is None:
        day_nums = []
        for r in recs:
            match = re.search(r"(\d{1,2})$", r["日期"])
            if match:
                day_nums.append(int(match.group(1)))
        if day_nums:
            current_day = max(day_nums)
        else:
            import datetime

            current_day = datetime.date.today().day

    daily_total_budget = max(0, monthly_budget - rent_total)
    safe_daily_baseline = daily_total_budget / days_in_month
    month_net_spent_so_far = sum(v for _, v in daily_net)
    remaining_days = max(1, days_in_month - current_day + 1)
    dynamic_safe_budget = max(
        0, (daily_total_budget - month_net_spent_so_far) / remaining_days
    )

    # 堆叠透视表
    pivot_map = defaultdict(lambda: defaultdict(float))
    for r in recs:
        if r["交易类型"] == "EX" and not is_rent(r) and not is_accident(r):
            pivot_map[r["日期"]][r["分类"]] += r["实际金额"]
    categories = sorted({cat for day_map in pivot_map.values() for cat in day_map})
    pivot_dates = [d for d, _ in daily_net]
    pivot_values = [
        [pivot_map[d].get(cat, 0.0) for cat in categories] for d in pivot_dates
    ]

    # 双环图
    fixed_pattern = r"房租|分期|月卡|电费|提现手续|宽带|话费"

    def mark_rigidity(r):
        text = f"{r['分类']}_{r['品名']}"
        return (
            "刚性固定支出"
            if re.search(fixed_pattern, text, re.IGNORECASE)
            else "弹性自由支配"
        )

    inner_map = defaultdict(float)
    outer_map = defaultdict(float)
    for r in regular_ex:
        attr = mark_rigidity(r)
        inner_map[attr] += r["实际金额"]
        outer_map[(attr, r["分类"])] += r["实际金额"]

    inner_labels = sorted(inner_map)
    inner_values = [inner_map[k] for k in inner_labels]
    outer_pairs = []
    outer_values = []
    for attr in inner_labels:
        attr_cats = sorted({cat for (a, cat) in outer_map if a == attr})
        for cat in attr_cats:
            outer_pairs.append((attr, cat))
            outer_values.append(outer_map[(attr, cat)])

    all_categories = sorted({r["分类"] for r in regular_ex})

    data_bundle = {
        "overview": {
            "monthly_total_expense": monthly_total_expense,
            "monthly_net_growth": monthly_net_growth,
            "pending_recovery": pending_recovery,
            "raw_income": in_val,
            "raw_expense": ex_val,
            "raw_advance": ar_val,
            "raw_recovered": ap_val
        },
        "hb": {
            "spent": round(hb_spent, 2),
            "repaid": round(hb_repaid, 2),
            "need_pay": round(hb_need_pay, 2),
        },
        "accident": {
            "income": round(accident_in, 2),
            "expense": round(accident_out, 2),
            "net": round(accident_in - accident_out, 2),
        },
        "latte": latte_stats,
        "top_merchants": top_merchants,
        "budget": {
            "monthly_budget": monthly_budget,
            "rent_total": round(rent_total, 2),
            "daily_total_budget": round(daily_total_budget, 2),
            "safe_daily_baseline": round(safe_daily_baseline, 2),
            "dynamic_safe_budget": round(dynamic_safe_budget, 2),
            "current_day": current_day,
        },
        "daily_trend": {
            "dates": [d for d, _ in daily_net],
            "net_expenses": [
                round(v, 2) for _, v in daily_net
            ],
            "categories": categories,
            "pivot_data": {
                cat: [round(row[ci], 2) for row in pivot_values]
                for ci, cat in enumerate(categories)
            },
        },
        "donut_chart": {
            "inner": [
                {"name": name, "value": round(float(val), 2)}
                for name, val in zip(inner_labels, inner_values)
            ],
            "outer": [
                {"name": cat, "value": round(float(val), 2), "parent": attr}
                for (attr, cat), val in zip(outer_pairs, outer_values)
            ],
        },
        "_raw": {
            "pivot_amount": {
                "dates": pivot_dates,
                "categories": categories,
                "values": pivot_values,
            },
            "daily_net": {
                "dates": [d for d, _ in daily_net],
                "values": [v for _, v in daily_net],
            },
            "inner_data": {"labels": inner_labels, "values": inner_values},
            "outer_data": {"labels": outer_pairs, "values": outer_values},
            "all_categories": all_categories,
        },
    }
    return data_bundle


def print_analysis_report(data):
    hb = data["hb"]
    acc = data["accident"]
    latte = data["latte"]
    b = data["budget"]

    print("=" * 65)
    print(
        f"【花呗账务】本期累计HB结账: ¥{hb['spent']:.2f} | 已还款: ¥{hb['repaid']:.2f} | 下月待还: ¥{hb['need_pay']:.2f}"
    )
    if acc["income"] > 0 or acc["expense"] > 0:
        print("-" * 65)
        print(
            f"【意外损益】赔偿收入: ¥{acc['income']:.2f} | 赔付他人支出: ¥{acc['expense']:.2f} | 净差额: ¥{acc['net']:+.2f}"
        )
    print("-" * 65)
    print(
        f"【拿铁因子总计（饮食*）】共消费 {latte['count']} 笔（折合 {latte['items']} 件商品）, 累计支出: ¥{latte['cost']:.2f}"
    )
    print(
        f"  ├─ 饮品/糖分: 购买 {latte['drinks_count']} 笔（折合 {latte['drinks_items']} 罐/杯）, 支出: ¥{latte['drinks_cost']:.2f}"
    )
    print(
        f"  └─ 零食小吃: 购买 {latte['snacks_count']} 笔（折合 {latte['snacks_items']} 份/包）, 支出: ¥{latte['snacks_cost']:.2f}"
    )
    print("\n【商户复购榜 Top 5】")
    sep_line = "-" * 46
    print(sep_line)
    print(
        f"{pad_chinese('商户名称', 14)} {'消费次数':>8} {'累计金额':>10} {'购买件数':>8}"
    )
    print(sep_line)
    for m in data["top_merchants"]:
        print(
            f"{pad_chinese(m['name'], 14)} {m['count']:>8d} {m['amount']:>10.2f} {m['items']:>8d}"
        )
    print(sep_line)
    print("-" * 65)
    print(
        f"【预算水位】月总预算: ¥{b['monthly_budget']} | 扣除房租后可用: ¥{b['daily_total_budget']:.2f}"
    )
    print(
        f"【预算水位】基准安全日均: ¥{b['safe_daily_baseline']:.2f} | 今日({b['current_day']}日)起可用日均: ¥{b['dynamic_safe_budget']:.2f}/天"
    )
    print("=" * 65)


def render_matplotlib_charts(data):
    raw = data["_raw"]
    pivot = raw["pivot_amount"]
    pivot_dates = pivot["dates"]
    pivot_categories = pivot["categories"]
    pivot_values = pivot["values"]
    daily_dates = raw["daily_net"]["dates"]
    daily_values = raw["daily_net"]["values"]
    inner_labels = raw["inner_data"]["labels"]
    inner_values = raw["inner_data"]["values"]
    outer_pairs = raw["outer_data"]["labels"]
    outer_values = raw["outer_data"]["values"]
    all_categories = raw["all_categories"]
    safe_daily_baseline = data["budget"]["safe_daily_baseline"]
    dynamic_safe_budget = data["budget"]["dynamic_safe_budget"]

    base_palette = plt.get_cmap("tab20")(
        np.linspace(0, 1, max(20, len(all_categories)))
    )
    category_color_map = {
        cat: base_palette[i] for i, cat in enumerate(all_categories)
    }

    fig, axes = plt.subplots(1, 2, figsize=(21, 7.5))
    ax = axes[0]
    left_bar_colors = [category_color_map[col] for col in pivot_categories]
    x_positions = np.arange(len(pivot_dates))
    bottom = np.zeros(len(pivot_dates))
    for ci, cat in enumerate(pivot_categories):
        vals = [row[ci] for row in pivot_values]
        ax.bar(
            x_positions,
            vals,
            bottom=bottom,
            color=left_bar_colors[ci],
            width=0.6,
            alpha=0.82,
            edgecolor="white",
            linewidth=0.8,
            label=cat,
        )
        bottom = bottom + np.asarray(vals, dtype=float)
    (line_net,) = ax.plot(
        x_positions,
        daily_values,
        color="#c0392b",
        linewidth=2.5,
        marker="o",
        markersize=6,
        zorder=5,
    )
    line_safe = ax.axhline(
        safe_daily_baseline,
        color="#27ae60",
        linestyle="--",
        linewidth=1.8,
        zorder=4,
    )
    for i, val in enumerate(daily_values):
        ax.annotate(
            f"¥{val:.1f}",
            (x_positions[i], val),
            textcoords="offset points",
            xytext=(0, 7),
            ha="center",
            fontsize=8.5,
            fontweight="bold",
            color="#962d00",
            bbox=dict(
                boxstyle="round,pad=0.2",
                facecolor="white",
                edgecolor="none",
                alpha=0.85,
            ),
        )
    ax.set_ylabel("金额 (元)", fontsize=11, fontweight="bold")
    ax.set_xlabel("日期", fontsize=11)
    ax.tick_params(axis="x", rotation=45)
    ax.grid(axis="y", linestyle=":", alpha=0.5)
    y_ceiling = max(
        (max(daily_values) if daily_values else 0.0), safe_daily_baseline
    ) * 1.22
    ax.set_ylim(0, y_ceiling)
    ax.set_title(
        f"逐日日常支出分类构成与净支出走势\n[今日起建议日均额度: ¥{dynamic_safe_budget:.1f}/天]",
        fontsize=12,
        fontweight="bold",
        pad=15,
    )
    bar_handles, bar_labels = ax.get_legend_handles_labels()
    cat_len = len(pivot_categories)
    ax.legend(
        handles=bar_handles[:cat_len] + [line_net, line_safe],
        labels=bar_labels[:cat_len]
        + ["每日净支出走势", f"建议日均线 (¥{safe_daily_baseline:.1f})"],
        loc="upper left",
        bbox_to_anchor=(1.02, 1.0),
        fontsize=9,
        frameon=False,
        title="分类与指标",
    )

    axes[1].pie(
        inner_values,
        radius=0.7,
        labels=inner_labels,
        labeldistance=0.35,
        autopct="%1.1f%%",
        pctdistance=0.75,
        colors=["#3498db", "#e67e22"],
        wedgeprops=dict(width=0.35, edgecolor="white", linewidth=1.5),
        textprops=dict(fontweight="bold", fontsize=10),
    )
    outer_labels = [pair[1] for pair in outer_pairs]
    right_outer_colors = [category_color_map[cat] for cat in outer_labels]
    axes[1].pie(
        outer_values,
        radius=1.05,
        labels=outer_labels,
        labeldistance=1.15,
        rotatelabels=True,
        colors=right_outer_colors,
        wedgeprops=dict(width=0.35, edgecolor="white", linewidth=1),
        textprops=dict(fontsize=8.5),
    )
    axes[1].set_title(
        "常规刚性 vs 弹性支出构成双环图\n(饮食与饮食*独立分类呈现)",
        fontsize=12,
        fontweight="bold",
        pad=20,
    )
    plt.tight_layout()
    plt.subplots_adjust(left=0.06, right=0.92, top=0.88, bottom=0.15)
    plt.show()


def export_to_json(data, output_json_path="expense_data.json"):
    chart_payload = {k: v for k, v in data.items() if k != "_raw"}
    # 增加万能兜底转换函数
    def default_serializer(obj):
        if isinstance(obj, (np.integer, np.int64, np.int32)):
            return int(obj)
        if isinstance(obj, (np.floating, np.float64, np.float32)):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return str(obj)
    with open(output_json_path, "w", encoding="utf-8") as f:
        json.dump(chart_payload, f, ensure_ascii=False, indent=2, default=default_serializer)
    print(f"[OK] 数据接口已更新: {output_json_path}")


# 暴露给 server.py 调用的统一入口
def run_analysis_from_db(
    db_path="bills.db",
    monthly_budget=2800,
    json_path=None,
    current_day=None,
    year=None,
    month=None,
):
    """从 SQLite 数据库中读取指定年/月的数据并刷新 JSON；year/month 均缺省时分析全量条目"""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    sql = "SELECT * FROM expenses"
    conditions = []
    params = []
    if year is not None:
        if month is not None:
            conditions.append("日期 LIKE ?")
            params.append(f"{int(year)}-{int(month):02d}%")
        else:
            conditions.append("日期 LIKE ?")
            params.append(f"{int(year)}-")
    elif month is not None:
        conditions.append("substr(日期, 6, 2) = ?")
        params.append(f"{int(month):02d}")
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    cursor = conn.cursor()
    cursor.execute(sql, params)
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()

    if not rows:
        return None

    data = process_expense_data(
        rows=rows,
        monthly_budget=monthly_budget,
        current_day=current_day,
        year=year,
        month=month,
    )
    # 词云跟随当前选取的核算月份统计（未指定年月时保持全量统计）
    data["wordcloud"] = generate_wordcloud_data(db_path=db_path, year=year, month=month)
    if json_path:
        export_to_json(data, json_path)
    return data


def analyze_expenses(
    db_path="bills.db",
    year=None,
    month=None,
    monthly_budget=2800,
    current_day=None,
    mode="all",
    json_path="expense_data.json",
):
    data = run_analysis_from_db(
        db_path=db_path,
        monthly_budget=monthly_budget,
        json_path=None,
        current_day=current_day,
        year=year,
        month=month,
    )
    if data is None:
        print("[Warning] bills.db 中无匹配条目（或数据为空），无法分析。")
        return None
    if mode in ["all", "console"]:
        print_analysis_report(data)
    if mode in ["all", "web"]:
        export_to_json(data, output_json_path=json_path)
    if mode in ["all", "matplotlib"]:
        render_matplotlib_charts(data)
    return data


if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    db_file = os.path.join(current_dir, "bills.db")
    target_json_path = os.path.join(current_dir, "static", "expense_data.json")

    # 单独运行 analyze.py 依然完全可用；可选传入年月参数，如 python analyze.py 2026-09
    target_year = target_month = None
    if len(sys.argv) > 1:
        target_year, target_month = parse_year_month_arg(sys.argv[1])
        if target_year is not None and target_month is not None:
            # 指定月份时按月份隔离缓存文件，避免与其它月份互相覆盖
            target_json_path = build_month_json_path(
                target_json_path, target_year, target_month
            )

    analyze_expenses(
        db_path=db_file,
        year=target_year,
        month=target_month,
        monthly_budget=2800,
        mode="all",
        json_path=target_json_path,
    )
