@echo off
set "FRONTEND=%~dp0"
set "ROOT=%FRONTEND%.."
set "LOGDIR=%ROOT%\data\logs"
if not exist "%LOGDIR%" mkdir "%LOGDIR%"
cd /d "%FRONTEND%"
npm run dev >> "%LOGDIR%\frontend-vite.log" 2>&1
