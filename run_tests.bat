@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
call scripts\python_env.bat
if errorlevel 1 goto fail
echo Python: %PYTHON%
if not exist "logs" mkdir "logs"
set "TEST_LOG=%~dp0logs\run_tests.log"
echo ===== %DATE% %TIME% ===== > "%TEST_LOG%"

rem 先确认 Qt 平台插件能被当前解释器找到; 找不到时直接指出缺哪个包,
rem 而不是让测试跑到一半抛出 "Could not find the Qt platform plugin windows"
"%PYTHON%" scripts\diagnose_qt.py --check >> "%TEST_LOG%" 2>&1
if errorlevel 1 (
    echo [ERROR] Qt 平台插件缺失或无法加载。
    "%PYTHON%" scripts\diagnose_qt.py --check
    echo         修复: .venv\Scripts\python.exe -m pip install --only-binary=:all: --force-reinstall "PyQt5>=5.15.11,<5.16" "PyQt5-Qt5>=5.15.2,<5.16"
    goto fail
)

"%PYTHON%" -m unittest discover -s tests -t . -v >> "%TEST_LOG%" 2>&1
set "RESULT=%errorlevel%"
type "%TEST_LOG%"
if "%RESULT%"=="0" (
    echo [PASSED] All tests passed.
    exit /b 0
)
echo [FAILED] Tests failed. 完整输出: %TEST_LOG%
pause
exit /b %RESULT%

:fail
echo.
echo [ERROR] 测试未启动。日志: %TEST_LOG%
pause
exit /b 1
