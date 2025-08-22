"""
Enhanced Cache Manager for Yemen Net Bot v2
Implements TTL, LRU eviction, and comprehensive monitoring
"""

import time
import asyncio
import logging
import threading
from typing import Dict, Any, Optional, List, Tuple, Union, Callable
from dataclasses import dataclass, field
from collections import OrderedDict, defaultdict
from functools import wraps
import json
import hashlib
import pickle

from ..core.exceptions import BotException
from ..core.config import config

@dataclass
class CacheItem:
    """Cache item with metadata"""
    key: str
    value: Any
    created_at: float
    accessed_at: float
    access_count: int = 0
    ttl: Optional[int] = None
    size_bytes: int = 0
    tags: List[str] = field(default_factory=list)

@dataclass
class CacheStats:
    """Cache performance statistics"""
    total_items: int = 0
    total_size_bytes: int = 0
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    expired_items: int = 0
    hit_rate: float = 0.0
    avg_item_size: float = 0.0
    memory_usage_mb: float = 0.0
    last_cleanup: float = 0.0

class CacheManager:
    """Enhanced cache manager with TTL, LRU, and monitoring"""
    
    def __init__(self, max_size_mb: int = 100, default_ttl: int = 300):
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.default_ttl = default_ttl
        self.logger = logging.getLogger('CacheManager')
        self.stats = CacheStats()
        
        # Cache storage
        self.cache: OrderedDict[str, CacheItem] = OrderedDict()
        self.tags_index: Dict[str, List[str]] = defaultdict(list)
        
        # Threading
        self.lock = threading.RLock()
        
        # Start cleanup task
        self._start_cleanup_task()
        
        self.logger.info(f"Cache manager initialized with {max_size_mb}MB limit")
    
    def _start_cleanup_task(self):
        """Start background cleanup task"""
        def cleanup_loop():
            while True:
                try:
                    time.sleep(60)  # Cleanup every minute
                    self._cleanup_expired_items()
                    self._enforce_size_limit()
                except Exception as e:
                    self.logger.error(f"Cleanup task error: {e}")
        
        cleanup_thread = threading.Thread(target=cleanup_loop, daemon=True)
        cleanup_thread.start()
        self.logger.info("Cache cleanup task started")
    
    def _calculate_size(self, value: Any) -> int:
        """Calculate approximate size of a value in bytes"""
        try:
            if isinstance(value, (str, bytes)):
                return len(value)
            elif isinstance(value, (int, float)):
                return 8
            elif isinstance(value, (list, tuple)):
                return sum(self._calculate_size(item) for item in value)
            elif isinstance(value, dict):
                return sum(self._calculate_size(k) + self._calculate_size(v) for k, v in value.items())
            else:
                # Try to serialize to JSON for size estimation
                return len(json.dumps(value, default=str).encode('utf-8'))
        except Exception:
            return 1024  # Default size if calculation fails
    
    def _cleanup_expired_items(self):
        """Remove expired cache items"""
        current_time = time.time()
        expired_keys = []
        
        with self.lock:
            for key, item in self.cache.items():
                if item.ttl and (current_time - item.created_at) > item.ttl:
                    expired_keys.append(key)
            
            for key in expired_keys:
                self._remove_item(key)
                self.stats.expired_items += 1
            
            if expired_keys:
                self.logger.debug(f"Cleaned up {len(expired_keys)} expired items")
    
    def _enforce_size_limit(self):
        """Enforce maximum cache size using LRU eviction"""
        while self.stats.total_size_bytes > self.max_size_bytes and self.cache:
            # Remove least recently used item
            key, item = self.cache.popitem(last=False)
            self._remove_item(key)
            self.stats.evictions += 1
            
            self.logger.debug(f"Evicted item {key} due to size limit")
    
    def _remove_item(self, key: str):
        """Remove item from cache and update statistics"""
        if key in self.cache:
            item = self.cache[key]
            
            # Remove from tags index
            for tag in item.tags:
                if tag in self.tags_index and key in self.tags_index[tag]:
                    self.tags_index[tag].remove(key)
                    if not self.tags_index[tag]:
                        del self.tags_index[tag]
            
            # Update statistics
            self.stats.total_items -= 1
            self.stats.total_size_bytes -= item.size_bytes
            
            # Remove from cache
            del self.cache[key]
    
    def _update_access_stats(self, key: str):
        """Update access statistics for a cache item"""
        if key in self.cache:
            item = self.cache[key]
            item.accessed_at = time.time()
            item.access_count += 1
            
            # Move to end (most recently used)
            self.cache.move_to_end(key)
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None, tags: List[str] = None) -> bool:
        """Set a value in cache"""
        try:
            current_time = time.time()
            ttl = ttl or self.default_ttl
            tags = tags or []
            
            # Calculate size
            size_bytes = self._calculate_size(value)
            
            # Check if we need to make space
            if self.stats.total_size_bytes + size_bytes > self.max_size_bytes:
                self._enforce_size_limit()
            
            # Create cache item
            item = CacheItem(
                key=key,
                value=value,
                created_at=current_time,
                accessed_at=current_time,
                ttl=ttl,
                size_bytes=size_bytes,
                tags=tags
            )
            
            with self.lock:
                # Remove existing item if it exists
                if key in self.cache:
                    self._remove_item(key)
                
                # Add new item
                self.cache[key] = item
                self.stats.total_items += 1
                self.stats.total_size_bytes += size_bytes
                
                # Update tags index
                for tag in tags:
                    if tag not in self.tags_index:
                        self.tags_index[tag] = []
                    if key not in self.tags_index[tag]:
                        self.tags_index[tag].append(key)
                
                # Update average item size
                self.stats.avg_item_size = self.stats.total_size_bytes / self.stats.total_items
                self.stats.memory_usage_mb = self.stats.total_size_bytes / (1024 * 1024)
                
                self.logger.debug(f"Cached item {key} (size: {size_bytes} bytes, TTL: {ttl}s)")
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to cache item {key}: {e}")
            return False
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a value from cache"""
        try:
            current_time = time.time()
            
            with self.lock:
                if key in self.cache:
                    item = self.cache[key]
                    
                    # Check if item is expired
                    if item.ttl and (current_time - item.created_at) > item.ttl:
                        self._remove_item(key)
                        self.stats.misses += 1
                        return default
                    
                    # Update access statistics
                    self._update_access_stats(key)
                    self.stats.hits += 1
                    
                    # Update hit rate
                    total_requests = self.stats.hits + self.stats.misses
                    self.stats.hit_rate = self.stats.hits / total_requests if total_requests > 0 else 0.0
                    
                    return item.value
                else:
                    self.stats.misses += 1
                    return default
                    
        except Exception as e:
            self.logger.error(f"Failed to get cached item {key}: {e}")
            self.stats.misses += 1
            return default
    
    def delete(self, key: str) -> bool:
        """Delete a value from cache"""
        try:
            with self.lock:
                if key in self.cache:
                    self._remove_item(key)
                    self.logger.debug(f"Deleted cached item {key}")
                    return True
                return False
        except Exception as e:
            self.logger.error(f"Failed to delete cached item {key}: {e}")
            return False
    
    def delete_by_tag(self, tag: str) -> int:
        """Delete all items with a specific tag"""
        try:
            deleted_count = 0
            
            with self.lock:
                if tag in self.tags_index:
                    keys_to_delete = self.tags_index[tag].copy()
                    
                    for key in keys_to_delete:
                        if self.delete(key):
                            deleted_count += 1
                    
                    self.logger.info(f"Deleted {deleted_count} items with tag '{tag}'")
                
                return deleted_count
                
        except Exception as e:
            self.logger.error(f"Failed to delete items by tag '{tag}': {e}")
            return 0
    
    def clear(self):
        """Clear all cache items"""
        try:
            with self.lock:
                self.cache.clear()
                self.tags_index.clear()
                
                # Reset statistics
                self.stats.total_items = 0
                self.stats.total_size_bytes = 0
                self.stats.hits = 0
                self.stats.misses = 0
                self.stats.evictions = 0
                self.stats.expired_items = 0
                self.stats.hit_rate = 0.0
                self.stats.avg_item_size = 0.0
                self.stats.memory_usage_mb = 0.0
                
                self.logger.info("Cache cleared")
                
        except Exception as e:
            self.logger.error(f"Failed to clear cache: {e}")
    
    def exists(self, key: str) -> bool:
        """Check if a key exists in cache"""
        try:
            with self.lock:
                if key in self.cache:
                    item = self.cache[key]
                    
                    # Check if item is expired
                    current_time = time.time()
                    if item.ttl and (current_time - item.created_at) > item.ttl:
                        self._remove_item(key)
                        return False
                    
                    return True
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to check existence of key {key}: {e}")
            return False
    
    def get_ttl(self, key: str) -> Optional[int]:
        """Get remaining TTL for a key"""
        try:
            with self.lock:
                if key in self.cache:
                    item = self.cache[key]
                    if item.ttl:
                        current_time = time.time()
                        remaining = item.ttl - (current_time - item.created_at)
                        return max(0, int(remaining))
                return None
                
        except Exception as e:
            self.logger.error(f"Failed to get TTL for key {key}: {e}")
            return None
    
    def extend_ttl(self, key: str, additional_seconds: int) -> bool:
        """Extend TTL for a key"""
        try:
            with self.lock:
                if key in self.cache:
                    item = self.cache[key]
                    if item.ttl:
                        item.ttl += additional_seconds
                        self.logger.debug(f"Extended TTL for {key} by {additional_seconds}s")
                        return True
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to extend TTL for key {key}: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self.lock:
            return {
                'total_items': self.stats.total_items,
                'total_size_bytes': self.stats.total_size_bytes,
                'total_size_mb': round(self.stats.total_size_bytes / (1024 * 1024), 2),
                'max_size_mb': round(self.max_size_bytes / (1024 * 1024), 2),
                'hits': self.stats.hits,
                'misses': self.stats.misses,
                'evictions': self.stats.evictions,
                'expired_items': self.stats.expired_items,
                'hit_rate': round(self.stats.hit_rate * 100, 2),
                'avg_item_size': round(self.stats.avg_item_size, 2),
                'memory_usage_mb': round(self.stats.memory_usage_mb, 2),
                'tags_count': len(self.tags_index),
                'last_cleanup': self.stats.last_cleanup
            }
    
    def get_keys_by_tag(self, tag: str) -> List[str]:
        """Get all keys with a specific tag"""
        try:
            with self.lock:
                return self.tags_index.get(tag, []).copy()
        except Exception as e:
            self.logger.error(f"Failed to get keys by tag '{tag}': {e}")
            return []
    
    def get_cache_info(self, key: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a cache item"""
        try:
            with self.lock:
                if key in self.cache:
                    item = self.cache[key]
                    current_time = time.time()
                    
                    return {
                        'key': key,
                        'created_at': item.created_at,
                        'accessed_at': item.accessed_at,
                        'access_count': item.access_count,
                        'ttl': item.ttl,
                        'remaining_ttl': self.get_ttl(key),
                        'size_bytes': item.size_bytes,
                        'tags': item.tags.copy(),
                        'is_expired': item.ttl and (current_time - item.created_at) > item.ttl
                    }
                return None
                
        except Exception as e:
            self.logger.error(f"Failed to get cache info for key {key}: {e}")
            return None

def cached(ttl: Optional[int] = None, tags: List[str] = None, key_prefix: str = ""):
    """Decorator for caching function results"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get cache manager instance
            cache_manager = getattr(config, 'cache_manager', None)
            if not cache_manager:
                return await func(*args, **kwargs)
            
            # Generate cache key
            key_parts = [key_prefix, func.__name__]
            
            # Add args and kwargs to key
            if args:
                key_parts.append(str(args))
            if kwargs:
                # Sort kwargs for consistent key generation
                sorted_kwargs = sorted(kwargs.items())
                key_parts.append(str(sorted_kwargs))
            
            cache_key = hashlib.md5("|".join(key_parts).encode()).hexdigest()
            
            # Try to get from cache
            cached_result = cache_manager.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = await func(*args, **kwargs)
            cache_manager.set(cache_key, result, ttl=ttl, tags=tags)
            
            return result
        
        return wrapper
    return decorator

# Global cache manager instance
cache_manager = CacheManager(
    max_size_mb=config.CACHE_TTL if hasattr(config, 'CACHE_TTL') else 100,
    default_ttl=config.CACHE_TTL if hasattr(config, 'CACHE_TTL') else 300
)