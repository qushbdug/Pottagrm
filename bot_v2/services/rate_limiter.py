"""
Enhanced Rate Limiter for Yemen Net Bot v2
Implements sophisticated rate limiting with caching and monitoring
"""

import time
import asyncio
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from collections import defaultdict, deque
from functools import wraps
import threading

from ..core.exceptions import RateLimitException
from ..core.config import config

@dataclass
class RateLimitRule:
    """Rate limiting rule configuration"""
    name: str
    max_requests: int
    window_seconds: int
    burst_size: int = 0
    penalty_seconds: int = 0
    user_specific: bool = True
    global_limit: bool = False
    priority: int = 1

@dataclass
class RateLimitStats:
    """Rate limiting statistics"""
    total_requests: int = 0
    allowed_requests: int = 0
    blocked_requests: int = 0
    rate_limited_users: int = 0
    current_active_users: int = 0
    peak_requests_per_second: float = 0.0
    avg_requests_per_second: float = 0.0
    last_reset: float = 0.0

class RateLimiter:
    """Enhanced rate limiter with multiple strategies and monitoring"""
    
    def __init__(self):
        self.config = config
        self.logger = logging.getLogger('RateLimiter')
        self.stats = RateLimitStats()
        
        # Rate limiting storage
        self.user_requests: Dict[int, deque] = defaultdict(lambda: deque())
        self.global_requests: deque = deque()
        self.user_penalties: Dict[int, float] = {}
        self.global_penalty_until: float = 0.0
        
        # Rules configuration
        self.rules: List[RateLimitRule] = self._setup_default_rules()
        
        # Threading
        self.lock = threading.RLock()
        
        # Start cleanup task
        self._start_cleanup_task()
    
    def _setup_default_rules(self) -> List[RateLimitRule]:
        """Setup default rate limiting rules"""
        return [
            # General user rate limiting
            RateLimitRule(
                name="user_general",
                max_requests=30,
                window_seconds=60,
                burst_size=5,
                penalty_seconds=300,
                user_specific=True,
                priority=1
            ),
            
            # Message rate limiting
            RateLimitRule(
                name="user_messages",
                max_requests=100,
                window_seconds=300,
                burst_size=20,
                penalty_seconds=600,
                user_specific=True,
                priority=2
            ),
            
            # Button clicks rate limiting
            RateLimitRule(
                name="user_buttons",
                max_requests=50,
                window_seconds=60,
                burst_size=10,
                penalty_seconds=180,
                user_specific=True,
                priority=2
            ),
            
            # Admin operations rate limiting
            RateLimitRule(
                name="admin_operations",
                max_requests=200,
                window_seconds=300,
                burst_size=50,
                penalty_seconds=900,
                user_specific=True,
                priority=3
            ),
            
            # Global rate limiting
            RateLimitRule(
                name="global_limit",
                max_requests=1000,
                window_seconds=60,
                burst_size=200,
                penalty_seconds=1800,
                user_specific=False,
                global_limit=True,
                priority=4
            ),
            
            # Payment operations rate limiting
            RateLimitRule(
                name="payment_operations",
                max_requests=10,
                window_seconds=300,
                burst_size=2,
                penalty_seconds=1800,
                user_specific=True,
                priority=5
            ),
            
            # File upload rate limiting
            RateLimitRule(
                name="file_uploads",
                max_requests=5,
                window_seconds=300,
                burst_size=1,
                penalty_seconds=3600,
                user_specific=True,
                priority=5
            )
        ]
    
    def _start_cleanup_task(self):
        """Start background cleanup task"""
        def cleanup_loop():
            while True:
                try:
                    time.sleep(60)  # Cleanup every minute
                    self._cleanup_expired_requests()
                except Exception as e:
                    self.logger.error(f"Cleanup task error: {e}")
        
        cleanup_thread = threading.Thread(target=cleanup_loop, daemon=True)
        cleanup_thread.start()
        self.logger.info("Rate limiter cleanup task started")
    
    def _cleanup_expired_requests(self):
        """Clean up expired request records"""
        current_time = time.time()
        
        with self.lock:
            # Clean user requests
            for user_id in list(self.user_requests.keys()):
                user_queue = self.user_requests[user_id]
                while user_queue and current_time - user_queue[0] > max(rule.window_seconds for rule in self.rules):
                    user_queue.popleft()
                
                # Remove empty user queues
                if not user_queue:
                    del self.user_requests[user_id]
            
            # Clean global requests
            while self.global_requests and current_time - self.global_requests[0] > max(rule.window_seconds for rule in self.rules):
                self.global_requests.popleft()
            
            # Clean expired penalties
            expired_penalties = [user_id for user_id, penalty_until in self.user_penalties.items() 
                               if current_time > penalty_until]
            for user_id in expired_penalties:
                del self.user_penalties[user_id]
            
            # Clean global penalty
            if current_time > self.global_penalty_until:
                self.global_penalty_until = 0.0
            
            # Update stats
            self.stats.current_active_users = len(self.user_requests)
            self.stats.last_reset = current_time
    
    def add_rule(self, rule: RateLimitRule):
        """Add a new rate limiting rule"""
        with self.lock:
            # Remove existing rule with same name
            self.rules = [r for r in self.rules if r.name != rule.name]
            self.rules.append(rule)
            
            # Sort by priority
            self.rules.sort(key=lambda r: r.priority)
            
            self.logger.info(f"Added rate limiting rule: {rule.name}")
    
    def remove_rule(self, rule_name: str):
        """Remove a rate limiting rule"""
        with self.lock:
            original_count = len(self.rules)
            self.rules = [r for r in self.rules if r.name != rule_name]
            
            if len(self.rules) < original_count:
                self.logger.info(f"Removed rate limiting rule: {rule_name}")
            else:
                self.logger.warning(f"Rate limiting rule not found: {rule_name}")
    
    def is_rate_limited(self, user_id: int, rule_name: str = None) -> Tuple[bool, Optional[str], int]:
        """
        Check if user is rate limited
        Returns: (is_limited, reason, retry_after)
        """
        current_time = time.time()
        
        with self.lock:
            # Check if user is under penalty
            if user_id in self.user_penalties:
                penalty_until = self.user_penalties[user_id]
                if current_time < penalty_until:
                    retry_after = int(penalty_until - current_time)
                    return True, f"User under penalty for {rule_name or 'violation'}", retry_after
            
            # Check global penalty
            if current_time < self.global_penalty_until:
                retry_after = int(self.global_penalty_until - current_time)
                return True, "Global rate limit exceeded", retry_after
            
            # Find applicable rules
            applicable_rules = []
            if rule_name:
                applicable_rules = [r for r in self.rules if r.name == rule_name]
            else:
                applicable_rules = [r for r in self.rules if r.user_specific]
            
            for rule in applicable_rules:
                if rule.user_specific:
                    # Check user-specific rule
                    user_queue = self.user_requests[user_id]
                    
                    # Remove expired requests
                    while user_queue and current_time - user_queue[0] > rule.window_seconds:
                        user_queue.popleft()
                    
                    # Check if limit exceeded
                    if len(user_queue) >= rule.max_requests:
                        retry_after = int(rule.window_seconds - (current_time - user_queue[0]))
                        
                        # Apply penalty if configured
                        if rule.penalty_seconds > 0:
                            penalty_until = current_time + rule.penalty_seconds
                            self.user_penalties[user_id] = penalty_until
                            self.stats.rate_limited_users += 1
                        
                        return True, f"Rate limit exceeded for {rule.name}", retry_after
                
                elif rule.global_limit:
                    # Check global rule
                    global_queue = self.global_requests
                    
                    # Remove expired requests
                    while global_queue and current_time - global_queue[0] > rule.window_seconds:
                        global_queue.popleft()
                    
                    # Check if limit exceeded
                    if len(global_queue) >= rule.max_requests:
                        retry_after = int(rule.window_seconds - (current_time - global_queue[0]))
                        
                        # Apply global penalty
                        if rule.penalty_seconds > 0:
                            self.global_penalty_until = current_time + rule.penalty_seconds
                        
                        return True, f"Global rate limit exceeded for {rule.name}", retry_after
            
            return False, None, 0
    
    def record_request(self, user_id: int, rule_name: str = None):
        """Record a user request"""
        current_time = time.time()
        
        with self.lock:
            # Record user request
            user_queue = self.user_requests[user_id]
            user_queue.append(current_time)
            
            # Record global request
            self.global_requests.append(current_time)
            
            # Update stats
            self.stats.total_requests += 1
            self.stats.allowed_requests += 1
            
            # Calculate current requests per second
            current_rps = len([req for req in user_queue if current_time - req <= 1.0])
            if current_rps > self.stats.peak_requests_per_second:
                self.stats.peak_requests_per_second = current_rps
            
            # Update average RPS
            total_time = max(1.0, current_time - self.stats.last_reset)
            self.stats.avg_requests_per_second = self.stats.total_requests / total_time
    
    def block_request(self, user_id: int, rule_name: str = None):
        """Record a blocked request"""
        with self.lock:
            self.stats.total_requests += 1
            self.stats.blocked_requests += 1
    
    def get_user_stats(self, user_id: int) -> Dict[str, Any]:
        """Get rate limiting statistics for a specific user"""
        current_time = time.time()
        
        with self.lock:
            user_queue = self.user_requests.get(user_id, deque())
            
            # Calculate requests per rule
            rule_stats = {}
            for rule in self.rules:
                if rule.user_specific:
                    rule_requests = [req for req in user_queue if current_time - req <= rule.window_seconds]
                    rule_stats[rule.name] = {
                        'current_requests': len(rule_requests),
                        'max_requests': rule.max_requests,
                        'window_seconds': rule.window_seconds,
                        'remaining_requests': max(0, rule.max_requests - len(rule_requests)),
                        'time_to_reset': max(0, rule.window_seconds - (current_time - rule_requests[0])) if rule_requests else 0
                    }
            
            # Check penalty status
            penalty_info = None
            if user_id in self.user_penalties:
                penalty_until = self.user_penalties[user_id]
                if current_time < penalty_until:
                    penalty_info = {
                        'is_penalized': True,
                        'penalty_until': penalty_until,
                        'remaining_penalty': int(penalty_until - current_time),
                        'reason': 'Rate limit violation'
                    }
                else:
                    penalty_info = {'is_penalized': False}
            else:
                penalty_info = {'is_penalized': False}
            
            return {
                'user_id': user_id,
                'total_requests': len(user_queue),
                'rule_stats': rule_stats,
                'penalty_info': penalty_info,
                'last_request': user_queue[-1] if user_queue else None
            }
    
    def get_global_stats(self) -> Dict[str, Any]:
        """Get global rate limiting statistics"""
        current_time = time.time()
        
        with self.lock:
            return {
                'total_requests': self.stats.total_requests,
                'allowed_requests': self.stats.allowed_requests,
                'blocked_requests': self.stats.blocked_requests,
                'rate_limited_users': self.stats.rate_limited_users,
                'current_active_users': self.stats.current_active_users,
                'peak_requests_per_second': self.stats.peak_requests_per_second,
                'avg_requests_per_second': round(self.stats.avg_requests_per_second, 2),
                'global_penalty_active': current_time < self.global_penalty_until,
                'global_penalty_until': self.global_penalty_until if self.global_penalty_until > 0 else None,
                'total_users_tracked': len(self.user_requests),
                'total_penalties_active': len([p for p in self.user_penalties.values() if p > current_time])
            }
    
    def reset_user_limits(self, user_id: int):
        """Reset rate limits for a specific user"""
        with self.lock:
            if user_id in self.user_requests:
                del self.user_requests[user_id]
            
            if user_id in self.user_penalties:
                del self.user_penalties[user_id]
            
            self.logger.info(f"Reset rate limits for user {user_id}")
    
    def reset_all_limits(self):
        """Reset all rate limits"""
        with self.lock:
            self.user_requests.clear()
            self.user_penalties.clear()
            self.global_requests.clear()
            self.global_penalty_until = 0.0
            
            # Reset stats
            self.stats = RateLimitStats()
            
            self.logger.info("All rate limits reset")
    
    def update_rule(self, rule_name: str, **kwargs):
        """Update an existing rate limiting rule"""
        with self.lock:
            for rule in self.rules:
                if rule.name == rule_name:
                    for key, value in kwargs.items():
                        if hasattr(rule, key):
                            setattr(rule, key, value)
                    
                    self.logger.info(f"Updated rate limiting rule: {rule_name}")
                    return
            
            self.logger.warning(f"Rate limiting rule not found: {rule_name}")

def rate_limit(rule_name: str = None, user_id_param: str = 'user_id'):
    """Decorator for rate limiting functions"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get rate limiter instance
            rate_limiter = getattr(config, 'rate_limiter', None)
            if not rate_limiter:
                return await func(*args, **kwargs)
            
            # Extract user ID from function parameters
            user_id = None
            if user_id_param in kwargs:
                user_id = kwargs[user_id_param]
            else:
                # Try to find user_id in args (assuming it's the first parameter after self)
                if len(args) > 1:
                    user_id = args[1]  # Assuming user_id is the second parameter
            
            if user_id is None:
                # If we can't determine user_id, allow the request
                return await func(*args, **kwargs)
            
            # Check rate limit
            is_limited, reason, retry_after = rate_limiter.is_rate_limited(user_id, rule_name)
            
            if is_limited:
                rate_limiter.block_request(user_id, rule_name)
                raise RateLimitException(
                    message=f"Rate limit exceeded: {reason}",
                    user_id=user_id,
                    limit_type=rule_name or "general",
                    retry_after=retry_after
                )
            
            # Record request and proceed
            rate_limiter.record_request(user_id, rule_name)
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator

# Global rate limiter instance
rate_limiter = RateLimiter()