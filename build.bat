@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
call scripts\python_env.bat
if errorlevel 1 goto fail
echo Python: %PYTHON%
set "BUILD_LOG=%~dp0build.log"
echo ===== %DATE% %TIME% ===== > "%BUILD_LOG%"
echo Python: %PYTHON%>> "%BUILD_LOG%"
"%PYTHON%" -V>> "%BUILD_LOG%" 2>&1
"%PYTHON%" -c "import sys; sys.exit(0 if sys.version_info[:2] == (3, 14) else 1)"
if errorlevel 1 (
    echo [ERROR] 打包固定要求 Python 3.14 x64 (源码运行才支持 3.11-3.15)。
    "%PYTHON%" -V
    echo         请用 py -3.14 -m venv .venv 单独建一个打包环境,
    echo         再安装 requirements-build.lock.txt。
    goto fail
)
echo [1/3] Checking installed build dependencies...
"%PYTHON%" -c "import PyInstaller, PyQt5, requests, win32api, deep_translator"
if errorlevel 1 (
    echo [ERROR] 缺少打包依赖, 请先执行:
    echo         .venv\Scripts\python.exe -m pip install -r requirements-build.lock.txt
    goto fail
)
echo [2/3] Checking release configuration and regression tests...
"%PYTHON%" scripts\check_release.py
if errorlevel 1 goto fail
"%PYTHON%" -m unittest discover -s tests -t . >> "%BUILD_LOG%" 2>&1
if errorlevel 1 (
    echo [ERROR] 回归测试未通过, 详情见 build.log
    goto fail
)
echo [3/3] Building with TranslateAssistant.spec...
"%PYTHON%" -m PyInstaller --clean --noconfirm TranslateAssistant.spec >> "%BUILD_LOG%" 2>&1
if errorlevel 1 (
    echo [ERROR] PyInstaller 打包失败, 详情见 build.log
    goto fail
)
echo Output: dist\TranslateAssistant.exe
echo Credentials are supplied at runtime through environment variables.
exit /b 0

:fail
echo.
echo [ERROR] 打包中止。完整日志: %BUILD_LOG%
echo         常见原因: 当前解释器不是 Python 3.14 / 未装 requirements-build.lock.txt
pause
exit /b 1
