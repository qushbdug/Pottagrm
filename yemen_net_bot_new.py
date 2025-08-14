#!/usr/bin/env python3
"""
Pottagrm Enhanced Bot - Main Entry Point
Yemen Net Card Sales Bot with Enhanced Features
Version: 2.1.0

Author: AI Assistant
License: MIT
"""

import logging
import asyncio
import sys
import os
from datetime import datetime

# Add bot_modules to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'bot_modules'))

# Import Telegram bot components
from telegram import Update, MenuButtonCommands, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ConversationHandler, PicklePersistence, filters
)

# Import our modular components
try:
    from config import *
    from database import init_db
    from utils import *
    from handlers import COMMAND_HANDLERS, CONVERSATION_STATES, handle_text_message, show_main_menu
    from admin_functions import ADMIN_CALLBACKS, activate_single_supplier
except ImportError as e:
    print(f"Error importing modules: {e}")
    print("Make sure all module files are in the bot_modules directory")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Main callback handler
async def button_click_handler(update: Update, context):
    """Enhanced callback query handler with better error handling"""
    try:
        query = update.callback_query
        await query.answer()
        
        callback_data = query.data
        user = get_user(query.from_user.id)
        
        if not user:
            await query.edit_message_text(f"{EMOJIS['error']} يرجى التسجيل أولاً /start")
            return
        
        update_user_activity(user['id'])
        
        # Route to appropriate handlers
        
        # Main menu
        if callback_data == 'main_menu':
            return await show_main_menu(update, context, user['role'])
        
        # Enhanced wallet
        elif callback_data == 'enhanced_wallet':
            from handlers import enhanced_wallet_handler
            return await enhanced_wallet_handler(update, context)
        
        # Admin panel routing
        elif callback_data == 'admin_panel':
            if user['role'] in ['admin', 'super_admin']:
                from admin_functions import admin_panel_handler
                return await admin_panel_handler(update, context)
            else:
                await query.edit_message_text(f"{EMOJIS['error']} ليس لديك صلاحية للوصول لهذه اللوحة.")
                return
        
        # Super admin functions
        elif callback_data in ADMIN_CALLBACKS:
            if user['role'] == 'super_admin':
                return await ADMIN_CALLBACKS[callback_data](update, context)
            else:
                await query.edit_message_text(f"{EMOJIS['error']} ليس لديك صلاحية لهذه العملية.")
                return
        
        # Supplier activation (specific handling)
        elif callback_data.startswith('activate_supplier_'):
            if user['role'] == 'super_admin':
                supplier_id = callback_data.split('_')[2]
                return await activate_single_supplier(update, context, supplier_id)
            else:
                await query.edit_message_text(f"{EMOJIS['error']} ليس لديك صلاحية لهذه العملية.")
                return
        
        # Role selection during registration
        elif callback_data.startswith('role_'):
            from handlers import choose_role
            return await choose_role(update, context)
        
        # Core features
        elif callback_data == 'buy_cards':
            await buy_cards_handler(update, context)
        elif callback_data == 'transfer_to_friend':
            await transfer_handler(update, context)
        
        # Personal features
        elif callback_data == 'personal_reports':
            await personal_reports_handler(update, context)
        elif callback_data == 'my_ratings':
            await my_ratings_handler(update, context)
        elif callback_data == 'my_notifications':
            await my_notifications_handler(update, context)
        elif callback_data == 'promotions':
            await promotions_handler(update, context)
        elif callback_data == 'account_settings':
            await account_settings_handler(update, context)
        
        # Refresh balance
        elif callback_data == 'refresh_balance':
            new_balance = recalc_and_set_user_balance(user['id'])
            await query.edit_message_text(
                f"🔄 **تم تحديث الرصيد**\n\n💰 رصيدك الحالي: **{new_balance:.2f}** ريال",
                parse_mode='Markdown'
            )
        
        # Help
        elif callback_data == 'help':
            await help_handler(update, context)
        
        # Default fallback for unrecognized callbacks
        else:
            logger.warning(f"Unhandled callback: {callback_data}")
            await query.edit_message_text(
                f"{EMOJIS['warning']} هذه الميزة قيد التطوير.\n\n"
                f"سيتم إضافتها في التحديث القادم إن شاء الله.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(f'{EMOJIS["home"]} القائمة الرئيسية', callback_data='main_menu')]
                ])
            )
    
    except Exception as e:
        logger.error(f"Error in button click handler: {e}")
        try:
            if update.callback_query:
                await update.callback_query.edit_message_text(
                    f"{EMOJIS['error']} حدث خطأ. يرجى المحاولة مرة أخرى.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton(f'{EMOJIS["home"]} القائمة الرئيسية', callback_data='main_menu')]
                    ])
                )
        except:
            pass

# Placeholder handlers for features being implemented
async def personal_reports_handler(update: Update, context):
    """Show personal reports"""
    try:
        query = update.callback_query
        user = get_user(query.from_user.id)
        
        # Get user statistics
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT COUNT(*) as total_purchases, SUM(amount) as total_spent
            FROM transactions 
            WHERE from_user = ? AND type = 'purchase'
        ''', (user['id'],))
        
        stats = cursor.fetchone()
        total_purchases = stats['total_purchases'] or 0
        total_spent = stats['total_spent'] or 0.0
        
        conn.close()
        
        report_text = f"""
📊 **تقاريري الشخصية** 📊

👤 **{user['full_name']}**

📈 **إحصائيات الشراء:**
🛒 إجمالي المشتريات: **{total_purchases}**
💰 إجمالي المبلغ المصروف: **{total_spent:.2f}** ريال
📅 عضو منذ: {user['created_at'][:10]}
⚡ آخر نشاط: {user['last_activity'][:10]}

🎯 **معدلات الاستخدام:**
📊 متوسط الشراء الشهري: قيد الحساب
🔥 الشبكة المفضلة: قيد التحليل
⭐ تقييمي: {calculate_user_rating(user['id'])['average_rating']}/5

📈 **المزيد من التقارير المفصلة قريباً...**
"""
        
        keyboard = [
            [InlineKeyboardButton(f'📊 تحليل مفصل', callback_data='detailed_analysis')],
            [InlineKeyboardButton(f'{EMOJIS["home"]} القائمة الرئيسية', callback_data='main_menu')]
        ]
        
        await query.edit_message_text(report_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in personal reports handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في عرض التقارير.")

async def my_ratings_handler(update: Update, context):
    """Show user ratings"""
    try:
        query = update.callback_query
        user = get_user(query.from_user.id)
        
        rating_summary = calculate_user_rating(user['id'])
        
        rating_text = f"""
⭐ **تقييماتي ومراجعاتي** ⭐

👤 **{user['full_name']}**

📊 **ملخص التقييمات:**
⭐ متوسط التقييم: **{rating_summary['average_rating']}/5**
🔢 إجمالي التقييمات: **{rating_summary['total_ratings']}**

📈 **توزيع النجوم:**
⭐⭐⭐⭐⭐ {rating_summary['rating_distribution'].get(5, 0)} تقييم
⭐⭐⭐⭐ {rating_summary['rating_distribution'].get(4, 0)} تقييم  
⭐⭐⭐ {rating_summary['rating_distribution'].get(3, 0)} تقييم
⭐⭐ {rating_summary['rating_distribution'].get(2, 0)} تقييم
⭐ {rating_summary['rating_distribution'].get(1, 0)} تقييم

🎯 **نصائح لتحسين تقييمك:**
• كن مهذباً في التعامل
• أكمل المعاملات بسرعة
• قدم خدمة عملاء ممتازة
"""
        
        keyboard = [
            [InlineKeyboardButton(f'📝 تقييماتي المرسلة', callback_data='my_sent_ratings')],
            [InlineKeyboardButton(f'📨 تقييماتي المستلمة', callback_data='my_received_ratings')],
            [InlineKeyboardButton(f'{EMOJIS["home"]} القائمة الرئيسية', callback_data='main_menu')]
        ]
        
        await query.edit_message_text(rating_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in my ratings handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في عرض التقييمات.")

async def my_notifications_handler(update: Update, context):
    """Show user notifications"""
    try:
        query = update.callback_query
        user = get_user(query.from_user.id)
        
        # Get recent notifications
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM smart_notifications 
            WHERE user_id = ? 
            ORDER BY created_at DESC 
            LIMIT 10
        ''', (user['id'],))
        
        notifications = cursor.fetchall()
        
        cursor.execute('''
            SELECT COUNT(*) as unread_count 
            FROM smart_notifications 
            WHERE user_id = ? AND is_read = 0
        ''', (user['id'],))
        
        unread_count = cursor.fetchone()['unread_count']
        conn.close()
        
        notif_text = f"""
🔔 **إشعاراتي وتنبيهاتي** 🔔

👤 **{user['full_name']}**
📬 الإشعارات غير المقروءة: **{unread_count}**

📋 **آخر الإشعارات:**
"""
        
        if notifications:
            for notif in notifications[:5]:
                status = "🔴" if not notif['is_read'] else "✅"
                priority = "🔥" if notif['priority'] == 'high' else "📢"
                notif_text += f"\n{status} {priority} {notif['title'][:25]}..."
        else:
            notif_text += "\nلا توجد إشعارات بعد"
        
        keyboard = [
            [InlineKeyboardButton(f'✅ قراءة الكل', callback_data='mark_all_read'),
             InlineKeyboardButton(f'⚙️ إعدادات الإشعارات', callback_data='notification_settings')],
            [InlineKeyboardButton(f'{EMOJIS["home"]} القائمة الرئيسية', callback_data='main_menu')]
        ]
        
        await query.edit_message_text(notif_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in my notifications handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في عرض الإشعارات.")

async def promotions_handler(update: Update, context):
    """Show available promotions"""
    try:
        query = update.callback_query
        user = get_user(query.from_user.id)
        
        # Get active promotions
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM promotions 
            WHERE is_active = 1 
            AND start_date <= ? 
            AND end_date >= ?
            AND (target_user_role IS NULL OR target_user_role = ?)
            ORDER BY created_at DESC 
            LIMIT 5
        ''', (datetime.now(), datetime.now(), user['role']))
        
        promotions = cursor.fetchall()
        conn.close()
        
        promo_text = f"""
🎁 **العروض والخصومات** 🎁

👤 **{user['full_name']}**

🔥 **العروض المتاحة حالياً:**
"""
        
        if promotions:
            for promo in promotions:
                discount_text = f"{promo['discount_percentage']}%" if promo['discount_percentage'] > 0 else f"{promo['discount_amount']} ريال"
                promo_text += f"""
💫 **{promo['title']}**
📝 {promo['description'][:50]}...
💰 خصم: {discount_text}
📅 ينتهي: {promo['end_date'][:10]}
---
"""
        else:
            promo_text += "\nلا توجد عروض متاحة حالياً"
        
        keyboard = [
            [InlineKeyboardButton(f'🎯 تفاصيل العروض', callback_data='promotion_details')],
            [InlineKeyboardButton(f'📜 استخدام كود خصم', callback_data='use_promo_code')],
            [InlineKeyboardButton(f'{EMOJIS["home"]} القائمة الرئيسية', callback_data='main_menu')]
        ]
        
        await query.edit_message_text(promo_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in promotions handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في عرض العروض.")

async def account_settings_handler(update: Update, context):
    """Show account settings"""
    try:
        query = update.callback_query
        user = get_user(query.from_user.id)
        
        permissions = get_user_permissions(user['id'])
        
        settings_text = f"""
⚙️ **إعدادات الحساب** ⚙️

👤 **معلومات الحساب:**
📛 الاسم: **{user['full_name']}**
📞 الهاتف: **{user['phone']}**
🏷️ النوع: **{USER_ROLES.get(user['role'], user['role'])}**
💳 رقم المحفظة: **{user['wallet_number']}**
📅 تاريخ التسجيل: {user['created_at'][:10]}
⚡ الحالة: {"مفعل" if user['is_active'] else "غير مفعل"}

🔐 **الصلاحيات:**
"""
        
        if permissions:
            for perm in permissions:
                settings_text += f"✅ {PERMISSIONS.get(perm, perm)}\n"
        else:
            settings_text += "📋 الصلاحيات الأساسية فقط"
        
        keyboard = [
            [InlineKeyboardButton(f'🔔 إعدادات الإشعارات', callback_data='notification_preferences'),
             InlineKeyboardButton(f'🔒 الأمان والخصوصية', callback_data='privacy_settings')],
            [InlineKeyboardButton(f'📱 تغيير رقم الهاتف', callback_data='change_phone'),
             InlineKeyboardButton(f'🎫 دعوة صديق', callback_data='invite_friend')],
            [InlineKeyboardButton(f'{EMOJIS["home"]} القائمة الرئيسية', callback_data='main_menu')]
        ]
        
        await query.edit_message_text(settings_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in account settings handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في عرض الإعدادات.")

async def buy_cards_handler(update: Update, context):
    """Handle buy cards request"""
    try:
        query = update.callback_query
        user = get_user(query.from_user.id)
        
        buy_text = f"""
🛒 **شراء كروت الإنترنت** 🛒

👤 **{user['full_name']}**
💰 رصيدك: **{user['balance']:.2f}** ريال

📶 **الشبكات المتاحة:**

هذه الميزة قيد التطوير حالياً وسيتم إضافة:
• عرض الشبكات المتاحة
• اختيار فئات الكروت
• معاينة الأسعار
• تأكيد الشراء

⚠️ سيتم إضافة هذه الميزة في التحديث القادم.
"""
        
        keyboard = [
            [InlineKeyboardButton(f'📊 عرض الشبكات', callback_data='view_networks')],
            [InlineKeyboardButton(f'💰 شحن الرصيد', callback_data='recharge_balance')],
            [InlineKeyboardButton(f'{EMOJIS["home"]} القائمة الرئيسية', callback_data='main_menu')]
        ]
        
        await query.edit_message_text(buy_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in buy cards handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في عرض صفحة الشراء.")

async def transfer_handler(update: Update, context):
    """Handle transfer request"""
    try:
        query = update.callback_query
        user = get_user(query.from_user.id)
        
        transfer_text = f"""
💸 **تحويل رصيد لصديق** 💸

👤 **{user['full_name']}**
💰 رصيدك: **{user['balance']:.2f}** ريال

📋 **تعليمات التحويل:**
1️⃣ أدخل رقم محفظة المستلم (9 أرقام)
2️⃣ أدخل المبلغ المراد تحويله
3️⃣ تأكيد العملية

⚠️ هذه الميزة قيد التطوير وسيتم إضافتها قريباً.
"""
        
        keyboard = [
            [InlineKeyboardButton(f'🔍 البحث عن مستخدم', callback_data='search_user')],
            [InlineKeyboardButton(f'📋 آخر التحويلات', callback_data='transfer_history')],
            [InlineKeyboardButton(f'{EMOJIS["home"]} القائمة الرئيسية', callback_data='main_menu')]
        ]
        
        await query.edit_message_text(transfer_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in transfer handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في عرض صفحة التحويل.")

async def help_handler(update: Update, context):
    """Show help information"""
    try:
        query = update.callback_query if update.callback_query else None
        
        help_text = f"""
❓ **المساعدة والدعم** ❓

🤖 **بوت كروت الإنترنت اليمني المطور**
📱 النسخة: 2.1.0 Enhanced

🔥 **الميزات الجديدة:**
• 💳 محفظة إلكترونية متطورة
• 📊 تقارير شخصية تفصيلية  
• ⭐ نظام تقييمات ومراجعات
• 🔔 إشعارات ذكية مخصصة
• 🎁 نظام عروض وخصومات
• 🔒 أمان محسّن ومشفر

📋 **الأوامر الأساسية:**
/start - البداية والقائمة الرئيسية
/wallet - المحفظة المطورة
/menu - القائمة السريعة
/admin - لوحة الإدارة (للمشرفين)
/cancel - إلغاء العملية الحالية

📞 **للدعم الفني:**
تواصل مع الإدارة عبر البوت

🔄 **آخر تحديث:** {datetime.now().strftime('%Y-%m-%d')}
"""
        
        keyboard = [
            [InlineKeyboardButton(f'📖 دليل الاستخدام', callback_data='user_guide'),
             InlineKeyboardButton(f'🛠️ الإبلاغ عن مشكلة', callback_data='report_issue')],
            [InlineKeyboardButton(f'{EMOJIS["home"]} القائمة الرئيسية', callback_data='main_menu')]
        ]
        
        if query:
            await query.edit_message_text(help_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        else:
            await update.message.reply_text(help_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
            
    except Exception as e:
        logger.error(f"Error in help handler: {e}")
        error_text = f"{EMOJIS['error']} حدث خطأ في عرض المساعدة."
        if update.callback_query:
            await update.callback_query.edit_message_text(error_text)
        else:
            await update.message.reply_text(error_text)

def main():
    """Main function to start the bot"""
    try:
        # Initialize database
        logger.info("Initializing database...")
        init_db()
        
        # Create persistence
        persistence = PicklePersistence(filepath='yemen_net_bot_data')
        application = Application.builder().token(BOT_TOKEN).persistence(persistence).build()
        
        # Set bot commands (will be done after startup)
        async def post_init(application):
            try:
                logger.info("Setting bot commands...")
                await application.bot.set_my_commands(QUICK_COMMANDS)
                await application.bot.set_chat_menu_button(menu_button=MenuButtonCommands())
                logger.info("Bot commands set successfully")
            except Exception as e:
                logger.warning(f'Failed setting commands/menu: {e}')
        
        application.post_init = post_init
        
        # Create conversation handler with proper fallbacks
        conv_handler = ConversationHandler(
            entry_points=[
                CommandHandler('start', COMMAND_HANDLERS['start']),
                CommandHandler('menu', lambda u, c: show_main_menu(u, c, get_user(u.effective_user.id)['role'] if get_user(u.effective_user.id) else 'customer')),
                CommandHandler('wallet', COMMAND_HANDLERS['wallet']),
                CommandHandler('admin', COMMAND_HANDLERS['admin']),
            ],
            states=CONVERSATION_STATES,
            fallbacks=[
                CommandHandler('cancel', COMMAND_HANDLERS['cancel']),
                CallbackQueryHandler(lambda u, c: show_main_menu(u, c, get_user(u.effective_user.id)['role'] if get_user(u.effective_user.id) else 'customer'), pattern='^main_menu$'),
                MessageHandler(filters.TEXT & filters.Regex(r'^/cancel$'), COMMAND_HANDLERS['cancel']),
            ],
            name='yemen_net_conversation',
            persistent=True,
            allow_reentry=True,
            per_message=False,
        )
        
        # Error handler
        async def error_handler(update: object, context):
            """Log errors and handle them gracefully"""
            logger.error("Exception while handling an update:", exc_info=context.error)
            
            # Try to send error message to user
            try:
                if isinstance(update, Update) and update.effective_chat:
                    await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text=f"{EMOJIS['error']} حدث خطأ غير متوقع. يرجى المحاولة مرة أخرى."
                    )
            except Exception:
                pass
        
        # Add handlers
        application.add_handler(conv_handler)
        application.add_handler(CallbackQueryHandler(button_click_handler))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))
        application.add_error_handler(error_handler)
        
        # Add individual command handlers for direct access
        for command, handler in COMMAND_HANDLERS.items():
            if command not in ['start']:  # start is already in conversation handler
                application.add_handler(CommandHandler(command, handler))
        
        # Start the bot
        logger.info(f'{EMOJIS["fire"]} Starting Pottagrm Enhanced Bot v2.1.0...')
        application.run_polling(allowed_updates=Update.ALL_TYPES)
        
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        raise

if __name__ == '__main__':
    main()