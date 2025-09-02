#!/usr/bin/env python3
"""
Simple Supabase Import - استيراد مبسط لـ Supabase
"""

import json
from supabase import create_client

# إعدادات Supabase
SUPABASE_URL = "https://poxdecozxjnzbmumvqzx.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InBveGRlY296eGpuemJtdW12cXp4Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTY2ODIzNDIsImV4cCI6MjA3MjI1ODM0Mn0.OpoVMldNCBqIkhSSvic29LlSrhfmOIqt7NBp5v27CUk"

def import_users():
    """استيراد المستخدمين"""
    print("👥 استيراد المستخدمين...")
    
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    try:
        with open('users.json', 'r', encoding='utf-8') as f:
            users_data = json.load(f)
        
        for user in users_data:
            # تنظيف البيانات
            clean_user = {
                'telegram_id': user['telegram_id'],
                'full_name': user['full_name'],
                'phone': user['phone'],
                'role': user['role'],
                'balance': float(user['balance']),
                'wallet_number': user['wallet_number'],
                'is_active': bool(user['is_active']),
                'created_at': user['created_at']
            }
            
            try:
                result = supabase.table('users').insert(clean_user).execute()
                print(f"  ✅ {user['full_name']}")
            except Exception as e:
                print(f"  ❌ {user['full_name']}: {e}")
        
        print(f"✅ تم استيراد المستخدمين")
        
    except Exception as e:
        print(f"❌ خطأ في استيراد المستخدمين: {e}")

def import_all_data():
    """استيراد جميع البيانات"""
    print("📤 بدء استيراد البيانات إلى Supabase...")
    
    # ترتيب الجداول حسب التبعيات
    tables_order = [
        'users',           # أولاً - لا يعتمد على أحد
        'networks',        # ثانياً - يعتمد على users
        'network_cards',   # ثالثاً - يعتمد على networks
        'transactions',    # رابعاً - يعتمد على users
        'wallet_transactions', # خامساً - يعتمد على users
        'coupons',         # سادساً - يعتمد على users
        'chart_of_accounts', # سابعاً - مستقل
        'general_ledger'   # أخيراً - يعتمد على chart_of_accounts
    ]
    
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    for table in tables_order:
        print(f"\n📋 استيراد {table}...")
        
        try:
            with open(f'{table}.json', 'r', encoding='utf-8') as f:
                table_data = json.load(f)
            
            if not table_data:
                print(f"  ℹ️ لا توجد بيانات في {table}")
                continue
            
            # استيراد على دفعات صغيرة
            batch_size = 10
            imported_count = 0
            
            for i in range(0, len(table_data), batch_size):
                batch = table_data[i:i + batch_size]
                
                try:
                    result = supabase.table(table).insert(batch).execute()
                    imported_count += len(batch)
                    print(f"    ✅ دفعة {i//batch_size + 1}: {len(batch)} سجل")
                    
                except Exception as e:
                    print(f"    ❌ دفعة {i//batch_size + 1}: {e}")
                    
                    # محاولة فردية
                    for record in batch:
                        try:
                            supabase.table(table).insert(record).execute()
                            imported_count += 1
                        except Exception as record_error:
                            print(f"      ❌ سجل فردي: {record_error}")
            
            print(f"  ✅ تم استيراد {imported_count}/{len(table_data)} سجل")
            
        except FileNotFoundError:
            print(f"  ⚠️ ملف {table}.json غير موجود")
        except Exception as e:
            print(f"  ❌ خطأ في {table}: {e}")

if __name__ == "__main__":
    import_all_data()
