#!/usr/bin/env python3
"""
ملف بدء تشغيل البوت لمنصة Render
"""

import os
import sys
import logging

# إضافة المجلد الحالي إلى Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# إعداد السجلات
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)

def main():
    """تشغيل البوت الرئيسي"""
    try:
        logger.info("🚀 بدء تشغيل بوت يمن نت...")
        
        # استيراد وتشغيل البوت الرئيسي
        from main_bot import YemenNetBot
        
        bot = YemenNetBot()
        bot.run()
        
    except KeyboardInterrupt:
        logger.info("تم إيقاف البوت بواسطة المستخدم")
    except Exception as e:
        logger.error(f"خطأ حرج في التشغيل: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()