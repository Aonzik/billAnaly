// static/auth.js
// 统一的登录态处理：注入右上角用户栏，并对所有 fetch 补上 401 跳转逻辑

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

    // 覆盖全局 fetch，使既有业务代码（dashboard.js / manager.js）无需改动
    window.fetch = function (input, init) {
        // 相对路径的站内请求统一走 apiFetch；外链保持原生行为
        const url = typeof input === 'string' ? input : (input && input.url) || '';
        const isExternal = /^https?:\/\//i.test(url) && !url.startsWith(window.location.origin);
        if (isExternal) return originalFetch(input, init);
        return window.apiFetch(input, init);
    };

    // ---------------------------------------------------------------
    // 2. 用户信息 + 右上角悬浮用户栏
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

    function injectStyle() {
        if (document.getElementById('auth-bar-style')) return;
        const style = document.createElement('style');
        style.id = 'auth-bar-style';
        style.textContent = `
            #auth-bar {
                position: fixed; top: 12px; right: 14px; z-index: 99999;
                display: flex; align-items: center; gap: 8px;
                background: rgba(255,255,255,0.96);
                border: 1px solid #e2e8f0; border-radius: 30px;
                padding: 5px 6px 5px 14px;
                box-shadow: 0 3px 14px rgba(15,23,42,0.12);
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Microsoft YaHei", sans-serif;
                font-size: 12.5px; color: #334155;
            }
            #auth-bar .who { font-weight: 700; color: #0f172a; }
            #auth-bar .role {
                font-size: 10.5px; font-weight: 700; padding: 1px 6px;
                border-radius: 10px; background: #dbeafe; color: #1d4ed8;
            }
            #auth-bar .role.user { background: #e2e8f0; color: #475569; }
            #auth-bar a, #auth-bar button {
                font-size: 12px; font-weight: 600; text-decoration: none;
                border: 1px solid #cbd5e1; background: #fff; color: #334155;
                padding: 4px 10px; border-radius: 20px; cursor: pointer;
            }
            #auth-bar a:hover, #auth-bar button:hover { background: #f1f5f9; }
            #auth-bar .out { color: #b91c1c; border-color: #fecaca; background: #fef2f2; }
            #auth-bar .out:hover { background: #fee2e2; }
        `;
        document.head.appendChild(style);
    }

    function injectBar() {
        if (document.getElementById('auth-bar')) return;
        injectStyle();

        const bar = document.createElement('div');
        bar.id = 'auth-bar';
        bar.innerHTML = `
            <span>👤 <span class="who">-</span></span>
            <span class="role" id="auth-role"></span>
            <a href="/account.html" title="修改账号名与密码">账号管理</a>
            <button class="out" id="auth-logout-btn">退出</button>
        `;
        document.body.appendChild(bar);

        bar.querySelector('#auth-logout-btn').addEventListener('click', window.logout);
    }

    function fillBar(user) {
        if (!user) return;
        const who = document.querySelector('#auth-bar .who');
        const role = document.getElementById('auth-role');
        if (who) who.textContent = user.username;
        if (role) {
            role.textContent = user.role === 'admin' ? '管理员' : '普通用户';
            role.className = 'role' + (user.role === 'admin' ? '' : ' user');
        }
    }

    document.addEventListener('DOMContentLoaded', async () => {
        const user = await window.loadCurrentUser();
        if (!user) return;   // 未登录由后端重定向处理
        injectBar();
        fillBar(user);
    });
})();
