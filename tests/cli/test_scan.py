import pytest
from unittest.mock import patch, MagicMock
from homeauto.cli.scan import ScanCommand, format_device_table


def test_format_device_table():
    devices = [
        {
            "id": "cam-001",
            "type": "camera",
            "ip": "192.168.1.100",
            "name": "Front Camera",
            "status": "online",
        },
        {
            "id": "sensor-001",
            "type": "sensor",
            "ip": "192.168.1.101",
            "name": "Living Room Sensor",
            "status": "online",
        },
    ]

    table = format_device_table(devices)
    assert "cam-001" in table
    assert "192.168.1.100" in table
    assert "Front Camera" in table


@patch('homeauto.cli.scan.NetworkScanner')
@patch('homeauto.cli.scan.DeviceIdentifier')
@patch('homeauto.cli.scan.DeviceRepository')
def test_scan_command(mock_repo, mock_identifier, mock_scanner):
    # Mock scanner to return active hosts
    mock_scanner_instance = MagicMock()
    mock_scanner_instance.scan_subnet.return_value = ["192.168.1.100"]
    mock_scanner_instance.scan_ports.return_value = [554, 80]
    mock_scanner_instance.get_mac_address.return_value = "AA:BB:CC:DD:EE:FF"
    mock_scanner.return_value = mock_scanner_instance

    # Mock identifier
    mock_identifier_instance = MagicMock()
    mock_identifier_instance.identify.return_value = ("camera", 0.8)
    mock_identifier.return_value = mock_identifier_instance

    # Mock repository
    mock_repo_instance = MagicMock()
    mock_repo.return_value = mock_repo_instance

    cmd = ScanCommand()
    result = cmd.execute()

    assert result["discovered"] == 1
    assert mock_repo_instance.save.called
