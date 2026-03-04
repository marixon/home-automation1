"""
Global camera service manager for handling multiple cameras.
"""

import threading
import time
from typing import Dict, Any, List, Optional
from datetime import datetime
from homeauto.utils.logging_config import get_logger
from homeauto.database.repository import DeviceRepository
from homeauto.config.manager import ConfigManager
from homeauto.devices.camera import CameraDevice

from .manager import CameraServiceManager


class GlobalCameraServiceManager:
    """Global manager for all camera services across all cameras."""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.config_manager = ConfigManager()
        self.device_repo = DeviceRepository()
        
        # Service managers for each camera
        self.service_managers: Dict[str, CameraServiceManager] = {}
        self.running = False
        self.initialized = False
        
        # Configuration
        self.config = self.config_manager.get_config().get("camera_services", {})
        self.enabled = self.config.get("enabled", True)
        
        # Statistics
        self.stats = {
            "start_time": None,
            "total_cameras": 0,
            "initialized_cameras": 0,
            "running_cameras": 0,
            "total_snapshots": 0,
            "total_errors": 0,
            "last_scan_time": None
        }
        
        # Auto-start thread
        self.auto_start = self.config.get("auto_start", False)
        self.scan_interval = self.config.get("scan_interval", 300)  # seconds
        self.scan_thread = None
    
    def initialize(self) -> bool:
        """Initialize the global service manager."""
        if not self.enabled:
            self.logger.info("Camera services are disabled in configuration")
            return False
        
        try:
            self.logger.info("Initializing global camera service manager")
            
            # Load camera devices
            cameras = self._get_camera_devices()
            self.stats["total_cameras"] = len(cameras)
            
            # Initialize service managers for each camera
            for camera_id, camera_device in cameras.items():
                try:
                    self._initialize_camera_service_manager(camera_id, camera_device)
                except Exception as e:
                    self.logger.error(f"Failed to initialize service manager for camera {camera_id}: {e}")
                    self.stats["total_errors"] += 1
            
            self.initialized = len(self.service_managers) > 0
            self.stats["initialized_cameras"] = len(self.service_managers)
            
            if self.initialized:
                self.logger.info(f"Global camera service manager initialized with {len(self.service_managers)} cameras")
                
                # Start auto-start thread if configured
                if self.auto_start:
                    self._start_auto_start_thread()
            else:
                self.logger.warning("No camera service managers were initialized")
            
            return self.initialized
            
        except Exception as e:
            self.logger.error(f"Failed to initialize global camera service manager: {e}")
            return False
    
    def _get_camera_devices(self) -> Dict[str, CameraDevice]:
        """Get all camera devices from the database."""
        cameras = {}
        
        try:
            all_devices = self.device_repo.get_all()
            
            for device in all_devices:
                if device.device_type == "camera":
                    # Check if camera is enabled in configuration
                    cameras_config = self.config.get("cameras", {})
                    camera_enabled = True
                    
                    if device.ip_address in cameras_config:
                        camera_config = cameras_config[device.ip_address]
                        camera_enabled = camera_config.get("enabled", True)
                    
                    if camera_enabled:
                        credentials = self.config_manager.get_credentials("camera") or {}
                        camera_device = CameraDevice(device.ip_address, credentials)
                        cameras[device.id] = camera_device
            
            self.logger.info(f"Found {len(cameras)} camera devices")
            return cameras
            
        except Exception as e:
            self.logger.error(f"Error getting camera devices: {e}")
            return {}
    
    def _initialize_camera_service_manager(self, camera_id: str, camera_device: CameraDevice):
        """Initialize a service manager for a specific camera."""
        # Get device info
        device = self.device_repo.get(camera_id)
        if not device:
            self.logger.error(f"Device {camera_id} not found in database")
            return
        
        # Get camera-specific configuration
        camera_config = self.config.get("defaults", {}).copy()
        
        # Apply camera-specific overrides
        cameras_config = self.config.get("cameras", {})
        if device.ip_address in cameras_config:
            camera_config.update(cameras_config[device.ip_address])
        
        # Add camera info to config
        camera_config["camera_name"] = device.name
        camera_config["camera_ip"] = device.ip_address
        
        # Create service manager
        service_manager = CameraServiceManager(camera_device, camera_config)
        
        # Initialize the service manager
        if service_manager.initialize():
            self.service_managers[camera_id] = service_manager
            self.logger.info(f"Service manager initialized for camera: {device.name} ({device.ip_address})")
        else:
            self.logger.error(f"Failed to initialize service manager for camera: {device.name}")
    
    def start_all(self) -> bool:
        """Start all camera services."""
        if not self.initialized:
            self.logger.error("Global service manager not initialized")
            return False
        
        if self.running:
            self.logger.warning("Services already running")
            return True
        
        try:
            self.logger.info("Starting all camera services")
            started_count = 0
            
            for camera_id, service_manager in self.service_managers.items():
                try:
                    if service_manager.start():
                        started_count += 1
                        self.logger.info(f"Services started for camera {camera_id}")
                    else:
                        self.logger.error(f"Failed to start services for camera {camera_id}")
                        self.stats["total_errors"] += 1
                except Exception as e:
                    self.logger.error(f"Error starting services for camera {camera_id}: {e}")
                    self.stats["total_errors"] += 1
            
            self.running = started_count > 0
            self.stats["running_cameras"] = started_count
            self.stats["start_time"] = datetime.now().isoformat()
            
            if self.running:
                self.logger.info(f"Started services for {started_count} cameras")
            else:
                self.logger.warning("No camera services were started")
            
            return self.running
            
        except Exception as e:
            self.logger.error(f"Failed to start all camera services: {e}")
            return False
    
    def stop_all(self) -> bool:
        """Stop all camera services."""
        if not self.running:
            return True
        
        try:
            self.logger.info("Stopping all camera services")
            stopped_count = 0
            
            for camera_id, service_manager in self.service_managers.items():
                try:
                    if service_manager.stop():
                        stopped_count += 1
                        self.logger.info(f"Services stopped for camera {camera_id}")
                    else:
                        self.logger.error(f"Failed to stop services for camera {camera_id}")
                except Exception as e:
                    self.logger.error(f"Error stopping services for camera {camera_id}: {e}")
            
            self.running = False
            self.stats["running_cameras"] = 0
            
            self.logger.info(f"Stopped services for {stopped_count} cameras")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to stop all camera services: {e}")
            return False
    
    def start_camera(self, camera_id: str) -> bool:
        """Start services for a specific camera."""
        if camera_id not in self.service_managers:
            self.logger.error(f"Service manager not found for camera {camera_id}")
            return False
        
        try:
            service_manager = self.service_managers[camera_id]
            success = service_manager.start()
            
            if success:
                self.stats["running_cameras"] += 1
                self.running = self.stats["running_cameras"] > 0
                self.logger.info(f"Services started for camera {camera_id}")
            else:
                self.logger.error(f"Failed to start services for camera {camera_id}")
                self.stats["total_errors"] += 1
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error starting services for camera {camera_id}: {e}")
            self.stats["total_errors"] += 1
            return False
    
    def stop_camera(self, camera_id: str) -> bool:
        """Stop services for a specific camera."""
        if camera_id not in self.service_managers:
            self.logger.error(f"Service manager not found for camera {camera_id}")
            return False
        
        try:
            service_manager = self.service_managers[camera_id]
            success = service_manager.stop()
            
            if success:
                self.stats["running_cameras"] = max(0, self.stats["running_cameras"] - 1)
                self.running = self.stats["running_cameras"] > 0
                self.logger.info(f"Services stopped for camera {camera_id}")
            else:
                self.logger.error(f"Failed to stop services for camera {camera_id}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error stopping services for camera {camera_id}: {e}")
            return False
    
    def get_camera_service_manager(self, camera_id: str) -> Optional[CameraServiceManager]:
        """Get the service manager for a specific camera."""
        return self.service_managers.get(camera_id)
    
    def get_status(self) -> Dict[str, Any]:
        """Get global status of all camera services."""
        camera_statuses = {}
        
        for camera_id, service_manager in self.service_managers.items():
            try:
                camera_statuses[camera_id] = service_manager.get_status()
            except Exception as e:
                self.logger.error(f"Error getting status for camera {camera_id}: {e}")
                camera_statuses[camera_id] = {"error": str(e)}
        
        # Calculate runtime
        runtime = None
        if self.stats["start_time"]:
            start_dt = datetime.fromisoformat(self.stats["start_time"]) if isinstance(self.stats["start_time"], str) else self.stats["start_time"]
            runtime = (datetime.now() - start_dt).total_seconds()
        
        status = {
            "enabled": self.enabled,
            "initialized": self.initialized,
            "running": self.running,
            "auto_start": self.auto_start,
            "scan_interval": self.scan_interval,
            "stats": self.stats,
            "runtime_seconds": runtime,
            "camera_count": len(self.service_managers),
            "camera_statuses": camera_statuses
        }
        
        return status
    
    def get_camera_status(self, camera_id: str) -> Optional[Dict[str, Any]]:
        """Get status for a specific camera."""
        service_manager = self.get_camera_service_manager(camera_id)
        if not service_manager:
            return None
        
        try:
            return service_manager.get_status()
        except Exception as e:
            self.logger.error(f"Error getting camera status: {e}")
            return {"error": str(e)}
    
    def take_snapshot(self, camera_id: str, metadata: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """Take a snapshot from a specific camera."""
        service_manager = self.get_camera_service_manager(camera_id)
        if not service_manager:
            return None
        
        try:
            result = service_manager.take_snapshot(metadata)
            if result:
                self.stats["total_snapshots"] += 1
            return result
        except Exception as e:
            self.logger.error(f"Error taking snapshot: {e}")
            self.stats["total_errors"] += 1
            return None
    
    def request_snapshot(self, camera_id: str, metadata: Dict[str, Any] = None, priority: str = "normal") -> bool:
        """Request a snapshot from a specific camera."""
        service_manager = self.get_camera_service_manager(camera_id)
        if not service_manager:
            return False
        
        try:
            success = service_manager.request_snapshot(metadata, priority)
            return success
        except Exception as e:
            self.logger.error(f"Error requesting snapshot: {e}")
            self.stats["total_errors"] += 1
            return False
    
    def check_motion(self, camera_id: str) -> Optional[Dict[str, Any]]:
        """Check motion for a specific camera."""
        service_manager = self.get_camera_service_manager(camera_id)
        if not service_manager:
            return None
        
        try:
            return service_manager.check_motion()
        except Exception as e:
            self.logger.error(f"Error checking motion: {e}")
            self.stats["total_errors"] += 1
            return None
    
    def check_objects(self, camera_id: str) -> Optional[Dict[str, Any]]:
        """Check objects for a specific camera."""
        service_manager = self.get_camera_service_manager(camera_id)
        if not service_manager:
            return None
        
        try:
            return service_manager.check_objects()
        except Exception as e:
            self.logger.error(f"Error checking objects: {e}")
            self.stats["total_errors"] += 1
            return None
    
    def _start_auto_start_thread(self):
        """Start the auto-start thread."""
        if self.scan_thread and self.scan_thread.is_alive():
            return
        
        self.scan_thread = threading.Thread(target=self._auto_start_loop)
        self.scan_thread.daemon = True
        self.scan_thread.start()
        self.logger.info("Auto-start thread started")
    
    def _auto_start_loop(self):
        """Background thread for auto-start functionality."""
        self.logger.info("Auto-start loop started")
        
        while self.running:
            try:
                # Scan for new cameras
                self._scan_for_new_cameras()
                
                # Update scan time
                self.stats["last_scan_time"] = datetime.now().isoformat()
                
                # Sleep for scan interval
                time.sleep(self.scan_interval)
                
            except Exception as e:
                self.logger.error(f"Error in auto-start loop: {e}")
                time.sleep(60)  # Sleep for a minute before retry
        
        self.logger.info("Auto-start loop stopped")
    
    def _scan_for_new_cameras(self):
        """Scan for new cameras and initialize them."""
        try:
            # Get current camera IDs
            current_camera_ids = set(self.service_managers.keys())
            
            # Get all camera devices
            cameras = self._get_camera_devices()
            
            # Find new cameras
            for camera_id, camera_device in cameras.items():
                if camera_id not in current_camera_ids:
                    self.logger.info(f"Found new camera: {camera_id}")
                    self._initialize_camera_service_manager(camera_id, camera_device)
                    
                    # Auto-start if configured
                    if self.running:
                        service_manager = self.service_managers.get(camera_id)
                        if service_manager:
                            service_manager.start()
                            self.stats["running_cameras"] += 1
            
            # Update stats
            self.stats["total_cameras"] = len(cameras)
            self.stats["initialized_cameras"] = len(self.service_managers)
            
        except Exception as e:
            self.logger.error(f"Error scanning for new cameras: {e}")
    
    def cleanup(self):
        """Clean up all resources."""
        self.logger.info("Cleaning up global camera service manager")
        
        # Stop all services
        self.stop_all()
        
        # Clean up individual service managers
        for camera_id, service_manager in self.service_managers.items():
            try:
                service_manager.cleanup()
            except Exception as e:
                self.logger.error(f"Error cleaning up service manager for camera {camera_id}: {e}")
        
        self.service_managers.clear()
        self.initialized = False
        self.running = False
        
        self.logger.info("Global camera service manager cleaned up")


# Global instance
_global_manager: Optional[GlobalCameraServiceManager] = None


def get_global_manager() -> GlobalCameraServiceManager:
    """Get or create the global camera service manager instance."""
    global _global_manager
    
    if _global_manager is None:
        _global_manager = GlobalCameraServiceManager()
    
    return _global_manager


def initialize_global_manager() -> bool:
    """Initialize the global camera service manager."""
    manager = get_global_manager()
    return manager.initialize()


def start_all_services() -> bool:
    """Start all camera services."""
    manager = get_global_manager()
    return manager.start_all()


def stop_all_services() -> bool:
    """Stop all camera services."""
    manager = get_global_manager()
    return manager.stop_all()


def get_global_status() -> Dict[str, Any]:
    """Get global status of all camera services."""
    manager = get_global_manager()
    return manager.get_status()
