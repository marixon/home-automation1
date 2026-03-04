import sys
import argparse
from typing import Dict
from homeauto.database.repository import DeviceRepository
from homeauto.config.manager import ConfigManager
from homeauto.devices.gate import HikGateDevice
from homeauto.utils.logging_config import setup_logging, get_logger, log_device_communication


class ConfigCommand:
    def __init__(self, config_path: str = "config.yaml", verbose: bool = False):
        self.config = ConfigManager(config_path)
        self.verbose = verbose
        self.repository = DeviceRepository()
        
        # Setup logging
        self.logger = get_logger("cli.config")
        setup_logging(verbose=verbose)

    def list_devices(self) -> Dict:
        """List all discovered devices"""
        devices = self.repository.get_all()

        print("\nConfigured Devices:\n")
        print(f"{'ID':<15} {'Type':<10} {'Name':<25} {'IP':<15}")
        print("-" * 70)

        for device in devices:
            print(f"{device.id:<15} {device.device_type:<10} {device.name:<25} {device.ip_address:<15}")

        print(f"\nTotal: {len(devices)} devices\n")
        return {"count": len(devices)}

    def set_credentials(self, device_type: str, username: str, password: str) -> bool:
        """Set credentials for a device type"""
        if "credentials" not in self.config.config:
            self.config.config["credentials"] = {}

        self.config.config["credentials"][device_type] = {
            "username": username,
            "password": password
        }

        self.config.save(self.config.config)
        print(f"Credentials saved for {device_type}")
        
        if self.verbose:
            self.logger.debug(f"Credentials set for {device_type}: username={username}")
        
        return True

    def get_credentials(self, device_type: str) -> Dict:
        """Get credentials for a device type"""
        creds = self.config.get_credentials(device_type)

        if creds:
            print(f"\nCredentials for {device_type}:")
            print(f"  Username: {creds.get('username', 'Not set')}")
            print(f"  Password: {'*' * len(creds.get('password', ''))}\n")
        else:
            print(f"No credentials found for {device_type}\n")

        return creds

    def set_setting(self, key: str, value: str) -> bool:
        """Set a configuration setting"""
        if "settings" not in self.config.config:
            self.config.config["settings"] = {}

        # Try to convert value to appropriate type
        try:
            if value.isdigit():
                value = int(value)
            elif value.replace('.', '', 1).isdigit():
                value = float(value)
            elif value.lower() in ['true', 'false']:
                value = value.lower() == 'true'
        except:
            pass

        self.config.config["settings"][key] = value
        self.config.save(self.config.config)
        print(f"Setting {key} = {value}")
        
        if self.verbose:
            self.logger.debug(f"Configuration setting updated: {key}={value}")
        
        return True

    def show_config(self) -> Dict:
        """Show current configuration"""
        print("\nCurrent Configuration:\n")

        if "credentials" in self.config.config:
            print("Credentials:")
            for device_type, creds in self.config.config["credentials"].items():
                print(f"  {device_type}:")
                print(f"    username: {creds.get('username', 'Not set')}")
                print(f"    password: {'*' * len(creds.get('password', ''))}")

        if "settings" in self.config.config:
            print("\nSettings:")
            for key, value in self.config.config["settings"].items():
                print(f"  {key}: {value}")

        print()
        return self.config.config

    def test_gate_connection(self, device_id: str) -> Dict:
        """Test connection to a gate device"""
        device = self.repository.get(device_id)
        if not device:
            print(f"Device {device_id} not found")
            return {"success": False, "message": "Device not found"}
        
        if device.device_type != "gate":
            print(f"Device {device_id} is not a gate")
            return {"success": False, "message": "Device is not a gate"}
        
        credentials = self.config.get_credentials("gate") or {}
        gate = HikGateDevice(device.ip_address, credentials)
        
        if self.verbose:
            self.logger.debug(f"Testing connection to gate {device.name} at {device.ip_address}")
            self.logger.debug(f"Using credentials: username={credentials.get('username', 'not set')}")
        
        print(f"\nTesting connection to gate {device.name} ({device.ip_address})...")
        connected = gate.test_connection()
        
        if connected:
            print("Gate is reachable")
            # Get additional info
            info = gate.get_info()
            status = gate.get_status()
            print(f"   Model: {info.get('model', 'Unknown')}")
            print(f"   Serial: {info.get('serial_number', 'Unknown')}")
            print(f"   Status: {status.get('state', 'unknown')}")
            print(f"   Online: {status.get('online', False)}")
            
            if self.verbose:
                log_device_communication(self.logger, "gate", device.ip_address, 
                                       "connection_test", "Device reachable", success=True)
                self.logger.debug(f"Device info: {info}")
                self.logger.debug(f"Device status: {status}")
            
            return {"success": True, "connected": True, "info": info, "status": status}
        else:
            print("Gate is not reachable")
            
            if self.verbose:
                log_device_communication(self.logger, "gate", device.ip_address, 
                                       "connection_test", "Device not reachable", success=False)
            
            return {"success": False, "connected": False}

    def control_gate(self, device_id: str, action: str) -> Dict:
        """Control a gate device (open/close/toggle)"""
        device = self.repository.get(device_id)
        if not device or device.device_type != "gate":
            return {"success": False, "message": "Gate device not found"}
        
        credentials = self.config.get_credentials("gate") or {}
        gate = HikGateDevice(device.ip_address, credentials)
        
        if self.verbose:
            self.logger.debug(f"Controlling gate {device.name} at {device.ip_address}")
            self.logger.debug(f"Action: {action}")
            self.logger.debug(f"Using credentials: username={credentials.get('username', 'not set')}")
        
        if action == "open":
            result = gate.open_gate()
        elif action == "close":
            result = gate.close_gate()
        elif action == "toggle":
            result = gate.toggle_gate()
        else:
            return {"success": False, "message": f"Unknown action: {action}"}
        
        if self.verbose:
            success = result.get("success", False)
            message = result.get("message", "")
            log_device_communication(self.logger, "gate", device.ip_address, 
                                   f"{action}_gate", message, success=success)
            self.logger.debug(f"Gate control result: {result}")
        
        return result


def main():
    """Main entry point for homeauto-config command"""
    parser = argparse.ArgumentParser(description="Home Automation Configuration Tool")
    parser.add_argument("--verbose", "-v", action="store_true", 
                       help="Enable verbose logging for device communication details")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # List devices
    subparsers.add_parser("list", help="List all discovered devices")

    # Set credentials
    creds_parser = subparsers.add_parser("set-creds", help="Set device credentials")
    creds_parser.add_argument("device_type", help="Device type (camera, tuya, hikconnect)")
    creds_parser.add_argument("username", help="Username")
    creds_parser.add_argument("password", help="Password")

    # Get credentials
    get_creds_parser = subparsers.add_parser("get-creds", help="Get device credentials")
    get_creds_parser.add_argument("device_type", help="Device type")

    # Set setting
    setting_parser = subparsers.add_parser("set", help="Set a configuration setting")
    setting_parser.add_argument("key", help="Setting key")
    setting_parser.add_argument("value", help="Setting value")

    # Show config
    subparsers.add_parser("show", help="Show current configuration")

    # Test gate connection
    test_gate_parser = subparsers.add_parser("test-gate", help="Test connection to a gate device")
    test_gate_parser.add_argument("device_id", help="Device ID of the gate")

    # Control gate
    control_gate_parser = subparsers.add_parser("control-gate", help="Control a gate device")
    control_gate_parser.add_argument("device_id", help="Device ID of the gate")
    control_gate_parser.add_argument("action", choices=["open", "close", "toggle"], help="Action to perform")

    args = parser.parse_args()

    cmd = ConfigCommand(verbose=args.verbose)

    try:
        if args.command == "list":
            cmd.list_devices()
        elif args.command == "set-creds":
            cmd.set_credentials(args.device_type, args.username, args.password)
        elif args.command == "get-creds":
            cmd.get_credentials(args.device_type)
        elif args.command == "set":
            cmd.set_setting(args.key, args.value)
        elif args.command == "show":
            cmd.show_config()
        elif args.command == "test-gate":
            result = cmd.test_gate_connection(args.device_id)
            if not result.get("success"):
                sys.exit(1)
        elif args.command == "control-gate":
            result = cmd.control_gate(args.device_id, args.action)
            if result.get("success"):
                print(f"Command executed successfully: {result.get('message', '')}")
            else:
                print(f"Command failed: {result.get('message', '')}")
                sys.exit(1)
        else:
            parser.print_help()
            return 1

        return 0
    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
