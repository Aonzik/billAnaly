// static/auth.js
// 统一的登录态处理：将账号信息并入顶部导航栏，并对所有 fetch 补上 401 跳转逻辑

(function () {
    // ---------------------------------------------------------------
    // 1. 统一 fetch 包装：同源携带 Cookie；遇到 401 自动跳登录页
    // ---------------------------------------------------------------
    const originalFetch = window.fetch.bind(window);

    window.apiFetch = async function (input, init) {
        const options = Object.assign({}, init || {});
        options.credentials = 'same-origin';

        const res = await originalFetch(input, options);

        if (res.status === 401) {
            const url = typeof input === 'string' ? input : (input && input.url) || '';
            // 登录/登出接口自身不触发跳转，避免死循环
            if (!url.includes('/api/auth/login') && !url.includes('/api/auth/logout')) {
                const back = encodeURIComponent(window.location.pathname + window.location.search);
                window.location.replace('/login.html?next=' + back);
                throw new Error('UNAUTHORIZED');
            }
        }
        return res;
    };

    // 覆盖全局 fetch，使既有业务代码（dashboard.js / manager.js 等）无需改动
    window.fetch = function (input, init) {
        const url = typeof input === 'string' ? input : (input && input.url) || '';
        const isExternal = /^https?:\/\//i.test(url) && !url.startsWith(window.location.origin);
        if (isExternal) return originalFetch(input, init);
        return window.apiFetch(input, init);
    };

    // ---------------------------------------------------------------
    // 2. 用户信息 + 顶栏用户徽标（并入上栏固定，杜绝悬浮遮挡）
    // ---------------------------------------------------------------
    window.currentUser = null;

    window.loadCurrentUser = async function () {
        try {
            const res = await originalFetch('/api/auth/me', { credentials: 'same-origin' });
            if (!res.ok) return null;
            window.currentUser = await res.json();
            return window.currentUser;
        } catch (e) {
            return null;
        }
    };

    window.logout = async function () {
        try {
            await originalFetch('/api/auth/logout', { method: 'POST', credentials: 'same-origin' });
        } catch (e) { /* 忽略网络异常 */ }
        window.location.replace('/login.html');
    };

    function injectUserPill(user) {
        if (!user) return;
        
        // 查找顶部导航右侧操作区 .topbar-actions
        const topbarActions = document.querySelector('.topbar-actions');
        if (topbarActions) {
            let pill = document.getElementById('topbar-user-pill');
            const roleText = user.role === 'admin' ? '管理员' : '普通用户';
            const roleClass = user.role === 'admin' ? 'role admin' : 'role user';
            const perm = window.permissionMeta(user);
            
            if (!pill) {
                pill = document.createElement('a');
                pill.id = 'topbar-user-pill';
                pill.href = '/account.html';
                pill.className = 'topbar-user-pill';
                pill.title = '点击进入账号管理';
                pill.innerHTML = `
                    <span class="avatar">👤</span>
                    <span class="who">${user.username || '-'}</span>
                    <span class="${roleClass}" id="topbar-role">${roleText}</span>
                    <span class="perm ${perm.cls}" id="topbar-perm" title="${perm.full}">${perm.short}</span>
                `;
                // 插入在操作区最前面（即主题切换按钮左侧）
                topbarActions.insertBefore(pill, topbarActions.firstChild);
            } else {
                const who = pill.querySelector('.who');
                const role = pill.querySelector('#topbar-role');
                const permEl = pill.querySelector('#topbar-perm');
                if (who) who.textContent = user.username || '-';
                if (role) {
                    role.textContent = roleText;
                    role.className = roleClass;
                }
                if (permEl) {
                    permEl.textContent = perm.short;
                    permEl.title = perm.full;
                    permEl.className = 'perm ' + perm.cls;
                }
            }

            // 若为管理员，同时自动点亮顶栏上的“账号”和“日志”导航入口
            if (user.role === 'admin') {
                const navAcc = document.getElementById('nav-account') || document.getElementById('logs-link');
                const navLogs = document.getElementById('nav-logs');
                if (navAcc) navAcc.style.display = 'inline-block';
                if (navLogs) navLogs.style.display = 'inline-block';
            }

            // 无数据读取权限的账号隐藏数据页入口，只保留账号页
            if (user.can_read === false) {
                document.querySelectorAll('.topbar-nav a').forEach(a => {
                    const href = a.getAttribute('href') || '';
                    if (!href.includes('account.html')) a.style.display = 'none';
                });
            }
        }
    }

    // 权限展示文案（与后端 permission_label 保持一致）
    window.permissionMeta = function (user) {
        if (!user) return { cls: 'none', short: '无权限', full: '不可读不可写' };
        if (user.can_write) return { cls: 'rw', short: '可读写', full: '可读可写' };
        if (user.can_read) return { cls: 'ro', short: '只读', full: '可读不可写' };
        return { cls: 'none', short: '无权限', full: '不可读不可写' };
    };

    // 无读取权限的账号不允许停留在数据页面（后端也会重定向，这里做前端兜底）
    window.guardReadPermission = function (user) {
        if (!user) return;
        if (user.can_read) return;
        const page = (window.location.pathname.split('/').pop() || '').toLowerCase();
        if (page === 'account.html' || page === 'login.html' || page === '') return;
        window.location.replace('/account.html?denied=1');
    };

    document.addEventListener('DOMContentLoaded', async () => {
        const user = await window.loadCurrentUser();
        if (!user) return; // 未登录由后端重定向或 401 拦截处理
        window.guardReadPermission(user);
        injectUserPill(user);
    });
})();
