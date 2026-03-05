"""
Storage backends for camera snapshots.
Supports local storage, FTP, SFTP, and Google Drive.
"""

from typing import Dict, Any, Optional, BinaryIO

from .base import StorageBackend, StorageManager
from .local_storage import LocalStorage
from .ftp_storage import FTPStorage
from .sftp_storage import SFTPStorage
from .google_drive_storage import GoogleDriveStorage

__all__ = [
    "StorageBackend",
    "StorageManager",
    "LocalStorage",
    "FTPStorage",
    "SFTPStorage",
    "GoogleDriveStorage",
]
