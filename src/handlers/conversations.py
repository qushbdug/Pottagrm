#!/usr/bin/env python3
"""
Conversation Handlers for Yemen Net Bot
Professional conversation management with state handling.
"""

import logging
from typing import Any, Dict
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, ConversationHandler
from telegram.constants import ParseMode

from .base import ConversationHandler as BaseConversationHandler
from ..core.utils import (
    keyboard_builder, formatter, security, validate_user_input,
    error_handler, notification_manager
)
from ..core.config import EMOJIS, CONVERSATION_STATES, USER_ROLES
from ..core.database import db

logger = logging.getLogger(__name__)


class RegistrationConversation(BaseConversationHandler):
    """Handle user registration conversation."""
    
    def __init__(self):
        super().__init__({
            'GET_FULL_NAME': CONVERSATION_STATES['GET_FULL_NAME'],
            'GET_PHONE': CONVERSATION_STATES['GET_PHONE'],
            'CHOOSE_ROLE': CONVERSATION_STATES['CHOOSE_ROLE']
        })
    
    def get_handler(self) -> ConversationHandler:
        """Get conversation handler for registration."""
        return ConversationHandler(
            entry_points=[],  # Entry points are handled by command handlers
            states={
                CONVERSATION_STATES['GET_FULL_NAME']: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_full_name)
                ],
                CONVERSATION_STATES['GET_PHONE']: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_phone)
                ],
                CONVERSATION_STATES['CHOOSE_ROLE']: [
                    CallbackQueryHandler(self._handle_role_selection, pattern='^role_')
                ]
            },
            fallbacks=[CommandHandler('cancel', self._cancel_registration)]
        )
    
    async def _handle_conversation_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Start registration conversation."""
        await self._ask_for_full_name(update, context)
        return CONVERSATION_STATES['GET_FULL_NAME']
    
    async def _handle_conversation_continue(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Continue registration conversation."""
        current_state = self._get_state(context)
        
        if current_state == CONVERSATION_STATES['GET_FULL_NAME']:
            return await self._handle_full_name(update, context)
        elif current_state == CONVERSATION_STATES['GET_PHONE']:
            return await self._handle_phone(update, context)
        elif current_state == CONVERSATION_STATES['CHOOSE_ROLE']:
            return await self._handle_role_selection(update, context)
        else:
            return ConversationHandler.END
    
    async def _ask_for_full_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Ask user for full name."""
        message = (
            f"{EMOJIS['user']} **الخطوة الأولى: الاسم الكامل**\n\n"
            "أرسل اسمك الكامل كما يظهر في الوثائق الرسمية.\n"
            "مثال: أحمد محمد علي"
        )
        
        await self._send_message(update, context, message)
    
    async def _handle_full_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle full name input."""
        try:
            full_name = validate_user_input(update.message.text, 'text')
            
            # Store in context
            context.user_data['full_name'] = full_name
            
            # Move to next state
            self._set_state(context, CONVERSATION_STATES['GET_PHONE'])
            
            # Ask for phone number
            await self._ask_for_phone(update, context)
            
            return CONVERSATION_STATES['GET_PHONE']
            
        except Exception as e:
            error_message = error_handler.handle_validation_error(e)
            await self._send_message(update, context, error_message)
            return CONVERSATION_STATES['GET_FULL_NAME']
    
    async def _ask_for_phone(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Ask user for phone number."""
        message = (
            f"{EMOJIS['phone']} **الخطوة الثانية: رقم الهاتف**\n\n"
            "أرسل رقم هاتفك اليمني.\n"
            "يمكنك إرساله بأي من هذه الصيغ:\n"
            "• +967XXXXXXXXX\n"
            "• 967XXXXXXXXX\n"
            "• XXXXXXXXX"
        )
        
        await self._send_message(update, context, message)
    
    async def _handle_phone(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle phone number input."""
        try:
            phone = validate_user_input(update.message.text, 'phone')
            
            # Check if phone already exists
            existing_user = db.get_user_by_phone(phone)
            if existing_user:
                await self._send_message(
                    update, 
                    context, 
                    f"{EMOJIS['error']} رقم الهاتف مسجل مسبقاً. استخدم رقم آخر أو تواصل مع الدعم."
                )
                return CONVERSATION_STATES['GET_PHONE']
            
            # Store in context
            context.user_data['phone'] = phone
            
            # Move to next state
            self._set_state(context, CONVERSATION_STATES['CHOOSE_ROLE'])
            
            # Ask for role selection
            await self._ask_for_role(update, context)
            
            return CONVERSATION_STATES['CHOOSE_ROLE']
            
        except Exception as e:
            error_message = error_handler.handle_validation_error(e)
            await self._send_message(update, context, error_message)
            return CONVERSATION_STATES['GET_PHONE']
    
    async def _ask_for_role(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Ask user to choose role."""
        message = (
            f"{EMOJIS['info']} **الخطوة الثالثة: اختيار الدور**\n\n"
            "اختر دورك في النظام:\n\n"
            "**العميل:** شراء كروت الشبكة واستخدام الخدمات\n"
            "**الوكيل:** بيع الكروت للعملاء مع عمولة\n"
            "**المزود:** توفير كروت الشبكة للبيع"
        )
        
        keyboard = [
            [{'text': f"{EMOJIS['user']} عميل", 'callback_data': 'role_customer'}],
            [{'text': f"{EMOJIS['user']} وكيل", 'callback_data': 'role_agent'}],
            [{'text': f"{EMOJIS['user']} مزود", 'callback_data': 'role_supplier'}]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await self._send_message(update, context, message, reply_markup)
    
    async def _handle_role_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle role selection."""
        try:
            query = update.callback_query
            await query.answer()
            
            # Extract role from callback data
            role = query.data.replace('role_', '')
            
            if role not in USER_ROLES:
                await self._send_message(
                    update, 
                    context, 
                    f"{EMOJIS['error']} دور غير صحيح. يرجى الاختيار مرة أخرى."
                )
                return CONVERSATION_STATES['CHOOSE_ROLE']
            
            # Store in context
            context.user_data['role'] = role
            
            # Complete registration
            return await self._complete_registration(update, context)
            
        except Exception as e:
            logger.error(f"Error handling role selection: {e}")
            await self._send_message(
                update, 
                context, 
                f"{EMOJIS['error']} حدث خطأ في اختيار الدور. يرجى المحاولة مرة أخرى."
            )
            return CONVERSATION_STATES['CHOOSE_ROLE']
    
    async def _complete_registration(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Complete user registration."""
        try:
            # Get user data from context
            full_name = context.user_data['full_name']
            phone = context.user_data['phone']
            role = context.user_data['role']
            telegram_id = update.effective_user.id
            
            # Create user in database
            user = db.create_user(telegram_id, full_name, phone, role)
            
            if not user:
                await self._send_message(
                    update, 
                    context, 
                    f"{EMOJIS['error']} فشل في إنشاء الحساب. يرجى المحاولة مرة أخرى أو التواصل مع الدعم."
                )
                return ConversationHandler.END
            
            # Clear conversation data
            context.user_data.clear()
            
            # Send success message
            success_message = (
                f"{EMOJIS['success']} **تم التسجيل بنجاح!**\n\n"
                f"**مرحباً {user.full_name}!**\n"
                f"**رقم المحفظة:** {user.wallet_number}\n"
                f"**الدور:** {USER_ROLES.get(user.role, user.role)}\n"
                f"**رصيدك:** {formatter.format_currency(user.balance)}\n\n"
                "يمكنك الآن استخدام جميع خدمات البوت!"
            )
            
            # Show main menu
            keyboard = keyboard_builder.main_menu(user.role)
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await self._send_message(update, context, success_message, reply_markup)
            
            logger.info(f"User {user.id} registered successfully with role {role}")
            return ConversationHandler.END
            
        except Exception as e:
            logger.error(f"Error completing registration: {e}")
            await self._send_message(
                update, 
                context, 
                f"{EMOJIS['error']} حدث خطأ في إكمال التسجيل. يرجى المحاولة مرة أخرى."
            )
            return ConversationHandler.END
    
    async def _cancel_registration(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Cancel registration process."""
        # Clear conversation data
        context.user_data.clear()
        
        await self._send_message(
            update, 
            context, 
            f"{EMOJIS['cancel']} تم إلغاء عملية التسجيل."
        )
        
        return ConversationHandler.END
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle incoming message based on current state."""
        current_state = self._get_state(context)
        
        if current_state == CONVERSATION_STATES['GET_FULL_NAME']:
            return await self._handle_full_name(update, context)
        elif current_state == CONVERSATION_STATES['GET_PHONE']:
            return await self._handle_phone(update, context)
        else:
            return ConversationHandler.END


# Import required modules for the conversation handler
from telegram.ext import MessageHandler, CallbackQueryHandler, CommandHandler, filters