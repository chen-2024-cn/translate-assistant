@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
call scripts\python_env.bat
if errorlevel 1 goto failed
rem   run.bat            无控制台启动(推荐, 双击即可)
rem   run.bat --console  前台启动, 保留控制台看输出(调试用)
rem   run.bat --diagnose 只跑 Qt 启动诊断, 不启动程序
if /i "%~1"=="--diagnose" goto diagnose
if /i "%~1"=="--console" goto console
"%PYTHON%" scripts\diagnose_qt.py --check
if errorlevel 1 goto failed

rem 首选 pythonw.exe: 它不带控制台, 与启动它的终端完全解耦
for %%p in ("%PYTHON%") do set "PYW=%%~dpppythonw.exe"
if exist "%PYW%" (
    start "" "%PYW%" "%~dp0main.py"
    exit /b 0
)

rem 兜底: 环境里没有 pythonw.exe(例如某些非官方工具建的 venv) 时,
rem 用 wscript 以隐藏窗口方式启动 python.exe, 同样不会留下可见终端
if exist "%~dp0run_silent.vbs" (
    wscript //nologo "%~dp0run_silent.vbs"
    exit /b 0
)

echo [WARN] 未找到 pythonw.exe, 也没有 run_silent.vbs, 退化为前台启动。
start "" "%PYTHON%" "%~dp0main.py"
exit /b 0
:console
"%PYTHON%" "%~dp0main.py"
exit /b %errorlevel%
:diagnose
"%PYTHON%" scripts\diagnose_qt.py
exit /b %errorlevel%
:failed
echo.
echo [ERROR] 启动前检查失败。
echo   1. 运行 run.bat --diagnose 查看具体原因
echo   2. 日志位置: logs\translate-assistant.log
pause
exit /b 1
