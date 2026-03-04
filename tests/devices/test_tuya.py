import pytest
from unittest.mock import patch, MagicMock
from homeauto.devices.tuya import TuyaDevice


@patch("homeauto.devices.tuya.requests")
def test_tuya_test_connection(mock_requests):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"success": True}
    mock_requests.post.return_value = mock_response

    device = TuyaDevice(
        ip="192.168.1.100",
        credentials={
            "api_key": "test_key",
            "secret": "test_secret",
            "device_id": "12345",
        },
    )

    assert device.test_connection() is True


@patch("homeauto.devices.tuya.requests")
def test_tuya_get_status(mock_requests):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "result": {"online": True, "state": "on", "temperature": 22.5, "humidity": 45}
    }
    mock_requests.get.return_value = mock_response

    device = TuyaDevice(
        ip="192.168.1.100",
        credentials={
            "api_key": "test_key",
            "secret": "test_secret",
            "device_id": "12345",
        },
    )

    status = device.get_status()
    assert status["online"] is True
    assert "state" in status


@patch("homeauto.devices.tuya.requests")
def test_tuya_control(mock_requests):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"success": True}
    mock_requests.post.return_value = mock_response

    device = TuyaDevice(
        ip="192.168.1.100",
        credentials={
            "api_key": "test_key",
            "secret": "test_secret",
            "device_id": "12345",
        },
    )

    result = device.control({"switch": True})
    assert result is True
