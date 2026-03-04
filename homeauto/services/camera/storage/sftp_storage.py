"""
SFTP storage backend for camera snapshots.
"""

import os
import json
import stat
from datetime import datetime
from typing import Dict, Any, List, Optional
from io import BytesIO
from .base import StorageBackend


class SFTPStorage(StorageBackend):
    """SFTP storage backend."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.host = config.get("host", "localhost")
        self.port = config.get("port", 22)
        self.username = config.get("username", "")
        self.password = config.get("password", "")
        self.private_key_path = config.get("private_key_path")
        self.remote_path = config.get("remote_path", "/")
        self.timeout = config.get("timeout", 30)
        
        self.sftp = None
        self.transport = None
    
    def initialize(self) -> bool:
        """Initialize SFTP connection."""
        try:
            import paramiko
            
            # Create SSH client
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            # Connect with appropriate authentication
            if self.private_key_path and os.path.exists(self.private_key_path):
                # Use private key authentication
                key = paramiko.RSAKey.from_private_key_file(self.private_key_path)
                ssh.connect(
                    self.host,
                    port=self.port,
                    username=self.username,
                    pkey=key,
                    timeout=self.timeout
                )
            else:
                # Use password authentication
                ssh.connect(
                    self.host,
                    port=self.port,
                    username=self.username,
                    password=self.password,
                    timeout=self.timeout
                )
            
            # Create SFTP client
            self.transport = ssh.get_transport()
            self.sftp = paramiko.SFTPClient.from_transport(self.transport)
            
            # Ensure remote path exists
            self._ensure_remote_path()
            
            self.initialized = True
            self.logger.info(f"SFTP storage initialized: {self.host}:{self.port}{self.remote_path}")
            return True
            
        except ImportError:
            self.logger.error("Paramiko not installed. Install with: pip install paramiko")
            return False
        except Exception as e:
            self.logger.error(f"Failed to initialize SFTP storage: {e}")
            self.sftp = None
            self.transport = None
            return False
    
    def _ensure_remote_path(self):
        """Ensure remote path exists on SFTP server."""
        try:
            self.sftp.chdir(self.remote_path)
        except IOError:
            # Directory doesn't exist, create it
            self.logger.info(f"Creating remote path: {self.remote_path}")
            self._create_directory(self.remote_path)
            self.sftp.chdir(self.remote_path)
    
    def _create_directory(self, path: str):
        """Create directory on SFTP server."""
        # Split path into components
        parts = path.strip('/').split('/')
        current_path = ""
        
        for part in parts:
            if not part:
                continue
                
            current_path = f"{current_path}/{part}" if current_path else part
            
            try:
                self.sftp.chdir(current_path)
            except IOError:
                try:
                    self.sftp.mkdir(current_path)
                    self.sftp.chdir(current_path)
                except Exception as e:
                    self.logger.error(f"Failed to create directory {current_path}: {e}")
                    raise
    
    def save(self, data: bytes, filename: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Save data to SFTP server."""
        if not self.sftp:
            return {"success": False, "error": "SFTP not initialized"}
        
        try:
            # Upload file
            remote_filepath = f"{self.remote_path}/{filename}"
            with self.sftp.open(remote_filepath, 'wb') as f:
                f.write(data)
            
            # Upload metadata if provided
            if metadata:
                metadata_filename = filename + ".meta"
                metadata_remote_path = f"{self.remote_path}/{metadata_filename}"
                metadata_json = json.dumps(metadata, indent=2).encode('utf-8')
                with self.sftp.open(metadata_remote_path, 'wb') as f:
                    f.write(metadata_json)
            
            # Get file stats
            file_stat = self.sftp.stat(remote_filepath)
            
            return {
                "success": True,
                "filename": filename,
                "remote_path": remote_filepath,
                "size": file_stat.st_size,
                "modified_at": datetime.fromtimestamp(file_stat.st_mtime).isoformat(),
                "metadata_saved": metadata is not None,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error saving file '{filename}' to SFTP: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def list_files(self, prefix: str = "", limit: int = 100) -> List[Dict[str, Any]]:
        """List files on SFTP server."""
        if not self.sftp:
            return []
        
        try:
            files = []
            file_list = self.sftp.listdir(self.remote_path)
            
            for filename in file_list:
                # Skip metadata files
                if filename.endswith('.meta'):
                    continue
                
                # Check prefix
                if prefix and not filename.startswith(prefix):
                    continue
                
                try:
                    remote_filepath = f"{self.remote_path}/{filename}"
                    file_stat = self.sftp.stat(remote_filepath)
                    
                    # Skip directories
                    if stat.S_ISDIR(file_stat.st_mode):
                        continue
                    
                    file_info = {
                        "filename": filename,
                        "size": file_stat.st_size,
                        "modified_at": datetime.fromtimestamp(file_stat.st_mtime).isoformat(),
                        "created_at": datetime.fromtimestamp(file_stat.st_ctime).isoformat(),
                        "remote_path": remote_filepath
                    }
                    
                    # Check for metadata file
                    metadata_filename = filename + ".meta"
                    if metadata_filename in file_list:
                        try:
                            metadata_remote_path = f"{self.remote_path}/{metadata_filename}"
                            with self.sftp.open(metadata_remote_path, 'r') as f:
                                metadata = json.load(f)
                            file_info["metadata"] = metadata
                        except Exception as e:
                            self.logger.debug(f"Failed to load metadata for {filename}: {e}")
                    
                    files.append(file_info)
                    
                    # Limit results
                    if len(files) >= limit:
                        break
                        
                except Exception as e:
                    self.logger.debug(f"Error getting info for file {filename}: {e}")
                    continue
            
            return files
            
        except Exception as e:
            self.logger.error(f"Error listing SFTP files: {e}")
            return []
    
    def delete(self, filename: str) -> bool:
        """Delete a file from SFTP server."""
        if not self.sftp:
            return False
        
        try:
            # Delete main file
            remote_filepath = f"{self.remote_path}/{filename}"
            self.sftp.remove(remote_filepath)
            
            # Delete metadata file if it exists
            metadata_filename = filename + ".meta"
            metadata_remote_path = f"{self.remote_path}/{metadata_filename}"
            try:
                self.sftp.remove(metadata_remote_path)
            except:
                pass  # Metadata file might not exist
            
            self.logger.info(f"Deleted file from SFTP: {filename}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error deleting file '{filename}' from SFTP: {e}")
            return False
    
    def get_file_info(self, filename: str) -> Optional[Dict[str, Any]]:
        """Get information about a file on SFTP server."""
        if not self.sftp:
            return None
        
        try:
            remote_filepath = f"{self.remote_path}/{filename}"
            
            # Check if file exists
            try:
                file_stat = self.sftp.stat(remote_filepath)
            except IOError:
                return None  # File doesn't exist
            
            # Skip if it's a directory
            if stat.S_ISDIR(file_stat.st_mode):
                return None
            
            file_info = {
                "filename": filename,
                "size": file_stat.st_size,
                "modified_at": datetime.fromtimestamp(file_stat.st_mtime).isoformat(),
                "created_at": datetime.fromtimestamp(file_stat.st_ctime).isoformat(),
                "remote_path": remote_filepath,
                "exists": True
            }
            
            # Check for metadata file
            metadata_filename = filename + ".meta"
            metadata_remote_path = f"{self.remote_path}/{metadata_filename}"
            try:
                with self.sftp.open(metadata_remote_path, 'r') as f:
                    metadata = json.load(f)
                file_info["metadata"] = metadata
            except:
                pass  # Metadata file might not exist
            
            return file_info
            
        except Exception as e:
            self.logger.error(f"Error getting file info for '{filename}' from SFTP: {e}")
            return None
    
    def cleanup(self):
        """Close SFTP connection."""
        if self.sftp:
            try:
                self.sftp.close()
            except:
                pass
            self.sftp = None
        
        if self.transport:
            try:
                self.transport.close()
            except:
                pass
            self.transport = None
        
        self.initialized = False
