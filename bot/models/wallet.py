"""
نموذج المحفظة الإلكترونية
"""

import uuid
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Optional, List
from datetime import datetime
from bot.database.connection import db_manager
from bot.config import MIN_TRANSFER_AMOUNT, MAX_TRANSFER_AMOUNT

logger = logging.getLogger(__name__)

class TransactionType(Enum):
    """أنواع معاملات المحفظة"""
    TRANSFER = "transfer"  # تحويل بين المحافظ
    PAYMENT = "payment"    # دفع للتجار
    REFUND = "refund"      # استرداد

class TransactionStatus(Enum):
    """حالات المعاملات"""
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class EWalletTransaction:
    """معاملة المحفظة الإلكترونية"""
    id: str
    sender_id: Optional[int]
    receiver_id: Optional[int]
    amount: float
    transaction_type: TransactionType
    status: TransactionStatus = TransactionStatus.PENDING
    description: Optional[str] = None
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

class EWallet:
    """نظام المحفظة الإلكترونية"""
    
    @staticmethod
    def transfer(sender_id: int, receiver_wallet: str, amount: float, description: str = None) -> dict:
        """تحويل أموال بين المحافظ"""
        
        # التحقق من صحة المبلغ
        if amount < MIN_TRANSFER_AMOUNT:
            return {
                'success': False,
                'message': f'الحد الأدنى للتحويل هو {MIN_TRANSFER_AMOUNT} ريال'
            }
        
        if amount > MAX_TRANSFER_AMOUNT:
            return {
                'success': False,
                'message': f'الحد الأقصى للتحويل هو {MAX_TRANSFER_AMOUNT} ريال'
            }
        
        try:
            with db_manager.get_cursor() as (conn, cursor):
                # البحث عن المرسل
                cursor.execute('SELECT id, balance, wallet_number FROM users WHERE id = ?', (sender_id,))
                sender_row = cursor.fetchone()
                if not sender_row:
                    return {'success': False, 'message': 'المرسل غير موجود'}
                
                sender_balance = sender_row[1]
                
                # التحقق من الرصيد
                if sender_balance < amount:
                    return {'success': False, 'message': 'الرصيد غير كافي'}
                
                # البحث عن المستقبل
                cursor.execute('SELECT id, wallet_number FROM users WHERE wallet_number = ?', (receiver_wallet,))
                receiver_row = cursor.fetchone()
                if not receiver_row:
                    return {'success': False, 'message': 'رقم المحفظة غير صحيح'}
                
                receiver_id = receiver_row[0]
                
                # منع التحويل للنفس
                if sender_id == receiver_id:
                    return {'success': False, 'message': 'لا يمكن التحويل إلى نفس المحفظة'}
                
                # إنشاء معرف المعاملة
                transaction_id = str(uuid.uuid4())
                
                # تسجيل المعاملة
                cursor.execute('''
                    INSERT INTO e_wallet_transactions 
                    (id, sender_id, receiver_id, amount, transaction_type, description, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (transaction_id, sender_id, receiver_id, amount, TransactionType.TRANSFER.value, description, TransactionStatus.PENDING.value))
                
                # تحديث الأرصدة
                cursor.execute('UPDATE users SET balance = balance - ? WHERE id = ?', (amount, sender_id))
                cursor.execute('UPDATE users SET balance = balance + ? WHERE id = ?', (amount, receiver_id))
                
                # تحديث حالة المعاملة
                cursor.execute('''
                    UPDATE e_wallet_transactions 
                    SET status = ?, completed_at = CURRENT_TIMESTAMP 
                    WHERE id = ?
                ''', (TransactionStatus.COMPLETED.value, transaction_id))
                
                # تسجيل في سجل النشاط
                EWallet._log_activity(cursor, sender_id, f'تحويل {amount} ريال إلى محفظة {receiver_wallet}')
                EWallet._log_activity(cursor, receiver_id, f'استلام {amount} ريال من محفظة {sender_row[2]}')
                
                return {
                    'success': True,
                    'message': 'تم التحويل بنجاح',
                    'transaction_id': transaction_id,
                    'new_balance': sender_balance - amount
                }
                
        except Exception as e:
            logger.error(f"خطأ في التحويل: {e}")
            return {'success': False, 'message': 'حدث خطأ أثناء التحويل'}
    
    @staticmethod
    def pay_vendor(user_id: int, vendor_id: int, amount: float, description: str = None) -> dict:
        """دفع للتجار"""
        
        try:
            with db_manager.get_cursor() as (conn, cursor):
                # التحقق من المستخدم
                cursor.execute('SELECT balance FROM users WHERE id = ?', (user_id,))
                user_row = cursor.fetchone()
                if not user_row or user_row[0] < amount:
                    return {'success': False, 'message': 'الرصيد غير كافي'}
                
                # التحقق من التاجر
                cursor.execute('SELECT id, commission_rate FROM vendors WHERE id = ? AND is_active = 1', (vendor_id,))
                vendor_row = cursor.fetchone()
                if not vendor_row:
                    return {'success': False, 'message': 'التاجر غير موجود أو غير نشط'}
                
                commission_rate = vendor_row[1]
                commission = amount * commission_rate
                vendor_amount = amount - commission
                
                transaction_id = str(uuid.uuid4())
                
                # تسجيل المعاملة
                cursor.execute('''
                    INSERT INTO e_wallet_transactions 
                    (id, sender_id, receiver_id, amount, transaction_type, description, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (transaction_id, user_id, None, amount, TransactionType.PAYMENT.value, description, TransactionStatus.COMPLETED.value))
                
                # خصم من المستخدم
                cursor.execute('UPDATE users SET balance = balance - ? WHERE id = ?', (amount, user_id))
                
                # تسجيل النشاط
                EWallet._log_activity(cursor, user_id, f'دفع {amount} ريال للتاجر (عمولة: {commission})')
                
                return {
                    'success': True,
                    'message': 'تم الدفع بنجاح',
                    'transaction_id': transaction_id,
                    'commission': commission
                }
                
        except Exception as e:
            logger.error(f"خطأ في الدفع للتاجر: {e}")
            return {'success': False, 'message': 'حدث خطأ أثناء الدفع'}
    
    @staticmethod
    def get_transaction_history(user_id: int, limit: int = 50) -> List[dict]:
        """جلب تاريخ المعاملات"""
        
        try:
            with db_manager.get_cursor() as (conn, cursor):
                cursor.execute('''
                    SELECT e.id, e.sender_id, e.receiver_id, e.amount, e.transaction_type,
                           e.status, e.description, e.created_at, e.completed_at,
                           u1.wallet_number as sender_wallet, u2.wallet_number as receiver_wallet
                    FROM e_wallet_transactions e
                    LEFT JOIN users u1 ON e.sender_id = u1.id
                    LEFT JOIN users u2 ON e.receiver_id = u2.id
                    WHERE e.sender_id = ? OR e.receiver_id = ?
                    ORDER BY e.created_at DESC
                    LIMIT ?
                ''', (user_id, user_id, limit))
                
                transactions = []
                for row in cursor.fetchall():
                    transactions.append({
                        'id': row[0],
                        'sender_id': row[1],
                        'receiver_id': row[2],
                        'amount': row[3],
                        'type': row[4],
                        'status': row[5],
                        'description': row[6],
                        'created_at': row[7],
                        'completed_at': row[8],
                        'sender_wallet': row[9],
                        'receiver_wallet': row[10],
                        'is_incoming': row[2] == user_id
                    })
                
                return transactions
                
        except Exception as e:
            logger.error(f"خطأ في جلب تاريخ المعاملات: {e}")
            return []
    
    @staticmethod
    def _log_activity(cursor, user_id: int, action: str, details: str = None):
        """تسجيل النشاط"""
        try:
            cursor.execute('''
                INSERT INTO activity_log (user_id, action, details)
                VALUES (?, ?, ?)
            ''', (user_id, action, details))
        except Exception as e:
            logger.error(f"خطأ في تسجيل النشاط: {e}")