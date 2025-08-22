"""
Rate limiter service for preventing abuse
"""

import time
import asyncio
import logging
from typing import Dict, Optional, Tuple
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from ..core.exceptions import RateLimitException
from ..core.config import config

logger = logging.getLogger(__name__)

@dataclass
class RateLimitConfig:
    """Rate limiting configuration"""
    max_requests: int = 10
    time_window: int = 60  # seconds
    burst_limit: int = 20
    penalty_duration: int = 300  # seconds

@dataclass
class UserRateLimit:
    """User rate limit tracking"""
    requests: deque = field(default_factory=lambda: deque(maxlen=100))
    blocked_until: Optional[float] = None
    warning_count: int = 0
    last_warning: Optional[float] = None

class RateLimiter:
    """Rate limiter with configurable limits and penalties"""
    
    def __init__(self):
        self.config = RateLimitConfig(
            max_requests=config.bot.rate_limit_per_user,
            time_window=60,
            burst_limit=config.bot.rate_limit_burst
        )
        
        self.user_limits: Dict[int, UserRateLimit] = defaultdict(UserRateLimit)
        self.global_limits: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        self.ip_limits: Dict[str, UserRateLimit] = defaultdict(UserRateLimit)
        
        # Cleanup task
        self._cleanup_task = None
        self._start_cleanup_task()
    
    def _start_cleanup_task(self):
        """Start background cleanup task"""
        async def cleanup_loop():
            while True:
                try:
                    await asyncio.sleep(300)  # Clean every 5 minutes
                    self._cleanup_expired_entries()
                except Exception as e:
                    logger.error(f"Cleanup task error: {e}")
        
        try:
            loop = asyncio.get_event_loop()
            self._cleanup_task = loop.create_task(cleanup_loop())
        except RuntimeError:
            # No event loop, skip cleanup task
            pass
    
    def _cleanup_expired_entries(self):
        """Clean up expired rate limit entries"""
        current_time = time.time()
        
        # Clean user limits
        expired_users = []
        for user_id, user_limit in self.user_limits.items():
            if (current_time - user_limit.last_warning > 3600 and 
                user_limit.warning_count == 0 and
                not user_limit.blocked_until):
                expired_users.append(user_id)
        
        for user_id in expired_users:
            del self.user_limits[user_id]
        
        # Clean IP limits
        expired_ips = []
        for ip, ip_limit in self.ip_limits.items():
            if (current_time - ip_limit.last_warning > 3600 and
                ip_limit.warning_count == 0 and
                not ip_limit.blocked_until):
                expired_ips.append(ip)
        
        for ip in expired_ips:
            del self.ip_limits[ip]
        
        # Clean global limits
        for key in list(self.global_limits.keys()):
            self.global_limits[key] = deque(
                [t for t in self.global_limits[key] if current_time - t < 3600],
                maxlen=100
            )
        
        if expired_users or expired_ips:
            logger.info(f"Cleaned up {len(expired_users)} users and {len(expired_ips)} IPs")
    
    def is_allowed(self, user_id: int, action: str = "general") -> Tuple[bool, Optional[str]]:
        """
        Check if user is allowed to perform action
        
        Returns:
            Tuple[bool, Optional[str]]: (allowed, reason if not allowed)
        """
        current_time = time.time()
        user_limit = self.user_limits[user_id]
        
        # Check if user is blocked
        if user_limit.blocked_until and current_time < user_limit.blocked_until:
            remaining = int(user_limit.blocked_until - current_time)
            return False, f"User is blocked for {remaining} seconds"
        
        # Check burst limit
        if len(user_limit.requests) >= self.config.burst_limit:
            return False, "Burst limit exceeded"
        
        # Check time window limit
        window_start = current_time - self.config.time_window
        recent_requests = [req for req in user_limit.requests if req > window_start]
        
        if len(recent_requests) >= self.config.max_requests:
            # Apply penalty
            penalty_end = current_time + self.config.penalty_duration
            user_limit.blocked_until = penalty_end
            user_limit.warning_count += 1
            
            logger.warning(f"Rate limit exceeded for user {user_id}, blocked until {penalty_end}")
            return False, f"Rate limit exceeded. Blocked for {self.config.penalty_duration} seconds"
        
        # Record request
        user_limit.requests.append(current_time)
        return True, None
    
    def is_ip_allowed(self, ip_address: str) -> Tuple[bool, Optional[str]]:
        """Check if IP address is allowed"""
        current_time = time.time()
        ip_limit = self.ip_limits[ip_address]
        
        # Check if IP is blocked
        if ip_limit.blocked_until and current_time < ip_limit.blocked_until:
            remaining = int(ip_limit.blocked_until - current_time)
            return False, f"IP is blocked for {remaining} seconds"
        
        # Check IP rate limit (stricter than user limit)
        window_start = current_time - 60  # 1 minute window
        recent_requests = [req for req in ip_limit.requests if req > window_start]
        
        if len(recent_requests) >= 30:  # 30 requests per minute per IP
            penalty_end = current_time + 600  # 10 minute penalty
            ip_limit.blocked_until = penalty_end
            ip_limit.warning_count += 1
            
            logger.warning(f"IP rate limit exceeded for {ip_address}, blocked until {penalty_end}")
            return False, f"IP rate limit exceeded. Blocked for 10 minutes"
        
        # Record request
        ip_limit.requests.append(current_time)
        return True, None
    
    def is_global_allowed(self, action: str, limit: int = 100) -> bool:
        """Check global rate limit for specific actions"""
        current_time = time.time()
        window_start = current_time - 60  # 1 minute window
        
        # Clean old entries
        self.global_limits[action] = deque(
            [t for t in self.global_limits[action] if t > window_start],
            maxlen=100
        )
        
        # Check limit
        if len(self.global_limits[action]) >= limit:
            return False
        
        # Record action
        self.global_limits[action].append(current_time)
        return True
    
    async def check_rate_limit(self, user_id: int, action: str = "general") -> bool:
        """Async rate limit check"""
        try:
            allowed, reason = self.is_allowed(user_id, action)
            if not allowed:
                logger.warning(f"Rate limit check failed for user {user_id}: {reason}")
                raise RateLimitException(reason)
            return True
        except RateLimitException:
            raise
        except Exception as e:
            logger.error(f"Rate limit check error for user {user_id}: {e}")
            return False
    
    def get_user_stats(self, user_id: int) -> Dict:
        """Get rate limit statistics for user"""
        if user_id not in self.user_limits:
            return {
                'requests_count': 0,
                'is_blocked': False,
                'blocked_until': None,
                'warning_count': 0,
                'remaining_requests': self.config.max_requests
            }
        
        user_limit = self.user_limits[user_id]
        current_time = time.time()
        
        # Calculate remaining requests in current window
        window_start = current_time - self.config.time_window
        recent_requests = [req for req in user_limit.requests if req > window_start]
        remaining_requests = max(0, self.config.max_requests - len(recent_requests))
        
        return {
            'requests_count': len(user_limit.requests),
            'is_blocked': bool(user_limit.blocked_until and current_time < user_limit.blocked_until),
            'blocked_until': user_limit.blocked_until,
            'warning_count': user_limit.warning_count,
            'remaining_requests': remaining_requests,
            'time_window': self.config.time_window
        }
    
    def reset_user_limits(self, user_id: int):
        """Reset rate limits for user (admin function)"""
        if user_id in self.user_limits:
            self.user_limits[user_id] = UserRateLimit()
            logger.info(f"Rate limits reset for user {user_id}")
    
    def block_user(self, user_id: int, duration: int = 3600):
        """Block user for specified duration (admin function)"""
        current_time = time.time()
        user_limit = self.user_limits[user_id]
        user_limit.blocked_until = current_time + duration
        logger.warning(f"User {user_id} blocked for {duration} seconds by admin")
    
    def unblock_user(self, user_id: int):
        """Unblock user (admin function)"""
        if user_id in self.user_limits:
            self.user_limits[user_id].blocked_until = None
            logger.info(f"User {user_id} unblocked by admin")
    
    def get_system_stats(self) -> Dict:
        """Get system-wide rate limiting statistics"""
        current_time = time.time()
        
        # Count blocked users
        blocked_users = sum(
            1 for user_limit in self.user_limits.values()
            if user_limit.blocked_until and current_time < user_limit.blocked_until
        )
        
        # Count blocked IPs
        blocked_ips = sum(
            1 for ip_limit in self.ip_limits.values()
            if ip_limit.blocked_until and current_time < ip_limit.blocked_until
        )
        
        # Calculate average requests per user
        total_requests = sum(len(user_limit.requests) for user_limit in self.user_limits.values())
        avg_requests = total_requests / len(self.user_limits) if self.user_limits else 0
        
        return {
            'total_users': len(self.user_limits),
            'blocked_users': blocked_users,
            'total_ips': len(self.ip_limits),
            'blocked_ips': blocked_ips,
            'total_requests': total_requests,
            'average_requests_per_user': round(avg_requests, 2),
            'global_actions': {action: len(requests) for action, requests in self.global_limits.items()}
        }
    
    def shutdown(self):
        """Shutdown rate limiter and cleanup"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
        
        # Clear all data
        self.user_limits.clear()
        self.ip_limits.clear()
        self.global_limits.clear()
        
        logger.info("Rate limiter shutdown complete")

# Global rate limiter instance
rate_limiter = RateLimiter()