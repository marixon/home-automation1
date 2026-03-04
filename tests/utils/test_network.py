import pytest
from homeauto.utils.network import (
    is_valid_ip,
    is_valid_mac,
    parse_subnet,
    get_local_ip,
)


def test_is_valid_ip():
    assert is_valid_ip("192.168.1.1") is True
    assert is_valid_ip("192.168.1.256") is False
    assert is_valid_ip("not-an-ip") is False


def test_is_valid_mac():
    assert is_valid_mac("AA:BB:CC:DD:EE:FF") is True
    assert is_valid_mac("aa:bb:cc:dd:ee:ff") is True
    assert is_valid_mac("AA-BB-CC-DD-EE-FF") is True
    assert is_valid_mac("not-a-mac") is False


def test_parse_subnet():
    ips = parse_subnet("192.168.1.0/30")
    # /30 gives us 4 IPs: .0 (network), .1, .2, .3 (broadcast)
    assert len(ips) == 4
    assert "192.168.1.1" in ips
    assert "192.168.1.2" in ips


def test_get_local_ip():
    ip = get_local_ip()
    assert is_valid_ip(ip)
