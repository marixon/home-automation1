# Hik Connect Integration Guide

## Overview

This document describes the Hik Connect integration for the Home Automation system. The integration allows controlling Hikvision gate controllers through the ISAPI protocol.

## Features

- **Device Discovery**: Automatically detect Hikvision gate controllers on the network
- **Status Monitoring**: Get real-time gate status (open/closed, locked/unlocked)
- **Gate Control**: Open, close, and toggle gates remotely
- **Configuration**: View and manage gate settings
- **Web Interface**: Control gates through the web dashboard
- **CLI Tools**: Manage gates through command-line interface

## Architecture

The Hik Connect integration consists of:

1. **HikGateDevice Class**: Device adapter implementing ISAPI protocol
2. **Web API Endpoints**: REST API for gate control
3. **Web UI Components**: Gate control interface in the dashboard
4. **CLI Commands**: Command-line tools for gate management

## Device Adapter: HikGateDevice

### Key Methods

- `test_connection()`: Test connectivity to gate controller
- `get_info()`: Get device information (model, serial, firmware)
- `get_status()`: Get current gate status
- `open_gate()`: Open the gate
- `close_gate()`: Close the gate
- `toggle_gate()`: Toggle gate state
- `get_config()`: Get gate configuration
- `get_capabilities()`: List supported capabilities

### ISAPI Protocol Implementation

The adapter uses Hikvision's ISAPI (Internet Services Application Programming Interface) protocol:

- **Authentication**: HTTP Basic Auth
- **Endpoints**: Standard ISAPI endpoints for access control
- **Data Format**: XML request/response
- **Error Handling**: Comprehensive error handling with retry logic

## Web API Endpoints

### Gate Control Endpoints

```
GET    /api/gates/{device_id}/status     # Get detailed gate status
POST   /api/gates/{device_id}/open       # Open gate
POST   /api/gates/{device_id}/close      # Close gate
```

### General Device Endpoints

```
GET    /api/devices/{device_id}/status   # Get device status
POST   /api/devices/{device_id}/control  # Send control command
```

## Web Interface

The web dashboard includes:

1. **Gate Status Display**: Shows gate state (open/closed)
2. **Control Buttons**: Open/Close buttons for each gate
3. **Real-time Updates**: WebSocket updates for status changes
4. **Device Details**: Modal with detailed gate information

## CLI Tools

### Configuration Commands

```bash
# Set gate credentials
homeauto-config set-creds gate admin password123

# Test gate connection
homeauto-config test-gate gate-001

# Control gate
homeauto-config control-gate gate-001 open
homeauto-config control-gate gate-001 close
homeauto-config control-gate gate-001 toggle
```

### Scanner Integration

```bash
# Scan for devices (includes Hikvision gates)
homeauto-scan

# Scan with mock devices for testing
homeauto-scan --mock
```

## Configuration

### Credentials Configuration

Add gate credentials to `config.yaml`:

```yaml
credentials:
  gate:
    username: "admin"
    password: "your_password"
```

### Device Configuration

Gates discovered by the scanner are stored in the SQLite database with:
- Device type: `gate`
- Manufacturer: `Hikvision`
- Confidence score based on port detection and API responses

## Testing

### Unit Tests

Run gate-specific tests:

```bash
pytest tests/devices/test_gate.py -v
pytest tests/web/test_api.py -v
```

### Integration Testing

1. **Mock Testing**: Tests with mocked HTTP responses
2. **Error Scenarios**: Tests for connection failures and API errors
3. **Web Interface**: Tests for UI interactions

## Error Handling

The integration includes comprehensive error handling:

1. **Connection Errors**: Retry logic with exponential backoff
2. **Authentication Errors**: Clear error messages for credential issues
3. **API Errors**: Parsing of ISAPI error responses
4. **Network Errors**: Timeout handling and reconnection logic

## Security Considerations

1. **Credential Storage**: Credentials stored in encrypted config file
2. **Network Security**: Local network access only (no cloud dependency)
3. **Input Validation**: All inputs validated before processing
4. **Error Messages**: Generic error messages to avoid information leakage

## Limitations

1. **Local Network Only**: Requires gate controller to be on local network
2. **ISAPI Protocol**: Specific to Hikvision devices
3. **Basic Auth Only**: Currently supports HTTP Basic Authentication only
4. **Single Door**: Assumes single door per controller (door 1)

## Future Enhancements

1. **Hik Connect Cloud**: Add cloud API support for remote access
2. **Multiple Doors**: Support for controllers with multiple doors
3. **Advanced Features**: Support for schedules, access logs, etc.
4. **Authentication Methods**: Support for digest auth and tokens

## Troubleshooting

### Common Issues

1. **Connection Failed**: Check IP address and network connectivity
2. **Authentication Error**: Verify username/password in config
3. **API Error**: Check if ISAPI is enabled on the gate controller
4. **XML Parse Error**: Verify device compatibility with ISAPI protocol

### Debug Mode

Enable debug logging in the configuration:

```yaml
settings:
  debug: true
  log_level: "DEBUG"
```

## References

- [Hikvision ISAPI Documentation](https://www.hikvision.com/en/support/technical-documentation/)
- [ISAPI Protocol Reference](https://www.hikvision.com/content/dam/hikvision/en/support/technical-documentation/isapi/)
- [Access Control API Guide](https://www.hikvision.com/content/dam/hikvision/en/support/technical-documentation/access-control/)
