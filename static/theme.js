// static/theme.js
// BillAnaly - 主题管理器 (浅色 / 深色无缝切换)

(function () {
    // 1. 初始化主题（防止页面初次加载时白屏闪烁）
    const THEME_KEY = 'billanaly_theme';
    const savedTheme = localStorage.getItem(THEME_KEY);
    
    // 如果没有手动选过，检测系统偏好；默认浅色
    let activeTheme = 'light';
    if (savedTheme === 'dark' || savedTheme === 'light') {
        activeTheme = savedTheme;
    } else if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
        activeTheme = 'dark';
    }
    
    document.documentElement.setAttribute('data-theme', activeTheme);

    // 2. 更新页面上的切换按钮图标与提示
    function syncButtonState() {
        const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
        const btns = document.querySelectorAll('.btn-theme-toggle, #btn-theme-toggle');
        btns.forEach(btn => {
            if (btn) {
                btn.innerHTML = isDark ? '☀️' : '🌙';
                btn.setAttribute('title', isDark ? '切换到浅色模式' : '切换到深色模式');
                btn.setAttribute('aria-label', isDark ? '切换到浅色模式' : '切换到深色模式');
            }
        });
    }

    // 3. 全局切换方法
    window.toggleTheme = function () {
        const current = document.documentElement.getAttribute('data-theme') || 'light';
        const next = current === 'dark' ? 'light' : 'dark';
        document.documentElement.setAttribute('data-theme', next);
        localStorage.setItem(THEME_KEY, next);
        syncButtonState();

        // 派发自定义事件，供 ECharts 等图表组件即时响应
        window.dispatchEvent(new CustomEvent('themechange', { detail: { theme: next } }));
    };

    // DOM 加载完成后同步按钮状态
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', syncButtonState);
    } else {
        syncButtonState();
    }
})();
