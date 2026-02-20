@echo off
echo Starting Morshed's Deletor Application...
cd /d "%~dp0backend"
start "Backend Server" cmd /k "..\.venv\Scripts\python.exe main.py"
echo Waiting for server to start...
timeout /t 3 /nobreak >nul
start http://localhost:8000
exit
