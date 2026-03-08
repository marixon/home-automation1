"""
Home Automation Scan Command - Click Version
"""

import click
import sys
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from homeauto.discovery.scanner import NetworkScanner
from homeauto.discovery.identifier import DeviceIdentifier
from homeauto.discovery.mock import MockDeviceGenerator
from homeauto.database.repository import DeviceRepository
from homeauto.database.models import Device, DeviceStatus
from homeauto.config.manager import ConfigManager
from homeauto.utils.logging_config import get_logger

def format_device_table(devices: List[Dict]) -> str:
    """Format devices as ASCII table"""
    if not devices:
        return "No devices found."
    
    # Calculate column widths
    max_id = max(len(str(d.get('id', ''))) for d in devices) if devices else 10
    max_type = max(len(str(d.get('type', ''))) for d in devices) if devices else 10
    max_ip = max(len(str(d.get('ip', ''))) for d in devices) if devices else 15
    max_name = max(len(str(d.get('name', ''))) for d in devices) if devices else 20
    max_status = max(len(str(d.get('status', ''))) for d in devices) if devices else 10
    
    # Ensure minimum widths
    max_id = max(max_id, 10)
    max_type = max(max_type, 10)
    max_ip = max(max_ip, 15)
    max_name = max(max_name, 20)
    max_status = max(max_status, 10)
    
    # Header
    header = (f"{'ID':<{max_id}} "
              f"{'Type':<{max_type}} "
              f"{'IP Address':<{max_ip}} "
              f"{'Name':<{max_name}} "
              f"{'Status':<{max_status}}")
    
    separator = "-" * (max_id + max_type + max_ip + max_name + max_status + 4)
    
    rows = [header, separator]
    
    for device in devices:
        row = (f"{device.get('id', 'N/A'):<{max_id}} "
               f"{device.get('type', 'unknown'):<{max_type}} "
               f"{device.get('ip', 'N/A'):<{max_ip}} "
               f"{device.get('name', 'Unnamed'):<{max_name}} "
               f"{device.get('status', 'unknown'):<{max_status}}")
        rows.append(row)
    
    return "\n".join(rows)

def format_device_details(device: Dict) -> str:
    """Format device details"""
    details = [
        f"Device Details:",
        f"  ID: {device.get('id', 'N/A')}",
        f"  Type: {device.get('type', 'unknown')}",
        f"  IP Address: {device.get('ip', 'N/A')}",
        f"  MAC Address: {device.get('mac', 'N/A')}",
        f"  Name: {device.get('name', 'Unnamed')}",
        f"  Status: {device.get('status', 'unknown')}",
        f"  Manufacturer: {device.get('manufacturer', 'Unknown')}",
        f"  Model: {device.get('model', 'Unknown')}",
        f"  Last Seen: {device.get('last_seen', 'Never')}",
    ]
    
    if 'confidence' in device:
        details.append(f"  Confidence: {device.get('confidence', 0):.2%}")
    
    if 'ports' in device and device['ports']:
        ports_str = ', '.join(str(p) for p in device['ports'])
        details.append(f"  Open Ports: {ports_str}")
    
    return "\n".join(details)

@click.group()
def scan():
    """Network scanning and device discovery commands"""
    pass

@scan.command()
@click.option('--subnet', '-s', default=None,
              help='Subnet to scan (e.g., 192.168.1.0/24)')
@click.option('--timeout', '-t', default=5, type=int,
              help='Timeout for each scan in seconds')
@click.option('--max-threads', '-m', default=10, type=int,
              help='Maximum number of threads for scanning')
@click.option('--output', '-o', type=click.Choice(['table', 'json', 'csv']),
              default='table', help='Output format')
@click.option('--save', is_flag=True,
              help='Save discovered devices to database')
@click.option('--verbose', '-v', is_flag=True,
              help='Enable verbose output')
@click.pass_context
def network(ctx, subnet: Optional[str], timeout: int, max_threads: int,
            output: str, save: bool, verbose: bool):
    """Scan network for devices"""
    
    config = ctx.obj['CONFIG']
    logger = ctx.obj['LOGGER']
    
    # Use configured subnet if not specified
    if not subnet:
        subnet = config.get_setting('subnet', '192.168.1.0/24')
    
    click.echo(f"Scanning network: {subnet}")
    click.echo(f"   Timeout: {timeout}s, Threads: {max_threads}")
    
    try:
        # Create scanner
        scanner = NetworkScanner(
            subnet=subnet,
            timeout=timeout,
            max_threads=max_threads
        )
        
        # Scan network
        with click.progressbar(length=100, label='Scanning') as bar:
            devices = scanner.scan(progress_callback=lambda p: bar.update(p))
        
        click.echo(f"\nFound {len(devices)} device(s)")
        
        # Format output
        if output == 'table':
            formatted = format_device_table(devices)
            click.echo(f"\n{formatted}")
        elif output == 'json':
            import json
            click.echo(json.dumps(devices, indent=2))
        elif output == 'csv':
            import csv
            import io
            output_stream = io.StringIO()
            writer = csv.DictWriter(output_stream, fieldnames=['id', 'type', 'ip', 'name', 'status'])
            writer.writeheader()
            writer.writerows(devices)
            click.echo(output_stream.getvalue())
        
        # Save to database if requested
        if save and devices:
            repo = DeviceRepository()
            saved_count = 0
            
            for device_data in devices:
                # Check if device already exists
                existing = repo.get(device_data['id'])
                
                if not existing:
                    # Create new device
                    device = Device(
                        id=device_data['id'],
                        device_type=device_data['type'],
                        ip_address=device_data['ip'],
                        mac_address=device_data.get('mac', '00:00:00:00:00:00'),
                        name=device_data['name'],
                        status=DeviceStatus.ONLINE,
                        manufacturer=device_data.get('manufacturer', 'Unknown'),
                        model=device_data.get('model', 'Unknown'),
                        confidence_score=device_data.get('confidence', 0.5),
                        last_seen=datetime.now(),
                        config={},
                        metadata={
                            'ports': device_data.get('ports', []),
                            'discovery_method': 'network_scan'
                        }
                    )
                    repo.save(device)
                    saved_count += 1
            
            click.echo(f"\nSaved {saved_count} new device(s) to database")
        
        return 0
        
    except Exception as e:
        logger.error(f"Scan failed: {e}")
        click.echo(f"Error: {e}", err=True)
        if verbose:
            import traceback
            traceback.print_exc()
        return 1

@scan.command()
@click.option('--device-id', '-d', required=True,
              help='Device ID to identify')
@click.option('--ip', '-i', 
              help='IP address (overrides device lookup)')
@click.option('--detailed', is_flag=True,
              help='Show detailed identification information')
@click.pass_context
def identify(ctx, device_id: str, ip: Optional[str], detailed: bool):
    """Identify a specific device"""
    
    repo = DeviceRepository()
    identifier = DeviceIdentifier()
    
    # Get device from database or use provided IP
    if ip:
        device_ip = ip
        device_name = f"Manual IP: {ip}"
    else:
        device = repo.get(device_id)
        if not device:
            click.echo(f"Error: Device not found: {device_id}", err=True)
            return 1
        device_ip = device.ip_address
        device_name = device.name
    
    click.echo(f"Identifying device: {device_name} ({device_ip})")
    
    try:
        open_ports = []
        manufacturer = "Unknown"
        mac = "00:00:00:00:00:00"

        if not ip:
            metadata = device.metadata or {}
            open_ports = metadata.get("ports", [])
            manufacturer = device.manufacturer or "Unknown"
            mac = device.mac_address

        identified_type, confidence = identifier.identify(
            device_ip,
            mac,
            open_ports,
            manufacturer=manufacturer,
        )

        result = {
            "type": identified_type,
            "manufacturer": manufacturer,
            "model": (device.model if not ip else "Unknown"),
            "confidence": confidence,
        }

        if detailed:
            click.echo(format_device_details(result))
        else:
            click.echo("Device identified:")
            click.echo(f"  Type: {result.get('type', 'unknown')}")
            click.echo(f"  Manufacturer: {result.get('manufacturer', 'Unknown')}")
            click.echo(f"  Model: {result.get('model', 'Unknown')}")
            click.echo(f"  Confidence: {result.get('confidence', 0):.2%}")

        if not ip:
            device.device_type = result.get("type", device.device_type)
            device.manufacturer = result.get("manufacturer", device.manufacturer)
            device.model = result.get("model", device.model)
            device.confidence_score = result.get("confidence", device.confidence_score)
            device.metadata = {
                **(device.metadata or {}),
                "identification_result": result,
                "last_identified": datetime.now().isoformat(),
            }
            repo.save(device)
            click.echo("Device information updated in database")

        return 0
        
    except Exception as e:
        click.echo(f"Error: Identification failed: {e}", err=True)
        return 1

@scan.command()
@click.option('--count', '-c', default=5, type=int,
              help='Number of mock devices to generate')
@click.option('--types', '-t', multiple=True,
              type=click.Choice(['camera', 'gate', 'sensor', 'switch']),
              help='Device types to generate')
@click.option('--save', is_flag=True,
              help='Save mock devices to database')
@click.option('--list-types', is_flag=True,
              help='List available mock device types')
@click.pass_context
def mock(ctx, count: int, types: tuple, save: bool, list_types: bool):
    """Generate mock devices for testing"""
    
    if list_types:
        click.echo("Available mock device types:")
        click.echo("  camera - IP cameras with streaming capabilities")
        click.echo("  gate   - Hikvision gate controllers")
        click.echo("  sensor - Various sensors (motion, temperature, etc.)")
        click.echo("  switch - Smart switches and plugs")
        return 0
    
    generator = MockDeviceGenerator()
    
    # Convert tuple to list
    type_list = list(types) if types else ['camera', 'gate', 'sensor', 'switch']
    
    click.echo(f"Generating {count} mock device(s) of types: {', '.join(type_list)}")
    
    try:
        # Generate mock devices
        devices = generator.generate_mock_devices(count=count, types=type_list)
        
        # Display devices
        formatted = format_device_table(devices)
        click.echo(f"\n{formatted}")
        
        # Save to database if requested
        if save:
            repo = DeviceRepository()
            saved_count = 0
            
            for device_data in devices:
                # Check if device already exists
                existing = repo.get(device_data['id'])
                
                if not existing:
                    # Create mock device
                    device = Device(
                        id=device_data['id'],
                        device_type=device_data['type'],
                        ip_address=device_data['ip'],
                        mac_address=device_data.get('mac', '00:00:00:00:00:00'),
                        name=device_data['name'],
                        status=DeviceStatus.ONLINE,
                        manufacturer=device_data.get('manufacturer', 'Mock'),
                        model=device_data.get('model', 'Mock Model'),
                        confidence_score=1.0,  # Mock devices have 100% confidence
                        last_seen=datetime.now(),
                        config=device_data.get('config', {}),
                        metadata={
                            'is_mock': True,
                            'mock_type': device_data['type'],
                            'generated_at': datetime.now().isoformat()
                        }
                    )
                    repo.save(device)
                    saved_count += 1
            
            click.echo(f"\nSaved {saved_count} mock device(s) to database")
            click.echo("Note: Mock devices are for testing only")
        
        return 0
        
    except Exception as e:
        click.echo(f"Error: Mock generation failed: {e}", err=True)
        return 1

@scan.command()
@click.option('--device-id', '-d',
              help='Filter by device ID')
@click.option('--type', '-t',
              type=click.Choice(['camera', 'gate', 'sensor', 'switch', 'all']),
              default='all', help='Filter by device type')
@click.option('--status', '-s',
              type=click.Choice(['online', 'offline', 'all']),
              default='all', help='Filter by status')
@click.option('--limit', '-l', default=50, type=int,
              help='Maximum number of devices to show')
@click.option('--sort', default='last_seen',
              type=click.Choice(['name', 'type', 'ip', 'last_seen']),
              help='Sort order')
@click.option('--reverse', '-r', is_flag=True,
              help='Reverse sort order')
@click.pass_context
def list(ctx, device_id: Optional[str], type: str, status: str, 
         limit: int, sort: str, reverse: bool):
    """List discovered devices"""
    
    repo = DeviceRepository()
    
    try:
        # Get devices based on filters
        if device_id:
            device = repo.get(device_id)
            if not device:
                click.echo(f"Error: Device not found: {device_id}", err=True)
                return 1
            
            devices = [device]
        else:
            if type != 'all':
                devices = repo.get_by_type(type)
            else:
                devices = repo.get_all()
        
        # Filter by status
        if status != 'all':
            devices = [d for d in devices if d.status.value == status]
        
        # Sort devices
        reverse_sort = reverse
        if sort == 'name':
            devices.sort(key=lambda d: d.name, reverse=reverse_sort)
        elif sort == 'type':
            devices.sort(key=lambda d: d.device_type, reverse=reverse_sort)
        elif sort == 'ip':
            devices.sort(key=lambda d: d.ip_address, reverse=reverse_sort)
        elif sort == 'last_seen':
            devices.sort(key=lambda d: d.last_seen or datetime.min, reverse=not reverse_sort)
        
        # Limit results
        devices = devices[:limit]
        
        # Convert to display format
        display_devices = []
        for device in devices:
            display_devices.append({
                'id': device.id,
                'type': device.device_type,
                'ip': device.ip_address,
                'name': device.name,
                'status': device.status.value,
                'manufacturer': device.manufacturer,
                'model': device.model,
                'last_seen': device.last_seen.strftime('%Y-%m-%d %H:%M:%S') if device.last_seen else 'Never'
            })
        
        # Display results
        if not display_devices:
            click.echo("No devices found matching criteria")
            return 0
        
        formatted = format_device_table(display_devices)
        click.echo(f"\nFound {len(display_devices)} device(s):")
        click.echo(formatted)
        
        # Show summary
        type_counts = {}
        for device in display_devices:
            dev_type = device['type']
            type_counts[dev_type] = type_counts.get(dev_type, 0) + 1
        
        click.echo(f"\nSummary:")
        for dev_type, count in type_counts.items():
            click.echo(f"  {dev_type}: {count} device(s)")
        
        return 0
        
    except Exception as e:
        click.echo(f"Error: Failed to list devices: {e}", err=True)
        return 1

@scan.command()
@click.option('--device-id', '-d', required=True,
              help='Device ID to test')
@click.option('--timeout', '-t', default=5, type=int,
              help='Connection timeout in seconds')
@click.pass_context
def test(ctx, device_id: str, timeout: int):
    """Test connection to a device"""
    
    repo = DeviceRepository()
    
    # Get device
    device = repo.get(device_id)
    if not device:
        click.echo(f"Error: Device not found: {device_id}", err=True)
        return 1
    
    click.echo(f"Testing connection to: {device.name} ({device.ip_address})")
    
    try:
        # Import appropriate device adapter
        if device.device_type == 'camera':
            from homeauto.devices.camera import CameraDevice
            config = ctx.obj['CONFIG']
            credentials = config.get_credentials('camera') or {}
            adapter = CameraDevice(device.ip_address, credentials)
        elif device.device_type == 'gate':
            from homeauto.devices.gate import HikGateDevice
            config = ctx.obj['CONFIG']
            credentials = config.get_credentials('gate') or {}
            adapter = HikGateDevice(device.ip_address, credentials)
        else:
            click.echo(f"Warning: No specific adapter for device type: {device.device_type}")
            click.echo("Testing basic connectivity...")
            
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            
            result = sock.connect_ex((device.ip_address, 80))
            sock.close()
            
            if result == 0:
                click.echo("Basic connectivity: OK (port 80 open)")
                return 0
            else:
                click.echo("Basic connectivity: FAILED")
                return 1
        
        # Test connection with device-specific adapter
        is_connected = adapter.test_connection()
        
        if is_connected:
            click.echo("Connection test: SUCCESS")
            
            # Get device info if connected
            try:
                info = adapter.get_info()
                click.echo(f"  Manufacturer: {info.get('manufacturer', 'Unknown')}")
                click.echo(f"  Model: {info.get('model', 'Unknown')}")
                click.echo(f"  Firmware: {info.get('firmware_version', 'Unknown')}")
            except:
                click.echo("  (Additional info not available)")
            
            return 0
        else:
            click.echo("Connection test: FAILED")
            return 1
        
    except Exception as e:
        click.echo(f"Error: Connection test failed: {e}", err=True)
        return 1

# For backward compatibility with existing code
def main():
    """Main entry point for the scan command (backward compatibility)"""
    import sys
    from .main import cli
    
    # Run just the scan command group
    sys.argv = ['homeauto', 'scan'] + sys.argv[1:]
    cli(obj={})





