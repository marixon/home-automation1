import requests
import xml.etree.ElementTree as ET
from typing import Dict, Any, List, Optional
from homeauto.devices.base import BaseDevice, DeviceCapability
from homeauto.utils.retry import retry_with_backoff


class HikGateDevice(BaseDevice):
    """Hikvision gate controller adapter with ISAPI implementation"""

    def __init__(self, ip: str, credentials: Dict[str, str]):
        super().__init__(ip, credentials)
        self.base_url = f"http://{ip}"
        self.timeout = 10
        self.session = requests.Session()
        if "username" in credentials and "password" in credentials:
            self.session.auth = (credentials["username"], credentials["password"])

    def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[str] = None,
        headers: Optional[Dict] = None,
    ) -> Optional[requests.Response]:
        """Make HTTP request to Hikvision device"""
        url = f"{self.base_url}{endpoint}"
        request_headers = {"Content-Type": "application/xml"}
        if headers:
            request_headers.update(headers)

        try:
            if method.upper() == "GET":
                response = self.session.get(
                    url, headers=request_headers, timeout=self.timeout
                )
            elif method.upper() == "PUT":
                response = self.session.put(
                    url, data=data, headers=request_headers, timeout=self.timeout
                )
            elif method.upper() == "POST":
                response = self.session.post(
                    url, data=data, headers=request_headers, timeout=self.timeout
                )
            else:
                return None

            return response
        except requests.RequestException:
            return None

    def _parse_xml_response(self, xml_string: str, xpath: str) -> Optional[str]:
        """Parse XML response and extract value using XPath"""
        try:
            root = ET.fromstring(xml_string)
            element = root.find(xpath)
            return element.text if element is not None else None
        except ET.ParseError:
            return None

    @retry_with_backoff(max_attempts=3, base_delay=1.0)
    def test_connection(self) -> bool:
        """Test gate controller connectivity using ISAPI System status"""
        response = self._make_request("GET", "/ISAPI/System/status")
        if response and response.status_code == 200:
            return True
        # Also accept 401 as valid (device reachable but auth required)
        if response and response.status_code == 401:
            return True
        return False

    @retry_with_backoff(max_attempts=3)
    def get_info(self) -> Dict[str, Any]:
        """Get detailed gate controller information"""
        response = self._make_request("GET", "/ISAPI/System/deviceInfo")
        device_info = {
            "type": "gate",
            "ip": self.ip,
            "model": "Hikvision Gate Controller",
            "manufacturer": "Hikvision",
            "serial_number": "Unknown",
            "firmware_version": "Unknown",
        }

        if response and response.status_code == 200:
            try:
                root = ET.fromstring(response.text)
                # Parse device information from XML
                model = root.find(".//deviceName")
                serial = root.find(".//serialNumber")
                firmware = root.find(".//firmwareVersion")

                if model is not None and model.text:
                    device_info["model"] = model.text
                if serial is not None and serial.text:
                    device_info["serial_number"] = serial.text
                if firmware is not None and firmware.text:
                    device_info["firmware_version"] = firmware.text
            except ET.ParseError:
                pass

        return device_info

    @retry_with_backoff(max_attempts=3)
    def get_status(self) -> Dict[str, Any]:
        """Get detailed gate status including door state and lock status"""
        # Try to get door status
        response = self._make_request("GET", "/ISAPI/AccessControl/Door/status/1")

        status_info = {
            "online": False,
            "state": "unknown",
            "locked": False,
            "last_open_time": None,
            "last_close_time": None,
            "error_code": 0,
        }

        if response and response.status_code == 200:
            status_info["online"] = True

            try:
                root = ET.fromstring(response.text)
                # Parse door status
                door_state = root.find(".//doorState")
                lock_state = root.find(".//lockState")
                last_open = root.find(".//lastOpenTime")
                last_close = root.find(".//lastCloseTime")
                error_code = root.find(".//errorCode")

                if door_state is not None and door_state.text:
                    status_info["state"] = door_state.text.lower()
                if lock_state is not None and lock_state.text:
                    status_info["locked"] = lock_state.text.lower() == "locked"
                if last_open is not None and last_open.text:
                    status_info["last_open_time"] = last_open.text
                if last_close is not None and last_close.text:
                    status_info["last_close_time"] = last_close.text
                if error_code is not None and error_code.text:
                    status_info["error_code"] = int(error_code.text)

            except (ET.ParseError, ValueError):
                pass

        # If we can't get detailed status, at least check connectivity
        elif self.test_connection():
            status_info["online"] = True
            status_info["state"] = "unknown"

        return status_info

    @retry_with_backoff(max_attempts=3)
    def open_gate(self) -> Dict[str, Any]:
        """Open the gate and return operation result"""
        xml_data = """<?xml version="1.0" encoding="UTF-8"?>
<RemoteControlDoor>
    <cmd>open</cmd>
    <doorNo>1</doorNo>
</RemoteControlDoor>"""

        response = self._make_request(
            "PUT", "/ISAPI/AccessControl/RemoteControl/door/1", data=xml_data
        )

        result = {
            "success": False,
            "message": "Failed to send command",
            "error_code": 0,
        }

        if response:
            if response.status_code == 200:
                result["success"] = True
                result["message"] = "Gate open command sent successfully"
                # Parse response for more details
                try:
                    root = ET.fromstring(response.text)
                    status = root.find(".//statusString")
                    if status is not None:
                        result["message"] = status.text
                except ET.ParseError:
                    pass
            else:
                result["message"] = f"HTTP Error: {response.status_code}"
                result["error_code"] = response.status_code

        return result

    @retry_with_backoff(max_attempts=3)
    def close_gate(self) -> Dict[str, Any]:
        """Close the gate and return operation result"""
        xml_data = """<?xml version="1.0" encoding="UTF-8"?>
<RemoteControlDoor>
    <cmd>close</cmd>
    <doorNo>1</doorNo>
</RemoteControlDoor>"""

        response = self._make_request(
            "PUT", "/ISAPI/AccessControl/RemoteControl/door/1", data=xml_data
        )

        result = {
            "success": False,
            "message": "Failed to send command",
            "error_code": 0,
        }

        if response:
            if response.status_code == 200:
                result["success"] = True
                result["message"] = "Gate close command sent successfully"
                # Parse response for more details
                try:
                    root = ET.fromstring(response.text)
                    status = root.find(".//statusString")
                    if status is not None:
                        result["message"] = status.text
                except ET.ParseError:
                    pass
            else:
                result["message"] = f"HTTP Error: {response.status_code}"
                result["error_code"] = response.status_code

        return result

    def toggle_gate(self) -> Dict[str, Any]:
        """Toggle gate state (open if closed, close if open)"""
        status = self.get_status()
        if status["state"] == "open":
            return self.close_gate()
        else:
            return self.open_gate()

    def get_capabilities(self) -> List[DeviceCapability]:
        return [
            DeviceCapability.STATUS,
            DeviceCapability.CONTROL,
            DeviceCapability.CONFIG,
        ]

    def get_config(self) -> Dict[str, Any]:
        """Get gate configuration"""
        response = self._make_request("GET", "/ISAPI/AccessControl/Door/param/1")

        config = {
            "door_name": "Gate 1",
            "open_duration": 30,  # seconds
            "auto_close": True,
            "alarm_enabled": False,
        }

        if response and response.status_code == 200:
            try:
                root = ET.fromstring(response.text)
                name = root.find(".//doorName")
                duration = root.find(".//openDuration")
                auto_close = root.find(".//autoClose")
                alarm = root.find(".//alarmEnabled")

                if name is not None and name.text:
                    config["door_name"] = name.text
                if duration is not None and duration.text:
                    config["open_duration"] = int(duration.text)
                if auto_close is not None and auto_close.text:
                    config["auto_close"] = auto_close.text.lower() == "true"
                if alarm is not None and alarm.text:
                    config["alarm_enabled"] = alarm.text.lower() == "true"

            except (ET.ParseError, ValueError):
                pass

        return config

    def update_config(self, config: Dict[str, Any]) -> bool:
        """Update gate configuration (simplified implementation)"""
        # This would require constructing proper XML for configuration update
        # For now, return False as this is a complex operation
        return False
