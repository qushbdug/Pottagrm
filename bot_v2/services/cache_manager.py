"""
Cache manager for improving bot performance
"""

import time
import asyncio
import logging
import threading
from typing import Dict, Any, Optional, Union, Callable
from dataclasses import dataclass, field
from collections import OrderedDict
import json
import hashlib
import pickle

from ..core.exceptions import BotException

logger = logging.getLogger(__name__)

@dataclass
class CacheEntry:
    """Cache entry with metadata"""
    value: Any
    created_at: float
    expires_at: Optional[float]
    access_count: int = 0
    last_accessed: float = field(default_factory=time.time)
    size_bytes: int = 0

class CacheManager:
    """Advanced cache manager with multiple strategies"""
    
    def __init__(self, max_size_mb: int = 100, default_ttl: int = 300):
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.default_ttl = default_ttl
        self.current_size_bytes = 0
        
        # Cache storage
        self.memory_cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self.disk_cache_path = "cache/"
        
        # Statistics
        self.stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'size_evictions': 0,
            'expiry_evictions': 0
        }
        
        # Thread safety
        self.lock = threading.RLock()
        
        # Background cleanup
        self._cleanup_task = None
        self._start_cleanup_task()
        
        # Initialize disk cache
        self._init_disk_cache()
    
    def _init_disk_cache(self):
        """Initialize disk cache directory"""
        try:
            import os
            os.makedirs(self.disk_cache_path, exist_ok=True)
            logger.info(f"Disk cache initialized at {self.disk_cache_path}")
        except Exception as e:
            logger.warning(f"Failed to initialize disk cache: {e}")
    
    def _start_cleanup_task(self):
        """Start background cleanup task"""
        async def cleanup_loop():
            while True:
                try:
                    await asyncio.sleep(60)  # Clean every minute
                    self._cleanup_expired()
                    self._cleanup_size()
                except Exception as e:
                    logger.error(f"Cache cleanup error: {e}")
        
        try:
            loop = asyncio.get_event_loop()
            self._cleanup_task = loop.create_task(cleanup_loop())
        except RuntimeError:
            # No event loop, skip cleanup task
            pass
    
    def _generate_key(self, *args, **kwargs) -> str:
        """Generate cache key from arguments"""
        # Create a string representation
        key_data = str(args) + str(sorted(kwargs.items()))
        
        # Generate hash
        key_hash = hashlib.md5(key_data.encode()).hexdigest()
        return f"cache_{key_hash}"
    
    def _calculate_size(self, value: Any) -> int:
        """Calculate approximate size of value in bytes"""
        try:
            # Try to serialize to get size
            serialized = pickle.dumps(value)
            return len(serialized)
        except Exception:
            # Fallback to string representation
            return len(str(value).encode())
    
    def _can_fit(self, size_bytes: int) -> bool:
        """Check if item can fit in cache"""
        return self.current_size_bytes + size_bytes <= self.max_size_bytes
    
    def _evict_lru(self, required_size: int):
        """Evict least recently used items to make space"""
        with self.lock:
            while self.current_size_bytes + required_size > self.max_size_bytes and self.memory_cache:
                # Remove oldest item
                key, entry = self.memory_cache.popitem(last=False)
                self.current_size_bytes -= entry.size_bytes
                self.stats['size_evictions'] += 1
                logger.debug(f"Evicted cache entry {key} due to size constraints")
    
    def _cleanup_expired(self):
        """Remove expired cache entries"""
        current_time = time.time()
        expired_keys = []
        
        with self.lock:
            for key, entry in self.memory_cache.items():
                if entry.expires_at and current_time > entry.expires_at:
                    expired_keys.append(key)
            
            for key in expired_keys:
                entry = self.memory_cache.pop(key)
                self.current_size_bytes -= entry.size_bytes
                self.stats['expiry_evictions'] += 1
            
            if expired_keys:
                logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")
    
    def _cleanup_size(self):
        """Clean up cache if it exceeds size limit"""
        if self.current_size_bytes > self.max_size_bytes:
            # Remove oldest 20% of entries
            target_size = int(self.max_size_bytes * 0.8)
            removed_count = 0
            
            with self.lock:
                while self.current_size_bytes > target_size and self.memory_cache:
                    key, entry = self.memory_cache.popitem(last=False)
                    self.current_size_bytes -= entry.size_bytes
                    removed_count += 1
                    self.stats['size_evictions'] += 1
                
                if removed_count > 0:
                    logger.info(f"Cleaned up {removed_count} cache entries due to size limit")
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get value from cache"""
        with self.lock:
            if key in self.memory_cache:
                entry = self.memory_cache[key]
                
                # Check if expired
                if entry.expires_at and time.time() > entry.expires_at:
                    del self.memory_cache[key]
                    self.current_size_bytes -= entry.size_bytes
                    self.stats['misses'] += 1
                    return default
                
                # Update access statistics
                entry.access_count += 1
                entry.last_accessed = time.time()
                
                # Move to end (most recently used)
                self.memory_cache.move_to_end(key)
                
                self.stats['hits'] += 1
                return entry.value
            else:
                self.stats['misses'] += 1
                return default
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache"""
        try:
            size_bytes = self._calculate_size(value)
            ttl = ttl or self.default_ttl
            
            with self.lock:
                # Check if we can fit this item
                if not self._can_fit(size_bytes):
                    self._evict_lru(size_bytes)
                
                # Create cache entry
                entry = CacheEntry(
                    value=value,
                    created_at=time.time(),
                    expires_at=time.time() + ttl if ttl > 0 else None,
                    size_bytes=size_bytes
                )
                
                # Remove existing entry if it exists
                if key in self.memory_cache:
                    old_entry = self.memory_cache[key]
                    self.current_size_bytes -= old_entry.size_bytes
                
                # Add new entry
                self.memory_cache[key] = entry
                self.current_size_bytes += size_bytes
                
                # Move to end (most recently used)
                self.memory_cache.move_to_end(key)
                
                logger.debug(f"Cached item {key} (size: {size_bytes} bytes, TTL: {ttl}s)")
                return True
                
        except Exception as e:
            logger.error(f"Failed to cache item {key}: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """Delete item from cache"""
        with self.lock:
            if key in self.memory_cache:
                entry = self.memory_cache.pop(key)
                self.current_size_bytes -= entry.size_bytes
                logger.debug(f"Deleted cache entry {key}")
                return True
            return False
    
    def clear(self):
        """Clear all cache entries"""
        with self.lock:
            self.memory_cache.clear()
            self.current_size_bytes = 0
            logger.info("Cache cleared")
    
    def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        with self.lock:
            if key in self.memory_cache:
                entry = self.memory_cache[key]
                # Check if expired
                if entry.expires_at and time.time() > entry.expires_at:
                    del self.memory_cache[key]
                    self.current_size_bytes -= entry.size_bytes
                    return False
                return True
            return False
    
    def get_or_set(self, key: str, default_func: Callable, ttl: Optional[int] = None) -> Any:
        """Get value from cache or set default if not exists"""
        value = self.get(key)
        if value is None:
            value = default_func()
            self.set(key, value, ttl)
        return value
    
    def mget(self, keys: list) -> Dict[str, Any]:
        """Get multiple values from cache"""
        result = {}
        for key in keys:
            value = self.get(key)
            if value is not None:
                result[key] = value
        return result
    
    def mset(self, data: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """Set multiple values in cache"""
        try:
            for key, value in data.items():
                self.set(key, value, ttl)
            return True
        except Exception as e:
            logger.error(f"Failed to set multiple cache items: {e}")
            return False
    
    def increment(self, key: str, amount: int = 1) -> Optional[int]:
        """Increment numeric value in cache"""
        try:
            current_value = self.get(key, 0)
            if isinstance(current_value, (int, float)):
                new_value = current_value + amount
                self.set(key, new_value)
                return new_value
            return None
        except Exception as e:
            logger.error(f"Failed to increment cache key {key}: {e}")
            return None
    
    def decrement(self, key: str, amount: int = 1) -> Optional[int]:
        """Decrement numeric value in cache"""
        return self.increment(key, -amount)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self.lock:
            hit_rate = 0
            if self.stats['hits'] + self.stats['misses'] > 0:
                hit_rate = self.stats['hits'] / (self.stats['hits'] + self.stats['misses'])
            
            return {
                **self.stats,
                'hit_rate': round(hit_rate, 3),
                'current_size_bytes': self.current_size_bytes,
                'current_size_mb': round(self.current_size_bytes / (1024 * 1024), 2),
                'max_size_mb': round(self.max_size_bytes / (1024 * 1024), 2),
                'entries_count': len(self.memory_cache),
                'utilization_percent': round((self.current_size_bytes / self.max_size_bytes) * 100, 2)
            }
    
    def get_keys(self, pattern: str = "*") -> list:
        """Get cache keys matching pattern"""
        with self.lock:
            if pattern == "*":
                return list(self.memory_cache.keys())
            
            # Simple pattern matching
            import fnmatch
            return [key for key in self.memory_cache.keys() if fnmatch.fnmatch(key, pattern)]
    
    def persist_to_disk(self, filename: str = None) -> bool:
        """Persist cache to disk"""
        try:
            if not filename:
                filename = f"cache_backup_{int(time.time())}.json"
            
            filepath = f"{self.disk_cache_path}{filename}"
            
            with self.lock:
                # Prepare data for serialization
                cache_data = {}
                for key, entry in self.memory_cache.items():
                    # Skip expired entries
                    if entry.expires_at and time.time() > entry.expires_at:
                        continue
                    
                    try:
                        # Try to serialize value
                        serialized_value = pickle.dumps(entry.value)
                        cache_data[key] = {
                            'value': serialized_value.hex(),
                            'created_at': entry.created_at,
                            'expires_at': entry.expires_at,
                            'access_count': entry.access_count,
                            'size_bytes': entry.size_bytes
                        }
                    except Exception as e:
                        logger.warning(f"Failed to serialize cache value for key {key}: {e}")
                        continue
            
            # Save to file
            with open(filepath, 'w') as f:
                json.dump(cache_data, f, indent=2)
            
            logger.info(f"Cache persisted to {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to persist cache: {e}")
            return False
    
    def load_from_disk(self, filename: str) -> bool:
        """Load cache from disk"""
        try:
            filepath = f"{self.disk_cache_path}{filename}"
            
            with open(filepath, 'r') as f:
                cache_data = json.load(f)
            
            with self.lock:
                loaded_count = 0
                for key, data in cache_data.items():
                    try:
                        # Deserialize value
                        serialized_value = bytes.fromhex(data['value'])
                        value = pickle.loads(serialized_value)
                        
                        # Create cache entry
                        entry = CacheEntry(
                            value=value,
                            created_at=data['created_at'],
                            expires_at=data['expires_at'],
                            access_count=data['access_count'],
                            size_bytes=data['size_bytes']
                        )
                        
                        # Check if expired
                        if entry.expires_at and time.time() > entry.expires_at:
                            continue
                        
                        # Add to cache
                        self.memory_cache[key] = entry
                        self.current_size_bytes += entry.size_bytes
                        loaded_count += 1
                        
                    except Exception as e:
                        logger.warning(f"Failed to deserialize cache value for key {key}: {e}")
                        continue
            
            logger.info(f"Loaded {loaded_count} cache entries from {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load cache from disk: {e}")
            return False
    
    def shutdown(self):
        """Shutdown cache manager"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
        
        # Persist cache before shutdown
        self.persist_to_disk("shutdown_cache.json")
        
        # Clear memory cache
        self.clear()
        
        logger.info("Cache manager shutdown complete")

# Global cache manager instance
cache_manager = CacheManager()

# Decorator for caching function results
def cached(ttl: Optional[int] = None, key_prefix: str = ""):
    """Decorator to cache function results"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Generate cache key
            cache_key = f"{key_prefix}{func.__name__}_{hash(str(args) + str(sorted(kwargs.items()))}"
            
            # Try to get from cache
            cached_result = cache_manager.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            cache_manager.set(cache_key, result, ttl)
            
            return result
        
        return wrapper
    return decorator

# Async version of cached decorator
def async_cached(ttl: Optional[int] = None, key_prefix: str = ""):
    """Async decorator to cache function results"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Generate cache key
            cache_key = f"{key_prefix}{func.__name__}_{hash(str(args) + str(sorted(kwargs.items()))}"
            
            # Try to get from cache
            cached_result = cache_manager.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = await func(*args, **kwargs)
            cache_manager.set(cache_key, result, ttl)
            
            return result
        
        return wrapper
    return decorator