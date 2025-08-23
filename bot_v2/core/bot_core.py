"""
Main bot core for Yemen Net Bot v2
"""

import asyncio
import logging
import signal
import sys
from typing import Optional, Dict, Any
from telegram import Update, Bot
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ConversationHandler, filters, CallbackContext
)
from .exceptions import *
from .rate_limiter import ActionRateLimiter
from .cache_manager import cache_manager
from .database_manager import db_manager
from .error_handler import error_handler
from .security import security_manager

logger = logging.getLogger(__name__)

class YemenNetBot:
    """Enhanced Yemen Net Bot with modern architecture"""
    
    def __init__(self, token: str, db_path: str = "yemen_net.db"):
        """
        Initialize bot
        
        Args:
            token: Telegram bot token
            db_path: Database file path
        """
        self.token = token
        self.db_path = db_path
        self.application: Optional[Application] = None
        self.bot: Optional[Bot] = None
        
        # Core systems
        self.rate_limiter = ActionRateLimiter()
        self.error_handler = error_handler
        
        # Bot state
        self.is_running = False
        self.startup_time = None
        
        # Performance monitoring
        self.stats = {
            "messages_processed": 0,
            "commands_processed": 0,
            "callback_queries_processed": 0,
            "errors_handled": 0,
            "startup_time": None
        }
        
        # Setup signal handlers
        self._setup_signal_handlers()
    
    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, shutting down gracefully...")
            asyncio.create_task(self.shutdown())
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    async def initialize(self):
        """Initialize bot systems"""
        try:
            logger.info("Initializing Yemen Net Bot v2...")
            
            # Initialize database
            await db_manager.initialize()
            logger.info("Database initialized")
            
            # Initialize cache manager
            await cache_manager.start_cleanup()
            logger.info("Cache manager initialized")
            
            # Initialize rate limiter
            await self.rate_limiter.start_all()
            logger.info("Rate limiter initialized")
            
            # Initialize security manager
            # Security manager is already initialized in __init__
            logger.info("Security manager initialized")
            
            # Create application
            self.application = Application.builder().token(self.token).build()
            self.bot = self.application.bot
            
            # Setup handlers
            await self._setup_handlers()
            logger.info("Handlers setup completed")
            
            # Setup error handler
            self.application.add_error_handler(self._error_handler)
            logger.info("Error handler setup completed")
            
            logger.info("Bot initialization completed successfully")
            
        except Exception as e:
            logger.error(f"Bot initialization failed: {e}")
            raise ConfigurationError(f"Bot initialization failed: {e}")
    
    async def _setup_handlers(self):
        """Setup bot handlers"""
        # Import handlers here to avoid circular imports
        from ..handlers.user_handlers import setup_user_handlers
        from ..handlers.admin_handlers import setup_admin_handlers
        from ..handlers.payment_handlers import setup_payment_handlers
        
        # Setup different handler categories
        await setup_user_handlers(self.application)
        await setup_admin_handlers(self.application)
        await setup_payment_handlers(self.application)
        
        # Setup core handlers
        self._setup_core_handlers()
    
    def _setup_core_handlers(self):
        """Setup core bot handlers"""
        # Start command
        start_handler = CommandHandler("start", self._start_command)
        self.application.add_handler(start_handler)
        
        # Help command
        help_handler = CommandHandler("help", self._help_command)
        self.application.add_handler(help_handler)
        
        # Status command
        status_handler = CommandHandler("status", self._status_command)
        self.application.add_handler(status_handler)
        
        # Unknown command handler
        unknown_handler = MessageHandler(filters.COMMAND, self._unknown_command)
        self.application.add_handler(unknown_handler)
        
        # Unknown message handler
        unknown_message_handler = MessageHandler(filters.TEXT & ~filters.COMMAND, self._unknown_message)
        self.application.add_handler(unknown_message_handler)
    
    async def _start_command(self, update: Update, context: CallbackContext):
        """Handle /start command"""
        try:
            user = update.effective_user
            chat_id = update.effective_chat.id
            
            welcome_message = f"""
🎉 مرحباً {user.first_name}!

مرحباً بك في بوت شبكة اليمن المحسن v2.0

🔹 هذا البوت يوفر لك:
• إدارة المحفظة الإلكترونية
• شراء وبيع البطاقات
• تتبع المعاملات
• التقارير والإحصائيات
• نظام العمولات للموظفين

🔹 للبدء، استخدم القائمة الرئيسية أدناه
🔹 للمساعدة، اكتب /help
🔹 لمعرفة حالة النظام، اكتب /status

تم تطوير هذا البوت بأحدث التقنيات لضمان الأداء العالي والأمان التام.
            """
            
            # Create main menu keyboard
            from ..utils.keyboards import get_main_menu_keyboard
            keyboard = get_main_menu_keyboard(user.id)
            
            await context.bot.send_message(
                chat_id=chat_id,
                text=welcome_message.strip(),
                reply_markup=keyboard,
                parse_mode='HTML'
            )
            
            self.stats["commands_processed"] += 1
            
        except Exception as e:
            logger.error(f"Error in start command: {e}")
            await self.error_handler.handle_error(update, context, e)
    
    async def _help_command(self, update: Update, context: CallbackContext):
        """Handle /help command"""
        try:
            chat_id = update.effective_chat.id
            
            help_message = """
📚 دليل استخدام البوت

🔹 الأوامر الأساسية:
/start - بدء استخدام البوت
/help - عرض هذا الدليل
/status - حالة النظام

🔹 الميزات الرئيسية:
• المحفظة الإلكترونية
• شراء وبيع البطاقات
• تتبع المعاملات
• التقارير والإحصائيات
• نظام العمولات

🔹 للتواصل مع الدعم:
• راسل الإدارة عبر البوت
• أو اكتب رسالة وسيتم الرد عليك

🔹 نصائح للاستخدام:
• تأكد من صحة البيانات المدخلة
• احتفظ بنسخة من المعاملات المهمة
• استخدم القوائم للتنقل السريع
            """
            
            await context.bot.send_message(
                chat_id=chat_id,
                text=help_message.strip(),
                parse_mode='HTML'
            )
            
            self.stats["commands_processed"] += 1
            
        except Exception as e:
            logger.error(f"Error in help command: {e}")
            await self.error_handler.handle_error(update, context, e)
    
    async def _status_command(self, update: Update, context: CallbackContext):
        """Handle /status command"""
        try:
            chat_id = update.effective_chat.id
            
            # Get system status
            db_status = await db_manager.check_integrity()
            cache_stats = cache_manager.get_stats()
            db_stats = db_manager.get_stats()
            
            status_message = f"""
📊 حالة النظام

🟢 البوت: يعمل بشكل طبيعي
🟢 قاعدة البيانات: {'سليمة' if db_status['integrity'] else 'مشكلة'}
🟢 التخزين المؤقت: {cache_stats['size']}/{cache_stats['max_size']} عنصر
🟢 اتصالات قاعدة البيانات: {db_stats['pool_size']} متصل

📈 إحصائيات الأداء:
• الرسائل المعالجة: {self.stats['messages_processed']}
• الأوامر المعالجة: {self.stats['commands_processed']}
• الاستعلامات: {db_stats['queries_executed']}
• معدل نجاح التخزين المؤقت: {cache_stats['hit_rate']:.1%}

⏰ وقت التشغيل: {self.startup_time.strftime('%Y-%m-%d %H:%M:%S') if self.startup_time else 'غير محدد'}
            """
            
            await context.bot.send_message(
                chat_id=chat_id,
                text=status_message.strip(),
                parse_mode='HTML'
            )
            
            self.stats["commands_processed"] += 1
            
        except Exception as e:
            logger.error(f"Error in status command: {e}")
            await self.error_handler.handle_error(update, context, e)
    
    async def _unknown_command(self, update: Update, context: CallbackContext):
        """Handle unknown commands"""
        try:
            chat_id = update.effective_chat.id
            command = update.message.text
            
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"❌ الأمر '{command}' غير معروف.\n\nاستخدم /help لعرض الأوامر المتاحة.",
                parse_mode='HTML'
            )
            
            self.stats["commands_processed"] += 1
            
        except Exception as e:
            logger.error(f"Error in unknown command handler: {e}")
            await self.error_handler.handle_error(update, context, e)
    
    async def _unknown_message(self, update: Update, context: CallbackContext):
        """Handle unknown text messages"""
        try:
            chat_id = update.effective_chat.id
            
            await context.bot.send_message(
                chat_id=chat_id,
                text="💬 استخدم القوائم والأزرار للتنقل في البوت.\n\nللمساعدة، اكتب /help",
                parse_mode='HTML'
            )
            
            self.stats["messages_processed"] += 1
            
        except Exception as e:
            logger.error(f"Error in unknown message handler: {e}")
            await self.error_handler.handle_error(update, context, e)
    
    async def _error_handler(self, update: Update, context: CallbackContext):
        """Global error handler"""
        try:
            # Extract error from context
            error = context.error
            
            # Log error
            logger.error(f"Unhandled error: {error}")
            logger.error(f"Update: {update}")
            logger.error(f"Context: {context}")
            
            # Handle error
            await self.error_handler.handle_error(update, context, error)
            
            self.stats["errors_handled"] += 1
            
        except Exception as e:
            logger.error(f"Error in global error handler: {e}")
    
    async def start(self):
        """Start the bot"""
        try:
            if self.is_running:
                logger.warning("Bot is already running")
                return
            
            logger.info("Starting Yemen Net Bot v2...")
            
            # Initialize bot
            await self.initialize()
            
            # Start application
            await self.application.initialize()
            await self.application.start()
            await self.application.updater.start_polling()
            
            self.is_running = True
            self.startup_time = asyncio.get_event_loop().time()
            
            logger.info("Bot started successfully")
            logger.info(f"Bot username: @{self.bot.username}")
            logger.info(f"Bot ID: {self.bot.id}")
            
            # Keep bot running
            await self.application.updater.idle()
            
        except Exception as e:
            logger.error(f"Failed to start bot: {e}")
            raise BotError(f"Failed to start bot: {e}")
    
    async def stop(self):
        """Stop the bot"""
        try:
            if not self.is_running:
                logger.warning("Bot is not running")
                return
            
            logger.info("Stopping Yemen Net Bot v2...")
            
            # Stop application
            if self.application:
                await self.application.updater.stop()
                await self.application.stop()
                await self.application.shutdown()
            
            # Stop core systems
            await self.rate_limiter.stop_all()
            await cache_manager.stop_cleanup()
            await db_manager.cleanup()
            
            self.is_running = False
            
            logger.info("Bot stopped successfully")
            
        except Exception as e:
            logger.error(f"Error stopping bot: {e}")
            raise BotError(f"Error stopping bot: {e}")
    
    async def shutdown(self):
        """Graceful shutdown"""
        try:
            logger.info("Initiating graceful shutdown...")
            await self.stop()
            logger.info("Graceful shutdown completed")
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
        finally:
            # Force exit if needed
            sys.exit(0)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get bot statistics"""
        return {
            **self.stats,
            "is_running": self.is_running,
            "startup_time": self.startup_time,
            "database_stats": db_manager.get_stats(),
            "cache_stats": cache_manager.get_stats(),
            "rate_limiter_stats": {
                "active_limiters": len(self.rate_limiter.limiters)
            }
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check"""
        try:
            health_status = {
                "bot_status": "healthy" if self.is_running else "stopped",
                "database": await db_manager.check_integrity(),
                "cache": cache_manager.get_stats(),
                "rate_limiter": "healthy",
                "timestamp": asyncio.get_event_loop().time()
            }
            
            return health_status
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "bot_status": "error",
                "error": str(e),
                "timestamp": asyncio.get_event_loop().time()
            }

# Bot factory function
def create_bot(token: str, db_path: str = "yemen_net.db") -> YemenNetBot:
    """
    Create bot instance
    
    Args:
        token: Telegram bot token
        db_path: Database file path
        
    Returns:
        Bot instance
    """
    return YemenNetBot(token, db_path)