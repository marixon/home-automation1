@echo off
echo ========================================
echo   Home Automation Project - Quick Start
echo ========================================
echo.

REM Check if we're in the right directory
if not exist "setup.py" (
    echo ❌ Error: setup.py not found!
    echo Please run this script from the project root directory.
    pause
    exit /b 1
)

echo Step 1: Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python not found! Please install Python 3.10+ from python.org
    pause
    exit /b 1
)

echo ✅ Python found
python --version

echo.
echo Step 2: Setting up virtual environment...
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo ❌ Failed to create virtual environment
        pause
        exit /b 1
    )
    echo ✅ Virtual environment created
) else (
    echo ✅ Virtual environment already exists
)

echo.
echo Step 3: Activating virtual environment...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo ❌ Failed to activate virtual environment
    echo Trying PowerShell activation...
    powershell -Command "& {.\venv\Scripts\Activate.ps1}"
    if errorlevel 1 (
        echo ❌ Failed to activate with PowerShell too
        pause
        exit /b 1
    )
)
echo ✅ Virtual environment activated

echo.
echo Step 4: Installing dependencies...
pip install --upgrade pip
pip install -r requirements.txt
pip install -e .
if errorlevel 1 (
    echo ❌ Failed to install dependencies
    pause
    exit /b 1
)
echo ✅ Dependencies installed

echo.
echo Step 5: Setting up configuration...
if not exist "config.yaml" (
    if exist "config.example.yaml" (
        echo Creating configuration file from example...
        copy config.example.yaml config.yaml
        echo ✅ Configuration file created
        echo.
        echo ⚠️  IMPORTANT: Please edit config.yaml with your device credentials!
        echo    - Open config.yaml in a text editor
        echo    - Update the credentials section with your device passwords
        echo.
    ) else (
        echo ⚠️  Warning: config.example.yaml not found
    )
) else (
    echo ✅ Configuration file already exists
)

echo.
echo Step 6: Testing installation...
echo Running tests (this may take a moment)...
pytest tests/devices/test_gate.py -q
if errorlevel 1 (
    echo ⚠️  Some tests failed, but installation may still work
) else (
    echo ✅ Tests passed
)

echo.
echo ========================================
echo   Installation Complete! 🎉
echo ========================================
echo.
echo Available commands:
echo.
echo   1. Scan for devices:
echo      homeauto-scan --mock
echo.
echo   2. List discovered devices:
echo      homeauto-config list
echo.
echo   3. Start web interface:
echo      python -m homeauto.web.api
echo      Then open: http://localhost:8000
echo.
echo   4. Get help:
echo      homeauto-scan --help
echo      homeauto-config --help
echo.
echo For more details, see BUILD.md
echo.
pause
