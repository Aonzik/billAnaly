// static/manager.js
// BillAnaly - 记账管理交互逻辑脚本 (Fintech 极简浅色优化版)

function cleanAccountCode(val) {
    if (!val) return '';
    const m = val.match(/（([A-Za-z0-9]+)）|\(([A-Za-z0-9]+)\)/);
    return m ? (m[1] || m[2]) : val.trim();
}

const TYPE_MAP = {
    'EX': '支出 EX',
    'IN': '收入 IN',
    'AP': '收回 AP',
    'AR': '垫付 AR',
    'TR': '转移 TR'
};

const ACC_MAP = {
    'AL': '支付宝（AL）',
    'VX': '微信（VX）',
    'BK': '银行卡（BK）',
    'TC': '交通卡（TC）',
    'HB': '花呗（HB）'
};

// 格式化金额显示 (带千分位与两位小数)
function formatMoney(num) {
    return '¥' + Number(num || 0).toLocaleString('zh-CN', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    });
}

// 快捷时间胶囊交互
function setQuickPeriod(type) {
    const startInput = document.getElementById('filter-start');
    const endInput = document.getElementById('filter-end');
    if (!startInput || !endInput) return;

    // 清空所有 pill 激活状态
    document.querySelectorAll('.pill-btn').forEach(btn => btn.classList.remove('active'));

    const now = new Date();
    const y = now.getFullYear();
    const m = now.getMonth(); // 0-based
    const d = now.getDate();

    const pad = n => String(n).padStart(2, '0');
    const fmt = date => `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;

    if (type === 'all') {
        startInput.value = '';
        endInput.value = '';
        const pill = document.getElementById('pill-all');
        if (pill) pill.classList.add('active');
    } else if (type === 'this_month') {
        const firstDay = new Date(y, m, 1);
        const lastDay = new Date(y, m + 1, 0);
        startInput.value = fmt(firstDay);
        endInput.value = fmt(lastDay);
        const pill = document.getElementById('pill-this-month');
        if (pill) pill.classList.add('active');
    } else if (type === 'last_month') {
        const firstDay = new Date(y, m - 1, 1);
        const lastDay = new Date(y, m, 0);
        startInput.value = fmt(firstDay);
        endInput.value = fmt(lastDay);
        const pill = document.getElementById('pill-last-month');
        if (pill) pill.classList.add('active');
    } else if (type === '7d') {
        const past = new Date(now.getTime() - 6 * 24 * 60 * 60 * 1000);
        startInput.value = fmt(past);
        endInput.value = fmt(now);
        const pill = document.getElementById('pill-7d');
        if (pill) pill.classList.add('active');
    } else if (type === '30d') {
        const past = new Date(now.getTime() - 29 * 24 * 60 * 60 * 1000);
        startInput.value = fmt(past);
        endInput.value = fmt(now);
        const pill = document.getElementById('pill-30d');
        if (pill) pill.classList.add('active');
    } else if (type === 'this_year') {
        const firstDay = new Date(y, 0, 1);
        const lastDay = new Date(y, 11, 31);
        startInput.value = fmt(firstDay);
        endInput.value = fmt(lastDay);
        const pill = document.getElementById('pill-year');
        if (pill) pill.classList.add('active');
    }

    // 触发数据重载
    loadData();
}

// 点击表头快捷翻转排序
function toggleSort() {
    const sortSelect = document.getElementById('sort-order');
    sortSelect.value = (sortSelect.value === 'desc') ? 'asc' : 'desc';
    loadData();
}

// 核心数据拉取、筛选与实时动态汇总
// ===== 数据权限控制（可读可写 / 只读 / 不可读不可写） =====
// admin 恒为可读可写；普通账号由后端 /api/auth/me 返回 can_read / can_write
window.BILL_CAN_WRITE = true;
window.BILL_CURRENT_USER = null;

function ensureWritable() {
    if (window.BILL_CAN_WRITE) return true;
    alert('当前账号为只读权限，不能新增 / 修改 / 删除账单数据。如需写入权限，请联系管理员开通。');
    return false;
}

async function initPermission() {
    try {
        const res = await fetch('/api/auth/me', { credentials: 'same-origin' });
        if (res.ok) {
            const me = await res.json();
            window.BILL_CURRENT_USER = me;
            window.BILL_CAN_WRITE = me.role === 'admin' || me.can_write === true;
        }
    } catch (e) { /* 网络异常时保持默认可写，后端 403 兜底 */ }
    applyPermissionUI();
}

function applyPermissionUI() {
    const canWrite = window.BILL_CAN_WRITE;
    document.body.classList.toggle('read-only-mode', !canWrite);

    const entryCard = document.getElementById('entry-form-card');
    if (entryCard) entryCard.style.display = canWrite ? '' : 'none';

    const banner = document.getElementById('readonly-banner');
    if (banner) banner.style.display = canWrite ? 'none' : 'flex';

    if (!canWrite) {
        // 移除表格中的行内编辑与删除入口，避免误点
        document.querySelectorAll('#table-body .editable-cell').forEach(el => {
            el.removeAttribute('onclick');
            el.removeAttribute('title');
            el.classList.add('readonly-cell');
        });
        document.querySelectorAll('#table-body .btn-action-del').forEach(btn => {
            const td = btn.closest('td');
            if (td) td.remove();
        });
        document.querySelectorAll('.col-action').forEach(el => { el.style.display = 'none'; });
    }
}

async function loadData() {
    const start = document.getElementById('filter-start').value;
    const end = document.getElementById('filter-end').value;
    const cat = document.getElementById('filter-category').value.trim();
    const exact = document.getElementById('filter-exact').checked;
    const acc = document.getElementById('filter-account').value;
    const sortOrder = document.getElementById('sort-order').value;

    const name = document.getElementById('filter-name').value.trim();
    const type = document.getElementById('filter-type').value;
    const merchant = document.getElementById('filter-merchant').value.trim();
    const minAmount = document.getElementById('filter-min-amount').value.trim();
    const maxAmount = document.getElementById('filter-max-amount').value.trim();

    const indicator = document.getElementById('sort-indicator');
    if (indicator) {
        indicator.innerText = (sortOrder === 'desc') ? '↓' : '↑';
    }

    const params = new URLSearchParams();
    if (start) params.append('start_date', start);
    if (end) params.append('end_date', end);
    if (cat) {
        params.append('category', cat);
        params.append('exact_category', exact);
    }
    if (acc) params.append('pay_acc', acc);
    params.append('sort_order', sortOrder);

    if (name) params.append('name', name);
    if (type) params.append('trans_type', type);
    if (merchant) params.append('merchant', merchant);
    if (minAmount !== '') params.append('min_amount', minAmount);
    if (maxAmount !== '') params.append('max_amount', maxAmount);

    try {
        const res = await fetch(`/api/db/expenses?${params.toString()}`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();

        // 1. 统计当前筛选结果的指标小计
        let totalExpense = 0;
        let totalIncome = 0;

        data.forEach(item => {
            const amt = Number(item.实际金额) || 0;
            const t = item.交易类型;
            if (t === 'EX') {
                totalExpense += amt;
            } else if (t === 'AR') {
                totalExpense += amt; // 垫付算作当期现金流出
            } else if (t === 'AP') {
                totalExpense -= amt; // 垫付收回冲减支出
            } else if (t === 'IN') {
                totalIncome += amt;
            }
        });

        const netGrowth = totalIncome - totalExpense;

        // 更新 Summary KPI Bar 动态统计条
        const sumCountElem = document.getElementById('sum-count');
        const sumExpenseElem = document.getElementById('sum-expense');
        const sumIncomeElem = document.getElementById('sum-income');
        const sumNetElem = document.getElementById('sum-net');
        const totalCountElem = document.getElementById('total-count');

        if (sumCountElem) sumCountElem.innerText = `${data.length} 笔`;
        if (totalCountElem) totalCountElem.innerText = data.length;
        if (sumExpenseElem) sumExpenseElem.innerText = formatMoney(totalExpense);
        if (sumIncomeElem) sumIncomeElem.innerText = formatMoney(totalIncome);

        if (sumNetElem) {
            if (netGrowth >= 0) {
                sumNetElem.innerText = `+${formatMoney(netGrowth)}`;
                sumNetElem.style.color = 'var(--color-success)';
            } else {
                sumNetElem.innerText = `-${formatMoney(Math.abs(netGrowth))}`;
                sumNetElem.style.color = 'var(--color-danger)';
            }
        }

        // 2. 渲染流水表格
        const tbody = document.getElementById('table-body');
        if (data.length === 0) {
            tbody.innerHTML = '<tr><td colspan="11" style="text-align:center;color:var(--color-text-tertiary);padding:36px;">未查找到匹配条件的账单记录</td></tr>';
            return;
        }

        tbody.innerHTML = data.map(item => {
            const typeDisplay = TYPE_MAP[item.交易类型] || item.交易类型;
            const accDisplay = ACC_MAP[item.支付账户] || item.支付账户 || '-';
            const tarDisplay = ACC_MAP[item.目标账户] || item.目标账户 || '-';
            const itemId = item.id;
            const amt = Number(item.实际金额 || 0);

            // 金额符号与着色
            let amtStr = '';
            let amtClass = 'amount-neutral';
            if (item.交易类型 === 'EX') {
                amtStr = `-¥${amt.toFixed(2)}`;
                amtClass = 'amount-expense';
            } else if (item.交易类型 === 'IN') {
                amtStr = `+¥${amt.toFixed(2)}`;
                amtClass = 'amount-income';
            } else if (item.交易类型 === 'AP') {
                amtStr = `¥${amt.toFixed(2)}`;
                amtClass = 'amount-income';
            } else {
                amtStr = `¥${amt.toFixed(2)}`;
                amtClass = 'amount-neutral';
            }

            return `
                <tr id="row-${itemId}">
                    <td style="color:var(--color-text-tertiary); font-weight:600; font-variant-numeric:tabular-nums;">#${itemId}</td>
                    <td class="editable-cell" data-field="日期" onclick="inlineEdit(this, ${itemId})" title="点击编辑日期">${item.日期}</td>
                    <td class="editable-cell" data-field="时间" onclick="inlineEdit(this, ${itemId})" style="color:var(--color-text-tertiary);">${item.时间 || '-'}</td>
                    <td class="editable-cell" data-field="交易类型" data-raw="${item.交易类型}" onclick="inlineEditType(this, ${itemId})" title="点击切换类型">
                        <span class="badge-type type-${item.交易类型}">${typeDisplay}</span>
                    </td>
                    <td class="editable-cell" data-field="分类" onclick="inlineEdit(this, ${itemId})">
                        <span style="font-weight:600; color:var(--color-text-primary);">${item.分类}</span>
                    </td>
                    <td class="editable-cell" data-field="品名" onclick="inlineEdit(this, ${itemId})">
                        <span style="color:var(--color-text-primary);">${item.品名}</span>
                    </td>
                    <td class="editable-cell amount-cell ${amtClass}" data-field="实际金额" onclick="inlineEdit(this, ${itemId})" style="text-align: right;" title="点击修改金额">
                        ${amtStr}
                    </td>
                    <td class="editable-cell" data-field="支付账户" onclick="inlineEdit(this, ${itemId})" style="color:var(--color-text-secondary);">${accDisplay}</td>
                    <td class="editable-cell" data-field="目标账户" onclick="inlineEdit(this, ${itemId})" style="color:var(--color-text-secondary);">${tarDisplay}</td>
                    <td class="editable-cell" data-field="备注" onclick="inlineEdit(this, ${itemId})" style="color:var(--color-text-tertiary);">${item.备注 || '-'}</td>
                    <td style="text-align: center;">
                        <button class="btn-action-del" onclick="deleteItem(${itemId})" title="删除此条流水">🗑️ 删除</button>
                    </td>
                </tr>
            `;
        }).join('');

        // 只读账号：渲染后立即移除行内编辑 / 删除入口
        if (!window.BILL_CAN_WRITE) applyPermissionUI();
    } catch (err) {
        console.error("加载数据失败:", err);
    }
}

// 自动读取 URL 中的过滤参数并填入对应筛选框
function applyUrlFilterParams() {
    const urlParams = new URLSearchParams(window.location.search);
    let hasFilter = false;

    const startInput = document.getElementById('filter-start');
    const endInput = document.getElementById('filter-end');
    const dateVal = urlParams.get('date');
    const startVal = urlParams.get('start_date');
    const endVal = urlParams.get('end_date');
    if (dateVal) {
        if (startInput) startInput.value = dateVal;
        if (endInput) endInput.value = dateVal;
        hasFilter = true;
    } else {
        if (startVal && startInput) {
            startInput.value = startVal;
            hasFilter = true;
        }
        if (endVal && endInput) {
            endInput.value = endVal;
            hasFilter = true;
        }
    }

    const catVal = urlParams.get('category');
    if (catVal) {
        const catSelect = document.getElementById('filter-category');
        if (catSelect) {
            catSelect.value = catVal;
            hasFilter = true;
        }
        const exactCheck = document.getElementById('filter-exact');
        if (exactCheck) {
            exactCheck.checked = true;
        }
    }

    const merchantVal = urlParams.get('merchant');
    if (merchantVal) {
        const merchantInput = document.getElementById('filter-merchant');
        if (merchantInput) {
            merchantInput.value = merchantVal;
            hasFilter = true;
        }
    }

    const keywordVal = urlParams.get('keyword');
    if (keywordVal) {
        const nameInput = document.getElementById('filter-name');
        if (nameInput) {
            nameInput.value = keywordVal;
            hasFilter = true;
        }
    }

    return hasFilter;
}

// 行内直接修改
function inlineEdit(cell, id) {
    if (!ensureWritable()) return;
    if (!id || id === 'null' || id === 'undefined') {
        alert("无效数据ID，请刷新页面后重试");
        return;
    }
    if (cell.querySelector('input')) return;

    const field = cell.getAttribute('data-field');
    const oldText = cell.innerText.replace(/^[+-¥\s]+/, '').trim(); // 提取纯净数值
    const input = document.createElement('input');
    input.className = 'cell-input';
    input.value = (field === '实际金额') ? oldText : cell.innerText.trim();

    cell.innerHTML = '';
    cell.appendChild(input);
    input.focus();

    let isSaved = false;
    async function save() {
        if (isSaved) return;
        isSaved = true;

        let newVal = input.value.trim();
        if (field === '支付账户' || field === '目标账户') newVal = cleanAccountCode(newVal);
        if (field === '实际金额') newVal = parseFloat(newVal) || 0.0;

        if (newVal !== oldText) {
            await fetch(`/api/db/expenses/${id}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ [field]: newVal })
            });
            await fetch('/api/refresh_analysis', { method: 'POST' });
        }
        loadData();
    }

    input.addEventListener('blur', save);
    input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') save();
        if (e.key === 'Escape') { isSaved = true; loadData(); }
    });
}

// 交易类型下拉修改
function inlineEditType(cell, id) {
    if (!ensureWritable()) return;
    if (!id || id === 'null') return;
    if (cell.querySelector('select')) return;

    const currentVal = cell.getAttribute('data-raw') || 'EX';
    const select = document.createElement('select');
    select.className = 'cell-input';
    select.innerHTML = `
        <option value="EX" ${currentVal === 'EX' ? 'selected' : ''}>支出（EX）</option>
        <option value="IN" ${currentVal === 'IN' ? 'selected' : ''}>收入（IN）</option>
        <option value="AP" ${currentVal === 'AP' ? 'selected' : ''}>收回（AP）</option>
        <option value="AR" ${currentVal === 'AR' ? 'selected' : ''}>垫付（AR）</option>
        <option value="TR" ${currentVal === 'TR' ? 'selected' : ''}>转移（TR）</option>
    `;

    cell.innerHTML = '';
    cell.appendChild(select);
    select.focus();

    let isSaved = false;
    async function save() {
        if (isSaved) return;
        isSaved = true;
        const newVal = select.value;
        if (newVal !== currentVal) {
            await fetch(`/api/db/expenses/${id}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ '交易类型': newVal })
            });
            await fetch('/api/refresh_analysis', { method: 'POST' });
        }
        loadData();
    }

    select.addEventListener('blur', save);
    select.addEventListener('change', save);
}

// 提交新增表单
document.getElementById('expense-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    if (!ensureWritable()) return;
    const rawAcc = document.getElementById('pay_acc').value;

    const payload = {
        日期: document.getElementById('date').value,
        时间: document.getElementById('time').value.trim() || '12:00',
        交易类型: document.getElementById('type').value,
        分类: document.getElementById('category').value.trim(),
        品名: document.getElementById('name').value.trim(),
        实际金额: parseFloat(document.getElementById('amount').value),
        支付账户: cleanAccountCode(rawAcc),
        目标账户: document.getElementById('merchant').value.trim(),
        备注: document.getElementById('remark').value.trim()
    };

    const res = await fetch('/api/db/expenses', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    });

    if (res.ok) {
        document.getElementById('name').value = '';
        document.getElementById('amount').value = '';
        document.getElementById('merchant').value = '';
        document.getElementById('remark').value = '';
        await fetch('/api/refresh_analysis', { method: 'POST' });
        loadData();
    }
});

// 删除条目
async function deleteItem(id) {
    if (!ensureWritable()) return;
    if (!id || id === 'null') {
        alert("无效数据ID");
        return;
    }
    if (confirm(`确定删除编号为 #${id} 的消费记录吗？该操作将即时同步并重新核算月度缓存。`)) {
        await fetch(`/api/db/expenses/${id}`, { method: 'DELETE' });
        await fetch('/api/refresh_analysis', { method: 'POST' });
        loadData();
    }
}

// 重置筛选
function resetFilter() {
    if (window.event && window.event.preventDefault) {
        window.event.preventDefault();
    }

    const clearVal = (id, defaultVal = '') => {
        const el = document.getElementById(id);
        if (el) el.value = defaultVal;
    };
    const setChecked = (id, status = false) => {
        const el = document.getElementById(id);
        if (el) el.checked = status;
    };

    clearVal('filter-start');
    clearVal('filter-end');
    clearVal('filter-category');
    setChecked('filter-exact', false);
    clearVal('filter-account');
    clearVal('sort-order', 'desc');
    clearVal('filter-name');
    clearVal('filter-type');
    clearVal('filter-merchant');
    clearVal('filter-min-amount');
    clearVal('filter-max-amount');

    // 重置快捷时间胶囊高亮
    document.querySelectorAll('.pill-btn').forEach(btn => btn.classList.remove('active'));
    const allPill = document.getElementById('pill-all');
    if (allPill) allPill.classList.add('active');

    // 清除地址栏查询参数
    if (window.location.search) {
        window.history.replaceState({}, document.title, window.location.pathname);
    }

    loadData();
}

async function exportToExcel() {
    const start = document.getElementById('filter-start').value;
    const end = document.getElementById('filter-end').value;
    const cat = document.getElementById('filter-category').value.trim();
    const exact = document.getElementById('filter-exact').checked;
    const acc = document.getElementById('filter-account').value;
    const sortOrder = document.getElementById('sort-order').value;
    const name = document.getElementById('filter-name').value.trim();
    const type = document.getElementById('filter-type').value;
    const merchant = document.getElementById('filter-merchant').value.trim();
    const minAmount = document.getElementById('filter-min-amount').value.trim();
    const maxAmount = document.getElementById('filter-max-amount').value.trim();

    const params = new URLSearchParams();
    if (start) params.append('start_date', start);
    if (end) params.append('end_date', end);
    if (cat) {
        params.append('category', cat);
        params.append('exact_category', exact);
    }
    if (acc) params.append('pay_acc', acc);
    params.append('sort_order', sortOrder);
    if (name) params.append('name', name);
    if (type) params.append('trans_type', type);
    if (merchant) params.append('merchant', merchant);
    if (minAmount !== '') params.append('min_amount', minAmount);
    if (maxAmount !== '') params.append('max_amount', maxAmount);

    let defaultFileName = '账单流水明细';
    if (start && end) {
        defaultFileName += `_${start}至${end}`;
    } else if (start) {
        defaultFileName += `_${start}起`;
    } else if (cat) {
        defaultFileName += `_${cat}`;
    } else {
        const today = new Date().toISOString().split('T')[0];
        defaultFileName += `_${today}`;
    }
    defaultFileName += '.xlsx';

    try {
        const response = await fetch(`/api/db/export_excel?${params.toString()}`);
        if (!response.ok) throw new Error(`导出失败，状态码: ${response.status}`);
        const blob = await response.blob();

        if ('showSaveFilePicker' in window) {
            try {
                const handle = await window.showSaveFilePicker({
                    suggestedName: defaultFileName,
                    types: [{
                        description: 'Excel 工作簿 (*.xlsx)',
                        accept: {
                            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx']
                        }
                    }]
                });
                const writable = await handle.createWritable();
                await writable.write(blob);
                await writable.close();
                alert('✅ 账单已成功导出并保存！');
                return;
            } catch (pickerErr) {
                if (pickerErr.name === 'AbortError') return;
                console.warn('文件保存窗口取消或不支持，调用备选下载:', pickerErr);
            }
        }

        const customName = prompt('请输入要保存的 Excel 文件名：', defaultFileName);
        if (!customName) return;

        const finalName = customName.endsWith('.xlsx') ? customName : `${customName}.xlsx`;
        const blobUrl = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = blobUrl;
        a.download = finalName;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(blobUrl);

    } catch (err) {
        console.error('导出异常:', err);
        alert(`❌ 导出失败: ${err.message}`);
    }
}

// 初始化默认今日日期
document.getElementById('date').value = new Date().toISOString().split('T')[0];

document.addEventListener('DOMContentLoaded', async () => {
    // 0. 先取当前账号权限，决定是否展示录入 / 编辑入口
    await initPermission();

    // 1. 读取 URL 传递过来的跳转参数并回填到界面筛选框
    const hasFilter = applyUrlFilterParams();

    // 2. 如果没有特定 URL 过滤，默认 pill 处于“全部流水”状态
    if (!hasFilter) {
        const pill = document.getElementById('pill-all');
        if (pill) pill.classList.add('active');
    } else {
        document.querySelectorAll('.pill-btn').forEach(btn => btn.classList.remove('active'));
    }

    // 3. 执行加载流水数据
    loadData();
});
