#!/usr/bin/env python3
"""
ملف تشغيل البوت المحسن مع إدارة صحيحة لـ event loop
"""

import asyncio
import logging
import os
import sys
import platform

# إضافة المسار الحالي
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# إعداد السجلات
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)

async def run_bot_async():
    """تشغيل البوت بشكل غير متزامن"""
    try:
        logger.info("🚀 بدء تشغيل بوت يمن نت المحسن...")
        
        # استيراد البوت
        from main_bot import YemenNetBot
        
        # إنشاء البوت
        bot = YemenNetBot()
        
        # إعداد الأوامر السريعة
        try:
            await bot.setup_commands()
        except Exception as e:
            logger.warning(f"فشل إعداد الأوامر السريعة: {e}")
        
        # تشغيل البوت حسب البيئة
        if os.getenv('RENDER'):
            # تشغيل webhook للبيئة الإنتاجية
            port = int(os.getenv('PORT', 8080))
            webhook_url = f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}"
            
            logger.info(f"تشغيل webhook على المنفذ {port}")
            logger.info(f"webhook URL: {webhook_url}")
            
            # تشغيل webhook
            async with bot.application:
                await bot.application.updater.start_webhook(
                    listen='0.0.0.0',
                    port=port,
                    webhook_url=webhook_url,
                    drop_pending_updates=True
                )
                
                # الانتظار إلى ما لا نهاية
                await asyncio.Event().wait()
        else:
            # تشغيل polling للتطوير المحلي
            logger.info("تشغيل polling للتطوير المحلي")
            
            # تشغيل polling
            async with bot.application:
                await bot.application.updater.start_polling(drop_pending_updates=True)
                
                # الانتظار إلى ما لا نهاية
                await asyncio.Event().wait()
                
    except KeyboardInterrupt:
        logger.info("تم إيقاف البوت بواسطة المستخدم")
    except Exception as e:
        logger.error(f"خطأ حرج في تشغيل البوت: {e}", exc_info=True)
        raise

def main():
    """الدالة الرئيسية"""
    try:
        # إصلاح مشكلة event loop في Windows
        if platform.system() == 'Windows':
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        
        # تشغيل البوت
        asyncio.run(run_bot_async())
        
    except KeyboardInterrupt:
        logger.info("تم إيقاف البوت بواسطة المستخدم")
    except Exception as e:
        logger.error(f"خطأ حرج في main: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()