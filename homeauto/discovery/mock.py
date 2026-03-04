import random
from typing import List, Dict
from dataclasses import dataclass


@dataclass
class MockDevice:
    device_type: str
    ip: str
    mac: str
    manufacturer: str = "Mock Manufacturer"
    model: str = "Mock Model"

    def is_online(self) -> bool:
        """Simulate device availability (90% online)"""
        return random.random() < 0.9

    def get_info(self) -> Dict:
        """Return device information"""
        return {
            "type": self.device_type,
            "ip": self.ip,
            "mac": self.mac,
            "manufacturer": self.manufacturer,
            "model": self.model,
        }

    def get_config(self) -> Dict:
        """Return mock configuration"""
        return {
            "name": f"Mock {self.device_type} {self.ip.split('.')[-1]}",
            "enabled": True,
        }


class MockDeviceGenerator:
    DEVICE_TYPES = [
        ("camera", "MockCam", "IP Camera X1"),
        ("sensor", "MockSensor", "TempHumid Pro"),
        ("gate", "MockGate", "Gate Controller"),
        ("switch", "MockSwitch", "Smart Switch"),
    ]

    def generate(self, count: int = 5, base_ip: str = "192.168.1") -> List[MockDevice]:
        """Generate mock devices with varied types"""
        devices = []

        for i in range(count):
            device_type, manufacturer, model = random.choice(self.DEVICE_TYPES)
            ip = f"{base_ip}.{100 + i}"
            mac = self._generate_mac()

            device = MockDevice(
                device_type=device_type,
                ip=ip,
                mac=mac,
                manufacturer=manufacturer,
                model=model,
            )
            devices.append(device)

        return devices

    def _generate_mac(self) -> str:
        """Generate random MAC address"""
        return ":".join([f"{random.randint(0, 255):02X}" for _ in range(6)])
