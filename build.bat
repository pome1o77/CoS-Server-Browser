
@echo off
title CoS Server Browser - Build

echo =====================================
echo   Creatures of Sonaria Server Browser
echo   Building Windows executable...
echo =====================================
echo.

cd /d "%~dp0"

echo Installing or updating PyInstaller...
py -m pip install --upgrade pyinstaller

if errorlevel 1 (
    echo.
    echo ERROR: Could not install PyInstaller.
    pause
    exit /b 1
)

echo.
echo Building EXE...

py -m PyInstaller --noconfirm --clean --onefile --windowed --name "CoS_Server_Browser" "%~dp0cos_server_browser.py"

if errorlevel 1 (
    echo.
    echo ERROR: Build failed.
    pause
    exit /b 1
)

echo.
echo =====================================
echo BUILD COMPLETE!
echo EXE location: dist\CoS_Server_Browser.exe
echo =====================================
pause
