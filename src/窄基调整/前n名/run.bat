@echo off
chcp 65001 >nul
echo ========================================
echo 批量分析前N名指数
echo ========================================
echo.

python batch_analyze.py

echo.
echo 分析完成！
pause