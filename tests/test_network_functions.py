#!/usr/bin/env python3
"""
اختبار شامل لجميع دوال إنشاء الشبكات
Comprehensive Network Functions Test
"""

import sqlite3
import sys
import os
from datetime import datetime

# إضافة مسار المشروع
sys.path.append('/workspace')

def test_database_manager():
    """اختبار database_manager"""
    try:
        from bot_modules.database_manager import create_network_safe
        
        print("🧪 اختبار database_manager.create_network_safe...")
        
        network_data = {
            'name': f'شبكة اختبار DB {datetime.now().strftime("%H%M%S")}',
            'provider': 'مزود الاختبار',
            'description': 'شبكة اختبار لفحص database_manager',
            'location': 'موقع اختبار',
            'city': 'صنعاء'
        }
        
        # الحصول على أول مستخدم
        conn = sqlite3.connect('/workspace/yemen_net.db')
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users LIMIT 1")
        user_id = cursor.fetchone()[0]
        conn.close()
        
        # اختبار إنشاء الشبكة
        network_id = create_network_safe(network_data, user_id)
        
        if network_id:
            print(f"  ✅ تم إنشاء الشبكة بنجاح - ID: {network_id}")
            
            # حذف الشبكة الاختبارية
            conn = sqlite3.connect('/workspace/yemen_net.db')
            cursor = conn.cursor()
            cursor.execute("DELETE FROM networks WHERE id = ?", (network_id,))
            conn.commit()
            conn.close()
            print("  🗑️ تم حذف شبكة الاختبار")
            
            return True
        else:
            print("  ❌ فشل في إنشاء الشبكة")
            return False
            
    except Exception as e:
        print(f"  ❌ خطأ في اختبار database_manager: {e}")
        return False

def test_network_service():
    """اختبار network_service"""
    try:
        from services.network_service import network_service
        
        print("🧪 اختبار network_service.create_network...")
        
        network_data = {
            'name': f'شبكة اختبار Service {datetime.now().strftime("%H%M%S")}',
            'provider': 'مزود الاختبار',
            'description': 'شبكة اختبار لفحص network_service',
            'location': 'موقع اختبار'
        }
        
        # الحصول على أول مستخدم
        conn = sqlite3.connect('/workspace/yemen_net.db')
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users LIMIT 1")
        user_id = cursor.fetchone()[0]
        conn.close()
        
        # اختبار إنشاء الشبكة
        success, network_id, message = network_service.create_network(network_data, user_id)
        
        if success and network_id:
            print(f"  ✅ تم إنشاء الشبكة بنجاح - ID: {network_id}")
            print(f"  📝 الرسالة: {message}")
            
            # حذف الشبكة الاختبارية
            conn = sqlite3.connect('/workspace/yemen_net.db')
            cursor = conn.cursor()
            cursor.execute("DELETE FROM networks WHERE id = ?", (network_id,))
            conn.commit()
            conn.close()
            print("  🗑️ تم حذف شبكة الاختبار")
            
            return True
        else:
            print(f"  ❌ فشل في إنشاء الشبكة: {message}")
            return False
            
    except Exception as e:
        print(f"  ❌ خطأ في اختبار network_service: {e}")
        return False

def test_direct_sql():
    """اختبار SQL مباشر"""
    try:
        print("🧪 اختبار SQL مباشر...")
        
        conn = sqlite3.connect('/workspace/yemen_net.db')
        cursor = conn.cursor()
        
        # الحصول على أول مستخدم
        cursor.execute("SELECT id, full_name FROM users LIMIT 1")
        user = cursor.fetchone()
        user_id, user_name = user[0], user[1]
        
        # إنشاء شبكة مباشرة
        test_name = f'شبكة اختبار SQL {datetime.now().strftime("%H%M%S")}'
        
        cursor.execute('''
            INSERT INTO networks (supplier_id, name, city, provider, description, location, created_by, is_active, is_approved, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, 1, 1, CURRENT_TIMESTAMP)
        ''', (user_id, test_name, 'صنعاء', user_name, 'شبكة اختبار SQL', 'موقع اختبار', user_id))
        
        network_id = cursor.lastrowid
        conn.commit()
        
        print(f"  ✅ تم إنشاء الشبكة بنجاح - ID: {network_id}")
        
        # حذف الشبكة الاختبارية
        cursor.execute("DELETE FROM networks WHERE id = ?", (network_id,))
        conn.commit()
        conn.close()
        print("  🗑️ تم حذف شبكة الاختبار")
        
        return True
        
    except Exception as e:
        print(f"  ❌ خطأ في اختبار SQL مباشر: {e}")
        return False

def test_all_required_columns():
    """اختبار جميع الأعمدة المطلوبة"""
    try:
        print("🧪 اختبار جميع الأعمدة المطلوبة...")
        
        conn = sqlite3.connect('/workspace/yemen_net.db')
        cursor = conn.cursor()
        
        # فحص هيكل الجدول
        cursor.execute('PRAGMA table_info(networks)')
        columns = cursor.fetchall()
        
        required_columns = []
        for col in columns:
            if col[3]:  # NOT NULL
                required_columns.append(col[1])
        
        print(f"  📋 الأعمدة المطلوبة: {required_columns}")
        
        # اختبار إدراج مع جميع الأعمدة المطلوبة
        cursor.execute("SELECT id, full_name FROM users LIMIT 1")
        user = cursor.fetchone()
        user_id, user_name = user[0], user[1]
        
        test_name = f'شبكة اختبار كاملة {datetime.now().strftime("%H%M%S")}'
        
        # إدراج مع جميع الأعمدة المطلوبة
        cursor.execute('''
            INSERT INTO networks (supplier_id, name, city, provider, description, location, created_by, is_active, is_approved)
            VALUES (?, ?, ?, ?, ?, ?, ?, 1, 1)
        ''', (user_id, test_name, 'صنعاء', user_name, 'اختبار كامل', 'موقع كامل', user_id))
        
        network_id = cursor.lastrowid
        print(f"  ✅ تم إدراج الشبكة مع جميع الأعمدة المطلوبة - ID: {network_id}")
        
        # فحص البيانات المُدرجة
        cursor.execute("SELECT supplier_id, name, city FROM networks WHERE id = ?", (network_id,))
        result = cursor.fetchone()
        
        if result and all(result):
            print(f"  ✅ جميع الأعمدة المطلوبة تحتوي على قيم: {result}")
        else:
            print(f"  ⚠️ بعض الأعمدة فارغة: {result}")
        
        # حذف الشبكة الاختبارية
        cursor.execute("DELETE FROM networks WHERE id = ?", (network_id,))
        conn.commit()
        conn.close()
        print("  🗑️ تم حذف شبكة الاختبار")
        
        return True
        
    except Exception as e:
        print(f"  ❌ خطأ في اختبار الأعمدة المطلوبة: {e}")
        return False

def main():
    """الدالة الرئيسية"""
    print("🧪 **اختبار شامل لجميع دوال إنشاء الشبكات** 🧪")
    print("=" * 60)
    
    tests = [
        ("اختبار SQL مباشر", test_direct_sql),
        ("اختبار الأعمدة المطلوبة", test_all_required_columns),
        ("اختبار database_manager", test_database_manager),
        ("اختبار network_service", test_network_service)
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        print(f"\n🔍 {test_name}:")
        try:
            if test_func():
                passed += 1
                print(f"  🎉 {test_name} - نجح")
            else:
                failed += 1
                print(f"  ❌ {test_name} - فشل")
        except Exception as e:
            failed += 1
            print(f"  💥 {test_name} - خطأ: {e}")
    
    print("\n" + "=" * 60)
    print(f"📊 **النتائج النهائية:**")
    print(f"✅ نجح: {passed}")
    print(f"❌ فشل: {failed}")
    print(f"📈 معدل النجاح: {(passed/(passed+failed)*100):.1f}%")
    
    if failed == 0:
        print("\n🎉 **جميع الاختبارات نجحت! البوت جاهز للعمل** 🎉")
        return True
    else:
        print(f"\n⚠️ **يوجد {failed} اختبار فاشل. يحتاج إصلاح** ⚠️")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)