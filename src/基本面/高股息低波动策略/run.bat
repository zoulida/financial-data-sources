@echo off
REM 高股息低波动股票筛选系统 - Windows启动脚本
chcp 65001 >nul
echo ========================================
echo 高股息低波动股票筛选系统
echo ========================================
echo.

REM 检查Python环境
python --version >nul 2>&1
if errorlevel 1 (
    echo 错误: 未找到Python，请先安装Python 3.8+
    pause
    exit /b 1
)

echo 正在启动...
echo.

REM 运行主程序
python main.py %*

echo.
echo 程序运行完成！
pause

