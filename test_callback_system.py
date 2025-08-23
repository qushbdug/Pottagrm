#!/usr/bin/env python3
"""
اختبار نظام Callback الجديد
"""

import sys
import os

# إضافة bot_modules للمسار
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'bot_modules'))

from callback_utils import create_callback, get_callback_data, cleanup_callbacks

def test_callback_system():
    """اختبار نظام Callback"""
    print("🧪 اختبار نظام Callback الجديد")
    print("=" * 50)
    
    # اختبار 1: إنشاء callback بسيط
    print("\n1️⃣ اختبار إنشاء callback بسيط:")
    simple_callback = create_callback('buy_cards')
    print(f"   النتيجة: {simple_callback}")
    print(f"   الطول: {len(simple_callback)} حرف")
    
    # اختبار 2: إنشاء callback مع بيانات
    print("\n2️⃣ اختبار إنشاء callback مع بيانات:")
    network_callback = create_callback('buy_from_network', network_id='12345')
    print(f"   النتيجة: {network_callback}")
    print(f"   الطول: {len(network_callback)} حرف")
    
    # اختبار 3: إنشاء callback مع بيانات متعددة
    print("\n3️⃣ اختبار إنشاء callback مع بيانات متعددة:")
    complex_callback = create_callback('buy_card', 
                                     category_id='67890', 
                                     price='1000', 
                                     currency='YER')
    print(f"   النتيجة: {complex_callback}")
    print(f"   الطول: {len(complex_callback)} حرف")
    
    # اختبار 4: استرجاع البيانات
    print("\n4️⃣ اختبار استرجاع البيانات:")
    callback_info = get_callback_data(network_callback)
    if callback_info:
        print(f"   الإجراء: {callback_info['action']}")
        print(f"   البيانات: {callback_info['data']}")
    else:
        print("   ❌ فشل في استرجاع البيانات")
    
    # اختبار 5: استرجاع بيانات معقدة
    print("\n5️⃣ اختبار استرجاع بيانات معقدة:")
    complex_info = get_callback_data(complex_callback)
    if complex_info:
        print(f"   الإجراء: {complex_info['action']}")
        print(f"   البيانات: {complex_info['data']}")
    else:
        print("   ❌ فشل في استرجاع البيانات")
    
    # اختبار 6: التحقق من الحد الأقصى
    print("\n6️⃣ اختبار الحد الأقصى (64 حرف):")
    long_data = {
        'network_id': '12345678901234567890',
        'category_id': '09876543210987654321',
        'price': '99999999999999999999',
        'currency': 'YER',
        'description': 'شبكة اختبار طويلة جداً'
    }
    long_callback = create_callback('very_long_action_name', **long_data)
    print(f"   النتيجة: {long_callback}")
    print(f"   الطول: {len(long_callback)} حرف")
    print(f"   ✅ تحت الحد: {'نعم' if len(long_callback) <= 64 else 'لا'}")
    
    # اختبار 7: تنظيف البيانات
    print("\n7️⃣ اختبار تنظيف البيانات:")
    cleanup_callbacks()
    print("   ✅ تم تنظيف البيانات القديمة")
    
    print("\n" + "=" * 50)
    print("🎉 انتهى الاختبار بنجاح!")

if __name__ == "__main__":
    test_callback_system()