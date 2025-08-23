#!/usr/bin/env python3
"""
Yemen Net Bot - Clean Architecture Runner
مشغل البوت مع الهندسة النظيفة - إصدار مبسط
"""

import sys
import os

# إضافة مسار bot_modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'bot_modules'))

# استيراد البوت الجديد مع معالجة للأخطاء
try:
    print("🔄 جاري تحضير البوت المنظم...")
    
    # استيراد الوحدات الأساسية
    from bot_modules.config import BOT_TOKEN, BOT_VERSION
    from bot_modules.database import init_db
    from bot_modules.db_networks import get_all_networks
    from bot_modules.show_networks import show_all_networks
    
    print("✅ تم تحميل الوحدات الجديدة بنجاح")
    print(f"📊 إصدار البوت: {BOT_VERSION}")
    
    # اختبار قاعدة البيانات
    print("🔄 اختبار قاعدة البيانات...")
    init_db()
    networks = get_all_networks()
    print(f"✅ قاعدة البيانات تعمل - تم العثور على {len(networks)} شبكة")
    
    print("\n✅ جميع الوحدات الجديدة تعمل بنجاح!")
    print("📌 ملاحظة: البوت الجديد يحتوي على:")
    print("   - db_networks.py: طبقة قاعدة البيانات المنفصلة")
    print("   - show_networks.py: طبقة العرض المنفصلة") 
    print("   - bot.py: ملف التشغيل النظيف")
    print("   - نظام تسجيل متقدم (bot_info.log & bot_errors.log)")
    print("   - دوال مساعدة موحدة في utils.py")
    
    print("\n🔧 لتشغيل البوت الجديد، استخدم:")
    print("   python3 bot.py")
    
    print("\n⚠️  في الوقت الحالي، البوت الأصلي لا زال يعمل لضمان عدم انقطاع الخدمة")
    print("   يمكن التبديل للنسخة الجديدة بعد حل مشاكل مكتبة تيليجرام")
    
except Exception as e:
    print(f"❌ خطأ في تحميل الوحدات الجديدة: {e}")
    print("💡 يمكن استخدام البوت الأصلي: python3 yemen_net_bot_new.py")
    sys.exit(1)