import requests
from typing import Dict, Any, List
from homeauto.devices.base import BaseDevice, DeviceCapability
from homeauto.utils.retry import retry_with_backoff


class CameraDevice(BaseDevice):
    """IP Camera device adapter (generic ONVIF/HTTP)"""

    def __init__(self, ip: str, credentials: Dict[str, str]):
        super().__init__(ip, credentials)
        self.base_url = f"http://{ip}"
        self.timeout = 5

    @retry_with_backoff(max_attempts=3, base_delay=1.0)
    def test_connection(self) -> bool:
        """Test camera connectivity"""
        try:
            response = requests.get(
                f"{self.base_url}/",
                auth=(
                    self.credentials.get("username"),
                    self.credentials.get("password")
                ),
                timeout=self.timeout
            )
            return response.status_code in [200, 401]  # 401 means auth required but reachable
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
                    self.credentials.get("password")
                ),
                timeout=self.timeout
            )

            if response.status_code == 200:
                data = response.json()
                return {
                    "type": "camera",
                    "ip": self.ip,
                    "model": data.get("model", "Unknown"),
                    "firmware": data.get("firmware", "Unknown"),
                }
        except Exception:
            pass

        # Fallback to basic info
        return {
            "type": "camera",
            "ip": self.ip,
            "model": "Generic IP Camera",
            "firmware": "Unknown",
        }

    @retry_with_backoff(max_attempts=3)
    def get_status(self) -> Dict[str, Any]:
        """Get camera status"""
        online = self.test_connection()

        return {
            "online": online,
            "streaming": online,  # Assume streaming if online
            "recording": False,   # Would need specific API call
        }

    def get_capabilities(self) -> List[DeviceCapability]:
        return [
            DeviceCapability.STATUS,
            DeviceCapability.CONFIG,
            DeviceCapability.STREAM,
        ]

    def get_stream_url(self) -> str:
        """Get RTSP stream URL"""
        username = self.credentials.get("username", "")
        password = self.credentials.get("password", "")
        return f"rtsp://{username}:{password}@{self.ip}:554/stream1"
