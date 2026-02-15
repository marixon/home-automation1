import pytest
from unittest.mock import patch, MagicMock
from homeauto.discovery.identifier import DeviceIdentifier


def test_identify_by_ports():
    identifier = DeviceIdentifier()

    # Camera on RTSP port
    device_type = identifier.identify_by_ports([554, 80])
    assert device_type == "camera"

    # Unknown device
    device_type = identifier.identify_by_ports([3000])
    assert device_type == "unknown"


def test_identify_by_manufacturer():
    identifier = DeviceIdentifier()

    device_type = identifier.identify_by_manufacturer("Tuya")
    assert device_type in ["sensor", "switch"]

    device_type = identifier.identify_by_manufacturer("Hikvision")
    assert device_type == "camera"


def test_calculate_confidence():
    identifier = DeviceIdentifier()

    signals = {
        "port_match": True,
        "manufacturer_match": True,
        "api_probe": True,
    }

    confidence = identifier.calculate_confidence(signals)
    assert confidence > 0.7
