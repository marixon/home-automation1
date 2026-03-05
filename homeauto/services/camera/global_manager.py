#!/usr/bin/env python3
"""
Global camera service manager.
Manages all camera services across the system.
"""

import sys
import os
import threading
import time
from typing import Dict, List, Optional, Any
from datetime import datetime

from homeauto.config.manager import ConfigManager
from homeauto.database.repository import DeviceRepository
from .manager import CameraServiceManager
from homeauto.devices.camera import CameraDevice


class GlobalCameraServiceManager:
    """Global manager for all camera services."""
    
    def __init__(self):
        # Core components
        self.config_manager = ConfigManager()
        self.device_repo = DeviceRepository()
        
        # Service managers for each camera
        self.service_managers: Dict[str, CameraServiceManager] = {}
        self.running = False
        self.initialized = False
        
        # Configuration
        self.config = self.config_manager.config.get("camera_services", {})
        self.enabled = self.config.get("enabled", True)
        
        # Statistics
        self.stats = {
            "start_time": None,
            "total_cameras": 0,
            "initialized_cameras": 0,
            "running_cameras": 0,
            "total_snapshots": 0,
            "total_motion_events": 0,
            "total_object_detections": 0,
            "storage_usage": {},
            "service_status": {}
        }
        
        # Thread management
        self.control_thread = None
        self.shutdown_event = threading.Event()
    
    def initialize(self) -> bool:
        """Initialize the global camera service manager."""
        if self.initialized:
            return True
        
        if not self.enabled:
            self.log("Camera services are disabled in configuration")
            return False
        
        try:
            # Load camera devices from database
            cameras = self.device_repo.get_by_type("camera")
            self.stats["total_cameras"] = len(cameras)
            
            # Create service manager for each camera
            for camera in cameras:
                try:
                                        # Convert Device object to CameraDevice object
                    credentials = self.config_manager.get_credentials('camera') or {}
                    camera_device = CameraDevice(camera.ip_address, credentials)
                    
                    manager = CameraServiceManager(camera_device, self.config)
                    self.service_managers[camera.id] = manager
                    self.stats["initialized_cameras"] += 1
                    
                    self.log(f"Initialized service manager for camera: {camera.id}")
                    
                except Exception as e:
                    self.log(f"Failed to initialize service manager for camera {camera.id}: {e}")
            
            self.initialized = True
            self.log(f"Global camera service manager initialized with {self.stats['initialized_cameras']} cameras")
            return True
            
        except Exception as e:
            self.log(f"Failed to initialize global camera service manager: {e}")
            return False
    
    def start_all_services(self) -> bool:
        """Start all camera services."""
        if not self.initialized:
            if not self.initialize():
                return False
        
        if self.running:
            self.log("Services already running")
            return True
        
        try:
            self.running = True
            self.stats["start_time"] = datetime.now().isoformat()
            self.shutdown_event.clear()
            
            # Start control thread
            self.control_thread = threading.Thread(target=self._control_loop)
            self.control_thread.daemon = True
            self.control_thread.start()
            
            # Start individual camera services
            for camera_id, manager in self.service_managers.items():
                try:
                    if manager.start():
                        self.stats["running_cameras"] += 1
                        self.stats["service_status"][camera_id] = "running"
                        self.log(f"Started services for camera: {camera_id}")
                    else:
                        self.stats["service_status"][camera_id] = "failed"
                        self.log(f"Failed to start services for camera: {camera_id}")
                        
                except Exception as e:
                    self.stats["service_status"][camera_id] = "error"
                    self.log(f"Error starting services for camera {camera_id}: {e}")
            
            self.log(f"Started all camera services. Running: {self.stats['running_cameras']}/{self.stats['total_cameras']}")
            return True
            
        except Exception as e:
            self.log(f"Failed to start camera services: {e}")
            self.running = False
            return False
    
    def stop_all_services(self) -> bool:
        """Stop all camera services."""
        if not self.running:
            return True
        
        try:
            self.running = False
            self.shutdown_event.set()
            
            # Stop individual camera services
            for camera_id, manager in self.service_managers.items():
                try:
                    if manager.stop():
                        self.stats["service_status"][camera_id] = "stopped"
                        self.log(f"Stopped services for camera: {camera_id}")
                    else:
                        self.log(f"Failed to stop services for camera: {camera_id}")
                        
                except Exception as e:
                    self.log(f"Error stopping services for camera {camera_id}: {e}")
            
            # Wait for control thread to stop
            if self.control_thread:
                self.control_thread.join(timeout=10)
            
            self.stats["running_cameras"] = 0
            self.log("Stopped all camera services")
            return True
            
        except Exception as e:
            self.log(f"Error stopping camera services: {e}")
            return False
    
    def _control_loop(self):
        """Main control loop for monitoring and managing services."""
        while not self.shutdown_event.is_set() and self.running:
            try:
                # Update statistics
                self._update_statistics()
                
                # Check service health
                self._check_service_health()
                
                # Process any pending tasks
                self._process_pending_tasks()
                
                # Sleep for a bit
                self.shutdown_event.wait(timeout=5)
                
            except Exception as e:
                self.log(f"Error in control loop: {e}")
                time.sleep(1)
    
    def _update_statistics(self):
        """Update service statistics."""
        try:
            total_snapshots = 0
            total_motion = 0
            total_objects = 0
            
            for camera_id, manager in self.service_managers.items():
                status = manager.get_status()
                
                total_snapshots += status.get("total_snapshots", 0)
                total_motion += status.get("motion_events", 0)
                total_objects += status.get("object_detections", 0)
                
                # Update storage usage
                storage_stats = status.get("storage_stats", {})
                for backend, usage in storage_stats.items():
                    if backend not in self.stats["storage_usage"]:
                        self.stats["storage_usage"][backend] = 0
                    self.stats["storage_usage"][backend] += usage.get("total_files", 0)
            
            self.stats["total_snapshots"] = total_snapshots
            self.stats["total_motion_events"] = total_motion
            self.stats["total_object_detections"] = total_objects
            
        except Exception as e:
            self.log(f"Error updating statistics: {e}")
    
    def _check_service_health(self):
        """Check health of all camera services."""
        for camera_id, manager in self.service_managers.items():
            try:
                status = manager.get_status()
                if status.get("running", False):
                    self.stats["service_status"][camera_id] = "running"
                else:
                    self.stats["service_status"][camera_id] = "stopped"
                    
                    # Try to restart if it should be running
                    if self.running and status.get("should_run", False):
                        self.log(f"Restarting services for camera: {camera_id}")
                        manager.start()
                        
            except Exception as e:
                self.log(f"Error checking health for camera {camera_id}: {e}")
                self.stats["service_status"][camera_id] = "error"
    
    def _process_pending_tasks(self):
        """Process any pending tasks."""
        # This can be extended to handle queued tasks
        pass
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status of all camera services."""
        return {
            "running": self.running,
            "initialized": self.initialized,
            "enabled": self.enabled,
            "statistics": self.stats,
            "cameras": {
                camera_id: manager.get_status()
                for camera_id, manager in self.service_managers.items()
            }
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get detailed statistics."""
        return self.stats.copy()
    
    def take_snapshot(self, camera_id: str) -> Optional[Dict[str, Any]]:
        """Take a snapshot from a specific camera."""
        if camera_id not in self.service_managers:
            self.log(f"Camera not found: {camera_id}")
            return None
        
        try:
            manager = self.service_managers[camera_id]
            result = manager.take_snapshot()
            
            if result.get("success", False):
                self.stats["total_snapshots"] += 1
            
            return result
            
        except Exception as e:
            self.log(f"Error taking snapshot for camera {camera_id}: {e}")
            return None
    
    def get_service_manager(self, camera_id: str) -> Optional[CameraServiceManager]:
        """Get the service manager for a specific camera."""
        return self.service_managers.get(camera_id)
    
    def add_camera(self, camera_device, config: Dict[str, Any] = None) -> bool:
        """Add a new camera to the service manager."""
        try:
            if camera_device.id in self.service_managers:
                self.log(f"Camera already exists: {camera_device.id}")
                return False
            
            manager_config = config or self.config
            manager = CameraServiceManager(camera_device, manager_config)
            self.service_managers[camera_device.id] = manager
            self.stats["total_cameras"] += 1
            self.stats["initialized_cameras"] += 1
            
            # Start services if global manager is running
            if self.running:
                if manager.start():
                    self.stats["running_cameras"] += 1
                    self.stats["service_status"][camera_device.id] = "running"
                else:
                    self.stats["service_status"][camera_device.id] = "failed"
            
            self.log(f"Added camera: {camera_device.id}")
            return True
            
        except Exception as e:
            self.log(f"Failed to add camera {camera_device.id}: {e}")
            return False
    
    def remove_camera(self, camera_id: str) -> bool:
        """Remove a camera from the service manager."""
        if camera_id not in self.service_managers:
            return False
        
        try:
            manager = self.service_managers[camera_id]
            
            # Stop services if running
            if self.running:
                manager.stop()
            
            # Remove from managers
            del self.service_managers[camera_id]
            
            # Update statistics
            self.stats["total_cameras"] -= 1
            self.stats["initialized_cameras"] -= 1
            
            if camera_id in self.stats["service_status"]:
                del self.stats["service_status"][camera_id]
            
            self.log(f"Removed camera: {camera_id}")
            return True
            
        except Exception as e:
            self.log(f"Error removing camera {camera_id}: {e}")
            return False
    
    def log(self, message: str):
        """Log a message."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] [GlobalCameraManager] {message}")
    
    def cleanup(self):
        """Clean up resources."""
        self.stop_all_services()
        self.initialized = False


def main():
    """Command-line interface for the global camera service manager."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Global Camera Service Manager")
    parser.add_argument("command", choices=["start", "stop", "status", "restart", "snapshot"],
                       help="Command to execute")
    parser.add_argument("--camera", help="Camera ID (for snapshot command)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    manager = GlobalCameraServiceManager()
    
    if args.command == "start":
        if manager.start_all_services():
            print("Camera services started successfully")
            sys.exit(0)
        else:
            print("Failed to start camera services")
            sys.exit(1)
    
    elif args.command == "stop":
        if manager.stop_all_services():
            print("Camera services stopped successfully")
            sys.exit(0)
        else:
            print("Failed to stop camera services")
            sys.exit(1)
    
    elif args.command == "restart":
        manager.stop_all_services()
        time.sleep(2)
        if manager.start_all_services():
            print("Camera services restarted successfully")
            sys.exit(0)
        else:
            print("Failed to restart camera services")
            sys.exit(1)
    
    elif args.command == "status":
        status = manager.get_status()
        
        if args.verbose:
            import json
            print(json.dumps(status, indent=2))
        else:
            print(f"Running: {status['running']}")
            print(f"Initialized: {status['initialized']}")
            print(f"Enabled: {status['enabled']}")
            print(f"Total cameras: {status['statistics']['total_cameras']}")
            print(f"Running cameras: {status['statistics']['running_cameras']}")
            print(f"Total snapshots: {status['statistics']['total_snapshots']}")
    
    elif args.command == "snapshot":
        if not args.camera:
            print("Error: --camera argument required for snapshot command")
            sys.exit(1)
        
        result = manager.take_snapshot(args.camera)
        if result and result.get("success", False):
            print(f"Snapshot successful: {result.get('filename', 'Unknown')}")
            if args.verbose:
                import json
                print(json.dumps(result, indent=2))
            sys.exit(0)
        else:
            print(f"Snapshot failed: {result.get('error', 'Unknown error') if result else 'Unknown error'}")
            sys.exit(1)


if __name__ == "__main__":
    main()
