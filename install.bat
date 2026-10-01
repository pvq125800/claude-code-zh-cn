@echo off
chcp 65001 >nul 2>&1
title Claude Code 桌面版中文汉化
echo ============================================
echo   Claude Code 桌面版 中文汉化安装程序
echo ============================================
echo.

:: 检查 Python
python3 --version >nul 2>&1
if errorlevel 1 (
    python --version >nul 2>&1
    if errorlevel 1 (
        echo [错误] 未检测到 Python，请先安装 Python 3:
        echo   https://www.python.org/downloads/
        echo.
        pause
        exit /b 1
    )
    set PYTHON=python
) else (
    set PYTHON=python3
)

:: 检查管理员权限
net session >nul 2>&1
if errorlevel 1 (
    echo 正在请求管理员权限...
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

echo 以管理员权限运行
echo.

%PYTHON% "%~dp0install.py" %*

echo.
echo 按任意键退出...
pause >nul
