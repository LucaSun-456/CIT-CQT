@echo off
chcp 65001 >nul
title CIT/CQT 模拟审讯系统 - Legal Psychology

echo ============================================================
echo   CIT/CQT 模拟审讯系统
echo   法律心理学 Murder Case Simulation
echo   NYU Shanghai - Fall 2026
echo ============================================================
echo.

:: Switch to script directory
cd /d "%~dp0"

:: Check if Flask is installed
python -c "import flask" 2>nul
if errorlevel 1 (
    echo [INFO] 正在安装依赖...
    pip install -r requirements.txt
    echo.
)

echo [INFO] 启动系统...
echo.
echo   访问地址: http://localhost:5000
echo   控方密码: cit2026
echo   辩方密码: 2026cqt
echo.
echo   按 Ctrl+C 停止服务
echo.

python app.py

pause
