"""
Rate limiting system for Yemen Net Bot v2
"""

import time
import asyncio
from collections import defaultdict, deque
from typing import Dict, Deque, Optional
from .exceptions import RateLimitError

class RateLimiter:
    """Rate limiter for user actions"""
    
    def __init__(self, max_requests: int = 10, time_window: int = 60):
        """
        Initialize rate limiter
        
        Args:
            max_requests: Maximum requests allowed in time window
            time_window: Time window in seconds
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests: Dict[int, Deque[float]] = defaultdict(lambda: deque())
        self._cleanup_task: Optional[asyncio.Task] = None
        
    async def start_cleanup(self):
        """Start background cleanup task"""
        if not self._cleanup_task or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
    
    async def stop_cleanup(self):
        """Stop background cleanup task"""
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
    
    async def _cleanup_loop(self):
        """Background cleanup loop"""
        while True:
            try:
                await asyncio.sleep(self.time_window)
                await self._cleanup_expired()
            except asyncio.CancelledError:
                break
            except Exception as e:
                # Log error but continue
                print(f"Rate limiter cleanup error: {e}")
    
    async def _cleanup_expired(self):
        """Remove expired requests"""
        current_time = time.time()
        expired_time = current_time - self.time_window
        
        for user_id in list(self.requests.keys()):
            # Remove expired requests
            while self.requests[user_id] and self.requests[user_id][0] < expired_time:
                self.requests[user_id].popleft()
            
            # Remove empty user entries
            if not self.requests[user_id]:
                del self.requests[user_id]
    
    def is_allowed(self, user_id: int) -> bool:
        """
        Check if user is allowed to make a request
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            True if allowed, False if rate limited
        """
        current_time = time.time()
        user_requests = self.requests[user_id]
        
        # Remove expired requests
        while user_requests and user_requests[0] < current_time - self.time_window:
            user_requests.popleft()
        
        # Check if under limit
        if len(user_requests) < self.max_requests:
            user_requests.append(current_time)
            return True
        
        return False
    
    async def check_rate_limit(self, user_id: int) -> None:
        """
        Check rate limit and raise exception if exceeded
        
        Args:
            user_id: Telegram user ID
            
        Raises:
            RateLimitError: If rate limit exceeded
        """
        if not self.is_allowed(user_id):
            remaining_time = self._get_remaining_time(user_id)
            raise RateLimitError(
                f"Rate limit exceeded. Please wait {remaining_time:.1f} seconds."
            )
    
    def _get_remaining_time(self, user_id: int) -> float:
        """Get remaining time until next allowed request"""
        if user_id not in self.requests or not self.requests[user_id]:
            return 0.0
        
        oldest_request = self.requests[user_id][0]
        return max(0.0, self.time_window - (time.time() - oldest_request))
    
    def get_user_stats(self, user_id: int) -> Dict[str, int]:
        """Get rate limiting stats for a user"""
        if user_id not in self.requests:
            return {"requests": 0, "remaining": self.max_requests}
        
        current_requests = len(self.requests[user_id])
        return {
            "requests": current_requests,
            "remaining": max(0, self.max_requests - current_requests)
        }

class ActionRateLimiter:
    """Rate limiter for specific actions"""
    
    def __init__(self):
        """Initialize action rate limiters"""
        self.limiters = {
            "message": RateLimiter(max_requests=20, time_window=60),
            "button_click": RateLimiter(max_requests=30, time_window=60),
            "payment": RateLimiter(max_requests=5, time_window=300),
            "admin_action": RateLimiter(max_requests=10, time_window=60),
            "file_upload": RateLimiter(max_requests=3, time_window=300),
            "api_call": RateLimiter(max_requests=50, time_window=60)
        }
    
    async def start_all(self):
        """Start all rate limiters"""
        for limiter in self.limiters.values():
            await limiter.start_cleanup()
    
    async def stop_all(self):
        """Stop all rate limiters"""
        for limiter in self.limiters.values():
            await limiter.stop_cleanup()
    
    async def check_action(self, action: str, user_id: int) -> None:
        """
        Check rate limit for specific action
        
        Args:
            action: Action type
            user_id: Telegram user ID
            
        Raises:
            RateLimitError: If rate limit exceeded
        """
        if action not in self.limiters:
            return  # No rate limiting for unknown actions
        
        await self.limiters[action].check_rate_limit(user_id)
    
    def get_action_stats(self, action: str, user_id: int) -> Dict[str, int]:
        """Get stats for specific action"""
        if action not in self.limiters:
            return {"requests": 0, "remaining": 0}
        
        return self.limiters[action].get_user_stats(user_id)