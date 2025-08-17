#!/usr/bin/env python3
"""
أداة اختبار ميزة الكوبون الجديدة
Coupon Feature Testing Tool
"""

import sys
import sqlite3
import datetime

sys.path.append('/workspace')

def test_coupon_feature():
    """اختبار ميزة الكوبون"""
    print("🎟️ ================================================================ 🎟️")
    print("                     اختبار ميزة الكوبون الجديدة")
    print("🎟️ ================================================================ 🎟️")
    
    try:
        # فحص قاعدة البيانات
        conn = sqlite3.connect('/workspace/yemen_net.db')
        cursor = conn.cursor()
        
        # فحص جدول الكوبونات
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='coupons'")
        coupons_table_exists = cursor.fetchone() is not None
        
        print("🔍 === فحص قاعدة البيانات ===")
        print(f"✅ جدول الكوبونات: {'موجود' if coupons_table_exists else 'مفقود'}")
        
        if coupons_table_exists:
            # فحص الأعمدة
            cursor.execute("PRAGMA table_info(coupons)")
            columns = cursor.fetchall()
            required_columns = ['coupon_code', 'amount', 'is_used', 'used_by', 'expiry_date']
            
            print("\n📊 أعمدة جدول الكوبونات:")
            for col in required_columns:
                exists = any(c[1] == col for c in columns)
                status = "✅" if exists else "❌"
                print(f"  {status} {col}")
            
            # فحص الكوبونات الموجودة
            cursor.execute("SELECT COUNT(*) FROM coupons")
            total_coupons = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM coupons WHERE is_used = 0")
            available_coupons = cursor.fetchone()[0]
            
            print(f"\n📈 إحصائيات الكوبونات:")
            print(f"  📦 إجمالي الكوبونات: {total_coupons}")
            print(f"  🔓 كوبونات متاحة: {available_coupons}")
            print(f"  ✅ كوبونات مستخدمة: {total_coupons - available_coupons}")
            
            # عرض أمثلة من الكوبونات
            if total_coupons > 0:
                cursor.execute("SELECT coupon_code, amount, is_used FROM coupons LIMIT 3")
                sample_coupons = cursor.fetchall()
                
                print(f"\n🎟️ أمثلة من الكوبونات:")
                for coupon in sample_coupons:
                    status = "مستخدم" if coupon[2] else "متاح"
                    print(f"  🎫 {coupon[0]} - {coupon[1]:,.0f} ريال ({status})")
        
        conn.close()
        
        # فحص الكود
        print("\n🔧 === فحص الكود ===")
        
        # فحص وجود الدوال
        try:
            from bot_modules.handlers import redeem_coupon_handler, process_coupon_redemption, validate_coupon_format
            print("✅ دوال الكوبون: موجودة")
        except ImportError as e:
            print(f"❌ دوال الكوبون: مفقودة - {e}")
            return False
        
        # اختبار دالة التحقق من التنسيق
        test_codes = [
            ("A12345678", True),   # صحيح
            ("A1234567", False),   # قصير
            ("B12345678", False),  # لا يبدأ بـ A
            ("A123456789", False), # طويل
            ("A1234567a", False),  # يحتوي على حرف
        ]
        
        print("\n🧪 اختبار دالة التحقق من التنسيق:")
        all_tests_passed = True
        for code, expected in test_codes:
            result = validate_coupon_format(code)
            status = "✅" if result == expected else "❌"
            print(f"  {status} {code}: {'صحيح' if result else 'خاطئ'}")
            if result != expected:
                all_tests_passed = False
        
        # فحص الواجهة
        print("\n🖥️ === فحص الواجهة ===")
        
        # فحص وجود الزر في القائمة
        with open('/workspace/bot_modules/handlers.py', 'r', encoding='utf-8') as f:
            handlers_content = f.read()
        
        coupon_button_exists = 'شحن بكوبون' in handlers_content
        redeem_callback_exists = 'redeem_coupon' in handlers_content
        
        print(f"✅ زر شحن بكوبون: {'موجود' if coupon_button_exists else 'مفقود'}")
        print(f"✅ معالج callback: {'موجود' if redeem_callback_exists else 'مفقود'}")
        
        # فحص الملف الرئيسي
        with open('/workspace/yemen_net_bot_new.py', 'r', encoding='utf-8') as f:
            main_content = f.read()
        
        main_handler_exists = 'redeem_coupon' in main_content
        print(f"✅ معالج في الملف الرئيسي: {'موجود' if main_handler_exists else 'مفقود'}")
        
        # النتيجة النهائية
        print("\n🎯 === النتيجة النهائية ===")
        
        if (coupons_table_exists and coupon_button_exists and 
            redeem_callback_exists and main_handler_exists and all_tests_passed):
            print("🎉 جميع الاختبارات نجحت! ميزة الكوبون جاهزة للاستخدام.")
            
            print("\n💡 === كيفية الاستخدام ===")
            print("1️⃣ افتح البوت واذهب للقائمة الرئيسية")
            print("2️⃣ اضغط على '🎟️ شحن بكوبون'")
            print("3️⃣ أدخل رقم كوبون صالح (مثل: A12345678)")
            print("4️⃣ سيتم إضافة القيمة لرصيدك فوراً")
            
            if available_coupons > 0:
                print(f"\n🎁 لديك {available_coupons} كوبون متاح للاختبار!")
            else:
                print("\n⚠️ لا توجد كوبونات متاحة - يمكن للمشرف إنشاء كوبون للاختبار")
            
            return True
        else:
            print("❌ بعض الاختبارات فشلت. الميزة تحتاج مراجعة.")
            return False
            
    except Exception as e:
        print(f"❌ خطأ في الاختبار: {e}")
        return False

def create_test_coupon():
    """إنشاء كوبون للاختبار"""
    try:
        conn = sqlite3.connect('/workspace/yemen_net.db')
        cursor = conn.cursor()
        
        # توليد رقم كوبون للاختبار
        import random
        test_code = f"A{random.randint(10000000, 99999999)}"
        test_amount = 100.0
        
        # إنشاء الكوبون
        expiry_date = datetime.datetime.now() + datetime.timedelta(days=30)
        cursor.execute('''
            INSERT INTO coupons (coupon_code, amount, is_used, created_by, expiry_date, description)
            VALUES (?, ?, 0, 1, ?, ?)
        ''', (test_code, test_amount, expiry_date.isoformat(), 'كوبون اختبار'))
        
        conn.commit()
        conn.close()
        
        print(f"\n🎁 تم إنشاء كوبون اختبار:")
        print(f"🎟️ الرقم: {test_code}")
        print(f"💰 القيمة: {test_amount:,.0f} ريال")
        print(f"📅 ينتهي في: {expiry_date.strftime('%Y-%m-%d')}")
        
        return test_code
        
    except Exception as e:
        print(f"❌ خطأ في إنشاء كوبون الاختبار: {e}")
        return None

if __name__ == "__main__":
    success = test_coupon_feature()
    
    if success:
        print("\n" + "="*60)
        choice = input("هل تريد إنشاء كوبون للاختبار؟ (y/n): ")
        if choice.lower() in ['y', 'yes', 'نعم']:
            create_test_coupon()
    
    print("🎟️ ================================================================ 🎟️")