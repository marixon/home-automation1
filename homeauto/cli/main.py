"""
Home Automation CLI - Main Entry Point
"""

import click
import sys
from pathlib import Path
from typing import Optional

# Add the project root to the path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from homeauto.config.manager import ConfigManager
from homeauto.utils.logging_config import setup_logging, get_logger

# Create main CLI group
@click.group()
@click.version_option(version="0.1.0")
@click.option('--config', '-c', default='config.yaml', 
              help='Path to configuration file')
@click.option('--verbose', '-v', is_flag=True, 
              help='Enable verbose logging')
@click.pass_context
def cli(ctx, config: str, verbose: bool):
    """Home Automation System CLI
    
    A comprehensive CLI for managing your home automation system,
    including device discovery, configuration, and camera services.
    """
    # Ensure ctx.obj exists and is a dict
    ctx.ensure_object(dict)
    
    # Store configuration in context
    ctx.obj['CONFIG_PATH'] = config
    ctx.obj['VERBOSE'] = verbose
    
    # Setup logging
    setup_logging(verbose=verbose)
    ctx.obj['LOGGER'] = get_logger('cli')
    
    # Load configuration
    try:
        config_manager = ConfigManager(config)
        ctx.obj['CONFIG'] = config_manager
        ctx.obj['CONFIG_MANAGER'] = config_manager
        
        if verbose:
            click.echo(f"[OK] Configuration loaded from: {config}")
    except Exception as e:
        click.echo(f"[ERROR] Error loading configuration: {e}", err=True)
        sys.exit(1)

# Import and register subcommands
try:
    from .scan_click import scan
    cli.add_command(scan)
except ImportError as e:
    click.echo(f"[WARNING] Scan command not available: {e}")

try:
    from .config import ConfigCommand
    import click
    
    @click.group()
    def config():
        """Device configuration management"""
        pass
    
    @config.command()
    @click.pass_context
    def list(ctx):
        """List all devices"""
        cmd = ConfigCommand(
            config_path=ctx.obj.get('CONFIG_PATH', 'config.yaml'),
            verbose=ctx.obj.get('VERBOSE', False)
        )
        return cmd.list_devices()
    
    @config.command()
    @click.argument('device_type')
    @click.argument('username')
    @click.argument('password')
    @click.pass_context
    def set_creds(ctx, device_type, username, password):
        """Set device credentials"""
        cmd = ConfigCommand(
            config_path=ctx.obj.get('CONFIG_PATH', 'config.yaml'),
            verbose=ctx.obj.get('VERBOSE', False)
        )
        return cmd.set_credentials(device_type, username, password)
    
    cli.add_command(config)
except ImportError as e:
    click.echo(f"[WARNING] Config command not available: {e}")

try:
    from .security import SecurityCommand
    import click
    
    @click.group()
    def security():
        """Security tools and utilities"""
        pass
    
    @security.command()
    @click.pass_context
    def check(ctx):
        """Check security status"""
        cmd = SecurityCommand(
            config_path=ctx.obj.get('CONFIG_PATH', 'config.yaml'),
            verbose=ctx.obj.get('VERBOSE', False)
        )
        return cmd.check_devices()
    
    cli.add_command(security)
except ImportError as e:
    click.echo(f"[WARNING] Security command not available: {e}")

try:
    from .camera import camera
    if camera:
        cli.add_command(camera)
except ImportError as e:
    click.echo(f"[WARNING] Camera command not available: {e}")

def main():
    """Main entry point for the CLI"""
    try:
        cli(obj={})
    except KeyboardInterrupt:
        click.echo("\n\nOperation cancelled by user")
        sys.exit(130)
    except Exception as e:
        click.echo(f"\n[ERROR] Error: {e}", err=True)
        if cli.context_class().obj.get('VERBOSE', False):
            import traceback
            traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
