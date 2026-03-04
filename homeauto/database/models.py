from datetime import datetime
from enum import Enum
from typing import Optional
from dataclasses import dataclass, field


class DeviceStatus(Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    UNKNOWN = "unknown"
    ERROR = "error"


@dataclass
class Device:
    id: str
    device_type: str
    ip_address: str
    mac_address: str
    name: str
    status: DeviceStatus
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    confidence_score: float = 0.0
    last_seen: datetime = field(default_factory=datetime.now)
    config: dict = field(default_factory=dict)
    metadata: dict = field(default_factory=dict)
