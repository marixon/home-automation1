import pytest
from pathlib import Path
from homeauto.config.manager import ConfigManager


@pytest.fixture
def config_file(tmp_path):
    config_path = tmp_path / "config.yaml"
    config_content = """
credentials:
  hikconnect:
    username: testuser
    password: testpass
  tuya:
    api_key: test_key
    secret: test_secret
settings:
  scan_interval: 300
  retry_attempts: 3
  timeout: 10
"""
    config_path.write_text(config_content)
    return str(config_path)


def test_load_config(config_file):
    config = ConfigManager(config_file)
    assert config.get("credentials.hikconnect.username") == "testuser"
    assert config.get("settings.scan_interval") == 300


def test_get_credentials(config_file):
    config = ConfigManager(config_file)
    hik_creds = config.get_credentials("hikconnect")
    assert hik_creds["username"] == "testuser"
    assert hik_creds["password"] == "testpass"


def test_get_setting(config_file):
    config = ConfigManager(config_file)
    assert config.get_setting("scan_interval") == 300
    assert config.get_setting("retry_attempts") == 3


def test_default_value(config_file):
    config = ConfigManager(config_file)
    assert config.get("nonexistent.key", "default") == "default"
