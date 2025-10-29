@echo off
chcp 65001 >nul
echo ================================================
echo   窄基前60名指数变动数据下载
echo ================================================
echo.
cd /d "%~dp0"
python download_changes.py
echo.
pause

