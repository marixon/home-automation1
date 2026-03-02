# Home Automation Project - Build Guide

## Prerequisites

### System Requirements
- **Operating System**: Windows, macOS, or Linux
- **Python**: 3.10 or higher
- **Git**: For version control (optional)

### Python Installation
1. Download Python from [python.org](https://www.python.org/downloads/)
2. During installation, check "Add Python to PATH"
3. Verify installation:
   ```bash
   python --version
   pip --version
   ```

## Project Setup

### 1. Clone the Project (if not already done)
```bash
# Clone the repository
git clone https://github.com/marixon/home-automation1.git
cd home-automation1

# Or navigate to existing project
cd .worktrees/home-automation-implementation
```

### 2. Set Up Virtual Environment

#### Windows (PowerShell):
```powershell
# Create virtual environment
python -m venv venv

# Activate virtual environment
.\venv\Scripts\Activate.ps1

# If you get execution policy error, run:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

#### Windows (Command Prompt):
```cmd
python -m venv venv
venv\Scripts\activate.bat
```

#### macOS/Linux:
```bash
python3 -m venv venv
source venv/bin/activate
```

**Verify activation**: Your terminal prompt should show `(venv)` at the beginning.

### 3. Install Dependencies

```bash
# Install production dependencies
pip install -r requirements.txt

# Install development dependencies (optional, for testing/development)
pip install -r requirements-dev.txt

# Install the package in development mode
pip install -e .
```

### 4. Verify Installation

```bash
# Check installed packages
pip list

# Test CLI tools are available
homeauto-scan --help
homeauto-config --help

# Run tests to verify installation
pytest --version
```

## Configuration

### 1. Create Configuration File

Copy the example configuration:
```bash
# Copy example config
copy config.example.yaml config.yaml
# or on Linux/macOS:
# cp config.example.yaml config.yaml
```

### 2. Edit Configuration

Edit `config.yaml` with your settings:

```yaml
# Basic configuration
settings:
  debug: false
  scan_timeout: 5
  max_threads: 10

# Device credentials (update with your actual credentials)
credentials:
  gate:
    username: "admin"
    password: "your_gate_password"
  camera:
    username: "admin"
    password: "your_camera_password"
  tuya:
    local_key: "your_tuya_local_key"
```

### 3. Initialize Database

The database will be created automatically on first run. You can also initialize it manually:

```bash
# Run the scanner to discover devices and populate database
homeauto-scan --mock  # Use --mock for testing without real devices
```

## Building the Project

### Development Build (Editable Installation)

```bash
# Already done with: pip install -e .
# This allows you to edit code without reinstalling
```

### Production Build (Package Distribution)

```bash
# Build distribution packages
python setup.py sdist bdist_wheel

# The built packages will be in dist/ directory:
# - dist/homeauto-0.1.0.tar.gz (source distribution)
# - dist/homeauto-0.1.0-py3-none-any.whl (wheel distribution)
```

### Install from Built Package

```bash
# Install from wheel (recommended)
pip install dist/homeauto-0.1.0-py3-none-any.whl

# Or install from source distribution
pip install dist/homeauto-0.1.0.tar.gz
```

## Running the Application

### 1. Command Line Tools

#### Device Discovery (Scanner):
```bash
# Scan for devices on local network
homeauto-scan

# Scan with mock devices (for testing)
homeauto-scan --mock

# Scan specific subnet
homeauto-scan --subnet 192.168.1.0/24

# Get help
homeauto-scan --help
```

#### Configuration Tool:
```bash
# List discovered devices
homeauto-config list

# Set device credentials
homeauto-config set-creds gate admin password123

# Test gate connection
homeauto-config test-gate gate-001

# Control gate
homeauto-config control-gate gate-001 open
homeauto-config control-gate gate-001 close

# Show configuration
homeauto-config show
```

### 2. Web Application

#### Start the Web Server:
```bash
# Method 1: Using Python module directly
python -m homeauto.web.api

# Method 2: Using uvicorn directly
uvicorn homeauto.web.api:app --host 0.0.0.0 --port 8000 --reload

# Method 3: Using the provided run script (if available)
python scripts/run_web.py
```

#### Access the Web Interface:
- Open browser and go to: `http://localhost:8000`
- API documentation: `http://localhost:8000/docs`
- Alternative interface: `http://localhost:8000/redoc`

#### Web Server Options:
```bash
# Development mode with auto-reload
uvicorn homeauto.web.api:app --reload

# Production mode (no auto-reload)
uvicorn homeauto.web.api:app --host 0.0.0.0 --port 8000

# With specific workers (for production)
uvicorn homeauto.web.api:app --host 0.0.0.0 --port 8000 --workers 4
```

## Testing

### Run All Tests
```bash
pytest

# With verbose output
pytest -v

# With coverage report
pytest --cov=homeauto --cov-report=html --cov-report=term
```

### Run Specific Test Categories
```bash
# Test device adapters
pytest tests/devices/ -v

# Test web API
pytest tests/web/ -v

# Test CLI tools
pytest tests/cli/ -v

# Test with specific marker
pytest -m "not slow"  # Skip slow tests
```

### View Coverage Report
After running tests with coverage:
```bash
# HTML report will be in htmlcov/ directory
# Open htmlcov/index.html in browser
```

## Development Workflow

### 1. Code Structure
```
homeauto/
├── __init__.py
├── cli/              # Command-line tools
├── config/           # Configuration management
├── database/         # Database models and repository
├── devices/          # Device adapters (gate, camera, tuya)
├── discovery/        # Network scanning and device identification
├── utils/            # Utilities (network, retry logic)
└── web/              # Web application (FastAPI)
```

### 2. Adding New Device Adapters
1. Create new file in `homeauto/devices/`
2. Inherit from `BaseDevice` class
3. Implement required methods:
   - `test_connection()`
   - `get_info()`
   - `get_status()`
4. Add to device adapter registry in `homeauto/web/api.py`

### 3. Code Quality Tools
```bash
# Format code with black
black homeauto/ tests/

# Check code style with flake8
flake8 homeauto/ tests/

# Type checking with mypy
mypy homeauto/

# Run all checks
python -m black homeauto/ tests/
python -m flake8 homeauto/ tests/
python -m mypy homeauto/
```

## Deployment

### 1. Production Considerations

#### Environment Variables:
```bash
# Set in production environment
export HOME_AUTO_DEBUG=false
export HOME_AUTO_DB_PATH=/var/lib/homeauto/homeauto.db
export HOME_AUTO_CONFIG_PATH=/etc/homeauto/config.yaml
```

#### Database Backup:
```bash
# Backup SQLite database
cp homeauto.db homeauto.db.backup.$(date +%Y%m%d)

# Or use SQLite backup command
sqlite3 homeauto.db ".backup homeauto.db.backup"
```

### 2. System Service (Linux)

Create systemd service file `/etc/systemd/system/homeauto.service`:
```ini
[Unit]
Description=Home Automation Web Service
After=network.target

[Service]
Type=simple
User=homeauto
WorkingDirectory=/opt/homeauto
Environment="PATH=/opt/homeauto/venv/bin"
ExecStart=/opt/homeauto/venv/bin/uvicorn homeauto.web.api:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start the service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable homeauto
sudo systemctl start homeauto
sudo systemctl status homeauto
```

### 3. Docker Deployment (Optional)

Create `Dockerfile`:
```dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "homeauto.web.api:app", "--host", "0.0.0.0", "--port", "8000"]
```

Build and run:
```bash
docker build -t homeauto .
docker run -p 8000:8000 homeauto
```

## Troubleshooting

### Common Issues

#### 1. Virtual Environment Issues
```bash
# If activation fails on Windows
.\venv\Scripts\activate

# If Python not found in venv
python -m venv --clear venv
```

#### 2. Dependency Installation Issues
```bash
# Upgrade pip first
python -m pip install --upgrade pip

# Install with no cache
pip install --no-cache-dir -r requirements.txt

# On Windows, may need Visual C++ Build Tools for some packages
```

#### 3. Database Issues
```bash
# Reset database (WARNING: deletes all data)
rm homeauto.db
# Database will be recreated on next run
```

#### 4. Web Server Issues
```bash
# Check if port is in use
netstat -ano | findstr :8000  # Windows
lsof -i :8000                 # macOS/Linux

# Run on different port
uvicorn homeauto.web.api:app --port 8080
```

### Debug Mode

Enable debug logging in `config.yaml`:
```yaml
settings:
  debug: true
  log_level: "DEBUG"
```

Or set environment variable:
```bash
export HOME_AUTO_DEBUG=true
```

## Getting Help

- Check `docs/` directory for documentation
- Run `--help` on any command
- View API documentation at `http://localhost:8000/docs`
- Check test coverage reports in `htmlcov/`

## Quick Start Summary

```bash
# 1. Navigate to project
cd .worktrees/home-automation-implementation

# 2. Activate virtual environment
.\venv\Scripts\Activate.ps1  # Windows PowerShell
# or
venv\Scripts\activate.bat    # Windows CMD
# or
source venv/bin/activate     # macOS/Linux

# 3. Install dependencies
pip install -r requirements.txt
pip install -e .

# 4. Configure
copy config.example.yaml config.yaml
# Edit config.yaml with your credentials

# 5. Test with mock devices
homeauto-scan --mock
homeauto-config list

# 6. Start web server
python -m homeauto.web.api

# 7. Open browser: http://localhost:8000
```

Enjoy your home automation system! 🏠
