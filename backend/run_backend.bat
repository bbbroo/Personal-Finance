@echo off
set "BACKEND=%~dp0"
set "ROOT=%BACKEND%.."
set "LOGDIR=%ROOT%\data\logs"
if not exist "%LOGDIR%" mkdir "%LOGDIR%"
cd /d "%BACKEND%"
"%BACKEND%\.venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000 >> "%LOGDIR%\backend-uvicorn.log" 2>&1
