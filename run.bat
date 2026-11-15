@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
call scripts\python_env.bat
if errorlevel 1 exit /b 1
for %%p in ("%PYTHON%") do set "PYW=%%~dpppythonw.exe"
if exist "%PYW%" (
    start "" "%PYW%" main.py
) else (
    start "" "%PYTHON%" main.py
)
exit /b 0
