"""
Advanced Rate Limiting Service for Yemen Net Bot
Provides multiple rate limiting strategies and user-based throttling
"""

import time
import asyncio
import logging
from typing import Dict, Optional, Tuple, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import threading
from collections import defaultdict, deque

from core.exceptions import RateLimitError
from core.logger import get_security_logger


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting"""
    requests_per_minute: int = 10
    requests_per_hour: int = 100
    requests_per_day: int = 1000
    burst_limit: int = 5
    cooldown_seconds: int = 60


@dataclass
class UserRateLimit:
    """Rate limit data for a specific user"""
    user_id: int
    requests_per_minute: deque = field(default_factory=deque)
    requests_per_hour: deque = field(default_factory=deque)
    requests_per_day: deque = field(default_factory=deque)
    burst_count: int = 0
    last_request_time: float = 0
    cooldown_until: float = 0
    total_requests: int = 0
    violations_count: int = 0
    first_violation_time: Optional[float] = None


class RateLimiter:
    """Advanced rate limiter with multiple strategies"""
    
    def __init__(self, default_config: Optional[RateLimitConfig] = None):
        self.default_config = default_config or RateLimitConfig()
        self.user_limits: Dict[int, UserRateLimit] = {}
        self.user_configs: Dict[int, RateLimitConfig] = {}
        self.global_limits: Dict[str, deque] = {
            'minute': deque(),
            'hour': deque(),
            'day': deque()
        }
        self.logger = logging.getLogger(__name__)
        self.security_logger = get_security_logger()
        self._lock = threading.RLock()
        
        # Global rate limits
        self.global_max_per_minute = 1000
        self.global_max_per_hour = 10000
        self.global_max_per_day = 100000
        
        # Suspicious activity detection
        self.suspicious_patterns = {
            'rapid_fire': {'threshold': 20, 'window': 10},  # 20 requests in 10 seconds
            'high_volume': {'threshold': 500, 'window': 3600},  # 500 requests in 1 hour
            'burst_pattern': {'threshold': 10, 'burst_window': 5}  # 10 bursts in 5 minutes
        }
        
        # Start cleanup task
        asyncio.create_task(self._cleanup_task())
    
    def set_user_config(self, user_id: int, config: RateLimitConfig):
        """Set custom rate limit configuration for a user"""
        with self._lock:
            self.user_configs[user_id] = config
            self.logger.info(f"Updated rate limit config for user {user_id}")
    
    def get_user_config(self, user_id: int) -> RateLimitConfig:
        """Get rate limit configuration for a user"""
        return self.user_configs.get(user_id, self.default_config)
    
    def _get_user_limit(self, user_id: int) -> UserRateLimit:
        """Get or create user rate limit data"""
        if user_id not in self.user_limits:
            self.user_limits[user_id] = UserRateLimit(user_id=user_id)
        return self.user_limits[user_id]
    
    def _cleanup_expired_requests(self, requests_deque: deque, window_seconds: int):
        """Remove expired requests from deque"""
        current_time = time.time()
        while requests_deque and requests_deque[0] < current_time - window_seconds:
            requests_deque.popleft()
    
    def _check_global_limits(self) -> bool:
        """Check global rate limits"""
        current_time = time.time()
        
        # Clean up expired requests
        self._cleanup_expired_requests(self.global_limits['minute'], 60)
        self._cleanup_expired_requests(self.global_limits['hour'], 3600)
        self._cleanup_expired_requests(self.global_limits['day'], 86400)
        
        # Check limits
        if len(self.global_limits['minute']) >= self.global_max_per_minute:
            return False
        if len(self.global_limits['hour']) >= self.global_max_per_hour:
            return False
        if len(self.global_limits['day']) >= self.global_max_per_day:
            return False
        
        # Add current request
        self.global_limits['minute'].append(current_time)
        self.global_limits['hour'].append(current_time)
        self.global_limits['day'].append(current_time)
        
        return True
    
    def _detect_suspicious_activity(self, user_limit: UserRateLimit, config: RateLimitConfig) -> Optional[str]:
        """Detect suspicious activity patterns"""
        current_time = time.time()
        
        # Rapid fire detection
        rapid_requests = [req for req in user_limit.requests_per_minute 
                         if req > current_time - self.suspicious_patterns['rapid_fire']['window']]
        if len(rapid_requests) >= self.suspicious_patterns['rapid_fire']['threshold']:
            return "rapid_fire"
        
        # High volume detection
        high_volume_requests = [req for req in user_limit.requests_per_hour 
                               if req > current_time - self.suspicious_patterns['high_volume']['window']]
        if len(high_volume_requests) >= self.suspicious_patterns['high_volume']['threshold']:
            return "high_volume"
        
        # Burst pattern detection
        if user_limit.burst_count >= self.suspicious_patterns['burst_pattern']['threshold']:
            return "burst_pattern"
        
        return None
    
    async def check_rate_limit(self, user_id: int, action: str = "general") -> Tuple[bool, Optional[str]]:
        """
        Check if user is within rate limits
        Returns: (is_allowed, reason_if_denied)
        """
        current_time = time.time()
        
        with self._lock:
            # Check global limits first
            if not self._check_global_limits():
                self.security_logger.warning(
                    "Global rate limit exceeded",
                    extra={'user_id': user_id, 'action': action}
                )
                return False, "عذراً، الخدمة مشغولة حالياً. يرجى المحاولة لاحقاً."
            
            user_limit = self._get_user_limit(user_id)
            config = self.get_user_config(user_id)
            
            # Check if user is in cooldown
            if user_limit.cooldown_until > current_time:
                remaining_cooldown = int(user_limit.cooldown_until - current_time)
                self.logger.warning(f"User {user_id} in cooldown for {remaining_cooldown}s")
                return False, f"يرجى الانتظار {remaining_cooldown} ثانية قبل المحاولة مرة أخرى."
            
            # Clean up expired requests
            self._cleanup_expired_requests(user_limit.requests_per_minute, 60)
            self._cleanup_expired_requests(user_limit.requests_per_hour, 3600)
            self._cleanup_expired_requests(user_limit.requests_per_day, 86400)
            
            # Check burst protection
            time_since_last = current_time - user_limit.last_request_time
            if time_since_last < 1:  # Less than 1 second since last request
                user_limit.burst_count += 1
                if user_limit.burst_count > config.burst_limit:
                    user_limit.cooldown_until = current_time + config.cooldown_seconds
                    self._log_violation(user_id, "burst_limit", action)
                    return False, f"تم تجاوز الحد المسموح. يرجى الانتظار {config.cooldown_seconds} ثانية."
            else:
                user_limit.burst_count = max(0, user_limit.burst_count - 1)
            
            # Check rate limits
            if len(user_limit.requests_per_minute) >= config.requests_per_minute:
                self._log_violation(user_id, "minute_limit", action)
                return False, "تم تجاوز الحد المسموح للدقيقة الواحدة. يرجى الانتظار."
            
            if len(user_limit.requests_per_hour) >= config.requests_per_hour:
                self._log_violation(user_id, "hour_limit", action)
                return False, "تم تجاوز الحد المسموح للساعة الواحدة. يرجى الانتظار."
            
            if len(user_limit.requests_per_day) >= config.requests_per_day:
                self._log_violation(user_id, "day_limit", action)
                return False, "تم تجاوز الحد المسموح لليوم الواحد."
            
            # Detect suspicious activity
            suspicious_activity = self._detect_suspicious_activity(user_limit, config)
            if suspicious_activity:
                self._log_violation(user_id, f"suspicious_{suspicious_activity}", action)
                user_limit.cooldown_until = current_time + (config.cooldown_seconds * 2)
                self.security_logger.warning(
                    f"Suspicious activity detected: {suspicious_activity}",
                    extra={'user_id': user_id, 'action': action, 'pattern': suspicious_activity}
                )
                return False, "تم اكتشاف نشاط مشبوه. تم تقييد الحساب مؤقتاً."
            
            # Record the request
            user_limit.requests_per_minute.append(current_time)
            user_limit.requests_per_hour.append(current_time)
            user_limit.requests_per_day.append(current_time)
            user_limit.last_request_time = current_time
            user_limit.total_requests += 1
            
            return True, None
    
    def _log_violation(self, user_id: int, violation_type: str, action: str):
        """Log rate limit violation"""
        current_time = time.time()
        user_limit = self._get_user_limit(user_id)
        
        user_limit.violations_count += 1
        if user_limit.first_violation_time is None:
            user_limit.first_violation_time = current_time
        
        self.security_logger.warning(
            f"Rate limit violation: {violation_type}",
            extra={
                'user_id': user_id,
                'action': action,
                'violation_type': violation_type,
                'total_violations': user_limit.violations_count,
                'total_requests': user_limit.total_requests
            }
        )
    
    async def reset_user_limits(self, user_id: int):
        """Reset rate limits for a specific user"""
        with self._lock:
            if user_id in self.user_limits:
                del self.user_limits[user_id]
                self.logger.info(f"Reset rate limits for user {user_id}")
    
    async def get_user_stats(self, user_id: int) -> Dict[str, any]:
        """Get rate limiting statistics for a user"""
        with self._lock:
            user_limit = self._get_user_limit(user_id)
            config = self.get_user_config(user_id)
            current_time = time.time()
            
            # Clean up expired requests
            self._cleanup_expired_requests(user_limit.requests_per_minute, 60)
            self._cleanup_expired_requests(user_limit.requests_per_hour, 3600)
            self._cleanup_expired_requests(user_limit.requests_per_day, 86400)
            
            return {
                'user_id': user_id,
                'requests_last_minute': len(user_limit.requests_per_minute),
                'requests_last_hour': len(user_limit.requests_per_hour),
                'requests_last_day': len(user_limit.requests_per_day),
                'total_requests': user_limit.total_requests,
                'violations_count': user_limit.violations_count,
                'is_in_cooldown': user_limit.cooldown_until > current_time,
                'cooldown_remaining': max(0, int(user_limit.cooldown_until - current_time)),
                'limits': {
                    'per_minute': config.requests_per_minute,
                    'per_hour': config.requests_per_hour,
                    'per_day': config.requests_per_day,
                    'burst_limit': config.burst_limit
                },
                'remaining': {
                    'per_minute': config.requests_per_minute - len(user_limit.requests_per_minute),
                    'per_hour': config.requests_per_hour - len(user_limit.requests_per_hour),
                    'per_day': config.requests_per_day - len(user_limit.requests_per_day)
                }
            }
    
    async def get_global_stats(self) -> Dict[str, any]:
        """Get global rate limiting statistics"""
        with self._lock:
            current_time = time.time()
            
            # Clean up expired requests
            self._cleanup_expired_requests(self.global_limits['minute'], 60)
            self._cleanup_expired_requests(self.global_limits['hour'], 3600)
            self._cleanup_expired_requests(self.global_limits['day'], 86400)
            
            return {
                'global_requests_last_minute': len(self.global_limits['minute']),
                'global_requests_last_hour': len(self.global_limits['hour']),
                'global_requests_last_day': len(self.global_limits['day']),
                'active_users': len(self.user_limits),
                'users_in_cooldown': sum(1 for u in self.user_limits.values() if u.cooldown_until > current_time),
                'total_violations': sum(u.violations_count for u in self.user_limits.values()),
                'global_limits': {
                    'per_minute': self.global_max_per_minute,
                    'per_hour': self.global_max_per_hour,
                    'per_day': self.global_max_per_day
                }
            }
    
    async def whitelist_user(self, user_id: int, duration_hours: int = 24):
        """Temporarily whitelist a user from rate limiting"""
        config = RateLimitConfig(
            requests_per_minute=1000,
            requests_per_hour=10000,
            requests_per_day=100000,
            burst_limit=100,
            cooldown_seconds=1
        )
        
        self.set_user_config(user_id, config)
        self.logger.info(f"Whitelisted user {user_id} for {duration_hours} hours")
        
        # Schedule removal of whitelist
        async def remove_whitelist():
            await asyncio.sleep(duration_hours * 3600)
            if user_id in self.user_configs:
                del self.user_configs[user_id]
                self.logger.info(f"Removed whitelist for user {user_id}")
        
        asyncio.create_task(remove_whitelist())
    
    async def blacklist_user(self, user_id: int, duration_hours: int = 1):
        """Temporarily blacklist a user (very strict limits)"""
        config = RateLimitConfig(
            requests_per_minute=1,
            requests_per_hour=5,
            requests_per_day=10,
            burst_limit=1,
            cooldown_seconds=300  # 5 minutes
        )
        
        self.set_user_config(user_id, config)
        self.security_logger.warning(
            f"Blacklisted user {user_id} for {duration_hours} hours",
            extra={'user_id': user_id, 'duration_hours': duration_hours}
        )
        
        # Schedule removal of blacklist
        async def remove_blacklist():
            await asyncio.sleep(duration_hours * 3600)
            if user_id in self.user_configs:
                del self.user_configs[user_id]
                self.logger.info(f"Removed blacklist for user {user_id}")
        
        asyncio.create_task(remove_blacklist())
    
    async def _cleanup_task(self):
        """Periodic cleanup task to remove old data"""
        while True:
            try:
                await asyncio.sleep(300)  # Run every 5 minutes
                current_time = time.time()
                
                with self._lock:
                    # Remove inactive users (no requests in last 24 hours)
                    inactive_users = []
                    for user_id, user_limit in self.user_limits.items():
                        if current_time - user_limit.last_request_time > 86400:
                            inactive_users.append(user_id)
                    
                    for user_id in inactive_users:
                        del self.user_limits[user_id]
                        self.logger.debug(f"Cleaned up inactive user {user_id}")
                    
                    # Clean up global limits
                    self._cleanup_expired_requests(self.global_limits['minute'], 60)
                    self._cleanup_expired_requests(self.global_limits['hour'], 3600)
                    self._cleanup_expired_requests(self.global_limits['day'], 86400)
                    
                    if inactive_users:
                        self.logger.info(f"Cleaned up {len(inactive_users)} inactive users")
                        
            except Exception as e:
                self.logger.error(f"Error in cleanup task: {e}")