# analyze.py
import calendar
import json
import os
import yaml
import re
import sqlite3
import unicodedata
import jieba
from collections import defaultdict
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# 设置 Matplotlib 中文字体支持
plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "Arial Unicode MS"]
plt.rcParams["axes.unicode_minus"] = False

WORDCLOUD_STOP_WORDS = {
    "微信", "一份", "支付", "支出", "账单", "退款", "购买", "消费", 
    "商品", "代金券", "优惠券", "红包", "其他", "备注", "我们", "这个"
}


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

# =========================================================================
# 词云清洗规则与统计引擎
# =========================================================================
# 过滤助词、交易通道、无实际商品特征的杂词
WORDCLOUD_STOP_WORDS = {
    "微信", "支付宝", "支付", "支出", "账单", "退款", "购买", "消费", 
    "商品", "代金券", "优惠券", "红包", "其他", "备注", "我们", "这个"
}

def clean_product_name(text: str) -> str:
    """清洗商品名中的规格、容量、包装数量（如 100ml, 300ml, .5L, x24 等）"""
    if not text:
        return ""
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

def generate_wordcloud_data(db_path: str = "bills.db", df_source: pd.DataFrame = None, top_n: int = 80) -> dict:
    """提取所有月份的实际支出(EX)，清洗后分词并生成频次与金额双加权数据"""
    rows = []
    if df_source is not None:
        # 兼容直接传入 DataFrame（如离线运行 Excel）
        ex_df = df_source[df_source["交易类型"] == "EX"]
        rows = ex_df[["品名", "实际金额"]].dropna().values.tolist()
    elif os.path.exists(db_path):
        # 默认从 bills.db 全量读取跨月份历史
        conn = sqlite3.connect(db_path)
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT 品名, 实际金额 FROM expenses WHERE 交易类型 = 'EX' AND 品名 IS NOT NULL AND 品名 != ''")
            rows = cursor.fetchall()
        finally:
            conn.close()

    # 注册自定义专有名词
    cfg = load_system_config()
    custom_words = cfg.get("custom_words", [])
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

        # ================= 核心过滤逻辑 =================
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
# 1. 核心计算层（支持传入 file_path 或 外部 df）
# =========================================================================
def process_expense_data(
    file_path=None, df=None, monthly_budget=2300, current_day=None
):
    """
    清洗并计算账单数据。支持通过 file_path (Excel) 或 直接传入 df (从 SQLite 查询)。
    """
    if df is None:
        if file_path is None:
            raise ValueError("必须提供 file_path 或 df 之一")
        df = pd.read_excel(file_path, dtype={"日期": str, "时间": str})
    else:
        df = df.copy()

    df.columns = df.columns.str.strip()
    text_cols = ["交易类型", "分类", "品名", "支付账户", "目标账户", "结算状态"]
    for col in text_cols:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()

    df["实际金额"] = pd.to_numeric(df["实际金额"], errors="coerce").fillna(0)
    df["件数"] = df["品名"].apply(extract_item_quantity)

    # 识别“意外”非日常消费事件
    accident_mask = df["交易类型"].str.contains("意外") | df["分类"].str.contains(
        "赔偿|意外"
    )

    # 识别房租
    rent_condition = (
        df["分类"].str.contains("房租")
        | df["品名"].str.contains("房租")
        | df["品名"].str.contains("押金")
    )
    rent_total = float(
        df[(df["交易类型"] == "EX") & rent_condition]["实际金额"].sum()
    )

    # (0) 总览数据
        # 1. 按交易类型汇总金额 (严格基于用户定义: AR=垫付, AP=收回, EX=支出, IN=收入)
    type_sums = df.groupby("交易类型")["实际金额"].sum().to_dict()
    ex_val = float(type_sums.get("EX", 0.0))  # 支出
    in_val = float(type_sums.get("IN", 0.0))  # 收入
    ar_val = float(type_sums.get("AR", 0.0))  # 垫付
    ap_val = float(type_sums.get("AP", 0.0))  # 收回
        # 2. 按照公式计算三大核心财务指标
    monthly_total_expense = round(ex_val + ar_val - ap_val, 2)  # SUM(EX + AR - AP)
    monthly_net_growth = round(in_val - ex_val - ar_val + ap_val, 2)  # SUM(IN - EX - AR + AP)
    pending_recovery = round(ar_val - ap_val, 2)  # SUM(AR - AP)

    # (1) 花呗
    hb_spent = float(df[df["支付账户"] == "HB"]["实际金额"].sum())
    hb_repaid = float(
        df[(df["交易类型"] == "TR") & (df["品名"].str.contains("花呗还款"))][
            "实际金额"
        ].sum()
    )
    hb_need_pay = hb_spent - hb_repaid

    # (2) 意外损益
    accident_df = df[accident_mask].copy()
    accident_in = 0.0
    accident_out = 0.0
    if not accident_df.empty:
        accident_in = float(
            accident_df[accident_df["交易类型"] == "IN"]["实际金额"].sum()
        )
        accident_out = float(
            accident_df[accident_df["交易类型"] == "EX"]["实际金额"].sum()
        )

    # (3) 拿铁因子
    regular_ex = df[(df["交易类型"] == "EX") & (~accident_mask)].copy()
    latte_df = regular_ex[regular_ex["分类"] == "饮食*"].copy()

    drink_pattern = r"奶茶|茶|咖啡|可乐|雪碧|水|冰城|拿铁|饮|乳|蜜雪|库迪"
    drinks = latte_df[
        latte_df["品名"].str.contains(drink_pattern, regex=True, case=False)
    ]
    snacks = latte_df[
        ~latte_df["品名"].str.contains(drink_pattern, regex=True, case=False)
    ]

    latte_stats = {
        "count": len(latte_df),
        "items": int(latte_df["件数"].fillna(0).sum()),
        "cost": float(latte_df["实际金额"].sum()),
        "drinks_count": len(drinks),
        "drinks_items": int(drinks["件数"].fillna(0).sum()),
        "drinks_cost": float(drinks["实际金额"].sum()),
        "snacks_count": len(snacks),
        "snacks_items": int(snacks["件数"].fillna(0).sum()),
        "snacks_cost": float(snacks["实际金额"].sum()),
    }

    # (4) 商户复购榜
    regular_ex["结账单号"] = regular_ex["日期"] + "_" + regular_ex["时间"]
    # 读取配置文件中的剔除列表，若读取失败则使用默认值兜底
    config = load_system_config()
    default_non_merchants = ["HB", "VX", "AL", "BK", "TC", "腾讯"]
    non_merchants = config.get("non_merchants", default_non_merchants)
    # 确保比较时做去空白处理
    non_merchants = {str(item).strip() for item in non_merchants}
    merchant_filter = ~regular_ex["目标账户"].isin(non_merchants)

    merchant_stats_df = (
        regular_ex[merchant_filter]
        .groupby("目标账户")
        .agg(
            消费次数=("结账单号", "nunique"),
            累计金额=("实际金额", "sum"),
            购买件数=("件数", "sum"),
        )
        .sort_values(by=["消费次数", "累计金额"], ascending=False)
        .head(5)
    )

    top_merchants = [
        {
            "name": name,
            "count": int(row["消费次数"]),
            "amount": float(row["累计金额"]),
            "items": int(row["购买件数"]),
        }
        for name, row in merchant_stats_df.iterrows()
    ]

    # (5) 动态预算
    pure_daily_ex = df[
        (df["交易类型"] == "EX") & (~rent_condition) & (~accident_mask)
    ]
    pure_daily_ex_sum = pure_daily_ex.groupby("日期")["实际金额"].sum()

    regular_ap = df[
        (df["交易类型"] == "AP") & (~rent_condition) & (~accident_mask)
    ]
    regular_ap_sum = regular_ap.groupby("日期")["实际金额"].sum()

    daily_net_df = (
        pure_daily_ex_sum.subtract(regular_ap_sum, fill_value=0)
        .reset_index()
        .rename(columns={"实际金额": "净支出"})
        .sort_values("日期")
        .reset_index(drop=True)
    )

    # 提取月份
    month_str = "09"
    if len(df) > 0 and pd.notna(df["日期"].iloc[0]):
        raw_str = str(df["日期"].iloc[0]).strip()
        # 针对带分隔符的格式（如 2026-09-01, 2026-9-1, 26-09-01, 2026/9/1 等）
        # 匹配 年-月-日 中的 "月"
        sep_match = re.search(r"^\d{2,4}[-/.]([0-1]?\d)[-/.]([0-3]?\d)", raw_str)
        # 针对纯数字紧凑格式（如 20260901, 260901, 0901）
        if sep_match:
            m = int(sep_match.group(1))
            month_str = f"{m:02d}"
        elif raw_str.isdigit():
            if len(raw_str) == 8:      # 20260901 -> 取第 5-6 位
                month_str = raw_str[4:6]
            elif len(raw_str) == 6:    # 260901   -> 取第 3-4 位
                month_str = raw_str[2:4]
            elif len(raw_str) == 4:    # 0901     -> 取第 1-2 位
                month_str = raw_str[:2]

    days_in_month = calendar.monthrange(2026, int(month_str))[1]

    if current_day is None:
        day_series = (
            df["日期"].astype(str).str.extract(r"(\d{1,2})$")[0].dropna()
        )
        if not day_series.empty:
            current_day = int(day_series.astype(int).max())
        else:
            import datetime

            current_day = datetime.date.today().day

    daily_total_budget = max(0, monthly_budget - rent_total)
    safe_daily_baseline = daily_total_budget / days_in_month
    month_net_spent_so_far = float(daily_net_df["净支出"].sum())
    remaining_days = max(1, days_in_month - current_day + 1)
    dynamic_safe_budget = max(
        0, (daily_total_budget - month_net_spent_so_far) / remaining_days
    )

    # 堆叠透视表
    pivot_amount = pure_daily_ex.pivot_table(
        index="日期", columns="分类", values="实际金额", aggfunc="sum", fill_value=0
    )
    pivot_amount = pivot_amount.reindex(daily_net_df["日期"]).fillna(0)

    # 双环图
    fixed_pattern = r"房租|分期|月卡|电费|提现手续|宽带|话费"

    def mark_rigidity(row):
        text = f"{row['分类']}_{row['品名']}"
        return (
            "刚性固定支出"
            if re.search(fixed_pattern, text, re.IGNORECASE)
            else "弹性自由支配"
        )

    regular_ex["支出属性"] = regular_ex.apply(mark_rigidity, axis=1)
    inner_series = regular_ex.groupby("支出属性")["实际金额"].sum()
    outer_series = (
        regular_ex.groupby(["支出属性", "分类"])["实际金额"]
        .sum()
        .loc[inner_series.index]
    )

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
            "dates": daily_net_df["日期"].tolist(),
            "net_expenses": [
                round(x, 2) for x in daily_net_df["净支出"].tolist()
            ],
            "categories": pivot_amount.columns.tolist(),
            "pivot_data": {
                col: [round(v, 2) for v in pivot_amount[col].tolist()]
                for col in pivot_amount.columns
            },
        },
        "donut_chart": {
            "inner": [
                {"name": name, "value": round(float(val), 2)}
                for name, val in inner_series.items()
            ],
            "outer": [
                {"name": cat, "value": round(float(val), 2), "parent": attr}
                for (attr, cat), val in outer_series.items()
            ],
        },
        "_raw": {
            "pivot_amount": pivot_amount,
            "daily_net": daily_net_df,
            "inner_data": inner_series,
            "outer_data": outer_series,
            "all_categories": sorted(regular_ex["分类"].unique()),
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
    pivot_amount = raw["pivot_amount"]
    daily_net = raw["daily_net"]
    inner_data = raw["inner_data"]
    outer_data = raw["outer_data"]
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
    left_bar_colors = [category_color_map[col] for col in pivot_amount.columns]
    pivot_amount.plot(
        kind="bar",
        stacked=True,
        ax=ax,
        color=left_bar_colors,
        width=0.6,
        alpha=0.82,
        edgecolor="white",
        linewidth=0.8,
    )
    x_positions = np.arange(len(daily_net))
    (line_net,) = ax.plot(
        x_positions,
        daily_net["净支出"],
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
    for i, val in enumerate(daily_net["净支出"]):
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
    ax.set_ylim(0, max(daily_net["净支出"].max(), safe_daily_baseline) * 1.22)
    ax.set_title(
        f"逐日日常支出分类构成与净支出走势\n[今日起建议日均额度: ¥{dynamic_safe_budget:.1f}/天]",
        fontsize=12,
        fontweight="bold",
        pad=15,
    )
    bar_handles, bar_labels = ax.get_legend_handles_labels()
    cat_len = len(pivot_amount.columns)
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
        inner_data,
        radius=0.7,
        labels=inner_data.index,
        labeldistance=0.35,
        autopct="%1.1f%%",
        pctdistance=0.75,
        colors=["#3498db", "#e67e22"],
        wedgeprops=dict(width=0.35, edgecolor="white", linewidth=1.5),
        textprops=dict(fontweight="bold", fontsize=10),
    )
    outer_labels = [idx[1] for idx in outer_data.index]
    right_outer_colors = [category_color_map[cat] for cat in outer_labels]
    axes[1].pie(
        outer_data,
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
        if isinstance(obj, (pd.DataFrame, pd.Series)):
            return obj.to_dict()
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
    year_month=None,
):
    """从 SQLite 数据库中读取指定月份的数据并刷新 JSON"""
    conn = sqlite3.connect(db_path)
    sql = "SELECT * FROM expenses"
    if year_month:
        sql += f" WHERE 日期 LIKE '{year_month}%'"
    df = pd.read_sql_query(sql, conn)
    conn.close()

    if df.empty:
        return None

    data = process_expense_data(
        df=df, monthly_budget=monthly_budget, current_day=current_day
    )
    data["wordcloud"] = generate_wordcloud_data(df_source=df)
    if json_path:
        export_to_json(data, json_path)
    return data


def analyze_expenses(
    file_path=None,
    df=None,
    monthly_budget=2800,
    current_day=None,
    mode="all",
    json_path="expense_data.json",
):
    data = process_expense_data(
        file_path=file_path,
        df=df,
        monthly_budget=monthly_budget,
        current_day=current_day,
    )
    if mode in ["all", "console"]:
        print_analysis_report(data)
    if mode in ["all", "web"]:
        export_to_json(data, output_json_path=json_path)
    if mode in ["all", "matplotlib"]:
        render_matplotlib_charts(data)
    return data


if __name__ == "__main__":
    excel_file = "D:\\files\\账单\\2609.xlsx"
    current_dir = os.path.dirname(os.path.abspath(__file__))
    target_json_path = os.path.join(current_dir, "static", "expense_data.json")

    # 单独运行 analyze.py 依然完全可用
    analyze_expenses(
        file_path=excel_file,
        monthly_budget=2800,
        mode="all",
        json_path=target_json_path,
    )