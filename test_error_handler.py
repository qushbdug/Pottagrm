#!/usr/bin/env python3
"""
اختبار معالج الأخطاء الجديد
"""

import sys
import os
import sqlite3

# إضافة bot_modules للمسار
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'bot_modules'))

from error_handler import (
    safe_database_transaction, 
    ErrorHandler, 
    safe_execute, 
    safe_async_execute,
    log_and_handle_error
)

def test_error_handler():
    """اختبار معالج الأخطاء"""
    print("🧪 اختبار معالج الأخطاء الجديد")
    print("=" * 50)
    
    # اختبار 1: معالجة أخطاء قاعدة البيانات
    print("\n1️⃣ اختبار معالجة أخطاء قاعدة البيانات:")
    try:
        # محاولة إنشاء جدول موجود بالفعل
        conn = sqlite3.connect(':memory:')
        cursor = conn.cursor()
        cursor.execute('CREATE TABLE test (id INTEGER PRIMARY KEY)')
        cursor.execute('CREATE TABLE test (id INTEGER PRIMARY KEY)')  # خطأ
    except Exception as e:
        error_msg = ErrorHandler.handle_database_error(e, "إنشاء جدول اختبار")
        print(f"   الخطأ: {e}")
        print(f"   الرسالة: {error_msg}")
    
    # اختبار 2: معالجة أخطاء تيليجرام
    print("\n2️⃣ اختبار معالجة أخطاء تيليجرام:")
    class MockTelegramError(Exception):
        def __init__(self, message):
            self.message = message
        
        def __str__(self):
            return self.message
    
    telegram_error = MockTelegramError("message is not modified")
    error_msg = ErrorHandler.handle_telegram_error(telegram_error, "تعديل رسالة")
    print(f"   الخطأ: {telegram_error}")
    print(f"   الرسالة: {error_msg}")
    
    # اختبار 3: معالجة أخطاء عامة
    print("\n3️⃣ اختبار معالجة أخطاء عامة:")
    general_error = ValueError("قيمة غير صحيحة")
    error_msg = ErrorHandler.handle_general_error(general_error, "معالجة البيانات")
    print(f"   الخطأ: {general_error}")
    print(f"   الرسالة: {error_msg}")
    
    # اختبار 4: مزخرف safe_execute
    print("\n4️⃣ اختبار مزخرف safe_execute:")
    
    @safe_execute("اختبار الدالة", "❌ فشل في الاختبار")
    def test_function():
        raise RuntimeError("خطأ في الاختبار")
    
    result = test_function()
    print(f"   النتيجة: {result}")
    
    # اختبار 5: مزخرف safe_async_execute
    print("\n5️⃣ اختبار مزخرف safe_async_execute:")
    
    @safe_async_execute("اختبار دالة غير متزامنة", "❌ فشل في الاختبار")
    async def test_async_function():
        raise RuntimeError("خطأ في الاختبار غير المتزامن")
    
    # محاكاة استدعاء الدالة غير المتزامنة
    import asyncio
    try:
        result = asyncio.run(test_async_function())
        print(f"   النتيجة: {result}")
    except Exception as e:
        print(f"   ❌ فشل في تشغيل الدالة غير المتزامنة: {e}")
    
    # اختبار 6: معاملات قاعدة البيانات الآمنة
    print("\n6️⃣ اختبار معاملات قاعدة البيانات الآمنة:")
    try:
        conn = sqlite3.connect(':memory:')
        cursor = conn.cursor()
        
        # إنشاء جدول
        cursor.execute('CREATE TABLE test_transaction (id INTEGER PRIMARY KEY, name TEXT)')
        
        # استخدام معاملات آمنة
        with safe_database_transaction(conn) as cursor:
            cursor.execute('INSERT INTO test_transaction (id, name) VALUES (1, "اختبار")')
            cursor.execute('INSERT INTO test_transaction (id, name) VALUES (2, "نجح")')
            print("   ✅ تم إنشاء المعاملة بنجاح")
        
        # التحقق من البيانات
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM test_transaction')
        rows = cursor.fetchall()
        print(f"   البيانات: {rows}")
        
        conn.close()
        
    except Exception as e:
        print(f"   ❌ فشل في اختبار المعاملات: {e}")
    
    # اختبار 7: دالة مساعدة سريعة
    print("\n7️⃣ اختبار دالة مساعدة سريعة:")
    try:
        # محاولة إنشاء جدول موجود
        conn = sqlite3.connect(':memory:')
        cursor = conn.cursor()
        cursor.execute('CREATE TABLE test_quick (id INTEGER PRIMARY KEY)')
        cursor.execute('CREATE TABLE test_quick (id INTEGER PRIMARY KEY)')  # خطأ
    except Exception as e:
        error_msg = log_and_handle_error(e, "إنشاء جدول سريع")
        print(f"   الخطأ: {e}")
        print(f"   الرسالة: {error_msg}")
    
    print("\n" + "=" * 50)
    print("🎉 انتهى اختبار معالج الأخطاء بنجاح!")

if __name__ == "__main__":
    test_error_handler()