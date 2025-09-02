#!/usr/bin/env python3
"""
Cache Manager - مدير التخزين المؤقت
يحسن الأداء عبر تخزين البيانات المستخدمة بكثرة مؤقتاً
"""

import logging
import time
import threading
import json
from typing import Any, Dict, Optional, Callable, List
from datetime import datetime, timedelta
from collections import OrderedDict

logger = logging.getLogger(__name__)

class CacheManager:
    """مدير التخزين المؤقت مع TTL وLRU"""
    
    def __init__(self, max_size: int = 1000, default_ttl: int = 300):
        self.max_size = max_size
        self.default_ttl = default_ttl  # 5 minutes default
        self._cache = OrderedDict()
        self._lock = threading.RLock()
        self._stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'expired': 0
        }
    
    def get(self, key: str) -> Optional[Any]:
        """الحصول على قيمة من التخزين المؤقت"""
        with self._lock:
            if key not in self._cache:
                self._stats['misses'] += 1
                return None
            
            entry = self._cache[key]
            
            # التحقق من انتهاء الصلاحية
            if entry['expires_at'] < time.time():
                del self._cache[key]
                self._stats['expired'] += 1
                self._stats['misses'] += 1
                return None
            
            # نقل إلى النهاية (LRU)
            self._cache.move_to_end(key)
            self._stats['hits'] += 1
            return entry['value']
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """تخزين قيمة في التخزين المؤقت"""
        if ttl is None:
            ttl = self.default_ttl
        
        with self._lock:
            expires_at = time.time() + ttl
            
            entry = {
                'value': value,
                'expires_at': expires_at,
                'created_at': time.time()
            }
            
            # إزالة القيمة القديمة إن وجدت
            if key in self._cache:
                del self._cache[key]
            
            self._cache[key] = entry
            self._cache.move_to_end(key)
            
            # تنظيف التخزين المؤقت إذا تجاوز الحد الأقصى
            self._evict_if_needed()
    
    def delete(self, key: str) -> bool:
        """حذف قيمة من التخزين المؤقت"""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False
    
    def clear(self) -> None:
        """مسح جميع القيم من التخزين المؤقت"""
        with self._lock:
            self._cache.clear()
    
    def _evict_if_needed(self) -> None:
        """إزالة القيم الزائدة باستخدام LRU"""
        while len(self._cache) > self.max_size:
            # إزالة أقدم عنصر (LRU)
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]
            self._stats['evictions'] += 1
    
    def cleanup_expired(self) -> int:
        """تنظيف القيم منتهية الصلاحية"""
        current_time = time.time()
        expired_keys = []
        
        with self._lock:
            for key, entry in self._cache.items():
                if entry['expires_at'] < current_time:
                    expired_keys.append(key)
            
            for key in expired_keys:
                del self._cache[key]
                self._stats['expired'] += 1
        
        return len(expired_keys)
    
    def get_stats(self) -> Dict[str, Any]:
        """الحصول على إحصائيات التخزين المؤقت"""
        with self._lock:
            total_requests = self._stats['hits'] + self._stats['misses']
            hit_rate = (self._stats['hits'] / total_requests * 100) if total_requests > 0 else 0
            
            return {
                'size': len(self._cache),
                'max_size': self.max_size,
                'hit_rate': round(hit_rate, 2),
                'hits': self._stats['hits'],
                'misses': self._stats['misses'],
                'evictions': self._stats['evictions'],
                'expired': self._stats['expired'],
                'total_requests': total_requests
            }
    
    def cached_function(self, ttl: Optional[int] = None, key_func: Optional[Callable] = None):
        """ديكوريتر للتخزين المؤقت للدوال"""
        def decorator(func):
            def wrapper(*args, **kwargs):
                # إنشاء مفتاح التخزين المؤقت
                if key_func:
                    cache_key = key_func(*args, **kwargs)
                else:
                    cache_key = f"{func.__name__}:{hash(str(args) + str(sorted(kwargs.items())))}"
                
                # محاولة الحصول على النتيجة من التخزين المؤقت
                cached_result = self.get(cache_key)
                if cached_result is not None:
                    return cached_result
                
                # تنفيذ الدالة وتخزين النتيجة
                result = func(*args, **kwargs)
                self.set(cache_key, result, ttl)
                return result
            
            return wrapper
        return decorator

class SmartCache:
    """تخزين مؤقت ذكي مع فئات مختلفة"""
    
    def __init__(self):
        # تخزين مؤقت للمستخدمين (TTL: 10 دقائق)
        self.users_cache = CacheManager(max_size=500, default_ttl=600)
        
        # تخزين مؤقت للشبكات (TTL: 30 دقيقة)
        self.networks_cache = CacheManager(max_size=200, default_ttl=1800)
        
        # تخزين مؤقت للإحصائيات (TTL: 5 دقائق)
        self.stats_cache = CacheManager(max_size=100, default_ttl=300)
        
        # تخزين مؤقت للبطاقات المتاحة (TTL: 2 دقيقة)
        self.cards_cache = CacheManager(max_size=300, default_ttl=120)
        
        # بدء تنظيف دوري
        self._start_cleanup_thread()
    
    def _start_cleanup_thread(self):
        """بدء thread للتنظيف الدوري"""
        def cleanup_loop():
            while True:
                try:
                    time.sleep(60)  # كل دقيقة
                    total_cleaned = 0
                    total_cleaned += self.users_cache.cleanup_expired()
                    total_cleaned += self.networks_cache.cleanup_expired()
                    total_cleaned += self.stats_cache.cleanup_expired()
                    total_cleaned += self.cards_cache.cleanup_expired()
                    
                    if total_cleaned > 0:
                        logger.debug(f"Cleaned {total_cleaned} expired cache entries")
                        
                except Exception as e:
                    logger.error(f"Cache cleanup error: {e}")
        
        cleanup_thread = threading.Thread(target=cleanup_loop, daemon=True)
        cleanup_thread.start()
    
    def get_user(self, telegram_id: int) -> Optional[Dict]:
        """الحصول على مستخدم مع تخزين مؤقت"""
        return self.users_cache.get(f"user:{telegram_id}")
    
    def set_user(self, telegram_id: int, user_data: Dict) -> None:
        """تخزين بيانات المستخدم مؤقتاً"""
        self.users_cache.set(f"user:{telegram_id}", user_data)
    
    def invalidate_user(self, telegram_id: int) -> None:
        """إبطال تخزين المستخدم المؤقت"""
        self.users_cache.delete(f"user:{telegram_id}")
    
    def get_network(self, network_id: int) -> Optional[Dict]:
        """الحصول على شبكة مع تخزين مؤقت"""
        return self.networks_cache.get(f"network:{network_id}")
    
    def set_network(self, network_id: int, network_data: Dict) -> None:
        """تخزين بيانات الشبكة مؤقتاً"""
        self.networks_cache.set(f"network:{network_id}", network_data)
    
    def get_available_cards(self, network_id: int) -> Optional[List[Dict]]:
        """الحصول على البطاقات المتاحة مع تخزين مؤقت"""
        return self.cards_cache.get(f"cards:{network_id}")
    
    def set_available_cards(self, network_id: int, cards: List[Dict]) -> None:
        """تخزين البطاقات المتاحة مؤقتاً"""
        self.cards_cache.set(f"cards:{network_id}", cards)
    
    def invalidate_cards(self, network_id: int) -> None:
        """إبطال تخزين البطاقات المؤقت"""
        self.cards_cache.delete(f"cards:{network_id}")
    
    def get_stats(self, stats_key: str) -> Optional[Dict]:
        """الحصول على إحصائيات مع تخزين مؤقت"""
        return self.stats_cache.get(f"stats:{stats_key}")
    
    def set_stats(self, stats_key: str, stats_data: Dict) -> None:
        """تخزين الإحصائيات مؤقتاً"""
        self.stats_cache.set(f"stats:{stats_key}", stats_data)
    
    def get_all_stats(self) -> Dict[str, Any]:
        """الحصول على إحصائيات جميع أنواع التخزين المؤقت"""
        return {
            'users_cache': self.users_cache.get_stats(),
            'networks_cache': self.networks_cache.get_stats(),
            'stats_cache': self.stats_cache.get_stats(),
            'cards_cache': self.cards_cache.get_stats()
        }
    
    def clear_all(self) -> None:
        """مسح جميع أنواع التخزين المؤقت"""
        self.users_cache.clear()
        self.networks_cache.clear()
        self.stats_cache.clear()
        self.cards_cache.clear()

class CachedDatabaseOperations:
    """عمليات قاعدة البيانات مع تخزين مؤقت"""
    
    def __init__(self, cache: SmartCache):
        self.cache = cache
    
    def get_user_by_telegram_id(self, telegram_id: int) -> Optional[Dict]:
        """الحصول على مستخدم مع تخزين مؤقت"""
        # محاولة الحصول من التخزين المؤقت
        cached_user = self.cache.get_user(telegram_id)
        if cached_user:
            return cached_user
        
        # الحصول من قاعدة البيانات
        from bot_modules.query_optimizer import query_optimizer
        user = query_optimizer.get_user_by_telegram_id(telegram_id)
        
        if user:
            # تخزين في التخزين المؤقت
            self.cache.set_user(telegram_id, user)
        
        return user
    
    def get_network_with_cards(self, network_id: int) -> Optional[Dict]:
        """الحصول على شبكة مع بطاقاتها المتاحة"""
        # محاولة الحصول من التخزين المؤقت
        cached_network = self.cache.get_network(network_id)
        cached_cards = self.cache.get_available_cards(network_id)
        
        if cached_network and cached_cards is not None:
            cached_network['available_cards'] = cached_cards
            return cached_network
        
        # الحصول من قاعدة البيانات
        from bot_modules.database import get_db_connection
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            # الحصول على بيانات الشبكة
            cursor.execute('''
                SELECT id, supplier_id, name, provider, city, location, 
                       is_active, is_approved, created_at
                FROM networks 
                WHERE id = ?
            ''', (network_id,))
            
            network = cursor.fetchone()
            if not network:
                return None
            
            network_dict = dict(network)
            
            # الحصول على البطاقات المتاحة
            cursor.execute('''
                SELECT id, card_code, card_value, created_at
                FROM network_cards 
                WHERE network_id = ? AND is_sold = 0
                ORDER BY card_value
            ''', (network_id,))
            
            cards = [dict(card) for card in cursor.fetchall()]
            network_dict['available_cards'] = cards
            
            # تخزين في التخزين المؤقت
            self.cache.set_network(network_id, network_dict)
            self.cache.set_available_cards(network_id, cards)
            
            return network_dict
            
        finally:
            conn.close()
    
    def update_user_balance(self, telegram_id: int, new_balance: float) -> None:
        """تحديث رصيد المستخدم وإبطال التخزين المؤقت"""
        # إبطال التخزين المؤقت للمستخدم
        self.cache.invalidate_user(telegram_id)
        
        # تحديث قاعدة البيانات
        from bot_modules.database import get_db_connection
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                UPDATE users 
                SET balance = ?, last_activity = ?
                WHERE telegram_id = ?
            ''', (new_balance, datetime.now(), telegram_id))
            
            conn.commit()
            
        finally:
            conn.close()
    
    def mark_card_sold(self, card_id: int, network_id: int) -> None:
        """تحديد البطاقة كمباعة وإبطال التخزين المؤقت"""
        # إبطال تخزين البطاقات المؤقت
        self.cache.invalidate_cards(network_id)
        
        # تحديث قاعدة البيانات
        from bot_modules.database import get_db_connection
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                UPDATE network_cards 
                SET is_sold = 1, sold_at = ?
                WHERE id = ?
            ''', (datetime.now(), card_id))
            
            conn.commit()
            
        finally:
            conn.close()

# إنشاء مثيل عام للاستخدام
smart_cache = SmartCache()
cached_db_ops = CachedDatabaseOperations(smart_cache)