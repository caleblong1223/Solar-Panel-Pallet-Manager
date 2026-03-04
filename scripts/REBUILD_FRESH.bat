@echo off
REM Complete fresh rebuild - runs cleanup then build
REM This ensures absolutely no cached data is used

cd /d "%~dp0"

echo ========================================
echo FRESH REBUILD
echo ========================================
echo.
echo Step 1: Cleaning all artifacts...
call CLEAN_BUILD.bat

echo.
echo Step 2: Building application...
call build_windows.bat








