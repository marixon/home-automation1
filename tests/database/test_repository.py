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
        id="cam-001",
        device_type="camera",
        ip_address="192.168.1.100",
        mac_address="AA:BB:CC:DD:EE:FF",
        name="Camera 1",
        status=DeviceStatus.ONLINE,
    )
    device2 = Device(
        id="sensor-001",
        device_type="sensor",
        ip_address="192.168.1.101",
        mac_address="11:22:33:44:55:66",
        name="Sensor 1",
        status=DeviceStatus.ONLINE,
    )

    repo.save(device1)
    repo.save(device2)

    devices = repo.get_all()
    assert len(devices) == 2


def test_get_by_type(repo):
    camera = Device(
        id="cam-001",
        device_type="camera",
        ip_address="192.168.1.100",
        mac_address="AA:BB:CC:DD:EE:FF",
        name="Camera 1",
        status=DeviceStatus.ONLINE,
    )
    sensor = Device(
        id="sensor-001",
        device_type="sensor",
        ip_address="192.168.1.101",
        mac_address="11:22:33:44:55:66",
        name="Sensor 1",
        status=DeviceStatus.ONLINE,
    )

    repo.save(camera)
    repo.save(sensor)

    cameras = repo.get_by_type("camera")
    assert len(cameras) == 1
    assert cameras[0].device_type == "camera"
