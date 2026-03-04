"""
Base camera service classes.
"""

import threading
import time
import json
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime
from homeauto.utils.logging_config import get_logger
from homeauto.devices.camera import CameraDevice


class CameraService(ABC):
    """Abstract base class for camera services."""
    
    def __init__(self, camera_device: CameraDevice, config: Dict[str, Any]):
        self.camera = camera_device
        self.config = config
        self.logger = get_logger(f"{__name__}.{self.__class__.__name__}")
        self.running = False
        self.service_thread = None
        self.callbacks: Dict[str, List[Callable]] = {
            "on_start": [],
            "on_stop": [],
            "on_error": [],
            "on_snapshot": [],
            "on_event": []
        }
        
        # Statistics
        self.stats = {
            "start_time": None,
            "snapshots_taken": 0,
            "errors": 0,
            "last_snapshot_time": None,
            "last_error": None
        }
    
    @abstractmethod
    def start(self) -> bool:
        """Start the service."""
        pass
    
    @abstractmethod
    def stop(self) -> bool:
        """Stop the service."""
        pass
    
    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """Get service status."""
        pass
    
    def register_callback(self, event: str, callback: Callable):
        """Register a callback for service events."""
        if event in self.callbacks:
            self.callbacks[event].append(callback)
        else:
            self.logger.warning(f"Unknown event type: {event}")
    
    def _trigger_callbacks(self, event: str, *args, **kwargs):
        """Trigger all registered callbacks for an event."""
        for callback in self.callbacks.get(event, []):
            try:
                callback(*args, **kwargs)
            except Exception as e:
                self.logger.error(f"Error in callback for event '{event}': {e}")
    
    def _take_snapshot(self, trigger_type: str = "manual", metadata: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """Take a snapshot from the camera."""
        try:
            snapshot_result = self.camera.get_snapshot()
            
            if not snapshot_result.get("success", False):
                self.logger.error(f"Failed to take snapshot: {snapshot_result}")
                self.stats["errors"] += 1
                self.stats["last_error"] = "Snapshot failed"
                self._trigger_callbacks("on_error", "snapshot_failed", snapshot_result)
                return None
            
            # Update statistics
            self.stats["snapshots_taken"] += 1
            self.stats["last_snapshot_time"] = datetime.now().isoformat()
            
            # Prepare snapshot metadata
            snapshot_metadata = {
                "camera_ip": self.camera.ip,
                "trigger_type": trigger_type,
                "timestamp": datetime.now().isoformat(),
                "camera_online": self.camera.test_connection(),
                "snapshot_source": snapshot_result.get("source", "unknown"),
                "is_placeholder": snapshot_result.get("is_placeholder", False),
                "content_type": snapshot_result.get("content_type", "unknown"),
                "size_bytes": snapshot_result.get("size_bytes", 0)
            }
            
            # Add custom metadata if provided
            if metadata:
                snapshot_metadata.update(metadata)
            
            # Decode image data if present
            image_data = None
            if "image_data" in snapshot_result:
                import base64
                image_data = base64.b64decode(snapshot_result["image_data"])
            
            snapshot_info = {
                "success": True,
                "metadata": snapshot_metadata,
                "image_data": image_data,
                "snapshot_result": snapshot_result
            }
            
            # Trigger snapshot callback
            self._trigger_callbacks("on_snapshot", snapshot_info)
            
            return snapshot_info
            
        except Exception as e:
            self.logger.error(f"Error taking snapshot: {e}")
            self.stats["errors"] += 1
            self.stats["last_error"] = str(e)
            self._trigger_callbacks("on_error", "snapshot_exception", str(e))
            return None
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get service statistics."""
        current_time = datetime.now()
        runtime = None
        if self.stats["start_time"]:
            start_dt = datetime.fromisoformat(self.stats["start_time"]) if isinstance(self.stats["start_time"], str) else self.stats["start_time"]
            runtime = (current_time - start_dt).total_seconds()
        
        return {
            **self.stats,
            "running": self.running,
            "runtime_seconds": runtime,
            "snapshots_per_hour": self.stats["snapshots_taken"] / (runtime / 3600) if runtime and runtime > 0 else 0
        }


class SnapshotService(CameraService):
    """Base class for snapshot-based services."""
    
    def __init__(self, camera_device: CameraDevice, config: Dict[str, Any]):
        super().__init__(camera_device, config)
        self.storage_manager = None
        self.image_quality = config.get("quality", "medium")
        self.image_format = config.get("format", "jpg")
        self.storage_destinations = config.get("storage", [])
    
    def set_storage_manager(self, storage_manager):
        """Set the storage manager for saving snapshots."""
        self.storage_manager = storage_manager
    
    def _save_snapshot(self, snapshot_info: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """Save snapshot to configured storage destinations."""
        if not self.storage_manager or not snapshot_info or not snapshot_info.get("success"):
            return {}
        
        image_data = snapshot_info.get("image_data")
        if not image_data:
            self.logger.warning("No image data to save")
            return {}
        
        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        camera_name = self.config.get("camera_name", "camera").replace(" ", "_").lower()
        filename = f"{camera_name}_{timestamp}.{self.image_format}"
        
        # Prepare metadata
        metadata = snapshot_info.get("metadata", {})
        metadata.update({
            "service_type": self.__class__.__name__,
            "image_quality": self.image_quality,
            "image_format": self.image_format
        })
        
        # Save to all configured destinations
        save_results = {}
        if self.storage_destinations:
            for destination in self.storage_destinations:
                result = self.storage_manager.save_to_backend(destination, image_data, filename, metadata)
                if result:
                    save_results[destination] = result
        else:
            # Save to all available backends
            save_results = self.storage_manager.save_to_all(image_data, filename, metadata)
        
        # Log results
        successful_saves = sum(1 for r in save_results.values() if r.get("success", False))
        self.logger.info(f"Saved snapshot to {successful_saves}/{len(save_results)} destinations")
        
        # Update snapshot info with save results
        snapshot_info["storage_results"] = save_results
        
        return save_results
    
    def _process_and_save_snapshot(self, trigger_type: str = "manual", 
                                  metadata: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """Take a snapshot and save it to storage."""
        # Take snapshot
        snapshot_info = self._take_snapshot(trigger_type, metadata)
        if not snapshot_info:
            return None
        
        # Save to storage
        save_results = self._save_snapshot(snapshot_info)
        
        # Trigger event callback
        event_data = {
            "snapshot": snapshot_info,
            "storage": save_results,
            "trigger": trigger_type
        }
        self._trigger_callbacks("on_event", "snapshot_saved", event_data)
        
        return {
            "snapshot": snapshot_info,
            "storage": save_results
        }
