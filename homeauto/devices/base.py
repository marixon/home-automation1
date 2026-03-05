from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, List, Any
from homeauto.utils.retry import retry_with_backoff


class DeviceCapability(Enum):
    STATUS = "status"
    CONTROL = "control"
    CONFIG = "config"
    STREAM = "stream"
    DISCOVERY = "discovery"


class BaseDevice(ABC):
    """Base class for all device adapters"""

    def __init__(self, ip: str, credentials: Dict[str, str]):
        self.ip = ip
        self.credentials = credentials

    @abstractmethod
    def get_info(self) -> Dict[str, Any]:
        """Get basic device information"""
        pass

    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """Get current device status"""
        pass

    @abstractmethod
    def test_connection(self) -> bool:
        """Test if device is reachable"""
        pass

    def get_config(self) -> Dict[str, Any]:
        """Get device configuration (optional)"""
        return {}

    def update_config(self, config: Dict[str, Any]) -> bool:
        """Update device configuration (optional)"""
        return False

    def get_capabilities(self) -> List[DeviceCapability]:
        """Return list of supported capabilities"""
        return [DeviceCapability.STATUS, DeviceCapability.CONFIG]
