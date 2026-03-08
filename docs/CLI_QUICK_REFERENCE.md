# CLI Quick Reference

## Installation

```bash
# Install in development mode
pip install -e .

# Or from PyPI (when published)
pip install homeauto
```

## Available Commands

### Modern Click-based CLI (Recommended)
```bash
homeauto [OPTIONS] COMMAND [ARGS]...
```

### Legacy Commands
```bash
homeauto-scan [OPTIONS] COMMAND [ARGS]...
homeauto-config [OPTIONS] COMMAND [ARGS]...
homeauto-security [OPTIONS] COMMAND [ARGS]...
```

## Command Reference

### Main CLI (`homeauto`)
```bash
# Show help
homeauto --help

# Show version
homeauto --version

# With custom config
homeauto --config /path/to/config.yaml

# Verbose mode
homeauto --verbose
```

### Network Scanning (`homeauto scan`)
```bash
# Scan network for devices
homeauto scan network [OPTIONS]

# Generate mock devices for testing
homeauto scan mock [OPTIONS]

# List discovered devices
homeauto scan list [OPTIONS]

# Identify a specific device
homeauto scan identify [OPTIONS]

# Test device connection
homeauto scan test [OPTIONS]
```

### Device Configuration (`homeauto config`)
```bash
# List all devices
homeauto config list

# Set device credentials
homeauto config set-creds <device_type> <username> <password>

# Test gate connection
homeauto config test-gate <device_id>

# Control gate
homeauto config control-gate <device_id> <action>

# Test camera connection
homeauto config test-camera <device_id>
```

### Security Tools (`homeauto security`)
```bash
# Check security status
homeauto security check

# Test notification system
homeauto security test-notify [--email <email>]

# Audit system logs
homeauto security audit [--days <days>]

# Generate security report
homeauto security report [--output <file>]
```

### Camera Services (`homeauto camera`)
```bash
# List camera services status
homeauto camera list

# Start camera services
homeauto camera start [--camera <camera_id>]

# Stop camera services
homeauto camera stop [--camera <camera_id>]

# Take camera snapshot
homeauto camera snapshot <camera_id>

# Show camera services configuration
homeauto camera config
```

## Common Usage Examples

### 1. Initial Setup
```bash
# Scan network and save devices
homeauto scan network --save

# Set camera credentials
homeauto config set-creds camera admin password123

# Test camera connection
homeauto config test-camera camera-001
```

### 2. Daily Operations
```bash
# List all devices
homeauto config list

# Check security status
homeauto security check

# Take snapshot from camera
homeauto camera snapshot camera-001
```

### 3. Testing and Development
```bash
# Generate mock devices
homeauto scan mock --count 5 --save

# Test notification system
homeauto security test-notify --email user@example.com

# Run in verbose mode
homeauto --verbose scan network --save
```

## Configuration File

Commands read from `config.yaml` by default. Use `--config` to specify a different file:

```yaml
# Example config.yaml
credentials:
  camera:
    username: "admin"
    password: "your_password"
  gate:
    username: "admin"
    password: "gate_password"

settings:
  debug: false
  subnet: "192.168.1.0/24"

camera_services:
  enabled: true
  storage:
    local:
      enabled: true
      path: "./camera_snapshots"
```

## Exit Codes

- `0`: Success
- `1`: General error
- `130`: Operation cancelled (Ctrl+C)
- Other: Command-specific errors

## Environment Variables

```bash
# Override default config path
export HOMEAUTO_CONFIG=/path/to/config.yaml

# Enable debug logging
export HOMEAUTO_DEBUG=true
```

## Troubleshooting

### Command not found
```bash
# Check installation
pip show homeauto

# Reinstall in development mode
pip install -e .
```

### Import errors
```bash
# Run from project directory
cd /path/to/home-automation1

# Use Python module directly
python -m homeauto.cli.main --help
```

### Configuration issues
```bash
# Check config file exists
ls -la config.yaml

# Create example config
cp config.example.yaml config.yaml
```

## Advanced Usage

### Scripting with CLI
```bash
#!/bin/bash
# Backup script using CLI

# Take snapshots from all cameras
for camera in $(homeauto config list | grep camera | awk '{print $2}'); do
    homeauto camera snapshot "$camera" --save
done

# Generate security report
homeauto security report --output security_report_$(date +%Y%m%d).txt
```

### Integration with Cron
```cron
# Daily security check at 2 AM
0 2 * * * /usr/local/bin/homeauto security check

# Hourly camera snapshots
0 * * * * /usr/local/bin/homeauto camera snapshot camera-001
```

### Output Formats
```bash
# JSON output for scripting
homeauto scan list --output json

# CSV output for spreadsheets
homeauto scan list --output csv > devices.csv

# Table output (default)
homeauto scan list --output table
```

## Getting Help

```bash
# General help
homeauto --help

# Command-specific help
homeauto scan --help
homeauto scan network --help

# Verbose error messages
homeauto --verbose <command>
```

## Quick Start Cheat Sheet

```bash
# 1. Install
pip install -e .

# 2. Configure
cp config.example.yaml config.yaml
# Edit config.yaml with your credentials

# 3. Discover devices
homeauto scan network --save

# 4. Test devices
homeauto config test-camera camera-001
homeauto config test-gate gate-001

# 5. Use camera services
homeauto camera start
homeauto camera snapshot camera-001

# 6. Monitor security
homeauto security check
homeauto security report
```

## Migration from Legacy Commands

| Legacy Command | Modern Equivalent |
|----------------|-------------------|
| `homeauto-scan network` | `homeauto scan network` |
| `homeauto-config list` | `homeauto config list` |
| `homeauto-security check` | `homeauto security check` |

The modern CLI provides better error handling, more options, and consistent interface across all commands.
