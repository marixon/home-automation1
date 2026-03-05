import requests
from typing import Dict, Any, List, Optional
from homeauto.devices.base import BaseDevice, DeviceCapability
from homeauto.utils.retry import retry_with_backoff
import base64


class CameraDevice(BaseDevice):
    """IP Camera device adapter (generic ONVIF/HTTP) with services support"""

    def __init__(self, ip: str, credentials: Dict[str, str]):
        super().__init__(ip, credentials)
        self.base_url = f"http://{ip}"
        self.timeout = 5
        self.services_enabled = False
        self.service_manager = None
        self.available_services = {
            "on_demand_snapshot": True,
            "scheduled_snapshots": True,
            "motion_detection": True,
            "object_recognition": True
        }

    @retry_with_backoff(max_attempts=3, base_delay=1.0)
    def test_connection(self) -> bool:
        """Test camera connectivity"""
        try:
            response = requests.get(
                f"{self.base_url}/",
                auth=(
                    self.credentials.get("username"),
                    self.credentials.get("password"),
                ),
                timeout=self.timeout,
            )
            return response.status_code in [
                200,
                401,
            ]  # 401 means auth required but reachable
        except Exception:
            return False

    @retry_with_backoff(max_attempts=3)
    def get_info(self) -> Dict[str, Any]:
        """Get camera information"""
        try:
            # Try ONVIF GetDeviceInformation
            response = requests.get(
                f"{self.base_url}/onvif/device_service",
                auth=(
                    self.credentials.get("username"),
                    self.credentials.get("password"),
                ),
                timeout=self.timeout,
            )

            if response.status_code == 200:
                data = response.json()
                return {
                    "manufacturer": data.get("Manufacturer", "Unknown"),
                    "model": data.get("Model", "Unknown"),
                    "firmware_version": data.get("FirmwareVersion", "Unknown"),
                    "serial_number": data.get("SerialNumber", "Unknown"),
                    "hardware_id": data.get("HardwareId", "Unknown"),
                }
        except Exception:
            pass

        # Fallback to basic HTTP check
        try:
            response = requests.get(
                self.base_url,
                auth=(
                    self.credentials.get("username"),
                    self.credentials.get("password"),
                ),
                timeout=self.timeout,
            )
            return {
                "manufacturer": "Generic IP Camera",
                "model": "HTTP Camera",
                "firmware_version": "Unknown",
                "serial_number": "N/A",
                "hardware_id": self.ip,
            }
        except Exception:
            return {
                "manufacturer": "Unknown",
                "model": "Unknown",
                "firmware_version": "Unknown",
                "serial_number": "Unknown",
                "hardware_id": self.ip,
            }

    @retry_with_backoff(max_attempts=3)
    def get_snapshot(self, quality: str = "medium") -> Optional[bytes]:
        """Get snapshot from camera"""
        try:
            # Try common snapshot URLs
            snapshot_urls = [
                f"{self.base_url}/snapshot.jpg",
                f"{self.base_url}/cgi-bin/snapshot.cgi",
                f"{self.base_url}/img/snapshot.cgi",
                f"{self.base_url}/video.jpg",
                f"{self.base_url}/jpg/image.jpg",
            ]

            for url in snapshot_urls:
                try:
                    response = requests.get(
                        url,
                        auth=(
                            self.credentials.get("username"),
                            self.credentials.get("password"),
                        ),
                        timeout=self.timeout,
                        stream=True,
                    )
                    if response.status_code == 200:
                        return response.content
                except Exception:
                    continue

            return None
        except Exception:
            return None

    def get_capabilities(self) -> List[DeviceCapability]:
        """Get device capabilities including camera services"""
        capabilities = super().get_capabilities()
        
        # Add camera-specific capabilities
        capabilities.extend([
            DeviceCapability.SNAPSHOT,
            DeviceCapability.VIDEO_STREAM,
            DeviceCapability.MOTION_DETECTION,
        ])
        
        # Add camera services capabilities if enabled
        if self.services_enabled:
            if self.available_services.get("on_demand_snapshot"):
                capabilities.append(DeviceCapability("on_demand_snapshot", "On-demand Snapshots"))
            if self.available_services.get("scheduled_snapshots"):
                capabilities.append(DeviceCapability("scheduled_snapshots", "Scheduled Snapshots"))
            if self.available_services.get("motion_detection"):
                capabilities.append(DeviceCapability("motion_detection_service", "Motion Detection Service"))
            if self.available_services.get("object_recognition"):
                capabilities.append(DeviceCapability("object_recognition", "Object Recognition"))
        
        return capabilities

    def enable_services(self, config: Optional[Dict[str, Any]] = None) -> bool:
        """Enable camera services for this device"""
        try:
            # Import here to avoid circular imports
            from homeauto.services.camera.manager import CameraServiceManager
            from homeauto.config.manager import ConfigManager
            
            # Get configuration
            config_manager = ConfigManager()
            camera_config = config_manager.config.get('camera_services', {})
            
            # Use provided config or defaults
            if config is None:
                defaults = camera_config.get('defaults', {})
                config = defaults
            
            # Create service manager
            self.service_manager = CameraServiceManager(self, config)
            
            # Initialize services
            if self.service_manager.initialize():
                self.services_enabled = True
                return True
            else:
                self.service_manager = None
                return False
                
        except ImportError as e:
            print(f"Error importing camera services: {e}")
            return False
        except Exception as e:
            print(f"Error enabling camera services: {e}")
            return False

    def disable_services(self) -> bool:
        """Disable camera services for this device"""
        if self.service_manager:
            try:
                self.service_manager.stop()
                self.service_manager.cleanup()
                self.service_manager = None
                self.services_enabled = False
                return True
            except Exception as e:
                print(f"Error disabling camera services: {e}")
                return False
        return True

    def get_service_status(self) -> Dict[str, Any]:
        """Get camera service status"""
        if self.service_manager:
            return self.service_manager.get_status()
        else:
            return {
                "services_enabled": False,
                "available_services": self.available_services,
                "service_manager": None
            }

    def take_snapshot(self, metadata: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """Take a snapshot using camera services if enabled"""
        if self.service_manager:
            return self.service_manager.take_snapshot(metadata)
        else:
            # Fallback to basic snapshot
            image_data = self.get_snapshot()
            if image_data:
                return {
                    "success": True,
                    "image_data": base64.b64encode(image_data).decode('utf-8'),
                    "metadata": metadata or {}
                }
            return None

    def __del__(self):
        """Cleanup when object is destroyed"""
        if self.service_manager:
            try:
                self.service_manager.cleanup()
            except:
                pass
