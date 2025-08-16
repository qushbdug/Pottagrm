#!/usr/bin/env python3
"""
Yemen Net Bot - Simple Version
بوت شبكات اليمن - النسخة المبسطة

A simple Telegram bot for network card sales in Yemen
بوت تيليجرام بسيط لبيع كروت الشبكات في اليمن

Author: Professional Development Team
المؤلف: فريق التطوير المحترف
Version: 1.0.0
License: MIT
"""

import logging
import os
import sqlite3
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Updater, CommandHandler, CallbackQueryHandler, MessageHandler,
    Filters, CallbackContext, ConversationHandler
)
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Bot token
BOT_TOKEN = os.getenv('BOT_TOKEN', '7766964799:AAHex-hGfjPX6g_R2aZ7-UPrgnFxQKAjSa0')

# Database path
DB_PATH = 'yemen_net.db'

# Conversation states
GET_FULL_NAME, GET_PHONE, CHOOSE_ROLE = range(3)

# Emojis
EMOJIS = {
    'success': '✅', 'error': '❌', 'warning': '⚠️', 'info': 'ℹ️',
    'loading': '⏳', 'money': '💰', 'card': '🎫', 'network': '📶',
    'user': '👤', 'admin': '👑', 'stats': '📊', 'home': '🏠',
    'back': '↩️', 'cancel': '❌', 'confirm': '✅', 'search': '🔍',
    'settings': '⚙️', 'wallet': '💳', 'transfer': '💸', 'purchase': '🛒',
    'phone': '📱', 'star': '⭐', 'fire': '🔥', 'new': '🆕'
}

# User roles
USER_ROLES = {
    'customer': 'عميل',
    'agent': 'وكيل',
    'supplier': 'مزود'
}


def init_database():
    """Initialize database with required tables."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Create users table if it doesn't exist
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE NOT NULL,
                full_name TEXT NOT NULL,
                phone TEXT UNIQUE NOT NULL,
                role TEXT NOT NULL DEFAULT 'customer',
                balance REAL DEFAULT 0.0,
                wallet_number TEXT UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create transactions table if it doesn't exist
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                transaction_type TEXT NOT NULL,
                amount REAL NOT NULL,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("Database initialized successfully")
        
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise


def get_user(telegram_id):
    """Get user from database."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE telegram_id = ?', (telegram_id,))
        user = cursor.fetchone()
        conn.close()
        return user
    except Exception as e:
        logger.error(f"Failed to get user: {e}")
        return None


def create_user(telegram_id, full_name, phone, role):
    """Create new user in database."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Generate wallet number
        wallet_number = f"YE{telegram_id:08d}"
        
        cursor.execute('''
            INSERT INTO users (telegram_id, full_name, phone, role, wallet_number)
            VALUES (?, ?, ?, ?, ?)
        ''', (telegram_id, full_name, phone, role, wallet_number))
        
        user_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        logger.info(f"User {user_id} created successfully")
        return user_id
        
    except Exception as e:
        logger.error(f"Failed to create user: {e}")
        return None


def update_user_activity(telegram_id):
    """Update user's last activity."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE users SET last_activity = CURRENT_TIMESTAMP
            WHERE telegram_id = ?
        ''', (telegram_id,))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Failed to update user activity: {e}")
        return False


def start_command(update: Update, context: CallbackContext):
    """Handle /start command."""
    user = update.effective_user
    existing_user = get_user(user.id)
    
    if existing_user:
        # User already exists
        show_main_menu(update, context, existing_user)
    else:
        # Start registration
        start_registration(update, context)
        return GET_FULL_NAME


def start_registration(update: Update, context: CallbackContext):
    """Start user registration process."""
    message = (
        f"{EMOJIS['new']} **مرحباً بك في بوت شبكات اليمن!**\n\n"
        "أهلاً وسهلاً بك في البوت الأفضل لبيع كروت الشبكات.\n"
        "لنبدأ بالتسجيل:\n\n"
        "**الخطوة الأولى:** أرسل اسمك الكامل"
    )
    
    update.message.reply_text(message, parse_mode='Markdown')


def get_full_name(update: Update, context: CallbackContext):
    """Handle full name input."""
    full_name = update.message.text.strip()
    
    if len(full_name) < 3:
        update.message.reply_text(
            f"{EMOJIS['error']} الاسم يجب أن يكون 3 أحرف على الأقل. حاول مرة أخرى."
        )
        return GET_FULL_NAME
    
    context.user_data['full_name'] = full_name
    
    # Ask for phone number
    message = (
        f"{EMOJIS['phone']} **الخطوة الثانية: رقم الهاتف**\n\n"
        "أرسل رقم هاتفك اليمني.\n"
        "يمكنك إرساله بأي من هذه الصيغ:\n"
        "• +967XXXXXXXXX\n"
        "• 967XXXXXXXXX\n"
        "• XXXXXXXXX"
    )
    
    update.message.reply_text(message, parse_mode='Markdown')
    return GET_PHONE


def get_phone(update: Update, context: CallbackContext):
    """Handle phone number input."""
    phone = update.message.text.strip()
    
    # Simple phone validation
    if not phone or len(phone) < 9:
        update.message.reply_text(
            f"{EMOJIS['error']} رقم الهاتف غير صحيح. حاول مرة أخرى."
        )
        return GET_PHONE
    
    context.user_data['phone'] = phone
    
    # Ask for role selection
    message = (
        f"{EMOJIS['info']} **الخطوة الثالثة: اختيار الدور**\n\n"
        "اختر دورك في النظام:\n\n"
        "**العميل:** شراء كروت الشبكة واستخدام الخدمات\n"
        "**الوكيل:** بيع الكروت للعملاء مع عمولة\n"
        "**المزود:** توفير كروت الشبكة للبيع"
    )
    
    keyboard = [
        [InlineKeyboardButton(f"{EMOJIS['user']} عميل", callback_data='role_customer')],
        [InlineKeyboardButton(f"{EMOJIS['user']} وكيل", callback_data='role_agent')],
        [InlineKeyboardButton(f"{EMOJIS['user']} مزود", callback_data='role_supplier')]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text(message, parse_mode='Markdown', reply_markup=reply_markup)
    return CHOOSE_ROLE


def handle_role_selection(update: Update, context: CallbackContext):
    """Handle role selection."""
    query = update.callback_query
    query.answer()
    
    role = query.data.replace('role_', '')
    
    if role not in USER_ROLES:
        query.edit_message_text(
            f"{EMOJIS['error']} دور غير صحيح. يرجى المحاولة مرة أخرى."
        )
        return CHOOSE_ROLE
    
    # Complete registration
    full_name = context.user_data['full_name']
    phone = context.user_data['phone']
    telegram_id = update.effective_user.id
    
    user_id = create_user(telegram_id, full_name, phone, role)
    
    if user_id:
        # Get user data
        user = get_user(telegram_id)
        
        success_message = (
            f"{EMOJIS['success']} **تم التسجيل بنجاح!**\n\n"
            f"**مرحباً {user[2]}!**\n"
            f"**رقم المحفظة:** {user[6]}\n"
            f"**الدور:** {USER_ROLES.get(user[4], user[4])}\n"
            f"**رصيدك:** {user[5]:.2f} ريال\n\n"
            "يمكنك الآن استخدام جميع خدمات البوت!"
        )
        
        # Show main menu
        show_main_menu(update, context, user)
        
        # Clear conversation data
        context.user_data.clear()
        
        logger.info(f"User {user_id} registered successfully with role {role}")
        return ConversationHandler.END
    else:
        query.edit_message_text(
            f"{EMOJIS['error']} فشل في إنشاء الحساب. يرجى المحاولة مرة أخرى أو التواصل مع الدعم."
        )
        return ConversationHandler.END


def show_main_menu(update: Update, context: CallbackContext, user=None):
    """Show main menu."""
    if not user:
        user = get_user(update.effective_user.id)
        if not user:
            update.message.reply_text(
                f"{EMOJIS['error']} يرجى التسجيل أولاً /start"
            )
            return
    
    update_user_activity(user[1])
    
    message = (
        f"{EMOJIS['home']} **القائمة الرئيسية**\n\n"
        f"مرحباً {user[2]}!\n"
        f"رصيدك: {user[5]:.2f} ريال\n"
        f"دورك: {USER_ROLES.get(user[4], user[4])}\n\n"
        "اختر من الخيارات أدناه:"
    )
    
    keyboard = [
        [InlineKeyboardButton(f"{EMOJIS['wallet']} محفظتي", callback_data='wallet')],
        [InlineKeyboardButton(f"{EMOJIS['purchase']} شراء كروت", callback_data='buy_cards')],
        [InlineKeyboardButton(f"{EMOJIS['transfer']} تحويل رصيد", callback_data='transfer')],
        [InlineKeyboardButton(f"{EMOJIS['stats']} تقاريري", callback_data='reports')],
        [InlineKeyboardButton(f"{EMOJIS['settings']} الإعدادات", callback_data='settings')]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        update.callback_query.edit_message_text(
            text=message, 
            parse_mode='Markdown', 
            reply_markup=reply_markup
        )
    else:
        update.message.reply_text(
            text=message, 
            parse_mode='Markdown', 
            reply_markup=reply_markup
        )


def handle_callback(update: Update, context: CallbackContext):
    """Handle callback queries."""
    query = update.callback_query
    query.answer()
    
    if query.data == 'wallet':
        show_wallet(update, context)
    elif query.data == 'buy_cards':
        show_buy_cards(update, context)
    elif query.data == 'transfer':
        show_transfer(update, context)
    elif query.data == 'reports':
        show_reports(update, context)
    elif query.data == 'settings':
        show_settings(update, context)
    elif query.data == 'main_menu':
        show_main_menu(update, context)


def show_wallet(update: Update, context: CallbackContext):
    """Show wallet information."""
    user = get_user(update.effective_user.id)
    
    message = (
        f"{EMOJIS['wallet']} **محفظتك**\n\n"
        f"**الاسم:** {user[2]}\n"
        f"**رقم المحفظة:** {user[6]}\n"
        f"**الرصيد الحالي:** {user[5]:.2f} ريال\n"
        f"**آخر نشاط:** {user[8]}\n\n"
        "**العمليات السريعة:**"
    )
    
    keyboard = [
        [InlineKeyboardButton(f"{EMOJIS['transfer']} تحويل رصيد", callback_data='transfer')],
        [InlineKeyboardButton(f"{EMOJIS['stats']} كشف حساب", callback_data='account_statement')],
        [InlineKeyboardButton(f"{EMOJIS['back']} رجوع", callback_data='main_menu')]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.callback_query.edit_message_text(
        text=message, 
        parse_mode='Markdown', 
        reply_markup=reply_markup
    )


def show_buy_cards(update: Update, context: CallbackContext):
    """Show buy cards options."""
    message = (
        f"{EMOJIS['purchase']} **شراء كروت الشبكة**\n\n"
        "هذه الميزة ستكون متاحة قريباً.\n"
        "يمكنك شراء كروت الشبكة من مختلف المزودين."
    )
    
    keyboard = [[InlineKeyboardButton(f"{EMOJIS['back']} رجوع", callback_data='main_menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    update.callback_query.edit_message_text(
        text=message, 
        parse_mode='Markdown', 
        reply_markup=reply_markup
    )


def show_transfer(update: Update, context: CallbackContext):
    """Show transfer options."""
    message = (
        f"{EMOJIS['transfer']} **تحويل رصيد**\n\n"
        "هذه الميزة ستكون متاحة قريباً.\n"
        "يمكنك تحويل رصيدك إلى مستخدمين آخرين."
    )
    
    keyboard = [[InlineKeyboardButton(f"{EMOJIS['back']} رجوع", callback_data='main_menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    update.callback_query.edit_message_text(
        text=message, 
        parse_mode='Markdown', 
        reply_markup=reply_markup
    )


def show_reports(update: Update, context: CallbackContext):
    """Show user reports."""
    user = get_user(update.effective_user.id)
    
    message = (
        f"{EMOJIS['stats']} **تقاريرك**\n\n"
        f"**الاسم:** {user[2]}\n"
        f"**الدور:** {USER_ROLES.get(user[4], user[4])}\n"
        f"**تاريخ التسجيل:** {user[7]}\n"
        f"**آخر نشاط:** {user[8]}\n\n"
        "**المعاملات:**\n"
        "لا توجد معاملات سابقة"
    )
    
    keyboard = [[InlineKeyboardButton(f"{EMOJIS['back']} رجوع", callback_data='main_menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    update.callback_query.edit_message_text(
        text=message, 
        parse_mode='Markdown', 
        reply_markup=reply_markup
    )


def show_settings(update: Update, context: CallbackContext):
    """Show settings."""
    message = (
        f"{EMOJIS['settings']} **الإعدادات**\n\n"
        "هذه الميزة ستكون متاحة قريباً.\n"
        "يمكنك تخصيص إعدادات البوت حسب احتياجاتك."
    )
    
    keyboard = [[InlineKeyboardButton(f"{EMOJIS['back']} رجوع", callback_data='main_menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    update.callback_query.edit_message_text(
        text=message, 
        parse_mode='Markdown', 
        reply_markup=reply_markup
    )


def menu_command(update: Update, context: CallbackContext):
    """Handle /menu command."""
    show_main_menu(update, context)


def help_command(update: Update, context: CallbackContext):
    """Handle /help command."""
    help_text = (
        f"{EMOJIS['info']} **مركز المساعدة**\n\n"
        "**الأوامر المتاحة:**\n"
        "/start - بدء البوت والتسجيل\n"
        "/menu - القائمة الرئيسية\n"
        "/help - هذه المساعدة\n\n"
        "**للتواصل مع الدعم:**\n"
        "يمكنك التواصل مع فريق الدعم عبر:\n"
        "📧 البريد الإلكتروني\n"
        "📱 رقم الهاتف\n\n"
        "**نصائح للاستخدام:**\n"
        "• تأكد من صحة رقم الهاتف\n"
        "• احتفظ برقم المحفظة\n"
        "• تحقق من المعاملات قبل التأكيد"
    )
    
    keyboard = [[InlineKeyboardButton(f"{EMOJIS['back']} رجوع", callback_data='main_menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    update.message.reply_text(help_text, parse_mode='Markdown', reply_markup=reply_markup)


def cancel_command(update: Update, context: CallbackContext):
    """Handle /cancel command."""
    context.user_data.clear()
    update.message.reply_text(
        f"{EMOJIS['cancel']} تم إلغاء العملية الحالية"
    )
    
    user = get_user(update.effective_user.id)
    if user:
        show_main_menu(update, context, user)


def main():
    """Main function."""
    # Initialize database
    init_database()
    
    # Create updater
    updater = Updater(token=BOT_TOKEN, use_context=True)
    dispatcher = updater.dispatcher
    
    # Add conversation handler for registration
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start_command)],
        states={
            GET_FULL_NAME: [MessageHandler(Filters.text & ~Filters.command, get_full_name)],
            GET_PHONE: [MessageHandler(Filters.text & ~Filters.command, get_phone)],
            CHOOSE_ROLE: [CallbackQueryHandler(handle_role_selection, pattern='^role_')]
        },
        fallbacks=[CommandHandler('cancel', cancel_command)]
    )
    
    dispatcher.add_handler(conv_handler)
    
    # Add other handlers
    dispatcher.add_handler(CommandHandler('menu', menu_command))
    dispatcher.add_handler(CommandHandler('help', help_command))
    dispatcher.add_handler(CommandHandler('cancel', cancel_command))
    dispatcher.add_handler(CallbackQueryHandler(handle_callback))
    
    # Start the bot
    logger.info("Starting Yemen Net Bot...")
    updater.start_polling()
    
    # Keep the bot running
    updater.idle()


if __name__ == '__main__':
    main()