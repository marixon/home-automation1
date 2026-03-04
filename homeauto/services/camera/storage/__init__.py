"""
Storage backends for camera snapshots.
Supports local storage, FTP, SFTP, and Google Drive.
"""

from typing import Dict, Any, Optional, BinaryIO

__all__ = [
    "StorageBackend",
    "LocalStorage",
    "FTPStorage",
    "SFTPStorage",
    "GoogleDriveStorage",
    "StorageManager",
]
