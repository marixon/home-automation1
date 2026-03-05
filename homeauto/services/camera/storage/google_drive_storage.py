"""
Google Drive storage backend for camera snapshots.
"""

import os
import json
import mimetypes
from datetime import datetime
from typing import Dict, Any, List, Optional
from io import BytesIO
from .base import StorageBackend


class GoogleDriveStorage(StorageBackend):
    """Google Drive storage backend."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.credentials_path = config.get("credentials_path")
        self.folder_id = config.get("folder_id")
        self.scopes = ['https://www.googleapis.com/auth/drive.file']
        
        self.service = None
        self.initial_folder_id = None
    
    def initialize(self) -> bool:
        """Initialize Google Drive connection."""
        try:
            from google.oauth2 import service_account
            from googleapiclient.discovery import build
            from googleapiclient.http import MediaIoBaseUpload
            
            # Check if credentials file exists
            if not self.credentials_path or not os.path.exists(self.credentials_path):
                self.logger.error(f"Google Drive credentials file not found: {self.credentials_path}")
                return False
            
            # Load credentials
            credentials = service_account.Credentials.from_service_account_file(
                self.credentials_path,
                scopes=self.scopes
            )
            
            # Build Google Drive service
            self.service = build('drive', 'v3', credentials=credentials)
            
            # Verify folder access if folder_id is provided
            if self.folder_id:
                try:
                    folder = self.service.files().get(
                        fileId=self.folder_id,
                        fields='id, name'
                    ).execute()
                    self.initial_folder_id = folder['id']
                    self.logger.info(f"Google Drive folder verified: {folder.get('name', 'Unknown')}")
                except Exception as e:
                    self.logger.error(f"Failed to access Google Drive folder {self.folder_id}: {e}")
                    return False
            else:
                # Create a folder if none specified
                self.initial_folder_id = self._create_folder("Camera Snapshots")
                if not self.initial_folder_id:
                    return False
            
            self.initialized = True
            self.logger.info("Google Drive storage initialized successfully")
            return True
            
        except ImportError:
            self.logger.error("Google API client not installed. Install with: pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib")
            return False
        except Exception as e:
            self.logger.error(f"Failed to initialize Google Drive storage: {e}")
            self.service = None
            return False
    
    def _create_folder(self, folder_name: str) -> Optional[str]:
        """Create a folder in Google Drive."""
        try:
            from googleapiclient.http import MediaIoBaseUpload
            
            folder_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            
            folder = self.service.files().create(
                body=folder_metadata,
                fields='id'
            ).execute()
            
            folder_id = folder.get('id')
            self.logger.info(f"Created Google Drive folder: {folder_name} (ID: {folder_id})")
            return folder_id
            
        except Exception as e:
            self.logger.error(f"Failed to create Google Drive folder: {e}")
            return None
    
    def save(self, data: bytes, filename: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Save data to Google Drive."""
        if not self.service:
            return {"success": False, "error": "Google Drive not initialized"}
        
        try:
            from googleapiclient.http import MediaIoBaseUpload
            
            # Determine MIME type
            mime_type, _ = mimetypes.guess_type(filename)
            if not mime_type:
                mime_type = 'application/octet-stream'
            
            # Prepare file metadata
            file_metadata = {
                'name': filename,
                'parents': [self.initial_folder_id] if self.initial_folder_id else []
            }
            
            # Create media upload
            file_obj = BytesIO(data)
            media = MediaIoBaseUpload(
                file_obj,
                mimetype=mime_type,
                resumable=True
            )
            
            # Upload file
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, name, size, createdTime, modifiedTime'
            ).execute()
            
            # Save metadata as a separate file if provided
            if metadata:
                metadata_filename = filename + ".meta.json"
                metadata_json = json.dumps(metadata, indent=2).encode('utf-8')
                
                metadata_metadata = {
                    'name': metadata_filename,
                    'parents': [self.initial_folder_id] if self.initial_folder_id else [],
                    'description': f"Metadata for {filename}"
                }
                
                metadata_obj = BytesIO(metadata_json)
                metadata_media = MediaIoBaseUpload(
                    metadata_obj,
                    mimetype='application/json',
                    resumable=True
                )
                
                self.service.files().create(
                    body=metadata_metadata,
                    media_body=metadata_media,
                    fields='id'
                ).execute()
            
            return {
                "success": True,
                "file_id": file['id'],
                "filename": file['name'],
                "size": int(file.get('size', 0)),
                "created_at": file.get('createdTime'),
                "modified_at": file.get('modifiedTime'),
                "metadata_saved": metadata is not None,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error saving file '{filename}' to Google Drive: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def list_files(self, prefix: str = "", limit: int = 100) -> List[Dict[str, Any]]:
        """List files in Google Drive folder."""
        if not self.service:
            return []
        
        try:
            # Build query
            query_parts = []
            
            # Filter by folder
            if self.initial_folder_id:
                query_parts.append(f"'{self.initial_folder_id}' in parents")
            
            # Filter by name prefix
            if prefix:
                query_parts.append(f"name contains '{prefix}'")
            
            # Exclude metadata files and folders
            query_parts.append("mimeType != 'application/vnd.google-apps.folder'")
            query_parts.append("not name contains '.meta.json'")
            
            query = " and ".join(query_parts) if query_parts else ""
            
            # List files
            results = self.service.files().list(
                q=query,
                pageSize=limit,
                fields="files(id, name, size, createdTime, modifiedTime, mimeType)",
                orderBy="createdTime desc"
            ).execute()
            
            files = []
            for file in results.get('files', []):
                file_info = {
                    "file_id": file['id'],
                    "filename": file['name'],
                    "size": int(file.get('size', 0)),
                    "created_at": file.get('createdTime'),
                    "modified_at": file.get('modifiedTime'),
                    "mime_type": file.get('mimeType')
                }
                
                # Try to find associated metadata file
                metadata_filename = file['name'] + ".meta.json"
                metadata_query = f"name = '{metadata_filename}'"
                if self.initial_folder_id:
                    metadata_query += f" and '{self.initial_folder_id}' in parents"
                
                try:
                    metadata_results = self.service.files().list(
                        q=metadata_query,
                        pageSize=1,
                        fields="files(id, name)"
                    ).execute()
                    
                    if metadata_results.get('files'):
                        metadata_file_id = metadata_results['files'][0]['id']
                        
                        # Download and parse metadata
                        from googleapiclient.http import MediaIoBaseDownload
                        request = self.service.files().get_media(fileId=metadata_file_id)
                        metadata_content = BytesIO()
                        downloader = MediaIoBaseDownload(metadata_content, request)
                        done = False
                        while not done:
                            status, done = downloader.next_chunk()
                        
                        metadata = json.loads(metadata_content.getvalue().decode('utf-8'))
                        file_info["metadata"] = metadata
                        
                except Exception as e:
                    self.logger.debug(f"Failed to load metadata for {file['name']}: {e}")
                
                files.append(file_info)
            
            return files
            
        except Exception as e:
            self.logger.error(f"Error listing Google Drive files: {e}")
            return []
    
    def delete(self, filename: str) -> bool:
        """Delete a file from Google Drive."""
        if not self.service:
            return False
        
        try:
            # Find the file
            query = f"name = '{filename}'"
            if self.initial_folder_id:
                query += f" and '{self.initial_folder_id}' in parents"
            
            results = self.service.files().list(
                q=query,
                pageSize=1,
                fields="files(id)"
            ).execute()
            
            files = results.get('files', [])
            if not files:
                self.logger.warning(f"File not found in Google Drive: {filename}")
                return False
            
            # Delete the file
            file_id = files[0]['id']
            self.service.files().delete(fileId=file_id).execute()
            
            # Try to delete metadata file
            metadata_filename = filename + ".meta.json"
            metadata_query = f"name = '{metadata_filename}'"
            if self.initial_folder_id:
                metadata_query += f" and '{self.initial_folder_id}' in parents"
            
            try:
                metadata_results = self.service.files().list(
                    q=metadata_query,
                    pageSize=1,
                    fields="files(id)"
                ).execute()
                
                if metadata_results.get('files'):
                    metadata_file_id = metadata_results['files'][0]['id']
                    self.service.files().delete(fileId=metadata_file_id).execute()
            except:
                pass  # Metadata file might not exist
            
            self.logger.info(f"Deleted file from Google Drive: {filename}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error deleting file '{filename}' from Google Drive: {e}")
            return False
    
    def get_file_info(self, filename: str) -> Optional[Dict[str, Any]]:
        """Get information about a file in Google Drive."""
        if not self.service:
            return None
        
        try:
            # Find the file
            query = f"name = '{filename}'"
            if self.initial_folder_id:
                query += f" and '{self.initial_folder_id}' in parents"
            
            results = self.service.files().list(
                q=query,
                pageSize=1,
                fields="files(id, name, size, createdTime, modifiedTime, mimeType)"
            ).execute()
            
            files = results.get('files', [])
            if not files:
                return None
            
            file = files[0]
            file_info = {
                "file_id": file['id'],
                "filename": file['name'],
                "size": int(file.get('size', 0)),
                "created_at": file.get('createdTime'),
                "modified_at": file.get('modifiedTime'),
                "mime_type": file.get('mimeType'),
                "exists": True
            }
            
            # Try to find metadata
            metadata_filename = filename + ".meta.json"
            metadata_query = f"name = '{metadata_filename}'"
            if self.initial_folder_id:
                metadata_query += f" and '{self.initial_folder_id}' in parents"
            
            try:
                metadata_results = self.service.files().list(
                    q=metadata_query,
                    pageSize=1,
                    fields="files(id)"
                ).execute()
                
                if metadata_results.get('files'):
                    metadata_file_id = metadata_results['files'][0]['id']
                    
                    # Download metadata
                    from googleapiclient.http import MediaIoBaseDownload
                    request = self.service.files().get_media(fileId=metadata_file_id)
                    metadata_content = BytesIO()
                    downloader = MediaIoBaseDownload(metadata_content, request)
                    done = False
                    while not done:
                        status, done = downloader.next_chunk()
                    
                    metadata = json.loads(metadata_content.getvalue().decode('utf-8'))
                    file_info["metadata"] = metadata
                    
            except Exception as e:
                self.logger.debug(f"Failed to load metadata for {filename}: {e}")
            
            return file_info
            
        except Exception as e:
            self.logger.error(f"Error getting file info for '{filename}' from Google Drive: {e}")
            return None
    
    def cleanup(self):
        """Clean up Google Drive connection."""
        self.service = None
        self.initialized = False
