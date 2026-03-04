"""
Object recognition service for cameras.
"""

import threading
import time
import queue
from typing import Dict, Any, Optional, List
from datetime import datetime
import numpy as np
from .base_service import SnapshotService
from homeauto.analytics.camera_analytics import FaceDetector


class ObjectRecognitionService(SnapshotService):
    """Service for object and shape recognition in camera snapshots."""
    
    def __init__(self, camera_device, config: Dict[str, Any]):
        super().__init__(camera_device, config)
        
        # Object recognition configuration
        self.recognition_config = config.get("recognition_config", {})
        self.objects_to_detect = config.get("objects_to_detect", ["person", "car", "dog", "cat"])
        self.min_confidence = config.get("min_confidence", 0.7)
        self.cooldown = config.get("cooldown", 60)  # seconds
        self.annotate_images = config.get("annotate_images", True)
        self.save_annotated = config.get("save_annotated", True)
        
        # Recognition components
        self.face_detector = None
        self.object_detector = None
        self.frame_queue = queue.Queue(maxsize=10)
        self.processing_thread = None
        self.capture_thread = None
        self.frame_interval = config.get("frame_interval", 2.0)  # seconds between frames
        
        # Recognition statistics
        self.recognition_stats = {
            "total_detections": 0,
            "object_detections": {},
            "face_detections": 0,
            "snapshots_triggered": 0,
            "last_detection_time": None,
            "last_detected_objects": [],
            "cooldown_active": False
        }
        
        # Initialize object counts
        for obj in self.objects_to_detect:
            self.recognition_stats["object_detections"][obj] = 0
        
        # Last recognition trigger time for cooldown
        self.last_trigger_time = 0
    
    def start(self) -> bool:
        """Start the object recognition service."""
        if self.running:
            self.logger.warning("Service already running")
            return True
        
        try:
            # Initialize recognition components
            self._initialize_recognition()
            
            # Start processing thread
            self.running = True
            self.processing_thread = threading.Thread(target=self._process_frames)
            self.processing_thread.daemon = True
            self.processing_thread.start()
            
            # Start frame capture thread
            self.capture_thread = threading.Thread(target=self._capture_frames)
            self.capture_thread.daemon = True
            self.capture_thread.start()
            
            self.stats["start_time"] = datetime.now().isoformat()
            self.logger.info("Object recognition service started")
            self._trigger_callbacks("on_start")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start object recognition service: {e}")
            self.running = False
            return False
    
    def stop(self) -> bool:
        """Stop the object recognition service."""
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
            
            self.logger.info("Object recognition service stopped")
            self._trigger_callbacks("on_stop")
            return True
            
        except Exception as e:
            self.logger.error(f"Error stopping object recognition service: {e}")
            return False
    
    def _initialize_recognition(self):
        """Initialize object recognition components."""
        try:
            # Initialize face detector
            self.face_detector = FaceDetector(self.recognition_config)
            
            # Initialize object detector (if available)
            self._initialize_object_detector()
            
            self.logger.info("Object recognition initialized")
            
        except Exception as e:
            self.logger.error(f"Error initializing object recognition: {e}")
    
    def _initialize_object_detector(self):
        """Initialize object detector (YOLO, COCO, etc.)."""
        try:
            # Try to import Ultralytics YOLO
            try:
                from ultralytics import YOLO
                
                # Load model
                model_path = self.recognition_config.get("model_path", "yolov8n.pt")
                self.object_detector = YOLO(model_path)
                
                self.logger.info(f"YOLO object detector initialized with model: {model_path}")
                
            except ImportError:
                self.logger.warning("Ultralytics YOLO not available. Object detection limited to faces.")
                self.object_detector = None
                
        except Exception as e:
            self.logger.error(f"Error initializing object detector: {e}")
            self.object_detector = None
    
    def _capture_frames(self):
        """Background thread for capturing frames."""
        self.logger.debug("Object recognition frame capture thread started")
        
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
        
        self.logger.debug("Object recognition frame capture thread stopped")
    
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
        """Background thread for processing frames for object recognition."""
        self.logger.debug("Object recognition processing thread started")
        
        while self.running:
            try:
                # Get frame from queue with timeout
                try:
                    frame = self.frame_queue.get(timeout=1)
                except queue.Empty:
                    # No frames in queue, continue waiting
                    continue
                
                # Process frame for object recognition
                self._process_frame(frame)
                
                # Mark task as done
                self.frame_queue.task_done()
                
            except Exception as e:
                self.logger.error(f"Error processing frame: {e}")
        
        self.logger.debug("Object recognition processing thread stopped")
    
    def _process_frame(self, frame: np.ndarray):
        """Process a single frame for object recognition."""
        try:
            # Detect objects
            detection_results = self._detect_objects(frame)
            
            if detection_results["detected"]:
                self.recognition_stats["total_detections"] += 1
                self.recognition_stats["last_detection_time"] = datetime.now().isoformat()
                self.recognition_stats["last_detected_objects"] = detection_results["objects"]
                
                # Update object counts
                for obj_info in detection_results["objects"]:
                    obj_name = obj_info["name"]
                    if obj_name in self.recognition_stats["object_detections"]:
                        self.recognition_stats["object_detections"][obj_name] += 1
                
                # Check for face detections
                if detection_results.get("faces_detected", 0) > 0:
                    self.recognition_stats["face_detections"] += detection_results["faces_detected"]
                
                # Check cooldown and trigger snapshot if needed
                current_time = time.time()
                can_trigger = (current_time - self.last_trigger_time) >= self.cooldown
                
                # Check if any detected objects meet confidence threshold
                high_confidence_objects = [
                    obj for obj in detection_results["objects"]
                    if obj["confidence"] >= self.min_confidence
                ]
                
                if can_trigger and high_confidence_objects:
                    # Trigger snapshot
                    self._trigger_object_snapshot(frame, detection_results)
                    self.last_trigger_time = current_time
                    self.recognition_stats["cooldown_active"] = True
                    
                    # Schedule cooldown reset
                    threading.Timer(self.cooldown, self._reset_cooldown).start()
                
                # Trigger detection event callback
                event_data = {
                    "detection_results": detection_results,
                    "frame_shape": frame.shape,
                    "triggered_snapshot": can_trigger and bool(high_confidence_objects)
                }
                self._trigger_callbacks("on_event", "object_detected", event_data)
            
        except Exception as e:
            self.logger.error(f"Error in object recognition: {e}")
    
    def _detect_objects(self, frame: np.ndarray) -> Dict[str, Any]:
        """Detect objects in a frame."""
        results = {
            "detected": False,
            "objects": [],
            "faces_detected": 0,
            "total_objects": 0,
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            # Detect faces
            if self.face_detector and self.face_detector.opencv_available:
                face_result = self.face_detector.detect(frame)
                if face_result["detected"]:
                    results["faces_detected"] = face_result["count"]
                    
                    # Add faces as objects
                    for face in face_result["faces"]:
                        results["objects"].append({
                            "name": "face",
                            "confidence": face["confidence"],
                            "bbox": [face["x"], face["y"], face["width"], face["height"]],
                            "recognized_as": face.get("recognized_as")
                        })
            
            # Detect other objects using YOLO
            if self.object_detector:
                try:
                    # Run object detection
                    detections = self.object_detector(frame, verbose=False)[0]
                    
                    for box in detections.boxes:
                        # Get object info
                        cls = int(box.cls[0])
                        conf = float(box.conf[0])
                        xyxy = box.xyxy[0].tolist()
                        
                        # Get class name
                        class_name = detections.names[cls]
                        
                        # Check if this is an object we want to detect
                        if class_name in self.objects_to_detect and conf >= self.min_confidence:
                            # Convert bounding box to [x, y, width, height]
                            x1, y1, x2, y2 = xyxy
                            bbox = [int(x1), int(y1), int(x2 - x1), int(y2 - y1)]
                            
                            results["objects"].append({
                                "name": class_name,
                                "confidence": conf,
                                "bbox": bbox
                            })
                            
                except Exception as e:
                    self.logger.debug(f"Error in YOLO detection: {e}")
            
            # Update results
            results["total_objects"] = len(results["objects"])
            results["detected"] = results["total_objects"] > 0
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error detecting objects: {e}")
            return results
    
    def _trigger_object_snapshot(self, frame: np.ndarray, detection_results: Dict[str, Any]):
        """Trigger a snapshot due to object detection."""
        detected_objects = [obj["name"] for obj in detection_results["objects"]]
        self.logger.info(f"Objects detected: {', '.join(detected_objects)}")
        
        # Annotate frame if configured
        annotated_frame = None
        if self.annotate_images:
            annotated_frame = self._annotate_frame(frame, detection_results)
        
        # Prepare metadata
        metadata = {
            "trigger_type": "object_recognition",
            "detected_objects": detected_objects,
            "object_details": detection_results["objects"],
            "faces_detected": detection_results.get("faces_detected", 0),
            "total_objects": detection_results["total_objects"],
            "timestamp": detection_results["timestamp"]
        }
        
        # Take and save snapshot
        snapshot_result = self._process_and_save_snapshot("object", metadata)
        
        if snapshot_result:
            self.recognition_stats["snapshots_triggered"] += 1
            
            # Save annotated version if configured
            if self.save_annotated and annotated_frame is not None:
                self._save_annotated_image(annotated_frame, metadata)
            
            # Trigger object snapshot event
            event_data = {
                "detection_results": detection_results,
                "snapshot_result": snapshot_result,
                "frame_shape": frame.shape,
                "annotated_saved": annotated_frame is not None and self.save_annotated
            }
            self._trigger_callbacks("on_event", "object_snapshot", event_data)
            
            self.logger.info(f"Object recognition snapshot saved successfully")
        else:
            self.logger.warning("Failed to save object recognition snapshot")
    
    def _annotate_frame(self, frame: np.ndarray, detection_results: Dict[str, Any]) -> Optional[np.ndarray]:
        """Annotate frame with detection results."""
        try:
            import cv2
            
            annotated = frame.copy()
            
            # Draw bounding boxes for each object
            for obj in detection_results["objects"]:
                x, y, w, h = obj["bbox"]
                confidence = obj["confidence"]
                name = obj["name"]
                
                # Choose color based on object type
                if name == "face":
                    color = (0, 255, 0)  # Green for faces
                elif name == "person":
                    color = (0, 0, 255)  # Red for people
                elif name == "car":
                    color = (255, 0, 0)  # Blue for cars
                else:
                    color = (255, 255, 0)  # Cyan for other objects
                
                # Draw bounding box
                cv2.rectangle(annotated, (x, y), (x + w, y + h), color, 2)
                
                # Draw label
                label = f"{name}: {confidence:.2f}"
                cv2.putText(annotated, label, (x, y - 10),
                          cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
            
            # Add timestamp
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cv2.putText(annotated, timestamp, (10, annotated.shape[0] - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            
            return annotated
            
        except Exception as e:
            self.logger.error(f"Error annotating frame: {e}")
            return None
    
    def _save_annotated_image(self, annotated_frame: np.ndarray, metadata: Dict[str, Any]):
        """Save annotated image to storage."""
        if not self.storage_manager:
            return
        
        try:
            import cv2
            
            # Encode annotated frame
            success, encoded_image = cv2.imencode('.jpg', annotated_frame)
            if not success:
                self.logger.warning("Failed to encode annotated image")
                return
            
            image_data = encoded_image.tobytes()
            
            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            camera_name = self.config.get("camera_name", "camera").replace(" ", "_").lower()
            filename = f"{camera_name}_annotated_{timestamp}.jpg"
            
            # Prepare metadata
            save_metadata = {
                **metadata,
                "image_type": "annotated",
                "original_trigger": metadata.get("trigger_type", "object")
            }
            
            # Save to storage
            self.storage_manager.save_to_all(image_data, filename, save_metadata)
            
            self.logger.debug(f"Annotated image saved: {filename}")
            
        except Exception as e:
            self.logger.error(f"Error saving annotated image: {e}")
    
    def _reset_cooldown(self):
        """Reset the cooldown flag."""
        self.recognition_stats["cooldown_active"] = False
        self.logger.debug("Object recognition cooldown reset")
    
    def trigger_manual_object_check(self) -> Optional[Dict[str, Any]]:
        """
        Manually trigger an object recognition check.
        
        Returns:
            Object detection results, or None if failed
        """
        self.logger.info("Manual object recognition check triggered")
        
        try:
            # Capture frame
            frame = self._capture_frame()
            if frame is None:
                self.logger.warning("Failed to capture frame for manual check")
                return None
            
            # Detect objects
            detection_results = self._detect_objects(frame)
            
            # Trigger snapshot if objects detected
            if detection_results["detected"]:
                high_confidence_objects = [
                    obj for obj in detection_results["objects"]
                    if obj["confidence"] >= self.min_confidence
                ]
                
                if high_confidence_objects:
                    self._trigger_object_snapshot(frame, detection_results)
            
            return detection_results
            
        except Exception as e:
            self.logger.error(f"Error in manual object check: {e}")
            return None
    
    def get_status(self) -> Dict[str, Any]:
        """Get service status."""
        base_status = super().get_status()
        
        # Calculate cooldown remaining
        cooldown_remaining = 0
        if self.recognition_stats["cooldown_active"]:
            elapsed = time.time() - self.last_trigger_time
            cooldown_remaining = max(0, self.cooldown - elapsed)
        
        status = {
            **base_status,
            "service_type": "object_recognition",
            "objects_to_detect": self.objects_to_detect,
            "min_confidence": self.min_confidence,
            "cooldown": self.cooldown,
            "cooldown_remaining": cooldown_remaining,
            "annotate_images": self.annotate_images,
            "save_annotated": self.save_annotated,
            "frame_interval": self.frame_interval,
            "recognition_stats": self.recognition_stats,
            "queue_size": self.frame_queue.qsize(),
            "face_detector_available": self.face_detector and self.face_detector.opencv_available if self.face_detector else False,
            "object_detector_available": self.object_detector is not None,
            "processing_thread_alive": self.processing_thread and self.processing_thread.is_alive() if self.processing_thread else False,
            "capture_thread_alive": self.capture_thread and self.capture_thread.is_alive() if self.capture_thread else False
        }
        
        return status
    
    def get_detection_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent object detection history."""
        # This would typically query a database
        # For now, return a simplified version
        history = []
        
        # Add current stats as a history entry
        if self.recognition_stats["last_detection_time"]:
            history.append({
                "timestamp": self.recognition_stats["last_detection_time"],
                "objects": self.recognition_stats["last_detected_objects"],
                "snapshot_triggered": self.recognition_stats["snapshots_triggered"] > 0,
                "type": "object_recognition"
            })
        
        return history[:limit]
