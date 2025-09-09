#!/usr/bin/env python3
"""
Pottagrm Enhanced Bot - Main Entry Point (Restructured)
Yemen Net Card Sales Bot with Enhanced Features
Version: 2.2.0 - Restructured for better maintainability

Author: AI Assistant
License: MIT
"""

import logging
import asyncio
import sys
import os
from datetime import datetime
import sqlite3
from telegram.error import TelegramError, NetworkError, TimedOut, BadRequest

# Add bot_modules to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'bot_modules'))

# Import Telegram bot components
from telegram import Update, MenuButtonCommands, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ConversationHandler, PicklePersistence, filters, CallbackContext
)

# Import our modular components
try:
    # Import configuration and database
    from config import *
    from database import init_db, get_db_connection
    
    # Import utilities
    from utils import (
        get_user, recalc_and_set_user_balance,
        get_or_create_supplier_code, get_cards_stats_by_category,
        get_card_categories, process_uploaded_cards,
        get_user_permissions
    )
    
    # Import handlers
    from handlers import (
        COMMAND_HANDLERS, CONVERSATION_STATES, handle_text_message, show_main_menu,
        redeem_coupon_handler, cancel_coupon_handler, quick_transfer_handler,
        select_user_for_transfer, process_amount_selection, process_card_purchase,
        skip_network_location, search_by_type_handler, choose_role
    )
    
    # Import account statement handlers
    from account_statement import (
        account_statement_handler, download_excel_30_handler, download_excel_90_handler,
        download_excel_all_handler, download_pdf_30_handler, download_pdf_90_handler,
        download_pdf_all_handler
    )
    
    # Import accounting engine
    from accounting_engine import (
        AccountingEngine, record_purchase_accounting, record_transfer_accounting,
        record_coupon_accounting, record_commission_accounting, record_money_creation_accounting
    )
    
    # Import export system
    from export_system import (
        export_options_handler, export_profits_handler, export_customers_handler,
        export_suppliers_handler, export_comprehensive_handler, ExportSystem, quick_export_handler
    )
    
    # Import accounting search
    from accounting_search import (
        accounting_search_handler, quick_stats_handler, quick_transaction_report_handler
    )
    
    # Import admin functions
    from admin_functions import (
        ADMIN_CALLBACKS, activate_single_supplier, admin_panel_handler,
        admin_add_offers_handler, accounting_system_handler,
        create_coupons_handler, create_quick_coupon_handler,
        coupons_stats_handler, list_coupons_handler
    )
    
    # Import management modules
    from customer_management import CustomerManagement
    from admin_management import AdminManagement
    from admin_management_extended import AdminManagementExtended
    from enhanced_error_messages import ErrorMessages, db_error, perm_error, net_error, unexpected_error, menu_error, wallet_error, search_error, coupon_error
    
    # Import permissions system
    from permissions import has_permission, check_permission_or_deny, AVAILABLE_PERMISSIONS
    
    # Import restructured handler modules
    from main_router import button_click_handler
    
    # Import withdrawal handlers for text processing
    from withdrawal_handlers import process_withdrawal_step
    
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

# Custom exception classes for better error handling
class BotError(Exception):
    """Base exception for bot errors"""
    pass

class BotConfigurationError(BotError):
    """Bot configuration error"""
    pass

class BotDatabaseError(BotError):
    """Database related error"""
    pass

class BotValidationError(BotError):
    """Validation error"""
    pass

class BotPermissionError(BotError):
    """Permission denied error"""
    pass

class BotNetworkError(BotError):
    """Network related error"""
    pass

# Database helper functions
async def safe_db_operation(operation_func, *args, timeout=10.0, **kwargs):
    """Execute database operation with timeout and error handling"""
    try:
        return await asyncio.wait_for(
            asyncio.create_task(operation_func(*args, **kwargs)),
            timeout=timeout
        )
    except asyncio.TimeoutError:
        logger.error(f"Database operation timed out: {operation_func.__name__}")
        raise BotDatabaseError("Database operation timed out")
    except sqlite3.Error as e:
        logger.error(f"Database error in {operation_func.__name__}: {e}")
        raise BotDatabaseError(f"Database error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error in {operation_func.__name__}: {e}")
        raise BotError(f"Operation failed: {e}")

# Cleanup function for conversation data
async def cleanup_old_conversations(context):
    """Clean up old conversation data to prevent memory leaks"""
    try:
        # This would normally clean up old conversation data
        # Implementation depends on your persistence strategy
        logger.debug("Conversation cleanup completed")
    except Exception as e:
        logger.error(f"Error in conversation cleanup: {e}")

# Enhanced database connection with better error handling
async def get_pooled_db_connection():
    """Get database connection from pool with retry logic"""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            return get_db_connection()
        except Exception as e:
            if attempt < max_retries - 1:
                await asyncio.sleep(0.1 * (attempt + 1))
                continue
            else:
                raise BotDatabaseError(f"Failed to get database connection: {e}")

# Enhanced text message handler
async def enhanced_text_handler(update: Update, context: CallbackContext):
    """Enhanced text message handler with withdrawal processing"""
    try:
        user = get_user(update.effective_user.id)
        if not user:
            return
            
        message_text = update.message.text.strip()
        
        # Handle withdrawal steps
        if context.user_data.get('withdrawal_step'):
            await process_withdrawal_step(update, context, message_text)
            return
        
        # Handle other text processing from original handlers
        await handle_text_message(update, context)
        
    except Exception as e:
        logger.error(f"Error in enhanced text handler: {e}")
        await update.message.reply_text(f"{EMOJIS['error']} حدث خطأ في معالجة الرسالة")

# Utility functions
async def send_notification_to_super_admin(message: str, context: CallbackContext):
    """Send notification to super admin"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT telegram_id FROM users WHERE role = 'super_admin' LIMIT 1")
        admin = cursor.fetchone()
        
        if admin:
            await context.bot.send_message(
                chat_id=admin[0],
                text=f"🔔 **إشعار إداري**\n\n{message}",
                parse_mode='Markdown'
            )
        
        conn.close()
    except Exception as e:
        logger.error(f"Error sending notification to admin: {e}")

def main():
    """Main function to start the bot with enhanced error handling"""
    try:
        # Initialize database with timeout
        logger.info("Initializing database...")
        try:
            init_db()
            logger.info("Database initialized successfully")
        except sqlite3.Error as e:
            raise BotDatabaseError(f"Failed to initialize database: {e}")
        except Exception as e:
            raise BotConfigurationError(f"Database configuration error: {e}")
        
        # Validate configuration
        if not BOT_TOKEN:
            raise BotConfigurationError("BOT_TOKEN is not configured")
        
        # Create application without persistence to avoid sqlite3.Row pickle issues
        try:
            # تم تعطيل persistence مؤقتاً لحل مشكلة sqlite3.Row
            application = Application.builder().token(BOT_TOKEN).build()
        except Exception as e:
            raise BotConfigurationError(f"Failed to create application: {e}")
        
        # Set bot commands (will be done after startup)
        async def post_init(application):
            """Post-initialization setup"""
            try:
                logger.info("Setting bot commands...")
                await application.bot.set_my_commands(QUICK_COMMANDS)
                await application.bot.set_chat_menu_button(menu_button=MenuButtonCommands())
                logger.info("Bot commands set successfully")
            except Exception as e:
                logger.error(f'Unexpected error setting commands/menu: {e}')
        
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
                MessageHandler(filters.TEXT & filters.Regex(r'^/cancel$'), COMMAND_HANDLERS['cancel']),
            ],
            name='yemen_net_conversation',
            persistent=False,
            allow_reentry=True,
            per_message=False,
            per_chat=True,
        )
        
        # Enhanced error handler
        async def error_handler(update: object, context: CallbackContext) -> None:
            """Enhanced error handler with detailed logging"""
            try:
                logger.error(f"Exception while handling an update: {context.error}")
                
                # Get error details
                error_message = str(context.error)
                error_type = type(context.error).__name__
                
                # Handle different error types
                if isinstance(context.error, NetworkError):
                    logger.warning(f"Network error: {error_message}")
                    return
                elif isinstance(context.error, TimedOut):
                    logger.warning(f"Request timed out: {error_message}")
                    return
                elif isinstance(context.error, BadRequest):
                    logger.warning(f"Bad request: {error_message}")
                    return
                
                # For update-related errors, try to send error message
                if update and hasattr(update, 'effective_chat'):
                    try:
                        error_text = f"""
❌ **حدث خطأ تقني**

🔧 نوع الخطأ: {error_type}
📝 التفاصيل: خطأ داخلي في النظام

💡 **الحلول المقترحة:**
• أعد المحاولة خلال دقيقة
• تأكد من اتصال الإنترنت
• تواصل مع الدعم إذا استمر الخطأ

🔄 يمكنك العودة للقائمة الرئيسية والمحاولة مرة أخرى
"""
                        
                        await context.bot.send_message(
                            chat_id=update.effective_chat.id,
                            text=error_text,
                            reply_markup=InlineKeyboardMarkup([
                                [InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
                            ]),
                            parse_mode='Markdown'
                        )
                    except Exception as send_error:
                        logger.error(f"Failed to send error message: {send_error}")
                
            except Exception as e:
                logger.critical(f"Error in error handler: {e}")
        
        # Add handlers to application
        try:
            application.add_handler(conv_handler)
            application.add_handler(CallbackQueryHandler(button_click_handler))
            application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, enhanced_text_handler))
            application.add_error_handler(error_handler)
            
            logger.info("All handlers added successfully")
        except Exception as e:
            raise BotConfigurationError(f"Failed to add handlers: {e}")
        
        # Start the bot
        logger.info("🔥 Starting Pottagrm Enhanced Bot v2.2.0 (Restructured)...")
        try:
            application.run_polling(
                drop_pending_updates=True
            )
        except KeyboardInterrupt:
            logger.info("Bot stopped by user")
        except Exception as e:
            logger.critical(f"Bot stopped due to error: {e}")
            raise
            
    except BotConfigurationError as e:
        logger.critical(f"Configuration error: {e}")
        sys.exit(1)
    except BotDatabaseError as e:
        logger.critical(f"Database error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.critical(f"Unexpected error prevented bot startup: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()