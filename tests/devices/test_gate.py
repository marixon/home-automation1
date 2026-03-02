import pytest
from unittest.mock import patch, MagicMock
from homeauto.devices.gate import HikGateDevice
from homeauto.devices.base import DeviceCapability


@patch("homeauto.devices.gate.requests.Session")
def test_gate_test_connection(mock_session_class):
    """Test gate connection testing"""
    mock_session = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_session.get.return_value = mock_response
    mock_session_class.return_value = mock_session

    gate = HikGateDevice(
        ip="192.168.1.100", credentials={"username": "admin", "password": "pass123"}
    )

    assert gate.test_connection() is True
    mock_session.get.assert_called_once()


@patch("homeauto.devices.gate.requests.Session")
def test_gate_get_info(mock_session_class):
    """Test getting gate information"""
    mock_session = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = """<?xml version="1.0" encoding="UTF-8"?>
<DeviceInfo>
    <deviceName>Hik-Gate-Controller</deviceName>
    <serialNumber>ABCD123456</serialNumber>
    <firmwareVersion>V5.5.0</firmwareVersion>
</DeviceInfo>"""
    mock_session.get.return_value = mock_response
    mock_session_class.return_value = mock_session

    gate = HikGateDevice(
        ip="192.168.1.100", credentials={"username": "admin", "password": "pass123"}
    )

    info = gate.get_info()
    assert info["type"] == "gate"
    assert info["ip"] == "192.168.1.100"
    assert info["model"] == "Hik-Gate-Controller"
    assert info["serial_number"] == "ABCD123456"
    assert info["firmware_version"] == "V5.5.0"


@patch("homeauto.devices.gate.requests.Session")
def test_gate_get_status(mock_session_class):
    """Test getting gate status"""
    mock_session = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = """<?xml version="1.0" encoding="UTF-8"?>
<DoorStatus>
    <doorState>closed</doorState>
    <lockState>locked</lockState>
    <lastOpenTime>2024-01-15T08:30:00</lastOpenTime>
    <lastCloseTime>2024-01-15T08:31:00</lastCloseTime>
    <errorCode>0</errorCode>
</DoorStatus>"""
    mock_session.get.return_value = mock_response
    mock_session_class.return_value = mock_session

    gate = HikGateDevice(
        ip="192.168.1.100", credentials={"username": "admin", "password": "pass123"}
    )

    status = gate.get_status()
    assert status["online"] is True
    assert status["state"] == "closed"
    assert status["locked"] is True
    assert status["last_open_time"] == "2024-01-15T08:30:00"
    assert status["error_code"] == 0


@patch("homeauto.devices.gate.requests.Session")
def test_gate_open(mock_session_class):
    """Test opening the gate"""
    mock_session = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <statusString>Operation successful</statusString>
</Response>"""
    mock_session.put.return_value = mock_response
    mock_session_class.return_value = mock_session

    gate = HikGateDevice(
        ip="192.168.1.100", credentials={"username": "admin", "password": "pass123"}
    )

    result = gate.open_gate()
    assert result["success"] is True
    assert "Operation successful" in result["message"]
    mock_session.put.assert_called_once()


@patch("homeauto.devices.gate.requests.Session")
def test_gate_close(mock_session_class):
    """Test closing the gate"""
    mock_session = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <statusString>Operation successful</statusString>
</Response>"""
    mock_session.put.return_value = mock_response
    mock_session_class.return_value = mock_session

    gate = HikGateDevice(
        ip="192.168.1.100", credentials={"username": "admin", "password": "pass123"}
    )

    result = gate.close_gate()
    assert result["success"] is True
    assert "Operation successful" in result["message"]
    mock_session.put.assert_called_once()


@patch("homeauto.devices.gate.requests.Session")
def test_gate_toggle(mock_session_class):
    """Test toggling gate state"""
    mock_session = MagicMock()

    # Mock status response (gate is closed)
    mock_status_response = MagicMock()
    mock_status_response.status_code = 200
    mock_status_response.text = """<?xml version="1.0" encoding="UTF-8"?>
<DoorStatus>
    <doorState>closed</doorState>
    <lockState>locked</lockState>
</DoorStatus>"""

    # Mock open response
    mock_open_response = MagicMock()
    mock_open_response.status_code = 200
    mock_open_response.text = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <statusString>Gate opened</statusString>
</Response>"""

    mock_session.get.return_value = mock_status_response
    mock_session.put.return_value = mock_open_response
    mock_session_class.return_value = mock_session

    gate = HikGateDevice(
        ip="192.168.1.100", credentials={"username": "admin", "password": "pass123"}
    )

    result = gate.toggle_gate()
    assert result["success"] is True
    assert "Gate opened" in result["message"]


def test_gate_capabilities():
    """Test gate capabilities"""
    gate = HikGateDevice(
        ip="192.168.1.100", credentials={"username": "admin", "password": "pass123"}
    )

    capabilities = gate.get_capabilities()
    assert DeviceCapability.STATUS in capabilities
    assert DeviceCapability.CONTROL in capabilities
    assert DeviceCapability.CONFIG in capabilities


@patch("homeauto.devices.gate.requests.Session")
def test_gate_get_config(mock_session_class):
    """Test getting gate configuration"""
    mock_session = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = """<?xml version="1.0" encoding="UTF-8"?>
<DoorParam>
    <doorName>Main Gate</doorName>
    <openDuration>45</openDuration>
    <autoClose>true</autoClose>
    <alarmEnabled>false</alarmEnabled>
</DoorParam>"""
    mock_session.get.return_value = mock_response
    mock_session_class.return_value = mock_session

    gate = HikGateDevice(
        ip="192.168.1.100", credentials={"username": "admin", "password": "pass123"}
    )

    config = gate.get_config()
    assert config["door_name"] == "Main Gate"
    assert config["open_duration"] == 45
    assert config["auto_close"] is True
    assert config["alarm_enabled"] is False


@patch("homeauto.devices.gate.requests.Session")
def test_gate_connection_failure(mock_session_class):
    """Test gate connection failure"""
    mock_session = MagicMock()
    # Simulate connection failure by returning None
    mock_session.get.return_value = None
    mock_session_class.return_value = mock_session

    gate = HikGateDevice(
        ip="192.168.1.100", credentials={"username": "admin", "password": "pass123"}
    )

    assert gate.test_connection() is False


@patch("homeauto.devices.gate.requests.Session")
def test_gate_open_failure(mock_session_class):
    """Test gate open failure"""
    mock_session = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_session.put.return_value = mock_response
    mock_session_class.return_value = mock_session

    gate = HikGateDevice(
        ip="192.168.1.100", credentials={"username": "admin", "password": "pass123"}
    )

    result = gate.open_gate()
    assert result["success"] is False
    assert "HTTP Error: 500" in result["message"]
    assert result["error_code"] == 500
