#!/usr/bin/env python3
"""
بوت كروت الإنترنت اليمني - النسخة الموحدة
Yemen Net Card Bot - Unified Version
"""

import logging
import asyncio
import sys
import os
from datetime import datetime

# إضافة bot_modules إلى مسار Python
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'bot_modules'))

# استيراد مكونات البوت
from telegram import Update, MenuButtonCommands, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ConversationHandler, PicklePersistence, filters, CallbackContext
)

# استيراد الوحدات المحلية
try:
    from config import *
    from database import init_db, get_db_connection
    from utils import *
    from handlers import *
    from admin_functions import *
except ImportError as e:
    print(f"خطأ في استيراد الوحدات: {e}")
    print("تأكد من وجود جميع ملفات الوحدات في مجلد bot_modules")
    sys.exit(1)

# إعداد التسجيل
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

async def main():
    """الدالة الرئيسية للبوت"""
    try:
        # تهيئة قاعدة البيانات
        print("🔧 تهيئة قاعدة البيانات...")
        init_db()
        print("✅ تم تهيئة قاعدة البيانات")
        
        # إنشاء تطبيق البوت
        print("🤖 إنشاء تطبيق البوت...")
        application = Application.builder().token(BOT_TOKEN).build()
        
        # إضافة معالجات الأوامر
        print("📝 إضافة معالجات الأوامر...")
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("wallet", wallet_handler))
        application.add_handler(CommandHandler("admin", admin_handler))
        application.add_handler(CommandHandler("cancel", cancel))
        
        # إضافة معالج النقر على الأزرار
        print("🔘 إضافة معالج النقر على الأزرار...")
        application.add_handler(CallbackQueryHandler(button_click_handler))
        
        # إضافة معالج الرسائل النصية
        print("📱 إضافة معالج الرسائل النصية...")
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))
        
        # تعيين قائمة الأوامر
        print("📋 تعيين قائمة الأوامر...")
        await application.bot.set_my_commands(QUICK_COMMANDS)
        
        # بدء البوت
        print("🚀 بدء البوت...")
        await application.run_polling()
        
    except Exception as e:
        logger.error(f"خطأ في تشغيل البوت: {e}")
        print(f"❌ فشل في تشغيل البوت: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 تم إيقاف البوت بواسطة المستخدم")
    except Exception as e:
        print(f"\n💥 خطأ غير متوقع: {e}")
        logger.error(f"خطأ غير متوقع: {e}")
