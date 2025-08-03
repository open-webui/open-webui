"""Monitoring and metrics collection for performance tracking"""

import time
import logging
from typing import Dict, Any, Optional
from collections import defaultdict
from datetime import datetime
import asyncio

log = logging.getLogger(__name__)


class MetricsCollector:
    """Collect and track performance metrics"""
    
    def __init__(self):
        self.metrics = defaultdict(lambda: {
            "count": 0,
            "total_time": 0.0,
            "min_time": float('inf'),
            "max_time": 0.0,
            "errors": 0,
            "last_error": None,
            "cache_hits": 0,
            "cache_misses": 0
        })
        self.start_time = time.time()
    
    def record_operation(
        self,
        operation: str,
        duration: float,
        success: bool = True,
        cache_hit: Optional[bool] = None
    ):
        """Record metrics for an operation"""
        metric = self.metrics[operation]
        
        metric["count"] += 1
        metric["total_time"] += duration
        metric["min_time"] = min(metric["min_time"], duration)
        metric["max_time"] = max(metric["max_time"], duration)
        
        if not success:
            metric["errors"] += 1
            metric["last_error"] = datetime.now().isoformat()
        
        if cache_hit is not None:
            if cache_hit:
                metric["cache_hits"] += 1
            else:
                metric["cache_misses"] += 1
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get all collected metrics"""
        result = {}
        uptime = time.time() - self.start_time
        
        for operation, data in self.metrics.items():
            count = data["count"]
            if count > 0:
                avg_time = data["total_time"] / count
                cache_total = data["cache_hits"] + data["cache_misses"]
                cache_hit_rate = (
                    data["cache_hits"] / cache_total * 100
                    if cache_total > 0 else 0
                )
            else:
                avg_time = 0
                cache_hit_rate = 0
            
            result[operation] = {
                "count": count,
                "avg_time_ms": avg_time * 1000,
                "min_time_ms": data["min_time"] * 1000 if count > 0 else 0,
                "max_time_ms": data["max_time"] * 1000,
                "total_time_s": data["total_time"],
                "errors": data["errors"],
                "error_rate": (data["errors"] / count * 100) if count > 0 else 0,
                "last_error": data["last_error"],
                "cache_hit_rate": cache_hit_rate,
                "cache_hits": data["cache_hits"],
                "cache_misses": data["cache_misses"]
            }
        
        result["_summary"] = {
            "uptime_seconds": uptime,
            "total_operations": sum(m["count"] for m in self.metrics.values()),
            "total_errors": sum(m["errors"] for m in self.metrics.values()),
            "operations_per_second": sum(m["count"] for m in self.metrics.values()) / uptime
        }
        
        return result
    
    def log_metrics(self):
        """Log current metrics summary"""
        metrics = self.get_metrics()
        summary = metrics.get("_summary", {})
        
        log.info(
            f"Metrics Summary - Uptime: {summary['uptime_seconds']:.0f}s, "
            f"Total Ops: {summary['total_operations']}, "
            f"Errors: {summary['total_errors']}, "
            f"Ops/sec: {summary['operations_per_second']:.2f}"
        )
        
        # Log top operations by count
        ops = [(k, v) for k, v in metrics.items() if k != "_summary"]
        ops.sort(key=lambda x: x[1]["count"], reverse=True)
        
        for op_name, op_data in ops[:5]:
            log.info(
                f"  {op_name}: {op_data['count']} calls, "
                f"avg: {op_data['avg_time_ms']:.1f}ms, "
                f"cache hit: {op_data['cache_hit_rate']:.1f}%"
            )


# Global metrics instance
metrics = MetricsCollector()


class TimedOperation:
    """Context manager for timing operations"""
    
    def __init__(self, operation: str, collector: Optional[MetricsCollector] = None):
        self.operation = operation
        self.collector = collector or metrics
        self.start_time = None
        self.success = True
        self.cache_hit = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time
        self.success = exc_type is None
        self.collector.record_operation(
            self.operation,
            duration,
            self.success,
            self.cache_hit
        )
        
        if not self.success:
            log.error(f"Operation {self.operation} failed: {exc_val}")
        
        # Don't suppress exceptions
        return False
    
    def set_cache_hit(self, hit: bool):
        """Mark whether this operation was a cache hit"""
        self.cache_hit = hit


# Periodic metrics logging task
async def log_metrics_periodically(interval: int = 300):
    """Log metrics every interval seconds"""
    while True:
        await asyncio.sleep(interval)
        metrics.log_metrics()