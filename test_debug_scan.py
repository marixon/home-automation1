#!/usr/bin/env python3
"""Debug network scan issues"""

import sys
import time
import subprocess

# Add project root to path
sys.path.insert(0, '.')

def test_ping():
    """Test ping functionality directly"""
    print("Testing ping functionality...")
    
    # Test ping to localhost
    test_ip = "127.0.0.1"
    
    # Windows ping command
    command = ["ping", "-n", "1", "-w", "1000", test_ip]
    
    try:
        print(f"Running command: {' '.join(command)}")
        start_time = time.time()
        
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=2,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        
        elapsed = time.time() - start_time
        print(f"Ping completed in {elapsed:.2f} seconds")
        print(f"Return code: {result.returncode}")
        print(f"Success: {result.returncode == 0}")
        
        return result.returncode == 0
        
    except subprocess.TimeoutExpired:
        print("ERROR: Ping command timed out")
        return False
    except Exception as e:
        print(f"ERROR: {e}")
        return False

def test_parse_subnet():
    """Test subnet parsing"""
    print("\nTesting subnet parsing...")
    
    try:
        from homeauto.utils.network import parse_subnet
        
        subnet = "192.168.1.0/30"
        print(f"Parsing subnet: {subnet}")
        
        ips = parse_subnet(subnet)
        print(f"Generated {len(ips)} IP addresses:")
        for ip in ips:
            print(f"  {ip}")
        
        return True
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_scanner_direct():
    """Test scanner directly without threading"""
    print("\nTesting scanner directly...")
    
    try:
        from homeauto.discovery.scanner import NetworkScanner
        
        scanner = NetworkScanner(subnet='127.0.0.1/30', timeout=1, max_threads=2)
        
        print("Testing ping_host method directly...")
        test_ips = ['127.0.0.1', '127.0.0.2', '127.0.0.3']
        
        for ip in test_ips:
            print(f"  Pinging {ip}...")
            start_time = time.time()
            result = scanner.ping_host(ip)
            elapsed = time.time() - start_time
            print(f"    Result: {result}, Time: {elapsed:.2f}s")
        
        print("\nTesting scan_subnet method...")
        start_time = time.time()
        active_hosts = scanner.scan_subnet(max_workers=1)  # Use single thread
        elapsed = time.time() - start_time
        
        print(f"Scan completed in {elapsed:.2f} seconds")
        print(f"Found {len(active_hosts)} active hosts: {active_hosts}")
        
        return True
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Debugging network scan issues...")
    
    success = True
    
    # Test 1: Direct ping
    if not test_ping():
        success = False
    
    # Test 2: Subnet parsing
    if not test_parse_subnet():
        success = False
    
    # Test 3: Scanner direct test
    if not test_scanner_direct():
        success = False
    
    if success:
        print("\nAll tests passed!")
        sys.exit(0)
    else:
        print("\nSome tests failed!")
        sys.exit(1)
