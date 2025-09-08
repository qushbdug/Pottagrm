#!/usr/bin/env python3
"""
Platform Management Functions for Admin
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext

from src.core.config import EMOJIS, QUICK_COMMANDS
from src.core.database import get_db_connection
from src.utils.user_utils import get_user

logger = logging.getLogger(__name__)

async def platform_management_handler(update: Update, context: CallbackContext):
    """Handle platform management for super admin"""
    query = update.callback_query
    await query.answer()

    user = get_user(query.from_user.id)
    if not user or user['role'] != 'super_admin':
        await query.edit_message_text(f"{EMOJIS['error']} ليس لديك صلاحية لهذه العملية.")
        return

    conn = get_db_connection()
    cursor = conn.cursor()
    stats_queries = [
        ('SELECT COUNT(*) as count FROM users WHERE role = "customer"', 'customers'),
        ('SELECT COUNT(*) as count FROM users WHERE role = "supplier"', 'suppliers'),
        ('SELECT COUNT(*) as count FROM networks WHERE is_active = 1', 'active_networks'),
    ]
    stats = {}
    for query_sql, key in stats_queries:
        cursor.execute(query_sql)
        stats[key] = cursor.fetchone()['count']
    conn.close()

    management_text = f"""
🏛️ **إدارة المنصة** 🏛️
...
"""

    keyboard = [
        [InlineKeyboardButton(f'📢 إشعار عام', callback_data='super_broadcast_message')],
        [InlineKeyboardButton(f'🔧 إعدادات النظام', callback_data='super_system_settings')],
        [InlineKeyboardButton(f'💾 النسخ الاحتياطي', callback_data='super_backup')],
        [InlineKeyboardButton(f'👑 لوحة المشرف الأعلى', callback_data='admin_panel')]
    ]

    await query.edit_message_text(management_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def broadcast_message_handler(update: Update, context: CallbackContext):
    """Handle broadcast message for super admin"""
    query = update.callback_query
    await query.answer()

    user = get_user(query.from_user.id)
    if not user or user['role'] != 'super_admin':
        await query.edit_message_text(f"{EMOJIS['error']} ليس لديك صلاحية لهذه العملية.")
        return

    text = "📢 **إرسال رسالة جماعية** 📢\n\nاكتب رسالتك الآن:"
    await query.edit_message_text(text, parse_mode='Markdown')
    context.user_data['awaiting_broadcast'] = True

async def process_broadcast_message(update: Update, context: CallbackContext):
    """Process broadcast message from super admin"""
    if not context.user_data.get('awaiting_broadcast'):
        return

    user = get_user(update.effective_user.id)
    if not user or user['role'] != 'super_admin':
        await update.message.reply_text(f"{EMOJIS['error']} ليس لديك صلاحية لهذه العملية.")
        return

    message_text = update.message.text.strip()

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT telegram_id FROM users WHERE is_active = 1')
    active_users = cursor.fetchall()
    conn.close()

    sent_count = 0
    failed_count = 0

    await update.message.reply_text(f"⏳ جاري إرسال الرسالة لـ {len(active_users)} مستخدم...")

    for target_user in active_users:
        try:
            await context.bot.send_message(chat_id=target_user['telegram_id'], text=message_text)
            sent_count += 1
        except Exception as e:
            failed_count += 1
            logger.warning(f"Failed to send broadcast to user {target_user['telegram_id']}: {e}")

    context.user_data.pop('awaiting_broadcast', None)

    summary_text = f"✅ **تم الإرسال الجماعي!**\n\nSent: {sent_count}\nFailed: {failed_count}"
    await update.message.reply_text(summary_text)

async def update_commands_handler(update: Update, context: CallbackContext):
    """Update bot sidebar commands"""
    query = update.callback_query
    await query.answer()

    user = get_user(query.from_user.id)
    if not user or user['role'] != 'super_admin':
        await query.edit_message_text(f"{EMOJIS['error']} ليس لديك صلاحية لهذه العملية.")
        return

    await context.bot.set_my_commands(QUICK_COMMANDS)
    await query.edit_message_text("✅ تم تحديث أوامر البوت!")

async def system_settings_handler(update: Update, context: CallbackContext):
    await update.callback_query.edit_message_text("Placeholder for system settings.")

async def backup_handler(update: Update, context: CallbackContext):
    await update.callback_query.edit_message_text("Placeholder for backup.")
