@echo off
setlocal enabledelayedexpansion
REM Robust reportlab installation script for Windows
REM Handles common installation issues and ensures reportlab is installed

echo ========================================
echo Installing reportlab for PDF Support
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python is not installed!
    echo Please install Python from: https://www.python.org/downloads/
    endlocal
    exit /b 1
)

echo [1/4] Upgrading pip to latest version...
python -m pip install --upgrade pip --quiet
if errorlevel 1 (
    echo ⚠️  WARNING: pip upgrade failed, trying alternative method...
    python -m ensurepip --upgrade
)
echo ✅ pip upgraded
echo.

echo [2/4] Installing setuptools and wheel (required for some packages)...
python -m pip install --upgrade setuptools wheel --quiet
if errorlevel 1 (
    echo ⚠️  WARNING: setuptools/wheel installation had issues, continuing...
)
echo ✅ Build tools ready
echo.

echo [3/4] Installing reportlab...
echo This may take a few minutes...
echo.

REM Try installing reportlab with verbose output
python -m pip install reportlab --upgrade --no-cache-dir
if errorlevel 1 (
    echo.
    echo ❌ Standard installation failed. Trying alternative methods...
    echo.
    
    REM Try installing from wheel
    echo Attempting to install from pre-built wheel...
    python -m pip install reportlab --only-binary :all: --upgrade
    if errorlevel 1 (
        echo.
        echo ❌ Wheel installation also failed.
        echo.
        echo Common causes and solutions:
        echo.
        echo 1. Missing C Compiler (most common):
        echo    reportlab requires a C compiler to build.
        echo    Install Microsoft Visual C++ Build Tools:
        echo    https://visualstudio.microsoft.com/visual-cpp-build-tools/
        echo    OR install Visual Studio Community (free)
        echo.
        echo 2. Network/Firewall issues:
        echo    Check your internet connection
        echo    Try: python -m pip install reportlab --trusted-host pypi.org --trusted-host files.pythonhosted.org
        echo.
        echo 3. Outdated Python:
        echo    Ensure you're using Python 3.11 or newer
        echo    Check version: python --version
        echo.
        echo 4. Permission issues:
        echo    Try running as administrator
        echo    Or use: python -m pip install --user reportlab
        echo.
        endlocal
        exit /b 1
    )
)

echo.
echo [4/4] Verifying reportlab installation...
python -c "import reportlab; print('✅ reportlab version:', reportlab.Version)" 2>nul
if errorlevel 1 (
    echo ❌ reportlab installation verification failed
    echo The package may not be working correctly.
    endlocal
    exit /b 1
)

echo.
echo ========================================
echo ✅ reportlab installed successfully!
echo ========================================
echo.
echo PDF export functionality is now available in the application.
echo.
endlocal
exit /b 0


