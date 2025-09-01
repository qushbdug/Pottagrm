#!/usr/bin/env python3
"""
Manual Migration - الهجرة اليدوية
نقل البيانات من SQLite إلى Supabase يدوياً
"""

import sqlite3
import sys
import os
import json
from datetime import datetime
from typing import Dict, List, Any

# إضافة مسار المشروع
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'bot_modules'))

def export_sqlite_data():
    """تصدير بيانات SQLite إلى ملفات JSON"""
    print("📤 تصدير بيانات SQLite...")
    
    conn = sqlite3.connect('yemen_net.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        # إنشاء مجلد للتصدير
        export_dir = 'sqlite_export'
        os.makedirs(export_dir, exist_ok=True)
        
        # الجداول المراد تصديرها
        tables_to_export = [
            'users', 'networks', 'network_cards', 'transactions', 
            'wallet_transactions', 'coupons', 'chart_of_accounts', 'general_ledger'
        ]
        
        exported_data = {}
        
        for table in tables_to_export:
            try:
                cursor.execute(f'SELECT * FROM {table}')
                rows = cursor.fetchall()
                
                # تحويل إلى قائمة من القواميس
                table_data = []
                for row in rows:
                    row_dict = dict(row)
                    # تحويل التواريخ إلى نصوص
                    for key, value in row_dict.items():
                        if isinstance(value, datetime):
                            row_dict[key] = value.isoformat()
                    table_data.append(row_dict)
                
                exported_data[table] = table_data
                
                # حفظ في ملف منفصل
                with open(f'{export_dir}/{table}.json', 'w', encoding='utf-8') as f:
                    json.dump(table_data, f, ensure_ascii=False, indent=2)
                
                print(f"  ✅ {table}: {len(table_data)} سجل")
                
            except Exception as e:
                print(f"  ❌ {table}: خطأ - {e}")
                exported_data[table] = []
        
        # حفظ ملف شامل
        with open(f'{export_dir}/complete_export.json', 'w', encoding='utf-8') as f:
            json.dump(exported_data, f, ensure_ascii=False, indent=2)
        
        # إحصائيات التصدير
        total_records = sum(len(data) for data in exported_data.values())
        
        print(f"\n📊 ملخص التصدير:")
        print(f"📁 مجلد التصدير: {export_dir}")
        print(f"📋 الجداول المصدرة: {len(exported_data)}")
        print(f"📊 إجمالي السجلات: {total_records:,}")
        
        return exported_data, export_dir
        
    except Exception as e:
        print(f"❌ خطأ في التصدير: {e}")
        return {}, None
    finally:
        conn.close()

def create_supabase_import_script(exported_data: Dict, export_dir: str):
    """إنشاء سكريبت استيراد لـ Supabase"""
    print("📝 إنشاء سكريبت الاستيراد...")
    
    try:
        script_content = '''#!/usr/bin/env python3
"""
Supabase Import Script - سكريبت استيراد Supabase
يستورد البيانات المصدرة إلى Supabase
"""

import json
import sys
import os
from supabase import create_client

# إعدادات Supabase
SUPABASE_URL = "https://poxdecozxjnzbmumvqzx.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InBveGRlY296eGpuemJtdW12cXp4Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTY2ODIzNDIsImV4cCI6MjA3MjI1ODM0Mn0.OpoVMldNCBqIkhSSvic29LlSrhfmOIqt7NBp5v27CUk"

def import_to_supabase():
    """استيراد البيانات إلى Supabase"""
    print("📤 بدء استيراد البيانات إلى Supabase...")
    
    # إنشاء عميل Supabase
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    # ترتيب الجداول حسب التبعيات
    tables_order = ['users', 'networks', 'network_cards', 'chart_of_accounts', 
                   'transactions', 'wallet_transactions', 'coupons', 'general_ledger']
    
    imported_counts = {}
    
    for table in tables_order:
        print(f"\\n📋 استيراد جدول {table}...")
        
        try:
            # قراءة البيانات من ملف JSON
            with open(f'sqlite_export/{table}.json', 'r', encoding='utf-8') as f:
                table_data = json.load(f)
            
            if not table_data:
                print(f"  ℹ️ لا توجد بيانات في {table}")
                imported_counts[table] = 0
                continue
            
            # استيراد البيانات على دفعات
            batch_size = 100
            imported_count = 0
            
            for i in range(0, len(table_data), batch_size):
                batch = table_data[i:i + batch_size]
                
                try:
                    result = supabase.table(table).insert(batch).execute()
                    imported_count += len(batch)
                    print(f"    ✅ استورد {len(batch)} سجل")
                    
                except Exception as e:
                    print(f"    ❌ خطأ في الدفعة {i//batch_size + 1}: {e}")
                    
                    # محاولة استيراد فردي للدفعة الفاشلة
                    for record in batch:
                        try:
                            supabase.table(table).insert(record).execute()
                            imported_count += 1
                        except Exception as record_error:
                            print(f"      ❌ فشل سجل: {record_error}")
            
            imported_counts[table] = imported_count
            print(f"  ✅ تم استيراد {imported_count}/{len(table_data)} سجل")
            
        except FileNotFoundError:
            print(f"  ⚠️ ملف {table}.json غير موجود")
            imported_counts[table] = 0
        except Exception as e:
            print(f"  ❌ خطأ في استيراد {table}: {e}")
            imported_counts[table] = 0
    
    # ملخص الاستيراد
    total_imported = sum(imported_counts.values())
    
    print(f"\\n📊 ملخص الاستيراد:")
    for table, count in imported_counts.items():
        print(f"  📋 {table}: {count:,} سجل")
    
    print(f"\\n✅ إجمالي السجلات المستوردة: {total_imported:,}")
    
    return imported_counts

if __name__ == "__main__":
    import_to_supabase()
'''
        
        # كتابة السكريبت
        script_path = f'{export_dir}/import_to_supabase.py'
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(script_content)
        
        print(f"✅ تم إنشاء سكريبت الاستيراد: {script_path}")
        return script_path
        
    except Exception as e:
        print(f"❌ خطأ في إنشاء السكريبت: {e}")
        return None

def create_migration_instructions():
    """إنشاء تعليمات الهجرة"""
    instructions = '''
# 📋 تعليمات الهجرة إلى Supabase

## الخطوة 1: إنشاء الجداول في Supabase
1. اذهب إلى https://supabase.com/dashboard/project/poxdecozxjnzbmumvqzx
2. اضغط على "SQL Editor" في القائمة الجانبية
3. انسخ محتوى ملف `create_supabase_tables.sql`
4. الصق المحتوى في SQL Editor
5. اضغط "Run" لتنفيذ السكريبت

## الخطوة 2: استيراد البيانات
1. شغل سكريبت التصدير: `python3 manual_migration.py`
2. شغل سكريبت الاستيراد: `python3 sqlite_export/import_to_supabase.py`

## الخطوة 3: تفعيل Supabase في البوت
1. أضف متغير البيئة: `export USE_SUPABASE=true`
2. أعد تشغيل البوت: `python3 main.py`

## الخطوة 4: التحقق من النجاح
- تحقق من أن البوت يعمل بدون أخطاء
- تحقق من أن البيانات موجودة في Supabase
- اختبر العمليات الأساسية (تسجيل، تحويل، شراء)

## ملاحظات مهمة:
- احتفظ بنسخة احتياطية من SQLite
- اختبر جميع الوظائف بعد الهجرة
- راقب الأداء والاستقرار
'''
    
    with open('MIGRATION_INSTRUCTIONS.md', 'w', encoding='utf-8') as f:
        f.write(instructions)
    
    print("📋 تم إنشاء ملف التعليمات: MIGRATION_INSTRUCTIONS.md")

def main():
    """الدالة الرئيسية"""
    print("🚀 بدء عملية التصدير للهجرة إلى Supabase")
    print("=" * 60)
    
    # تصدير البيانات
    exported_data, export_dir = export_sqlite_data()
    
    if export_dir:
        # إنشاء سكريبت الاستيراد
        script_path = create_supabase_import_script(exported_data, export_dir)
        
        # إنشاء التعليمات
        create_migration_instructions()
        
        print("\n" + "=" * 60)
        print("✅ تم تحضير الهجرة بنجاح!")
        print("\n📋 الخطوات التالية:")
        print("1. راجع ملف create_supabase_tables.sql")
        print("2. نفذ السكريبت في Supabase SQL Editor")
        print("3. شغل سكريبت الاستيراد")
        print("4. فعل USE_SUPABASE=true")
        print("5. أعد تشغيل البوت")
        
    else:
        print("\n❌ فشل التحضير للهجرة")

if __name__ == "__main__":
    main()