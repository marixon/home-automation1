# 🏠 Home Automation System

A Python-based home automation system that discovers devices on your local network, manages their configuration, and provides a web-based dashboard for monitoring and control.

## ✨ Features

### Device Discovery & Management
- **Network Scanning**: Automatically discovers devices on your local network
- **Device Identification**: Identifies device types (cameras, sensors, gates, switches) using port scanning and MAC address lookup
- **Configuration Management**: Secure credential storage and device configuration
- **Database Storage**: SQLite database for persistent device information

### Device Support
- **Hikvision Gate Controllers**: Full control via ISAPI protocol (open/close/toggle)
- **IP Cameras**: Basic camera support with ONVIF/HTTP protocols
- **Tuya Devices**: Support for Tuya sensors and switches (placeholder for future implementation)
- **Extensible Architecture**: Easy to add new device types

### User Interfaces
- **Web Dashboard**: Modern web interface built with FastAPI, Alpine.js, and Tailwind CSS
- **CLI Tools**: Command-line tools for scanning and configuration
- **REST API**: Full API for integration with other systems

### Advanced Features
- **Real-time Updates**: WebSocket support for live device status
- **Verbose Logging**: Detailed device communication logs for debugging
- **Mock Device Testing**: Test with simulated devices without real hardware
- **Comprehensive Testing**: 67% test coverage with comprehensive test suite

## 🚀 Quick Start

### Prerequisites
- Python 3.10 or higher
- Git (optional)

### Installation

#### Windows (Quickest Method):
```cmd
cd .worktrees\home-automation-implementation
quickstart.bat
```

#### Manual Installation:
```bash
# Clone the repository
git clone https://github.com/marixon/home-automation1.git
cd home-automation1/.worktrees/home-automation-implementation

# Create and activate virtual environment
python -m venv venv
venv\Scripts\activate.bat  # Windows
# or
source venv/bin/activate   # macOS/Linux

# Install dependencies
pip install -r requirements.txt
pip install -e .

# Configure the application
copy config.example.yaml config.yaml
# Edit config.yaml with your device credentials
```

### Configuration

Edit `config.yaml` with your device credentials:

```yaml
credentials:
  gate:
    username: "admin"
    password: "your_gate_password"
  camera:
    username: "admin"
    password: "your_camera_password"
  tuya:
    local_key: "your_tuya_local_key"

settings:
  debug: false
  scan_timeout: 5
  max_threads: 10
```

## 📖 Usage

### Device Discovery

```bash
# Scan for devices (use --mock for testing without real devices)
homeauto-scan --mock

# Scan with verbose logging
homeauto-scan --mock --verbose

# Scan specific subnet
homeauto-scan --subnet 192.168.1.0/24
```

### Device Configuration

```bash
# List discovered devices
homeauto-config list

# Set device credentials
homeauto-config set-creds gate admin password123

# Test gate connection
homeauto-config test-gate gate-001 --verbose

# Control gate
homeauto-config control-gate gate-001 open
homeauto-config control-gate gate-001 close
homeauto-config control-gate gate-001 toggle
```

### Web Interface

```bash
# Start the web server
python -m homeauto.web.api
# or
python run_web.py

# Access the dashboard
# Open browser to: http://localhost:8000
```

### Verbose Mode

Enable detailed logging for device communication:

```bash
# CLI tools with verbose logging
homeauto-scan --verbose
homeauto-config test-gate gate-001 --verbose
homeauto-config control-gate gate-001 open --verbose

# Verbose mode shows:
# - Device communication details
# - Network scan progress
# - API request/response details
# - Error debugging information
```

## 🏗️ Project Structure

```
homeauto/
├── cli/              # Command-line tools (scan, config)
├── config/           # Configuration management
├── database/         # Database models and repository
├── devices/          # Device adapters
│   ├── base.py      # Base device class
│   ├── gate.py      # Hikvision gate controller
│   ├── camera.py    # IP camera support
│   └── tuya.py      # Tuya device support
├── discovery/        # Network scanning and device identification
├── utils/            # Utilities (logging, network, retry logic)
└── web/              # Web application
    ├── api.py       # FastAPI application
    └── static/      # Web interface files

tests/               # Comprehensive test suite
docs/                # Documentation
```

## 🔧 Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=homeauto --cov-report=html

# Run specific test categories
pytest tests/devices/ -v      # Device adapter tests
pytest tests/web/ -v          # Web API tests
pytest tests/cli/ -v          # CLI tool tests
```

### Code Quality

```bash
# Format code
black homeauto/ tests/

# Check code style
flake8 homeauto/ tests/

# Type checking
mypy homeauto/
```

### Adding New Device Adapters

1. Create new file in `homeauto/devices/`
2. Inherit from `BaseDevice` class
3. Implement required methods:
   - `test_connection()`
   - `get_info()`
   - `get_status()`
4. Add to device adapter registry in `homeauto/web/api.py`

## 🌐 Web API

### Key Endpoints

```
GET    /api/devices              # List all devices
GET    /api/devices/{id}         # Get specific device
GET    /api/devices/{id}/status  # Get device status
POST   /api/devices/{id}/control # Send control command

GET    /api/gates/{id}/status    # Get detailed gate status
POST   /api/gates/{id}/open      # Open gate
POST   /api/gates/{id}/close     # Close gate

GET    /docs                     # Interactive API documentation
GET    /redoc                    # Alternative API documentation
WS     /ws                       # WebSocket for real-time updates
```

### API Examples

```bash
# Get all devices
curl http://localhost:8000/api/devices

# Get gate status
curl http://localhost:8000/api/gates/gate-001/status

# Open gate
curl -X POST http://localhost:8000/api/gates/gate-001/open
```

## 📊 Hik Connect Integration

The system includes comprehensive Hik Connect integration for controlling Hikvision gate controllers:

### Features
- **ISAPI Protocol**: Full implementation of Hikvision's ISAPI protocol
- **XML Parsing**: Proper XML request/response handling
- **Error Handling**: Comprehensive error handling with retry logic
- **Status Monitoring**: Real-time gate status (open/closed, locked/unlocked)
- **Configuration Management**: View and update gate settings

### Usage Examples
```bash
# Test Hik Connect integration
homeauto-config test-gate gate-001 --verbose

# Control gates via CLI
homeauto-config control-gate gate-001 open
homeauto-config control-gate gate-001 close

# Control gates via web interface
# Visit http://localhost:8000 and use the gate control buttons
```

## 🐛 Troubleshooting

### Common Issues

#### 1. Virtual Environment Issues
```bash
# If activation fails on Windows
.\venv\Scripts\activate

# If Python not found in venv
python -m venv --clear venv
```

#### 2. Port Already in Use
```bash
# Use different port
python run_web_port.py
# or
uvicorn homeauto.web.api:app --port 8080
```

#### 3. Database Issues
```bash
# Reset database (WARNING: deletes all data)
rm homeauto.db
# Database will be recreated on next run
```

#### 4. Encoding Issues (Windows)
```bash
# If you see Unicode errors, use the clean HTML version
# The system automatically falls back to ASCII-compatible versions
```

### Debug Mode

Enable debug logging in `config.yaml`:
```yaml
settings:
  debug: true
  log_level: "DEBUG"
```

Or use verbose mode in CLI:
```bash
homeauto-scan --verbose
homeauto-config --verbose test-gate gate-001
```

## 📈 Performance

- **Network Scanning**: Multi-threaded scanning for faster device discovery
- **Database**: SQLite with efficient queries and indexing
- **Web Server**: FastAPI with async support for high concurrency
- **Caching**: Intelligent caching of device status and configuration

## 🔒 Security

- **Credential Encryption**: Secure storage of device credentials
- **Input Validation**: All inputs validated before processing
- **Error Handling**: Generic error messages to avoid information leakage
- **Local Network**: Designed for local network use only (no cloud dependency)

## 🚀 Deployment

### Production Deployment

```bash
# Build distribution packages
python setup.py sdist bdist_wheel

# Install from built package
pip install dist/homeauto-0.1.0-py3-none-any.whl
```

### Docker Deployment

```dockerfile
FROM python:3.10-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "homeauto.web.api:app", "--host", "0.0.0.0", "--port", "8000"]
```

### System Service (Linux)

Create `/etc/systemd/system/homeauto.service`:
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

## 📚 Documentation

- **API Documentation**: Available at `http://localhost:8000/docs`
- **Integration Guides**: See `docs/` directory
- **Build Instructions**: See `BUILD.md`
- **Hik Connect Guide**: See `docs/hik-connect-integration.md`

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Run the test suite
6. Submit a pull request

### Development Guidelines
- Follow PEP 8 style guide
- Write comprehensive tests
- Add documentation for new features
- Use type hints where appropriate
- Maintain backward compatibility

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- **FastAPI**: For the excellent web framework
- **SQLAlchemy**: For database ORM
- **Tailwind CSS**: For utility-first CSS framework
- **Alpine.js**: For minimal JavaScript framework
- **Hikvision**: For ISAPI protocol documentation

## 📞 Support

- **Issues**: Use GitHub Issues for bug reports and feature requests
- **Documentation**: Check the `docs/` directory and API documentation
- **Testing**: Use `--mock` flag for testing without real devices
- **Debugging**: Use `--verbose` flag for detailed logging

## 🎯 Roadmap

### Planned Features
- [ ] Tuya Local Control protocol implementation
- [ ] Advanced camera features (PTZ control, streaming)
- [ ] Mobile app interface
- [ ] Scheduled automation rules
- [ ] Multi-user support with authentication
- [ ] Plugin system for third-party device support

### Current Status
- ✅ Core architecture complete
- ✅ Hik Connect integration complete
- ✅ Web interface functional
- ✅ CLI tools operational
- ✅ Comprehensive test suite
- 📊 67% test coverage

---

**Happy Automating!** 🏠✨
