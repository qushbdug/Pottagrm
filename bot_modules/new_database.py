#!/usr/bin/env python3
"""
New Database Layer - طبقة قاعدة البيانات الجديدة
تدعم كلاً من SQLite و Supabase مع إمكانية التبديل
"""

import logging
import os
import sqlite3
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
from bot_modules.config import DB_PATH

logger = logging.getLogger(__name__)

# تحديد نوع قاعدة البيانات من متغير البيئة
USE_SUPABASE = os.getenv('USE_SUPABASE', 'false').lower() == 'true'

class DatabaseManager:
    """مدير قاعدة البيانات الموحد"""
    
    def __init__(self):
        self.db_type = 'supabase' if USE_SUPABASE else 'sqlite'
        self.supabase_client = None
        
        if USE_SUPABASE:
            self._init_supabase()
        
        logger.info(f"Database manager initialized with {self.db_type}")
    
    def _init_supabase(self):
        """تهيئة Supabase"""
        try:
            from supabase import create_client
            
            SUPABASE_URL = "https://poxdecozxjnzbmumvqzx.supabase.co"
            SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InBveGRlY296eGpuemJtdW12cXp4Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTY2ODIzNDIsImV4cCI6MjA3MjI1ODM0Mn0.OpoVMldNCBqIkhSSvic29LlSrhfmOIqt7NBp5v27CUk"
            
            self.supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
            logger.info("Supabase client initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Supabase: {e}")
            logger.info("Falling back to SQLite")
            self.db_type = 'sqlite'
    
    def get_connection(self):
        """الحصول على اتصال قاعدة البيانات"""
        if self.db_type == 'supabase':
            return self.supabase_client
        else:
            conn = sqlite3.connect(DB_PATH, timeout=30.0)
            conn.execute('PRAGMA foreign_keys = ON')
            conn.execute('PRAGMA journal_mode = WAL')
            conn.execute('PRAGMA synchronous = NORMAL')
            conn.execute('PRAGMA cache_size = 2000')
            conn.execute('PRAGMA temp_store = memory')
            conn.row_factory = sqlite3.Row
            return conn
    
    def get_user(self, telegram_id: int) -> Optional[Dict]:
        """الحصول على مستخدم بـ telegram_id"""
        try:
            if self.db_type == 'supabase':
                result = self.supabase_client.table('users').select('*').eq('telegram_id', telegram_id).execute()
                return result.data[0] if result.data else None
            else:
                conn = self.get_connection()
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
                return dict(user) if user else None
                
        except Exception as e:
            logger.error(f"Error getting user: {e}")
            return None
    
    def get_user_by_id(self, user_id: int) -> Optional[Dict]:
        """الحصول على مستخدم بـ ID"""
        try:
            if self.db_type == 'supabase':
                result = self.supabase_client.table('users').select('*').eq('id', user_id).execute()
                return result.data[0] if result.data else None
            else:
                conn = self.get_connection()
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
                user = cursor.fetchone()
                conn.close()
                return dict(user) if user else None
                
        except Exception as e:
            logger.error(f"Error getting user by id: {e}")
            return None
    
    def create_user(self, telegram_id: int, full_name: str, phone: str, 
                   role: str, wallet_number: str, invite_code: str) -> Optional[int]:
        """إنشاء مستخدم جديد"""
        try:
            if self.db_type == 'supabase':
                user_data = {
                    'telegram_id': telegram_id,
                    'full_name': full_name,
                    'phone': phone,
                    'role': role,
                    'wallet_number': wallet_number,
                    'invite_code': invite_code,
                    'is_active': role == 'customer',  # العملاء مفعلون تلقائياً
                    'created_at': datetime.now().isoformat()
                }
                
                result = self.supabase_client.table('users').insert(user_data).execute()
                return result.data[0]['id'] if result.data else None
            else:
                conn = self.get_connection()
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO users (telegram_id, full_name, phone, role, wallet_number, invite_code, is_active)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (telegram_id, full_name, phone, role, wallet_number, invite_code, 
                      1 if role == 'customer' else 0))
                
                user_id = cursor.lastrowid
                conn.commit()
                conn.close()
                return user_id
                
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            return None
    
    def update_user_balance(self, user_id: int, new_balance: float) -> bool:
        """تحديث رصيد المستخدم"""
        try:
            if self.db_type == 'supabase':
                result = self.supabase_client.table('users').update({
                    'balance': new_balance,
                    'last_activity': datetime.now().isoformat()
                }).eq('id', user_id).execute()
                
                return len(result.data) > 0
            else:
                conn = self.get_connection()
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE users 
                    SET balance = ?, last_activity = ?
                    WHERE id = ?
                ''', (new_balance, datetime.now(), user_id))
                
                success = cursor.rowcount > 0
                conn.commit()
                conn.close()
                return success
                
        except Exception as e:
            logger.error(f"Error updating balance: {e}")
            return False
    
    def create_transaction(self, from_user: int, to_user: int, amount: float,
                          transaction_type: str, description: str) -> Optional[str]:
        """إنشاء معاملة جديدة"""
        try:
            if self.db_type == 'supabase':
                transaction_data = {
                    'from_user': from_user,
                    'to_user': to_user,
                    'amount': amount,
                    'type': transaction_type,
                    'description': description,
                    'created_at': datetime.now().isoformat()
                }
                
                result = self.supabase_client.table('transactions').insert(transaction_data).execute()
                return result.data[0]['id'] if result.data else None
            else:
                import uuid
                
                conn = self.get_connection()
                cursor = conn.cursor()
                transaction_id = str(uuid.uuid4())
                
                cursor.execute('''
                    INSERT INTO transactions (id, from_user, to_user, amount, type, description, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (transaction_id, from_user, to_user, amount, transaction_type, description, datetime.now()))
                
                conn.commit()
                conn.close()
                return transaction_id
                
        except Exception as e:
            logger.error(f"Error creating transaction: {e}")
            return None
    
    def get_user_transactions(self, user_id: int, limit: int = 50, days: int = None) -> List[Dict]:
        """الحصول على معاملات المستخدم"""
        try:
            if self.db_type == 'supabase':
                query = self.supabase_client.table('transactions').select('*').or_(
                    f'from_user.eq.{user_id},to_user.eq.{user_id}'
                ).order('created_at', desc=True).limit(limit)
                
                result = query.execute()
                return result.data if result.data else []
            else:
                conn = self.get_connection()
                cursor = conn.cursor()
                
                if days:
                    cursor.execute('''
                        SELECT id, from_user, to_user, amount, type, description, created_at
                        FROM transactions 
                        WHERE (from_user = ? OR to_user = ?) 
                        AND created_at >= datetime('now', '-' || ? || ' days')
                        ORDER BY created_at DESC
                        LIMIT ?
                    ''', (user_id, user_id, days, limit))
                else:
                    cursor.execute('''
                        SELECT id, from_user, to_user, amount, type, description, created_at
                        FROM transactions 
                        WHERE from_user = ? OR to_user = ?
                        ORDER BY created_at DESC
                        LIMIT ?
                    ''', (user_id, user_id, limit))
                
                transactions = cursor.fetchall()
                conn.close()
                return [dict(t) for t in transactions]
                
        except Exception as e:
            logger.error(f"Error getting user transactions: {e}")
            return []
    
    def get_available_cards(self, network_id: int, card_value: float = None) -> List[Dict]:
        """الحصول على البطاقات المتاحة"""
        try:
            if self.db_type == 'supabase':
                query = self.supabase_client.table('network_cards').select('*').eq('network_id', network_id).eq('is_sold', False)
                
                if card_value:
                    query = query.eq('card_value', card_value)
                
                result = query.execute()
                return result.data if result.data else []
            else:
                conn = self.get_connection()
                cursor = conn.cursor()
                
                if card_value:
                    cursor.execute('''
                        SELECT id, card_code, card_value, created_at
                        FROM network_cards 
                        WHERE network_id = ? AND card_value = ? AND is_sold = 0
                        ORDER BY card_value
                    ''', (network_id, card_value))
                else:
                    cursor.execute('''
                        SELECT id, card_code, card_value, created_at
                        FROM network_cards 
                        WHERE network_id = ? AND is_sold = 0
                        ORDER BY card_value
                    ''', (network_id,))
                
                cards = cursor.fetchall()
                conn.close()
                return [dict(c) for c in cards]
                
        except Exception as e:
            logger.error(f"Error getting available cards: {e}")
            return []
    
    def mark_card_sold(self, card_id: int) -> bool:
        """تحديد البطاقة كمباعة"""
        try:
            if self.db_type == 'supabase':
                result = self.supabase_client.table('network_cards').update({
                    'is_sold': True,
                    'sold_at': datetime.now().isoformat()
                }).eq('id', card_id).execute()
                
                return len(result.data) > 0
            else:
                conn = self.get_connection()
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE network_cards 
                    SET is_sold = 1, sold_at = ?
                    WHERE id = ?
                ''', (datetime.now(), card_id))
                
                success = cursor.rowcount > 0
                conn.commit()
                conn.close()
                return success
                
        except Exception as e:
            logger.error(f"Error marking card as sold: {e}")
            return False
    
    def get_database_stats(self) -> Dict[str, Any]:
        """الحصول على إحصائيات قاعدة البيانات"""
        stats = {
            'database_type': self.db_type,
            'timestamp': datetime.now().isoformat()
        }
        
        try:
            tables = ['users', 'networks', 'network_cards', 'transactions', 'coupons']
            
            if self.db_type == 'supabase':
                for table in tables:
                    result = self.supabase_client.table(table).select('count', count='exact').execute()
                    stats[f'{table}_count'] = result.count if result.count else 0
            else:
                conn = self.get_connection()
                cursor = conn.cursor()
                
                for table in tables:
                    try:
                        cursor.execute(f'SELECT COUNT(*) FROM {table}')
                        stats[f'{table}_count'] = cursor.fetchone()[0]
                    except:
                        stats[f'{table}_count'] = 0
                
                conn.close()
            
            # حساب إجمالي الأرصدة
            if self.db_type == 'supabase':
                result = self.supabase_client.rpc('sum_user_balances').execute()
                stats['total_balance'] = result.data if result.data else 0
            else:
                conn = self.get_connection()
                cursor = conn.cursor()
                cursor.execute('SELECT COALESCE(SUM(balance), 0) FROM users')
                stats['total_balance'] = cursor.fetchone()[0]
                conn.close()
            
        except Exception as e:
            logger.error(f"Error getting database stats: {e}")
            stats['error'] = str(e)
        
        return stats
    
    def test_connection(self) -> bool:
        """اختبار الاتصال"""
        try:
            if self.db_type == 'supabase':
                result = self.supabase_client.table('users').select('count', count='exact').execute()
                return True
            else:
                conn = self.get_connection()
                cursor = conn.cursor()
                cursor.execute('SELECT 1')
                conn.close()
                return True
                
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            return False

# إنشاء مثيل عام للاستخدام
db_manager = DatabaseManager()

# دوال مساعدة للتوافق مع الكود الحالي
def get_db_connection():
    """دالة توافق للحصول على اتصال قاعدة البيانات"""
    return db_manager.get_connection()

def get_user(telegram_id: int) -> Optional[Dict]:
    """دالة توافق للحصول على مستخدم"""
    return db_manager.get_user(telegram_id)

def get_user_by_id(user_id: int) -> Optional[Dict]:
    """دالة توافق للحصول على مستخدم بـ ID"""
    return db_manager.get_user_by_id(user_id)