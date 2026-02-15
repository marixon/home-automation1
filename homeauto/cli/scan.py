import sys
from typing import List, Dict
from datetime import datetime
from homeauto.discovery.scanner import NetworkScanner
from homeauto.discovery.identifier import DeviceIdentifier
from homeauto.discovery.mock import MockDeviceGenerator
from homeauto.database.repository import DeviceRepository
from homeauto.database.models import Device, DeviceStatus
from homeauto.config.manager import ConfigManager


def format_device_table(devices: List[Dict]) -> str:
    """Format devices as ASCII table"""
    if not devices:
        return "No devices found."

    # Header
    header = f"{'ID':<15} {'Type':<10} {'IP':<15} {'Name':<25} {'Status':<10}"
    separator = "-" * 80

    rows = [header, separator]

    for device in devices:
        row = (
            f"{device['id']:<15} "
            f"{device['type']:<10} "
            f"{device['ip']:<15} "
            f"{device['name']:<25} "
            f"{device['status']:<10}"
        )
        rows.append(row)

    return "\n".join(rows)


class ScanCommand:
    def __init__(self, config_path: str = "config.yaml"):
        self.config = ConfigManager(config_path)
        self.scanner = NetworkScanner(
            subnet=self.config.get_setting("subnet", "192.168.1.0/24")
        )
        self.identifier = DeviceIdentifier()
        self.repository = DeviceRepository()
        self.use_mock = self.config.get("testing.use_mock_devices", False)

    def execute(self) -> Dict:
        """Execute device scan"""
        print("🔍 Scanning network for devices...")

        if self.use_mock:
            return self._scan_mock_devices()
        else:
            return self._scan_real_devices()

    def _scan_mock_devices(self) -> Dict:
        """Scan using mock devices"""
        print("Using mock devices for testing")

        generator = MockDeviceGenerator()
        count = self.config.get("testing.mock_device_count", 5)
        mock_devices = generator.generate(count=count)

        discovered = 0

        for mock_device in mock_devices:
            if not mock_device.is_online():
                continue

            info = mock_device.get_info()

            device = Device(
                id=f"{info['type']}-{info['ip'].split('.')[-1]}",
                device_type=info['type'],
                ip_address=info['ip'],
                mac_address=info['mac'],
                name=f"{info['type'].title()} {info['ip'].split('.')[-1]}",
                status=DeviceStatus.ONLINE,
                manufacturer=info['manufacturer'],
                model=info['model'],
                confidence_score=0.9,
            )

            self.repository.save(device)
            discovered += 1
            print(f"  Found: {device.name} ({device.ip_address})")

        print(f"\n✅ Discovered {discovered} devices")
        return {"discovered": discovered}

    def _scan_real_devices(self) -> Dict:
        """Scan real network devices"""
        # Scan for active hosts
        active_hosts = self.scanner.scan_subnet()
        print(f"Found {len(active_hosts)} active hosts")

        discovered = 0
        common_ports = [80, 443, 554, 8000, 8080, 6668]

        for ip in active_hosts:
            print(f"  Probing {ip}...")

            # Scan ports
            open_ports = self.scanner.scan_ports(ip, common_ports)
            if not open_ports:
                continue

            # Get MAC address
            mac = self.scanner.get_mac_address(ip)

            # Identify device
            device_type, confidence = self.identifier.identify(
                ip=ip,
                mac=mac,
                open_ports=open_ports,
            )

            if device_type == "unknown":
                continue

            device = Device(
                id=f"{device_type}-{ip.split('.')[-1]}",
                device_type=device_type,
                ip_address=ip,
                mac_address=mac,
                name=f"{device_type.title()} {ip.split('.')[-1]}",
                status=DeviceStatus.ONLINE,
                confidence_score=confidence,
            )

            self.repository.save(device)
            discovered += 1
            print(f"    ✓ {device_type} at {ip}")

        print(f"\n✅ Discovered {discovered} devices")
        return {"discovered": discovered}


def main():
    """Main entry point for homeauto-scan command"""
    try:
        cmd = ScanCommand()
        result = cmd.execute()

        # Show discovered devices
        print("\n📋 Discovered devices:")
        devices = cmd.repository.get_all()
        device_dicts = [
            {
                "id": d.id,
                "type": d.device_type,
                "ip": d.ip_address,
                "name": d.name,
                "status": d.status.value,
            }
            for d in devices
        ]
        print(format_device_table(device_dicts))

        return 0
    except KeyboardInterrupt:
        print("\n\n⚠️  Scan interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
