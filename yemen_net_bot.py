#!/usr/bin/env python3
"""
Yemen Net Bot - Main Bot Class
Core bot functionality and initialization
"""

import logging
import asyncio
import sys
import os
from telegram.ext import Application, PicklePersistence

# Add bot_modules to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'bot_modules'))

from bot_modules.config import *
from bot_modules.database import init_db
from bot_modules.handlers import setup_handlers
from bot_modules.callback_handlers import setup_callback_handlers

logger = logging.getLogger(__name__)

class YemenNetBot:
    """Main bot class with all functionality"""
    
    def __init__(self):
        """Initialize the bot"""
        self.application = None
        self.setup_logging()
        self.init_database()
    
    def setup_logging(self):
        """Setup logging configuration"""
        logging.basicConfig(
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            level=logging.INFO,
            handlers=[
                logging.FileHandler('bot.log'),
                logging.StreamHandler()
            ]
        )
        logger.info("Logging configured successfully")
    
    def init_database(self):
        """Initialize database"""
        try:
            init_db()
            logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            raise
    
    def setup_application(self):
        """Setup the Telegram application"""
        try:
            # Create persistence
            persistence = PicklePersistence(filepath='yemen_net_bot_data')
            
            # Build application
            self.application = Application.builder().token(BOT_TOKEN).persistence(persistence).build()
            
            # Setup handlers
            setup_handlers(self.application)
            setup_callback_handlers(self.application)
            
            # Setup bot commands
            self.setup_commands()
            
            logger.info("Application setup completed successfully")
            
        except Exception as e:
            logger.error(f"Application setup failed: {e}")
            raise
    
    async def setup_commands(self):
        """Setup bot commands"""
        try:
            await self.application.bot.set_my_commands(QUICK_COMMANDS)
            await self.application.bot.set_chat_menu_button(menu_button=MenuButtonCommands())
            logger.info("Bot commands set successfully")
        except Exception as e:
            logger.warning(f'Failed setting commands/menu: {e}')
    
    def start(self):
        """Start the bot"""
        try:
            logger.info("Starting bot...")
            self.setup_application()
            
            # Start polling
            self.application.run_polling()
            
        except Exception as e:
            logger.error(f"Failed to start bot: {e}")
            raise
    
    def stop(self):
        """Stop the bot"""
        if self.application:
            self.application.stop()
            logger.info("Bot stopped successfully")