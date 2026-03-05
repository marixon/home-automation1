import requests
import time
import hashlib
import hmac
import json
import socket
import struct
from typing import Dict, Any, List, Optional
from homeauto.devices.base import BaseDevice, DeviceCapability
from homeauto.utils.retry import retry_with_backoff
from homeauto.utils.logging_config import get_device_logger


class TuyaDevice(BaseDevice):
    """Tuya smart device adapter with Local Control protocol support"""

    def __init__(self, ip: str, credentials: Dict[str, str]):
        super().__init__(ip, credentials)
        self.base_url = f"http://{ip}"
        self.api_key = credentials.get("api_key")
        self.secret = credentials.get("secret")
        self.device_id = credentials.get("device_id")
        self.local_key = credentials.get("local_key", "")
        self.timeout = 5
        self.logger = get_device_logger("tuya", ip)
        
        # Tuya Local Control protocol constants
        self.LOCAL_PORT = 6668
        self.PROTOCOL_VERSION = 3.3
        self.MESSAGE_HEADER = 0x000055AA
        self.MESSAGE_FOOTER = 0x0000AA55

    def _generate_signature(self, payload: str, timestamp: str) -> str:
        """Generate HMAC signature for Tuya Cloud API"""
        message = f"{self.api_key}{timestamp}{payload}"
        signature = (
            hmac.new(self.secret.encode(), message.encode(), hashlib.sha256)
            .hexdigest()
            .upper()
        )
        return signature

    def _encrypt_local_data(self, data: Dict[str, Any]) -> bytes:
        """Encrypt data for Tuya Local Control protocol"""
        import hashlib
        import base64
        
        if not self.local_key:
            return json.dumps(data).encode()
            
        # Simple XOR encryption (Tuya's basic local protocol)
        plaintext = json.dumps(data)
        key = self.local_key.encode()
        encrypted = bytearray()
        
        for i, char in enumerate(plaintext):
            encrypted.append(ord(char) ^ key[i % len(key)])
            
        return bytes(encrypted)

    def _decrypt_local_data(self, encrypted_data: bytes) -> Dict[str, Any]:
        """Decrypt data from Tuya Local Control protocol"""
        if not self.local_key:
            return json.loads(encrypted_data.decode())
            
        key = self.local_key.encode()
        decrypted = bytearray()
        
        for i, byte in enumerate(encrypted_data):
            decrypted.append(byte ^ key[i % len(key)])
            
        return json.loads(decrypted.decode())

    def _send_local_command(self, command: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Send command via Tuya Local Control protocol"""
        try:
            # Create socket connection
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            sock.connect((self.ip, self.LOCAL_PORT))
            
            # Encrypt and send command
            encrypted_data = self._encrypt_local_data(command)
            
            # Build Tuya protocol packet
            packet = struct.pack('>I', self.MESSAGE_HEADER)
            packet += struct.pack('>I', len(encrypted_data) + 32)  # Total length
            packet += struct.pack('>I', 0)  # Reserved
            packet += struct.pack('>I', 0)  # Reserved
            packet += struct.pack('>I', 0)  # Reserved
            packet += struct.pack('>I', 0)  # Reserved
            packet += struct.pack('>I', 0)  # Reserved
            packet += struct.pack('>I', 0)  # Reserved
            packet += struct.pack('>I', 0)  # Reserved
            packet += encrypted_data
            packet += struct.pack('>I', self.MESSAGE_FOOTER)
            
            sock.sendall(packet)
            
            # Receive response
            response = sock.recv(1024)
            sock.close()
            
            if len(response) >= 40:  # Minimum valid response size
                # Parse response
                data_start = 32  # Skip header
                data_end = len(response) - 4  # Skip footer
                encrypted_response = response[data_start:data_end]
                
                if encrypted_response:
                    return self._decrypt_local_data(encrypted_response)
                    
        except Exception as e:
            self.logger.error(f"Local command failed: {e}")
            
        return None

    @retry_with_backoff(max_attempts=3, base_delay=1.0)
    def test_connection(self) -> bool:
        """Test device connectivity using both cloud and local methods"""
        self.logger.debug("Testing Tuya device connection")
        
        # Try local connection first (faster)
        if self.local_key:
            try:
                local_status = self._send_local_command({"gwId": self.device_id, "devId": self.device_id})
                if local_status and local_status.get("dps"):
                    self.logger.debug("Local connection successful")
                    return True
            except Exception as e:
                self.logger.debug(f"Local connection failed: {e}")
        
        # Fall back to cloud API
        try:
            timestamp = str(int(time.time() * 1000))
            payload = ""
            signature = self._generate_signature(payload, timestamp)

            headers = {
                "client_id": self.api_key,
                "sign": signature,
                "t": timestamp,
                "sign_method": "HMAC-SHA256",
            }

            response = requests.post(
                f"{self.base_url}/v1.0/devices/{self.device_id}/commands",
                headers=headers,
                json={"commands": []},
                timeout=self.timeout,
            )
            
            success = response.status_code == 200
            self.logger.debug(f"Cloud connection: {success}")
            return success
        except Exception as e:
            self.logger.error(f"Connection test failed: {e}")
            return False

    @retry_with_backoff(max_attempts=3)
    def get_info(self) -> Dict[str, Any]:
        """Get device information"""
        info = {
            "type": "tuya",
            "ip": self.ip,
            "device_id": self.device_id,
            "model": "Tuya Smart Device",
            "protocol": "local" if self.local_key else "cloud",
            "capabilities": [cap.value for cap in self.get_capabilities()]
        }
        
        # Try to get more detailed info from local protocol
        if self.local_key:
            try:
                local_info = self._send_local_command({
                    "gwId": self.device_id,
                    "devId": self.device_id,
                    "uid": "",
                    "t": int(time.time())
                })
                if local_info:
                    info.update({
                        "local_protocol": True,
                        "device_info": local_info.get("dps", {})
                    })
            except Exception:
                pass
                
        return info

    @retry_with_backoff(max_attempts=3)
    def get_status(self) -> Dict[str, Any]:
        """Get device status using local protocol if available"""
        self.logger.debug("Getting Tuya device status")
        
        # Try local protocol first
        if self.local_key:
            try:
                command = {
                    "gwId": self.device_id,
                    "devId": self.device_id,
                    "uid": "",
                    "t": int(time.time())
                }
                
                local_status = self._send_local_command(command)
                if local_status and local_status.get("dps"):
                    self.logger.debug(f"Local status: {local_status}")
                    return {
                        "online": True,
                        "protocol": "local",
                        "dps": local_status.get("dps", {}),
                        "timestamp": time.time()
                    }
            except Exception as e:
                self.logger.debug(f"Local status failed: {e}")
        
        # Fall back to cloud API
        try:
            timestamp = str(int(time.time() * 1000))
            payload = ""
            signature = self._generate_signature(payload, timestamp)

            headers = {
                "client_id": self.api_key,
                "sign": signature,
                "t": timestamp,
                "sign_method": "HMAC-SHA256",
            }

            response = requests.get(
                f"{self.base_url}/v1.0/devices/{self.device_id}/status",
                headers=headers,
                timeout=self.timeout,
            )

            if response.status_code == 200:
                data = response.json()
                self.logger.debug(f"Cloud status: {data}")
                return {
                    "online": True,
                    "protocol": "cloud",
                    **data.get("result", {})
                }
        except Exception as e:
            self.logger.error(f"Status check failed: {e}")

        return {"online": False, "protocol": "unknown"}

    def control(self, commands: Dict[str, Any]) -> bool:
        """Send control commands to device using local protocol if available"""
        self.logger.debug(f"Sending Tuya control commands: {commands}")
        
        # Try local protocol first
        if self.local_key:
            try:
                # Convert commands to Tuya DPS format
                dps_commands = {}
                for i, (code, value) in enumerate(commands.items(), 1):
                    dps_commands[str(i)] = value
                
                command = {
                    "gwId": self.device_id,
                    "devId": self.device_id,
                    "uid": "",
                    "t": int(time.time()),
                    "dps": dps_commands
                }
                
                response = self._send_local_command(command)
                if response and response.get("dps"):
                    self.logger.debug(f"Local control successful: {response}")
                    return True
            except Exception as e:
                self.logger.debug(f"Local control failed: {e}")
        
        # Fall back to cloud API
        try:
            timestamp = str(int(time.time() * 1000))
            payload = ""
            signature = self._generate_signature(payload, timestamp)

            headers = {
                "client_id": self.api_key,
                "sign": signature,
                "t": timestamp,
                "sign_method": "HMAC-SHA256",
            }

            response = requests.post(
                f"{self.base_url}/v1.0/devices/{self.device_id}/commands",
                headers=headers,
                json={
                    "commands": [{"code": k, "value": v} for k, v in commands.items()]
                },
                timeout=self.timeout,
            )

            success = response.status_code == 200 and response.json().get("success", False)
            self.logger.debug(f"Cloud control: {success}")
            return success
        except Exception as e:
            self.logger.error(f"Control failed: {e}")
            return False

    def get_capabilities(self) -> List[DeviceCapability]:
        """Get device capabilities"""
        capabilities = [
            DeviceCapability.STATUS,
            DeviceCapability.CONTROL,
            DeviceCapability.CONFIG,
        ]
        
        # Add discovery capability if local key is available
        if self.local_key:
            capabilities.append(DeviceCapability.DISCOVERY)
            
        return capabilities

    def discover_local_devices(self) -> List[Dict[str, Any]]:
        """Discover Tuya devices on local network using broadcast"""
        if not self.local_key:
            return []
            
        try:
            # Create broadcast socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.settimeout(2)
            
            # Tuya discovery message
            discovery_msg = json.dumps({
                "gwId": "",
                "devId": "",
                "uid": "",
                "t": int(time.time())
            }).encode()
            
            # Send broadcast
            sock.sendto(discovery_msg, ('255.255.255.255', self.LOCAL_PORT))
            
            # Listen for responses
            devices = []
            start_time = time.time()
            
            while time.time() - start_time < 2:  # Listen for 2 seconds
                try:
                    data, addr = sock.recvfrom(1024)
                    if data:
                        try:
                            device_info = json.loads(data.decode())
                            devices.append({
                                "ip": addr[0],
                                "port": addr[1],
                                "info": device_info
                            })
                        except:
                            pass
                except socket.timeout:
                    break
                    
            sock.close()
            return devices
            
        except Exception as e:
            self.logger.error(f"Discovery failed: {e}")
            return []
