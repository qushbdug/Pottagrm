#!/usr/bin/env python3
"""
Query Optimizer - محسن الاستعلامات
يحسن أداء استعلامات قاعدة البيانات ويمنع استخدام SELECT *
"""

import logging
import time
from typing import Dict, List, Any, Optional, Tuple
from contextlib import contextmanager
from bot_modules.database import get_db_connection

logger = logging.getLogger(__name__)

class QueryOptimizer:
    """محسن الاستعلامات"""
    
    def __init__(self):
        self.query_stats = {}
        self.slow_query_threshold = 1.0  # ثانية واحدة
    
    @contextmanager
    def timed_query(self, query_name: str):
        """قياس وقت تنفيذ الاستعلام"""
        start_time = time.time()
        try:
            yield
        finally:
            execution_time = time.time() - start_time
            self._record_query_stats(query_name, execution_time)
            
            if execution_time > self.slow_query_threshold:
                logger.warning(f"Slow query detected: {query_name} took {execution_time:.2f}s")
    
    def _record_query_stats(self, query_name: str, execution_time: float):
        """تسجيل إحصائيات الاستعلام"""
        if query_name not in self.query_stats:
            self.query_stats[query_name] = {
                'count': 0,
                'total_time': 0,
                'avg_time': 0,
                'max_time': 0,
                'min_time': float('inf')
            }
        
        stats = self.query_stats[query_name]
        stats['count'] += 1
        stats['total_time'] += execution_time
        stats['avg_time'] = stats['total_time'] / stats['count']
        stats['max_time'] = max(stats['max_time'], execution_time)
        stats['min_time'] = min(stats['min_time'], execution_time)
    
    def get_optimized_user_query(self, fields: List[str] = None) -> str:
        """استعلام محسن للمستخدمين"""
        if fields is None:
            fields = ['id', 'telegram_id', 'full_name', 'phone', 'role', 'balance', 'is_active']
        
        return f"SELECT {', '.join(fields)} FROM users"
    
    def get_optimized_transaction_query(self, fields: List[str] = None) -> str:
        """استعلام محسن للمعاملات"""
        if fields is None:
            fields = ['id', 'from_user', 'to_user', 'amount', 'type', 'description', 'created_at']
        
        return f"SELECT {', '.join(fields)} FROM transactions"
    
    def get_optimized_network_query(self, fields: List[str] = None) -> str:
        """استعلام محسن للشبكات"""
        if fields is None:
            fields = ['id', 'supplier_id', 'name', 'provider', 'city', 'is_active', 'is_approved']
        
        return f"SELECT {', '.join(fields)} FROM networks"
    
    def execute_optimized_query(self, query: str, params: Tuple = (), 
                              query_name: str = "unnamed") -> List[Dict]:
        """تنفيذ استعلام محسن مع قياس الأداء"""
        with self.timed_query(query_name):
            conn = get_db_connection()
            cursor = conn.cursor()
            
            try:
                cursor.execute(query, params)
                results = cursor.fetchall()
                return [dict(row) for row in results]
            finally:
                conn.close()
    
    def get_user_by_telegram_id(self, telegram_id: int) -> Optional[Dict]:
        """الحصول على مستخدم بـ telegram_id محسن"""
        query = """
            SELECT id, telegram_id, full_name, phone, role, balance, 
                   is_active, total_purchases, total_spent, created_at, last_activity
            FROM users 
            WHERE telegram_id = ?
        """
        
        results = self.execute_optimized_query(
            query, (telegram_id,), "get_user_by_telegram_id"
        )
        
        return results[0] if results else None
    
    def get_user_transactions(self, user_id: int, limit: int = 50, 
                            offset: int = 0) -> List[Dict]:
        """الحصول على معاملات المستخدم محسن"""
        query = """
            SELECT t.id, t.from_user, t.to_user, t.amount, t.type, 
                   t.description, t.created_at,
                   u1.full_name as from_user_name,
                   u2.full_name as to_user_name
            FROM transactions t
            LEFT JOIN users u1 ON t.from_user = u1.id
            LEFT JOIN users u2 ON t.to_user = u2.id
            WHERE t.from_user = ? OR t.to_user = ?
            ORDER BY t.created_at DESC
            LIMIT ? OFFSET ?
        """
        
        return self.execute_optimized_query(
            query, (user_id, user_id, limit, offset), "get_user_transactions"
        )
    
    def get_network_cards(self, network_id: int, is_sold: bool = False) -> List[Dict]:
        """الحصول على كروت الشبكة محسن"""
        query = """
            SELECT id, card_code, card_value, is_sold, sold_at, created_at
            FROM network_cards 
            WHERE network_id = ? AND is_sold = ?
            ORDER BY card_value, created_at
        """
        
        return self.execute_optimized_query(
            query, (network_id, is_sold), "get_network_cards"
        )
    
    def get_supplier_networks(self, supplier_id: int) -> List[Dict]:
        """الحصول على شبكات المورد محسن"""
        query = """
            SELECT n.id, n.name, n.provider, n.city, n.location, 
                   n.is_active, n.is_approved, n.created_at,
                   COUNT(nc.id) as total_cards,
                   COUNT(CASE WHEN nc.is_sold = 0 THEN 1 END) as available_cards
            FROM networks n
            LEFT JOIN network_cards nc ON n.id = nc.network_id
            WHERE n.supplier_id = ?
            GROUP BY n.id
            ORDER BY n.created_at DESC
        """
        
        return self.execute_optimized_query(
            query, (supplier_id,), "get_supplier_networks"
        )
    
    def get_popular_networks(self, limit: int = 20) -> List[Dict]:
        """الحصول على الشبكات الأكثر شعبية"""
        query = """
            SELECT n.id, n.name, n.provider, n.city,
                   COUNT(t.id) as transaction_count,
                   COALESCE(SUM(t.amount), 0) as total_sales
            FROM networks n
            LEFT JOIN transactions t ON t.description LIKE '%' || n.name || '%'
            WHERE n.is_active = 1 AND n.is_approved = 1
            GROUP BY n.id
            ORDER BY transaction_count DESC, total_sales DESC
            LIMIT ?
        """
        
        return self.execute_optimized_query(
            query, (limit,), "get_popular_networks"
        )
    
    def get_user_balance_summary(self, user_id: int) -> Dict:
        """ملخص رصيد المستخدم محسن"""
        query = """
            SELECT 
                u.balance as current_balance,
                u.total_spent,
                u.total_purchases,
                COALESCE(SUM(CASE WHEN wt.amount > 0 THEN wt.amount ELSE 0 END), 0) as total_deposits,
                COALESCE(SUM(CASE WHEN wt.amount < 0 THEN ABS(wt.amount) ELSE 0 END), 0) as total_withdrawals,
                COUNT(wt.id) as total_transactions
            FROM users u
            LEFT JOIN wallet_transactions wt ON u.id = wt.user_id
            WHERE u.id = ?
            GROUP BY u.id
        """
        
        results = self.execute_optimized_query(
            query, (user_id,), "get_user_balance_summary"
        )
        
        return results[0] if results else {}
    
    def search_networks(self, search_term: str, limit: int = 20) -> List[Dict]:
        """البحث في الشبكات محسن"""
        query = """
            SELECT n.id, n.name, n.provider, n.city, n.location,
                   n.is_active, n.is_approved,
                   u.full_name as supplier_name
            FROM networks n
            JOIN users u ON n.supplier_id = u.id
            WHERE (n.name LIKE ? OR n.provider LIKE ? OR n.city LIKE ?)
              AND n.is_active = 1 AND n.is_approved = 1
            ORDER BY 
                CASE WHEN n.name LIKE ? THEN 1
                     WHEN n.provider LIKE ? THEN 2
                     ELSE 3 END,
                n.name
            LIMIT ?
        """
        
        search_pattern = f"%{search_term}%"
        exact_pattern = f"{search_term}%"
        
        return self.execute_optimized_query(
            query, (search_pattern, search_pattern, search_pattern, 
                   exact_pattern, exact_pattern, limit), 
            "search_networks"
        )
    
    def get_query_statistics(self) -> Dict[str, Any]:
        """الحصول على إحصائيات الاستعلامات"""
        total_queries = sum(stats['count'] for stats in self.query_stats.values())
        total_time = sum(stats['total_time'] for stats in self.query_stats.values())
        
        slow_queries = {
            name: stats for name, stats in self.query_stats.items()
            if stats['avg_time'] > self.slow_query_threshold
        }
        
        return {
            'total_queries': total_queries,
            'total_execution_time': total_time,
            'average_query_time': total_time / total_queries if total_queries > 0 else 0,
            'slow_queries_count': len(slow_queries),
            'slow_queries': slow_queries,
            'query_details': self.query_stats
        }
    
    def optimize_database(self):
        """تحسين قاعدة البيانات"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            # تحليل الجداول
            cursor.execute('ANALYZE')
            
            # تحسين الفهارس
            optimization_queries = [
                # فهارس المستخدمين
                'CREATE INDEX IF NOT EXISTS idx_users_telegram_id ON users(telegram_id)',
                'CREATE INDEX IF NOT EXISTS idx_users_role_active ON users(role, is_active)',
                'CREATE INDEX IF NOT EXISTS idx_users_balance ON users(balance)',
                
                # فهارس المعاملات
                'CREATE INDEX IF NOT EXISTS idx_transactions_from_user_date ON transactions(from_user, created_at)',
                'CREATE INDEX IF NOT EXISTS idx_transactions_to_user_date ON transactions(to_user, created_at)',
                'CREATE INDEX IF NOT EXISTS idx_transactions_type ON transactions(type)',
                
                # فهارس الشبكات
                'CREATE INDEX IF NOT EXISTS idx_networks_supplier_active ON networks(supplier_id, is_active)',
                'CREATE INDEX IF NOT EXISTS idx_networks_active_approved ON networks(is_active, is_approved)',
                'CREATE INDEX IF NOT EXISTS idx_networks_name ON networks(name)',
                
                # فهارس كروت الشبكة
                'CREATE INDEX IF NOT EXISTS idx_network_cards_network_sold ON network_cards(network_id, is_sold)',
                'CREATE INDEX IF NOT EXISTS idx_network_cards_value ON network_cards(card_value)',
                
                # فهارس معاملات المحفظة
                'CREATE INDEX IF NOT EXISTS idx_wallet_transactions_user_date ON wallet_transactions(user_id, created_at)',
                'CREATE INDEX IF NOT EXISTS idx_wallet_transactions_type ON wallet_transactions(transaction_type)'
            ]
            
            for query in optimization_queries:
                try:
                    cursor.execute(query)
                    logger.info(f"Created index: {query}")
                except Exception as e:
                    logger.warning(f"Index creation failed: {e}")
            
            conn.commit()
            logger.info("Database optimization completed")
            
        except Exception as e:
            logger.error(f"Database optimization failed: {e}")
            conn.rollback()
        finally:
            conn.close()

# إنشاء مثيل عام للاستخدام
query_optimizer = QueryOptimizer()