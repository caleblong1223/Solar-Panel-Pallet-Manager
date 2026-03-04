@echo off
setlocal enabledelayedexpansion
REM Complete Windows Setup Script
REM This script checks for Python, installs dependencies, and builds the .exe
REM Handles cases where Python is installed but not on PATH

echo ========================================
echo Pallet Manager - Windows Setup
echo ========================================
echo.

REM Initialize variables
set "PYTHON_CMD=python"
set PYTHON_FOUND=0

REM Step 1: Check if Python is installed and on PATH
echo [1/5] Checking for Python...
python --version >nul 2>&1
if errorlevel 1 (
    REM Python not on PATH, check common installation locations
    echo Python not found on PATH. Checking common installation locations...
    echo.
    
    REM Check common Python installation paths
    if exist "C:\Python311\python.exe" (
        set "PYTHON_CMD=C:\Python311\python.exe"
        set PYTHON_FOUND=1
        goto :found_python
    )
    if exist "C:\Python312\python.exe" (
        set "PYTHON_CMD=C:\Python312\python.exe"
        set PYTHON_FOUND=1
        goto :found_python
    )
    if exist "C:\Python310\python.exe" (
        set "PYTHON_CMD=C:\Python310\python.exe"
        set PYTHON_FOUND=1
        goto :found_python
    )
    if exist "C:\Program Files\Python311\python.exe" (
        set "PYTHON_CMD=C:\Program Files\Python311\python.exe"
        set PYTHON_FOUND=1
        goto :found_python
    )
    if exist "C:\Program Files\Python312\python.exe" (
        set "PYTHON_CMD=C:\Program Files\Python312\python.exe"
        set PYTHON_FOUND=1
        goto :found_python
    )
    if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" (
        set "PYTHON_CMD=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
        set PYTHON_FOUND=1
        goto :found_python
    )
    if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
        set "PYTHON_CMD=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
        set PYTHON_FOUND=1
        goto :found_python
    )
    if exist "%LOCALAPPDATA%\Programs\Python\Python310\python.exe" (
        set "PYTHON_CMD=%LOCALAPPDATA%\Programs\Python\Python310\python.exe"
        set PYTHON_FOUND=1
        goto :found_python
    )
    
    REM Python not found anywhere
    echo.
    echo ❌ Python is not installed!
    echo.
    echo Python is required to build the application.
    echo.
    echo Please install Python:
    echo   1. Go to: https://www.python.org/downloads/
    echo   2. Download Python 3.11 or newer
    echo   3. Run the installer
    echo   4. IMPORTANT: Check "Add Python to PATH" during installation
    echo   5. Restart this script after installing Python
    echo.
    echo Opening Python download page...
    start https://www.python.org/downloads/
    pause
    exit /b 1
)

:found_python
if !PYTHON_FOUND!==1 (
    echo.
    echo ✅ Found Python at: !PYTHON_CMD!
    echo.
    echo ⚠️  Python is installed but not on PATH.
    echo.
    echo You have two options:
    echo.
    echo Option 1 (Recommended): Add Python to PATH
    echo   1. Search Windows for "Environment Variables"
    echo   2. Click "Edit the system environment variables"
    echo   3. Click "Environment Variables" button
    echo   4. Under "System variables", find "Path" and click "Edit"
    echo   5. Click "New" and add the Python directory
    echo   6. Click "New" and add the Python Scripts directory
    echo   7. Click OK on all dialogs
    echo   8. Close and reopen this script
    echo.
    echo Option 2: Use Python directly (this session only)
    echo   This script will use the found Python for this session.
    echo   Press any key to continue with Option 2...
    pause >nul
) else (
    REM Python is on PATH, use standard command
    python --version
    echo ✅ Python is installed and on PATH!
)

echo.

REM Step 2: Check if pip is available
echo [2/5] Checking for pip...
"%PYTHON_CMD%" -m pip --version >nul 2>&1
if errorlevel 1 (
    echo ❌ pip is not available!
    echo Installing pip...
    "%PYTHON_CMD%" -m ensurepip --upgrade
    if errorlevel 1 (
        echo ERROR: Failed to install pip
        pause
        exit /b 1
    )
)

"%PYTHON_CMD%" -m pip --version
if errorlevel 1 (
    echo ERROR: pip verification failed
    pause
    exit /b 1
)
echo ✅ pip is available!
echo.

REM Step 3: Install/Upgrade dependencies
echo [3/5] Installing dependencies...
echo.

REM Upgrade pip first
echo Upgrading pip...
"%PYTHON_CMD%" -m pip install --upgrade pip --quiet
if errorlevel 1 (
    echo WARNING: pip upgrade failed, continuing anyway...
)

REM Install PyInstaller
echo Installing PyInstaller...
"%PYTHON_CMD%" -m pip install pyinstaller --quiet
if errorlevel 1 (
    echo ERROR: Failed to install PyInstaller
    echo.
    echo Try running manually:
    echo   "%PYTHON_CMD%" -m pip install pyinstaller
    pause
    exit /b 1
)

REM Install project dependencies
echo Installing project dependencies...
if exist requirements.txt (
    echo Installing from requirements.txt (including reportlab)...
    "%PYTHON_CMD%" -m pip install -r requirements.txt
    if errorlevel 1 (
        echo.
        echo ⚠️  WARNING: Some dependencies failed to install
        echo.
        echo Attempting to install reportlab separately (required for PDF)...
        call "%~dp0install_reportlab.bat"
        if errorlevel 1 (
            echo.
            echo ⚠️  reportlab installation failed. PDF features will be disabled.
            echo You can install it later with: "%PYTHON_CMD%" -m pip install reportlab
            echo.
        )
        echo.
        echo Installing remaining dependencies...
        "%PYTHON_CMD%" -m pip install openpyxl pandas python-dateutil pyyaml pyinstaller
    )
) else (
    echo WARNING: requirements.txt not found, installing core dependencies...
    "%PYTHON_CMD%" -m pip install openpyxl pandas python-dateutil pyyaml reportlab pyinstaller
    if errorlevel 1 (
        echo WARNING: Some dependencies may have failed to install
        echo Attempting reportlab installation...
        call "%~dp0install_reportlab.bat"
    )
)

REM Verify dependencies
echo.
echo Verifying dependencies...
"%PYTHON_CMD%" verify_dependencies.py
if errorlevel 1 (
    echo.
    echo WARNING: Some dependencies may be missing
    echo You can install them manually with:
    echo   "%PYTHON_CMD%" -m pip install -r requirements.txt
    echo.
)

echo ✅ Dependencies installed!
echo.

REM Step 4: Check if PyInstaller is accessible
echo [4/5] Verifying PyInstaller...
"%PYTHON_CMD%" -c "import PyInstaller" 2>nul
if errorlevel 1 (
    echo ERROR: PyInstaller not accessible
    echo Try running: "%PYTHON_CMD%" -m pip install pyinstaller
    pause
    exit /b 1
)

REM Step 5: Build the executable
echo [5/5] Building executable...
echo.
"%PYTHON_CMD%" -m PyInstaller pallet_builder.spec

if errorlevel 1 (
    echo.
    echo ❌ Build failed!
    echo.
    echo Check the error messages above for details.
    echo.
    echo Common issues:
    echo   • Missing dependencies - run: "%PYTHON_CMD%" -m pip install -r requirements.txt
    echo   • PyInstaller not found - run: "%PYTHON_CMD%" -m pip install pyinstaller
    echo   • Check that pallet_builder.spec exists in the current directory
    echo.
    pause
    exit /b 1
)

echo.
echo ========================================
echo ✅ SETUP COMPLETE!
echo ========================================
echo.
echo Your executable is ready:
echo   📁 dist\Pallet Manager.exe
echo.
echo You can now:
echo   • Copy the .exe to any Windows computer
echo   • No Python installation needed on target machines
echo   • Just double-click to run!
echo.
if !PYTHON_FOUND!==1 (
    echo.
    echo ⚠️  NOTE: Python is not on PATH.
    echo    For future builds, consider adding Python to PATH.
    echo    Run add_python_to_path.bat for help.
    echo.
)
pause
endlocal
