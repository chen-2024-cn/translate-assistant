@echo off
rem Shared interpreter selection. Call only from the project root.
set "PYTHON="
if exist ".venv\Scripts\python.exe" (
    set "PYTHON=.venv\Scripts\python.exe"
    exit /b 0
)
where py >nul 2>nul
if not errorlevel 1 (
    for /f "delims=" %%p in ('py -3 -c "import sys; print(sys.executable)" 2^>nul') do set "PYTHON=%%p"
    if defined PYTHON exit /b 0
)
where python >nul 2>nul
if not errorlevel 1 (
    for /f "delims=" %%p in ('python -c "import sys; print(sys.executable)" 2^>nul') do set "PYTHON=%%p"
    if defined PYTHON exit /b 0
)
echo [ERROR] Python not found. Install Windows Python 3.14 x64 or create .venv.
exit /b 1
