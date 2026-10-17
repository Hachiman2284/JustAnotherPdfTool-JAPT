@echo off
REM Change to the directory where this batch file is located
cd /d "%~dp0"

REM Find Python: "python" when it is on PATH, otherwise the "py" launcher,
REM which the python.org installer adds even when "Add python.exe to PATH"
REM is left unticked.
set "PY="
python --version >nul 2>&1 && set "PY=python"
if not defined PY (
    py -3 --version >nul 2>&1 && set "PY=py -3"
)
if not defined PY (
    echo Python is not installed. Install it from https://www.python.org/downloads/
    echo.
    echo Setup did not finish.
    pause
    exit /b 1
)
echo Using Python: %PY%

REM Check if virtual environment already exists
if exist "venv\Scripts\python.exe" (
    echo Virtual environment already exists.
) else (
    REM Create virtual environment
    %PY% -m venv venv
    if errorlevel 1 (
        echo Failed to create virtual environment.
        echo.
        echo Setup did not finish.
        pause
        exit /b 1
    )
    echo Virtual environment created.
)

REM Install requirements with the virtual environment's own pip
echo Installing requirements...
"venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
    echo Failed to install requirements. Check your internet connection and try again.
    echo.
    echo Setup did not finish.
    pause
    exit /b 1
)
echo Requirements installed successfully.

REM Report which optional programs (Tesseract, Ghostscript, Word/LibreOffice) were found
"venv\Scripts\python.exe" src\pdfsuite.py check
echo.

call start.bat
