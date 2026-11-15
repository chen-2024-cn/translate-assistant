@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
call scripts\python_env.bat
if errorlevel 1 goto failed
if /i "%~1"=="--diagnose" goto diagnose
"%PYTHON%" scripts\diagnose_qt.py --check
if errorlevel 1 goto failed
for %%p in ("%PYTHON%") do set "PYW=%%~dpppythonw.exe"
if exist "%PYW%" (
    start "" "%PYW%" main.py
) else (
    start "" "%PYTHON%" main.py
)
exit /b 0
:diagnose
"%PYTHON%" scripts\diagnose_qt.py
exit /b %errorlevel%
:failed
echo [ERROR] Startup preflight failed. Run run.bat --diagnose for details.
pause
exit /b 1
