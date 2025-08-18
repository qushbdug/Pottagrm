#!/usr/bin/env python3
"""
نظام محاسبي مزدوج القيود لبوت بيع كروت الإنترنت
Double-Entry Accounting System for Internet Cards Bot
"""

import sqlite3
import logging
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Dict, Optional, Tuple
import uuid
import json

logger = logging.getLogger(__name__)

class AccountingSystem:
    """نظام المحاسبة مزدوج القيود"""
    
    def __init__(self, db_path: str = "yemen_net.db"):
        self.db_path = db_path
        self.init_accounting_tables()
        self.seed_chart_of_accounts()
    
    def get_connection(self):
        """الحصول على اتصال قاعدة البيانات"""
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        return conn
    
    def init_accounting_tables(self):
        """إنشاء جداول النظام المحاسبي"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # دليل الحسابات - Chart of Accounts
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chart_of_accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_code TEXT NOT NULL UNIQUE,
                account_name TEXT NOT NULL,
                account_type TEXT NOT NULL CHECK (account_type IN ('asset', 'liability', 'equity', 'revenue', 'expense')),
                parent_account_id INTEGER,
                currency TEXT DEFAULT 'YER',
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by INTEGER,
                description TEXT,
                FOREIGN KEY (parent_account_id) REFERENCES chart_of_accounts (id),
                FOREIGN KEY (created_by) REFERENCES users (id)
            )
        ''')
        
        # دفتر الأستاذ العام - General Ledger
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS general_ledger (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entry_id TEXT NOT NULL,
                transaction_date DATE NOT NULL,
                account_id INTEGER NOT NULL,
                debit_amount DECIMAL(15,6) DEFAULT 0,
                credit_amount DECIMAL(15,6) DEFAULT 0,
                description TEXT NOT NULL,
                reference_type TEXT,
                reference_id INTEGER,
                currency TEXT DEFAULT 'YER',
                exchange_rate DECIMAL(10,6) DEFAULT 1.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by INTEGER NOT NULL,
                fiscal_year INTEGER,
                fiscal_period INTEGER,
                is_reversed BOOLEAN DEFAULT 0,
                reversal_entry_id TEXT,
                audit_trail TEXT,
                FOREIGN KEY (account_id) REFERENCES chart_of_accounts (id),
                FOREIGN KEY (created_by) REFERENCES users (id),
                CHECK (debit_amount >= 0 AND credit_amount >= 0),
                CHECK (NOT (debit_amount > 0 AND credit_amount > 0))
            )
        ''')
        
        # قيود اليومية - Journal Entries
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS journal_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entry_id TEXT NOT NULL UNIQUE,
                entry_date DATE NOT NULL,
                description TEXT NOT NULL,
                reference_type TEXT,
                reference_id INTEGER,
                total_debit DECIMAL(15,6) NOT NULL,
                total_credit DECIMAL(15,6) NOT NULL,
                currency TEXT DEFAULT 'YER',
                status TEXT DEFAULT 'draft' CHECK (status IN ('draft', 'posted', 'reversed')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by INTEGER NOT NULL,
                posted_at TIMESTAMP,
                posted_by INTEGER,
                fiscal_year INTEGER,
                fiscal_period INTEGER,
                audit_trail TEXT,
                FOREIGN KEY (created_by) REFERENCES users (id),
                FOREIGN KEY (posted_by) REFERENCES users (id),
                CHECK (total_debit = total_credit)
            )
        ''')
        
        # تفاصيل القيود - Journal Entry Lines
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS journal_entry_lines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                journal_entry_id INTEGER NOT NULL,
                line_number INTEGER NOT NULL,
                account_id INTEGER NOT NULL,
                debit_amount DECIMAL(15,6) DEFAULT 0,
                credit_amount DECIMAL(15,6) DEFAULT 0,
                description TEXT,
                reference_type TEXT,
                reference_id INTEGER,
                currency TEXT DEFAULT 'YER',
                exchange_rate DECIMAL(10,6) DEFAULT 1.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (journal_entry_id) REFERENCES journal_entries (id) ON DELETE CASCADE,
                FOREIGN KEY (account_id) REFERENCES chart_of_accounts (id),
                CHECK (debit_amount >= 0 AND credit_amount >= 0),
                CHECK (NOT (debit_amount > 0 AND credit_amount > 0))
            )
        ''')
        
        # سجل التدقيق المحاسبي - Audit Trail
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS accounting_audit_trail (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action_type TEXT NOT NULL,
                table_name TEXT NOT NULL,
                record_id INTEGER,
                old_values TEXT,
                new_values TEXT,
                user_id INTEGER NOT NULL,
                user_role TEXT NOT NULL,
                ip_address TEXT,
                user_agent TEXT,
                session_id TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                description TEXT,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # التسويات - Reconciliations
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS reconciliations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_id INTEGER NOT NULL,
                reconciliation_date DATE NOT NULL,
                book_balance DECIMAL(15,6) NOT NULL,
                statement_balance DECIMAL(15,6) NOT NULL,
                difference DECIMAL(15,6) NOT NULL,
                status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'completed', 'disputed')),
                reconciled_by INTEGER,
                reconciled_at TIMESTAMP,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (account_id) REFERENCES chart_of_accounts (id),
                FOREIGN KEY (reconciled_by) REFERENCES users (id)
            )
        ''')
        
        # الفترات المحاسبية - Fiscal Periods
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS fiscal_periods (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fiscal_year INTEGER NOT NULL,
                period_number INTEGER NOT NULL,
                period_name TEXT NOT NULL,
                start_date DATE NOT NULL,
                end_date DATE NOT NULL,
                is_closed BOOLEAN DEFAULT 0,
                closed_by INTEGER,
                closed_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (closed_by) REFERENCES users (id),
                UNIQUE(fiscal_year, period_number)
            )
        ''')
        
        # إنشاء الفهارس للأداء
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_general_ledger_account_date ON general_ledger(account_id, transaction_date)",
            "CREATE INDEX IF NOT EXISTS idx_general_ledger_entry_id ON general_ledger(entry_id)",
            "CREATE INDEX IF NOT EXISTS idx_journal_entries_date ON journal_entries(entry_date)",
            "CREATE INDEX IF NOT EXISTS idx_journal_entries_status ON journal_entries(status)",
            "CREATE INDEX IF NOT EXISTS idx_audit_trail_timestamp ON accounting_audit_trail(timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_audit_trail_user ON accounting_audit_trail(user_id)",
        ]
        
        for index in indexes:
            cursor.execute(index)
        
        conn.commit()
        conn.close()
        logger.info("تم إنشاء جداول النظام المحاسبي بنجاح")
    
    def seed_chart_of_accounts(self):
        """إنشاء دليل الحسابات الأساسي"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # التحقق من وجود الحسابات
        cursor.execute("SELECT COUNT(*) FROM chart_of_accounts")
        if cursor.fetchone()[0] > 0:
            conn.close()
            return
        
        # دليل الحسابات الأساسي
        accounts = [
            # الأصول - Assets
            ("1000", "النقدية والنقد المعادل", "asset", None, "YER", "النقدية في الصندوق والبنك"),
            ("1100", "المبالغ المستحقة - محافظ العملاء", "asset", None, "YER", "أرصدة العملاء في المحافظ"),
            ("1200", "مخزون الكروت", "asset", None, "YER", "كروت الإنترنت غير المباعة"),
            ("1300", "المصروفات المدفوعة مقدماً", "asset", None, "YER", "مصروفات مدفوعة مسبقاً"),
            
            # الخصوم - Liabilities  
            ("2000", "مستحقات المزودين", "liability", None, "YER", "المبالغ المستحقة للمزودين"),
            ("2100", "عمولات الوكلاء المستحقة", "liability", None, "YER", "عمولات غير مدفوعة للوكلاء"),
            ("2200", "مستحقات أخرى", "liability", None, "YER", "التزامات أخرى"),
            
            # حقوق الملكية - Equity
            ("3000", "رأس المال", "equity", None, "YER", "رأس مال المشروع"),
            ("3100", "الأرباح المحتجزة", "equity", None, "YER", "أرباح محتجزة من فترات سابقة"),
            ("3200", "أرباح السنة الحالية", "equity", None, "YER", "صافي أرباح السنة الجارية"),
            
            # الإيرادات - Revenue
            ("4000", "إيرادات بيع كروت الإنترنت", "revenue", None, "YER", "إيرادات من بيع الكروت"),
            ("4100", "دخل العمولات", "revenue", None, "YER", "عمولات من الوكلاء والمزودين"),
            ("4200", "إيرادات أخرى", "revenue", None, "YER", "إيرادات متنوعة"),
            
            # المصروفات - Expenses
            ("5000", "تكلفة البضاعة المباعة - كروت", "expense", None, "YER", "تكلفة الكروت المباعة"),
            ("5100", "رسوم الدفع الإلكتروني", "expense", None, "YER", "رسوم بوابات الدفع"),
            ("5200", "مصروف عمولات الوكلاء", "expense", None, "YER", "عمولات مدفوعة للوكلاء"),
            ("5300", "مصروفات تشغيلية", "expense", None, "YER", "مصروفات التشغيل العامة"),
            ("5400", "مصروفات تقنية", "expense", None, "YER", "تكاليف الخوادم والتقنية"),
        ]
        
        for account_code, name, acc_type, parent, currency, description in accounts:
            cursor.execute('''
                INSERT OR IGNORE INTO chart_of_accounts 
                (account_code, account_name, account_type, parent_account_id, currency, description, created_by)
                VALUES (?, ?, ?, ?, ?, ?, 1)
            ''', (account_code, name, acc_type, parent, currency, description))
        
        conn.commit()
        conn.close()
        logger.info("تم إنشاء دليل الحسابات الأساسي")
    
    def create_journal_entry(self, description: str, entries: List[Dict], 
                           reference_type: str = None, reference_id: int = None, 
                           created_by: int = 1) -> str:
        """إنشاء قيد يومية مزدوج"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # إنشاء معرف فريد للقيد
            entry_id = f"JE-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8]}"
            entry_date = datetime.now().date()
            
            # حساب إجماليات المدين والدائن
            total_debit = sum(Decimal(str(entry.get('debit', 0))) for entry in entries)
            total_credit = sum(Decimal(str(entry.get('credit', 0))) for entry in entries)
            
            # التحقق من توازن القيد
            if total_debit != total_credit:
                raise ValueError(f"القيد غير متوازن: مدين {total_debit} ≠ دائن {total_credit}")
            
            # إنشاء قيد اليومية الرئيسي
            cursor.execute('''
                INSERT INTO journal_entries 
                (entry_id, entry_date, description, reference_type, reference_id, 
                 total_debit, total_credit, created_by, fiscal_year, fiscal_period, audit_trail)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                entry_id, entry_date, description, reference_type, reference_id,
                float(total_debit), float(total_credit), created_by,
                entry_date.year, entry_date.month,
                json.dumps({
                    'created_at': datetime.now().isoformat(),
                    'created_by': created_by,
                    'ip': 'bot_system',
                    'action': 'create_journal_entry'
                })
            ))
            
            journal_id = cursor.lastrowid
            
            # إضافة سطور القيد
            for i, entry in enumerate(entries, 1):
                account_code = entry['account']
                debit = Decimal(str(entry.get('debit', 0)))
                credit = Decimal(str(entry.get('credit', 0)))
                line_desc = entry.get('description', description)
                
                # الحصول على معرف الحساب
                cursor.execute("SELECT id FROM chart_of_accounts WHERE account_code = ?", (account_code,))
                account_result = cursor.fetchone()
                if not account_result:
                    raise ValueError(f"حساب غير موجود: {account_code}")
                
                account_id = account_result[0]
                
                # إضافة سطر القيد
                cursor.execute('''
                    INSERT INTO journal_entry_lines
                    (journal_entry_id, line_number, account_id, debit_amount, credit_amount, 
                     description, reference_type, reference_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (journal_id, i, account_id, float(debit), float(credit), 
                      line_desc, reference_type, reference_id))
                
                # إضافة إلى دفتر الأستاذ العام
                cursor.execute('''
                    INSERT INTO general_ledger
                    (entry_id, transaction_date, account_id, debit_amount, credit_amount,
                     description, reference_type, reference_id, created_by, fiscal_year, fiscal_period, audit_trail)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    entry_id, entry_date, account_id, float(debit), float(credit),
                    line_desc, reference_type, reference_id, created_by,
                    entry_date.year, entry_date.month,
                    json.dumps({
                        'entry_id': entry_id,
                        'line_number': i,
                        'account_code': account_code,
                        'created_at': datetime.now().isoformat()
                    })
                ))
            
            # تحديث حالة القيد إلى مرحل
            cursor.execute('''
                UPDATE journal_entries 
                SET status = 'posted', posted_at = CURRENT_TIMESTAMP, posted_by = ?
                WHERE id = ?
            ''', (created_by, journal_id))
            
            # تسجيل في سجل التدقيق
            self.log_audit_action('CREATE', 'journal_entries', journal_id, 
                                 {'entry_id': entry_id, 'description': description}, 
                                 created_by, conn)
            
            conn.commit()
            conn.close()
            
            logger.info(f"تم إنشاء قيد محاسبي: {entry_id}")
            return entry_id
            
        except Exception as e:
            conn.rollback()
            conn.close()
            logger.error(f"خطأ في إنشاء القيد المحاسبي: {e}")
            raise
    
    def log_audit_action(self, action: str, table: str, record_id: int, 
                        data: Dict, user_id: int, conn=None):
        """تسجيل إجراء في سجل التدقيق"""
        if conn is None:
            conn = self.get_connection()
            should_close = True
        else:
            should_close = False
        
        try:
            cursor = conn.cursor()
            
            # الحصول على دور المستخدم
            cursor.execute("SELECT role FROM users WHERE id = ?", (user_id,))
            user_result = cursor.fetchone()
            user_role = user_result[0] if user_result else 'unknown'
            
            cursor.execute('''
                INSERT INTO accounting_audit_trail
                (action_type, table_name, record_id, new_values, user_id, user_role, description)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (action, table, record_id, json.dumps(data), user_id, user_role, 
                  f"{action} في {table}"))
            
            if should_close:
                conn.commit()
                conn.close()
                
        except Exception as e:
            logger.error(f"خطأ في تسجيل التدقيق: {e}")
    
    def get_account_balance(self, account_code: str, as_of_date: str = None) -> Decimal:
        """الحصول على رصيد حساب معين"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # الحصول على معرف الحساب ونوعه
        cursor.execute('''
            SELECT id, account_type FROM chart_of_accounts WHERE account_code = ?
        ''', (account_code,))
        result = cursor.fetchone()
        
        if not result:
            conn.close()
            raise ValueError(f"حساب غير موجود: {account_code}")
        
        account_id, account_type = result
        
        # بناء استعلام الرصيد
        date_filter = ""
        params = [account_id]
        
        if as_of_date:
            date_filter = "AND transaction_date <= ?"
            params.append(as_of_date)
        
        cursor.execute(f'''
            SELECT 
                COALESCE(SUM(debit_amount), 0) as total_debit,
                COALESCE(SUM(credit_amount), 0) as total_credit
            FROM general_ledger 
            WHERE account_id = ? {date_filter}
        ''', params)
        
        debit_total, credit_total = cursor.fetchone()
        conn.close()
        
        # حساب الرصيد حسب نوع الحساب
        if account_type in ['asset', 'expense']:
            # الأصول والمصروفات: مدين موجب
            balance = Decimal(str(debit_total)) - Decimal(str(credit_total))
        else:
            # الخصوم والإيرادات وحقوق الملكية: دائن موجب
            balance = Decimal(str(credit_total)) - Decimal(str(debit_total))
        
        return balance
    
    def generate_trial_balance(self, as_of_date: str = None) -> List[Dict]:
        """إنشاء ميزان المراجعة"""
        conn = self.get_connection()
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
        total_debits = Decimal('0')
        total_credits = Decimal('0')
        
        for account_code, name, acc_type, debit, credit in results:
            debit_decimal = Decimal(str(debit))
            credit_decimal = Decimal(str(credit))
            
            # حساب الرصيد حسب نوع الحساب
            if acc_type in ['asset', 'expense']:
                balance = debit_decimal - credit_decimal
                balance_type = 'debit' if balance >= 0 else 'credit'
                balance_amount = abs(balance)
            else:
                balance = credit_decimal - debit_decimal
                balance_type = 'credit' if balance >= 0 else 'debit'
                balance_amount = abs(balance)
            
            if balance_amount > 0:  # إظهار الحسابات التي لها رصيد فقط
                trial_balance.append({
                    'account_code': account_code,
                    'account_name': name,
                    'account_type': acc_type,
                    'balance_amount': float(balance_amount),
                    'balance_type': balance_type,
                    'total_debit': float(debit_decimal),
                    'total_credit': float(credit_decimal)
                })
                
                if balance_type == 'debit':
                    total_debits += balance_amount
                else:
                    total_credits += balance_amount
        
        # إضافة الإجماليات
        trial_balance.append({
            'account_code': 'TOTAL',
            'account_name': 'الإجماليات',
            'account_type': 'total',
            'balance_amount': 0,
            'balance_type': 'balanced',
            'total_debit': float(total_debits),
            'total_credit': float(total_credits)
        })
        
        return trial_balance

# قواعد القيد المزدوج للمعاملات
DOUBLE_ENTRY_RULES = {
    'card_purchase': {
        'description': 'شراء كرت إنترنت',
        'entries': [
            {'account': '1000', 'debit': 'amount', 'description': 'استلام نقدية من العميل'},
            {'account': '4000', 'credit': 'amount', 'description': 'إيراد بيع كرت إنترنت'}
        ]
    },
    'card_cost': {
        'description': 'تكلفة الكرت المباع',
        'entries': [
            {'account': '5000', 'debit': 'cost', 'description': 'تكلفة الكرت المباع'},
            {'account': '2000', 'credit': 'cost', 'description': 'مستحق للمزود'}
        ]
    },
    'agent_commission': {
        'description': 'عمولة الوكيل',
        'entries': [
            {'account': '5200', 'debit': 'commission', 'description': 'مصروف عمولة الوكيل'},
            {'account': '2100', 'credit': 'commission', 'description': 'عمولة مستحقة للوكيل'}
        ]
    },
    'coupon_redeem': {
        'description': 'شحن رصيد بكوبون',
        'entries': [
            {'account': '1100', 'debit': 'amount', 'description': 'زيادة رصيد محفظة العميل'},
            {'account': '1000', 'credit': 'amount', 'description': 'تقليل النقدية (قيمة الكوبون)'}
        ]
    },
    'transfer_balance': {
        'description': 'تحويل رصيد بين العملاء',
        'entries': [
            {'account': '1100', 'debit': 'amount', 'description': 'زيادة رصيد المستلم'},
            {'account': '1100', 'credit': 'amount', 'description': 'تقليل رصيد المرسل'}
        ]
    },
    'provider_payment': {
        'description': 'دفع مستحقات المزود',
        'entries': [
            {'account': '2000', 'debit': 'amount', 'description': 'تقليل مستحقات المزود'},
            {'account': '1000', 'credit': 'amount', 'description': 'دفع نقدي للمزود'}
        ]
    },
    'agent_commission_payment': {
        'description': 'دفع عمولة الوكيل',
        'entries': [
            {'account': '2100', 'debit': 'amount', 'description': 'تقليل عمولة مستحقة'},
            {'account': '1000', 'credit': 'amount', 'description': 'دفع نقدي للوكيل'}
        ]
    }
}

def process_transaction_accounting(transaction_type: str, amount: float, 
                                 reference_id: int, created_by: int, 
                                 additional_data: Dict = None):
    """معالجة محاسبية للمعاملة"""
    try:
        accounting = AccountingSystem()
        
        if transaction_type not in DOUBLE_ENTRY_RULES:
            logger.warning(f"نوع معاملة غير محاسبي: {transaction_type}")
            return None
        
        rule = DOUBLE_ENTRY_RULES[transaction_type]
        entries = []
        
        for entry_rule in rule['entries']:
            entry = {
                'account': entry_rule['account'],
                'description': entry_rule['description']
            }
            
            # حساب المبلغ
            if entry_rule.get('debit'):
                if entry_rule['debit'] == 'amount':
                    entry['debit'] = amount
                elif entry_rule['debit'] == 'cost' and additional_data:
                    entry['debit'] = additional_data.get('cost', amount * 0.8)  # افتراضي 80%
                elif entry_rule['debit'] == 'commission' and additional_data:
                    entry['debit'] = additional_data.get('commission', amount * 0.05)  # افتراضي 5%
            
            if entry_rule.get('credit'):
                if entry_rule['credit'] == 'amount':
                    entry['credit'] = amount
                elif entry_rule['credit'] == 'cost' and additional_data:
                    entry['credit'] = additional_data.get('cost', amount * 0.8)
                elif entry_rule['credit'] == 'commission' and additional_data:
                    entry['credit'] = additional_data.get('commission', amount * 0.05)
            
            entries.append(entry)
        
        # إنشاء القيد المحاسبي
        entry_id = accounting.create_journal_entry(
            description=f"{rule['description']} - معاملة #{reference_id}",
            entries=entries,
            reference_type=transaction_type,
            reference_id=reference_id,
            created_by=created_by
        )
        
        logger.info(f"تم إنشاء قيد محاسبي: {entry_id} للمعاملة {reference_id}")
        return entry_id
        
    except Exception as e:
        logger.error(f"خطأ في المعالجة المحاسبية: {e}")
        return None

if __name__ == "__main__":
    # اختبار النظام
    accounting = AccountingSystem()
    print("✅ تم إنشاء النظام المحاسبي بنجاح")
    
    # اختبار ميزان المراجعة
    trial_balance = accounting.generate_trial_balance()
    print(f"📊 ميزان المراجعة: {len(trial_balance)} حساب")