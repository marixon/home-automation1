#!/usr/bin/env python3
"""
Camera Services Examples

This file contains practical examples of using the camera services enhancement.
"""

import sys
import os
import time
from datetime import datetime

# Add the project to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def example_basic_usage():
    """Example 1: Basic camera services usage."""
    print("=" * 60)
    print("Example 1: Basic Camera Services Usage")
    print("=" * 60)
    
    try:
        from homeauto.services.camera.global_manager import get_global_manager
        
        # Get the global manager
        manager = get_global_manager()
        
        # Initialize all camera services
        print("Initializing camera services...")
        if manager.initialize():
            print("✓ Camera services initialized successfully")
            print(f"  - Total cameras: {manager.stats['total_cameras']}")
            print(f"  - Initialized cameras: {manager.stats['initialized_cameras']}")
        else:
            print("✗ Failed to initialize camera services")
            return
        
        # Start all services
        print("\nStarting camera services...")
        if manager.start_all():
            print("✓ Camera services started successfully")
            print(f"  - Running cameras: {manager.stats['running_cameras']}")
        else:
            print("✗ Failed to start camera services")
        
        # Get global status
        print("\nGetting global status...")
        status = manager.get_status()
        print(f"  - Services enabled: {status['enabled']}")
        print(f"  - Services running: {status['running']}")
        print(f"  - Auto-start: {status['auto_start']}")
        
        # Stop all services
        print("\nStopping camera services...")
        if manager.stop_all():
            print("✓ Camera services stopped successfully")
        
    except ImportError as e:
        print(f"✗ Import error: {e}")
        print("Make sure camera services modules are available")
    except Exception as e:
        print(f"✗ Error: {e}")


def example_individual_camera():
    """Example 2: Working with individual camera services."""
    print("\n" + "=" * 60)
    print("Example 2: Individual Camera Services")
    print("=" * 60)
    
    try:
        from homeauto.database.repository import DeviceRepository
        from homeauto.config.manager import ConfigManager
        from homeauto.devices.camera import CameraDevice
        from homeauto.services.camera.manager import CameraServiceManager
        
        # Get camera from database
        repo = DeviceRepository()
        config_manager = ConfigManager()
        
        # Find a camera device
        cameras = [d for d in repo.get_all() if d.device_type == 'camera']
        if not cameras:
            print("No cameras found in database")
            return
        
        camera_device = cameras[0]
        print(f"Using camera: {camera_device.name} ({camera_device.ip_address})")
        
        # Get credentials
        credentials = config_manager.get_credentials('camera') or {}
        
        # Create camera device
        camera = CameraDevice(camera_device.ip_address, credentials)
        
        # Create service manager configuration
        service_config = {
            "camera_name": camera_device.name,
            "camera_ip": camera_device.ip_address,
            "storage": {
                "local": {
                    "enabled": True,
                    "base_path": "./camera_snapshots",
                    "organization": "by_date"
                }
            },
            "services": {
                "on_demand": {
                    "enabled": True,
                    "max_queue_size": 5,
                    "storage": ["local"]
                },
                "scheduled": {
                    "enabled": True,
                    "schedules": [
                        {
                            "name": "test_schedule",
                            "interval_seconds": 10,  # Every 10 seconds for testing
                            "quality": "low",
                            "storage": ["local"]
                        }
                    ]
                }
            }
        }
        
        # Create and initialize service manager
        print("\nCreating camera service manager...")
        service_manager = CameraServiceManager(camera, service_config)
        
        if service_manager.initialize():
            print("✓ Service manager initialized")
        else:
            print("✗ Failed to initialize service manager")
            return
        
        # Start services
        print("\nStarting camera services...")
        if service_manager.start():
            print("✓ Camera services started")
            
            # Take a snapshot
            print("\nTaking snapshot...")
            result = service_manager.take_snapshot({
                "source": "example",
                "timestamp": datetime.now().isoformat()
            })
            
            if result:
                print("✓ Snapshot taken successfully")
                print(f"  - Storage results: {len(result.get('storage', {}))} backends")
            else:
                print("✗ Failed to take snapshot")
            
            # Request a snapshot (queued)
            print("\nRequesting snapshot (queued)...")
            if service_manager.request_snapshot({"priority": "high"}):
                print("✓ Snapshot request queued")
            
            # Get service status
            print("\nGetting service status...")
            status = service_manager.get_status()
            print(f"  - Running: {status['running']}")
            print(f"  - Snapshots taken: {status['stats']['snapshots_taken']}")
            print(f"  - Services available: {status['services_available']}")
            
            # Wait a bit for scheduled snapshot
            print("\nWaiting for scheduled snapshot (10 seconds)...")
            time.sleep(12)
            
            # Get updated status
            status = service_manager.get_status()
            print(f"  - Snapshots taken (after wait): {status['stats']['snapshots_taken']}")
            
            # Stop services
            print("\nStopping camera services...")
            if service_manager.stop():
                print("✓ Camera services stopped")
            
        else:
            print("✗ Failed to start camera services")
        
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()


def example_storage_management():
    """Example 3: Storage management examples."""
    print("\n" + "=" * 60)
    print("Example 3: Storage Management")
    print("=" * 60)
    
    try:
        from homeauto.services.camera.storage import StorageManager
        
        # Create storage configuration
        storage_config = {
            "local": {
                "enabled": True,
                "base_path": "./example_snapshots",
                "organization": "flat",
                "max_files": 50
            },
            "test_ftp": {
                "enabled": False,  # Disabled for example
                "type": "ftp",
                "host": "localhost",
                "username": "test",
                "password": "test"
            }
        }
        
        # Create storage manager
        print("Creating storage manager...")
        storage_manager = StorageManager(storage_config)
        
        # Initialize storage backends
        if storage_manager.initialize():
            print("✓ Storage manager initialized")
            print(f"  - Backends initialized: {len(storage_manager.backends)}")
            
            # Create test image data
            print("\nCreating test image...")
            from PIL import Image, ImageDraw
            import io
            
            # Create a simple test image
            img = Image.new('RGB', (640, 480), color='blue')
            draw = ImageDraw.Draw(img)
            draw.text((100, 100), "Test Snapshot", fill='white')
            
            # Convert to bytes
            img_bytes = io.BytesIO()
            img.save(img_bytes, format='JPEG')
            image_data = img_bytes.getvalue()
            
            # Save to storage
            print("Saving test image...")
            filename = f"test_snapshot_{int(time.time())}.jpg"
            metadata = {
                "camera": "test_camera",
                "timestamp": datetime.now().isoformat(),
                "test": True
            }
            
            results = storage_manager.save_to_all(image_data, filename, metadata)
            
            print(f"✓ Saved to {len(results)} storage backends")
            for backend_name, result in results.items():
                success = result.get('success', False)
                status = "✓" if success else "✗"
                print(f"  {status} {backend_name}: {result.get('message', 'Unknown')}")
            
            # List files
            print("\nListing stored files...")
            all_files = storage_manager.list_all_files(limit=5)
            
            for backend_name, files in all_files.items():
                print(f"\n{backend_name}:")
                for file_info in files[:3]:  # Show first 3 files
                    print(f"  - {file_info['filename']} ({file_info.get('size', 0)} bytes)")
            
            # Get storage status
            print("\nGetting storage status...")
            status = storage_manager.get_status()
            print(f"  - Initialized: {status['initialized']}")
            print(f"  - Backends: {len(status['backends'])}")
            
            # Cleanup
            print("\nCleaning up...")
            storage_manager.cleanup()
            print("✓ Storage manager cleaned up")
            
        else:
            print("✗ Failed to initialize storage manager")
        
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()


def example_api_usage():
    """Example 4: Using the REST API."""
    print("\n" + "=" * 60)
    print("Example 4: REST API Usage Examples")
    print("=" * 60)
    
    print("""
The camera services enhancement provides a comprehensive REST API.

Here are the main endpoints:

1. Initialize camera services:
   POST /api/camera-services/cameras/{device_id}/initialize

2. Start all services for a camera:
   POST /api/camera-services/cameras/{device_id}/start

3. Take immediate snapshot:
   POST /api/camera-services/cameras/{device_id}/snapshot/now
   Body: {"metadata": {"source": "manual"}}

4. Request snapshot (queued):
   POST /api/camera-services/cameras/{device_id}/snapshot/request
   Body: {"metadata": {...}, "priority": "normal"}

5. Check motion:
   POST /api/camera-services/cameras/{device_id}/motion/check

6. Check objects:
   POST /api/camera-services/cameras/{device_id}/objects/check

7. Get service status:
   GET /api/camera-services/cameras/{device_id}/status

8. Get stored snapshots:
   GET /api/camera-services/cameras/{device_id}/snapshots?limit=10

9. Health check:
   GET /api/camera-services/health

10. List all cameras:
    GET /api/camera-services/cameras

Example curl commands:
""")
    
    print("""# Initialize services for camera 1
curl -X POST http://localhost:8000/api/camera-services/cameras/1/initialize

# Take snapshot
curl -X POST http://localhost:8000/api/camera-services/cameras/1/snapshot/now \\
  -H "Content-Type: application/json" \\
  -d '{"metadata": {"source": "curl_test"}}'

# Get status
curl http://localhost:8000/api/camera-services/cameras/1/status

# Health check
curl http://localhost:8000/api/camera-services/health
""")


def example_web_interface():
    """Example 5: Using the web interface."""
    print("\n" + "=" * 60)
    print("Example 5: Web Interface")
    print("=" * 60)
    
    print("""
The camera services enhancement includes a web interface for easy management.

Access the interface at:
  http://localhost:8000/static/camera_services.html

Features:
1. Camera Overview
   - View all cameras with service status
   - See which cameras are online/offline
   - Check which services are running

2. Service Management
   - Start/stop individual services
   - Initialize camera services
   - View detailed service status

3. Snapshot Controls
   - Take immediate snapshots
   - View snapshot queue status
   - Check storage backends

4. Monitoring
   - Real-time service status
   - Snapshot statistics
   - Error tracking

5. Storage Management
   - View stored snapshots
   - Check storage backend status
   - Monitor storage usage

To use the web interface:
1. Start the web server:
   python -m homeauto.web.api
   or
   uvicorn homeauto.web.api:app --reload

2. Open your browser to:
   http://localhost:8000/static/camera_services.html

3. Click "Refresh Cameras" to load available cameras

4. Use the controls to manage camera services
""")


def example_advanced_configuration():
    """Example 6: Advanced configuration examples."""
    print("\n" + "=" * 60)
    print("Example 6: Advanced Configuration")
    print("=" * 60)
    
    print("""
Advanced configuration options:

1. Multiple Storage Backends:
```yaml
storage:
  local_primary:
    enabled: true
    base_path: "/mnt/primary/snapshots"
    organization: "by_date"
  
  local_backup:
    enabled: true
    base_path: "/mnt/backup/snapshots"
    organization: "by_camera"
  
  cloud_ftp:
    enabled: true
    type: "ftp"
    host: "cloud.example.com"
    remote_path: "/backups/{camera_name}"
  
  google_drive:
    enabled: true
    type: "google_drive"
    folder_id: "your_folder_id"
```

2. Complex Scheduling:
```yaml
schedules:
  - name: "business_hours"
    cron: "*/15 9-17 * * 1-5"  # Every 15 minutes, 9AM-5PM, Mon-Fri
    quality: "high"
    storage: ["local_primary", "cloud_ftp"]
  
  - name: "night_mode"
    cron: "0 */2 20-6 * * *"  # Every 2 hours, 8PM-6AM
    quality: "medium"
    storage: ["local_primary"]
  
  - name: "weekend"
    cron: "0 0 */3 * * 6,0"  # Every 3 hours on weekends
    quality: "low"
    storage: ["local_backup"]
```

3. Intelligent Motion Detection:
```yaml
motion_detected:
  enabled: true
  min_confidence: 0.3  # Very sensitive during day
  cooldown: 10
  frame_interval: 0.5
  
  # Time-based sensitivity
  sensitivity_schedule:
    - time: "06:00-18:00"  # Daytime
      min_confidence: 0.3
      cooldown: 10
    
    - time: "18:00-22:00"  # Evening
      min_confidence: 0.5
      cooldown: 20
    
    - time: "22:00-06:00"  # Night
      min_confidence: 0.7
      cooldown: 30
  
  # Zone-based detection
  detection_zones:
    - name: "entryway"
      coordinates: [[100, 100], [300, 100], [300, 300], [100, 300]]
      sensitivity: 0.4
    
    - name: "driveway"
      coordinates: [[400, 50], [600, 50], [600, 200], [400, 200]]
      sensitivity: 0.6
```

4. Object Recognition Pipeline:
```yaml
object_recognition:
  enabled: true
  
  # Detection pipeline
  pipeline:
    - stage: "face_detection"
      enabled: true
      model: "haarcascade"
      min_confidence: 0.8
    
    - stage: "person_detection"
      enabled: true
      model: "yolov8n"
      min_confidence: 0.6
    
    - stage: "vehicle_detection"
      enabled: true
      model: "yolov8n"
      classes: ["car", "truck", "motorcycle"]
      min_confidence: 0.7
    
    - stage: "animal_detection"
      enabled: true
      model: "yolov8n"
      classes: ["dog", "cat", "bird"]
      min_confidence: 0.5
  
  # Alert rules
  alerts:
    - objects: ["person"]
      min_confidence: 0.7
      cooldown: 300  # 5 minutes
      notify: ["email", "webhook"]
    
    - objects: ["car"]
      min_confidence: 0.8
      cooldown: 600  # 10 minutes
      notify: ["webhook"]
    
    - objects: ["dog", "cat"]
      min_confidence: 0.6
      cooldown: 900  # 15 minutes
      notify: ["email"]
```

5. Performance Optimization:
```yaml
performance:
  # Resource limits
  max_concurrent_cameras: 4
  frame_processing_threads: 2
  storage_upload_threads: 3
  
  # Memory management
  cache_size_mb: 200
  frame_buffer_size: 10
  cleanup_batch_size: 50
  
  # Processing optimization
  skip_frames: 2  # Process every 3rd frame
  downsample_ratio: 0.5  # Process at half resolution
  jpeg_quality: 80
  
  # Storage optimization
  compress_snapshots: true
  compression_level: 6
  deduplicate: true
  retention_days: 30
```

6. Notification System:
```yaml
notifications:
  enabled: true
  
  # Email notifications
  email:
    enabled: true
    smtp_host: "${SMTP_HOST}"
    smtp_port: 587
    smtp_username: "${SMTP_USERNAME}"
    smtp_password: "${SMTP_PASSWORD}"
    from_email: "security@example.com"
    to_emails:
      - "admin@example.com"
      - "security@example.com"
    
    # Email templates
    templates:
      motion_detected:
        subject: "Motion detected at {camera_name}"
        body: "Motion detected with confidence {confidence}%"
      
      object_detected:
        subject: "{object} detected at {camera_name}"
        body: "Detected {object} with confidence {confidence}%"
  
  # Webhook notifications
  webhook:
    enabled: true
    url: "https://api.example.com/events"
    secret: "${WEBHOOK_SECRET}"
    timeout: 5
    retry_attempts: 3
    
    # Event filtering
    events:
      - "motion_detected"
      - "object_detected"
      - "snapshot_saved"
      - "service_started"
      - "service_stopped"
      - "error_occurred"
  
  # Mobile push notifications
  push:
    enabled: false
    service: "fcm"  # or "apns", "webpush"
    api_key: "${PUSH_API_KEY}"
    topic: "camera_alerts"
  
  # Rate limiting
  rate_limiting:
    max_alerts_per_hour: 20
    cooldown_per_camera: 300
    quiet_hours: "23:00-06:00"
```
""")


def main():
    """Run all examples."""
    print("Camera Services Enhancement - Examples")
    print("=" * 60)
    
    # Create example directory
    os.makedirs("./camera_snapshots", exist_ok=True)
    os.makedirs("./example_snapshots", exist_ok=True)
    
    # Run examples
    example_basic_usage()
    example_individual_camera()
    example_storage_management()
    example_api_usage()
    example_web_interface()
    example_advanced_configuration()
    
    print("\n" + "=" * 60)
    print("Examples completed!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Review the configuration examples")
    print("2. Update your config.yaml file")
    print("3. Start the web server: python -m homeauto.web.api")
    print("4. Access the web interface: http://localhost:8000/static/camera_services.html")
    print("5. Test with the API examples")


if __name__ == "__main__":
    main()
