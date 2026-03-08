"""
Home Automation Camera Command
Camera services management
"""

import argparse
import sys
from datetime import datetime
from typing import Any, Dict

from homeauto.config.manager import ConfigManager
from homeauto.database.repository import DeviceRepository
from homeauto.devices.camera import CameraDevice
from homeauto.services.camera.global_manager import GlobalCameraServiceManager
from homeauto.services.camera.manager import CameraServiceManager
from homeauto.utils.logging_config import get_logger, setup_logging


class CameraCommand:
    def __init__(self, config_path: str = "config.yaml", verbose: bool = False):
        self.config = ConfigManager(config_path)
        self.verbose = verbose
        self.logger = get_logger("cli.camera")
        setup_logging(verbose=verbose)
        self.repo = DeviceRepository()

    def list_services(self) -> int:
        try:
            print("Camera Services Status")
            print("=" * 80)

            global_manager = GlobalCameraServiceManager()
            status = global_manager.get_status()

            print(f"Global Status: {'Running' if status['running'] else 'Stopped'}")
            print(f"Initialized: {status['initialized']}")
            print(f"Enabled: {status['enabled']}")

            stats = global_manager.stats
            print("\nStatistics:")
            print(f"  Total Cameras: {stats['total_cameras']}")
            print(f"  Initialized Cameras: {stats['initialized_cameras']}")
            print(f"  Running Cameras: {stats['running_cameras']}")
            print(f"  Total Snapshots: {stats['total_snapshots']}")
            print(f"  Motion Events: {stats['total_motion_events']}")
            print(f"  Object Detections: {stats['total_object_detections']}")

            cameras = self.repo.get_by_type("camera")
            if cameras:
                print(f"\nCameras ({len(cameras)}):")
                for camera in cameras:
                    print(f"  - {camera.name} ({camera.ip_address}) - {camera.status.value}")

            return 0
        except Exception as e:
            self.logger.error(f"Failed to list services: {e}")
            print(f"Error: {e}")
            return 1

    def start_services(self, camera_id: str = None) -> int:
        try:
            global_manager = GlobalCameraServiceManager()

            if camera_id:
                device = self.repo.get(camera_id)
                if not device:
                    print(f"Camera not found: {camera_id}")
                    return 1

                print(f"Starting services for: {device.name} ({device.ip_address})")
                credentials = self.config.get_credentials("camera") or {}
                camera_device = CameraDevice(device.ip_address, credentials)

                camera_config = self.config.config.get("camera_services", {}).get("defaults", {}).copy()
                cameras_config = self.config.config.get("camera_services", {}).get("cameras", {})
                if device.ip_address in cameras_config:
                    camera_config.update(cameras_config[device.ip_address])

                service_manager = CameraServiceManager(camera_device, camera_config)
                success = service_manager.start_all_services()
                print("Services started" if success else "Failed to start services")
                return 0 if success else 1

            print("Starting all camera services...")
            success = global_manager.start_all_services()
            print("All camera services started" if success else "Failed to start camera services")
            return 0 if success else 1
        except Exception as e:
            self.logger.error(f"Failed to start services: {e}")
            print(f"Error: {e}")
            return 1

    def stop_services(self, camera_id: str = None) -> int:
        try:
            global_manager = GlobalCameraServiceManager()

            if camera_id:
                device = self.repo.get(camera_id)
                if not device:
                    print(f"Camera not found: {camera_id}")
                    return 1
                print("Per-camera stop is not implemented yet. Use global stop.")
                return 1

            print("Stopping all camera services...")
            success = global_manager.stop_all_services()
            print("All camera services stopped" if success else "Failed to stop camera services")
            return 0 if success else 1
        except Exception as e:
            self.logger.error(f"Failed to stop services: {e}")
            print(f"Error: {e}")
            return 1

    def take_snapshot(self, camera_id: str, metadata: Dict[str, Any] = None) -> int:
        try:
            device = self.repo.get(camera_id)
            if not device:
                print(f"Camera not found: {camera_id}")
                return 1

            print(f"Taking snapshot from: {device.name} ({device.ip_address})")
            credentials = self.config.get_credentials("camera") or {}
            camera_device = CameraDevice(device.ip_address, credentials)
            snapshot_result = camera_device.get_snapshot()

            if snapshot_result.get("success") and snapshot_result.get("image_data"):
                import base64

                image_bytes = base64.b64decode(snapshot_result["image_data"])
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"snapshot_{device.id}_{timestamp}.jpg"
                with open(filename, "wb") as f:
                    f.write(image_bytes)

                print(f"Snapshot saved: {filename}")
                print(f"  Size: {len(image_bytes)} bytes")
                return 0

            print("Failed to take snapshot")
            return 1
        except Exception as e:
            self.logger.error(f"Failed to take snapshot: {e}")
            print(f"Error: {e}")
            return 1

    def show_config(self) -> int:
        try:
            config = self.config.config.get("camera_services", {})
            if not config:
                print("No camera services configuration found")
                return 0

            print("Camera Services Configuration")
            print("=" * 80)
            print(f"Enabled: {config.get('enabled', False)}")

            storage = config.get("storage", {})
            if storage:
                print("\nStorage Configuration:")
                for backend, settings in storage.items():
                    print(f"  {backend}: {'Enabled' if settings.get('enabled', False) else 'Disabled'}")
                    if settings.get("enabled", False):
                        for key, value in settings.items():
                            if key != "enabled" and not key.endswith("password"):
                                print(f"    {key}: {value}")

            services = config.get("defaults", {})
            if services:
                print("\nService Defaults:")
                for service, settings in services.items():
                    print(f"  {service}: {'Enabled' if settings.get('enabled', False) else 'Disabled'}")

            cameras = config.get("cameras", {})
            if cameras:
                print(f"\nCamera-specific configurations ({len(cameras)} cameras):")
                for ip, cam_config in cameras.items():
                    print(f"  {ip}: {cam_config.get('name', 'Unnamed')}")

            return 0
        except Exception as e:
            self.logger.error(f"Failed to show config: {e}")
            print(f"Error: {e}")
            return 1


def main():
    parser = argparse.ArgumentParser(description="Camera services management")
    parser.add_argument("--config", "-c", default="config.yaml", help="Path to configuration file")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")

    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    subparsers.add_parser("list", help="List camera services status")

    start_parser = subparsers.add_parser("start", help="Start camera services")
    start_parser.add_argument("--camera", "-c", help="Camera ID (optional, starts all if not specified)")

    stop_parser = subparsers.add_parser("stop", help="Stop camera services")
    stop_parser.add_argument("--camera", "-c", help="Camera ID (optional, stops all if not specified)")

    snapshot_parser = subparsers.add_parser("snapshot", help="Take camera snapshot")
    snapshot_parser.add_argument("camera_id", help="Camera ID")

    subparsers.add_parser("config", help="Show camera services configuration")

    args = parser.parse_args()
    cmd = CameraCommand(config_path=args.config, verbose=args.verbose)

    if args.command == "list":
        return cmd.list_services()
    if args.command == "start":
        return cmd.start_services(args.camera)
    if args.command == "stop":
        return cmd.stop_services(args.camera)
    if args.command == "snapshot":
        return cmd.take_snapshot(args.camera_id)
    if args.command == "config":
        return cmd.show_config()

    parser.print_help()
    return 1


try:
    import click

    @click.group()
    def camera():
        """Camera services management commands"""

    @camera.command()
    @click.pass_context
    def list(ctx):
        cmd = CameraCommand(config_path=ctx.obj.get("CONFIG_PATH", "config.yaml"), verbose=ctx.obj.get("VERBOSE", False))
        return cmd.list_services()

    @camera.command()
    @click.option("--camera", "-c", help="Camera ID (optional)")
    @click.pass_context
    def start(ctx, camera):
        cmd = CameraCommand(config_path=ctx.obj.get("CONFIG_PATH", "config.yaml"), verbose=ctx.obj.get("VERBOSE", False))
        return cmd.start_services(camera)

    @camera.command()
    @click.option("--camera", "-c", help="Camera ID (optional)")
    @click.pass_context
    def stop(ctx, camera):
        cmd = CameraCommand(config_path=ctx.obj.get("CONFIG_PATH", "config.yaml"), verbose=ctx.obj.get("VERBOSE", False))
        return cmd.stop_services(camera)

    @camera.command()
    @click.argument("camera_id")
    @click.pass_context
    def snapshot(ctx, camera_id):
        cmd = CameraCommand(config_path=ctx.obj.get("CONFIG_PATH", "config.yaml"), verbose=ctx.obj.get("VERBOSE", False))
        return cmd.take_snapshot(camera_id)

    @camera.command(name="config")
    @click.pass_context
    def config_cmd(ctx):
        cmd = CameraCommand(config_path=ctx.obj.get("CONFIG_PATH", "config.yaml"), verbose=ctx.obj.get("VERBOSE", False))
        return cmd.show_config()

except ImportError:
    camera = None


if __name__ == "__main__":
    sys.exit(main())
