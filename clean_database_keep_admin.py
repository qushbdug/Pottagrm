#!/usr/bin/env python3
"""
تنظيف قاعدة البيانات مع الحفاظ على المشرف الأعلى فقط
Clean Database While Keeping Only Super Admin
"""

import sqlite3
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def clean_database_keep_super_admin():
    """مسح جميع البيانات مع الحفاظ على المشرف الأعلى فقط"""
    db_path = '/workspace/yemen_net.db'
    super_admin_telegram_id = 7684780523
    
    try:
        conn = sqlite3.connect(db_path, timeout=30)
        cursor = conn.cursor()
        
        print("🧹 بدء تنظيف قاعدة البيانات...")
        print(f"👑 الحفاظ على المشرف الأعلى: {super_admin_telegram_id}")
        
        # حفظ بيانات المشرف الأعلى
        cursor.execute('SELECT * FROM users WHERE telegram_id = ?', (super_admin_telegram_id,))
        super_admin_data = cursor.fetchone()
        
        if not super_admin_data:
            print("⚠️ المشرف الأعلى غير موجود، سيتم إنشاؤه")
            super_admin_data = None
        else:
            print(f"✅ تم العثور على المشرف الأعلى: {super_admin_data[2]}")  # full_name
        
        # مسح جميع الجداول
        tables_to_clean = [
            'transactions',
            'cards', 
            'card_categories',
            'networks',
            'coupons',
            'commissions',
            'settings',
            'withdrawal_requests',
            'referrals',
            'accounts',
            'user_accounts',
            'journal_entries',
            'journal_lines',
            'system_logs',
            'admin_notifications',
            'sales_reports',
            'product_inventory',
            'wallet_transactions',
            'payment_methods',
            'ratings',
            'user_ratings_summary',
            'notification_preferences',
            'smart_notifications',
            'user_permissions',
            'activity_logs',
            'promotions',
            'promotion_usage',
            'supplier_codes',
            'network_cards',
            'card_upload_batches',
            'card_categories_ref',
            'recharge_cards',
            'general_ledger',
            'journal_entry_lines',
            'accounting_audit_trail',
            'reconciliations',
            'fiscal_periods',
            'transaction_accounting_link',
            'offers'
        ]
        
        cleaned_count = 0
        
        for table in tables_to_clean:
            try:
                cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
                if cursor.fetchone():
                    cursor.execute(f"DELETE FROM {table}")
                    deleted_rows = cursor.rowcount
                    if deleted_rows > 0:
                        print(f"  ✅ {table}: مسح {deleted_rows} سجل")
                        cleaned_count += deleted_rows
            except Exception as e:
                print(f"  ⚠️ خطأ في مسح {table}: {e}")
        
        # مسح جميع المستخدمين عدا المشرف الأعلى
        cursor.execute('DELETE FROM users WHERE telegram_id != ?', (super_admin_telegram_id,))
        deleted_users = cursor.rowcount
        print(f"  👥 مسح {deleted_users} مستخدم (عدا المشرف الأعلى)")
        
        # إعادة إنشاء المشرف الأعلى إذا لم يكن موجوداً
        if not super_admin_data:
            cursor.execute('''
                INSERT INTO users (telegram_id, full_name, phone, role, balance, is_active, created_at, wallet_number, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?, CURRENT_TIMESTAMP)
            ''', (
                super_admin_telegram_id,
                'Master 👾',
                '777777777',
                'super_admin',
                1000000.0,
                1,
                '768478052'
            ))
            print("✅ تم إعادة إنشاء المشرف الأعلى")
        else:
            # تحديث بيانات المشرف الأعلى للتأكد
            cursor.execute('''
                UPDATE users 
                SET role = 'super_admin', balance = 1000000.0, is_active = 1, updated_at = CURRENT_TIMESTAMP
                WHERE telegram_id = ?
            ''', (super_admin_telegram_id,))
            print("✅ تم تحديث بيانات المشرف الأعلى")
        
        # إعادة تعيين العدادات التلقائية
        print("\n🔄 إعادة تعيين العدادات التلقائية...")
        cursor.execute("UPDATE sqlite_sequence SET seq = 1 WHERE name = 'users'")
        cursor.execute("UPDATE sqlite_sequence SET seq = 0 WHERE name != 'users'")
        
        conn.commit()
        conn.close()
        
        print(f"\n🎉 تم تنظيف قاعدة البيانات بنجاح!")
        print(f"✅ مسح {cleaned_count + deleted_users} سجل")
        print("✅ تم الحفاظ على المشرف الأعلى فقط")
        
        return True
        
    except Exception as e:
        logger.error(f"خطأ في تنظيف قاعدة البيانات: {e}")
        return False

def verify_clean_database():
    """التحقق من نظافة قاعدة البيانات"""
    try:
        conn = sqlite3.connect('/workspace/yemen_net.db', timeout=30)
        cursor = conn.cursor()
        
        print("\n🔍 التحقق من نظافة قاعدة البيانات...")
        
        # فحص المستخدمين
        cursor.execute('SELECT COUNT(*) FROM users')
        users_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT telegram_id, full_name, role, balance FROM users')
        users = cursor.fetchall()
        
        print(f"👥 إجمالي المستخدمين: {users_count}")
        
        for user in users:
            telegram_id, full_name, role, balance = user
            print(f"  • {full_name} (ID: {telegram_id}) - {role} - {balance:,.0f} ريال")
        
        # فحص الجداول الأخرى
        main_tables = ['networks', 'transactions', 'cards', 'card_categories']
        for table in main_tables:
            cursor.execute(f'SELECT COUNT(*) FROM {table}')
            count = cursor.fetchone()[0]
            print(f"📊 {table}: {count} سجل")
        
        conn.close()
        
        if users_count == 1:
            print("✅ قاعدة البيانات نظيفة - المشرف الأعلى فقط")
            return True
        else:
            print(f"⚠️ يوجد {users_count} مستخدم")
            return False
        
    except Exception as e:
        logger.error(f"خطأ في التحقق من قاعدة البيانات: {e}")
        return False

def main():
    """الدالة الرئيسية"""
    print("🧹 بدء تنظيف قاعدة البيانات مع الحفاظ على المشرف الأعلى...")
    
    if clean_database_keep_super_admin():
        print("✅ تم تنظيف قاعدة البيانات")
        
        if verify_clean_database():
            print("✅ التحقق مكتمل - قاعدة البيانات نظيفة")
            return True
        else:
            print("⚠️ قد تحتاج تنظيف إضافي")
            return False
    else:
        print("❌ فشل في تنظيف قاعدة البيانات")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)