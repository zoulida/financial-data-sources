@echo off
chcp 65001 >nul
cd /d %~dp0..\..\..

echo ============================================================
echo 开户数据获取完整示例
echo ============================================================
echo.

echo 激活虚拟环境...
call venv\Scripts\activate.bat

echo.
echo 运行完整示例（包含数据获取、分析、可视化）...
echo ============================================================
python src\aksharedir\开户数据\示例代码.py

echo.
echo ============================================================
echo 执行完成！
echo 生成的文件：
echo - output\开户数据.csv
echo - output\开户数据.xlsx
echo - output\开户数据.parquet
echo - 开户数据_基础图表.png
echo - 开户数据_高级图表.png
echo.
echo 按任意键退出...
pause >nul

