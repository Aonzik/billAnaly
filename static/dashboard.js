document.addEventListener('DOMContentLoaded', () => {
    fetch('expense_data.json')
        .then(response => {
            if (!response.ok) {
                throw new Error('无法读取 expense_data.json，请确认文件路径是否正确。');
            }
            return response.json();
        })
        .then(data => {
            renderKpiCards(data);
            renderBarLineChart(data);
            renderDonutChart(data);
            renderLatteFactor(data);   // 新增：渲染拿铁因子明细
            renderMerchantRank(data);   // 新增：渲染商户复购榜
            renderWordCloud(data);     // 新增：渲染全景词云
        })
        .catch(err => {
            console.error('加载数据失败:', err);
            document.body.innerHTML += `<p style="color:red;padding:20px;">数据加载失败: ${err.message}</p>`;
        });
});

// 1. 顶部指标卡片
function renderKpiCards(data) {
    if (!data) return;
    const overview = data.overview || {};
    const hb = data.hb || {};
    const budget = data.budget || {};
    const latte = data.latte || {};
    // 1. 月度总支出
    const totalExpenseElem = document.getElementById('card-total-expense');
    if (totalExpenseElem) {
        totalExpenseElem.innerText = `¥${Number(overview.monthly_total_expense || 0).toFixed(2)}`;
    }
    // 2. 资产净增长
    const netGrowthElem = document.getElementById('card-net-growth');
    const growthHintElem = document.getElementById('card-growth-hint');
    if (netGrowthElem) {
        const netGrowth = Number(overview.monthly_net_growth || 0);
        if (netGrowth >= 0) {
            netGrowthElem.innerText = `+¥${netGrowth.toFixed(2)}`;
            netGrowthElem.style.color = '#16a34a';
            if (growthHintElem) growthHintElem.innerText = "当月收支结余健康";
        } else {
            netGrowthElem.innerText = `-¥${Math.abs(netGrowth).toFixed(2)}`;
            netGrowthElem.style.color = '#dc2626';
            if (growthHintElem) growthHintElem.innerText = "当月支出超过总收入";
        }
    }
    // 3. 待收回垫付
    const pendingRecoveryElem = document.getElementById('card-pending-recovery');
    const recoveryHintElem = document.getElementById('card-recovery-hint');
    if (pendingRecoveryElem) {
        const pendingRec = Number(overview.pending_recovery || 0);
        pendingRecoveryElem.innerText = `¥${pendingRec.toFixed(2)}`;
        if (pendingRec <= 0) {
            pendingRecoveryElem.style.color = '#64748b';
            if (recoveryHintElem) recoveryHintElem.innerText = "本期垫付已全部平账";
        } else {
            pendingRecoveryElem.style.color = '#2563eb';
            if (recoveryHintElem) recoveryHintElem.innerText = `仍有 ¥${pendingRec.toFixed(2)} 待平账`;
        }
    }
    // 4. 花呗待还
    const hbElem = document.getElementById('card-hb-need-pay');
    if (hbElem) hbElem.innerText = `¥${Number(hb.need_pay || 0).toFixed(2)}`;
    // 5. 建议日均
    const dynamicBudgetElem = document.getElementById('card-dynamic-budget');
    if (dynamicBudgetElem) dynamicBudgetElem.innerText = `¥${Number(budget.dynamic_safe_budget || 0).toFixed(1)}/天`;
    // 6. 基准日均
    const baselineBudgetElem = document.getElementById('card-baseline-budget');
    if (baselineBudgetElem) baselineBudgetElem.innerText = `¥${Number(budget.safe_daily_baseline || 0).toFixed(1)}/天`;
    // 7. 拿铁因子
    const latteElem = document.getElementById('card-latte-cost');
    if (latteElem) latteElem.innerText = `¥${Number(latte.cost || 0).toFixed(1)}`;
}

// 2. 左侧图：堆叠柱状图 + 净支出走势折线
function renderBarLineChart(data) {
    const chartDom = document.getElementById('barLineChart');
    if (!chartDom) return;
    const chart = echarts.init(chartDom);
    const dates = data.daily_trend.dates;
    const categories = data.daily_trend.categories;
    const pivot = data.daily_trend.pivot_data;
    const safeBaseline = data.budget.safe_daily_baseline;

    const seriesList = categories.map(cat => ({
        name: cat,
        type: 'bar',
        stack: '支出构成',
        emphasis: { focus: 'series' },
        data: pivot[cat]
    }));

    seriesList.push({
        name: '每日净支出走势',
        type: 'line',
        data: data.daily_trend.net_expenses,
        lineStyle: { color: '#c0392b', width: 3 },
        itemStyle: { color: '#c0392b' },
        markLine: {
            data: [{
                yAxis: safeBaseline,
                name: '建议日均线',
                lineStyle: { color: '#27ae60', type: 'dashed', width: 2 },
                label: { formatter: '安全基准: ¥' + safeBaseline.toFixed(1) }
            }]
        }
    });

    const MOBILE_BREAKPOINT = 768;
    const checkboxElem = document.getElementById('toggle-datazoom');
    const labelElem = document.getElementById('toggle-datazoom-label');

    // 生成 dataZoom 配置：
    // 当 enabled 为 false 时，重置显示范围为 0% ~ 100% 并隐藏滑块，彻底恢复完整模式
    function getZoomConfig(enabled) {
        return [
            {
                type: 'inside',
                disabled: !enabled,
                start: enabled ? 65 : 0,
                end: 100,
                zoomOnMouseWheel: enabled,
                moveOnMouseMove: enabled,
                moveOnMouseWheel: enabled
            },
            {
                type: 'slider',
                show: enabled,
                start: enabled ? 65 : 0,
                end: 100,
                height: 14,
                bottom: 8,
                borderColor: 'transparent',
                backgroundColor: '#f1f5f9',
                fillerColor: 'rgba(59, 130, 246, 0.2)',
                handleSize: '100%',
                showDetail: false
            }
        ];
    }

    function syncZoomState() {
        const isSmallScreen = window.innerWidth <= MOBILE_BREAKPOINT;

        if (checkboxElem) {
            if (isSmallScreen) {
                checkboxElem.checked = true;
                checkboxElem.disabled = true;
                if (labelElem) labelElem.innerText = "聚焦 (小屏锁定)";
            } else {
                checkboxElem.disabled = false;
                if (labelElem) labelElem.innerText = "聚焦模式";
            }
        }

        const shouldEnableZoom = checkboxElem ? checkboxElem.checked : isSmallScreen;

        chart.setOption({
            grid: {
                left: '3%',
                right: '4%',
                top: 90, // 给顶部标题和图例留出足够空间
                bottom: shouldEnableZoom ? 50 : 36,
                containLabel: true
            },
            dataZoom: getZoomConfig(shouldEnableZoom)
        });
        // 监听柱块点击：获取日期和分类
        chart.off('click'); // 防止重复绑定
        chart.on('click', function (params) {
            // 排除趋势折线和标线，仅响应柱状堆叠块
            if (params.seriesType === 'bar') {
                const date = params.name;       // X 轴日期 (如 2026-09-12)
                const category = params.seriesName; // 堆叠系列的分类名称 (如 饮食、交通)
                jumpToManager({ date: date, category: category });
            }
        });
    }

    chart.setOption({
        title: {
            text: '逐日日常支出分类构成与净支出走势',
            subtext: '鼠标悬停可查看每日分类明细与走势',
            left: 'center',
            top: 6
        },
        tooltip: {
            trigger: 'axis',
            axisPointer: { type: 'cross' }
        },
        legend: {
            top: 50,
            type: 'scroll',
            // 避免左右过宽遮挡纵坐标标题和右上角勾选按钮
            left: '12%',
            right: '12%'
        },
        xAxis: { type: 'category', data: dates, axisLabel: { rotate: 35 } },
        yAxis: {
            type: 'value',
            name: '金额 (元)',
            nameGap: 14,
            nameTextStyle: {
                align: 'center',
                padding: [0, 6, 0, 0]
            }
        },
        series: seriesList
    });

    syncZoomState();

    if (checkboxElem) {
        checkboxElem.addEventListener('change', syncZoomState);
    }

    window.addEventListener('resize', () => {
        chart.resize();
        syncZoomState();
    });
}

// 3. 右侧图：紧凑微空心双环图
function renderDonutChart(data) {
    const chart = echarts.init(document.getElementById('nestedDonutChart'));

    chart.setOption({
        title: {
            text: '常规刚性 vs 弹性支出构成双环图',
            subtext: '鼠标悬停图块即时显示金额与占比信息',
            left: 'center'
        },
        tooltip: {
            trigger: 'item',
            formatter: function (params) {
                const isOuter = params.seriesIndex === 1;
                const tag = isOuter ? '二级细分' : '一级属性';
                return `<b>${params.name}</b> (${tag})<br/>` +
                       `支出金额: <b>¥${params.value.toFixed(2)}</b><br/>` +
                       `环内占比: <b>${params.percent}%</b>`;
            }
        },
        legend: {
            type: 'scroll',
            orient: 'horizontal',
            bottom: 5,
            left: 'center',
            itemWidth: 14,
            itemHeight: 10,
            textStyle: { fontSize: 11 }
        },
        series: [
            // 内环：圆环形态
            {
                name: '支出属性',
                type: 'pie',
                selectedMode: 'single',
                radius: ['28%', '46%'],
                center: ['50%', '50%'],
                itemStyle: {
                    borderRadius: 4,
                    borderColor: '#ffffff',
                    borderWidth: 2
                },
                label: {
                    position: 'inner',
                    fontSize: 11,
                    fontWeight: 'bold',
                    color: '#000000',
                    formatter: '{b}\n{d}%'
                },
                labelLine: { show: false },
                data: data.donut_chart.inner
            },
            // 外环：微缝贴合
            {
                name: '详细分类',
                type: 'pie',
                radius: ['50%', '68%'],
                center: ['50%', '50%'],
                itemStyle: {
                    borderRadius: 3,
                    borderColor: '#ffffff',
                    borderWidth: 1.5
                },
                avoidLabelOverlap: true,
                labelLayout: {
                    hideOverlap: false,
                    moveOverlap: 'shiftY'
                },
                label: {
                    formatter: '{b}: ¥{c} ({d}%)',
                    fontSize: 10.5
                },
                labelLine: {
                    length: 10,
                    length2: 12
                },
                data: data.donut_chart.outer
            }
        ]
    });

    window.addEventListener('resize', () => chart.resize());
}

// 4. 新增：渲染拿铁因子完整统计（饮品/糖分 vs 零食小吃）
function renderLatteFactor(data) {
    const latte = data.latte;
    const totalCost = latte.cost;

    // 更新标题旁边的总计汇总徽章
    document.getElementById('latte-total-summary').innerText = 
        `共消费 ${latte.count} 笔 / 折合 ${latte.items} 件 / 累计 ¥${totalCost.toFixed(2)}`;

    // 计算金额占比
    const drinkPct = totalCost > 0 ? ((latte.drinks_cost / totalCost) * 100).toFixed(1) : 0;
    const snackPct = totalCost > 0 ? ((latte.snacks_cost / totalCost) * 100).toFixed(1) : 0;

    const container = document.getElementById('latte-breakdown-container');
    container.innerHTML = `
        <!-- 饮品/糖分 -->
        <div class="latte-item">
            <div class="latte-item-header">
                <span>🥤 饮品/糖分</span>
                <span style="color: #2563eb;">¥${latte.drinks_cost.toFixed(2)} (${drinkPct}%)</span>
            </div>
            <div class="progress-bar">
                <div class="progress-fill" style="width: ${drinkPct}%; background-color: #3b82f6;"></div>
            </div>
            <div class="latte-meta">
                <span>购买频次: <b>${latte.drinks_count}</b> 笔</span>
                <span>折合商品: <b>${latte.drinks_items}</b> 罐/杯</span>
                <span>均笔单价: <b>¥${(latte.drinks_cost / (latte.drinks_count || 1)).toFixed(1)}</b></span>
            </div>
        </div>

        <!-- 零食小吃 -->
        <div class="latte-item">
            <div class="latte-item-header">
                <span>🍿 零食小吃</span>
                <span style="color: #ea580c;">¥${latte.snacks_cost.toFixed(2)} (${snackPct}%)</span>
            </div>
            <div class="progress-bar">
                <div class="progress-fill" style="width: ${snackPct}%; background-color: #f97316;"></div>
            </div>
            <div class="latte-meta">
                <span>购买频次: <b>${latte.snacks_count}</b> 笔</span>
                <span>折合商品: <b>${latte.snacks_items}</b> 份/包</span>
                <span>均笔单价: <b>¥${(latte.snacks_cost / (latte.snacks_count || 1)).toFixed(1)}</b></span>
            </div>
        </div>
    `;
}

// 5. 新增：渲染商户复购榜 Top 5
function renderMerchantRank(data) {
    const list = data.top_merchants || [];
    const tbody = document.getElementById('merchant-table-body');

    if (list.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;color:#94a3b8;">暂无商户消费数据</td></tr>';
        return;
    }

    tbody.innerHTML = list.map((item, idx) => {
        const rank = idx + 1;
        let rankClass = 'rank-other';
        if (rank === 1) rankClass = 'rank-1';
        else if (rank === 2) rankClass = 'rank-2';
        else if (rank === 3) rankClass = 'rank-3';

        return `
            <tr onclick="jumpToManager({ merchant: '${item.name}' })" 
                style="cursor: pointer; transition: background 0.15s;" 
                onmouseover="this.style.background='#f8fafc'" 
                onmouseout="this.style.background=''"
                title="点击筛选该商户全部流水">
                <td><span class="rank-badge ${rankClass}">${rank}</span></td>
                <td style="font-weight: 600; color: #1e293b;">${item.name}</td>
                <td style="text-align: right; font-weight: bold; color: #2563eb;">${item.count} 次</td>
                <td style="text-align: right; font-weight: bold; color: #0f172a;">¥${item.amount.toFixed(2)}</td>
                <td style="text-align: right; color: #64748b;">${item.items} 件</td>
            </tr>
        `;
    }).join('');
}

// =========================================================================
// 6. 新增：消费品名全景词云逻辑 (支持频次 / 金额双模式切换)
// =========================================================================
let wordCloudChart = null;
let wordCloudCache = { by_freq: [], by_amount: [] };
let currentWordCloudMode = 'freq'; // 'freq' | 'amount'

// 外部调用的入口函数：接收 expense_data.json 里的 wordcloud 数据
function renderWordCloud(data) {
    if (!data || !data.wordcloud) return;
    wordCloudCache = data.wordcloud;
    
    // 检查当前拨动开关状态
    const toggle = document.getElementById('wc-mode-toggle');
    const mode = (toggle && toggle.checked) ? 'amount' : 'freq';
    renderWordCloudChart(mode);
}

// 核心渲染函数
function renderWordCloudChart(mode = 'freq') {
    const chartDom = document.getElementById('wordcloud-chart');
    if (!chartDom) return;

    if (!wordCloudChart) {
        wordCloudChart = echarts.init(chartDom);
        window.addEventListener('resize', () => {
            if (wordCloudChart) wordCloudChart.resize();
        });
    }

    const isAmount = (mode === 'amount');
    const dataList = isAmount ? wordCloudCache.by_amount : wordCloudCache.by_freq;

    // 动态切换开关两端文字的高亮颜色
    const labelFreq = document.getElementById('label-mode-freq');
    const labelAmount = document.getElementById('label-mode-amount');
    if (labelFreq && labelAmount) {
        labelFreq.style.color = isAmount ? '#94a3b8' : '#2563eb';
        labelAmount.style.color = isAmount ? '#ea580c' : '#94a3b8';
    }

    const option = {
        tooltip: {
            show: true,
            formatter: function (params) {
                return `<b>${params.name}</b><br/>${isAmount ? '累计支出金额' : '消费出现频次'}: <b>${params.value}</b> ${isAmount ? '元' : '次'}`;
            }
        },
        series: [{
            type: 'wordCloud',
            shape: 'rect',
            keepAspect: false,
            left: 'center',
            top: 'center',
            width: '100%',
            height: '100%',
            sizeRange: isAmount ? [18, 65] : [16, 58],
            rotationRange: [-45, 45],
            rotationStep: 45,
            gridSize: 5,
            drawOutOfBound: false,
            layoutAnimation: true,
            textStyle: {
                fontFamily: 'system-ui, -apple-system, sans-serif',
                fontWeight: 'bold',
                color: function () {
                    // 金额模式偏暖红金色系，频次模式偏清新冷蓝色系
                    if (isAmount) {
                        return 'rgb(' + [
                            Math.round(180 + Math.random() * 60),
                            Math.round(40 + Math.random() * 80),
                            Math.round(20 + Math.random() * 50)
                        ].join(',') + ')';
                    } else {
                        return 'rgb(' + [
                            Math.round(30 + Math.random() * 100),
                            Math.round(70 + Math.random() * 110),
                            Math.round(160 + Math.random() * 80)
                        ].join(',') + ')';
                    }
                }
            },
            emphasis: {
                focus: 'self',
                textStyle: {
                    textShadowBlur: 8,
                    textShadowColor: 'rgba(0, 0, 0, 0.25)'
                }
            },
            data: dataList || []
        }]
    };

    wordCloudChart.setOption(option, true);
    // 监听词云词语点击
    wordCloudChart.off('click');
    wordCloudChart.on('click', function (params) {
        if (params.name) {
            // 将点击的词作为品名/关键词传入筛选
            jumpToManager({ keyword: params.name });
        }
    });
}

// 拨动开关切换事件（绑定在 HTML 上的 onchange="switchWordCloudMode(this.checked)"）
window.switchWordCloudMode = function(isAmountChecked) {
    currentWordCloudMode = isAmountChecked ? 'amount' : 'freq';
    renderWordCloudChart(currentWordCloudMode);
};

// 通用跳转至管理后台并携带筛选参数
function jumpToManager(filters = {}) {
    const params = new URLSearchParams();
    for (const [key, value] of Object.entries(filters)) {
        if (value !== undefined && value !== null && value !== '') {
            params.append(key, value);
        }
    }
    // 当前页面跳转；若希望新标签页打开可改为 window.open(`manager.html?${params.toString()}`, '_blank');
    const targetUrl = `manager.html?${params.toString()}`;
    window.open(targetUrl, '_blank')
}

// =========================================================================
// AI 智能问答与体检面板逻辑
// =========================================================================

// 定义全局变量，记录当前 AI 最新的原始 Markdown/文本内容
let currentAiRawMarkdown = "";

window.quickFill = function(text) {
    // 1. 动态获取当前界面输入框里的预算（若无则取本地缓存或兜底 2800）
    const budgetInput = document.getElementById('custom-budget-input');
    const budgetVal = (budgetInput && budgetInput.value.trim()) 
                      ? budgetInput.value.trim() 
                      : (localStorage.getItem('user_monthly_budget') || '2300');

    // 2. 顺便获取当前选中的核算账期（如 2026-09）
    const monthSelector = document.getElementById('month-selector');
    const monthVal = monthSelector ? monthSelector.value : '';

    // 3. 动态替换占位符
    let finalPrompt = text
        .replaceAll('{budget}', budgetVal)
        .replaceAll('{month}', monthVal);

    // 4. 智能兜底：如果 prompt 中没有显式写 {budget}，但涉及超支分析，自动在句首补充预算前提
    if (!text.includes('{budget}') && finalPrompt.includes('超支') && !finalPrompt.includes('预算')) {
        finalPrompt = `我本月设定的总预算是 ${budgetVal} 元。${finalPrompt}`;
    }

    // 5. 填入输入框并触发提问
    const input = document.getElementById('ai-query-input');
    if (input) {
        input.value = finalPrompt;
    }
    window.submitAiQuery();
};

// 1. 生成综合体检报告
async function runAiDiagnose() {
    const box = document.getElementById('ai-response-box');
    const btn = document.getElementById('btn-quick-diagnose');
    
    btn.disabled = true;
    btn.innerText = "⏳ 正在分析账单...";
    box.innerHTML = `<span style="color:#2563eb;">🤖 DeepSeek 正在基于本月预算、刚性支出与拿铁因子进行深度综合评估，请稍候...</span>`;

    try {
        const res = await fetch('/api/ai/diagnose');
        const data = await res.json();
        
        if (data.advice) {
            currentAiRawMarkdown = data.advice;
            box.innerHTML = marked.parse(data.advice);
        } else if (data.detail) {
            box.innerHTML = `<span style="color:#dc2626;">❌ 请求失败: ${data.detail}</span>`;
        } else {
            box.innerHTML = `<span style="color:#dc2626;">❌ 未获取到诊断内容，接口返回为空</span>`;
        }
    } catch (err) {
        console.error("AI 请求异常:", err);
        box.innerHTML = `<span style="color:#dc2626;">❌ 连接后端失败: ${err.message}</span>`;
    } finally {
        btn.disabled = false;
        btn.innerText = "⚡ 生成本月财务体检报告";
    }
}

// 2. 自由自然语言提问
async function submitAiQuery() {
    const input = document.getElementById('ai-query-input');
    const q = input.value.trim();
    if (!q) return;

    const box = document.getElementById('ai-response-box');
    const btn = document.getElementById('btn-submit-query');
    
    btn.disabled = true;
    btn.innerText = "思考中...";
    box.innerHTML = `<span style="color:#2563eb;">🔍 正在检索账单数据库并由 DeepSeek 汇总计算: "${q}"...</span>`;

    try {
        const res = await fetch('/api/ai/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query: q })
        });
        const data = await res.json();

        if (data.answer) {
            currentAiRawMarkdown = data.answer;
            box.innerHTML = marked.parse(data.answer);
        } else if (data.detail) {
            box.innerHTML = `<span style="color:#dc2626;">❌ 提问失败: ${data.detail}</span>`;
        } else {
            box.innerHTML = `<span style="color:#dc2626;">❌ 未获取到回答</span>`;
        }
    } catch (err) {
        console.error("提问异常:", err);
        box.innerHTML = `<span style="color:#dc2626;">❌ 提问失败: ${err.message}</span>`;
    } finally {
        btn.disabled = false;
        btn.innerText = "提 问";
    }
}

// 初始化加载月份列表
async function initMonthSelector() {
    const res = await fetch('/api/months');
    const months = await res.json();
    const selector = document.getElementById('month-selector');
    
    if (months.length > 0) {
        selector.innerHTML = months.map(m => `<option value="${m}">${m}</option>`).join('');
    } else {
        selector.innerHTML = `<option value="2026-09">2026-09</option>`;
    }
}

// 切换月份触发重新计算并刷新图表
async function changeMonth(selectedYm) {
    await fetch(`/api/refresh_analysis?year_month=${selectedYm}`, { method: 'POST' });
    // 重新拉取 static/expense_data.json 渲染 ECharts（调用你原有的渲染总函数）
    location.reload();
}

// =========================================================================
// AI 全月流水深度精读逻辑
// =========================================================================
window.runDeepRead = async function() {
    const box = document.getElementById('ai-response-box');
    const btn = document.getElementById('btn-deep-read');
    
    // 动态获取顶部选择的月份，若无选择器则兜底默认值
    const monthSelector = document.getElementById('month-selector');
    const ym = monthSelector ? monthSelector.value : '2026-09';

    if (btn) {
        btn.disabled = true;
        btn.innerText = "📖 正在逐笔通读全月流水...";
    }
    
    if (box) {
        box.innerHTML = `<span style="color:#ea580c;">🤖 DeepSeek 正在通读 ${ym} 的每一笔消费流水，分析消费节律、排查隐形开销，请稍候...</span>`;
    }

    try {
        const res = await fetch(`/api/ai/deep_read?year_month=${encodeURIComponent(ym)}`);
        const data = await res.json();

        if (box) {
            if (data.report) {
                currentAiRawMarkdown = data.report;
                // 如果页面引入了 marked.js 则渲染 Markdown，否则优雅降级为纯文本显示
                if (typeof marked !== 'undefined' && marked.parse) {
                    box.innerHTML = marked.parse(data.report);
                } else {
                    box.innerText = data.report;
                }
            } else if (data.detail) {
                box.innerHTML = `<span style="color:#dc2626;">❌ 错误: ${data.detail}</span>`;
            } else {
                box.innerHTML = `<span style="color:#dc2626;">❌ 未获取到精读报告内容</span>`;
            }
        }
    } catch (err) {
        console.error("精读请求异常:", err);
        if (box) {
            box.innerHTML = `<span style="color:#dc2626;">❌ 连接后端失败: ${err.message}</span>`;
        }
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerText = "📖 全月流水深度精读";
        }
    }
};

// ai 回答导出
function exportAiAdvice() {
    const box = document.getElementById('ai-response-box');

    // 优先读取原始 Markdown 文本，如果没有就读取 innerText 兜底
    let exportContent = currentAiRawMarkdown;
    if (!exportContent || !exportContent.trim()) {
        exportContent = box.innerText.trim();
    }

    // 校验是否有有效内容（排除默认提示文案）
    if (!exportContent || exportContent.includes("点击上方“生成本月财务体检报告”")) {
        alert("当前暂无可导出的 AI 分析内容，请先生成报告或提问！");
        return;
    }

    // 生成时间戳文件名：如 AI财务分析报告_2026-03-24_1430.md
    const now = new Date();
    const pad = (n) => String(n).padStart(2, '0');
    const timestamp = `${now.getFullYear()}${pad(now.getMonth() + 1)}${pad(now.getDate())}_${pad(now.getHours())}${pad(now.getMinutes())}`;
    const filename = `AI财务分析报告_${timestamp}.md`;

    // 加上文件头部元信息
    const fileHeader = `# AI 智能财务顾问分析报告\n> 导出时间: ${now.toLocaleString()}\n\n---\n\n`;
    const fullContent = fileHeader + exportContent;

    // 创建 Blob 对象并触发无感下载
    const blob = new Blob([fullContent], { type: 'text/markdown;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);

    link.setAttribute('href', url);
    link.setAttribute('download', filename);
    link.style.visibility = 'hidden';
    
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url); // 释放内存
}

// =========================================================================
// 自定义月度预算逻辑与联动刷新
// =========================================================================

// 获取当前生效的预算（优先从 localStorage 读取，兜底 2800）
function getCurrentBudget() {
    const saved = localStorage.getItem('user_monthly_budget');
    return saved ? parseFloat(saved) : 2300;
}

// 初始化预算输入框
function initBudgetInput() {
    const budgetInput = document.getElementById('custom-budget-input');
    if (budgetInput) {
        budgetInput.value = getCurrentBudget();
    }
}

// 用户点击“更新预算”或在输入框按回车
async function applyBudgetChange() {
    const budgetInput = document.getElementById('custom-budget-input');
    const newBudget = parseFloat(budgetInput.value);

    if (isNaN(newBudget) || newBudget < 0) {
        alert("请输入合法的预算金额！");
        return;
    }

    // 1. 持久化存入浏览器的本地存储
    localStorage.setItem('user_monthly_budget', newBudget);

    // 2. 触发重新计算与页面刷新
    await refreshWithCurrentParams();
}

// 切换月份触发
async function onMonthChange() {
    await refreshWithCurrentParams();
}

// 统一根据当前的月份与预算触发分析刷新
async function refreshWithCurrentParams() {
    const monthSelector = document.getElementById('month-selector');
    const ym = monthSelector ? monthSelector.value : '';
    const budget = getCurrentBudget();

    const params = new URLSearchParams();
    if (ym) params.append('year_month', ym);
    params.append('monthly_budget', budget);

    const res = await fetch(`/api/refresh_analysis?${params.toString()}`, { method: 'POST' });
    const data = await res.json();

    // 重新拉取并渲染 ECharts 图表（若有该函数则调用，没有则刷新页面）
    location.reload();
}

// 在页面 DOM 加载完成后执行初始化
document.addEventListener('DOMContentLoaded', () => {
    initBudgetInput();
    if (typeof initMonthSelector === 'function') {
        initMonthSelector();
    }
});

// 在页面加载事件中调用
initMonthSelector();