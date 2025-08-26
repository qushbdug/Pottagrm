#!/usr/bin/env python3
"""
تشغيل الإصلاح الشامل للبوت
Run Complete Bot Fix
"""

import os
import sys
import time
import subprocess
from datetime import datetime

def run_script(script_name, description):
    """تشغيل سكريبت مع عرض التقدم"""
    print(f"\n{'='*60}")
    print(f"🚀 {description}")
    print(f"📁 الملف: {script_name}")
    print(f"⏰ الوقت: {datetime.now().strftime('%H:%M:%S')}")
    print(f"{'='*60}")
    
    try:
        # تشغيل السكريبت
        result = subprocess.run([sys.executable, script_name], 
                              capture_output=True, text=True, encoding='utf-8')
        
        if result.returncode == 0:
            print("✅ تم تنفيذ السكريبت بنجاح!")
            if result.stdout:
                print("📤 المخرجات:")
                print(result.stdout)
        else:
            print("❌ فشل في تنفيذ السكريبت!")
            if result.stderr:
                print("📤 رسائل الخطأ:")
                print(result.stderr)
            return False
            
    except Exception as e:
        print(f"💥 خطأ في تشغيل السكريبت: {e}")
        return False
    
    return True

def check_database_status():
    """فحص حالة قاعدة البيانات"""
    print(f"\n{'='*60}")
    print("🔍 فحص حالة قاعدة البيانات")
    print(f"{'='*60}")
    
    try:
        import sqlite3
        
        # فحص الاتصال
        conn = sqlite3.connect('yemen_net.db', timeout=30.0)
        cursor = conn.cursor()
        
        # فحص الجداول الرئيسية
        tables = ['users', 'networks', 'card_categories', 'cards', 'transactions']
        
        for table in tables:
            try:
                cursor.execute(f'SELECT COUNT(*) FROM {table}')
                count = cursor.fetchone()[0]
                print(f"📊 جدول {table}: {count} صف")
            except Exception as e:
                print(f"❌ جدول {table}: خطأ - {e}")
        
        # فحص سلامة قاعدة البيانات
        cursor.execute('PRAGMA integrity_check')
        integrity_result = cursor.fetchone()
        
        if integrity_result[0] == 'ok':
            print("✅ فحص السلامة: ناجح")
        else:
            print(f"❌ فحص السلامة: فشل - {integrity_result[0]}")
        
        conn.close()
        
    except Exception as e:
        print(f"💥 خطأ في فحص قاعدة البيانات: {e}")

def main():
    """الدالة الرئيسية"""
    print("🔧 === أداة الإصلاح الشامل للبوت ===")
    print("=" * 60)
    print("📋 هذه الأداة ستقوم بـ:")
    print("   1. إصلاح قاعدة البيانات")
    print("   2. حل تضارب الوحدات")
    print("   3. تفعيل جميع الخدمات")
    print("   4. فحص الحالة النهائية")
    print("=" * 60)
    
    # التأكد من وجود الملفات المطلوبة
    required_files = [
        'database_fix_and_optimization.py',
        'module_conflict_resolver.py',
        'services_fix_and_activation.py'
    ]
    
    missing_files = []
    for file in required_files:
        if not os.path.exists(file):
            missing_files.append(file)
    
    if missing_files:
        print("❌ الملفات التالية مفقودة:")
        for file in missing_files:
            print(f"   - {file}")
        print("🔍 يرجى التأكد من وجود جميع ملفات الإصلاح")
        return
    
    print("✅ جميع ملفات الإصلاح موجودة")
    
    # بدء عملية الإصلاح
    start_time = time.time()
    
    print(f"\n⏰ بدء الإصلاح في: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # الخطوة 1: إصلاح قاعدة البيانات
    if not run_script('database_fix_and_optimization.py', 'إصلاح قاعدة البيانات'):
        print("❌ فشل في إصلاح قاعدة البيانات")
        return
    
    # انتظار قليلة
    time.sleep(2)
    
    # الخطوة 2: حل تضارب الوحدات
    if not run_script('module_conflict_resolver.py', 'حل تضارب الوحدات'):
        print("❌ فشل في حل تضارب الوحدات")
        return
    
    # انتظار قليلة
    time.sleep(2)
    
    # الخطوة 3: تفعيل الخدمات
    if not run_script('services_fix_and_activation.py', 'تفعيل جميع الخدمات'):
        print("❌ فشل في تفعيل الخدمات")
        return
    
    # فحص الحالة النهائية
    check_database_status()
    
    # حساب الوقت المستغرق
    end_time = time.time()
    duration = end_time - start_time
    
    print(f"\n{'='*60}")
    print("🎉 === تم الإصلاح الشامل بنجاح! ===")
    print(f"⏱️ الوقت المستغرق: {duration:.1f} ثانية")
    print(f"📅 التاريخ: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")
    
    print("\n📋 ملخص ما تم إنجازه:")
    print("✅ تم إصلاح قاعدة البيانات")
    print("✅ تم حل تضارب الوحدات")
    print("✅ تم تفعيل جميع الخدمات")
    print("✅ تم فحص الحالة النهائية")
    
    print("\n🚀 البوت جاهز للعمل!")
    print("💡 يمكنك الآن تشغيل البوت باستخدام:")
    print("   python3 yemen_net_bot_unified.py")
    
    print("\n📁 الملفات المُنشأة:")
    created_files = [
        'yemen_net_bot_unified.py',
        'yemen_net_backup_*.db',
        'backups/'
    ]
    
    for file in created_files:
        if os.path.exists(file) or file.endswith('*') or file.endswith('/'):
            print(f"   📄 {file}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n🛑 تم إيقاف العملية بواسطة المستخدم")
    except Exception as e:
        print(f"\n💥 حدث خطأ غير متوقع: {e}")
        import traceback
        traceback.print_exc()