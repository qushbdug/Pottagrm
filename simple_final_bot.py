#!/usr/bin/env python3
"""
بوت بسيط بدون APScheduler
Simple Bot without APScheduler
"""

import logging
import asyncio

# إعداد التسجيل
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)

async def main():
    """الدالة الرئيسية"""
    try:
        print("🚀 بدء البوت...")
        
        # استيراد المكتبة
        from telegram import Update
        from telegram.ext import Application, CommandHandler, ContextTypes
        
        print("✅ تم استيراد المكتبة")
        
        # إنشاء التطبيق بدون APScheduler
        token = "7766964799:AAHex-hGfjPX6g_R2aZ7-UPrgnFxQKAjSa0"
        application = Application.builder().token(token).build()
        
        print("✅ تم إنشاء التطبيق")
        
        # إضافة معالج البداية
        async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
            await update.message.reply_text("🔥 مرحباً! البوت يعمل الآن!")
        
        application.add_handler(CommandHandler("start", start_command))
        
        print("✅ تم إضافة المعالج")
        print("🚀 البوت يعمل الآن...")
        
        # تشغيل البوت
        await application.run_polling()
        
    except Exception as e:
        print(f"❌ خطأ: {e}")
        logger.error(f"خطأ: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🎯 بدء التشغيل...")
    asyncio.run(main())