@echo off
setlocal EnableExtensions
REM Create Windows installer using NSIS.

set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%.."
for %%I in ("%PROJECT_ROOT%") do set "PROJECT_ROOT=%%~fI\"
set "NSI_FILE=%SCRIPT_DIR%create_windows_installer.nsi"
set "LICENSE_FILE=%PROJECT_ROOT%installer_license.txt"
set "MAKENSIS_EXE=makensis"

cd /d "%PROJECT_ROOT%"

echo ========================================
echo Creating Windows Installer
echo ========================================
echo Project root: %PROJECT_ROOT%
echo.

if not exist "dist\Pallet Manager.exe" (
    echo ERROR: dist\Pallet Manager.exe not found.
    echo Run scripts\build_windows.bat first.
    exit /b 1
)

where makensis >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    if exist "C:\Program Files (x86)\NSIS\makensis.exe" (
        set "MAKENSIS_EXE=C:\Program Files (x86)\NSIS\makensis.exe"
    ) else (
        if exist "C:\Program Files\NSIS\makensis.exe" (
            set "MAKENSIS_EXE=C:\Program Files\NSIS\makensis.exe"
        ) else (
            echo ERROR: NSIS was not found.
            echo Install from: https://nsis.sourceforge.io/Download
            echo Then run this script again.
            exit /b 1
        )
    )
)

if not exist "%NSI_FILE%" (
    echo ERROR: NSIS script not found: %NSI_FILE%
    exit /b 1
)

if not exist "%LICENSE_FILE%" (
    (
        echo Pallet Manager
        echo.
        echo Copyright ^(c^) 2024 Crossroads Solar
        echo.
        echo This software is provided as-is for use with solar panel
        echo pallet management. All rights reserved.
    ) > "%LICENSE_FILE%"
)

echo Building installer with NSIS...
"%MAKENSIS_EXE%" /NOCD "%NSI_FILE%"
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Installer creation failed.
    exit /b 1
)

echo.
echo Installer created successfully.
echo Installer path: %PROJECT_ROOT%dist\Pallet Manager-Setup.exe
exit /b 0
