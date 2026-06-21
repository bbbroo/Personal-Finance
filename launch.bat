@echo off
setlocal enabledelayedexpansion

set "ROOT=%~dp0"
set "BACKEND=%ROOT%backend"
set "FRONTEND=%ROOT%frontend"
set "LOGDIR=%ROOT%data\logs"
set "VENV=%BACKEND%\.venv"
set "PY=%VENV%\Scripts\python.exe"

if not exist "%LOGDIR%" mkdir "%LOGDIR%"

echo Local Finance launcher
echo Logs: %LOGDIR%

where python >nul 2>nul
if errorlevel 1 (
  echo Python 3.11+ is required and was not found on PATH.
  pause
  exit /b 1
)

where npm >nul 2>nul
if errorlevel 1 (
  echo Node.js/npm is required and was not found on PATH.
  pause
  exit /b 1
)

if not exist "%PY%" (
  echo Creating backend virtual environment...
  python -m venv "%VENV%"
  if errorlevel 1 (
    echo Failed to create Python virtual environment.
    pause
    exit /b 1
  )
)

echo Installing backend dependencies...
"%PY%" -m pip install -r "%BACKEND%\requirements.txt" >> "%LOGDIR%\launch.log" 2>&1
if errorlevel 1 (
  echo Backend dependency install failed. See data\logs\launch.log
  pause
  exit /b 1
)

echo Installing frontend dependencies if needed...
pushd "%FRONTEND%"
if not exist node_modules (
  npm install >> "%LOGDIR%\launch.log" 2>&1
  if errorlevel 1 (
    echo Frontend dependency install failed. See data\logs\launch.log
    popd
    pause
    exit /b 1
  )
)
popd

echo Running database migrations...
pushd "%BACKEND%"
"%PY%" -m alembic upgrade head >> "%LOGDIR%\launch.log" 2>&1
if errorlevel 1 (
  echo Database migration failed. See data\logs\launch.log
  popd
  pause
  exit /b 1
)
popd

echo Starting backend on 127.0.0.1:8000...
start "Local Finance API" /min "%BACKEND%\run_backend.bat"

echo Starting frontend on 127.0.0.1:5173...
start "Local Finance UI" /min "%FRONTEND%\run_frontend.bat"

timeout /t 4 /nobreak >nul
start http://127.0.0.1:5173

echo App launched. Close the Local Finance API and UI windows to stop it.
pause
