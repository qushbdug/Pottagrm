#!/usr/bin/env python3
"""
بوت كروت الإنترنت اليمني - النسخة المبسطة
Yemen Net Card Bot - Simple Version
"""

import logging
import asyncio
import sys
import os
from datetime import datetime

# إضافة bot_modules إلى مسار Python
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'bot_modules'))

# استيراد مكونات البوت
from telegram import Update, BotCommand, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Updater, CommandHandler, MessageHandler, CallbackQueryHandler,
    ConversationHandler, Filters, CallbackContext
)

# إعداد التسجيل
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)

# تعريف حالات المحادثة
GET_FULL_NAME, GET_PHONE, CHOOSE_ROLE = range(3)

# تعريف الأوامر السريعة
QUICK_COMMANDS = [
    BotCommand('start', '🏠 البداية - القائمة الرئيسية'),
    BotCommand('wallet', '💳 محفظتي'),
    BotCommand('help', '❓ المساعدة'),
    BotCommand('cancel', '❌ إلغاء العملية الحالية'),
]

def start(update: Update, context: CallbackContext) -> int:
    """معالج أمر البداية"""
    try:
        user = update.effective_user
        welcome_text = f"""
🔥 **مرحباً بك في بوت كروت الإنترنت اليمني!** 🔥

👤 **المستخدم:** {user.first_name}
🆔 **المعرف:** {user.id}

🚀 **الميزات المتاحة:**
• 💳 محفظة إلكترونية
• 🛒 شراء كروت الشبكة
• 💸 تحويل رصيد
• 📊 تقارير مفصلة
• ⭐ نظام تقييمات

📝 **للمتابعة، يرجى إدخال اسمك الكامل:**
"""
        
        update.message.reply_text(welcome_text, parse_mode='Markdown')
        return GET_FULL_NAME
        
    except Exception as e:
        logger.error(f"خطأ في معالج البداية: {e}")
        update.message.reply_text("❌ حدث خطأ. يرجى المحاولة مرة أخرى.")
        return ConversationHandler.END

def get_full_name(update: Update, context: CallbackContext) -> int:
    """الحصول على الاسم الكامل"""
    try:
        full_name = update.message.text
        context.user_data['full_name'] = full_name
        
        update.message.reply_text(
            f"✅ تم حفظ الاسم: {full_name}\n\n"
            "📱 الآن يرجى إدخال رقم هاتفك:"
        )
        return GET_PHONE
        
    except Exception as e:
        logger.error(f"خطأ في الحصول على الاسم: {e}")
        update.message.reply_text("❌ حدث خطأ. يرجى المحاولة مرة أخرى.")
        return ConversationHandler.END

def get_phone(update: Update, context: CallbackContext) -> int:
    """الحصول على رقم الهاتف"""
    try:
        phone = update.message.text
        context.user_data['phone'] = phone
        
        # إنشاء قائمة اختيار الدور
        keyboard = [
            [InlineKeyboardButton("👤 عميل", callback_data="role_customer")],
            [InlineKeyboardButton("🤝 وكيل", callback_data="role_agent")],
            [InlineKeyboardButton("🏢 مزود", callback_data="role_supplier")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        update.message.reply_text(
            f"✅ تم حفظ رقم الهاتف: {phone}\n\n"
            "🎯 الآن اختر دورك في النظام:",
            reply_markup=reply_markup
        )
        return CHOOSE_ROLE
        
    except Exception as e:
        logger.error(f"خطأ في الحصول على الهاتف: {e}")
        update.message.reply_text("❌ حدث خطأ. يرجى المحاولة مرة أخرى.")
        return ConversationHandler.END

def choose_role(update: Update, context: CallbackContext) -> int:
    """اختيار الدور"""
    try:
        query = update.callback_query
        query.answer()
        
        role = query.data.replace('role_', '')
        context.user_data['role'] = role
        
        role_names = {
            'customer': 'عميل',
            'agent': 'وكيل', 
            'supplier': 'مزود'
        }
        
        query.edit_message_text(
            f"🎉 **تم التسجيل بنجاح!** 🎉\n\n"
            f"👤 **الاسم:** {context.user_data['full_name']}\n"
            f"📱 **الهاتف:** {context.user_data['phone']}\n"
            f"🎯 **الدور:** {role_names.get(role, role)}\n\n"
            f"🚀 **مرحباً بك في النظام!**\n\n"
            f"استخدم /wallet لعرض محفظتك\n"
            f"استخدم /help للمساعدة",
            parse_mode='Markdown'
        )
        
        return ConversationHandler.END
        
    except Exception as e:
        logger.error(f"خطأ في اختيار الدور: {e}")
        update.callback_query.edit_message_text("❌ حدث خطأ. يرجى المحاولة مرة أخرى.")
        return ConversationHandler.END

def wallet_handler(update: Update, context: CallbackContext):
    """معالج أمر المحفظة"""
    try:
        user = update.effective_user
        
        # محاكاة بيانات المحفظة
        balance = 1000.0
        transactions = [
            {"type": "إيداع", "amount": 500, "date": "2025-08-26"},
            {"type": "شراء كرت", "amount": -200, "date": "2025-08-25"},
            {"type": "تحويل", "amount": -100, "date": "2025-08-24"}
        ]
        
        wallet_text = f"""
💳 **محفظتك الإلكترونية** 💳

👤 **المستخدم:** {user.first_name}
💰 **الرصيد الحالي:** {balance} ريال

📊 **آخر المعاملات:**
"""
        
        for trans in transactions:
            emoji = "➕" if trans["amount"] > 0 else "➖"
            wallet_text += f"{emoji} {trans['type']}: {abs(trans['amount'])} ريال ({trans['date']})\n"
        
        wallet_text += "\n🔧 **الميزات المتاحة:**\n• 💸 تحويل رصيد\n• 🛒 شراء كروت\n• 📊 تقارير مفصلة"
        
        update.message.reply_text(wallet_text, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"خطأ في معالج المحفظة: {e}")
        update.message.reply_text("❌ حدث خطأ في عرض المحفظة.")

def help_handler(update: Update, context: CallbackContext):
    """معالج أمر المساعدة"""
    help_text = """
❓ **مركز المساعدة** ❓

🚀 **الأوامر المتاحة:**
• /start - بدء التسجيل
• /wallet - عرض المحفظة
• /help - هذه الرسالة
• /cancel - إلغاء العملية الحالية

💡 **نصائح للاستخدام:**
• تأكد من إدخال بيانات صحيحة
• استخدم /cancel لإلغاء أي عملية
• تواصل مع الدعم الفني عند الحاجة

📞 **الدعم الفني:**
• البريد الإلكتروني: support@yemen-net.com
• الهاتف: +967-XXX-XXX-XXX
"""
    
    update.message.reply_text(help_text, parse_mode='Markdown')

def cancel(update: Update, context: CallbackContext) -> int:
    """إلغاء العملية الحالية"""
    try:
        context.user_data.clear()
        update.message.reply_text(
            "❌ تم إلغاء العملية.\n\n"
            "استخدم /start للبدء من جديد"
        )
        return ConversationHandler.END
        
    except Exception as e:
        logger.error(f"خطأ في إلغاء العملية: {e}")
        update.message.reply_text("❌ حدث خطأ.")
        return ConversationHandler.END

def button_click_handler(update: Update, context: CallbackContext):
    """معالج النقر على الأزرار"""
    try:
        query = update.callback_query
        query.answer()
        
        if query.data.startswith('role_'):
            return choose_role(update, context)
        else:
            query.edit_message_text("❌ زر غير معروف")
            
    except Exception as e:
        logger.error(f"خطأ في معالج النقر: {e}")
        update.callback_query.answer("❌ حدث خطأ")

def main():
    """الدالة الرئيسية للبوت"""
    try:
        # إنشاء تطبيق البوت
        print("🤖 إنشاء تطبيق البوت...")
        updater = Updater("7766964799:AAHex-hGfjPX6g_R2aZ7-UPrgnFxQKAjSa0", use_context=True)
        dispatcher = updater.dispatcher
        
        # إضافة معالج التسجيل
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler('start', start)],
            states={
                GET_FULL_NAME: [MessageHandler(Filters.text & ~Filters.command, get_full_name)],
                GET_PHONE: [MessageHandler(Filters.text & ~Filters.command, get_phone)],
                CHOOSE_ROLE: [CallbackQueryHandler(choose_role)]
            },
            fallbacks=[CommandHandler('cancel', cancel)]
        )
        
        dispatcher.add_handler(conv_handler)
        
        # إضافة المعالجات الأخرى
        dispatcher.add_handler(CommandHandler("wallet", wallet_handler))
        dispatcher.add_handler(CommandHandler("help", help_handler))
        dispatcher.add_handler(CallbackQueryHandler(button_click_handler))
        
        # تعيين قائمة الأوامر
        print("📋 تعيين قائمة الأوامر...")
        updater.bot.set_my_commands(QUICK_COMMANDS)
        
        # بدء البوت
        print("🚀 بدء البوت...")
        updater.start_polling()
        
        # انتظار الإيقاف
        print("✅ البوت يعمل الآن! اضغط Ctrl+C لإيقافه")
        updater.idle()
        
    except Exception as e:
        logger.error(f"خطأ في تشغيل البوت: {e}")
        print(f"❌ فشل في تشغيل البوت: {e}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n🛑 تم إيقاف البوت بواسطة المستخدم")
    except Exception as e:
        print(f"\n💥 خطأ غير متوقع: {e}")
        logger.error(f"خطأ غير متوقع: {e}")