#!/usr/bin/env python3
"""
Constraints System - نظام القيود القوي
نظام شامل للقيود والتحقق من صحة العمليات والبيانات
"""

import logging
import sqlite3
import re
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from enum import Enum
from bot_modules.database import get_db_connection
from bot_modules.config import EMOJIS

logger = logging.getLogger(__name__)

class ConstraintType(Enum):
    """أنواع القيود"""
    BALANCE = "balance"           # قيود الرصيد
    AMOUNT = "amount"             # قيود المبالغ
    TIME = "time"                 # قيود الوقت
    FREQUENCY = "frequency"       # قيود التكرار
    ROLE = "role"                 # قيود الأدوار
    STATUS = "status"             # قيود الحالة
    RELATIONSHIP = "relationship" # قيود العلاقات
    BUSINESS = "business"         # قيود الأعمال

class ConstraintSeverity(Enum):
    """مستويات خطورة انتهاك القيود"""
    INFO = "info"         # معلوماتي
    WARNING = "warning"   # تحذير
    ERROR = "error"       # خطأ
    CRITICAL = "critical" # حرج

class ConstraintsSystem:
    """نظام القيود الشامل"""
    
    def __init__(self):
        self.constraints = {}
        self.violations_log = []
        self._initialize_default_constraints()
    
    def _initialize_default_constraints(self):
        """تهيئة القيود الافتراضية"""
        
        # قيود الرصيد
        self.add_constraint(
            "minimum_balance",
            ConstraintType.BALANCE,
            ConstraintSeverity.ERROR,
            lambda user_balance: user_balance >= 0,
            "الرصيد لا يمكن أن يكون سالباً",
            "تأكد من كفاية الرصيد قبل العملية"
        )
        
        self.add_constraint(
            "maximum_balance",
            ConstraintType.BALANCE,
            ConstraintSeverity.WARNING,
            lambda user_balance: user_balance <= 1000000,
            "الرصيد أكبر من الحد الأقصى المسموح (1,000,000 ريال)",
            "راجع مصدر هذا الرصيد الكبير"
        )
        
        # قيود المبالغ
        self.add_constraint(
            "minimum_transfer_amount",
            ConstraintType.AMOUNT,
            ConstraintSeverity.ERROR,
            lambda amount: amount >= 1,
            "الحد الأدنى للتحويل هو 1 ريال",
            "أدخل مبلغاً أكبر من 1 ريال"
        )
        
        self.add_constraint(
            "maximum_transfer_amount",
            ConstraintType.AMOUNT,
            ConstraintSeverity.WARNING,
            lambda amount: amount <= 50000,
            "مبلغ التحويل كبير جداً (أكثر من 50,000 ريال)",
            "تأكد من صحة المبلغ أو قسمه على دفعات"
        )
        
        self.add_constraint(
            "maximum_single_purchase",
            ConstraintType.AMOUNT,
            ConstraintSeverity.WARNING,
            lambda amount: amount <= 10000,
            "مبلغ الشراء كبير جداً (أكثر من 10,000 ريال)",
            "تأكد من صحة قيمة البطاقة"
        )
        
        # قيود التكرار
        self.add_constraint(
            "max_transfers_per_hour",
            ConstraintType.FREQUENCY,
            ConstraintSeverity.WARNING,
            lambda user_id: self._check_transfer_frequency(user_id, 1, 10),
            "تجاوز الحد الأقصى للتحويلات (10 تحويلات/ساعة)",
            "انتظر قليلاً قبل إجراء تحويل آخر"
        )
        
        self.add_constraint(
            "max_purchases_per_day",
            ConstraintType.FREQUENCY,
            ConstraintSeverity.WARNING,
            lambda user_id: self._check_purchase_frequency(user_id, 24, 20),
            "تجاوز الحد الأقصى للمشتريات (20 شراء/يوم)",
            "انتظر حتى الغد أو تواصل مع الدعم"
        )
        
        # قيود الأدوار
        self.add_constraint(
            "supplier_can_sell",
            ConstraintType.ROLE,
            ConstraintSeverity.ERROR,
            lambda user_role, operation: operation != "sell" or user_role in ["supplier", "admin", "super_admin"],
            "فقط الموردين والمدراء يمكنهم بيع البطاقات",
            "تقدم بطلب ليصبح مورد معتمد"
        )
        
        self.add_constraint(
            "customer_can_buy",
            ConstraintType.ROLE,
            ConstraintSeverity.ERROR,
            lambda user_role, operation: operation != "buy" or user_role in ["customer", "supplier", "agent", "admin", "super_admin"],
            "يجب أن تكون مسجلاً لشراء البطاقات",
            "قم بالتسجيل أولاً باستخدام /start"
        )
        
        # قيود الحالة
        self.add_constraint(
            "user_must_be_active",
            ConstraintType.STATUS,
            ConstraintSeverity.ERROR,
            lambda user_active: user_active == 1,
            "الحساب غير مفعل",
            "انتظر تفعيل حسابك من الإدارة"
        )
        
        # قيود العلاقات
        self.add_constraint(
            "no_self_transfer",
            ConstraintType.RELATIONSHIP,
            ConstraintSeverity.ERROR,
            lambda from_user, to_user: from_user != to_user,
            "لا يمكن تحويل الأموال لنفسك",
            "اختر مستخدماً آخر للتحويل"
        )
        
        # قيود الأعمال
        self.add_constraint(
            "card_must_be_available",
            ConstraintType.BUSINESS,
            ConstraintSeverity.ERROR,
            lambda card_status: card_status == 0,  # is_sold = 0
            "البطاقة غير متاحة أو مباعة بالفعل",
            "اختر بطاقة أخرى أو حدث الصفحة"
        )
        
        self.add_constraint(
            "network_must_be_active",
            ConstraintType.BUSINESS,
            ConstraintSeverity.ERROR,
            lambda network_active, network_approved: network_active == 1 and network_approved == 1,
            "الشبكة غير نشطة أو غير معتمدة",
            "اختر شبكة أخرى أو تواصل مع المورد"
        )
    
    def add_constraint(self, name: str, constraint_type: ConstraintType, 
                      severity: ConstraintSeverity, validator_func,
                      error_message: str, user_action: str):
        """إضافة قيد جديد"""
        self.constraints[name] = {
            'type': constraint_type,
            'severity': severity,
            'validator': validator_func,
            'error_message': error_message,
            'user_action': user_action,
            'created_at': datetime.now()
        }
    
    def validate_constraint(self, constraint_name: str, *args, **kwargs) -> Tuple[bool, Optional[Dict]]:
        """التحقق من قيد محدد"""
        if constraint_name not in self.constraints:
            logger.warning(f"Constraint {constraint_name} not found")
            return True, None
        
        constraint = self.constraints[constraint_name]
        
        try:
            is_valid = constraint['validator'](*args, **kwargs)
            
            if not is_valid:
                violation = {
                    'constraint_name': constraint_name,
                    'type': constraint['type'].value,
                    'severity': constraint['severity'].value,
                    'error_message': constraint['error_message'],
                    'user_action': constraint['user_action'],
                    'timestamp': datetime.now(),
                    'args': args,
                    'kwargs': kwargs
                }
                
                self.violations_log.append(violation)
                logger.warning(f"Constraint violation: {constraint_name} - {constraint['error_message']}")
                
                return False, violation
            
            return True, None
            
        except Exception as e:
            logger.error(f"Error validating constraint {constraint_name}: {e}")
            return False, {
                'constraint_name': constraint_name,
                'type': 'validation_error',
                'severity': 'error',
                'error_message': f"خطأ في التحقق من القيد: {str(e)}",
                'user_action': "تواصل مع الدعم الفني"
            }
    
    def validate_transfer_operation(self, from_user_id: int, to_user_id: int, 
                                  amount: float) -> Tuple[bool, List[Dict]]:
        """التحقق من صحة عملية التحويل"""
        violations = []
        
        # الحصول على بيانات المستخدمين
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            # بيانات المرسل
            cursor.execute('SELECT balance, role, is_active FROM users WHERE id = ?', (from_user_id,))
            sender_data = cursor.fetchone()
            if not sender_data:
                violations.append({
                    'error_message': "المرسل غير موجود",
                    'severity': 'error'
                })
                return False, violations
            
            sender_balance, sender_role, sender_active = sender_data
            
            # بيانات المستقبل
            cursor.execute('SELECT role, is_active FROM users WHERE id = ?', (to_user_id,))
            receiver_data = cursor.fetchone()
            if not receiver_data:
                violations.append({
                    'error_message': "المستقبل غير موجود",
                    'severity': 'error'
                })
                return False, violations
            
            receiver_role, receiver_active = receiver_data
            
            # التحقق من القيود
            constraints_to_check = [
                ('minimum_balance', sender_balance - amount),
                ('minimum_transfer_amount', amount),
                ('maximum_transfer_amount', amount),
                ('no_self_transfer', from_user_id, to_user_id),
                ('user_must_be_active', sender_active),
                ('user_must_be_active', receiver_active),
                ('max_transfers_per_hour', from_user_id)
            ]
            
            for constraint_name, *args in constraints_to_check:
                is_valid, violation = self.validate_constraint(constraint_name, *args)
                if not is_valid and violation:
                    violations.append(violation)
            
            return len(violations) == 0, violations
            
        finally:
            conn.close()
    
    def validate_purchase_operation(self, user_id: int, card_id: int, 
                                   amount: float, network_id: int) -> Tuple[bool, List[Dict]]:
        """التحقق من صحة عملية الشراء"""
        violations = []
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            # بيانات المستخدم
            cursor.execute('SELECT balance, role, is_active FROM users WHERE id = ?', (user_id,))
            user_data = cursor.fetchone()
            if not user_data:
                violations.append({
                    'error_message': "المستخدم غير موجود",
                    'severity': 'error'
                })
                return False, violations
            
            user_balance, user_role, user_active = user_data
            
            # بيانات البطاقة
            cursor.execute('SELECT is_sold FROM network_cards WHERE id = ?', (card_id,))
            card_data = cursor.fetchone()
            if not card_data:
                violations.append({
                    'error_message': "البطاقة غير موجودة",
                    'severity': 'error'
                })
                return False, violations
            
            card_sold = card_data[0]
            
            # بيانات الشبكة
            cursor.execute('SELECT is_active, is_approved FROM networks WHERE id = ?', (network_id,))
            network_data = cursor.fetchone()
            if not network_data:
                violations.append({
                    'error_message': "الشبكة غير موجودة",
                    'severity': 'error'
                })
                return False, violations
            
            network_active, network_approved = network_data
            
            # التحقق من القيود
            constraints_to_check = [
                ('minimum_balance', user_balance - amount),
                ('maximum_single_purchase', amount),
                ('customer_can_buy', user_role, "buy"),
                ('user_must_be_active', user_active),
                ('card_must_be_available', card_sold),
                ('network_must_be_active', network_active, network_approved),
                ('max_purchases_per_day', user_id)
            ]
            
            for constraint_name, *args in constraints_to_check:
                is_valid, violation = self.validate_constraint(constraint_name, *args)
                if not is_valid and violation:
                    violations.append(violation)
            
            return len(violations) == 0, violations
            
        finally:
            conn.close()
    
    def validate_user_registration(self, telegram_id: int, full_name: str, 
                                 phone: str, role: str) -> Tuple[bool, List[Dict]]:
        """التحقق من صحة تسجيل المستخدم"""
        violations = []
        
        # قيود البيانات الأساسية
        if not self._validate_phone_number(phone):
            violations.append({
                'error_message': "رقم الهاتف غير صحيح",
                'severity': 'error',
                'user_action': "أدخل رقم هاتف صحيح (9 أرقام على الأقل)"
            })
        
        if not self._validate_full_name(full_name):
            violations.append({
                'error_message': "الاسم غير صحيح",
                'severity': 'error', 
                'user_action': "أدخل اسماً صحيحاً (حرفين على الأقل)"
            })
        
        if not self._validate_role(role):
            violations.append({
                'error_message': "نوع الحساب غير صحيح",
                'severity': 'error',
                'user_action': "اختر نوع حساب صحيح"
            })
        
        # فحص التكرار
        if self._check_duplicate_telegram_id(telegram_id):
            violations.append({
                'error_message': "هذا الحساب مسجل بالفعل",
                'severity': 'error',
                'user_action': "استخدم /start إذا نسيت حسابك"
            })
        
        if self._check_duplicate_phone(phone):
            violations.append({
                'error_message': "رقم الهاتف مسجل بالفعل",
                'severity': 'error',
                'user_action': "استخدم رقم هاتف مختلف أو تواصل مع الدعم"
            })
        
        return len(violations) == 0, violations
    
    def validate_coupon_redemption(self, user_id: int, coupon_code: str) -> Tuple[bool, List[Dict]]:
        """التحقق من صحة استخدام الكوبون"""
        violations = []
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            # فحص الكوبون
            cursor.execute('''
                SELECT amount, is_used, expires_at, created_by, usage_limit
                FROM coupons 
                WHERE coupon_code = ?
            ''', (coupon_code,))
            
            coupon_data = cursor.fetchone()
            if not coupon_data:
                violations.append({
                    'error_message': "الكوبون غير موجود",
                    'severity': 'error',
                    'user_action': "تأكد من كتابة الكوبون بشكل صحيح"
                })
                return False, violations
            
            amount, is_used, expires_at, created_by, usage_limit = coupon_data
            
            # فحص انتهاء الصلاحية
            if expires_at and datetime.fromisoformat(expires_at) < datetime.now():
                violations.append({
                    'error_message': "انتهت صلاحية الكوبون",
                    'severity': 'error',
                    'user_action': "استخدم كوبوناً آخر"
                })
            
            # فحص الاستخدام
            if is_used:
                violations.append({
                    'error_message': "الكوبون مستخدم بالفعل",
                    'severity': 'error',
                    'user_action': "استخدم كوبوناً آخر"
                })
            
            # فحص عدم استخدام المنشئ لكوبونه
            if created_by == user_id:
                violations.append({
                    'error_message': "لا يمكنك استخدام الكوبون الذي أنشأته",
                    'severity': 'error',
                    'user_action': "استخدم كوبوناً من مصدر آخر"
                })
            
            return len(violations) == 0, violations
            
        finally:
            conn.close()
    
    def _validate_phone_number(self, phone: str) -> bool:
        """التحقق من صحة رقم الهاتف"""
        if not phone or len(phone.strip()) < 9:
            return False
        
        # إزالة المسافات والرموز
        clean_phone = re.sub(r'[^\d]', '', phone)
        
        # التحقق من الطول والبداية
        if len(clean_phone) < 9 or len(clean_phone) > 15:
            return False
        
        # التحقق من أرقام يمنية صحيحة
        yemen_prefixes = ['967', '77', '78', '79', '70', '71', '73', '74']
        if not any(clean_phone.startswith(prefix) for prefix in yemen_prefixes):
            return False
        
        return True
    
    def _validate_full_name(self, full_name: str) -> bool:
        """التحقق من صحة الاسم الكامل"""
        if not full_name or len(full_name.strip()) < 2:
            return False
        
        # التحقق من وجود حروف فقط (عربية وإنجليزية)
        clean_name = re.sub(r'[^\u0600-\u06FFa-zA-Z\s]', '', full_name)
        if len(clean_name) < 2:
            return False
        
        return True
    
    def _validate_role(self, role: str) -> bool:
        """التحقق من صحة نوع الحساب"""
        valid_roles = ['customer', 'supplier', 'agent', 'admin', 'super_admin']
        return role in valid_roles
    
    def _check_duplicate_telegram_id(self, telegram_id: int) -> bool:
        """فحص تكرار معرف تيليجرام"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('SELECT 1 FROM users WHERE telegram_id = ?', (telegram_id,))
            return cursor.fetchone() is not None
        finally:
            conn.close()
    
    def _check_duplicate_phone(self, phone: str) -> bool:
        """فحص تكرار رقم الهاتف"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('SELECT 1 FROM users WHERE phone = ?', (phone,))
            return cursor.fetchone() is not None
        finally:
            conn.close()
    
    def _check_transfer_frequency(self, user_id: int, hours: int, max_transfers: int) -> bool:
        """فحص تكرار التحويلات"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT COUNT(*) FROM transactions 
                WHERE from_user = ? AND type = 'transfer'
                AND created_at >= datetime('now', '-' || ? || ' hours')
            ''', (user_id, hours))
            
            transfer_count = cursor.fetchone()[0]
            return transfer_count < max_transfers
            
        finally:
            conn.close()
    
    def _check_purchase_frequency(self, user_id: int, hours: int, max_purchases: int) -> bool:
        """فحص تكرار المشتريات"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT COUNT(*) FROM transactions 
                WHERE from_user = ? AND type = 'card_purchase'
                AND created_at >= datetime('now', '-' || ? || ' hours')
            ''', (user_id, hours))
            
            purchase_count = cursor.fetchone()[0]
            return purchase_count < max_purchases
            
        finally:
            conn.close()
    
    def validate_all_user_constraints(self, user_id: int) -> Tuple[bool, List[Dict]]:
        """التحقق من جميع قيود المستخدم"""
        violations = []
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('SELECT balance, role, is_active, telegram_id, phone, full_name FROM users WHERE id = ?', (user_id,))
            user_data = cursor.fetchone()
            
            if not user_data:
                violations.append({
                    'error_message': "المستخدم غير موجود",
                    'severity': 'error'
                })
                return False, violations
            
            balance, role, is_active, telegram_id, phone, full_name = user_data
            
            # فحص القيود الأساسية
            basic_constraints = [
                ('minimum_balance', balance),
                ('maximum_balance', balance),
                ('user_must_be_active', is_active)
            ]
            
            for constraint_name, *args in basic_constraints:
                is_valid, violation = self.validate_constraint(constraint_name, *args)
                if not is_valid and violation:
                    violations.append(violation)
            
            # فحص صحة البيانات
            data_valid, data_violations = self.validate_user_registration(telegram_id, full_name, phone, role)
            if not data_valid:
                violations.extend([v for v in data_violations if v.get('severity') != 'error' or 'مسجل بالفعل' not in v.get('error_message', '')])
            
            return len(violations) == 0, violations
            
        finally:
            conn.close()
    
    def get_violations_summary(self, hours: int = 24) -> Dict[str, Any]:
        """الحصول على ملخص انتهاكات القيود"""
        recent_violations = [
            v for v in self.violations_log 
            if v['timestamp'] >= datetime.now() - timedelta(hours=hours)
        ]
        
        # تجميع حسب النوع والخطورة
        by_type = {}
        by_severity = {}
        
        for violation in recent_violations:
            v_type = violation['type']
            v_severity = violation['severity']
            
            by_type[v_type] = by_type.get(v_type, 0) + 1
            by_severity[v_severity] = by_severity.get(v_severity, 0) + 1
        
        return {
            'total_violations': len(recent_violations),
            'by_type': by_type,
            'by_severity': by_severity,
            'recent_violations': recent_violations[-10:],  # آخر 10
            'period_hours': hours
        }
    
    def create_violation_report(self) -> str:
        """إنشاء تقرير انتهاكات القيود"""
        summary = self.get_violations_summary(24)
        
        report = f"""
📋 **تقرير انتهاكات القيود - آخر 24 ساعة**

📊 **الإحصائيات:**
• إجمالي الانتهاكات: **{summary['total_violations']}**

🔍 **حسب النوع:**
"""
        
        for v_type, count in summary['by_type'].items():
            report += f"• {v_type}: **{count}** انتهاك\n"
        
        report += "\n⚠️ **حسب الخطورة:**\n"
        for severity, count in summary['by_severity'].items():
            emoji = {"info": "ℹ️", "warning": "⚠️", "error": "❌", "critical": "🚨"}.get(severity, "❓")
            report += f"• {emoji} {severity}: **{count}** انتهاك\n"
        
        if summary['recent_violations']:
            report += "\n📋 **آخر الانتهاكات:**\n"
            for violation in summary['recent_violations']:
                time_str = violation['timestamp'].strftime('%H:%M')
                report += f"• {time_str} - {violation['error_message']}\n"
        
        return report
    
    def enforce_database_constraints(self):
        """تطبيق قيود قاعدة البيانات"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            # إنشاء فهارس وtriggers للتحقق من القيود (SQLite لا يدعم ALTER TABLE ADD CONSTRAINT)
            constraints_sql = [
                # فهارس للأداء
                'CREATE INDEX IF NOT EXISTS idx_users_balance_check ON users(balance) WHERE balance >= 0',
                'CREATE INDEX IF NOT EXISTS idx_transactions_amount_check ON transactions(amount) WHERE amount > 0',
                'CREATE INDEX IF NOT EXISTS idx_network_cards_value_check ON network_cards(card_value) WHERE card_value > 0',
                
                # Triggers للتحقق من القيود
                '''CREATE TRIGGER IF NOT EXISTS check_balance_positive 
                   BEFORE UPDATE OF balance ON users
                   WHEN NEW.balance < 0
                   BEGIN
                       SELECT RAISE(ABORT, 'Balance cannot be negative');
                   END''',
                
                '''CREATE TRIGGER IF NOT EXISTS check_transfer_not_self
                   BEFORE INSERT ON transactions
                   WHEN NEW.type = 'transfer' AND NEW.from_user = NEW.to_user
                   BEGIN
                       SELECT RAISE(ABORT, 'Cannot transfer to same user');
                   END''',
                
                '''CREATE TRIGGER IF NOT EXISTS check_amount_positive
                   BEFORE INSERT ON transactions
                   WHEN NEW.amount <= 0
                   BEGIN
                       SELECT RAISE(ABORT, 'Amount must be positive');
                   END''',
                
                '''CREATE TRIGGER IF NOT EXISTS check_card_value_positive
                   BEFORE INSERT ON network_cards
                   WHEN NEW.card_value <= 0
                   BEGIN
                       SELECT RAISE(ABORT, 'Card value must be positive');
                   END''',
            ]
            
            added_constraints = 0
            for constraint_sql in constraints_sql:
                try:
                    cursor.execute(constraint_sql)
                    added_constraints += 1
                    logger.info(f"Added constraint: {constraint_sql}")
                except sqlite3.Error as e:
                    if "already exists" not in str(e).lower() and "duplicate" not in str(e).lower():
                        logger.warning(f"Failed to add constraint: {e}")
            
            conn.commit()
            logger.info(f"Database constraints enforced: {added_constraints} constraints")
            
        except Exception as e:
            logger.error(f"Error enforcing database constraints: {e}")
            conn.rollback()
        finally:
            conn.close()
    
    def create_constraints_summary(self) -> str:
        """إنشاء ملخص القيود المطبقة"""
        summary = f"""
🛡️ **نظام القيود المطبق** 🛡️

📊 **إحصائيات النظام:**
• إجمالي القيود: **{len(self.constraints)}**
• انتهاكات آخر 24 ساعة: **{len([v for v in self.violations_log if v['timestamp'] >= datetime.now() - timedelta(hours=24)])}**

🔍 **القيود المطبقة:**

💰 **قيود الرصيد:**
• الحد الأدنى: 0 ريال
• الحد الأقصى: 1,000,000 ريال

💸 **قيود التحويل:**
• الحد الأدنى: 1 ريال
• الحد الأقصى: 50,000 ريال
• الحد الأقصى: 10 تحويلات/ساعة

🛒 **قيود الشراء:**
• الحد الأقصى: 10,000 ريال/بطاقة
• الحد الأقصى: 20 شراء/يوم

👤 **قيود المستخدمين:**
• الاسم: حرفين على الأقل
• الهاتف: 9 أرقام على الأقل
• لا تكرار في البيانات

🏪 **قيود الأعمال:**
• فقط الموردين يبيعون
• الشبكات يجب أن تكون مفعلة
• البطاقات يجب أن تكون متاحة

🔒 **قيود الأمان:**
• لا تحويل للمستخدم نفسه
• لا استخدام الكوبونات المنتهية
• الحسابات يجب أن تكون مفعلة
"""
        
        return summary

# إنشاء مثيل عام للاستخدام
constraints_system = ConstraintsSystem()