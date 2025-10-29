@echo off
chcp 65001
echo ========================================
echo 中证全指指数成分股获取程序
echo ========================================
echo.

echo 请选择操作:
echo 1. 测试 Wind API 连接
echo 2. 获取并过滤中证全指成分股
echo 3. 运行使用示例
echo 4. 测试 Wind API 工具库
echo 5. 测试缓存功能
echo 6. 调试字段信息
echo.
set /p choice=请输入选项 (1-6): 

if "%choice%"=="1" (
    echo.
    echo 正在运行测试程序...
    python test_api.py
    pause
    exit /b
)

if "%choice%"=="2" (
    echo.
    echo 正在运行主程序...
    python get_995000_constituents.py
    pause
    exit /b
)

if "%choice%"=="3" (
    echo.
    echo 正在运行使用示例...
    python example_usage.py
    pause
    exit /b
)

if "%choice%"=="4" (
    echo.
    echo 正在测试 Wind API 工具库...
    python wind_api_utils.py
    pause
    exit /b
)

if "%choice%"=="5" (
    echo.
    echo 正在测试缓存功能...
    python test_cache.py
    pause
    exit /b
)

if "%choice%"=="6" (
    echo.
    echo 正在调试字段信息...
    python debug_fields.py
    pause
    exit /b
)

echo 无效选项！
pause

