"""
Camera analytics module for motion and face detection with email alerts.
"""
import time
import threading
import queue
import numpy as np
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
import io
from homeauto.utils.logging_config import get_logger
from homeauto.utils.notifications import EmailNotifier


class MotionDetector:
    """Motion detection using background subtraction"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.logger = get_logger(__name__)
        
        # Motion detection parameters
        self.min_area = self.config.get("min_area", 500)
        self.threshold = self.config.get("threshold", 25)
        self.cooldown = self.config.get("cooldown", 5)  # seconds
        
        # Background subtractor (will be initialized when OpenCV is available)
        self.bg_subtractor = None
        self._init_opencv()
        
        self.last_detection_time = 0
        self.detection_count = 0
        
    def _init_opencv(self):
        """Initialize OpenCV components if available"""
        try:
            import cv2
            self.bg_subtractor = cv2.createBackgroundSubtractorMOG2(
                history=500,
                varThreshold=self.threshold,
                detectShadows=False
            )
            self.cv2 = cv2
            self.opencv_available = True
        except ImportError:
            self.logger.warning("OpenCV not available. Motion detection disabled.")
            self.opencv_available = False
    
    def detect(self, frame: np.ndarray) -> Dict[str, Any]:
        """Detect motion in frame"""
        if not self.opencv_available or self.bg_subtractor is None:
            return self._get_empty_result()
        
        current_time = time.time()
        
        # Apply background subtraction
        fg_mask = self.bg_subtractor.apply(frame)
        
        # Apply threshold
        _, thresh = self.cv2.threshold(fg_mask, 25, 255, self.cv2.THRESH_BINARY)
        
        # Remove noise
        kernel = self.cv2.getStructuringElement(self.cv2.MORPH_ELLIPSE, (3, 3))
        thresh = self.cv2.morphologyEx(thresh, self.cv2.MORPH_OPEN, kernel)
        thresh = self.cv2.morphologyEx(thresh, self.cv2.MORPH_CLOSE, kernel)
        
        # Find contours
        contours, _ = self.cv2.findContours(thresh, self.cv2.RETR_EXTERNAL, self.cv2.CHAIN_APPROX_SIMPLE)
        
        motion_regions = []
        max_confidence = 0
        
        for contour in contours:
            area = self.cv2.contourArea(contour)
            
            if area > self.min_area:
                # Calculate bounding box
                x, y, w, h = self.cv2.boundingRect(contour)
                motion_regions.append({
                    "x": x,
                    "y": y,
                    "width": w,
                    "height": h,
                    "area": area
                })
                
                # Calculate confidence based on area
                confidence = min(area / (frame.shape[0] * frame.shape[1] * 0.1), 1.0)
                max_confidence = max(max_confidence, confidence)
        
        # Check cooldown
        motion_detected = len(motion_regions) > 0
        can_trigger = (current_time - self.last_detection_time) >= self.cooldown
        
        if motion_detected and can_trigger:
            self.last_detection_time = current_time
            self.detection_count += 1
            
            return {
                "detected": True,
                "regions": motion_regions,
                "confidence": max_confidence,
                "count": len(motion_regions),
                "timestamp": current_time,
                "total_detections": self.detection_count
            }
        
        return self._get_empty_result(current_time)
    
    def _get_empty_result(self, timestamp: float = None) -> Dict[str, Any]:
        """Get empty detection result"""
        if timestamp is None:
            timestamp = time.time()
        return {
            "detected": False,
            "regions": [],
            "confidence": 0,
            "count": 0,
            "timestamp": timestamp,
            "total_detections": self.detection_count
        }
    
    def draw_detections(self, frame: np.ndarray, detection_result: Dict[str, Any]) -> np.ndarray:
        """Draw motion detection results on frame"""
        if not self.opencv_available:
            return frame
        
        result_frame = frame.copy()
        
        if detection_result["detected"]:
            for region in detection_result["regions"]:
                x, y, w, h = region["x"], region["y"], region["width"], region["height"]
                
                # Draw bounding box
                self.cv2.rectangle(result_frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                
                # Draw label
                label = f"Motion: {region['area']:.0f}"
                self.cv2.putText(result_frame, label, (x, y - 10),
                               self.cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        
        # Draw detection count
        self.cv2.putText(result_frame, f"Detections: {detection_result['total_detections']}",
                       (10, 30), self.cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        return result_frame


class FaceDetector:
    """Face detection using Haar cascades"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.logger = get_logger(__name__)
        
        # Load Haar cascade for face detection
        self.face_cascade = None
        self.cv2 = None
        self._init_opencv()
        
        # Face recognition database (simple in-memory for now)
        self.known_faces = self.config.get("known_faces", {})
        
        # Detection parameters
        self.scale_factor = self.config.get("scale_factor", 1.1)
        self.min_neighbors = self.config.get("min_neighbors", 5)
        self.min_size = self.config.get("min_size", (30, 30))
        self.cooldown = self.config.get("cooldown", 10)  # seconds
        
        self.last_detection_time = 0
        self.detection_count = 0
        
    def _init_opencv(self):
        """Initialize OpenCV components if available"""
        try:
            import cv2
            self.cv2 = cv2
            
            # Load Haar cascade
            cascade_path = self.config.get("cascade_path")
            if cascade_path:
                self.face_cascade = cv2.CascadeClassifier(cascade_path)
            else:
                # Try to load default cascade
                try:
                    self.face_cascade = cv2.CascadeClassifier(
                        cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
                    )
                except:
                    self.logger.error("Failed to load face cascade")
                    self.face_cascade = None
            
            self.opencv_available = True
        except ImportError:
            self.logger.warning("OpenCV not available. Face detection disabled.")
            self.opencv_available = False
    
    def detect(self, frame: np.ndarray) -> Dict[str, Any]:
        """Detect faces in frame"""
        if not self.opencv_available or self.face_cascade is None:
            return self._get_empty_result()
        
        current_time = time.time()
        
        # Convert to grayscale for face detection
        gray = self.cv2.cvtColor(frame, self.cv2.COLOR_BGR2GRAY)
        
        # Detect faces
        faces = self.face_cascade.detectMultiScale(
            gray,
            scaleFactor=self.scale_factor,
            minNeighbors=self.min_neighbors,
            minSize=self.min_size
        )
        
        face_results = []
        
        for (x, y, w, h) in faces:
            # Extract face region
            face_region = frame[y:y+h, x:x+w]
            
            # Simple recognition (placeholder - would use face_recognition library in production)
            recognized_as = self._recognize_face(face_region)
            
            face_results.append({
                "x": x,
                "y": y,
                "width": w,
                "height": h,
                "recognized_as": recognized_as,
                "confidence": 0.8 if recognized_as else 0.5  # Placeholder confidence
            })
        
        # Check cooldown
        faces_detected = len(face_results) > 0
        can_trigger = (current_time - self.last_detection_time) >= self.cooldown
        
        if faces_detected and can_trigger:
            self.last_detection_time = current_time
            self.detection_count += 1
            
            # Get recognized faces
            recognized_faces = [f["recognized_as"] for f in face_results if f["recognized_as"]]
            
            return {
                "detected": True,
                "faces": face_results,
                "count": len(face_results),
                "recognized_count": len(recognized_faces),
                "recognized_faces": recognized_faces,
                "timestamp": current_time,
                "total_detections": self.detection_count
            }
        
        return self._get_empty_result(current_time)
    
    def _get_empty_result(self, timestamp: float = None) -> Dict[str, Any]:
        """Get empty detection result"""
        if timestamp is None:
            timestamp = time.time()
        return {
            "detected": False,
            "faces": [],
            "count": 0,
            "recognized_count": 0,
            "recognized_faces": [],
            "timestamp": timestamp,
            "total_detections": self.detection_count
        }
    
    def _recognize_face(self, face_region: np.ndarray) -> Optional[str]:
        """Simple face recognition (placeholder)"""
        # In a real implementation, this would use face_recognition library
        # or a trained model to compare with known faces
        
        # For now, return None (unknown face)
        # This is where you would integrate with a proper face recognition system
        return None
    
    def draw_detections(self, frame: np.ndarray, detection_result: Dict[str, Any]) -> np.ndarray:
        """Draw face detection results on frame"""
        if not self.opencv_available:
            return frame
        
        result_frame = frame.copy()
        
        if detection_result["detected"]:
            for face in detection_result["faces"]:
                x, y, w, h = face["x"], face["y"], face["width"], face["height"]
                
                # Choose color based on recognition
                if face["recognized_as"]:
                    color = (0, 255, 0)  # Green for recognized
                    label = f"Face: {face['recognized_as']}"
                else:
                    color = (0, 0, 255)  # Red for unknown
                    label = "Face: Unknown"
                
                # Draw bounding box
                self.cv2.rectangle(result_frame, (x, y), (x + w, y + h), color, 2)
                
                # Draw label
                self.cv2.putText(result_frame, label, (x, y - 10),
                               self.cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
        
        # Draw detection count
        self.cv2.putText(result_frame, f"Faces: {detection_result['count']}",
                       (10, 60), self.cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        
        if detection_result["recognized_count"] > 0:
            self.cv2.putText(result_frame, f"Recognized: {detection_result['recognized_count']}",
                           (10, 90), self.cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        return result_frame


class CameraAnalytics:
    """Main camera analytics system with email alerts"""
    
    def __init__(self, camera_config: Dict[str, Any], email_config: Dict[str, Any] = None):
        self.camera_config = camera_config
        self.logger = get_logger(__name__)
        
        # Initialize detectors
        self.motion_detector = MotionDetector(
            camera_config.get("motion_config", {})
        )
        
        self.face_detector = FaceDetector(
            camera_config.get("face_config", {})
        )
        
        # Initialize email notifier if configured
        self.email_notifier = None
        if email_config:
            try:
                self.email_notifier = EmailNotifier(email_config)
                self.logger.info("Email notifications enabled")
            except Exception as e:
                self.logger.error(f"Failed to initialize email notifier: {e}")
        
        # Analytics state
        self.running = False
        self.analytics_thread = None
        self.frame_queue = queue.Queue(maxsize=10)
        
        # Statistics
        self.stats = {
            "motion_detections": 0,
            "face_detections": 0,
            "alerts_sent": 0,
            "start_time": time.time()
        }
        
        # Callbacks for external integration
        self.on_motion_detected = None
        self.on_face_detected = None
        self.on_alert_sent = None
        
    def start(self):
        """Start analytics processing"""
        if self.running:
            self.logger.warning("Analytics already running")
            return
        
        self.running = True
        self.analytics_thread = threading.Thread(target=self._process_frames)
        self.analytics_thread.daemon = True
        self.analytics_thread.start()
        
        self.logger.info("Camera analytics started")
    
    def stop(self):
        """Stop analytics processing"""
        self.running = False
        if self.analytics_thread:
            self.analytics_thread.join(timeout=2)
        
        self.logger.info("Camera analytics stopped")
    
    def process_frame(self, frame: np.ndarray) -> Dict[str, Any]:
        """Process a single frame and return results"""
        results = {
            "timestamp": time.time(),
            "motion": None,
            "faces": None,
            "alerts": []
        }
        
        # Motion detection
        motion_result = self.motion_detector.detect(frame)
        results["motion"] = motion_result
        
        if motion_result["detected"]:
            self.stats["motion_detections"] += 1
            
            # Trigger motion callback
            if self.on_motion_detected:
                self.on_motion_detected(motion_result)
            
            # Send email alert if configured
            if self.email_notifier and motion_result["confidence"] > 0.5:
                # Convert frame to bytes for email attachment
                if hasattr(self.motion_detector, 'cv2') and self.motion_detector.cv2:
                    success, buffer = self.motion_detector.cv2.imencode('.jpg', frame)
                    if success:
                        image_bytes = io.BytesIO(buffer)
                        
                        alert_sent = self.email_notifier.send_motion_alert(
                            camera_name=self.camera_config.get("name", "Unknown Camera"),
                            camera_ip=self.camera_config.get("ip", "0.0.0.0"),
                            confidence=motion_result["confidence"],
                            image_data=image_bytes
                        )
                        
                        if alert_sent:
                            self.stats["alerts_sent"] += 1
                            results["alerts"].append({
                                "type": "motion",
                                "sent": True,
                                "confidence": motion_result["confidence"]
                            })
                            
                            # Trigger alert callback
                            if self.on_alert_sent:
                                self.on_alert_sent("motion", motion_result)
        
        # Face detection
        face_result = self.face_detector.detect(frame)
        results["faces"] = face_result
        
        if face_result["detected"]:
            self.stats["face_detections"] += 1
            
            # Trigger face callback
            if self.on_face_detected:
                self.on_face_detected(face_result)
            
            # Send email alert if configured and unknown faces detected
            if (self.email_notifier and 
                face_result["count"] > 0 and 
                face_result["recognized_count"] < face_result["count"]):
                
                # Convert frame to bytes for email attachment
                if hasattr(self.face_detector, 'cv2') and self.face_detector.cv2:
                    success, buffer = self.face_detector.cv2.imencode('.jpg', frame)
                    if success:
                        image_bytes = io.BytesIO(buffer)
                        
                        alert_sent = self.email_notifier.send_face_alert(
                            camera_name=self.camera_config.get("name", "Unknown Camera"),
                            camera_ip=self.camera_config.get("ip", "0.0.0.0"),
                            confidence=face_result.get("confidence", 0.8),
                            face_count=face_result["count"],
                            recognized_faces=face_result["recognized_faces"],
                            image_data=image_bytes
                        )
                        
                        if alert_sent:
                            self.stats["alerts_sent"] += 1
                            results["alerts"].append({
                                "type": "face",
                                "sent": True,
                                "face_count": face_result["count"],
                                "recognized_count": face_result["recognized_count"]
                            })
                            
                            # Trigger alert callback
                            if self.on_alert_sent:
                                self.on_alert_sent("face", face_result)
        
        return results
    
    def _process_frames(self):
        """Background thread for processing frames from queue"""
        while self.running:
            try:
                # Get frame from queue with timeout
                frame = self.frame_queue.get(timeout=1)
                
                # Process frame
                self.process_frame(frame)
                
                # Mark task as done
                self.frame_queue.task_done()
                
            except queue.Empty:
                # No frames to process, continue
                continue
            except Exception as e:
                self.logger.error(f"Error processing frame: {e}")
    
    def add_frame(self, frame: np.ndarray):
        """Add frame to processing queue"""
        if not self.running:
            self.logger.warning("Analytics not running, frame ignored")
            return
        
        try:
            # Try to put frame in queue (non-blocking)
            self.frame_queue.put_nowait(frame)
        except queue.Full:
            # Queue full, drop frame
            self.logger.debug("Frame queue full, dropping frame")
    
    def get_annotated_frame(self, frame: np.ndarray, results: Dict[str, Any]) -> np.ndarray:
        """Get frame with detection annotations"""
        annotated_frame = frame.copy()
        
        if results["motion"] and results["motion"]["detected"]:
            annotated_frame = self.motion_detector.draw_detections(
                annotated_frame, results["motion"]
            )
        
        if results["faces"] and results["faces"]["detected"]:
            annotated_frame = self.face_detector.draw_detections(
                annotated_frame, results["faces"]
            )
        
        # Add timestamp and camera name if OpenCV is available
        if hasattr(self.motion_detector, 'cv2') and self.motion_detector.cv2:
            # Add timestamp
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.motion_detector.cv2.putText(annotated_frame, timestamp, 
                                           (10, annotated_frame.shape[0] - 10),
                                           self.motion_detector.cv2.FONT_HERSHEY_SIMPLEX, 
                                           0.5, (255, 255, 255), 1)
            
            # Add camera name
            camera_name = self.camera_config.get("name", "Camera")
            self.motion_detector.cv2.putText(annotated_frame, camera_name, 
                                           (annotated_frame.shape[1] - 150, 30),
                                           self.motion_detector.cv2.FONT_HERSHEY_SIMPLEX, 
                                           0.7, (255, 255, 255), 2)
        
        return annotated_frame
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get analytics statistics"""
        current_time = time.time()
        runtime = current_time - self.stats["start_time"]
        
        return {
            **self.stats,
            "runtime_seconds": runtime,
            "runtime_hours": runtime / 3600,
            "motion_detections_per_hour": self.stats["motion_detections"] / (runtime / 3600) if runtime > 0 else 0,
            "face_detections_per_hour": self.stats["face_detections"] / (runtime / 3600) if runtime > 0 else 0,
            "email_notifications_enabled": self.email_notifier is not None,
            "opencv_available": hasattr(self.motion_detector, 'opencv_available') and self.motion_detector.opencv_available
        }
    
    def send_daily_report(self):
        """Send daily analytics report via email"""
        if not self.email_notifier:
            self.logger.warning("Email notifier not configured")
            return False
        
        stats = self.get_statistics()
        summary = {
            "total_events": stats["motion_detections"] + stats["face_detections"],
            "motion_events": stats["motion_detections"],
            "face_events": stats["face_detections"],
            "alerts_sent": stats["alerts_sent"],
            "cameras": [{
                "name": self.camera_config.get("name", "Unknown Camera"),
                "online": True,
                "ip": self.camera_config.get("ip", "0.0.0.0")
            }]
        }
        
        return self.email_notifier.send_daily_report(summary)


# Test function
def test_camera_analytics():
    """Test camera analytics system"""
    
    # Create test configuration
    camera_config = {
        "name": "Test Camera",
        "ip": "192.168.1.100",
        "motion_config": {
            "min_area": 500,
            "threshold": 25,
            "cooldown": 2
        },
        "face_config": {
            "scale_factor": 1.1,
            "min_neighbors": 5,
            "cooldown": 5
        }
    }
    
    # Create analytics system (without email for testing)
    analytics = CameraAnalytics(camera_config)
    
    # Create test callback
    def on_motion_detected(result):
        print(f"Motion detected: {result['count']} regions, confidence: {result['confidence']:.2f}")
    
    def on_face_detected(result):
        print(f"Faces detected: {result['count']}, recognized: {result['recognized_count']}")
    
    analytics.on_motion_detected = on_motion_detected
    analytics.on_face_detected = on_face_detected
    
    # Check if OpenCV is available
    if not analytics.motion_detector.opencv_available:
        print("OpenCV not available. Skipping frame processing test.")
        print("Install OpenCV with: pip install opencv-python")
        
        # Test statistics
        print("\nAnalytics Statistics (without OpenCV):")
        stats = analytics.get_statistics()
        for key, value in stats.items():
            print(f"  {key}: {value}")
        
        return
    
    # Start analytics
    analytics.start()
    
    # Create test frames
    print("Creating test frames...")
    
    # Test frame 1: Empty room (no motion)
    frame1 = np.zeros((480, 640, 3), dtype=np.uint8)
    frame1[:] = (100, 100, 100)  # Gray background
    
    # Test frame 2: With motion (white rectangle)
    frame2 = frame1.copy()
    import cv2
    cv2.rectangle(frame2, (200, 150), (400, 300), (255, 255, 255), -1)
    
    # Test frame 3: With face (simplified)
    frame3 = frame1.copy()
    cv2.rectangle(frame3, (250, 200), (350, 300), (200, 200, 255), -1)  # "Face"
    
    # Process frames
    print("\nProcessing test frames...")
    
    results1 = analytics.process_frame(frame1)
    print(f"Frame 1 - Motion: {results1['motion']['detected']}, Faces: {results1['faces']['detected']}")
    
    results2 = analytics.process_frame(frame2)
    print(f"Frame 2 - Motion: {results2['motion']['detected']}, Faces: {results2['faces']['detected']}")
    
    results3 = analytics.process_frame(frame3)
    print(f"Frame 3 - Motion: {results3['motion']['detected']}, Faces: {results3['faces']['detected']}")
    
    # Get annotated frames
    annotated2 = analytics.get_annotated_frame(frame2, results2)
    annotated3 = analytics.get_annotated_frame(frame3, results3)
    
    # Display statistics
    print("\nAnalytics Statistics:")
    stats = analytics.get_statistics()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    # Stop analytics
    analytics.stop()
    
    print("\nTest completed successfully!")
    
    # Save test frames for inspection
    cv2.imwrite("test_frame1.jpg", frame1)
    cv2.imwrite("test_frame2_motion.jpg", annotated2)
    cv2.imwrite("test_frame3_face.jpg", annotated3)
    print("Test frames saved to disk")


if __name__ == "__main__":
    test_camera_analytics()
