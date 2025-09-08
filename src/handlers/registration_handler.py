#!/usr/bin/env python3
"""
Registration Handlers for Pottagrm Enhanced Bot
"""

import logging
import random
import uuid
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext, ConversationHandler

from src.core.config import EMOJIS
from src.core.database import get_db_connection
from src.utils.system_utils import log_activity
from src.utils.user_utils import get_user
from src.handlers.menu_handler import show_main_menu

logger = logging.getLogger(__name__)

# Conversation states
GET_FULL_NAME, GET_PHONE, CHOOSE_ROLE = range(3)

async def start(update: Update, context: CallbackContext) -> int:
    """Handle /start command, entry point for registration."""
    user = get_user(update.effective_user.id)
    if user:
        # User is already registered, show main menu.
        from src.utils.user_utils import update_user_activity
        update_user_activity(user['id'])
        await show_main_menu(update, context, user['role'])
        return ConversationHandler.END
    else:
        # New user, start registration process.
        return await register_new_user(update, context)

async def register_new_user(update: Update, context: CallbackContext) -> int:
    """Start new user registration by asking for full name."""
    welcome_text = f"""
{EMOJIS['fire']} **مرحباً بك في بوت كروت الإنترنت اليمني المطور!** {EMOJIS['fire']}

🚀 **Pottagrm Enhanced v2.1.0**

🌟 **ميزات جديدة ومطورة:**
• 💳 محفظة إلكترونية متقدمة
• 📊 تقارير شخصية مفصلة
• ⭐ نظام تقييمات ومراجعات
• 🔔 إشعارات ذكية مخصصة
• 🎁 نظام عروض وخصومات
• 🔒 أمان محسّن ومشفر

📝 **للمتابعة، يرجى إدخال اسمك الكامل:**
"""
    await update.message.reply_text(welcome_text, parse_mode='Markdown')
    return GET_FULL_NAME

async def get_full_name(update: Update, context: CallbackContext) -> int:
    """Get user's full name and ask for phone number."""
    full_name = update.message.text.strip()
    if len(full_name) < 3:
        await update.message.reply_text(f"{EMOJIS['error']} الاسم يجب أن يكون 3 أحرف على الأقل.")
        return GET_FULL_NAME

    context.user_data['full_name'] = full_name
    await update.message.reply_text(
        f"{EMOJIS['phone']} **أهلاً {full_name}!**\n\n"
        f"يرجى إدخال رقم هاتفك (يجب أن يبدأ بـ 77, 78, 79 أو 70):",
        parse_mode='Markdown'
    )
    return GET_PHONE

async def get_phone(update: Update, context: CallbackContext) -> int:
    """Get user's phone number and ask for their role."""
    phone = update.message.text.strip()

    if not (phone.startswith(('77', '78', '79', '70')) and len(phone) == 9 and phone.isdigit()):
        await update.message.reply_text(
            f"{EMOJIS['error']} رقم الهاتف غير صحيح.\n"
            f"يجب أن يكون 9 أرقام ويبدأ بـ 77, 78, 79 أو 70"
        )
        return GET_PHONE

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM users WHERE phone = ?', (phone,))
    if cursor.fetchone():
        conn.close()
        await update.message.reply_text(f"{EMOJIS['error']} رقم الهاتف مسجل مسبقاً.")
        return GET_PHONE
    conn.close()

    context.user_data['phone'] = phone

    role_text = f"""
{EMOJIS['user']} **اختر نوع حسابك:**

🛒 **عميل** - شراء كروت الإنترنت

🏪 **مزود** - رفع وإدارة الشبكات والكروت

👇 **اختر الدور المناسب لك:**
"""
    keyboard = [
        [InlineKeyboardButton(f"{EMOJIS['purchase']} عميل", callback_data='role_customer')],
        [InlineKeyboardButton(f'🏪 مزود', callback_data='role_supplier')]
    ]
    await update.message.reply_text(role_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    return CHOOSE_ROLE

async def choose_role(update: Update, context: CallbackContext) -> int:
    """Handle role selection and create user account."""
    query = update.callback_query
    await query.answer()

    role = query.data.split('_')[1]

    conn = get_db_connection()
    cursor = conn.cursor()

    wallet_number = None
    for _ in range(50):
        trial = '79' + ''.join(str(random.randint(0, 9)) for _ in range(7))
        cursor.execute('SELECT 1 FROM users WHERE wallet_number = ?', (trial,))
        if not cursor.fetchone():
            wallet_number = trial
            break

    if not wallet_number:
        await query.edit_message_text("حدث خطأ أثناء إنشاء رقم المحفظة. يرجى المحاولة مرة أخرى.")
        return ConversationHandler.END

    invite_code = ''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=8))

    cursor.execute('''
        INSERT INTO users (telegram_id, full_name, phone, role, wallet_number, invite_code, is_active)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (update.effective_user.id, context.user_data['full_name'],
          context.user_data['phone'], role, wallet_number, invite_code,
          1 if role == 'customer' else 0))

    user_id = cursor.lastrowid

    log_activity(user_id, 'user_registration', f'New user registered as {role}', {
        'telegram_id': update.effective_user.id,
        'role': role,
        'wallet_number': wallet_number
    })

    conn.commit()
    conn.close()

    full_name = context.user_data.get('full_name', 'المستخدم')
    phone = context.user_data.get('phone', 'غير محدد')

    context.user_data.clear()

    if role == 'customer':
        welcome_message = f"""
✅ **تم إنشاء حسابك بنجاح!**
...
"""
    else:
        welcome_message = f"""
✅ **تم إنشاء حساب المزود بنجاح!**
...
"""

    await query.edit_message_text(welcome_message, parse_mode='Markdown')
    await show_main_menu(update, context, role)

    return ConversationHandler.END
