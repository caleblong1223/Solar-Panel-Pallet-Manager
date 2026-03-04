@echo off
setlocal EnableExtensions
REM Deterministic Windows EXE build script.
REM - Finds Python
REM - Installs all compile dependencies
REM - Verifies imports (including PDF stack)
REM - Builds dist\Pallet Manager.exe using pallet_builder.spec

set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%.."
for %%I in ("%PROJECT_ROOT%") do set "PROJECT_ROOT=%%~fI\"
cd /d "%PROJECT_ROOT%"

set "SKIP_CLEAN=0"
set "DEPS_ONLY=0"
set "SKIP_SUMATRA=0"

if /I "%~1"=="--no-clean" set "SKIP_CLEAN=1"
if /I "%~1"=="--deps-only" set "DEPS_ONLY=1"
if /I "%~1"=="--skip-sumatra" set "SKIP_SUMATRA=1"

echo ========================================
echo Pallet Manager Windows Build
echo ========================================
echo Project root: %PROJECT_ROOT%
echo.

set "PYTHON_CMD="
python --version >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    set "PYTHON_CMD=python"
) else (
    py -3 --version >nul 2>&1
    if %ERRORLEVEL% EQU 0 (
        set "PYTHON_CMD=py -3"
    )
)

if "%PYTHON_CMD%"=="" (
    echo ERROR: Python 3 was not found.
    echo Install Python 3.10+ and ensure either "python" or "py -3" is available.
    exit /b 1
)

echo Using Python command: %PYTHON_CMD%
%PYTHON_CMD% --version
echo.

echo [1/5] Ensuring pip...
%PYTHON_CMD% -m pip --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    %PYTHON_CMD% -m ensurepip --upgrade
    if %ERRORLEVEL% NEQ 0 (
        echo ERROR: Failed to bootstrap pip.
        exit /b 1
    )
)

echo [2/5] Installing compile dependencies...
%PYTHON_CMD% -m pip install --upgrade pip
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: pip upgrade failed.
    exit /b 1
)

if exist "requirements.txt" (
    %PYTHON_CMD% -m pip install -r requirements.txt
    if %ERRORLEVEL% NEQ 0 (
        echo ERROR: Failed installing requirements.txt.
        exit /b 1
    )
)

%PYTHON_CMD% -m pip install pyinstaller pyinstaller-hooks-contrib reportlab jinja2 Pillow pywin32 PyPDF2 openpyxl pandas pyyaml python-dateutil
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed installing explicit build dependencies.
    exit /b 1
)

echo [3/5] Verifying required imports...
%PYTHON_CMD% -c "import PyInstaller, reportlab, jinja2, PIL, win32com, PyPDF2, openpyxl, pandas, yaml, dateutil; print('Dependency verification passed')"
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Import verification failed.
    exit /b 1
)

if "%DEPS_ONLY%"=="1" (
    echo [4/5] --deps-only selected. Dependency setup completed.
    echo You can now run: scripts\build_windows.bat
    exit /b 0
)

if "%SKIP_SUMATRA%"=="0" (
    echo [4/5] Optional SumatraPDF bundle check...
    if not exist "external_tools\SumatraPDF\SumatraPDF.exe" (
        if exist "scripts\download_sumatrapdf.py" (
            echo SumatraPDF not found. Attempting automatic download ^(non-fatal^)...
            %PYTHON_CMD% scripts\download_sumatrapdf.py
            if %ERRORLEVEL% NEQ 0 (
                echo WARNING: SumatraPDF download failed. Build continues without it.
            )
        ) else (
            echo WARNING: scripts\download_sumatrapdf.py not found. Skipping SumatraPDF step.
        )
    ) else (
        echo SumatraPDF already present: external_tools\SumatraPDF\SumatraPDF.exe
    )
) else (
    echo [4/5] SumatraPDF step skipped by flag.
)

if not exist "pallet_builder.spec" (
    echo ERROR: Missing pallet_builder.spec in project root.
    exit /b 1
)

if "%SKIP_CLEAN%"=="0" (
    echo [5/5] Cleaning prior build outputs...
    if exist "build" rmdir /s /q "build"
    if exist "dist" rmdir /s /q "dist"
) else (
    echo [5/5] Skipping clean step.
)

echo Building EXE from pallet_builder.spec...
%PYTHON_CMD% -m PyInstaller pallet_builder.spec --clean --noconfirm
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Build failed.
    exit /b 1
)

if not exist "dist\Pallet Manager.exe" (
    echo ERROR: Build finished but dist\Pallet Manager.exe was not produced.
    exit /b 1
)

echo.
echo Build complete.
echo EXE path: %PROJECT_ROOT%dist\Pallet Manager.exe
echo To create installer: scripts\create_windows_installer.bat
exit /b 0
