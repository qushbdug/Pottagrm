#!/usr/bin/env python3
"""
بوت كروت الإنترنت اليمني - النسخة العاملة
Yemen Net Card Bot - Working Version
"""

import logging
import asyncio
import sys
import os
from datetime import datetime

# استيراد مكونات البوت
from telegram import Update, BotCommand, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    filters, ContextTypes
)

# إعداد التسجيل
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)

# تعريف الأوامر السريعة
QUICK_COMMANDS = [
    BotCommand('start', '🏠 البداية - القائمة الرئيسية'),
    BotCommand('wallet', '💳 محفظتي'),
    BotCommand('help', '❓ المساعدة'),
    BotCommand('menu', '📋 القائمة الرئيسية'),
]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج أمر البداية"""
    try:
        user = update.effective_user
        
        # إنشاء القائمة الرئيسية
        keyboard = [
            [InlineKeyboardButton("💳 محفظتي", callback_data="wallet")],
            [InlineKeyboardButton("🛒 شراء كروت", callback_data="buy_cards")],
            [InlineKeyboardButton("💸 تحويل رصيد", callback_data="transfer")],
            [InlineKeyboardButton("📊 تقاريري", callback_data="reports")],
            [InlineKeyboardButton("❓ المساعدة", callback_data="help")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
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

🎯 **اختر من القائمة أدناه:**
"""
        
        await update.message.reply_text(welcome_text, parse_mode='Markdown', reply_markup=reply_markup)
        
    except Exception as e:
        logger.error(f"خطأ في معالج البداية: {e}")
        await update.message.reply_text("❌ حدث خطأ. يرجى المحاولة مرة أخرى.")

async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج أمر القائمة"""
    try:
        user = update.effective_user
        
        # إنشاء القائمة الرئيسية
        keyboard = [
            [InlineKeyboardButton("💳 محفظتي", callback_data="wallet")],
            [InlineKeyboardButton("🛒 شراء كروت", callback_data="buy_cards")],
            [InlineKeyboardButton("💸 تحويل رصيد", callback_data="transfer")],
            [InlineKeyboardButton("📊 تقاريري", callback_data="reports")],
            [InlineKeyboardButton("❓ المساعدة", callback_data="help")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        menu_text = f"""
📋 **القائمة الرئيسية** 📋

👤 **مرحباً:** {user.first_name}

🎯 **اختر الخدمة المطلوبة:**
"""
        
        await update.message.reply_text(menu_text, parse_mode='Markdown', reply_markup=reply_markup)
        
    except Exception as e:
        logger.error(f"خطأ في معالج القائمة: {e}")
        await update.message.reply_text("❌ حدث خطأ في عرض القائمة.")

async def wallet_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        
        # إضافة أزرار للمحفظة
        keyboard = [
            [InlineKeyboardButton("💸 تحويل رصيد", callback_data="transfer")],
            [InlineKeyboardButton("🛒 شراء كروت", callback_data="buy_cards")],
            [InlineKeyboardButton("📊 تقارير مفصلة", callback_data="reports")],
            [InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(wallet_text, parse_mode='Markdown', reply_markup=reply_markup)
        
    except Exception as e:
        logger.error(f"خطأ في معالج المحفظة: {e}")
        await update.message.reply_text("❌ حدث خطأ في عرض المحفظة.")

async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج أمر المساعدة"""
    help_text = """
❓ **مركز المساعدة** ❓

🚀 **الأوامر المتاحة:**
• /start - بدء البوت
• /menu - القائمة الرئيسية
• /wallet - عرض المحفظة
• /help - هذه الرسالة

💡 **نصائح للاستخدام:**
• استخدم الأزرار للتنقل بين الخدمات
• تأكد من إدخال بيانات صحيحة
• تواصل مع الدعم الفني عند الحاجة

📞 **الدعم الفني:**
• البريد الإلكتروني: support@yemen-net.com
• الهاتف: +967-XXX-XXX-XXX

🔧 **الميزات:**
• 💳 محفظة إلكترونية متقدمة
• 🛒 شراء كروت الإنترنت
• 💸 تحويل رصيد للمستخدمين
• 📊 تقارير مفصلة
• ⭐ نظام تقييمات
"""
    
    # إضافة أزرار للمساعدة
    keyboard = [
        [InlineKeyboardButton("💳 محفظتي", callback_data="wallet")],
        [InlineKeyboardButton("🛒 شراء كروت", callback_data="buy_cards")],
        [InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(help_text, parse_mode='Markdown', reply_markup=reply_markup)

async def button_click_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج النقر على الأزرار"""
    try:
        query = update.callback_query
        await query.answer()
        
        if query.data == "wallet":
            await show_wallet_menu(query)
        elif query.data == "buy_cards":
            await show_buy_cards_menu(query)
        elif query.data == "transfer":
            await show_transfer_menu(query)
        elif query.data == "reports":
            await show_reports_menu(query)
        elif query.data == "help":
            await show_help_menu(query)
        elif query.data == "main_menu":
            await show_main_menu(query)
        else:
            await query.edit_message_text("❌ زر غير معروف")
            
    except Exception as e:
        logger.error(f"خطأ في معالج النقر: {e}")
        await update.callback_query.answer("❌ حدث خطأ")

async def show_wallet_menu(query):
    """عرض قائمة المحفظة"""
    wallet_text = f"""
💳 **محفظتك الإلكترونية** 💳

💰 **الرصيد الحالي:** 1000 ريال

📊 **آخر المعاملات:**
➕ إيداع: 500 ريال (2025-08-26)
➖ شراء كرت: 200 ريال (2025-08-25)
➖ تحويل: 100 ريال (2025-08-24)

🔧 **الميزات المتاحة:**
• 💸 تحويل رصيد
• 🛒 شراء كروت
• 📊 تقارير مفصلة
"""
    
    keyboard = [
        [InlineKeyboardButton("💸 تحويل رصيد", callback_data="transfer")],
        [InlineKeyboardButton("🛒 شراء كروت", callback_data="buy_cards")],
        [InlineKeyboardButton("📊 تقارير مفصلة", callback_data="reports")],
        [InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(wallet_text, parse_mode='Markdown', reply_markup=reply_markup)

async def show_buy_cards_menu(query):
    """عرض قائمة شراء الكروت"""
    cards_text = """
🛒 **شراء كروت الإنترنت** 🛒

📶 **الشبكات المتاحة:**
• 🌐 يمن نت
• 📡 تليمن
• 📶 سابافون
• 🌍 يمن موبايل

💳 **أنواع الكروت:**
• 🎫 كرت يومي
• 🎫 كرت أسبوعي
• 🎫 كرت شهري
• 🎫 كرت سنوي

💰 **الأسعار تبدأ من:** 50 ريال
"""
    
    keyboard = [
        [InlineKeyboardButton("🌐 يمن نت", callback_data="network_yemen_net")],
        [InlineKeyboardButton("📡 تليمن", callback_data="network_telemen")],
        [InlineKeyboardButton("📶 سابافون", callback_data="network_sabafon")],
        [InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(cards_text, parse_mode='Markdown', reply_markup=reply_markup)

async def show_transfer_menu(query):
    """عرض قائمة التحويل"""
    transfer_text = """
💸 **تحويل رصيد** 💸

📱 **لتحويل رصيد:**
• أدخل معرف المستخدم
• أدخل المبلغ المطلوب
• تأكد من البيانات
• اضغط تأكيد

⚠️ **ملاحظات مهمة:**
• الحد الأدنى: 10 ريال
• الحد الأقصى: 1000 ريال
• رسوم التحويل: مجانية
"""
    
    keyboard = [
        [InlineKeyboardButton("📱 إدخال معرف المستخدم", callback_data="enter_user_id")],
        [InlineKeyboardButton("💰 إدخال المبلغ", callback_data="enter_amount")],
        [InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(transfer_text, parse_mode='Markdown', reply_markup=reply_markup)

async def show_reports_menu(query):
    """عرض قائمة التقارير"""
    reports_text = """
📊 **تقاريري الشخصية** 📊

📈 **إحصائيات عامة:**
• إجمالي المشتريات: 15 كرت
• إجمالي الإنفاق: 750 ريال
• عدد التحويلات: 8
• التقييم: ⭐⭐⭐⭐⭐

📅 **آخر 7 أيام:**
• المشتريات: 3 كروت
• الإنفاق: 150 ريال
• التحويلات: 2
"""
    
    keyboard = [
        [InlineKeyboardButton("📈 تقرير مفصل", callback_data="detailed_report")],
        [InlineKeyboardButton("📅 تقرير شهري", callback_data="monthly_report")],
        [InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(reports_text, parse_mode='Markdown', reply_markup=reply_markup)

async def show_help_menu(query):
    """عرض قائمة المساعدة"""
    help_text = """
❓ **مركز المساعدة** ❓

🚀 **كيفية الاستخدام:**
• استخدم الأزرار للتنقل
• اتبع التعليمات بدقة
• تأكد من صحة البيانات

💡 **نصائح مهمة:**
• احتفظ برقم معرفك
• تأكد من رصيد المحفظة
• تحقق من صحة البيانات

📞 **الدعم الفني:**
• البريد: support@yemen-net.com
• الهاتف: +967-XXX-XXX-XXX
"""
    
    keyboard = [
        [InlineKeyboardButton("💳 محفظتي", callback_data="wallet")],
        [InlineKeyboardButton("🛒 شراء كروت", callback_data="buy_cards")],
        [InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(help_text, parse_mode='Markdown', reply_markup=reply_markup)

async def show_main_menu(query):
    """عرض القائمة الرئيسية"""
    menu_text = f"""
🏠 **القائمة الرئيسية** 🏠

🎯 **اختر الخدمة المطلوبة:**
"""
    
    keyboard = [
        [InlineKeyboardButton("💳 محفظتي", callback_data="wallet")],
        [InlineKeyboardButton("🛒 شراء كروت", callback_data="buy_cards")],
        [InlineKeyboardButton("💸 تحويل رصيد", callback_data="transfer")],
        [InlineKeyboardButton("📊 تقاريري", callback_data="reports")],
        [InlineKeyboardButton("❓ المساعدة", callback_data="help")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(menu_text, parse_mode='Markdown', reply_markup=reply_markup)

async def main():
    """الدالة الرئيسية للبوت"""
    try:
        # إنشاء تطبيق البوت
        print("🤖 إنشاء تطبيق البوت...")
        application = Application.builder().token("7766964799:AAHex-hGfjPX6g_R2aZ7-UPrgnFxQKAjSa0").build()
        
        # إضافة المعالجات
        print("📝 إضافة معالجات الأوامر...")
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("menu", menu_handler))
        application.add_handler(CommandHandler("wallet", wallet_handler))
        application.add_handler(CommandHandler("help", help_handler))
        
        # إضافة معالج النقر على الأزرار
        print("🔘 إضافة معالج النقر على الأزرار...")
        application.add_handler(CallbackQueryHandler(button_click_handler))
        
        # تعيين قائمة الأوامر
        print("📋 تعيين قائمة الأوامر...")
        await application.bot.set_my_commands(QUICK_COMMANDS)
        
        # بدء البوت
        print("🚀 بدء البوت...")
        print("✅ البوت يعمل الآن! اضغط Ctrl+C لإيقافه")
        await application.run_polling(allowed_updates=Update.ALL_TYPES)
        
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