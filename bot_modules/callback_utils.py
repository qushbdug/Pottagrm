"""
أدوات إدارة بيانات Callback
للتأكد من عدم تجاوز الحد المسموح به في تيليجرام (64 بايت)
"""

import hashlib
import json
from typing import Dict, Any, Optional
from datetime import datetime

class CallbackDataManager:
    """مدير بيانات Callback الذكي"""
    
    def __init__(self):
        self._callback_cache = {}
        self._callback_counter = 0
    
    def create_short_callback(self, action: str, data: Dict[str, Any] = None) -> str:
        """
        إنشاء بيانات callback قصيرة
        
        Args:
            action: نوع الإجراء (مثل: buy_card, activate_supplier)
            data: البيانات المراد تضمينها
            
        Returns:
            بيانات callback قصيرة
        """
        if not data:
            return action
        
        # إنشاء معرف فريد قصير
        unique_id = f"{self._callback_counter:04d}"
        self._callback_counter += 1
        
        # تخزين البيانات في الذاكرة مع المعرف
        cache_key = f"{action}_{unique_id}"
        self._callback_cache[cache_key] = {
            'action': action,
            'data': data,
            'timestamp': datetime.now().isoformat()
        }
        
        # إرجاع بيانات callback قصيرة
        return cache_key
    
    def get_callback_data(self, callback_key: str) -> Optional[Dict[str, Any]]:
        """
        استرجاع البيانات من معرف callback
        
        Args:
            callback_key: مفتاح callback
            
        Returns:
            البيانات المخزنة أو None
        """
        if callback_key in self._callback_cache:
            return self._callback_cache[callback_key]
        return None
    
    def cleanup_old_callbacks(self, max_age_hours: int = 24):
        """تنظيف بيانات callback القديمة"""
        from datetime import datetime, timedelta
        
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        keys_to_remove = []
        
        for key, value in self._callback_cache.items():
            if datetime.fromisoformat(value['timestamp']) < cutoff_time:
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            del self._callback_cache[key]
    
    def create_network_callback(self, action: str, network_id: str, **kwargs) -> str:
        """إنشاء callback لشبكة مع بيانات إضافية"""
        data = {'network_id': network_id, **kwargs}
        return self.create_short_callback(action, data)
    
    def create_category_callback(self, action: str, category_id: str, **kwargs) -> str:
        """إنشاء callback لفئة كرت مع بيانات إضافية"""
        data = {'category_id': category_id, **kwargs}
        return self.create_short_callback(action, data)
    
    def create_user_callback(self, action: str, user_id: str, **kwargs) -> str:
        """إنشاء callback لمستخدم مع بيانات إضافية"""
        data = {'user_id': user_id, **kwargs}
        return self.create_short_callback(action, data)

# إنشاء نسخة عامة
callback_manager = CallbackDataManager()

def create_callback(action: str, **data) -> str:
    """دالة مساعدة لإنشاء callback"""
    return callback_manager.create_short_callback(action, data)

def get_callback_data(callback_key: str) -> Optional[Dict[str, Any]]:
    """دالة مساعدة لاسترجاع بيانات callback"""
    return callback_manager.get_callback_data(callback_key)

def cleanup_callbacks():
    """تنظيف بيانات callback القديمة"""
    callback_manager.cleanup_old_callbacks()