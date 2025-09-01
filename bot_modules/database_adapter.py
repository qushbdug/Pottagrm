#!/usr/bin/env python3
"""
Database Adapter - محول قاعدة البيانات
يوفر واجهة موحدة للتعامل مع SQLite أو Supabase
"""

import logging
import os
import sqlite3
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
from bot_modules.config import DB_PATH

logger = logging.getLogger(__name__)

# تحديد نوع قاعدة البيانات
USE_SUPABASE = os.getenv('USE_SUPABASE', 'false').lower() == 'true'

class DatabaseAdapter:
    """محول قاعدة البيانات الموحد"""
    
    def __init__(self):
        self.db_type = 'supabase' if USE_SUPABASE else 'sqlite'
        
        if USE_SUPABASE:
            try:
                from bot_modules.supabase_database import supabase_db
                self.db = supabase_db
                logger.info("Using Supabase database")
            except ImportError as e:
                logger.error(f"Failed to import Supabase: {e}")
                logger.info("Falling back to SQLite")
                self.db_type = 'sqlite'
                self.db = None
        else:
            logger.info("Using SQLite database")
            self.db = None
    
    def get_connection(self):
        """الحصول على اتصال قاعدة البيانات"""
        if self.db_type == 'supabase':
            return self.db.supabase
        else:
            # SQLite connection
            conn = sqlite3.connect(DB_PATH, timeout=30.0)
            conn.execute('PRAGMA foreign_keys = ON')
            conn.execute('PRAGMA journal_mode = WAL')
            conn.execute('PRAGMA synchronous = NORMAL')
            conn.execute('PRAGMA cache_size = 2000')
            conn.execute('PRAGMA temp_store = memory')
            conn.row_factory = sqlite3.Row
            return conn
    
    def get_user_by_telegram_id(self, telegram_id: int) -> Optional[Dict]:
        """الحصول على مستخدم بـ telegram_id"""
        if self.db_type == 'supabase':
            return self.db.get_user_by_telegram_id(telegram_id)
        else:
            # SQLite implementation
            conn = self.get_connection()
            cursor = conn.cursor()
            try:
                cursor.execute('''
                    SELECT id, telegram_id, full_name, phone, role, balance, 
                           is_active, total_purchases, total_spent, created_at, 
                           last_activity, invite_code, wallet_number, referred_by
                    FROM users 
                    WHERE telegram_id = ?
                ''', (telegram_id,))
                user = cursor.fetchone()
                return dict(user) if user else None
            finally:
                conn.close()
    
    def get_user_by_id(self, user_id: int) -> Optional[Dict]:
        """الحصول على مستخدم بـ ID"""
        if self.db_type == 'supabase':
            return self.db.get_user_by_id(user_id)
        else:
            # SQLite implementation
            conn = self.get_connection()
            cursor = conn.cursor()
            try:
                cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
                user = cursor.fetchone()
                return dict(user) if user else None
            finally:
                conn.close()
    
    def update_user_balance(self, user_id: int, new_balance: float) -> bool:
        """تحديث رصيد المستخدم"""
        if self.db_type == 'supabase':
            return self.db.update_user_balance(user_id, new_balance)
        else:
            # SQLite implementation
            conn = self.get_connection()
            cursor = conn.cursor()
            try:
                cursor.execute('''
                    UPDATE users 
                    SET balance = ?, last_activity = ?
                    WHERE id = ?
                ''', (new_balance, datetime.now(), user_id))
                
                conn.commit()
                return cursor.rowcount > 0
            except Exception as e:
                logger.error(f"Error updating balance: {e}")
                conn.rollback()
                return False
            finally:
                conn.close()
    
    def create_transaction(self, from_user: int, to_user: int, amount: float,
                          transaction_type: str, description: str) -> Optional[str]:
        """إنشاء معاملة جديدة"""
        if self.db_type == 'supabase':
            return self.db.create_transaction(from_user, to_user, amount, transaction_type, description)
        else:
            # SQLite implementation
            import uuid
            
            conn = self.get_connection()
            cursor = conn.cursor()
            try:
                transaction_id = str(uuid.uuid4())
                cursor.execute('''
                    INSERT INTO transactions (id, from_user, to_user, amount, type, description, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (transaction_id, from_user, to_user, amount, transaction_type, description, datetime.now()))
                
                conn.commit()
                return transaction_id
            except Exception as e:
                logger.error(f"Error creating transaction: {e}")
                conn.rollback()
                return None
            finally:
                conn.close()
    
    def get_user_transactions(self, user_id: int, limit: int = 50) -> List[Dict]:
        """الحصول على معاملات المستخدم"""
        if self.db_type == 'supabase':
            return self.db.get_user_transactions(user_id, limit)
        else:
            # SQLite implementation
            conn = self.get_connection()
            cursor = conn.cursor()
            try:
                cursor.execute('''
                    SELECT id, from_user, to_user, amount, type, description, created_at
                    FROM transactions 
                    WHERE from_user = ? OR to_user = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                ''', (user_id, user_id, limit))
                
                transactions = cursor.fetchall()
                return [dict(t) for t in transactions]
            finally:
                conn.close()
    
    def get_available_cards(self, network_id: int, card_value: float = None) -> List[Dict]:
        """الحصول على البطاقات المتاحة"""
        if self.db_type == 'supabase':
            return self.db.get_available_cards(network_id, card_value)
        else:
            # SQLite implementation
            conn = self.get_connection()
            cursor = conn.cursor()
            try:
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
                return [dict(c) for c in cards]
            finally:
                conn.close()
    
    def execute_query(self, query: str, params: tuple = ()) -> List[Dict]:
        """تنفيذ استعلام مخصص"""
        if self.db_type == 'supabase':
            # للاستعلامات المعقدة في Supabase
            try:
                result = self.db.supabase.rpc('exec_sql', {'sql': query})
                return result.data if result.data else []
            except Exception as e:
                logger.error(f"Error executing Supabase query: {e}")
                return []
        else:
            # SQLite implementation
            conn = self.get_connection()
            cursor = conn.cursor()
            try:
                cursor.execute(query, params)
                results = cursor.fetchall()
                return [dict(r) for r in results]
            finally:
                conn.close()
    
    def get_database_stats(self) -> Dict[str, Any]:
        """الحصول على إحصائيات قاعدة البيانات"""
        stats = {
            'database_type': self.db_type,
            'connection_status': 'connected'
        }
        
        try:
            if self.db_type == 'supabase':
                # إحصائيات Supabase
                tables = ['users', 'networks', 'network_cards', 'transactions', 'coupons']
                for table in tables:
                    result = self.db.supabase.table(table).select('count', count='exact').execute()
                    stats[f'{table}_count'] = result.count if result.count else 0
            else:
                # إحصائيات SQLite
                conn = self.get_connection()
                cursor = conn.cursor()
                
                tables = ['users', 'networks', 'network_cards', 'transactions', 'coupons']
                for table in tables:
                    try:
                        cursor.execute(f'SELECT COUNT(*) FROM {table}')
                        stats[f'{table}_count'] = cursor.fetchone()[0]
                    except:
                        stats[f'{table}_count'] = 0
                
                conn.close()
        
        except Exception as e:
            logger.error(f"Error getting database stats: {e}")
            stats['connection_status'] = 'error'
            stats['error'] = str(e)
        
        return stats

# إنشاء مثيل عام للاستخدام
db_adapter = DatabaseAdapter()