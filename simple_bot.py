#!/usr/bin/env python3
"""
بوت بسيط جداً
Simple Bot
"""

import logging
import asyncio
import sys
import os

# إعداد التسجيل
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)

async def main():
    """الدالة الرئيسية"""
    try:
        print("🚀 بدء اختبار البوت...")
        
        # محاولة استيراد المكتبة
        print("📦 استيراد مكتبة python-telegram-bot...")
        from telegram import Update, BotCommand
        from telegram.ext import Application, CommandHandler, filters, ContextTypes
        print("✅ تم استيراد المكتبة بنجاح")
        
        # اختبار إنشاء التطبيق
        print("🤖 إنشاء تطبيق البوت...")
        application = Application.builder().token("7766964799:AAHex-hGfjPX6g_R2aZ7-UPrgnFxQKAjSa0").build()
        print("✅ تم إنشاء التطبيق بنجاح")
        
        # اختبار إضافة معالج بسيط
        async def test_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
            await update.message.reply_text("✅ البوت يعمل بنجاح!")
        
        print("📝 إضافة معالج الاختبار...")
        application.add_handler(CommandHandler("test", test_handler))
        print("✅ تم إضافة المعالج بنجاح")
        
        print("🎉 جميع الاختبارات نجحت!")
        print("🚀 البوت جاهز للتشغيل")
        
        # محاولة تشغيل البوت
        print("🚀 بدء البوت...")
        await application.run_polling(allowed_updates=Update.ALL_TYPES)
        
    except Exception as e:
        print(f"❌ فشل في الاختبار: {e}")
        logger.error(f"خطأ في الاختبار: {e}")
        
        # محاولة تشغيل البوت رغم الخطأ
        print("🔄 محاولة تشغيل البوت رغم الخطأ...")
        
        try:
            # إنشاء تطبيق جديد
            application = Application.builder().token("7766964799:AAHex-hGfjPX6g_R2aZ7-UPrgnFxQKAjSa0").build()
            
            # إضافة معالج بسيط
            async def simple_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
                await update.message.reply_text("🔥 مرحباً! البوت يعمل الآن!")
            
            application.add_handler(CommandHandler("start", simple_start))
            print("✅ تم إضافة معالج البداية")
            
            print("🚀 بدء البوت...")
            await application.run_polling(allowed_updates=Update.ALL_TYPES)
            
        except Exception as e2:
            print(f"❌ فشل في تشغيل البوت: {e2}")
            logger.error(f"خطأ في تشغيل البوت: {e2}")

if __name__ == "__main__":
    print("🎯 بدء التشغيل...")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 تم إيقاف البوت بواسطة المستخدم")
    except Exception as e:
        print(f"💥 خطأ غير متوقع: {e}")
        logger.error(f"خطأ غير متوقع: {e}")