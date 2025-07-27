"""Retry policy implementations for HTTP client"""

import asyncio
import random
from typing import Optional, Callable, Any
from dataclasses import dataclass
import logging

log = logging.getLogger(__name__)


@dataclass
class RetryPolicy:
    """Configuration for retry behavior"""
    max_retries: int = 3
    initial_delay: float = 1.0
    max_delay: float = 10.0
    backoff_factor: float = 2.0
    jitter: bool = True
    
    def calculate_delay(self, attempt: int) -> float:
        """Calculate delay for given attempt number"""
        delay = min(self.initial_delay * (self.backoff_factor ** attempt), self.max_delay)
        if self.jitter:
            # Add random jitter between 0-25% of delay
            delay *= (1 + random.random() * 0.25)
        return delay


class ExponentialBackoff:
    """Exponential backoff retry decorator"""
    
    def __init__(self, policy: Optional[RetryPolicy] = None):
        self.policy = policy or RetryPolicy()
    
    def __call__(self, func: Callable) -> Callable:
        """Decorator to add retry logic to async functions"""
        async def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            
            for attempt in range(self.policy.max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    
                    if attempt >= self.policy.max_retries:
                        log.error(f"Max retries ({self.policy.max_retries}) reached for {func.__name__}")
                        raise
                    
                    delay = self.policy.calculate_delay(attempt)
                    log.warning(
                        f"Attempt {attempt + 1}/{self.policy.max_retries + 1} failed for {func.__name__}: {e}. "
                        f"Retrying in {delay:.2f}s..."
                    )
                    
                    await asyncio.sleep(delay)
            
            raise last_exception
        
        return wrapper


class CircuitBreaker:
    """Circuit breaker pattern implementation"""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: type = Exception
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.state = "closed"  # closed, open, half-open
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection"""
        if self.state == "open":
            if self.last_failure_time and \
               (asyncio.get_event_loop().time() - self.last_failure_time) > self.recovery_timeout:
                self.state = "half-open"
                log.info(f"Circuit breaker entering half-open state for {func.__name__}")
            else:
                raise Exception(f"Circuit breaker is open for {func.__name__}")
        
        try:
            result = await func(*args, **kwargs)
            
            if self.state == "half-open":
                self.state = "closed"
                self.failure_count = 0
                log.info(f"Circuit breaker closed for {func.__name__}")
            
            return result
            
        except self.expected_exception as e:
            self.failure_count += 1
            self.last_failure_time = asyncio.get_event_loop().time()
            
            if self.failure_count >= self.failure_threshold:
                self.state = "open"
                log.error(f"Circuit breaker opened for {func.__name__} after {self.failure_count} failures")
            
            raise