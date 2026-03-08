from unittest.mock import MagicMock

from homeauto.services.camera.manager import CameraServiceManager


def _make_manager():
    camera = MagicMock()
    camera.ip = "192.168.1.10"
    return CameraServiceManager(camera, config={})


def test_manager_alias_methods_delegate_to_core():
    manager = _make_manager()
    manager.start = MagicMock(return_value=True)
    manager.stop = MagicMock(return_value=True)

    assert manager.start_all_services() is True
    assert manager.stop_all_services() is True
    manager.start.assert_called_once()
    manager.stop.assert_called_once()


def test_manager_add_schedule_uses_named_signature():
    manager = _make_manager()
    scheduled_service = MagicMock()
    scheduled_service.add_schedule.return_value = True
    manager.services["scheduled"] = scheduled_service

    cfg = {"name": "every-minute", "interval_seconds": 60}
    assert manager.add_schedule(cfg) is True
    scheduled_service.add_schedule.assert_called_once_with("every-minute", cfg)


def test_manager_get_recent_snapshots_flattens_backend_map():
    manager = _make_manager()
    manager.get_snapshots = MagicMock(
        return_value={
            "local": [{"filename": "a.jpg", "created_at": "2026-01-01T00:00:00"}],
            "ftp": [{"filename": "b.jpg", "created_at": "2026-01-02T00:00:00"}],
        }
    )

    snapshots = manager.get_recent_snapshots(limit=10)
    assert len(snapshots) == 2
    assert snapshots[0]["backend"] == "ftp"
    assert snapshots[1]["backend"] == "local"
