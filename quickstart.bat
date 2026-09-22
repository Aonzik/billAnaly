@echo off
chcp 65001 >nul
title billAnaly 启动器

echo ==================================================
echo             billAnaly 一键快速启动
echo ==================================================

:: 1. 检查虚拟环境是否存在，不存在则创建
if not exist "venv\Scripts\activate.bat" (
    echo [提示] 未检测到虚拟环境，正在匹配 Python 解释器...
    
    set "PY_CMD="
    set "IS_V312=0"

    :: 依次尝试检测 Python 3.12
    py -3.12 --version >nul 2>&1
    if not errorlevel 1 (
        set "PY_CMD=py -3.12"
        set "IS_V312=1"
    ) else (
        python3.12 --version >nul 2>&1
        if not errorlevel 1 (
            set "PY_CMD=python3.12"
            set "IS_V312=1"
        )
    )

    :: 如果没有找到 3.12，降级尝试 python
    if not defined PY_CMD (
        python --version >nul 2>&1
        if not errorlevel 1 (
            set "PY_CMD=python"
        ) else (
            py --version >nul 2>&1
            if not errorlevel 1 (
                set "PY_CMD=py"
            )
        )
    )

    :: 检查最终是否找到了可用解释器
    if not defined PY_CMD (
        echo [错误] 系统未检测到可用的 Python 环境，请先安装 Python 并添加至 PATH。
        pause
        exit /b 1
    )

    :: 如果不是 3.12，输出警告
    if "%IS_V312%"=="0" (
        echo [警告] 未检测到 Python 3.12，当前将降级使用:
        %PY_CMD% --version
        echo [警告] 版本不是 3.12，可能会出现若干未知问题！
    ) else (
        echo [提示] 成功命中 Python 3.12 环境。
    )

    echo [提示] 正在创建虚拟环境...
    %PY_CMD% -m venv venv
    if errorlevel 1 (
        echo [错误] 虚拟环境创建失败。
        pause
        exit /b 1
    )
    
    echo [提示] 正在激活虚拟环境并安装依赖...
    call venv\Scripts\activate.bat
    python -m pip install --upgrade pip
    pip install -r requirements.txt
    if errorlevel 1 (
        echo [错误] 依赖安装失败，请检查网络或 requirements.txt。
        pause
        exit /b 1
    )
) else (
    call venv\Scripts\activate.bat
)

:: 2. 检查配置文件
if not exist "config.yaml" (
    echo [警告] 未检测到 config.yaml，请确认配置是否填写完整！
)

echo [提示] 正在启动服务...
python server.py

pause