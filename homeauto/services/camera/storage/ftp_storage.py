"""
FTP storage backend for camera snapshots.
"""

import os
import json
import ftplib
from datetime import datetime
from typing import Dict, Any, List, Optional
from io import BytesIO
from .base import StorageBackend


class FTPStorage(StorageBackend):
    """FTP storage backend."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.host = config.get("host", "localhost")
        self.port = config.get("port", 21)
        self.username = config.get("username", "")
        self.password = config.get("password", "")
        self.remote_path = config.get("remote_path", "/")
        self.timeout = config.get("timeout", 30)
        self.passive_mode = config.get("passive_mode", True)
        
        self.ftp = None
    
    def initialize(self) -> bool:
        """Initialize FTP connection."""
        try:
            self.ftp = ftplib.FTP()
            self.ftp.connect(self.host, self.port, timeout=self.timeout)
            self.ftp.login(self.username, self.password)
            
            if self.passive_mode:
                self.ftp.set_pasv(True)
            
            # Change to remote path, create if it doesn't exist
            self._ensure_remote_path()
            
            self.initialized = True
            self.logger.info(f"FTP storage initialized: {self.host}:{self.port}{self.remote_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize FTP storage: {e}")
            self.ftp = None
            return False
    
    def _ensure_remote_path(self):
        """Ensure remote path exists on FTP server."""
        try:
            # Try to change to the directory
            self.ftp.cwd(self.remote_path)
        except ftplib.error_perm:
            # Directory doesn't exist, create it
            self.logger.info(f"Creating remote path: {self.remote_path}")
            self._create_directory(self.remote_path)
            self.ftp.cwd(self.remote_path)
    
    def _create_directory(self, path: str):
        """Create directory on FTP server."""
        # Split path into components
        parts = path.strip('/').split('/')
        current_path = ""
        
        for part in parts:
            if not part:
                continue
                
            current_path = f"{current_path}/{part}" if current_path else part
            
            try:
                self.ftp.cwd(current_path)
            except ftplib.error_perm:
                try:
                    self.ftp.mkd(current_path)
                    self.ftp.cwd(current_path)
                except ftplib.error_perm as e:
                    self.logger.error(f"Failed to create directory {current_path}: {e}")
                    raise
    
    def save(self, data: bytes, filename: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Save data to FTP server."""
        if not self.ftp:
            return {"success": False, "error": "FTP not initialized"}
        
        try:
            # Upload file
            file_obj = BytesIO(data)
            self.ftp.storbinary(f"STOR {filename}", file_obj)
            
            # Upload metadata if provided
            if metadata:
                metadata_filename = filename + ".meta"
                metadata_json = json.dumps(metadata, indent=2).encode('utf-8')
                metadata_obj = BytesIO(metadata_json)
                self.ftp.storbinary(f"STOR {metadata_filename}", metadata_obj)
            
            # Get file size
            self.ftp.voidcmd("TYPE I")  # Switch to binary mode for size
            size = self.ftp.size(filename)
            
            return {
                "success": True,
                "filename": filename,
                "remote_path": f"{self.remote_path}/{filename}",
                "size": size,
                "metadata_saved": metadata is not None,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error saving file '{filename}' to FTP: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def list_files(self, prefix: str = "", limit: int = 100) -> List[Dict[str, Any]]:
        """List files on FTP server."""
        if not self.ftp:
            return []
        
        try:
            files = []
            file_list = self.ftp.nlst()
            
            for filename in file_list:
                # Skip metadata files and directories
                if filename.endswith('.meta') or filename in ['.', '..']:
                    continue
                
                # Check prefix
                if prefix and not filename.startswith(prefix):
                    continue
                
                try:
                    # Get file size and modification time
                    self.ftp.voidcmd("TYPE I")  # Binary mode for size
                    size = self.ftp.size(filename)
                    
                    # Try to get modification time (not all FTP servers support this)
                    try:
                        mtime_str = self.ftp.sendcmd(f"MDTM {filename}")[4:]
                        mtime = datetime.strptime(mtime_str, "%Y%m%d%H%M%S").isoformat()
                    except:
                        mtime = datetime.now().isoformat()
                    
                    file_info = {
                        "filename": filename,
                        "size": size,
                        "modified_at": mtime,
                        "remote_path": f"{self.remote_path}/{filename}"
                    }
                    
                    # Check for metadata file
                    metadata_filename = filename + ".meta"
                    if metadata_filename in file_list:
                        try:
                            metadata_obj = BytesIO()
                            self.ftp.retrbinary(f"RETR {metadata_filename}", metadata_obj.write)
                            metadata = json.loads(metadata_obj.getvalue().decode('utf-8'))
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
            self.logger.error(f"Error listing FTP files: {e}")
            return []
    
    def delete(self, filename: str) -> bool:
        """Delete a file from FTP server."""
        if not self.ftp:
            return False
        
        try:
            # Delete main file
            self.ftp.delete(filename)
            
            # Delete metadata file if it exists
            metadata_filename = filename + ".meta"
            try:
                self.ftp.delete(metadata_filename)
            except:
                pass  # Metadata file might not exist
            
            self.logger.info(f"Deleted file from FTP: {filename}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error deleting file '{filename}' from FTP: {e}")
            return False
    
    def get_file_info(self, filename: str) -> Optional[Dict[str, Any]]:
        """Get information about a file on FTP server."""
        if not self.ftp:
            return None
        
        try:
            # Check if file exists
            file_list = self.ftp.nlst()
            if filename not in file_list:
                return None
            
            # Get file size
            self.ftp.voidcmd("TYPE I")  # Binary mode for size
            size = self.ftp.size(filename)
            
            # Try to get modification time
            try:
                mtime_str = self.ftp.sendcmd(f"MDTM {filename}")[4:]
                mtime = datetime.strptime(mtime_str, "%Y%m%d%H%M%S").isoformat()
            except:
                mtime = datetime.now().isoformat()
            
            file_info = {
                "filename": filename,
                "size": size,
                "modified_at": mtime,
                "remote_path": f"{self.remote_path}/{filename}",
                "exists": True
            }
            
            # Check for metadata file
            metadata_filename = filename + ".meta"
            if metadata_filename in file_list:
                try:
                    metadata_obj = BytesIO()
                    self.ftp.retrbinary(f"RETR {metadata_filename}", metadata_obj.write)
                    metadata = json.loads(metadata_obj.getvalue().decode('utf-8'))
                    file_info["metadata"] = metadata
                except Exception as e:
                    self.logger.debug(f"Failed to load metadata: {e}")
            
            return file_info
            
        except Exception as e:
            self.logger.error(f"Error getting file info for '{filename}' from FTP: {e}")
            return None
    
    def cleanup(self):
        """Close FTP connection."""
        if self.ftp:
            try:
                self.ftp.quit()
            except:
                try:
                    self.ftp.close()
                except:
                    pass
            self.ftp = None
        
        self.initialized = False
