@echo off
setlocal EnableExtensions EnableDelayedExpansion
REM Frontend build script (Windows)
REM - Finds Node.js/npm even if not on PATH
REM - Installs dependencies
REM - Runs TypeScript check + Vite build

set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%.."
for %%I in ("%PROJECT_ROOT%") do set "PROJECT_ROOT=%%~fI\"
set "FRONTEND_DIR=%PROJECT_ROOT%frontend"

echo ========================================
echo Pallet Manager Frontend Build
echo ========================================
echo Project root: %PROJECT_ROOT%
echo Frontend dir: %FRONTEND_DIR%
echo.

if not exist "%FRONTEND_DIR%\package.json" (
    echo ERROR: frontend\package.json not found.
    exit /b 1
)

set "NODE_DIR="
where node >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    for /f "usebackq delims=" %%P in (`where node`) do (
        set "NODE_EXE=%%P"
        goto :node_found
    )
)

for %%D in ("%ProgramFiles%\nodejs" "%ProgramFiles(x86)%\nodejs" "%LocalAppData%\Programs\nodejs") do (
    if exist "%%~D\node.exe" (
        set "NODE_DIR=%%~D"
        set "PATH=%%~D;%PATH%"
        set "NODE_EXE=%%~D\node.exe"
        goto :node_found
    )
)

echo ERROR: Node.js was not found.
echo Install Node.js LTS, then rerun this script.
echo Suggested install command:
echo   winget install --id OpenJS.NodeJS.LTS --exact
exit /b 1

:node_found
echo Using Node: %NODE_EXE%
node --version
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Node.js command failed.
    exit /b 1
)

where npm >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: npm not found even though Node.js exists.
    exit /b 1
)

echo Using npm:
call npm --version
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: npm command failed.
    exit /b 1
)
echo.

cd /d "%FRONTEND_DIR%"

if exist "package-lock.json" (
    echo [1/2] Installing dependencies with npm ci...
    call npm ci
) else (
    echo [1/2] Installing dependencies with npm install...
    call npm install
)
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Dependency installation failed.
    exit /b 1
)

echo [2/2] Running frontend build (tsc ^& vite build)...
call npm run build
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Frontend build failed.
    exit /b 1
)

echo.
echo Frontend build complete.
echo Output: %FRONTEND_DIR%\dist
exit /b 0
