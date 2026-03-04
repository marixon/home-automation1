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
            
            # Initialize storage manager
            storage_config = self.config.get("storage", {})
            self.storage_manager = StorageManager(storage_config)
            if not self.storage_manager.initialize():
                self.logger.error("Failed to initialize storage manager")
                return False
            
            # Initialize services based on configuration
            services_config = self.config.get("services", {})
            
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
            # Add camera name to config
            service_config = {
                **config,
                "camera_name": self.config.get("camera_name", f"Camera_{self.camera.ip}"),
                "camera_ip": self.camera.ip
            }
            
            # Create service instance
            service = service_class(self.camera, service_config)
            
            # Set storage manager if service supports it
            if hasattr(service, 'set_storage_manager'):
                service.set_storage_manager(self.storage_manager)
            
            # Register callbacks
            self._register_service_callbacks(service_name, service)
            
            self.services[service_name] = service
            self.logger.info(f"Service '{service_name}' initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize service '{service_name}': {e}")
    
    def _register_service_callbacks(self, service_name: str, service):
        """Register callbacks for service events."""
        # Register snapshot callback
        def on_snapshot_callback(snapshot_info):
            self.stats["total_snapshots"] += 1
            self.stats["last_activity"] = datetime.now().isoformat()
            self.logger.debug(f"Service '{service_name}' took snapshot")
        
        # Register error callback
        def on_error_callback(error_type, error_info):
            self.stats["service_errors"] += 1
            self.logger.error(f"Service '{service_name}' error: {error_type} - {error_info}")
        
        # Register event callback
        def on_event_callback(event_type, event_data):
            self.logger.debug(f"Service '{service_name}' event: {event_type}")
        
        service.register_callback("on_snapshot", on_snapshot_callback)
        service.register_callback("on_error", on_error_callback)
        service.register_callback("on_event", on_event_callback)
    
    def start(self) -> bool:
        """Start all camera services."""
        if self.running:
            self.logger.warning("Services already running")
            return True
        
        if not self.initialized:
            self.logger.error("Services not initialized")
            return False
        
        try:
            # Start all services
            for service_name, service in self.services.items():
                try:
                    if service.start():
                        self.logger.info(f"Service '{service_name}' started")
                    else:
                        self.logger.error(f"Failed to start service '{service_name}'")
                except Exception as e:
                    self.logger.error(f"Error starting service '{service_name}': {e}")
            
            self.running = True
            self.stats["start_time"] = datetime.now().isoformat()
            self.logger.info(f"All camera services started for {self.camera.ip}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start camera services: {e}")
            return False
    
    def stop(self) -> bool:
        """Stop all camera services."""
        if not self.running:
            return True
        
        try:
            # Stop all services
            for service_name, service in self.services.items():
                try:
                    if service.stop():
                        self.logger.info(f"Service '{service_name}' stopped")
                    else:
                        self.logger.warning(f"Failed to stop service '{service_name}'")
                except Exception as e:
                    self.logger.error(f"Error stopping service '{service_name}': {e}")
            
            # Cleanup storage manager
            if self.storage_manager:
                self.storage_manager.cleanup()
            
            self.running = False
            self.logger.info(f"All camera services stopped for {self.camera.ip}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error stopping camera services: {e}")
            return False
    
    def get_service(self, service_name: str) -> Optional[Any]:
        """Get a specific service by name."""
        return self.services.get(service_name)
    
    def take_snapshot(self, metadata: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """Take a snapshot using the on-demand service."""
        on_demand_service = self.get_service("on_demand")
        if not on_demand_service:
            self.logger.error("On-demand snapshot service not available")
            return None
        
        return on_demand_service.take_snapshot_now(metadata)
    
    def request_snapshot(self, metadata: Dict[str, Any] = None, priority: str = "normal") -> bool:
        """Request a snapshot via the on-demand service queue."""
        on_demand_service = self.get_service("on_demand")
        if not on_demand_service:
            self.logger.error("On-demand snapshot service not available")
            return False
        
        return on_demand_service.request_snapshot(metadata, priority)
    
    def execute_schedule(self, schedule_name: str, metadata: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """Execute a specific schedule immediately."""
        scheduled_service = self.get_service("scheduled")
        if not scheduled_service:
            self.logger.error("Scheduled snapshot service not available")
            return None
        
        return scheduled_service.execute_schedule(schedule_name, metadata)
    
    def check_motion(self) -> Optional[Dict[str, Any]]:
        """Manually trigger a motion check."""
        motion_service = self.get_service("motion")
        if not motion_service:
            self.logger.error("Motion detection service not available")
            return None
        
        return motion_service.trigger_manual_motion_check()
    
    def check_objects(self) -> Optional[Dict[str, Any]]:
        """Manually trigger an object recognition check."""
        object_service = self.get_service("object_recognition")
        if not object_service:
            self.logger.error("Object recognition service not available")
            return None
        
        return object_service.trigger_manual_object_check()
    
    def get_status(self) -> Dict[str, Any]:
        """Get overall status of all services."""
        service_statuses = {}
        for service_name, service in self.services.items():
            try:
                service_statuses[service_name] = service.get_status()
            except Exception as e:
                self.logger.error(f"Error getting status for service '{service_name}': {e}")
                service_statuses[service_name] = {"error": str(e)}
        
        # Calculate runtime
        runtime = None
        if self.stats["start_time"]:
            start_dt = datetime.fromisoformat(self.stats["start_time"]) if isinstance(self.stats["start_time"], str) else self.stats["start_time"]
            runtime = (datetime.now() - start_dt).total_seconds()
        
        status = {
            "camera_ip": self.camera.ip,
            "camera_online": self.camera.test_connection(),
            "running": self.running,
            "initialized": self.initialized,
            "services_available": list(self.services.keys()),
            "stats": self.stats,
            "runtime_seconds": runtime,
            "service_statuses": service_statuses,
            "storage_status": self.storage_manager.get_status() if self.storage_manager else None
        }
        
        return status
    
    def get_service_status(self, service_name: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific service."""
        service = self.get_service(service_name)
        if not service:
            return None
        
        try:
            return service.get_status()
        except Exception as e:
            self.logger.error(f"Error getting status for service '{service_name}': {e}")
            return {"error": str(e)}
    
    def add_schedule(self, name: str, config: Dict[str, Any]) -> bool:
        """Add a new schedule to the scheduled service."""
        scheduled_service = self.get_service("scheduled")
        if not scheduled_service:
            self.logger.error("Scheduled snapshot service not available")
            return False
        
        return scheduled_service.add_schedule(name, config)
    
    def remove_schedule(self, name: str) -> bool:
        """Remove a schedule from the scheduled service."""
        scheduled_service = self.get_service("scheduled")
        if not scheduled_service:
            self.logger.error("Scheduled snapshot service not available")
            return False
        
        return scheduled_service.remove_schedule(name)
    
    def get_snapshots(self, limit: int = 20) -> Dict[str, List[Dict[str, Any]]]:
        """Get snapshots from all storage backends."""
        if not self.storage_manager:
            return {}
        
        return self.storage_manager.list_all_files(limit=limit)
    
    def cleanup(self):
        """Clean up all resources."""
        self.stop()
        self.services.clear()
        self.initialized = False
