@echo off
REM Grid Strategy v3.0 launcher
REM Default args: --symbol 162411.SZ --step 0.001 --baseline 1.076
REM Override example: start_grid.bat --symbol 512710.SH --baseline 1.020

chcp 65001 > nul
title Grid Strategy v3.0

REM Switch to project root = bat_dir\..\..\..\
pushd "%~dp0..\..\.."
if errorlevel 1 (
    echo [ERROR] Cannot locate project root.
    pause
    exit /b 1
)

call venv\Scripts\activate.bat
if errorlevel 1 (
    echo [ERROR] Failed to activate venv. Check venv directory.
    popd
    pause
    exit /b 1
)

python "%~dp0run.py" --symbol 162411.SZ --step 0.001 --baseline 1.076 %*
set EXITCODE=%errorlevel%

popd
echo.
echo ============================================================
echo  Strategy exited (code %EXITCODE%). Press any key to close.
echo ============================================================
pause > nul
