#!/usr/bin/env python3
"""
إصلاح شامل لقاعدة البيانات وحل جميع المشاكل
Comprehensive Database Fix and Optimization
"""

import sqlite3
import logging
import os
import shutil
from datetime import datetime
import random

# إعداد التسجيل
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseFixer:
    def __init__(self, db_path='yemen_net.db'):
        self.db_path = db_path
        self.backup_path = f"yemen_net_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        
    def create_backup(self):
        """إنشاء نسخة احتياطية من قاعدة البيانات"""
        try:
            shutil.copy2(self.db_path, self.backup_path)
            print(f"✅ تم إنشاء نسخة احتياطية: {self.backup_path}")
            return True
        except Exception as e:
            print(f"❌ فشل في إنشاء النسخة الاحتياطية: {e}")
            return False
    
    def fix_database_structure(self):
        """إصلاح هيكل قاعدة البيانات"""
        print("🔧 === إصلاح هيكل قاعدة البيانات ===")
        
        try:
            conn = sqlite3.connect(self.db_path, timeout=30.0)
            cursor = conn.cursor()
            
            # تفعيل المفاتيح الخارجية
            cursor.execute('PRAGMA foreign_keys = ON')
            
            # تحسين إعدادات قاعدة البيانات
            cursor.execute('PRAGMA journal_mode = WAL')
            cursor.execute('PRAGMA synchronous = NORMAL')
            cursor.execute('PRAGMA cache_size = 50000')
            cursor.execute('PRAGMA temp_store = MEMORY')
            
            # إصلاح جدول users
            print("🔧 إصلاح جدول users...")
            self._fix_users_table(cursor)
            
            # إصلاح جدول networks
            print("🔧 إصلاح جدول networks...")
            self._fix_networks_table(cursor)
            
            # إصلاح جدول card_categories
            print("🔧 إصلاح جدول card_categories...")
            self._fix_card_categories_table(cursor)
            
            # إصلاح جدول cards
            print("🔧 إصلاح جدول cards...")
            self._fix_cards_table(cursor)
            
            # إصلاح جدول transactions
            print("🔧 إصلاح جدول transactions...")
            self._fix_transactions_table(cursor)
            
            # إنشاء الجداول المفقودة
            print("🔧 إنشاء الجداول المفقودة...")
            self._create_missing_tables(cursor)
            
            # إصلاح المفاتيح الخارجية
            print("🔧 إصلاح المفاتيح الخارجية...")
            self._fix_foreign_keys(cursor)
            
            # إنشاء الفهارس
            print("🔧 إنشاء الفهارس...")
            self._create_indexes(cursor)
            
            conn.commit()
            conn.close()
            
            print("✅ تم إصلاح هيكل قاعدة البيانات بنجاح")
            return True
            
        except Exception as e:
            logger.error(f"خطأ في إصلاح هيكل قاعدة البيانات: {e}")
            return False
    
    def _fix_users_table(self, cursor):
        """إصلاح جدول المستخدمين"""
        # إضافة الأعمدة المفقودة
        columns_to_add = [
            ('wallet_number', 'TEXT UNIQUE'),
            ('last_activity', 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'),
            ('is_verified', 'BOOLEAN DEFAULT 0'),
            ('total_purchases', 'INTEGER DEFAULT 0'),
            ('total_spent', 'REAL DEFAULT 0.0'),
            ('updated_at', 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP')
        ]
        
        for col_name, col_def in columns_to_add:
            try:
                cursor.execute(f'ALTER TABLE users ADD COLUMN {col_name} {col_def}')
                print(f"  ✅ تم إضافة العمود: {col_name}")
            except sqlite3.OperationalError:
                print(f"  ℹ️ العمود موجود بالفعل: {col_name}")
        
        # إنشاء أرقام المحفظة للمستخدمين الذين لا يملكونها
        cursor.execute("SELECT id FROM users WHERE wallet_number IS NULL OR wallet_number = ''")
        missing_wallets = cursor.fetchall()
        
        for (user_id,) in missing_wallets:
            wallet_number = self._generate_unique_wallet_number(cursor)
            cursor.execute('UPDATE users SET wallet_number = ? WHERE id = ?', (wallet_number, user_id))
            print(f"  ✅ تم إنشاء محفظة للمستخدم {user_id}: {wallet_number}")
    
    def _fix_networks_table(self, cursor):
        """إصلاح جدول الشبكات"""
        # إضافة الأعمدة المفقودة
        columns_to_add = [
            ('network_code', 'TEXT UNIQUE'),
            ('is_approved', 'BOOLEAN DEFAULT 0'),
            ('approved_at', 'TIMESTAMP'),
            ('approved_by', 'INTEGER'),
            ('updated_at', 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP')
        ]
        
        for col_name, col_def in columns_to_add:
            try:
                cursor.execute(f'ALTER TABLE networks ADD COLUMN {col_name} {col_def}')
                print(f"  ✅ تم إضافة العمود: {col_name}")
            except sqlite3.OperationalError:
                print(f"  ℹ️ العمود موجود بالفعل: {col_name}")
        
        # إنشاء رموز الشبكات للمستخدمين الذين لا يملكونها
        cursor.execute("SELECT id FROM networks WHERE network_code IS NULL OR network_code = ''")
        missing_codes = cursor.fetchall()
        
        for (network_id,) in missing_codes:
            network_code = self._generate_unique_network_code(cursor)
            cursor.execute('UPDATE networks SET network_code = ? WHERE id = ?', (network_code, network_id))
            print(f"  ✅ تم إنشاء رمز للشبكة {network_id}: {network_code}")
        
        # تحديث الشبكات لتكون معتمدة ومفعلة
        cursor.execute("""
            UPDATE networks 
            SET is_approved = 1, is_active = 1, approved_at = CURRENT_TIMESTAMP
            WHERE is_approved IS NULL OR is_approved = 0
        """)
        
        updated_rows = cursor.rowcount
        if updated_rows > 0:
            print(f"  ✅ تم تفعيل {updated_rows} شبكة")
    
    def _fix_card_categories_table(self, cursor):
        """إصلاح جدول فئات الكروت"""
        # إضافة الأعمدة المفقودة
        columns_to_add = [
            ('category_name', 'TEXT'),
            ('description', 'TEXT'),
            ('updated_at', 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP')
        ]
        
        for col_name, col_def in columns_to_add:
            try:
                cursor.execute(f'ALTER TABLE card_categories ADD COLUMN {col_name} {col_def}')
                print(f"  ✅ تم إضافة العمود: {col_name}")
            except sqlite3.OperationalError:
                print(f"  ℹ️ العمود موجود بالفعل: {col_name}")
        
        # إنشاء فئات افتراضية للشبكات الموجودة
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
                # التحقق من وجود الفئة
                cursor.execute("""
                    SELECT id FROM card_categories 
                    WHERE network_id = ? AND value = ?
                """, (network_id, category['value']))
                
                if not cursor.fetchone():
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
                    print(f"  ✅ تم إنشاء فئة {category['name']} للشبكة {network_name}")
    
    def _fix_cards_table(self, cursor):
        """إصلاح جدول الكروت"""
        # إضافة الأعمدة المفقودة
        columns_to_add = [
            ('expiry_date', 'TEXT'),
            ('used_at', 'TIMESTAMP'),
            ('used_by', 'INTEGER')
        ]
        
        for col_name, col_def in columns_to_add:
            try:
                cursor.execute(f'ALTER TABLE cards ADD COLUMN {col_name} {col_def}')
                print(f"  ✅ تم إضافة العمود: {col_name}")
            except sqlite3.OperationalError:
                print(f"  ℹ️ العمود موجود بالفعل: {col_name}")
        
        # إنشاء كروت افتراضية للفئات الموجودة
        cursor.execute("""
            SELECT cc.id, cc.network_id, cc.value, cc.name, n.name as network_name
            FROM card_categories cc
            JOIN networks n ON cc.network_id = n.id
            WHERE cc.is_available = 1
        """)
        categories = cursor.fetchall()
        
        for category_id, network_id, value, category_name, network_name in categories:
            # التحقق من وجود كروت لهذه الفئة
            cursor.execute("SELECT COUNT(*) FROM cards WHERE category_id = ?", (category_id,))
            existing_cards = cursor.fetchone()[0]
            
            if existing_cards == 0:
                # إنشاء 50 كرت افتراضي
                for i in range(50):
                    card_code = f"{network_id:03d}{value:03d}{i+1:03d}"
                    cursor.execute("""
                        INSERT INTO cards (id, category_id, code, is_used, added_at)
                        VALUES (?, ?, ?, 0, CURRENT_TIMESTAMP)
                    """, (f"card_{category_id}_{i+1}", category_id, card_code))
                
                print(f"  ✅ تم إنشاء 50 كرت للفئة {category_name} في {network_name}")
    
    def _fix_transactions_table(self, cursor):
        """إصلاح جدول المعاملات"""
        # إضافة الأعمدة المفقودة
        columns_to_add = [
            ('is_withdrawable', 'BOOLEAN DEFAULT 0'),
            ('commission_amount', 'REAL DEFAULT 0.0')
        ]
        
        for col_name, col_def in columns_to_add:
            try:
                cursor.execute(f'ALTER TABLE transactions ADD COLUMN {col_name} {col_def}')
                print(f"  ✅ تم إضافة العمود: {col_name}")
            except sqlite3.OperationalError:
                print(f"  ℹ️ العمود موجود بالفعل: {col_name}")
    
    def _create_missing_tables(self, cursor):
        """إنشاء الجداول المفقودة"""
        # جدول activity_logs
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
        
        # جدول smart_notifications
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS smart_notifications (
                id TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                notification_type TEXT NOT NULL,
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                priority TEXT DEFAULT 'normal',
                is_read BOOLEAN DEFAULT 0,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        ''')
        
        # جدول user_ratings_summary
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
        
        # جدول promotions
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
                FOREIGN KEY(created_by) REFERENCES users(id)
            )
        ''')
        
        print("  ✅ تم إنشاء الجداول المفقودة")
    
    def _fix_foreign_keys(self, cursor):
        """إصلاح المفاتيح الخارجية"""
        # إصلاح supplier_id في جدول networks
        cursor.execute("""
            UPDATE networks 
            SET supplier_id = created_by 
            WHERE supplier_id IS NULL AND created_by IS NOT NULL
        """)
        
        # إصلاح network_id في جدول card_categories
        cursor.execute("""
            UPDATE card_categories 
            SET network_id = (
                SELECT id FROM networks 
                WHERE networks.id = card_categories.network_id
            )
            WHERE network_id IS NOT NULL
        """)
        
        print("  ✅ تم إصلاح المفاتيح الخارجية")
    
    def _create_indexes(self, cursor):
        """إنشاء الفهارس لتحسين الأداء"""
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_users_telegram_id ON users(telegram_id)",
            "CREATE INDEX IF NOT EXISTS idx_users_wallet_number ON users(wallet_number)",
            "CREATE INDEX IF NOT EXISTS idx_users_phone ON users(phone)",
            "CREATE INDEX IF NOT EXISTS idx_networks_supplier_id ON networks(supplier_id)",
            "CREATE INDEX IF NOT EXISTS idx_networks_network_code ON networks(network_code)",
            "CREATE INDEX IF NOT EXISTS idx_card_categories_network_id ON card_categories(network_id)",
            "CREATE INDEX IF NOT EXISTS idx_cards_category_id ON cards(category_id)",
            "CREATE INDEX IF NOT EXISTS idx_cards_is_used ON cards(is_used)",
            "CREATE INDEX IF NOT EXISTS idx_transactions_from_user ON transactions(from_user)",
            "CREATE INDEX IF NOT EXISTS idx_transactions_type ON transactions(type)",
            "CREATE INDEX IF NOT EXISTS idx_transactions_created_at ON transactions(created_at)"
        ]
        
        for index in indexes:
            try:
                cursor.execute(index)
            except:
                pass
        
        print("  ✅ تم إنشاء الفهارس")
    
    def _generate_unique_wallet_number(self, cursor):
        """إنشاء رقم محفظة فريد"""
        while True:
            wallet_number = '79' + ''.join(str(random.randint(0, 9)) for _ in range(7))
            cursor.execute('SELECT 1 FROM users WHERE wallet_number = ?', (wallet_number,))
            if not cursor.fetchone():
                return wallet_number
    
    def _generate_unique_network_code(self, cursor):
        """إنشاء رمز شبكة فريد"""
        while True:
            network_code = ''.join(str(random.randint(0, 9)) for _ in range(6))
            cursor.execute('SELECT 1 FROM networks WHERE network_code = ?', (network_code,))
            if not cursor.fetchone():
                return network_code
    
    def populate_sample_data(self):
        """إضافة بيانات تجريبية للاختبار"""
        print("🔧 === إضافة بيانات تجريبية ===")
        
        try:
            conn = sqlite3.connect(self.db_path, timeout=30.0)
            cursor = conn.cursor()
            
            # إضافة كروت تجريبية
            cursor.execute("SELECT COUNT(*) FROM cards")
            total_cards = cursor.fetchone()[0]
            
            if total_cards == 0:
                print("  📝 إضافة كروت تجريبية...")
                
                # الحصول على الفئات الموجودة
                cursor.execute("""
                    SELECT cc.id, cc.network_id, cc.value, n.name
                    FROM card_categories cc
                    JOIN networks n ON cc.network_id = n.id
                    LIMIT 10
                """)
                categories = cursor.fetchall()
                
                for category_id, network_id, value, network_name in categories:
                    # إنشاء 20 كرت لكل فئة
                    for i in range(20):
                        card_code = f"{network_id:03d}{value:03d}{i+1:03d}"
                        cursor.execute("""
                            INSERT INTO cards (id, category_id, code, is_used, added_at)
                            VALUES (?, ?, ?, 0, CURRENT_TIMESTAMP)
                        """, (f"card_{category_id}_{i+1}", category_id, card_code))
                    
                    print(f"    ✅ تم إضافة 20 كرت للفئة {value} ريال في {network_name}")
            
            # إضافة معاملات تجريبية
            cursor.execute("SELECT COUNT(*) FROM transactions")
            total_transactions = cursor.fetchone()[0]
            
            if total_transactions == 0:
                print("  📝 إضافة معاملات تجريبية...")
                
                # الحصول على المستخدمين
                cursor.execute("SELECT id FROM users LIMIT 3")
                users = cursor.fetchall()
                
                if len(users) >= 2:
                    user1_id = users[0][0]
                    user2_id = users[1][0]
                    
                    # إضافة معاملات تجريبية
                    sample_transactions = [
                        (user1_id, user2_id, 50.0, 'transfer', 'تحويل تجريبي'),
                        (user2_id, user1_id, 25.0, 'transfer', 'تحويل تجريبي'),
                        (user1_id, None, 100.0, 'recharge', 'شحن تجريبي')
                    ]
                    
                    for from_user, to_user, amount, txn_type, description in sample_transactions:
                        cursor.execute("""
                            INSERT INTO transactions (id, from_user, to_user, amount, type, description, created_at)
                            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                        """, (f"txn_{random.randint(1000, 9999)}", from_user, to_user, amount, txn_type, description))
                    
                    print("    ✅ تم إضافة معاملات تجريبية")
            
            conn.commit()
            conn.close()
            
            print("✅ تم إضافة البيانات التجريبية بنجاح")
            return True
            
        except Exception as e:
            logger.error(f"خطأ في إضافة البيانات التجريبية: {e}")
            return False
    
    def verify_database_integrity(self):
        """التحقق من سلامة قاعدة البيانات"""
        print("🔍 === التحقق من سلامة قاعدة البيانات ===")
        
        try:
            conn = sqlite3.connect(self.db_path, timeout=30.0)
            cursor = conn.cursor()
            
            # فحص المفاتيح الخارجية
            cursor.execute('PRAGMA foreign_key_check')
            fk_violations = cursor.fetchall()
            
            if fk_violations:
                print(f"⚠️ وجدت {len(fk_violations)} انتهاكات للمفاتيح الخارجية:")
                for violation in fk_violations:
                    print(f"  - {violation}")
            else:
                print("✅ لا توجد انتهاكات للمفاتيح الخارجية")
            
            # فحص سلامة قاعدة البيانات
            cursor.execute('PRAGMA integrity_check')
            integrity_result = cursor.fetchone()
            
            if integrity_result[0] == 'ok':
                print("✅ فحص السلامة: ناجح")
            else:
                print(f"❌ فحص السلامة: فشل - {integrity_result[0]}")
            
            # إحصائيات قاعدة البيانات
            tables = ['users', 'networks', 'card_categories', 'cards', 'transactions']
            
            for table in tables:
                try:
                    cursor.execute(f'SELECT COUNT(*) FROM {table}')
                    count = cursor.fetchone()[0]
                    print(f"📊 جدول {table}: {count} صف")
                except:
                    print(f"❌ جدول {table}: غير موجود")
            
            conn.close()
            
            return len(fk_violations) == 0 and integrity_result[0] == 'ok'
            
        except Exception as e:
            logger.error(f"خطأ في فحص سلامة قاعدة البيانات: {e}")
            return False
    
    def run_complete_fix(self):
        """تشغيل الإصلاح الشامل"""
        print("🚀 === بدء الإصلاح الشامل لقاعدة البيانات ===")
        
        # إنشاء نسخة احتياطية
        if not self.create_backup():
            return False
        
        # إصلاح هيكل قاعدة البيانات
        if not self.fix_database_structure():
            return False
        
        # إضافة بيانات تجريبية
        if not self.populate_sample_data():
            print("⚠️ فشل في إضافة البيانات التجريبية، لكن الإصلاح الأساسي نجح")
        
        # التحقق من السلامة
        if not self.verify_database_integrity():
            print("⚠️ فشل في فحص السلامة، قد تكون هناك مشاكل متبقية")
            return False
        
        print("🎉 === تم الإصلاح الشامل بنجاح! ===")
        return True

def main():
    """الدالة الرئيسية"""
    print("🔧 أداة إصلاح قاعدة البيانات الشاملة")
    print("=" * 50)
    
    fixer = DatabaseFixer()
    
    try:
        success = fixer.run_complete_fix()
        
        if success:
            print("\n✅ تم إصلاح قاعدة البيانات بنجاح!")
            print("📊 يمكنك الآن تشغيل البوت بدون مشاكل")
        else:
            print("\n❌ فشل في إصلاح قاعدة البيانات")
            print("🔍 يرجى مراجعة السجلات للحصول على مزيد من التفاصيل")
            
    except Exception as e:
        print(f"\n💥 حدث خطأ غير متوقع: {e}")
        logger.error(f"خطأ غير متوقع: {e}")

if __name__ == "__main__":
    main()