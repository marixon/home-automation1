"""
Camera Services API endpoints for enhanced camera functionality.
"""

from fastapi import APIRouter, HTTPException, Depends, Body
from typing import Dict, Any, List, Optional
from datetime import datetime
import json

from homeauto.database.repository import DeviceRepository
from homeauto.config.manager import ConfigManager
from homeauto.devices.camera import CameraDevice
from homeauto.services.camera.manager import CameraServiceManager

# Create router
router = APIRouter(prefix="/api/camera-services", tags=["camera-services"])

# Global service managers cache
_service_managers: Dict[str, CameraServiceManager] = {}
_config_manager = ConfigManager()
_device_repo = DeviceRepository()


def get_camera_device(device_id: str) -> CameraDevice:
    """Get camera device adapter for a device ID."""
    device = _device_repo.get(device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    if device.device_type != "camera":
        raise HTTPException(status_code=400, detail="Device is not a camera")
    
    credentials = _config_manager.get_credentials("camera") or {}
    return CameraDevice(device.ip_address, credentials)


def get_camera_service_manager(device_id: str) -> CameraServiceManager:
    """Get or create camera service manager for a device."""
    if device_id in _service_managers:
        return _service_managers[device_id]
    
    # Get camera device
    camera_device = get_camera_device(device_id)
    device = _device_repo.get(device_id)
    
    # Load camera services configuration
    config = _config_manager.get_config()
    camera_services_config = config.get("camera_services", {})
    
    # Get camera-specific configuration
    camera_config = camera_services_config.get("defaults", {}).copy()
    
    # Apply camera-specific overrides
    cameras_config = camera_services_config.get("cameras", {})
    if device.ip_address in cameras_config:
        camera_config.update(cameras_config[device.ip_address])
    
    # Add camera info to config
    camera_config["camera_name"] = device.name
    camera_config["camera_ip"] = device.ip_address
    
    # Create service manager
    service_manager = CameraServiceManager(camera_device, camera_config)
    
    # Store in cache
    _service_managers[device_id] = service_manager
    
    return service_manager


@router.get("/cameras/{device_id}/status")
async def get_camera_services_status(device_id: str):
    """Get status of all camera services for a camera."""
    try:
        service_manager = get_camera_service_manager(device_id)
        status = service_manager.get_status()
        return status
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting services status: {str(e)}")


@router.post("/cameras/{device_id}/initialize")
async def initialize_camera_services(device_id: str):
    """Initialize camera services for a camera."""
    try:
        service_manager = get_camera_service_manager(device_id)
        success = service_manager.initialize()
        
        return {
            "success": success,
            "device_id": device_id,
            "message": "Camera services initialized" if success else "Failed to initialize camera services"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error initializing services: {str(e)}")


@router.post("/cameras/{device_id}/start")
async def start_camera_services(device_id: str):
    """Start all camera services for a camera."""
    try:
        service_manager = get_camera_service_manager(device_id)
        
        # Initialize if not already initialized
        if not hasattr(service_manager, 'initialized') or not service_manager.initialized:
            service_manager.initialize()
        
        success = service_manager.start()
        
        return {
            "success": success,
            "device_id": device_id,
            "message": "Camera services started" if success else "Failed to start camera services"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error starting services: {str(e)}")


@router.post("/cameras/{device_id}/stop")
async def stop_camera_services(device_id: str):
    """Stop all camera services for a camera."""
    try:
        service_manager = get_camera_service_manager(device_id)
        success = service_manager.stop()
        
        return {
            "success": success,
            "device_id": device_id,
            "message": "Camera services stopped" if success else "Failed to stop camera services"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error stopping services: {str(e)}")


@router.post("/cameras/{device_id}/snapshot/now")
async def take_snapshot_now(
    device_id: str,
    metadata: Dict[str, Any] = Body(default=None)
):
    """Take a snapshot immediately."""
    try:
        service_manager = get_camera_service_manager(device_id)
        result = service_manager.take_snapshot(metadata)
        
        if result:
            return {
                "success": True,
                "device_id": device_id,
                "result": result,
                "timestamp": datetime.now().isoformat()
            }
        else:
            return {
                "success": False,
                "device_id": device_id,
                "message": "Failed to take snapshot",
                "timestamp": datetime.now().isoformat()
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error taking snapshot: {str(e)}")


@router.post("/cameras/{device_id}/snapshot/request")
async def request_snapshot(
    device_id: str,
    metadata: Dict[str, Any] = Body(default=None),
    priority: str = Body(default="normal")
):
    """Request a snapshot (adds to queue)."""
    try:
        service_manager = get_camera_service_manager(device_id)
        success = service_manager.request_snapshot(metadata, priority)
        
        return {
            "success": success,
            "device_id": device_id,
            "message": "Snapshot request queued" if success else "Failed to queue snapshot request",
            "priority": priority,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error requesting snapshot: {str(e)}")


@router.post("/cameras/{device_id}/schedules/{schedule_name}/execute")
async def execute_schedule(
    device_id: str,
    schedule_name: str,
    metadata: Dict[str, Any] = Body(default=None)
):
    """Execute a specific schedule immediately."""
    try:
        service_manager = get_camera_service_manager(device_id)
        result = service_manager.execute_schedule(schedule_name, metadata)
        
        if result:
            return {
                "success": True,
                "device_id": device_id,
                "schedule_name": schedule_name,
                "result": result,
                "timestamp": datetime.now().isoformat()
            }
        else:
            return {
                "success": False,
                "device_id": device_id,
                "schedule_name": schedule_name,
                "message": "Failed to execute schedule",
                "timestamp": datetime.now().isoformat()
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error executing schedule: {str(e)}")


@router.post("/cameras/{device_id}/schedules")
async def add_schedule(
    device_id: str,
    schedule_config: Dict[str, Any] = Body(...)
):
    """Add a new schedule."""
    try:
        service_manager = get_camera_service_manager(device_id)
        
        schedule_name = schedule_config.get("name")
        if not schedule_name:
            raise HTTPException(status_code=400, detail="Schedule name is required")
        
        success = service_manager.add_schedule(schedule_name, schedule_config)
        
        return {
            "success": success,
            "device_id": device_id,
            "schedule_name": schedule_name,
            "message": "Schedule added" if success else "Failed to add schedule"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error adding schedule: {str(e)}")


@router.delete("/cameras/{device_id}/schedules/{schedule_name}")
async def remove_schedule(device_id: str, schedule_name: str):
    """Remove a schedule."""
    try:
        service_manager = get_camera_service_manager(device_id)
        success = service_manager.remove_schedule(schedule_name)
        
        return {
            "success": success,
            "device_id": device_id,
            "schedule_name": schedule_name,
            "message": "Schedule removed" if success else "Failed to remove schedule"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error removing schedule: {str(e)}")


@router.get("/cameras/{device_id}/schedules")
async def get_schedules(device_id: str):
    """Get all schedules for a camera."""
    try:
        service_manager = get_camera_service_manager(device_id)
        scheduled_service = service_manager.get_service("scheduled")
        
        if not scheduled_service:
            return {
                "device_id": device_id,
                "schedules": [],
                "message": "Scheduled service not available"
            }
        
        schedule_info = scheduled_service.get_schedule_info()
        return {
            "device_id": device_id,
            "schedules": schedule_info.get("schedules", []),
            "active_schedules": schedule_info.get("active_schedules", {})
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting schedules: {str(e)}")


@router.post("/cameras/{device_id}/motion/check")
async def check_motion(device_id: str):
    """Manually trigger a motion check."""
    try:
        service_manager = get_camera_service_manager(device_id)
        result = service_manager.check_motion()
        
        if result:
            return {
                "success": True,
                "device_id": device_id,
                "result": result,
                "timestamp": datetime.now().isoformat()
            }
        else:
            return {
                "success": False,
                "device_id": device_id,
                "message": "Failed to check motion",
                "timestamp": datetime.now().isoformat()
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error checking motion: {str(e)}")


@router.post("/cameras/{device_id}/objects/check")
async def check_objects(device_id: str):
    """Manually trigger an object recognition check."""
    try:
        service_manager = get_camera_service_manager(device_id)
        result = service_manager.check_objects()
        
        if result:
            return {
                "success": True,
                "device_id": device_id,
                "result": result,
                "timestamp": datetime.now().isoformat()
            }
        else:
            return {
                "success": False,
                "device_id": device_id,
                "message": "Failed to check objects",
                "timestamp": datetime.now().isoformat()
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error checking objects: {str(e)}")


@router.get("/cameras/{device_id}/snapshots")
async def get_snapshots(
    device_id: str,
    limit: int = 20,
    prefix: str = ""
):
    """Get stored snapshots for a camera."""
    try:
        service_manager = get_camera_service_manager(device_id)
        snapshots = service_manager.get_snapshots(limit)
        
        return {
            "device_id": device_id,
            "snapshots": snapshots,
            "count": sum(len(files) for files in snapshots.values()),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting snapshots: {str(e)}")


@router.get("/cameras/{device_id}/services/{service_name}/status")
async def get_service_status(device_id: str, service_name: str):
    """Get status of a specific service."""
    try:
        service_manager = get_camera_service_manager(device_id)
        status = service_manager.get_service_status(service_name)
        
        if status:
            return {
                "device_id": device_id,
                "service_name": service_name,
                "status": status
            }
        else:
            raise HTTPException(status_code=404, detail=f"Service '{service_name}' not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting service status: {str(e)}")


@router.get("/cameras/{device_id}/queue")
async def get_queue_info(device_id: str):
    """Get information about the snapshot request queue."""
    try:
        service_manager = get_camera_service_manager(device_id)
        on_demand_service = service_manager.get_service("on_demand")
        
        if not on_demand_service:
            return {
                "device_id": device_id,
                "queue_info": None,
                "message": "On-demand service not available"
            }
        
        queue_info = on_demand_service.get_queue_info()
        return {
            "device_id": device_id,
            "queue_info": queue_info
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting queue info: {str(e)}")


@router.get("/health")
async def camera_services_health():
    """Health check for camera services."""
    try:
        # Check if any service managers are initialized
        initialized_count = sum(1 for sm in _service_managers.values() if sm.initialized)
        running_count = sum(1 for sm in _service_managers.values() if sm.running)
        
        return {
            "status": "healthy",
            "service_managers_count": len(_service_managers),
            "initialized_services": initialized_count,
            "running_services": running_count,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")


@router.get("/cameras")
async def get_cameras_with_services():
    """Get all cameras with their service status."""
    try:
        cameras = []
        all_devices = _device_repo.get_all()
        
        for device in all_devices:
            if device.device_type == "camera":
                camera_info = {
                    "id": device.id,
                    "name": device.name,
                    "ip_address": device.ip_address,
                    "online": False,
                    "services_available": False,
                    "services_running": False
                }
                
                # Check if service manager exists
                if device.id in _service_managers:
                    service_manager = _service_managers[device.id]
                    camera_info["services_available"] = service_manager.initialized
                    camera_info["services_running"] = service_manager.running
                
                # Check camera connectivity
                try:
                    camera_device = get_camera_device(device.id)
                    camera_info["online"] = camera_device.test_connection()
                except:
                    camera_info["online"] = False
                
                cameras.append(camera_info)
        
        return {
            "cameras": cameras,
            "count": len(cameras),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting cameras: {str(e)}")
