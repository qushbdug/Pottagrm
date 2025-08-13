#!/usr/bin/env python3
"""
ملف بدء تشغيل البوت لمنصة Render
"""

import os
import sys
import logging
import asyncio

# إضافة المجلد الحالي إلى Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# إعداد السجلات
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)

async def main_async():
    """تشغيل البوت الرئيسي بشكل غير متزامن"""
    try:
        logger.info("🚀 بدء تشغيل بوت يمن نت...")
        
        # استيراد وتشغيل البوت الرئيسي
        from main_bot import YemenNetBot
        
        bot = YemenNetBot()
        
        # تشغيل البوت حسب البيئة
        if os.getenv('RENDER'):
            # تشغيل webhook للبيئة الإنتاجية
            port = int(os.getenv('PORT', 10000))
            webhook_url = f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}"
            
            await bot.run_webhook(port=port, webhook_url=webhook_url)
        else:
            # تشغيل polling للتطوير المحلي
            await bot.run()
        
    except KeyboardInterrupt:
        logger.info("تم إيقاف البوت بواسطة المستخدم")
    except Exception as e:
        logger.error(f"خطأ حرج في التشغيل: {e}")
        raise

def main():
    """الدالة الرئيسية"""
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        logger.info("تم إيقاف البوت بواسطة المستخدم")
    except Exception as e:
        logger.error(f"خطأ حرج في التشغيل: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()