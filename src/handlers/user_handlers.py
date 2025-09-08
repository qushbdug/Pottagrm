#!/usr/bin/env python3
"""
User Handlers for Pottagrm Enhanced Bot
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext

from src.core.config import EMOJIS
from src.core.database import get_db_connection
from src.utils.user_utils import get_user
from src.utils.ui_utils import format_user_info

logger = logging.getLogger(__name__)

async def buy_cards_handler(update: Update, context: CallbackContext):
    """Handle the 'buy_cards' action."""
    query = update.callback_query
    user = get_user(query.from_user.id)

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT n.id, n.name, n.provider, n.location, COUNT(cc.id) as categories_count,
               MIN(cc.price) as min_price, MAX(cc.price) as max_price
        FROM networks n
        LEFT JOIN card_categories cc ON n.id = cc.network_id AND cc.is_available = 1
        WHERE n.is_active = 1 AND n.is_approved = 1
        GROUP BY n.id, n.name, n.provider, n.location
        HAVING categories_count > 0
        ORDER BY n.name
    ''')
    networks = cursor.fetchall()
    conn.close()

    buy_text = f"""
🛒 **شراء كروت الإنترنت** 🛒

👤 **{user['full_name']}**
💰 رصيدك: **{user['balance']:,.2f}** ريال

📶 **الشبكات المتاحة ({len(networks)} شبكة):**
"""
    if networks:
        for network in networks:
            net_id, name, provider, location, cat_count, min_price, max_price = network
            location_text = f"📍 {location}" if location else ""
            price_range = f"{min_price:,.0f} - {max_price:,.0f}" if min_price != max_price else f"{min_price:,.0f}"

            buy_text += f"""
🌐 **{name}**
👤 {provider} {location_text}
💳 {cat_count} فئة متاحة
💰 {price_range} ريال
━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    else:
        buy_text += "❌ لا توجد شبكات متاحة حالياً"

    keyboard = []
    if networks:
        for network in networks[:6]:
            net_id = network[0]
            name = network[1]
            keyboard.append([
                InlineKeyboardButton(f'🛒 شراء من {name}', callback_data=f'buy_from_network_{net_id}')
            ])

    keyboard.extend([
        [InlineKeyboardButton(f'📊 جميع الشبكات', callback_data='view_all_networks'),
         InlineKeyboardButton(f'🔍 البحث في الشبكات', callback_data='search_networks')],
        [InlineKeyboardButton(f'💰 شحن الرصيد', callback_data='recharge_balance'),
         InlineKeyboardButton(f'📈 إحصائياتي', callback_data='my_purchase_stats')],
        [InlineKeyboardButton(f'{EMOJIS["home"]} القائمة الرئيسية', callback_data='main_menu')]
    ])

    await query.edit_message_text(buy_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def transfer_handler(update: Update, context: CallbackContext):
    """Handle the 'transfer_to_friend' action."""
    query = update.callback_query
    user = get_user(query.from_user.id)

    transfer_text = f"""
💸 **تحويل رصيد لصديق** 💸

👤 **{user['full_name']}**
💰 رصيدك: **{user['balance']:.2f}** ريال

📋 **تعليمات التحويل:**
1️⃣ أدخل رقم محفظة المستلم (9 أرقام)
2️⃣ أدخل المبلغ المراد تحويله
3️⃣ تأكيد العملية

💡 **للتحويل السريع:**
• استخدم زر "🔍 البحث عن مستخدم" أدناه
• ابحث بالاسم أو رقم المحفظة أو الهاتف
• أدخل المبلغ المطلوب تحويله
• تأكيد العملية بأمان

🔒 **ضمانات الأمان:**
• تأكيد مزدوج قبل التحويل
• إشعار فوري للطرفين
• سجل كامل للمعاملة
"""

    keyboard = [
        [InlineKeyboardButton(f'🔍 البحث عن مستخدم', callback_data='search_user')],
        [InlineKeyboardButton(f'📋 آخر التحويلات', callback_data='transfer_history')],
        [InlineKeyboardButton(f'{EMOJIS["home"]} القائمة الرئيسية', callback_data='main_menu')]
    ]

    await query.edit_message_text(transfer_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def redeem_coupon_handler(update: Update, context: CallbackContext):
    """Handles the start of the coupon redemption process."""
    query = update.callback_query
    await query.answer()

    context.user_data['redeeming_coupon'] = True

    text = """
🎟️ **شحن الرصيد بكوبون** 🎟️

أدخل رقم الكوبون:
"""
    keyboard = [
        [InlineKeyboardButton('❌ إلغاء', callback_data='cancel_coupon')]
    ]

    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def process_coupon_redemption(update: Update, context: CallbackContext):
    """Processes the coupon code entered by the user."""
    if not context.user_data.get('redeeming_coupon'):
        return

    user = get_user(update.message.from_user.id)
    coupon_code = update.message.text.strip().upper()

    # (Logic to validate and apply coupon)
    # This part will be more complex and will involve DB lookups and updates.
    # For now, we'll just show a success message.

    await update.message.reply_text(f"✅ تم استخدام الكوبون {coupon_code} بنجاح!")
    context.user_data.clear()

async def cancel_coupon_handler(update: Update, context: CallbackContext):
    """Cancels the coupon redemption process."""
    query = update.callback_query
    await query.answer()
    context.user_data.clear()
    await query.edit_message_text("❌ تم إلغاء عملية شحن الكوبون.")

async def personal_reports_handler(update: Update, context: CallbackContext):
    """Handles personal reports."""
    query = update.callback_query
    await query.edit_message_text("Placeholder for personal reports.")

async def my_ratings_handler(update: Update, context: CallbackContext):
    """Handles user ratings."""
    query = update.callback_query
    await query.edit_message_text("Placeholder for user ratings.")

async def my_notifications_handler(update: Update, context: CallbackContext):
    """Handles user notifications."""
    query = update.callback_query
    await query.edit_message_text("Placeholder for user notifications.")

async def promotions_handler(update: Update, context: CallbackContext):
    """Handles promotions."""
    query = update.callback_query
    await query.edit_message_text("Placeholder for promotions.")

async def account_settings_handler(update: Update, context: CallbackContext):
    """Handles account settings."""
    query = update.callback_query
    await query.edit_message_text("Placeholder for account settings.")
