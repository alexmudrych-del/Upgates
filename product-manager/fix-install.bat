@echo off
cd /d "%~dp0"
echo Cleaning npm cache...
call npm cache clean --force
echo.
echo Removing node_modules (ignore errors if folder is locked)...
if exist node_modules rd /s /q node_modules 2>nul
echo.
echo Installing dependencies...
call npm install
if errorlevel 1 (
  echo.
  echo INSTALACE SELHALA. Zkuste:
  echo 1. Zavrit Cursor a vsechny terminály, pak spustit tento skript znovu.
  echo 2. Nebo zkopirovat cely projekt do C:\Projects\Upgates a tam spustit: npm install
  pause
  exit /b 1
)
echo.
echo Hotovo. Spustte: npm start
pause
