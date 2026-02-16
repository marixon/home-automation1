import requests
from typing import Dict, Any, List
from homeauto.devices.base import BaseDevice, DeviceCapability
from homeauto.utils.retry import retry_with_backoff


class HikGateDevice(BaseDevice):
    """Hikvision gate controller adapter"""

    def __init__(self, ip: str, credentials: Dict[str, str]):
        super().__init__(ip, credentials)
        self.base_url = f"http://{ip}"
        self.timeout = 5

    @retry_with_backoff(max_attempts=3, base_delay=1.0)
    def test_connection(self) -> bool:
        """Test gate controller connectivity"""
        try:
            response = requests.get(
                f"{self.base_url}/ISAPI/System/status",
                auth=(
                    self.credentials.get("username"),
                    self.credentials.get("password")
                ),
                timeout=self.timeout
            )
            return response.status_code in [200, 401]
        except Exception:
            return False

    @retry_with_backoff(max_attempts=3)
    def get_info(self) -> Dict[str, Any]:
        """Get gate controller information"""
        return {
            "type": "gate",
            "ip": self.ip,
            "model": "Hikvision Gate Controller",
            "manufacturer": "Hikvision",
        }

    @retry_with_backoff(max_attempts=3)
    def get_status(self) -> Dict[str, Any]:
        """Get gate status"""
        try:
            response = requests.get(
                f"{self.base_url}/ISAPI/AccessControl/Door/status",
                auth=(
                    self.credentials.get("username"),
                    self.credentials.get("password")
                ),
                timeout=self.timeout
            )

            if response.status_code == 200:
                # Parse XML response (simplified)
                return {
                    "online": True,
                    "state": "closed",  # Would parse from XML
                    "locked": True,
                }
        except Exception:
            pass

        return {"online": False, "state": "unknown"}

    def open_gate(self) -> bool:
        """Open the gate"""
        try:
            response = requests.put(
                f"{self.base_url}/ISAPI/AccessControl/RemoteControl/door/1",
                auth=(
                    self.credentials.get("username"),
                    self.credentials.get("password")
                ),
                data='<RemoteControlDoor><cmd>open</cmd></RemoteControlDoor>',
                headers={"Content-Type": "application/xml"},
                timeout=self.timeout
            )
            return response.status_code == 200
        except Exception:
            return False

    def close_gate(self) -> bool:
        """Close the gate"""
        try:
            response = requests.put(
                f"{self.base_url}/ISAPI/AccessControl/RemoteControl/door/1",
                auth=(
                    self.credentials.get("username"),
                    self.credentials.get("password")
                ),
                data='<RemoteControlDoor><cmd>close</cmd></RemoteControlDoor>',
                headers={"Content-Type": "application/xml"},
                timeout=self.timeout
            )
            return response.status_code == 200
        except Exception:
            return False

    def get_capabilities(self) -> List[DeviceCapability]:
        return [
            DeviceCapability.STATUS,
            DeviceCapability.CONTROL,
            DeviceCapability.CONFIG,
        ]
