"""
Advanced Cache Manager for Yemen Net Bot
Provides in-memory caching with TTL, size limits, and statistics
"""

import asyncio
import time
import threading
import pickle
import hashlib
import logging
from typing import Any, Optional, Dict, List, Tuple, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from functools import wraps
from collections import OrderedDict

from core.exceptions import CacheError
from core.logger import get_performance_logger


@dataclass
class CacheItem:
    """Cache item with metadata"""
    key: str
    value: Any
    created_at: float
    expires_at: Optional[float]
    access_count: int = 0
    last_accessed: float = 0
    size_bytes: int = 0


@dataclass
class CacheStats:
    """Cache statistics"""
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    total_size_bytes: int = 0
    item_count: int = 0
    hit_rate: float = 0.0


class CacheManager:
    """Advanced in-memory cache with TTL and LRU eviction"""
    
    def __init__(self, 
                 max_size: int = 1000,
                 default_ttl: int = 300,
                 max_memory_mb: int = 100,
                 cleanup_interval: int = 60):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        self.cleanup_interval = cleanup_interval
        
        self.cache: OrderedDict[str, CacheItem] = OrderedDict()
        self.stats = CacheStats()
        self.logger = logging.getLogger(__name__)
        self.perf_logger = get_performance_logger()
        self._lock = threading.RLock()
        
        # Cache key prefixes for different data types
        self.prefixes = {
            'user': 'user:',
            'network': 'network:',
            'card': 'card:',
            'transaction': 'transaction:',
            'query': 'query:',
            'api': 'api:',
            'temp': 'temp:'
        }
        
        # Start cleanup task
        self._cleanup_task = asyncio.create_task(self._periodic_cleanup())
    
    def _generate_key(self, prefix: str, identifier: str, suffix: str = "") -> str:
        """Generate a standardized cache key"""
        full_key = f"{prefix}{identifier}{suffix}"
        return hashlib.md5(full_key.encode()).hexdigest()[:16]
    
    def _calculate_size(self, value: Any) -> int:
        """Calculate approximate size of value in bytes"""
        try:
            return len(pickle.dumps(value))
        except Exception:
            # Fallback for non-serializable objects
            return len(str(value).encode('utf-8'))
    
    def _is_expired(self, item: CacheItem) -> bool:
        """Check if cache item is expired"""
        if item.expires_at is None:
            return False
        return time.time() > item.expires_at
    
    def _evict_lru(self):
        """Evict least recently used items"""
        while len(self.cache) >= self.max_size or self.stats.total_size_bytes > self.max_memory_bytes:
            if not self.cache:
                break
            
            # Remove least recently used item
            key, item = self.cache.popitem(last=False)
            self.stats.total_size_bytes -= item.size_bytes
            self.stats.item_count -= 1
            self.stats.evictions += 1
            
            self.logger.debug(f"Evicted cache item: {key}")
    
    def _update_stats(self):
        """Update cache statistics"""
        total_requests = self.stats.hits + self.stats.misses
        self.stats.hit_rate = self.stats.hits / total_requests if total_requests > 0 else 0.0
    
    async def get(self, key: str, default: Any = None) -> Any:
        """Get value from cache"""
        with self._lock:
            if key not in self.cache:
                self.stats.misses += 1
                self._update_stats()
                return default
            
            item = self.cache[key]
            
            # Check if expired
            if self._is_expired(item):
                del self.cache[key]
                self.stats.total_size_bytes -= item.size_bytes
                self.stats.item_count -= 1
                self.stats.misses += 1
                self._update_stats()
                return default
            
            # Update access info
            item.access_count += 1
            item.last_accessed = time.time()
            
            # Move to end (most recently used)
            self.cache.move_to_end(key)
            
            self.stats.hits += 1
            self._update_stats()
            
            return item.value
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache"""
        try:
            with self._lock:
                current_time = time.time()
                ttl = ttl or self.default_ttl
                expires_at = current_time + ttl if ttl > 0 else None
                size_bytes = self._calculate_size(value)
                
                # Check if updating existing item
                if key in self.cache:
                    old_item = self.cache[key]
                    self.stats.total_size_bytes -= old_item.size_bytes
                else:
                    self.stats.item_count += 1
                
                # Create new cache item
                item = CacheItem(
                    key=key,
                    value=value,
                    created_at=current_time,
                    expires_at=expires_at,
                    access_count=1,
                    last_accessed=current_time,
                    size_bytes=size_bytes
                )
                
                self.cache[key] = item
                self.stats.total_size_bytes += size_bytes
                
                # Move to end (most recently used)
                self.cache.move_to_end(key)
                
                # Evict if necessary
                self._evict_lru()
                
                return True
                
        except Exception as e:
            self.logger.error(f"Error setting cache key {key}: {e}")
            raise CacheError(f"Failed to set cache key: {e}", cache_key=key)
    
    async def delete(self, key: str) -> bool:
        """Delete value from cache"""
        with self._lock:
            if key in self.cache:
                item = self.cache.pop(key)
                self.stats.total_size_bytes -= item.size_bytes
                self.stats.item_count -= 1
                return True
            return False
    
    async def clear(self, prefix: Optional[str] = None):
        """Clear cache (optionally by prefix)"""
        with self._lock:
            if prefix:
                # Clear only keys with specific prefix
                keys_to_delete = [k for k in self.cache.keys() if k.startswith(prefix)]
                for key in keys_to_delete:
                    item = self.cache.pop(key)
                    self.stats.total_size_bytes -= item.size_bytes
                    self.stats.item_count -= 1
                self.logger.info(f"Cleared {len(keys_to_delete)} cache items with prefix {prefix}")
            else:
                # Clear all
                self.cache.clear()
                self.stats.total_size_bytes = 0
                self.stats.item_count = 0
                self.logger.info("Cleared all cache items")
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        with self._lock:
            if key not in self.cache:
                return False
            
            item = self.cache[key]
            if self._is_expired(item):
                del self.cache[key]
                self.stats.total_size_bytes -= item.size_bytes
                self.stats.item_count -= 1
                return False
            
            return True
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self._lock:
            return {
                'hits': self.stats.hits,
                'misses': self.stats.misses,
                'hit_rate': self.stats.hit_rate,
                'evictions': self.stats.evictions,
                'item_count': self.stats.item_count,
                'total_size_bytes': self.stats.total_size_bytes,
                'total_size_mb': round(self.stats.total_size_bytes / (1024 * 1024), 2),
                'max_size': self.max_size,
                'max_memory_mb': self.max_memory_bytes // (1024 * 1024),
                'utilization': {
                    'count_percent': (self.stats.item_count / self.max_size) * 100,
                    'memory_percent': (self.stats.total_size_bytes / self.max_memory_bytes) * 100
                }
            }
    
    async def get_keys(self, prefix: Optional[str] = None) -> List[str]:
        """Get all cache keys (optionally filtered by prefix)"""
        with self._lock:
            if prefix:
                return [k for k in self.cache.keys() if k.startswith(prefix)]
            return list(self.cache.keys())
    
    async def get_item_info(self, key: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a cache item"""
        with self._lock:
            if key not in self.cache:
                return None
            
            item = self.cache[key]
            current_time = time.time()
            
            return {
                'key': item.key,
                'created_at': datetime.fromtimestamp(item.created_at).isoformat(),
                'expires_at': datetime.fromtimestamp(item.expires_at).isoformat() if item.expires_at else None,
                'last_accessed': datetime.fromtimestamp(item.last_accessed).isoformat(),
                'access_count': item.access_count,
                'size_bytes': item.size_bytes,
                'ttl_remaining': int(item.expires_at - current_time) if item.expires_at else None,
                'is_expired': self._is_expired(item)
            }
    
    # Convenience methods for different data types
    async def cache_user(self, user_id: int, user_data: Dict[str, Any], ttl: int = 300) -> bool:
        """Cache user data"""
        key = self._generate_key(self.prefixes['user'], str(user_id))
        return await self.set(key, user_data, ttl)
    
    async def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get cached user data"""
        key = self._generate_key(self.prefixes['user'], str(user_id))
        return await self.get(key)
    
    async def cache_network(self, network_id: int, network_data: Dict[str, Any], ttl: int = 600) -> bool:
        """Cache network data"""
        key = self._generate_key(self.prefixes['network'], str(network_id))
        return await self.set(key, network_data, ttl)
    
    async def get_network(self, network_id: int) -> Optional[Dict[str, Any]]:
        """Get cached network data"""
        key = self._generate_key(self.prefixes['network'], str(network_id))
        return await self.get(key)
    
    async def cache_query_result(self, query: str, params: tuple, result: Any, ttl: int = 180) -> bool:
        """Cache database query result"""
        key_data = f"{query}:{str(params)}"
        key = self._generate_key(self.prefixes['query'], key_data)
        return await self.set(key, result, ttl)
    
    async def get_query_result(self, query: str, params: tuple) -> Any:
        """Get cached database query result"""
        key_data = f"{query}:{str(params)}"
        key = self._generate_key(self.prefixes['query'], key_data)
        return await self.get(key)
    
    async def invalidate_user_cache(self, user_id: int):
        """Invalidate all cache entries for a user"""
        prefix = self._generate_key(self.prefixes['user'], str(user_id))[:8]
        await self.clear(prefix)
    
    async def invalidate_network_cache(self, network_id: int):
        """Invalidate all cache entries for a network"""
        prefix = self._generate_key(self.prefixes['network'], str(network_id))[:8]
        await self.clear(prefix)
    
    async def _periodic_cleanup(self):
        """Periodic cleanup of expired items"""
        while True:
            try:
                await asyncio.sleep(self.cleanup_interval)
                
                with self._lock:
                    current_time = time.time()
                    expired_keys = []
                    
                    for key, item in self.cache.items():
                        if self._is_expired(item):
                            expired_keys.append(key)
                    
                    for key in expired_keys:
                        item = self.cache.pop(key)
                        self.stats.total_size_bytes -= item.size_bytes
                        self.stats.item_count -= 1
                    
                    if expired_keys:
                        self.logger.info(f"Cleaned up {len(expired_keys)} expired cache items")
                        
                        # Log performance stats
                        self.perf_logger.info(
                            f"Cache cleanup completed",
                            extra={
                                'expired_items': len(expired_keys),
                                'total_items': self.stats.item_count,
                                'cache_size_mb': self.stats.total_size_bytes / (1024 * 1024),
                                'hit_rate': self.stats.hit_rate
                            }
                        )
                        
            except Exception as e:
                self.logger.error(f"Error in cache cleanup: {e}")
    
    async def cleanup(self):
        """Manual cleanup and shutdown"""
        try:
            if hasattr(self, '_cleanup_task'):
                self._cleanup_task.cancel()
            
            await self.clear()
            self.logger.info("✅ Cache manager cleaned up")
            
        except Exception as e:
            self.logger.error(f"❌ Error during cache cleanup: {e}")


def cache_decorator(ttl: int = 300, key_prefix: str = "func"):
    """Decorator for caching function results"""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Create cache key from function name and arguments
            cache_key = f"{key_prefix}:{func.__name__}:{hash(str(args) + str(sorted(kwargs.items())))}"
            
            # Try to get from cache (this would need access to cache manager instance)
            # For now, just call the function
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


class DistributedCache:
    """Extended cache with potential for distributed caching (Redis-like interface)"""
    
    def __init__(self, cache_manager: CacheManager):
        self.cache_manager = cache_manager
        self.logger = logging.getLogger(__name__)
    
    async def hset(self, name: str, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set field in hash"""
        hash_key = f"hash:{name}:{key}"
        return await self.cache_manager.set(hash_key, value, ttl)
    
    async def hget(self, name: str, key: str) -> Any:
        """Get field from hash"""
        hash_key = f"hash:{name}:{key}"
        return await self.cache_manager.get(hash_key)
    
    async def hdel(self, name: str, key: str) -> bool:
        """Delete field from hash"""
        hash_key = f"hash:{name}:{key}"
        return await self.cache_manager.delete(hash_key)
    
    async def hgetall(self, name: str) -> Dict[str, Any]:
        """Get all fields from hash"""
        prefix = f"hash:{name}:"
        keys = await self.cache_manager.get_keys(prefix)
        result = {}
        
        for key in keys:
            field_name = key[len(prefix):]
            value = await self.cache_manager.get(key)
            if value is not None:
                result[field_name] = value
        
        return result
    
    async def expire(self, key: str, ttl: int) -> bool:
        """Set TTL for existing key"""
        value = await self.cache_manager.get(key)
        if value is not None:
            return await self.cache_manager.set(key, value, ttl)
        return False