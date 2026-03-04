@echo off
setlocal enabledelayedexpansion
REM Pallet Manager - Initial Developer Setup
REM Installs all tools needed for automatic updates and development

echo ========================================
echo Pallet Manager - Initial Setup
echo ========================================
echo.
echo This script will install the following tools:
echo - Chocolatey (package manager)
echo - Git (version control)
echo - Python 3.11+ (for building)
echo - Pip (Python package manager)
echo.
echo Administrator privileges are REQUIRED for installation.
echo.
set /p confirm="Do you want to continue? (y/N): "
if /i not "%confirm%"=="y" goto :cancel

echo.
echo Checking prerequisites...
echo.

REM Check if running as administrator
echo Checking administrator privileges...
net session >nul 2>&1
if %errorLevel% == 0 (
    echo ✓ Running with administrator privileges.
) else (
    echo ✗ ERROR: Administrator privileges required!
    echo Please right-click this script and select "Run as administrator"
    echo.
    echo Press any key to exit...
    pause >nul
    exit /b 1
)

echo.
echo Starting installation process...
echo.

echo ========================================
echo Step 1: Installing Chocolatey
echo ========================================
echo.

REM Check if Chocolatey is already installed by looking for the directory
if exist "%ALLUSERSPROFILE%\chocolatey\bin\choco.exe" (
    echo ✓ Chocolatey is already installed.
    goto :choco_done
)

echo Installing Chocolatey...

REM Create temp directory if it doesn't exist
if not exist "%TEMP%" mkdir "%TEMP%" 2>nul

REM Download Chocolatey installer
echo Downloading Chocolatey installer...
powershell -NoProfile -ExecutionPolicy Bypass -Command "try { Invoke-WebRequest -Uri 'https://chocolatey.org/install.ps1' -OutFile '%TEMP%\choco-install.ps1' -UseBasicParsing; exit 0 } catch { Write-Host 'Download failed'; exit 1 }" 2>nul

if errorlevel 1 (
    echo ✗ ERROR: Failed to download Chocolatey installer.
    echo Please check your internet connection and try again.
    goto :error
)

REM Run the installer
echo Installing Chocolatey...
powershell -NoProfile -ExecutionPolicy Bypass -Command "try { & '%TEMP%\choco-install.ps1'; exit $LASTEXITCODE } catch { Write-Host 'Installation failed'; exit 1 }" 2>nul

if errorlevel 1 (
    echo ✗ ERROR: Failed to run Chocolatey installer.
    goto :error
)

REM Clean up temp file
del "%TEMP%\choco-install.ps1" 2>nul

REM Add Chocolatey to PATH for this session
set "PATH=%PATH%;%ALLUSERSPROFILE%\chocolatey\bin"

REM Verify Chocolatey installation
if exist "%ALLUSERSPROFILE%\chocolatey\bin\choco.exe" (
    echo ✓ Chocolatey installed successfully.
    echo.
) else (
    echo ✗ ERROR: Chocolatey installation verification failed.
    goto :error
)

:choco_done

echo ========================================
echo Step 2: Installing Git
echo ========================================
echo.

REM Check if Git is already installed
where git >nul 2>&1
if %errorLevel% == 0 (
    echo ✓ Git is already installed.
    goto :git_done
)

echo Installing Git via Chocolatey...

REM Install Git
echo Running: choco install git -y --params="/GitAndUnixToolsOnPath /WindowsTerminal /NoShellIntegration"
choco install git -y --params="/GitAndUnixToolsOnPath /WindowsTerminal /NoShellIntegration" 2>nul

if errorlevel 1 (
    echo ✗ ERROR: Failed to install Git via Chocolatey.
    echo.
    echo MANUAL ALTERNATIVE:
    echo 1. Download Git from: https://git-scm.com/download/win
    echo 2. Run the installer (accept all defaults)
    echo 3. Make sure to select "Git from the command line and also from 3rd-party software"
    echo 4. Re-run this script after manual installation.
    echo.
    goto :error
)

REM Verify Git installation
where git >nul 2>&1
if errorlevel 1 (
    echo ✗ ERROR: Git installation failed verification.
    goto :error
)

echo ✓ Git installed successfully.
echo.

:git_done

echo ========================================
echo Step 3: Installing Python
echo ========================================
echo.

REM Check if Python is already installed
where python >nul 2>&1
if %errorLevel% == 0 (
    python --version 2>nul | findstr "Python 3" >nul
    if %errorLevel% == 0 (
        echo ✓ Python 3.x is already installed.
        goto :python_done
    )
)

echo Installing Python via Chocolatey...

REM Install Python 3.11
echo Running: choco install python311 -y
choco install python311 -y 2>nul

if errorlevel 1 (
    echo ✗ ERROR: Failed to install Python via Chocolatey.
    echo.
    echo MANUAL ALTERNATIVE:
    echo 1. Download Python from: https://python.org/downloads/
    echo 2. Run the installer
    echo 3. IMPORTANT: Check "Add Python to PATH" during installation
    echo 4. Re-run this script after manual installation.
    echo.
    goto :error
)

REM Add Python to PATH for current session
if exist "C:\Python311" (
    set "PATH=%PATH%;C:\Python311;C:\Python311\Scripts"
)

REM Verify Python installation
python --version 2>nul | findstr "Python 3" >nul
if errorlevel 1 (
    echo ✗ ERROR: Python installation failed verification.
    goto :error
)

REM Verify Pip
python -m pip --version >nul 2>&1
if errorlevel 1 (
    echo ✗ WARNING: Pip may not be available.
) else (
    echo ✓ Pip is available.
)

echo ✓ Python installed successfully.
echo.

:python_done

echo ========================================
echo Step 4: Verifying Installations
echo ========================================
echo.

set "verification_errors=0"

echo Checking Chocolatey...
if exist "%ALLUSERSPROFILE%\chocolatey\bin\choco.exe" (
    echo ✓ Chocolatey: OK
) else (
    echo ✗ Chocolatey: NOT FOUND
    set /a "verification_errors+=1"
)

echo Checking Git...
where git >nul 2>&1
if %errorLevel% == 0 (
    echo ✓ Git: OK
) else (
    echo ✗ Git: NOT FOUND
    set /a "verification_errors+=1"
)

echo Checking Python...
where python >nul 2>&1
if %errorLevel% == 0 (
    python --version 2>nul | findstr "Python 3" >nul
    if %errorLevel% == 0 (
        echo ✓ Python: OK
    ) else (
        echo ✗ Python: Version 3.x required
        set /a "verification_errors+=1"
    )
) else (
    echo ✗ Python: NOT FOUND
    set /a "verification_errors+=1"
)

echo Checking Pip...
if %verification_errors% == 0 (
    python -m pip --version >nul 2>&1
    if %errorLevel% == 0 (
        echo ✓ Pip: OK
    ) else (
        echo ✗ Pip: NOT FOUND
        set /a "verification_errors+=1"
    )
)

echo.
if %verification_errors% gtr 0 (
    echo ⚠️  Some tools failed verification (%verification_errors% errors).
    echo.
    echo TROUBLESHOOTING:
    echo 1. Close and reopen Command Prompt as Administrator
    echo 2. Run this script again
    echo 3. If issues persist, install manually:
    echo   - Git: https://git-scm.com/download/win
    echo   - Python: https://python.org/downloads/
    echo.
    goto :error
) else (
    echo ✓ All tools verified successfully!
)

echo.
echo ========================================
echo 🎉 Setup Complete!
echo ========================================
echo.
echo All developer tools have been installed successfully!
echo.
echo NEXT STEPS:
echo ──────────────────────────────────────
echo 1. Close this Command Prompt window
echo 2. Open a NEW Command Prompt as Administrator
echo 3. Navigate to your project folder
echo 4. Run: scripts\update_from_github.bat
echo.
echo Your development environment is now ready! 🚀
echo.
echo Press any key to exit...
pause >nul
goto :eof

:error
echo.
echo ========================================
echo ❌ Setup Incomplete
echo ========================================
echo.
echo Some installations failed or need manual completion.
echo.
echo OPTIONS:
echo ──────────────────────────────────────
echo 1. Try running this script again as Administrator
echo 2. Install manually using the links below
echo 3. Check your internet connection
echo.
echo MANUAL INSTALLATION LINKS:
echo ──────────────────────────────────────
echo Chocolatey: https://chocolatey.org/install
echo Git:        https://git-scm.com/download/win
echo Python:     https://python.org/downloads/
echo.
echo After manual installation, re-run this script.
echo.
echo Press any key to exit...
pause >nul
exit /b 1

:cancel
echo.
echo ========================================
echo Setup Cancelled
echo ========================================
echo.
echo No tools were installed.
echo You can run this script again anytime.
echo.
echo Press any key to exit...
pause >nul
