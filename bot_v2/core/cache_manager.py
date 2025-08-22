"""
Cache management system for Yemen Net Bot v2
"""

import time
import asyncio
from typing import Any, Optional, Dict, List, Tuple
from functools import lru_cache
from .exceptions import BotError

class CacheItem:
    """Cache item with expiration"""
    
    def __init__(self, value: Any, ttl: int = 300):
        """
        Initialize cache item
        
        Args:
            value: Value to cache
            ttl: Time to live in seconds
        """
        self.value = value
        self.created_at = time.time()
        self.ttl = ttl
    
    def is_expired(self) -> bool:
        """Check if item is expired"""
        return time.time() - self.created_at > self.ttl
    
    def get_age(self) -> float:
        """Get age of item in seconds"""
        return time.time() - self.created_at
    
    def get_remaining_ttl(self) -> float:
        """Get remaining TTL in seconds"""
        return max(0, self.ttl - self.get_age())

class CacheManager:
    """Advanced cache manager with TTL and cleanup"""
    
    def __init__(self, max_size: int = 1000, cleanup_interval: int = 60):
        """
        Initialize cache manager
        
        Args:
            max_size: Maximum number of items in cache
            cleanup_interval: Cleanup interval in seconds
        """
        self.max_size = max_size
        self.cleanup_interval = cleanup_interval
        self.cache: Dict[str, CacheItem] = {}
        self.access_times: Dict[str, float] = {}
        self._cleanup_task: Optional[asyncio.Task] = None
        self._stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0,
            "expirations": 0
        }
    
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
                await asyncio.sleep(self.cleanup_interval)
                await self._cleanup_expired()
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Cache cleanup error: {e}")
    
    async def _cleanup_expired(self):
        """Remove expired items"""
        expired_keys = [
            key for key, item in self.cache.items()
            if item.is_expired()
        ]
        
        for key in expired_keys:
            self.delete(key)
            self._stats["expirations"] += 1
    
    def set(self, key: str, value: Any, ttl: int = 300) -> None:
        """
        Set cache item
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds
        """
        # Check if cache is full
        if len(self.cache) >= self.max_size:
            self._evict_oldest()
        
        self.cache[key] = CacheItem(value, ttl)
        self.access_times[key] = time.time()
        self._stats["sets"] += 1
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get cache item
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found/expired
        """
        if key not in self.cache:
            self._stats["misses"] += 1
            return None
        
        item = self.cache[key]
        if item.is_expired():
            self.delete(key)
            self._stats["misses"] += 1
            return None
        
        # Update access time
        self.access_times[key] = time.time()
        self._stats["hits"] += 1
        return item.value
    
    def delete(self, key: str) -> bool:
        """
        Delete cache item
        
        Args:
            key: Cache key
            
        Returns:
            True if deleted, False if not found
        """
        if key in self.cache:
            del self.cache[key]
            del self.access_times[key]
            self._stats["deletes"] += 1
            return True
        return False
    
    def exists(self, key: str) -> bool:
        """Check if key exists and is not expired"""
        if key not in self.cache:
            return False
        
        item = self.cache[key]
        if item.is_expired():
            self.delete(key)
            return False
        
        return True
    
    def get_ttl(self, key: str) -> float:
        """Get remaining TTL for key"""
        if key not in self.cache:
            return 0.0
        
        item = self.cache[key]
        if item.is_expired():
            self.delete(key)
            return 0.0
        
        return item.get_remaining_ttl()
    
    def clear(self) -> None:
        """Clear all cache items"""
        self.cache.clear()
        self.access_times.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return {
            **self._stats,
            "size": len(self.cache),
            "max_size": self.max_size,
            "hit_rate": self._stats["hits"] / max(1, self._stats["hits"] + self._stats["misses"])
        }
    
    def _evict_oldest(self) -> None:
        """Evict oldest accessed item"""
        if not self.access_times:
            return
        
        oldest_key = min(self.access_times.keys(), key=lambda k: self.access_times[k])
        self.delete(oldest_key)

class FunctionCache:
    """Function result caching with TTL"""
    
    def __init__(self, ttl: int = 300):
        """
        Initialize function cache
        
        Args:
            ttl: Time to live in seconds
        """
        self.ttl = ttl
        self.cache: Dict[str, CacheItem] = {}
    
    def __call__(self, func):
        """Cache decorator"""
        async def wrapper(*args, **kwargs):
            # Create cache key from function name and arguments
            cache_key = f"{func.__name__}:{hash(str(args) + str(kwargs))}"
            
            # Check cache
            if cache_key in self.cache:
                item = self.cache[cache_key]
                if not item.is_expired():
                    return item.value
            
            # Execute function and cache result
            result = await func(*args, **kwargs)
            self.cache[cache_key] = CacheItem(result, self.ttl)
            
            return result
        
        return wrapper

# Global cache manager instance
cache_manager = CacheManager()

# Function cache decorator
def cached(ttl: int = 300):
    """Cache decorator for functions"""
    return FunctionCache(ttl)

# LRU cache decorator for expensive operations
@lru_cache(maxsize=128)
def expensive_operation_cache(key: str) -> Any:
    """Example of LRU cache usage"""
    # This would be replaced with actual expensive operations
    return f"cached_result_for_{key}"