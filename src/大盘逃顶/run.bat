@echo off
REM A股逃顶打分器 - Windows快速启动脚本
REM 双击此文件即可运行

echo ======================================================================
echo A股牛市逃顶打分器
echo ======================================================================
echo.

REM 切换到脚本所在目录
cd /d %~dp0

REM 激活虚拟环境（如果存在）
if exist "..\..\venv\Scripts\activate.bat" (
    echo 正在激活虚拟环境...
    call ..\..\venv\Scripts\activate.bat
)

REM 运行主程序（默认使用简化版）
echo 正在运行打分器...
echo.

REM 检查是否传入参数选择版本
if "%1"=="full" (
    echo 使用完整版...
    python escape_top_scorer.py
) else (
    echo 使用简化版...
    python escape_top_scorer_simple.py
)

echo.
echo ======================================================================
echo 程序运行完毕
echo ======================================================================
echo.

pause

