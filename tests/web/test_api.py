import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from homeauto.web.api import app, repo


client = TestClient(app)


@patch.object(repo, 'get_all')
def test_get_devices(mock_get_all):
    # Mock repository response
    mock_device = MagicMock()
    mock_device.id = "cam-001"
    mock_device.device_type = "camera"
    mock_device.name = "Front Camera"
    mock_device.ip_address = "192.168.1.100"
    mock_device.mac_address = "AA:BB:CC:DD:EE:FF"
    mock_device.status.value = "online"
    mock_device.manufacturer = "Test"
    mock_device.model = "Model1"
    mock_device.confidence_score = 0.9
    mock_device.last_seen.isoformat.return_value = "2026-02-16T00:00:00"
    mock_get_all.return_value = [mock_device]

    response = client.get("/api/devices")
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["id"] == "cam-001"


@patch.object(repo, 'get')
def test_get_device_by_id(mock_get):
    mock_device = MagicMock()
    mock_device.id = "cam-001"
    mock_device.device_type = "camera"
    mock_device.name = "Front Camera"
    mock_device.ip_address = "192.168.1.100"
    mock_device.mac_address = "AA:BB:CC:DD:EE:FF"
    mock_device.status.value = "online"
    mock_device.manufacturer = "Test"
    mock_device.model = "Model1"
    mock_device.confidence_score = 0.9
    mock_device.last_seen.isoformat.return_value = "2026-02-16T00:00:00"
    mock_get.return_value = mock_device

    response = client.get("/api/devices/cam-001")
    assert response.status_code == 200
    assert response.json()["id"] == "cam-001"


def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
