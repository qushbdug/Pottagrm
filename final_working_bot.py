#!/usr/bin/env python3
"""
البوت النهائي العامل
Final Working Bot
"""

import logging
import sys
import os

# إضافة المجلد الحالي إلى Python path لحل مشكلة imghdr
sys.path.insert(0, os.getcwd())

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
        from telegram.ext import Updater, CommandHandler, CallbackQueryHandler
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        
        print("✅ تم استيراد المكتبة")
        
        # إنشاء البوت
        token = "7766964799:AAHex-hGfjPX6g_R2aZ7-UPrgnFxQKAjSa0"
        updater = Updater(token)
        
        print("✅ تم إنشاء البوت")
        
        # الحصول على dispatcher
        dispatcher = updater.dispatcher
        
        # إضافة معالج البداية مع أزرار
        def start_command(update, context):
            keyboard = [
                [InlineKeyboardButton("💳 محفظتي", callback_data="wallet")],
                [InlineKeyboardButton("🛒 شراء كروت", callback_data="buy_cards")],
                [InlineKeyboardButton("💸 تحويل رصيد", callback_data="transfer")],
                [InlineKeyboardButton("📊 تقاريري", callback_data="reports")],
                [InlineKeyboardButton("❓ المساعدة", callback_data="help")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            welcome_text = """
🔥 **مرحباً بك في بوت كروت الإنترنت اليمني!** 🔥

🚀 **الميزات المتاحة:**
• 💳 محفظة إلكترونية
• 🛒 شراء كروت الشبكة
• 💸 تحويل رصيد
• 📊 تقارير مفصلة
• ⭐ نظام تقييمات

🎯 **اختر من القائمة أدناه:**
"""
            update.message.reply_text(welcome_text, parse_mode='Markdown', reply_markup=reply_markup)
        
        # إضافة معالج النقر على الأزرار
        def button_callback(update, context):
            query = update.callback_query
            query.answer()
            
            if query.data == "wallet":
                wallet_text = """
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
                    [InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="main_menu")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                query.edit_message_text(wallet_text, parse_mode='Markdown', reply_markup=reply_markup)
                
            elif query.data == "buy_cards":
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
                    [InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="main_menu")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                query.edit_message_text(cards_text, parse_mode='Markdown', reply_markup=reply_markup)
                
            elif query.data == "transfer":
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
                query.edit_message_text(transfer_text, parse_mode='Markdown', reply_markup=reply_markup)
                
            elif query.data == "reports":
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
                query.edit_message_text(reports_text, parse_mode='Markdown', reply_markup=reply_markup)
                
            elif query.data == "help":
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
                query.edit_message_text(help_text, parse_mode='Markdown', reply_markup=reply_markup)
                
            elif query.data == "main_menu":
                # العودة للقائمة الرئيسية
                start_command(update, context)
                
            else:
                query.edit_message_text("❌ زر غير معروف")
        
        dispatcher.add_handler(CommandHandler("start", start_command))
        dispatcher.add_handler(CallbackQueryHandler(button_callback))
        
        print("✅ تم إضافة المعالجات")
        print("🚀 البوت يعمل الآن...")
        print("📱 يمكنك الآن إرسال /start للبوت!")
        print("🔘 البوت يستجيب للنقر على الأزرار!")
        
        # تشغيل البوت
        updater.start_polling()
        updater.idle()
        
    except Exception as e:
        print(f"❌ خطأ: {e}")
        logger.error(f"خطأ: {e}")

if __name__ == "__main__":
    print("🎯 بدء التشغيل...")
    main()