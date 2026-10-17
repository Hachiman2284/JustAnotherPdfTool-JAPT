@echo off
cd /d "%~dp0"
REM Use the virtual environment created by setupEnv.bat when it exists.
if exist "venv\Scripts\python.exe" (
    "venv\Scripts\python.exe" src/pdfsuite.py
) else (
    python src/pdfsuite.py
)
pause