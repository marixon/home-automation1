import pytest
from unittest.mock import patch, MagicMock
from homeauto.cli.config import ConfigCommand


@patch('homeauto.cli.config.DeviceRepository')
@patch('homeauto.cli.config.ConfigManager')
def test_list_devices(mock_config, mock_repo):
    # Mock repository with devices
    mock_repo_instance = MagicMock()
    mock_device = MagicMock()
    mock_device.id = "cam-001"
    mock_device.device_type = "camera"
    mock_device.name = "Front Camera"
    mock_device.ip_address = "192.168.1.100"
    mock_repo_instance.get_all.return_value = [mock_device]
    mock_repo.return_value = mock_repo_instance

    cmd = ConfigCommand()
    result = cmd.list_devices()

    assert result["count"] == 1


@patch('homeauto.cli.config.ConfigManager')
def test_set_credentials(mock_config):
    mock_config_instance = MagicMock()
    mock_config_instance.config = {}
    mock_config.return_value = mock_config_instance

    cmd = ConfigCommand()
    result = cmd.set_credentials("camera", "admin", "password123")

    assert result is True
    assert mock_config_instance.save.called


@patch('homeauto.cli.config.ConfigManager')
def test_get_credentials(mock_config):
    mock_config_instance = MagicMock()
    mock_config_instance.get_credentials.return_value = {
        "username": "admin",
        "password": "test"
    }
    mock_config.return_value = mock_config_instance

    cmd = ConfigCommand()
    creds = cmd.get_credentials("camera")

    assert creds["username"] == "admin"
