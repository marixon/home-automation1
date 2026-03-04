from typing import List, Dict, Tuple


class DeviceIdentifier:
    # Port-based identification
    PORT_SIGNATURES = {
        "camera": [554, 8000, 8080],  # RTSP, common camera ports
        "gate": [8000, 9000],
        "sensor": [6668],  # Tuya
        "switch": [6668],  # Tuya
    }

    # Manufacturer-based identification
    MANUFACTURER_TYPES = {
        "Hikvision": "camera",
        "Dahua": "camera",
        "Tuya": "sensor",  # Can also be switch
        "Hik": "gate",
    }

    def identify_by_ports(self, open_ports: List[int]) -> str:
        """Identify device type by open ports"""
        for device_type, signature_ports in self.PORT_SIGNATURES.items():
            if any(port in open_ports for port in signature_ports):
                return device_type

        return "unknown"

    def identify_by_manufacturer(self, manufacturer: str) -> str:
        """Identify device type by manufacturer"""
        for mfr, device_type in self.MANUFACTURER_TYPES.items():
            if mfr.lower() in manufacturer.lower():
                return device_type

        return "unknown"

    def calculate_confidence(self, signals: Dict[str, bool]) -> float:
        """Calculate confidence score based on identification signals"""
        weights = {
            "port_match": 0.3,
            "manufacturer_match": 0.3,
            "api_probe": 0.4,
        }

        confidence = 0.0
        for signal, weight in weights.items():
            if signals.get(signal, False):
                confidence += weight

        return confidence

    def identify(
        self, ip: str, mac: str, open_ports: List[int], manufacturer: str = None
    ) -> Tuple[str, float]:
        """
        Identify device type and calculate confidence score

        Returns:
            Tuple of (device_type, confidence_score)
        """
        signals = {
            "port_match": False,
            "manufacturer_match": False,
            "api_probe": False,  # Placeholder for future API probing
        }

        # Try port-based identification
        port_type = self.identify_by_ports(open_ports)
        if port_type != "unknown":
            signals["port_match"] = True
            device_type = port_type
        else:
            device_type = "unknown"

        # Try manufacturer-based identification
        if manufacturer:
            mfr_type = self.identify_by_manufacturer(manufacturer)
            if mfr_type != "unknown":
                signals["manufacturer_match"] = True
                # Manufacturer signal can override port detection
                if device_type == "unknown":
                    device_type = mfr_type

        confidence = self.calculate_confidence(signals)

        return device_type, confidence
