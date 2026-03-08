from homeauto.config.manager import ConfigManager


def test_get_credentials_gate_alias_hikconnect(tmp_path):
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        """
credentials:
  hikconnect:
    username: admin
    password: secret
""".strip()
    )

    manager = ConfigManager(str(config_file))
    creds = manager.get_credentials("gate")

    assert creds["username"] == "admin"
    assert creds["password"] == "secret"
