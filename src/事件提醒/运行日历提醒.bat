@echo off
chcp 65001 >nul
echo 正在启动日历提醒程序...
echo.
python calendar_reminder.py
echo.
echo 程序执行完成，按任意键退出...
pause >nul
