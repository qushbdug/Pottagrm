#!/usr/bin/env python3
"""
Pottagrm Enhanced Bot v2.0
Main Entry Point - Completely Restructured
"""

import asyncio
import logging
import logging.config
import signal
import sys
import time
from typing import Optional, Dict, Any
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from telegram import Update, BotCommand
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ConversationHandler, filters, CallbackContext
)

# Import bot modules
from bot_v2.config.settings import *
from bot_v2.services.database_service import get_database_manager, close_database_manager
from bot_v2.services.rate_limiter import get_rate_limiter, shutdown_rate_limiter
from bot_v2.handlers.user_handlers import UserHandlers
from bot_v2.handlers.admin_handlers import AdminHandlers
from bot_v2.handlers.payment_handlers import PaymentHandlers
from bot_v2.utils.logging_config import setup_logging
from bot_v2.utils.health_monitor import HealthMonitor
from bot_v2.utils.performance_monitor import PerformanceMonitor
from bot_v2.utils.error_handler import ErrorHandler
from bot_v2.utils.security_manager import SecurityManager

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

class PottagrmBot:
    """Main bot class with enhanced features"""
    
    def __init__(self):
        self.application: Optional[Application] = None
        self.database_manager = None
        self.rate_limiter = None
        self.health_monitor = None
        self.performance_monitor = None
        self.error_handler = None
        self.security_manager = None
        self.user_handlers = None
        self.admin_handlers = None
        self.payment_handlers = None
        self.shutdown_event = asyncio.Event()
        
        # Performance tracking
        self.start_time = time.time()
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        
        # Signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    async def initialize(self):
        """Initialize all bot components"""
        try:
            logger.info("🚀 Initializing Pottagrm Enhanced Bot v2.0...")
            
            # Initialize database
            logger.info("📊 Initializing database...")
            self.database_manager = get_database_manager()
            
            # Initialize rate limiter
            logger.info("🛡️ Initializing rate limiter...")
            self.rate_limiter = get_rate_limiter()
            
            # Initialize security manager
            logger.info("🔒 Initializing security manager...")
            self.security_manager = SecurityManager()
            
            # Initialize error handler
            logger.info("⚠️ Initializing error handler...")
            self.error_handler = ErrorHandler()
            
            # Initialize health monitor
            logger.info("💚 Initializing health monitor...")
            self.health_monitor = HealthMonitor()
            
            # Initialize performance monitor
            logger.info("📈 Initializing performance monitor...")
            self.performance_monitor = PerformanceMonitor()
            
            # Initialize handlers
            logger.info("🎯 Initializing handlers...")
            self.user_handlers = UserHandlers(self.database_manager, self.rate_limiter)
            self.admin_handlers = AdminHandlers(self.database_manager, self.rate_limiter)
            self.payment_handlers = PaymentHandlers(self.database_manager, self.rate_limiter)
            
            # Initialize Telegram application
            logger.info("📱 Initializing Telegram application...")
            self.application = Application.builder().token(BOT_TOKEN).build()
            
            # Setup handlers
            await self._setup_handlers()
            
            # Setup commands
            await self._setup_commands()
            
            # Start monitoring
            await self._start_monitoring()
            
            logger.info("✅ Bot initialization completed successfully!")
            
        except Exception as e:
            logger.error(f"❌ Bot initialization failed: {e}")
            await self.shutdown()
            raise
    
    async def _setup_handlers(self):
        """Setup all bot handlers"""
        try:
            # Command handlers
            self.application.add_handler(CommandHandler("start", self._rate_limited_handler(self.user_handlers.start_command)))
            self.application.add_handler(CommandHandler("help", self._rate_limited_handler(self.user_handlers.help_command)))
            self.application.add_handler(CommandHandler("wallet", self._rate_limited_handler(self.user_handlers.wallet_command)))
            self.application.add_handler(CommandHandler("profile", self._rate_limited_handler(self.user_handlers.profile_command)))
            self.application.add_handler(CommandHandler("admin", self._rate_limited_handler(self.admin_handlers.admin_command)))
            self.application.add_handler(CommandHandler("status", self._rate_limited_handler(self.user_handlers.status_command)))
            
            # Message handlers
            self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._rate_limited_handler(self.user_handlers.handle_text_message)))
            
            # Callback query handlers
            self.application.add_handler(CallbackQueryHandler(self._rate_limited_handler(self._handle_callback_query)))
            
            # Error handler
            self.application.add_error_handler(self._handle_error)
            
            logger.info("✅ Handlers setup completed")
            
        except Exception as e:
            logger.error(f"❌ Handler setup failed: {e}")
            raise
    
    async def _setup_commands(self):
        """Setup bot commands"""
        try:
            commands = [
                BotCommand("start", "بدء البوت"),
                BotCommand("help", "المساعدة"),
                BotCommand("wallet", "المحفظة"),
                BotCommand("profile", "الملف الشخصي"),
                BotCommand("admin", "لوحة الإدارة"),
                BotCommand("status", "حالة الحساب")
            ]
            
            await self.application.bot.set_my_commands(commands)
            logger.info("✅ Bot commands setup completed")
            
        except Exception as e:
            logger.error(f"❌ Command setup failed: {e}")
            raise
    
    async def _start_monitoring(self):
        """Start monitoring services"""
        try:
            # Start health monitoring
            asyncio.create_task(self.health_monitor.start())
            
            # Start performance monitoring
            asyncio.create_task(self.performance_monitor.start())
            
            logger.info("✅ Monitoring services started")
            
        except Exception as e:
            logger.error(f"❌ Monitoring startup failed: {e}")
            raise
    
    def _rate_limited_handler(self, handler_func):
        """Decorator to add rate limiting to handlers"""
        async def wrapper(update: Update, context: CallbackContext):
            try:
                # Get user info
                user_id = update.effective_user.id if update.effective_user else None
                ip_address = self._get_client_ip(context)
                
                # Check rate limit
                is_allowed, rate_info = self.rate_limiter.is_allowed(
                    user_id=user_id,
                    ip_address=ip_address,
                    endpoint=f"{handler_func.__name__}"
                )
                
                if not is_allowed:
                    await self._send_rate_limit_message(update, rate_info)
                    return
                
                # Record request
                self.rate_limiter.record_request(
                    user_id=user_id,
                    ip_address=ip_address,
                    endpoint=f"{handler_func.__name__}"
                )
                
                # Track performance
                start_time = time.time()
                self.total_requests += 1
                
                try:
                    # Execute handler
                    result = await handler_func(update, context)
                    self.successful_requests += 1
                    
                    # Record performance
                    execution_time = time.time() - start_time
                    self.performance_monitor.record_request(
                        handler=handler_func.__name__,
                        execution_time=execution_time,
                        success=True
                    )
                    
                    return result
                    
                except Exception as e:
                    self.failed_requests += 1
                    
                    # Record performance
                    execution_time = time.time() - start_time
                    self.performance_monitor.record_request(
                        handler=handler_func.__name__,
                        execution_time=execution_time,
                        success=False
                    )
                    
                    # Handle error
                    await self.error_handler.handle_error(update, context, e)
                    raise
                
            except Exception as e:
                logger.error(f"Handler execution failed: {e}")
                await self.error_handler.handle_error(update, context, e)
        
        return wrapper
    
    async def _handle_callback_query(self, update: Update, context: CallbackContext):
        """Handle callback queries with routing"""
        try:
            query = update.callback_query
            await query.answer()
            
            callback_data = query.data
            
            # Route to appropriate handler based on callback data
            if callback_data.startswith('user_'):
                return await self.user_handlers.handle_callback(update, context)
            elif callback_data.startswith('admin_'):
                return await self.admin_handlers.handle_callback(update, context)
            elif callback_data.startswith('payment_'):
                return await self.payment_handlers.handle_callback(update, context)
            else:
                # Default to user handler
                return await self.user_handlers.handle_callback(update, context)
                
        except Exception as e:
            logger.error(f"Callback query handling failed: {e}")
            await self.error_handler.handle_error(update, context, e)
    
    async def _handle_error(self, update: Update, context: CallbackContext):
        """Global error handler"""
        try:
            await self.error_handler.handle_error(update, context, sys.exc_info())
        except Exception as e:
            logger.error(f"Error in global error handler: {e}")
    
    async def _send_rate_limit_message(self, update: Update, rate_info: Dict[str, Any]):
        """Send rate limit exceeded message"""
        try:
            if update.message:
                await update.message.reply_text(
                    f"⚠️ تم تجاوز حد الطلبات المسموح\n"
                    f"يرجى الانتظار {rate_info.get('remaining_block', 0):.0f} ثانية"
                )
            elif update.callback_query:
                await update.callback_query.answer(
                    f"⚠️ تم تجاوز حد الطلبات المسموح",
                    show_alert=True
                )
        except Exception as e:
            logger.error(f"Failed to send rate limit message: {e}")
    
    def _get_client_ip(self, context: CallbackContext) -> Optional[str]:
        """Get client IP address"""
        try:
            # This would need to be implemented based on your deployment
            # For now, return None
            return None
        except Exception:
            return None
    
    async def start(self):
        """Start the bot"""
        try:
            logger.info("🚀 Starting bot...")
            
            # Start the application
            await self.application.initialize()
            await self.application.start()
            await self.application.updater.start_polling()
            
            logger.info("✅ Bot started successfully!")
            logger.info(f"🤖 Bot username: @{self.application.bot.username}")
            logger.info(f"📊 Database: {self.database_manager.db_path}")
            logger.info(f"🛡️ Rate limiting: {self.rate_limiter.config.max_requests} requests per {self.rate_limiter.config.window}s")
            
            # Keep running until shutdown
            await self.shutdown_event.wait()
            
        except Exception as e:
            logger.error(f"❌ Bot startup failed: {e}")
            await self.shutdown()
            raise
    
    async def shutdown(self):
        """Shutdown the bot gracefully"""
        try:
            logger.info("🛑 Shutting down bot...")
            
            # Stop monitoring
            if self.health_monitor:
                await self.health_monitor.stop()
            
            if self.performance_monitor:
                await self.performance_monitor.stop()
            
            # Stop application
            if self.application:
                await self.application.updater.stop()
                await self.application.stop()
                await self.application.shutdown()
            
            # Close services
            if self.rate_limiter:
                shutdown_rate_limiter()
            
            if self.database_manager:
                close_database_manager()
            
            logger.info("✅ Bot shutdown completed")
            
        except Exception as e:
            logger.error(f"❌ Bot shutdown failed: {e}")
        finally:
            # Force exit
            sys.exit(0)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"📡 Received signal {signum}, initiating shutdown...")
        asyncio.create_task(self.shutdown())
    
    def get_status(self) -> Dict[str, Any]:
        """Get bot status information"""
        uptime = time.time() - self.start_time
        
        return {
            'status': 'running' if not self.shutdown_event.is_set() else 'shutting_down',
            'uptime_seconds': uptime,
            'uptime_formatted': self._format_uptime(uptime),
            'total_requests': self.total_requests,
            'successful_requests': self.successful_requests,
            'failed_requests': self.failed_requests,
            'success_rate': (self.successful_requests / max(self.total_requests, 1)) * 100,
            'database_status': self.database_manager.get_database_stats() if self.database_manager else None,
            'rate_limiter_status': self.rate_limiter.get_statistics() if self.rate_limiter else None,
            'health_status': self.health_monitor.get_status() if self.health_monitor else None,
            'performance_status': self.performance_monitor.get_status() if self.performance_monitor else None
        }
    
    def _format_uptime(self, seconds: float) -> str:
        """Format uptime in human readable format"""
        days = int(seconds // 86400)
        hours = int((seconds % 86400) // 3600)
        minutes = int((seconds % 3600) // 60)
        seconds = int(seconds % 60)
        
        if days > 0:
            return f"{days}d {hours}h {minutes}m {seconds}s"
        elif hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"

async def main():
    """Main entry point"""
    bot = PottagrmBot()
    
    try:
        # Initialize bot
        await bot.initialize()
        
        # Start bot
        await bot.start()
        
    except KeyboardInterrupt:
        logger.info("📱 Keyboard interrupt received")
    except Exception as e:
        logger.error(f"❌ Bot execution failed: {e}")
        raise
    finally:
        await bot.shutdown()

if __name__ == "__main__":
    try:
        # Run the bot
        asyncio.run(main())
    except Exception as e:
        logger.error(f"❌ Bot execution failed: {e}")
        sys.exit(1)