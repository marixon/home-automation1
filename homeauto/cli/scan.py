import sys
import argparse
from typing import List, Dict
from datetime import datetime
from homeauto.discovery.scanner import NetworkScanner
from homeauto.discovery.identifier import DeviceIdentifier
from homeauto.discovery.mock import MockDeviceGenerator
from homeauto.database.repository import DeviceRepository
from homeauto.database.models import Device, DeviceStatus
from homeauto.config.manager import ConfigManager
from homeauto.utils.logging_config import setup_logging, get_logger, log_network_scan, log_device_identification


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
    def __init__(self, config_path: str = "config.yaml", verbose: bool = False):
        self.config = ConfigManager(config_path)
        self.verbose = verbose
        
        # Setup logging
        self.logger = get_logger("cli.scan")
        setup_logging(verbose=verbose)
        
        self.scanner = NetworkScanner(
            subnet=self.config.get_setting("subnet", "192.168.1.0/24")
        )
        self.identifier = DeviceIdentifier()
        self.repository = DeviceRepository()
        self.use_mock = self.config.get("testing.use_mock_devices", False)

    def execute(self) -> Dict:
        """Execute device scan"""
        self.logger.info("Scanning network for devices...")
        if self.verbose:
            self.logger.debug(f"Using subnet: {self.scanner.subnet}")
            self.logger.debug(f"Mock mode: {self.use_mock}")

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

        if self.verbose:
            self.logger.debug(f"Generating {count} mock devices")

        discovered = 0

        for mock_device in mock_devices:
            if not mock_device.is_online():
                continue

            info = mock_device.get_info()

            # Create device object
            device = Device(
                id=f"{info['type']}-{info['ip'].split('.')[-1]}",
                device_type=info["type"],
                ip_address=info["ip"],
                mac_address=info["mac"],
                name=f"{info['type'].title()} {info['ip'].split('.')[-1]}",
                status=DeviceStatus.ONLINE,
                manufacturer=info["manufacturer"],
                model=info["model"],
                confidence_score=0.9,
            )

            self.repository.save(device)
            discovered += 1
            print(f"  Found: {device.name} ({device.ip_address})")

            if self.verbose:
                self.logger.debug(f"Mock device created: {device.device_type} at {device.ip_address}")

        self.logger.info(f"Discovered {discovered} mock devices")
        if self.verbose:
            self.logger.debug(f"Total mock devices generated: {len(mock_devices)}")

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

            if self.verbose:
                self.logger.debug(f"Scanning host: {ip}")

            # Scan ports
            open_ports = self.scanner.scan_ports(ip, common_ports)
            
            if self.verbose:
                log_network_scan(self.logger, ip, open_ports, 
                               f"Found {len(open_ports)} open ports" if open_ports else "No open ports")
            
            if not open_ports:
                continue

            # Get MAC address
            mac = self.scanner.get_mac_address(ip)
            
            if self.verbose:
                self.logger.debug(f"MAC address for {ip}: {mac}")

            # Identify device
            device_type, confidence = self.identifier.identify(
                ip=ip,
                mac=mac,
                open_ports=open_ports,
            )

            if self.verbose:
                log_device_identification(self.logger, ip, mac, device_type, confidence)

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

            if self.verbose:
                self.logger.debug(f"Device saved to database: {device.id}")

        self.logger.info(f"Discovered {discovered} real devices")
        if self.verbose:
            self.logger.debug(f"Total active hosts scanned: {len(active_hosts)}")

        return {"discovered": discovered}


def main():
    """Main entry point for homeauto-scan command"""
    parser = argparse.ArgumentParser(description="Home Automation Device Scanner")
    parser.add_argument("--verbose", "-v", action="store_true", 
                       help="Enable verbose logging for device communication details")
    parser.add_argument("--mock", action="store_true", 
                       help="Use mock devices for testing")
    parser.add_argument("--subnet", help="Subnet to scan (e.g., 192.168.1.0/24)")
    
    args = parser.parse_args()
    
    try:
        cmd = ScanCommand(verbose=args.verbose)
        
        # Override config if command line arguments provided
        if args.mock:
            cmd.use_mock = True
        if args.subnet:
            cmd.scanner.subnet = args.subnet
            
        result = cmd.execute()

        # Show discovered devices
        print("\nDiscovered devices:")
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
        print("\n\nScan interrupted by user")
        return 1
    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
