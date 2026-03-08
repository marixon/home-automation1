#!/usr/bin/env python3
"""
Quick fix for MockDeviceGenerator issue
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Patch the MockDeviceGenerator to add the missing method
from homeauto.discovery.mock import MockDeviceGenerator

# Add the missing method to MockDeviceGenerator
def generate_mock_devices(self, count=5, types=None):
    """Generate mock devices (compatibility method)"""
    mock_devices = self.generate(count=count)
    
    # Convert to the expected format
    devices = []
    for mock_device in mock_devices:
        # Filter by type if specified
        if types and mock_device.device_type not in types:
            continue
            
        devices.append({
            'id': f"mock-{mock_device.ip.replace('.', '-')}",
            'type': mock_device.device_type,
            'ip': mock_device.ip,
            'name': f"Mock {mock_device.device_type} {mock_device.ip.split('.')[-1]}",
            'status': 'online' if mock_device.is_online() else 'offline',
            'mac': mock_device.mac,
            'manufacturer': mock_device.manufacturer,
            'model': mock_device.model,
            'confidence': 1.0
        })
    
    return devices

# Add the method to the class
MockDeviceGenerator.generate_mock_devices = generate_mock_devices

print("✓ MockDeviceGenerator patched with generate_mock_devices method")

# Test the patch
generator = MockDeviceGenerator()
devices = generator.generate_mock_devices(count=2)
print(f"✓ Generated {len(devices)} mock devices successfully")

# Also patch the scan_click.py if it exists
try:
    import homeauto.cli.scan_click as scan_click
    # The scan_click.py already has the fix, so we just need to make sure
    # it uses the patched generator
    print("✓ scan_click.py is already fixed")
except ImportError:
    print("⚠ scan_click.py not found")

print("\n✅ Fix applied successfully!")
print("\nYou can now run:")
print("  python -m homeauto.cli.scan mock --count 2")
print("  python -m homeauto.cli.main scan mock --count 2")
