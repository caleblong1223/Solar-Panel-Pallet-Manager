@echo off
REM Helper script to add Python to PATH on Windows
REM Run this as Administrator for best results

echo ========================================
echo Add Python to PATH - Helper Script
echo ========================================
echo.

REM Check for admin rights
net session >nul 2>&1
if errorlevel 1 (
    echo ⚠️  This script works best when run as Administrator.
    echo Right-click this file and select "Run as administrator"
    echo.
    echo Press any key to continue anyway (may have limited functionality)...
    pause >nul
    echo.
)

REM Find Python installation
echo Searching for Python installation...
set PYTHON_FOUND=0
set PYTHON_DIR=

REM Check common locations
if exist "C:\Python311\python.exe" (
    set "PYTHON_DIR=C:\Python311"
    set PYTHON_FOUND=1
) else if exist "C:\Python312\python.exe" (
    set "PYTHON_DIR=C:\Python312"
    set PYTHON_FOUND=1
) else if exist "C:\Python310\python.exe" (
    set "PYTHON_DIR=C:\Python310"
    set PYTHON_FOUND=1
) else if exist "C:\Program Files\Python311\python.exe" (
    set "PYTHON_DIR=C:\Program Files\Python311"
    set PYTHON_FOUND=1
) else if exist "C:\Program Files\Python312\python.exe" (
    set "PYTHON_DIR=C:\Program Files\Python312"
    set PYTHON_FOUND=1
) else if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" (
    set "PYTHON_DIR=%LOCALAPPDATA%\Programs\Python\Python311"
    set PYTHON_FOUND=1
) else if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
    set "PYTHON_DIR=%LOCALAPPDATA%\Programs\Python\Python312"
    set PYTHON_FOUND=1
) else if exist "%LOCALAPPDATA%\Programs\Python\Python310\python.exe" (
    set "PYTHON_DIR=%LOCALAPPDATA%\Programs\Python\Python310"
    set PYTHON_FOUND=1
)

if %PYTHON_FOUND%==0 (
    echo.
    echo ❌ Could not find Python installation automatically.
    echo.
    echo Please provide the Python installation directory:
    echo (e.g., C:\Python311 or C:\Program Files\Python311)
    echo.
    set /p PYTHON_DIR="Enter Python directory: "
    
    if not exist "%PYTHON_DIR%\python.exe" (
        echo.
        echo ❌ Python.exe not found at: %PYTHON_DIR%
        echo Please check the path and try again.
        pause
        exit /b 1
    )
)

echo.
echo ✅ Found Python at: %PYTHON_DIR%
echo.

REM Check if already on PATH
echo %PATH% | findstr /C:"%PYTHON_DIR%" >nul
if not errorlevel 1 (
    echo ✅ Python directory is already on PATH!
    echo.
    echo Current PATH includes: %PYTHON_DIR%
    pause
    exit /b 0
)

echo Adding Python to PATH...
echo.

REM Method 1: Try using setx (works for user PATH)
echo Attempting to add to user PATH...
setx PATH "%PATH%;%PYTHON_DIR%;%PYTHON_DIR%\Scripts" >nul 2>&1
if errorlevel 1 (
    echo ⚠️  Could not automatically add to PATH.
    echo.
    echo Please add manually:
    echo   1. Search Windows for "Environment Variables"
    echo   2. Click "Edit the system environment variables"
    echo   3. Click "Environment Variables" button
    echo   4. Under "User variables" or "System variables", find "Path" and click "Edit"
    echo   5. Click "New" and add: %PYTHON_DIR%
    echo   6. Click "New" and add: %PYTHON_DIR%\Scripts
    echo   7. Click OK on all dialogs
    echo   8. Close and reopen Command Prompt
    echo.
) else (
    echo ✅ Successfully added to PATH!
    echo.
    echo ⚠️  IMPORTANT: Close and reopen Command Prompt for changes to take effect.
    echo.
    echo The following paths were added:
    echo   • %PYTHON_DIR%
    echo   • %PYTHON_DIR%\Scripts
    echo.
)

echo Press any key to open Environment Variables dialog (optional)...
pause >nul

REM Try to open System Properties (Environment Variables)
start ms-settings:about

echo.
echo ========================================
echo Next Steps:
echo ========================================
echo 1. Close this Command Prompt window
echo 2. Open a NEW Command Prompt window
echo 3. Run: python --version
echo 4. If it works, run: setup_windows.bat
echo.
pause


