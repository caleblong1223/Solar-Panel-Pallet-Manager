@echo off
REM Super simple script to rebuild the exe - minimal approach
REM Just run this after making code changes

cd /d "%~dp0.."

echo Rebuilding exe...
echo.

REM Check if reportlab is installed (required for PDF creation)
python -c "import reportlab" 2>nul
if errorlevel 1 (
    echo WARNING: reportlab is not installed. PDF creation will not work.
    echo Installing reportlab...
    pip install reportlab
    if errorlevel 1 (
        echo ERROR: Failed to install reportlab. Please install manually:
        echo   pip install reportlab
        pause
        exit /b 1
    )
)

REM Check if jinja2 is installed (dependency of pandas/reportlab)
python -c "import jinja2" 2>nul
if errorlevel 1 (
    echo Installing jinja2...
    pip install jinja2
    if errorlevel 1 (
        echo ERROR: Failed to install jinja2. Please install manually:
        echo   pip install jinja2
        pause
        exit /b 1
    )
)

REM Check if Pillow is installed (dependency of reportlab for image support)
python -c "import PIL" 2>nul
if errorlevel 1 (
    echo Installing Pillow...
    pip install Pillow
    if errorlevel 1 (
        echo WARNING: Failed to install Pillow. PDF creation may have limited functionality.
        echo   pip install Pillow
    )
)

python -m PyInstaller pallet_builder.spec --clean --noconfirm --distpath=.

if errorlevel 1 (
    echo Build failed!
    pause
    exit /b 1
)

echo.
echo Done! New exe: Pallet Manager.exe
pause

