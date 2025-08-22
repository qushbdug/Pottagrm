"""
Rate limiting system for Yemen Net Bot v2
"""

import time
import asyncio
from collections import defaultdict
from typing import Dict, Tuple, Optional
import logging

logger = logging.getLogger(__name__)

class RateLimiter:
    """
    Rate limiter implementation with sliding window
    """
    
    def __init__(self, max_requests: int = 10, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: Dict[int, list] = defaultdict(list)
        self._cleanup_task: Optional[asyncio.Task] = None
        
    async def start_cleanup(self):
        """Start cleanup task for expired requests"""
        if self._cleanup_task is None or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
    
    async def _cleanup_loop(self):
        """Cleanup loop for expired requests"""
        while True:
            try:
                await asyncio.sleep(60)  # Cleanup every minute
                await self._cleanup_expired()
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
    
    async def _cleanup_expired(self):
        """Remove expired requests"""
        current_time = time.time()
        expired_threshold = current_time - self.window_seconds
        
        for user_id in list(self.requests.keys()):
            self.requests[user_id] = [
                req_time for req_time in self.requests[user_id]
                if req_time > expired_threshold
            ]
            if not self.requests[user_id]:
                del self.requests[user_id]
    
    def is_allowed(self, user_id: int) -> bool:
        """
        Check if user is allowed to make a request
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            bool: True if allowed, False if rate limited
        """
        current_time = time.time()
        user_requests = self.requests[user_id]
        
        # Remove expired requests
        user_requests[:] = [
            req_time for req_time in user_requests
            if req_time > current_time - self.window_seconds
        ]
        
        # Check if under limit
        if len(user_requests) >= self.max_requests:
            return False
        
        # Add current request
        user_requests.append(current_time)
        return True
    
    def get_remaining_requests(self, user_id: int) -> int:
        """
        Get remaining requests for user
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            int: Number of remaining requests
        """
        current_time = time.time()
        user_requests = self.requests[user_id]
        
        # Remove expired requests
        user_requests[:] = [
            req_time for req_time in user_requests
            if req_time > current_time - self.window_seconds
        ]
        
        return max(0, self.max_requests - len(user_requests))
    
    def get_reset_time(self, user_id: int) -> Optional[float]:
        """
        Get time when rate limit resets for user
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            Optional[float]: Reset time or None if no requests
        """
        user_requests = self.requests[user_id]
        if not user_requests:
            return None
        
        # Get oldest request time
        oldest_request = min(user_requests)
        return oldest_request + self.window_seconds
    
    async def wait_if_needed(self, user_id: int) -> bool:
        """
        Wait if user is rate limited
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            bool: True if waited, False if not needed
        """
        if self.is_allowed(user_id):
            return False
        
        reset_time = self.get_reset_time(user_id)
        if reset_time:
            wait_time = reset_time - time.time()
            if wait_time > 0:
                await asyncio.sleep(wait_time)
                return True
        
        return False

# Global rate limiter instance
rate_limiter = RateLimiter()

# Rate limit decorator
def rate_limit(max_requests: int = 10, window_seconds: int = 60):
    """
    Decorator to apply rate limiting to functions
    
    Args:
        max_requests: Maximum requests per window
        window_seconds: Time window in seconds
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Try to get user_id from first argument (usually update)
            user_id = None
            if args and hasattr(args[0], 'effective_user'):
                user_id = args[0].effective_user.id
            elif args and hasattr(args[0], 'from_user'):
                user_id = args[0].from_user.id
            
            if user_id:
                # Create user-specific rate limiter
                user_limiter = RateLimiter(max_requests, window_seconds)
                
                if not user_limiter.is_allowed(user_id):
                    remaining_time = user_limiter.get_reset_time(user_id) - time.time()
                    raise RateLimitError(
                        f"Rate limit exceeded. Try again in {int(remaining_time)} seconds."
                    )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator