#!/usr/bin/env python3
"""
Enhanced Rate Limiting Service
Version 2.0 - Advanced Request Management
"""

import time
import logging
import threading
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict, deque
import json
import hashlib
import ipaddress

from bot_v2.config.settings import (
    RATE_LIMIT_MAX_REQUESTS, RATE_LIMIT_WINDOW,
    ADMIN_RATE_LIMIT, SUPER_ADMIN_RATE_LIMIT,
    API_RATE_LIMITS, SECURITY_THRESHOLDS
)

logger = logging.getLogger(__name__)

@dataclass
class RateLimitConfig:
    """Configuration for rate limiting"""
    max_requests: int = RATE_LIMIT_MAX_REQUESTS
    window: int = RATE_LIMIT_WINDOW  # seconds
    burst_limit: int = 5  # Allow burst of requests
    penalty_duration: int = 300  # 5 minutes penalty
    whitelist: List[str] = field(default_factory=list)
    blacklist: List[str] = field(default_factory=list)
    custom_rules: Dict[str, Any] = field(default_factory=dict)

@dataclass
class RateLimitInfo:
    """Information about rate limiting for a user/IP"""
    request_count: int = 0
    first_request: float = field(default_factory=time.time)
    last_request: float = field(default_factory=time.time)
    is_blocked: bool = False
    blocked_until: Optional[float] = None
    penalty_count: int = 0
    suspicious_activities: List[Dict[str, Any]] = field(default_factory=list)
    custom_limits: Dict[str, Any] = field(default_factory=dict)

class RateLimiter:
    """Advanced rate limiting system with multiple strategies"""
    
    def __init__(self, config: RateLimitConfig = None):
        self.config = config or RateLimitConfig()
        self.requests: Dict[str, RateLimitInfo] = defaultdict(RateLimitInfo)
        self.ip_requests: Dict[str, RateLimitInfo] = defaultdict(RateLimitInfo)
        self.user_requests: Dict[int, RateLimitInfo] = defaultdict(RateLimitInfo)
        self.endpoint_limits: Dict[str, RateLimitConfig] = {}
        self.lock = threading.RLock()
        self.cleanup_thread = None
        self.shutdown_event = threading.Event()
        
        # Initialize endpoint-specific limits
        self._initialize_endpoint_limits()
        
        # Start cleanup thread
        self._start_cleanup_thread()
    
    def _initialize_endpoint_limits(self):
        """Initialize endpoint-specific rate limits"""
        for endpoint, limits in API_RATE_LIMITS.items():
            self.endpoint_limits[endpoint] = RateLimitConfig(
                max_requests=limits['requests'],
                window=limits['window']
            )
    
    def _start_cleanup_thread(self):
        """Start background cleanup thread"""
        def cleanup_worker():
            while not self.shutdown_event.is_set():
                try:
                    self._cleanup_expired_entries()
                    time.sleep(60)  # Cleanup every minute
                except Exception as e:
                    logger.error(f"Rate limiter cleanup error: {e}")
                    time.sleep(30)
        
        self.cleanup_thread = threading.Thread(
            target=cleanup_worker,
            daemon=True,
            name="RateLimiterCleanup"
        )
        self.cleanup_thread.start()
    
    def _cleanup_expired_entries(self):
        """Clean up expired rate limit entries"""
        current_time = time.time()
        
        with self.lock:
            # Clean IP requests
            expired_ips = [
                ip for ip, info in self.ip_requests.items()
                if current_time - info.last_request > self.config.window * 2
            ]
            for ip in expired_ips:
                del self.ip_requests[ip]
            
            # Clean user requests
            expired_users = [
                user_id for user_id, info in self.user_requests.items()
                if current_time - info.last_request > self.config.window * 2
            ]
            for user_id in expired_users:
                del self.user_requests[user_id]
            
            # Clean general requests
            expired_keys = [
                key for key, info in self.requests.items()
                if current_time - info.last_request > self.config.window * 2
            ]
            for key in expired_keys:
                del self.requests[key]
    
    def _get_identifier(self, user_id: Optional[int] = None, ip_address: Optional[str] = None) -> str:
        """Generate unique identifier for rate limiting"""
        if user_id:
            return f"user_{user_id}"
        elif ip_address:
            return f"ip_{ip_address}"
        else:
            return "anonymous"
    
    def _is_whitelisted(self, identifier: str) -> bool:
        """Check if identifier is whitelisted"""
        return identifier in self.config.whitelist
    
    def _is_blacklisted(self, identifier: str) -> bool:
        """Check if identifier is blacklisted"""
        return identifier in self.config.blacklist
    
    def _get_rate_limit_config(self, endpoint: str = None, user_role: str = None) -> RateLimitConfig:
        """Get rate limit configuration for specific endpoint/user role"""
        config = self.config.copy()
        
        # Apply endpoint-specific limits
        if endpoint and endpoint in self.endpoint_limits:
            endpoint_config = self.endpoint_limits[endpoint]
            config.max_requests = endpoint_config.max_requests
            config.window = endpoint_config.window
        
        # Apply role-specific limits
        if user_role == 'admin':
            config.max_requests = ADMIN_RATE_LIMIT
        elif user_role == 'super_admin':
            config.max_requests = SUPER_ADMIN_RATE_LIMIT
        
        return config
    
    def _detect_suspicious_activity(self, identifier: str, request_data: Dict[str, Any]) -> bool:
        """Detect suspicious activity patterns"""
        current_time = time.time()
        info = self.requests.get(identifier)
        
        if not info:
            return False
        
        # Check for rapid successive requests
        if current_time - info.last_request < 0.1:  # Less than 100ms between requests
            info.suspicious_activities.append({
                'type': 'rapid_requests',
                'timestamp': current_time,
                'data': request_data
            })
            return True
        
        # Check for unusual request patterns
        if len(info.suspicious_activities) > 5:
            info.suspicious_activities.append({
                'type': 'multiple_suspicious',
                'timestamp': current_time,
                'data': request_data
            })
            return True
        
        return False
    
    def is_allowed(
        self, 
        user_id: Optional[int] = None, 
        ip_address: Optional[str] = None,
        endpoint: str = None,
        user_role: str = None,
        request_data: Dict[str, Any] = None
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Check if request is allowed based on rate limiting rules
        
        Returns:
            Tuple[bool, Dict]: (is_allowed, rate_limit_info)
        """
        current_time = time.time()
        request_data = request_data or {}
        
        # Get identifier
        identifier = self._get_identifier(user_id, ip_address)
        
        # Check whitelist/blacklist
        if self._is_whitelisted(identifier):
            return True, {'status': 'whitelisted', 'identifier': identifier}
        
        if self._is_blacklisted(identifier):
            return False, {
                'status': 'blacklisted', 
                'identifier': identifier,
                'reason': 'IP/User is blacklisted'
            }
        
        # Get rate limit configuration
        config = self._get_rate_limit_config(endpoint, user_role)
        
        with self.lock:
            # Get or create rate limit info
            if user_id:
                info = self.user_requests[user_id]
            elif ip_address:
                info = self.ip_requests[ip_address]
            else:
                info = self.requests[identifier]
            
            # Check if currently blocked
            if info.is_blocked and info.blocked_until and current_time < info.blocked_until:
                remaining_block = info.blocked_until - current_time
                return False, {
                    'status': 'blocked',
                    'identifier': identifier,
                    'remaining_block': remaining_block,
                    'blocked_until': info.blocked_until,
                    'penalty_count': info.penalty_count
                }
            
            # Reset block if expired
            if info.is_blocked and (not info.blocked_until or current_time >= info.blocked_until):
                info.is_blocked = False
                info.blocked_until = None
            
            # Check window-based limits
            window_start = current_time - config.window
            if current_time - info.first_request > config.window:
                # Reset window
                info.request_count = 1
                info.first_request = current_time
                info.last_request = current_time
            else:
                # Check burst limit
                if current_time - info.last_request < 0.1:  # Less than 100ms
                    if info.request_count >= config.burst_limit:
                        # Apply penalty
                        self._apply_penalty(info, config)
                        return False, {
                            'status': 'burst_limit_exceeded',
                            'identifier': identifier,
                            'penalty_duration': config.penalty_duration,
                            'burst_limit': config.burst_limit
                        }
                
                # Check regular limits
                if info.request_count >= config.max_requests:
                    # Apply penalty
                    self._apply_penalty(info, config)
                    return False, {
                        'status': 'rate_limit_exceeded',
                        'identifier': identifier,
                        'max_requests': config.max_requests,
                        'window': config.window,
                        'penalty_duration': config.penalty_duration
                    }
                
                # Increment request count
                info.request_count += 1
                info.last_request = current_time
            
            # Detect suspicious activity
            if self._detect_suspicious_activity(identifier, request_data):
                logger.warning(f"Suspicious activity detected for {identifier}")
                # Could implement additional measures here
            
            # Calculate remaining requests
            remaining_requests = max(0, config.max_requests - info.request_count)
            reset_time = info.first_request + config.window
            
            return True, {
                'status': 'allowed',
                'identifier': identifier,
                'remaining_requests': remaining_requests,
                'reset_time': reset_time,
                'current_count': info.request_count,
                'max_requests': config.max_requests,
                'window': config.window
            }
    
    def _apply_penalty(self, info: RateLimitInfo, config: RateLimitConfig):
        """Apply penalty for exceeding rate limits"""
        info.penalty_count += 1
        info.is_blocked = True
        
        # Progressive penalty duration
        penalty_multiplier = min(info.penalty_count, 5)  # Cap at 5x
        penalty_duration = config.penalty_duration * penalty_multiplier
        
        info.blocked_until = time.time() + penalty_duration
        
        logger.warning(f"Rate limit penalty applied: {penalty_duration}s for {penalty_multiplier}x violation")
    
    def record_request(
        self, 
        user_id: Optional[int] = None, 
        ip_address: Optional[str] = None,
        endpoint: str = None,
        user_role: str = None,
        request_data: Dict[str, Any] = None
    ):
        """Record a successful request"""
        identifier = self._get_identifier(user_id, ip_address)
        
        with self.lock:
            if user_id:
                info = self.user_requests[user_id]
            elif ip_address:
                info = self.ip_requests[ip_address]
            else:
                info = self.requests[identifier]
            
            # Update last request time
            info.last_request = time.time()
    
    def get_rate_limit_status(
        self, 
        user_id: Optional[int] = None, 
        ip_address: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get current rate limit status for user/IP"""
        identifier = self._get_identifier(user_id, ip_address)
        
        with self.lock:
            if user_id and user_id in self.user_requests:
                info = self.user_requests[user_id]
            elif ip_address and ip_address in self.ip_requests:
                info = self.ip_requests[ip_address]
            elif identifier in self.requests:
                info = self.requests[identifier]
            else:
                return {'status': 'no_data', 'identifier': identifier}
            
            current_time = time.time()
            
            return {
                'identifier': identifier,
                'request_count': info.request_count,
                'first_request': info.first_request,
                'last_request': info.last_request,
                'is_blocked': info.is_blocked,
                'blocked_until': info.blocked_until,
                'penalty_count': info.penalty_count,
                'suspicious_activities_count': len(info.suspicious_activities),
                'time_since_last_request': current_time - info.last_request if info.last_request else 0
            }
    
    def add_to_whitelist(self, identifier: str):
        """Add identifier to whitelist"""
        with self.lock:
            if identifier not in self.config.whitelist:
                self.config.whitelist.append(identifier)
                logger.info(f"Added {identifier} to whitelist")
    
    def remove_from_whitelist(self, identifier: str):
        """Remove identifier from whitelist"""
        with self.lock:
            if identifier in self.config.whitelist:
                self.config.whitelist.remove(identifier)
                logger.info(f"Removed {identifier} from whitelist")
    
    def add_to_blacklist(self, identifier: str, reason: str = None):
        """Add identifier to blacklist"""
        with self.lock:
            if identifier not in self.config.blacklist:
                self.config.blacklist.append(identifier)
                logger.warning(f"Added {identifier} to blacklist. Reason: {reason}")
    
    def remove_from_blacklist(self, identifier: str):
        """Remove identifier from blacklist"""
        with self.lock:
            if identifier in self.config.blacklist:
                self.config.blacklist.remove(identifier)
                logger.info(f"Removed {identifier} from blacklist")
    
    def reset_rate_limits(self, user_id: Optional[int] = None, ip_address: Optional[str] = None):
        """Reset rate limits for specific user/IP"""
        identifier = self._get_identifier(user_id, ip_address)
        
        with self.lock:
            if user_id and user_id in self.user_requests:
                del self.user_requests[user_id]
            elif ip_address and ip_address in self.ip_requests:
                del self.ip_requests[ip_address]
            elif identifier in self.requests:
                del self.requests[identifier]
            
            logger.info(f"Reset rate limits for {identifier}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get rate limiter statistics"""
        with self.lock:
            current_time = time.time()
            
            # Count blocked users/IPs
            blocked_count = sum(
                1 for info in self.user_requests.values() 
                if info.is_blocked and info.blocked_until and current_time < info.blocked_until
            )
            
            blocked_ip_count = sum(
                1 for info in self.ip_requests.values() 
                if info.is_blocked and info.blocked_until and current_time < info.blocked_until
            )
            
            # Count suspicious activities
            total_suspicious = sum(
                len(info.suspicious_activities) 
                for info in self.user_requests.values()
            ) + sum(
                len(info.suspicious_activities) 
                for info in self.ip_requests.values()
            )
            
            return {
                'total_users': len(self.user_requests),
                'total_ips': len(self.ip_requests),
                'total_requests': len(self.requests),
                'blocked_users': blocked_count,
                'blocked_ips': blocked_ip_count,
                'whitelisted': len(self.config.whitelist),
                'blacklisted': len(self.config.blacklist),
                'total_suspicious_activities': total_suspicious,
                'endpoint_limits': len(self.endpoint_limits)
            }
    
    def export_config(self) -> Dict[str, Any]:
        """Export current rate limiter configuration"""
        return {
            'config': {
                'max_requests': self.config.max_requests,
                'window': self.config.window,
                'burst_limit': self.config.burst_limit,
                'penalty_duration': self.config.penalty_duration
            },
            'whitelist': self.config.whitelist.copy(),
            'blacklist': self.config.blacklist.copy(),
            'endpoint_limits': {
                endpoint: {
                    'max_requests': config.max_requests,
                    'window': config.window
                }
                for endpoint, config in self.endpoint_limits.items()
            }
        }
    
    def import_config(self, config_data: Dict[str, Any]):
        """Import rate limiter configuration"""
        with self.lock:
            if 'config' in config_data:
                self.config.max_requests = config_data['config'].get('max_requests', self.config.max_requests)
                self.config.window = config_data['config'].get('window', self.config.window)
                self.config.burst_limit = config_data['config'].get('burst_limit', self.config.burst_limit)
                self.config.penalty_duration = config_data['config'].get('penalty_duration', self.config.penalty_duration)
            
            if 'whitelist' in config_data:
                self.config.whitelist = config_data['whitelist']
            
            if 'blacklist' in config_data:
                self.config.blacklist = config_data['blacklist']
            
            if 'endpoint_limits' in config_data:
                for endpoint, limits in config_data['endpoint_limits'].items():
                    self.endpoint_limits[endpoint] = RateLimitConfig(
                        max_requests=limits['max_requests'],
                        window=limits['window']
                    )
            
            logger.info("Rate limiter configuration imported")
    
    def shutdown(self):
        """Shutdown rate limiter"""
        self.shutdown_event.set()
        
        if self.cleanup_thread and self.cleanup_thread.is_alive():
            self.cleanup_thread.join(timeout=5.0)
        
        logger.info("Rate limiter shutdown complete")

# Global rate limiter instance
_rate_limiter: Optional[RateLimiter] = None

def get_rate_limiter() -> RateLimiter:
    """Get global rate limiter instance"""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter

def shutdown_rate_limiter():
    """Shutdown global rate limiter"""
    global _rate_limiter
    if _rate_limiter:
        _rate_limiter.shutdown()
        _rate_limiter = None

# Decorator for rate limiting
def rate_limit(
    max_requests: int = None,
    window: int = None,
    user_id_param: str = 'user_id',
    ip_param: str = 'ip_address',
    endpoint_param: str = 'endpoint'
):
    """Decorator for rate limiting functions"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            rate_limiter = get_rate_limiter()
            
            # Extract parameters
            user_id = kwargs.get(user_id_param)
            ip_address = kwargs.get(ip_param)
            endpoint = kwargs.get(endpoint_param)
            
            # Check rate limit
            is_allowed, info = rate_limiter.is_allowed(
                user_id=user_id,
                ip_address=ip_address,
                endpoint=endpoint
            )
            
            if not is_allowed:
                logger.warning(f"Rate limit exceeded: {info}")
                raise Exception(f"Rate limit exceeded: {info['status']}")
            
            # Record request
            rate_limiter.record_request(
                user_id=user_id,
                ip_address=ip_address,
                endpoint=endpoint
            )
            
            return func(*args, **kwargs)
        
        return wrapper
    return decorator

# Cleanup on module unload
import atexit
atexit.register(shutdown_rate_limiter)

if __name__ == "__main__":
    # Test rate limiter
    try:
        rate_limiter = RateLimiter()
        print("✅ Rate limiter initialized successfully")
        
        # Test basic rate limiting
        user_id = 12345
        ip_address = "192.168.1.1"
        
        # Check if allowed
        is_allowed, info = rate_limiter.is_allowed(user_id=user_id, ip_address=ip_address)
        print(f"✅ Rate limit check: {is_allowed} - {info}")
        
        # Record request
        rate_limiter.record_request(user_id=user_id, ip_address=ip_address)
        print("✅ Request recorded")
        
        # Get statistics
        stats = rate_limiter.get_statistics()
        print(f"✅ Statistics: {stats}")
        
        rate_limiter.shutdown()
        print("✅ Rate limiter shutdown successfully")
        
    except Exception as e:
        print(f"❌ Rate limiter test failed: {e}")
        exit(1)