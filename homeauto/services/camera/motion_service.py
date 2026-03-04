"""
Motion detection service for cameras.
"""

import threading
import time
import queue
from typing import Dict, Any, Optional, List
from datetime import datetime
import numpy as np
from .base_service import SnapshotService
from homeauto.analytics.camera_analytics import MotionDetector, CameraAnalytics


class MotionDetectionService(SnapshotService):
    """Service for taking snapshots on motion detection."""
    
    def __init__(self, camera_device, config: Dict[str, Any]):
        super().__init__(camera_device, config)
        
        # Motion detection configuration
        self.motion_config = config.get("motion_config", {})
        self.min_confidence = config.get("min_confidence", 0.5)
        self.cooldown = config.get("cooldown", 30)  # seconds
        self.continuous_mode = config.get("continuous_mode", False)
        self.frame_interval = config.get("frame_interval", 1.0)  # seconds between frames
        
        # Motion detection components
        self.motion_detector = None
        self.camera_analytics = None
        self.frame_queue = queue.Queue(maxsize=10)
        self.processing_thread = None
        self.capture_thread = None
        
        # Motion statistics
        self.motion_stats = {
            "motion_events": 0,
            "motion_detections": 0,
            "snapshots_triggered": 0,
            "last_motion_time": None,
            "last_motion_confidence": 0,
            "cooldown_active": False
        }
        
        # Last motion detection time for cooldown
        self.last_trigger_time = 0
    
    def start(self) -> bool:
        """Start the motion detection service."""
        if self.running:
            self.logger.warning("Service already running")
            return True
        
        try:
            # Initialize motion detector
            self._initialize_motion_detector()
            
            if not self.motion_detector or not self.motion_detector.opencv_available:
                self.logger.error("OpenCV not available for motion detection")
                return False
            
            # Start processing thread
            self.running = True
            self.processing_thread = threading.Thread(target=self._process_frames)
            self.processing_thread.daemon = True
            self.processing_thread.start()
            
            # Start frame capture thread if continuous mode
            if self.continuous_mode:
                self.capture_thread = threading.Thread(target=self._capture_frames)
                self.capture_thread.daemon = True
                self.capture_thread.start()
            
            self.stats["start_time"] = datetime.now().isoformat()
            self.logger.info("Motion detection service started")
            self._trigger_callbacks("on_start")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start motion detection service: {e}")
            self.running = False
            return False
    
    def stop(self) -> bool:
        """Stop the motion detection service."""
        if not self.running:
            return True
        
        try:
            self.running = False
            
            # Wait for threads to stop
            if self.processing_thread:
                self.processing_thread.join(timeout=5)
            
            if self.capture_thread:
                self.capture_thread.join(timeout=5)
            
            # Clear queue
            while not self.frame_queue.empty():
                try:
                    self.frame_queue.get_nowait()
                except queue.Empty:
                    break
            
            self.logger.info("Motion detection service stopped")
            self._trigger_callbacks("on_stop")
            return True
            
        except Exception as e:
            self.logger.error(f"Error stopping motion detection service: {e}")
            return False
    
    def _initialize_motion_detector(self):
        """Initialize motion detection components."""
        try:
            # Create motion detector
            self.motion_detector = MotionDetector(self.motion_config)
            
            # Create camera analytics (for more advanced features)
            analytics_config = {
                "name": self.config.get("camera_name", "Camera"),
                "ip": self.camera.ip,
                "motion_config": self.motion_config
            }
            self.camera_analytics = CameraAnalytics(analytics_config)
            
            self.logger.info("Motion detector initialized")
            
        except Exception as e:
            self.logger.error(f"Error initializing motion detector: {e}")
    
    def _capture_frames(self):
        """Background thread for capturing frames in continuous mode."""
        self.logger.debug("Frame capture thread started")
        
        while self.running:
            try:
                # Capture frame from camera
                frame = self._capture_frame()
                if frame is not None:
                    # Add frame to processing queue
                    try:
                        self.frame_queue.put_nowait(frame)
                    except queue.Full:
                        # Queue full, drop frame
                        pass
                
                # Wait for next frame
                time.sleep(self.frame_interval)
                
            except Exception as e:
                self.logger.error(f"Error capturing frame: {e}")
                time.sleep(self.frame_interval)  # Wait before retry
        
        self.logger.debug("Frame capture thread stopped")
    
    def _capture_frame(self) -> Optional[np.ndarray]:
        """Capture a frame from the camera."""
        try:
            # Get snapshot from camera
            snapshot_result = self.camera.get_snapshot()
            
            if not snapshot_result.get("success", False):
                self.logger.debug("Failed to capture frame from camera")
                return None
            
            # Check if it's a placeholder
            if snapshot_result.get("is_placeholder", False):
                self.logger.debug("Camera offline, using placeholder")
                return None
            
            # Decode image data
            import base64
            import cv2
            
            image_data = base64.b64decode(snapshot_result["image_data"])
            
            # Convert to numpy array
            nparr = np.frombuffer(image_data, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if frame is None:
                self.logger.debug("Failed to decode image")
                return None
            
            return frame
            
        except Exception as e:
            self.logger.debug(f"Error capturing frame: {e}")
            return None
    
    def _process_frames(self):
        """Background thread for processing frames for motion detection."""
        self.logger.debug("Frame processing thread started")
        
        while self.running:
            try:
                # Get frame from queue with timeout
                try:
                    frame = self.frame_queue.get(timeout=1)
                except queue.Empty:
                    # No frames in queue, check if we should capture one
                    if not self.continuous_mode:
                        # In non-continuous mode, capture a single frame
                        frame = self._capture_frame()
                        if frame is None:
                            continue
                    else:
                        # In continuous mode, just wait for next frame
                        continue
                
                # Process frame for motion detection
                self._process_frame(frame)
                
                # Mark task as done if it came from queue
                if self.continuous_mode:
                    self.frame_queue.task_done()
                
            except Exception as e:
                self.logger.error(f"Error processing frame: {e}")
        
        self.logger.debug("Frame processing thread stopped")
    
    def _process_frame(self, frame: np.ndarray):
        """Process a single frame for motion detection."""
        try:
            # Detect motion
            motion_result = self.motion_detector.detect(frame)
            
            if motion_result["detected"]:
                self.motion_stats["motion_detections"] += 1
                self.motion_stats["last_motion_confidence"] = motion_result["confidence"]
                self.motion_stats["last_motion_time"] = datetime.now().isoformat()
                
                # Check cooldown
                current_time = time.time()
                can_trigger = (current_time - self.last_trigger_time) >= self.cooldown
                
                if can_trigger and motion_result["confidence"] >= self.min_confidence:
                    # Trigger snapshot
                    self._trigger_motion_snapshot(frame, motion_result)
                    self.last_trigger_time = current_time
                    self.motion_stats["cooldown_active"] = True
                    
                    # Schedule cooldown reset
                    threading.Timer(self.cooldown, self._reset_cooldown).start()
                
                # Trigger motion event callback
                event_data = {
                    "motion_result": motion_result,
                    "frame_shape": frame.shape,
                    "triggered_snapshot": can_trigger and motion_result["confidence"] >= self.min_confidence
                }
                self._trigger_callbacks("on_event", "motion_detected", event_data)
            
        except Exception as e:
            self.logger.error(f"Error in motion detection: {e}")
    
    def _trigger_motion_snapshot(self, frame: np.ndarray, motion_result: Dict[str, Any]):
        """Trigger a snapshot due to motion detection."""
        self.logger.info(f"Motion detected! Confidence: {motion_result['confidence']:.2f}")
        
        # Prepare metadata
        metadata = {
            "trigger_type": "motion",
            "motion_confidence": motion_result["confidence"],
            "motion_regions": motion_result["regions"],
            "motion_count": motion_result["count"],
            "total_motion_detections": motion_result["total_detections"]
        }
        
        # Take and save snapshot
        result = self._process_and_save_snapshot("motion", metadata)
        
        if result:
            self.motion_stats["snapshots_triggered"] += 1
            self.motion_stats["motion_events"] += 1
            
            # Trigger motion snapshot event
            event_data = {
                "motion_result": motion_result,
                "snapshot_result": result,
                "frame_shape": frame.shape
            }
            self._trigger_callbacks("on_event", "motion_snapshot", event_data)
            
            self.logger.info(f"Motion snapshot saved successfully")
        else:
            self.logger.warning("Failed to save motion snapshot")
    
    def _reset_cooldown(self):
        """Reset the cooldown flag."""
        self.motion_stats["cooldown_active"] = False
        self.logger.debug("Motion cooldown reset")
    
    def trigger_manual_motion_check(self) -> Optional[Dict[str, Any]]:
        """
        Manually trigger a motion check.
        
        Returns:
            Motion detection results, or None if failed
        """
        self.logger.info("Manual motion check triggered")
        
        try:
            # Capture frame
            frame = self._capture_frame()
            if frame is None:
                self.logger.warning("Failed to capture frame for manual check")
                return None
            
            # Detect motion
            motion_result = self.motion_detector.detect(frame)
            
            # Prepare response
            response = {
                "motion_detected": motion_result["detected"],
                "confidence": motion_result["confidence"],
                "regions": motion_result["regions"],
                "count": motion_result["count"],
                "frame_shape": frame.shape,
                "timestamp": datetime.now().isoformat()
            }
            
            # Trigger snapshot if motion detected
            if motion_result["detected"] and motion_result["confidence"] >= self.min_confidence:
                self._trigger_motion_snapshot(frame, motion_result)
            
            return response
            
        except Exception as e:
            self.logger.error(f"Error in manual motion check: {e}")
            return None
    
    def get_status(self) -> Dict[str, Any]:
        """Get service status."""
        base_status = super().get_status()
        
        # Calculate cooldown remaining
        cooldown_remaining = 0
        if self.motion_stats["cooldown_active"]:
            elapsed = time.time() - self.last_trigger_time
            cooldown_remaining = max(0, self.cooldown - elapsed)
        
        status = {
            **base_status,
            "service_type": "motion_detection",
            "continuous_mode": self.continuous_mode,
            "frame_interval": self.frame_interval,
            "cooldown": self.cooldown,
            "cooldown_remaining": cooldown_remaining,
            "min_confidence": self.min_confidence,
            "motion_stats": self.motion_stats,
            "queue_size": self.frame_queue.qsize(),
            "opencv_available": self.motion_detector and self.motion_detector.opencv_available if self.motion_detector else False,
            "processing_thread_alive": self.processing_thread and self.processing_thread.is_alive() if self.processing_thread else False,
            "capture_thread_alive": self.capture_thread and self.capture_thread.is_alive() if self.capture_thread else False
        }
        
        return status
    
    def get_motion_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent motion detection history."""
        # This would typically query a database
        # For now, return a simplified version
        history = []
        
        # Add current stats as a history entry
        if self.motion_stats["last_motion_time"]:
            history.append({
                "timestamp": self.motion_stats["last_motion_time"],
                "confidence": self.motion_stats["last_motion_confidence"],
                "snapshot_triggered": self.motion_stats["snapshots_triggered"] > 0,
                "type": "motion"
            })
        
        return history[:limit]
