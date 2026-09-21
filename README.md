# BillAnaly - 智能个人财务分析与记账系统

[![Python Version](https://img.shields.io/badge/Python-3.12.6-blue.svg)](https://www.python.org/downloads/release/python-3126/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg)](https://fastapi.tiangolo.com)
[![SQLite](https://img.shields.io/badge/Database-SQLite3-003B57.svg)](https://www.sqlite.org/)
[![AI Model](https://img.shields.io/badge/LLM-DeepSeek--Flash-4D6BFE.svg)](https://www.deepseek.com/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

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
- **丰富的可视化图表**：集成 ECharts，直观展示消费分类占比环形图、每日支出趋势图以及剔除通道账户后的真实商户复购排行。

### 🤖 DeepSeek-Flash 驱动的 AI 智能顾问
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
git clone https://github.com/komuro-kaede/billAnaly.git
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
在项目根目录检查并编辑 `config.yaml`（若无则根据模板新建）：
```yaml
deepseek:
  api_key: "sk-your-deepseek-api-key" # 填入你的 DeepSeek API Key
  base_url: "https://api.deepseek.com"
  model: "deepseek-flash"

# 默认月度总预算基准 (元)
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

### 第四步：启动服务
```bash
python server.py
# 或使用 uvicorn 直接启动：
# uvicorn server.py:app --host 127.0.0.1 --port 8000 --reload
```

启动成功后，在浏览器中访问：
- 📈 **财务分析大屏 (Dashboard)**: `http://127.0.0.1:8000/static/dashboard.html`
- 📑 **流水数据管理后台 (Manager)**: `http://127.0.0.1:8000/static/manager.html`

---

## 4. 目录结构 (Project Structure)

```text
billAnaly/
├── config.yaml               # 全局配置文件 (DeepSeek API Key、预算基线、剔除商户名单)
├── server.py                 # FastAPI 核心入口与静态文件路由托管
├── analyze.py                # 核心财务核算引擎 (聚合统计、垫付冲抵、商户排行榜)
├── ai_assistant.py           # AI 模块 (财务体检、全月深度精读、账单流水问答)
├── db_manager.py             # 数据库 CRUD 路由与 Excel 导出接口
├── bills.db                  # SQLite 核心账单数据库
├── static/                   # 前端静态资源
│   ├── dashboard.html        # 财务分析大屏页面
│   ├── dashboard.js          # 大屏数据拉取、ECharts 图表渲染、AI 交互与预算联动
│   ├── manager.html          # 流水数据管理与查询后台页面
│   ├── manager.js            # 流水多维筛选、行内实时编辑、另存为导出逻辑
│   ├── style.css             # 响应式全局界面样式与卡片网格布局
│   └── expense_data.json     # 中间态账单分析聚合缓存文件
└── README.md                 # 项目使用与说明文档
```

---

## 5. 配置说明 (Configuration)

### 交易类型代号定义 (Transaction Types)
系统中严格采用两字英文代号标识交易性质，并在传递给 AI 及页面展示时自动映射转义：
- `EX` (Expense)：**日常支出**（计入消费与总预算统计）。
- `IN` (Income)：**收入**（计入资产正向增长）。
- `AR` (Advance Receivable)：**垫付 / 借出**（帮他人代付，属于应收债权）。
- `AP` (Advance Paid / Recovered)：**垫付收回 / 还入**（收回代付款，冲抵支出）。
- `TR` (Transfer)：**内部转账 / 信用卡及花呗还款**（资金在自有账户间流动，不影响净资产）。

### 账户代号定义 (Accounts)
- `VX`：微信支付
- `AL`：支付宝
- `BK`：银行卡
- `HB`：蚂蚁花呗
- `TC`：交通卡 / 公交卡
- *注：商户名或外部联系人（如“猛火炒饭”、“张三”）直接录入原文本即可，系统会自动识别并保留。*

---

## 6. 使用说明与 API 规范 (Usage & API Reference)

### 1. 常用后端 API 概览

| 请求方法 | 端点 URL | 说明 |
| :--- | :--- | :--- |
| `GET` | `/api/months` | 获取数据库中已有记录的所有有效核算月份列表 |
| `POST` | `/api/refresh_analysis` | 接收 `year_month` 与 `monthly_budget`，触发重新核算并更新数据缓存 |
| `GET` | `/api/system_config` | 获取 `config.yaml` 中配置的默认预算与基础配置 |
| `GET` | `/api/db/expenses` | 多条件检索流水明细（支持排序、区间与分页） |
| `GET` | `/api/db/export_excel` | 接收筛选条件，以二进制流形式导出 `.xlsx` Excel 文件 |
| `GET` | `/api/ai/diagnose` | 获取针对当前月份核心指标的 AI 体检评估 |
| `GET` | `/api/ai/deep_read` | 调取选定月份的逐笔全量流水，输出行为学审计深度报告 |
| `POST` | `/api/ai/chat` | 接收自然语言提问文本，检索近 200 条时序流水后由大模型作答 |

### 2. 前端快捷操作技巧
- **预算动态绑定**：在大屏右上角的“月度总预算”输入框中输入新的目标金额并按回车，页面指标会立即按新预算重新推算；在 AI 快捷提问中点击 `⚠️ 月底超支风险评估`，会自动捕获该输入框中的实时数字带入提问。
- **跨月对比**：在“核算账期”下拉框中选择不同历史月份，一键查看历史收支结余与环比走势。

---

## 7. 常见问题与排错 (FAQ & Troubleshooting)

### Q1: 点击 AI 诊断或精读时提示“生成超时或 Token 额度不足，未获取到完整正文”？
- **原因**：DeepSeek 的 Reasoner / Flash 系列架构默认可能开启思维链（Thinking Process）。当推理推导过程过长时，会挤占 `max_tokens` 配额，导致最终正文未生成即被截断。
- **解决办法**：在 `ai_assistant.py` 中向 API 请求传入显式禁用参数：
  ```python
  extra_body={"thinking": {"type": "disabled"}}
  ```
  同时将 `max_tokens` 提升至 `2048` 或更高，保证输出通畅。

### Q2: 为什么 DeepSeek 会把正餐快餐误判为零食“拿铁因子”？
- **原因**：大模型仅看到商户名字时可能产生常识偏差。
- **解决办法**：项目已在组织 Prompt 时注入了消费画像常识规则（如指出“猛火炒饭”属于健康低成本正餐、“闲鱼”多为购买快餐优惠券等省钱举动），AI 会在精读时自动识别并给予正向评价。

### Q3: 导出 Excel 时没有弹出选择文件夹的窗口，而是直接下载到了“下载”文件夹？
- **原因**：浏览器的安全策略要求，只有在用户主动触发的事件中且当前环境支持 `window.showSaveFilePicker` 时才会唤起系统另存为窗口。如果使用的是 Firefox、较旧版本浏览器或通过非安全上下文（部分非 localhost 的 HTTP 环境）访问，代码会自动平滑降级为浏览器默认下载。在 Chrome / Edge 上直接访问 `http://127.0.0.1:8000` 即可正常唤起。

### Q4: 修改了静态资源（如 `dashboard.js` 或 CSS）后刷新网页没有变化？
- **原因**：浏览器对静态 JS/CSS 资源具有强缓存机制。
- **解决办法**：在浏览器页面上按下 **`Ctrl + F5`**（macOS 上为 `Cmd + Shift + R`）强制刷新并清除本地缓存。

---

## 8. 贡献指南与开源协议 (Contributing & License)

### 参与贡献
欢迎提交 Issue 报告 Bug 或提出新需求；也欢迎直接发起 Pull Request：
1. Fork 本项目并创建分支 (`git checkout -b feature/AmazingFeature`)
2. 提交你的修改 (`git commit -m 'Add some AmazingFeature'`)
3. 推送分支 (`git push origin feature/AmazingFeature`)
4. 发起 Pull Request

### 开源协议
本项目采用 [MIT License](LICENSE) 授权许可。你可以自由地使用、修改和分发本项目代码。