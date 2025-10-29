@echo off
chcp 65001 >nul
echo ================================================
echo   窄基前60名指数股票表现分析
echo ================================================
echo.
cd /d "%~dp0"
python analyze_performance.py
echo.
pause

