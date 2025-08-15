#!/usr/bin/env python3
"""
Handlers module for Pottagrm Enhanced Bot
Contains all main bot handlers and command processors
"""

import logging
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext, ConversationHandler
from bot_modules.config import *
from bot_modules.utils import *

logger = logging.getLogger(__name__)

# Command handlers
async def start(update: Update, context: CallbackContext) -> int:
    """Handle /start command"""
    try:
        user = get_user(update.effective_user.id)
        if user:
            update_user_activity(user['id'])
            return await show_main_menu(update, context, user['role'])
        else:
            return await register_new_user(update, context)
    except Exception as e:
        logger.error(f"Error in start handler: {e}")
        await update.message.reply_text(f"{EMOJIS['error']} حدث خطأ. يرجى المحاولة مرة أخرى.")
        return ConversationHandler.END

async def wallet_handler(update: Update, context: CallbackContext):
    """Handle /wallet command - enhanced wallet view"""
    try:
        user = get_user(update.effective_user.id)
        if not user:
            await update.message.reply_text(f"{EMOJIS['error']} يرجى التسجيل أولاً /start")
            return

        return await enhanced_wallet_handler(update, context)
    except Exception as e:
        logger.error(f"Error in wallet handler: {e}")
        await update.message.reply_text(f"{EMOJIS['error']} حدث خطأ في عرض المحفظة.")

async def admin_handler(update: Update, context: CallbackContext):
    """Handle /admin command"""
    try:
        from bot_modules.admin_functions import admin_panel_handler
        return await admin_panel_handler(update, context)
    except Exception as e:
        logger.error(f"Error in admin handler: {e}")
        await update.message.reply_text(f"{EMOJIS['error']} حدث خطأ في الوصول للوحة الإدارة.")

async def cancel(update: Update, context: CallbackContext) -> int:
    """Handle cancellation"""
    try:
        # Clear any pending states
        context.user_data.clear()
        
        user = get_user(update.effective_user.id)
        if user:
            update_user_activity(user['id'])
            return await show_main_menu(update, context, user['role'])
        else:
            await update.message.reply_text(f"{EMOJIS['cancel']} تم الإلغاء. استخدم /start للبدء.")
            return ConversationHandler.END
    except Exception as e:
        logger.error(f"Error in cancel handler: {e}")
        await update.message.reply_text(f"{EMOJIS['error']} حدث خطأ.")
        return ConversationHandler.END

# Registration handlers
async def register_new_user(update: Update, context: CallbackContext) -> int:
    """Start new user registration"""
    try:
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
    except Exception as e:
        logger.error(f"Error in register new user: {e}")
        await update.message.reply_text(f"{EMOJIS['error']} حدث خطأ في بدء التسجيل.")
        return ConversationHandler.END

async def get_full_name(update: Update, context: CallbackContext) -> int:
    """Get user's full name"""
    try:
        full_name = update.message.text.strip()
        if len(full_name) < 3:
            await update.message.reply_text(f"{EMOJIS['error']} الاسم يجب أن يكون 3 أحرف على الأقل.")
            return GET_FULL_NAME
        
        context.user_data['full_name'] = full_name
        await update.message.reply_text(
            f"{EMOJIS['phone']} **أهلاً {full_name}!**\n\n"
            f"يرجى إدخال رقم هاتفك (يجب أن يبدأ بـ 77, 78, 79 أو 70):"
        , parse_mode='Markdown')
        return GET_PHONE
    except Exception as e:
        logger.error(f"Error in get full name: {e}")
        await update.message.reply_text(f"{EMOJIS['error']} حدث خطأ. يرجى المحاولة مرة أخرى.")
        return GET_FULL_NAME

async def get_phone(update: Update, context: CallbackContext) -> int:
    """Get user's phone number"""
    try:
        phone = update.message.text.strip()
        
        # Validate phone format
        if not (phone.startswith(('77', '78', '79', '70')) and len(phone) == 9 and phone.isdigit()):
            await update.message.reply_text(
                f"{EMOJIS['error']} رقم الهاتف غير صحيح.\n"
                f"يجب أن يكون 9 أرقام ويبدأ بـ 77, 78, 79 أو 70"
            )
            return GET_PHONE
        
        # Check if phone already exists
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM users WHERE phone = ?', (phone,))
        if cursor.fetchone():
            conn.close()
            await update.message.reply_text(f"{EMOJIS['error']} رقم الهاتف مسجل مسبقاً.")
            return GET_PHONE
        conn.close()
        
        context.user_data['phone'] = phone
        
        # Show role selection
        role_text = f"""
{EMOJIS['user']} **اختر نوع حسابك:**

🛒 **عميل** - شراء كروت الإنترنت
🔷 **وكيل** - بيع الكروت وكسب عمولة  
🏪 **مزود** - رفع وإدارة الشبكات والكروت

👇 **اختر الدور المناسب لك:**
"""
        
        keyboard = [
            [InlineKeyboardButton(f'{EMOJIS["purchase"]} عميل', callback_data='role_customer')],
            [InlineKeyboardButton(f'🔷 وكيل', callback_data='role_agent')],
            [InlineKeyboardButton(f'🏪 مزود', callback_data='role_supplier')]
        ]
        
        await update.message.reply_text(role_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        return CHOOSE_ROLE
    except Exception as e:
        logger.error(f"Error in get phone: {e}")
        await update.message.reply_text(f"{EMOJIS['error']} حدث خطأ. يرجى المحاولة مرة أخرى.")
        return GET_PHONE

async def choose_role(update: Update, context: CallbackContext) -> int:
    """Handle role selection"""
    try:
        query = update.callback_query
        await query.answer()
        
        role = query.data.split('_')[1]  # Extract role from callback_data
        
        # Create user account
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Generate unique wallet number
        wallet_number = None
        for _ in range(50):
            trial = '79' + ''.join(str(random.randint(0, 9)) for _ in range(7))
            cursor.execute('SELECT 1 FROM users WHERE wallet_number = ?', (trial,))
            if not cursor.fetchone():
                wallet_number = trial
                break
        
        if not wallet_number:
            await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في إنشاء رقم المحفظة.")
            return ConversationHandler.END
        
        # Generate invite code
        invite_code = None
        for _ in range(50):
            trial = ''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=8))
            cursor.execute('SELECT 1 FROM users WHERE invite_code = ?', (trial,))
            if not cursor.fetchone():
                invite_code = trial
                break
        
        # Insert new user
        cursor.execute('''
            INSERT INTO users (telegram_id, full_name, phone, role, wallet_number, invite_code, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (update.effective_user.id, context.user_data['full_name'], 
              context.user_data['phone'], role, wallet_number, invite_code, 
              1 if role == 'customer' else 0))  # Auto-activate customers only
        
        user_id = cursor.lastrowid
        
        # Log the registration
        log_activity(user_id, 'user_registration', f'New user registered as {role}', {
            'telegram_id': update.effective_user.id,
            'role': role,
            'wallet_number': wallet_number
        })
        
        conn.commit()
        conn.close()
        
        # Store data before clearing
        full_name = context.user_data.get('full_name', 'المستخدم')
        phone = context.user_data.get('phone', 'غير محدد')
        
        # Clear registration data
        context.user_data.clear()
        
        # Send welcome message based on role
        if role == 'customer':
            welcome_message = f"""
✅ **تم إنشاء حسابك بنجاح!**

👤 **معلومات حسابك:**
📛 الاسم: **{full_name}**
📞 الهاتف: **{phone}**
🏷️ النوع: **عميل**
💳 رقم المحفظة: **{wallet_number}**
🎫 كود الدعوة: **{invite_code}**

🎉 **حسابك مفعل ويمكنك البدء في الشراء فوراً!**

💡 **يمكنك الآن:**
• شراء كروت الإنترنت
• تحويل رصيد للأصدقاء
• عرض إحصائياتك
• تقييم الخدمات
"""
        elif role == 'agent':
            welcome_message = f"""
✅ **تم إنشاء حساب الوكيل بنجاح!**

👤 **معلومات حسابك:**
📛 الاسم: **{full_name}**
📞 الهاتف: **{phone}**
🏷️ النوع: **وكيل**
💳 رقم المحفظة: **{wallet_number}**
🎫 كود الدعوة: **{invite_code}**

⏳ **حسابك في انتظار التفعيل من الإدارة**

💰 **كوكيل ستحصل على عمولة من كل عملية بيع!**
"""
        else:  # supplier
            welcome_message = f"""
✅ **تم إنشاء حساب المزود بنجاح!**

👤 **معلومات حسابك:**
📛 الاسم: **{full_name}**
📞 الهاتف: **{phone}**
🏷️ النوع: **مزود**
💳 رقم المحفظة: **{wallet_number}**
🎫 كود الدعوة: **{invite_code}**

⏳ **حسابك في انتظار التفعيل من الإدارة**

🏪 **كمزود يمكنك رفع وإدارة الشبكات والكروت**
"""
        
        keyboard = [[InlineKeyboardButton(f'{EMOJIS["home"]} القائمة الرئيسية', callback_data='main_menu')]]
        
        await query.edit_message_text(welcome_message, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
        # Send notification to admins for non-customer registrations
        if role in ['agent', 'supplier']:
            # Notify admins about new registration
            pass  # Will implement admin notification
        
        return ConversationHandler.END
        
    except Exception as e:
        logger.error(f"Error in choose role: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في إنشاء الحساب.")
        return ConversationHandler.END

# Menu handlers
async def show_main_menu(update: Update, context: CallbackContext, role: str) -> int:
    """Show main menu based on user role"""
    try:
        user = get_user(update.effective_user.id)
        if not user:
            return await start(update, context)
        
        update_user_activity(user['id'])
        
        # Create dynamic menu based on role
        keyboard = create_main_keyboard(role)
        
        menu_text = f"""
{EMOJIS['fire']} **بوت كروت الإنترنت اليمني المطور** {EMOJIS['fire']}

{EMOJIS['user']} مرحباً **{user['full_name']}**
🏷️ النوع: **{USER_ROLES.get(role, role)}**
{EMOJIS['wallet']} رصيدك: **{user['balance']:.2f}** ريال
💳 محفظتك: **{user['wallet_number']}**

📱 **النسخة:** 2.1.0 Enhanced
⚡ **الحالة:** {"مفعل" if user['is_active'] else "في انتظار التفعيل"}

🎯 **اختر العملية المطلوبة:**
"""
        
        if update.message:
            await update.message.reply_text(menu_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        else:
            await update.callback_query.edit_message_text(menu_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
            
        return ConversationHandler.END
        
    except Exception as e:
        logger.error(f"Error in show main menu: {e}")
        error_text = f"{EMOJIS['error']} حدث خطأ في تحميل القائمة الرئيسية."
        if update.message:
            await update.message.reply_text(error_text)
        else:
            await update.callback_query.edit_message_text(error_text)
        return ConversationHandler.END

def create_main_keyboard(role: str):
    """Create main menu keyboard based on user role"""
    try:
        base_buttons = [
            [InlineKeyboardButton(f'{EMOJIS["wallet"]} محفظتي المطورة', callback_data='enhanced_wallet')],
            [InlineKeyboardButton(f'{EMOJIS["purchase"]} شراء كروت', callback_data='buy_cards'),
             InlineKeyboardButton(f'{EMOJIS["transfer"]} تحويل رصيد', callback_data='transfer_to_friend')],
            [InlineKeyboardButton(f'📊 تقاريري الشخصية', callback_data='personal_reports'),
             InlineKeyboardButton(f'⭐ تقييماتي', callback_data='my_ratings')],
            [InlineKeyboardButton(f'🔔 إشعاراتي', callback_data='my_notifications'),
             InlineKeyboardButton(f'🎁 العروض والخصومات', callback_data='promotions')],
            [InlineKeyboardButton(f'⚙️ إعدادات الحساب', callback_data='account_settings')]
        ]
        
        # Add role-specific buttons
        if role == 'agent':
            base_buttons.extend([
                [InlineKeyboardButton(f'💼 لوحة الوكيل', callback_data='agent_panel'),
                 InlineKeyboardButton(f'💰 عمولاتي', callback_data='my_commissions')]
            ])
        elif role == 'supplier':
            base_buttons.extend([
                [InlineKeyboardButton(f'🏪 لوحة المزود', callback_data='supplier_panel'),
                 InlineKeyboardButton(f'📶 إدارة الشبكات', callback_data='manage_networks')],
                [InlineKeyboardButton(f'📤 رفع كروت', callback_data='upload_cards'),
                 InlineKeyboardButton(f'📊 تقارير المبيعات', callback_data='sales_reports')]
            ])
        elif role in ['admin', 'super_admin']:
            base_buttons.extend([
                [InlineKeyboardButton(f'👑 لوحة الإدارة', callback_data='admin_panel'),
                 InlineKeyboardButton(f'📈 التقارير التنفيذية', callback_data='executive_reports')]
            ])
            
            if role == 'super_admin':
                base_buttons.append([
                    InlineKeyboardButton(f'💰 إصدار رصيد', callback_data='super_issue_balance'),
                    InlineKeyboardButton(f'✅ تفعيل مزودين', callback_data='super_activate_suppliers')
                ])
        
        # Add help button
        base_buttons.append([InlineKeyboardButton(f'❓ المساعدة', callback_data='help')])
        
        return base_buttons
    except Exception as e:
        logger.error(f"Error creating main keyboard: {e}")
        return [[InlineKeyboardButton(f'{EMOJIS["error"]} خطأ في القائمة', callback_data='main_menu')]]

# Enhanced wallet handler
async def enhanced_wallet_handler(update: Update, context: CallbackContext):
    """Show enhanced wallet information"""
    try:
        user = get_user(update.effective_user.id)
        if not user:
            await update.message.reply_text(f"{EMOJIS['error']} يرجى التسجيل أولاً.")
            return
        
        update_user_activity(user['id'])
        
        # Get recent transactions
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT wt.*, u.full_name as related_user
            FROM wallet_transactions wt
            LEFT JOIN users u ON (
                CASE 
                    WHEN wt.transaction_type = 'credit' THEN NULL
                    ELSE u.id = ?
                END
            )
            WHERE wt.user_id = ?
            ORDER BY wt.created_at DESC
            LIMIT 10
        ''', (user['id'], user['id']))
        
        recent_transactions = cursor.fetchall()
        
        # Get transaction summary
        cursor.execute('''
            SELECT 
                COUNT(*) as total_transactions,
                SUM(CASE WHEN transaction_type = 'credit' THEN amount ELSE 0 END) as total_credits,
                SUM(CASE WHEN transaction_type = 'debit' THEN amount ELSE 0 END) as total_debits
            FROM wallet_transactions 
            WHERE user_id = ?
        ''', (user['id'],))
        
        summary = cursor.fetchone()
        conn.close()
        
        wallet_text = f"""
💳 **محفظتي المطورة** 💳

👤 **{user['full_name']}**
💰 **الرصيد الحالي:** {user['balance']:.2f} ريال
🆔 **رقم المحفظة:** {user['wallet_number']}

📊 **ملخص المعاملات:**
📈 إجمالي الإيداعات: **{summary['total_credits']:.2f}** ريال
📉 إجمالي المصروفات: **{summary['total_debits']:.2f}** ريال
🔢 عدد المعاملات: **{summary['total_transactions']}**

📝 **آخر المعاملات:**
"""
        
        if recent_transactions:
            for tx in recent_transactions[:5]:
                tx_type = "➕" if tx['transaction_type'] == 'credit' else "➖"
                description = tx['description'] or 'معاملة'
                try:
                    amount = float(tx['amount']) if tx['amount'] is not None else 0.0
                except (ValueError, TypeError):
                    amount = 0.0
                wallet_text += f"\n{tx_type} {amount:.2f} ريال - {description[:30]}..."
        else:
            wallet_text += "\nلا توجد معاملات بعد"
        
        keyboard = [
            [InlineKeyboardButton(f'📊 تفاصيل المعاملات', callback_data='transaction_details'),
             InlineKeyboardButton(f'💸 تحويل رصيد', callback_data='transfer_to_friend')],
            [InlineKeyboardButton(f'🔄 تحديث الرصيد', callback_data='refresh_balance'),
             InlineKeyboardButton(f'📈 إحصائيات مفصلة', callback_data='wallet_stats')],
            [InlineKeyboardButton(f'{EMOJIS["home"]} القائمة الرئيسية', callback_data='main_menu')]
        ]
        
        if update.message:
            await update.message.reply_text(wallet_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        else:
            await update.callback_query.edit_message_text(wallet_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
            
    except Exception as e:
        logger.error(f"Error in enhanced wallet handler: {e}")
        error_msg = f"{EMOJIS['error']} حدث خطأ في عرض المحفظة."
        if update.message:
            await update.message.reply_text(error_msg)
        else:
            await update.callback_query.edit_message_text(error_msg)

# Message handler for processing admin operations
async def handle_text_message(update: Update, context: CallbackContext):
    """Handle text messages for special operations"""
    try:
        # Check if waiting for balance issue
        if context.user_data.get('awaiting_balance_issue'):
            from bot_modules.admin_functions import process_balance_issue
            return await process_balance_issue(update, context)
        
        # Regular message handling
        user = get_user(update.effective_user.id)
        if not user:
            await update.message.reply_text(f"{EMOJIS['info']} أرسل /start للبدء.")
            return
        
        # Default response for unrecognized messages
        await update.message.reply_text(
            f"{EMOJIS['info']} لم أفهم رسالتك. استخدم الأزرار أو /menu للقائمة الرئيسية."
        )
        
    except Exception as e:
        logger.error(f"Error in handle text message: {e}")
        await update.message.reply_text(f"{EMOJIS['error']} حدث خطأ في معالجة الرسالة.")

# Export main handlers for use in main bot file
COMMAND_HANDLERS = {
    'start': start,
    'wallet': wallet_handler,
    'admin': admin_handler,
    'cancel': cancel,
}

from telegram.ext import MessageHandler, CallbackQueryHandler, filters

CONVERSATION_STATES = {
    GET_FULL_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_full_name)],
    GET_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_phone)],
    CHOOSE_ROLE: [CallbackQueryHandler(choose_role, pattern='^role_')],
}