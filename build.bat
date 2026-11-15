@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
call scripts\python_env.bat
if errorlevel 1 exit /b 1
echo Python: %PYTHON%
echo [1/3] Checking installed build dependencies...
"%PYTHON%" -c "import PyInstaller, PyQt5, requests, win32api, deep_translator"
if errorlevel 1 (
    echo [ERROR] Install dependencies first: .venv\Scripts\python.exe -m pip install -r requirements-build.lock.txt
    exit /b 1
)
echo [2/3] Checking release configuration and regression tests...
"%PYTHON%" scripts\check_release.py
if errorlevel 1 exit /b 1
"%PYTHON%" -m unittest discover -s tests -t .
if errorlevel 1 exit /b 1
echo [3/3] Building with TranslateAssistant.spec...
"%PYTHON%" -m PyInstaller --clean --noconfirm TranslateAssistant.spec
if errorlevel 1 exit /b 1
echo Output: dist\TranslateAssistant.exe
echo Credentials are supplied at runtime through environment variables.
exit /b 0
