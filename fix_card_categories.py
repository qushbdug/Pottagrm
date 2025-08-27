#!/usr/bin/env python3
"""
إصلاح مشكلة فئات الكروت
Fix Card Categories Issue
"""

import sqlite3
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fix_card_categories():
    """إصلاح مشكلة فئات الكروت"""
    print("🔧 === إصلاح فئات الكروت ===")
    
    try:
        conn = sqlite3.connect('yemen_net.db', timeout=30.0)
        cursor = conn.cursor()
        
        # إضافة الأعمدة المفقودة إذا لم تكن موجودة
        try:
            cursor.execute('ALTER TABLE card_categories ADD COLUMN category_name TEXT')
            print("✅ تم إضافة العمود category_name")
        except sqlite3.OperationalError:
            print("ℹ️ العمود category_name موجود بالفعل")
        
        try:
            cursor.execute('ALTER TABLE card_categories ADD COLUMN description TEXT')
            print("✅ تم إضافة العمود description")
        except sqlite3.OperationalError:
            print("ℹ️ العمود description موجود بالفعل")
        
        # الحصول على الشبكات النشطة
        cursor.execute("SELECT id, name FROM networks WHERE is_active = 1")
        networks = cursor.fetchall()
        
        print(f"📊 وجدت {len(networks)} شبكة نشطة")
        
        # تعريف فئات الكروت الافتراضية
        default_categories = [
            {'name': '5 ريال', 'value': 5, 'price': 5.5},
            {'name': '10 ريال', 'value': 10, 'price': 11.0},
            {'name': '20 ريال', 'value': 20, 'price': 22.0},
            {'name': '50 ريال', 'value': 50, 'price': 55.0},
            {'name': '100 ريال', 'value': 100, 'price': 110.0}
        ]
        
        total_categories_created = 0
        
        for network_id, network_name in networks:
            print(f"🔧 إنشاء فئات للشبكة: {network_name}")
            
            for category in default_categories:
                # التحقق من وجود الفئة
                cursor.execute("""
                    SELECT id FROM card_categories 
                    WHERE network_id = ? AND value = ?
                """, (network_id, category['value']))
                
                if not cursor.fetchone():
                    cursor.execute("""
                        INSERT INTO card_categories 
                        (network_id, name, value, price, category_name, is_available, stock_count)
                        VALUES (?, ?, ?, ?, ?, 1, 100)
                    """, (
                        network_id,
                        category['name'],
                        category['value'],
                        category['price'],
                        category['name']
                    ))
                    
                    total_categories_created += 1
                    print(f"  ✅ تم إنشاء فئة {category['name']}")
                else:
                    print(f"  ℹ️ فئة {category['name']} موجودة بالفعل")
        
        print(f"\n📊 إجمالي الفئات المُنشأة: {total_categories_created}")
        
        # إنشاء كروت افتراضية
        print("\n🔧 إنشاء كروت افتراضية...")
        
        cursor.execute("""
            SELECT cc.id, cc.network_id, cc.value, cc.name, n.name as network_name
            FROM card_categories cc
            JOIN networks n ON cc.network_id = n.id
            WHERE cc.is_available = 1
        """)
        categories = cursor.fetchall()
        
        total_cards_created = 0
        
        for category_id, network_id, value, category_name, network_name in categories:
            # إنشاء 50 كرت لكل فئة
            for i in range(50):
                card_number = f"{network_id:03d}{value:03d}{i+1:03d}"
                serial_number = f"SN{category_id:03d}{i+1:03d}"
                
                cursor.execute("""
                    INSERT INTO cards (category_id, card_number, serial_number, is_sold, uploaded_at)
                    VALUES (?, ?, ?, 0, CURRENT_TIMESTAMP)
                """, (category_id, card_number, serial_number))
                
                total_cards_created += 1
            
            print(f"  ✅ تم إنشاء 50 كرت للفئة {category_name} في {network_name}")
        
        print(f"\n📊 إجمالي الكروت المُنشأة: {total_cards_created}")
        
        conn.commit()
        conn.close()
        
        print("✅ تم إصلاح فئات الكروت بنجاح")
        return True
        
    except Exception as e:
        logger.error(f"خطأ في إصلاح فئات الكروت: {e}")
        return False

def verify_fix():
    """التحقق من الإصلاح"""
    print("\n🔍 === التحقق من الإصلاح ===")
    
    try:
        conn = sqlite3.connect('yemen_net.db', timeout=30.0)
        cursor = conn.cursor()
        
        # فحص فئات الكروت
        cursor.execute("SELECT COUNT(*) FROM card_categories")
        categories_count = cursor.fetchone()[0]
        print(f"📊 فئات الكروت: {categories_count}")
        
        # فحص الكروت
        cursor.execute("SELECT COUNT(*) FROM cards")
        cards_count = cursor.fetchone()[0]
        print(f"📊 الكروت: {cards_count}")
        
        # فحص الشبكات
        cursor.execute("SELECT COUNT(*) FROM networks WHERE is_active = 1")
        networks_count = cursor.fetchone()[0]
        print(f"📊 الشبكات النشطة: {networks_count}")
        
        # فحص المستخدمين
        cursor.execute("SELECT COUNT(*) FROM users")
        users_count = cursor.fetchone()[0]
        print(f"📊 المستخدمين: {users_count}")
        
        conn.close()
        
        if categories_count > 0 and cards_count > 0:
            print("✅ تم إصلاح المشكلة بنجاح!")
            return True
        else:
            print("❌ المشكلة لم تُحل")
            return False
            
    except Exception as e:
        logger.error(f"خطأ في التحقق: {e}")
        return False

def main():
    """الدالة الرئيسية"""
    print("🔧 أداة إصلاح فئات الكروت")
    print("=" * 50)
    
    try:
        # إصلاح المشكلة
        if fix_card_categories():
            # التحقق من الإصلاح
            if verify_fix():
                print("\n🎉 تم إصلاح جميع المشاكل بنجاح!")
                print("🚀 البوت جاهز للعمل!")
            else:
                print("\n⚠️ الإصلاح لم يكتمل")
        else:
            print("\n❌ فشل في الإصلاح")
            
    except Exception as e:
        print(f"\n💥 حدث خطأ غير متوقع: {e}")
        logger.error(f"خطأ غير متوقع: {e}")

if __name__ == "__main__":
    main()