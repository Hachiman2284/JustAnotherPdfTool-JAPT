@echo off
REM Change to the directory where this batch file is located
cd /d "%~dp0"

REM JAP-T's packages have ready-made Windows builds for Python 3.11 to 3.14.
set "CHECK=import sys; sys.exit(0 if (3, 11) <= sys.version_info[:2] <= (3, 14) else 1)"

REM Find a supported Python: "python" when it is on PATH and supported,
REM otherwise ask the "py" launcher (which the python.org installer adds even
REM when "Add python.exe to PATH" is left unticked) for each supported version,
REM newest first. This also picks 3.14 when a newer, unsupported Python is the
REM default.
set "PY="
python -c "%CHECK%" >nul 2>&1 && set "PY=python"
for %%V in (3.14 3.13 3.12 3.11) do (
    if not defined PY (
        py -%%V -c "%CHECK%" >nul 2>&1 && set "PY=py -%%V"
    )
)
if not defined PY (
    set "FOUND="
    for /f "delims=" %%A in ('python --version 2^>nul') do set "FOUND=%%A"
    for /f "delims=" %%A in ('py --version 2^>nul') do set "FOUND=%%A"
    if defined FOUND (
        REM "call" expands FOUND now; a plain %%FOUND%% would be read before it is set.
        call echo Found %%FOUND%%, but JAP-T needs Python 3.11, 3.12, 3.13 or 3.14.
    ) else (
        echo Python is not installed.
    )
    echo Install Python 3.14 from https://www.python.org/downloads/windows/
    echo You can keep any other Python you already have; JAP-T will find 3.14.
    echo.
    echo Setup did not finish.
    pause
    exit /b 1
)
echo Using Python: %PY%

REM A virtual environment left over from an unsupported Python (for example a
REM failed earlier attempt) is rebuilt with the Python found above.
if exist "venv\Scripts\python.exe" (
    "venv\Scripts\python.exe" -c "%CHECK%" >nul 2>&1
    if errorlevel 1 (
        echo The existing virtual environment uses an unsupported Python. Rebuilding it...
        rmdir /s /q venv
    )
)

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
