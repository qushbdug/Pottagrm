#!/usr/bin/env python3
"""
Hybrid Database - قاعدة بيانات هجينة
تحاول استخدام Supabase وتعود إلى SQLite عند الفشل
"""

import logging
import sqlite3
import os
from typing import Dict, List, Any, Optional
from datetime import datetime
from bot_modules.config import DB_PATH

logger = logging.getLogger(__name__)

class HybridDatabase:
    """قاعدة بيانات هجينة تدعم Supabase مع fallback إلى SQLite"""
    
    def __init__(self):
        self.supabase_available = False
        self.supabase_client = None
        
        # محاولة تهيئة Supabase
        self._try_init_supabase()
        
        logger.info(f"Hybrid database initialized - Supabase: {self.supabase_available}")
    
    def _try_init_supabase(self):
        """محاولة تهيئة Supabase"""
        try:
            from supabase import create_client
            
            SUPABASE_URL = "https://poxdecozxjnzbmumvqzx.supabase.co"
            SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InBveGRlY296eGpuemJtdW12cXp4Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTY2ODIzNDIsImV4cCI6MjA3MjI1ODM0Mn0.OpoVMldNCBqIkhSSvic29LlSrhfmOIqt7NBp5v27CUk"
            
            self.supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
            
            # اختبار الاتصال
            result = self.supabase_client.table('users').select('count', count='exact').execute()
            self.supabase_available = True
            logger.info("Supabase connection successful")
            
        except Exception as e:
            logger.warning(f"Supabase not available, using SQLite: {e}")
            self.supabase_available = False
    
    def get_sqlite_connection(self):
        """الحصول على اتصال SQLite"""
        conn = sqlite3.connect(DB_PATH, timeout=30.0)
        conn.execute('PRAGMA foreign_keys = ON')
        conn.execute('PRAGMA journal_mode = WAL')
        conn.execute('PRAGMA synchronous = NORMAL')
        conn.execute('PRAGMA cache_size = 2000')
        conn.execute('PRAGMA temp_store = memory')
        conn.row_factory = sqlite3.Row
        return conn
    
    def get_user(self, telegram_id: int) -> Optional[Dict]:
        """الحصول على مستخدم"""
        # محاولة Supabase أولاً
        if self.supabase_available:
            try:
                result = self.supabase_client.table('users').select('*').eq('telegram_id', telegram_id).execute()
                if result.data:
                    logger.debug(f"User {telegram_id} found in Supabase")
                    return result.data[0]
            except Exception as e:
                logger.warning(f"Supabase query failed, falling back to SQLite: {e}")
                self.supabase_available = False
        
        # fallback إلى SQLite
        try:
            conn = self.get_sqlite_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, telegram_id, full_name, phone, role, balance, 
                       is_active, total_purchases, total_spent, created_at, 
                       last_activity, invite_code, wallet_number, referred_by
                FROM users 
                WHERE telegram_id = ?
            ''', (telegram_id,))
            user = cursor.fetchone()
            conn.close()
            
            if user:
                logger.debug(f"User {telegram_id} found in SQLite")
                return dict(user)
            return None
            
        except Exception as e:
            logger.error(f"Error getting user from SQLite: {e}")
            return None
    
    def get_user_by_id(self, user_id: int) -> Optional[Dict]:
        """الحصول على مستخدم بـ ID"""
        # محاولة Supabase أولاً
        if self.supabase_available:
            try:
                result = self.supabase_client.table('users').select('*').eq('id', user_id).execute()
                if result.data:
                    return result.data[0]
            except Exception as e:
                logger.warning(f"Supabase query failed: {e}")
                self.supabase_available = False
        
        # fallback إلى SQLite
        try:
            conn = self.get_sqlite_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
            user = cursor.fetchone()
            conn.close()
            return dict(user) if user else None
        except Exception as e:
            logger.error(f"Error getting user by id: {e}")
            return None
    
    def update_user_balance(self, user_id: int, new_balance: float) -> bool:
        """تحديث رصيد المستخدم"""
        success = False
        
        # محاولة Supabase أولاً
        if self.supabase_available:
            try:
                result = self.supabase_client.table('users').update({
                    'balance': new_balance,
                    'last_activity': datetime.now().isoformat()
                }).eq('id', user_id).execute()
                
                success = len(result.data) > 0
                if success:
                    logger.debug(f"Balance updated in Supabase for user {user_id}")
            except Exception as e:
                logger.warning(f"Supabase update failed: {e}")
                self.supabase_available = False
        
        # fallback إلى SQLite
        if not success:
            try:
                conn = self.get_sqlite_connection()
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE users 
                    SET balance = ?, last_activity = ?
                    WHERE id = ?
                ''', (new_balance, datetime.now(), user_id))
                
                success = cursor.rowcount > 0
                conn.commit()
                conn.close()
                
                if success:
                    logger.debug(f"Balance updated in SQLite for user {user_id}")
                    
            except Exception as e:
                logger.error(f"Error updating balance in SQLite: {e}")
                return False
        
        return success
    
    def get_connection(self):
        """الحصول على اتصال - للتوافق مع الكود الحالي"""
        if self.supabase_available:
            return self.supabase_client
        else:
            return self.get_sqlite_connection()
    
    def get_database_status(self) -> Dict[str, Any]:
        """الحصول على حالة قاعدة البيانات"""
        status = {
            'primary_db': 'supabase' if self.supabase_available else 'sqlite',
            'supabase_available': self.supabase_available,
            'timestamp': datetime.now().isoformat()
        }
        
        # إحصائيات سريعة
        try:
            if self.supabase_available:
                result = self.supabase_client.table('users').select('count', count='exact').execute()
                status['users_count'] = result.count
                status['source'] = 'supabase'
            else:
                conn = self.get_sqlite_connection()
                cursor = conn.cursor()
                cursor.execute('SELECT COUNT(*) FROM users')
                status['users_count'] = cursor.fetchone()[0]
                status['source'] = 'sqlite'
                conn.close()
        except Exception as e:
            status['error'] = str(e)
            status['users_count'] = 0
        
        return status

# إنشاء مثيل عام
hybrid_db = HybridDatabase()

# دوال توافق مع الكود الحالي
def get_db_connection():
    """دالة توافق للحصول على اتصال"""
    return hybrid_db.get_connection()

def get_user(telegram_id: int) -> Optional[Dict]:
    """دالة توافق للحصول على مستخدم"""
    return hybrid_db.get_user(telegram_id)

def get_user_by_id(user_id: int) -> Optional[Dict]:
    """دالة توافق للحصول على مستخدم بـ ID"""
    return hybrid_db.get_user_by_id(user_id)