#!/usr/bin/env python3
"""
Admin Handlers for Pottagrm Enhanced Bot
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext

from src.core.config import EMOJIS
from src.core.database import get_db_connection
from src.utils.user_utils import get_user, update_user_activity

logger = logging.getLogger(__name__)

async def admin_panel_handler(update: Update, context: CallbackContext):
    """Handle admin panel access."""
    user = get_user(update.effective_user.id)
    if not user or user['role'] not in ['admin', 'super_admin']:
        if update.message:
            await update.message.reply_text(f"{EMOJIS['error']} ليس لديك صلاحية للوصول لهذه اللوحة.")
        else:
            await update.callback_query.edit_message_text(f"{EMOJIS['error']} ليس لديك صلاحية للوصول لهذه اللوحة.")
        return

    update_user_activity(user['id'])

    if user['role'] == 'super_admin':
        await show_super_admin_panel(update, context, user)
    else:
        await show_admin_panel(update, context, user)

async def show_super_admin_panel(update: Update, context: CallbackContext, user):
    """Show super admin control panel."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT COUNT(*) FROM users')
    total_users = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(*) FROM users WHERE is_active = 1')
    active_users = cursor.fetchone()[0]
    cursor.execute('SELECT SUM(balance) FROM users')
    total_balance = cursor.fetchone()[0] or 0
    cursor.execute('SELECT COUNT(*) FROM users WHERE role = "supplier" AND is_active = 0')
    pending_suppliers = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(*) FROM transactions')
    total_transactions = cursor.fetchone()[0]

    conn.close()

    panel_text = f"""
👑 **لوحة المشرف الأعلى** 👑

{EMOJIS['user']} مرحباً **{user['full_name']}**

📊 **إحصائيات المنصة:**
👥 إجمالي المستخدمين: **{total_users}**
✅ المستخدمين النشطين: **{active_users}**
💰 إجمالي الأرصدة: **{total_balance:.2f}** ريال
⏳ مزودين في الانتظار: **{pending_suppliers}**
💸 إجمالي المعاملات: **{total_transactions}**

🔥 **اختر العملية المطلوبة:**
"""

    keyboard = [
        [InlineKeyboardButton(f'👥 إدارة العملاء', callback_data='customer_dashboard'),
         InlineKeyboardButton(f'👑 إدارة المشرفين', callback_data='admin_dashboard')],
        [InlineKeyboardButton(f'🎁 إضافة عروض', callback_data='admin_add_offers'),
         InlineKeyboardButton(f'✅ تفعيل مزودين', callback_data='super_activate_suppliers')],
        [InlineKeyboardButton(f'🎟️ إنشاء كوبونات', callback_data='super_create_coupons')],
        [InlineKeyboardButton(f'{EMOJIS["home"]} العودة للقائمة', callback_data='main_menu')]
    ]

    if update.callback_query:
        await update.callback_query.edit_message_text(panel_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    else:
        await update.message.reply_text(panel_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def show_admin_panel(update: Update, context: CallbackContext, user):
    """Show regular admin control panel."""
    # Placeholder for regular admin panel
    panel_text = f"أهلاً بك في لوحة تحكم المشرف, {user['full_name']}"
    keyboard = [
        [InlineKeyboardButton(f'👥 إدارة العملاء', callback_data='customer_dashboard')],
        [InlineKeyboardButton(f'{EMOJIS["home"]} العودة للقائمة', callback_data='main_menu')]
    ]
    if update.callback_query:
        await update.callback_query.edit_message_text(panel_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    else:
        await update.message.reply_text(panel_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

# Placeholder handlers for other admin actions
async def customer_dashboard_handler(update: Update, context: CallbackContext):
    await update.callback_query.edit_message_text("Placeholder for customer dashboard.")

async def admin_dashboard_handler(update: Update, context: CallbackContext):
    await update.callback_query.edit_message_text("Placeholder for admin dashboard.")

async def admin_add_offers_handler(update: Update, context: CallbackContext):
    await update.callback_query.edit_message_text("Placeholder for adding offers.")

async def activate_suppliers_handler(update: Update, context: CallbackContext):
    await update.callback_query.edit_message_text("Placeholder for activating suppliers.")

async def create_coupons_handler(update: Update, context: CallbackContext):
    await update.callback_query.edit_message_text("Placeholder for creating coupons.")
