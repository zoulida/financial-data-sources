@echo off
chcp 65001 >nul
echo ================================================
echo   API可用性检查
echo ================================================
echo.
cd /d "%~dp0"
python check_api.py
echo.
pause

