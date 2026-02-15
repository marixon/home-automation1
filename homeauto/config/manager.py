import yaml
from typing import Any, Dict, Optional
from pathlib import Path


class ConfigManager:
    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = Path(config_path)
        self.config = self._load_config()

    def _load_config(self) -> Dict:
        if not self.config_path.exists():
            return {}

        with open(self.config_path, 'r') as f:
            return yaml.safe_load(f) or {}

    def get(self, key: str, default: Any = None) -> Any:
        """Get config value using dot notation (e.g., 'credentials.hikconnect.username')"""
        keys = key.split('.')
        value = self.config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    def get_credentials(self, device_type: str) -> Dict:
        """Get credentials for a specific device type"""
        return self.get(f"credentials.{device_type}", {})

    def get_setting(self, key: str, default: Any = None) -> Any:
        """Get setting value"""
        return self.get(f"settings.{key}", default)

    def save(self, config: Dict):
        """Save configuration to file"""
        with open(self.config_path, 'w') as f:
            yaml.dump(config, f, default_flow_style=False)
