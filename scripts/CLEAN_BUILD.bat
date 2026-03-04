@echo off
REM Ultra-aggressive cleanup script for Windows
REM This will delete ALL build artifacts and cache

cd /d "%~dp0.."

echo ========================================
echo CLEANING ALL BUILD ARTIFACTS
echo ========================================
echo.

REM Delete PyInstaller build directories
if exist "build" (
    echo Removing build/...
    rmdir /s /q "build"
)

if exist "dist" (
    echo Removing dist/...
    rmdir /s /q "dist"
)

REM Delete executable
if exist "Pallet Manager.exe" (
    echo Removing Pallet Manager.exe...
    del /f /q "Pallet Manager.exe"
)

REM Delete ALL __pycache__ directories recursively
echo Removing all __pycache__ directories...
for /d /r . %%d in (__pycache__) do @if exist "%%d" rmdir /s /q "%%d"

REM Delete .pyc files
echo Removing all .pyc files...
del /s /q *.pyc 2>nul

REM Delete PyInstaller spec cache
if exist "%LOCALAPPDATA%\pyinstaller" (
    echo Removing PyInstaller cache...
    rmdir /s /q "%LOCALAPPDATA%\pyinstaller"
)

if exist "%TEMP%\_MEI*" (
    echo Removing PyInstaller temp files...
    rmdir /s /q "%TEMP%\_MEI*" 2>nul
)

echo.
echo ========================================
echo CLEANUP COMPLETE!
echo ========================================
echo.
echo Now run: scripts\build_windows.bat
echo.
pause








