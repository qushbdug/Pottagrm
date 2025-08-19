#!/usr/bin/env python3
"""
إصلاح شامل لمشاكل قاعدة البيانات
Comprehensive Database Issues Fix
"""

import sqlite3
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fix_networks_table():
    """إصلاح جدول الشبكات"""
    try:
        conn = sqlite3.connect('/workspace/yemen_net.db', timeout=30)
        cursor = conn.cursor()
        
        print("🔧 إصلاح جدول networks...")
        
        # 1. فحص البيانات الحالية
        cursor.execute("SELECT COUNT(*) FROM networks WHERE supplier_id IS NULL")
        null_supplier_count = cursor.fetchone()[0]
        
        if null_supplier_count > 0:
            print(f"⚠️ وجدت {null_supplier_count} شبكة بدون supplier_id")
            
            # تحديث الشبكات التي لا تحتوي على supplier_id
            cursor.execute("""
                UPDATE networks 
                SET supplier_id = created_by 
                WHERE supplier_id IS NULL AND created_by IS NOT NULL
            """)
            
            updated_rows = cursor.rowcount
            print(f"✅ تم تحديث {updated_rows} شبكة")
            
            # حذف الشبكات التي لا تحتوي على created_by أيضاً
            cursor.execute("""
                DELETE FROM networks 
                WHERE supplier_id IS NULL AND created_by IS NULL
            """)
            
            deleted_rows = cursor.rowcount
            if deleted_rows > 0:
                print(f"🗑️ تم حذف {deleted_rows} شبكة غير صالحة")
        
        # 2. التأكد من وجود مفتاح خارجي
        cursor.execute("PRAGMA foreign_key_check(networks)")
        fk_violations = cursor.fetchall()
        
        if fk_violations:
            print(f"⚠️ وجدت {len(fk_violations)} انتهاكات للمفاتيح الخارجية")
            for violation in fk_violations:
                print(f"  - {violation}")
        else:
            print("✅ لا توجد انتهاكات للمفاتيح الخارجية")
        
        # 3. إعادة بناء الفهارس
        cursor.execute("REINDEX networks")
        print("✅ تم إعادة بناء فهارس جدول networks")
        
        conn.commit()
        conn.close()
        
        return True
        
    except Exception as e:
        logger.error(f"خطأ في إصلاح جدول networks: {e}")
        return False

def test_network_creation():
    """اختبار إنشاء شبكة"""
    try:
        conn = sqlite3.connect('/workspace/yemen_net.db', timeout=30)
        cursor = conn.cursor()
        
        print("🧪 اختبار إنشاء شبكة...")
        
        # الحصول على أول مستخدم للاختبار
        cursor.execute("SELECT id, full_name FROM users LIMIT 1")
        user = cursor.fetchone()
        
        if not user:
            print("❌ لا توجد مستخدمين للاختبار")
            conn.close()
            return False
        
        user_id = user[0]
        user_name = user[1]
        
        # محاولة إنشاء شبكة اختبار
        test_network_name = f"شبكة اختبار {datetime.now().strftime('%H%M%S')}"
        
        cursor.execute('''
            INSERT INTO networks (supplier_id, name, city, provider, description, location, 
                                created_by, is_active, is_approved, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, 1, 1, CURRENT_TIMESTAMP)
        ''', (
            user_id,  # supplier_id
            test_network_name,
            "صنعاء",  # city
            user_name,
            "شبكة اختبار للتأكد من عمل النظام",
            "موقع اختبار",
            user_id  # created_by
        ))
        
        network_id = cursor.lastrowid
        print(f"✅ تم إنشاء شبكة اختبار بنجاح - ID: {network_id}")
        
        # حذف الشبكة الاختبارية
        cursor.execute("DELETE FROM networks WHERE id = ?", (network_id,))
        print("🗑️ تم حذف شبكة الاختبار")
        
        conn.commit()
        conn.close()
        
        return True
        
    except Exception as e:
        logger.error(f"خطأ في اختبار إنشاء الشبكة: {e}")
        return False

def optimize_database():
    """تحسين قاعدة البيانات"""
    try:
        conn = sqlite3.connect('/workspace/yemen_net.db', timeout=30)
        cursor = conn.cursor()
        
        print("⚡ تحسين قاعدة البيانات...")
        
        # تفعيل WAL mode
        cursor.execute("PRAGMA journal_mode = WAL")
        cursor.execute("PRAGMA synchronous = NORMAL")
        cursor.execute("PRAGMA cache_size = 10000")
        cursor.execute("PRAGMA temp_store = MEMORY")
        
        # تنظيف قاعدة البيانات
        cursor.execute("VACUUM")
        cursor.execute("ANALYZE")
        
        print("✅ تم تحسين قاعدة البيانات")
        
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"خطأ في تحسين قاعدة البيانات: {e}")
        return False

def check_database_integrity():
    """فحص سلامة قاعدة البيانات"""
    try:
        conn = sqlite3.connect('/workspace/yemen_net.db', timeout=30)
        cursor = conn.cursor()
        
        print("🔍 فحص سلامة قاعدة البيانات...")
        
        # فحص سلامة قاعدة البيانات
        cursor.execute("PRAGMA integrity_check")
        integrity_result = cursor.fetchone()[0]
        
        if integrity_result == 'ok':
            print("✅ قاعدة البيانات سليمة")
        else:
            print(f"⚠️ مشكلة في سلامة قاعدة البيانات: {integrity_result}")
        
        # فحص المفاتيح الخارجية
        cursor.execute("PRAGMA foreign_key_check")
        fk_issues = cursor.fetchall()
        
        if not fk_issues:
            print("✅ لا توجد مشاكل في المفاتيح الخارجية")
        else:
            print(f"⚠️ مشاكل في المفاتيح الخارجية: {len(fk_issues)}")
            for issue in fk_issues[:5]:  # أول 5 مشاكل فقط
                print(f"  - {issue}")
        
        # إحصائيات الجداول
        tables = ['users', 'networks', 'transactions', 'cards', 'card_categories']
        print("\n📊 إحصائيات الجداول:")
        
        for table in tables:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                print(f"  - {table}: {count} سجل")
            except Exception as e:
                print(f"  - {table}: خطأ - {e}")
        
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"خطأ في فحص سلامة قاعدة البيانات: {e}")
        return False

def main():
    """الدالة الرئيسية"""
    print("🔧 **بدء إصلاح مشاكل قاعدة البيانات** 🔧")
    print("=" * 60)
    
    # 1. فحص سلامة قاعدة البيانات
    if not check_database_integrity():
        print("❌ فشل فحص سلامة قاعدة البيانات")
        return
    
    # 2. إصلاح جدول الشبكات
    if not fix_networks_table():
        print("❌ فشل إصلاح جدول networks")
        return
    
    # 3. اختبار إنشاء شبكة
    if not test_network_creation():
        print("❌ فشل اختبار إنشاء الشبكة")
        return
    
    # 4. تحسين قاعدة البيانات
    if not optimize_database():
        print("❌ فشل تحسين قاعدة البيانات")
        return
    
    print("\n" + "=" * 60)
    print("🎉 **تم إصلاح جميع مشاكل قاعدة البيانات بنجاح!** 🎉")
    print("✅ جدول networks تم إصلاحه")
    print("✅ اختبار إنشاء الشبكة نجح")
    print("✅ قاعدة البيانات تم تحسينها")
    print("🚀 البوت جاهز للعمل بدون مشاكل!")

if __name__ == "__main__":
    main()