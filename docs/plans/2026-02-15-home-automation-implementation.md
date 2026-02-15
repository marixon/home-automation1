# Home Automation System Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a Python-based home automation system that discovers, configures, and monitors local network devices through CLI tools and a web dashboard.

**Architecture:** Layered architecture with shared core library, CLI tools for scanning/configuration, and FastAPI web app with Alpine.js frontend. Device discovery uses multi-stage approach (network scan, mDNS, port fingerprinting, MAC lookup, API probing).

**Tech Stack:** Python 3.10+, venv, FastAPI, SQLite, Alpine.js, Tailwind CSS, pytest

---

## Phase 0: Project Setup

### Task 1: Initialize Python Project Structure

**Files:**
- Create: `setup.py`
- Create: `requirements.txt`
- Create: `requirements-dev.txt`
- Create: `pytest.ini`
- Create: `homeauto/__init__.py`

**Step 1: Create virtual environment**

Run:
```bash
python -m venv venv
source venv/Scripts/activate  # On Windows Git Bash
```

Expected: Virtual environment created and activated, prompt shows (venv)

**Step 2: Create setup.py**

Create `setup.py`:
```python
from setuptools import setup, find_packages

setup(
    name="homeauto",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "fastapi>=0.100.0",
        "uvicorn>=0.23.0",
        "sqlalchemy>=2.0.0",
        "pyyaml>=6.0",
        "requests>=2.31.0",
        "python-multipart>=0.0.6",
        "websockets>=11.0",
    ],
    entry_points={
        "console_scripts": [
            "homeauto-scan=homeauto.cli.scan:main",
            "homeauto-config=homeauto.cli.config:main",
        ],
    },
)
```

**Step 3: Create requirements files**

Create `requirements.txt`:
```
fastapi>=0.100.0
uvicorn>=0.23.0
sqlalchemy>=2.0.0
pyyaml>=6.0
requests>=2.31.0
python-multipart>=0.0.6
websockets>=11.0
zeroconf>=0.120.0
scapy>=2.5.0
```

Create `requirements-dev.txt`:
```
-r requirements.txt
pytest>=7.4.0
pytest-cov>=4.1.0
pytest-asyncio>=0.21.0
black>=23.7.0
flake8>=6.1.0
mypy>=1.5.0
```

**Step 4: Create pytest configuration**

Create `pytest.ini`:
```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -v --cov=homeauto --cov-report=html --cov-report=term
```

**Step 5: Create package structure**

Run:
```bash
mkdir -p homeauto/{discovery,devices,config,database,utils,cli,web}
touch homeauto/__init__.py
touch homeauto/discovery/__init__.py
touch homeauto/devices/__init__.py
touch homeauto/config/__init__.py
touch homeauto/database/__init__.py
touch homeauto/utils/__init__.py
touch homeauto/cli/__init__.py
touch homeauto/web/__init__.py
mkdir -p tests/{discovery,devices,config,database,utils,cli,web}
touch tests/__init__.py
```

Expected: Package structure created

**Step 6: Install dependencies**

Run:
```bash
pip install -r requirements-dev.txt
pip install -e .
```

Expected: All dependencies installed, homeauto package installed in editable mode

**Step 7: Commit**

Run:
```bash
git add setup.py requirements.txt requirements-dev.txt pytest.ini homeauto/ tests/
git commit -m "feat: initialize project structure and dependencies"
```

---

## Phase 1: Core Library - Database Layer

### Task 2: Database Models and Repository

**Files:**
- Create: `homeauto/database/models.py`
- Create: `tests/database/test_models.py`
- Create: `homeauto/database/repository.py`
- Create: `tests/database/test_repository.py`

**Step 1: Write database model test**

Create `tests/database/test_models.py`:
```python
import pytest
from datetime import datetime
from homeauto.database.models import Device, DeviceStatus


def test_device_creation():
    device = Device(
        id="test-001",
        device_type="camera",
        ip_address="192.168.1.100",
        mac_address="AA:BB:CC:DD:EE:FF",
        name="Test Camera",
        status=DeviceStatus.ONLINE,
    )
    assert device.id == "test-001"
    assert device.device_type == "camera"
    assert device.status == DeviceStatus.ONLINE


def test_device_status_enum():
    assert DeviceStatus.ONLINE.value == "online"
    assert DeviceStatus.OFFLINE.value == "offline"
    assert DeviceStatus.UNKNOWN.value == "unknown"
    assert DeviceStatus.ERROR.value == "error"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/database/test_models.py -v`

Expected: FAIL with "ModuleNotFoundError: No module named 'homeauto.database.models'"

**Step 3: Implement database models**

Create `homeauto/database/models.py`:
```python
from datetime import datetime
from enum import Enum
from typing import Optional
from dataclasses import dataclass, field


class DeviceStatus(Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    UNKNOWN = "unknown"
    ERROR = "error"


@dataclass
class Device:
    id: str
    device_type: str
    ip_address: str
    mac_address: str
    name: str
    status: DeviceStatus
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    confidence_score: float = 0.0
    last_seen: datetime = field(default_factory=datetime.now)
    config: dict = field(default_factory=dict)
    metadata: dict = field(default_factory=dict)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/database/test_models.py -v`

Expected: PASS (2 tests)

**Step 5: Write repository test**

Create `tests/database/test_repository.py`:
```python
import pytest
from pathlib import Path
from homeauto.database.repository import DeviceRepository
from homeauto.database.models import Device, DeviceStatus


@pytest.fixture
def repo(tmp_path):
    db_path = tmp_path / "test.db"
    return DeviceRepository(str(db_path))


def test_save_and_get_device(repo):
    device = Device(
        id="cam-001",
        device_type="camera",
        ip_address="192.168.1.100",
        mac_address="AA:BB:CC:DD:EE:FF",
        name="Front Door Camera",
        status=DeviceStatus.ONLINE,
    )

    repo.save(device)
    retrieved = repo.get("cam-001")

    assert retrieved is not None
    assert retrieved.id == "cam-001"
    assert retrieved.name == "Front Door Camera"


def test_get_all_devices(repo):
    device1 = Device(
        id="cam-001", device_type="camera", ip_address="192.168.1.100",
        mac_address="AA:BB:CC:DD:EE:FF", name="Camera 1", status=DeviceStatus.ONLINE
    )
    device2 = Device(
        id="sensor-001", device_type="sensor", ip_address="192.168.1.101",
        mac_address="11:22:33:44:55:66", name="Sensor 1", status=DeviceStatus.ONLINE
    )

    repo.save(device1)
    repo.save(device2)

    devices = repo.get_all()
    assert len(devices) == 2


def test_get_by_type(repo):
    camera = Device(
        id="cam-001", device_type="camera", ip_address="192.168.1.100",
        mac_address="AA:BB:CC:DD:EE:FF", name="Camera 1", status=DeviceStatus.ONLINE
    )
    sensor = Device(
        id="sensor-001", device_type="sensor", ip_address="192.168.1.101",
        mac_address="11:22:33:44:55:66", name="Sensor 1", status=DeviceStatus.ONLINE
    )

    repo.save(camera)
    repo.save(sensor)

    cameras = repo.get_by_type("camera")
    assert len(cameras) == 1
    assert cameras[0].device_type == "camera"
```

**Step 6: Run test to verify it fails**

Run: `pytest tests/database/test_repository.py -v`

Expected: FAIL with "ModuleNotFoundError: No module named 'homeauto.database.repository'"

**Step 7: Implement repository**

Create `homeauto/database/repository.py`:
```python
import sqlite3
import json
from typing import Optional, List
from datetime import datetime
from homeauto.database.models import Device, DeviceStatus


class DeviceRepository:
    def __init__(self, db_path: str = "homeauto.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS devices (
                    id TEXT PRIMARY KEY,
                    device_type TEXT NOT NULL,
                    ip_address TEXT NOT NULL,
                    mac_address TEXT NOT NULL,
                    name TEXT NOT NULL,
                    status TEXT NOT NULL,
                    manufacturer TEXT,
                    model TEXT,
                    confidence_score REAL,
                    last_seen TEXT,
                    config TEXT,
                    metadata TEXT
                )
            """)
            conn.commit()

    def save(self, device: Device):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO devices
                (id, device_type, ip_address, mac_address, name, status,
                 manufacturer, model, confidence_score, last_seen, config, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                device.id,
                device.device_type,
                device.ip_address,
                device.mac_address,
                device.name,
                device.status.value,
                device.manufacturer,
                device.model,
                device.confidence_score,
                device.last_seen.isoformat(),
                json.dumps(device.config),
                json.dumps(device.metadata),
            ))
            conn.commit()

    def get(self, device_id: str) -> Optional[Device]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM devices WHERE id = ?", (device_id,))
            row = cursor.fetchone()
            if row:
                return self._row_to_device(row)
            return None

    def get_all(self) -> List[Device]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM devices ORDER BY last_seen DESC")
            return [self._row_to_device(row) for row in cursor.fetchall()]

    def get_by_type(self, device_type: str) -> List[Device]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM devices WHERE device_type = ? ORDER BY last_seen DESC",
                (device_type,)
            )
            return [self._row_to_device(row) for row in cursor.fetchall()]

    def _row_to_device(self, row) -> Device:
        return Device(
            id=row["id"],
            device_type=row["device_type"],
            ip_address=row["ip_address"],
            mac_address=row["mac_address"],
            name=row["name"],
            status=DeviceStatus(row["status"]),
            manufacturer=row["manufacturer"],
            model=row["model"],
            confidence_score=row["confidence_score"],
            last_seen=datetime.fromisoformat(row["last_seen"]),
            config=json.loads(row["config"]),
            metadata=json.loads(row["metadata"]),
        )
```

**Step 8: Run test to verify it passes**

Run: `pytest tests/database/test_repository.py -v`

Expected: PASS (3 tests)

**Step 9: Commit**

Run:
```bash
git add homeauto/database/ tests/database/
git commit -m "feat: implement database models and repository"
```

---

## Phase 1: Core Library - Configuration Management

### Task 3: Configuration Manager

**Files:**
- Create: `homeauto/config/manager.py`
- Create: `tests/config/test_manager.py`
- Create: `config.example.yaml`

**Step 1: Write configuration test**

Create `tests/config/test_manager.py`:
```python
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
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/config/test_manager.py -v`

Expected: FAIL with "ModuleNotFoundError: No module named 'homeauto.config.manager'"

**Step 3: Implement configuration manager**

Create `homeauto/config/manager.py`:
```python
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
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/config/test_manager.py -v`

Expected: PASS (4 tests)

**Step 5: Create example config file**

Create `config.example.yaml`:
```yaml
# Home Automation Configuration Example
# Copy this to config.yaml and fill in your credentials

credentials:
  hikconnect:
    username: your_username
    password: your_password
  tuya:
    api_key: your_api_key
    secret: your_secret
  camera:
    username: admin
    password: camera_password

settings:
  # Network scanning interval in seconds
  scan_interval: 300

  # Number of retry attempts for failed connections
  retry_attempts: 3

  # Connection timeout in seconds
  timeout: 10

  # Network subnet to scan (e.g., 192.168.1.0/24)
  subnet: 192.168.1.0/24

testing:
  # Use mock devices for testing
  use_mock_devices: false

  # Number of mock devices to generate
  mock_device_count: 5
```

**Step 6: Commit**

Run:
```bash
git add homeauto/config/ tests/config/ config.example.yaml
git commit -m "feat: implement configuration manager"
```

---

## Phase 1: Core Library - Utilities

### Task 4: Retry Logic and Network Utilities

**Files:**
- Create: `homeauto/utils/retry.py`
- Create: `tests/utils/test_retry.py`
- Create: `homeauto/utils/network.py`
- Create: `tests/utils/test_network.py`

**Step 1: Write retry logic test**

Create `tests/utils/test_retry.py`:
```python
import pytest
import time
from homeauto.utils.retry import retry_with_backoff


def test_retry_succeeds_first_try():
    call_count = 0

    @retry_with_backoff(max_attempts=3, base_delay=0.1)
    def succeeds_immediately():
        nonlocal call_count
        call_count += 1
        return "success"

    result = succeeds_immediately()
    assert result == "success"
    assert call_count == 1


def test_retry_succeeds_after_failures():
    call_count = 0

    @retry_with_backoff(max_attempts=3, base_delay=0.1)
    def succeeds_on_third_try():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise ConnectionError("Failed")
        return "success"

    result = succeeds_on_third_try()
    assert result == "success"
    assert call_count == 3


def test_retry_exhausts_attempts():
    call_count = 0

    @retry_with_backoff(max_attempts=3, base_delay=0.1)
    def always_fails():
        nonlocal call_count
        call_count += 1
        raise ConnectionError("Always fails")

    with pytest.raises(ConnectionError):
        always_fails()

    assert call_count == 3
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/utils/test_retry.py -v`

Expected: FAIL with "ModuleNotFoundError"

**Step 3: Implement retry logic**

Create `homeauto/utils/retry.py`:
```python
import time
import functools
from typing import Callable, Type, Tuple


def retry_with_backoff(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    backoff_factor: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,)
):
    """
    Decorator for retrying a function with exponential backoff.

    Args:
        max_attempts: Maximum number of retry attempts
        base_delay: Initial delay between retries in seconds
        backoff_factor: Multiplier for delay after each retry
        exceptions: Tuple of exception types to catch and retry
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            delay = base_delay
            last_exception = None

            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        time.sleep(delay)
                        delay *= backoff_factor

            # All attempts exhausted, raise the last exception
            raise last_exception

        return wrapper
    return decorator
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/utils/test_retry.py -v`

Expected: PASS (3 tests)

**Step 5: Write network utilities test**

Create `tests/utils/test_network.py`:
```python
import pytest
from homeauto.utils.network import (
    is_valid_ip,
    is_valid_mac,
    parse_subnet,
    get_local_ip,
)


def test_is_valid_ip():
    assert is_valid_ip("192.168.1.1") is True
    assert is_valid_ip("192.168.1.256") is False
    assert is_valid_ip("not-an-ip") is False


def test_is_valid_mac():
    assert is_valid_mac("AA:BB:CC:DD:EE:FF") is True
    assert is_valid_mac("aa:bb:cc:dd:ee:ff") is True
    assert is_valid_mac("AA-BB-CC-DD-EE-FF") is True
    assert is_valid_mac("not-a-mac") is False


def test_parse_subnet():
    ips = parse_subnet("192.168.1.0/30")
    # /30 gives us 4 IPs: .0 (network), .1, .2, .3 (broadcast)
    assert len(ips) == 4
    assert "192.168.1.1" in ips
    assert "192.168.1.2" in ips


def test_get_local_ip():
    ip = get_local_ip()
    assert is_valid_ip(ip)
```

**Step 6: Run test to verify it fails**

Run: `pytest tests/utils/test_network.py -v`

Expected: FAIL with "ModuleNotFoundError"

**Step 7: Implement network utilities**

Create `homeauto/utils/network.py`:
```python
import socket
import ipaddress
from typing import List


def is_valid_ip(ip: str) -> bool:
    """Check if string is a valid IP address"""
    try:
        ipaddress.ip_address(ip)
        return True
    except ValueError:
        return False


def is_valid_mac(mac: str) -> bool:
    """Check if string is a valid MAC address"""
    # Remove common separators and check format
    mac_clean = mac.replace(':', '').replace('-', '').upper()
    if len(mac_clean) != 12:
        return False

    try:
        int(mac_clean, 16)
        return True
    except ValueError:
        return False


def parse_subnet(subnet: str) -> List[str]:
    """Parse subnet and return list of IP addresses"""
    try:
        network = ipaddress.ip_network(subnet, strict=False)
        return [str(ip) for ip in network.hosts()] + [str(network.network_address), str(network.broadcast_address)]
    except ValueError:
        return []


def get_local_ip() -> str:
    """Get local IP address of this machine"""
    try:
        # Connect to external host (doesn't actually send data)
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception:
        return "127.0.0.1"
```

**Step 8: Run test to verify it passes**

Run: `pytest tests/utils/test_network.py -v`

Expected: PASS (4 tests)

**Step 9: Commit**

Run:
```bash
git add homeauto/utils/ tests/utils/
git commit -m "feat: implement retry logic and network utilities"
```

---

## Phase 1: Device Discovery

### Task 5: Mock Device System

**Files:**
- Create: `homeauto/discovery/mock.py`
- Create: `tests/discovery/test_mock.py`

**Step 1: Write mock device test**

Create `tests/discovery/test_mock.py`:
```python
import pytest
from homeauto.discovery.mock import MockDeviceGenerator, MockDevice


def test_generate_mock_devices():
    generator = MockDeviceGenerator()
    devices = generator.generate(count=5)

    assert len(devices) == 5
    assert all(isinstance(d, MockDevice) for d in devices)


def test_mock_device_types():
    generator = MockDeviceGenerator()
    devices = generator.generate(count=10)

    types = [d.device_type for d in devices]
    # Should have variety of device types
    assert "camera" in types or "sensor" in types or "gate" in types


def test_mock_device_response():
    device = MockDevice(
        device_type="camera",
        ip="192.168.1.100",
        mac="AA:BB:CC:DD:EE:FF"
    )

    assert device.is_online() is True
    assert device.get_info()["type"] == "camera"
    assert device.get_info()["ip"] == "192.168.1.100"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/discovery/test_mock.py -v`

Expected: FAIL with "ModuleNotFoundError"

**Step 3: Implement mock device system**

Create `homeauto/discovery/mock.py`:
```python
import random
from typing import List, Dict
from dataclasses import dataclass


@dataclass
class MockDevice:
    device_type: str
    ip: str
    mac: str
    manufacturer: str = "Mock Manufacturer"
    model: str = "Mock Model"

    def is_online(self) -> bool:
        """Simulate device availability (90% online)"""
        return random.random() < 0.9

    def get_info(self) -> Dict:
        """Return device information"""
        return {
            "type": self.device_type,
            "ip": self.ip,
            "mac": self.mac,
            "manufacturer": self.manufacturer,
            "model": self.model,
        }

    def get_config(self) -> Dict:
        """Return mock configuration"""
        return {
            "name": f"Mock {self.device_type} {self.ip.split('.')[-1]}",
            "enabled": True,
        }


class MockDeviceGenerator:
    DEVICE_TYPES = [
        ("camera", "MockCam", "IP Camera X1"),
        ("sensor", "MockSensor", "TempHumid Pro"),
        ("gate", "MockGate", "Gate Controller"),
        ("switch", "MockSwitch", "Smart Switch"),
    ]

    def generate(self, count: int = 5, base_ip: str = "192.168.1") -> List[MockDevice]:
        """Generate mock devices with varied types"""
        devices = []

        for i in range(count):
            device_type, manufacturer, model = random.choice(self.DEVICE_TYPES)
            ip = f"{base_ip}.{100 + i}"
            mac = self._generate_mac()

            device = MockDevice(
                device_type=device_type,
                ip=ip,
                mac=mac,
                manufacturer=manufacturer,
                model=model,
            )
            devices.append(device)

        return devices

    def _generate_mac(self) -> str:
        """Generate random MAC address"""
        return ":".join([f"{random.randint(0, 255):02X}" for _ in range(6)])
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/discovery/test_mock.py -v`

Expected: PASS (3 tests)

**Step 5: Commit**

Run:
```bash
git add homeauto/discovery/mock.py tests/discovery/test_mock.py
git commit -m "feat: implement mock device system for testing"
```

---

### Task 6: Network Scanner

**Files:**
- Create: `homeauto/discovery/scanner.py`
- Create: `tests/discovery/test_scanner.py`

**Step 1: Write scanner test**

Create `tests/discovery/test_scanner.py`:
```python
import pytest
from unittest.mock import patch, MagicMock
from homeauto.discovery.scanner import NetworkScanner


def test_scanner_initialization():
    scanner = NetworkScanner(subnet="192.168.1.0/24")
    assert scanner.subnet == "192.168.1.0/24"


@patch('homeauto.discovery.scanner.os.system')
def test_ping_host(mock_system):
    scanner = NetworkScanner()

    # Mock successful ping
    mock_system.return_value = 0
    assert scanner.ping_host("192.168.1.1") is True

    # Mock failed ping
    mock_system.return_value = 1
    assert scanner.ping_host("192.168.1.1") is False


@patch('homeauto.discovery.scanner.NetworkScanner.ping_host')
def test_scan_subnet(mock_ping):
    # Mock ping results: first 3 IPs respond
    mock_ping.side_effect = [True, True, True] + [False] * 250

    scanner = NetworkScanner(subnet="192.168.1.0/28")  # Small subnet for testing
    active_hosts = scanner.scan_subnet()

    assert len(active_hosts) == 3
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/discovery/test_scanner.py -v`

Expected: FAIL with "ModuleNotFoundError"

**Step 3: Implement network scanner**

Create `homeauto/discovery/scanner.py`:
```python
import os
import platform
import socket
from typing import List, Dict
from concurrent.futures import ThreadPoolExecutor, as_completed
from homeauto.utils.network import parse_subnet, get_local_ip


class NetworkScanner:
    def __init__(self, subnet: str = None, timeout: int = 1):
        self.subnet = subnet or self._get_default_subnet()
        self.timeout = timeout

    def _get_default_subnet(self) -> str:
        """Get default subnet based on local IP"""
        local_ip = get_local_ip()
        # Assume /24 subnet
        parts = local_ip.split('.')
        return f"{parts[0]}.{parts[1]}.{parts[2]}.0/24"

    def ping_host(self, ip: str) -> bool:
        """Ping a host to check if it's alive"""
        param = '-n' if platform.system().lower() == 'windows' else '-c'
        command = f"ping {param} 1 -w {self.timeout * 1000} {ip}"

        # Redirect output to null
        null_device = 'NUL' if platform.system().lower() == 'windows' else '/dev/null'
        command = f"{command} > {null_device} 2>&1"

        return os.system(command) == 0

    def scan_subnet(self, max_workers: int = 50) -> List[str]:
        """Scan subnet for active hosts"""
        ips = parse_subnet(self.subnet)
        active_hosts = []

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_ip = {executor.submit(self.ping_host, ip): ip for ip in ips}

            for future in as_completed(future_to_ip):
                ip = future_to_ip[future]
                try:
                    if future.result():
                        active_hosts.append(ip)
                except Exception:
                    pass

        return active_hosts

    def get_mac_address(self, ip: str) -> str:
        """Get MAC address for an IP (placeholder - would use ARP)"""
        # This is a simplified version - real implementation would use ARP tables
        # For now, return a placeholder
        return "00:00:00:00:00:00"

    def scan_ports(self, ip: str, ports: List[int]) -> List[int]:
        """Scan specific ports on a host"""
        open_ports = []

        for port in ports:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(self.timeout)
                result = sock.connect_ex((ip, port))
                sock.close()

                if result == 0:
                    open_ports.append(port)
            except Exception:
                pass

        return open_ports
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/discovery/test_scanner.py -v`

Expected: PASS (3 tests)

**Step 5: Commit**

Run:
```bash
git add homeauto/discovery/scanner.py tests/discovery/test_scanner.py
git commit -m "feat: implement network scanner with ping and port scanning"
```

---

### Task 7: Device Identifier

**Files:**
- Create: `homeauto/discovery/identifier.py`
- Create: `tests/discovery/test_identifier.py`

**Step 1: Write identifier test**

Create `tests/discovery/test_identifier.py`:
```python
import pytest
from unittest.mock import patch, MagicMock
from homeauto.discovery.identifier import DeviceIdentifier


def test_identify_by_ports():
    identifier = DeviceIdentifier()

    # Camera on RTSP port
    device_type = identifier.identify_by_ports([554, 80])
    assert device_type == "camera"

    # Unknown device
    device_type = identifier.identify_by_ports([8080])
    assert device_type == "unknown"


def test_identify_by_manufacturer():
    identifier = DeviceIdentifier()

    device_type = identifier.identify_by_manufacturer("Tuya")
    assert device_type in ["sensor", "switch"]

    device_type = identifier.identify_by_manufacturer("Hikvision")
    assert device_type == "camera"


def test_calculate_confidence():
    identifier = DeviceIdentifier()

    signals = {
        "port_match": True,
        "manufacturer_match": True,
        "api_probe": True,
    }

    confidence = identifier.calculate_confidence(signals)
    assert confidence > 0.7
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/discovery/test_identifier.py -v`

Expected: FAIL with "ModuleNotFoundError"

**Step 3: Implement device identifier**

Create `homeauto/discovery/identifier.py`:
```python
from typing import List, Dict, Tuple


class DeviceIdentifier:
    # Port-based identification
    PORT_SIGNATURES = {
        "camera": [554, 8000, 8080],  # RTSP, common camera ports
        "gate": [8000, 9000],
        "sensor": [6668],  # Tuya
        "switch": [6668],  # Tuya
    }

    # Manufacturer-based identification
    MANUFACTURER_TYPES = {
        "Hikvision": "camera",
        "Dahua": "camera",
        "Tuya": "sensor",  # Can also be switch
        "Hik": "gate",
    }

    def identify_by_ports(self, open_ports: List[int]) -> str:
        """Identify device type by open ports"""
        for device_type, signature_ports in self.PORT_SIGNATURES.items():
            if any(port in open_ports for port in signature_ports):
                return device_type

        return "unknown"

    def identify_by_manufacturer(self, manufacturer: str) -> str:
        """Identify device type by manufacturer"""
        for mfr, device_type in self.MANUFACTURER_TYPES.items():
            if mfr.lower() in manufacturer.lower():
                return device_type

        return "unknown"

    def calculate_confidence(self, signals: Dict[str, bool]) -> float:
        """Calculate confidence score based on identification signals"""
        weights = {
            "port_match": 0.3,
            "manufacturer_match": 0.3,
            "api_probe": 0.4,
        }

        confidence = 0.0
        for signal, weight in weights.items():
            if signals.get(signal, False):
                confidence += weight

        return confidence

    def identify(
        self,
        ip: str,
        mac: str,
        open_ports: List[int],
        manufacturer: str = None
    ) -> Tuple[str, float]:
        """
        Identify device type and calculate confidence score

        Returns:
            Tuple of (device_type, confidence_score)
        """
        signals = {
            "port_match": False,
            "manufacturer_match": False,
            "api_probe": False,  # Placeholder for future API probing
        }

        # Try port-based identification
        port_type = self.identify_by_ports(open_ports)
        if port_type != "unknown":
            signals["port_match"] = True
            device_type = port_type
        else:
            device_type = "unknown"

        # Try manufacturer-based identification
        if manufacturer:
            mfr_type = self.identify_by_manufacturer(manufacturer)
            if mfr_type != "unknown":
                signals["manufacturer_match"] = True
                # Manufacturer signal can override port detection
                if device_type == "unknown":
                    device_type = mfr_type

        confidence = self.calculate_confidence(signals)

        return device_type, confidence
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/discovery/test_identifier.py -v`

Expected: PASS (3 tests)

**Step 5: Commit**

Run:
```bash
git add homeauto/discovery/identifier.py tests/discovery/test_identifier.py
git commit -m "feat: implement device identifier with port and manufacturer detection"
```

---

## Phase 1: CLI Scanner

### Task 8: CLI Scanner Tool

**Files:**
- Create: `homeauto/cli/scan.py`
- Create: `tests/cli/test_scan.py`

**Step 1: Write CLI scanner test**

Create `tests/cli/test_scan.py`:
```python
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
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/cli/test_scan.py -v`

Expected: FAIL with "ModuleNotFoundError"

**Step 3: Implement CLI scanner**

Create `homeauto/cli/scan.py`:
```python
import sys
from typing import List, Dict
from datetime import datetime
from homeauto.discovery.scanner import NetworkScanner
from homeauto.discovery.identifier import DeviceIdentifier
from homeauto.discovery.mock import MockDeviceGenerator
from homeauto.database.repository import DeviceRepository
from homeauto.database.models import Device, DeviceStatus
from homeauto.config.manager import ConfigManager


def format_device_table(devices: List[Dict]) -> str:
    """Format devices as ASCII table"""
    if not devices:
        return "No devices found."

    # Header
    header = f"{'ID':<15} {'Type':<10} {'IP':<15} {'Name':<25} {'Status':<10}"
    separator = "-" * 80

    rows = [header, separator]

    for device in devices:
        row = (
            f"{device['id']:<15} "
            f"{device['type']:<10} "
            f"{device['ip']:<15} "
            f"{device['name']:<25} "
            f"{device['status']:<10}"
        )
        rows.append(row)

    return "\n".join(rows)


class ScanCommand:
    def __init__(self, config_path: str = "config.yaml"):
        self.config = ConfigManager(config_path)
        self.scanner = NetworkScanner(
            subnet=self.config.get_setting("subnet", "192.168.1.0/24")
        )
        self.identifier = DeviceIdentifier()
        self.repository = DeviceRepository()
        self.use_mock = self.config.get("testing.use_mock_devices", False)

    def execute(self) -> Dict:
        """Execute device scan"""
        print("🔍 Scanning network for devices...")

        if self.use_mock:
            return self._scan_mock_devices()
        else:
            return self._scan_real_devices()

    def _scan_mock_devices(self) -> Dict:
        """Scan using mock devices"""
        print("Using mock devices for testing")

        generator = MockDeviceGenerator()
        count = self.config.get("testing.mock_device_count", 5)
        mock_devices = generator.generate(count=count)

        discovered = 0

        for mock_device in mock_devices:
            if not mock_device.is_online():
                continue

            info = mock_device.get_info()

            device = Device(
                id=f"{info['type']}-{info['ip'].split('.')[-1]}",
                device_type=info['type'],
                ip_address=info['ip'],
                mac_address=info['mac'],
                name=f"{info['type'].title()} {info['ip'].split('.')[-1]}",
                status=DeviceStatus.ONLINE,
                manufacturer=info['manufacturer'],
                model=info['model'],
                confidence_score=0.9,
            )

            self.repository.save(device)
            discovered += 1
            print(f"  Found: {device.name} ({device.ip_address})")

        print(f"\n✅ Discovered {discovered} devices")
        return {"discovered": discovered}

    def _scan_real_devices(self) -> Dict:
        """Scan real network devices"""
        # Scan for active hosts
        active_hosts = self.scanner.scan_subnet()
        print(f"Found {len(active_hosts)} active hosts")

        discovered = 0
        common_ports = [80, 443, 554, 8000, 8080, 6668]

        for ip in active_hosts:
            print(f"  Probing {ip}...")

            # Scan ports
            open_ports = self.scanner.scan_ports(ip, common_ports)
            if not open_ports:
                continue

            # Get MAC address
            mac = self.scanner.get_mac_address(ip)

            # Identify device
            device_type, confidence = self.identifier.identify(
                ip=ip,
                mac=mac,
                open_ports=open_ports,
            )

            if device_type == "unknown":
                continue

            device = Device(
                id=f"{device_type}-{ip.split('.')[-1]}",
                device_type=device_type,
                ip_address=ip,
                mac_address=mac,
                name=f"{device_type.title()} {ip.split('.')[-1]}",
                status=DeviceStatus.ONLINE,
                confidence_score=confidence,
            )

            self.repository.save(device)
            discovered += 1
            print(f"    ✓ {device_type} at {ip}")

        print(f"\n✅ Discovered {discovered} devices")
        return {"discovered": discovered}


def main():
    """Main entry point for homeauto-scan command"""
    try:
        cmd = ScanCommand()
        result = cmd.execute()

        # Show discovered devices
        print("\n📋 Discovered devices:")
        devices = cmd.repository.get_all()
        device_dicts = [
            {
                "id": d.id,
                "type": d.device_type,
                "ip": d.ip_address,
                "name": d.name,
                "status": d.status.value,
            }
            for d in devices
        ]
        print(format_device_table(device_dicts))

        return 0
    except KeyboardInterrupt:
        print("\n\n⚠️  Scan interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/cli/test_scan.py -v`

Expected: PASS (2 tests)

**Step 5: Test CLI manually with mock devices**

Create a test config:
```bash
cp config.example.yaml config.yaml
```

Edit `config.yaml` to enable mock devices:
```yaml
testing:
  use_mock_devices: true
  mock_device_count: 5
```

Run:
```bash
homeauto-scan
```

Expected: Should discover and display 5 mock devices

**Step 6: Commit**

Run:
```bash
git add homeauto/cli/scan.py tests/cli/test_scan.py
git commit -m "feat: implement CLI scanner tool with mock support"
```

---

## Phase 2: Device Adapters

### Task 9: Base Device Adapter

**Files:**
- Create: `homeauto/devices/base.py`
- Create: `tests/devices/test_base.py`

**Step 1: Write base device test**

Create `tests/devices/test_base.py`:
```python
import pytest
from homeauto.devices.base import BaseDevice, DeviceCapability


def test_device_capability_enum():
    assert DeviceCapability.STATUS in [c for c in DeviceCapability]
    assert DeviceCapability.CONTROL in [c for c in DeviceCapability]


def test_base_device_interface():
    # BaseDevice is abstract, so we test that subclasses must implement methods
    class TestDevice(BaseDevice):
        pass

    with pytest.raises(TypeError):
        # Should fail because abstract methods not implemented
        device = TestDevice(ip="192.168.1.100", credentials={})
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/devices/test_base.py -v`

Expected: FAIL with "ModuleNotFoundError"

**Step 3: Implement base device adapter**

Create `homeauto/devices/base.py`:
```python
from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, List, Any
from homeauto.utils.retry import retry_with_backoff


class DeviceCapability(Enum):
    STATUS = "status"
    CONTROL = "control"
    CONFIG = "config"
    STREAM = "stream"


class BaseDevice(ABC):
    """Base class for all device adapters"""

    def __init__(self, ip: str, credentials: Dict[str, str]):
        self.ip = ip
        self.credentials = credentials

    @abstractmethod
    def get_info(self) -> Dict[str, Any]:
        """Get basic device information"""
        pass

    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """Get current device status"""
        pass

    @abstractmethod
    def test_connection(self) -> bool:
        """Test if device is reachable"""
        pass

    def get_config(self) -> Dict[str, Any]:
        """Get device configuration (optional)"""
        return {}

    def update_config(self, config: Dict[str, Any]) -> bool:
        """Update device configuration (optional)"""
        return False

    def get_capabilities(self) -> List[DeviceCapability]:
        """Return list of supported capabilities"""
        return [DeviceCapability.STATUS, DeviceCapability.CONFIG]
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/devices/test_base.py -v`

Expected: PASS (2 tests)

**Step 5: Commit**

Run:
```bash
git add homeauto/devices/base.py tests/devices/test_base.py
git commit -m "feat: implement base device adapter interface"
```

---

### Task 10: Camera Device Adapter

**Files:**
- Create: `homeauto/devices/camera.py`
- Create: `tests/devices/test_camera.py`

**Step 1: Write camera device test**

Create `tests/devices/test_camera.py`:
```python
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
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/devices/test_camera.py -v`

Expected: FAIL with "ModuleNotFoundError"

**Step 3: Implement camera device adapter**

Create `homeauto/devices/camera.py`:
```python
import requests
from typing import Dict, Any, List
from homeauto.devices.base import BaseDevice, DeviceCapability
from homeauto.utils.retry import retry_with_backoff


class CameraDevice(BaseDevice):
    """IP Camera device adapter (generic ONVIF/HTTP)"""

    def __init__(self, ip: str, credentials: Dict[str, str]):
        super().__init__(ip, credentials)
        self.base_url = f"http://{ip}"
        self.timeout = 5

    @retry_with_backoff(max_attempts=3, base_delay=1.0)
    def test_connection(self) -> bool:
        """Test camera connectivity"""
        try:
            response = requests.get(
                f"{self.base_url}/",
                auth=(
                    self.credentials.get("username"),
                    self.credentials.get("password")
                ),
                timeout=self.timeout
            )
            return response.status_code in [200, 401]  # 401 means auth required but reachable
        except Exception:
            return False

    @retry_with_backoff(max_attempts=3)
    def get_info(self) -> Dict[str, Any]:
        """Get camera information"""
        try:
            # Try ONVIF GetDeviceInformation
            response = requests.get(
                f"{self.base_url}/onvif/device_service",
                auth=(
                    self.credentials.get("username"),
                    self.credentials.get("password")
                ),
                timeout=self.timeout
            )

            if response.status_code == 200:
                data = response.json()
                return {
                    "type": "camera",
                    "ip": self.ip,
                    "model": data.get("model", "Unknown"),
                    "firmware": data.get("firmware", "Unknown"),
                }
        except Exception:
            pass

        # Fallback to basic info
        return {
            "type": "camera",
            "ip": self.ip,
            "model": "Generic IP Camera",
            "firmware": "Unknown",
        }

    @retry_with_backoff(max_attempts=3)
    def get_status(self) -> Dict[str, Any]:
        """Get camera status"""
        online = self.test_connection()

        return {
            "online": online,
            "streaming": online,  # Assume streaming if online
            "recording": False,   # Would need specific API call
        }

    def get_capabilities(self) -> List[DeviceCapability]:
        return [
            DeviceCapability.STATUS,
            DeviceCapability.CONFIG,
            DeviceCapability.STREAM,
        ]

    def get_stream_url(self) -> str:
        """Get RTSP stream URL"""
        username = self.credentials.get("username", "")
        password = self.credentials.get("password", "")
        return f"rtsp://{username}:{password}@{self.ip}:554/stream1"
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/devices/test_camera.py -v`

Expected: PASS (3 tests)

**Step 5: Commit**

Run:
```bash
git add homeauto/devices/camera.py tests/devices/test_camera.py
git commit -m "feat: implement camera device adapter"
```

---

*Due to length constraints, I'll provide a condensed version of remaining tasks. Follow the same TDD pattern for:*

- Task 11: Tuya Device Adapter
- Task 12: Hik Connect Gate Adapter
- Task 13: CLI Config Tool
- Task 14: FastAPI Web Backend
- Task 15: Alpine.js Frontend
- Task 16: WebSocket Real-time Updates
- Task 17: Integration Tests
- Task 18: Documentation

---

## Summary Checklist

**Phase 1 - Core & CLI Scanner:**
- ✓ Project setup with venv
- ✓ Database layer (SQLite models & repository)
- ✓ Configuration manager (YAML)
- ✓ Utilities (retry, network)
- ✓ Mock device system
- ✓ Network scanner
- ✓ Device identifier
- ✓ CLI scanner tool
- ✓ Device adapters base
- ✓ Camera adapter

**Phase 2 - Configuration CLI:**
- Tuya adapter
- Hik Connect adapter
- CLI config tool
- Device configuration management

**Phase 3 - Web Application:**
- FastAPI backend setup
- REST API endpoints
- WebSocket support
- Frontend HTML/Alpine.js
- Tailwind CSS styling
- Device dashboard widgets
- Real-time status updates

**Testing & Documentation:**
- Integration tests
- End-to-end tests
- README documentation
- API documentation

---

## Testing Philosophy

Every feature follows TDD:
1. Write failing test
2. Run test (verify failure)
3. Write minimal implementation
4. Run test (verify pass)
5. Commit

**Coverage goal: 80%+ for core library**

## Commit Conventions

```
feat: add new feature
fix: bug fix
test: add tests
docs: documentation
refactor: code improvement
```

Each commit should be small, focused, and include tests.
