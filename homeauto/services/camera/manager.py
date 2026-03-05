"""
Camera service manager for coordinating all camera services.
"""

import threading
import time
from typing import Dict, Any, Optional, List
from datetime import datetime
from homeauto.utils.logging_config import get_logger
from homeauto.devices.camera import CameraDevice

from .storage import StorageManager
from .snapshot_service import OnDemandSnapshotService
from .scheduled_service import ScheduledSnapshotService
from .motion_service import MotionDetectionService
from .object_recognition import ObjectRecognitionService


class CameraServiceManager:
    """Manages all camera services for a single camera."""
    
    def __init__(self, camera_device: CameraDevice, config: Dict[str, Any]):
        self.camera = camera_device
        self.config = config
        self.logger = get_logger(f"{__name__}.{self.__class__.__name__}")
        
        # Service instances
        self.services: Dict[str, Any] = {}
        self.storage_manager = None
        
        # Service status
        self.running = False
        self.initialized = False
        
        # Statistics
        self.stats = {
            "start_time": None,
            "total_snapshots": 0,
            "service_errors": 0,
            "last_activity": None
        }
    
    def initialize(self) -> bool:
        """Initialize all camera services."""
        try:
            self.logger.info(f"Initializing camera service manager for {self.camera.ip}")
            
            # Get configuration from defaults or direct config
            defaults = self.config.get("defaults", {})
            
            # Initialize storage manager
            storage_config = defaults.get("storage", self.config.get("storage", {}))
            self.storage_manager = StorageManager(storage_config)
            if not self.storage_manager.initialize():
                self.logger.error("Failed to initialize storage manager")
                return False
            
            # Initialize services based on configuration
            services_config = defaults.get("services", self.config.get("services", {}))
            
            # On-demand snapshot service
            if services_config.get("on_demand", {}).get("enabled", True):
                self._initialize_service("on_demand", OnDemandSnapshotService, 
                                       services_config.get("on_demand", {}))
            
            # Scheduled snapshot service
            if services_config.get("scheduled", {}).get("enabled", False):
                self._initialize_service("scheduled", ScheduledSnapshotService,
                                       services_config.get("scheduled", {}))
            
            # Motion detection service
            if services_config.get("motion_detected", {}).get("enabled", False):
                self._initialize_service("motion", MotionDetectionService,
                                       services_config.get("motion_detected", {}))
            
            # Object recognition service
            if services_config.get("object_recognition", {}).get("enabled", False):
                self._initialize_service("object_recognition", ObjectRecognitionService,
                                       services_config.get("object_recognition", {}))
            
            self.initialized = True
            self.logger.info(f"Camera service manager initialized with {len(self.services)} services")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize camera service manager: {e}")
            return False
    
    def _initialize_service(self, service_name: str, service_class, config: Dict[str, Any]):
        """Initialize a specific service."""
        try:
            service = service_class(self.camera, config)
            # Set storage manager for snapshot-based services
            if hasattr(service, 'storage_manager'):
                service.storage_manager = self.storage_manager
            self.services[service_name] = service
            self.logger.info(f"Initialized {service_name} service")
        except Exception as e:
            self.logger.error(f"Error initializing {service_name} service: {e}")
    
    def start(self) -> bool:
        """Start all camera services."""
        if not self.initialized:
            if not self.initialize():
                return False
        
        try:
            self.running = True
            self.stats["start_time"] = datetime.now().isoformat()
            
            # Start all services
            for service_name, service in self.services.items():
                try:
                    if service.start():
                        self.logger.info(f"Started {service_name} service")
                    else:
                        self.logger.error(f"Failed to start {service_name} service")
                        self.stats["service_errors"] += 1
                except Exception as e:
                    self.logger.error(f"Error starting {service_name} service: {e}")
                    self.stats["service_errors"] += 1
            
            self.logger.info(f"Camera service manager started with {len(self.services)} services")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start camera service manager: {e}")
            self.running = False
            return False
    
    def stop(self) -> bool:
        """Stop all camera services."""
        if not self.running:
            return True
        
        try:
            self.running = False
            
            # Stop all services
            for service_name, service in self.services.items():
                try:
                    service.stop()
                    self.logger.info(f"Stopped {service_name} service")
                except Exception as e:
                    self.logger.error(f"Error stopping {service_name} service: {e}")
            
            self.logger.info("Camera service manager stopped")
            return True
            
        except Exception as e:
            self.logger.error(f"Error stopping camera service manager: {e}")
            return False
    
    def take_snapshot(self, metadata: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """Take an immediate snapshot."""
        if "on_demand" not in self.services:
            self.logger.warning("On-demand snapshot service not available")
            return None
        
        try:
            result = self.services["on_demand"].take_snapshot(metadata)
            if result and result.get("success", False):
                self.stats["total_snapshots"] += 1
                self.stats["last_activity"] = datetime.now().isoformat()
            return result
        except Exception as e:
            self.logger.error(f"Error taking snapshot: {e}")
            return None
    
    def request_snapshot(self, metadata: Dict[str, Any] = None) -> bool:
        """Request a snapshot (queued)."""
        if "on_demand" not in self.services:
            self.logger.warning("On-demand snapshot service not available")
            return False
        
        try:
            return self.services["on_demand"].request_snapshot(metadata)
        except Exception as e:
            self.logger.error(f"Error requesting snapshot: {e}")
            return False
    
    def check_motion(self) -> Optional[Dict[str, Any]]:
        """Check for motion."""
        if "motion" not in self.services:
            return None
        
        try:
            return self.services["motion"].check_motion()
        except Exception as e:
            self.logger.error(f"Error checking motion: {e}")
            return None
    
    def check_objects(self) -> Optional[Dict[str, Any]]:
        """Check for objects."""
        if "object_recognition" not in self.services:
            return None
        
        try:
            return self.services["object_recognition"].check_objects()
        except Exception as e:
            self.logger.error(f"Error checking objects: {e}")
            return None
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status of all services."""
        service_status = {}
        for service_name, service in self.services.items():
            try:
                service_status[service_name] = service.get_status()
            except Exception as e:
                service_status[service_name] = {"error": str(e)}
        
        return {
            "running": self.running,
            "initialized": self.initialized,
            "camera_ip": self.camera.ip,
            "services_available": list(self.services.keys()),
            "stats": self.stats.copy(),
            "service_status": service_status,
            "storage_available": self.storage_manager is not None and self.storage_manager.initialized
        }
    
    def get_service(self, service_name: str) -> Optional[Any]:
        """Get a specific service by name."""
        return self.services.get(service_name)
    
    def add_schedule(self, schedule_config: Dict[str, Any]) -> bool:
        """Add a new schedule to the scheduled service."""
        if "scheduled" not in self.services:
            return False
        
        try:
            return self.services["scheduled"].add_schedule(schedule_config)
        except Exception as e:
            self.logger.error(f"Error adding schedule: {e}")
            return False
    
    def remove_schedule(self, schedule_name: str) -> bool:
        """Remove a schedule from the scheduled service."""
        if "scheduled" not in self.services:
            return False
        
        try:
            return self.services["scheduled"].remove_schedule(schedule_name)
        except Exception as e:
            self.logger.error(f"Error removing schedule: {e}")
            return False
    
    def get_snapshots(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent snapshots."""
        if not self.storage_manager or not self.storage_manager.initialized:
            return []
        
        try:
            return self.storage_manager.list_all_files(limit=limit)
        except Exception as e:
            self.logger.error(f"Error getting snapshots: {e}")
            return []
    
    def _register_service_callbacks(self):
        """Register callbacks for service events."""
        for service_name, service in self.services.items():
            if hasattr(service, 'on_snapshot'):
                service.on_snapshot = self._on_snapshot_callback
            if hasattr(service, 'on_motion'):
                service.on_motion = self._on_motion_callback
            if hasattr(service, 'on_objects'):
                service.on_objects = self._on_objects_callback
            if hasattr(service, 'on_error'):
                service.on_error = self._on_error_callback
    
    def _on_snapshot_callback(self, result: Dict[str, Any]):
        """Handle snapshot callback."""
        self.stats["total_snapshots"] += 1
        self.stats["last_activity"] = datetime.now().isoformat()
        self.logger.info(f"Snapshot taken: {result.get('filename', 'unknown')}")
    
    def _on_motion_callback(self, result: Dict[str, Any]):
        """Handle motion detection callback."""
        self.logger.info(f"Motion detected: confidence={result.get('confidence', 0)}")
    
    def _on_objects_callback(self, result: Dict[str, Any]):
        """Handle object detection callback."""
        objects = result.get('objects', [])
        self.logger.info(f"Objects detected: {len(objects)} objects")
    
    def _on_error_callback(self, error: str, service_name: str):
        """Handle error callback."""
        self.stats["service_errors"] += 1
        self.logger.error(f"Service error in {service_name}: {error}")
    
    def execute_schedule(self, schedule_name: str) -> bool:
        """Execute a specific schedule immediately."""
        if "scheduled" not in self.services:
            return False
        
        try:
            return self.services["scheduled"].execute_schedule(schedule_name)
        except Exception as e:
            self.logger.error(f"Error executing schedule {schedule_name}: {e}")
            return False
    
    def get_service_status(self, service_name: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific service."""
        service = self.services.get(service_name)
        if not service:
            return None
        
        try:
            return service.get_status()
        except Exception as e:
            return {"error": str(e)}
    
    def cleanup(self):
        """Clean up resources."""
        self.stop()
        if self.storage_manager:
            self.storage_manager.cleanup()
        self.initialized = False

