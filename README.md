# BillAnaly - 智能个人财务分析与记账系统

[![Python Version](https://img.shields.io/badge/Python-3.12.6-blue.svg)](https://www.python.org/downloads/release/python-3126/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg)](https://fastapi.tiangolo.com)
[![SQLite](https://img.shields.io/badge/Database-SQLite3-003B57.svg)](https://www.sqlite.org/)
[![AI Model](https://img.shields.io/badge/LLM-DeepSeek--Flash-4D6BFE.svg)](https://www.deepseek.com/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![AIGC Assisted](https://img.shields.io/badge/AIGC-Powered%20by%20Gemini-8E75FF.svg)](#9-致谢与-aigc-声明-acknowledgments--aigc-statement)

BillAnaly 是一款面向个人与家庭的高效、自主可控的轻量级财务分析系统。项目以后端 **FastAPI + SQLite3** 为核心，结合原生极简的前端看板与管理后台，并深度接入 **DeepSeek-Flash** 大模型，实现开箱即用的自动化多维账目核算、垫付对冲平账、图表可视化，以及全流水行为学深度审计与自然语言智能问答。

---

## 目录

- [1. 核心特性 (Features)](#1-核心特性-features)
- [2. 技术栈与运行环境 (Tech Stack & Prerequisites)](#2-技术栈与运行环境-tech-stack--prerequisites)
- [3. 快速上手 (Getting Started)](#3-快速上手-getting-started)
- [4. 目录结构 (Project Structure)](#4-目录结构-project-structure)
- [5. 配置说明 (Configuration)](#5-配置说明-configuration)
- [6. 使用说明与 API 规范 (Usage & API Reference)](#6-使用说明与-api-规范-usage--api-reference)
- [7. 常见问题与排错 (FAQ & Troubleshooting)](#7-常见问题与排错-faq--troubleshooting)
- [8. 贡献指南与开源协议 (Contributing & License)](#8-贡献指南与开源协议-contributing--license)
- [9. 致谢与 AIGC 声明 (Acknowledgments & AIGC Statement)](#9-致谢与-aigc-声明-acknowledgments--aigc-statement)

---

## 1. 核心特性 (Features)

### 📊 严谨的财务核算与动态看板 (Dashboard)
- **多账期全局隔离与切换**：支持跨月份多账本存储在同一数据库中，顶部账期选择器自动读取所有有效月份，看板秒级联动。
- **自定义月度动态预算**：支持前端自由设定并持久化保存（`localStorage`）月度预算，实时测算动态日均可用配额与安全基线。
- **精准真实的七维财务概况**：
  - **月度总支出（真实净流出）**：$SUM(EX + AR - AP)$，精准对冲垫付借出与收回。
  - **月度资产净增长（净结余）**：$SUM(IN - EX - AR + AP)$，收支盈余状态自动呈现红/绿指示。
  - **待收回垫付资金**：$SUM(AR - AP)$，实时跟踪外部欠款与代付未平账余额。
  - 扣除固定成本后建议可用日均、花呗下月待还预留、拿铁因子（零食饮品）统计等。
- **丰富的可视化图表与时间聚焦**：
  - 集成 ECharts 分类环形图、商户复购榜以及**分类堆叠柱状图 + 净支出走势折线图**。
  - **时间范围聚焦模式 (dataZoom)**：图表底部配备可视化滑动条与调节手柄，可自由框选并缩放任意日期区间的收支波动；移动端（视口宽度低于阈值）自动强制激活聚焦手柄，保障窄屏触控浏览体验。

### 🤖 DeepSeek-Flash 驱动的 AI 智能顾问
- **配置中心化与热调优**：所有任务的 System Prompt、模板结构（`prompt_template`）、采样温度（`temperature`）、最大输出（`max_tokens`）以及全局消费画像（`user_habits`）统一在 `config.yaml` 中配置，修改即刻生效，无需重启服务。
- **⚡ 核心指标体检 (`/api/ai/diagnose`)**：基于当月预算水位、花呗账单及消费画像快速给出务实、犀利的三点财务健康诊断。
- **📖 全月流水深度精读 (`/api/ai/deep_read`)**：将当月全量流水（百条级记录）脱敏并紧凑化喂入大模型，耗费不到半分钱（Token 极低），全景扫描时间节律、情绪消费（夜间冲动花销）、小额隐形刺客（<15元高频支出）及高性价比省钱动作。
- **💬 账单流水智能问答 (`/api/ai/chat`)**：自然语言即时查询（如“本月吃炒饭花了多少钱？”、“我最近用花呗买了什么？”），内置账户代码语义翻译，无需人工写 SQL。
- **低延迟高吞吐优化**：深度调优 API 调用参数，禁用冗余思考链（Reasoning Chain），实现毫秒级快速响应，彻底告别 Token 截断。

### 🛠️ 全功能流水管理后台 (Manager GUI)
- **多维复合筛选**：支持按日期区间、多级分类（精确/包含匹配）、交易类型、收付款账户、商户、金额范围及关键字综合查询。
- **行内无感编辑 (Inline Edit)**：表格单元格单击即改，失焦即存，内置账户代号与名称智能清洗。
- **系统级另存为导出 Excel**：采用现代浏览器的 `File System Access API`（`showSaveFilePicker`），弹出操作系统原生文件保存弹窗，支持自定义文件夹路径与文件名；自动降级兼容传统浏览器。

---

## 2. 技术栈与运行环境 (Tech Stack & Prerequisites)

### 运行环境
- **Python**: `3.12.6`（推荐使用 Python 3.12.x 环境）
- **操作系统**: Windows 10/11, macOS, Linux
- **现代浏览器**: Chrome / Edge 86+（支持 File System Access API 原生另存为特性）

### 依赖项与核心库
- **Web 框架**: `FastAPI` + `Uvicorn`
- **数据处理与导出**: `SQLite3`, `Pandas`, `openpyxl`
- **配置解析**: `PyYAML`
- **大模型 SDK**: `openai`（适配 DeepSeek 开放平台接口）
- **前端库**: 原生 JavaScript (ES6+), HTML5, CSS3, `ECharts 5.x`, `marked.js`

---

## 3. 快速上手 (Getting Started)

### 第一步：克隆仓库与准备虚拟环境
```bash
git clone [https://github.com/komuro-kaede/billAnaly.git](https://github.com/komuro-kaede/billAnaly.git)
cd billAnaly

# 创建 Python 3.12.6 虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

```

### 第二步：安装项目依赖

```bash
pip install --upgrade pip
pip install -r requirements.txt

```

### 第三步：配置应用参数

在项目根目录检查并编辑 `config.yaml`（完整字段见[配置说明](https://www.google.com/search?q=%25235-%25E9%2585%258D%25E7%25BD%25AE%25E8%25AF%25B4%25E6%2598%258E-configuration&utm_source=gemini)）：

```yaml
deepseek:
  api_key: "sk-your-deepseek-api-key" # 填入你的 DeepSeek API Key
  base_url: "[https://api.deepseek.com](https://api.deepseek.com)"
  model: "deepseek-flash"

# 默认月度总预算基准 (元)
budget:
  monthly_budget: 2800.0

```

### 第四步：启动服务

```bash
python server.py
# 或使用 uvicorn 直接启动：
# uvicorn server.py:app --host 127.0.0.1 --port 8000 --reload

```

启动成功后，在浏览器中访问：

* 📈 **财务分析大屏 (Dashboard)**: `http://127.0.0.1:8000/static/dashboard.html`
* 📑 **流水数据管理后台 (Manager)**: `http://127.0.0.1:8000/static/manager.html`

---

## 4. 目录结构 (Project Structure)

```text
billAnaly/
├── config.yaml               # 全局配置文件 (DeepSeek Key、预算、剔除商户、AI 提示词中心)
├── server.py                 # FastAPI 核心入口与静态文件路由托管
├── analyze.py                # 核心财务核算引擎 (聚合统计、垫付冲抵、商户排行榜)
├── ai_assistant.py           # AI 模块 (动态热加载配置、财务体检、深度精读、账单问答)
├── db_manager.py             # 数据库 CRUD 路由与 Excel 导出接口
├── bills.db                  # SQLite 核心账单数据库
├── static/                   # 前端静态资源
│   ├── dashboard.html        # 财务分析大屏页面 (含 dataZoom 时间聚焦组件)
│   ├── dashboard.js          # 大屏数据拉取、ECharts 走势图与聚焦、AI 交互与预算联动
│   ├── manager.html          # 流水数据管理与查询后台页面
│   ├── manager.js            # 流水多维筛选、行内实时编辑、另存为导出逻辑
│   ├── style.css             # 响应式全局界面样式与卡片网格布局
│   └── expense_data.json     # 中间态账单分析聚合缓存文件
└── README.md                 # 项目使用与说明文档

```

---

## 5. 配置说明 (Configuration)

### 1. 基础环境与商户过滤 (`config.yaml`)

```yaml
deepseek:
  api_key: "sk-your-deepseek-api-key"
  base_url: "[https://api.deepseek.com](https://api.deepseek.com)"
  model: "deepseek-flash"

budget:
  monthly_budget: 2800.0

# 商户排行榜需剔除的内部账户/通道
non_merchants:
  - HB
  - VX
  - AL
  - BK
  - TC
  - 腾讯
  - 财付通
  - 内部转账

```

### 2. AI 任务与提示词配置中心 (`ai_tasks`)

系统支持通过 YAML 文件对提示词与生成参数进行热调配，开箱支持全局个人消费习惯注入：

```yaml
ai_tasks:
  # 1. 个人长期消费画像与常识库（所有任务均可共享，在此处统一维护）
  user_habits:
    - "「优特卖」主要是批量采购低价临期零食饮品，是拿铁因子的主要来源。"
    - "用户习惯饮用怡宝、哇哈哈等灌装纯净水，属于硬性饮水需求，不计入拿铁因子。"
    - "日常饮品如果单价低于 10 元属于克制解馋，但若一周超过 4 次需警惕频次依赖。"

  # 2. 核心指标体检 (/api/ai/diagnose)
  diagnose:
    max_tokens: 2048
    temperature: 0.6
    system_prompt: "你是一位敏锐、幽默且切中要害的日常财务顾问。请直接输出简明的中文诊断建议，言简意赅，不要输出草稿或推导过程。"
    prompt_template: |
      以下是用户本月的核心财务数据指标：
      {context_summary}

      【用户个人消费习惯特别说明】：
      {user_habits}

      请结合上述数据与特征，请分 3 点给出务实、犀利但不刻板的诊断（300字以内）：
      1. 预算水位预警（指出日均压缩现状与花呗预留）；
      2. 拿铁因子成瘾度分析（聚焦零食饮品）；
      3. 针对性的省钱建议。

  # 3. 全月流水深度精读 (/api/ai/deep_read)
  deep_read:
    max_tokens: 4096
    temperature: 0.3
    system_prompt: "你是一位客观敏锐的个人财务审计师，请直接输出结构严整、见解深刻的 Markdown 报告。"
    prompt_template: |
      以下是用户在 【{year_month}】 月份的【全部消费流水（共 {record_count} 笔）】：
      {records}

      【用户个人消费习惯特别说明】：
      {user_habits}

      【你的任务】：请通读每一笔消费，做一份全景式的「消费行为深度精读审计报告」。
      请包含以下维度（使用清晰的 Markdown 标题与要点排版，言辞犀利、具体，直接点名具体商品与金额）：
      1. **时间节律与情绪消费捕获**：通读每笔时间与日期，指出是否存在深夜冲动消费（如22点后）、周末放纵开销，或某些固定时段的无意识花销习惯。
      2. **微小流失洞察（隐形刺客）**：找出单笔金额很小（<15元）但出现极其高频、不知不觉吞噬预算的商品或行为特征。
      3. **聪明省钱点赞**：指出流水中体现出哪些极致性价比的省钱操作（如代金券、平价快餐、折扣临期囤货等），予以肯定。
      4. **异常脉冲账目排查**：单笔大额或不合常规节奏的支出复盘，分析其对整月预算的冲击。
      5. **下月精准靶向调整建议**：给出 2~3 条可立即执行、不严重降低生活质量的靶向减负动作。
      注意：转移、垫付、收回等非消费行为不计入消费分析，但请在报告中标注出来。

  # 4. 智能流水问答 (/api/ai/chat)
  chat:
    max_tokens: 2048
    temperature: 0.3
    system_prompt: "你是账单系统的专属数据管家，请直接根据提供的流水准确计算并回答用户问题，回答要简洁明了。"
    prompt_template: |
      以下是用户近期的真实消费明细流水（最多200条）：
      {records}

      【用户个人消费习惯特别说明】：
      {user_habits}

      用户提问：“{user_query}”

      请根据账单流水与个人消费习惯准确回答。直接计算并给出明确结论，条理清晰。

```

### 3. 交易类型与账户代号定义

* **交易类型**：
* `EX` (Expense)：日常支出（计入消费与总预算统计）。
* `IN` (Income)：收入（计入资产正向增长）。
* `AR` (Advance Receivable)：垫付 / 借出（帮他人代付，属于应收债权）。
* `AP` (Advance Paid)：垫付收回 / 还入（收回代付款，冲抵支出）。
* `TR` (Transfer)：内部转账 / 信用卡及花呗还款（不影响净资产）。


* **账户代码**：`VX` (微信)、`AL` (支付宝)、`BK` (银行卡)、`HB` (蚂蚁花呗)、`TC` (交通卡)。商户或人名直接录入中文原名即可。

---

## 6. 使用说明与 API 规范 (Usage & API Reference)

### 1. 常用后端 API 概览

| 请求方法 | 端点 URL | 说明 |
| --- | --- | --- |
| `GET` | `/api/months` | 获取数据库中已有记录的所有有效核算月份列表 |
| `POST` | `/api/refresh_analysis` | 接收 `year_month` 与 `monthly_budget`，触发重新核算并更新数据缓存 |
| `GET` | `/api/system_config` | 获取 `config.yaml` 中配置的默认预算与基础配置 |
| `GET` | `/api/db/expenses` | 多条件检索流水明细（支持排序、区间与分页） |
| `GET` | `/api/db/export_excel` | 接收筛选条件，以二进制流形式导出 `.xlsx` Excel 文件 |
| `GET` | `/api/ai/diagnose` | 读取 YAML 模板并调优，生成当前月份核心指标体检评估 |
| `GET` | `/api/ai/deep_read` | 调取选定月份的逐笔全量流水，输出行为学审计深度报告 |
| `POST` | `/api/ai/chat` | 接收自然语言提问文本，检索近 200 条时序流水后由大模型作答 |

### 2. 前端快捷操作技巧

* **日期范围聚焦 (dataZoom)**：在仪表盘左侧的“每日支出趋势与分类堆叠”图表中，可直接拖动底部的缩放手柄，快速排查特定周期（如小长假、某一周冲动消费期）的花销分布；在窄屏移动端设备上该组件会自动勾选启动。
* **预算动态绑定**：在大屏右上角的“月度总预算”输入框中输入新金额按回车，页面指标会立即重算；在 AI 快捷提问中点击 `⚠️ 月底超支风险评估`，会自动捕获该输入框中的实时预算数字。
* **跨月对比**：在“核算账期”下拉框中选择历史月份，一键切换并查看历史收支结余与环比走势。

---

## 7. 常见问题与排错 (FAQ & Troubleshooting)

### Q1: 修改了 `config.yaml` 中的 AI 提示词或消费习惯后需要重启后端服务吗？

* **解答**：不需要。后端在每次发起 `/diagnose`、`/deep_read` 和 `/chat` 请求时，均会动态读取并解析最新的 `config.yaml`，即时应用新的 Prompt、`temperature` 与习惯库。

### Q2: 点击 AI 诊断或精读时提示“生成超时或 Token 额度不足，未获取到完整正文”？

* **原因**：DeepSeek 系列模型若开启思考链（Thinking Process），过长的推导会挤占 `max_tokens` 配额导致正文被截断。
* **解决办法**：系统默认已在接口内配置 `extra_body={"thinking": {"type": "disabled"}}` 极速直出，同时在 YAML 中可根据需要自由调大 `max_tokens`（如精读建议设为 `4096`）。

### Q3: 为什么 DeepSeek 会把正餐快餐误判为零食“拿铁因子”？

* **解答**：无需改动 Python 源码，只需在 `config.yaml` 的 `ai_tasks.user_habits` 中添加一条自然语言习惯声明（例如 `- "「某商户/品名」是正餐，不属于拿铁因子"`），模型即会自动理解并校正分类。

### Q4: 导出 Excel 时没有弹出选择文件夹的窗口，而是直接下载到了“下载”文件夹？

* **原因**：浏览器仅在支持且允许 `window.showSaveFilePicker` 时唤起原生保存弹窗。若环境不满足（如非 Chrome/Edge、安全策略限制或非 HTTPS/localhost 环境），系统会自动降级触发普通文件下载。

### Q5: 修改了静态资源（如 JS/CSS）后刷新网页没有变化？

* **解决办法**：浏览器对本地静态资源有强缓存，请使用 **`Ctrl + F5`**（macOS 上为 `Cmd + Shift + R`）强制刷新网页。

---

## 8. 贡献指南与开源协议 (Contributing & License)

### 参与贡献

欢迎提交 Issue 报告 Bug 或提出新需求；

### 开源协议

本项目采用 [MIT License](https://www.google.com/search?q=LICENSE&utm_source=gemini) 授权许可。你可以自由地使用、修改和分发本项目代码。

---

## 9. 致谢与 AIGC 声明 (Acknowledgments & AIGC Statement)

本项目由开发者主导架构设计，**全项目代码均在 Google Gemini 的协助与结对编程支持下完成**。涵盖系统架构选型、FastAPI 后端路由与 SQLite 核心财务核算、ECharts 动态可视化与响应式交互、以及 DeepSeek API 深度调用优化与配置解耦。
