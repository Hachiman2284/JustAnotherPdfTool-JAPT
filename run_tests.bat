@echo off
REM Run the automated tests. Run setupEnv.bat once first.
cd /d "%~dp0"

if exist "venv\Scripts\python.exe" (
    set "PY=venv\Scripts\python.exe"
) else (
    echo The virtual environment was not found. Run setupEnv.bat first.
    pause
    exit /b 1
)

REM Install pytest (the test runner) the first time.
"%PY%" -m pytest --version >nul 2>&1
if errorlevel 1 (
    echo Installing the test tools...
    "%PY%" -m pip install -r requirements-dev.txt
    if errorlevel 1 (
        echo Failed to install the test tools.
        pause
        exit /b 1
    )
)

REM Extra arguments are passed to pytest, e.g. run_tests.bat -k redact
"%PY%" -m pytest tests %*
set "RC=%ERRORLEVEL%"
pause
exit /b %RC%
