#!/usr/bin/env python3
"""
Menu Handlers for Pottagrm Enhanced Bot
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext, ConversationHandler

from src.core.config import EMOJIS, USER_ROLES
from src.utils.user_utils import get_user, update_user_activity

logger = logging.getLogger(__name__)

async def show_main_menu(update: Update, context: CallbackContext, role: str = None) -> int:
    """Show main menu based on user role"""
    try:
        if role is None:
            user = get_user(update.effective_user.id)
        else:
            user_data = get_user(update.effective_user.id)
            if user_data:
                user = dict(user_data)
                user['role'] = role
            else:
                user = None

        if not user:
            # This should ideally not be hit if called from registration, but as a fallback:
            from src.handlers.registration_handler import start
            return await start(update, context)

        update_user_activity(user['id'])

        keyboard = create_main_keyboard(user['role'])

        menu_text = f"""
🚀 **بوت كروت الإنترنت اليمني المطور** 🚀

👤 أهلاً وسهلاً **{user['full_name']}**
🏷️ النوع: **{USER_ROLES.get(user['role'], user['role'])}**
💰 رصيدك: **{user['balance']:.2f}** ريال
💳 رقم محفظتك: **{user['wallet_number']}**
⚡ الحالة: **{"✅ مفعل" if user['is_active'] else "⏳ في انتظار التفعيل"}**

🎯 **اختر العملية المطلوبة:**
"""

        if update.callback_query:
            await update.callback_query.edit_message_text(menu_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        else:
            await update.message.reply_text(menu_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

        return ConversationHandler.END

    except Exception as e:
        logger.error(f"Error in show main menu: {e}")
        error_text = "خطأ في عرض القائمة الرئيسية"
        if update.callback_query:
            await update.callback_query.edit_message_text(error_text)
        else:
            await update.message.reply_text(error_text)
        return ConversationHandler.END

def create_main_keyboard(role: str):
    """Create main menu keyboard based on user role"""
    try:
        base_buttons = [
            [InlineKeyboardButton('💳 محفظتي المطورة', callback_data='enhanced_wallet')],
            [InlineKeyboardButton('🛒 شراء كروت', callback_data='buy_cards'),
             InlineKeyboardButton('💸 تحويل رصيد', callback_data='transfer_to_friend')],
            [InlineKeyboardButton('🎟️ شحن بكوبون', callback_data='redeem_coupon'),
             InlineKeyboardButton('🔍 البحث عن شبكات', callback_data='search_networks')],
            [InlineKeyboardButton('📊 تقاريري الشخصية', callback_data='personal_reports'),
             InlineKeyboardButton('🎁 العروض والخصومات', callback_data='promotions')],
            [InlineKeyboardButton('🎟️ كشف الحساب', callback_data='account_statement'),
             InlineKeyboardButton('🔔 إشعاراتي', callback_data='my_notifications')],
            [InlineKeyboardButton('⚙️ إعدادات الحساب', callback_data='account_settings'),
             InlineKeyboardButton('⭐ تقييماتي', callback_data='my_ratings')]
        ]

        if role == 'supplier':
            base_buttons.extend([
                [InlineKeyboardButton('🏪 لوحة المزود', callback_data='supplier_panel'),
                 InlineKeyboardButton('📶 إدارة الشبكات', callback_data='manage_networks')],
                [InlineKeyboardButton('📤 رفع كروت', callback_data='upload_cards'),
                 InlineKeyboardButton('📈 تقارير المبيعات', callback_data='sales_reports')]
            ])
        elif role in ['admin', 'super_admin']:
            base_buttons.extend([
                [InlineKeyboardButton('👑 لوحة الإدارة', callback_data='admin_panel'),
                 InlineKeyboardButton('📊 التقارير التنفيذية', callback_data='executive_reports')]
            ])

            if role == 'super_admin':
                base_buttons.append([
                    InlineKeyboardButton('💰 إدارة الأرصدة', callback_data='admin_wallet'),
                    InlineKeyboardButton('✅ تفعيل مزودين', callback_data='super_activate_suppliers')
                ])

        base_buttons.append([InlineKeyboardButton('❓ المساعدة والدعم', callback_data='help')])

        return base_buttons
    except Exception as e:
        logger.error(f"Error creating main keyboard: {e}")
        return [[InlineKeyboardButton(f'{EMOJIS["error"]} خطأ في القائمة', callback_data='main_menu')]]
