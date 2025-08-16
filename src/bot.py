#!/usr/bin/env python3
"""
Yemen Net Bot - Main Bot Application
Professional Telegram bot with advanced features and error handling.
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Dict, Any

from telegram import BotCommand, Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ConversationHandler, PicklePersistence, filters, ContextTypes
)

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from core.config import config, EMOJIS, CONVERSATION_STATES
from core.database import db
from handlers.commands import COMMAND_HANDLERS
from handlers.conversations import RegistrationConversation

logger = logging.getLogger(__name__)


class YemenNetBot:
    """Main bot class with professional architecture."""
    
    def __init__(self):
        self.config = config
        self.db = db
        self.application = None
        self._setup_logging()
    
    def _setup_logging(self) -> None:
        """Setup comprehensive logging."""
        log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        
        # File handler
        file_handler = logging.FileHandler('bot.log', encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(logging.Formatter(log_format))
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(logging.Formatter(log_format))
        
        # Root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)
        root_logger.addHandler(file_handler)
        root_logger.addHandler(console_handler)
        
        logger.info("Logging setup completed")
    
    async def _setup_application(self) -> None:
        """Setup Telegram application with persistence."""
        try:
            # Initialize persistence
            persistence = PicklePersistence(filepath="bot_data.pkl")
            
            # Create application
            self.application = Application.builder().token(
                self.config.bot.token
            ).persistence(persistence).build()
            
            logger.info("Telegram application created successfully")
            
        except Exception as e:
            logger.error(f"Failed to create application: {e}")
            raise
    
    async def _setup_handlers(self) -> None:
        """Setup all bot handlers."""
        try:
            # Command handlers
            for command, handler in COMMAND_HANDLERS.items():
                self.application.add_handler(
                    CommandHandler(command, handler)
                )
                logger.info(f"Added command handler: /{command}")
            
            # Registration conversation
            registration_handler = RegistrationConversation()
            self.application.add_handler(registration_handler.get_handler())
            logger.info("Added registration conversation handler")
            
            # Callback query handlers
            self._setup_callback_handlers()
            
            # Message handlers
            self._setup_message_handlers()
            
            # Error handler
            self.application.add_error_handler(self._error_handler)
            
            logger.info("All handlers setup completed")
            
        except Exception as e:
            logger.error(f"Failed to setup handlers: {e}")
            raise
    
    def _setup_callback_handlers(self) -> None:
        """Setup callback query handlers."""
        # Main menu
        self.application.add_handler(
            CallbackQueryHandler(self._main_menu_callback, pattern='^main_menu$')
        )
        
        # Enhanced wallet
        self.application.add_handler(
            CallbackQueryHandler(self._enhanced_wallet_callback, pattern='^enhanced_wallet$')
        )
        
        # Buy cards
        self.application.add_handler(
            CallbackQueryHandler(self._buy_cards_callback, pattern='^buy_cards$')
        )
        
        # Transfer balance
        self.application.add_handler(
            CallbackQueryHandler(self._transfer_balance_callback, pattern='^transfer_balance$')
        )
        
        # Search networks
        self.application.add_handler(
            CallbackQueryHandler(self._search_networks_callback, pattern='^search_networks$')
        )
        
        # My reports
        self.application.add_handler(
            CallbackQueryHandler(self._my_reports_callback, pattern='^my_reports$')
        )
        
        # Settings
        self.application.add_handler(
            CallbackQueryHandler(self._settings_callback, pattern='^settings$')
        )
        
        # Admin panel
        self.application.add_handler(
            CallbackQueryHandler(self._admin_panel_callback, pattern='^admin_panel$')
        )
        
        logger.info("Callback handlers setup completed")
    
    def _setup_message_handlers(self) -> None:
        """Setup message handlers."""
        # Text messages (for conversations)
        self.application.add_handler(
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                self._handle_text_message
            )
        )
        
        logger.info("Message handlers setup completed")
    
    async def _setup_commands(self) -> None:
        """Setup bot commands menu."""
        try:
            commands = [
                BotCommand('start', '🏠 البداية - القائمة الرئيسية'),
                BotCommand('menu', '📋 القائمة السريعة'),
                BotCommand('wallet', '💳 محفظتي المطورة'),
                BotCommand('buy', '🛒 شراء كروت الشبكة'),
                BotCommand('transfer', '💸 تحويل رصيد لصديق'),
                BotCommand('balance', '💰 عرض الرصيد والمعاملات'),
                BotCommand('reports', '📊 تقاريري الشخصية'),
                BotCommand('help', '❓ المساعدة والدعم'),
                BotCommand('cancel', '❌ إلغاء العملية الحالية'),
            ]
            
            # Add admin commands for admin users
            if hasattr(self, 'admin_commands'):
                commands.extend(self.admin_commands)
            
            await self.application.bot.set_my_commands(commands)
            logger.info("Bot commands setup completed")
            
        except Exception as e:
            logger.error(f"Failed to setup commands: {e}")
    
    async def _error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Global error handler."""
        try:
            logger.error(f"Exception while handling an update: {context.error}")
            
            # Send user-friendly error message
            if update and update.effective_message:
                error_message = (
                    f"{EMOJIS['error']} عذراً، حدث خطأ غير متوقع.\n"
                    "يرجى المحاولة مرة أخرى أو التواصل مع الدعم."
                )
                await update.effective_message.reply_text(error_message)
                
        except Exception as e:
            logger.error(f"Error in error handler: {e}")
    
    # Callback handlers
    async def _main_menu_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle main menu callback."""
        from handlers.commands import menu_handler
        await menu_handler.handle(update, context)
    
    async def _enhanced_wallet_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle enhanced wallet callback."""
        from handlers.commands import wallet_handler
        await wallet_handler.handle(update, context)
    
    async def _buy_cards_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle buy cards callback."""
        # TODO: Implement buy cards functionality
        await update.callback_query.answer("سيتم إضافة هذه الميزة قريباً")
    
    async def _transfer_balance_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle transfer balance callback."""
        # TODO: Implement transfer balance functionality
        await update.callback_query.answer("سيتم إضافة هذه الميزة قريباً")
    
    async def _search_networks_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle search networks callback."""
        # TODO: Implement search networks functionality
        await update.callback_query.answer("سيتم إضافة هذه الميزة قريباً")
    
    async def _my_reports_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle my reports callback."""
        # TODO: Implement reports functionality
        await update.callback_query.answer("سيتم إضافة هذه الميزة قريباً")
    
    async def _settings_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle settings callback."""
        # TODO: Implement settings functionality
        await update.callback_query.answer("سيتم إضافة هذه الميزة قريباً")
    
    async def _admin_panel_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle admin panel callback."""
        from handlers.commands import admin_handler
        await admin_handler.handle(update, context)
    
    async def _handle_text_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle text messages for conversations."""
        # Check if user is in a conversation
        if 'conversation_state' in context.user_data:
            # Route to appropriate conversation handler
            current_state = context.user_data['conversation_state']
            
            if current_state in [CONVERSATION_STATES['GET_FULL_NAME'], 
                               CONVERSATION_STATES['GET_PHONE'], 
                               CONVERSATION_STATES['CHOOSE_ROLE']]:
                # Registration conversation
                registration_handler = RegistrationConversation()
                await registration_handler.handle_message(update, context)
            else:
                # Unknown conversation state
                await update.message.reply_text(
                    f"{EMOJIS['error']} حالة محادثة غير معروفة. استخدم /cancel للإلغاء."
                )
        else:
            # No active conversation
            await update.message.reply_text(
                f"{EMOJIS['info']} استخدم /start للبدء أو /help للمساعدة."
            )
    
    async def start(self) -> None:
        """Start the bot."""
        try:
            logger.info("Starting Yemen Net Bot...")
            
            # Setup application
            await self._setup_application()
            
            # Setup handlers
            await self._setup_handlers()
            
            # Setup commands
            await self._setup_commands()
            
            # Initialize database
            logger.info("Initializing database...")
            # Database is already initialized in DatabaseManager.__init__()
            
            # Start polling
            logger.info("Starting bot polling...")
            await self.application.initialize()
            await self.application.start()
            await self.application.updater.start_polling()
            
            logger.info("Bot started successfully!")
            
            # Keep the bot running
            await self.application.updater.idle()
            
        except Exception as e:
            logger.error(f"Failed to start bot: {e}")
            raise
        finally:
            if self.application:
                try:
                    await self.application.updater.stop()
                    await self.application.stop()
                    await self.application.shutdown()
                except Exception as e:
                    logger.error(f"Error during shutdown: {e}")
    
    async def stop(self) -> None:
        """Stop the bot gracefully."""
        try:
            if self.application:
                logger.info("Stopping bot...")
                await self.application.updater.stop()
                await self.application.stop()
                await self.application.shutdown()
                logger.info("Bot stopped successfully")
        except Exception as e:
            logger.error(f"Error stopping bot: {e}")


async def main():
    """Main entry point."""
    bot = YemenNetBot()
    
    try:
        await bot.start()
    except KeyboardInterrupt:
        logger.info("Received interrupt signal, stopping bot...")
        await bot.stop()
    except Exception as e:
        logger.error(f"Bot crashed: {e}")
        await bot.stop()
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)