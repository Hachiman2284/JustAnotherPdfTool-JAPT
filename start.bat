@echo off
cd /d "%~dp0"
REM The tool runs from the virtual environment created by setupEnv.bat.
if exist "venv\Scripts\python.exe" (
    "venv\Scripts\python.exe" src\pdfsuite.py
) else (
    echo JAP-T is not set up yet. Double-click setupEnv.bat first.
)
pause
