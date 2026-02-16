import pytest
from unittest.mock import patch, MagicMock
from homeauto.devices.gate import HikGateDevice


@patch('homeauto.devices.gate.requests')
def test_gate_test_connection(mock_requests):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_requests.get.return_value = mock_response

    gate = HikGateDevice(
        ip="192.168.1.100",
        credentials={"username": "admin", "password": "pass"}
    )

    assert gate.test_connection() is True


@patch('homeauto.devices.gate.requests')
def test_gate_get_status(mock_requests):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = '<GateStatus><state>closed</state><lock>locked</lock></GateStatus>'
    mock_requests.get.return_value = mock_response

    gate = HikGateDevice(
        ip="192.168.1.100",
        credentials={"username": "admin", "password": "pass"}
    )

    status = gate.get_status()
    assert "state" in status


@patch('homeauto.devices.gate.requests')
def test_gate_open(mock_requests):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_requests.put.return_value = mock_response

    gate = HikGateDevice(
        ip="192.168.1.100",
        credentials={"username": "admin", "password": "pass"}
    )

    result = gate.open_gate()
    assert result is True


@patch('homeauto.devices.gate.requests')
def test_gate_close(mock_requests):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_requests.put.return_value = mock_response

    gate = HikGateDevice(
        ip="192.168.1.100",
        credentials={"username": "admin", "password": "pass"}
    )

    result = gate.close_gate()
    assert result is True
