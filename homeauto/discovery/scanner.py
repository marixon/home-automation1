import os
import platform
import socket
from typing import List, Dict
from concurrent.futures import ThreadPoolExecutor, as_completed
from homeauto.utils.network import parse_subnet, get_local_ip


class NetworkScanner:
    def __init__(self, subnet: str = None, timeout: int = 1):
        self.subnet = subnet or self._get_default_subnet()
        self.timeout = timeout

    def _get_default_subnet(self) -> str:
        """Get default subnet based on local IP"""
        local_ip = get_local_ip()
        # Assume /24 subnet
        parts = local_ip.split('.')
        return f"{parts[0]}.{parts[1]}.{parts[2]}.0/24"

    def ping_host(self, ip: str) -> bool:
        """Ping a host to check if it's alive"""
        param = '-n' if platform.system().lower() == 'windows' else '-c'
        command = f"ping {param} 1 -w {self.timeout * 1000} {ip}"

        # Redirect output to null
        null_device = 'NUL' if platform.system().lower() == 'windows' else '/dev/null'
        command = f"{command} > {null_device} 2>&1"

        return os.system(command) == 0

    def scan_subnet(self, max_workers: int = 50) -> List[str]:
        """Scan subnet for active hosts"""
        ips = parse_subnet(self.subnet)
        active_hosts = []

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_ip = {executor.submit(self.ping_host, ip): ip for ip in ips}

            for future in as_completed(future_to_ip):
                ip = future_to_ip[future]
                try:
                    if future.result():
                        active_hosts.append(ip)
                except Exception:
                    pass

        return active_hosts

    def get_mac_address(self, ip: str) -> str:
        """Get MAC address for an IP (placeholder - would use ARP)"""
        # This is a simplified version - real implementation would use ARP tables
        # For now, return a placeholder
        return "00:00:00:00:00:00"

    def scan_ports(self, ip: str, ports: List[int]) -> List[int]:
        """Scan specific ports on a host"""
        open_ports = []

        for port in ports:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(self.timeout)
                result = sock.connect_ex((ip, port))
                sock.close()

                if result == 0:
                    open_ports.append(port)
            except Exception:
                pass

        return open_ports
