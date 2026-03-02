import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from homeauto.web.api import app, repo, config
from homeauto.devices.gate import HikGateDevice
from homeauto.database.models import Device, DeviceStatus

client = TestClient(app)


@patch.object(repo, "get_all")
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


@patch.object(repo, "get")
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
    # Mock os.path.exists to return False so it uses the fallback HTML
    with patch("os.path.exists", return_value=False):
        response = client.get("/")
        assert response.status_code == 200


@patch.object(repo, "get")
@patch("homeauto.web.api.get_device_adapter")
def test_get_device_status(mock_get_adapter, mock_get):
    """Test getting device status"""
    # Create a mock device
    mock_device = MagicMock(spec=Device)
    mock_device.id = "gate-001"
    mock_device.device_type = "gate"
    mock_device.ip_address = "192.168.1.100"
    mock_get.return_value = mock_device

    # Create a mock adapter
    mock_adapter = MagicMock()
    mock_adapter.test_connection.return_value = True
    mock_adapter.get_status.return_value = {"state": "closed", "locked": True}
    mock_adapter.get_info.return_value = {"model": "Hik-Gate-Controller"}
    mock_get_adapter.return_value = mock_adapter

    response = client.get("/api/devices/gate-001/status")
    assert response.status_code == 200
    data = response.json()
    assert data["device_id"] == "gate-001"
    assert "status" in data


@patch.object(repo, "get")
def test_get_device_status_not_found(mock_get):
    """Test getting status for non-existent device"""
    mock_get.return_value = None

    response = client.get("/api/devices/nonexistent/status")
    assert response.status_code == 404


@patch.object(repo, "get")
@patch("homeauto.web.api.get_device_adapter")
def test_open_gate(mock_get_adapter, mock_get):
    """Test opening a gate"""
    # Create a mock device
    mock_device = MagicMock(spec=Device)
    mock_device.id = "gate-001"
    mock_device.device_type = "gate"
    mock_device.name = "Main Gate"
    mock_get.return_value = mock_device

    # Create a mock adapter that simulates HikGateDevice
    mock_adapter = MagicMock(spec=HikGateDevice)
    mock_adapter.open_gate.return_value = {
        "success": True,
        "message": "Gate opened successfully",
    }
    mock_get_adapter.return_value = mock_adapter

    response = client.post("/api/gates/gate-001/open")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "Gate opened" in data["message"]
    assert data["command"] == "open"


@patch.object(repo, "get")
@patch("homeauto.web.api.get_device_adapter")
def test_close_gate(mock_get_adapter, mock_get):
    """Test closing a gate"""
    # Create a mock device
    mock_device = MagicMock(spec=Device)
    mock_device.id = "gate-001"
    mock_device.device_type = "gate"
    mock_device.name = "Main Gate"
    mock_get.return_value = mock_device

    # Create a mock adapter that simulates HikGateDevice
    mock_adapter = MagicMock(spec=HikGateDevice)
    mock_adapter.close_gate.return_value = {
        "success": True,
        "message": "Gate closed successfully",
    }
    mock_get_adapter.return_value = mock_adapter

    response = client.post("/api/gates/gate-001/close")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "Gate closed" in data["message"]
    assert data["command"] == "close"


@patch.object(repo, "get")
def test_open_gate_not_found(mock_get):
    """Test opening non-existent gate"""
    mock_get.return_value = None

    response = client.post("/api/gates/nonexistent/open")
    assert response.status_code == 404


@patch.object(repo, "get")
def test_open_gate_wrong_type(mock_get):
    """Test opening a device that's not a gate"""
    mock_device = MagicMock(spec=Device)
    mock_device.id = "cam-001"
    mock_device.device_type = "camera"
    mock_get.return_value = mock_device

    response = client.post("/api/gates/cam-001/open")
    assert response.status_code == 400
    assert "not a gate" in response.json()["detail"].lower()


@patch.object(repo, "get")
@patch("homeauto.web.api.get_device_adapter")
def test_get_gate_status(mock_get_adapter, mock_get):
    """Test getting detailed gate status"""
    # Create a mock device
    mock_device = MagicMock(spec=Device)
    mock_device.id = "gate-001"
    mock_device.device_type = "gate"
    mock_get.return_value = mock_device

    # Create a mock adapter that simulates HikGateDevice
    mock_adapter = MagicMock(spec=HikGateDevice)
    mock_adapter.test_connection.return_value = True
    mock_adapter.get_status.return_value = {"state": "closed", "locked": True}
    mock_adapter.get_info.return_value = {"model": "Hik-Gate-Controller"}
    mock_adapter.get_config.return_value = {"door_name": "Main Gate"}
    mock_adapter.get_capabilities.return_value = []
    mock_get_adapter.return_value = mock_adapter

    response = client.get("/api/gates/gate-001/status")
    assert response.status_code == 200
    data = response.json()
    assert data["device_id"] == "gate-001"
    assert "status" in data
