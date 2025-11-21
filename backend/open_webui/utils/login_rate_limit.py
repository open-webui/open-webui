import time
from collections import defaultdict

class RateLimiter:
    def __init__(self, max_attempts: int, window_seconds: int):
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self.attempts = defaultdict(list)

    def check(self, key: str) -> bool:
        """
        Check if the rate limit has been exceeded for the given key.
        Returns True if the request is allowed, False otherwise.
        """
        current_time = time.time()
        # Filter out timestamps older than the window
        self.attempts[key] = [t for t in self.attempts[key] if current_time - t < self.window_seconds]
        
        if len(self.attempts[key]) >= self.max_attempts:
            return False
        
        self.attempts[key].append(current_time)
        return True

    def reset(self, key: str):
        if key in self.attempts:
            del self.attempts[key]
