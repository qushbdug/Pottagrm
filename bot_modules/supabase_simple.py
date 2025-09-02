#!/usr/bin/env python3
"""
Supabase Simple - طبقة Supabase مبسطة
طبقة مبسطة للتعامل مع Supabase مباشرة
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from supabase import create_client

logger = logging.getLogger(__name__)

# إعدادات Supabase
SUPABASE_URL = "https://poxdecozxjnzbmumvqzx.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InBveGRlY296eGpuemJtdW12cXp4Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTY2ODIzNDIsImV4cCI6MjA3MjI1ODM0Mn0.OpoVMldNCBqIkhSSvic29LlSrhfmOIqt7NBp5v27CUk"

class SupabaseSimple:
    """فئة Supabase مبسطة"""
    
    def __init__(self):
        try:
            self.client = create_client(SUPABASE_URL, SUPABASE_KEY)
            logger.info("Supabase client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Supabase client: {e}")
            raise
    
    def create_basic_tables(self):
        """إنشاء الجداول الأساسية إذا لم تكن موجودة"""
        print("🔧 محاولة إنشاء الجداول الأساسية...")
        
        # إنشاء جدول المستخدمين أولاً
        try:
            # محاولة إدراج مستخدم تجريبي لإنشاء الجدول
            test_user = {
                'telegram_id': 999999999,
                'full_name': 'Test User',
                'phone': '999999999',
                'role': 'customer',
                'balance': 0.0,
                'wallet_number': '999999999',
                'is_active': False
            }
            
            result = self.client.table('users').insert(test_user).execute()
            
            if result.data:
                print("✅ جدول users تم إنشاؤه")
                # حذف المستخدم التجريبي
                self.client.table('users').delete().eq('telegram_id', 999999999).execute()
            
        except Exception as e:
            print(f"⚠️ جدول users: {e}")
        
        return True
    
    def import_users_data(self, users_data: List[Dict]) -> int:
        """استيراد بيانات المستخدمين"""
        imported_count = 0
        
        for user in users_data:
            try:
                # تنظيف البيانات
                clean_user = {
                    'telegram_id': int(user['telegram_id']),
                    'full_name': str(user['full_name']),
                    'phone': str(user['phone']),
                    'role': str(user.get('role', 'customer')),
                    'balance': float(user.get('balance', 0)),
                    'wallet_number': user.get('wallet_number'),
                    'is_active': bool(user.get('is_active', False)),
                    'total_referrals': int(user.get('total_referrals', 0)),
                    'total_purchases': int(user.get('total_purchases', 0)),
                    'total_spent': float(user.get('total_spent', 0)),
                    'invite_code': user.get('invite_code'),
                    'created_at': user.get('created_at', datetime.now().isoformat())
                }
                
                result = self.client.table('users').insert(clean_user).execute()
                
                if result.data:
                    imported_count += 1
                    print(f"  ✅ {clean_user['full_name']}")
                
            except Exception as e:
                print(f"  ❌ {user.get('full_name', 'Unknown')}: {e}")
        
        return imported_count
    
    def quick_setup_and_import(self):
        """إعداد سريع واستيراد البيانات"""
        print("🚀 بدء الإعداد السريع لـ Supabase...")
        
        try:
            # محاولة إنشاء الجداول
            self.create_basic_tables()
            
            # استيراد بيانات المستخدمين
            try:
                import json
                with open('sqlite_export/users.json', 'r', encoding='utf-8') as f:
                    users_data = json.load(f)
                
                print(f"👥 استيراد {len(users_data)} مستخدم...")
                imported = self.import_users_data(users_data)
                print(f"✅ تم استيراد {imported}/{len(users_data)} مستخدم")
                
            except FileNotFoundError:
                print("⚠️ ملف المستخدمين غير موجود")
            except Exception as e:
                print(f"❌ خطأ في استيراد المستخدمين: {e}")
            
            return True
            
        except Exception as e:
            print(f"❌ فشل الإعداد السريع: {e}")
            return False

# إنشاء مثيل عام
supabase_simple = SupabaseSimple()

# دوال توافق مع الكود الحالي
def get_db_connection():
    """دالة توافق - إرجاع عميل Supabase"""
    return supabase_simple.client

def get_user(telegram_id: int) -> Optional[Dict]:
    """الحصول على مستخدم من Supabase"""
    try:
        result = supabase_simple.client.table('users').select('*').eq('telegram_id', telegram_id).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        logger.error(f"Error getting user from Supabase: {e}")
        # fallback إلى SQLite في حالة الفشل
        try:
            import sqlite3
            conn = sqlite3.connect('yemen_net.db')
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users WHERE telegram_id = ?', (telegram_id,))
            user = cursor.fetchone()
            conn.close()
            return dict(user) if user else None
        except Exception as fallback_error:
            logger.error(f"Fallback to SQLite also failed: {fallback_error}")
            return None

def get_user_by_id(user_id: int) -> Optional[Dict]:
    """الحصول على مستخدم بـ ID من Supabase"""
    try:
        result = supabase_simple.client.table('users').select('*').eq('id', user_id).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        logger.error(f"Error getting user by id from Supabase: {e}")
        # fallback إلى SQLite
        try:
            import sqlite3
            conn = sqlite3.connect('yemen_net.db')
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
            user = cursor.fetchone()
            conn.close()
            return dict(user) if user else None
        except Exception as fallback_error:
            logger.error(f"Fallback to SQLite also failed: {fallback_error}")
            return None