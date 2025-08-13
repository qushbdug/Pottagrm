#!/usr/bin/env python3
"""
سكريبت ترحيل البوت إلى النسخة المحسنة
"""

import logging
import sqlite3
import os
import shutil
from datetime import datetime

# إعداد السجلات
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def backup_database():
    """إنشاء نسخة احتياطية من قاعدة البيانات"""
    try:
        if os.path.exists('yemen_net.db'):
            backup_name = f'yemen_net_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.db'
            shutil.copy2('yemen_net.db', backup_name)
            logger.info(f"تم إنشاء نسخة احتياطية: {backup_name}")
            return backup_name
        return None
    except Exception as e:
        logger.error(f"خطأ في إنشاء النسخة الاحتياطية: {e}")
        return None

def migrate_database():
    """ترحيل قاعدة البيانات إلى النسخة المحسنة"""
    try:
        # تشغيل ترحيل قاعدة البيانات
        from bot.database.migrations import run_migrations
        run_migrations()
        logger.info("تم ترحيل قاعدة البيانات بنجاح")
        return True
    except Exception as e:
        logger.error(f"خطأ في ترحيل قاعدة البيانات: {e}")
        return False

def test_new_bot():
    """اختبار البوت الجديد"""
    try:
        from main_bot import YemenNetBot
        bot = YemenNetBot()
        logger.info("تم اختبار البوت الجديد بنجاح")
        return True
    except Exception as e:
        logger.error(f"خطأ في اختبار البوت الجديد: {e}")
        return False

def main():
    """الدالة الرئيسية للترحيل"""
    logger.info("🚀 بدء عملية ترحيل البوت...")
    
    try:
        # إنشاء نسخة احتياطية
        backup_file = backup_database()
        if backup_file:
            logger.info("✅ تم إنشاء النسخة الاحتياطية بنجاح")
        
        # ترحيل قاعدة البيانات
        if migrate_database():
            logger.info("✅ تم ترحيل قاعدة البيانات بنجاح")
        else:
            logger.error("❌ فشل في ترحيل قاعدة البيانات")
            return False
        
        # اختبار البوت الجديد
        if test_new_bot():
            logger.info("✅ تم اختبار البوت الجديد بنجاح")
        else:
            logger.error("❌ فشل في اختبار البوت الجديد")
            return False
        
        logger.info("🎉 تم إكمال عملية الترحيل بنجاح!")
        logger.info("يمكنك الآن تشغيل البوت المحسن باستخدام: python main_bot.py")
        
        return True
        
    except Exception as e:
        logger.error(f"خطأ حرج في عملية الترحيل: {e}")
        
        # استعادة النسخة الاحتياطية في حالة الفشل
        if backup_file and os.path.exists(backup_file):
            shutil.copy2(backup_file, 'yemen_net.db')
            logger.info("تم استعادة النسخة الاحتياطية")
        
        return False

if __name__ == '__main__':
    success = main()
    exit(0 if success else 1)