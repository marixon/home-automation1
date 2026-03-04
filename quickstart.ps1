Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Home Automation Project - Quick Start" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if we're in the right directory
if (-not (Test-Path "setup.py")) {
    Write-Host "❌ Error: setup.py not found!" -ForegroundColor Red
    Write-Host "Please run this script from the project root directory." -ForegroundColor Yellow
    pause
    exit 1
}

Write-Host "Step 1: Checking Python installation..." -ForegroundColor Green
try {
    $pythonVersion = python --version 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Python found: $pythonVersion" -ForegroundColor Green
    } else {
        throw "Python not found"
    }
} catch {
    Write-Host "❌ Python not found! Please install Python 3.10+ from python.org" -ForegroundColor Red
    pause
    exit 1
}

Write-Host ""
Write-Host "Step 2: Setting up virtual environment..." -ForegroundColor Green
if (-not (Test-Path "venv")) {
    Write-Host "Creating virtual environment..." -ForegroundColor Yellow
    python -m venv venv
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Failed to create virtual environment" -ForegroundColor Red
        pause
        exit 1
    }
    Write-Host "✅ Virtual environment created" -ForegroundColor Green
} else {
    Write-Host "✅ Virtual environment already exists" -ForegroundColor Green
}

Write-Host ""
Write-Host "Step 3: Activating virtual environment..." -ForegroundColor Green
try {
    & .\venv\Scripts\Activate.ps1
    Write-Host "✅ Virtual environment activated" -ForegroundColor Green
} catch {
    Write-Host "❌ Failed to activate virtual environment" -ForegroundColor Red
    Write-Host "Trying alternative activation..." -ForegroundColor Yellow
    try {
        .\venv\Scripts\Activate.ps1
        Write-Host "✅ Virtual environment activated" -ForegroundColor Green
    } catch {
        Write-Host "❌ Failed to activate with alternative method" -ForegroundColor Red
        pause
        exit 1
    }
}

Write-Host ""
Write-Host "Step 4: Installing dependencies..." -ForegroundColor Green
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -e .
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Failed to install dependencies" -ForegroundColor Red
    pause
    exit 1
}
Write-Host "✅ Dependencies installed" -ForegroundColor Green

Write-Host ""
Write-Host "Step 5: Setting up configuration..." -ForegroundColor Green
if (-not (Test-Path "config.yaml")) {
    if (Test-Path "config.example.yaml") {
        Write-Host "Creating configuration file from example..." -ForegroundColor Yellow
        Copy-Item config.example.yaml config.yaml
        Write-Host "✅ Configuration file created" -ForegroundColor Green
        Write-Host ""
        Write-Host "⚠️  IMPORTANT: Please edit config.yaml with your device credentials!" -ForegroundColor Yellow
        Write-Host "   - Open config.yaml in a text editor" -ForegroundColor Yellow
        Write-Host "   - Update the credentials section with your device passwords" -ForegroundColor Yellow
        Write-Host ""
    } else {
        Write-Host "⚠️  Warning: config.example.yaml not found" -ForegroundColor Yellow
    }
} else {
    Write-Host "✅ Configuration file already exists" -ForegroundColor Green
}

Write-Host ""
Write-Host "Step 6: Testing installation..." -ForegroundColor Green
Write-Host "Running tests (this may take a moment)..." -ForegroundColor Yellow
python -m pytest tests/devices/test_gate.py -q
if ($LASTEXITCODE -ne 0) {
    Write-Host "⚠️  Some tests failed, but installation may still work" -ForegroundColor Yellow
} else {
    Write-Host "✅ Tests passed" -ForegroundColor Green
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Installation Complete! 🎉" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Available commands:" -ForegroundColor White
Write-Host ""
Write-Host "  1. Scan for devices:" -ForegroundColor Cyan
Write-Host "     homeauto-scan --mock" -ForegroundColor Gray
Write-Host ""
Write-Host "  2. List discovered devices:" -ForegroundColor Cyan
Write-Host "     homeauto-config list" -ForegroundColor Gray
Write-Host ""
Write-Host "  3. Start web interface:" -ForegroundColor Cyan
Write-Host "     python -m homeauto.web.api" -ForegroundColor Gray
Write-Host "     Then open: http://localhost:8000" -ForegroundColor Gray
Write-Host ""
Write-Host "  4. Get help:" -ForegroundColor Cyan
Write-Host "     homeauto-scan --help" -ForegroundColor Gray
Write-Host "     homeauto-config --help" -ForegroundColor Gray
Write-Host ""
Write-Host "For more details, see BUILD.md" -ForegroundColor Gray
Write-Host ""
pause
