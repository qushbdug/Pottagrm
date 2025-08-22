#!/usr/bin/env python3
"""
Yemen Net Bot v2 - Enhanced Version
Main entry point with improved architecture and error handling
"""

import asyncio
import logging
import signal
import sys
import time
from pathlib import Path
from typing import Optional

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from telegram import Update, Bot
from telegram.ext import (
    Application, 
    CommandHandler, 
    MessageHandler, 
    CallbackQueryHandler,
    ConversationHandler,
    filters,
    ContextTypes
)

# Import our modules
from core.config import config, EMOJIS
from core.exceptions import BotException, DatabaseException, ConfigurationException
from services import (
    db_manager, 
    rate_limiter, 
    cache_manager, 
    notification_manager
)

# Configure logging
logging.basicConfig(
    level=getattr(logging, config.bot.log_level.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(config.bot.log_file, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

class YemenNetBot:
    """Enhanced Yemen Net Bot with improved architecture"""
    
    def __init__(self):
        self.application: Optional[Application] = None
        self.bot: Optional[Bot] = None
        self.is_running = False
        self.start_time = None
        
        # Validate configuration
        self._validate_config()
        
        # Initialize services
        self._init_services()
    
    def _validate_config(self):
        """Validate bot configuration"""
        try:
            errors = config.validate()
            if errors:
                error_msg = "Configuration validation failed:\n" + "\n".join(f"  - {error}" for error in errors)
                raise ConfigurationException(error_msg)
            
            logger.info("Configuration validated successfully")
            
        except Exception as e:
            logger.error(f"Configuration validation failed: {e}")
            raise ConfigurationException(f"Configuration error: {e}")
    
    def _init_services(self):
        """Initialize all services"""
        try:
            logger.info("Initializing services...")
            
            # Check database health
            db_health = db_manager.health_check()
            if db_health['status'] != 'healthy':
                logger.warning(f"Database health check: {db_health}")
            else:
                logger.info("Database health check passed")
            
            # Initialize cache
            cache_stats = cache_manager.get_stats()
            logger.info(f"Cache initialized: {cache_stats['entries_count']} entries")
            
            # Initialize rate limiter
            rate_stats = rate_limiter.get_system_stats()
            logger.info(f"Rate limiter initialized: {rate_stats['total_users']} users tracked")
            
            # Initialize notification manager
            notif_stats = notification_manager.get_stats()
            logger.info(f"Notification manager initialized: {notif_stats['templates_count']} templates")
            
            logger.info("All services initialized successfully")
            
        except Exception as e:
            logger.error(f"Service initialization failed: {e}")
            raise BotException(f"Service initialization error: {e}")
    
    async def start(self):
        """Start the bot"""
        try:
            logger.info("Starting Yemen Net Bot v2...")
            
            # Create application
            self.application = Application.builder().token(config.bot.token).build()
            self.bot = self.application.bot
            
            # Add handlers
            self._add_handlers()
            
            # Add error handler
            self.application.add_error_handler(self._error_handler)
            
            # Start the bot
            await self.application.initialize()
            await self.application.start()
            await self.application.updater.start_polling()
            
            self.is_running = True
            self.start_time = time.time()
            
            logger.info("Bot started successfully")
            
            # Send startup notification to admins
            await self._send_startup_notification()
            
        except Exception as e:
            logger.error(f"Failed to start bot: {e}")
            raise BotException(f"Bot startup failed: {e}")
    
    def _add_handlers(self):
        """Add all message and callback handlers"""
        try:
            # Basic command handlers
            self.application.add_handler(CommandHandler("start", self._start_command))
            self.application.add_handler(CommandHandler("help", self._help_command))
            self.application.add_handler(CommandHandler("status", self._status_command))
            self.application.add_handler(CommandHandler("admin", self._admin_command))
            
            # Message handlers
            self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_message))
            
            # Callback query handlers
            self.application.add_handler(CallbackQueryHandler(self._handle_callback))
            
            logger.info("All handlers added successfully")
            
        except Exception as e:
            logger.error(f"Failed to add handlers: {e}")
            raise BotException(f"Handler setup failed: {e}")
    
    async def _start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        try:
            user = update.effective_user
            user_id = user.id
            
            # Check rate limit
            try:
                await rate_limiter.check_rate_limit(user_id, "start_command")
            except Exception as e:
                await update.message.reply_text(
                    f"{EMOJIS['warning']} يرجى الانتظار قليلاً قبل إرسال طلب آخر."
                )
                return
            
            # Welcome message
            welcome_text = f"""
{EMOJIS['party']} مرحباً بك في بوت يمن نت! {EMOJIS['party']}

مرحباً {user.first_name}! أهلاً وسهلاً بك في البوت الأفضل لإدارة البطاقات والمدفوعات.

{EMOJIS['info']} يمكنك استخدام الأوامر التالية:
/help - عرض المساعدة
/status - حالة حسابك
/admin - لوحة الإدارة (للمديرين فقط)

{EMOJIS['star']} استمتع بتجربتك معنا!
            """.strip()
            
            await update.message.reply_text(welcome_text)
            
            # Send welcome notification
            await notification_manager.send_template_notification(
                'welcome',
                user_id,
                {'user_name': user.first_name}
            )
            
        except Exception as e:
            logger.error(f"Error in start command: {e}")
            await update.message.reply_text(
                f"{EMOJIS['error']} حدث خطأ أثناء بدء البوت. يرجى المحاولة مرة أخرى."
            )
    
    async def _help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        try:
            user = update.effective_user
            user_id = user.id
            
            # Check rate limit
            try:
                await rate_limiter.check_rate_limit(user_id, "help_command")
            except Exception as e:
                await update.message.reply_text(
                    f"{EMOJIS['warning']} يرجى الانتظار قليلاً قبل إرسال طلب آخر."
                )
                return
            
            help_text = f"""
{EMOJIS['info']} دليل استخدام بوت يمن نت {EMOJIS['info']}

{EMOJIS['check']} الأوامر الأساسية:
/start - بدء استخدام البوت
/help - عرض هذه المساعدة
/status - عرض حالة حسابك

{EMOJIS['check']} الميزات المتاحة:
{EMOJIS['wallet']} إدارة المحفظة والرصيد
{EMOJIS['card']} شراء وإدارة البطاقات
{EMOJIS['transfer']} تحويل الأموال
{EMOJIS['stats']} عرض الإحصائيات والتقارير
{EMOJIS['settings']} إعدادات الحساب

{EMOJIS['check']} للمديرين:
/admin - لوحة الإدارة
/analytics - التحليلات والإحصائيات

{EMOJIS['support']} للحصول على المساعدة:
تواصل مع فريق الدعم الفني
            """.strip()
            
            await update.message.reply_text(help_text)
            
        except Exception as e:
            logger.error(f"Error in help command: {e}")
            await update.message.reply_text(
                f"{EMOJIS['error']} حدث خطأ أثناء عرض المساعدة. يرجى المحاولة مرة أخرى."
            )
    
    async def _status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command"""
        try:
            user = update.effective_user
            user_id = user.id
            
            # Check rate limit
            try:
                await rate_limiter.check_rate_limit(user_id, "status_command")
            except Exception as e:
                await update.message.reply_text(
                    f"{EMOJIS['warning']} يرجى الانتظار قليلاً قبل إرسال طلب آخر."
                )
                return
            
            # Get user status from database
            try:
                user_data = await self._get_user_status(user_id)
                if user_data:
                    status_text = f"""
{EMOJIS['user']} حالة حسابك {EMOJIS['user']}

{EMOJIS['info']} المعلومات الأساسية:
الاسم: {user_data.get('full_name', 'غير محدد')}
الدور: {user_data.get('role', 'مستخدم')}
الحالة: {'نشط' if user_data.get('is_active') else 'غير نشط'}

{EMOJIS['wallet']} المحفظة:
الرصيد: {user_data.get('balance', 0):.2f} ريال
آخر نشاط: {user_data.get('last_activity', 'غير محدد')}

{EMOJIS['stats']} الإحصائيات:
عدد المعاملات: {user_data.get('transaction_count', 0)}
عدد البطاقات: {user_data.get('card_count', 0)}
                    """.strip()
                else:
                    status_text = f"{EMOJIS['warning']} لم يتم العثور على بيانات المستخدم."
                
                await update.message.reply_text(status_text)
                
            except Exception as e:
                logger.error(f"Error getting user status: {e}")
                await update.message.reply_text(
                    f"{EMOJIS['error']} حدث خطأ أثناء جلب حالة الحساب."
                )
            
        except Exception as e:
            logger.error(f"Error in status command: {e}")
            await update.message.reply_text(
                f"{EMOJIS['error']} حدث خطأ أثناء عرض الحالة. يرجى المحاولة مرة أخرى."
            )
    
    async def _admin_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /admin command"""
        try:
            user = update.effective_user
            user_id = user.id
            
            # Check if user is admin
            if not config.is_admin(user_id):
                await update.message.reply_text(
                    f"{EMOJIS['error']} عذراً، هذا الأمر متاح للمديرين فقط."
                )
                return
            
            # Check rate limit
            try:
                await rate_limiter.check_rate_limit(user_id, "admin_command")
            except Exception as e:
                await update.message.reply_text(
                    f"{EMOJIS['warning']} يرجى الانتظار قليلاً قبل إرسال طلب آخر."
                )
                return
            
            admin_text = f"""
{EMOJIS['admin']} لوحة الإدارة {EMOJIS['admin']}

مرحباً {user.first_name}! أنت تستخدم حساب المدير.

{EMOJIS['check']} الميزات المتاحة:
{EMOJIS['stats']} عرض إحصائيات النظام
{EMOJIS['user']} إدارة المستخدمين
{EMOJIS['settings']} إعدادات النظام
{EMOJIS['notification']} إرسال إشعارات

{EMOJIS['info']} استخدم الأزرار أدناه للوصول إلى الميزات المختلفة.
            """.strip()
            
            await update.message.reply_text(admin_text)
            
        except Exception as e:
            logger.error(f"Error in admin command: {e}")
            await update.message.reply_text(
                f"{EMOJIS['error']} حدث خطأ أثناء عرض لوحة الإدارة."
            )
    
    async def _handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text messages"""
        try:
            user = update.effective_user
            user_id = user.id
            message_text = update.message.text
            
            # Check rate limit
            try:
                await rate_limiter.check_rate_limit(user_id, "message")
            except Exception as e:
                await update.message.reply_text(
                    f"{EMOJIS['warning']} يرجى الانتظار قليلاً قبل إرسال رسالة أخرى."
                )
                return
            
            # Process message based on content
            if "مرحبا" in message_text or "أهلا" in message_text:
                await update.message.reply_text(
                    f"{EMOJIS['party']} أهلاً وسهلاً بك! كيف يمكنني مساعدتك؟"
                )
            elif "شكرا" in message_text or "مشكور" in message_text:
                await update.message.reply_text(
                    f"{EMOJIS['star']} شكراً لك! نحن سعداء بخدمتك."
                )
            else:
                await update.message.reply_text(
                    f"{EMOJIS['info']} استخدم الأمر /help لعرض المساعدة المتاحة."
                )
            
        except Exception as e:
            logger.error(f"Error handling message: {e}")
            await update.message.reply_text(
                f"{EMOJIS['error']} حدث خطأ أثناء معالجة الرسالة."
            )
    
    async def _handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle callback queries from inline keyboards"""
        try:
            query = update.callback_query
            user_id = query.from_user.id
            callback_data = query.data
            
            # Check rate limit
            try:
                await rate_limiter.check_rate_limit(user_id, "callback")
            except Exception as e:
                await query.answer("يرجى الانتظار قليلاً قبل إرسال طلب آخر.")
                return
            
            # Process callback data
            if callback_data == "help":
                await self._show_help_menu(query)
            elif callback_data == "status":
                await self._show_status_menu(query)
            elif callback_data == "admin":
                await self._show_admin_menu(query)
            else:
                await query.answer("ميزة قيد التطوير")
            
        except Exception as e:
            logger.error(f"Error handling callback: {e}")
            try:
                await update.callback_query.answer("حدث خطأ أثناء معالجة الطلب.")
            except:
                pass
    
    async def _show_help_menu(self, query):
        """Show help menu"""
        help_text = f"""
{EMOJIS['info']} قائمة المساعدة {EMOJIS['info']}

اختر الموضوع الذي تريد معرفة المزيد عنه:

{EMOJIS['wallet']} إدارة المحفظة
{EMOJIS['card']} شراء البطاقات
{EMOJIS['transfer']} التحويلات
{EMOJIS['settings']} الإعدادات
        """.strip()
        
        await query.edit_message_text(help_text)
    
    async def _show_status_menu(self, query):
        """Show status menu"""
        status_text = f"""
{EMOJIS['stats']} حالة الحساب {EMOJIS['stats']}

هنا يمكنك عرض:
{EMOJIS['wallet']} رصيد المحفظة
{EMOJIS['card']} البطاقات المملوكة
{EMOJIS['transfer']} سجل التحويلات
{EMOJIS['stats']} الإحصائيات
        """.strip()
        
        await query.edit_message_text(status_text)
    
    async def _show_admin_menu(self, query):
        """Show admin menu"""
        user_id = query.from_user.id
        
        if not config.is_admin(user_id):
            await query.answer("غير مصرح لك بالوصول إلى هذه القائمة.")
            return
        
        admin_text = f"""
{EMOJIS['admin']} لوحة الإدارة {EMOJIS['admin']}

{EMOJIS['stats']} إحصائيات النظام
{EMOJIS['user']} إدارة المستخدمين
{EMOJIS['settings']} إعدادات النظام
{EMOJIS['notification']} الإشعارات
        """.strip()
        
        await query.edit_message_text(admin_text)
    
    async def _get_user_status(self, user_id: int) -> Optional[dict]:
        """Get user status from database"""
        try:
            # Check cache first
            cache_key = f"user_status_{user_id}"
            cached_status = cache_manager.get(cache_key)
            if cached_status:
                return cached_status
            
            # Get from database
            query = '''
                SELECT u.*, 
                       COUNT(DISTINCT t.id) as transaction_count,
                       COUNT(DISTINCT c.id) as card_count
                FROM users u
                LEFT JOIN transactions t ON (u.id = t.from_user OR u.id = t.to_user)
                LEFT JOIN cards c ON u.id = c.sold_to
                WHERE u.id = ?
                GROUP BY u.id
            '''
            
            results = await db_manager.execute_query(query, (user_id,))
            if results:
                user_data = results[0]
                
                # Cache the result for 5 minutes
                cache_manager.set(cache_key, user_data, 300)
                
                return user_data
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting user status: {e}")
            return None
    
    async def _send_startup_notification(self):
        """Send startup notification to admins"""
        try:
            startup_message = f"""
{EMOJIS['rocket']} البوت يعمل الآن! {EMOJIS['rocket']}

تم تشغيل بوت يمن نت بنجاح.
الوقت: {time.strftime('%Y-%m-%d %H:%M:%S')}
الإصدار: v2.0
            """.strip()
            
            await notification_manager.send_admin_notification(
                "تم تشغيل البوت",
                startup_message
            )
            
        except Exception as e:
            logger.error(f"Failed to send startup notification: {e}")
    
    async def _error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle errors in bot updates"""
        try:
            logger.error(f"Exception while handling an update: {context.error}")
            
            # Send error notification to admins
            error_message = f"""
{EMOJIS['error']} خطأ في البوت {EMOJIS['error']}

حدث خطأ أثناء معالجة طلب:
{context.error}

التفاصيل:
- المستخدم: {update.effective_user.id if update.effective_user else 'غير محدد'}
- الوقت: {time.strftime('%Y-%m-%d %H:%M:%S')}
            """.strip()
            
            await notification_manager.send_admin_notification(
                "خطأ في البوت",
                error_message
            )
            
        except Exception as e:
            logger.error(f"Error in error handler: {e}")
    
    async def stop(self):
        """Stop the bot"""
        try:
            logger.info("Stopping Yemen Net Bot...")
            
            if self.application:
                await self.application.updater.stop()
                await self.application.stop()
                await self.application.shutdown()
            
            # Stop services
            rate_limiter.shutdown()
            cache_manager.shutdown()
            notification_manager.stop()
            db_manager.close_all_connections()
            
            self.is_running = False
            
            logger.info("Bot stopped successfully")
            
        except Exception as e:
            logger.error(f"Error stopping bot: {e}")
    
    def get_status(self) -> dict:
        """Get bot status"""
        uptime = time.time() - self.start_time if self.start_time else 0
        
        return {
            'is_running': self.is_running,
            'uptime_seconds': int(uptime),
            'uptime_formatted': self._format_uptime(uptime),
            'start_time': self.start_time,
            'database_health': db_manager.health_check(),
            'cache_stats': cache_manager.get_stats(),
            'rate_limiter_stats': rate_limiter.get_system_stats(),
            'notification_stats': notification_manager.get_stats()
        }
    
    def _format_uptime(self, seconds: float) -> str:
        """Format uptime in human readable format"""
        if seconds < 60:
            return f"{int(seconds)} ثانية"
        elif seconds < 3600:
            minutes = int(seconds // 60)
            return f"{minutes} دقيقة"
        elif seconds < 86400:
            hours = int(seconds // 3600)
            return f"{hours} ساعة"
        else:
            days = int(seconds // 86400)
            return f"{days} يوم"

async def main():
    """Main function"""
    bot = None
    
    try:
        # Create bot instance
        bot = YemenNetBot()
        
        # Start the bot
        await bot.start()
        
        # Keep running
        while bot.is_running:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
    finally:
        if bot:
            await bot.stop()

def signal_handler(signum, frame):
    """Handle system signals"""
    logger.info(f"Received signal {signum}, shutting down...")
    sys.exit(0)

if __name__ == "__main__":
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Run the bot
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot crashed: {e}")
        sys.exit(1)