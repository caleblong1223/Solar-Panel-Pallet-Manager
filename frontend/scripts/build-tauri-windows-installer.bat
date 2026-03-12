@echo off
setlocal

REM Build the Windows Tauri desktop app and copy the supported MSI installer into dist\installers.
REM Run this from anywhere; the script resolves the frontend directory itself.

set "SCRIPT_DIR=%~dp0"
set "FRONTEND_DIR=%SCRIPT_DIR%.."

if "%VITE_PRIMARY_API_BASE_URL%"=="" set "VITE_PRIMARY_API_BASE_URL=http://10.20.10.100:8001/api/v1"
if "%VITE_FALLBACK_API_BASE_URL%"=="" set "VITE_FALLBACK_API_BASE_URL=http://127.0.0.1:8010/api/v1"

echo Using VITE_PRIMARY_API_BASE_URL=%VITE_PRIMARY_API_BASE_URL%
echo Using VITE_FALLBACK_API_BASE_URL=%VITE_FALLBACK_API_BASE_URL%
echo.

pushd "%FRONTEND_DIR%"
if errorlevel 1 exit /b 1

call npm install
if errorlevel 1 goto :fail

call npm run build:desktop
if errorlevel 1 goto :fail

echo.
echo Build complete.
echo MSI: %FRONTEND_DIR%\dist\installers\Pallet Manager_2.0.0_x64_en-US.msi

popd
exit /b 0

:fail
set "ERR=%ERRORLEVEL%"
popd
exit /b %ERR%
