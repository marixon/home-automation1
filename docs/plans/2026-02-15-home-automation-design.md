# Home Automation System - Design Document

**Date:** 2026-02-15
**Status:** Approved

## Overview

A Python-based home automation system that discovers devices on the local network, manages their configuration, and provides a web-based dashboard for monitoring and control.

**Target Devices:**
- Hik Connect gate control systems
- IP cameras (RTSP/ONVIF)
- Tuya temperature and humidity sensors
- Tuya light switches

## Product Roadmap

1. **Phase 1:** CLI module to scan IP devices and recognize them by type
2. **Phase 2:** CLI module to configure recognized devices
3. **Phase 3:** Web application with dashboard interface

## Architecture

### Approach: Layered Architecture with Shared Core

```
┌─────────────────────────────────────┐
│   CLI Tools    │    Web App         │
│   (scan, cfg)  │  (FastAPI + UI)    │
├─────────────────────────────────────┤
│         Core Library                │
│  - Device Discovery                 │
│  - Device Adapters (Hik/Tuya/etc)  │
│  - Configuration Management         │
│  - Data Access (SQLite)             │
└─────────────────────────────────────┘
```

### Core Library Structure (`homeauto` package)

```
homeauto/
├── discovery/
│   ├── scanner.py          # Network scanning (subnet, mDNS, UPnP)
│   ├── fingerprint.py      # Port/service detection
│   ├── identifier.py       # MAC vendor lookup + API probing
│   └── mock.py            # Mock device generator for testing
├── devices/
│   ├── base.py            # Abstract Device class
│   ├── hikconnect.py      # Hik Connect gate controller
│   ├── camera.py          # IP camera support
│   ├── tuya.py            # Tuya sensors/switches
│   └── registry.py        # Device type registry
├── config/
│   ├── manager.py         # Config file handling
│   └── credentials.py     # Credential storage
├── database/
│   ├── models.py          # SQLite schema
│   └── repository.py      # Data access layer
└── utils/
    ├── network.py         # Network utilities
    └── retry.py           # Retry logic with backoff
```

### CLI Tools (Phase 1 & 2)

- **homeauto-scan**: Device discovery CLI using discovery module
- **homeauto-config**: Configuration CLI using config + devices modules

### Web Application (Phase 3)

- **Backend**: FastAPI serving REST API + WebSocket for real-time updates
- **Frontend**: Alpine.js + Tailwind CSS with device widget dashboard
- Uses same core library as CLI tools

## Key Components

### Device Discovery Flow

Multi-stage discovery process:

1. **Network Scan** - Ping sweep of subnet to find active hosts
2. **Protocol Discovery** - mDNS/UPnP for self-announcing devices
3. **Port Fingerprinting** - Check common ports (80, 443, 554/RTSP, Tuya ports)
4. **MAC Vendor Lookup** - Use OUI database to identify manufacturer
5. **API Probing** - Attempt connections to known device APIs to confirm type
6. **Confidence Scoring** - Combine signals to determine device type with confidence level

### Device Adapters

Each device type implements the base Device interface:

```python
class Device:
    def get_info()          # Basic device information
    def get_status()        # Current status (online/offline)
    def get_config()        # Read configuration
    def update_config()     # Write basic settings (name, IP, etc)
    def test_connection()   # Verify connectivity
```

**Device-specific adapters:**
- Hik Connect: Gate control API integration
- IP Camera: RTSP/ONVIF protocol support
- Tuya: Tuya API for sensors and switches

### Data Persistence

**SQLite Database:**
- Discovered devices
- Scan history
- Device status and metadata

**Config File (config.yaml):**
```yaml
credentials:
  hikconnect:
    username: user
    password: pass
  tuya:
    api_key: key
    secret: secret
settings:
  scan_interval: 300
  retry_attempts: 3
```

**Device Registry:**
- In-memory cache of active devices
- Refreshed from database

### Configuration Manager

- Reads/writes YAML configuration files
- Provides credential storage (plain-text for home network use)
- Manages application settings

## Data Flow

### CLI Scan Flow (Phase 1)

```
User runs homeauto-scan
    ↓
Scanner performs discovery stages
    ↓
Devices identified → stored in SQLite
    ↓
Results printed to console (table format)
    ↓
Device data persisted for later use
```

### CLI Configuration Flow (Phase 2)

```
User runs homeauto-config --device <id>
    ↓
Load device from SQLite
    ↓
Instantiate appropriate device adapter
    ↓
Retry logic: attempt connection (3 tries with backoff)
    ↓
If connected: fetch current config, allow edits
    ↓
Update device → save changes to SQLite
    ↓
Confirm success or report error with status
```

### Web Dashboard Flow (Phase 3)

```
Frontend loads → GET /api/devices
    ↓
FastAPI queries SQLite → returns device list
    ↓
Alpine.js renders widget for each device
    ↓
WebSocket connection for real-time updates
    ↓
User clicks widget action (e.g., "refresh status")
    ↓
POST /api/devices/{id}/action
    ↓
Backend uses device adapter with retry logic
    ↓
Result pushed via WebSocket → widget updates
```

### Real-time Updates

WebSocket broadcasts device status changes to all connected clients. When a device status changes, all dashboard viewers see the update immediately.

## Error Handling

### Network & Connection Errors

- **Retry with exponential backoff**: 3 attempts with delays (1s, 2s, 4s)
- **Timeout management**: Configurable timeouts per device type
- **Graceful degradation**: Unreachable devices marked as offline but kept in database

### Device Status States

```
ONLINE:  Successfully connected and responsive
OFFLINE: Known device but currently unreachable
UNKNOWN: Discovered but not yet fully identified
ERROR:   Connection attempted but failed with error
```

Status stored in SQLite and updated during each scan/interaction. Web dashboard shows visual indicators for each state.

### Authentication Failures

- Log authentication errors clearly
- Don't retry auth failures (avoid DOSing devices)
- Prompt user to check credentials in config file
- Support per-device credential override

### Discovery Errors

- Report network accessibility issues if scan fails entirely
- Continue with partial results if some scans fail
- Log failed discovery attempts for debugging
- Mock mode bypasses all network operations

### API Error Responses

Web API returns structured errors:
```json
{
  "error": "device_unreachable",
  "message": "Camera at 192.168.1.100 not responding",
  "device_id": "cam-001",
  "retry_after": 300
}
```

## Testing Strategy

### Unit Tests

Test individual components in isolation:
- **Discovery modules**: Scanner, fingerprinter, identifier with mocked network
- **Device adapters**: Each adapter with mock API responses
- **Config manager**: YAML parsing, credential loading
- **Database layer**: SQLite operations with in-memory database

### Integration Tests

Test components working together:
- **CLI tools**: Full scan and config workflows with mock devices
- **API endpoints**: FastAPI routes with test client
- **End-to-end**: Mock devices → scan → store → retrieve → configure

### Mock Device System

Simulated devices for testing:
- Mock Hik Connect gate (auth, status queries)
- Mock IP camera (RTSP port, ONVIF endpoints)
- Mock Tuya sensor (status updates)
- Configurable response delays and error scenarios

Configuration flag:
```yaml
testing:
  use_mock_devices: true
  mock_device_count: 5
```

### Testing Phases

- **Phase 1**: Test discovery with mocks, validate with real devices
- **Phase 2**: Test configuration workflows with mocks and real devices
- **Phase 3**: Test API endpoints, WebSocket updates, frontend interactions

### Test Coverage Goals

- Core library: 80%+ coverage
- CLI tools: Smoke tests for main workflows
- API endpoints: Test all routes with success/error cases

## Technology Stack

- **Language**: Python 3.10+
- **Environment**: venv for isolation
- **Backend Framework**: FastAPI
- **Frontend**: Alpine.js + Tailwind CSS
- **Database**: SQLite
- **Configuration**: YAML files
- **Testing**: pytest with mocking support
- **Repository**: https://github.com/marixon/home-automation1

## Design Principles

1. **Code Reuse**: Shared core library used by CLI and web app
2. **Testability**: Mock device support for development without hardware
3. **Simplicity**: Plain-text config for home network use
4. **Reliability**: Retry logic and graceful degradation
5. **Extensibility**: Easy to add new device types via adapter pattern
6. **User Experience**: Clear status indicators and error messages

## Next Steps

Proceed to implementation planning with detailed tasks for:
1. Project setup and core library structure
2. Phase 1: CLI scanner implementation
3. Phase 2: CLI configuration tool
4. Phase 3: Web application development
