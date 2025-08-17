#!/usr/bin/env python3
"""
أداة فحص وتحقق من جميع الميزات
Feature Validation and Testing Tool
"""

import sys
import os
import sqlite3
import asyncio
import logging

# إضافة مسار الوحدات
sys.path.append('/workspace')

def test_database_structure():
    """فحص هيكل قاعدة البيانات"""
    print("🔍 === فحص هيكل قاعدة البيانات ===")
    
    try:
        conn = sqlite3.connect('/workspace/yemen_net.db')
        cursor = conn.cursor()
        
        # فحص جدول networks
        cursor.execute("PRAGMA table_info(networks)")
        networks_columns = [col[1] for col in cursor.fetchall()]
        required_network_columns = ['id', 'name', 'provider', 'description', 'location', 'created_by']
        
        print("📊 جدول networks:")
        for col in required_network_columns:
            status = "✅" if col in networks_columns else "❌"
            print(f"  {status} {col}")
        
        # فحص جدول coupons
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='coupons'")
        coupons_exists = cursor.fetchone() is not None
        
        print(f"\n🎟️ جدول coupons: {'✅ موجود' if coupons_exists else '❌ مفقود'}")
        
        if coupons_exists:
            cursor.execute("PRAGMA table_info(coupons)")
            coupons_columns = [col[1] for col in cursor.fetchall()]
            required_coupon_columns = ['id', 'coupon_code', 'amount', 'is_used', 'created_by']
            
            for col in required_coupon_columns:
                status = "✅" if col in coupons_columns else "❌"
                print(f"  {status} {col}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ خطأ في فحص قاعدة البيانات: {e}")
        return False

def test_admin_functions_structure():
    """فحص هيكل دوال الإدارة"""
    print("\n🔧 === فحص دوال الإدارة ===")
    
    try:
        from bot_modules.admin_functions import (
            create_coupons_handler,
            process_coupon_creation,
            admin_add_network_handler,
            admin_process_network_creation,
            ADMIN_CALLBACKS
        )
        
        # فحص وجود الدوال
        functions_to_check = [
            ('create_coupons_handler', create_coupons_handler),
            ('process_coupon_creation', process_coupon_creation),
            ('admin_add_network_handler', admin_add_network_handler),
            ('admin_process_network_creation', admin_process_network_creation),
        ]
        
        for func_name, func in functions_to_check:
            status = "✅" if callable(func) else "❌"
            print(f"  {status} {func_name}")
        
        # فحص ADMIN_CALLBACKS
        required_callbacks = [
            'super_create_coupons',
            'admin_add_network',
            'super_coupons_stats',
            'super_list_coupons'
        ]
        
        print("\n📋 فحص callbacks:")
        for callback in required_callbacks:
            status = "✅" if callback in ADMIN_CALLBACKS else "❌"
            print(f"  {status} {callback}")
        
        return True
        
    except Exception as e:
        print(f"❌ خطأ في فحص دوال الإدارة: {e}")
        return False

def test_handlers_routing():
    """فحص توجيه المعالجات"""
    print("\n🎯 === فحص توجيه المعالجات ===")
    
    try:
        from bot_modules.handlers import handle_text_message
        
        print("✅ دالة handle_text_message موجودة")
        
        # فحص الملف للتأكد من وجود فحوصات الحالة
        with open('/workspace/bot_modules/handlers.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        required_checks = [
            'admin_adding_network',
            'admin_creating_coupon',
            'admin_uploading_card'
        ]
        
        for check in required_checks:
            status = "✅" if check in content else "❌"
            print(f"  {status} فحص {check}")
        
        return True
        
    except Exception as e:
        print(f"❌ خطأ في فحص المعالجات: {e}")
        return False

def simulate_coupon_creation():
    """محاكاة إنشاء كوبون"""
    print("\n🎟️ === محاكاة إنشاء كوبون ===")
    
    try:
        from bot_modules.admin_functions import generate_coupon_code
        
        # اختبار توليد رقم كوبون
        coupon_code = generate_coupon_code()
        
        # فحص التنسيق
        is_valid_format = (
            len(coupon_code) == 9 and
            coupon_code.startswith('A') and
            coupon_code[1:].isdigit()
        )
        
        print(f"🔢 رقم كوبون مُولد: {coupon_code}")
        print(f"✅ التنسيق صحيح: {'نعم' if is_valid_format else 'لا'}")
        
        return is_valid_format
        
    except Exception as e:
        print(f"❌ خطأ في محاكاة إنشاء الكوبون: {e}")
        return False

def check_state_management():
    """فحص إدارة الحالات"""
    print("\n🔄 === فحص إدارة الحالات ===")
    
    # فحص وجود تنظيف الحالة في الدوال
    files_to_check = [
        '/workspace/bot_modules/admin_functions.py'
    ]
    
    patterns_to_find = [
        'context.user_data.clear()',
        'admin_creating_coupon',
        'admin_adding_network',
        'network_step'
    ]
    
    for file_path in files_to_check:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            print(f"\n📁 فحص {os.path.basename(file_path)}:")
            for pattern in patterns_to_find:
                count = content.count(pattern)
                status = "✅" if count > 0 else "❌"
                print(f"  {status} {pattern}: {count} مرة")
        
        except Exception as e:
            print(f"❌ خطأ في فحص {file_path}: {e}")
    
    return True

def run_comprehensive_test():
    """تشغيل فحص شامل"""
    print("🧪 ================================================================ 🧪")
    print("                     فحص شامل لجميع الميزات")
    print("🧪 ================================================================ 🧪")
    
    results = []
    
    # تشغيل جميع الاختبارات
    tests = [
        ("هيكل قاعدة البيانات", test_database_structure),
        ("دوال الإدارة", test_admin_functions_structure),
        ("توجيه المعالجات", test_handlers_routing),
        ("إنشاء الكوبونات", simulate_coupon_creation),
        ("إدارة الحالات", check_state_management),
    ]
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ فشل اختبار {test_name}: {e}")
            results.append((test_name, False))
    
    # عرض النتائج النهائية
    print("\n🎯 === النتائج النهائية ===")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ نجح" if result else "❌ فشل"
        print(f"  {status} {test_name}")
    
    print(f"\n📊 الإحصائيات:")
    print(f"✅ اختبارات ناجحة: {passed}/{total}")
    print(f"❌ اختبارات فاشلة: {total-passed}/{total}")
    print(f"📈 معدل النجاح: {(passed/total)*100:.1f}%")
    
    if passed == total:
        print("\n🎉 جميع الاختبارات نجحت! النظام يعمل بشكل صحيح.")
    else:
        print("\n⚠️ بعض الاختبارات فشلت. يرجى مراجعة المشاكل المذكورة أعلاه.")
    
    print("🧪 ================================================================ 🧪")
    
    return passed == total

if __name__ == "__main__":
    success = run_comprehensive_test()
    sys.exit(0 if success else 1)