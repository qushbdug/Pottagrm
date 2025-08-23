#!/usr/bin/env python3
"""
خدمة إدارة المعاملات المالية
Financial Transactions Service
"""

import logging
from typing import List, Dict, Optional, Tuple
from decimal import Decimal
from datetime import datetime
from bot_modules.database_manager import db_manager
from bot_modules.input_validation import InputValidator

logger = logging.getLogger(__name__)

class TransactionService:
    """خدمة إدارة المعاملات المالية"""
    
    @staticmethod
    def transfer_balance(from_user_id: int, to_user_id: int, amount: float, description: str = None) -> Tuple[bool, Optional[int], str]:
        """تحويل رصيد بين المستخدمين"""
        try:
            # التحقق من صحة المبلغ
            is_valid, validated_amount, error_msg = InputValidator.validate_amount(str(amount))
            if not is_valid:
                return False, None, error_msg
            
            # التحقق من رصيد المرسل
            from bot_modules.database import get_user
            sender = get_user(from_user_id)
            receiver = get_user(to_user_id)
            
            if not sender or not receiver:
                return False, None, "أحد المستخدمين غير موجود"
            
            if sender['balance'] < validated_amount:
                return False, None, f"رصيد غير كافٍ. رصيدك: {sender['balance']:,.2f} ريال"
            
            if validated_amount < 1:
                return False, None, "الحد الأدنى للتحويل: 1 ريال"
            
            # تنفيذ التحويل في معاملة واحدة
            operations = [
                {
                    'query': 'UPDATE users SET balance = balance - ? WHERE id = ?',
                    'params': (validated_amount, from_user_id)
                },
                {
                    'query': 'UPDATE users SET balance = balance + ? WHERE id = ?',
                    'params': (validated_amount, to_user_id)
                },
                {
                    'query': '''INSERT INTO transactions (from_user, to_user, amount, type, description, created_at)
                               VALUES (?, ?, ?, 'transfer', ?, CURRENT_TIMESTAMP)''',
                    'params': (from_user_id, to_user_id, validated_amount, description or f"تحويل من {sender['full_name']} إلى {receiver['full_name']}")
                }
            ]
            
            success = db_manager.execute_transaction(operations)
            
            if success:
                # الحصول على معرف المعاملة
                transaction_id = db_manager.execute_query(
                    "SELECT id FROM transactions WHERE from_user = ? AND to_user = ? AND amount = ? ORDER BY created_at DESC LIMIT 1",
                    (from_user_id, to_user_id, validated_amount),
                    fetch='one'
                )[0]
                
                # إنشاء قيد محاسبي
                try:
                    from bot_modules.accounting_integration import create_accounting_entry
                    create_accounting_entry('transfer', validated_amount, from_user_id, transaction_id)
                except Exception as acc_e:
                    logger.warning(f"خطأ في القيد المحاسبي: {acc_e}")
                
                logger.info(f"تم تحويل {validated_amount} ريال من {from_user_id} إلى {to_user_id}")
                return True, transaction_id, f"تم تحويل {validated_amount:,.2f} ريال بنجاح"
            else:
                return False, None, "فشل في تنفيذ التحويل"
            
        except Exception as e:
            logger.error(f"Error in transfer balance: {e}")
            return False, None, f"خطأ في التحويل: {str(e)}"
    
    @staticmethod
    def redeem_coupon(user_id: int, coupon_code: str) -> Tuple[bool, Optional[float], str]:
        """استخدام كوبون شحن"""
        try:
            # التحقق من رمز الكوبون
            is_valid, validated_code = InputValidator.validate_coupon_code(coupon_code)
            if not is_valid:
                return False, None, validated_code
            
            # البحث عن الكوبون
            coupon_query = '''
                SELECT * FROM coupons 
                WHERE coupon_code = ? AND is_used = 0 
                AND (expiry_date IS NULL OR expiry_date > CURRENT_TIMESTAMP)
            '''
            
            coupon = db_manager.execute_query(coupon_query, (validated_code,), fetch='one')
            
            if not coupon:
                return False, None, "الكوبون غير صحيح أو مستخدم أو منتهي الصلاحية"
            
            coupon = dict(coupon)
            amount = coupon['amount']
            
            # تنفيذ استخدام الكوبون
            operations = [
                {
                    'query': 'UPDATE users SET balance = balance + ? WHERE id = ?',
                    'params': (amount, user_id)
                },
                {
                    'query': '''UPDATE coupons SET is_used = 1, used_by = ?, used_at = CURRENT_TIMESTAMP 
                               WHERE coupon_code = ?''',
                    'params': (user_id, validated_code)
                },
                {
                    'query': '''INSERT INTO transactions (to_user, amount, type, description, created_at)
                               VALUES (?, ?, 'coupon_redeem', ?, CURRENT_TIMESTAMP)''',
                    'params': (user_id, amount, f"شحن بكوبون {validated_code}")
                }
            ]
            
            success = db_manager.execute_transaction(operations)
            
            if success:
                # إنشاء قيد محاسبي
                try:
                    from bot_modules.accounting_integration import create_accounting_entry
                    transaction_id = db_manager.execute_query(
                        "SELECT id FROM transactions WHERE to_user = ? AND amount = ? AND type = 'coupon_redeem' ORDER BY created_at DESC LIMIT 1",
                        (user_id, amount),
                        fetch='one'
                    )[0]
                    create_accounting_entry('coupon_redeem', amount, user_id, transaction_id)
                except Exception as acc_e:
                    logger.warning(f"خطأ في القيد المحاسبي: {acc_e}")
                
                logger.info(f"تم استخدام كوبون {validated_code} بقيمة {amount} ريال للمستخدم {user_id}")
                return True, amount, f"تم شحن {amount:,.2f} ريال بنجاح"
            else:
                return False, None, "فشل في استخدام الكوبون"
            
        except Exception as e:
            logger.error(f"Error redeeming coupon: {e}")
            return False, None, f"خطأ في استخدام الكوبون: {str(e)}"
    
    @staticmethod
    def purchase_card(user_id: int, category_id: int, quantity: int = 1) -> Tuple[bool, Optional[List], str]:
        """شراء كرت/كروت"""
        try:
            # الحصول على تفاصيل الفئة
            category_query = '''
                SELECT cc.*, n.name as network_name, n.provider
                FROM card_categories cc
                JOIN networks n ON cc.network_id = n.id
                WHERE cc.id = ? AND cc.is_available = 1 AND n.is_active = 1
            '''
            
            category = db_manager.execute_query(category_query, (category_id,), fetch='one')
            
            if not category:
                return False, None, "فئة الكرت غير متاحة"
            
            category = dict(category)
            total_amount = category['price'] * quantity
            
            # التحقق من رصيد المستخدم
            from bot_modules.database import get_user
            user = get_user(user_id)
            
            if user['balance'] < total_amount:
                return False, None, f"رصيد غير كافٍ. المطلوب: {total_amount:,.2f} ريال، المتاح: {user['balance']:,.2f} ريال"
            
            # البحث عن كروت متاحة
            cards_query = '''
                SELECT * FROM cards 
                WHERE category_id = ? AND is_used = 0 AND is_sold = 0
                ORDER BY added_at ASC
                LIMIT ?
            '''
            
            available_cards = db_manager.execute_query(cards_query, (category_id, quantity), fetch='all')
            
            if len(available_cards) < quantity:
                return False, None, f"كروت غير كافية. متاح: {len(available_cards)}, مطلوب: {quantity}"
            
            # تنفيذ عملية الشراء
            purchased_cards = []
            operations = [
                {
                    'query': 'UPDATE users SET balance = balance - ? WHERE id = ?',
                    'params': (total_amount, user_id)
                }
            ]
            
            for card in available_cards:
                card_dict = dict(card)
                operations.extend([
                    {
                        'query': 'UPDATE cards SET is_sold = 1, sold_at = CURRENT_TIMESTAMP, used_by = ? WHERE id = ?',
                        'params': (user_id, card_dict['id'])
                    }
                ])
                purchased_cards.append(card_dict)
            
            # إضافة معاملة الشراء
            operations.append({
                'query': '''INSERT INTO transactions (from_user, to_user, amount, type, description, created_at)
                           VALUES (?, NULL, ?, 'card_purchase', ?, CURRENT_TIMESTAMP)''',
                'params': (user_id, total_amount, f"شراء {quantity} كرت من {category['network_name']}")
            })
            
            success = db_manager.execute_transaction(operations)
            
            if success:
                # إنشاء قيد محاسبي
                try:
                    from bot_modules.accounting_integration import create_accounting_entry
                    transaction_id = db_manager.execute_query(
                        "SELECT id FROM transactions WHERE from_user = ? AND amount = ? AND type = 'card_purchase' ORDER BY created_at DESC LIMIT 1",
                        (user_id, total_amount),
                        fetch='one'
                    )[0]
                    create_accounting_entry('card_purchase', total_amount, user_id, transaction_id)
                except Exception as acc_e:
                    logger.warning(f"خطأ في القيد المحاسبي: {acc_e}")
                
                logger.info(f"تم شراء {quantity} كرت بقيمة {total_amount} ريال للمستخدم {user_id}")
                return True, purchased_cards, f"تم شراء {quantity} كرت بنجاح"
            else:
                return False, None, "فشل في تنفيذ عملية الشراء"
            
        except Exception as e:
            logger.error(f"Error purchasing card: {e}")
            return False, None, f"خطأ في الشراء: {str(e)}"
    
    @staticmethod
    def get_transaction_history(user_id: int, transaction_type: str = None, limit: int = 20) -> List[Dict]:
        """الحصول على سجل المعاملات"""
        try:
            where_clause = "WHERE (t.from_user = ? OR t.to_user = ?)"
            params = [user_id, user_id]
            
            if transaction_type:
                where_clause += " AND t.type = ?"
                params.append(transaction_type)
            
            query = f'''
                SELECT t.*, 
                       u1.full_name as from_user_name,
                       u2.full_name as to_user_name,
                       CASE WHEN t.from_user = ? THEN 'sent' ELSE 'received' END as direction
                FROM transactions t
                LEFT JOIN users u1 ON t.from_user = u1.id
                LEFT JOIN users u2 ON t.to_user = u2.id
                {where_clause}
                ORDER BY t.created_at DESC
                LIMIT ?
            '''
            
            params.insert(0, user_id)  # للـ CASE statement
            params.append(limit)
            
            results = db_manager.execute_query(query, tuple(params), fetch='all')
            return [dict(row) for row in results] if results else []
            
        except Exception as e:
            logger.error(f"Error getting transaction history: {e}")
            return []

# إنشاء مثيل مشترك
transaction_service = TransactionService()