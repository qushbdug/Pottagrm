#!/usr/bin/env python3
"""
دمج النظام المحاسبي مع معاملات البوت
Integration of Accounting System with Bot Transactions
"""

import sqlite3
import logging
from datetime import datetime
from decimal import Decimal
import uuid
import json

logger = logging.getLogger(__name__)

def get_db_connection():
    """الحصول على اتصال قاعدة البيانات"""
    conn = sqlite3.connect("yemen_net.db", timeout=30.0)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def create_accounting_entry(transaction_type: str, amount: float, user_id: int, 
                          reference_id: int = None, additional_data: dict = None):
    """إنشاء قيد محاسبي مزدوج للمعاملة"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # إنشاء معرف فريد للقيد
        entry_id = f"JE-{datetime.now().strftime('%Y%m%d%H%M%S')}-{str(uuid.uuid4())[:6]}"
        entry_date = datetime.now().date()
        
        # قواعد القيد المزدوج حسب نوع المعاملة
        accounting_rules = {
            'card_purchase': {
                'description': f'شراء كرت إنترنت - مبلغ {amount:,.2f} ريال',
                'entries': [
                    {'account_code': '1000', 'debit': amount, 'credit': 0, 'desc': 'استلام نقدية من العميل'},
                    {'account_code': '4000', 'debit': 0, 'credit': amount, 'desc': 'إيراد بيع كرت إنترنت'},
                    {'account_code': '5000', 'debit': amount * 0.8, 'credit': 0, 'desc': 'تكلفة الكرت المباع'},
                    {'account_code': '2000', 'debit': 0, 'credit': amount * 0.8, 'desc': 'مستحق للمزود'}
                ]
            },
            'coupon_redeem': {
                'description': f'شحن رصيد بكوبون - مبلغ {amount:,.2f} ريال',
                'entries': [
                    {'account_code': '1100', 'debit': amount, 'credit': 0, 'desc': 'زيادة رصيد محفظة العميل'},
                    {'account_code': '1000', 'debit': 0, 'credit': amount, 'desc': 'تقليل النقدية (قيمة الكوبون)'}
                ]
            },
            'transfer': {
                'description': f'تحويل رصيد بين العملاء - مبلغ {amount:,.2f} ريال',
                'entries': [
                    {'account_code': '1100', 'debit': amount, 'credit': 0, 'desc': 'زيادة رصيد المستلم'},
                    {'account_code': '1100', 'debit': 0, 'credit': amount, 'desc': 'تقليل رصيد المرسل'}
                ]
            },
            'agent_commission': {
                'description': f'عمولة وكيل - مبلغ {amount:,.2f} ريال',
                'entries': [
                    {'account_code': '5200', 'debit': amount, 'credit': 0, 'desc': 'مصروف عمولة الوكيل'},
                    {'account_code': '2100', 'debit': 0, 'credit': amount, 'desc': 'عمولة مستحقة للوكيل'}
                ]
            },
            'provider_payment': {
                'description': f'دفع مستحقات مزود - مبلغ {amount:,.2f} ريال',
                'entries': [
                    {'account_code': '2000', 'debit': amount, 'credit': 0, 'desc': 'تقليل مستحقات المزود'},
                    {'account_code': '1000', 'debit': 0, 'credit': amount, 'desc': 'دفع نقدي للمزود'}
                ]
            }
        }
        
        if transaction_type not in accounting_rules:
            logger.warning(f"نوع معاملة غير محاسبي: {transaction_type}")
            conn.close()
            return None
        
        rule = accounting_rules[transaction_type]
        entries = rule['entries']
        
        # حساب إجماليات المدين والدائن
        total_debit = sum(entry['debit'] for entry in entries)
        total_credit = sum(entry['credit'] for entry in entries)
        
        # التحقق من توازن القيد
        if abs(total_debit - total_credit) > 0.01:
            raise ValueError(f"القيد غير متوازن: مدين {total_debit} ≠ دائن {total_credit}")
        
        # إنشاء قيد اليومية الرئيسي
        cursor.execute('''
            INSERT INTO journal_entries 
            (entry_id, entry_date, description, reference_type, reference_id, 
             total_debit, total_credit, created_by, fiscal_year, fiscal_period)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            entry_id, entry_date, rule['description'], transaction_type, reference_id,
            total_debit, total_credit, user_id, entry_date.year, entry_date.month
        ))
        
        # إضافة إدخالات دفتر الأستاذ
        for entry in entries:
            # الحصول على معرف الحساب
            cursor.execute("SELECT id FROM chart_of_accounts WHERE account_code = ?", (entry['account_code'],))
            account_result = cursor.fetchone()
            
            if not account_result:
                raise ValueError(f"حساب غير موجود: {entry['account_code']}")
            
            account_id = account_result[0]
            
            # إضافة إلى دفتر الأستاذ العام
            cursor.execute('''
                INSERT INTO general_ledger
                (entry_id, transaction_date, account_id, debit_amount, credit_amount,
                 description, reference_type, reference_id, created_by, fiscal_year, fiscal_period)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                entry_id, entry_date, account_id, entry['debit'], entry['credit'],
                entry['desc'], transaction_type, reference_id, user_id,
                entry_date.year, entry_date.month
            ))
        
        # تسجيل في سجل التدقيق
        cursor.execute('''
            INSERT INTO accounting_audit_trail
            (action_type, table_name, record_id, new_values, user_id, user_role, description)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            'CREATE', 'journal_entries', cursor.lastrowid,
            json.dumps({'entry_id': entry_id, 'amount': amount, 'type': transaction_type}),
            user_id, 'system', f"إنشاء قيد محاسبي: {transaction_type}"
        ))
        
        conn.commit()
        conn.close()
        
        logger.info(f"تم إنشاء قيد محاسبي: {entry_id} للمعاملة {transaction_type}")
        return entry_id
        
    except Exception as e:
        conn.rollback()
        conn.close()
        logger.error(f"خطأ في إنشاء القيد المحاسبي: {e}")
        raise

def get_trial_balance(as_of_date: str = None):
    """إنشاء ميزان المراجعة"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    date_filter = ""
    params = []
    
    if as_of_date:
        date_filter = "AND gl.transaction_date <= ?"
        params.append(as_of_date)
    
    cursor.execute(f'''
        SELECT 
            coa.account_code,
            coa.account_name,
            coa.account_type,
            COALESCE(SUM(gl.debit_amount), 0) as total_debit,
            COALESCE(SUM(gl.credit_amount), 0) as total_credit
        FROM chart_of_accounts coa
        LEFT JOIN general_ledger gl ON coa.id = gl.account_id {date_filter}
        WHERE coa.is_active = 1
        GROUP BY coa.id, coa.account_code, coa.account_name, coa.account_type
        HAVING (total_debit > 0 OR total_credit > 0)
        ORDER BY coa.account_code
    ''', params)
    
    results = cursor.fetchall()
    conn.close()
    
    trial_balance = []
    grand_total_debit = 0
    grand_total_credit = 0
    
    for account_code, name, acc_type, debit, credit in results:
        # حساب الرصيد حسب نوع الحساب
        if acc_type in ['asset', 'expense']:
            balance = debit - credit
            balance_type = 'debit' if balance >= 0 else 'credit'
            balance_amount = abs(balance)
        else:
            balance = credit - debit
            balance_type = 'credit' if balance >= 0 else 'debit'
            balance_amount = abs(balance)
        
        trial_balance.append({
            'account_code': account_code,
            'account_name': name,
            'account_type': acc_type,
            'debit_total': debit,
            'credit_total': credit,
            'balance_amount': balance_amount,
            'balance_type': balance_type
        })
        
        if balance_type == 'debit':
            grand_total_debit += balance_amount
        else:
            grand_total_credit += balance_amount
    
    return {
        'accounts': trial_balance,
        'totals': {
            'total_debit': grand_total_debit,
            'total_credit': grand_total_credit,
            'is_balanced': abs(grand_total_debit - grand_total_credit) < 0.01
        },
        'as_of_date': as_of_date or datetime.now().date().isoformat()
    }

def get_income_statement(start_date: str = None, end_date: str = None):
    """إنشاء قائمة الأرباح والخسائر"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # تحديد الفترة
    if not start_date:
        start_date = f"{datetime.now().year}-01-01"
    if not end_date:
        end_date = datetime.now().date().isoformat()
    
    # الإيرادات
    cursor.execute('''
        SELECT 
            coa.account_code,
            coa.account_name,
            COALESCE(SUM(gl.credit_amount - gl.debit_amount), 0) as net_amount
        FROM chart_of_accounts coa
        LEFT JOIN general_ledger gl ON coa.id = gl.account_id
        WHERE coa.account_type = 'revenue' 
        AND gl.transaction_date BETWEEN ? AND ?
        GROUP BY coa.id, coa.account_code, coa.account_name
        ORDER BY coa.account_code
    ''', (start_date, end_date))
    
    revenues = cursor.fetchall()
    total_revenue = sum(amount for _, _, amount in revenues)
    
    # المصروفات
    cursor.execute('''
        SELECT 
            coa.account_code,
            coa.account_name,
            COALESCE(SUM(gl.debit_amount - gl.credit_amount), 0) as net_amount
        FROM chart_of_accounts coa
        LEFT JOIN general_ledger gl ON coa.id = gl.account_id
        WHERE coa.account_type = 'expense'
        AND gl.transaction_date BETWEEN ? AND ?
        GROUP BY coa.id, coa.account_code, coa.account_name
        ORDER BY coa.account_code
    ''', (start_date, end_date))
    
    expenses = cursor.fetchall()
    total_expenses = sum(amount for _, _, amount in expenses)
    
    conn.close()
    
    net_income = total_revenue - total_expenses
    
    return {
        'period': {'start_date': start_date, 'end_date': end_date},
        'revenues': [{'code': code, 'name': name, 'amount': amount} for code, name, amount in revenues],
        'expenses': [{'code': code, 'name': name, 'amount': amount} for code, name, amount in expenses],
        'totals': {
            'total_revenue': total_revenue,
            'total_expenses': total_expenses,
            'net_income': net_income
        }
    }

def get_balance_sheet(as_of_date: str = None):
    """إنشاء الميزانية العمومية"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if not as_of_date:
        as_of_date = datetime.now().date().isoformat()
    
    balance_sheet = {}
    
    # الأصول
    cursor.execute('''
        SELECT 
            coa.account_code,
            coa.account_name,
            COALESCE(SUM(gl.debit_amount - gl.credit_amount), 0) as balance
        FROM chart_of_accounts coa
        LEFT JOIN general_ledger gl ON coa.id = gl.account_id
        WHERE coa.account_type = 'asset' 
        AND gl.transaction_date <= ?
        GROUP BY coa.id, coa.account_code, coa.account_name
        HAVING balance != 0
        ORDER BY coa.account_code
    ''', (as_of_date,))
    
    assets = cursor.fetchall()
    total_assets = sum(balance for _, _, balance in assets)
    
    # الخصوم
    cursor.execute('''
        SELECT 
            coa.account_code,
            coa.account_name,
            COALESCE(SUM(gl.credit_amount - gl.debit_amount), 0) as balance
        FROM chart_of_accounts coa
        LEFT JOIN general_ledger gl ON coa.id = gl.account_id
        WHERE coa.account_type = 'liability'
        AND gl.transaction_date <= ?
        GROUP BY coa.id, coa.account_code, coa.account_name
        HAVING balance != 0
        ORDER BY coa.account_code
    ''', (as_of_date,))
    
    liabilities = cursor.fetchall()
    total_liabilities = sum(balance for _, _, balance in liabilities)
    
    # حقوق الملكية
    cursor.execute('''
        SELECT 
            coa.account_code,
            coa.account_name,
            COALESCE(SUM(gl.credit_amount - gl.debit_amount), 0) as balance
        FROM chart_of_accounts coa
        LEFT JOIN general_ledger gl ON coa.id = gl.account_id
        WHERE coa.account_type = 'equity'
        AND gl.transaction_date <= ?
        GROUP BY coa.id, coa.account_code, coa.account_name
        HAVING balance != 0
        ORDER BY coa.account_code
    ''', (as_of_date,))
    
    equity = cursor.fetchall()
    total_equity = sum(balance for _, _, balance in equity)
    
    conn.close()
    
    return {
        'as_of_date': as_of_date,
        'assets': [{'code': code, 'name': name, 'amount': amount} for code, name, amount in assets],
        'liabilities': [{'code': code, 'name': name, 'amount': amount} for code, name, amount in liabilities],
        'equity': [{'code': code, 'name': name, 'amount': amount} for code, name, amount in equity],
        'totals': {
            'total_assets': total_assets,
            'total_liabilities': total_liabilities,
            'total_equity': total_equity,
            'is_balanced': abs(total_assets - (total_liabilities + total_equity)) < 0.01
        }
    }

def process_bot_transaction_accounting(transaction_id: int):
    """معالجة محاسبية لمعاملة البوت"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # الحصول على تفاصيل المعاملة
        cursor.execute('''
            SELECT id, from_user, to_user, amount, type, description, created_at
            FROM transactions 
            WHERE id = ?
        ''', (transaction_id,))
        
        transaction = cursor.fetchone()
        if not transaction:
            conn.close()
            return None
        
        trans_id, from_user, to_user, amount, trans_type, description, created_at = transaction
        
        # تحديد المستخدم المنشئ للقيد
        created_by = from_user or to_user or 1
        
        # إنشاء القيد المحاسبي
        entry_id = create_accounting_entry(
            transaction_type=trans_type,
            amount=float(amount),
            user_id=created_by,
            reference_id=trans_id
        )
        
        # تحديث المعاملة بمعرف القيد المحاسبي
        cursor.execute('''
            UPDATE transactions 
            SET description = COALESCE(description, '') || ' [محاسبي: ' || ? || ']'
            WHERE id = ?
        ''', (entry_id, trans_id))
        
        conn.commit()
        conn.close()
        
        logger.info(f"تم ربط المعاملة {trans_id} بالقيد المحاسبي {entry_id}")
        return entry_id
        
    except Exception as e:
        logger.error(f"خطأ في معالجة المعاملة المحاسبية: {e}")
        return None

def update_user_balance_accounting(user_id: int, old_balance: float, new_balance: float, reason: str):
    """تحديث محاسبي لرصيد المستخدم"""
    try:
        balance_change = new_balance - old_balance
        
        if abs(balance_change) < 0.01:
            return  # لا يوجد تغيير معتبر
        
        # تحديد نوع المعاملة حسب السبب
        if 'كوبون' in reason:
            transaction_type = 'coupon_redeem'
        elif 'تحويل' in reason:
            transaction_type = 'transfer'
        elif 'شراء' in reason:
            transaction_type = 'card_purchase'
        else:
            transaction_type = 'balance_adjustment'
        
        # إنشاء قيد محاسبي لتغيير الرصيد
        if balance_change > 0:
            # زيادة في الرصيد
            create_accounting_entry(
                transaction_type=transaction_type,
                amount=abs(balance_change),
                user_id=user_id,
                additional_data={'reason': reason}
            )
        else:
            # نقص في الرصيد
            create_accounting_entry(
                transaction_type=transaction_type,
                amount=abs(balance_change),
                user_id=user_id,
                additional_data={'reason': reason}
            )
        
        logger.info(f"تم تحديث المحاسبة لرصيد المستخدم {user_id}: {balance_change:+.2f}")
        
    except Exception as e:
        logger.error(f"خطأ في تحديث محاسبة الرصيد: {e}")

if __name__ == "__main__":
    # اختبار النظام
    print("🧪 اختبار النظام المحاسبي...")
    
    # اختبار ميزان المراجعة
    trial_balance = get_trial_balance()
    print(f"📊 ميزان المراجعة: {len(trial_balance['accounts'])} حساب")
    print(f"⚖️ متوازن: {'نعم' if trial_balance['totals']['is_balanced'] else 'لا'}")
    
    # اختبار قائمة الأرباح والخسائر
    income_statement = get_income_statement()
    print(f"💰 صافي الدخل: {income_statement['totals']['net_income']:,.2f} ريال")
    
    print("✅ النظام المحاسبي يعمل بنجاح!")