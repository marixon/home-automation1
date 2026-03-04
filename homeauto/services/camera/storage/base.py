"""
Base storage backend interface for camera snapshots.
"""

import os
import json
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, BinaryIO, List
from datetime import datetime
from homeauto.utils.logging_config import get_logger


class StorageBackend(ABC):
    """Abstract base class for storage backends."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = get_logger(f"{__name__}.{self.__class__.__name__}")
        self.initialized = False
    
    @abstractmethod
    def initialize(self) -> bool:
        """Initialize the storage backend."""
        pass
    
    @abstractmethod
    def save(self, data: bytes, filename: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Save data to storage.
        
        Args:
            data: Binary data to save
            filename: Name of the file
            metadata: Optional metadata about the file
            
        Returns:
            Dict with save result including path, size, etc.
        """
        pass
    
    @abstractmethod
    def list_files(self, prefix: str = "", limit: int = 100) -> List[Dict[str, Any]]:
        """
        List files in storage.
        
        Args:
            prefix: Optional prefix to filter files
            limit: Maximum number of files to return
            
        Returns:
            List of file metadata dictionaries
        """
        pass
    
    @abstractmethod
    def delete(self, filename: str) -> bool:
        """
        Delete a file from storage.
        
        Args:
            filename: Name of the file to delete
            
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def get_file_info(self, filename: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a file.
        
        Args:
            filename: Name of the file
            
        Returns:
            File metadata or None if not found
        """
        pass
    
    def get_status(self) -> Dict[str, Any]:
        """Get storage backend status."""
        return {
            "type": self.__class__.__name__,
            "initialized": self.initialized,
            "config": {k: "***" if "password" in k.lower() or "key" in k.lower() else v 
                      for k, v in self.config.items()}
        }


class StorageManager:
    """Manages multiple storage backends."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = get_logger(__name__)
        self.backends: Dict[str, StorageBackend] = {}
        self.initialized = False
    
    def initialize(self) -> bool:
        """Initialize all configured storage backends."""
        try:
            for backend_name, backend_config in self.config.items():
                if not backend_config.get("enabled", False):
                    self.logger.debug(f"Storage backend '{backend_name}' is disabled")
                    continue
                
                backend_type = backend_config.get("type", backend_name)
                self.logger.info(f"Initializing storage backend: {backend_name} ({backend_type})")
                
                # Create backend instance based on type
                backend = self._create_backend(backend_type, backend_config)
                if backend and backend.initialize():
                    self.backends[backend_name] = backend
                    self.logger.info(f"Storage backend '{backend_name}' initialized successfully")
                else:
                    self.logger.error(f"Failed to initialize storage backend '{backend_name}'")
            
            self.initialized = len(self.backends) > 0
            return self.initialized
            
        except Exception as e:
            self.logger.error(f"Error initializing storage manager: {e}")
            return False
    
    def _create_backend(self, backend_type: str, config: Dict[str, Any]) -> Optional[StorageBackend]:
        """Create a storage backend instance based on type."""
        try:
            if backend_type == "local":
                from .local_storage import LocalStorage
                return LocalStorage(config)
            elif backend_type == "ftp":
                from .ftp_storage import FTPStorage
                return FTPStorage(config)
            elif backend_type == "sftp":
                from .sftp_storage import SFTPStorage
                return SFTPStorage(config)
            elif backend_type == "google_drive":
                from .google_drive_storage import GoogleDriveStorage
                return GoogleDriveStorage(config)
            else:
                self.logger.error(f"Unknown storage backend type: {backend_type}")
                return None
        except ImportError as e:
            self.logger.error(f"Failed to import backend '{backend_type}': {e}")
            return None
        except Exception as e:
            self.logger.error(f"Error creating backend '{backend_type}': {e}")
            return None
    
    def save_to_all(self, data: bytes, filename: str, metadata: Dict[str, Any] = None) -> Dict[str, Dict[str, Any]]:
        """
        Save data to all initialized storage backends.
        
        Args:
            data: Binary data to save
            filename: Name of the file
            metadata: Optional metadata about the file
            
        Returns:
            Dict mapping backend name to save result
        """
        if not self.initialized:
            self.logger.warning("Storage manager not initialized")
            return {}
        
        results = {}
        for backend_name, backend in self.backends.items():
            try:
                result = backend.save(data, filename, metadata)
                results[backend_name] = result
                self.logger.debug(f"Saved to '{backend_name}': {result.get('success', False)}")
            except Exception as e:
                self.logger.error(f"Error saving to backend '{backend_name}': {e}")
                results[backend_name] = {"success": False, "error": str(e)}
        
        return results
    
    def save_to_backend(self, backend_name: str, data: bytes, filename: str, 
                       metadata: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """
        Save data to a specific storage backend.
        
        Args:
            backend_name: Name of the backend
            data: Binary data to save
            filename: Name of the file
            metadata: Optional metadata about the file
            
        Returns:
            Save result or None if backend not found
        """
        if backend_name not in self.backends:
            self.logger.error(f"Storage backend '{backend_name}' not found")
            return None
        
        try:
            return self.backends[backend_name].save(data, filename, metadata)
        except Exception as e:
            self.logger.error(f"Error saving to backend '{backend_name}': {e}")
            return {"success": False, "error": str(e)}
    
    def list_all_files(self, prefix: str = "", limit: int = 100) -> Dict[str, List[Dict[str, Any]]]:
        """List files from all storage backends."""
        if not self.initialized:
            return {}
        
        results = {}
        for backend_name, backend in self.backends.items():
            try:
                files = backend.list_files(prefix, limit)
                results[backend_name] = files
            except Exception as e:
                self.logger.error(f"Error listing files from backend '{backend_name}': {e}")
                results[backend_name] = []
        
        return results
    
    def get_status(self) -> Dict[str, Any]:
        """Get status of all storage backends."""
        status = {
            "initialized": self.initialized,
            "backends": {}
        }
        
        for backend_name, backend in self.backends.items():
            status["backends"][backend_name] = backend.get_status()
        
        return status
    
    def cleanup(self):
        """Clean up resources."""
        for backend_name, backend in self.backends.items():
            try:
                # Some backends might have cleanup methods
                if hasattr(backend, 'cleanup'):
                    backend.cleanup()
            except Exception as e:
                self.logger.error(f"Error cleaning up backend '{backend_name}': {e}")
        
        self.backends.clear()
        self.initialized = False
