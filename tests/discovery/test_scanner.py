import pytest
from unittest.mock import patch, MagicMock
from homeauto.discovery.scanner import NetworkScanner


def test_scanner_initialization():
    scanner = NetworkScanner(subnet="192.168.1.0/24")
    assert scanner.subnet == "192.168.1.0/24"


@patch('homeauto.discovery.scanner.os.system')
def test_ping_host(mock_system):
    scanner = NetworkScanner()

    # Mock successful ping
    mock_system.return_value = 0
    assert scanner.ping_host("192.168.1.1") is True

    # Mock failed ping
    mock_system.return_value = 1
    assert scanner.ping_host("192.168.1.1") is False


@patch('homeauto.discovery.scanner.NetworkScanner.ping_host')
def test_scan_subnet(mock_ping):
    # Mock ping results: first 3 IPs respond
    mock_ping.side_effect = [True, True, True] + [False] * 250

    scanner = NetworkScanner(subnet="192.168.1.0/28")  # Small subnet for testing
    active_hosts = scanner.scan_subnet()

    assert len(active_hosts) == 3
