#!/usr/bin/env python3
"""
خدمة إدارة العروض
Offers Management Service
"""

import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from bot_modules.database_manager import db_manager
from bot_modules.input_validation import InputValidator

logger = logging.getLogger(__name__)

class OfferService:
    """خدمة إدارة العروض"""
    
    @staticmethod
    def create_offer(offer_data: Dict, user_id: int) -> Tuple[bool, Optional[int], str]:
        """إنشاء عرض جديد"""
        try:
            # التحقق من البيانات
            validations = [
                (True, offer_data.get('title', '').strip()) if offer_data.get('title', '').strip() else (False, "عنوان العرض مطلوب"),
                InputValidator.validate_description(offer_data.get('description', ''), min_length=10),
                InputValidator.validate_percentage(str(offer_data.get('discount_percentage', 0))),
                (True, int(offer_data.get('duration_days', 0))) if offer_data.get('duration_days', 0) > 0 else (False, "مدة العرض يجب أن تكون أكبر من صفر")
            ]
            
            for is_valid, value_or_error in validations:
                if not is_valid:
                    return False, None, str(value_or_error)
            
            # إنشاء العرض
            offer_id = db_manager.create_offer_safe(offer_data, user_id)
            
            logger.info(f"تم إنشاء عرض جديد: {offer_id} بواسطة المستخدم {user_id}")
            return True, offer_id, "تم إنشاء العرض بنجاح"
            
        except Exception as e:
            logger.error(f"Error creating offer: {e}")
            return False, None, f"خطأ في إنشاء العرض: {str(e)}"
    
    @staticmethod
    def get_active_offers(network_id: int = None, limit: int = 10) -> List[Dict]:
        """الحصول على العروض النشطة"""
        try:
            where_clause = "WHERE o.is_active = 1 AND o.end_date >= DATE('now')"
            params = []
            
            if network_id:
                where_clause += " AND o.network_id = ?"
                params.append(network_id)
            
            query = f'''
                SELECT o.*, n.name as network_name, n.provider,
                       u.full_name as created_by_name,
                       (o.max_uses - COALESCE(o.current_uses, 0)) as remaining_uses
                FROM offers o
                LEFT JOIN networks n ON o.network_id = n.id
                LEFT JOIN users u ON o.created_by = u.id
                {where_clause}
                ORDER BY o.created_at DESC
                LIMIT ?
            '''
            
            params.append(limit)
            results = db_manager.execute_query(query, tuple(params), fetch='all')
            
            return [dict(row) for row in results] if results else []
            
        except Exception as e:
            logger.error(f"Error getting active offers: {e}")
            return []
    
    @staticmethod
    def apply_offer(offer_id: int, user_id: int, purchase_amount: float) -> Tuple[bool, float, str]:
        """تطبيق عرض على عملية شراء"""
        try:
            # الحصول على تفاصيل العرض
            query = '''
                SELECT * FROM offers 
                WHERE id = ? AND is_active = 1 AND end_date >= DATE('now')
            '''
            
            offer = db_manager.execute_query(query, (offer_id,), fetch='one')
            
            if not offer:
                return False, purchase_amount, "العرض غير متاح أو منتهي الصلاحية"
            
            offer = dict(offer)
            
            # التحقق من الحد الأقصى للاستخدام
            if offer['max_uses'] and offer['current_uses'] >= offer['max_uses']:
                return False, purchase_amount, "تم استنفاد العرض"
            
            # حساب الخصم
            discount_amount = 0
            if offer['discount_percentage']:
                discount_amount = purchase_amount * (offer['discount_percentage'] / 100)
            elif offer['discount_amount']:
                discount_amount = min(offer['discount_amount'], purchase_amount)
            
            final_amount = purchase_amount - discount_amount
            
            # تحديث عدد الاستخدامات
            update_query = "UPDATE offers SET current_uses = COALESCE(current_uses, 0) + 1 WHERE id = ?"
            db_manager.execute_query(update_query, (offer_id,))
            
            logger.info(f"تم تطبيق العرض {offer_id} للمستخدم {user_id}: خصم {discount_amount:.2f}")
            return True, final_amount, f"تم تطبيق خصم {discount_amount:.2f} ريال"
            
        except Exception as e:
            logger.error(f"Error applying offer: {e}")
            return False, purchase_amount, f"خطأ في تطبيق العرض: {str(e)}"
    
    @staticmethod
    def get_offer_statistics() -> Dict:
        """إحصائيات العروض"""
        try:
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                # إحصائيات عامة
                cursor.execute('''
                    SELECT 
                        COUNT(*) as total_offers,
                        COUNT(CASE WHEN is_active = 1 AND end_date >= DATE('now') THEN 1 END) as active_offers,
                        COUNT(CASE WHEN end_date < DATE('now') THEN 1 END) as expired_offers,
                        COALESCE(SUM(current_uses), 0) as total_uses
                    FROM offers
                ''')
                
                general_stats = dict(cursor.fetchone())
                
                # أفضل العروض استخداماً
                cursor.execute('''
                    SELECT title, current_uses, discount_percentage
                    FROM offers
                    WHERE current_uses > 0
                    ORDER BY current_uses DESC
                    LIMIT 5
                ''')
                
                top_offers = [dict(row) for row in cursor.fetchall()]
                
                return {
                    'general': general_stats,
                    'top_offers': top_offers,
                    'generated_at': datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Error getting offer statistics: {e}")
            return {}
    
    @staticmethod
    def deactivate_offer(offer_id: int, user_id: int) -> Tuple[bool, str]:
        """إلغاء تفعيل عرض"""
        try:
            # التحقق من الصلاحية
            from bot_modules.permissions import has_permission
            
            if not has_permission(user_id, 'offers:edit'):
                return False, "لا تملك صلاحية تعديل العروض"
            
            # إلغاء التفعيل
            query = "UPDATE offers SET is_active = 0 WHERE id = ?"
            rows_affected = db_manager.execute_query(query, (offer_id,))
            
            if rows_affected > 0:
                logger.info(f"تم إلغاء تفعيل العرض {offer_id} بواسطة المستخدم {user_id}")
                return True, "تم إلغاء تفعيل العرض بنجاح"
            else:
                return False, "العرض غير موجود"
            
        except Exception as e:
            logger.error(f"Error deactivating offer: {e}")
            return False, f"خطأ في إلغاء العرض: {str(e)}"

# إنشاء مثيل مشترك
offer_service = OfferService()