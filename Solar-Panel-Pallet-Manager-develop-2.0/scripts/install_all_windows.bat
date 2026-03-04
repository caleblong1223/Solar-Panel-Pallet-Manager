@echo off
REM One-command installer creator for Windows
REM Builds app and creates professional installer

echo ========================================
echo Pallet Manager - Complete Installer Creator
echo ========================================
echo.

REM Get script directory
set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%.."

REM Step 1: Build the app
echo Step 1/2: Building application...
cd /d "%PROJECT_ROOT%"
call "%SCRIPT_DIR%build_windows.bat"
if %ERRORLEVEL% NEQ 0 (
    echo Build failed!
    pause
    exit /b 1
)

REM Step 2: Create installer
echo.
echo Step 2/2: Creating installer...
call "%SCRIPT_DIR%create_windows_installer.bat"

echo.
echo ========================================
echo Complete!
echo ========================================
echo.
echo Installer location: dist\Pallet Manager-Setup.exe
echo.
echo Users can now double-click the installer and
echo follow the installation wizard.
echo.

pause

