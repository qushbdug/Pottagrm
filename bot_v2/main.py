"""
Yemen Net Bot v2 - Main Entry Point
Enhanced architecture with proper error handling, monitoring, and performance optimization
"""

import asyncio
import logging
import signal
import sys
import time
from typing import Optional

from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ConversationHandler, filters
)

# Import core modules
from .core.config import config
from .core.exceptions import BotException, ConfigurationException

# Import services
from .services import db_manager, cache_manager, rate_limiter, monitoring_service

# Import handlers (will be created next)
# from .handlers import user_handlers, admin_handlers, payment_handlers

# Import conversation states
from .core.conversation_states import ConversationStates

class YemenNetBot:
    """Enhanced Yemen Net Bot with comprehensive error handling and monitoring"""
    
    def __init__(self):
        self.config = config
        self.logger = logging.getLogger('YemenNetBot')
        
        # Initialize application
        self.application: Optional[Application] = None
        
        # Bot state
        self.is_running = False
        self.start_time = None
        
        # Performance tracking
        self.message_count = 0
        self.error_count = 0
        
        # Initialize services
        self._initialize_services()
        
        # Setup signal handlers
        self._setup_signal_handlers()
        
        self.logger.info("Yemen Net Bot v2 initialized successfully")
    
    def _initialize_services(self):
        """Initialize all services"""
        try:
            # Verify database connection
            db_stats = db_manager.get_database_stats()
            if not db_stats:
                raise ConfigurationException("Database initialization failed")
            
            self.logger.info("Database service initialized successfully")
            
            # Verify cache service
            cache_stats = cache_manager.get_stats()
            self.logger.info(f"Cache service initialized: {cache_stats['total_items']} items")
            
            # Verify rate limiter
            rate_limit_stats = rate_limiter.get_global_stats()
            self.logger.info("Rate limiter service initialized successfully")
            
            # Verify monitoring service
            monitoring_status = monitoring_service.get_health_status()
            self.logger.info("Monitoring service initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Service initialization failed: {e}")
            raise ConfigurationException(f"Service initialization failed: {e}")
    
    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        def signal_handler(signum, frame):
            self.logger.info(f"Received signal {signum}, initiating shutdown...")
            self.shutdown()
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    def _setup_handlers(self):
        """Setup all bot handlers"""
        try:
            # Import handlers here to avoid circular imports
            from .handlers.user_handlers import setup_user_handlers
            from .handlers.admin_handlers import setup_admin_handlers
            from .handlers.payment_handlers import setup_payment_handlers
            
            # Setup user handlers
            user_handlers = setup_user_handlers()
            for handler in user_handlers:
                self.application.add_handler(handler)
            
            # Setup admin handlers
            admin_handlers = setup_admin_handlers()
            for handler in admin_handlers:
                self.application.add_handler(handler)
            
            # Setup payment handlers
            payment_handlers = setup_payment_handlers()
            for handler in payment_handlers:
                self.application.add_handler(handler)
            
            # Setup conversation handler
            self._setup_conversation_handler()
            
            # Setup error handler
            self.application.add_error_handler(self._error_handler)
            
            self.logger.info("All handlers setup successfully")
            
        except Exception as e:
            self.logger.error(f"Handler setup failed: {e}")
            raise ConfigurationException(f"Handler setup failed: {e}")
    
    def _setup_conversation_handler(self):
        """Setup conversation handler for multi-step interactions"""
        try:
            # Import conversation states
            from .core.conversation_states import ConversationStates
            
            # Create conversation handler
            conv_handler = ConversationHandler(
                entry_points=[
                    CommandHandler('start', self._start_command),
                    CommandHandler('help', self._help_command),
                    CommandHandler('profile', self._profile_command),
                    CommandHandler('wallet', self._wallet_command),
                    CommandHandler('settings', self._settings_command),
                    CommandHandler('support', self._support_command)
                ],
                states={
                    ConversationStates.PROFILE_EDIT: [
                        MessageHandler(filters.TEXT & ~filters.COMMAND, self._profile_edit_handler)
                    ],
                    ConversationStates.TRANSFER_AMOUNT: [
                        MessageHandler(filters.TEXT & ~filters.COMMAND, self._transfer_amount_handler)
                    ],
                    ConversationStates.TRANSFER_CONFIRM: [
                        CallbackQueryHandler(self._transfer_confirm_handler)
                    ],
                    ConversationStates.CARD_UPLOAD: [
                        MessageHandler(filters.Document.ALL, self._card_upload_handler)
                    ]
                },
                fallbacks=[
                    CommandHandler('cancel', self._cancel_command),
                    CommandHandler('start', self._start_command)
                ]
            )
            
            self.application.add_handler(conv_handler)
            self.logger.info("Conversation handler setup successfully")
            
        except Exception as e:
            self.logger.error(f"Conversation handler setup failed: {e}")
            raise ConfigurationException(f"Conversation handler setup failed: {e}")
    
    async def _start_command(self, update: Update, context):
        """Handle /start command"""
        try:
            start_time = time.time()
            
            # Record metrics
            monitoring_service.increment_metric('bot_commands_executed')
            monitoring_service.increment_metric('bot_messages_processed')
            
            # Get user info
            user = update.effective_user
            user_id = user.id
            
            # Check rate limit
            is_limited, reason, retry_after = rate_limiter.is_rate_limited(user_id, 'user_commands')
            if is_limited:
                await update.message.reply_text(
                    f"⚠️ تم تجاوز حد الطلبات. يرجى المحاولة بعد {retry_after} ثانية."
                )
                return ConversationStates.END
            
            # Record request
            rate_limiter.record_request(user_id, 'user_commands')
            
            # Check if user exists in database
            db_user = db_manager.get_user_by_telegram_id(user_id)
            if not db_user:
                # Create new user
                db_user_id = db_manager.create_user(user_id, user.full_name, user.username)
                welcome_message = (
                    f"🎉 مرحباً {user.first_name}!\n\n"
                    "مرحباً بك في بوت شبكة اليمن\n"
                    "البوت الذي يوفر لك جميع الخدمات المالية والدفع\n\n"
                    "📱 استخدم الأزرار أدناه للتنقل بين الخدمات"
                )
            else:
                # Update user activity
                db_manager.update_user_activity(db_user['id'])
                welcome_message = (
                    f"مرحباً {user.first_name}! 👋\n\n"
                    "مرحباً بعودتك إلى بوت شبكة اليمن\n"
                    "كيف يمكنني مساعدتك اليوم؟"
                )
            
            # Create main menu keyboard
            from .utils.keyboards import get_main_menu_keyboard
            keyboard = get_main_menu_keyboard()
            
            # Send welcome message
            await update.message.reply_text(welcome_message, reply_markup=keyboard)
            
            # Record response time
            response_time = (time.time() - start_time) * 1000
            monitoring_service.record_metric('bot_response_time', response_time)
            
            return ConversationStates.MAIN_MENU
            
        except Exception as e:
            self.logger.error(f"Error in start command: {e}")
            monitoring_service.increment_metric('bot_errors')
            await update.message.reply_text("❌ حدث خطأ أثناء بدء البوت. يرجى المحاولة مرة أخرى.")
            return ConversationStates.END
    
    async def _help_command(self, update: Update, context):
        """Handle /help command"""
        try:
            help_text = (
                "🔧 **مساعدة البوت**\n\n"
                "**الأوامر الأساسية:**\n"
                "/start - بدء استخدام البوت\n"
                "/help - عرض هذه الرسالة\n"
                "/profile - عرض الملف الشخصي\n"
                "/wallet - عرض المحفظة\n"
                "/settings - الإعدادات\n"
                "/support - الدعم الفني\n\n"
                "**للحصول على مساعدة إضافية:**\n"
                "تواصل مع فريق الدعم عبر @yemen_net_support"
            )
            
            await update.message.reply_text(help_text, parse_mode='Markdown')
            monitoring_service.increment_metric('bot_commands_executed')
            
        except Exception as e:
            self.logger.error(f"Error in help command: {e}")
            monitoring_service.increment_metric('bot_errors')
            await update.message.reply_text("❌ حدث خطأ أثناء عرض المساعدة.")
    
    async def _profile_command(self, update: Update, context):
        """Handle /profile command"""
        try:
            user = update.effective_user
            db_user = db_manager.get_user_by_telegram_id(user.id)
            
            if not db_user:
                await update.message.reply_text("❌ يرجى التسجيل أولاً باستخدام /start")
                return
            
            # Get profile info
            profile_text = (
                f"👤 **الملف الشخصي**\n\n"
                f"**الاسم:** {db_user['full_name']}\n"
                f"**اسم المستخدم:** @{user.username or 'غير محدد'}\n"
                f"**الدور:** {db_user['role']}\n"
                f"**الرصيد:** {db_user['balance']:.2f} ريال\n"
                f"**تاريخ التسجيل:** {db_user['created_at']}\n"
                f"**آخر نشاط:** {db_user['last_activity']}"
            )
            
            # Create profile keyboard
            from .utils.keyboards import get_profile_keyboard
            keyboard = get_profile_keyboard()
            
            await update.message.reply_text(profile_text, reply_markup=keyboard, parse_mode='Markdown')
            monitoring_service.increment_metric('bot_commands_executed')
            
        except Exception as e:
            self.logger.error(f"Error in profile command: {e}")
            monitoring_service.increment_metric('bot_errors')
            await update.message.reply_text("❌ حدث خطأ أثناء عرض الملف الشخصي.")
    
    async def _wallet_command(self, update: Update, context):
        """Handle /wallet command"""
        try:
            user = update.effective_user
            db_user = db_manager.get_user_by_telegram_id(user.id)
            
            if not db_user:
                await update.message.reply_text("❌ يرجى التسجيل أولاً باستخدام /start")
                return
            
            # Get wallet info
            balance = db_manager.get_user_balance(db_user['id'])
            transactions = db_manager.get_user_transactions(db_user['id'], limit=5)
            
            wallet_text = (
                f"👛 **المحفظة**\n\n"
                f"**الرصيد الحالي:** {balance:.2f} ريال\n"
                f"**آخر المعاملات:**\n"
            )
            
            if transactions:
                for tx in transactions[:3]:
                    tx_type = "➕" if tx['type'] == 'credit' else "➖"
                    amount = float(tx['amount']) if tx['amount'] else 0.0
                    wallet_text += f"{tx_type} {amount:.2f} ريال - {tx['description'] or 'معاملة'}\n"
            else:
                wallet_text += "لا توجد معاملات حديثة\n"
            
            # Create wallet keyboard
            from .utils.keyboards import get_wallet_keyboard
            keyboard = get_wallet_keyboard()
            
            await update.message.reply_text(wallet_text, reply_markup=keyboard, parse_mode='Markdown')
            monitoring_service.increment_metric('bot_commands_executed')
            
        except Exception as e:
            self.logger.error(f"Error in wallet command: {e}")
            monitoring_service.increment_metric('bot_errors')
            await update.message.reply_text("❌ حدث خطأ أثناء عرض المحفظة.")
    
    async def _settings_command(self, update: Update, context):
        """Handle /settings command"""
        try:
            settings_text = (
                "⚙️ **الإعدادات**\n\n"
                "**الإشعارات:** ✅ مفعلة\n"
                "**اللغة:** العربية\n"
                "**المنطقة الزمنية:** GMT+3\n"
                "**وضع التطوير:** ❌ معطل\n\n"
                "استخدم الأزرار أدناه لتغيير الإعدادات"
            )
            
            # Create settings keyboard
            from .utils.keyboards import get_settings_keyboard
            keyboard = get_settings_keyboard()
            
            await update.message.reply_text(settings_text, reply_markup=keyboard, parse_mode='Markdown')
            monitoring_service.increment_metric('bot_commands_executed')
            
        except Exception as e:
            self.logger.error(f"Error in settings command: {e}")
            monitoring_service.increment_metric('bot_errors')
            await update.message.reply_text("❌ حدث خطأ أثناء عرض الإعدادات.")
    
    async def _support_command(self, update: Update, context):
        """Handle /support command"""
        try:
            support_text = (
                "🆘 **الدعم الفني**\n\n"
                "**للحصول على المساعدة:**\n"
                "📧 البريد الإلكتروني: support@yemen-net.com\n"
                "📱 تليجرام: @yemen_net_support\n"
                "🌐 الموقع: www.yemen-net.com\n\n"
                "**أوقات العمل:**\n"
                "الأحد - الخميس: 8:00 ص - 6:00 م\n"
                "الجمعة - السبت: 10:00 ص - 4:00 م\n\n"
                "**للحالات الطارئة:**\n"
                "اتصل على: +967-1-123456"
            )
            
            await update.message.reply_text(support_text, parse_mode='Markdown')
            monitoring_service.increment_metric('bot_commands_executed')
            
        except Exception as e:
            self.logger.error(f"Error in support command: {e}")
            monitoring_service.increment_metric('bot_errors')
            await update.message.reply_text("❌ حدث خطأ أثناء عرض معلومات الدعم.")
    
    async def _cancel_command(self, update: Update, context):
        """Handle /cancel command"""
        await update.message.reply_text("❌ تم إلغاء العملية.")
        return ConversationStates.END
    
    async def _profile_edit_handler(self, update: Update, context):
        """Handle profile editing"""
        # Placeholder for profile editing logic
        await update.message.reply_text("📝 تم تحديث الملف الشخصي.")
        return ConversationStates.MAIN_MENU
    
    async def _transfer_amount_handler(self, update: Update, context):
        """Handle transfer amount input"""
        # Placeholder for transfer amount logic
        await update.message.reply_text("💰 تم تحديد مبلغ التحويل.")
        return ConversationStates.TRANSFER_CONFIRM
    
    async def _transfer_confirm_handler(self, update: Update, context):
        """Handle transfer confirmation"""
        # Placeholder for transfer confirmation logic
        await update.callback_query.answer("✅ تم تأكيد التحويل.")
        return ConversationStates.MAIN_MENU
    
    async def _card_upload_handler(self, update: Update, context):
        """Handle card upload"""
        # Placeholder for card upload logic
        await update.message.reply_text("💳 تم رفع البطاقة بنجاح.")
        return ConversationStates.MAIN_MENU
    
    async def _error_handler(self, update: Update, context):
        """Handle errors in bot operations"""
        try:
            self.logger.error(f"Exception while handling an update: {context.error}")
            monitoring_service.increment_metric('bot_errors')
            
            # Send user-friendly error message
            if update and update.effective_message:
                await update.effective_message.reply_text(
                    "❌ حدث خطأ أثناء معالجة طلبك. يرجى المحاولة مرة أخرى لاحقاً."
                )
            
        except Exception as e:
            self.logger.error(f"Error in error handler: {e}")
    
    async def start(self):
        """Start the bot"""
        try:
            self.logger.info("Starting Yemen Net Bot v2...")
            
            # Create application
            self.application = Application.builder().token(self.config.BOT_TOKEN).build()
            
            # Setup handlers
            self._setup_handlers()
            
            # Start application
            await self.application.initialize()
            await self.application.start()
            await self.application.updater.start_polling()
            
            # Update bot state
            self.is_running = True
            self.start_time = time.time()
            
            # Record startup metrics
            monitoring_service.record_metric('bot_startup_time', time.time())
            monitoring_service.record_metric('bot_status', 1)  # 1 = running
            
            self.logger.info("Yemen Net Bot v2 started successfully")
            
            # Keep bot running
            while self.is_running:
                await asyncio.sleep(1)
                
        except Exception as e:
            self.logger.error(f"Failed to start bot: {e}")
            monitoring_service.record_metric('bot_status', 0)  # 0 = stopped
            raise BotException(f"Bot startup failed: {e}")
    
    async def stop(self):
        """Stop the bot"""
        try:
            self.logger.info("Stopping Yemen Net Bot v2...")
            
            # Update bot state
            self.is_running = False
            
            # Stop application
            if self.application:
                await self.application.updater.stop()
                await self.application.stop()
                await self.application.shutdown()
            
            # Record shutdown metrics
            if self.start_time:
                uptime = time.time() - self.start_time
                monitoring_service.record_metric('bot_uptime', uptime)
            monitoring_service.record_metric('bot_status', 0)  # 0 = stopped
            
            self.logger.info("Yemen Net Bot v2 stopped successfully")
            
        except Exception as e:
            self.logger.error(f"Error stopping bot: {e}")
    
    def shutdown(self):
        """Shutdown the bot and all services"""
        try:
            self.logger.info("Shutting down Yemen Net Bot v2...")
            
            # Stop bot
            if self.is_running:
                asyncio.create_task(self.stop())
            
            # Stop services
            monitoring_service.stop()
            db_manager.close()
            
            self.logger.info("Shutdown completed")
            
            # Exit
            sys.exit(0)
            
        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}")
            sys.exit(1)

async def main():
    """Main entry point"""
    try:
        # Create and start bot
        bot = YemenNetBot()
        await bot.start()
        
    except KeyboardInterrupt:
        logging.info("Received keyboard interrupt, shutting down...")
    except Exception as e:
        logging.error(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # Run the bot
    asyncio.run(main())