"""
Main Bot Handlers for Yemen Net Bot
Refactored with proper error handling and modular design
"""

import asyncio
import logging
from typing import Optional, Dict, Any
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext

from core.exceptions import (
    BotError, DatabaseError, ValidationError, RateLimitError,
    AuthenticationError, PermissionError, InsufficientBalanceError
)
from core.config import Config
from core.logger import log_async_function_call
from services.database_manager import DatabaseManager
from services.rate_limiter import RateLimiter
from services.cache_manager import CacheManager
from services.notification_manager import NotificationManager
from utils.validators import Validators


class BotHandlers:
    """Main bot handlers with improved architecture"""
    
    def __init__(self, 
                 db_manager: DatabaseManager,
                 rate_limiter: RateLimiter,
                 cache_manager: CacheManager,
                 notification_manager: NotificationManager):
        self.db = db_manager
        self.rate_limiter = rate_limiter
        self.cache = cache_manager
        self.notifications = notification_manager
        self.config = Config()
        self.logger = logging.getLogger(__name__)
        
    async def _check_rate_limit(self, user_id: int, action: str = "general") -> bool:
        """Check rate limit for user action"""
        try:
            is_allowed, reason = await self.rate_limiter.check_rate_limit(user_id, action)
            return is_allowed
        except Exception as e:
            self.logger.error(f"Rate limit check failed: {e}")
            return True  # Allow on error to avoid blocking users
    
    async def _get_or_create_user(self, telegram_user) -> Optional[Dict[str, Any]]:
        """Get or create user in database"""
        try:
            user_id = Validators.validate_user_id(telegram_user.id)
            
            # Try cache first
            cached_user = await self.cache.get_user(user_id)
            if cached_user:
                return cached_user
            
            # Check database
            query = "SELECT * FROM users WHERE user_id = ?"
            user = await self.db.execute_query(query, (user_id,), fetch_one=True)
            
            if not user:
                # Create new user
                full_name = f"{telegram_user.first_name or ''} {telegram_user.last_name or ''}".strip()
                create_query = """
                    INSERT INTO users (user_id, username, first_name, last_name, full_name, role)
                    VALUES (?, ?, ?, ?, ?, 'user')
                """
                await self.db.execute_query(
                    create_query,
                    (user_id, telegram_user.username, telegram_user.first_name, 
                     telegram_user.last_name, full_name)
                )
                
                # Get the created user
                user = await self.db.execute_query(query, (user_id,), fetch_one=True)
                
                # Send welcome notification
                await self.notifications.notify_welcome(user_id, full_name or "المستخدم")
                
                self.logger.info(f"Created new user: {user_id}")
            
            # Cache user data
            if user:
                await self.cache.cache_user(user_id, user)
            
            return user
            
        except Exception as e:
            self.logger.error(f"Error getting/creating user: {e}")
            raise DatabaseError(f"Failed to get user data: {e}")
    
    @log_async_function_call(logging.getLogger(__name__))
    async def start_handler(self, update: Update, context: CallbackContext):
        """Handle /start command"""
        try:
            user = update.effective_user
            if not user:
                return
            
            # Check rate limit
            if not await self._check_rate_limit(user.id, "start"):
                return
            
            # Get or create user
            db_user = await self._get_or_create_user(user)
            if not db_user:
                await update.message.reply_text("❌ حدث خطأ في النظام. يرجى المحاولة لاحقاً.")
                return
            
            # Create welcome message
            welcome_text = f"""
🎉 مرحباً بك في Yemen Net Bot!

👤 الاسم: {db_user['full_name'] or 'غير محدد'}
💰 الرصيد: {db_user['balance']:.2f} ر.ي
📱 الحالة: {'نشط' if db_user['is_active'] else 'غير نشط'}

يمكنك الآن:
• شراء البطاقات 💳
• إدارة محفظتك 💰
• عرض التقارير 📊
• والمزيد...

استخدم الأزرار أدناه للبدء:
            """
            
            # Create keyboard
            keyboard = [
                [
                    InlineKeyboardButton("💳 شراء بطاقة", callback_data="buy_card"),
                    InlineKeyboardButton("💰 المحفظة", callback_data="wallet")
                ],
                [
                    InlineKeyboardButton("🌐 الشبكات", callback_data="networks"),
                    InlineKeyboardButton("📋 التاريخ", callback_data="history")
                ],
                [
                    InlineKeyboardButton("👤 الملف الشخصي", callback_data="profile"),
                    InlineKeyboardButton("❓ المساعدة", callback_data="help")
                ]
            ]
            
            # Add admin panel for admins
            if self.config.is_admin(user.id):
                keyboard.append([
                    InlineKeyboardButton("👨‍💼 لوحة الإدارة", callback_data="admin_panel")
                ])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(welcome_text, reply_markup=reply_markup)
            
        except RateLimitError as e:
            await update.message.reply_text(f"⏳ {e.message}")
        except Exception as e:
            self.logger.error(f"Error in start handler: {e}")
            await update.message.reply_text("❌ حدث خطأ غير متوقع. يرجى المحاولة لاحقاً.")
    
    @log_async_function_call(logging.getLogger(__name__))
    async def help_handler(self, update: Update, context: CallbackContext):
        """Handle /help command"""
        try:
            help_text = """
📖 مساعدة Yemen Net Bot

🔸 الأوامر المتاحة:
• /start - بدء البوت والقائمة الرئيسية
• /wallet - عرض المحفظة والرصيد
• /buy - شراء بطاقة جديدة
• /profile - عرض وتعديل الملف الشخصي
• /help - عرض هذه المساعدة

🔸 المميزات:
• شراء البطاقات الرقمية
• إدارة المحفظة والرصيد
• عرض تاريخ المعاملات
• إشعارات فورية
• دعم فني متاح

🔸 للدعم الفني:
تواصل مع الإدارة عبر الضغط على زر "الدعم الفني"

⚡ Yemen Net - خدمة البطاقات الرقمية
            """
            
            keyboard = [
                [InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="main_menu")],
                [InlineKeyboardButton("📞 الدعم الفني", callback_data="support")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(help_text, reply_markup=reply_markup)
            
        except Exception as e:
            self.logger.error(f"Error in help handler: {e}")
            await update.message.reply_text("❌ حدث خطأ في عرض المساعدة.")
    
    @log_async_function_call(logging.getLogger(__name__))
    async def wallet_handler(self, update: Update, context: CallbackContext):
        """Handle wallet command"""
        try:
            user = update.effective_user
            if not user:
                return
            
            # Check rate limit
            if not await self._check_rate_limit(user.id, "wallet"):
                return
            
            db_user = await self._get_or_create_user(user)
            if not db_user:
                await update.message.reply_text("❌ لم يتم العثور على بيانات المستخدم.")
                return
            
            # Get recent transactions
            transactions_query = """
                SELECT * FROM transactions 
                WHERE from_user = ? OR to_user = ?
                ORDER BY created_at DESC 
                LIMIT 5
            """
            transactions = await self.db.execute_query(
                transactions_query, 
                (db_user['id'], db_user['id']), 
                fetch_all=True
            )
            
            wallet_text = f"""
💰 معلومات المحفظة

👤 المستخدم: {db_user['full_name']}
💳 الرصيد الحالي: {db_user['balance']:.2f} ر.ي
📅 تاريخ التسجيل: {db_user['registration_date'][:10]}
⭐ الحالة: {'نشط' if db_user['is_active'] else 'غير نشط'}

📋 آخر المعاملات:
            """
            
            if transactions:
                for tx in transactions[:3]:
                    tx_type = "➕ إيداع" if tx['type'] == 'credit' else "➖ سحب"
                    amount = float(tx['amount']) if tx['amount'] else 0
                    wallet_text += f"\n• {tx_type}: {amount:.2f} ر.ي - {tx['created_at'][:10]}"
            else:
                wallet_text += "\nلا توجد معاملات حتى الآن"
            
            keyboard = [
                [
                    InlineKeyboardButton("🔄 تحديث الرصيد", callback_data="refresh_balance"),
                    InlineKeyboardButton("📋 كل المعاملات", callback_data="all_transactions")
                ],
                [
                    InlineKeyboardButton("💳 شراء بطاقة", callback_data="buy_card"),
                    InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="main_menu")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            if update.message:
                await update.message.reply_text(wallet_text, reply_markup=reply_markup)
            else:
                await update.callback_query.edit_message_text(wallet_text, reply_markup=reply_markup)
            
        except Exception as e:
            self.logger.error(f"Error in wallet handler: {e}")
            error_msg = "❌ حدث خطأ في عرض المحفظة."
            if update.message:
                await update.message.reply_text(error_msg)
            else:
                await update.callback_query.answer(error_msg)
    
    @log_async_function_call(logging.getLogger(__name__))
    async def button_click_handler(self, update: Update, context: CallbackContext):
        """Handle inline keyboard button clicks"""
        try:
            query = update.callback_query
            if not query:
                return
            
            await query.answer()
            user = query.from_user
            
            # Check rate limit
            if not await self._check_rate_limit(user.id, "button_click"):
                await query.answer("⏳ يرجى الانتظار قبل المحاولة مرة أخرى.")
                return
            
            data = query.data
            self.logger.info(f"Button clicked by user {user.id}: {data}")
            
            # Route to appropriate handler
            if data == "main_menu":
                await self._show_main_menu(update, context)
            elif data == "wallet":
                await self.wallet_handler(update, context)
            elif data == "buy_card":
                await self._show_buy_card_menu(update, context)
            elif data == "networks":
                await self._show_networks(update, context)
            elif data == "profile":
                await self._show_profile(update, context)
            elif data == "help":
                await self.help_handler(update, context)
            elif data == "admin_panel":
                await self._show_admin_panel(update, context)
            elif data == "refresh_balance":
                await self.wallet_handler(update, context)
            elif data == "all_transactions":
                await self._show_all_transactions(update, context)
            elif data == "support":
                await self._show_support_info(update, context)
            else:
                await query.answer("🔧 هذه الميزة قيد التطوير...")
                
        except Exception as e:
            self.logger.error(f"Error in button click handler: {e}")
            if update.callback_query:
                await update.callback_query.answer("❌ حدث خطأ في معالجة الطلب.")
    
    async def _show_main_menu(self, update: Update, context: CallbackContext):
        """Show main menu"""
        try:
            user = update.effective_user
            db_user = await self._get_or_create_user(user)
            
            menu_text = f"""
🏠 القائمة الرئيسية

👋 أهلاً {db_user['full_name']}!
💰 رصيدك: {db_user['balance']:.2f} ر.ي

اختر الخدمة المطلوبة:
            """
            
            keyboard = [
                [
                    InlineKeyboardButton("💳 شراء بطاقة", callback_data="buy_card"),
                    InlineKeyboardButton("💰 المحفظة", callback_data="wallet")
                ],
                [
                    InlineKeyboardButton("🌐 الشبكات", callback_data="networks"),
                    InlineKeyboardButton("📋 التاريخ", callback_data="all_transactions")
                ],
                [
                    InlineKeyboardButton("👤 الملف الشخصي", callback_data="profile"),
                    InlineKeyboardButton("❓ المساعدة", callback_data="help")
                ]
            ]
            
            # Add admin panel for admins
            if self.config.is_admin(user.id):
                keyboard.append([
                    InlineKeyboardButton("👨‍💼 لوحة الإدارة", callback_data="admin_panel")
                ])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.callback_query.edit_message_text(menu_text, reply_markup=reply_markup)
            
        except Exception as e:
            self.logger.error(f"Error showing main menu: {e}")
    
    async def _show_buy_card_menu(self, update: Update, context: CallbackContext):
        """Show card purchase menu"""
        try:
            # Get available networks
            networks_query = "SELECT * FROM networks WHERE is_active = 1 ORDER BY name"
            networks = await self.db.execute_query(networks_query, fetch_all=True)
            
            if not networks:
                await update.callback_query.edit_message_text(
                    "❌ لا توجد شبكات متاحة حالياً.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="main_menu")
                    ]])
                )
                return
            
            menu_text = "💳 اختر الشبكة المطلوبة:\n\n"
            keyboard = []
            
            for network in networks:
                menu_text += f"🌐 {network['name']}\n"
                keyboard.append([
                    InlineKeyboardButton(
                        f"🌐 {network['name']}", 
                        callback_data=f"network_{network['id']}"
                    )
                ])
            
            keyboard.append([
                InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="main_menu")
            ])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.callback_query.edit_message_text(menu_text, reply_markup=reply_markup)
            
        except Exception as e:
            self.logger.error(f"Error showing buy card menu: {e}")
    
    async def _show_networks(self, update: Update, context: CallbackContext):
        """Show available networks"""
        # Similar implementation to buy card menu but for viewing only
        await self._show_buy_card_menu(update, context)
    
    async def _show_profile(self, update: Update, context: CallbackContext):
        """Show user profile"""
        try:
            user = update.effective_user
            db_user = await self._get_or_create_user(user)
            
            profile_text = f"""
👤 الملف الشخصي

🆔 معرف المستخدم: {db_user['user_id']}
📝 الاسم الكامل: {db_user['full_name'] or 'غير محدد'}
👤 اسم المستخدم: @{user.username or 'غير محدد'}
📱 الهاتف: {db_user['phone'] or 'غير محدد'}
📧 البريد الإلكتروني: {db_user['email'] or 'غير محدد'}
⭐ الدور: {self.config.USER_ROLES.get(db_user['role'], db_user['role'])}
💰 الرصيد: {db_user['balance']:.2f} ر.ي
📅 تاريخ التسجيل: {db_user['registration_date'][:10]}
🔄 آخر نشاط: {db_user['last_activity'][:10] if db_user['last_activity'] else 'غير محدد'}
            """
            
            keyboard = [
                [
                    InlineKeyboardButton("✏️ تعديل الملف الشخصي", callback_data="edit_profile"),
                    InlineKeyboardButton("🔔 الإشعارات", callback_data="notifications")
                ],
                [
                    InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="main_menu")
                ]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.callback_query.edit_message_text(profile_text, reply_markup=reply_markup)
            
        except Exception as e:
            self.logger.error(f"Error showing profile: {e}")
    
    async def _show_admin_panel(self, update: Update, context: CallbackContext):
        """Show admin panel (for admins only)"""
        try:
            user = update.effective_user
            
            if not self.config.is_admin(user.id):
                await update.callback_query.answer("❌ غير مصرح لك بالوصول لهذه الميزة.")
                return
            
            admin_text = """
👨‍💼 لوحة الإدارة

اختر العملية المطلوبة:
            """
            
            keyboard = [
                [
                    InlineKeyboardButton("👥 إدارة المستخدمين", callback_data="admin_users"),
                    InlineKeyboardButton("🌐 إدارة الشبكات", callback_data="admin_networks")
                ],
                [
                    InlineKeyboardButton("💳 إدارة البطاقات", callback_data="admin_cards"),
                    InlineKeyboardButton("💰 إدارة المحافظ", callback_data="admin_wallets")
                ],
                [
                    InlineKeyboardButton("📊 التقارير", callback_data="admin_reports"),
                    InlineKeyboardButton("⚙️ إعدادات النظام", callback_data="admin_settings")
                ],
                [
                    InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="main_menu")
                ]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.callback_query.edit_message_text(admin_text, reply_markup=reply_markup)
            
        except Exception as e:
            self.logger.error(f"Error showing admin panel: {e}")
    
    async def _show_all_transactions(self, update: Update, context: CallbackContext):
        """Show all user transactions"""
        try:
            user = update.effective_user
            db_user = await self._get_or_create_user(user)
            
            # Get user transactions with pagination
            transactions_query = """
                SELECT * FROM transactions 
                WHERE from_user = ? OR to_user = ?
                ORDER BY created_at DESC 
                LIMIT 10
            """
            transactions = await self.db.execute_query(
                transactions_query, 
                (db_user['id'], db_user['id']), 
                fetch_all=True
            )
            
            if not transactions:
                text = "📋 لا توجد معاملات في سجلك حتى الآن."
            else:
                text = f"📋 سجل المعاملات (آخر 10 معاملات):\n\n"
                
                for tx in transactions:
                    tx_type = "➕ إيداع" if tx['type'] == 'credit' else "➖ سحب"
                    amount = float(tx['amount']) if tx['amount'] else 0
                    date = tx['created_at'][:10] if tx['created_at'] else ''
                    description = tx['description'] or 'معاملة'
                    text += f"• {tx_type}: {amount:.2f} ر.ي\n  📝 {description}\n  📅 {date}\n\n"
            
            keyboard = [
                [InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="main_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.callback_query.edit_message_text(text, reply_markup=reply_markup)
            
        except Exception as e:
            self.logger.error(f"Error showing transactions: {e}")
    
    async def _show_support_info(self, update: Update, context: CallbackContext):
        """Show support information"""
        support_text = """
📞 الدعم الفني

🔸 طرق التواصل:
• Telegram: @YemenNetSupport
• WhatsApp: +967xxxxxxxxx
• Email: support@yemennet.com

🔸 ساعات العمل:
من الأحد إلى الخميس
من 8:00 صباحاً إلى 8:00 مساءً

🔸 الأسئلة الشائعة:
• كيفية شراء البطاقات
• استرداد الأموال
• مشاكل فنية
• تحديث البيانات الشخصية

⚡ Yemen Net - خدمة البطاقات الرقمية
        """
        
        keyboard = [
            [InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(support_text, reply_markup=reply_markup)
    
    # Placeholder handlers for other features
    async def balance_handler(self, update: Update, context: CallbackContext):
        """Handle balance command - redirect to wallet"""
        await self.wallet_handler(update, context)
    
    async def buy_handler(self, update: Update, context: CallbackContext):
        """Handle buy command - redirect to buy menu"""
        await self._show_buy_card_menu(update, context)
    
    async def profile_handler(self, update: Update, context: CallbackContext):
        """Handle profile command - redirect to profile"""
        await self._show_profile(update, context)
    
    async def stats_handler(self, update: Update, context: CallbackContext):
        """Handle stats command"""
        await update.message.reply_text("📊 الإحصائيات قيد التطوير...")
    
    async def networks_handler(self, update: Update, context: CallbackContext):
        """Handle networks command"""
        await self._show_networks(update, context)
    
    async def admin_handler(self, update: Update, context: CallbackContext):
        """Handle admin command"""
        user = update.effective_user
        if self.config.is_admin(user.id):
            await self._show_admin_panel(update, context)
        else:
            await update.message.reply_text("❌ غير مصرح لك بالوصول لهذه الميزة.")
    
    async def message_handler(self, update: Update, context: CallbackContext):
        """Handle text messages"""
        await update.message.reply_text(
            "👋 مرحباً! استخدم الأزرار أو الأوامر للتفاعل مع البوت.\n"
            "اكتب /help للمساعدة أو /start للقائمة الرئيسية."
        )
    
    async def document_handler(self, update: Update, context: CallbackContext):
        """Handle document uploads"""
        await update.message.reply_text("📄 تم استلام الملف. هذه الميزة قيد التطوير...")
    
    async def photo_handler(self, update: Update, context: CallbackContext):
        """Handle photo uploads"""
        await update.message.reply_text("🖼️ تم استلام الصورة. هذه الميزة قيد التطوير...")