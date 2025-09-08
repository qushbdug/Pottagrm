#!/usr/bin/env python3
"""
Supplier Handlers for Pottagrm Enhanced Bot
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext

from src.core.config import EMOJIS
from src.core.database import get_db_connection
from src.utils.user_utils import get_user
from src.utils.supplier_utils import get_or_create_supplier_code

logger = logging.getLogger(__name__)

async def supplier_panel_handler(update: Update, context: CallbackContext):
    """Handle the 'supplier_panel' action."""
    query = update.callback_query
    user = get_user(query.from_user.id)

    supplier_code = get_or_create_supplier_code(user['id'])

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) as count FROM networks WHERE supplier_id = ?', (user['id'],))
    networks_count = cursor.fetchone()['count']
    cursor.execute('SELECT COUNT(*) as count FROM network_cards WHERE supplier_id = ? AND is_sold = 0', (user['id'],))
    active_cards = cursor.fetchone()['count']
    cursor.execute('SELECT COUNT(*) as count FROM network_cards WHERE supplier_id = ? AND is_sold = 1', (user['id'],))
    sold_cards = cursor.fetchone()['count']
    cursor.execute('SELECT COUNT(*) as count FROM card_upload_batches WHERE supplier_id = ?', (user['id'],))
    recent_uploads = cursor.fetchone()['count']
    conn.close()

    network_status = "✅ متاحة" if networks_count == 0 else "📶 مُنشأة"

    panel_text = f"""
🏪 **لوحة المزود المطورة** 🏪

👤 **{user['full_name']}**
💰 رصيدك: **{user['balance']:.2f}** ريال
🆔 **معرف المزود: `{supplier_code}`**
🔰 حالة التفعيل: **{'✅ مفعل' if user['is_active'] else '⏳ في الانتظار'}**

📊 **إحصائيات المزود:**
📶 شبكتك: **{network_status}** ({networks_count}/1)
📋 كروت متاحة: **{active_cards}**
✅ كروت مباعة: **{sold_cards}**
📤 رفع حديث (7 أيام): **{recent_uploads}**

🎯 **إدارة الكروت والشبكات:**
💡 **ملاحظة:** يُسمح بشبكة واحدة فقط لكل مزود
"""

    keyboard = [
        [InlineKeyboardButton(f'📶 إدارة الشبكات', callback_data='manage_networks'),
         InlineKeyboardButton(f'📤 رفع كروت', callback_data='upload_cards')],
        [InlineKeyboardButton(f'📊 تقارير الكروت', callback_data='cards_reports'),
         InlineKeyboardButton(f'🎯 فلترة حسب الفئة', callback_data='filter_by_category')],
        [InlineKeyboardButton(f'🔍 البحث في الشبكات', callback_data='search_networks'),
         InlineKeyboardButton(f'📈 إحصائيات المبيعات', callback_data='sales_stats')],
        [InlineKeyboardButton(f'📋 سجل الرفع', callback_data='upload_history'),
         InlineKeyboardButton(f'⚙️ إعدادات المزود', callback_data='supplier_settings')],
        [InlineKeyboardButton(f'{EMOJIS["home"]} القائمة الرئيسية', callback_data='main_menu')]
    ]

    await query.edit_message_text(panel_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

# Placeholders for other supplier handlers
async def manage_networks_handler(update: Update, context: CallbackContext):
    await update.callback_query.edit_message_text("Placeholder for managing networks.")

async def upload_cards_handler(update: Update, context: CallbackContext):
    await update.callback_query.edit_message_text("Placeholder for uploading cards.")

async def cards_reports_handler(update: Update, context: CallbackContext):
    await update.callback_query.edit_message_text("Placeholder for card reports.")
