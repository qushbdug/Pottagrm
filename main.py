#!/usr/bin/env python3
"""
Yemen Net Bot - الملف الرئيسي للتشغيل
نظام بوت تليجرام متطور لبيع كروت الشبكة
"""

import os
import sys
import logging

# إضافة المسار الحالي
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# إعداد السجلات
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)

def main():
    """الدالة الرئيسية للتشغيل"""
    try:
        logger.info("🚀 بدء تشغيل بوت يمن نت...")
        
        # استخدام run_bot.py للتشغيل
        from run_bot import main as run_bot_main
        run_bot_main()
        
    except KeyboardInterrupt:
        logger.info("تم إيقاف البوت بواسطة المستخدم")
    except Exception as e:
        logger.error(f"خطأ حرج في التشغيل: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()