"""
Advanced Rate Limiting Service with Sliding Window Algorithm
"""
import time
import threading
from collections import defaultdict, deque
from typing import Dict, Optional, Tuple, Any
from dataclasses import dataclass
from functools import wraps

from ..core.exceptions import RateLimitException, RateLimitExceeded
from ..core.logger import logger


@dataclass
class RateLimitConfig:
    """Rate limit configuration"""
    requests_per_window: int
    window_size_seconds: int
    burst_limit: Optional[int] = None
    cooldown_seconds: Optional[int] = None


class SlidingWindowCounter:
    """Sliding window rate limiter using timestamp-based counting"""
    
    def __init__(self, requests_per_window: int, window_size_seconds: int):
        self.requests_per_window = requests_per_window
        self.window_size_seconds = window_size_seconds
        self.requests = deque()
        self.lock = threading.Lock()
        
    def is_allowed(self) -> Tuple[bool, float]:
        """Check if request is allowed, return (allowed, reset_time)"""
        current_time = time.time()
        
        with self.lock:
            # Remove old requests outside the window
            while self.requests and self.requests[0] <= current_time - self.window_size_seconds:
                self.requests.popleft()
                
            # Check if we can accept this request
            if len(self.requests) < self.requests_per_window:
                self.requests.append(current_time)
                return True, current_time + self.window_size_seconds
            else:
                # Calculate when the oldest request will expire
                oldest_request = self.requests[0]
                reset_time = oldest_request + self.window_size_seconds
                return False, reset_time
                
    def get_remaining(self) -> int:
        """Get remaining requests in current window"""
        current_time = time.time()
        
        with self.lock:
            # Remove old requests
            while self.requests and self.requests[0] <= current_time - self.window_size_seconds:
                self.requests.popleft()
                
            return max(0, self.requests_per_window - len(self.requests))


class RateLimiter:
    """Advanced rate limiting service with multiple strategies"""
    
    def __init__(self):
        self.user_limiters: Dict[int, Dict[str, SlidingWindowCounter]] = defaultdict(dict)
        self.global_limiters: Dict[str, SlidingWindowCounter] = {}
        self.blocked_users: Dict[int, float] = {}  # user_id -> unblock_time
        self.blocked_ips: Dict[str, float] = {}  # ip -> unblock_time
        self.lock = threading.Lock()
        
        # Default rate limit configurations
        self.configs = {
            'default': RateLimitConfig(60, 60),  # 60 requests per minute
            'login': RateLimitConfig(5, 300),    # 5 login attempts per 5 minutes
            'message': RateLimitConfig(30, 60),  # 30 messages per minute
            'payment': RateLimitConfig(10, 300), # 10 payments per 5 minutes
            'admin': RateLimitConfig(120, 60),   # 120 requests per minute for admins
            'api': RateLimitConfig(1000, 3600),  # 1000 API calls per hour
            'download': RateLimitConfig(5, 60),  # 5 downloads per minute
            'upload': RateLimitConfig(3, 300),   # 3 uploads per 5 minutes
        }
        
        # Start cleanup thread
        self._start_cleanup_thread()
        
    def _start_cleanup_thread(self):
        """Start background thread to clean up expired entries"""
        def cleanup_worker():
            while True:
                try:
                    self._cleanup_expired()
                    time.sleep(60)  # Cleanup every minute
                except Exception as e:
                    logger.error("Rate limiter cleanup error", e)
                    time.sleep(30)
                    
        cleanup_thread = threading.Thread(
            target=cleanup_worker,
            daemon=True,
            name="RateLimiterCleanup"
        )
        cleanup_thread.start()
        
    def _cleanup_expired(self):
        """Remove expired blocked users and IPs"""
        current_time = time.time()
        
        with self.lock:
            # Clean up blocked users
            expired_users = [
                user_id for user_id, unblock_time in self.blocked_users.items()
                if current_time >= unblock_time
            ]
            for user_id in expired_users:
                del self.blocked_users[user_id]
                logger.info(f"Unblocked user {user_id}")
                
            # Clean up blocked IPs
            expired_ips = [
                ip for ip, unblock_time in self.blocked_ips.items()
                if current_time >= unblock_time
            ]
            for ip in expired_ips:
                del self.blocked_ips[ip]
                logger.info(f"Unblocked IP {ip}")
                
            # Clean up old user limiters (keep only active ones)
            for user_id in list(self.user_limiters.keys()):
                user_limiters = self.user_limiters[user_id]
                active_limiters = {}
                
                for action, limiter in user_limiters.items():
                    if limiter.get_remaining() < limiter.requests_per_window:
                        active_limiters[action] = limiter
                        
                if active_limiters:
                    self.user_limiters[user_id] = active_limiters
                else:
                    del self.user_limiters[user_id]
                    
    def _get_config(self, action: str, user_role: str = 'user') -> RateLimitConfig:
        """Get rate limit configuration for action and user role"""
        if user_role == 'admin' and action != 'login':
            return self.configs.get('admin', self.configs['default'])
        return self.configs.get(action, self.configs['default'])
        
    def check_rate_limit(self, user_id: int, action: str, user_role: str = 'user', 
                        ip_address: Optional[str] = None) -> Dict[str, Any]:
        """
        Check if user can perform action
        Returns dict with: allowed, remaining, reset_time, reason
        """
        current_time = time.time()
        
        # Check if user is blocked
        if user_id in self.blocked_users:
            if current_time < self.blocked_users[user_id]:
                return {
                    'allowed': False,
                    'remaining': 0,
                    'reset_time': self.blocked_users[user_id],
                    'reason': 'user_blocked'
                }
            else:
                del self.blocked_users[user_id]
                
        # Check if IP is blocked
        if ip_address and ip_address in self.blocked_ips:
            if current_time < self.blocked_ips[ip_address]:
                return {
                    'allowed': False,
                    'remaining': 0,
                    'reset_time': self.blocked_ips[ip_address],
                    'reason': 'ip_blocked'
                }
            else:
                del self.blocked_ips[ip_address]
                
        # Get rate limit configuration
        config = self._get_config(action, user_role)
        
        # Get or create limiter for this user and action
        if user_id not in self.user_limiters:
            self.user_limiters[user_id] = {}
            
        if action not in self.user_limiters[user_id]:
            self.user_limiters[user_id][action] = SlidingWindowCounter(
                config.requests_per_window,
                config.window_size_seconds
            )
            
        limiter = self.user_limiters[user_id][action]
        allowed, reset_time = limiter.is_allowed()
        remaining = limiter.get_remaining()
        
        if not allowed:
            logger.log_security_event(
                "rate_limit_exceeded",
                user_id,
                f"Action: {action}, IP: {ip_address}"
            )
            
        return {
            'allowed': allowed,
            'remaining': remaining,
            'reset_time': reset_time,
            'reason': 'rate_limit_exceeded' if not allowed else None
        }
        
    def block_user(self, user_id: int, duration_seconds: int, reason: str):
        """Block user for specified duration"""
        unblock_time = time.time() + duration_seconds
        self.blocked_users[user_id] = unblock_time
        
        logger.log_security_event(
            "user_blocked",
            user_id,
            f"Duration: {duration_seconds}s, Reason: {reason}"
        )
        
    def block_ip(self, ip_address: str, duration_seconds: int, reason: str):
        """Block IP address for specified duration"""
        unblock_time = time.time() + duration_seconds
        self.blocked_ips[ip_address] = unblock_time
        
        logger.log_security_event(
            "ip_blocked",
            None,
            f"IP: {ip_address}, Duration: {duration_seconds}s, Reason: {reason}"
        )
        
    def unblock_user(self, user_id: int):
        """Manually unblock user"""
        if user_id in self.blocked_users:
            del self.blocked_users[user_id]
            logger.log_security_event("user_unblocked", user_id)
            
    def unblock_ip(self, ip_address: str):
        """Manually unblock IP"""
        if ip_address in self.blocked_ips:
            del self.blocked_ips[ip_address]
            logger.log_security_event("ip_unblocked", None, f"IP: {ip_address}")
            
    def reset_user_limits(self, user_id: int, action: Optional[str] = None):
        """Reset rate limits for user"""
        if user_id in self.user_limiters:
            if action:
                if action in self.user_limiters[user_id]:
                    del self.user_limiters[user_id][action]
            else:
                del self.user_limiters[user_id]
                
        logger.log_security_event(
            "rate_limit_reset",
            user_id,
            f"Action: {action or 'all'}"
        )
        
    def get_user_status(self, user_id: int) -> Dict[str, Any]:
        """Get detailed status for user"""
        current_time = time.time()
        
        status = {
            'user_id': user_id,
            'is_blocked': user_id in self.blocked_users,
            'blocked_until': self.blocked_users.get(user_id),
            'active_limits': {}
        }
        
        if user_id in self.user_limiters:
            for action, limiter in self.user_limiters[user_id].items():
                status['active_limits'][action] = {
                    'remaining': limiter.get_remaining(),
                    'total': limiter.requests_per_window,
                    'window_size': limiter.window_size_seconds
                }
                
        return status
        
    def get_global_stats(self) -> Dict[str, Any]:
        """Get global rate limiting statistics"""
        return {
            'active_users': len(self.user_limiters),
            'blocked_users': len(self.blocked_users),
            'blocked_ips': len(self.blocked_ips),
            'rate_limit_configs': {
                action: {
                    'requests_per_window': config.requests_per_window,
                    'window_size_seconds': config.window_size_seconds
                }
                for action, config in self.configs.items()
            }
        }


def rate_limit(action: str, user_role: str = 'user'):
    """Decorator for rate limiting functions"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract user_id from function arguments
            user_id = None
            
            # Try to get user_id from various argument patterns
            if args and hasattr(args[0], 'effective_user'):
                user_id = args[0].effective_user.id
            elif 'update' in kwargs and hasattr(kwargs['update'], 'effective_user'):
                user_id = kwargs['update'].effective_user.id
            elif 'user_id' in kwargs:
                user_id = kwargs['user_id']
                
            if user_id:
                result = rate_limiter.check_rate_limit(user_id, action, user_role)
                
                if not result['allowed']:
                    logger.warning(f"Rate limit exceeded for user {user_id} on action {action}")
                    raise RateLimitExceeded(
                        f"Rate limit exceeded for action {action}. "
                        f"Try again after {result['reset_time'] - time.time():.0f} seconds"
                    )
                    
            return await func(*args, **kwargs)
        return wrapper
    return decorator


# Global rate limiter instance
rate_limiter = RateLimiter()