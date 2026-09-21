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
        })
        .catch(err => {
            console.error('加载数据失败:', err);
            document.body.innerHTML += `<p style="color:red;padding:20px;">数据加载失败: ${err.message}</p>`;
        });
});

// 1. 顶部指标卡片
function renderKpiCards(data) {
    const kpiCards = document.getElementById('kpi-cards');
    kpiCards.innerHTML = `
        <div class="card">
            <div class="card-label">下月待还花呗</div>
            <div class="card-value" style="color: #e67e22;">¥${data.hb.need_pay.toFixed(2)}</div>
        </div>
        <div class="card">
            <div class="card-label">建议今日起可用日均</div>
            <div class="card-value" style="color: #27ae60;">¥${data.budget.dynamic_safe_budget.toFixed(1)}/天</div>
        </div>
        <div class="card">
            <div class="card-label">基准安全日均</div>
            <div class="card-value">¥${data.budget.safe_daily_baseline.toFixed(1)}/天</div>
        </div>
        <div class="card">
            <div class="card-label">拿铁因子（饮食*累计）</div>
            <div class="card-value" style="color: #c0392b;">¥${data.latte.cost.toFixed(1)}</div>
        </div>
    `;
}

// 2. 左侧图：堆叠柱状图 + 净支出走势折线
function renderBarLineChart(data) {
    const chart = echarts.init(document.getElementById('barLineChart'));
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

    chart.setOption({
        title: {
            text: '逐日日常支出分类构成与净支出走势',
            subtext: '鼠标悬停可查看每日分类明细与走势',
            left: 'center'
        },
        tooltip: {
            trigger: 'axis',
            axisPointer: { type: 'cross' }
        },
        legend: {
            top: 45,
            type: 'scroll'
        },
        grid: { left: '4%', right: '4%', bottom: '8%', top: 95, containLabel: true },
        xAxis: { type: 'category', data: dates, axisLabel: { rotate: 35 } },
        yAxis: { type: 'value', name: '金额 (元)' },
        series: seriesList
    });

    window.addEventListener('resize', () => chart.resize());
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
            <tr>
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
// AI 智能问答与体检面板逻辑
// =========================================================================

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
    if (typeof loadDashboardData === 'function') {
        loadDashboardData();
    } else {
        location.reload();
    }
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
    if (typeof loadDashboardData === 'function') {
        loadDashboardData();
    } else {
        location.reload();
    }
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