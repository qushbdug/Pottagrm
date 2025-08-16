#!/usr/bin/env python3
"""
Command Handlers for Yemen Net Bot
Professional command handling with proper validation and error handling.
"""

import logging
from typing import Any
from telegram import Update, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from telegram.constants import ParseMode

# Import from base and core modules
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from .base import CommandHandler
from core.utils import (
    keyboard_builder, formatter, notification_manager, 
    validate_user_input, is_admin, has_permission
)
from core.config import EMOJIS, CONVERSATION_STATES, USER_ROLES
from core.database import db

logger = logging.getLogger(__name__)


class StartCommand(CommandHandler):
    """Handle /start command with user registration."""
    
    def __init__(self):
        super().__init__("start")
    
    async def _handle_command(
        self, 
        update: Update, 
        context: ContextTypes.DEFAULT_TYPE, 
        user: Any
    ) -> Any:
        """Handle start command."""
        # Check if user already exists
        if user:
            await self._show_main_menu(update, context, user)
            return ConversationHandler.END
        
        # Start registration process
        await self._start_registration(update, context)
        return CONVERSATION_STATES['GET_FULL_NAME']
    
    async def _start_registration(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Start user registration process."""
        welcome_message = (
            f"{EMOJIS['new']} **مرحباً بك في بوت شبكات اليمن!**\n\n"
            "أهلاً وسهلاً بك في البوت الأفضل لشراء كروت الشبكات.\n"
            "لنبدأ بالتسجيل:\n\n"
            "**الخطوة الأولى:** أرسل اسمك الكامل"
        )
        
        await self._send_message(update, context, welcome_message)
    
    async def _show_main_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Any) -> None:
        """Show main menu for existing user."""
        welcome_back = (
            f"{EMOJIS['home']} **مرحباً بعودتك {user.full_name}!**\n\n"
            f"رصيدك الحالي: {formatter.format_currency(user.balance)}\n"
            f"دورك: {USER_ROLES.get(user.role, user.role)}\n\n"
            "اختر من القائمة أدناه:"
        )
        
        keyboard = keyboard_builder.main_menu(user.role)
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await self._send_message(update, context, welcome_back, reply_markup)


class MenuCommand(CommandHandler):
    """Handle /menu command to show main menu."""
    
    def __init__(self):
        super().__init__("menu")
    
    async def _handle_command(
        self, 
        update: Update, 
        context: ContextTypes.DEFAULT_TYPE, 
        user: Any
    ) -> Any:
        """Show main menu."""
        await self._show_main_menu(update, context, user)
        return ConversationHandler.END
    
    async def _show_main_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Any) -> None:
        """Show main menu."""
        message = (
            f"{EMOJIS['home']} **القائمة الرئيسية**\n\n"
            f"مرحباً {user.full_name}!\n"
            f"رصيدك: {formatter.format_currency(user.balance)}\n\n"
            "اختر من الخيارات أدناه:"
        )
        
        keyboard = keyboard_builder.main_menu(user.role)
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await self._send_message(update, context, message, reply_markup)


class WalletCommand(CommandHandler):
    """Handle /wallet command to show wallet information."""
    
    def __init__(self):
        super().__init__("wallet")
    
    async def _handle_command(
        self, 
        update: Update, 
        context: ContextTypes.DEFAULT_TYPE, 
        user: Any
    ) -> Any:
        """Show wallet information."""
        await self._show_wallet(update, context, user)
        return ConversationHandler.END
    
    async def _show_wallet(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Any) -> None:
        """Display wallet information."""
        message = (
            f"{EMOJIS['wallet']} **محفظتك المطورة**\n\n"
            f"**الاسم:** {user.full_name}\n"
            f"**رقم المحفظة:** {user.wallet_number}\n"
            f"**الرصيد الحالي:** {formatter.format_currency(user.balance)}\n"
            f"**إجمالي المشتريات:** {formatter.format_currency(user.total_spent)}\n"
            f"**عدد الإحالات:** {user.total_referrals}\n"
            f"**آخر نشاط:** {formatter.format_datetime(user.last_activity)}\n\n"
            "**العمليات السريعة:**"
        )
        
        keyboard = [
            [{'text': f"{EMOJIS['transfer']} تحويل رصيد", 'callback_data': 'transfer_balance'}],
            [{'text': f"{EMOJIS['stats']} كشف حساب", 'callback_data': 'account_statement'}],
            [{'text': f"{EMOJIS['back']} رجوع", 'callback_data': 'main_menu'}]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await self._send_message(update, context, message, reply_markup)


class BalanceCommand(CommandHandler):
    """Handle /balance command to show balance and transactions."""
    
    def __init__(self):
        super().__init__("balance")
    
    async def _handle_command(
        self, 
        update: Update, 
        context: ContextTypes.DEFAULT_TYPE, 
        user: Any
    ) -> Any:
        """Show balance and recent transactions."""
        await self._show_balance(update, context, user)
        return ConversationHandler.END
    
    async def _show_balance(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Any) -> None:
        """Display balance and transactions."""
        message = (
            f"{EMOJIS['money']} **رصيدك والمعاملات**\n\n"
            f"**الرصيد الحالي:** {formatter.format_currency(user.balance)}\n"
            f"**إجمالي المشتريات:** {formatter.format_currency(user.total_spent)}\n"
            f"**عدد المعاملات:** {user.total_purchases}\n\n"
            "**آخر 5 معاملات:**\n"
        )
        
        # Get recent transactions
        try:
            transactions = db.get_user_transactions(user.id, limit=5)
            if transactions:
                for i, trans in enumerate(transactions, 1):
                    message += f"{i}. {trans['transaction_type']}: {formatter.format_currency(trans['amount'])}\n"
            else:
                message += "لا توجد معاملات سابقة\n"
        except Exception as e:
            logger.error(f"Failed to get transactions: {e}")
            message += "لا يمكن عرض المعاملات حالياً\n"
        
        keyboard = [
            [{'text': f"{EMOJIS['stats']} كشف حساب كامل", 'callback_data': 'full_statement'}],
            [{'text': f"{EMOJIS['back']} رجوع", 'callback_data': 'main_menu'}]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await self._send_message(update, context, message, reply_markup)


class HelpCommand(CommandHandler):
    """Handle /help command to show help information."""
    
    def __init__(self):
        super().__init__("help")
    
    async def _handle_command(
        self, 
        update: Update, 
        context: ContextTypes.DEFAULT_TYPE, 
        user: Any
    ) -> Any:
        """Show help information."""
        await self._show_help(update, context, user)
        return ConversationHandler.END
    
    async def _show_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Any) -> None:
        """Display help information."""
        help_text = (
            f"{EMOJIS['info']} **مركز المساعدة**\n\n"
            "**الأوامر المتاحة:**\n"
            "/start - بدء البوت والتسجيل\n"
            "/menu - القائمة الرئيسية\n"
            "/wallet - عرض المحفظة\n"
            "/balance - عرض الرصيد والمعاملات\n"
            "/buy - شراء كروت الشبكة\n"
            "/transfer - تحويل رصيد\n"
            "/help - هذه المساعدة\n\n"
            "**للتواصل مع الدعم:**\n"
            "يمكنك التواصل مع فريق الدعم عبر:\n"
            "📧 البريد الإلكتروني\n"
            "📱 رقم الهاتف\n\n"
            "**نصائح للاستخدام:**\n"
            "• تأكد من صحة رقم الهاتف\n"
            "• احتفظ برقم المحفظة\n"
            "• تحقق من المعاملات قبل التأكيد"
        )
        
        keyboard = [
            [{'text': f"{EMOJIS['back']} رجوع", 'callback_data': 'main_menu'}],
            [{'text': f"{EMOJIS['info']} المزيد من المساعدة", 'callback_data': 'more_help'}]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await self._send_message(update, context, help_text, reply_markup)


class AdminCommand(CommandHandler):
    """Handle /admin command for admin panel."""
    
    def __init__(self):
        super().__init__("admin")
    
    async def _handle_command(
        self, 
        update: Update, 
        context: ContextTypes.DEFAULT_TYPE, 
        user: Any
    ) -> Any:
        """Show admin panel if user has permissions."""
        if not is_admin(user.role):
            await self._send_message(
                update, 
                context, 
                f"{EMOJIS['error']} ليس لديك صلاحية للوصول للوحة الإدارة"
            )
            return ConversationHandler.END
        
        await self._show_admin_panel(update, context, user)
        return ConversationHandler.END
    
    async def _show_admin_panel(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Any) -> None:
        """Display admin panel."""
        message = (
            f"{EMOJIS['admin']} **لوحة الإدارة**\n\n"
            f"مرحباً {user.full_name}\n"
            f"دورك: {USER_ROLES.get(user.role, user.role)}\n\n"
            "**الصلاحيات المتاحة:**\n"
        )
        
        # Show available permissions
        permissions = []
        if has_permission(user.role, 'create_users'):
            permissions.append("إنشاء مستخدمين")
        if has_permission(user.role, 'manage_balance'):
            permissions.append("إدارة الأرصدة")
        if has_permission(user.role, 'view_reports'):
            permissions.append("عرض التقارير")
        if has_permission(user.role, 'manage_promotions'):
            permissions.append("إدارة العروض")
        
        for perm in permissions:
            message += f"• {perm}\n"
        
        keyboard = [
            [{'text': f"{EMOJIS['stats']} إحصائيات النظام", 'callback_data': 'system_stats'}],
            [{'text': f"{EMOJIS['user']} إدارة المستخدمين", 'callback_data': 'manage_users'}],
            [{'text': f"{EMOJIS['money']} إدارة الأرصدة", 'callback_data': 'manage_balances'}],
            [{'text': f"{EMOJIS['back']} رجوع", 'callback_data': 'main_menu'}]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await self._send_message(update, context, message, reply_markup)


class CancelCommand(CommandHandler):
    """Handle /cancel command to cancel current operation."""
    
    def __init__(self):
        super().__init__("cancel")
    
    async def _handle_command(
        self, 
        update: Update, 
        context: ContextTypes.DEFAULT_TYPE, 
        user: Any
    ) -> Any:
        """Cancel current operation and return to main menu."""
        # Clear conversation state
        if 'conversation_state' in context.user_data:
            del context.user_data['conversation_state']
        
        await self._send_message(
            update, 
            context, 
            f"{EMOJIS['cancel']} تم إلغاء العملية الحالية"
        )
        
        # Show main menu
        await self._show_main_menu(update, context, user)
        return ConversationHandler.END
    
    async def _show_main_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Any) -> None:
        """Show main menu."""
        message = (
            f"{EMOJIS['home']} **القائمة الرئيسية**\n\n"
            "اختر من الخيارات أدناه:"
        )
        
        keyboard = keyboard_builder.main_menu(user.role)
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await self._send_message(update, context, message, reply_markup)


# Command handler instances
start_handler = StartCommand()
menu_handler = MenuCommand()
wallet_handler = WalletCommand()
balance_handler = BalanceCommand()
help_handler = HelpCommand()
admin_handler = AdminCommand()
cancel_handler = CancelCommand()


# Command handler mapping
COMMAND_HANDLERS = {
    'start': start_handler.handle,
    'menu': menu_handler.handle,
    'wallet': wallet_handler.handle,
    'balance': balance_handler.handle,
    'help': help_handler.handle,
    'admin': admin_handler.handle,
    'cancel': cancel_handler.handle,
}