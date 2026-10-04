# BillAnaly - 智能个人财务分析与记账系统

[![Python Version](https://img.shields.io/badge/Python-3.12.6-blue.svg)](https://www.python.org/downloads/release/python-3126/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg)](https://fastapi.tiangolo.com)
[![SQLite](https://img.shields.io/badge/Database-SQLite3-003B57.svg)](https://www.sqlite.org/)
[![AI Model](https://img.shields.io/badge/LLM-DeepSeek--Flash-4D6BFE.svg)](https://www.deepseek.com/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE.md)
[![AIGC Gemini](https://img.shields.io/badge/AIGC-Gemini%20Assisted-8E75FF.svg)](#9-致谢与-aigc-声明-acknowledgments--aigc-statement)
[![AIGC DeepSeek](https://img.shields.io/badge/AIGC-DeepSeek%20Assisted-4D6BFE.svg)](#9-致谢与-aigc-声明-acknowledgments--aigc-statement)

BillAnaly 是一款面向个人与家庭的高效、自主可控的轻量级财务分析系统。项目以后端 **FastAPI + SQLite3** 为核心，结合原生极简的前端看板与管理后台，并深度接入 **DeepSeek-Flash** 大模型，实现开箱即用的自动化多维账目核算、垫付对冲平账、图表可视化，以及全流水行为学深度审计与自然语言智能问答。

系统内置**多账号登录与权限体系**：全站页面与接口均需登录后访问，首次部署自带管理员账号 `admin` / `123456`，管理员可创建并分配普通账号，密码以「随机盐 + PBKDF2 哈希」加密存储，适合直接部署到云服务器供多人使用。

---

## 目录

- [1. 核心特性 (Features)](#1-核心特性-features)
- [2. 技术栈与运行环境 (Tech Stack & Prerequisites)](#2-技术栈与运行环境-tech-stack--prerequisites)
- [3. 快速上手 (Getting Started)](#3-快速上手-getting-started)
- [4. 目录结构 (Project Structure)](#4-目录结构-project-structure)
- [5. 配置说明 (Configuration)](#5-配置说明-configuration)
- [6. 使用说明与 API 规范 (Usage & API Reference)](#6-使用说明与-api-规范-usage--api-reference)
  - [多账号登录与账号管理](#2-多账号登录与账号管理)
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
  - **动态品名词云透视 (WordCloud)**：深度挖掘**当前核算账期**的支出品名关键词（未选定月份时为全量历史），前端支持**按频次（消费偏好）**与**按金额（重度开销）**双维度加权自由切换，直观还原消费图谱。
  - **时间范围聚焦模式 (dataZoom)**：图表底部配备可视化滑动条与调节手柄，可自由框选并缩放任意日期区间的收支波动；移动端（视口宽度低于阈值）自动强制激活聚焦手柄，保障窄屏触控浏览体验。
- **深度穿透下钻（Drill-down 联动）**：
    - **柱状堆叠块点击**：点击任意一天的某一分类柱块，自动在**新标签页**打开管理后台，精确筛选当天的目标分类下的所有消费记录。
    - **商户榜与词云点击**：点击商户复购榜中的商户名或全景词云中的商品关键词，一键在新标签页中筛选出目标商户或目标品名关键词的检索，并**自动携带当前所选账期的起止日期**（如 2026-10 会传 `2026-10-01 ~ 2026-10-31`），保证只命中当月流水。
    - **多任务保留**：跳转默认以 `_blank` 新标签页唤起，不会破坏中断当前的看板浏览态。

### 🤖 DeepSeek-Flash 驱动的 AI 智能顾问
- **配置中心化与热调优**：所有任务的 System Prompt、模板结构（`prompt_template`）、采样温度（`temperature`）、最大输出（`max_tokens`）以及全局消费画像（`user_habits`）统一在 `config.yaml` 中配置，修改即刻生效，无需重启服务。
- **⚡ 核心指标体检 (`/api/ai/diagnose`)**：基于当月预算水位、花呗账单及消费画像快速给出务实、犀利的三点财务健康诊断。
- **📖 全月流水深度精读 (`/api/ai/deep_read`)**：将当月全量流水（百条级记录）紧凑化喂入大模型，耗费不到半分钱（Token 极低），全景扫描时间节律、情绪消费（夜间冲动花销）、小额隐形刺客（<15元高频支出）及高性价比省钱动作。
- **💬 账单流水智能问答 (`/api/ai/chat`)**：自然语言即时查询（如“本月吃炒饭花了多少钱？”、“我最近用花呗买了什么？”），内置账户代码语义翻译，无需人工写 SQL。
- **低延迟高吞吐优化**：深度调优 API 调用参数，禁用冗余思考链（Reasoning Chain），实现毫秒级快速响应，彻底告别 Token 截断。

### 🛠️ 全功能流水管理后台 (Manager GUI)
- **多维复合筛选**：支持按日期区间、多级分类（精确/包含匹配）、交易类型、收付款账户、商户、金额范围及关键字综合查询。
  - **与 URL 状态联动**：**原生支持从看板携带 URL 查询参数自动回填并触发精准检索**，同时支持一键安全重置（清空筛选与 URL 状态并恢复全量视图）。
- **行内无感编辑 (Inline Edit)**：表格单元格单击即改，失焦即存，内置账户代号与名称智能清洗。
- **系统级另存为导出 Excel**：采用现代浏览器的 `File System Access API`（`showSaveFilePicker`），弹出操作系统原生文件保存弹窗，支持自定义文件夹路径与文件名；自动降级兼容传统浏览器。

### 🛠️ 架构与工程化特性
- **零配置开箱即用（Auto-Init DB）**：基于 FastAPI `lifespan` 机制内置数据库自检。服务首次启动时，若检测到缺失 `bills.db`，会自动无感创建数据库文件、数据表结构及核心检索索引，无需手动执行 SQL 或额外初始化脚本。

### 🔐 多账号登录与权限体系 (Authentication)
- **全站登录闸门**：除登录页外，**所有页面与数据接口均需登录后方可访问**；未登录访问任意页面会自动跳转到 `static/login.html`，并在登录成功后回跳原目标页面。直接输入 URL、刷新页面或调用接口均无法绕过。
- **开箱即用的管理员**：首次部署（`users.db` 不存在时）自动创建管理员账号 **`admin` / `123456`**，无需任何手工初始化；初始化逻辑幂等，重复启动不会重复建号，也不会覆盖已修改的密码。
- **账号由管理员统一分配**：管理员登录后可在「账号管理」页创建新账号并分配初始密码，其他成员使用该账号密码即可登录；普通用户无权创建或删除账号。
- **自助修改账号名与密码**：所有用户（含管理员）均可自行修改**自己的**账号名与密码。修改密码需**两次填写新密码**以确保一致，无密码强度限制；修改账号名需输入当前密码确认身份。
- **密码绝不明文存储**：采用「**随机盐 + PBKDF2-HMAC-SHA256**（12 万次迭代）」哈希存储，格式为 `salt$hash`，每个账号盐值独立；校验使用恒定时间比较，防范时序攻击。会话令牌亦仅保存 SHA256 摘要，明文令牌只在登录响应中出现一次。
- **会话安全**：登录态通过 `HttpOnly` + `SameSite=Lax` Cookie 承载（前端 JS 无法读取，可缓解 XSS 窃取），有效期 7 天；密码修改后自动失效该账号全部会话，强制重新登录。

### 🌐 随时随地多端管理与远程协同
- **即插即用的远程访问支持**：系统服务默认监听本地/局域网端口，轻量无状态。配合 **虚拟内网 / 异地组网**（如 Tailscale、WireGuard、ZeroTier）或 **内网穿透工具**（如 Cloudflare Tunnel、frp、cpolar），无需公网 IP 即可在手机端浏览器、平板或异地电脑随时随地记账、核账与查阅 AI 报表。

---

## 2. 技术栈与运行环境 (Tech Stack & Prerequisites)

### 运行环境
- **Python**: `3.12.6`（推荐使用 Python 3.12.x 环境）
- **操作系统**: Windows 10/11, macOS, Linux
- **现代浏览器**: Chrome / Edge 86+（支持 File System Access API 原生另存为特性）

### 依赖项与核心库
- **Web 框架**: `FastAPI` + `Uvicorn`
- **数据存储**: `SQLite3`（Python 标准库，零配置本地账单数据库）
- **核算引擎与本地图表**: `jieba`（词云中文分词）、`numpy` + `matplotlib`（`analyze.py` 独立运行时渲染终端图表）
- **Excel 导出**: `pandas` + `openpyxl`（网页端按筛选条件导出 `.xlsx`）
- **配置解析**: `PyYAML`
- **大模型 SDK**: `openai`（适配 DeepSeek 开放平台接口）
- **前端库**: 原生 JavaScript (ES6+), HTML5, CSS3, `ECharts 5.x`, `marked.js`, `echarts-wordcloud.js`

---

## 3. 快速上手 (Getting Started)

你可以选择**方式一（一键脚本快速启动）**或**方式二（手动分步执行）**来进行部署：

---

### 方式一：一键快速启动（推荐）

项目内置了自动化环境准备与启动脚本，会自动检测并优先调用 Python 3.12 创建虚拟环境、安装依赖并启动服务。

1. **克隆仓库并进入目录**：
  ```bash
  git clone https://github.com/aonzik/billAnaly.git
  cd billAnaly

  ```

2. **配置应用参数**：
在项目根目录检查编辑 `config-example.yaml`（填入你的 DeepSeek API Key）并重命名为 `config.yaml`。
3. **双击或运行启动脚本**：
* **Windows**：双击运行项目根目录下的 `quickstart.bat`。
* **macOS**：初次使用需在终端赋予执行权限 `chmod +x quickstart.command`，随后在访达中双击 `quickstart.command` 即可运行。
* **Linux**：在终端中执行 `chmod +x quickstart.sh && ./quickstart.sh`。脚本会自动检测 Python 3.12、创建虚拟环境并安装依赖；下载前端资源需要 `curl` 或 `wget`（任选其一，均未安装时脚本会给出提示）。

---

### 方式二：手动分步执行

### 第一步：克隆仓库与准备虚拟环境
```bash
git clone https://github.com/aonzik/billAnaly.git
cd billAnaly

# 创建 Python 3.12.6 虚拟环境
python -m venv venv
# Windows 可用下述指令指定 3.12 版本：
# py -3.12 -m venv venv
# MacOS/Linux 可用下述指令指定 3.12 版本：
# python3.12 -m venv venv

# 激活虚拟环境
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

```

### 第二步：安装项目依赖

```bash
# 安装 python 第三方库依赖
pip install --upgrade pip
pip install -r requirements.txt
# 安装前端库依赖
# Windows (PowerShell):
#   New-Item -ItemType Directory -Force static/js
# macOS/Linux:
#   mkdir -p static/js
curl -o static/js/echarts.min.js "https://cdn.jsdelivr.net/npm/echarts@5.5.0/dist/echarts.min.js"
curl -o static/js/marked.min.js "https://cdn.jsdelivr.net/npm/marked/marked.min.js"
curl -o static/js/echarts-wordcloud.min.js "https://cdn.jsdelivr.net/npm/echarts-wordcloud@2/dist/echarts-wordcloud.min.js"
# 提示：Windows PowerShell 内置的 curl 是 Invoke-WebRequest 的别名，请改用 curl.exe；
# 也可以直接运行对应平台的 quickstart 脚本自动完成依赖下载。



```

### 第三步：配置应用参数

在项目根目录检查编辑 `config-example.yaml` 并重命名为 `config.yaml`：

```yaml
deepseek:
  api_key: "your-deepseek-api-key" # 填入你的 DeepSeek API Key
  base_url: "https://api.deepseek.com"
  model: "deepseek-flash"

```

### 第四步：启动服务

```bash
python server.py
# 或使用 uvicorn 直接启动：
# uvicorn server.py:app --host 127.0.0.1 --port 8000 --reload

```

**📌 访问入口**：
* **本地访问**：
  * 📈 **财务分析大屏 (Dashboard)**: `http://127.0.0.1:8000/dashboard.html`
  * 📑 **流水数据管理后台 (Manager)**: `http://127.0.0.1:8000/manager.html`
* **远程 / 移动端访问**：
  1. **局域网同一 Wi-Fi**：直接通过主机内网 IP 访问（如 `http://192.168.x.x:8000/dashboard.html`）。
  2. **异地远程访问**：通过 **Tailscale / WireGuard** 虚拟内网直接直连，或使用 **Cloudflare Tunnel / frp / cpolar** 进行内网穿透映射，实现外出时手机随时打开网页快速记账。

---

## 4. 目录结构 (Project Structure)

```text
billAnaly/
├── config.yaml               # 全局配置文件 (DeepSeek Key、剔除商户、词云词典、AI 提示词中心)
├── config-example.yaml       # 配置模板 (复制为 config.yaml 并填入 Key 后使用)
├── server.py                 # FastAPI 核心入口与静态文件路由托管
├── analyze.py                # 核心财务核算引擎 (聚合统计、垫付冲抵、商户排行榜)；可独立运行 `python analyze.py [YYYY-MM]`
├── ai_assistant.py           # AI 模块 (动态热加载配置、财务体检、深度精读、账单问答)
├── db_manager.py             # 数据库 CRUD 路由与 Excel 导出接口
├── auth.py                   # 身份验证模块 (盐哈希加密、会话管理、账号创建与改密 API)
├── bills.db                  # SQLite 核心账单数据库(首次启动由服务自动检测并创建)
├── users.db                  # 账号数据库(首次启动自动创建，并植入管理员 admin/123456)
├── requirements.txt          # Python 依赖清单
├── static/                   # 前端静态资源
│   ├── login.html            # 登录页 (未登录时所有页面均跳转至此)
│   ├── account.html          # 账号管理页 (改账号名/改密码；管理员可创建与删除账号)
│   ├── auth.js               # 前端登录态公共脚本 (用户栏注入、401 统一跳转登录页)
│   ├── dashboard.html        # 财务分析大屏页面 (含 dataZoom 时间聚焦组件)
│   ├── dashboard.js          # 大屏数据拉取、ECharts 走势图与聚焦、AI 交互与预算联动
│   ├── manager.html          # 流水数据管理与查询后台页面
│   ├── manager.js            # 流水多维筛选、行内实时编辑、另存为导出逻辑
│   ├── style.css             # 响应式全局界面样式与卡片网格布局
│   ├── expense_data.json     # 全量账单分析聚合缓存（未指定月份时使用）
│   ├── expense_data_YYYY-MM.json  # 按月份隔离的账单分析聚合缓存（如 expense_data_2026-09.json）
│   └── js/                   # 离线前端核心依赖库 (ECharts, Marked, WordCloud)
├── quickstart.bat            # Windows 一键快速配置虚拟环境并启动
├── quickstart.command        # macOS 一键快速配置虚拟环境并启动
├── quickstart.sh             # Linux 一键快速配置虚拟环境并启动
├── LICENSE.md                # MIT 开源许可证
└── README.md                 # 项目使用与说明文档

```

---

## 5. 配置说明 (Configuration)

### 1. 基础环境与商户过滤、专有名词定义 (`config.yaml`)

```yaml
deepseek:
  api_key: "sk-your-deepseek-api-key"
  base_url: "https://api.deepseek.com"
  model: "deepseek-flash"

# 商户复购榜中需要剔除的账户代码、支付通道或非真实商户名称
non_merchants:
  - HB        # 花呗
  - VX        # 微信
  - AL        # 支付宝
  - BK        # 银行卡
  - TC        # 交通卡
  - 微信
  - 支付宝

# 词云自定义专有名词（防止被 jieba 拆散成单字或碎词）
custom_words:
  - 娃哈哈
  - 蜜雪冰城
  - 洁面巾
  - 月卡
  - 盒味道
  - 牛丼
  - 拿铁

# 词云自定义屏蔽词（从统计结果中剔除）
stop_words:
  - 学费

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

* **花呗「下月待还」当期口径**：按选定账期核算时，`hb_repaid` 仅统计**品名含当月月份号（如 `10月花呗还款`）且目标账户为 `HB`** 的还款记录——本月还上月的款项（如 10 月 1 日还的 `9月花呗还款`）不会被计入当期；全量核算（未选定月份）时保持对所有花呗还款求和。请按 `N月花呗还款` 的格式录入还款品名。

---

## 6. 使用说明与 API 规范 (Usage & API Reference)

### 1. 常用后端 API 概览

| 请求方法 | 端点 URL | 说明 |
| --- | --- | --- |
| `GET` | `/api/months` | 获取数据库中已有记录的所有有效核算月份列表 |
| `POST` | `/api/refresh_analysis` | 接收 `year`、`month` 与 `monthly_budget`（兼容旧参数 `year_month`），触发重新核算，并按月份写入隔离缓存 `expense_data_YYYY-MM.json` |
| `GET` | `/api/wordcloud` | 获取支出品名的词云统计数据，支持按频次与金额双维度加权计算（默认提取 Top 80；可传 `year`+`month` 限定统计月份，缺省为全量历史） |
| `GET` | `/api/db/expenses` | 多条件检索流水明细（支持日期区间、分类/交易类型/账户/商户/品名/金额范围过滤与排序） |
| `POST` | `/api/db/expenses` | 新增一条流水明细（日期、时间、交易类型、分类、品名、金额、账户等） |
| `PUT` | `/api/db/expenses/{id}` | 按 ID 更新流水明细的任意字段 |
| `DELETE` | `/api/db/expenses/{id}` | 按 ID 删除流水明细 |
| `GET` | `/api/db/export_excel` | 接收筛选条件，以二进制流形式导出 `.xlsx` Excel 文件 |
| `GET` | `/api/ai/diagnose` | 读取 YAML 模板并调优，生成当前月份核心指标体检评估（支持 `year_month` 参数读取对应月份缓存） |
| `POST` | `/api/ai/parse_expense` | 将自然语言/语音记账文本解析为结构化账单条目（返回标准 JSON 字段） |
| `GET` | `/api/ai/deep_read` | 调取选定月份的逐笔全量流水，输出行为学审计深度报告 |
| `POST` | `/api/ai/chat` | 接收自然语言提问文本，检索近 200 条时序流水后由大模型作答 |
| `POST` | `/api/auth/login` | 登录验证，成功后下发会话 Cookie（**免登录可访问**） |
| `POST` | `/api/auth/logout` | 退出登录，销毁当前会话 |
| `GET` | `/api/auth/me` | 获取当前登录账号的 ID、账号名与角色 |
| `PUT` | `/api/auth/me/username` | 修改**自己**的账号名（需提供当前密码确认） |
| `PUT` | `/api/auth/me/password` | 修改**自己**的密码（需当前密码 + 两次一致的新密码） |
| `GET` | `/api/auth/users` | 列出全部账号（**仅管理员**） |
| `POST` | `/api/auth/users` | 创建新账号（**仅管理员**） |
| `DELETE` | `/api/auth/users/{id}` | 删除账号（**仅管理员**，不能删除自己或最后一个管理员） |

> 除 `/api/auth/login` 与登录页外，**所有**页面与接口均要求已登录；未登录访问页面返回 `302` 跳转登录页，访问接口返回 `401`。

### 2. 多账号登录与账号管理

**首次部署自动获得管理员账号：**

| 账号名 | 密码 | 角色 |
| --- | --- | --- |
| `admin` | `123456` | 管理员 |

> ⚠️ **安全提示**：服务部署到公网云服务器后，请务必第一时间登录并修改 `admin` 的默认密码（「账号管理 → 修改密码」）。密码为**盐哈希加密存储**，一旦忘记无法找回，只能由其他管理员重置或删除账号后重建。

**使用流程：**

1. 浏览器打开 `http://<服务器地址>:8000/`，未登录会自动跳转到 `login.html` 登录页。
2. 使用 `admin` / `123456` 登录，进入图表看板。
3. 点击右上角用户栏的 **「账号管理」**，在管理员区域填写新账号名与初始密码，点击「➕ 创建账号」，把账号密码告知使用者。
4. 使用者打开同一地址，用管理员分配的账号密码登录即可。
5. 任何用户（含管理员）都可以在「账号管理」页：
   * **修改账号名**：填写新账号名 + 当前密码 → 保存；之后请用新账号名登录。
   * **修改密码**：填写当前密码 + 新密码 + 确认新密码 → 保存；**两次输入必须一致**，无密码强度限制。修改成功后会强制退出，需用新密码重新登录。
6. 点击右上角 **「退出」** 即可注销登录态。

**账号数据说明：** 所有账号存放于项目根目录的 `users.db`（已被 `.gitignore` 忽略，不会误传到仓库）。删除该文件后重启服务，会重新生成默认管理员 `admin` / `123456`。

### 3. 前端快捷操作技巧

* **日期范围聚焦 (dataZoom)**：在仪表盘左侧的“每日支出趋势与分类堆叠”图表中，可直接拖动底部的缩放手柄，快速排查特定周期（如小长假、某一周冲动消费期）的花销分布；在窄屏移动端设备上该组件会自动勾选启动。
* **预算动态绑定**：在大屏右上角的“月度总预算”输入框中输入新金额按回车，页面指标会立即重算；在 AI 快捷提问中点击 `⚠️ 月底超支风险评估`，会自动捕获该输入框中的实时预算数字。
* **跨月对比**：在“核算账期”下拉框中选择历史月份，一键切换并查看历史收支结余与环比走势。
* **图表元素穿透下钻（查账必备）**：
  * 在堆叠柱状图中发现某一天某类开销突然冲高时，**直接鼠标点击该柱块**，系统会自动在新标签页打开 `manager.html` 并精准筛选出该天该类别的明细流水。
  * 在商户复购榜中点击商户行、或在全景词云中点击某个大字关键词，均可一键弹出新页面查阅相关的所有交易记录；跳转时会自动携带当前「核算账期」的起止日期，只命中当月流水。
  * 如果需要恢复全览，点击管理页的 **“重置筛选”** 按钮即可一键抹除参数并刷新展示全量数据。

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

### Q6: 首次部署时没有 `bills.db` 数据库文件怎么处理？
- **解答**：无需任何操作。系统在启动阶段会自动探测 `bills.db` 是否存在，若缺失会自动完成建库、建表（`expenses`）及建立相关查询索引（日期、分类、类型）。

### Q7: 为什么 2026-10 的「下月待还花呗」没有把 10 月 1 日还的「9月花呗还款」算进去？

- **解答**：按账期核算时，当期还款只认**品名含当月月份号（如 `10月花呗还款`）且目标账户为 `HB`** 的记录。10 月 1 日还的 `9月花呗还款` 是清偿 9 月账单，不计入 10 月的 `hb_repaid`（全量核算时保持对所有还款求和）。请按 `N月花呗还款` 的命名格式录入还款记录，即可正确统计当期待还。

### Q8: 词云图里的词和某个月份对不上？

- **解答**：词云默认跟随「核算账期」选择器统计**当前所选月份**的支出品名（未选定月份时为全量历史）。切换月份后看板会自动重新核算并刷新对应月份的隔离缓存，词云随之更新。

### Q9: 忘记密码了怎么办？密码存在哪里？

- **解答**：密码采用「随机盐 + PBKDF2-HMAC-SHA256」**单向哈希**存储于 `users.db`，**不可逆、无法找回**。普通用户忘记密码请联系管理员删除旧账号后重新创建；管理员忘记密码且无其他管理员时，可删除项目根目录的 `users.db` 并重启服务，系统会重新生成默认管理员 `admin` / `123456`（注意：此操作会清空所有已创建的账号）。

### Q10: 登录后过一段时间又要重新登录，或者多人共用一个账号有影响吗？

- **解答**：会话有效期默认为 **7 天**（见 `auth.py` 中的 `SESSION_TTL`）。同一账号可在多台设备同时登录，互不影响。修改密码后会强制该账号的全部设备下线，需用新密码重新登录。

### Q11: 部署到公网云服务器需要注意什么？

- **解答**：建议至少做到以下几点：
  1. 登录后**立即修改** `admin` 的默认密码；
  2. 为每位使用者**单独创建账号**，避免共用 `admin`；
  3. 生产环境建议在前面加一层 **Nginx / Caddy 反向代理并启用 HTTPS**（当前会话 Cookie 未强制 `Secure` 属性，如需更高安全性可在 `auth.py` 的 `set_cookie` 中补充 `secure=True`）；
  4. 切勿把 `users.db`、`bills.db`、`config.yaml` 提交到公开仓库（`.gitignore` 已默认忽略）。

---

## 8. 贡献指南与开源协议 (Contributing & License)

### 参与贡献

欢迎提交 Issue 报告 Bug 或提出新需求；

### 开源协议

本项目采用 [MIT License](LICENSE.md) 授权许可。你可以自由地使用、修改和分发本项目代码。

---

## 9. 致谢与 AIGC 声明 (Acknowledgments & AIGC Statement)

本项目由开发者主导架构设计与业务把控，项目全生命周期在 **Google Gemini** 与 **DeepSeek** 的结对编程及协作下迭代推进：

* **前期构建与核心架构 (Powered by Google Gemini)**：主导全项目基础架构选型、FastAPI 路由规范、SQLite 核心财务核算逻辑设计、ECharts 动态可视化与前端响应式交互链路搭建。
* **功能扩展与深度迭代 (Powered by DeepSeek)**：深度参与后续特性的编码实现、部分模块的重构优化、细分业务逻辑完善以及基于 DeepSeek 模型的智能财务分析场景落地。
