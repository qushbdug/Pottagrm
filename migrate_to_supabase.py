#!/usr/bin/env python3
"""
Migrate to Supabase - الهجرة إلى Supabase
سكريبت لنقل البيانات من SQLite إلى Supabase
"""

import asyncio
import sys
import os
import sqlite3
from datetime import datetime

# إضافة مسار المشروع
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'bot_modules'))

async def test_supabase_connection():
    """اختبار الاتصال مع Supabase"""
    print("🔗 اختبار الاتصال مع Supabase...")
    
    try:
        from bot_modules.supabase_database import supabase_db
        
        # اختبار بسيط للاتصال
        result = supabase_db.supabase.table('users').select('count', count='exact').execute()
        
        print(f"✅ الاتصال مع Supabase نجح")
        print(f"📊 عدد المستخدمين الحالي في Supabase: {result.count if result.count else 0}")
        
        return True
        
    except Exception as e:
        print(f"❌ فشل الاتصال مع Supabase: {e}")
        print("💡 تأكد من:")
        print("  - صحة SUPABASE_URL")
        print("  - صحة SUPABASE_KEY") 
        print("  - أن المشروع نشط في Supabase")
        return False

async def create_supabase_schema():
    """إنشاء مخطط قاعدة البيانات في Supabase"""
    print("🏗️ إنشاء مخطط قاعدة البيانات...")
    
    try:
        from bot_modules.supabase_database import supabase_db
        
        # إنشاء الجداول
        await supabase_db.create_tables_schema()
        
        print("✅ تم إنشاء مخطط قاعدة البيانات بنجاح")
        return True
        
    except Exception as e:
        print(f"❌ فشل إنشاء المخطط: {e}")
        return False

def analyze_sqlite_data():
    """تحليل بيانات SQLite قبل النقل"""
    print("📊 تحليل بيانات SQLite...")
    
    try:
        conn = sqlite3.connect('yemen_net.db')
        cursor = conn.cursor()
        
        # إحصائيات الجداول
        tables_stats = {}
        
        tables_to_check = [
            'users', 'networks', 'network_cards', 'transactions', 
            'wallet_transactions', 'coupons', 'chart_of_accounts', 'general_ledger'
        ]
        
        for table in tables_to_check:
            try:
                cursor.execute(f'SELECT COUNT(*) FROM {table}')
                count = cursor.fetchone()[0]
                tables_stats[table] = count
                print(f"  📋 {table}: {count:,} سجل")
            except Exception as e:
                print(f"  ❌ {table}: خطأ - {e}")
                tables_stats[table] = 0
        
        total_records = sum(tables_stats.values())
        print(f"\n📊 إجمالي السجلات: {total_records:,}")
        
        # فحص سلامة البيانات
        print("\n🔍 فحص سلامة البيانات:")
        
        # فحص Foreign Keys
        cursor.execute('''
            SELECT COUNT(*) FROM transactions t
            LEFT JOIN users u1 ON t.from_user = u1.id
            LEFT JOIN users u2 ON t.to_user = u2.id
            WHERE u1.id IS NULL OR u2.id IS NULL
        ''')
        orphaned_transactions = cursor.fetchone()[0]
        
        if orphaned_transactions > 0:
            print(f"  ⚠️ معاملات معلقة: {orphaned_transactions}")
        else:
            print(f"  ✅ جميع المعاملات صحيحة")
        
        # فحص الأرصدة
        cursor.execute('SELECT COUNT(*) FROM users WHERE balance < 0')
        negative_balances = cursor.fetchone()[0]
        
        if negative_balances > 0:
            print(f"  ⚠️ أرصدة سالبة: {negative_balances}")
        else:
            print(f"  ✅ جميع الأرصدة إيجابية")
        
        conn.close()
        return tables_stats, total_records
        
    except Exception as e:
        print(f"❌ خطأ في تحليل البيانات: {e}")
        return {}, 0

async def perform_migration():
    """تنفيذ عملية الهجرة"""
    print("🚀 بدء عملية الهجرة...")
    
    try:
        from bot_modules.supabase_database import supabase_db
        
        # نقل البيانات
        await supabase_db.migrate_sqlite_data('yemen_net.db')
        
        print("✅ تمت الهجرة بنجاح!")
        return True
        
    except Exception as e:
        print(f"❌ فشلت الهجرة: {e}")
        return False

async def verify_migration():
    """التحقق من نجاح الهجرة"""
    print("🔍 التحقق من نجاح الهجرة...")
    
    try:
        from bot_modules.supabase_database import supabase_db
        
        # فحص عدد السجلات في كل جدول
        tables_to_check = ['users', 'networks', 'network_cards', 'transactions', 'coupons']
        
        for table in tables_to_check:
            try:
                result = supabase_db.supabase.table(table).select('count', count='exact').execute()
                count = result.count if result.count else 0
                print(f"  📋 {table}: {count:,} سجل في Supabase")
            except Exception as e:
                print(f"  ❌ {table}: خطأ - {e}")
        
        # اختبار استعلام بسيط
        result = supabase_db.supabase.table('users').select('full_name, balance').limit(3).execute()
        
        if result.data:
            print(f"\n👥 عينة من المستخدمين المنقولين:")
            for user in result.data:
                print(f"  - {user['full_name']}: {user['balance']:,.2f} ريال")
        
        return True
        
    except Exception as e:
        print(f"❌ خطأ في التحقق: {e}")
        return False

async def create_backup_before_migration():
    """إنشاء نسخة احتياطية قبل الهجرة"""
    print("💾 إنشاء نسخة احتياطية...")
    
    try:
        import shutil
        from datetime import datetime
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"yemen_net_backup_before_supabase_{timestamp}.db"
        
        shutil.copy2('yemen_net.db', backup_name)
        
        print(f"✅ تم إنشاء نسخة احتياطية: {backup_name}")
        return backup_name
        
    except Exception as e:
        print(f"❌ فشل إنشاء النسخة الاحتياطية: {e}")
        return None

async def main():
    """الدالة الرئيسية للهجرة"""
    print("🚀 بدء عملية الهجرة إلى Supabase")
    print("=" * 60)
    print(f"📅 التاريخ: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🎯 الهدف: https://poxdecozxjnzbmumvqzx.supabase.co")
    print("=" * 60)
    
    # الخطوات
    steps = [
        ("إنشاء نسخة احتياطية", create_backup_before_migration),
        ("تحليل بيانات SQLite", analyze_sqlite_data),
        ("اختبار اتصال Supabase", test_supabase_connection),
        ("إنشاء مخطط قاعدة البيانات", create_supabase_schema),
        ("تنفيذ الهجرة", perform_migration),
        ("التحقق من الهجرة", verify_migration)
    ]
    
    completed_steps = 0
    total_steps = len(steps)
    
    for step_name, step_func in steps:
        print(f"\n🔄 الخطوة {completed_steps + 1}/{total_steps}: {step_name}...")
        
        try:
            if asyncio.iscoroutinefunction(step_func):
                result = await step_func()
            else:
                result = step_func()
            
            if result or result is None:  # None يعني نجح بدون قيمة إرجاع
                completed_steps += 1
                print(f"✅ {step_name} - مكتملة")
            else:
                print(f"❌ {step_name} - فشلت")
                break
                
        except Exception as e:
            print(f"❌ {step_name} - خطأ: {e}")
            break
    
    print("\n" + "=" * 60)
    print("📊 نتائج الهجرة:")
    print(f"✅ مكتمل: {completed_steps}/{total_steps} خطوة")
    print(f"📈 معدل النجاح: {(completed_steps/total_steps)*100:.1f}%")
    
    if completed_steps == total_steps:
        print("\n🎉 **تمت الهجرة إلى Supabase بنجاح!**")
        print("✅ يمكنك الآن تشغيل البوت مع Supabase")
        print("🔄 سيتم تحديث ملفات التكوين تلقائياً")
    elif completed_steps >= total_steps * 0.8:
        print(f"\n✅ **الهجرة نجحت جزئياً**")
        print("⚠️ قد تحتاج لإكمال بعض الخطوات يدوياً")
    else:
        print(f"\n❌ **فشلت الهجرة**")
        print("💡 راجع الأخطاء أعلاه وحاول مرة أخرى")
    
    return completed_steps == total_steps

if __name__ == "__main__":
    asyncio.run(main())