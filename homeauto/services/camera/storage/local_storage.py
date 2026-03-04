"""
Local file system storage backend for camera snapshots.
"""

import os
import json
import shutil
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path
from .base import StorageBackend


class LocalStorage(StorageBackend):
    """Local file system storage backend."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.base_path = config.get("base_path", "/var/camera_snapshots")
        self.organization = config.get("organization", "by_date")  # by_date, by_camera, flat
        self.max_files = config.get("max_files", 1000)
        self.max_age_days = config.get("max_age_days", 30)
        
        # Create base directory if it doesn't exist
        os.makedirs(self.base_path, exist_ok=True)
    
    def initialize(self) -> bool:
        """Initialize local storage."""
        try:
            # Ensure base directory exists and is writable
            test_file = os.path.join(self.base_path, ".test_write")
            with open(test_file, 'w') as f:
                f.write("test")
            os.remove(test_file)
            
            self.initialized = True
            self.logger.info(f"Local storage initialized at {self.base_path}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize local storage: {e}")
            return False
    
    def _get_file_path(self, filename: str, metadata: Dict[str, Any] = None) -> str:
        """Get the full file path based on organization strategy."""
        if self.organization == "flat":
            return os.path.join(self.base_path, filename)
        
        elif self.organization == "by_date":
            # Organize by date: YYYY/MM/DD/filename
            if metadata and "timestamp" in metadata:
                dt = datetime.fromisoformat(metadata["timestamp"]) if isinstance(metadata["timestamp"], str) else metadata["timestamp"]
            else:
                dt = datetime.now()
            
            date_path = dt.strftime("%Y/%m/%d")
            full_path = os.path.join(self.base_path, date_path, filename)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            return full_path
        
        elif self.organization == "by_camera":
            # Organize by camera: camera_name/YYYY/MM/DD/filename
            camera_name = metadata.get("camera_name", "unknown") if metadata else "unknown"
            camera_name = camera_name.replace(" ", "_").lower()
            
            if metadata and "timestamp" in metadata:
                dt = datetime.fromisoformat(metadata["timestamp"]) if isinstance(metadata["timestamp"], str) else metadata["timestamp"]
            else:
                dt = datetime.now()
            
            date_path = dt.strftime("%Y/%m/%d")
            full_path = os.path.join(self.base_path, camera_name, date_path, filename)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            return full_path
        
        else:
            # Default to flat organization
            return os.path.join(self.base_path, filename)
    
    def save(self, data: bytes, filename: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Save data to local file system."""
        try:
            file_path = self._get_file_path(filename, metadata)
            
            # Write file
            with open(file_path, 'wb') as f:
                f.write(data)
            
            # Get file stats
            file_size = len(data)
            created_time = datetime.now().isoformat()
            
            # Create metadata file if metadata provided
            if metadata:
                metadata_file = file_path + ".meta"
                metadata_to_save = {
                    **metadata,
                    "file_size": file_size,
                    "created_at": created_time,
                    "file_path": file_path
                }
                with open(metadata_file, 'w') as f:
                    json.dump(metadata_to_save, f, indent=2)
            
            # Perform cleanup if needed
            self._cleanup_old_files()
            
            return {
                "success": True,
                "file_path": file_path,
                "file_size": file_size,
                "created_at": created_time,
                "metadata_saved": metadata is not None
            }
            
        except Exception as e:
            self.logger.error(f"Error saving file '{filename}': {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def list_files(self, prefix: str = "", limit: int = 100) -> List[Dict[str, Any]]:
        """List files in local storage."""
        try:
            files = []
            
            # Walk through directory tree
            for root, dirs, filenames in os.walk(self.base_path):
                for filename in filenames:
                    # Skip metadata files
                    if filename.endswith('.meta'):
                        continue
                    
                    # Check prefix
                    if prefix and not filename.startswith(prefix):
                        continue
                    
                    file_path = os.path.join(root, filename)
                    rel_path = os.path.relpath(file_path, self.base_path)
                    
                    # Get file info
                    stat = os.stat(file_path)
                    file_info = {
                        "filename": filename,
                        "path": rel_path,
                        "full_path": file_path,
                        "size": stat.st_size,
                        "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                        "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat()
                    }
                    
                    # Try to load metadata
                    metadata_file = file_path + ".meta"
                    if os.path.exists(metadata_file):
                        try:
                            with open(metadata_file, 'r') as f:
                                metadata = json.load(f)
                            file_info["metadata"] = metadata
                        except Exception as e:
                            self.logger.debug(f"Failed to load metadata for {file_path}: {e}")
                    
                    files.append(file_info)
                    
                    # Limit results
                    if len(files) >= limit:
                        break
                
                if len(files) >= limit:
                    break
            
            # Sort by creation time (newest first)
            files.sort(key=lambda x: x.get("created_at", ""), reverse=True)
            
            return files
            
        except Exception as e:
            self.logger.error(f"Error listing files: {e}")
            return []
    
    def delete(self, filename: str) -> bool:
        """Delete a file from local storage."""
        try:
            # Find the file (could be in subdirectories based on organization)
            for root, dirs, filenames in os.walk(self.base_path):
                if filename in filenames:
                    file_path = os.path.join(root, filename)
                    
                    # Delete the file
                    os.remove(file_path)
                    
                    # Delete metadata file if it exists
                    metadata_file = file_path + ".meta"
                    if os.path.exists(metadata_file):
                        os.remove(metadata_file)
                    
                    self.logger.info(f"Deleted file: {file_path}")
                    return True
            
            self.logger.warning(f"File not found: {filename}")
            return False
            
        except Exception as e:
            self.logger.error(f"Error deleting file '{filename}': {e}")
            return False
    
    def get_file_info(self, filename: str) -> Optional[Dict[str, Any]]:
        """Get information about a file."""
        try:
            # Find the file
            for root, dirs, filenames in os.walk(self.base_path):
                if filename in filenames:
                    file_path = os.path.join(root, filename)
                    
                    # Get file stats
                    stat = os.stat(file_path)
                    file_info = {
                        "filename": filename,
                        "path": os.path.relpath(file_path, self.base_path),
                        "full_path": file_path,
                        "size": stat.st_size,
                        "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                        "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        "exists": True
                    }
                    
                    # Try to load metadata
                    metadata_file = file_path + ".meta"
                    if os.path.exists(metadata_file):
                        try:
                            with open(metadata_file, 'r') as f:
                                metadata = json.load(f)
                            file_info["metadata"] = metadata
                        except Exception as e:
                            self.logger.debug(f"Failed to load metadata: {e}")
                    
                    return file_info
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting file info for '{filename}': {e}")
            return None
    
    def _cleanup_old_files(self):
        """Clean up old files based on max_age_days and max_files."""
        try:
            if not self.max_age_days and not self.max_files:
                return
            
            # Get all files with their creation times
            files = []
            for root, dirs, filenames in os.walk(self.base_path):
                for filename in filenames:
                    if filename.endswith('.meta'):
                        continue
                    
                    file_path = os.path.join(root, filename)
                    stat = os.stat(file_path)
                    files.append({
                        "path": file_path,
                        "created": datetime.fromtimestamp(stat.st_ctime),
                        "size": stat.st_size
                    })
            
            # Sort by creation time (oldest first)
            files.sort(key=lambda x: x["created"])
            
            # Remove files older than max_age_days
            if self.max_age_days:
                cutoff_date = datetime.now() - timedelta(days=self.max_age_days)
                for file_info in files[:]:
                    if file_info["created"] < cutoff_date:
                        try:
                            os.remove(file_info["path"])
                            # Remove metadata file if exists
                            metadata_file = file_info["path"] + ".meta"
                            if os.path.exists(metadata_file):
                                os.remove(metadata_file)
                            files.remove(file_info)
                            self.logger.debug(f"Cleaned up old file: {file_info['path']}")
                        except Exception as e:
                            self.logger.error(f"Error cleaning up file {file_info['path']}: {e}")
            
            # Remove files if exceeding max_files
            if self.max_files and len(files) > self.max_files:
                files_to_remove = files[:len(files) - self.max_files]
                for file_info in files_to_remove:
                    try:
                        os.remove(file_info["path"])
                        # Remove metadata file if exists
                        metadata_file = file_info["path"] + ".meta"
                        if os.path.exists(metadata_file):
                            os.remove(metadata_file)
                        self.logger.debug(f"Cleaned up excess file: {file_info['path']}")
                    except Exception as e:
                        self.logger.error(f"Error cleaning up file {file_info['path']}: {e}")
                        
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")


# Import timedelta for cleanup method
from datetime import timedelta
