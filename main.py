#!/usr/bin/env python3
"""
Yemen Net Bot - Main Entry Point
Improved version with proper error handling and modular structure
"""

import asyncio
import logging
import signal
import sys
import os
from datetime import datetime
from typing import Optional

# Import core modules
from core.config import Config
from core.exceptions import BotError, DatabaseError, NetworkError
from core.logger import setup_logger
from services.database_manager import DatabaseManager
from services.rate_limiter import RateLimiter
from services.cache_manager import CacheManager
from services.notification_manager import NotificationManager
from handlers.bot_handlers import BotHandlers
from utils.validators import validate_environment

# Import telegram modules
from telegram import Update
from telegram.ext import Application, ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from telegram.error import NetworkError as TelegramNetworkError, TimedOut, BadRequest

class YemenNetBot:
    """Main bot class with improved architecture"""
    
    def __init__(self):
        self.config = Config()
        self.logger = setup_logger()
        self.db_manager: Optional[DatabaseManager] = None
        self.rate_limiter: Optional[RateLimiter] = None
        self.cache_manager: Optional[CacheManager] = None
        self.notification_manager: Optional[NotificationManager] = None
        self.application: Optional[Application] = None
        self.bot_handlers: Optional[BotHandlers] = None
        self.shutdown_event = asyncio.Event()
        
    async def initialize(self) -> bool:
        """Initialize all bot components"""
        try:
            self.logger.info("🚀 Initializing Yemen Net Bot...")
            
            # Validate environment
            if not validate_environment():
                raise BotError("Environment validation failed")
            
            # Initialize database manager
            self.db_manager = DatabaseManager(self.config.DATABASE_PATH)
            await self.db_manager.initialize()
            
            # Initialize other services
            self.rate_limiter = RateLimiter()
            self.cache_manager = CacheManager()
            self.notification_manager = NotificationManager(self.db_manager)
            
            # Initialize telegram application
            self.application = ApplicationBuilder().token(self.config.BOT_TOKEN).build()
            
            # Initialize handlers
            self.bot_handlers = BotHandlers(
                db_manager=self.db_manager,
                rate_limiter=self.rate_limiter,
                cache_manager=self.cache_manager,
                notification_manager=self.notification_manager
            )
            
            # Setup handlers
            self._setup_handlers()
            
            # Setup error handlers
            self.application.add_error_handler(self._error_handler)
            
            self.logger.info("✅ Bot initialization completed successfully")
            return True
            
        except DatabaseError as e:
            self.logger.error(f"❌ Database initialization failed: {e}")
            return False
        except NetworkError as e:
            self.logger.error(f"❌ Network initialization failed: {e}")
            return False
        except Exception as e:
            self.logger.error(f"❌ Unexpected error during initialization: {e}", exc_info=True)
            return False
    
    def _setup_handlers(self):
        """Setup all bot handlers"""
        try:
            # Command handlers
            self.application.add_handler(CommandHandler("start", self.bot_handlers.start_handler))
            self.application.add_handler(CommandHandler("help", self.bot_handlers.help_handler))
            self.application.add_handler(CommandHandler("admin", self.bot_handlers.admin_handler))
            self.application.add_handler(CommandHandler("wallet", self.bot_handlers.wallet_handler))
            self.application.add_handler(CommandHandler("balance", self.bot_handlers.balance_handler))
            self.application.add_handler(CommandHandler("buy", self.bot_handlers.buy_handler))
            self.application.add_handler(CommandHandler("profile", self.bot_handlers.profile_handler))
            self.application.add_handler(CommandHandler("stats", self.bot_handlers.stats_handler))
            self.application.add_handler(CommandHandler("networks", self.bot_handlers.networks_handler))
            
            # Callback query handler
            self.application.add_handler(CallbackQueryHandler(self.bot_handlers.button_click_handler))
            
            # Message handlers
            self.application.add_handler(MessageHandler(
                filters.TEXT & ~filters.COMMAND, 
                self.bot_handlers.message_handler
            ))
            self.application.add_handler(MessageHandler(
                filters.Document.ALL,
                self.bot_handlers.document_handler
            ))
            self.application.add_handler(MessageHandler(
                filters.PHOTO,
                self.bot_handlers.photo_handler
            ))
            
            self.logger.info("✅ All handlers registered successfully")
            
        except Exception as e:
            self.logger.error(f"❌ Error setting up handlers: {e}", exc_info=True)
            raise BotError(f"Handler setup failed: {e}")
    
    async def _error_handler(self, update: Update, context) -> None:
        """Global error handler with proper categorization"""
        try:
            error = context.error
            user_id = update.effective_user.id if update and update.effective_user else "Unknown"
            
            # Log the error with context
            self.logger.error(
                f"❌ Error for user {user_id}: {error}",
                exc_info=True,
                extra={
                    'user_id': user_id,
                    'update': str(update),
                    'error_type': type(error).__name__
                }
            )
            
            # Handle specific error types
            if isinstance(error, TelegramNetworkError):
                await self._handle_network_error(update, context, error)
            elif isinstance(error, TimedOut):
                await self._handle_timeout_error(update, context, error)
            elif isinstance(error, BadRequest):
                await self._handle_bad_request_error(update, context, error)
            elif isinstance(error, DatabaseError):
                await self._handle_database_error(update, context, error)
            else:
                await self._handle_unknown_error(update, context, error)
                
        except Exception as e:
            self.logger.critical(f"🚨 Critical error in error handler: {e}", exc_info=True)
    
    async def _handle_network_error(self, update: Update, context, error: TelegramNetworkError):
        """Handle network-related errors"""
        self.logger.warning(f"🌐 Network error: {error}")
        if update and update.effective_chat:
            try:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="⚠️ حدث خطأ في الشبكة. يرجى المحاولة مرة أخرى."
                )
            except Exception:
                pass  # Don't raise on error notification failure
    
    async def _handle_timeout_error(self, update: Update, context, error: TimedOut):
        """Handle timeout errors"""
        self.logger.warning(f"⏱️ Timeout error: {error}")
        if update and update.effective_chat:
            try:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="⏱️ انتهت مهلة العملية. يرجى المحاولة مرة أخرى."
                )
            except Exception:
                pass
    
    async def _handle_bad_request_error(self, update: Update, context, error: BadRequest):
        """Handle bad request errors"""
        self.logger.warning(f"❌ Bad request: {error}")
        if "Message is not modified" not in str(error):
            # Only log non-trivial bad requests
            self.logger.error(f"❌ Significant bad request: {error}")
    
    async def _handle_database_error(self, update: Update, context, error: DatabaseError):
        """Handle database errors"""
        self.logger.error(f"🗄️ Database error: {error}")
        if update and update.effective_chat:
            try:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="🗄️ حدث خطأ في قاعدة البيانات. يرجى المحاولة لاحقاً."
                )
            except Exception:
                pass
    
    async def _handle_unknown_error(self, update: Update, context, error: Exception):
        """Handle unknown errors"""
        self.logger.error(f"❓ Unknown error: {error}", exc_info=True)
        if update and update.effective_chat:
            try:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="❌ حدث خطأ غير متوقع. تم إبلاغ المطورين."
                )
            except Exception:
                pass
    
    async def start(self):
        """Start the bot"""
        try:
            self.logger.info("🚀 Starting Yemen Net Bot...")
            
            # Initialize bot
            if not await self.initialize():
                self.logger.error("❌ Bot initialization failed")
                return False
            
            # Start polling
            self.logger.info("📡 Starting bot polling...")
            await self.application.run_polling(
                drop_pending_updates=True,
                allowed_updates=Update.ALL_TYPES
            )
            
        except KeyboardInterrupt:
            self.logger.info("⏹️ Bot stopped by user")
        except Exception as e:
            self.logger.error(f"❌ Critical error in bot startup: {e}", exc_info=True)
            return False
        finally:
            await self.shutdown()
    
    async def shutdown(self):
        """Graceful shutdown"""
        try:
            self.logger.info("⏹️ Shutting down bot...")
            
            if self.application:
                await self.application.shutdown()
            
            if self.db_manager:
                await self.db_manager.close()
            
            if self.cache_manager:
                await self.cache_manager.cleanup()
            
            self.logger.info("✅ Bot shutdown completed")
            
        except Exception as e:
            self.logger.error(f"❌ Error during shutdown: {e}", exc_info=True)
    
    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        def signal_handler(signum, frame):
            self.logger.info(f"📡 Received signal {signum}")
            asyncio.create_task(self.shutdown())
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)


async def main():
    """Main entry point"""
    bot = YemenNetBot()
    bot.setup_signal_handlers()
    
    try:
        await bot.start()
    except Exception as e:
        print(f"❌ Critical error in main: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # Set up proper event loop policy for different platforms
    if sys.platform.startswith('win'):
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    # Run the bot
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("⏹️ Bot stopped")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        sys.exit(1)