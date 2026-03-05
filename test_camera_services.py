#!/usr/bin/env python3
"""
Test script to verify camera services are working.
"""

import sys
import os

# Fix Unicode encoding for Windows
sys.stdout.reconfigure(encoding='utf-8')

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test if all required modules can be imported."""
    print("Testing imports...")
    
    modules_to_test = [
        ("homeauto.services.camera.global_manager", "GlobalCameraServiceManager"),
        ("homeauto.services.camera.manager", "CameraServiceManager"),
        ("homeauto.services.camera.storage", "StorageManager"),
        ("homeauto.analytics.camera_analytics", "MotionDetector"),
        ("homeauto.utils.notifications", "EmailNotifier"),
    ]
    
    all_imports_ok = True
    
    for module_path, class_name in modules_to_test:
        try:
            module = __import__(module_path, fromlist=[class_name])
            if hasattr(module, class_name):
                print(f"OK: {module_path}.{class_name}")
            else:
                print(f"FAIL: {module_path}.{class_name} (class not found)")
                all_imports_ok = False
        except ImportError as e:
            print(f"FAIL: {module_path}.{class_name} (ImportError: {e})")
            all_imports_ok = False
        except Exception as e:
            print(f"FAIL: {module_path}.{class_name} (Error: {e})")
            all_imports_ok = False
    
    return all_imports_ok

def test_camera_services():
    """Test camera services functionality."""
    print("\nTesting camera services...")
    
    try:
        from homeauto.services.camera.global_manager import GlobalCameraServiceManager
        
        # Create a global manager instance
        manager = GlobalCameraServiceManager()
        
        print(f"OK: GlobalCameraServiceManager created: {manager}")
        
        # Check status
        status = manager.get_status()
        print(f"OK: Camera services status: {status}")
        
        return True
        
    except Exception as e:
        print(f"FAIL: Camera services test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main test function."""
    print("Camera Services Test")
    print("=" * 60)
    
    # Test imports
    imports_ok = test_imports()
    
    if not imports_ok:
        print("\nERROR: Import tests failed. Fix dependencies first.")
        return 1
    
    # Test camera services
    services_ok = test_camera_services()
    
    print("\n" + "=" * 60)
    
    if services_ok:
        print("SUCCESS: All tests passed!")
        print("\nYou can now use camera services with:")
        print("  python -m homeauto.services.camera.global_manager start")
        print("  python -m homeauto.services.camera.global_manager status")
        print("  python -m homeauto.services.camera.global_manager stop")
        return 0
    else:
        print("ERROR: Some tests failed.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
