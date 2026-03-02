import pytest
from homeauto.discovery.mock import MockDeviceGenerator, MockDevice


def test_generate_mock_devices():
    generator = MockDeviceGenerator()
    devices = generator.generate(count=5)

    assert len(devices) == 5
    assert all(isinstance(d, MockDevice) for d in devices)


def test_mock_device_types():
    generator = MockDeviceGenerator()
    devices = generator.generate(count=10)

    types = [d.device_type for d in devices]
    # Should have variety of device types
    assert "camera" in types or "sensor" in types or "gate" in types


def test_mock_device_response():
    device = MockDevice(
        device_type="camera", ip="192.168.1.100", mac="AA:BB:CC:DD:EE:FF"
    )

    # is_online() returns random bool (90% True), so just check it's callable
    assert isinstance(device.is_online(), bool)
    assert device.get_info()["type"] == "camera"
    assert device.get_info()["ip"] == "192.168.1.100"
