#!/usr/bin/env python3
"""
Yemen Net Bot - Main Entry Point (Clean Architecture)
بوت بيع كروت الإنترنت اليمني - نقطة الدخول الرئيسية (هندسة نظيفة)

هذا الملف مسؤول فقط عن:
1. إعداد البوت والاتصال
2. ربط الطبقات المنفصلة
3. إدارة دورة حياة البوت

منطق الأعمال منفصل في ملفات مختصة:
- db_networks.py: عمليات قاعدة البيانات للشبكات
- show_networks.py: عرض الشبكات في تيليجرام
- handlers.py: باقي معالجات البوت
"""

import logging
import asyncio
import sys
import os
from datetime import datetime

# إضافة مسار bot_modules لـ Python
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'bot_modules'))

# استيراد مكونات تيليجرام
from telegram import Update, MenuButtonCommands
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ConversationHandler, PicklePersistence, filters, CallbackContext
)

# استيراد المكونات المنفصلة
try:
    from bot_modules.config import *
    from bot_modules.database import init_db
    from bot_modules.utils import get_user, update_user_activity
    from bot_modules.handlers import COMMAND_HANDLERS, CONVERSATION_STATES, handle_text_message, show_main_menu
    from bot_modules.admin_functions import ADMIN_CALLBACKS
    from bot_modules.callback_utils import get_callback_data
    from bot_modules.error_handler import ErrorHandler
    
    # استيراد وحدات الشبكات المنفصلة
    from bot_modules.show_networks import show_all_networks, show_network_details, show_search_results
    from bot_modules.db_networks import NetworkNotFoundError
    
except ImportError as e:
    print(f"❌ خطأ في استيراد الوحدات: {e}")
    print("تأكد من وجود جميع ملفات الوحدات في مجلد bot_modules")
    sys.exit(1)

# إعداد نظام التسجيل المتقدم
def setup_advanced_logging():
    """إعداد نظام تسجيل متقدم مع فصل الأخطاء عن المعلومات العادية"""
    
    # إعداد التنسيق المتقدم
    detailed_formatter = logging.Formatter(
        '%(asctime)s | %(name)s | %(levelname)s | %(funcName)s:%(lineno)d | %(message)s'
    )
    
    simple_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # إعداد logger الجذر
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # مسح المعالجات الموجودة
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # معالج الملف للمعلومات العادية
    info_handler = logging.FileHandler('bot_info.log', encoding='utf-8')
    info_handler.setLevel(logging.INFO)
    info_handler.setFormatter(simple_formatter)
    
    # فلتر لاستبعاد الأخطاء من ملف المعلومات
    class NoErrorFilter(logging.Filter):
        def filter(self, record):
            return record.levelno < logging.ERROR
    
    info_handler.addFilter(NoErrorFilter())
    
    # معالج الملف للأخطاء فقط
    error_handler = logging.FileHandler('bot_errors.log', encoding='utf-8')
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(detailed_formatter)
    
    # معالج الكونسول للأخطاء الحرجة فقط
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.ERROR)
    console_handler.setFormatter(detailed_formatter)
    
    # إضافة المعالجات
    root_logger.addHandler(info_handler)
    root_logger.addHandler(error_handler)
    root_logger.addHandler(console_handler)
    
    # logger خاص بالبوت
    bot_logger = logging.getLogger('YemenNetBot')
    bot_logger.setLevel(logging.INFO)
    
    return bot_logger

# إعداد التسجيل
logger = setup_advanced_logging()

class BotRouter:
    """موجه البوت - مسؤول عن توجيه الطلبات للوحدات المناسبة"""
    
    @staticmethod
    async def handle_callback_query(update: Update, context: CallbackContext):
        """معالج الاستعلامات المنفصل والنظيف"""
        try:
            query = update.callback_query
            
            # الإجابة على الاستعلام لمنع انتظار المستخدم
            try:
                await query.answer()
            except Exception:
                pass  # تجاهل أخطاء انتهاء المهلة
            
            callback_data = query.data
            
            # التحقق من المستخدم
            user = get_user(query.from_user.id)
            if not user:
                await query.edit_message_text(f"{EMOJIS['error']} يرجى التسجيل أولاً /start")
                return
            
            update_user_activity(user['id'])
            
            logger.info(f"معالجة callback: {callback_data} من المستخدم {user['full_name']}")
            
            # توجيه طلبات الشبكات للوحدة المختصة
            if callback_data == 'search_networks':
                await show_all_networks(update, context)
                return
            
            elif callback_data.startswith('network_'):
                network_id = callback_data.split('_')[1]
                await show_network_details(update, context, network_id)
                return
            
            elif callback_data.startswith('buy_from_network_'):
                # استخراج معرف الشبكة من callback data الجديد
                try:
                    callback_info = get_callback_data(callback_data)
                    if callback_info and 'network_id' in callback_info:
                        network_id = str(callback_info['network_id'])
                        await show_network_details(update, context, network_id)
                        return
                except Exception as e:
                    logger.error(f"خطأ في استخراج معرف الشبكة: {e}", exc_info=True)
                
                # fallback للنظام القديم
                network_id = callback_data.split('_')[-1]
                await show_network_details(update, context, network_id)
                return
            
            # القائمة الرئيسية
            elif callback_data == 'main_menu':
                await show_main_menu(update, context, user['role'])
                return
            
            # توجيه باقي الطلبات للمعالجات الأخرى
            elif callback_data in ADMIN_CALLBACKS:
                if user['role'] == 'super_admin':
                    await ADMIN_CALLBACKS[callback_data](update, context)
                else:
                    await query.edit_message_text(f"{EMOJIS['error']} ليس لديك صلاحية لهذه العملية")
                return
            
            # معالجة الطلبات الأخرى من خلال النظام الموجود
            else:
                # استيراد المعالج الرئيسي من النظام القديم لباقي الطلبات
                from yemen_net_bot_new import button_click_handler as legacy_handler
                await legacy_handler(update, context)
                return
            
        except NetworkNotFoundError as e:
            logger.warning(f"الشبكة المطلوبة غير موجودة: {e}")
            await ErrorHandler.handle_general_error(
                update, context, "الشبكة المطلوبة غير موجودة أو غير متاحة"
            )
            
        except Exception as e:
            logger.error(f"خطأ في معالجة callback query: {e}", exc_info=True)
            await ErrorHandler.handle_general_error(
                update, context, "حدث خطأ في معالجة طلبك"
            )

class YemenNetBot:
    """الكلاس الرئيسي لإدارة البوت"""
    
    def __init__(self):
        self.application = None
        self.router = BotRouter()
    
    def setup_handlers(self):
        """إعداد معالجات البوت بشكل منظم"""
        
        # المعالجات الأساسية
        self.application.add_handler(CommandHandler("start", COMMAND_HANDLERS['start']))
        self.application.add_handler(CommandHandler("help", COMMAND_HANDLERS['help']))
        self.application.add_handler(CommandHandler("cancel", COMMAND_HANDLERS['cancel']))
        
        # معالج الاستعلامات المنفصل
        self.application.add_handler(CallbackQueryHandler(self.router.handle_callback_query))
        
        # معالج النصوص
        self.application.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND, 
            handle_text_message
        ))
        
        # معالج المحادثات
        conversation_handler = ConversationHandler(
            entry_points=[CommandHandler("start", COMMAND_HANDLERS['start'])],
            states=CONVERSATION_STATES,
            fallbacks=[CommandHandler("cancel", COMMAND_HANDLERS['cancel'])]
        )
        self.application.add_handler(conversation_handler)
        
        logger.info("تم إعداد معالجات البوت بنجاح")
    
    async def setup_bot_commands(self):
        """إعداد أوامر البوت"""
        try:
            await self.application.bot.set_my_commands(BOT_COMMANDS)
            await self.application.bot.set_chat_menu_button(
                menu_button=MenuButtonCommands()
            )
            logger.info("تم إعداد أوامر البوت بنجاح")
        except Exception as e:
            logger.error(f"خطأ في إعداد أوامر البوت: {e}", exc_info=True)
    
    async def initialize(self):
        """تهيئة البوت"""
        try:
            logger.info("بدء تهيئة البوت...")
            
            # تهيئة قاعدة البيانات
            init_db()
            logger.info("تم تهيئة قاعدة البيانات")
            
            # إنشاء التطبيق
            persistence = PicklePersistence(filepath="bot_data.pkl")
            self.application = Application.builder().token(BOT_TOKEN).persistence(persistence).build()
            
            # إعداد المعالجات
            self.setup_handlers()
            
            # إعداد أوامر البوت
            await self.setup_bot_commands()
            
            logger.info("تم تهيئة البوت بنجاح")
            
        except Exception as e:
            logger.error(f"خطأ فادح في تهيئة البوت: {e}", exc_info=True)
            raise
    
    async def start(self):
        """بدء تشغيل البوت"""
        await self.initialize()
        
        logger.info("🚀 بدء تشغيل البوت...")
        logger.info(f"📊 إصدار البوت: {BOT_VERSION}")
        logger.info(f"🕐 وقت البدء: {datetime.now()}")
        
        # بدء البوت
        await self.application.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True
        )

async def main():
    """الدالة الرئيسية"""
    bot = None
    try:
        bot = YemenNetBot()
        await bot.start()
    except KeyboardInterrupt:
        logger.info("تم إيقاف البوت بواسطة المستخدم")
    except Exception as e:
        logger.error(f"خطأ فادح في تطبيق البوت: {e}", exc_info=True)
        raise
    finally:
        if bot and bot.application:
            try:
                await bot.application.stop()
                await bot.application.shutdown()
            except Exception as e:
                logger.error(f"خطأ في إغلاق البوت: {e}")

if __name__ == "__main__":
    # تشغيل البوت
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 تم إيقاف البوت بنجاح")
    except Exception as e:
        print(f"❌ خطأ فادح: {e}")
        sys.exit(1)