#!/usr/bin/env python3
"""
بوت بسيط يعمل
Simple Working Bot
"""

import logging

# إعداد التسجيل
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)

def main():
    """الدالة الرئيسية"""
    try:
        print("🚀 بدء البوت...")
        
        # استيراد المكتبة
        from telegram.ext import Updater, CommandHandler
        
        print("✅ تم استيراد المكتبة")
        
        # إنشاء البوت
        token = "7766964799:AAHex-hGfjPX6g_R2aZ7-UPrgnFxQKAjSa0"
        updater = Updater(token)
        
        print("✅ تم إنشاء البوت")
        
        # الحصول على dispatcher
        dispatcher = updater.dispatcher
        
        # إضافة معالج البداية
        def start_command(update, context):
            update.message.reply_text("🔥 مرحباً! البوت يعمل الآن!")
        
        dispatcher.add_handler(CommandHandler("start", start_command))
        
        print("✅ تم إضافة المعالج")
        print("🚀 البوت يعمل الآن...")
        print("📱 يمكنك الآن إرسال /start للبوت!")
        
        # تشغيل البوت
        updater.start_polling()
        updater.idle()
        
    except Exception as e:
        print(f"❌ خطأ: {e}")
        logger.error(f"خطأ: {e}")

if __name__ == "__main__":
    print("🎯 بدء التشغيل...")
    main()