#!/usr/bin/env python3
"""Simple test to debug scan timeout"""

import sys
import time
import threading

# Add project root to path
sys.path.insert(0, '.')

def test_scan():
    try:
        print("Importing NetworkScanner...")
        from homeauto.discovery.scanner import NetworkScanner
        
        print("Creating scanner with small subnet...")
        scanner = NetworkScanner(subnet='192.168.1.0/30', timeout=1, max_threads=2)
        
        print(f"Scanner created: subnet={scanner.subnet}, timeout={scanner.timeout}, max_threads={scanner.max_threads}")
        
        print("\nStarting scan...")
        start_time = time.time()
        
        # Run scan in a thread with timeout
        result = []
        scan_thread = threading.Thread(target=lambda: result.extend(scanner.scan()))
        scan_thread.daemon = True
        scan_thread.start()
        
        # Wait with timeout
        scan_thread.join(timeout=10)
        
        if scan_thread.is_alive():
            print("ERROR: Scan timed out after 10 seconds!")
            return False
        else:
            elapsed = time.time() - start_time
            print(f"Scan completed in {elapsed:.2f} seconds")
            print(f"Found {len(result)} devices")
            return True
            
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Testing network scan...")
    success = test_scan()
    sys.exit(0 if success else 1)
