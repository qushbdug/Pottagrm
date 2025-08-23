#!/usr/bin/env python3
"""
خدمة إدارة الشبكات
Network Management Service
"""

import logging
from typing import List, Dict, Optional, Tuple
from bot_modules.database_manager import db_manager
from bot_modules.input_validation import InputValidator

logger = logging.getLogger(__name__)

class NetworkService:
    """خدمة إدارة الشبكات"""
    
    @staticmethod
    def create_network(network_data: Dict, user_id: int) -> Tuple[bool, Optional[int], str]:
        """إنشاء شبكة جديدة"""
        try:
            # التحقق من البيانات
            validations = [
                InputValidator.validate_network_name(network_data.get('name', '')),
                InputValidator.validate_description(network_data.get('description', ''), min_length=5),
                (True, network_data.get('provider', '').strip()) if network_data.get('provider', '').strip() else (False, "اسم المزود مطلوب"),
                (True, network_data.get('location', '').strip()) if network_data.get('location', '').strip() else (False, "الموقع مطلوب")
            ]
            
            for is_valid, value_or_error in validations:
                if not is_valid:
                    return False, None, value_or_error
            
            # إنشاء الشبكة
            network_id = db_manager.create_network_safe(network_data, user_id)
            
            logger.info(f"تم إنشاء شبكة جديدة: {network_id} بواسطة المستخدم {user_id}")
            return True, network_id, "تم إنشاء الشبكة بنجاح"
            
        except Exception as e:
            logger.error(f"Error in create_network service: {e}")
            return False, None, f"خطأ في إنشاء الشبكة: {str(e)}"
    
    @staticmethod
    def get_networks_for_user(user_id: int, user_role: str) -> List[Dict]:
        """الحصول على الشبكات حسب دور المستخدم"""
        try:
            if user_role in ['super_admin', 'admin']:
                # المشرفون يرون جميع الشبكات
                query = '''
                    SELECT n.*, u.full_name as supplier_name,
                           COUNT(cc.id) as categories_count,
                           COUNT(c.id) as total_cards,
                           COUNT(CASE WHEN c.is_sold = 0 THEN 1 END) as available_cards
                    FROM networks n
                    LEFT JOIN users u ON n.supplier_id = u.id
                    LEFT JOIN card_categories cc ON n.id = cc.network_id
                    LEFT JOIN cards c ON cc.id = c.category_id
                    GROUP BY n.id
                    ORDER BY n.created_at DESC
                '''
                params = ()
            elif user_role == 'supplier':
                # المزود يرى شبكاته فقط
                query = '''
                    SELECT n.*, u.full_name as supplier_name,
                           COUNT(cc.id) as categories_count,
                           COUNT(c.id) as total_cards,
                           COUNT(CASE WHEN c.is_sold = 0 THEN 1 END) as available_cards
                    FROM networks n
                    LEFT JOIN users u ON n.supplier_id = u.id
                    LEFT JOIN card_categories cc ON n.id = cc.network_id
                    LEFT JOIN cards c ON cc.id = c.category_id
                    WHERE n.supplier_id = ?
                    GROUP BY n.id
                    ORDER BY n.created_at DESC
                '''
                params = (user_id,)
            else:
                # العملاء والوكلاء يرون الشبكات النشطة فقط
                query = '''
                    SELECT n.*, u.full_name as supplier_name,
                           COUNT(cc.id) as categories_count,
                           COUNT(c.id) as total_cards,
                           COUNT(CASE WHEN c.is_sold = 0 THEN 1 END) as available_cards
                    FROM networks n
                    LEFT JOIN users u ON n.supplier_id = u.id
                    LEFT JOIN card_categories cc ON n.id = cc.network_id AND cc.is_available = 1
                    LEFT JOIN cards c ON cc.id = c.category_id
                    WHERE n.is_active = 1 AND n.is_approved = 1
                    GROUP BY n.id
                    HAVING available_cards > 0
                    ORDER BY n.created_at DESC
                '''
                params = ()
            
            results = db_manager.execute_query(query, params, fetch='all')
            return [dict(row) for row in results] if results else []
            
        except Exception as e:
            logger.error(f"Error getting networks for user: {e}")
            return []
    
    @staticmethod
    def get_network_details(network_id: int, user_id: int) -> Optional[Dict]:
        """الحصول على تفاصيل شبكة معينة"""
        try:
            query = '''
                SELECT n.*, u.full_name as supplier_name,
                       COUNT(cc.id) as categories_count,
                       MIN(cc.price) as min_price,
                       MAX(cc.price) as max_price,
                       COUNT(c.id) as total_cards,
                       COUNT(CASE WHEN c.is_sold = 0 THEN 1 END) as available_cards
                FROM networks n
                LEFT JOIN users u ON n.supplier_id = u.id
                LEFT JOIN card_categories cc ON n.id = cc.network_id AND cc.is_available = 1
                LEFT JOIN cards c ON cc.id = c.category_id
                WHERE n.id = ?
                GROUP BY n.id
            '''
            
            result = db_manager.execute_query(query, (network_id,), fetch='one')
            return dict(result) if result else None
            
        except Exception as e:
            logger.error(f"Error getting network details: {e}")
            return None
    
    @staticmethod
    def search_networks(search_query: str, user_role: str = 'user') -> List[Dict]:
        """البحث في الشبكات"""
        try:
            # التحقق من استعلام البحث
            is_valid, search_type, search_value = InputValidator.validate_search_query(search_query)
            
            if not is_valid:
                return []
            
            # بناء الاستعلام حسب نوع البحث
            if search_type == 'name':
                where_clause = "AND (n.name LIKE ? OR n.provider LIKE ?)"
                params = (f"%{search_value}%", f"%{search_value}%")
            elif search_type == 'general':
                where_clause = "AND (n.name LIKE ? OR n.provider LIKE ? OR n.location LIKE ?)"
                params = (f"%{search_value}%", f"%{search_value}%", f"%{search_value}%")
            else:
                where_clause = "AND n.name LIKE ?"
                params = (f"%{search_value}%",)
            
            # الاستعلام الأساسي
            base_query = '''
                SELECT n.*, u.full_name as supplier_name,
                       COUNT(cc.id) as categories_count,
                       MIN(cc.price) as min_price,
                       MAX(cc.price) as max_price,
                       COUNT(CASE WHEN c.is_sold = 0 THEN 1 END) as available_cards
                FROM networks n
                LEFT JOIN users u ON n.supplier_id = u.id
                LEFT JOIN card_categories cc ON n.id = cc.network_id AND cc.is_available = 1
                LEFT JOIN cards c ON cc.id = c.category_id
                WHERE n.is_active = 1 AND n.is_approved = 1
            '''
            
            query = base_query + where_clause + " GROUP BY n.id ORDER BY available_cards DESC, n.created_at DESC LIMIT 20"
            
            results = db_manager.execute_query(query, params, fetch='all')
            return [dict(row) for row in results] if results else []
            
        except Exception as e:
            logger.error(f"Error searching networks: {e}")
            return []
    
    @staticmethod
    def update_network(network_id: int, updates: Dict, user_id: int) -> Tuple[bool, str]:
        """تحديث بيانات الشبكة"""
        try:
            # التحقق من ملكية الشبكة أو الصلاحيات
            from bot_modules.permissions import has_permission
            
            network = NetworkService.get_network_details(network_id, user_id)
            if not network:
                return False, "الشبكة غير موجودة"
            
            # التحقق من الصلاحيات
            if network['supplier_id'] != user_id and not has_permission(user_id, 'networks:edit'):
                return False, "لا تملك صلاحية تعديل هذه الشبكة"
            
            # بناء استعلام التحديث
            update_fields = []
            params = []
            
            for field, value in updates.items():
                if field in ['name', 'provider', 'description', 'location']:
                    # التحقق من القيمة
                    if field == 'name':
                        is_valid, validated_value = InputValidator.validate_network_name(value)
                        if not is_valid:
                            return False, validated_value
                    elif field == 'description':
                        is_valid, validated_value = InputValidator.validate_description(value)
                        if not is_valid:
                            return False, validated_value
                    else:
                        validated_value = InputValidator.sanitize_text(value)
                    
                    update_fields.append(f"{field} = ?")
                    params.append(validated_value)
            
            if not update_fields:
                return False, "لا توجد حقول للتحديث"
            
            # تنفيذ التحديث
            params.append(network_id)
            query = f"UPDATE networks SET {', '.join(update_fields)} WHERE id = ?"
            
            db_manager.execute_query(query, tuple(params))
            
            # مسح الكاش
            db_manager.cleanup_cache()
            
            logger.info(f"تم تحديث الشبكة {network_id} بواسطة المستخدم {user_id}")
            return True, "تم تحديث الشبكة بنجاح"
            
        except Exception as e:
            logger.error(f"Error updating network: {e}")
            return False, f"خطأ في تحديث الشبكة: {str(e)}"

# إنشاء مثيل مشترك
network_service = NetworkService()