#!/bin/bash

echo "========================================"
echo "配对交易全市场扫描系统"
echo "========================================"
echo ""

# 检查虚拟环境是否存在
if [ ! -f "../../venv/bin/activate" ]; then
    echo "[错误] 虚拟环境不存在！"
    echo "请先创建虚拟环境：python -m venv venv"
    exit 1
fi

echo "[1/3] 激活虚拟环境..."
source ../../venv/bin/activate
echo ""

echo "[2/3] 检查依赖..."
python -c "import pandas, numpy, statsmodels, pykalman, WindPy" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "[警告] 部分依赖缺失，尝试安装..."
    pip install -r requirements.txt
    echo ""
fi

echo "[3/3] 启动扫描程序..."
echo ""
python main.py

echo ""
echo "========================================"
echo "程序执行完毕"
echo "========================================"

