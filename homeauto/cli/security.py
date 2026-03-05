"""
CLI command for camera security testing and dictionary attacks.
"""
import argparse
import sys
import time
from typing import List
from homeauto.devices.security import CameraSecurityTester
from homeauto.utils.logging_config import setup_logging, get_logger


def security_scan_command(args: List[str] = None) -> None:
    """CLI command for camera security scanning"""
    parser = argparse.ArgumentParser(
        description="Camera security scanning and penetration testing"
    )
    # Add verbose flag to main parser
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Enable verbose logging")
    subparsers = parser.add_subparsers(dest="command", help="Security command")
    
    # Bruteforce subcommand
    bruteforce_parser = subparsers.add_parser("bruteforce", help="Dictionary attack on camera")
    bruteforce_parser.add_argument("ip", help="Target camera IP address")
    bruteforce_parser.add_argument("--username-file", help="File containing usernames (one per line)")
    bruteforce_parser.add_argument("--password-file", help="File containing passwords (one per line)")
    bruteforce_parser.add_argument("--protocol", choices=["http", "rtsp", "onvif"], 
                                  default="http", help="Authentication protocol")
    bruteforce_parser.add_argument("--endpoint", default="/", help="HTTP endpoint to test")
    bruteforce_parser.add_argument("--workers", type=int, default=10, 
                                   help="Number of concurrent workers")
    bruteforce_parser.add_argument("--default-only", action="store_true",
                                   help="Only test default credentials")
    scan_parser = subparsers.add_parser("scan", help="Security scan of camera")
    scan_parser.add_argument("ip", help="Target camera IP address")
    scan_parser.add_argument("--port", type=int, default=80, help="Camera port")
    
    # Test subcommand
    test_parser = subparsers.add_parser("test", help="Test specific credentials")
    test_parser.add_argument("ip", help="Target camera IP address")
    test_parser.add_argument("username", help="Username to test")
    test_parser.add_argument("password", help="Password to test")
    test_parser.add_argument("--protocol", choices=["http", "rtsp", "onvif"], 
                            default="http", help="Authentication protocol")
    test_parser.add_argument("--endpoint", default="/", help="HTTP endpoint to test")
    
    if args is None:
        args = sys.argv[1:]
    
    parsed_args = parser.parse_args(args)
    
    # Setup logging
    setup_logging(verbose=parsed_args.verbose)
    logger = get_logger("cli.security")
    
    if parsed_args.command == "bruteforce":
        logger.info(f"Starting dictionary attack on {parsed_args.ip}")
        
        # Create security tester
        tester = CameraSecurityTester(parsed_args.ip)
        tester.max_workers = parsed_args.workers
        
        if parsed_args.default_only:
            print(f"Testing default credentials on {parsed_args.ip}...")
            credentials = tester.test_default_credentials()
            
            if credentials:
                print(f"\n[WARNING] DEFAULT CREDENTIALS FOUND:")
                for cred in credentials:
                    print(f"  - {cred['username']}:{cred['password']} ({cred['protocol']})")
            else:
                print("No default credentials found.")
                
        else:
            # Load wordlists
            if parsed_args.username_file:
                usernames = tester.load_wordlist(parsed_args.username_file)
            else:
                usernames = tester.generate_common_credentials()[0]
                
            if parsed_args.password_file:
                passwords = tester.load_wordlist(parsed_args.password_file)
            else:
                passwords = tester.generate_common_credentials()[1]
            
            print(f"Starting dictionary attack on {parsed_args.ip}")
            print(f"Usernames: {len(usernames)}, Passwords: {len(passwords)}")
            print(f"Total combinations: {len(usernames) * len(passwords)}")
            print(f"Protocol: {parsed_args.protocol}")
            print("-" * 50)
            
            credentials = tester.dictionary_attack(
                usernames, passwords, parsed_args.protocol, parsed_args.endpoint
            )
            
            if credentials:
                print(f"\n✅ VALID CREDENTIALS FOUND:")
                for cred in credentials:
                    print(f"  - {cred['username']}:{cred['password']}")
            else:
                print("\n❌ No valid credentials found.")
        
        # Generate security report
        print("\n" + "=" * 50)
        print("SECURITY REPORT")
        print("=" * 50)
        report = tester.get_security_report()
        
        print(f"Target: {report['target']}")
        print(f"Security Level: {report['security_level']}")
        print(f"Open Ports: {len(report['open_ports'])}")
        
        for port, service in report['open_ports'].items():
            print(f"  - {port}: {service}")
        
        if report['recommendations']:
            print("\nRecommendations:")
            for rec in report['recommendations']:
                print(f"  - {rec}")
        
    elif parsed_args.command == "scan":
        logger.info(f"Starting security scan on {parsed_args.ip}:{parsed_args.port}")
        
        tester = CameraSecurityTester(parsed_args.ip, parsed_args.port)
        report = tester.get_security_report()
        
        print("\n" + "=" * 60)
        print("CAMERA SECURITY SCAN REPORT")
        print("=" * 60)
        print(f"Target: {report['target']}")
        print(f"Scan Time: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(report['timestamp']))}")
        print(f"Security Level: {report['security_level']}")
        
        print(f"\nOpen Ports ({len(report['open_ports'])}):")
        if report['open_ports']:
            for port, service in report['open_ports'].items():
                print(f"  • {port}/TCP - {service}")
        else:
            print("  No open ports detected")
        
        print(f"\nDefault Credentials Test:")
        if report['default_credentials_test']:
            print("  ⚠️  DEFAULT CREDENTIALS FOUND!")
            for cred in report['default_credentials_test']:
                print(f"    - {cred['username']}:{cred['password']} ({cred['protocol']})")
        else:
            print("  ✓ No default credentials found")
        
        if report['recommendations']:
            print(f"\nSecurity Recommendations:")
            for i, rec in enumerate(report['recommendations'], 1):
                print(f"  {i}. {rec}")
        
        print("\n" + "=" * 60)
        
    elif parsed_args.command == "test":
        logger.info(f"Testing credentials on {parsed_args.ip}")
        
        tester = CameraSecurityTester(parsed_args.ip)
        
        if parsed_args.protocol == "http":
            result = tester.test_http_auth(parsed_args.username, parsed_args.password, parsed_args.endpoint)
        elif parsed_args.protocol == "rtsp":
            result = tester.test_rtsp_auth(parsed_args.username, parsed_args.password)
        else:  # onvif
            result = tester.test_onvif_auth(parsed_args.username, parsed_args.password)
        
        if result:
            print(f"\n✅ CREDENTIALS VALID!")
            print(f"  Username: {parsed_args.username}")
            print(f"  Password: {parsed_args.password}")
            print(f"  Protocol: {parsed_args.protocol}")
        else:
            print(f"\n❌ CREDENTIALS INVALID")
            print(f"  Username: {parsed_args.username}")
            print(f"  Password: {parsed_args.password}")
            print(f"  Protocol: {parsed_args.protocol}")
        
    else:
        parser.print_help()


if __name__ == "__main__":
    security_scan_command()
