#!/usr/bin/env python3
"""
Test script to verify the home automation project build
"""

import sys
import os

def test_imports():
    """Test that all required modules can be imported"""
    modules_to_test = [
        "homeauto",
        "homeauto.cli.scan",
        "homeauto.cli.config",
        "homeauto.database.repository",
        "homeauto.config.manager",
        "homeauto.devices.gate",
        "homeauto.devices.camera",
        "homeauto.devices.tuya",
        "homeauto.discovery.scanner",
        "homeauto.web.api",
    ]
    
    print("Testing module imports...")
    for module in modules_to_test:
        try:
            __import__(module)
            print(f"  [OK] {module}")
        except ImportError as e:
            print(f"  [FAIL] {module}: {e}")
            return False
    
    return True

def test_dependencies():
    """Test that required dependencies are available"""
    dependencies = [
        ("fastapi", "FastAPI"),
        ("sqlalchemy", "create_engine"),
        ("yaml", "safe_load"),
        ("requests", "get"),
    ]
    
    print("\nTesting dependencies...")
    for package, item in dependencies:
        try:
            if item:
                # Try to import specific item
                exec(f"from {package} import {item}")
            else:
                # Import the whole package
                __import__(package)
            print(f"  [OK] {package}")
        except ImportError as e:
            print(f"  [FAIL] {package}: {e}")
            return False
    
    return True

def test_database():
    """Test database functionality"""
    print("\nTesting database...")
    try:
        from homeauto.database.repository import DeviceRepository
        from homeauto.database.models import Device, DeviceStatus
        
        repo = DeviceRepository()
        
        # Test creating a mock device
        device = Device(
            id="test-001",
            device_type="gate",
            ip_address="192.168.1.100",
            mac_address="00:11:22:33:44:55",
            name="Test Gate",
            status=DeviceStatus.ONLINE,
            manufacturer="Hikvision",
            model="Test Model",
            confidence_score=0.9
        )
        
        # Save device
        repo.save(device)
        print("  [OK] Database repository created")
        
        # Retrieve device
        retrieved = repo.get("test-001")
        if retrieved:
            print(f"  [OK] Device retrieved: {retrieved.name}")
        else:
            print("  [FAIL] Failed to retrieve device")
            return False
            
        # Clean up - delete test device
        # Note: In production, you might want different cleanup logic
        
        return True
        
    except Exception as e:
        print(f"  [FAIL] Database test failed: {e}")
        return False

def test_gate_adapter():
    """Test HikGateDevice adapter"""
    print("\nTesting gate adapter...")
    try:
        from homeauto.devices.gate import HikGateDevice
        
        # Create a gate adapter with test credentials
        gate = HikGateDevice(
            ip="192.168.1.100",
            credentials={"username": "admin", "password": "test"}
        )
        
        print(f"  [OK] HikGateDevice created: {gate.ip}")
        
        # Test methods (these will fail without real device, but we can test structure)
        methods = ["test_connection", "get_info", "get_status", "open_gate", "close_gate"]
        for method in methods:
            if hasattr(gate, method):
                print(f"  [OK] Method available: {method}")
            else:
                print(f"  [FAIL] Method missing: {method}")
                return False
        
        return True
        
    except Exception as e:
        print(f"  [FAIL] Gate adapter test failed: {e}")
        return False

def test_web_api():
    """Test web API structure"""
    print("\nTesting web API...")
    try:
        from homeauto.web.api import app
        
        # Check FastAPI app
        if hasattr(app, "routes"):
            print(f"  [OK] FastAPI app has {len(app.routes)} routes")
            
            # List some important routes
            important_routes = ["/api/devices", "/api/gates/", "/health"]
            for route in important_routes:
                # Simple check if route pattern exists in any route path
                route_exists = any(route in str(r.path) for r in app.routes)
                if route_exists:
                    print(f"  [OK] Route pattern found: {route}")
                else:
                    print(f"  [WARN] Route pattern not found: {route}")
            
            return True
        else:
            print("  [FAIL] FastAPI app doesn't have routes attribute")
            return False
            
    except Exception as e:
        print(f"  [FAIL] Web API test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("=" * 60)
    print("Home Automation Project - Build Verification")
    print("=" * 60)
    
    tests = [
        ("Module Imports", test_imports),
        ("Dependencies", test_dependencies),
        ("Database", test_database),
        ("Gate Adapter", test_gate_adapter),
        ("Web API", test_web_api),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"  [FAIL] Test crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY:")
    print("=" * 60)
    
    all_passed = True
    for test_name, success in results:
        status = "PASS" if success else "FAIL"
        print(f"{test_name:20} {status}")
        if not success:
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("SUCCESS: All tests passed! Build is successful.")
        print("\nNext steps:")
        print("1. Configure your devices in config.yaml")
        print("2. Run: homeauto-scan --mock (to test with mock devices)")
        print("3. Run: python -m homeauto.web.api (to start web server)")
        print("4. Open http://localhost:8000 in your browser")
    else:
        print("FAILURE: Some tests failed. Please check the errors above.")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())
