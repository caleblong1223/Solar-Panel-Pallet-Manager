@echo off
REM Create Windows installer using NSIS
REM This creates a professional installer wizard

set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%.."
cd /d "%PROJECT_ROOT%"

echo ========================================
echo Creating Windows Installer
echo ========================================
echo.

REM Check if exe exists
if not exist "dist\Pallet Manager.exe" (
    echo ERROR: Pallet Manager.exe not found in dist folder
    echo Please run build_windows.bat first
    pause
    exit /b 1
)

REM Check if NSIS is installed
where makensis >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo NSIS ^(Nullsoft Scriptable Install System^) is not installed.
    echo.
    echo Please install NSIS from: https://nsis.sourceforge.io/Download
    echo.
    echo After installing NSIS, add it to your PATH or run:
    echo   "C:\Program Files ^(x86^)\NSIS\makensis.exe" create_windows_installer.nsi
    echo.
    pause
    exit /b 1
)

REM Create license file if it doesn't exist (must be in project root for /NOCD compile)
if not exist "installer_license.txt" (
    (
        echo Pallet Manager
        echo.
        echo Copyright ^(c^) 2024 Crossroads Solar
        echo.
        echo This software is provided as-is for use with solar panel
        echo pallet management. All rights reserved.
    ) > installer_license.txt
)

REM Build the installer
echo Building installer...
makensis /NOCD "%SCRIPT_DIR%create_windows_installer.nsi"

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ========================================
    echo Installer Created Successfully!
    echo ========================================
    echo.
    echo Installer location: dist\Pallet Manager-Setup.exe
    echo.
    echo Users can now double-click the installer and
    echo follow the installation wizard.
    echo.
) else (
    echo.
    echo ERROR: Installer creation failed
    echo.
)

pause

