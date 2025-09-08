#!/usr/bin/env python3
"""
Main entry point for the refactored Yemen Net Bot
"""

import logging
import os
import sys

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    filters,
)

# Add src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.core.config import BOT_TOKEN
from src.core.database import init_db
from src.handlers.registration_handler import (
    start,
    get_full_name,
    get_phone,
    choose_role,
    GET_FULL_NAME,
    GET_PHONE,
    CHOOSE_ROLE,
)
from src.handlers.callback_dispatcher import dispatch_callback_query
from src.handlers.text_handler import handle_text_message
from src.handlers.menu_handler import show_main_menu

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

def main():
    """Main function to start the bot."""
    logger.info("Initializing database...")
    init_db()
    logger.info("Database initialized.")

    application = Application.builder().token(BOT_TOKEN).build()

    # Conversation handler for registration
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            GET_FULL_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_full_name)],
            GET_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_phone)],
            CHOOSE_ROLE: [CallbackQueryHandler(choose_role, pattern='^role_')],
        },
        fallbacks=[CommandHandler('start', start)],
        name="registration_conversation",
        persistent=False,
        allow_reentry=True,
    )

    application.add_handler(conv_handler)

    # Add other handlers
    application.add_handler(CommandHandler("menu", show_main_menu))
    application.add_handler(CallbackQueryHandler(dispatch_callback_query))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))

    logger.info("Starting bot...")
    application.run_polling()

if __name__ == '__main__':
    main()
