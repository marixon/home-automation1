import pytest
from unittest.mock import patch, MagicMock
from homeauto.devices.camera import CameraDevice


@patch('homeauto.devices.camera.requests')
def test_camera_test_connection(mock_requests):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_requests.get.return_value = mock_response

    camera = CameraDevice(
        ip="192.168.1.100",
        credentials={"username": "admin", "password": "pass"}
    )

    assert camera.test_connection() is True


@patch('homeauto.devices.camera.requests')
def test_camera_get_info(mock_requests):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"model": "IP Camera X1", "firmware": "1.0.0"}
    mock_requests.get.return_value = mock_response

    camera = CameraDevice(
        ip="192.168.1.100",
        credentials={"username": "admin", "password": "pass"}
    )

    info = camera.get_info()
    assert "type" in info
    assert info["type"] == "camera"


@patch('homeauto.devices.camera.requests')
def test_camera_get_status(mock_requests):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_requests.get.return_value = mock_response

    camera = CameraDevice(
        ip="192.168.1.100",
        credentials={"username": "admin", "password": "pass"}
    )

    status = camera.get_status()
    assert "online" in status
