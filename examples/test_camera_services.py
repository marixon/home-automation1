#!/usr/bin/env python3
"""
Test script for camera services enhancement.
"""

import sys
import os

# Add the project to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_imports():
    """Test that all modules can be imported."""
    print("Testing imports...")
    
    modules_to_test = [
        "homeauto.services.camera.manager",
        "homeauto.services.camera.global_manager",
        "homeauto.services.camera.snapshot_service",
        "homeauto.services.camera.scheduled_service",
        "homeauto.services.camera.motion_service",
        "homeauto.services.camera.object_recognition",
        "homeauto.services.camera.storage.base",
        "homeauto.services.camera.storage.local_storage",
        "homeauto.services.camera.storage.ftp_storage",
        "homeauto.services.camera.storage.sftp_storage",
        "homeauto.services.camera.storage.google_drive_storage",
    ]
    
    for module_name in modules_to_test:
        try:
            __import__(module_name)
            print(f"✓ {module_name}")
        except ImportError as e:
            print(f"✗ {module_name}: {e}")
        except Exception as e:
            print(f"✗ {module_name}: {type(e).__name__}: {e}")


def test_configuration():
    """Test configuration loading."""
    print("\nTesting configuration...")
    
    try:
        from homeauto.config.manager import ConfigManager
        
        config_manager = ConfigManager()
        config = config_manager.get_config()
        
        if "camera_services" in config:
            print("✓ Camera services configuration found")
            camera_config = config["camera_services"]
            print(f"  - Enabled: {camera_config.get('enabled', 'Not set')}")
            print(f"  - Auto-start: {camera_config.get('auto_start', 'Not set')}")
        else:
            print("✗ Camera services configuration not found")
            print("  Add camera_services section to your config.yaml")
            
    except Exception as e:
        print(f"✗ Error loading configuration: {e}")


def test_database():
    """Test database connectivity."""
    print("\nTesting database...")
    
    try:
        from homeauto.database.repository import DeviceRepository
        
        repo = DeviceRepository()
        devices = repo.get_all()
        
        cameras = [d for d in devices if d.device_type == 'camera']
        print(f"✓ Database connected")
        print(f"  - Total devices: {len(devices)}")
        print(f"  - Cameras: {len(cameras)}")
        
        if cameras:
            for camera in cameras[:3]:  # Show first 3 cameras
                print(f"    • {camera.name} ({camera.ip_address})")
        
    except Exception as e:
        print(f"✗ Database error: {e}")


def test_storage_classes():
    """Test storage class instantiation."""
    print("\nTesting storage classes...")
    
    try:
        from homeauto.services.camera.storage import (
            LocalStorage, FTPStorage, SFTPStorage, GoogleDriveStorage
        )
        
        # Test LocalStorage
        local_config = {
            "enabled": True,
            "base_path": "./test_storage",
            "organization": "flat"
        }
        
        try:
            local_storage = LocalStorage(local_config)
            print("✓ LocalStorage created")
        except Exception as e:
            print(f"✗ LocalStorage error: {e}")
        
        # Test FTPStorage (configuration only)
        ftp_config = {
            "enabled": False,
            "host": "localhost",
            "username": "test",
            "password": "test"
        }
        
        try:
            ftp_storage = FTPStorage(ftp_config)
            print("✓ FTPStorage created (not initialized)")
        except Exception as e:
            print(f"✗ FTPStorage error: {e}")
        
        # Test StorageManager
        from homeauto.services.camera.storage import StorageManager
        
        storage_config = {
            "local": local_config,
            "ftp": ftp_config
        }
        
        try:
            storage_manager = StorageManager(storage_config)
            print("✓ StorageManager created")
        except Exception as e:
            print(f"✗ StorageManager error: {e}")
            
    except ImportError as e:
        print(f"✗ Import error: {e}")
    except Exception as e:
        print(f"✗ Error: {e}")


def test_service_classes():
    """Test service class instantiation."""
    print("\nTesting service classes...")
    
    try:
        from homeauto.devices.camera import CameraDevice
        from homeauto.services.camera import (
            OnDemandSnapshotService,
            ScheduledSnapshotService,
            MotionDetectionService,
            ObjectRecognitionService
        )
        
        # Create a mock camera device
        camera = CameraDevice("192.168.1.100", {"username": "test", "password": "test"})
        
        # Test OnDemandSnapshotService
        on_demand_config = {
            "camera_name": "Test Camera",
            "camera_ip": "192.168.1.100",
            "max_queue_size": 5,
            "storage": ["local"]
        }
        
        try:
            on_demand_service = OnDemandSnapshotService(camera, on_demand_config)
            print("✓ OnDemandSnapshotService created")
        except Exception as e:
            print(f"✗ OnDemandSnapshotService error: {e}")
        
        # Test ScheduledSnapshotService
        scheduled_config = {
            "camera_name": "Test Camera",
            "camera_ip": "192.168.1.100",
            "schedules": [
                {
                    "name": "test",
                    "interval_seconds": 60
                }
            ]
        }
        
        try:
            scheduled_service = ScheduledSnapshotService(camera, scheduled_config)
            print("✓ ScheduledSnapshotService created")
        except Exception as e:
            print(f"✗ ScheduledSnapshotService error: {e}")
        
        # Test CameraServiceManager
        from homeauto.services.camera.manager import CameraServiceManager
        
        manager_config = {
            "camera_name": "Test Camera",
            "camera_ip": "192.168.1.100",
            "storage": {
                "local": {
                    "enabled": True,
                    "base_path": "./test_snapshots"
                }
            },
            "services": {
                "on_demand": {"enabled": True},
                "scheduled": {"enabled": False},
                "motion_detected": {"enabled": False},
                "object_recognition": {"enabled": False}
            }
        }
        
        try:
            service_manager = CameraServiceManager(camera, manager_config)
            print("✓ CameraServiceManager created")
        except Exception as e:
            print(f"✗ CameraServiceManager error: {e}")
            
    except ImportError as e:
        print(f"✗ Import error: {e}")
    except Exception as e:
        print(f"✗ Error: {e}")


def test_api_endpoints():
    """Test API endpoint availability."""
    print("\nTesting API endpoints...")
    
    print("""
API endpoints that should be available:

1. Camera Services API:
   - GET    /api/camera-services/cameras
   - GET    /api/camera-services/health
   - GET    /api/camera-services/cameras/{id}/status
   - POST   /api/camera-services/cameras/{id}/initialize
   - POST   /api/camera-services/cameras/{id}/start
   - POST   /api/camera-services/cameras/{id}/stop
   - POST   /api/camera-services/cameras/{id}/snapshot/now
   - POST   /api/camera-services/cameras/{id}/snapshot/request
   - POST   /api/camera-services/cameras/{id}/motion/check
   - POST   /api/camera-services/cameras/{id}/objects/check
   - GET    /api/camera-services/cameras/{id}/snapshots
   - GET    /api/camera-services/cameras/{id}/services/{service}/status

2. Web Interface:
   - GET    /static/camera_services.html

To test the API:
1. Start the web server: python -m homeauto.web.api
2. Open http://localhost:8000/docs for API documentation
3. Open http://localhost:8000/static/camera_services.html for web interface
""")


def main():
    """Run all tests."""
    print("Camera Services Enhancement - Test Suite")
    print("=" * 60)
    
    test_imports()
    test_configuration()
    test_database()
    test_storage_classes()
    test_service_classes()
    test_api_endpoints()
    
    print("\n" + "=" * 60)
    print("Test completed!")
    print("=" * 60)
    
    print("\nSummary:")
    print("1. Check that all imports succeed")
    print("2. Verify configuration is loaded")
    print("3. Ensure database connectivity")
    print("4. Test storage and service classes")
    print("5. Review API endpoint documentation")
    
    print("\nNext steps:")
    print("1. Update your config.yaml with camera_services section")
    print("2. Install required dependencies (see requirements.txt)")
    print("3. Start the web server and test the API")
    print("4. Use the web interface to manage camera services")


if __name__ == "__main__":
    main()
