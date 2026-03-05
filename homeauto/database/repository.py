import sqlite3
import json
from typing import Optional, List
from datetime import datetime
from homeauto.database.models import Device, DeviceStatus


class DeviceRepository:
    def __init__(self, db_path: str = "homeauto.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS devices (
                    id TEXT PRIMARY KEY,
                    device_type TEXT NOT NULL,
                    ip_address TEXT NOT NULL,
                    mac_address TEXT NOT NULL,
                    name TEXT NOT NULL,
                    status TEXT NOT NULL,
                    manufacturer TEXT,
                    model TEXT,
                    confidence_score REAL,
                    last_seen TEXT,
                    config TEXT,
                    metadata TEXT
                )
            """)
            conn.commit()

    def save(self, device: Device):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO devices
                (id, device_type, ip_address, mac_address, name, status,
                 manufacturer, model, confidence_score, last_seen, config, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    device.id,
                    device.device_type,
                    device.ip_address,
                    device.mac_address,
                    device.name,
                    device.status.value,
                    device.manufacturer,
                    device.model,
                    device.confidence_score,
                    device.last_seen.isoformat(),
                    json.dumps(device.config),
                    json.dumps(device.metadata),
                ),
            )
            conn.commit()

    def get(self, device_id: str) -> Optional[Device]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM devices WHERE id = ?", (device_id,))
            row = cursor.fetchone()
            if row:
                return self._row_to_device(row)
            return None

    def get_all(self) -> List[Device]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM devices ORDER BY last_seen DESC")
            return [self._row_to_device(row) for row in cursor.fetchall()]

    def get_by_type(self, device_type: str) -> List[Device]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM devices WHERE device_type = ? ORDER BY last_seen DESC",
                (device_type,),
            )
            return [self._row_to_device(row) for row in cursor.fetchall()]

    def delete(self, device_id: str) -> bool:
        """Delete a device from the database"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("DELETE FROM devices WHERE id = ?", (device_id,))
            conn.commit()
            return cursor.rowcount > 0

    def _row_to_device(self, row) -> Device:
        return Device(
            id=row["id"],
            device_type=row["device_type"],
            ip_address=row["ip_address"],
            mac_address=row["mac_address"],
            name=row["name"],
            status=DeviceStatus(row["status"]),
            manufacturer=row["manufacturer"],
            model=row["model"],
            confidence_score=row["confidence_score"],
            last_seen=datetime.fromisoformat(row["last_seen"]),
            config=json.loads(row["config"]),
            metadata=json.loads(row["metadata"]),
        )
