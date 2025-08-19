#!/usr/bin/env python3
"""
مدير قاعدة البيانات المحسن
Enhanced Database Manager
"""

import sqlite3
import logging
from contextlib import contextmanager
from typing import List, Dict, Any, Optional
import threading
from cachetools import TTLCache
import time

logger = logging.getLogger(__name__)

class DatabaseManager:
    """مدير قاعدة البيانات المحسن"""
    
    def __init__(self, db_path: str = "yemen_net.db"):
        self.db_path = db_path
        self.connection_pool = threading.local()
        self.query_cache = TTLCache(maxsize=100, ttl=300)  # 5 دقائق
        self.setup_database()
    
    def setup_database(self):
        """إعداد قاعدة البيانات"""
        with self.get_connection() as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute("PRAGMA journal_mode = WAL")
            conn.execute("PRAGMA synchronous = NORMAL")
            conn.execute("PRAGMA busy_timeout = 30000")
            conn.execute("PRAGMA cache_size = 10000")
            conn.execute("PRAGMA temp_store = MEMORY")
    
    @contextmanager
    def get_connection(self):
        """الحصول على اتصال محمي بقاعدة البيانات"""
        conn = None
        try:
            conn = sqlite3.connect(
                self.db_path, 
                timeout=30.0,
                check_same_thread=False
            )
            conn.row_factory = sqlite3.Row  # للوصول بالأسماء
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Database connection error: {e}")
            raise
        finally:
            if conn:
                conn.close()
    
    def execute_query(self, query: str, params: tuple = (), fetch: str = 'none') -> Any:
        """تنفيذ استعلام مع إدارة محسنة للاتصال"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                
                if fetch == 'all':
                    result = cursor.fetchall()
                elif fetch == 'one':
                    result = cursor.fetchone()
                elif fetch == 'many':
                    result = cursor.fetchmany()
                else:
                    result = cursor.rowcount
                
                conn.commit()
                return result
                
        except Exception as e:
            logger.error(f"Query execution error: {e}")
            logger.error(f"Query: {query}")
            logger.error(f"Params: {params}")
            raise
    
    def execute_transaction(self, operations: List[Dict]) -> bool:
        """تنفيذ عدة عمليات في معاملة واحدة"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                for operation in operations:
                    query = operation['query']
                    params = operation.get('params', ())
                    cursor.execute(query, params)
                
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"Transaction error: {e}")
            return False
    
    def get_cached_networks(self, force_refresh: bool = False) -> List[Dict]:
        """الحصول على الشبكات مع تخزين مؤقت"""
        cache_key = 'active_networks'
        
        if not force_refresh and cache_key in self.query_cache:
            return self.query_cache[cache_key]
        
        try:
            query = '''
                SELECT n.*, COUNT(cc.id) as categories_count,
                       MIN(cc.price) as min_price, MAX(cc.price) as max_price
                FROM networks n
                LEFT JOIN card_categories cc ON n.id = cc.network_id AND cc.is_available = 1
                WHERE n.is_active = 1 AND n.is_approved = 1
                GROUP BY n.id
                ORDER BY n.created_at DESC
            '''
            
            results = self.execute_query(query, fetch='all')
            networks = [dict(row) for row in results] if results else []
            
            # تخزين في الكاش
            self.query_cache[cache_key] = networks
            
            return networks
            
        except Exception as e:
            logger.error(f"Error getting cached networks: {e}")
            return []
    
    def get_user_transactions(self, user_id: int, limit: int = 10) -> List[Dict]:
        """الحصول على معاملات المستخدم مع تخزين مؤقت"""
        cache_key = f'user_transactions_{user_id}_{limit}'
        
        if cache_key in self.query_cache:
            return self.query_cache[cache_key]
        
        try:
            query = '''
                SELECT t.*, 
                       u1.full_name as from_user_name,
                       u2.full_name as to_user_name
                FROM transactions t
                LEFT JOIN users u1 ON t.from_user = u1.id
                LEFT JOIN users u2 ON t.to_user = u2.id
                WHERE t.from_user = ? OR t.to_user = ?
                ORDER BY t.created_at DESC
                LIMIT ?
            '''
            
            results = self.execute_query(query, (user_id, user_id, limit), fetch='all')
            transactions = [dict(row) for row in results] if results else []
            
            # تخزين مؤقت لدقيقة واحدة فقط (البيانات المالية حساسة)
            self.query_cache[cache_key] = transactions
            
            return transactions
            
        except Exception as e:
            logger.error(f"Error getting user transactions: {e}")
            return []
    
    def create_network_safe(self, network_data: Dict, user_id: int) -> Optional[int]:
        """إنشاء شبكة بطريقة آمنة"""
        try:
            # التحقق من البيانات المطلوبة
            required_fields = ['name', 'provider', 'description', 'location']
            for field in required_fields:
                if not network_data.get(field):
                    raise ValueError(f"الحقل مطلوب: {field}")
            
            # التحقق من عدم تكرار الاسم
            existing = self.execute_query(
                "SELECT id FROM networks WHERE name = ? AND supplier_id = ?",
                (network_data['name'], user_id),
                fetch='one'
            )
            
            if existing:
                raise ValueError("اسم الشبكة موجود بالفعل لهذا المزود")
            
            # إنشاء الشبكة
            query = '''
                INSERT INTO networks (supplier_id, name, city, provider, description, location, 
                                    created_by, is_active, is_approved, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, 1, 1, CURRENT_TIMESTAMP)
            '''
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (
                    user_id,  # supplier_id
                    network_data['name'],
                    network_data.get('city', network_data['location']),  # city
                    network_data['provider'],
                    network_data['description'],
                    network_data['location'],
                    user_id  # created_by
                ))
                
                network_id = cursor.lastrowid
                conn.commit()
                
                # مسح الكاش
                self.query_cache.clear()
                
                logger.info(f"تم إنشاء شبكة جديدة: {network_id}")
                return network_id
                
        except Exception as e:
            logger.error(f"Error creating network: {e}")
            raise
    
    def create_offer_safe(self, offer_data: Dict, user_id: int) -> Optional[int]:
        """إنشاء عرض بطريقة آمنة"""
        try:
            # التحقق من البيانات المطلوبة
            required_fields = ['title', 'description', 'discount_percentage', 'duration_days']
            for field in required_fields:
                if field not in offer_data:
                    raise ValueError(f"الحقل مطلوب: {field}")
            
            # حساب تواريخ العرض
            from datetime import datetime, timedelta
            start_date = datetime.now().date()
            end_date = start_date + timedelta(days=offer_data['duration_days'])
            
            # إنشاء العرض
            query = '''
                INSERT INTO offers (title, description, discount_percentage, start_date, end_date,
                                  max_uses, created_by, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?, 1)
            '''
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (
                    offer_data['title'],
                    offer_data['description'],
                    offer_data['discount_percentage'],
                    start_date,
                    end_date,
                    offer_data.get('max_uses'),
                    user_id
                ))
                
                offer_id = cursor.lastrowid
                conn.commit()
                
                logger.info(f"تم إنشاء عرض جديد: {offer_id}")
                return offer_id
                
        except Exception as e:
            logger.error(f"Error creating offer: {e}")
            raise
    
    def get_financial_summary(self) -> Dict:
        """الحصول على ملخص مالي شامل"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # إجمالي المعاملات
                cursor.execute('''
                    SELECT 
                        COUNT(*) as total_transactions,
                        COALESCE(SUM(amount), 0) as total_amount,
                        COUNT(DISTINCT CASE WHEN from_user IS NOT NULL THEN from_user END) as unique_senders,
                        COUNT(DISTINCT CASE WHEN to_user IS NOT NULL THEN to_user END) as unique_receivers
                    FROM transactions
                ''')
                
                trans_summary = dict(cursor.fetchone())
                
                # المعاملات حسب النوع
                cursor.execute('''
                    SELECT type, COUNT(*) as count, COALESCE(SUM(amount), 0) as total
                    FROM transactions
                    GROUP BY type
                    ORDER BY total DESC
                ''')
                
                trans_by_type = [dict(row) for row in cursor.fetchall()]
                
                # المعاملات اليومية
                cursor.execute('''
                    SELECT 
                        DATE(created_at) as date,
                        COUNT(*) as daily_count,
                        COALESCE(SUM(amount), 0) as daily_amount
                    FROM transactions
                    WHERE DATE(created_at) >= DATE('now', '-7 days')
                    GROUP BY DATE(created_at)
                    ORDER BY date DESC
                ''')
                
                daily_stats = [dict(row) for row in cursor.fetchall()]
                
                return {
                    'summary': trans_summary,
                    'by_type': trans_by_type,
                    'daily_stats': daily_stats,
                    'generated_at': datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Error getting financial summary: {e}")
            return {}
    
    def cleanup_cache(self):
        """تنظيف الكاش"""
        self.query_cache.clear()
        logger.info("تم تنظيف كاش قاعدة البيانات")

# إنشاء مثيل مشترك
db_manager = DatabaseManager()

# دوال مساعدة للاستخدام المباشر
def get_db_connection():
    """الحصول على اتصال قاعدة البيانات"""
    return db_manager.get_connection()

def execute_safe_query(query: str, params: tuple = (), fetch: str = 'none'):
    """تنفيذ استعلام آمن"""
    return db_manager.execute_query(query, params, fetch)

def get_cached_networks(force_refresh: bool = False):
    """الحصول على الشبكات مع تخزين مؤقت"""
    return db_manager.get_cached_networks(force_refresh)

def create_network_safe(network_data: Dict, user_id: int):
    """إنشاء شبكة بطريقة آمنة"""
    return db_manager.create_network_safe(network_data, user_id)

def create_offer_safe(offer_data: Dict, user_id: int):
    """إنشاء عرض بطريقة آمنة"""
    return db_manager.create_offer_safe(offer_data, user_id)