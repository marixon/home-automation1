#!/usr/bin/env python3
"""Test script to debug the scan command issue"""

import sys
import traceback

# Add project root to path
sys.path.insert(0, '.')

try:
    print("Testing NetworkScanner import...")
    from homeauto.discovery.scanner import NetworkScanner
    
    print("Creating scanner with max_threads=2...")
    scanner = NetworkScanner(subnet='127.0.0.1/30', timeout=1, max_threads=2)
    print(f"Scanner created successfully: {scanner}")
    print(f"Scanner max_threads: {scanner.max_threads}")
    
    print("\nTesting CLI command import...")
    from homeauto.cli.scan import ScanCommand
    
    print("Creating ScanCommand instance...")
    cmd = ScanCommand(config_path="config.yaml", verbose=False)
    
    print("Testing scan_network method...")
    result = cmd.scan_network(subnet='127.0.0.1/30', timeout=1, max_threads=2, save=False)
    print(f"Scan result: {result}")
    
except Exception as e:
    print(f"\nERROR: {e}")
    traceback.print_exc()
    sys.exit(1)
