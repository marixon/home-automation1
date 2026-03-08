#!/usr/bin/env python3
"""Verify that the scan command works correctly"""

import sys
import os
import subprocess

def clear_cache():
    """Clear Python cache files"""
    print("Clearing Python cache...")
    try:
        # Remove __pycache__ directories
        for root, dirs, files in os.walk('.'):
            if '__pycache__' in dirs:
                cache_dir = os.path.join(root, '__pycache__')
                try:
                    import shutil
                    shutil.rmtree(cache_dir)
                    print(f"  Removed: {cache_dir}")
                except Exception as e:
                    print(f"  Error removing {cache_dir}: {e}")
        print("Cache cleared successfully")
        return True
    except Exception as e:
        print(f"Error clearing cache: {e}")
        return False

def test_network_scanner():
    """Test NetworkScanner class directly"""
    print("\nTesting NetworkScanner class...")
    try:
        import sys
        sys.path.insert(0, '.')
        
        from homeauto.discovery.scanner import NetworkScanner
        
        # Test 1: Check constructor accepts max_threads
        print("  Test 1: Creating scanner with max_threads=2...")
        scanner = NetworkScanner(subnet='127.0.0.1/30', timeout=1, max_threads=2)
        print(f"    SUCCESS: Scanner created with max_threads={scanner.max_threads}")
        
        # Test 2: Check scan works
        print("  Test 2: Testing scan functionality...")
        devices = scanner.scan()
        print(f"    SUCCESS: Found {len(devices)} devices")
        
        return True
        
    except TypeError as e:
        print(f"    ERROR: {e}")
        return False
    except Exception as e:
        print(f"    ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_cli_command():
    """Test CLI command"""
    print("\nTesting CLI command...")
    try:
        # Test with small subnet
        cmd = [
            sys.executable, '-m', 'homeauto.cli.scan',
            'network',
            '-s', '127.0.0.1/30',
            '-m', '2',
            '-t', '1'
        ]
        
        print(f"  Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            print("  SUCCESS: CLI command executed successfully")
            print(f"  Output:\n{result.stdout[:500]}...")  # Show first 500 chars
            return True
        else:
            print(f"  ERROR: CLI command failed with code {result.returncode}")
            print(f"  Stderr: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print("  ERROR: CLI command timed out")
        return False
    except Exception as e:
        print(f"  ERROR: {e}")
        return False

def main():
    print("=" * 60)
    print("Verifying Scan Command Fix")
    print("=" * 60)
    
    success = True
    
    # Step 1: Clear cache
    if not clear_cache():
        print("Warning: Could not clear cache, continuing anyway...")
    
    # Step 2: Test NetworkScanner class
    if not test_network_scanner():
        success = False
    
    # Step 3: Test CLI command
    if not test_cli_command():
        success = False
    
    print("\n" + "=" * 60)
    if success:
        print("✅ ALL TESTS PASSED!")
        print("\nThe scan command is now working correctly.")
        print("\nRecommended usage:")
        print("  python -m homeauto.cli.scan network -s 192.168.1.0/24 -m 50 -t 1")
        print("  python -m homeauto.cli.scan network -s 192.168.1.0/24 -m 20 -t 2 --save")
    else:
        print("❌ SOME TESTS FAILED")
        print("\nPlease try these steps:")
        print("1. Clear Python cache: del /s /q __pycache__")
        print("2. Reinstall package: pip install -e . --force-reinstall")
        print("3. Restart your terminal/IDE")
    
    print("=" * 60)
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
