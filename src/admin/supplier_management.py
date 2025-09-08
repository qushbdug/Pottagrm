#!/usr/bin/env python3
"""
Supplier Management Functions for Admin
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext

from src.core.config import EMOJIS
from src.core.database import get_db_connection
from src.utils.user_utils import get_user
from src.utils.system_utils import log_system_action, log_activity
from src.utils.notification_utils import send_smart_notification

logger = logging.getLogger(__name__)

async def activate_suppliers_handler(update: Update, context: CallbackContext):
    """Handle supplier activation for super admin"""
    query = update.callback_query
    await query.answer()

    user = get_user(query.from_user.id)
    if not user or user['role'] != 'super_admin':
        await query.edit_message_text(f"{EMOJIS['error']} ليس لديك صلاحية لهذه العملية.")
        return

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM users
        WHERE role = 'supplier' AND is_active = 0
        ORDER BY created_at DESC
        LIMIT 10
    ''')
    pending_suppliers = cursor.fetchall()
    conn.close()

    if not pending_suppliers:
        text = "✅ لا توجد طلبات تفعيل مزودين"
        keyboard = [
            [InlineKeyboardButton(f'👑 لوحة المشرف الأعلى', callback_data='admin_panel')]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        return

    text = f"✅ **تفعيل حسابات المزودين** ✅\n\n📋 **المزودين في الانتظار:** {len(pending_suppliers)}\n\n👇 **اختر المزود للتفعيل:**"
    keyboard = []
    for supplier in pending_suppliers:
        supplier_info = f"{supplier['full_name'][:15]}... | {supplier['phone']}"
        keyboard.append([
            InlineKeyboardButton(f"✅ {supplier_info}", callback_data=f'activate_supplier_{supplier["id"]}')
        ])

    keyboard.extend([
        [InlineKeyboardButton(f'✅ تفعيل الجميع', callback_data='activate_all_suppliers')],
        [InlineKeyboardButton(f'👑 لوحة المشرف الأعلى', callback_data='admin_panel')]
    ])

    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def activate_single_supplier(update: Update, context: CallbackContext):
    """Activate a single supplier."""
    query = update.callback_query
    supplier_id = int(query.data.split('_')[-1])

    user = get_user(query.from_user.id)
    if not user or user['role'] != 'super_admin':
        await query.edit_message_text(f"{EMOJIS['error']} ليس لديك صلاحية لهذه العملية.")
        return

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM users WHERE id = ? AND role = "supplier"', (supplier_id,))
    supplier = cursor.fetchone()

    if not supplier:
        await query.edit_message_text(f"{EMOJIS['error']} لم يتم العثور على المزود.")
        conn.close()
        return

    cursor.execute('UPDATE users SET is_active = 1 WHERE id = ?', (supplier_id,))
    log_system_action(user['id'], 'supplier_activation', f'Activated supplier {supplier["full_name"]} (ID: {supplier_id})')

    conn.commit()
    conn.close()

    send_smart_notification(
        supplier['id'],
        'account_activated',
        '🎉 تم تفعيل حسابك كمزود!',
        f'مرحباً {supplier["full_name"]},\n\nتم تفعيل حسابك كمزود بنجاح.',
        'high'
    )

    await query.edit_message_text(f"✅ تم تفعيل المزود {supplier['full_name']} بنجاح!")
    await activate_suppliers_handler(update, context) # Refresh the list

async def activate_all_suppliers(update: Update, context: CallbackContext):
    """Activate all pending suppliers"""
    query = update.callback_query
    user = get_user(query.from_user.id)
    if not user or user['role'] != 'super_admin':
        await query.edit_message_text(f"{EMOJIS['error']} ليس لديك صلاحية لهذه العملية.")
        return

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT id, full_name FROM users WHERE role = "supplier" AND is_active = 0')
    pending_suppliers = cursor.fetchall()

    if not pending_suppliers:
        await query.edit_message_text(f"{EMOJIS['warning']} لا توجد مزودين في الانتظار للتفعيل.")
        conn.close()
        return

    cursor.execute('UPDATE users SET is_active = 1 WHERE role = "supplier" AND is_active = 0')
    activated_count = cursor.rowcount

    supplier_names = [s['full_name'] for s in pending_suppliers]
    log_system_action(user['id'], 'mass_supplier_activation', f'Activated {activated_count} suppliers: {", ".join(supplier_names)}')

    conn.commit()
    conn.close()

    for supplier in pending_suppliers:
        send_smart_notification(
            supplier['id'],
            'account_activated',
            '🎉 تم تفعيل حسابك كمزود!',
            f'مرحباً {supplier["full_name"]},\n\nتم تفعيل حسابك كمزود بنجاح.',
            'high'
        )

    await query.edit_message_text(f"🎉 تم تفعيل {activated_count} من المزودين بنجاح!")
