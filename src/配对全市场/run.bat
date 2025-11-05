@echo off
chcp 65001 >nul
echo ========================================
echo 配对交易全市场扫描系统
echo ========================================
echo.

REM 检查虚拟环境是否存在
if not exist "..\..\venv\Scripts\activate.bat" (
    echo [错误] 虚拟环境不存在！
    echo 请先创建虚拟环境：python -m venv venv
    pause
    exit /b 1
)

echo [1/3] 激活虚拟环境...
call ..\..\venv\Scripts\activate.bat
echo.

echo [2/3] 检查依赖...
python -c "import pandas, numpy, statsmodels, pykalman, WindPy" 2>nul
if errorlevel 1 (
    echo [警告] 部分依赖缺失，尝试安装...
    pip install -r requirements.txt
    echo.
)

echo [3/3] 启动扫描程序...
echo.
python main.py

echo.
echo ========================================
echo 程序执行完毕
echo ========================================
pause

