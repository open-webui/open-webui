"""
Specialized logging for batch processing with performance metrics
"""

import logging
import time
from typing import Dict, Any, Optional
from contextlib import contextmanager
from datetime import datetime

log = logging.getLogger(__name__)


class BatchLogger:
    """Enhanced logger for batch operations with timing and metrics"""
    
    def __init__(self, operation_name: str):
        self.operation_name = operation_name
        self.metrics: Dict[str, Any] = {
            "operation": operation_name,
            "start_time": None,
            "end_time": None,
            "duration_seconds": None,
            "steps": []
        }
        
    @contextmanager
    def step(self, step_name: str, details: Optional[Dict[str, Any]] = None):
        """Track a single step within the operation"""
        step_start = time.time()
        step_data = {
            "name": step_name,
            "start_time": datetime.now().isoformat(),
            "details": details or {}
        }
        
        try:
            log.info(f"🔄 {self.operation_name} - Starting: {step_name}")
            yield step_data
            
            # Success
            step_data["duration_seconds"] = round(time.time() - step_start, 3)
            step_data["success"] = True
            step_data["end_time"] = datetime.now().isoformat()
            log.info(f"✅ {self.operation_name} - Completed: {step_name} ({step_data['duration_seconds']}s)")
            
        except Exception as e:
            # Failure
            step_data["duration_seconds"] = round(time.time() - step_start, 3)
            step_data["success"] = False
            step_data["error"] = str(e)
            step_data["end_time"] = datetime.now().isoformat()
            log.error(f"❌ {self.operation_name} - Failed: {step_name} - {e}")
            raise
            
        finally:
            self.metrics["steps"].append(step_data)
            
    def start(self):
        """Start tracking the operation"""
        self.metrics["start_time"] = datetime.now().isoformat()
        log.info(f"🕰️ Starting {self.operation_name}")
        
    def complete(self, additional_metrics: Optional[Dict[str, Any]] = None):
        """Mark operation as complete and log summary"""
        self.metrics["end_time"] = datetime.now().isoformat()
        
        if self.metrics["start_time"]:
            start = datetime.fromisoformat(self.metrics["start_time"])
            end = datetime.fromisoformat(self.metrics["end_time"])
            self.metrics["duration_seconds"] = round((end - start).total_seconds(), 3)
            
        if additional_metrics:
            self.metrics.update(additional_metrics)
            
        # Count successful steps
        successful_steps = sum(1 for step in self.metrics["steps"] if step.get("success", False))
        total_steps = len(self.metrics["steps"])
        
        log.info(
            f"📊 {self.operation_name} completed: "
            f"{successful_steps}/{total_steps} steps successful in {self.metrics['duration_seconds']}s"
        )
        
        return self.metrics
        
    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics"""
        return self.metrics.copy()