@echo off
rem Shared interpreter selection. Call only from the project root.
set "PYTHON="
if exist ".venv\Scripts\python.exe" (
    set "PYTHON=.venv\Scripts\python.exe"
    goto validate
)
where py >nul 2>nul
if not errorlevel 1 (
    for /f "delims=" %%p in ('py -3 -c "import sys; print(sys.executable)" 2^>nul') do set "PYTHON=%%p"
    if defined PYTHON goto validate
)
where python >nul 2>nul
if not errorlevel 1 (
    for /f "delims=" %%p in ('python -c "import sys; print(sys.executable)" 2^>nul') do set "PYTHON=%%p"
    if defined PYTHON goto validate
)
echo [ERROR] Install standard CPython 3.11-3.15 for Windows x64 or create .venv.
exit /b 1
:validate
"%PYTHON%" python_runtime.py
exit /b %errorlevel%
