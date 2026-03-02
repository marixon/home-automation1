import socket
import ipaddress
from typing import List


def is_valid_ip(ip: str) -> bool:
    """Check if string is a valid IP address"""
    try:
        ipaddress.ip_address(ip)
        return True
    except ValueError:
        return False


def is_valid_mac(mac: str) -> bool:
    """Check if string is a valid MAC address"""
    # Remove common separators and check format
    mac_clean = mac.replace(":", "").replace("-", "").upper()
    if len(mac_clean) != 12:
        return False

    try:
        int(mac_clean, 16)
        return True
    except ValueError:
        return False


def parse_subnet(subnet: str) -> List[str]:
    """Parse subnet and return list of IP addresses"""
    try:
        network = ipaddress.ip_network(subnet, strict=False)
        return [str(ip) for ip in network.hosts()] + [
            str(network.network_address),
            str(network.broadcast_address),
        ]
    except ValueError:
        return []


def get_local_ip() -> str:
    """Get local IP address of this machine"""
    try:
        # Connect to external host (doesn't actually send data)
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception:
        return "127.0.0.1"
