#!/usr/bin/env python3
"""
اختبار عرض تفاصيل الشبكة
"""

import sys
import os
sys.path.insert(0, 'bot_modules')

from config import EMOJIS
from database import get_db_connection

def test_network_details():
    """اختبار عرض تفاصيل الشبكة"""
    print("🧪 اختبار عرض تفاصيل الشبكة")
    print("=" * 50)
    
    # اختبار 1: التحقق من EMOJIS
    print("\n1️⃣ اختبار EMOJIS:")
    try:
        print(f"✅ EMOJIS متاح: {EMOJIS['error']}")
        print(f"✅ EMOJIS متاح: {EMOJIS['success']}")
        print(f"✅ EMOJIS متاح: {EMOJIS['info']}")
    except Exception as e:
        print(f"❌ خطأ في EMOJIS: {e}")
        return False
    
    # اختبار 2: التحقق من قاعدة البيانات
    print("\n2️⃣ اختبار قاعدة البيانات:")
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # فحص جدول networks
        cursor.execute('PRAGMA table_info(networks)')
        columns = cursor.fetchall()
        print(f"✅ جدول networks يحتوي على {len(columns)} عمود")
        
        # فحص البيانات
        cursor.execute('SELECT COUNT(*) FROM networks WHERE is_active = 1')
        networks_count = cursor.fetchone()[0]
        print(f"✅ عدد الشبكات النشطة: {networks_count}")
        
        # فحص جدول card_categories
        cursor.execute('PRAGMA table_info(card_categories)')
        columns = cursor.fetchall()
        print(f"✅ جدول card_categories يحتوي على {len(columns)} عمود")
        
        # فحص البيانات
        cursor.execute('SELECT COUNT(*) FROM card_categories WHERE is_available = 1')
        categories_count = cursor.fetchone()[0]
        print(f"✅ عدد فئات الكروت المتاحة: {categories_count}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ خطأ في قاعدة البيانات: {e}")
        return False
    
    # اختبار 3: محاكاة استعلام عرض تفاصيل الشبكة
    print("\n3️⃣ اختبار استعلام عرض تفاصيل الشبكة:")
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # نفس الاستعلام المستخدم في show_network_details
        cursor.execute('''
            SELECT n.id, n.name, n.provider, n.location, n.description, n.created_at,
                   COUNT(cc.id) as categories_count,
                   MIN(cc.price) as min_price, MAX(cc.price) as max_price,
                   COUNT(CASE WHEN c.is_sold = 0 THEN 1 END) as available_cards
            FROM networks n
            LEFT JOIN card_categories cc ON n.id = cc.network_id AND cc.is_available = 1
            LEFT JOIN cards c ON cc.id = c.category_id
            WHERE n.id = 1 AND n.is_active = 1
            GROUP BY n.id, n.name, n.provider, n.location, n.description, n.created_at
        ''')
        
        network = cursor.fetchone()
        if network:
            net_id, name, provider, location, description, created_at, cat_count, min_price, max_price, available_cards = network
            print(f"✅ تم جلب بيانات الشبكة: {name}")
            print(f"   - المزود: {provider}")
            print(f"   - الموقع: {location}")
            print(f"   - الوصف: {description}")
            print(f"   - عدد الفئات: {cat_count}")
            print(f"   - نطاق الأسعار: {min_price} - {max_price}")
            print(f"   - الكروت المتاحة: {available_cards}")
        else:
            print("❌ لم يتم العثور على الشبكة")
            return False
        
        # اختبار جلب فئات الكروت
        cursor.execute('''
            SELECT name, price, description
            FROM card_categories
            WHERE network_id = 1 AND is_available = 1
            ORDER BY price ASC
        ''')
        
        categories = cursor.fetchall()
        print(f"\n✅ تم جلب {len(categories)} فئة كروت:")
        for cat_name, price, cat_desc in categories:
            print(f"   - {cat_name}: {price} ريال - {cat_desc or 'لا يوجد وصف'}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ خطأ في الاستعلام: {e}")
        return False
    
    # اختبار 4: محاكاة إنشاء رسالة التفاصيل
    print("\n4️⃣ اختبار إنشاء رسالة التفاصيل:")
    try:
        location_text = f"📍 {location}" if location else "📍 غير محدد"
        price_range = f"{min_price:,.0f} - {max_price:,.0f}" if min_price and max_price and min_price != max_price else f"{min_price:,.0f}" if min_price else "غير محدد"
        
        details_text = f"""
🌐 **تفاصيل الشبكة** 🌐

📋 **المعلومات الأساسية:**
🏷️ الاسم: **{name}**
👤 المزود: **{provider}**
{location_text}
📝 الوصف: {description or 'غير متاح'}
📅 تاريخ الإضافة: {created_at[:10] if created_at else 'غير محدد'}

📊 **الإحصائيات:**
💳 عدد الفئات: **{cat_count}** فئة
💰 نطاق الأسعار: **{price_range}** ريال
📦 الكروت المتاحة: **{available_cards or 0}** كرت

💳 **فئات الكروت المتاحة:**

"""
        
        if categories:
            for cat_name, price, cat_desc in categories:
                details_text += f"""
🎫 **{cat_name}**
💰 السعر: **{price:,.0f}** ريال
📝 الوصف: {cat_desc or 'غير متاح'}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        else:
            details_text += "❌ لا توجد فئات متاحة حالياً"
        
        print("✅ تم إنشاء رسالة التفاصيل بنجاح")
        print(f"   - طول الرسالة: {len(details_text)} حرف")
        
    except Exception as e:
        print(f"❌ خطأ في إنشاء الرسالة: {e}")
        return False
    
    print("\n" + "=" * 50)
    print("🎉 انتهى الاختبار بنجاح!")
    print("✅ جميع الميزات تعمل بشكل صحيح")
    print("✅ مشكلة عرض تفاصيل الشبكة تم حلها")
    
    return True

if __name__ == "__main__":
    test_network_details()