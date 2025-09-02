#!/usr/bin/env python3
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
        print(f"\n📋 استيراد جدول {table}...")
        
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
    
    print(f"\n📊 ملخص الاستيراد:")
    for table, count in imported_counts.items():
        print(f"  📋 {table}: {count:,} سجل")
    
    print(f"\n✅ إجمالي السجلات المستوردة: {total_imported:,}")
    
    return imported_counts

if __name__ == "__main__":
    import_to_supabase()
