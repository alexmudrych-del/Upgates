@echo off
cd /d "%~dp0"
echo Installing dependencies...
call npm install
if errorlevel 1 (
  echo npm install failed.
  pause
  exit /b 1
)
echo.
echo Starting server...
call npm start
pause
