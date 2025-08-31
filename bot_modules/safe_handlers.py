#!/usr/bin/env python3
"""
Safe Handlers - معالجات آمنة
تحتوي على دوال مساعدة آمنة للتعامل مع callback queries ومعالجة الأخطاء
"""

import logging
from typing import Optional, Dict, Any
from telegram import Update, InlineKeyboardMarkup
from telegram.ext import CallbackContext

logger = logging.getLogger(__name__)

async def safe_get_user_from_update(update: Update) -> Optional[int]:
    """الحصول على user_id بشكل آمن من Update"""
    try:
        if update.callback_query:
            return update.callback_query.from_user.id
        elif update.message:
            return update.message.from_user.id
        elif update.effective_user:
            return update.effective_user.id
        else:
            return None
    except Exception as e:
        logger.error(f"Error getting user ID from update: {e}")
        return None

async def safe_answer_query(query) -> bool:
    """الرد على callback query بشكل آمن"""
    try:
        if query:
            await query.answer()
            return True
        return False
    except Exception as e:
        logger.warning(f"Failed to answer query: {e}")
        return False

async def safe_edit_message(update: Update, text: str, 
                          reply_markup: InlineKeyboardMarkup = None,
                          parse_mode: str = 'Markdown') -> bool:
    """تحديث الرسالة بشكل آمن"""
    try:
        if update.callback_query:
            await update.callback_query.edit_message_text(
                text, reply_markup=reply_markup, parse_mode=parse_mode
            )
            return True
        elif update.message:
            await update.message.reply_text(
                text, reply_markup=reply_markup, parse_mode=parse_mode
            )
            return True
        else:
            logger.warning("No callback_query or message found in update")
            return False
    except Exception as e:
        logger.error(f"Failed to edit/send message: {e}")
        return False

async def safe_send_error_message(update: Update, context: CallbackContext,
                                error_text: str, 
                                reply_markup: InlineKeyboardMarkup = None) -> bool:
    """إرسال رسالة خطأ بشكل آمن"""
    try:
        return await safe_edit_message(update, error_text, reply_markup)
    except Exception as e:
        logger.error(f"Failed to send error message: {e}")
        return False

def safe_get_user_field(user: Dict, field: str, default: Any = 'غير محدد') -> Any:
    """الحصول على حقل من بيانات المستخدم بشكل آمن"""
    if not user:
        return default
    
    if isinstance(user, dict):
        return user.get(field, default)
    else:
        # إذا كان user هو sqlite3.Row
        try:
            return user[field] if field in user.keys() else default
        except:
            return default

def safe_format_balance(balance: Any) -> str:
    """تنسيق الرصيد بشكل آمن"""
    try:
        if balance is None:
            return "0.00"
        return f"{float(balance):,.2f}"
    except:
        return "0.00"

def safe_format_user_info(user: Dict) -> Dict[str, str]:
    """تنسيق معلومات المستخدم بشكل آمن"""
    if not user:
        return {
            'full_name': 'غير محدد',
            'phone': 'غير محدد',
            'balance': '0.00',
            'wallet_number': 'غير محدد',
            'role': 'customer'
        }
    
    return {
        'full_name': safe_get_user_field(user, 'full_name', 'غير محدد'),
        'phone': safe_get_user_field(user, 'phone', 'غير محدد'),
        'balance': safe_format_balance(safe_get_user_field(user, 'balance', 0)),
        'wallet_number': safe_get_user_field(user, 'wallet_number', 'غير محدد'),
        'role': safe_get_user_field(user, 'role', 'customer'),
        'is_active': safe_get_user_field(user, 'is_active', 0),
        'telegram_id': safe_get_user_field(user, 'telegram_id', 0)
    }

async def handle_callback_safely(update: Update, context: CallbackContext,
                                handler_func, handler_name: str = "العملية") -> bool:
    """تنفيذ معالج callback بشكل آمن"""
    try:
        # التحقق من وجود callback_query
        if not update.callback_query:
            logger.warning(f"No callback_query in {handler_name}")
            return False
        
        # الرد على القائمة
        await safe_answer_query(update.callback_query)
        
        # تنفيذ المعالج
        await handler_func(update, context)
        return True
        
    except Exception as e:
        logger.error(f"Error in {handler_name}: {e}")
        
        # إرسال رسالة خطأ للمستخدم
        from bot_modules.enhanced_error_messages import ErrorMessages
        error_msg = ErrorMessages.custom_error(
            handler_name,
            f"حدث خطأ أثناء {handler_name}",
            "يرجى إعادة المحاولة أو التواصل مع الدعم الفني",
            "HANDLER_ERROR"
        )
        
        await safe_send_error_message(update, context, error_msg)
        return False