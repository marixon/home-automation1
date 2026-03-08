# CLI Development Guide

This guide explains how to build CLI commands like `homeauto-scan` for the Home Automation system.

## Architecture Overview

The CLI system supports two approaches:
1. **Legacy**: `argparse`-based commands (e.g., `homeauto-scan`)
2. **Modern**: `Click`-based commands (e.g., `homeauto scan`)

## 1. Creating a New CLI Command

### Option A: Modern Click-based Command (Recommended)

#### Step 1: Create the Command Module
```python
# homeauto/cli/your_command.py
import click
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from homeauto.config.manager import ConfigManager
from homeauto.utils.logging_config import get_logger

@click.group()
def your_command():
    """Your command description"""
    pass

@your_command.command()
@click.option('--option1', '-o', help='Description of option1')
@click.option('--flag', '-f', is_flag=True, help='Description of flag')
@click.argument('required_arg')
@click.pass_context
def subcommand(ctx, option1, flag, required_arg):
    """Subcommand description"""
    
    # Access context
    config_path = ctx.obj.get('CONFIG_PATH', 'config.yaml')
    verbose = ctx.obj.get('VERBOSE', False)
    
    # Create command instance
    cmd = YourCommand(config_path=config_path, verbose=verbose)
    
    # Execute command logic
    return cmd.execute(option1, flag, required_arg)

class YourCommand:
    def __init__(self, config_path: str = "config.yaml", verbose: bool = False):
        self.config = ConfigManager(config_path)
        self.verbose = verbose
        self.logger = get_logger("cli.your_command")
    
    def execute(self, option1, flag, required_arg):
        """Main command logic"""
        try:
            # Your implementation here
            self.logger.info(f"Executing command with: {option1}, {flag}, {required_arg}")
            
            # Return 0 for success, 1 for failure
            return 0
        except Exception as e:
            self.logger.error(f"Command failed: {e}")
            return 1

# For backward compatibility
def main():
    """Legacy entry point"""
    import sys
    from .main import cli
    
    # Run just this command group
    sys.argv = ['homeauto', 'your_command'] + sys.argv[1:]
    cli(obj={})
```

#### Step 2: Register in Main CLI
```python
# In homeauto/cli/main.py
try:
    from .your_command import your_command
    cli.add_command(your_command)
except ImportError as e:
    click.echo(f"[WARNING] Your command not available: {e}")
```

### Option B: Legacy Argparse Command

#### Step 1: Create the Command Module
```python
# homeauto/cli/your_command.py
import sys
import argparse

from homeauto.config.manager import ConfigManager
from homeauto.utils.logging_config import setup_logging, get_logger

class YourCommand:
    def __init__(self, config_path: str = "config.yaml", verbose: bool = False):
        self.config = ConfigManager(config_path)
        self.verbose = verbose
        self.logger = get_logger("cli.your_command")
        setup_logging(verbose=verbose)
    
    def execute(self, args):
        """Execute command with parsed arguments"""
        try:
            # Your implementation here
            print(f"Executing with args: {args}")
            return 0
        except Exception as e:
            self.logger.error(f"Command failed: {e}")
            return 1

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Your command description")
    parser.add_argument("--config", "-c", default="config.yaml", help="Configuration file")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")
    
    # Add your arguments
    parser.add_argument("--option1", "-o", help="Description")
    parser.add_argument("required_arg", help="Required argument")
    
    args = parser.parse_args()
    
    # Create and execute command
    cmd = YourCommand(config_path=args.config, verbose=args.verbose)
    return cmd.execute(args)
```

#### Step 2: Register in setup.py
```python
# In setup.py
entry_points={
    "console_scripts": [
        "homeauto-yourcommand=homeauto.cli.your_command:main",
    ],
}
```

## 2. Best Practices

### 2.1 Command Structure
```python
# Good structure
@click.command()
@click.option('--input', '-i', required=True, help='Input file')
@click.option('--output', '-o', help='Output file (default: stdout)')
@click.option('--verbose', '-v', is_flag=True, help='Verbose output')
@click.argument('target')
def process(input, output, verbose, target):
    """Process target with input file"""
    pass
```

### 2.2 Error Handling
```python
def safe_execute(func):
    """Decorator for safe command execution"""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except KeyboardInterrupt:
            click.echo("\nOperation cancelled")
            return 130
        except Exception as e:
            if kwargs.get('verbose', False):
                import traceback
                traceback.print_exc()
            click.echo(f"Error: {e}", err=True)
            return 1
    return wrapper
```

### 2.3 Logging
```python
import logging

def setup_command_logging(verbose=False):
    """Setup logging for CLI commands"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger(__name__)
```

### 2.4 Configuration Access
```python
class BaseCommand:
    """Base class for all commands"""
    def __init__(self, config_path="config.yaml", verbose=False):
        self.config = ConfigManager(config_path)
        self.verbose = verbose
        self.logger = get_logger(f"cli.{self.__class__.__name__.lower()}")
    
    def get_config_value(self, key, default=None):
        """Get configuration value with dot notation"""
        return self.config.get(key, default)
```

## 3. Common Patterns

### 3.1 Subcommands with Shared Context
```python
@click.group()
@click.pass_context
def device(ctx):
    """Device management commands"""
    # Shared initialization
    ctx.obj['DEVICE_MANAGER'] = DeviceManager()

@device.command()
@click.pass_context
def list(ctx):
    """List devices"""
    manager = ctx.obj['DEVICE_MANAGER']
    devices = manager.list_devices()
    # ...
```

### 3.2 Progress Reporting
```python
import click
import time

@click.command()
def long_operation():
    """Command with progress reporting"""
    with click.progressbar(range(100), label='Processing') as bar:
        for i in bar:
            time.sleep(0.1)  # Simulate work
    click.echo("Done!")
```

### 3.3 Interactive Prompts
```python
@click.command()
@click.option('--name', prompt='Device name')
@click.option('--ip', prompt='IP address')
@click.option('--confirm', is_flag=True, prompt='Confirm creation?')
def add_device(name, ip, confirm):
    """Add a new device"""
    if confirm:
        click.echo(f"Adding device: {name} ({ip})")
    else:
        click.echo("Cancelled")
```

### 3.4 Output Formatting
```python
def format_table(data, headers):
    """Format data as a table"""
    from tabulate import tabulate
    return tabulate(data, headers=headers, tablefmt='grid')

def format_json(data):
    """Format data as JSON"""
    import json
    return json.dumps(data, indent=2, default=str)
```

## 4. Testing CLI Commands

### 4.1 Unit Testing
```python
# tests/test_cli_your_command.py
import pytest
from click.testing import CliRunner
from homeauto.cli.your_command import your_command

def test_your_command():
    runner = CliRunner()
    result = runner.invoke(your_command, ['--help'])
    assert result.exit_code == 0
    assert 'Usage:' in result.output

def test_subcommand():
    runner = CliRunner()
    result = runner.invoke(your_command, ['subcommand', '--option1', 'value', 'arg'])
    assert result.exit_code == 0
```

### 4.2 Integration Testing
```python
# tests/integration/test_cli_integration.py
import subprocess

def test_cli_installation():
    """Test that CLI commands are installed"""
    result = subprocess.run(['homeauto', '--help'], capture_output=True, text=True)
    assert result.returncode == 0
    assert 'Usage:' in result.stdout
```

## 5. Packaging and Distribution

### 5.1 setup.py Configuration
```python
setup(
    # ...
    entry_points={
        "console_scripts": [
            "homeauto=homeauto.cli.main:main",
            "homeauto-scan=homeauto.cli.scan:main",
            "homeauto-config=homeauto.cli.config:main",
            "homeauto-yourcommand=homeauto.cli.your_command:main",
        ],
    },
    # ...
)
```

### 5.2 pyproject.toml Configuration
```toml
[project.scripts]
homeauto = "homeauto.cli.main:main"
homeauto-scan = "homeauto.cli.scan:main"
homeauto-config = "homeauto.cli.config:main"
homeauto-yourcommand = "homeauto.cli.your_command:main"
```

## 6. Example: Complete Camera Command

```python
"""
Example: Complete camera management command
"""
import click
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from homeauto.config.manager import ConfigManager
from homeauto.database.repository import DeviceRepository
from homeauto.utils.logging_config import get_logger

@click.group()
def camera():
    """Camera management commands"""
    pass

@camera.command()
@click.option('--type', '-t', default='all', 
              type=click.Choice(['all', 'camera', 'gate', 'sensor']),
              help='Filter by device type')
@click.option('--status', '-s', default='all',
              type=click.Choice(['all', 'online', 'offline']),
              help='Filter by status')
@click.option('--output', '-o', 
              type=click.Choice(['table', 'json', 'csv']),
              default='table', help='Output format')
@click.pass_context
def list(ctx, type, status, output):
    """List cameras"""
    config_path = ctx.obj.get('CONFIG_PATH', 'config.yaml')
    verbose = ctx.obj.get('VERBOSE', False)
    
    cmd = CameraCommand(config_path, verbose)
    return cmd.list_cameras(type, status, output)

@camera.command()
@click.argument('camera_id')
@click.option('--quality', '-q', default=85, type=int,
              help='Snapshot quality (1-100)')
@click.option('--save', '-s', is_flag=True,
              help='Save snapshot to file')
@click.pass_context
def snapshot(ctx, camera_id, quality, save):
    """Take camera snapshot"""
    config_path = ctx.obj.get('CONFIG_PATH', 'config.yaml')
    verbose = ctx.obj.get('VERBOSE', False)
    
    cmd = CameraCommand(config_path, verbose)
    return cmd.take_snapshot(camera_id, quality, save)

class CameraCommand:
    def __init__(self, config_path="config.yaml", verbose=False):
        self.config = ConfigManager(config_path)
        self.verbose = verbose
        self.logger = get_logger("cli.camera")
        self.repo = DeviceRepository()
    
    def list_cameras(self, type_filter, status_filter, output_format):
        """List cameras with filters"""
        try:
            # Get cameras
            if type_filter == 'all':
                devices = self.repo.get_all()
            else:
                devices = self.repo.get_by_type(type_filter)
            
            # Filter by status
            if status_filter != 'all':
                devices = [d for d in devices if d.status.value == status_filter]
            
            # Format output
            if output_format == 'table':
                self._print_table(devices)
            elif output_format == 'json':
                self._print_json(devices)
            elif output_format == 'csv':
                self._print_csv(devices)
            
            return 0
        except Exception as e:
            self.logger.error(f"Failed to list cameras: {e}")
            click.echo(f"Error: {e}", err=True)
            return 1
    
    def take_snapshot(self, camera_id, quality, save):
        """Take snapshot from camera"""
        try:
            device = self.repo.get(camera_id)
            if not device:
                click.echo(f"Camera not found: {camera_id}", err=True)
                return 1
            
            click.echo(f"Taking snapshot from: {device.name}")
            # Implementation here...
            return 0
        except Exception as e:
            self.logger.error(f"Failed to take snapshot: {e}")
            click.echo(f"Error: {e}", err=True)
            return 1
    
    def _print_table(self, devices):
        """Print devices as table"""
        # Table formatting implementation
        pass
    
    def _print_json(self, devices):
        """Print devices as JSON"""
        import json
        data = [{"id": d.id, "name": d.name, "type": d.device_type} for d in devices]
        click.echo(json.dumps(data, indent=2))
    
    def _print_csv(self, devices):
        """Print devices as CSV"""
        import csv
        import io
        
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['ID', 'Name', 'Type', 'IP', 'Status'])
        
        for device in devices:
            writer.writerow([
                device.id, device.name, device.device_type,
                device.ip_address, device.status.value
            ])
        
        click.echo(output.getvalue())
```

## 7. Deployment Checklist

- [ ] Command is registered in `setup.py` or `pyproject.toml`
- [ ] Command has proper help text
- [ ] Command handles errors gracefully
- [ ] Command supports `--verbose` flag
- [ ] Command supports `--config` option
- [ ] Command has unit tests
- [ ] Command output is properly formatted
- [ ] Command follows consistent naming conventions
- [ ] Command documentation is updated

## 8. Troubleshooting

### Command not found after installation
```bash
# Check if package is installed
pip show homeauto

# Check entry points
python -c "import pkg_resources; print([ep.name for ep in pkg_resources.iter_entry_points('console_scripts')])"

# Install in development mode
pip install -e .
```

### Import errors
```python
# Add project root to path
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
```

### Click context issues
```python
# Ensure context object exists
ctx.ensure_object(dict)

# Store data in context
ctx.obj['KEY'] = value

# Retrieve from context
value = ctx.obj.get('KEY', default)
```

## Summary

Building CLI commands for the Home Automation system involves:

1. **Choose approach**: Click (modern) or argparse (legacy)
2. **Create module**: Implement command logic in a class
3. **Register command**: Add to main CLI or setup.py
4. **Handle errors**: Use try/except with proper error codes
5. **Add logging**: Use the shared logging configuration
6. **Test thoroughly**: Unit and integration tests
7. **Document**: Update README and help text

The system supports both legacy commands (`homeauto-scan`) and modern commands (`homeauto scan`) for backward compatibility while providing a clean, consistent user experience.
