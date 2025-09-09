#!/usr/bin/env python3
"""
Accounting Engine - نظام المحاسبة التلقائي
يطبق مبدأ القيد المزدوج ويربط المعاملات بالقيود المحاسبية
"""

import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from bot_modules.database import get_db_connection, get_db_context
from bot_modules.config import (
    ACCOUNT_TYPE_ASSET, ACCOUNT_TYPE_LIABILITY, ACCOUNT_TYPE_EQUITY,
    ACCOUNT_TYPE_REVENUE, ACCOUNT_TYPE_EXPENSE, ACCOUNT_CODE_ISSUANCE_EXPENSE,
    ACCOUNT_CODE_BOT_COMMISSION_REVENUE
)

logger = logging.getLogger(__name__)

class AccountingEngine:
    """محرك المحاسبة التلقائي"""
    
    # خريطة الحسابات للمعاملات المختلفة
    TRANSACTION_ACCOUNTS = {
        'purchase': {
            'debit': '1000',   # النقدية (من العميل)
            'credit': '4000'   # إيرادات المبيعات
        },
        'transfer': {
            'debit': '1100',   # محافظ العملاء (المستلم)
            'credit': '1100'   # محافظ العملاء (المرسل)
        },
        'coupon_redeem': {
            'debit': '1000',   # النقدية
            'credit': '4200'   # إيرادات أخرى
        },
        'commission': {
            'debit': '5200',   # مصروف عمولات
            'credit': '2100'   # عمولات مستحقة
        },
        'card_purchase': {
            'debit': '1000',   # النقدية
            'credit': '4000'   # إيرادات بيع الكروت
        },
        'money_creation': {
            'debit': '1000',   # النقدية
            'credit': '3000'   # رأس المال
        },
        'transfer_fee': {
            'debit': '1000',   # النقدية (رسوم التحويل)
            'credit': '4200'   # إيرادات أخرى
        }
    }

    @staticmethod
    def create_journal_entry(description: str, created_by: int, reference_type: str = None, reference_id: str = None) -> str:
        """إنشاء قيد محاسبي جديد"""
        try:
            with get_db_context() as conn:

                cursor = conn.cursor()
            entry_id = str(uuid.uuid4())
            
            cursor.execute('''
                INSERT INTO journal_entries (id, description, created_at, created_by)
                VALUES (?, ?, ?, ?)
            ''', (entry_id, description, datetime.now(), created_by))
            
            conn.commit()            logger.info(f"Created journal entry: {entry_id} - {description}")
            return entry_id
            
        except Exception as e:
            logger.error(f"Error creating journal entry: {e}")
            return None

    @staticmethod
    def add_journal_line(entry_id: str, account_code: str, debit: float = 0, credit: float = 0, 
                        user_id: int = None, ref_type: str = None, ref_id: str = None):
        """إضافة بند إلى القيد المحاسبي"""
        try:
            with get_db_context() as conn:

                cursor = conn.cursor()
            # البحث عن الحساب في chart_of_accounts (الجدول الرئيسي)
            cursor.execute('SELECT id FROM chart_of_accounts WHERE account_code = ?', (account_code,))
            account = cursor.fetchone()
            
            if not account:
                logger.error(f"Account not found in chart_of_accounts: {account_code}")                return False
            
            account_id = account['id']
            
            # تسجيل مباشر في دفتر الأستاذ العام (تجاهل journal_lines مؤقتاً بسبب foreign key issue)
            cursor.execute('''
                INSERT INTO general_ledger 
                (entry_id, transaction_date, account_id, debit_amount, credit_amount, 
                 description, reference_type, reference_id, currency, created_at, created_by)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (entry_id, datetime.now().date(), account_id, debit, credit,
                  f"قيد تلقائي - {ref_type}", ref_type, ref_id, 'YER', datetime.now(), user_id))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Added journal line: {account_code} - Debit: {debit}, Credit: {credit}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding journal line: {e}")
            return False

    @staticmethod
    def record_transaction_accounting(transaction_type: str, amount: float, user_id: int, 
                                    transaction_id: str, description: str = None,
                                    from_user_id: int = None, to_user_id: int = None):
        """تسجيل المعاملة محاسبياً بمبدأ القيد المزدوج"""
        try:
            if transaction_type not in AccountingEngine.TRANSACTION_ACCOUNTS:
                logger.warning(f"Unknown transaction type for accounting: {transaction_type}")
                return False
            
            # إنشاء وصف القيد
            if not description:
                descriptions = {
                    'purchase': 'شراء كرت',
                    'transfer': 'تحويل رصيد',
                    'coupon_redeem': 'شحن بكوبون',
                    'commission': 'عمولة',
                    'card_purchase': 'شراء كرت',
                    'money_creation': 'إنشاء رصيد',
                    'transfer_fee': 'رسوم تحويل'
                }
                description = descriptions.get(transaction_type, 'معاملة مالية')
            
            # إنشاء القيد المحاسبي
            entry_id = AccountingEngine.create_journal_entry(
                f"{description} - {amount:.2f} ريال",
                user_id,
                transaction_type,
                transaction_id
            )
            
            if not entry_id:
                return False
            
            accounts = AccountingEngine.TRANSACTION_ACCOUNTS[transaction_type]
            
            # معالجة خاصة للتحويلات
            if transaction_type == 'transfer' and from_user_id and to_user_id:
                # قيد للمرسل (تقليل رصيده)
                AccountingEngine.add_journal_line(
                    entry_id, accounts['credit'], 0, amount, 
                    from_user_id, transaction_type, transaction_id
                )
                # قيد للمستلم (زيادة رصيده)
                AccountingEngine.add_journal_line(
                    entry_id, accounts['debit'], amount, 0, 
                    to_user_id, transaction_type, transaction_id
                )
            else:
                # القيود العادية
                # الجانب المدين
                AccountingEngine.add_journal_line(
                    entry_id, accounts['debit'], amount, 0, 
                    user_id, transaction_type, transaction_id
                )
                # الجانب الدائن
                AccountingEngine.add_journal_line(
                    entry_id, accounts['credit'], 0, amount, 
                    user_id, transaction_type, transaction_id
                )
            
            logger.info(f"Successfully recorded accounting entry for {transaction_type}: {amount}")
            return True
            
        except Exception as e:
            logger.error(f"Error recording transaction accounting: {e}")
            return False

    @staticmethod
    def get_account_balance(account_code: str) -> float:
        """الحصول على رصيد حساب محاسبي"""
        try:
            with get_db_context() as conn:

                cursor = conn.cursor()
            cursor.execute('''
                SELECT 
                    COALESCE(SUM(debit_amount), 0) - COALESCE(SUM(credit_amount), 0) as balance
                FROM general_ledger gl
                JOIN chart_of_accounts coa ON gl.account_id = coa.id
                WHERE coa.account_code = ?
            ''', (account_code,))
            
            result = cursor.fetchone()
            balance = result[0] if result else 0            return balance
            
        except Exception as e:
            logger.error(f"Error getting account balance: {e}")
            return 0

    @staticmethod
    def get_trial_balance() -> List[Dict]:
        """الحصول على ميزان المراجعة"""
        try:
            with get_db_context() as conn:

                cursor = conn.cursor()
            cursor.execute('''
                SELECT 
                    coa.account_code,
                    coa.account_name,
                    coa.account_type,
                    COALESCE(SUM(gl.debit_amount), 0) as total_debit,
                    COALESCE(SUM(gl.credit_amount), 0) as total_credit,
                    COALESCE(SUM(gl.debit_amount), 0) - COALESCE(SUM(gl.credit_amount), 0) as balance
                FROM chart_of_accounts coa
                LEFT JOIN general_ledger gl ON coa.id = gl.account_id
                WHERE coa.is_active = 1
                GROUP BY coa.id, coa.account_code, coa.account_name, coa.account_type
                ORDER BY coa.account_code
            ''')
            
            accounts = cursor.fetchall()            return [dict(account) for account in accounts]
            
        except Exception as e:
            logger.error(f"Error getting trial balance: {e}")
            return []

    @staticmethod
    def verify_balance_integrity():
        """التحقق من سلامة الميزان"""
        try:
            with get_db_context() as conn:

                cursor = conn.cursor()
            # إجمالي المدين والدائن
            cursor.execute('''
                SELECT 
                    COALESCE(SUM(debit_amount), 0) as total_debit,
                    COALESCE(SUM(credit_amount), 0) as total_credit
                FROM general_ledger
            ''')
            
            result = cursor.fetchone()
            total_debit = result[0] if result else 0
            total_credit = result[1] if result else 0            difference = abs(total_debit - total_credit)
            is_balanced = difference < 0.01  # تسامح صغير للأخطاء العشرية
            
            return {
                'is_balanced': is_balanced,
                'total_debit': total_debit,
                'total_credit': total_credit,
                'difference': difference
            }
            
        except Exception as e:
            logger.error(f"Error verifying balance integrity: {e}")
            return None

    @staticmethod
    def backfill_missing_entries():
        """ملء القيود المحاسبية المفقودة للمعاملات السابقة"""
        try:
            with get_db_context() as conn:

                cursor = conn.cursor()
            # الحصول على المعاملات التي لا توجد لها قيود محاسبية
            cursor.execute('''
                SELECT t.id, t.type, t.amount, t.from_user, t.to_user, t.description, t.created_at
                FROM transactions t
                LEFT JOIN general_ledger gl ON t.id = gl.reference_id
                WHERE gl.id IS NULL
                ORDER BY t.created_at
            ''')
            
            missing_transactions = cursor.fetchall()            success_count = 0
            
            for transaction in missing_transactions:
                trans_id, trans_type, amount, from_user, to_user, desc, created_at = transaction
                
                # تسجيل القيد المحاسبي
                success = AccountingEngine.record_transaction_accounting(
                    trans_type, amount, from_user or to_user, trans_id, desc, from_user, to_user
                )
                
                if success:
                    success_count += 1
            
            logger.info(f"Backfilled {success_count} missing accounting entries out of {len(missing_transactions)}")
            return success_count, len(missing_transactions)
            
        except Exception as e:
            logger.error(f"Error backfilling missing entries: {e}")
            return 0, 0

# دوال مساعدة للاستدعاء المباشر
def record_purchase_accounting(amount: float, user_id: int, transaction_id: str):
    """تسجيل محاسبة الشراء"""
    return AccountingEngine.record_transaction_accounting(
        'card_purchase', amount, user_id, transaction_id, 'شراء كرت'
    )

def record_transfer_accounting(amount: float, from_user_id: int, to_user_id: int, transaction_id: str):
    """تسجيل محاسبة التحويل"""
    return AccountingEngine.record_transaction_accounting(
        'transfer', amount, from_user_id, transaction_id, 'تحويل رصيد', from_user_id, to_user_id
    )

def record_coupon_accounting(amount: float, user_id: int, transaction_id: str):
    """تسجيل محاسبة شحن الكوبون"""
    return AccountingEngine.record_transaction_accounting(
        'coupon_redeem', amount, user_id, transaction_id, 'شحن بكوبون'
    )

def record_commission_accounting(amount: float, user_id: int, transaction_id: str):
    """تسجيل محاسبة العمولة"""
    return AccountingEngine.record_transaction_accounting(
        'commission', amount, user_id, transaction_id, 'عمولة'
    )

def record_money_creation_accounting(amount: float, user_id: int, transaction_id: str):
    """تسجيل محاسبة إنشاء الرصيد"""
    return AccountingEngine.record_transaction_accounting(
        'money_creation', amount, user_id, transaction_id, 'إنشاء رصيد'
    )

def record_transfer_fee_accounting(amount: float, user_id: int, transaction_id: str):
    """تسجيل محاسبة رسوم التحويل"""
    return AccountingEngine.record_transaction_accounting(
        'transfer_fee', amount, user_id, transaction_id, 'رسوم تحويل'
    )