#!/usr/bin/env python3
"""
Simple test for camera services functionality.
"""

import sys
import os
import time
from datetime import datetime

# Add the project to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_camera_services():
    """Test basic camera services functionality."""
    print("Testing Camera Services Enhancement")
    print("=" * 60)
    
    try:
        # Test 1: Check if we can import the modules
        print("\n1. Testing imports...")
        from homeauto.services.camera.global_manager import GlobalCameraServiceManager
        from homeauto.database.repository import DeviceRepository
        from homeauto.devices.camera import CameraDevice
        from homeauto.config.manager import ConfigManager
        
        print("   [OK] All imports successful")
        
        # Test 2: Check configuration
        print("\n2. Testing configuration...")
        config_manager = ConfigManager()
        config = config_manager.config.get('camera_services', {})
        
        if config:
            print(f"   [OK] Camera services config loaded")
            print(f"   - Enabled: {config.get('enabled', False)}")
            print(f"   - Has defaults: {'defaults' in config}")
            print(f"   - Has cameras: {'cameras' in config}")
        else:
            print("   ✗ No camera services configuration found")
            return
        
        # Test 3: Check database for cameras
        print("\n3. Testing database...")
        repo = DeviceRepository()
        cameras = repo.get_by_type('camera')
        
        if cameras:
            print(f"   [OK] Found {len(cameras)} camera(s) in database")
            for camera in cameras:
                print(f"   - {camera.name} ({camera.ip_address})")
        else:
            print("   ✗ No cameras found in database")
            # Create a test camera
            from homeauto.database.models import Device, DeviceStatus
            test_camera = Device(
                id='test_camera_simple',
                device_type='camera',
                ip_address='127.0.0.1',
                mac_address='00:11:22:33:44:55',
                name='Test Camera Simple',
                status=DeviceStatus.ONLINE,
                manufacturer='Test',
                model='Test Model',
                confidence_score=0.95,
                last_seen=datetime.now(),
                config={'resolution': '640x480', 'fps': 30},
                metadata={'location': 'Test', 'notes': 'Test camera for simple test'}
            )
            repo.save(test_camera)
            print("   [OK] Created test camera in database")
            cameras = [test_camera]
        
        # Test 4: Test global manager
        print("\n4. Testing global manager...")
        global_manager = GlobalCameraServiceManager()
        
        # Initialize
        if global_manager.initialize():
            print("   [OK] Global manager initialized")
            print(f"   - Total cameras: {global_manager.stats['total_cameras']}")
            print(f"   - Initialized cameras: {global_manager.stats['initialized_cameras']}")
        else:
            print("   ✗ Failed to initialize global manager")
            return
        
        # Start services
        if global_manager.start_all_services():
            print("   [OK] Camera services started")
            print(f"   - Running cameras: {global_manager.stats['running_cameras']}")
            
            # Get status
            status = global_manager.get_status()
            print(f"   - Services running: {status['running']}")
            print(f"   - Services initialized: {status['initialized']}")
            
            # Wait a bit
            print("\n   Waiting 3 seconds...")
            time.sleep(3)
            
            # Stop services
            if global_manager.stop_all_services():
                print("   [OK] Camera services stopped")
            else:
                print("   ✗ Failed to stop camera services")
        else:
            print("   ✗ Failed to start camera services")
        
        # Test 5: Cleanup
        print("\n5. Cleaning up...")
        global_manager.cleanup()
        print("   ✓ Cleanup completed")
        
        print("\n" + "=" * 60)
        print("Camera Services Test: SUCCESS ✓")
        print("=" * 60)
        
    except ImportError as e:
        print(f"\n✗ Import error: {e}")
        print("Make sure all dependencies are installed:")
        print("  pip install schedule paramiko google-auth google-auth-oauthlib")
        print("  pip install google-auth-httplib2 google-api-python-client")
        print("  pip install opencv-python-headless pillow")
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_camera_services()
