#!/usr/bin/env python3
"""
Database Networks Module - Yemen Net Bot
مسؤول عن جميع عمليات قاعدة البيانات المتعلقة بالشبكات
يفصل منطق قاعدة البيانات عن منطق العرض
"""

import logging
from typing import List, Dict, Optional, Tuple
from bot_modules.database import get_db_connection
from bot_modules.error_handler import safe_database_transaction

logger = logging.getLogger(__name__)

class NetworkNotFoundError(Exception):
    """استثناء يرمى عندما لا توجد الشبكة المطلوبة"""
    pass

class DatabaseNetworks:
    """كلاس مسؤول عن جميع عمليات قاعدة البيانات للشبكات"""
    
    @staticmethod
    def get_all_networks(active_only: bool = True, approved_only: bool = True) -> List[Dict]:
        """
        جلب جميع الشبكات من قاعدة البيانات
        
        Args:
            active_only: جلب الشبكات النشطة فقط
            approved_only: جلب الشبكات المعتمدة فقط
            
        Returns:
            قائمة بجميع الشبكات
        """
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # بناء الاستعلام حسب المعايير
            query = '''
                SELECT 
                    n.id, n.name, n.provider, n.description, n.location, 
                    n.is_active, n.is_approved, n.created_at, n.supplier_id,
                    COUNT(DISTINCT cc.id) as categories_count,
                    MIN(cc.price) as min_price, 
                    MAX(cc.price) as max_price,
                    SUM(CASE WHEN c.is_sold = 0 THEN 1 ELSE 0 END) as available_cards
                FROM networks n
                LEFT JOIN card_categories cc ON n.id = cc.network_id AND cc.is_available = 1
                LEFT JOIN cards c ON cc.id = c.category_id
                WHERE 1=1
            '''
            
            params = []
            if active_only:
                query += " AND n.is_active = 1"
            if approved_only:
                query += " AND n.is_approved = 1"
                
            query += " GROUP BY n.id, n.name, n.provider, n.description, n.location, n.is_active, n.is_approved, n.created_at, n.supplier_id"
            query += " ORDER BY n.created_at DESC"
            
            cursor.execute(query, params)
            networks = cursor.fetchall()
            conn.close()
            
            # تحويل النتائج إلى قاموس
            result = []
            for network in networks:
                result.append({
                    'id': network[0],
                    'name': network[1],
                    'provider': network[2],
                    'description': network[3],
                    'location': network[4],
                    'is_active': network[5],
                    'is_approved': network[6],
                    'created_at': network[7],
                    'supplier_id': network[8],
                    'categories_count': network[9] or 0,
                    'min_price': network[10],
                    'max_price': network[11],
                    'available_cards': network[12] or 0
                })
            
            logger.info(f"جلب {len(result)} شبكة من قاعدة البيانات")
            return result
            
        except Exception as e:
            logger.error(f"خطأ في جلب الشبكات: {e}", exc_info=True)
            raise
    
    @staticmethod
    def get_network_by_id(network_id: int) -> Dict:
        """
        جلب شبكة معينة بواسطة المعرف
        
        Args:
            network_id: معرف الشبكة
            
        Returns:
            بيانات الشبكة
            
        Raises:
            NetworkNotFoundError: إذا لم توجد الشبكة
        """
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT 
                    n.id, n.name, n.provider, n.description, n.location, 
                    n.is_active, n.is_approved, n.created_at, n.supplier_id,
                    COUNT(DISTINCT cc.id) as categories_count,
                    MIN(cc.price) as min_price, 
                    MAX(cc.price) as max_price,
                    SUM(CASE WHEN c.is_sold = 0 THEN 1 ELSE 0 END) as available_cards
                FROM networks n
                LEFT JOIN card_categories cc ON n.id = cc.network_id AND cc.is_available = 1
                LEFT JOIN cards c ON cc.id = c.category_id
                WHERE n.id = ? AND n.is_active = 1
                GROUP BY n.id, n.name, n.provider, n.description, n.location, n.is_active, n.is_approved, n.created_at, n.supplier_id
            ''', (network_id,))
            
            network = cursor.fetchone()
            conn.close()
            
            if not network:
                raise NetworkNotFoundError(f"الشبكة برقم {network_id} غير موجودة أو غير متاحة")
            
            result = {
                'id': network[0],
                'name': network[1],
                'provider': network[2],
                'description': network[3],
                'location': network[4],
                'is_active': network[5],
                'is_approved': network[6],
                'created_at': network[7],
                'supplier_id': network[8],
                'categories_count': network[9] or 0,
                'min_price': network[10],
                'max_price': network[11],
                'available_cards': network[12] or 0
            }
            
            logger.info(f"تم جلب الشبكة: {result['name']} (ID: {network_id})")
            return result
            
        except NetworkNotFoundError:
            raise
        except Exception as e:
            logger.error(f"خطأ في جلب الشبكة {network_id}: {e}", exc_info=True)
            raise
    
    @staticmethod
    def get_network_categories(network_id: int) -> List[Dict]:
        """
        جلب فئات الكروت لشبكة معينة
        
        Args:
            network_id: معرف الشبكة
            
        Returns:
            قائمة بفئات الكروت
        """
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT 
                    cc.id, cc.name, cc.value, cc.price, cc.stock_count,
                    cc.currency, cc.is_available,
                    COUNT(CASE WHEN c.is_sold = 0 THEN 1 END) as available_cards
                FROM card_categories cc
                LEFT JOIN cards c ON cc.id = c.category_id
                WHERE cc.network_id = ? AND cc.is_available = 1
                GROUP BY cc.id, cc.name, cc.value, cc.price, cc.stock_count, cc.currency, cc.is_available
                ORDER BY cc.value ASC, cc.price ASC
            ''', (network_id,))
            
            categories = cursor.fetchall()
            conn.close()
            
            result = []
            for category in categories:
                result.append({
                    'id': category[0],
                    'name': category[1],
                    'value': category[2],
                    'price': category[3],
                    'stock_count': category[4],
                    'currency': category[5],
                    'is_available': category[6],
                    'available_cards': category[7] or 0
                })
            
            logger.info(f"تم جلب {len(result)} فئة للشبكة {network_id}")
            return result
            
        except Exception as e:
            logger.error(f"خطأ في جلب فئات الشبكة {network_id}: {e}", exc_info=True)
            raise
    
    @staticmethod
    def search_networks(search_term: str, search_type: str = 'all') -> List[Dict]:
        """
        البحث في الشبكات
        
        Args:
            search_term: مصطلح البحث
            search_type: نوع البحث ('name', 'provider', 'location', 'all')
            
        Returns:
            قائمة بالشبكات المطابقة
        """
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # بناء استعلام البحث
            base_query = '''
                SELECT 
                    n.id, n.name, n.provider, n.description, n.location, 
                    n.is_active, n.is_approved, n.created_at, n.supplier_id,
                    COUNT(DISTINCT cc.id) as categories_count,
                    MIN(cc.price) as min_price, 
                    MAX(cc.price) as max_price,
                    SUM(CASE WHEN c.is_sold = 0 THEN 1 ELSE 0 END) as available_cards
                FROM networks n
                LEFT JOIN card_categories cc ON n.id = cc.network_id AND cc.is_available = 1
                LEFT JOIN cards c ON cc.id = c.category_id
                WHERE n.is_active = 1 AND n.is_approved = 1
            '''
            
            search_pattern = f"%{search_term}%"
            
            if search_type == 'name':
                query = base_query + " AND n.name LIKE ?"
                params = [search_pattern]
            elif search_type == 'provider':
                query = base_query + " AND n.provider LIKE ?"
                params = [search_pattern]
            elif search_type == 'location':
                query = base_query + " AND n.location LIKE ?"
                params = [search_pattern]
            elif search_type == 'id':
                # البحث بالمعرف (رقم صحيح)
                try:
                    network_id = int(search_term)
                    query = base_query + " AND n.id = ?"
                    params = [network_id]
                except ValueError:
                    return []  # إذا لم يكن رقم صحيح
            else:  # search_type == 'all'
                query = base_query + " AND (n.name LIKE ? OR n.provider LIKE ? OR n.location LIKE ?)"
                params = [search_pattern, search_pattern, search_pattern]
            
            query += " GROUP BY n.id, n.name, n.provider, n.description, n.location, n.is_active, n.is_approved, n.created_at, n.supplier_id"
            query += " ORDER BY n.created_at DESC"
            
            cursor.execute(query, params)
            networks = cursor.fetchall()
            conn.close()
            
            # تحويل النتائج إلى قاموس
            result = []
            for network in networks:
                result.append({
                    'id': network[0],
                    'name': network[1],
                    'provider': network[2],
                    'description': network[3],
                    'location': network[4],
                    'is_active': network[5],
                    'is_approved': network[6],
                    'created_at': network[7],
                    'supplier_id': network[8],
                    'categories_count': network[9] or 0,
                    'min_price': network[10],
                    'max_price': network[11],
                    'available_cards': network[12] or 0
                })
            
            logger.info(f"البحث عن '{search_term}' أعطى {len(result)} نتيجة")
            return result
            
        except Exception as e:
            logger.error(f"خطأ في البحث عن '{search_term}': {e}", exc_info=True)
            raise
    
    @staticmethod
    def get_networks_by_supplier(supplier_id: int) -> List[Dict]:
        """
        جلب شبكات مزود معين
        
        Args:
            supplier_id: معرف المزود
            
        Returns:
            قائمة بشبكات المزود
        """
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT 
                    n.id, n.name, n.provider, n.description, n.location, 
                    n.is_active, n.is_approved, n.created_at, n.supplier_id,
                    COUNT(DISTINCT cc.id) as categories_count,
                    MIN(cc.price) as min_price, 
                    MAX(cc.price) as max_price,
                    SUM(CASE WHEN c.is_sold = 0 THEN 1 ELSE 0 END) as available_cards
                FROM networks n
                LEFT JOIN card_categories cc ON n.id = cc.network_id AND cc.is_available = 1
                LEFT JOIN cards c ON cc.id = c.category_id
                WHERE n.supplier_id = ?
                GROUP BY n.id, n.name, n.provider, n.description, n.location, n.is_active, n.is_approved, n.created_at, n.supplier_id
                ORDER BY n.created_at DESC
            ''', (supplier_id,))
            
            networks = cursor.fetchall()
            conn.close()
            
            result = []
            for network in networks:
                result.append({
                    'id': network[0],
                    'name': network[1],
                    'provider': network[2],
                    'description': network[3],
                    'location': network[4],
                    'is_active': network[5],
                    'is_approved': network[6],
                    'created_at': network[7],
                    'supplier_id': network[8],
                    'categories_count': network[9] or 0,
                    'min_price': network[10],
                    'max_price': network[11],
                    'available_cards': network[12] or 0
                })
            
            logger.info(f"تم جلب {len(result)} شبكة للمزود {supplier_id}")
            return result
            
        except Exception as e:
            logger.error(f"خطأ في جلب شبكات المزود {supplier_id}: {e}", exc_info=True)
            raise


# دوال مساعدة سريعة (wrapper functions)
def get_all_networks(active_only: bool = True, approved_only: bool = True) -> List[Dict]:
    """دالة مساعدة لجلب جميع الشبكات"""
    return DatabaseNetworks.get_all_networks(active_only, approved_only)

def get_network_by_id(network_id: int) -> Dict:
    """دالة مساعدة لجلب شبكة بالمعرف"""
    return DatabaseNetworks.get_network_by_id(network_id)

def get_network_categories(network_id: int) -> List[Dict]:
    """دالة مساعدة لجلب فئات شبكة"""
    return DatabaseNetworks.get_network_categories(network_id)

def search_networks(search_term: str, search_type: str = 'all') -> List[Dict]:
    """دالة مساعدة للبحث في الشبكات"""
    return DatabaseNetworks.search_networks(search_term, search_type)

def get_networks_by_supplier(supplier_id: int) -> List[Dict]:
    """دالة مساعدة لجلب شبكات مزود"""
    return DatabaseNetworks.get_networks_by_supplier(supplier_id)