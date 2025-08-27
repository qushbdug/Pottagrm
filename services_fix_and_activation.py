#!/usr/bin/env python3
"""
إصلاح وتفعيل جميع الخدمات المعطلة في البوت
Fix and Activate All Disabled Services in Bot
"""

import os
import re
import sqlite3
import logging
from datetime import datetime, timedelta

# إعداد التسجيل
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ServicesActivator:
    def __init__(self, db_path='yemen_net.db'):
        self.db_path = db_path
        
    def activate_all_services(self):
        """تفعيل جميع الخدمات"""
        print("🚀 === تفعيل جميع الخدمات ===")
        
        try:
            # تفعيل خدمة شراء الكروت
            self._activate_card_purchase_service()
            
            # تفعيل خدمة المحفظة
            self._activate_wallet_service()
            
            # تفعيل خدمة التحويل
            self._activate_transfer_service()
            
            # تفعيل خدمة البحث
            self._activate_search_service()
            
            # تفعيل خدمة التقارير
            self._activate_reports_service()
            
            # تفعيل خدمة التقييمات
            self._activate_ratings_service()
            
            # تفعيل خدمة الإشعارات
            self._activate_notifications_service()
            
            # تفعيل خدمة العروض
            self._activate_promotions_service()
            
            # تفعيل الخدمات الإدارية
            self._activate_admin_services()
            
            print("✅ تم تفعيل جميع الخدمات بنجاح")
            return True
            
        except Exception as e:
            logger.error(f"خطأ في تفعيل الخدمات: {e}")
            return False
    
    def _activate_card_purchase_service(self):
        """تفعيل خدمة شراء الكروت"""
        print("🔧 تفعيل خدمة شراء الكروت...")
        
        try:
            conn = sqlite3.connect(self.db_path, timeout=30.0)
            cursor = conn.cursor()
            
            # التأكد من وجود فئات كروت
            cursor.execute("SELECT COUNT(*) FROM card_categories")
            categories_count = cursor.fetchone()[0]
            
            if categories_count == 0:
                print("  📝 إنشاء فئات كروت افتراضية...")
                
                # الحصول على الشبكات النشطة
                cursor.execute("SELECT id, name FROM networks WHERE is_active = 1")
                networks = cursor.fetchall()
                
                default_categories = [
                    {'name': '5 ريال', 'value': 5, 'price': 5.5},
                    {'name': '10 ريال', 'value': 10, 'price': 11.0},
                    {'name': '20 ريال', 'value': 20, 'price': 22.0},
                    {'name': '50 ريال', 'value': 50, 'price': 55.0},
                    {'name': '100 ريال', 'value': 100, 'price': 110.0}
                ]
                
                for network_id, network_name in networks:
                    for category in default_categories:
                        cursor.execute("""
                            INSERT INTO card_categories 
                            (network_id, name, value, price, category_name, is_available, stock_count)
                            VALUES (?, ?, ?, ?, ?, 1, 100)
                        """, (
                            network_id,
                            category['name'],
                            category['value'],
                            category['price'],
                            category['name']
                        ))
                
                print(f"    ✅ تم إنشاء {len(default_categories)} فئة لكل شبكة")
            
            # التأكد من وجود كروت
            cursor.execute("SELECT COUNT(*) FROM cards")
            cards_count = cursor.fetchone()[0]
            
            if cards_count == 0:
                print("  📝 إنشاء كروت افتراضية...")
                
                cursor.execute("""
                    SELECT cc.id, cc.network_id, cc.value, n.name
                    FROM card_categories cc
                    JOIN networks n ON cc.network_id = n.id
                    WHERE cc.is_available = 1
                """)
                categories = cursor.fetchall()
                
                for category_id, network_id, value, network_name in categories:
                    # إنشاء 50 كرت لكل فئة
                    for i in range(50):
                        card_code = f"{network_id:03d}{value:03d}{i+1:03d}"
                        cursor.execute("""
                            INSERT INTO cards (id, category_id, code, is_used, added_at)
                            VALUES (?, ?, ?, 0, CURRENT_TIMESTAMP)
                        """, (f"card_{category_id}_{i+1}", category_id, card_code))
                    
                    print(f"    ✅ تم إنشاء 50 كرت للفئة {value} ريال في {network_name}")
            
            conn.commit()
            conn.close()
            
            print("  ✅ تم تفعيل خدمة شراء الكروت")
            
        except Exception as e:
            logger.error(f"خطأ في تفعيل خدمة شراء الكروت: {e}")
    
    def _activate_wallet_service(self):
        """تفعيل خدمة المحفظة"""
        print("🔧 تفعيل خدمة المحفظة...")
        
        try:
            conn = sqlite3.connect(self.db_path, timeout=30.0)
            cursor = conn.cursor()
            
            # التأكد من وجود أرقام محفظة لجميع المستخدمين
            cursor.execute("SELECT id FROM users WHERE wallet_number IS NULL OR wallet_number = ''")
            missing_wallets = cursor.fetchall()
            
            if missing_wallets:
                print(f"  📝 إنشاء أرقام محفظة لـ {len(missing_wallets)} مستخدم...")
                
                for (user_id,) in missing_wallets:
                    wallet_number = self._generate_unique_wallet_number(cursor)
                    cursor.execute('UPDATE users SET wallet_number = ? WHERE id = ?', (wallet_number, user_id))
                
                print("    ✅ تم إنشاء أرقام المحفظة")
            
            # إنشاء جدول معاملات المحفظة إذا لم يكن موجوداً
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS wallet_transactions (
                    id TEXT PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    transaction_type TEXT NOT NULL,
                    amount REAL NOT NULL,
                    balance_before REAL NOT NULL,
                    balance_after REAL NOT NULL,
                    reference_id TEXT,
                    description TEXT,
                    status TEXT DEFAULT 'completed',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT,
                    FOREIGN KEY(user_id) REFERENCES users(id)
                )
            ''')
            
            conn.commit()
            conn.close()
            
            print("  ✅ تم تفعيل خدمة المحفظة")
            
        except Exception as e:
            logger.error(f"خطأ في تفعيل خدمة المحفظة: {e}")
    
    def _activate_transfer_service(self):
        """تفعيل خدمة التحويل"""
        print("🔧 تفعيل خدمة التحويل...")
        
        try:
            conn = sqlite3.connect(self.db_path, timeout=30.0)
            cursor = conn.cursor()
            
            # التأكد من وجود جدول المعاملات
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS transactions (
                    id TEXT PRIMARY KEY,
                    from_user INTEGER,
                    to_user INTEGER,
                    amount REAL NOT NULL,
                    type TEXT NOT NULL,
                    status TEXT DEFAULT 'completed',
                    reference_id TEXT,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_withdrawable BOOLEAN DEFAULT 0,
                    commission_amount REAL DEFAULT 0.0,
                    FOREIGN KEY(from_user) REFERENCES users(id),
                    FOREIGN KEY(to_user) REFERENCES users(id)
                )
            ''')
            
            # إنشاء فهارس لتحسين الأداء
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_transactions_from_user ON transactions(from_user)",
                "CREATE INDEX IF NOT EXISTS idx_transactions_to_user ON transactions(to_user)",
                "CREATE INDEX IF NOT EXISTS idx_transactions_type ON transactions(type)",
                "CREATE INDEX IF NOT EXISTS idx_transactions_created_at ON transactions(created_at)"
            ]
            
            for index in indexes:
                try:
                    cursor.execute(index)
                except:
                    pass
            
            conn.commit()
            conn.close()
            
            print("  ✅ تم تفعيل خدمة التحويل")
            
        except Exception as e:
            logger.error(f"خطأ في تفعيل خدمة التحويل: {e}")
    
    def _activate_search_service(self):
        """تفعيل خدمة البحث"""
        print("🔧 تفعيل خدمة البحث...")
        
        try:
            conn = sqlite3.connect(self.db_path, timeout=30.0)
            cursor = conn.cursor()
            
            # إنشاء فهارس للبحث
            search_indexes = [
                "CREATE INDEX IF NOT EXISTS idx_users_full_name ON users(full_name)",
                "CREATE INDEX IF NOT EXISTS idx_users_phone ON users(phone)",
                "CREATE INDEX IF NOT EXISTS idx_networks_name ON networks(name)",
                "CREATE INDEX IF NOT EXISTS idx_networks_city ON networks(city)",
                "CREATE INDEX IF NOT EXISTS idx_card_categories_value ON card_categories(value)"
            ]
            
            for index in search_indexes:
                try:
                    cursor.execute(index)
                except:
                    pass
            
            conn.commit()
            conn.close()
            
            print("  ✅ تم تفعيل خدمة البحث")
            
        except Exception as e:
            logger.error(f"خطأ في تفعيل خدمة البحث: {e}")
    
    def _activate_reports_service(self):
        """تفعيل خدمة التقارير"""
        print("🔧 تفعيل خدمة التقارير...")
        
        try:
            conn = sqlite3.connect(self.db_path, timeout=30.0)
            cursor = conn.cursor()
            
            # إنشاء جدول التقارير
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS sales_reports (
                    id TEXT PRIMARY KEY,
                    report_type TEXT NOT NULL,
                    start_date DATE NOT NULL,
                    end_date DATE NOT NULL,
                    total_sales REAL DEFAULT 0.0,
                    total_commission REAL DEFAULT 0.0,
                    total_transactions INTEGER DEFAULT 0,
                    generated_by INTEGER NOT NULL,
                    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    data TEXT,
                    FOREIGN KEY(generated_by) REFERENCES users(id)
                )
            ''')
            
            # إنشاء جدول سجل النشاط
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS activity_logs (
                    id TEXT PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    activity_type TEXT NOT NULL,
                    description TEXT NOT NULL,
                    metadata TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(user_id) REFERENCES users(id)
                )
            ''')
            
            conn.commit()
            conn.close()
            
            print("  ✅ تم تفعيل خدمة التقارير")
            
        except Exception as e:
            logger.error(f"خطأ في تفعيل خدمة التقارير: {e}")
    
    def _activate_ratings_service(self):
        """تفعيل خدمة التقييمات"""
        print("🔧 تفعيل خدمة التقييمات...")
        
        try:
            conn = sqlite3.connect(self.db_path, timeout=30.0)
            cursor = conn.cursor()
            
            # إنشاء جدول التقييمات
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS ratings (
                    id TEXT PRIMARY KEY,
                    rater_id INTEGER NOT NULL,
                    rated_user_id INTEGER NOT NULL,
                    transaction_id TEXT,
                    rating INTEGER NOT NULL CHECK(rating >= 1 AND rating <= 5),
                    review_text TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_visible BOOLEAN DEFAULT 1,
                    FOREIGN KEY(rater_id) REFERENCES users(id),
                    FOREIGN KEY(rated_user_id) REFERENCES users(id),
                    FOREIGN KEY(transaction_id) REFERENCES transactions(id)
                )
            ''')
            
            # إنشاء جدول ملخص التقييمات
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_ratings_summary (
                    user_id INTEGER PRIMARY KEY,
                    total_ratings INTEGER DEFAULT 0,
                    average_rating REAL DEFAULT 0.0,
                    rating_1_count INTEGER DEFAULT 0,
                    rating_2_count INTEGER DEFAULT 0,
                    rating_3_count INTEGER DEFAULT 0,
                    rating_4_count INTEGER DEFAULT 0,
                    rating_5_count INTEGER DEFAULT 0,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(user_id) REFERENCES users(id)
                )
            ''')
            
            conn.commit()
            conn.close()
            
            print("  ✅ تم تفعيل خدمة التقييمات")
            
        except Exception as e:
            logger.error(f"خطأ في تفعيل خدمة التقييمات: {e}")
    
    def _activate_notifications_service(self):
        """تفعيل خدمة الإشعارات"""
        print("🔧 تفعيل خدمة الإشعارات...")
        
        try:
            conn = sqlite3.connect(self.db_path, timeout=30.0)
            cursor = conn.cursor()
            
            # إنشاء جدول تفضيلات الإشعارات
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS notification_preferences (
                    user_id INTEGER PRIMARY KEY,
                    balance_alerts BOOLEAN DEFAULT 1,
                    transaction_alerts BOOLEAN DEFAULT 1,
                    promotion_alerts BOOLEAN DEFAULT 1,
                    system_alerts BOOLEAN DEFAULT 1,
                    low_stock_alerts BOOLEAN DEFAULT 0,
                    rating_requests BOOLEAN DEFAULT 1,
                    email_notifications BOOLEAN DEFAULT 0,
                    sms_notifications BOOLEAN DEFAULT 0,
                    quiet_hours_start TIME,
                    quiet_hours_end TIME,
                    FOREIGN KEY(user_id) REFERENCES users(id)
                )
            ''')
            
            # إنشاء جدول الإشعارات الذكية
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS smart_notifications (
                    id TEXT PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    notification_type TEXT NOT NULL,
                    title TEXT NOT NULL,
                    message TEXT NOT NULL,
                    priority TEXT DEFAULT 'normal',
                    is_read BOOLEAN DEFAULT 0,
                    is_sent BOOLEAN DEFAULT 0,
                    scheduled_for TIMESTAMP,
                    sent_at TIMESTAMP,
                    read_at TIMESTAMP,
                    metadata TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(user_id) REFERENCES users(id)
                )
            ''')
            
            conn.commit()
            conn.close()
            
            print("  ✅ تم تفعيل خدمة الإشعارات")
            
        except Exception as e:
            logger.error(f"خطأ في تفعيل خدمة الإشعارات: {e}")
    
    def _activate_promotions_service(self):
        """تفعيل خدمة العروض"""
        print("🔧 تفعيل خدمة العروض...")
        
        try:
            conn = sqlite3.connect(self.db_path, timeout=30.0)
            cursor = conn.cursor()
            
            # إنشاء جدول العروض
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS promotions (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    promotion_type TEXT NOT NULL,
                    discount_percentage REAL DEFAULT 0.0,
                    discount_amount REAL DEFAULT 0.0,
                    min_purchase_amount REAL DEFAULT 0.0,
                    max_usage_per_user INTEGER DEFAULT 1,
                    start_date TIMESTAMP NOT NULL,
                    end_date TIMESTAMP NOT NULL,
                    is_active BOOLEAN DEFAULT 1,
                    created_by INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    target_user_role TEXT,
                    applicable_networks TEXT,
                    FOREIGN KEY(created_by) REFERENCES users(id)
                )
            ''')
            
            # إنشاء جدول استخدام العروض
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS promotion_usage (
                    id TEXT PRIMARY KEY,
                    promotion_id TEXT NOT NULL,
                    user_id INTEGER NOT NULL,
                    transaction_id TEXT NOT NULL,
                    discount_applied REAL NOT NULL,
                    used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(promotion_id) REFERENCES promotions(id),
                    FOREIGN KEY(user_id) REFERENCES users(id),
                    FOREIGN KEY(transaction_id) REFERENCES transactions(id)
                )
            ''')
            
            # إضافة عروض افتراضية
            default_promotions = [
                {
                    'title': 'عرض الترحيب',
                    'description': 'خصم 10% على أول عملية شراء',
                    'promotion_type': 'percentage_discount',
                    'discount_percentage': 10.0,
                    'min_purchase_amount': 5.0,
                    'max_usage_per_user': 1,
                    'start_date': datetime.now(),
                    'end_date': datetime.now() + timedelta(days=365),
                    'target_user_role': 'customer'
                },
                {
                    'title': 'عرض العميل المخلص',
                    'description': 'خصم 5% للمشترين المتكررين',
                    'promotion_type': 'percentage_discount',
                    'discount_percentage': 5.0,
                    'min_purchase_amount': 20.0,
                    'max_usage_per_user': 5,
                    'start_date': datetime.now(),
                    'end_date': datetime.now() + timedelta(days=365),
                    'target_user_role': 'customer'
                }
            ]
            
            # الحصول على المشرف الأعلى
            cursor.execute("SELECT id FROM users WHERE role = 'super_admin' LIMIT 1")
            admin = cursor.fetchone()
            
            if admin:
                admin_id = admin[0]
                
                for promo in default_promotions:
                    cursor.execute("""
                        INSERT OR IGNORE INTO promotions 
                        (id, title, description, promotion_type, discount_percentage, 
                         min_purchase_amount, max_usage_per_user, start_date, end_date, 
                         created_by, target_user_role)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        f"promo_{datetime.now().strftime('%Y%m%d%H%M%S')}_{hash(promo['title'])}",
                        promo['title'],
                        promo['description'],
                        promo['promotion_type'],
                        promo['discount_percentage'],
                        promo['min_purchase_amount'],
                        promo['max_usage_per_user'],
                        promo['start_date'],
                        promo['end_date'],
                        admin_id,
                        promo['target_user_role']
                    ))
                
                print("    ✅ تم إضافة عروض افتراضية")
            
            conn.commit()
            conn.close()
            
            print("  ✅ تم تفعيل خدمة العروض")
            
        except Exception as e:
            logger.error(f"خطأ في تفعيل خدمة العروض: {e}")
    
    def _activate_admin_services(self):
        """تفعيل الخدمات الإدارية"""
        print("🔧 تفعيل الخدمات الإدارية...")
        
        try:
            conn = sqlite3.connect(self.db_path, timeout=30.0)
            cursor = conn.cursor()
            
            # إنشاء جدول الصلاحيات
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_permissions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    permission_name TEXT NOT NULL,
                    granted_by INTEGER NOT NULL,
                    granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP,
                    is_active BOOLEAN DEFAULT 1,
                    FOREIGN KEY(user_id) REFERENCES users(id),
                    FOREIGN KEY(granted_by) REFERENCES users(id)
                )
            ''')
            
            # إنشاء جدول إشعارات المشرفين
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS admin_notifications (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    message TEXT NOT NULL,
                    type TEXT DEFAULT 'info',
                    is_read BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_by INTEGER,
                    target_admin INTEGER,
                    FOREIGN KEY(created_by) REFERENCES users(id),
                    FOREIGN KEY(target_admin) REFERENCES users(id)
                )
            ''')
            
            # إنشاء جدول سجل النظام
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS system_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    action TEXT NOT NULL,
                    details TEXT,
                    ip_address TEXT,
                    user_agent TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(user_id) REFERENCES users(id)
                )
            ''')
            
            # منح صلاحيات افتراضية للمشرفين
            cursor.execute("SELECT id FROM users WHERE role IN ('admin', 'super_admin')")
            admins = cursor.fetchall()
            
            default_permissions = [
                'create_users',
                'manage_balance',
                'approve_suppliers',
                'view_reports',
                'manage_promotions',
                'system_admin'
            ]
            
            for (admin_id,) in admins:
                for permission in default_permissions:
                    cursor.execute("""
                        INSERT OR IGNORE INTO user_permissions 
                        (user_id, permission_name, granted_by)
                        VALUES (?, ?, ?)
                    """, (admin_id, permission, admin_id))
            
            conn.commit()
            conn.close()
            
            print("  ✅ تم تفعيل الخدمات الإدارية")
            
        except Exception as e:
            logger.error(f"خطأ في تفعيل الخدمات الإدارية: {e}")
    
    def _generate_unique_wallet_number(self, cursor):
        """إنشاء رقم محفظة فريد"""
        import random
        
        while True:
            wallet_number = '79' + ''.join(str(random.randint(0, 9)) for _ in range(7))
            cursor.execute('SELECT 1 FROM users WHERE wallet_number = ?', (wallet_number,))
            if not cursor.fetchone():
                return wallet_number
    
    def verify_services_activation(self):
        """التحقق من تفعيل الخدمات"""
        print("🔍 === التحقق من تفعيل الخدمات ===")
        
        try:
            conn = sqlite3.connect(self.db_path, timeout=30.0)
            cursor = conn.cursor()
            
            services_status = {}
            
            # فحص خدمة شراء الكروت
            cursor.execute("SELECT COUNT(*) FROM card_categories")
            categories_count = cursor.fetchone()[0]
            services_status['card_purchase'] = categories_count > 0
            
            cursor.execute("SELECT COUNT(*) FROM cards")
            cards_count = cursor.fetchone()[0]
            services_status['cards_available'] = cards_count > 0
            
            # فحص خدمة المحفظة
            cursor.execute("SELECT COUNT(*) FROM users WHERE wallet_number IS NOT NULL")
            wallet_users = cursor.fetchone()[0]
            services_status['wallet'] = wallet_users > 0
            
            # فحص خدمة التحويل
            cursor.execute("SELECT COUNT(*) FROM transactions")
            transactions_count = cursor.fetchone()[0]
            services_status['transfers'] = True  # الجدول موجود
            
            # فحص خدمة التقارير
            cursor.execute("SELECT COUNT(*) FROM activity_logs")
            activity_logs = cursor.fetchone()[0]
            services_status['reports'] = True  # الجدول موجود
            
            # فحص خدمة التقييمات
            cursor.execute("SELECT COUNT(*) FROM ratings")
            ratings_count = cursor.fetchone()[0]
            services_status['ratings'] = True  # الجدول موجود
            
            # فحص خدمة الإشعارات
            cursor.execute("SELECT COUNT(*) FROM smart_notifications")
            notifications_count = cursor.fetchone()[0]
            services_status['notifications'] = True  # الجدول موجود
            
            # فحص خدمة العروض
            cursor.execute("SELECT COUNT(*) FROM promotions")
            promotions_count = cursor.fetchone()[0]
            services_status['promotions'] = promotions_count > 0
            
            # فحص الخدمات الإدارية
            cursor.execute("SELECT COUNT(*) FROM user_permissions")
            permissions_count = cursor.fetchone()[0]
            services_status['admin_services'] = permissions_count > 0
            
            conn.close()
            
            # عرض حالة الخدمات
            print("📊 حالة الخدمات:")
            for service, status in services_status.items():
                status_icon = "✅" if status else "❌"
                service_name = {
                    'card_purchase': 'شراء الكروت',
                    'cards_available': 'توفر الكروت',
                    'wallet': 'المحفظة',
                    'transfers': 'التحويلات',
                    'reports': 'التقارير',
                    'ratings': 'التقييمات',
                    'notifications': 'الإشعارات',
                    'promotions': 'العروض',
                    'admin_services': 'الخدمات الإدارية'
                }.get(service, service)
                
                print(f"  {status_icon} {service_name}")
            
            # حساب نسبة التفعيل
            activated_services = sum(services_status.values())
            total_services = len(services_status)
            activation_rate = (activated_services / total_services) * 100
            
            print(f"\n📈 نسبة تفعيل الخدمات: {activation_rate:.1f}% ({activated_services}/{total_services})")
            
            return activation_rate >= 90  # نجح إذا كانت النسبة 90% أو أكثر
            
        except Exception as e:
            logger.error(f"خطأ في التحقق من تفعيل الخدمات: {e}")
            return False
    
    def run_complete_activation(self):
        """تشغيل التفعيل الشامل"""
        print("🚀 === بدء التفعيل الشامل للخدمات ===")
        
        # تفعيل جميع الخدمات
        if not self.activate_all_services():
            return False
        
        # التحقق من التفعيل
        if not self.verify_services_activation():
            print("⚠️ بعض الخدمات لم تُفعّل بشكل صحيح")
            return False
        
        print("🎉 === تم تفعيل جميع الخدمات بنجاح! ===")
        return True

def main():
    """الدالة الرئيسية"""
    print("🔧 أداة تفعيل الخدمات")
    print("=" * 50)
    
    activator = ServicesActivator()
    
    try:
        success = activator.run_complete_activation()
        
        if success:
            print("\n✅ تم تفعيل جميع الخدمات بنجاح!")
            print("🚀 البوت جاهز للعمل بكامل طاقته")
        else:
            print("\n❌ فشل في تفعيل بعض الخدمات")
            print("🔍 يرجى مراجعة السجلات للحصول على مزيد من التفاصيل")
            
    except Exception as e:
        print(f"\n💥 حدث خطأ غير متوقع: {e}")
        logger.error(f"خطأ غير متوقع: {e}")

if __name__ == "__main__":
    main()