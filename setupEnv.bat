@echo off
REM Change to the directory where this batch file is located
cd /d "%~dp0"

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Python is not installed.
    exit /b 1
)
echo Python is installed.

REM Check if pip is installed
pip --version >nul 2>&1
if errorlevel 1 (
    echo pip is not installed.
    exit /b 1
)
echo pip is installed.

REM Check if virtual environment already exists
if exist "venv\" (
    echo Virtual environment already exists.
) else (
    REM Create virtual environment
    python -m venv venv
    if errorlevel 1 (
        echo Failed to create virtual environment.
        exit /b 1
    )
    echo Virtual environment created.
)

REM Activate virtual environment
call venv\Scripts\activate.bat
echo Virtual environment activated.

REM Install requirements if requirements.txt exists
if exist "requirements.txt" (
    echo Installing requirements...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo Failed to install requirements.
        exit /b 1
    )
    echo Requirements installed successfully.
) else (
    echo requirements.txt not found in the current directory.
)

REM Report which optional programs (Tesseract, Ghostscript, Word/LibreOffice) were found
python src\pdfsuite.py check
echo.

REM Call start.bat if it exists
if exist "start.bat" (
    echo Calling start.bat...
    call start.bat
) else (
    echo start.bat not found in the current directory.
)