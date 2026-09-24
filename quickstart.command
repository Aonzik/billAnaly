#!/bin/bash

# 自动切换到脚本所在目录
cd "$(dirname "$0")"

echo "=================================================="
echo "            billAnaly 一键快速启动"
echo "=================================================="

# 1. 检查虚拟环境是否存在，不存在则创建
if [ ! -d "venv" ]; then
    echo "[提示] 未检测到虚拟环境，正在匹配 Python 解释器..."
    
    PY_CMD=""
    IS_V312=0

    # 优先检测 python3.12
    if command -v python3.12 &>/dev/null; then
        PY_CMD="python3.12"
        IS_V312=1
    # 降级检测 python3
    elif command -v python3 &>/dev/null; then
        PY_CMD="python3"
    # 降级检测 python
    elif command -v python &>/dev/null; then
        PY_CMD="python"
    fi

    # 检查是否找到可用的 Python
    if [ -z "$PY_CMD" ]; then
        echo "[错误] 系统未检测到可用的 Python，请安装后再试。"
        read -n 1 -s -r -p "按任意键退出..."
        exit 1
    fi

    # 如果不是 3.12，输出警告
    if [ "$IS_V312" -eq 0 ]; then
        echo "[警告] 未检测到 Python 3.12，当前将降级使用: $($PY_CMD --version)"
        echo "[警告] 版本不是 3.12，可能会出现若干未知问题！"
    else
        echo "[提示] 成功命中 Python 3.12: $($PY_CMD --version)"
    fi

    echo "[提示] 正在创建虚拟环境..."
    $PY_CMD -m venv venv
    if [ $? -ne 0 ]; then
        echo "[错误] 虚拟环境创建失败。"
        read -n 1 -s -r -p "按任意键退出..."
        exit 1
    fi

    echo "[提示] 正在激活虚拟环境并安装依赖..."
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "[错误] 依赖安装失败，请检查网络或 requirements.txt。"
        read -n 1 -s -r -p "按任意键退出..."
        exit 1
    fi
else
    source venv/bin/activate
fi

# 2. 安装前端依赖文件
mkdir -p static/js
curl -o static/js/echarts.min.js "https://cdn.jsdelivr.net/npm/echarts@5.5.0/dist/echarts.min.js"
curl -o static/js/marked.min.js "https://cdn.jsdelivr.net/npm/marked/marked.min.js"
curl -o static/js/echarts-wordcloud.min.js "https://cdn.jsdelivr.net/npm/echarts-wordcloud@2/dist/echarts-wordcloud.min.js"

# 3. 检查配置文件
if [ ! -f "config.yaml" ]; then
    echo "[警告] 未检测到 config.yaml，请确认配置是否填写完整！"
fi

echo "[提示] 正在启动服务..."
python server.py

# 退出前暂停
read -n 1 -s -r -p "服务已停止，按任意键关闭窗口..."