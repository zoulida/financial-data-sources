#!/bin/bash
# A股逃顶打分器 - Linux/Mac快速启动脚本
# 运行方法: chmod +x run.sh && ./run.sh

echo "======================================================================"
echo "A股牛市逃顶打分器"
echo "======================================================================"
echo

# 切换到脚本所在目录
cd "$(dirname "$0")"

# 激活虚拟环境（如果存在）
if [ -f "../../venv/bin/activate" ]; then
    echo "正在激活虚拟环境..."
    source ../../venv/bin/activate
fi

# 运行主程序（默认使用简化版）
echo "正在运行打分器..."
echo

# 检查是否传入参数选择版本
if [ "$1" = "full" ]; then
    echo "使用完整版..."
    python escape_top_scorer.py
else
    echo "使用简化版..."
    python escape_top_scorer_simple.py
fi

echo
echo "======================================================================"
echo "程序运行完毕"
echo "======================================================================"
echo

