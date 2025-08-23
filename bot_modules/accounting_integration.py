#!/usr/bin/env python3
"""
دمج النظام المحاسبي مع معاملات البوت + تصدير Excel
Integration of Accounting System with Bot Transactions + Excel Export
"""

import sqlite3
import logging
from datetime import datetime
from decimal import Decimal
import uuid
import json
import pandas as pd
import os
from io import BytesIO

logger = logging.getLogger(__name__)

def get_db_connection():
    """الحصول على اتصال قاعدة البيانات"""
    # احترام نفس المسار المستخدم في بقية المشروع
    db_path = os.getenv('DB_PATH', os.path.abspath('yemen_net.db'))
    conn = sqlite3.connect(db_path, timeout=30.0)
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
        
        # الحصول على بيانات إضافية أو استخدام القيم الافتراضية
        cost_percentage = 0.8  # افتراضي 80%
        commission_percentage = 0.05  # افتراضي 5%
        
        if additional_data:
            cost_percentage = additional_data.get('cost_percentage', 0.8)
            commission_percentage = additional_data.get('commission_percentage', 0.05)
            custom_description = additional_data.get('description', '')
        else:
            custom_description = ''
        
        # حساب التكلفة والعمولة بناءً على البيانات الإضافية
        cost_amount = amount * cost_percentage
        commission_amount = amount * commission_percentage
        
        # قواعد القيد المزدوج حسب نوع المعاملة
        accounting_rules = {
            'card_purchase': {
                'description': custom_description or f'شراء كرت إنترنت - مبلغ {amount:,.2f} ريال',
                'entries': [
                    {'account_code': '1000', 'debit': amount, 'credit': 0, 'desc': 'استلام نقدية من العميل'},
                    {'account_code': '4000', 'debit': 0, 'credit': amount, 'desc': 'إيراد بيع كرت إنترنت'},
                    {'account_code': '5000', 'debit': cost_amount, 'credit': 0, 'desc': 'تكلفة الكرت المباع'},
                    {'account_code': '2000', 'debit': 0, 'credit': cost_amount, 'desc': 'مستحق للمزود'}
                ]
            },
            'coupon_redeem': {
                'description': custom_description or f'شحن رصيد بكوبون - مبلغ {amount:,.2f} ريال',
                'entries': [
                    {'account_code': '1100', 'debit': amount, 'credit': 0, 'desc': 'زيادة رصيد محفظة العميل'},
                    {'account_code': '1000', 'debit': 0, 'credit': amount, 'desc': 'تقليل النقدية (قيمة الكوبون)'}
                ]
            },
            'transfer': {
                'description': custom_description or f'تحويل رصيد بين العملاء - مبلغ {amount:,.2f} ريال',
                'entries': [
                    {'account_code': '1100', 'debit': amount, 'credit': 0, 'desc': 'زيادة رصيد المستلم'},
                    {'account_code': '1100', 'debit': 0, 'credit': amount, 'desc': 'تقليل رصيد المرسل'}
                ]
            },
            'agent_commission': {
                'description': custom_description or f'عمولة وكيل - مبلغ {commission_amount:,.2f} ريال',
                'entries': [
                    {'account_code': '5200', 'debit': commission_amount, 'credit': 0, 'desc': 'مصروف عمولة الوكيل'},
                    {'account_code': '2100', 'debit': 0, 'credit': commission_amount, 'desc': 'عمولة مستحقة للوكيل'}
                ]
            },
            'supplier_payment': {
                'description': custom_description or f'دفع مستحقات مزود - مبلغ {amount:,.2f} ريال',
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
        
        # تسجيل البيانات الإضافية إذا كانت موجودة
        if additional_data:
            try:
                cursor.execute('''
                    INSERT INTO accounting_audit_trail 
                    (entry_id, action_type, action_details, created_by, created_at)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    entry_id, 'additional_data', str(additional_data), user_id, datetime.now()
                ))
                logger.info(f"تم تسجيل البيانات الإضافية للقيد: {entry_id}")
            except Exception as audit_e:
                logger.warning(f"فشل في تسجيل البيانات الإضافية: {audit_e}")
        
        conn.commit()
        conn.close()
        
        logger.info(f"تم إنشاء قيد محاسبي: {entry_id} مع بيانات إضافية: {bool(additional_data)}")
        return entry_id
        
    except Exception as e:
        conn.rollback()
        conn.close()
        logger.error(f"خطأ في إنشاء القيد المحاسبي: {e}")
        raise

def export_trial_balance_to_excel(as_of_date: str = None, filename: str = None) -> str:
    """تصدير ميزان المراجعة إلى Excel"""
    try:
        if not filename:
            date_str = as_of_date or datetime.now().strftime('%Y-%m-%d')
            filename = f"trial_balance_{date_str}.xlsx"
        
        # الحصول على بيانات ميزان المراجعة
        trial_balance = get_trial_balance(as_of_date)
        
        # إنشاء DataFrame
        df_data = []
        for account in trial_balance['accounts']:
            df_data.append({
                'رقم الحساب': account['account_code'],
                'اسم الحساب': account['account_name'],
                'نوع الحساب': {
                    'asset': 'أصول',
                    'liability': 'خصوم', 
                    'equity': 'حقوق ملكية',
                    'revenue': 'إيرادات',
                    'expense': 'مصروفات'
                }.get(account['account_type'], account['account_type']),
                'إجمالي المدين': f"{account['debit_total']:,.2f}",
                'إجمالي الدائن': f"{account['credit_total']:,.2f}",
                'نوع الرصيد': 'مدين' if account['balance_type'] == 'debit' else 'دائن',
                'مبلغ الرصيد': f"{account['balance_amount']:,.2f}"
            })
        
        # إضافة الإجماليات
        df_data.append({
            'رقم الحساب': '',
            'اسم الحساب': 'الإجماليات',
            'نوع الحساب': '',
            'إجمالي المدين': f"{trial_balance['totals']['total_debit']:,.2f}",
            'إجمالي الدائن': f"{trial_balance['totals']['total_credit']:,.2f}",
            'نوع الرصيد': 'متوازن' if trial_balance['totals']['is_balanced'] else 'غير متوازن',
            'مبلغ الرصيد': '0.00'
        })
        
        df = pd.DataFrame(df_data)
        
        # إنشاء ملف Excel مع تنسيق
        filepath = f"/workspace/{filename}"
        with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
            # ميزان المراجعة
            df.to_excel(writer, sheet_name='ميزان المراجعة', index=False)
            
            # تنسيق بسيط للورقة
            worksheet = writer.sheets['ميزان المراجعة']
            
            # تعديل عرض الأعمدة
            worksheet.column_dimensions['A'].width = 15  # رقم الحساب
            worksheet.column_dimensions['B'].width = 30  # اسم الحساب
            worksheet.column_dimensions['C'].width = 15  # نوع الحساب
            worksheet.column_dimensions['D'].width = 15  # إجمالي المدين
            worksheet.column_dimensions['E'].width = 15  # إجمالي الدائن
            worksheet.column_dimensions['F'].width = 15  # نوع الرصيد
            worksheet.column_dimensions['G'].width = 15  # مبلغ الرصيد
        
        return filepath
        
    except Exception as e:
        logger.error(f"خطأ في تصدير ميزان المراجعة: {e}")
        raise

def export_income_statement_to_excel(start_date: str = None, end_date: str = None, filename: str = None) -> str:
    """تصدير قائمة الأرباح والخسائر إلى Excel"""
    try:
        if not filename:
            date_str = datetime.now().strftime('%Y-%m')
            filename = f"income_statement_{date_str}.xlsx"
        
        # الحصول على بيانات قائمة الأرباح والخسائر
        income_statement = get_income_statement(start_date, end_date)
        
        # إنشاء DataFrame للإيرادات
        revenues_data = []
        for revenue in income_statement['revenues']:
            revenues_data.append({
                'رقم الحساب': revenue['code'],
                'اسم الحساب': revenue['name'],
                'المبلغ': f"{revenue['amount']:,.2f}"
            })
        
        # إنشاء DataFrame للمصروفات
        expenses_data = []
        for expense in income_statement['expenses']:
            expenses_data.append({
                'رقم الحساب': expense['code'],
                'اسم الحساب': expense['name'],
                'المبلغ': f"{expense['amount']:,.2f}"
            })
        
        # إنشاء ملف Excel
        filepath = f"/workspace/{filename}"
        with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
            # ورقة الإيرادات
            if revenues_data:
                df_revenues = pd.DataFrame(revenues_data)
                df_revenues.to_excel(writer, sheet_name='الإيرادات', index=False)
            
            # ورقة المصروفات
            if expenses_data:
                df_expenses = pd.DataFrame(expenses_data)
                df_expenses.to_excel(writer, sheet_name='المصروفات', index=False)
            
            # ورقة الملخص
            summary_data = [
                {'البيان': 'إجمالي الإيرادات', 'المبلغ': f"{income_statement['totals']['total_revenue']:,.2f}"},
                {'البيان': 'إجمالي المصروفات', 'المبلغ': f"{income_statement['totals']['total_expenses']:,.2f}"},
                {'البيان': 'صافي الدخل', 'المبلغ': f"{income_statement['totals']['net_income']:,.2f}"}
            ]
            
            df_summary = pd.DataFrame(summary_data)
            df_summary.to_excel(writer, sheet_name='الملخص', index=False)
        
        return filepath
        
    except Exception as e:
        logger.error(f"خطأ في تصدير قائمة الأرباح والخسائر: {e}")
        raise

def export_balance_sheet_to_excel(as_of_date: str = None, filename: str = None) -> str:
    """تصدير الميزانية العمومية إلى Excel"""
    try:
        if not filename:
            date_str = as_of_date or datetime.now().strftime('%Y-%m-%d')
            filename = f"balance_sheet_{date_str}.xlsx"
        
        # الحصول على بيانات الميزانية العمومية
        balance_sheet = get_balance_sheet(as_of_date)
        
        # إنشاء DataFrame
        all_data = []
        
        # الأصول
        all_data.append({'البيان': 'الأصول', 'المبلغ': '', 'النوع': 'header'})
        for asset in balance_sheet['assets']:
            all_data.append({
                'البيان': f"  {asset['name']} ({asset['code']})",
                'المبلغ': f"{asset['amount']:,.2f}",
                'النوع': 'asset'
            })
        all_data.append({'البيان': 'إجمالي الأصول', 'المبلغ': f"{balance_sheet['totals']['total_assets']:,.2f}", 'النوع': 'total'})
        
        # الخصوم
        all_data.append({'البيان': '', 'المبلغ': '', 'النوع': 'spacer'})
        all_data.append({'البيان': 'الخصوم', 'المبلغ': '', 'النوع': 'header'})
        for liability in balance_sheet['liabilities']:
            all_data.append({
                'البيان': f"  {liability['name']} ({liability['code']})",
                'المبلغ': f"{liability['amount']:,.2f}",
                'النوع': 'liability'
            })
        all_data.append({'البيان': 'إجمالي الخصوم', 'المبلغ': f"{balance_sheet['totals']['total_liabilities']:,.2f}", 'النوع': 'total'})
        
        # حقوق الملكية
        all_data.append({'البيان': '', 'المبلغ': '', 'النوع': 'spacer'})
        all_data.append({'البيان': 'حقوق الملكية', 'المبلغ': '', 'النوع': 'header'})
        for equity in balance_sheet['equity']:
            all_data.append({
                'البيان': f"  {equity['name']} ({equity['code']})",
                'المبلغ': f"{equity['amount']:,.2f}",
                'النوع': 'equity'
            })
        all_data.append({'البيان': 'إجمالي حقوق الملكية', 'المبلغ': f"{balance_sheet['totals']['total_equity']:,.2f}", 'النوع': 'total'})
        
        df = pd.DataFrame(all_data)
        
        # إنشاء ملف Excel
        filepath = f"/workspace/{filename}"
        with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
            df[['البيان', 'المبلغ']].to_excel(writer, sheet_name='الميزانية العمومية', index=False)
        
        return filepath
        
    except Exception as e:
        logger.error(f"خطأ في تصدير الميزانية العمومية: {e}")
        raise

def export_general_ledger_to_excel(account_code: str = None, start_date: str = None, 
                                 end_date: str = None, filename: str = None) -> str:
    """تصدير دفتر الأستاذ العام إلى Excel"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # بناء الاستعلام
        where_conditions = []
        params = []
        
        if account_code:
            where_conditions.append("coa.account_code = ?")
            params.append(account_code)
        
        if start_date:
            where_conditions.append("gl.transaction_date >= ?")
            params.append(start_date)
        
        if end_date:
            where_conditions.append("gl.transaction_date <= ?")
            params.append(end_date)
        
        where_clause = ""
        if where_conditions:
            where_clause = "WHERE " + " AND ".join(where_conditions)
        
        cursor.execute(f'''
            SELECT 
                gl.entry_id,
                gl.transaction_date,
                coa.account_code,
                coa.account_name,
                gl.description,
                gl.debit_amount,
                gl.credit_amount,
                gl.reference_type,
                gl.reference_id
            FROM general_ledger gl
            JOIN chart_of_accounts coa ON gl.account_id = coa.id
            {where_clause}
            ORDER BY gl.transaction_date DESC, gl.entry_id, coa.account_code
        ''', params)
        
        results = cursor.fetchall()
        conn.close()
        
        # إنشاء DataFrame
        df_data = []
        for row in results:
            entry_id, trans_date, acc_code, acc_name, desc, debit, credit, ref_type, ref_id = row
            df_data.append({
                'التاريخ': trans_date,
                'رقم القيد': entry_id,
                'رقم الحساب': acc_code,
                'اسم الحساب': acc_name,
                'البيان': desc,
                'مدين': f"{debit:,.2f}" if debit > 0 else "",
                'دائن': f"{credit:,.2f}" if credit > 0 else "",
                'نوع المرجع': ref_type or "",
                'رقم المرجع': ref_id or ""
            })
        
        df = pd.DataFrame(df_data)
        
        # تحديد اسم الملف
        if not filename:
            date_str = datetime.now().strftime('%Y-%m-%d')
            account_str = f"_{account_code}" if account_code else ""
            filename = f"general_ledger{account_str}_{date_str}.xlsx"
        
        # إنشاء ملف Excel
        filepath = f"/workspace/{filename}"
        with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='دفتر الأستاذ العام', index=False)
            
            # تنسيق بسيط للورقة
            worksheet = writer.sheets['دفتر الأستاذ العام']
            
            # تعديل عرض الأعمدة
            worksheet.column_dimensions['A'].width = 12  # التاريخ
            worksheet.column_dimensions['B'].width = 20  # رقم القيد
            worksheet.column_dimensions['C'].width = 12  # رقم الحساب
            worksheet.column_dimensions['D'].width = 30  # اسم الحساب
            worksheet.column_dimensions['E'].width = 25  # البيان
            worksheet.column_dimensions['F'].width = 15  # مدين
            worksheet.column_dimensions['G'].width = 15  # دائن
        
        return filepath
        
    except Exception as e:
        logger.error(f"خطأ في تصدير دفتر الأستاذ العام: {e}")
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
        ORDER BY coa.account_code
    ''', params)
    
    results = cursor.fetchall()
    conn.close()
    
    trial_balance = []
    total_debits = 0
    total_credits = 0
    
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
            total_debits += balance_amount
        else:
            total_credits += balance_amount
    
    return {
        'accounts': trial_balance,
        'totals': {
            'total_debit': total_debits,
            'total_credit': total_credits,
            'is_balanced': abs(total_debits - total_credits) < 0.01
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

def export_complete_accounting_package(filename_prefix: str = None) -> dict:
    """تصدير حزمة محاسبية كاملة (جميع التقارير)"""
    try:
        if not filename_prefix:
            filename_prefix = f"accounting_package_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        exported_files = {}
        
        # 1. ميزان المراجعة
        trial_balance_file = export_trial_balance_to_excel(filename=f"{filename_prefix}_trial_balance.xlsx")
        exported_files['trial_balance'] = trial_balance_file
        
        # 2. قائمة الأرباح والخسائر
        income_statement_file = export_income_statement_to_excel(filename=f"{filename_prefix}_income_statement.xlsx")
        exported_files['income_statement'] = income_statement_file
        
        # 3. الميزانية العمومية
        balance_sheet_file = export_balance_sheet_to_excel(filename=f"{filename_prefix}_balance_sheet.xlsx")
        exported_files['balance_sheet'] = balance_sheet_file
        
        # 4. دفتر الأستاذ العام
        general_ledger_file = export_general_ledger_to_excel(filename=f"{filename_prefix}_general_ledger.xlsx")
        exported_files['general_ledger'] = general_ledger_file
        
        return {
            'success': True,
            'files': exported_files,
            'package_name': filename_prefix,
            'exported_at': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"خطأ في تصدير الحزمة المحاسبية: {e}")
        return {
            'success': False,
            'error': str(e),
            'exported_at': datetime.now().isoformat()
        }

if __name__ == "__main__":
    # اختبار تصدير التقارير
    print("🧪 اختبار تصدير التقارير المحاسبية...")
    
    try:
        # تصدير ميزان المراجعة
        trial_file = export_trial_balance_to_excel()
        print(f"✅ ميزان المراجعة: {trial_file}")
        
        # تصدير قائمة الأرباح والخسائر
        income_file = export_income_statement_to_excel()
        print(f"✅ قائمة الأرباح والخسائر: {income_file}")
        
        # تصدير الميزانية العمومية
        balance_file = export_balance_sheet_to_excel()
        print(f"✅ الميزانية العمومية: {balance_file}")
        
        print("🎉 تم تصدير جميع التقارير بنجاح!")
        
    except Exception as e:
        print(f"❌ خطأ في الاختبار: {e}")