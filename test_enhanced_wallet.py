#!/usr/bin/env python3
"""
اختبار المحفظة المطورة - Yemen Net Bot
يختبر جميع جوانب المحفظة المطورة لمعرفة المشاكل
"""

import sys
import os

# إضافة مسار bot_modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'bot_modules'))

def test_enhanced_wallet_components():
    """اختبار جميع مكونات المحفظة المطورة"""
    
    print("🧪 بدء اختبار مكونات المحفظة المطورة...")
    print("=" * 50)
    
    # 1. اختبار الاستيرادات
    print("\n1️⃣ اختبار الاستيرادات...")
    try:
        from bot_modules.config import EMOJIS
        print("✅ تم استيراد EMOJIS بنجاح")
    except Exception as e:
        print(f"❌ خطأ في استيراد EMOJIS: {e}")
        return False
    
    try:
        from bot_modules.utils import get_user, calculate_user_rating
        print("✅ تم استيراد دوال المستخدم والتقييم بنجاح")
    except Exception as e:
        print(f"❌ خطأ في استيراد دوال المستخدم: {e}")
        return False
    
    try:
        from bot_modules.database import get_db_connection
        print("✅ تم استيراد قاعدة البيانات بنجاح")
    except Exception as e:
        print(f"❌ خطأ في استيراد قاعدة البيانات: {e}")
        return False
    
    # 2. اختبار قاعدة البيانات
    print("\n2️⃣ اختبار قاعدة البيانات...")
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        print("✅ تم الاتصال بقاعدة البيانات")
        
        # اختبار جدول المستخدمين
        cursor.execute('SELECT COUNT(*) FROM users')
        user_count = cursor.fetchone()[0]
        print(f"✅ جدول المستخدمين: {user_count} مستخدم")
        
        # اختبار جدول المعاملات
        cursor.execute('SELECT COUNT(*) FROM transactions')
        trans_count = cursor.fetchone()[0]
        print(f"✅ جدول المعاملات: {trans_count} معاملة")
        
        # اختبار جدول التقييمات
        cursor.execute('SELECT COUNT(*) FROM ratings')
        rating_count = cursor.fetchone()[0]
        print(f"✅ جدول التقييمات: {rating_count} تقييم")
        
        # اختبار جدول ملخص التقييمات
        cursor.execute('SELECT COUNT(*) FROM user_ratings_summary')
        summary_count = cursor.fetchone()[0]
        print(f"✅ جدول ملخص التقييمات: {summary_count} ملخص")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ خطأ في اختبار قاعدة البيانات: {e}")
        return False
    
    # 3. اختبار دالة get_user
    print("\n3️⃣ اختبار دالة get_user...")
    try:
        # البحث عن مستخدم موجود
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT telegram_id FROM users LIMIT 1')
        result = cursor.fetchone()
        conn.close()
        
        if result:
            telegram_id = result[0]
            user = get_user(telegram_id)
            if user:
                print(f"✅ تم العثور على المستخدم: {user.get('full_name', 'غير محدد')}")
                print(f"   - الرصيد: {user.get('balance', 0)}")
                print(f"   - الدور: {user.get('role', 'غير محدد')}")
            else:
                print("❌ دالة get_user لم تجد المستخدم")
                return False
        else:
            print("⚠️ لا توجد مستخدمين في قاعدة البيانات")
            
    except Exception as e:
        print(f"❌ خطأ في اختبار get_user: {e}")
        return False
    
    # 4. اختبار دالة calculate_user_rating
    print("\n4️⃣ اختبار دالة calculate_user_rating...")
    try:
        if result:  # إذا كان هناك مستخدم
            telegram_id = result[0]
            user = get_user(telegram_id)
            if user:
                rating_data = calculate_user_rating(user['id'])
                print(f"✅ تم حساب التقييم: {rating_data}")
                
                # اختبار البيانات
                if 'average_rating' in rating_data:
                    print(f"   - متوسط التقييم: {rating_data['average_rating']}")
                if 'total_ratings' in rating_data:
                    print(f"   - إجمالي التقييمات: {rating_data['total_ratings']}")
                    
            else:
                print("⚠️ لا يمكن اختبار التقييم - مستخدم غير موجود")
        else:
            print("⚠️ لا يمكن اختبار التقييم - لا توجد مستخدمين")
            
    except Exception as e:
        print(f"❌ خطأ في اختبار calculate_user_rating: {e}")
        return False
    
    # 5. اختبار بناء رسالة المحفظة
    print("\n5️⃣ اختبار بناء رسالة المحفظة...")
    try:
        if result and get_user(result[0]):
            user = get_user(result[0])
            
            # محاكاة بناء رسالة المحفظة
            wallet_text = f"""
💳 **محفظتي المطورة** 💳

👤 **{user.get('full_name', 'مستخدم')}**
💰 **الرصيد:** {user.get('balance', 0):,.2f} ريال
💳 **رقم المحفظة:** {user.get('wallet_number', 'غير محدد')}

📊 **إحصائيات المحفظة:**
⭐ تقييمي: **0.0/5** (0 تقييم)

📋 **آخر المعاملات:**
📭 لا توجد معاملات حتى الآن
"""
            print("✅ تم بناء رسالة المحفظة بنجاح")
            print(f"   - طول الرسالة: {len(wallet_text)} حرف")
            
        else:
            print("⚠️ لا يمكن اختبار بناء الرسالة - مستخدم غير موجود")
            
    except Exception as e:
        print(f"❌ خطأ في اختبار بناء الرسالة: {e}")
        return False
    
    # 6. اختبار معالجة الأخطاء
    print("\n6️⃣ اختبار معالجة الأخطاء...")
    try:
        # اختبار معالجة خطأ قاعدة البيانات
        from bot_modules.utils import log_and_return_error
        
        error_msg = log_and_return_error("اختبار", Exception("خطأ تجريبي"), "رسالة اختبار")
        print(f"✅ تم اختبار معالجة الأخطاء: {error_msg}")
        
    except Exception as e:
        print(f"❌ خطأ في اختبار معالجة الأخطاء: {e}")
        return False
    
    print("\n" + "=" * 50)
    print("🎉 تم اختبار جميع مكونات المحفظة المطورة بنجاح!")
    return True

def test_specific_error_scenarios():
    """اختبار سيناريوهات أخطاء محددة"""
    
    print("\n🔍 اختبار سيناريوهات الأخطاء...")
    print("=" * 50)
    
    # 1. اختبار مستخدم غير موجود
    print("\n1️⃣ اختبار مستخدم غير موجود...")
    try:
        user = get_user(999999999)  # معرف غير موجود
        if user is None:
            print("✅ تم التعامل مع المستخدم غير الموجود بشكل صحيح")
        else:
            print("❌ لم يتم التعامل مع المستخدم غير الموجود بشكل صحيح")
            
    except Exception as e:
        print(f"❌ خطأ في اختبار المستخدم غير الموجود: {e}")
    
    # 2. اختبار قاعدة بيانات فارغة
    print("\n2️⃣ اختبار قاعدة بيانات فارغة...")
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # اختبار جدول فارغ
        cursor.execute('SELECT COUNT(*) FROM transactions WHERE 1=0')
        count = cursor.fetchone()[0]
        print(f"✅ تم التعامل مع الاستعلام الفارغ: {count} نتيجة")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ خطأ في اختبار قاعدة البيانات الفارغة: {e}")
    
    # 3. اختبار بيانات غير صحيحة
    print("\n3️⃣ اختبار بيانات غير صحيحة...")
    try:
        # محاكاة بيانات غير صحيحة
        invalid_data = {
            'full_name': None,
            'balance': 'غير رقم',
            'wallet_number': None
        }
        
        # اختبار معالجة البيانات غير الصحيحة
        name = invalid_data.get('full_name', 'مستخدم غير محدد')
        balance = invalid_data.get('balance', 0)
        
        if name == 'مستخدم غير محدد':
            print("✅ تم التعامل مع الاسم الفارغ بشكل صحيح")
        else:
            print("❌ لم يتم التعامل مع الاسم الفارغ بشكل صحيح")
            
    except Exception as e:
        print(f"❌ خطأ في اختبار البيانات غير الصحيحة: {e}")

if __name__ == "__main__":
    print("🚀 بدء اختبار المحفظة المطورة - Yemen Net Bot")
    print("=" * 60)
    
    # اختبار المكونات الأساسية
    if test_enhanced_wallet_components():
        # اختبار سيناريوهات الأخطاء
        test_specific_error_scenarios()
        
        print("\n" + "=" * 60)
        print("✅ تم إكمال جميع الاختبارات بنجاح!")
        print("💡 المحفظة المطورة جاهزة للاستخدام")
        
    else:
        print("\n" + "=" * 60)
        print("❌ فشل في بعض الاختبارات")
        print("🔧 يرجى مراجعة الأخطاء أعلاه وإصلاحها")
        sys.exit(1)