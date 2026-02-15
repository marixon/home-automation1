import pytest
from datetime import datetime
from homeauto.database.models import Device, DeviceStatus


def test_device_creation():
    device = Device(
        id="test-001",
        device_type="camera",
        ip_address="192.168.1.100",
        mac_address="AA:BB:CC:DD:EE:FF",
        name="Test Camera",
        status=DeviceStatus.ONLINE,
    )
    assert device.id == "test-001"
    assert device.device_type == "camera"
    assert device.status == DeviceStatus.ONLINE


def test_device_status_enum():
    assert DeviceStatus.ONLINE.value == "online"
    assert DeviceStatus.OFFLINE.value == "offline"
    assert DeviceStatus.UNKNOWN.value == "unknown"
    assert DeviceStatus.ERROR.value == "error"
