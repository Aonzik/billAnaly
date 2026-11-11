// ============================================================
// 分类色彩系统：核心分类专属语义映射 + 长尾分类冷暖跳跃调色板
// ============================================================

// 1. 核心消费分类专属语义色（彻底解决高频分类扎堆撞色）
const SEMANTIC_CATEGORY_MAP = {
    '饮食':   '#F97316',  // 活力珊瑚橙 (暖色 H25) — 高频日常烟火气
    '饮食*':  '#F59E0B',  // 拿铁琥珀黄 (暖色 H38) — 拿铁/零食因子，同属就餐但阶梯清晰
    '交通':   '#635BFF',  // 主品牌紫蓝 (冷色 H265) — 理性通勤，Stripe 主题色
    '日用':   '#10B981',  // 清新翠绿 (冷/中性 H160) — 彻底告别紫色！生机明朗
    '居住':   '#854D0E',  // 典雅暖木褐/砖木棕 (暖中性偏深 H32) — 不动产刚需，解耦内环刚性灰色
    '房租':   '#854D0E',  // 房租别名
    '花呗':   '#06B6D4',  // 数智青蓝/湖蓝 (冷色 H191) — 金融信贷理性还款，告别橙红
    '娱乐':   '#8B5CF6',  // 优雅紫罗兰 (中性 H258) — 休闲放松
    '数字':   '#3B82F6',  // 科技天蓝 (冷色 H217) — 订阅与数码
    '数码':   '#3B82F6',  // 数码别名
    '周边':   '#EC4899',  // 潮流玫粉 (暖色 H330) — 潮玩文创独立色彩
    '医疗':   '#EF4444',  // 警示朱红 (H0) — 健康医药应急
    '服饰':   '#A855F7',  // 时尚亮紫
    '教育':   '#14B8A6',  // 学习蓝绿
    '转账':   '#64748B',  // 中性灰蓝
};

// 2. 长尾与动态分类兜底调色板（冷暖大交替序列，色距间隔 > 60°）
const DYNAMIC_PALETTE = [
    '#0284C7',  // 天蓝 (冷)
    '#F43F5E',  // 玫瑰红 (暖)
    '#14B8A6',  // 蓝绿 (冷)
    '#D97706',  // 赭石金 (暖)
    '#A855F7',  // 亮紫 (中)
    '#84CC16',  // 黄绿 (冷暖中性)
    '#6366F1',  // 靛青 (冷)
    '#FB923C',  // 杏橙 (暖)
    '#2DD4BF',  // 浅水绿 (冷)
    '#E11D48',  // 绯红 (暖)
    '#38BDF8',  // 冰天蓝 (冷)
    '#FB7185',  // 珊瑚粉 (暖)
    '#A3E635',  // 柠檬绿 (中)
    '#C084FC',  // 淡香芋紫 (冷)
    '#FBBF24',  // 暖亮金 (暖)
];

// 向后兼容旧名称
const CATEGORY_PALETTE = DYNAMIC_PALETTE;

// 3. 基于语义字典与动态分配生成稳定的 { 分类名: 颜色 } 字典
function buildCategoryColorMap(allCategories) {
    const colorMap = {};
    let dynamicIdx = 0;

    (allCategories || []).forEach(cat => {
        if (!cat) return;
        const name = String(cat).trim();

        // 优先完全匹配预设语义字典
        if (SEMANTIC_CATEGORY_MAP[name]) {
            colorMap[cat] = SEMANTIC_CATEGORY_MAP[name];
            return;
        }

        // 模糊匹配前缀或常见关键词
        if (name.startsWith('饮食*')) {
            colorMap[cat] = SEMANTIC_CATEGORY_MAP['饮食*'];
            return;
        } else if (name.startsWith('饮食') || name.includes('餐饮') || name.includes('外卖')) {
            colorMap[cat] = SEMANTIC_CATEGORY_MAP['饮食'];
            return;
        } else if (name.includes('交通') || name.includes('地铁') || name.includes('打车') || name.includes('公交')) {
            colorMap[cat] = SEMANTIC_CATEGORY_MAP['交通'];
            return;
        } else if (name.includes('居住') || name.includes('房租') || name.includes('物业') || name.includes('水电')) {
            colorMap[cat] = SEMANTIC_CATEGORY_MAP['居住'];
            return;
        } else if (name.includes('花呗') || name.includes('信用卡') || name.includes('还款')) {
            colorMap[cat] = SEMANTIC_CATEGORY_MAP['花呗'];
            return;
        } else if (name.includes('日用') || name.includes('超市') || name.includes('百货')) {
            colorMap[cat] = SEMANTIC_CATEGORY_MAP['日用'];
            return;
        } else if (name.includes('娱乐') || name.includes('电影') || name.includes('游戏')) {
            colorMap[cat] = SEMANTIC_CATEGORY_MAP['娱乐'];
            return;
        } else if (name.includes('数字') || name.includes('数码') || name.includes('软件')) {
            colorMap[cat] = SEMANTIC_CATEGORY_MAP['数字'];
            return;
        } else if (name.includes('周边') || name.includes('潮玩')) {
            colorMap[cat] = SEMANTIC_CATEGORY_MAP['周边'];
            return;
        }

        // 未命中语义规则的长尾动态分类，使用冷暖交替跳跃调色板
        colorMap[cat] = DYNAMIC_PALETTE[dynamicIdx % DYNAMIC_PALETTE.length];
        dynamicIdx++;
    });

    return colorMap;
}

document.addEventListener('DOMContentLoaded', async () => {
    // 按月份隔离的缓存文件：优先读取当前选中的月份（如 expense_data_2026-09.json）
    const savedYm = localStorage.getItem('selected_year_month');
    let dataFile = 'expense_data.json';
    if (savedYm) {
        dataFile = `expense_data_${savedYm}.json`;
        // 读取前先触发一次该月份的重新核算，确保在管理页增删改后数据仍然最新
        try {
            const [y, m] = savedYm.split('-');
            const budget = getCurrentBudget();
            await fetch(`/api/refresh_analysis?year=${encodeURIComponent(y)}&month=${encodeURIComponent(m)}&monthly_budget=${budget}`, { method: 'POST' });
        } catch (err) {
            console.warn('月度缓存预刷新失败，尝试直接读取已有文件:', err);
        }
    }
    fetch(dataFile)
        .then(response => {
            if (!response.ok) {
                throw new Error('无法读取 expense_data.json，请确认文件路径是否正确。');
            }
            return response.json();
        })
        .then(data => {
            // 提取所有分类并建立固定的映射表
            const categories = data.daily_trend ? data.daily_trend.categories : [];
            const colorMap = buildCategoryColorMap(categories);
            window._lastExpenseData = data;
            window._lastColorMap = colorMap;
            renderKpiCards(data);
            renderBarLineChart(data, colorMap);
            renderDonutChart(data, colorMap);
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
function renderBarLineChart(data, colorMap) {
    const chartDom = document.getElementById('barLineChart');
    if (!chartDom) return;
    const chart = echarts.init(chartDom);
    const dates = data.daily_trend.dates;
    const categories = data.daily_trend.categories;
    const pivot = data.daily_trend.pivot_data;
    const safeBaseline = data.budget.safe_daily_baseline;

    // ---------------- 累计消费进度（背景曲线，含房租口径） ----------------
    const CUM_SERIES_NAME = '累计消费进度';
    const LEGEND_TOTAL_NAME = '每日净支出走势';
    const PCT_AXIS_MAX = 100;   // 右轴顶端固定 100%，超出部分交给 clip 裁掉

    const monthlyBudget = Number((data.budget || {}).monthly_budget)
        || Number(getCurrentBudget()) || 0;
    const netExpenses = data.daily_trend.net_expenses || [];
    const dailyRent = data.daily_trend.daily_rent || [];   // 后端新增字段，缺失按 0 兜底
    const legendItems = [...categories, LEGEND_TOTAL_NAME];

    const firstYm = dates.length ? String(dates[0]).slice(0, 7) : '';
    const [selYear, selMonth] = firstYm ? firstYm.split('-').map(Number) : [0, 0];
    const today = new Date();
    const isCurrentMonth = selYear === today.getFullYear()
        && selMonth === today.getMonth() + 1;
    const cutoffDay = isCurrentMonth ? today.getDate() : 31;

    // 逐日累计：跨月时按月份分段重新累计（兼容"全部"模式的跨月数据）
    let accAmount = 0;
    let accMonth = '';
    const cumData = dates.map((d, i) => {
        const monthKey = String(d).slice(0, 7);
        if (monthKey !== accMonth) { accAmount = 0; accMonth = monthKey; }
        if (isCurrentMonth && Number(String(d).slice(8, 10)) > cutoffDay) return null;
        accAmount += (Number(netExpenses[i]) || 0) + (Number(dailyRent[i]) || 0);
        if (!(monthlyBudget > 0)) return null;
        const real = Number((accAmount / monthlyBudget * 100).toFixed(2));
        return {
            // 画出来的值钳在 100：超出预算的那一段不再画到网格外，而是贴着顶边，
            // 避免只留下被裁剪的碎片；真实百分比留在 real 里给 tooltip / 角标
            value: Math.min(real, PCT_AXIS_MAX),
            real: real,
            money: Number(accAmount.toFixed(2))                           // tooltip / 角标金额
        };
    });

    const cumLast = cumData.filter(Boolean).slice(-1)[0] || null;
    const cumOverBudget = !!(cumLast && cumLast.real > PCT_AXIS_MAX);

    // 窄屏（手机/单栏）顶部已被标题、图例占满，角标改到底部并加浅色底
    const narrowChart = chartDom.clientWidth < 520;

    // 常驻角标（仅宽屏）：曲线被裁剪后，进度数值依然可读
    const cumBadge = (cumLast && monthlyBudget > 0 && !narrowChart) ? {
        type: 'text',
        silent: true,
        z: 20,
        right: 8,
        top: 108,
        style: {
            text: '累计 ' + cumLast.real.toFixed(1) + '%   ¥' + cumLast.money.toFixed(0)
                + ' / ¥' + monthlyBudget.toFixed(0)
                + (cumOverBudget ? '   ▲ 已超预算' : ''),
            fill: cumOverBudget ? '#EF4444' : '#635BFF',
            font: 'bold 12px sans-serif',
            backgroundColor: (document.documentElement.getAttribute('data-theme') === 'dark') ? 'rgba(17,24,39,0.92)' : 'rgba(255,255,255,0.88)',
            padding: [2, 4]
        }
    } : null;

    // ---------------- 图例两态交互（全显态单击=隔离，其余=逐项切换） ----------------
    function makeAllSelected() {
        const map = {};
        legendItems.forEach(n => { map[n] = true; });
        return map;
    }

    function allCategoriesVisible(sel) {
        return categories.every(c => sel[c] !== false);
    }

    let legendSelected = makeAllSelected();   // 我们自己维护的"上一次已应用"状态
    let legendGuard = false;                  // 程序化 setOption 时的防递归哨兵

    function applyLegendSelected(sel) {
        legendSelected = sel;
        legendGuard = true;
        chart.setOption({ legend: { selected: sel } });
        legendGuard = false;
    }

    const seriesList = categories.map(cat => ({
        name: cat,
        type: 'bar',
        stack: '支出构成',
        emphasis: { focus: 'series' },
        itemStyle: {
            color: colorMap[cat] || '#94a3b8'  // 使用统一色彩
        },
        data: pivot[cat]
    }));

    seriesList.push({
        name: '每日净支出走势',
        type: 'line',
        data: data.daily_trend.net_expenses,
        lineStyle: { color: '#EF4444', width: 3 },
        itemStyle: { color: '#EF4444' },
        markLine: {
            data: [{
                yAxis: safeBaseline,
                name: '建议日均线',
                lineStyle: { color: '#10B981', type: 'dashed', width: 2 },
                label: { formatter: '安全基准: ¥' + safeBaseline.toFixed(1) }
            }]
        }
    });

    // 背景累计消费进度曲线：挂右轴（百分比），不参与左轴金额自适应
    if (monthlyBudget > 0) {
        // 房租入账日标注：解释"柱子没涨、曲线却跳"；>100% 的点不标（会被裁掉）
        const rentPoints = cumData
            .map((v, i) => ({ v, i }))
            .filter(o => o.v && o.v.value <= PCT_AXIS_MAX && (Number(dailyRent[o.i]) || 0) > 0)
            .map(o => ({
                name: '房租',
                coord: [dates[o.i], o.v.value],
                value: Number(dailyRent[o.i]),
                label: {
                    show: true,
                    fontSize: 10,
                    color: '#fff',
                    formatter: '房租 ¥' + Number(dailyRent[o.i]).toFixed(0)
                }
            }));

        seriesList.push({
            name: CUM_SERIES_NAME,
            type: 'line',
            yAxisIndex: 1,      // 必须挂右轴，挂左轴会把金额轴顶到累计值
            z: 1,               // 压在柱状图（默认 z=2）之下
            clip: true,         // 超出网格（>100%）的部分自动隐藏
            smooth: false,
            symbol: 'circle',
            symbolSize: 5,
            showSymbol: true,
            connectNulls: false,
            data: cumData,
            lineStyle: { color: 'rgba(96,165,250,0.95)', width: 2 },
            itemStyle: { color: '#60a5fa' },
            areaStyle: {
                color: {
                    type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
                    colorStops: [
                        { offset: 0, color: 'rgba(96,165,250,0.16)' },
                        { offset: 1, color: 'rgba(96,165,250,0.01)' }
                    ]
                }
            },
            markPoint: {
                symbol: 'pin',
                symbolSize: 30,
                z: 6,
                itemStyle: { color: '#f59e0b' },
                data: rentPoints
            }
        });
    }

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
                // 宽屏图例允许换行（分类多时一行放不下会翻页，把"每日净支出走势"挤到第 2 页）
                top: 90,
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

    // 右轴只在预算有效时出现：预算为 0 时退化成原来的单轴图，避免留一条空百分比轴
    const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    const yAxisList = [{
        // 左轴：保持自适应，只服务堆叠柱与每日净支出线的金额刻度
        type: 'value',
        name: '金额 (元)',
        nameGap: 14,
        nameTextStyle: {
            align: 'center',
            padding: [0, 6, 0, 0],
            color: isDark ? '#94A3B8' : '#64748B'
        },
        axisLabel: {
            color: isDark ? '#94A3B8' : '#64748B'
        },
        splitLine: {
            lineStyle: {
                color: isDark ? '#1F2937' : '#E2E8F0'
            }
        }
    }];
    if (monthlyBudget > 0) {
        yAxisList.push({
            // 右轴：累计消费进度百分比（与左轴金额刻度各自独立）
            type: 'value',
            name: '',
            min: 0,
            max: PCT_AXIS_MAX,
            splitNumber: 5,
            axisLabel: {
                formatter: '{value}%',
                color: isDark ? '#94A3B8' : '#64748B'
            },
            splitLine: { show: false },
            axisLine: { show: false },
            axisTick: { show: false },
            nameTextStyle: { align: 'center' }
        });
    }

    // 窄屏顶部空间紧张：进度写进副标题，不再画浮层角标（否则会压住横轴日期）
    const narrowSubtext = '预算 ¥' + monthlyBudget.toFixed(0)
        + (cumLast ? ' ｜ 累计 ' + cumLast.real.toFixed(1) + '%' : '')
        + (cumOverBudget ? ' ▲超' : '');

    chart.setOption({
        title: {
            text: '逐日日常支出分类构成与净支出走势',
            subtext: narrowChart ? narrowSubtext : '鼠标悬停可查看每日分类明细与走势',
            left: 'center',
            top: 6,
            textStyle: {
                color: isDark ? '#F8FAFC' : '#0F172A',
                fontSize: 14,
                fontWeight: 600
            },
            subtextStyle: {
                color: isDark ? '#64748B' : '#94A3B8',
                fontSize: 12
            }
        },
        tooltip: {
            trigger: 'axis',
            axisPointer: { type: 'cross' },
            formatter: function (params) {
                const rows = Array.isArray(params) ? params : [params];
                if (!rows.length) return '';
                const out = ['<b>' + rows[0].axisValue + '</b>'];
                let catSum = 0;
                rows.forEach(p => {
                    const v = p.value;
                    const raw = (v && typeof v === 'object') ? v.value : v;
                    if (raw == null || raw === '') return;
                    const marker = p.marker || '';
                    if (p.seriesName === CUM_SERIES_NAME) {
                        // ECharts 会把 {value, money} 解析成标量传给 params.value，
                        // 所以金额必须回查 cumData，不能从 params 上取
                        const item = cumData[p.dataIndex];
                        const money = item ? item.money : null;
                        const realPct = item && item.real != null ? item.real : Number(raw);
                        const rent = Number(dailyRent[p.dataIndex]) || 0;
                        out.push(marker + p.seriesName + '：<b>' + realPct.toFixed(1) + '%</b>'
                            + (money == null ? '' : ' <span style="color:#94a3b8">(¥'
                                + money.toFixed(2) + ' / ¥' + monthlyBudget.toFixed(0) + ')</span>')
                            + (rent > 0 ? ' <span style="color:#f59e0b">含房租 ¥' + rent.toFixed(0) + '</span>' : ''));
                    } else if (p.seriesName === LEGEND_TOTAL_NAME) {
                        out.push(marker + p.seriesName + '：<b>¥' + Number(raw).toFixed(2) + '</b>');
                    } else {
                        catSum += Number(raw) || 0;
                        out.push(marker + p.seriesName + '：¥' + Number(raw).toFixed(2));
                    }
                });
                if (catSum > 0) {
                    out.push('<span style="color:#64748b">分类合计：¥' + catSum.toFixed(2) + '</span>');
                }
                return out.join('<br/>');
            }
        },
        legend: {
            top: 50,
            type: 'scroll',
            left: '12%',
            right: '12%',
            data: legendItems,
            selected: makeAllSelected(),
            selectedMode: true,
            textStyle: {
                color: isDark ? '#94A3B8' : '#64748B'
            }
        },
        xAxis: {
            type: 'category',
            data: dates,
            axisLabel: {
                rotate: 35,
                color: (document.documentElement.getAttribute('data-theme') === 'dark') ? '#94A3B8' : '#64748B'
            },
            axisLine: {
                lineStyle: { color: (document.documentElement.getAttribute('data-theme') === 'dark') ? '#374151' : '#E2E8F0' }
            }
        },
        yAxis: yAxisList,
        graphic: { elements: cumBadge ? [cumBadge] : [] },
        series: seriesList
    });

    // 图例两态交互：
    //   全显态单击分类 → 隔离（只剩该类 + 净支出线）
    //   隔离态（只剩一个分类可见）单击该类 → 回到全显态
    //   其余情况 → 沿用 ECharts 默认逐项切换（叠加）
    chart.off('legendselectchanged');
    chart.on('legendselectchanged', function (params) {
        if (legendGuard) return;

        const name = params.name;
        const next = Object.assign({}, params.selected);   // 点击后的完整选中表
        const isCategory = categories.indexOf(name) !== -1;

        // 全显态单击分类 → 隔离
        if (allCategoriesVisible(legendSelected) && isCategory && next[name] === false) {
            const isolated = {};
            categories.forEach(c => { isolated[c] = (c === name); });
            isolated[LEGEND_TOTAL_NAME] = true;            // 总支出线强制保留
            applyLegendSelected(isolated);
            return;
        }

        // 只剩这一个分类可见时再单击它 → 全部恢复
        const visibleCategories = categories.filter(c => next[c] !== false);
        if (isCategory && next[name] === false && visibleCategories.length === 0) {
            applyLegendSelected(makeAllSelected());
            return;
        }

        applyLegendSelected(next);
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
function renderDonutChart(data, colorMap) {
    const chartDom = document.getElementById('nestedDonutChart');
    if (!chartDom) return;
    const chart = echarts.init(chartDom);
    const isDark = document.documentElement.getAttribute('data-theme') === 'dark';

    // 1. 内环数据：深邃藏青黑(刚性) vs 清爽海天蓝(弹性)，解耦外环分类
    const innerData = (data.donut_chart.inner || []).map(item => ({
        ...item,
        itemStyle: {
            color: item.name.includes('刚性') ? (isDark ? '#334155' : '#1E293B') : '#0284c7',
            borderColor: isDark ? '#111827' : '#ffffff',
            borderWidth: 2
        }
    }));

    // 2. 外环数据：按 item.name (即分类名) 精确匹配左图的分类颜色
    const outerData = (data.donut_chart.outer || []).map(item => ({
        ...item,
        itemStyle: {
            color: colorMap[item.name] || '#cbd5e1',
            borderColor: isDark ? '#111827' : '#ffffff',
            borderWidth: 1.5
        }
    }));

    chart.setOption({
        title: {
            text: '常规刚性 vs 弹性支出构成双环图',
            subtext: '鼠标悬停图块即时显示金额与占比信息',
            left: 'center',
            textStyle: {
                color: isDark ? '#F8FAFC' : '#0F172A',
                fontSize: 14,
                fontWeight: 600
            },
            subtextStyle: {
                color: isDark ? '#64748B' : '#94A3B8',
                fontSize: 12
            }
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
            textStyle: {
                fontSize: 11,
                color: isDark ? '#94A3B8' : '#64748B'
            }
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
                    borderColor: isDark ? '#111827' : '#ffffff',
                    borderWidth: 2
                },
                label: {
                    position: 'inner',
                    show: true,
                    formatter: '{name|{b}}\n{percent|{d}%}',
                    rich: {
                        name: {
                            fontSize: 11,
                            fontWeight: 500,
                            color: '#FFFFFF',
                            lineHeight: 16,
                            align: 'center',
                            textShadowColor: 'rgba(0, 0, 0, 0.45)',
                            textShadowBlur: 2
                        },
                        percent: {
                            fontSize: 14,
                            fontWeight: 700,
                            color: '#FFFFFF',
                            lineHeight: 18,
                            align: 'center',
                            textShadowColor: 'rgba(0, 0, 0, 0.45)',
                            textShadowBlur: 2
                        }
                    }
                },
                labelLine: { show: false },
                data: innerData
            },
            // 外环：微缝贴合
            {
                name: '详细分类',
                type: 'pie',
                radius: ['50%', '68%'],
                center: ['50%', '50%'],
                itemStyle: {
                    borderRadius: 3,
                    borderColor: isDark ? '#111827' : '#ffffff',
                    borderWidth: 1.5
                },
                avoidLabelOverlap: true,
                labelLayout: {
                    hideOverlap: false,
                    moveOverlap: 'shiftY'
                },
                label: {
                    formatter: '{b}: ¥{c} ({d}%)',
                    fontSize: 10.5,
                    color: isDark ? '#F8FAFC' : '#1E293B',
                    textBorderColor: isDark ? '#111827' : '#FFFFFF',
                    textBorderWidth: isDark ? 3 : 2
                },
                labelLine: {
                    length: 10,
                    length2: 12,
                    lineStyle: {
                        color: isDark ? '#64748B' : '#94A3B8'
                    }
                },
                data: outerData
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

// 计算当前所选月份的起止日期（如 2026-09 -> 2026-09-01 ~ 2026-09-30）
function getSelectedMonthRange() {
    const monthSelector = document.getElementById('month-selector');
    const ym = (monthSelector && monthSelector.value) ? monthSelector.value : (localStorage.getItem('selected_year_month') || '');
    if (!ym) return null;
    const parts = ym.split('-');
    const y = parseInt(parts[0], 10);
    const m = parseInt(parts[1], 10);
    if (!y || !m) return null;
    const pad = (n) => String(n).padStart(2, '0');
    const lastDay = new Date(y, m, 0).getDate(); // 当月最后一天（自动处理大小月与闰年）
    return { start_date: `${y}-${pad(m)}-01`, end_date: `${y}-${pad(m)}-${pad(lastDay)}` };
}

// 通用跳转至管理后台并携带筛选参数
function jumpToManager(filters = {}) {
    // 未指定任何日期约束时，自动附带当前所选月份的起止日期
    // （金额堆叠图点击会传入具体 date，本身已带日期信息，无需附加）
    if (!filters.date && !filters.start_date && !filters.end_date) {
        const range = getSelectedMonthRange();
        if (range) {
            filters = { ...range, ...filters };
        }
    }

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
        // 携带当前选中的月份，让后端读取对应月份的隔离缓存文件
        const monthSelector = document.getElementById('month-selector');
        const ym = monthSelector ? monthSelector.value : '';
        const query = ym ? `?year_month=${encodeURIComponent(ym)}` : '';
        const res = await fetch(`/api/ai/diagnose${query}`);
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
    
    const savedYm = localStorage.getItem('selected_year_month') || (months.length > 0 ? months[0] : '2026-09');
    if (months.length > 0) {
        selector.innerHTML = months.map(m => `<option value="${m}" ${m === savedYm ? 'selected' : ''}>${m}</option>`).join('');
    } else {
        selector.innerHTML = `<option value="2026-09">2026-09</option>`;
    }
}

// 切换月份触发重新计算并刷新图表
async function changeMonth(selectedYm) {
    localStorage.setItem('selected_year_month', selectedYm);
    const [y, m] = selectedYm.split('-');
    await fetch(`/api/refresh_analysis?year=${encodeURIComponent(y)}&month=${encodeURIComponent(m)}&monthly_budget=${getCurrentBudget()}`, { method: 'POST' });
    // 重新拉取按月份隔离的缓存文件渲染 ECharts
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
    if (ym) {
        localStorage.setItem('selected_year_month', ym);
    }

    const params = new URLSearchParams();
    if (ym) {
        const [y, m] = ym.split('-');
        params.append('year', y);
        params.append('month', m);
    }
    params.append('monthly_budget', budget);

    await fetch(`/api/refresh_analysis?${params.toString()}`, { method: 'POST' });

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

// 监听全局主题切换事件，无刷新重新渲染图表适配深色/浅色
window.addEventListener('themechange', () => {
    if (window._lastExpenseData && window._lastColorMap) {
        renderBarLineChart(window._lastExpenseData, window._lastColorMap);
        renderDonutChart(window._lastExpenseData, window._lastColorMap);
        renderWordCloud(window._lastExpenseData);
    }
});
