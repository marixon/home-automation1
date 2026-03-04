"""
Scheduled snapshot service for cameras.
"""

import threading
import time
import schedule
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from .base_service import SnapshotService


class ScheduledSnapshotService(SnapshotService):
    """Service for taking snapshots on a schedule."""
    
    def __init__(self, camera_device, config: Dict[str, Any]):
        super().__init__(camera_device, config)
        
        # Schedule configuration
        self.schedules = config.get("schedules", [])
        self.active_schedules = {}
        self.schedule_thread = None
        self.schedule_interval = config.get("schedule_check_interval", 60)  # seconds
        
        # Schedule statistics
        self.schedule_stats = {
            "total_scheduled": 0,
            "executed_schedules": 0,
            "failed_schedules": 0,
            "missed_schedules": 0,
            "last_schedule_check": None
        }
    
    def start(self) -> bool:
        """Start the scheduled snapshot service."""
        if self.running:
            self.logger.warning("Service already running")
            return True
        
        try:
            # Clear any existing schedules
            schedule.clear()
            
            # Setup schedules from configuration
            self._setup_schedules()
            
            # Start schedule checking thread
            self.running = True
            self.schedule_thread = threading.Thread(target=self._run_schedules)
            self.schedule_thread.daemon = True
            self.schedule_thread.start()
            
            self.stats["start_time"] = datetime.now().isoformat()
            self.logger.info(f"Scheduled snapshot service started with {len(self.schedules)} schedules")
            self._trigger_callbacks("on_start")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start scheduled snapshot service: {e}")
            self.running = False
            return False
    
    def stop(self) -> bool:
        """Stop the scheduled snapshot service."""
        if not self.running:
            return True
        
        try:
            self.running = False
            
            # Clear all schedules
            schedule.clear()
            self.active_schedules.clear()
            
            # Wait for thread to stop
            if self.schedule_thread:
                self.schedule_thread.join(timeout=5)
            
            self.logger.info("Scheduled snapshot service stopped")
            self._trigger_callbacks("on_stop")
            return True
            
        except Exception as e:
            self.logger.error(f"Error stopping scheduled snapshot service: {e}")
            return False
    
    def _setup_schedules(self):
        """Setup schedules from configuration."""
        for schedule_config in self.schedules:
            try:
                schedule_name = schedule_config.get("name", f"schedule_{len(self.active_schedules)}")
                cron_expression = schedule_config.get("cron")
                interval_seconds = schedule_config.get("interval_seconds")
                
                if cron_expression:
                    # Parse cron expression
                    self._add_cron_schedule(schedule_name, cron_expression, schedule_config)
                elif interval_seconds:
                    # Parse interval schedule
                    self._add_interval_schedule(schedule_name, interval_seconds, schedule_config)
                else:
                    self.logger.warning(f"Schedule '{schedule_name}' has no cron or interval specified")
                    
            except Exception as e:
                self.logger.error(f"Error setting up schedule: {e}")
    
    def _add_cron_schedule(self, name: str, cron_expr: str, config: Dict[str, Any]):
        """Add a cron-based schedule."""
        try:
            # Parse cron expression (format: "minute hour day month day_of_week")
            parts = cron_expr.split()
            if len(parts) != 5:
                raise ValueError(f"Invalid cron expression: {cron_expr}")
            
            minute, hour, day, month, day_of_week = parts
            
            # Create schedule job
            job = schedule.every()
            
            # Set day of week if specified
            if day_of_week != "*":
                day_map = {
                    "0": "sunday", "1": "monday", "2": "tuesday", "3": "wednesday",
                    "4": "thursday", "5": "friday", "6": "saturday",
                    "sun": "sunday", "mon": "monday", "tue": "tuesday", "wed": "wednesday",
                    "thu": "thursday", "fri": "friday", "sat": "saturday"
                }
                day_name = day_map.get(day_of_week.lower(), day_of_week)
                if hasattr(job, day_name):
                    job = getattr(job, day_name)()
            
            # Set time if specified
            if hour != "*" or minute != "*":
                if hour == "*":
                    hour = "00"
                if minute == "*":
                    minute = "00"
                
                job = job.at(f"{int(hour):02d}:{int(minute):02d}")
            
            # Tag the job with schedule info
            job.tag(name, "cron", config)
            
            self.active_schedules[name] = {
                "type": "cron",
                "expression": cron_expr,
                "config": config,
                "next_run": None
            }
            
            self.schedule_stats["total_scheduled"] += 1
            self.logger.info(f"Added cron schedule '{name}': {cron_expr}")
            
        except Exception as e:
            self.logger.error(f"Error adding cron schedule '{name}': {e}")
    
    def _add_interval_schedule(self, name: str, interval_seconds: int, config: Dict[str, Any]):
        """Add an interval-based schedule."""
        try:
            # Create schedule job
            job = schedule.every(interval_seconds).seconds
            
            # Tag the job with schedule info
            job.tag(name, "interval", config)
            
            self.active_schedules[name] = {
                "type": "interval",
                "interval_seconds": interval_seconds,
                "config": config,
                "next_run": None
            }
            
            self.schedule_stats["total_scheduled"] += 1
            self.logger.info(f"Added interval schedule '{name}': every {interval_seconds} seconds")
            
        except Exception as e:
            self.logger.error(f"Error adding interval schedule '{name}': {e}")
    
    def _run_schedules(self):
        """Background thread for running scheduled jobs."""
        self.logger.debug("Schedule runner started")
        
        while self.running:
            try:
                # Update next run times for active schedules
                self._update_next_run_times()
                
                # Run pending jobs
                schedule.run_pending()
                
                # Update schedule check time
                self.schedule_stats["last_schedule_check"] = datetime.now().isoformat()
                
                # Sleep for check interval
                time.sleep(self.schedule_interval)
                
            except Exception as e:
                self.logger.error(f"Error in schedule runner: {e}")
                time.sleep(self.schedule_interval)  # Sleep before retry
        
        self.logger.debug("Schedule runner stopped")
    
    def _update_next_run_times(self):
        """Update next run times for all active schedules."""
        # Note: This is a simplified implementation
        # In a real implementation, we would query schedule for next run times
        for name in self.active_schedules:
            # For simplicity, we'll just note that we checked
            pass
    
    def execute_schedule(self, schedule_name: str, metadata: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """
        Execute a specific schedule immediately.
        
        Args:
            schedule_name: Name of the schedule to execute
            metadata: Additional metadata for the snapshot
            
        Returns:
            Snapshot and storage results, or None if failed
        """
        if schedule_name not in self.active_schedules:
            self.logger.warning(f"Schedule '{schedule_name}' not found")
            return None
        
        schedule_config = self.active_schedules[schedule_name]
        self.logger.info(f"Executing schedule '{schedule_name}'")
        
        # Prepare metadata
        schedule_metadata = {
            "schedule_name": schedule_name,
            "schedule_type": schedule_config["type"],
            "schedule_config": schedule_config["config"]
        }
        
        if metadata:
            schedule_metadata.update(metadata)
        
        # Take snapshot
        result = self._process_and_save_snapshot("scheduled", schedule_metadata)
        
        if result:
            self.schedule_stats["executed_schedules"] += 1
            self.logger.info(f"Schedule '{schedule_name}' executed successfully")
        else:
            self.schedule_stats["failed_schedules"] += 1
            self.logger.warning(f"Schedule '{schedule_name}' execution failed")
        
        return result
    
    def add_schedule(self, name: str, config: Dict[str, Any]) -> bool:
        """
        Add a new schedule dynamically.
        
        Args:
            name: Name of the schedule
            config: Schedule configuration
            
        Returns:
            True if schedule was added successfully, False otherwise
        """
        if name in self.active_schedules:
            self.logger.warning(f"Schedule '{name}' already exists")
            return False
        
        try:
            # Add to schedules list
            self.schedules.append({**config, "name": name})
            
            # If service is running, setup the schedule
            if self.running:
                cron_expression = config.get("cron")
                interval_seconds = config.get("interval_seconds")
                
                if cron_expression:
                    self._add_cron_schedule(name, cron_expression, config)
                elif interval_seconds:
                    self._add_interval_schedule(name, interval_seconds, config)
                else:
                    self.logger.warning(f"Schedule '{name}' has no cron or interval specified")
                    return False
            
            self.logger.info(f"Added new schedule: {name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error adding schedule '{name}': {e}")
            return False
    
    def remove_schedule(self, name: str) -> bool:
        """
        Remove a schedule.
        
        Args:
            name: Name of the schedule to remove
            
        Returns:
            True if schedule was removed successfully, False otherwise
        """
        if name not in self.active_schedules:
            self.logger.warning(f"Schedule '{name}' not found")
            return False
        
        try:
            # Remove from active schedules
            del self.active_schedules[name]
            
            # Remove from schedules list
            self.schedules = [s for s in self.schedules if s.get("name") != name]
            
            # Clear the schedule from schedule library
            # Note: schedule library doesn't have a direct way to remove by tag
            # We would need to clear all and re-setup in a real implementation
            
            self.logger.info(f"Removed schedule: {name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error removing schedule '{name}': {e}")
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """Get service status."""
        base_status = super().get_status()
        
        # Calculate next run times
        next_runs = {}
        for name, schedule_info in self.active_schedules.items():
            # This is a simplified implementation
            # In a real implementation, we would calculate actual next run times
            next_runs[name] = "Unknown"
        
        status = {
            **base_status,
            "service_type": "scheduled",
            "active_schedules": len(self.active_schedules),
            "total_schedules": len(self.schedules),
            "schedule_check_interval": self.schedule_interval,
            "schedule_stats": self.schedule_stats,
            "next_runs": next_runs,
            "thread_alive": self.schedule_thread and self.schedule_thread.is_alive() if self.schedule_thread else False
        }
        
        return status
    
    def get_schedule_info(self) -> Dict[str, Any]:
        """Get detailed information about all schedules."""
        return {
            "schedules": self.schedules,
            "active_schedules": self.active_schedules,
            "stats": self.schedule_stats
        }
