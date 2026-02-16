import sys
from typing import Dict
from homeauto.database.repository import DeviceRepository
from homeauto.config.manager import ConfigManager


class ConfigCommand:
    def __init__(self, config_path: str = "config.yaml"):
        self.config = ConfigManager(config_path)
        self.repository = DeviceRepository()

    def list_devices(self) -> Dict:
        """List all discovered devices"""
        devices = self.repository.get_all()

        print("\n📋 Configured Devices:\n")
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
        print(f"✅ Credentials saved for {device_type}")
        return True

    def get_credentials(self, device_type: str) -> Dict:
        """Get credentials for a device type"""
        creds = self.config.get_credentials(device_type)

        if creds:
            print(f"\n🔑 Credentials for {device_type}:")
            print(f"  Username: {creds.get('username', 'Not set')}")
            print(f"  Password: {'*' * len(creds.get('password', ''))}\n")
        else:
            print(f"❌ No credentials found for {device_type}\n")

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
        print(f"✅ Setting {key} = {value}")
        return True

    def show_config(self) -> Dict:
        """Show current configuration"""
        print("\n⚙️  Current Configuration:\n")

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


def main():
    """Main entry point for homeauto-config command"""
    import argparse

    parser = argparse.ArgumentParser(description="Home Automation Configuration Tool")
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

    args = parser.parse_args()

    cmd = ConfigCommand()

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
        else:
            parser.print_help()
            return 1

        return 0
    except Exception as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
