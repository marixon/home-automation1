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
        self.use_mock = self.config.get_setting("testing.use_mock_devices", False)

    def execute(self) -> Dict:
        """Execute the scan command"""
        self.logger.info("Starting device scan...")
        
        if self.use_mock:
            print("Using mock devices for testing...")
            result = self._scan_mock_devices()
        else:
            print("Scanning real network devices...")
            result = self._scan_real_devices()
        
        # List all devices
        devices = self.repository.get_all()
        if devices:
            print("\n" + "=" * 80)
            print("All Devices in Database:")
            print("=" * 80)
            
            device_list = []
            for device in devices:
                device_list.append({
                    "id": device.id,
                    "type": device.device_type,
                    "ip": device.ip_address,
                    "name": device.name,
                    "status": device.status.value
                })
            
            print(format_device_table(device_list))
        
        self.logger.info("Device scan completed")
        return result

    def _scan_mock_devices(self) -> Dict:
        """Scan mock devices for testing"""
        mock_generator = MockDeviceGenerator(
            count=self.config.get_setting("testing.mock_device_count", 5)
        )
        
        mock_devices = mock_generator.generate_devices()
        discovered = 0
        
        for device in mock_devices:
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

            # Offer camera services if device is a camera
            if device_type == "camera":
                self._offer_camera_services(device)

            if self.verbose:
                self.logger.debug(f"Device saved to database: {device.id}")

        self.logger.info(f"Discovered {discovered} real devices")
        if self.verbose:
            self.logger.debug(f"Total active hosts scanned: {len(active_hosts)}")

        return {"discovered": discovered}

    def _offer_camera_services(self, camera_device):
        """Offer camera services for a newly discovered camera"""
        try:
            print(f"\n🎥 Camera detected: {camera_device.name} ({camera_device.ip_address})")
            print("Camera services available:")
            print("  1. On-demand snapshots")
            print("  2. Scheduled snapshots")
            print("  3. Motion detection")
            print("  4. Object recognition")
            print("  5. Multiple storage options (local, FTP, Google Drive)")
            
            response = input("\nEnable camera services for this camera? (y/N): ").strip().lower()
            
            if response == 'y' or response == 'yes':
                print("Enabling camera services...")
                
                # Create CameraDevice instance
                from homeauto.devices.camera import CameraDevice
                credentials = self.config.get_credentials('camera') or {}
                camera = CameraDevice(camera_device.ip_address, credentials)
                
                # Enable services
                if camera.enable_services():
                    print("✅ Camera services enabled successfully!")
                    print("   - Access camera services via web interface: http://localhost:8000/static/camera_services.html")
                    print("   - Use CLI: python -m homeauto.services.camera.global_manager start")
                else:
                    print("⚠️  Could not enable camera services. Check configuration.")
            else:
                print("Camera services not enabled. You can enable them later via the web interface.")
                
        except Exception as e:
            self.logger.error(f"Error offering camera services: {e}")
            print(f"Error: {e}")


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
        
        print(f"\nScan completed. Discovered {result['discovered']} devices.")
        sys.exit(0)
        
    except KeyboardInterrupt:
        print("\nScan interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"Error during scan: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
