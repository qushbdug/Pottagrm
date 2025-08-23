"""
Bot Handlers Module - Main handlers for Yemen Net Bot
"""
from typing import Optional, Dict, Any
from datetime import datetime

# Telegram imports with specific exception handling
try:
    from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
    from telegram.ext import (
        CommandHandler, MessageHandler, CallbackQueryHandler, 
        ConversationHandler, filters, CallbackContext
    )
    from telegram.error import BadRequest, Forbidden, NetworkError
except ImportError as e:
    from ..core.logger import logger
    logger.critical("Failed to import Telegram libraries", e)
    raise

# Internal imports with specific exception handling
try:
    from ..core.logger import logger
    from ..core.exceptions import (
        UserNotFound, UserPermissionDenied, InsufficientFunds,
        ValidationException, InvalidInput, NetworkException,
        PaymentException, TelegramException, MessageSendError
    )
    from ..services.database_service import db_service
    from ..services.rate_limiter import rate_limiter, rate_limit
    from ..utils.keyboards import KeyboardManager
    from ..utils.validators import validate_phone_number, validate_amount
    from ..utils.formatters import format_balance, format_transaction
    from ..config.settings import BOT_CONFIG, PAYMENT_CONFIG
except ImportError as e:
    print(f"Failed to import bot modules: {e}")
    raise


class ConversationStates:
    """Conversation state constants"""
    START = 0
    MAIN_MENU = 1
    PROFILE_EDIT = 2
    TRANSFER_AMOUNT = 3
    TRANSFER_CONFIRM = 4
    CARD_UPLOAD = 5
    PHONE_INPUT = 6
    END = -1


class BotHandlers:
    """Main bot handlers class with comprehensive error handling"""
    
    def __init__(self):
        self.keyboard_manager = KeyboardManager()
        
    @rate_limit('start_command')
    async def start_command(self, update: Update, context: CallbackContext):
        """Handle /start command with comprehensive error handling"""
        try:
            user = update.effective_user
            
            # Validate user
            if not user:
                raise TelegramException("Invalid user in update")
                
            logger.log_user_action(user.id, "start_command", f"Username: {user.username}")
            
            # Check if user exists in database
            try:
                db_user = await db_service.get_user(user.id)
            except Exception as e:
                logger.error("Database error while getting user", e)
                raise
                
            if not db_user:
                # New user registration
                try:
                    success = await db_service.create_user(
                        telegram_id=user.id,
                        full_name=user.full_name or f"{user.first_name} {user.last_name or ''}".strip(),
                        phone=None  # Will be collected later
                    )
                    
                    if not success:
                        raise Exception("Failed to create user")
                        
                    welcome_message = (
                        f"🎉 مرحباً {user.first_name}!\n\n"
                        "مرحباً بك في بوت شبكة اليمن المحسن\n"
                        "البوت الذي يوفر لك جميع خدمات الشبكات والدفع الإلكتروني\n\n"
                        "📱 لبدء استخدام البوت، يرجى إدخال رقم هاتفك أولاً\n"
                        "💡 استخدم الأزرار أدناه للتنقل بين الخدمات"
                    )
                    
                    keyboard = self.keyboard_manager.get_registration_keyboard()
                    
                except Exception as e:
                    logger.error("Failed to create new user", e)
                    await self._send_error_message(update, "حدث خطأ أثناء التسجيل. يرجى المحاولة مرة أخرى.")
                    return ConversationStates.END
                    
            else:
                # Existing user
                welcome_message = (
                    f"مرحباً بعودتك {user.first_name}! 👋\n\n"
                    "أهلاً وسهلاً بك في بوت شبكة اليمن\n"
                    "كيف يمكنني مساعدتك اليوم؟\n\n"
                    f"💰 رصيدك الحالي: {format_balance(db_user.get('balance', 0))}"
                )
                
                keyboard = self.keyboard_manager.get_main_menu_keyboard(db_user.get('role', 'user'))
                
            try:
                await update.message.reply_text(welcome_message, reply_markup=keyboard)
                return ConversationStates.MAIN_MENU
                
            except BadRequest as e:
                logger.error("Bad request when sending welcome message", e)
                raise MessageSendError("Failed to send welcome message")
            except Forbidden as e:
                logger.warning(f"Bot blocked by user {user.id}", e)
                return ConversationStates.END
            except NetworkError as e:
                logger.error("Network error when sending message", e)
                raise
                
        except TelegramException as e:
            logger.error("Telegram error in start command", e)
            await self._send_error_message(update, "حدث خطأ في التواصل مع تليجرام.")
            return ConversationStates.END
        except ValidationException as e:
            logger.error("Validation error in start command", e)
            await self._send_error_message(update, f"خطأ في البيانات: {str(e)}")
            return ConversationStates.END
        except Exception as e:
            logger.error("Unexpected error in start command", e)
            await self._send_error_message(update, "حدث خطأ غير متوقع. يرجى المحاولة مرة أخرى.")
            return ConversationStates.END
            
    @rate_limit('profile_command')
    async def profile_command(self, update: Update, context: CallbackContext):
        """Handle /profile command"""
        try:
            user = update.effective_user
            
            # Get user from database
            db_user = await db_service.get_user(user.id)
            if not db_user:
                raise UserNotFound("المستخدم غير موجود. يرجى التسجيل أولاً باستخدام /start")
                
            # Get user statistics
            transactions = await db_service.get_user_transactions(db_user['id'], limit=1)
            last_transaction = transactions[0] if transactions else None
            
            profile_text = (
                f"👤 **الملف الشخصي**\n\n"
                f"**الاسم:** {db_user['full_name']}\n"
                f"**معرف المستخدم:** @{user.username or 'غير محدد'}\n"
                f"**رقم الهاتف:** {db_user.get('phone') or 'غير محدد'}\n"
                f"**الدور:** {self._get_role_name(db_user['role'])}\n"
                f"**الرصيد:** {format_balance(db_user['balance'])}\n"
                f"**تاريخ التسجيل:** {self._format_date(db_user.get('created_at'))}\n"
                f"**الحالة:** {'نشط' if db_user.get('is_active') else 'غير نشط'}\n"
            )
            
            if last_transaction:
                profile_text += f"**آخر معاملة:** {format_transaction(last_transaction)}\n"
                
            keyboard = self.keyboard_manager.get_profile_keyboard()
            
            await update.message.reply_text(
                profile_text, 
                reply_markup=keyboard, 
                parse_mode='Markdown'
            )
            
        except UserNotFound as e:
            await self._send_error_message(update, str(e))
        except Exception as e:
            logger.error("Error in profile command", e)
            await self._send_error_message(update, "حدث خطأ أثناء عرض الملف الشخصي.")
            
    @rate_limit('wallet_command')
    async def wallet_command(self, update: Update, context: CallbackContext):
        """Handle /wallet command"""
        try:
            user = update.effective_user
            
            # Get user from database
            db_user = await db_service.get_user(user.id)
            if not db_user:
                raise UserNotFound("المستخدم غير موجود. يرجى التسجيل أولاً باستخدام /start")
                
            # Get recent transactions
            transactions = await db_service.get_user_transactions(db_user['id'], limit=5)
            
            wallet_text = (
                f"💰 **المحفظة المالية**\n\n"
                f"**الرصيد الحالي:** {format_balance(db_user['balance'])}\n"
                f"**العملة:** {PAYMENT_CONFIG.supported_currencies[0]}\n\n"
            )
            
            if transactions:
                wallet_text += "**آخر المعاملات:**\n"
                for tx in transactions:
                    wallet_text += f"{format_transaction(tx)}\n"
            else:
                wallet_text += "**لا توجد معاملات حديثة**\n"
                
            # Add wallet controls
            wallet_text += "\n💡 استخدم الأزرار أدناه لإدارة محفظتك"
            
            keyboard = self.keyboard_manager.get_wallet_keyboard()
            
            await update.message.reply_text(
                wallet_text, 
                reply_markup=keyboard, 
                parse_mode='Markdown'
            )
            
        except UserNotFound as e:
            await self._send_error_message(update, str(e))
        except Exception as e:
            logger.error("Error in wallet command", e)
            await self._send_error_message(update, "حدث خطأ أثناء عرض المحفظة.")
            
    @rate_limit('transfer_command')
    async def transfer_command(self, update: Update, context: CallbackContext):
        """Handle /transfer command"""
        try:
            user = update.effective_user
            
            # Get user from database
            db_user = await db_service.get_user(user.id)
            if not db_user:
                raise UserNotFound("المستخدم غير موجود. يرجى التسجيل أولاً باستخدام /start")
                
            # Check if transfers are enabled
            if not PAYMENT_CONFIG.enable_payments:
                await self._send_error_message(update, "خدمة التحويل معطلة حالياً.")
                return ConversationStates.END
                
            # Check minimum balance
            if db_user['balance'] < PAYMENT_CONFIG.min_transfer_amount:
                await self._send_error_message(
                    update, 
                    f"رصيدك غير كافي للتحويل. الحد الأدنى: {format_balance(PAYMENT_CONFIG.min_transfer_amount)}"
                )
                return ConversationStates.END
                
            transfer_text = (
                f"💸 **تحويل رصيد**\n\n"
                f"**رصيدك الحالي:** {format_balance(db_user['balance'])}\n"
                f"**الحد الأدنى للتحويل:** {format_balance(PAYMENT_CONFIG.min_transfer_amount)}\n"
                f"**الحد الأقصى للتحويل:** {format_balance(PAYMENT_CONFIG.max_transfer_amount)}\n"
                f"**رسوم التحويل:** {PAYMENT_CONFIG.commission_rate * 100:.1f}%\n\n"
                "📝 يرجى إدخال المبلغ المراد تحويله:"
            )
            
            keyboard = self.keyboard_manager.get_cancel_keyboard()
            
            await update.message.reply_text(
                transfer_text, 
                reply_markup=keyboard, 
                parse_mode='Markdown'
            )
            
            return ConversationStates.TRANSFER_AMOUNT
            
        except UserNotFound as e:
            await self._send_error_message(update, str(e))
            return ConversationStates.END
        except Exception as e:
            logger.error("Error in transfer command", e)
            await self._send_error_message(update, "حدث خطأ أثناء إعداد التحويل.")
            return ConversationStates.END
            
    async def handle_transfer_amount(self, update: Update, context: CallbackContext):
        """Handle transfer amount input"""
        try:
            user = update.effective_user
            amount_text = update.message.text.strip()
            
            # Validate amount
            try:
                amount = validate_amount(amount_text)
                if not amount:
                    raise InvalidInput("مبلغ غير صحيح")
            except ValidationException as e:
                await self._send_error_message(update, f"خطأ في المبلغ: {str(e)}")
                return ConversationStates.TRANSFER_AMOUNT
                
            # Check amount limits
            if amount < PAYMENT_CONFIG.min_transfer_amount:
                await self._send_error_message(
                    update, 
                    f"المبلغ أقل من الحد الأدنى: {format_balance(PAYMENT_CONFIG.min_transfer_amount)}"
                )
                return ConversationStates.TRANSFER_AMOUNT
                
            if amount > PAYMENT_CONFIG.max_transfer_amount:
                await self._send_error_message(
                    update, 
                    f"المبلغ أكبر من الحد الأقصى: {format_balance(PAYMENT_CONFIG.max_transfer_amount)}"
                )
                return ConversationStates.TRANSFER_AMOUNT
                
            # Get user balance
            db_user = await db_service.get_user(user.id)
            if not db_user:
                raise UserNotFound("المستخدم غير موجود")
                
            # Calculate total with commission
            commission = amount * PAYMENT_CONFIG.commission_rate
            total_amount = amount + commission
            
            # Check sufficient balance
            if db_user['balance'] < total_amount:
                raise InsufficientFunds(
                    f"رصيد غير كافي. تحتاج إلى: {format_balance(total_amount)} "
                    f"(المبلغ: {format_balance(amount)} + العمولة: {format_balance(commission)})"
                )
                
            # Store transfer data in context
            context.user_data['transfer_amount'] = amount
            context.user_data['transfer_commission'] = commission
            context.user_data['transfer_total'] = total_amount
            
            # Ask for recipient
            transfer_text = (
                f"💸 **تأكيد التحويل**\n\n"
                f"**المبلغ:** {format_balance(amount)}\n"
                f"**العمولة:** {format_balance(commission)}\n"
                f"**المجموع:** {format_balance(total_amount)}\n\n"
                "📱 يرجى إدخال رقم هاتف المستلم:"
            )
            
            keyboard = self.keyboard_manager.get_cancel_keyboard()
            
            await update.message.reply_text(
                transfer_text, 
                reply_markup=keyboard, 
                parse_mode='Markdown'
            )
            
            return ConversationStates.PHONE_INPUT
            
        except UserNotFound as e:
            await self._send_error_message(update, str(e))
            return ConversationStates.END
        except InsufficientFunds as e:
            await self._send_error_message(update, str(e))
            return ConversationStates.END
        except ValidationException as e:
            await self._send_error_message(update, str(e))
            return ConversationStates.TRANSFER_AMOUNT
        except Exception as e:
            logger.error("Error handling transfer amount", e)
            await self._send_error_message(update, "حدث خطأ أثناء معالجة المبلغ.")
            return ConversationStates.END
            
    async def handle_phone_input(self, update: Update, context: CallbackContext):
        """Handle phone number input for transfers"""
        try:
            phone_text = update.message.text.strip()
            
            # Validate phone number
            try:
                phone = validate_phone_number(phone_text)
                if not phone:
                    raise InvalidInput("رقم هاتف غير صحيح")
            except ValidationException as e:
                await self._send_error_message(update, f"خطأ في رقم الهاتف: {str(e)}")
                return ConversationStates.PHONE_INPUT
                
            # Find recipient user
            recipient = await self._find_user_by_phone(phone)
            if not recipient:
                await self._send_error_message(
                    update, 
                    "المستلم غير موجود. تأكد من صحة رقم الهاتف أو أن المستلم مسجل في النظام."
                )
                return ConversationStates.PHONE_INPUT
                
            # Store recipient data
            context.user_data['recipient_id'] = recipient['id']
            context.user_data['recipient_name'] = recipient['full_name']
            context.user_data['recipient_phone'] = phone
            
            # Get transfer data
            amount = context.user_data.get('transfer_amount', 0)
            commission = context.user_data.get('transfer_commission', 0)
            total_amount = context.user_data.get('transfer_total', 0)
            
            # Create confirmation message
            confirm_text = (
                f"✅ **تأكيد التحويل**\n\n"
                f"**المستلم:** {recipient['full_name']}\n"
                f"**رقم الهاتف:** {phone}\n"
                f"**المبلغ:** {format_balance(amount)}\n"
                f"**العمولة:** {format_balance(commission)}\n"
                f"**المجموع:** {format_balance(total_amount)}\n\n"
                "هل تريد تأكيد التحويل؟"
            )
            
            keyboard = self.keyboard_manager.get_confirmation_keyboard()
            
            await update.message.reply_text(
                confirm_text, 
                reply_markup=keyboard, 
                parse_mode='Markdown'
            )
            
            return ConversationStates.TRANSFER_CONFIRM
            
        except ValidationException as e:
            await self._send_error_message(update, str(e))
            return ConversationStates.PHONE_INPUT
        except Exception as e:
            logger.error("Error handling phone input", e)
            await self._send_error_message(update, "حدث خطأ أثناء معالجة رقم الهاتف.")
            return ConversationStates.END
            
    async def handle_transfer_confirm(self, update: Update, context: CallbackContext):
        """Handle transfer confirmation"""
        try:
            query = update.callback_query
            await query.answer()
            
            if query.data == "confirm_transfer":
                # Execute transfer
                try:
                    user = update.effective_user
                    
                    # Get transfer data
                    amount = context.user_data.get('transfer_amount', 0)
                    commission = context.user_data.get('transfer_commission', 0)
                    total_amount = context.user_data.get('transfer_total', 0)
                    recipient_id = context.user_data.get('recipient_id')
                    recipient_name = context.user_data.get('recipient_name')
                    
                    if not all([amount, recipient_id]):
                        raise PaymentException("بيانات التحويل غير مكتملة")
                        
                    # Get sender
                    sender = await db_service.get_user(user.id)
                    if not sender:
                        raise UserNotFound("المرسل غير موجود")
                        
                    # Check balance again
                    if sender['balance'] < total_amount:
                        raise InsufficientFunds("رصيد غير كافي")
                        
                    # Execute transfer
                    success = await self._execute_transfer(
                        sender['id'], 
                        recipient_id, 
                        amount, 
                        commission
                    )
                    
                    if success:
                        success_text = (
                            f"✅ **تم التحويل بنجاح**\n\n"
                            f"**المستلم:** {recipient_name}\n"
                            f"**المبلغ:** {format_balance(amount)}\n"
                            f"**العمولة:** {format_balance(commission)}\n"
                            f"**رصيدك الجديد:** {format_balance(sender['balance'] - total_amount)}\n"
                            f"**التاريخ:** {datetime.now().strftime('%Y-%m-%d %H:%M')}"
                        )
                        
                        keyboard = self.keyboard_manager.get_main_menu_keyboard(sender.get('role', 'user'))
                        
                        await query.edit_message_text(
                            success_text, 
                            reply_markup=keyboard, 
                            parse_mode='Markdown'
                        )
                        
                        # Clear transfer data
                        self._clear_transfer_data(context)
                        
                        return ConversationStates.MAIN_MENU
                    else:
                        raise PaymentException("فشل في تنفيذ التحويل")
                        
                except (UserNotFound, InsufficientFunds, PaymentException) as e:
                    await query.edit_message_text(f"❌ {str(e)}")
                    return ConversationStates.END
                    
            elif query.data == "cancel_transfer":
                await query.edit_message_text("❌ تم إلغاء التحويل.")
                self._clear_transfer_data(context)
                return ConversationStates.END
                
        except Exception as e:
            logger.error("Error in transfer confirmation", e)
            await self._send_error_message(update, "حدث خطأ أثناء تأكيد التحويل.")
            return ConversationStates.END
            
    async def cancel_command(self, update: Update, context: CallbackContext):
        """Handle /cancel command"""
        try:
            # Clear any ongoing data
            context.user_data.clear()
            
            await update.message.reply_text(
                "❌ تم إلغاء العملية الحالية.\n"
                "استخدم /start للعودة إلى القائمة الرئيسية."
            )
            
            return ConversationStates.END
            
        except Exception as e:
            logger.error("Error in cancel command", e)
            return ConversationStates.END
            
    # Helper methods
    
    async def _send_error_message(self, update: Update, message: str):
        """Send error message to user"""
        try:
            if update.message:
                await update.message.reply_text(f"❌ {message}")
            elif update.callback_query:
                await update.callback_query.message.reply_text(f"❌ {message}")
        except Exception as e:
            logger.error("Failed to send error message", e)
            
    async def _find_user_by_phone(self, phone: str) -> Optional[Dict[str, Any]]:
        """Find user by phone number"""
        try:
            # This would need a database method to find by phone
            # For now, returning None - implement in database service
            return None
        except Exception as e:
            logger.error("Error finding user by phone", e)
            return None
            
    async def _execute_transfer(self, sender_id: int, recipient_id: int, 
                              amount: float, commission: float) -> bool:
        """Execute transfer between users"""
        try:
            # Deduct from sender
            await db_service.update_user_balance(sender_id, -(amount + commission), "subtract")
            
            # Add to recipient
            await db_service.update_user_balance(recipient_id, amount, "add")
            
            # Create transaction records
            await db_service.create_transaction(
                sender_id, recipient_id, amount, "transfer", 
                f"تحويل رصيد إلى مستخدم {recipient_id}"
            )
            
            if commission > 0:
                await db_service.create_transaction(
                    sender_id, None, commission, "commission", 
                    "عمولة تحويل رصيد"
                )
                
            return True
            
        except Exception as e:
            logger.error("Failed to execute transfer", e)
            return False
            
    def _clear_transfer_data(self, context: CallbackContext):
        """Clear transfer data from context"""
        keys_to_clear = [
            'transfer_amount', 'transfer_commission', 'transfer_total',
            'recipient_id', 'recipient_name', 'recipient_phone'
        ]
        for key in keys_to_clear:
            context.user_data.pop(key, None)
            
    def _get_role_name(self, role: str) -> str:
        """Get Arabic role name"""
        role_names = {
            'user': 'مستخدم',
            'agent': 'وكيل',
            'supplier': 'مزود',
            'admin': 'مدير',
            'super_admin': 'مدير عام'
        }
        return role_names.get(role, role)
        
    def _format_date(self, date_str: Optional[str]) -> str:
        """Format date string"""
        if not date_str:
            return "غير محدد"
        try:
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            return dt.strftime('%Y-%m-%d %H:%M')
        except Exception:
            return date_str


def setup_handlers(application):
    """Setup all bot handlers"""
    try:
        handlers = BotHandlers()
        
        # Create conversation handler
        conv_handler = ConversationHandler(
            entry_points=[
                CommandHandler('start', handlers.start_command),
                CommandHandler('profile', handlers.profile_command),
                CommandHandler('wallet', handlers.wallet_command),
                CommandHandler('transfer', handlers.transfer_command),
            ],
            states={
                ConversationStates.MAIN_MENU: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.start_command)
                ],
                ConversationStates.TRANSFER_AMOUNT: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.handle_transfer_amount)
                ],
                ConversationStates.PHONE_INPUT: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.handle_phone_input)
                ],
                ConversationStates.TRANSFER_CONFIRM: [
                    CallbackQueryHandler(handlers.handle_transfer_confirm)
                ],
            },
            fallbacks=[
                CommandHandler('cancel', handlers.cancel_command),
                CommandHandler('start', handlers.start_command)
            ],
            name="main_conversation",
            persistent=True
        )
        
        # Add handlers to application
        application.add_handler(conv_handler)
        
        logger.info("Bot handlers setup completed successfully")
        
    except Exception as e:
        logger.critical("Failed to setup bot handlers", e)
        raise