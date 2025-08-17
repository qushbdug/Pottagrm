#!/usr/bin/env python3
"""
مُحسِّن قاعدة البيانات لحل مشكلة الأقفال
Database Optimizer to Fix Lock Issues
"""

import sqlite3
import os
import time
import shutil
import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def optimize_database():
    """تحسين قاعدة البيانات لحل مشكلة الأقفال"""
    db_path = "/workspace/yemen_net.db"
    backup_path = f"/workspace/yemen_net_backup_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    
    try:
        logger.info("🔧 بدء تحسين قاعدة البيانات...")
        
        # إنشاء نسخة احتياطية
        shutil.copy2(db_path, backup_path)
        logger.info(f"✅ تم إنشاء نسخة احتياطية: {backup_path}")
        
        # الاتصال بقاعدة البيانات مع timeout أطول
        conn = sqlite3.connect(db_path, timeout=30.0)
        conn.execute("PRAGMA journal_mode=WAL;")  # تمكين WAL mode
        conn.execute("PRAGMA synchronous=NORMAL;")  # تحسين الأداء
        conn.execute("PRAGMA cache_size=10000;")  # زيادة حجم الذاكرة المؤقتة
        conn.execute("PRAGMA temp_store=MEMORY;")  # استخدام الذاكرة للملفات المؤقتة
        conn.execute("PRAGMA mmap_size=268435456;")  # 256MB mmap
        
        # تنفيذ VACUUM لتنظيف قاعدة البيانات
        logger.info("🧹 تنظيف قاعدة البيانات...")
        conn.execute("VACUUM;")
        
        # تحليل قاعدة البيانات لتحسين الاستعلامات
        logger.info("📊 تحليل قاعدة البيانات...")
        conn.execute("ANALYZE;")
        
        conn.commit()
        conn.close()
        
        logger.info("✅ تم تحسين قاعدة البيانات بنجاح!")
        return True
        
    except Exception as e:
        logger.error(f"❌ خطأ في تحسين قاعدة البيانات: {e}")
        # استعادة النسخة الاحتياطية
        if os.path.exists(backup_path):
            shutil.copy2(backup_path, db_path)
            logger.info("🔄 تم استعادة النسخة الاحتياطية")
        return False

def add_database_indexes():
    """إضافة فهارس لتحسين الأداء"""
    db_path = "/workspace/yemen_net.db"
    
    try:
        conn = sqlite3.connect(db_path, timeout=30.0)
        cursor = conn.cursor()
        
        # فهارس للجداول الرئيسية
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_users_telegram_id ON users(telegram_id);",
            "CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);",
            "CREATE INDEX IF NOT EXISTS idx_transactions_from_user ON transactions(from_user);",
            "CREATE INDEX IF NOT EXISTS idx_transactions_to_user ON transactions(to_user);",
            "CREATE INDEX IF NOT EXISTS idx_transactions_created_at ON transactions(created_at);",
            "CREATE INDEX IF NOT EXISTS idx_networks_supplier_id ON networks(supplier_id);",
            "CREATE INDEX IF NOT EXISTS idx_networks_is_active ON networks(is_active);",
            "CREATE INDEX IF NOT EXISTS idx_coupons_coupon_code ON coupons(coupon_code);",
            "CREATE INDEX IF NOT EXISTS idx_coupons_is_used ON coupons(is_used);",
            "CREATE INDEX IF NOT EXISTS idx_coupons_created_by ON coupons(created_by);"
        ]
        
        logger.info("📝 إضافة فهارس قاعدة البيانات...")
        for index in indexes:
            try:
                cursor.execute(index)
                logger.info(f"✅ تم إنشاء فهرس: {index.split('ON')[1].split('(')[0].strip()}")
            except Exception as e:
                logger.warning(f"⚠️ فهرس موجود مسبقاً أو خطأ: {e}")
        
        conn.commit()
        conn.close()
        
        logger.info("✅ تم إضافة جميع الفهارس بنجاح!")
        return True
        
    except Exception as e:
        logger.error(f"❌ خطأ في إضافة الفهارس: {e}")
        return False

def check_database_health():
    """فحص صحة قاعدة البيانات"""
    db_path = "/workspace/yemen_net.db"
    
    try:
        conn = sqlite3.connect(db_path, timeout=10.0)
        cursor = conn.cursor()
        
        # فحص سلامة قاعدة البيانات
        cursor.execute("PRAGMA integrity_check;")
        integrity = cursor.fetchone()[0]
        
        # فحص الجداول
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        # فحص حجم قاعدة البيانات
        cursor.execute("PRAGMA page_count;")
        page_count = cursor.fetchone()[0]
        cursor.execute("PRAGMA page_size;")
        page_size = cursor.fetchone()[0]
        db_size_mb = (page_count * page_size) / (1024 * 1024)
        
        conn.close()
        
        print("🩺 === فحص صحة قاعدة البيانات ===")
        print(f"✅ سلامة البيانات: {integrity}")
        print(f"📊 عدد الجداول: {len(tables)}")
        print(f"💾 حجم قاعدة البيانات: {db_size_mb:.2f} MB")
        print(f"📄 عدد الصفحات: {page_count:,}")
        print(f"📏 حجم الصفحة: {page_size:,} بايت")
        
        return integrity == "ok"
        
    except Exception as e:
        logger.error(f"❌ خطأ في فحص قاعدة البيانات: {e}")
        return False

def main():
    """تنفيذ تحسين شامل لقاعدة البيانات"""
    print("🔧 ═══════════════════════════════════════════ 🔧")
    print("           مُحسِّن قاعدة البيانات")
    print("🔧 ═══════════════════════════════════════════ 🔧")
    print(f"⏰ الوقت: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # فحص صحة قاعدة البيانات قبل التحسين
    print("1️⃣ فحص صحة قاعدة البيانات...")
    health_before = check_database_health()
    print()
    
    if not health_before:
        print("❌ قاعدة البيانات تحتوي على أخطاء!")
        return
    
    # تحسين قاعدة البيانات
    print("2️⃣ تحسين قاعدة البيانات...")
    optimization_success = optimize_database()
    print()
    
    # إضافة فهارس
    print("3️⃣ إضافة فهارس الأداء...")
    indexes_success = add_database_indexes()
    print()
    
    # فحص نهائي
    print("4️⃣ فحص نهائي...")
    health_after = check_database_health()
    print()
    
    # النتيجة النهائية
    print("🎯 === النتيجة النهائية ===")
    if optimization_success and indexes_success and health_after:
        print("✅ تم تحسين قاعدة البيانات بنجاح!")
        print("📈 يُتوقع تحسن في الأداء وتقليل أقفال قاعدة البيانات")
    else:
        print("⚠️ التحسين مكتمل جزئياً - قد تحتاج مراجعة إضافية")
    
    print("🔧 ═══════════════════════════════════════════ 🔧")

if __name__ == "__main__":
    main()