"""
On-demand snapshot service for cameras.
"""

import threading
import time
from typing import Dict, Any, Optional
from datetime import datetime
from queue import Queue, Empty
from .base_service import SnapshotService


class OnDemandSnapshotService(SnapshotService):
    """Service for taking snapshots on demand."""
    
    def __init__(self, camera_device, config: Dict[str, Any]):
        super().__init__(camera_device, config)
        self.request_queue = Queue()
        self.processing_thread = None
        self.max_queue_size = config.get("max_queue_size", 10)
        self.processing_delay = config.get("processing_delay", 0.5)  # seconds
        
        # Request statistics
        self.request_stats = {
            "total_requests": 0,
            "processed_requests": 0,
            "failed_requests": 0,
            "queue_overflows": 0
        }
    
    def start(self) -> bool:
        """Start the on-demand snapshot service."""
        if self.running:
            self.logger.warning("Service already running")
            return True
        
        try:
            self.running = True
            self.processing_thread = threading.Thread(target=self._process_requests)
            self.processing_thread.daemon = True
            self.processing_thread.start()
            
            self.stats["start_time"] = datetime.now().isoformat()
            self.logger.info("On-demand snapshot service started")
            self._trigger_callbacks("on_start")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start on-demand snapshot service: {e}")
            self.running = False
            return False
    
    def stop(self) -> bool:
        """Stop the on-demand snapshot service."""
        if not self.running:
            return True
        
        try:
            self.running = False
            if self.processing_thread:
                self.processing_thread.join(timeout=5)
            
            # Clear the queue
            while not self.request_queue.empty():
                try:
                    self.request_queue.get_nowait()
                except Empty:
                    break
            
            self.logger.info("On-demand snapshot service stopped")
            self._trigger_callbacks("on_stop")
            return True
            
        except Exception as e:
            self.logger.error(f"Error stopping on-demand snapshot service: {e}")
            return False
    
    def request_snapshot(self, metadata: Dict[str, Any] = None, 
                        priority: str = "normal") -> bool:
        """
        Request a snapshot to be taken.
        
        Args:
            metadata: Additional metadata for the snapshot
            priority: Priority of the request ("high", "normal", "low")
            
        Returns:
            True if request was queued successfully, False otherwise
        """
        if not self.running:
            self.logger.warning("Cannot request snapshot: service not running")
            return False
        
        # Check queue size
        if self.request_queue.qsize() >= self.max_queue_size:
            self.logger.warning("Request queue full, dropping snapshot request")
            self.request_stats["queue_overflows"] += 1
            return False
        
        # Create request
        request = {
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {},
            "priority": priority,
            "request_id": f"req_{int(time.time())}_{self.request_stats['total_requests']}"
        }
        
        # Add to queue based on priority
        if priority == "high":
            # For high priority, we could use a priority queue
            # For simplicity, we'll just put it in the queue
            self.request_queue.put(request)
        else:
            self.request_queue.put(request)
        
        self.request_stats["total_requests"] += 1
        self.logger.debug(f"Snapshot request queued: {request['request_id']}")
        return True
    
    def take_snapshot_now(self, metadata: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """
        Take a snapshot immediately (bypassing queue).
        
        Args:
            metadata: Additional metadata for the snapshot
            
        Returns:
            Snapshot and storage results, or None if failed
        """
        self.logger.info("Taking immediate snapshot")
        return self._process_and_save_snapshot("manual", metadata)
    
    def _process_requests(self):
        """Background thread for processing snapshot requests."""
        self.logger.debug("Snapshot request processor started")
        
        while self.running:
            try:
                # Get request from queue with timeout
                request = self.request_queue.get(timeout=1)
                
                # Process request
                self._process_request(request)
                
                # Mark task as done
                self.request_queue.task_done()
                
                # Small delay to prevent overwhelming the camera
                time.sleep(self.processing_delay)
                
            except Empty:
                # No requests in queue, continue
                continue
            except Exception as e:
                self.logger.error(f"Error processing snapshot request: {e}")
                self.request_stats["failed_requests"] += 1
                self._trigger_callbacks("on_error", "request_processing", str(e))
        
        self.logger.debug("Snapshot request processor stopped")
    
    def _process_request(self, request: Dict[str, Any]):
        """Process a single snapshot request."""
        request_id = request.get("request_id", "unknown")
        self.logger.debug(f"Processing snapshot request: {request_id}")
        
        try:
            # Take snapshot with request metadata
            metadata = request.get("metadata", {})
            metadata["request_id"] = request_id
            metadata["request_priority"] = request.get("priority", "normal")
            metadata["request_timestamp"] = request.get("timestamp")
            
            result = self._process_and_save_snapshot("on_demand", metadata)
            
            if result:
                self.request_stats["processed_requests"] += 1
                self.logger.info(f"Snapshot request completed: {request_id}")
                
                # Trigger event with request info
                event_data = {
                    "request": request,
                    "result": result
                }
                self._trigger_callbacks("on_event", "request_completed", event_data)
            else:
                self.request_stats["failed_requests"] += 1
                self.logger.warning(f"Snapshot request failed: {request_id}")
                
        except Exception as e:
            self.request_stats["failed_requests"] += 1
            self.logger.error(f"Error processing request {request_id}: {e}")
            self._trigger_callbacks("on_error", "request_exception", str(e))
    
    def get_status(self) -> Dict[str, Any]:
        """Get service status."""
        base_status = super().get_status()
        
        status = {
            **base_status,
            "service_type": "on_demand",
            "queue_size": self.request_queue.qsize(),
            "max_queue_size": self.max_queue_size,
            "processing_delay": self.processing_delay,
            "request_stats": self.request_stats,
            "thread_alive": self.processing_thread and self.processing_thread.is_alive() if self.processing_thread else False
        }
        
        return status
    
    def get_queue_info(self) -> Dict[str, Any]:
        """Get information about the request queue."""
        # Note: This peeks at queue items without removing them
        queue_items = []
        temp_queue = Queue()
        
        # Move items to temp queue to inspect them
        while not self.request_queue.empty():
            try:
                item = self.request_queue.get_nowait()
                queue_items.append(item)
                temp_queue.put(item)
            except Empty:
                break
        
        # Restore items to original queue
        while not temp_queue.empty():
            try:
                item = temp_queue.get_nowait()
                self.request_queue.put(item)
            except Empty:
                break
        
        return {
            "count": len(queue_items),
            "items": queue_items[:10],  # Limit to first 10 items
            "total_queued": self.request_stats["total_requests"]
        }
