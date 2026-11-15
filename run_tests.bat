@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
call scripts\python_env.bat
if errorlevel 1 exit /b 1
echo Python: %PYTHON%
"%PYTHON%" -m unittest discover -s tests -t . -v
set "RESULT=%errorlevel%"
if "%RESULT%"=="0" (
    echo [PASSED] All tests passed.
) else (
    echo [FAILED] Tests failed.
)
exit /b %RESULT%
