// static/manager.js

function cleanAccountCode(val) {
    if (!val) return '';
    const m = val.match(/（([A-Za-z0-9]+)）|\(([A-Za-z0-9]+)\)/);
    return m ? (m[1] || m[2]) : val.trim();
}

const TYPE_MAP = {
    'EX': '支出（EX）',
    'IN': '收入（IN）',
    'AP': '收回（AP）',
    'AR': '垫付（AR）',
    'TR': '转移（TR）'
};

const ACC_MAP = {
    'AL': '支付宝（AL）',
    'VX': '微信（VX）',
    'BK': '银行卡（BK）',
    'TC': '交通卡（TC）',
    'HB': '花呗（HB）'
};

// 点击表头快捷翻转排序
function toggleSort() {
    const sortSelect = document.getElementById('sort-order');
    sortSelect.value = (sortSelect.value === 'desc') ? 'asc' : 'desc';
    loadData();
}

// 核心数据拉取与筛选
async function loadData() {
    const start = document.getElementById('filter-start').value;
    const end = document.getElementById('filter-end').value;
    const cat = document.getElementById('filter-category').value.trim();
    const exact = document.getElementById('filter-exact').checked;
    const acc = document.getElementById('filter-account').value;
    const sortOrder = document.getElementById('sort-order').value;

    // ======= 新增获取项 =======
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

    // ======= 附加新增参数 =======
    if (name) params.append('name', name);
    if (type) params.append('trans_type', type);
    if (merchant) params.append('merchant', merchant);
    if (minAmount !== '') params.append('min_amount', minAmount);
    if (maxAmount !== '') params.append('max_amount', maxAmount);

    try {
        const res = await fetch(`/api/db/expenses?${params.toString()}`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();

        document.getElementById('total-count').innerText = data.length;
        const tbody = document.getElementById('table-body');

        if (data.length === 0) {
            tbody.innerHTML = '<tr><td colspan="11" style="text-align:center;color:#94a3b8;padding:24px;">未查找到匹配条件的账单记录</td></tr>';
            return;
        }

        tbody.innerHTML = data.map(item => {
            const typeDisplay = TYPE_MAP[item.交易类型] || item.交易类型;
            const accDisplay = ACC_MAP[item.支付账户] || item.支付账户 || '-';
            const tarDisplay = ACC_MAP[item.目标账户] || item.目标账户 || '-';
            const itemId = item.id;

            return `
                <tr id="row-${itemId}">
                    <td style="color:#64748b; font-weight:bold;">${itemId}</td>
                    <td class="editable-cell" data-field="日期" onclick="inlineEdit(this, ${itemId})">${item.日期}</td>
                    <td class="editable-cell" data-field="时间" onclick="inlineEdit(this, ${itemId})">${item.时间 || ''}</td>
                    <td class="editable-cell" data-field="交易类型" data-raw="${item.交易类型}" onclick="inlineEditType(this, ${itemId})">
                        <span class="badge-type type-${item.交易类型}">${typeDisplay}</span>
                    </td>
                    <td class="editable-cell" data-field="分类" onclick="inlineEdit(this, ${itemId})">${item.分类}</td>
                    <td class="editable-cell" data-field="品名" onclick="inlineEdit(this, ${itemId})"><b>${item.品名}</b></td>
                    <td class="editable-cell" data-field="实际金额" onclick="inlineEdit(this, ${itemId})" style="color: #c0392b; font-weight: bold;">
                        ${Number(item.实际金额).toFixed(2)}
                    </td>
                    <td class="editable-cell" data-field="支付账户" onclick="inlineEdit(this, ${itemId})">${accDisplay}</td>
                    <td class="editable-cell" data-field="目标账户" onclick="inlineEdit(this, ${itemId})">${tarDisplay}</td>
                    <td class="editable-cell" data-field="备注" onclick="inlineEdit(this, ${itemId})">${item.备注 || ''}</td>
                    <td>
                        <button class="btn-action btn-del" onclick="deleteItem(${itemId})">删除</button>
                    </td>
                </tr>
            `;
        }).join('');
    } catch (err) {
        console.error("加载数据失败:", err);
    }
}

// 自动读取 URL 中的过滤参数并填入对应筛选框
function applyUrlFilterParams() {
    const urlParams = new URLSearchParams(window.location.search);
    let hasFilter = false;

    // 1. 日期联动：对齐真实的 filter-start 和 filter-end ID
    const dateVal = urlParams.get('date') || urlParams.get('start_date');
    if (dateVal) {
        const startInput = document.getElementById('filter-start') || document.getElementById('filter-start-date');
        const endInput = document.getElementById('filter-end') || document.getElementById('filter-end-date');
        if (startInput) startInput.value = dateVal;
        if (endInput) endInput.value = dateVal;
        hasFilter = true;
    }

    // 2. 消费分类联动 + 自动勾选精确匹配
    const catVal = urlParams.get('category');
    if (catVal) {
        const catSelect = document.getElementById('filter-category');
        if (catSelect) {
            catSelect.value = catVal;
            hasFilter = true;
        }

        // 核心修复：自动激活“精确匹配”，防止“饮食*”混入“饮食”
        const exactCheck = document.getElementById('filter-exact');
        if (exactCheck) {
            exactCheck.checked = true;
        }
    }

    // 3. 商户联动 (目标账户)
    const merchantVal = urlParams.get('merchant');
    if (merchantVal) {
        const merchantInput = document.getElementById('filter-merchant') || 
                              document.getElementById('filter-target-account') || 
                              document.getElementById('filter-keyword');
        if (merchantInput) {
            merchantInput.value = merchantVal;
            hasFilter = true;
        }
    }

    // 4. 词云关键词/品名联动
    const keywordVal = urlParams.get('keyword');
    if (keywordVal) {
        const nameInput = document.getElementById('filter-name') || 
                          document.getElementById('filter-keyword');
        if (nameInput) {
            nameInput.value = keywordVal;
            hasFilter = true;
        }
    }

    return hasFilter;
}

// 行内直接修改
function inlineEdit(cell, id) {
    if (!id || id === 'null' || id === 'undefined') {
        alert("无效数据ID，请刷新页面后重试");
        return;
    }
    if (cell.querySelector('input')) return;

    const field = cell.getAttribute('data-field');
    const oldText = cell.innerText.trim();
    const input = document.createElement('input');
    input.className = 'cell-input';
    input.value = oldText;

    cell.innerHTML = '';
    cell.appendChild(input);
    input.focus();

    let isSaved = false;
    async function save() {
        if (isSaved) return;
        isSaved = true;

        let newVal = input.value.trim();
        if (field === '支付账户'|| field === '目标账户') newVal = cleanAccountCode(newVal);
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
    const rawAcc = document.getElementById('pay_acc').value;

    const payload = {
        日期: document.getElementById('date').value,
        时间: document.getElementById('time').value.trim(),
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
        // 重新拉取以呈现生成的真实 ID 和正确排序
        loadData();
    }
});

// 删除条目
async function deleteItem(id) {
    if (!id || id === 'null') {
        alert("无效数据ID");
        return;
    }
    if (confirm(`确定删除编号为 ID=${id} 的消费记录吗？`)) {
        await fetch(`/api/db/expenses/${id}`, { method: 'DELETE' });
        await fetch('/api/refresh_analysis', { method: 'POST' });
        loadData();
    }
}

// 重置筛选
function resetFilter() {
    if (event && event.preventDefault) {
        event.preventDefault(); // 阻止按钮在 form 内的默认提交行为
    }

    // 辅助清空函数，防止某个元素在 HTML 中不存在时导致整段代码崩溃报错
    const clearVal = (id, defaultVal = '') => {
        const el = document.getElementById(id);
        if (el) el.value = defaultVal;
    };
    const setChecked = (id, status = false) => {
        const el = document.getElementById(id);
        if (el) el.checked = status;
    };

    // 1. 清空所有筛选框
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

    // 2. 清除浏览器地址栏中的 ?date=... 参数，避免刷新再次带入
    if (window.location.search) {
        window.history.replaceState({}, document.title, window.location.pathname);
    }

    // 3. 执行全量加载
    loadData();
}

async function exportToExcel() {
    // 1. 收集当前的各维度筛选条件
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

    // 2. 生成一个智能默认文件名（如：账单导出_2026-09-05至2026-09-20.xlsx）
    let defaultFileName = '账单导出';
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

    // 3. 请求后端生成 Excel 数据流
    try {
        const response = await fetch(`/api/db/export_excel?${params.toString()}`);
        if (!response.ok) throw new Error(`导出失败，状态码: ${response.status}`);
        const blob = await response.blob();

        // 4. 方案 A：支持原生“另存为”弹窗（Chrome、Edge 等）
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
                
                // 将数据写入用户选定的具体目录与文件名
                const writable = await handle.createWritable();
                await writable.write(blob);
                await writable.close();
                alert('✅ 账单已成功保存至选定目录！');
                return;
            } catch (pickerErr) {
                // 用户在弹出的系统窗口中点击了“取消”
                if (pickerErr.name === 'AbortError') {
                    console.log('用户取消了保存');
                    return;
                }
                console.warn('调用原生文件窗口失败，转用降级方案:', pickerErr);
            }
        }

        // 5. 方案 B：降级方案（浏览器弹 prompt 自定义文件名后下载）
        const customName = prompt('请输入要保存的 Excel 文件名：', defaultFileName);
        if (!customName) return; // 用户点击取消

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
document.addEventListener('DOMContentLoaded', () => {
    // 1. 读取 URL 传递过来的跳转参数并回填到界面筛选框
    applyUrlFilterParams();

    // 2. 执行原有的加载流水数据逻辑（此时收集筛选参数的函数会自动读取回填好的值）
    loadData(); 
});