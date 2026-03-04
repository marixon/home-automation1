import pytest
from homeauto.devices.base import BaseDevice, DeviceCapability


def test_device_capability_enum():
    assert DeviceCapability.STATUS in [c for c in DeviceCapability]
    assert DeviceCapability.CONTROL in [c for c in DeviceCapability]


def test_base_device_interface():
    # BaseDevice is abstract, so we test that subclasses must implement methods
    class TestDevice(BaseDevice):
        pass

    with pytest.raises(TypeError):
        # Should fail because abstract methods not implemented
        device = TestDevice(ip="192.168.1.100", credentials={})
