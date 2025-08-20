#!/usr/bin/env python3
"""
Simple Yemen Net Bot - Fixed Version
"""

import logging
import sqlite3
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ConversationHandler, PicklePersistence, filters, CallbackContext
)

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Bot configuration - KEEPING THE BOT TOKEN SAFE
BOT_TOKEN = '7766964799:AAHex-hGfjPX6g_R2aZ7-UPrgnFxQKAjSa0'
DB_PATH = os.getenv('DB_PATH', os.path.abspath('yemen_net.db'))

# Emojis
EMOJIS = {
    'success': '✅',
    'error': '❌',
    'warning': '⚠️',
    'info': 'ℹ️',
    'loading': '⏳',
    'money': '💰',
    'card': '🎫',
    'network': '📶',
    'user': '👤',
    'home': '🏠',
    'help': '❓'
}

def get_db_connection():
    """Get database connection"""
    try:
        conn = sqlite3.connect(DB_PATH, timeout=30.0)
        conn.execute('PRAGMA foreign_keys = ON')
        conn.execute('PRAGMA journal_mode = WAL')
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        raise

def init_db():
    """Initialize database"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE NOT NULL,
                full_name TEXT NOT NULL,
                phone TEXT UNIQUE NOT NULL,
                role TEXT NOT NULL DEFAULT 'customer',
                balance REAL DEFAULT 0.0,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Networks table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS networks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("Database initialized successfully")
        
    except Exception as e:
        logger.error(f"Database initialization error: {e}")
        raise

async def start(update: Update, context: CallbackContext):
    """Handle /start command"""
    try:
        user = update.effective_user
        welcome_text = f"""
🚀 **مرحباً بك في بوت كروت الإنترنت اليمني!** 🚀

👤 **{user.first_name}**
🎯 **اختر العملية المطلوبة:**
"""
        
        keyboard = [
            [InlineKeyboardButton('💳 محفظتي', callback_data='wallet')],
            [InlineKeyboardButton('🛒 شراء كروت', callback_data='buy_cards')],
            [InlineKeyboardButton('💸 تحويل رصيد', callback_data='transfer')],
            [InlineKeyboardButton('❓ المساعدة', callback_data='help')]
        ]
        
        await update.message.reply_text(
            welcome_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Error in start handler: {e}")
        await update.message.reply_text(f"{EMOJIS['error']} حدث خطأ. يرجى المحاولة مرة أخرى.")

async def button_click(update: Update, context: CallbackContext):
    """Handle button clicks"""
    try:
        query = update.callback_query
        await query.answer()
        
        if query.data == 'wallet':
            await query.edit_message_text(
                f"{EMOJIS['money']} **محفظتك**\n\n💰 الرصيد: **0.00** ريال\n\n🚧 هذه الميزة قيد التطوير",
                parse_mode='Markdown'
            )
        elif query.data == 'buy_cards':
            await query.edit_message_text(
                f"{EMOJIS['card']} **شراء الكروت**\n\n🚧 هذه الميزة قيد التطوير",
                parse_mode='Markdown'
            )
        elif query.data == 'transfer':
            await query.edit_message_text(
                f"{EMOJIS['money']} **تحويل الرصيد**\n\n🚧 هذه الميزة قيد التطوير",
                parse_mode='Markdown'
            )
        elif query.data == 'help':
            await query.edit_message_text(
                f"{EMOJIS['help']} **مركز المساعدة**\n\n📱 الأوامر المتاحة:\n/start - القائمة الرئيسية\n/help - المساعدة",
                parse_mode='Markdown'
            )
        else:
            await query.edit_message_text(
                f"{EMOJIS['info']} ميزة غير متاحة حالياً",
                parse_mode='Markdown'
            )
            
    except Exception as e:
        logger.error(f"Error in button click: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ.")

async def help_command(update: Update, context: CallbackContext):
    """Handle /help command"""
    help_text = f"""
{EMOJIS['help']} **مركز المساعدة**

📱 **الأوامر المتاحة:**
/start - القائمة الرئيسية
/help - هذه الرسالة

💡 **للمساعدة الإضافية:**
تواصل مع الإدارة
"""
    
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def error_handler(update: object, context: CallbackContext):
    """Handle errors"""
    logger.error("Exception while handling an update:", exc_info=context.error)
    
    try:
        if isinstance(update, Update) and update.effective_chat:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"{EMOJIS['error']} حدث خطأ غير متوقع. يرجى المحاولة مرة أخرى."
            )
    except Exception:
        pass

def main():
    """Main function"""
    try:
        # Initialize database
        logger.info("Initializing database...")
        init_db()
        
        # Create application
        persistence = PicklePersistence(filepath='bot_data')
        application = Application.builder().token(BOT_TOKEN).persistence(persistence).build()
        
        # Add handlers
        application.add_handler(CommandHandler('start', start))
        application.add_handler(CommandHandler('help', help_command))
        application.add_handler(CallbackQueryHandler(button_click))
        application.add_error_handler(error_handler)
        
        # Start the bot
        logger.info(f'{EMOJIS["success"]} Starting Yemen Net Bot...')
        application.run_polling(drop_pending_updates=True)
        
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        raise

if __name__ == '__main__':
    main()