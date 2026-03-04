@echo off
REM Update from GitHub script for Pallet Manager (Windows)
REM Pulls latest changes and automatically rebuilds the application

echo ========================================
echo Pallet Manager - Update from GitHub
echo ========================================
echo.

REM Check if git is available
git --version >nul 2>&1
if errorlevel 1 (
    echo [91mX Error: Git is not installed or not in PATH[0m
    echo Please install Git and try again.
    pause
    exit /b 1
)

REM Check if this is a git repository
git rev-parse --git-dir >nul 2>&1
if errorlevel 1 (
    echo [91mX Error: This is not a Git repository[0m
    echo Please initialize the repository or clone from GitHub first.
    echo.
    echo To clone from GitHub:
    echo   git clone ^<your-github-repo-url^>
    echo   cd ^<repository-directory^>
    pause
    exit /b 1
)

REM Get current branch
for /f "tokens=*" %%i in ('git branch --show-current') do set CURRENT_BRANCH=%%i
echo [94mCurrent branch: %CURRENT_BRANCH%[0m
echo.

REM Check for uncommitted changes
git diff-index --quiet HEAD -- >nul 2>&1
if errorlevel 1 (
    echo [93m^! Warning: You have uncommitted changes[0m
    echo Your local changes will be preserved, but you may need to resolve conflicts.
    echo.
    set /p continue_anyway="Continue anyway? (y/N): "
    if /i not "!continue_anyway!"=="y" if /i not "!continue_anyway!"=="Y" (
        echo Update cancelled.
        pause
        exit /b 0
    )
    echo.
)

REM Fetch latest changes
echo [94mFetching latest changes from remote...[0m
git fetch origin
if errorlevel 1 (
    echo [91mX Failed to fetch from remote[0m
    pause
    exit /b 1
)

REM Check if we're behind remote
for /f %%i in ('git rev-list HEAD...origin/%CURRENT_BRANCH% --count 2^>nul') do set BEHIND_COUNT=%%i
if "%BEHIND_COUNT%"=="0" (
    echo [92mYour branch is already up to date![0m
    echo.
    set /p rebuild_anyway="Rebuild anyway? (y/N): "
    if /i not "!rebuild_anyway!"=="y" if /i not "!rebuild_anyway!"=="Y" (
        echo No update needed.
        pause
        exit /b 0
    )
) else (
    echo [94m%BEHIND_COUNT% new commits available[0m
    echo.
)

REM Pull changes
echo [94mPulling latest changes...[0m
git pull origin %CURRENT_BRANCH%
if errorlevel 1 (
    echo [91mX Failed to pull changes[0m
    echo.
    echo This might be due to merge conflicts. Please resolve them manually:
    echo   1. Check git status: git status
    echo   2. Resolve conflicts in the affected files
    echo   3. Commit the resolved changes: git commit
    pause
    exit /b 1
)

echo [92mSuccessfully updated from GitHub![0m
echo.

REM Automatically rebuild the application
echo [94mRebuilding application...[0m

REM Run Windows build script
if exist "scripts\install_all_windows.bat" (
    call scripts\install_all_windows.bat
) else (
    echo [91mX Build script not found: scripts\install_all_windows.bat[0m
    pause
    exit /b 1
)

echo.
echo [92mRebuild complete![0m
echo.
echo New installer available in dist\:
echo   • Pallet Manager-Setup.exe

echo.
echo [92mUpdate process complete![0m
echo.
echo To run the updated application:
echo   From source: python app\pallet_builder_gui.py
echo   Built app: See dist\ directory

pause



