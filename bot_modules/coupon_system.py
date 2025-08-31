#!/usr/bin/env python3
"""
نظام الكوبونات المتقدم للبوت
Advanced Coupon System for Yemen Net Bot
Version: 1.0.0
"""

import logging
import sqlite3
import random
import string
import csv
import io
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from bot_modules.database import get_db_connection
from bot_modules.config import *

logger = logging.getLogger(__name__)

class CouponSystem:
    """نظام إدارة الكوبونات المتقدم"""
    
    def __init__(self):
        self.init_coupon_tables()
    
    def init_coupon_tables(self):
        """إنشاء جداول الكوبونات في قاعدة البيانات"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            # جدول الكوبونات الرئيسي
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS coupons (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code TEXT UNIQUE NOT NULL,
                    value REAL NOT NULL,
                    created_by INTEGER NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    used_by INTEGER NULL,
                    used_at DATETIME NULL,
                    is_active BOOLEAN DEFAULT 1,
                    batch_id TEXT NULL,
                    description TEXT NULL,
                    FOREIGN KEY (created_by) REFERENCES users(telegram_id),
                    FOREIGN KEY (used_by) REFERENCES users(telegram_id)
                )
            ''')
            
            # جدول محاولات الكوبونات الفاشلة (للحماية من التخمين)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS coupon_attempts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    attempted_code TEXT NOT NULL,
                    attempt_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                    ip_address TEXT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(telegram_id)
                )
            ''')
            
            # جدول سجل عمليات الكوبونات
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS coupon_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    coupon_code TEXT NOT NULL,
                    action TEXT NOT NULL,
                    user_id INTEGER NOT NULL,
                    admin_id INTEGER NULL,
                    details TEXT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(telegram_id),
                    FOREIGN KEY (admin_id) REFERENCES users(telegram_id)
                )
            ''')
            
            # جدول مجموعات الكوبونات
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS coupon_batches (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    batch_id TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    total_coupons INTEGER NOT NULL,
                    coupon_value REAL NOT NULL,
                    created_by INTEGER NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    description TEXT NULL,
                    FOREIGN KEY (created_by) REFERENCES users(telegram_id)
                )
            ''')
            
            conn.commit()
            logger.info("تم إنشاء جداول نظام الكوبونات بنجاح")
            
        except Exception as e:
            logger.error(f"خطأ في إنشاء جداول الكوبونات: {e}")
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def generate_coupon_code(self) -> str:
        """توليد رمز كوبون فريد بصيغة A123456789"""
        while True:
            # إنشاء 8 أرقام عشوائية
            numbers = ''.join([str(random.randint(0, 9)) for _ in range(8)])
            code = f"A{numbers}"
            
            # التحقق من عدم وجود الكوبون مسبقاً
            if not self.coupon_exists(code):
                return code
    
    def coupon_exists(self, code: str) -> bool:
        """التحقق من وجود الكوبون في قاعدة البيانات"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT id FROM coupons WHERE code = ?", (code,))
            exists = cursor.fetchone() is not None
            return exists
        except Exception as e:
            logger.error(f"خطأ في التحقق من وجود الكوبون: {e}")
            return True  # نعتبر أنه موجود لتجنب التكرار
        finally:
            conn.close()
    
    def create_single_coupon(self, admin_id: int, value: float, description: str = None) -> Tuple[bool, str, str]:
        """إنشاء كوبون فردي"""
        try:
            code = self.generate_coupon_code()
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # إدراج الكوبون في قاعدة البيانات
            cursor.execute('''
                INSERT INTO coupons (code, value, created_by, description)
                VALUES (?, ?, ?, ?)
            ''', (code, value, admin_id, description))
            
            # تسجيل العملية في السجل
            self.log_coupon_action(code, "CREATED", admin_id, admin_id, 
                                 f"كوبون فردي بقيمة {value} ريال")
            
            conn.commit()
            logger.info(f"تم إنشاء كوبون فردي: {code} بقيمة {value}")
            return True, code, "تم إنشاء الكوبون بنجاح"
            
        except Exception as e:
            logger.error(f"خطأ في إنشاء الكوبون الفردي: {e}")
            return False, "", f"خطأ في إنشاء الكوبون: {str(e)}"
        finally:
            conn.close()
    
    def create_batch_coupons(self, admin_id: int, count: int, value: float, 
                           batch_name: str = None, description: str = None) -> Tuple[bool, List[str], str, str]:
        """إنشاء مجموعة كوبونات دفعة واحدة"""
        try:
            if count > 1000:  # حد أقصى للأمان
                return False, [], "", "لا يمكن إنشاء أكثر من 1000 كوبون في المرة الواحدة"
            
            # إنشاء معرف المجموعة
            batch_id = f"BATCH_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{admin_id}"
            
            # إنشاء الكوبونات
            coupons = []
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # إدراج معلومات المجموعة
            cursor.execute('''
                INSERT INTO coupon_batches (batch_id, name, total_coupons, coupon_value, created_by, description)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (batch_id, batch_name or f"مجموعة {count} كوبون", count, value, admin_id, description))
            
            # إنشاء الكوبونات
            for i in range(count):
                code = self.generate_coupon_code()
                cursor.execute('''
                    INSERT INTO coupons (code, value, created_by, batch_id, description)
                    VALUES (?, ?, ?, ?, ?)
                ''', (code, value, admin_id, batch_id, f"كوبون من المجموعة {batch_name or batch_id}"))
                coupons.append(code)
            
            # تسجيل العملية
            self.log_coupon_action(batch_id, "BATCH_CREATED", admin_id, admin_id,
                                 f"مجموعة {count} كوبون بقيمة {value} ريال لكل كوبون")
            
            conn.commit()
            logger.info(f"تم إنشاء مجموعة {count} كوبون بقيمة {value} لكل كوبون")
            return True, coupons, batch_id, "تم إنشاء المجموعة بنجاح"
            
        except Exception as e:
            logger.error(f"خطأ في إنشاء مجموعة الكوبونات: {e}")
            return False, [], "", f"خطأ في إنشاء المجموعة: {str(e)}"
        finally:
            conn.close()
    
    def export_coupons_to_csv(self, coupons: List[str], batch_id: str, value: float) -> str:
        """تصدير الكوبونات إلى ملف CSV"""
        try:
            output = io.StringIO()
            writer = csv.writer(output)
            
            # كتابة العناوين
            writer.writerow(['رقم', 'كود الكوبون', 'القيمة', 'تاريخ الإنشاء', 'الحالة'])
            
            # كتابة الكوبونات
            for i, coupon in enumerate(coupons, 1):
                writer.writerow([
                    i, 
                    coupon, 
                    f"{value} ريال", 
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'غير مستخدم'
                ])
            
            csv_content = output.getvalue()
            output.close()
            
            return csv_content
            
        except Exception as e:
            logger.error(f"خطأ في تصدير الكوبونات: {e}")
            return ""
    
    def export_coupons_to_txt(self, coupons: List[str], batch_id: str, value: float) -> str:
        """تصدير الكوبونات إلى ملف نصي"""
        try:
            content = f"""
🎫 كوبونات اليمن نت - {batch_id}
📅 تاريخ الإنشاء: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
💰 قيمة كل كوبون: {value} ريال
📊 إجمالي الكوبونات: {len(coupons)}

═══════════════════════════════════════

"""
            
            for i, coupon in enumerate(coupons, 1):
                content += f"{i:3d}. {coupon}\n"
            
            content += f"""
═══════════════════════════════════════

📝 ملاحظات مهمة:
• كل كوبون يُستخدم مرة واحدة فقط
• صالح للاستخدام حتى يتم إلغاؤه
• للاستفسارات تواصل مع الإدارة

🔐 نظام الأمان:
• محمي ضد التخمين العشوائي
• تسجيل كامل لجميع العمليات
• منع إساءة الاستخدام تلقائياً
"""
            
            return content
            
        except Exception as e:
            logger.error(f"خطأ في تصدير الكوبونات النصي: {e}")
            return ""
    
    def redeem_coupon(self, user_id: int, code: str) -> Tuple[bool, float, str]:
        """استرداد كوبون من قبل العميل"""
        try:
            # التحقق من الحماية ضد التخمين
            if not self.check_attempt_limit(user_id):
                return False, 0.0, "⛔ تم منعك مؤقتاً من استخدام الكوبونات لمدة ساعة بسبب المحاولات الكثيرة"
            
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # البحث عن الكوبون
            cursor.execute('''
                SELECT id, value, used_by, is_active 
                FROM coupons 
                WHERE code = ?
            ''', (code,))
            
            coupon = cursor.fetchone()
            
            if not coupon:
                # تسجيل المحاولة الفاشلة
                self.record_failed_attempt(user_id, code)
                return False, 0.0, "❌ كود الكوبون غير صحيح"
            
            if not coupon['is_active']:
                return False, 0.0, "⛔ هذا الكوبون تم إلغاؤه"
            
            if coupon['used_by']:
                return False, 0.0, "⚠️ هذا الكوبون تم استخدامه مسبقاً"
            
            # تحديث الكوبون كمستخدم
            cursor.execute('''
                UPDATE coupons 
                SET used_by = ?, used_at = CURRENT_TIMESTAMP
                WHERE code = ?
            ''', (user_id, code))
            
            # إضافة الرصيد للمستخدم
            cursor.execute('''
                UPDATE users 
                SET balance = balance + ?
                WHERE telegram_id = ?
            ''', (coupon['value'], user_id))
            
            # تسجيل العملية
            self.log_coupon_action(code, "REDEEMED", user_id, None,
                                 f"تم استرداد كوبون بقيمة {coupon['value']} ريال")
            
            conn.commit()
            logger.info(f"تم استرداد كوبون {code} بقيمة {coupon['value']} للمستخدم {user_id}")
            return True, coupon['value'], f"✅ تم شحن رصيدك بـ {coupon['value']} ريال بنجاح!"
            
        except Exception as e:
            logger.error(f"خطأ في استرداد الكوبون: {e}")
            return False, 0.0, "❌ حدث خطأ في النظام، حاول مرة أخرى"
        finally:
            conn.close()
    
    def check_attempt_limit(self, user_id: int) -> bool:
        """التحقق من عدد المحاولات خلال الساعة الماضية"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            # حساب المحاولات خلال الساعة الماضية
            one_hour_ago = datetime.now() - timedelta(hours=1)
            cursor.execute('''
                SELECT COUNT(*) as attempts
                FROM coupon_attempts 
                WHERE user_id = ? AND attempt_time > ?
            ''', (user_id, one_hour_ago))
            
            attempts = cursor.fetchone()['attempts']
            return attempts < 20  # الحد الأقصى 20 محاولة في الساعة
            
        except Exception as e:
            logger.error(f"خطأ في فحص حد المحاولات: {e}")
            return True  # في حالة الخطأ، نسمح بالمحاولة
        finally:
            conn.close()
    
    def record_failed_attempt(self, user_id: int, attempted_code: str):
        """تسجيل محاولة فاشلة لاستخدام كوبون"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO coupon_attempts (user_id, attempted_code)
                VALUES (?, ?)
            ''', (user_id, attempted_code))
            
            conn.commit()
            
        except Exception as e:
            logger.error(f"خطأ في تسجيل المحاولة الفاشلة: {e}")
        finally:
            conn.close()
    
    def delete_coupon(self, admin_id: int, code: str) -> Tuple[bool, str]:
        """حذف/إلغاء كوبون"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            # التحقق من وجود الكوبون
            cursor.execute('''
                SELECT id, used_by, value 
                FROM coupons 
                WHERE code = ?
            ''', (code,))
            
            coupon = cursor.fetchone()
            
            if not coupon:
                return False, "❌ الكوبون غير موجود"
            
            if coupon['used_by']:
                return False, "⚠️ لا يمكن حذف كوبون تم استخدامه مسبقاً"
            
            # إلغاء الكوبون بدلاً من حذفه (للاحتفاظ بالسجلات)
            cursor.execute('''
                UPDATE coupons 
                SET is_active = 0
                WHERE code = ?
            ''', (code,))
            
            # تسجيل العملية
            self.log_coupon_action(code, "CANCELLED", admin_id, admin_id,
                                 f"تم إلغاء كوبون بقيمة {coupon['value']} ريال")
            
            conn.commit()
            logger.info(f"تم إلغاء الكوبون {code} بواسطة المشرف {admin_id}")
            return True, f"✅ تم إلغاء الكوبون {code} بنجاح"
            
        except Exception as e:
            logger.error(f"خطأ في حذف الكوبون: {e}")
            return False, "❌ حدث خطأ في النظام"
        finally:
            conn.close()
    
    def get_coupon_info(self, code: str) -> Optional[Dict]:
        """الحصول على معلومات الكوبون"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT c.*, u1.full_name as created_by_name, u2.full_name as used_by_name
                FROM coupons c
                LEFT JOIN users u1 ON c.created_by = u1.telegram_id
                LEFT JOIN users u2 ON c.used_by = u2.telegram_id
                WHERE c.code = ?
            ''', (code,))
            
            coupon = cursor.fetchone()
            
            if coupon:
                return dict(coupon)
            return None
            
        except Exception as e:
            logger.error(f"خطأ في الحصول على معلومات الكوبون: {e}")
            return None
        finally:
            conn.close()
    
    def get_user_coupons_stats(self, user_id: int) -> Dict:
        """إحصائيات كوبونات المستخدم"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            # الكوبونات المستخدمة
            cursor.execute('''
                SELECT COUNT(*) as used_count, COALESCE(SUM(value), 0) as total_value
                FROM coupons 
                WHERE used_by = ?
            ''', (user_id,))
            
            used_stats = cursor.fetchone()
            
            # المحاولات الفاشلة اليوم
            today = datetime.now().date()
            cursor.execute('''
                SELECT COUNT(*) as failed_attempts
                FROM coupon_attempts 
                WHERE user_id = ? AND DATE(attempt_time) = ?
            ''', (user_id, today))
            
            failed_stats = cursor.fetchone()
            
            return {
                'used_count': used_stats['used_count'],
                'total_value': used_stats['total_value'],
                'failed_attempts_today': failed_stats['failed_attempts']
            }
            
        except Exception as e:
            logger.error(f"خطأ في إحصائيات الكوبونات: {e}")
            return {'used_count': 0, 'total_value': 0, 'failed_attempts_today': 0}
        finally:
            conn.close()
    
    def get_admin_coupons_stats(self, admin_id: int = None) -> Dict:
        """إحصائيات كوبونات المشرف أو العامة"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            where_clause = "WHERE created_by = ?" if admin_id else ""
            params = (admin_id,) if admin_id else ()
            
            # إحصائيات عامة
            cursor.execute(f'''
                SELECT 
                    COUNT(*) as total_coupons,
                    COUNT(CASE WHEN used_by IS NOT NULL THEN 1 END) as used_coupons,
                    COUNT(CASE WHEN is_active = 1 AND used_by IS NULL THEN 1 END) as active_unused,
                    COUNT(CASE WHEN is_active = 0 THEN 1 END) as cancelled_coupons,
                    COALESCE(SUM(value), 0) as total_value,
                    COALESCE(SUM(CASE WHEN used_by IS NOT NULL THEN value ELSE 0 END), 0) as redeemed_value
                FROM coupons 
                {where_clause}
            ''', params)
            
            stats = cursor.fetchone()
            
            # إحصائيات المجموعات
            cursor.execute(f'''
                SELECT COUNT(*) as total_batches
                FROM coupon_batches 
                {where_clause}
            ''', params)
            
            batch_stats = cursor.fetchone()
            
            return {
                'total_coupons': stats['total_coupons'],
                'used_coupons': stats['used_coupons'],
                'active_unused': stats['active_unused'],
                'cancelled_coupons': stats['cancelled_coupons'],
                'total_value': stats['total_value'],
                'redeemed_value': stats['redeemed_value'],
                'total_batches': batch_stats['total_batches']
            }
            
        except Exception as e:
            logger.error(f"خطأ في إحصائيات المشرف: {e}")
            return {}
        finally:
            conn.close()
    
    def log_coupon_action(self, coupon_code: str, action: str, user_id: int, 
                         admin_id: int = None, details: str = None):
        """تسجيل عملية في سجل الكوبونات"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO coupon_logs (coupon_code, action, user_id, admin_id, details)
                VALUES (?, ?, ?, ?, ?)
            ''', (coupon_code, action, user_id, admin_id, details))
            
            conn.commit()
            
        except Exception as e:
            logger.error(f"خطأ في تسجيل عملية الكوبون: {e}")
        finally:
            conn.close()
    
    def get_coupon_logs(self, limit: int = 50, coupon_code: str = None) -> List[Dict]:
        """الحصول على سجل عمليات الكوبونات"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            where_clause = "WHERE coupon_code = ?" if coupon_code else ""
            params = (coupon_code, limit) if coupon_code else (limit,)
            
            cursor.execute(f'''
                SELECT 
                    cl.*,
                    u1.full_name as user_name,
                    u2.full_name as admin_name
                FROM coupon_logs cl
                LEFT JOIN users u1 ON cl.user_id = u1.telegram_id
                LEFT JOIN users u2 ON cl.admin_id = u2.telegram_id
                {where_clause}
                ORDER BY cl.timestamp DESC
                LIMIT ?
            ''', params)
            
            logs = cursor.fetchall()
            return [dict(log) for log in logs]
            
        except Exception as e:
            logger.error(f"خطأ في الحصول على سجل الكوبونات: {e}")
            return []
        finally:
            conn.close()
    
    def get_active_coupons(self, admin_id: int = None, limit: int = 50) -> List[Dict]:
        """الحصول على الكوبونات النشطة"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            where_clause = "WHERE c.created_by = ? AND c.is_active = 1 AND c.used_by IS NULL" if admin_id else "WHERE c.is_active = 1 AND c.used_by IS NULL"
            params = (admin_id, limit) if admin_id else (limit,)
            
            cursor.execute(f'''
                SELECT 
                    c.*,
                    u.full_name as created_by_name
                FROM coupons c
                LEFT JOIN users u ON c.created_by = u.telegram_id
                {where_clause}
                ORDER BY c.created_at DESC
                LIMIT ?
            ''', params)
            
            coupons = cursor.fetchall()
            return [dict(coupon) for coupon in coupons]
            
        except Exception as e:
            logger.error(f"خطأ في الحصول على الكوبونات النشطة: {e}")
            return []
        finally:
            conn.close()
    
    def cleanup_old_attempts(self):
        """تنظيف المحاولات القديمة (أكثر من 24 ساعة)"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            yesterday = datetime.now() - timedelta(hours=24)
            cursor.execute('''
                DELETE FROM coupon_attempts 
                WHERE attempt_time < ?
            ''', (yesterday,))
            
            deleted_count = cursor.rowcount
            conn.commit()
            
            if deleted_count > 0:
                logger.info(f"تم تنظيف {deleted_count} محاولة قديمة من سجل الكوبونات")
            
        except Exception as e:
            logger.error(f"خطأ في تنظيف المحاولات القديمة: {e}")
        finally:
            conn.close()

# إنشاء مثيل النظام
coupon_system = CouponSystem()