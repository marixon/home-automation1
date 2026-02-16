import requests
import time
import hashlib
import hmac
from typing import Dict, Any, List
from homeauto.devices.base import BaseDevice, DeviceCapability
from homeauto.utils.retry import retry_with_backoff


class TuyaDevice(BaseDevice):
    """Tuya smart device adapter (sensors, switches, etc.)"""

    def __init__(self, ip: str, credentials: Dict[str, str]):
        super().__init__(ip, credentials)
        self.base_url = f"http://{ip}"
        self.api_key = credentials.get("api_key")
        self.secret = credentials.get("secret")
        self.device_id = credentials.get("device_id")
        self.timeout = 5

    def _generate_signature(self, payload: str, timestamp: str) -> str:
        """Generate HMAC signature for Tuya API"""
        message = f"{self.api_key}{timestamp}{payload}"
        signature = hmac.new(
            self.secret.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest().upper()
        return signature

    @retry_with_backoff(max_attempts=3, base_delay=1.0)
    def test_connection(self) -> bool:
        """Test device connectivity"""
        try:
            timestamp = str(int(time.time() * 1000))
            payload = ""
            signature = self._generate_signature(payload, timestamp)

            headers = {
                "client_id": self.api_key,
                "sign": signature,
                "t": timestamp,
                "sign_method": "HMAC-SHA256"
            }

            response = requests.post(
                f"{self.base_url}/v1.0/devices/{self.device_id}/commands",
                headers=headers,
                json={"commands": []},
                timeout=self.timeout
            )
            return response.status_code == 200
        except Exception:
            return False

    @retry_with_backoff(max_attempts=3)
    def get_info(self) -> Dict[str, Any]:
        """Get device information"""
        return {
            "type": "tuya",
            "ip": self.ip,
            "device_id": self.device_id,
            "model": "Tuya Smart Device",
        }

    @retry_with_backoff(max_attempts=3)
    def get_status(self) -> Dict[str, Any]:
        """Get device status"""
        try:
            timestamp = str(int(time.time() * 1000))
            payload = ""
            signature = self._generate_signature(payload, timestamp)

            headers = {
                "client_id": self.api_key,
                "sign": signature,
                "t": timestamp,
                "sign_method": "HMAC-SHA256"
            }

            response = requests.get(
                f"{self.base_url}/v1.0/devices/{self.device_id}/status",
                headers=headers,
                timeout=self.timeout
            )

            if response.status_code == 200:
                data = response.json()
                return data.get("result", {})
        except Exception:
            pass

        return {"online": False}

    def control(self, commands: Dict[str, Any]) -> bool:
        """Send control commands to device"""
        try:
            timestamp = str(int(time.time() * 1000))
            payload = ""
            signature = self._generate_signature(payload, timestamp)

            headers = {
                "client_id": self.api_key,
                "sign": signature,
                "t": timestamp,
                "sign_method": "HMAC-SHA256"
            }

            response = requests.post(
                f"{self.base_url}/v1.0/devices/{self.device_id}/commands",
                headers=headers,
                json={"commands": [{"code": k, "value": v} for k, v in commands.items()]},
                timeout=self.timeout
            )

            return response.status_code == 200 and response.json().get("success", False)
        except Exception:
            return False

    def get_capabilities(self) -> List[DeviceCapability]:
        return [
            DeviceCapability.STATUS,
            DeviceCapability.CONTROL,
            DeviceCapability.CONFIG,
        ]
