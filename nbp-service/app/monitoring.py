"""
Health monitoring and metrics for NBP Service
"""
from datetime import datetime
from typing import Dict, Any
import psutil
import os

from .config import settings


class ServiceMetrics:
    """Track service metrics and health"""
    
    def __init__(self):
        self.start_time = datetime.utcnow()
        self.request_count = 0
        self.cache_hits = 0
        self.cache_misses = 0
        self.api_calls = 0
        self.api_errors = 0
        self.last_successful_fetch = None
        self.last_error = None
    
    def record_request(self):
        """Record an API request"""
        self.request_count += 1
    
    def record_cache_hit(self):
        """Record a cache hit"""
        self.cache_hits += 1
    
    def record_cache_miss(self):
        """Record a cache miss"""
        self.cache_misses += 1
    
    def record_api_call(self, success: bool = True):
        """Record an NBP API call"""
        self.api_calls += 1
        if success:
            self.last_successful_fetch = datetime.utcnow()
        else:
            self.api_errors += 1
    
    def record_error(self, error: str):
        """Record an error"""
        self.last_error = {
            "message": error,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics"""
        uptime = (datetime.utcnow() - self.start_time).total_seconds()
        cache_hit_rate = 0
        if self.cache_hits + self.cache_misses > 0:
            cache_hit_rate = self.cache_hits / (self.cache_hits + self.cache_misses)
        
        # System metrics
        process = psutil.Process(os.getpid())
        
        return {
            "service": {
                "name": "NBP Exchange Rate Service",
                "version": "1.0.0",
                "environment": settings.env,
                "mode": "mock" if settings.mock_mode else "live",
                "uptime_seconds": int(uptime),
                "start_time": self.start_time.isoformat()
            },
            "requests": {
                "total": self.request_count,
                "rate_per_minute": round(self.request_count / (uptime / 60), 2) if uptime > 0 else 0
            },
            "cache": {
                "hits": self.cache_hits,
                "misses": self.cache_misses,
                "hit_rate": round(cache_hit_rate, 3),
                "ttl_seconds": settings.cache_ttl
            },
            "nbp_api": {
                "calls": self.api_calls,
                "errors": self.api_errors,
                "error_rate": round(self.api_errors / self.api_calls, 3) if self.api_calls > 0 else 0,
                "last_successful_fetch": self.last_successful_fetch.isoformat() if self.last_successful_fetch else None
            },
            "system": {
                "memory_mb": round(process.memory_info().rss / 1024 / 1024, 2),
                "cpu_percent": process.cpu_percent(),
                "threads": process.num_threads()
            },
            "errors": {
                "last_error": self.last_error
            }
        }


# Global metrics instance
metrics = ServiceMetrics()