#!/usr/bin/env python3
"""
Handlers module for Pottagrm Enhanced Bot
Contains all main bot handlers and command processors
"""

import logging
import random
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext, ConversationHandler
from bot_modules.config import *
from bot_modules.utils import *
from bot_modules.enhanced_error_messages import ErrorMessages, unexpected_error, menu_error, wallet_error, search_error, coupon_error, perm_error

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
        await update.message.reply_text(unexpected_error("العملية المطلوبة", "النظام"))
        return ConversationHandler.END

async def wallet_handler(update: Update, context: CallbackContext):
    """Handle /wallet command - redirect to enhanced wallet from main bot"""
    try:
        user = get_user(update.effective_user.id)
        if not user:
            await update.message.reply_text(f"{EMOJIS['error']} يرجى التسجيل أولاً /start")
            return

        # Import and use the main enhanced wallet handler
        from yemen_net_bot_new import enhanced_wallet_handler as main_enhanced_wallet
        return await main_enhanced_wallet(update, context)
    except Exception as e:
        logger.error(f"Error in wallet handler: {e}")
        from enhanced_error_messages import ErrorMessages
        await update.message.reply_text(ErrorMessages.custom_error(
            "المحفظة",
            "فشل في تحميل بيانات المحفظة",
            "تأكد من التسجيل وحاول مرة أخرى",
            "WALLET_ERROR"
        ))

async def admin_handler(update: Update, context: CallbackContext):
    """Handle /admin command"""
    try:
        from bot_modules.admin_functions import admin_panel_handler
        return await admin_panel_handler(update, context)
    except Exception as e:
        logger.error(f"Error in admin handler: {e}")
        await update.message.reply_text(perm_error("إدارة النظام", "غير معروف"))

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
        await update.message.reply_text(unexpected_error("تنفيذ الطلب"))
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
        await update.message.reply_text(ErrorMessages.validation_error("التسجيل", "بيانات المستخدم"))
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
        await update.message.reply_text(unexpected_error("العملية المطلوبة", "النظام"))
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
  
🏪 **مزود** - رفع وإدارة الشبكات والكروت

👇 **اختر الدور المناسب لك:**
"""
        
        keyboard = [
            [InlineKeyboardButton(f'{EMOJIS["purchase"]} عميل', callback_data='role_customer')],

            [InlineKeyboardButton(f'🏪 مزود', callback_data='role_supplier')]
        ]
        
        await update.message.reply_text(role_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        return CHOOSE_ROLE
    except Exception as e:
        logger.error(f"Error in get phone: {e}")
        await update.message.reply_text(unexpected_error("العملية المطلوبة", "النظام"))
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
            await query.edit_message_text(wallet_error("إنشاء رقم المحفظة"))
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
        
        # Send notification to admins for supplier registrations
        if role == 'supplier':
            # Notify admins about new registration
            pass  # Will implement admin notification
        
        return ConversationHandler.END
        
    except Exception as e:
        logger.error(f"Error in choose role: {e}")
        await query.edit_message_text(ErrorMessages.validation_error("إنشاء الحساب", "اختيار الدور"))
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
🚀 **بوت كروت الإنترنت اليمني المطور** 🚀

👤 أهلاً وسهلاً **{user['full_name']}**
🏷️ النوع: **{USER_ROLES.get(role, role)}**
💰 رصيدك: **{user['balance']:,.2f}** ريال
💳 رقم محفظتك: **{user['wallet_number']}**
⚡ الحالة: **{"✅ مفعل" if user['is_active'] else "⏳ في انتظار التفعيل"}**

🎯 **اختر العملية المطلوبة:**
"""
        
        if update.message:
            await update.message.reply_text(menu_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        else:
            await update.callback_query.edit_message_text(menu_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
            
        return ConversationHandler.END
        
    except Exception as e:
        logger.error(f"Error in show main menu: {e}")
        error_text = menu_error("القائمة الرئيسية", "تحميل البيانات")
        if update.message:
            await update.message.reply_text(error_text)
        else:
            await update.callback_query.edit_message_text(error_text)
        return ConversationHandler.END

def create_main_keyboard(role: str):
    """Create main menu keyboard based on user role"""
    try:
        # Core features for all users
        base_buttons = [
            [InlineKeyboardButton('💳 محفظتي المطورة', callback_data='enhanced_wallet')],
            [InlineKeyboardButton('🛒 شراء كروت', callback_data='buy_cards'),
             InlineKeyboardButton('💸 تحويل رصيد', callback_data='transfer_to_friend')],
            [InlineKeyboardButton('🎟️ شحن بكوبون', callback_data='redeem_coupon'),
             InlineKeyboardButton('🔍 البحث عن شبكات', callback_data='search_networks')],
            [InlineKeyboardButton('📊 تقاريري الشخصية', callback_data='personal_reports'),
             InlineKeyboardButton('🎁 العروض والخصومات', callback_data='promotions')],
            [InlineKeyboardButton('🔔 إشعاراتي', callback_data='my_notifications'),
             InlineKeyboardButton('⚙️ إعدادات الحساب', callback_data='account_settings')],
            [InlineKeyboardButton('⭐ تقييماتي', callback_data='my_ratings')]
        ]
        
        # Role-specific features
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
        
        # Add help and support
        base_buttons.append([InlineKeyboardButton('❓ المساعدة والدعم', callback_data='help')])
        
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
            SELECT t.*, u.full_name as related_user
            FROM transactions t
            LEFT JOIN users u ON (
                CASE 
                    WHEN t.type = 'credit' THEN NULL
                    ELSE u.id = ?
                END
            )
            WHERE t.from_user = ? OR t.to_user = ?
            ORDER BY t.created_at DESC
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
        
        # Handle None values safely
        total_credits = summary['total_credits'] or 0.0
        total_debits = summary['total_debits'] or 0.0
        total_transactions = summary['total_transactions'] or 0
        
        # Calculate wallet analytics
        available_balance = user['balance']
        total_spent = total_debits
        savings_rate = ((total_credits - total_debits) / max(total_credits, 1)) * 100 if total_credits > 0 else 0
        
        wallet_text = f"""
💳 **محفظتي المطورة** 💳

👤 **{user['full_name']}**
🏷️ نوع الحساب: **{USER_ROLES.get(user['role'] if 'role' in user.keys() else 'customer', 'عميل')}**
⚡ حالة الحساب: **{"✅ مفعل" if user['is_active'] else "⏳ في انتظار التفعيل"}**

💰 **الرصيد والإحصائيات:**
💵 الرصيد المتاح: **{available_balance:,.2f}** ريال
🆔 رقم المحفظة: **{user['wallet_number']}**
📊 معدل الادخار: **{savings_rate:.1f}%**

📈 **ملخص المعاملات:**
🔺 إجمالي الإيداعات: **{total_credits:,.2f}** ريال
🔻 إجمالي المصروفات: **{total_debits:,.2f}** ريال
🔢 عدد المعاملات: **{total_transactions:,}** معاملة
💰 صافي الرصيد: **{(total_credits - total_debits):,.2f}** ريال

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
            [InlineKeyboardButton('📊 تفاصيل المعاملات', callback_data='transaction_details'),
             InlineKeyboardButton('💸 تحويل رصيد', callback_data='transfer_to_friend')],
            [InlineKeyboardButton('📈 إحصائيات مفصلة', callback_data='wallet_stats'),
             InlineKeyboardButton('💳 كشف حساب', callback_data='account_statement')],
            [InlineKeyboardButton('🔄 تحديث الرصيد', callback_data='enhanced_wallet'),
             InlineKeyboardButton('💰 إيداع رصيد', callback_data='deposit_balance')],
            [InlineKeyboardButton('⚙️ إعدادات المحفظة', callback_data='wallet_settings'),
             InlineKeyboardButton('📞 الدعم', callback_data='help')],
            [InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
        ]
        
        if update.message:
            await update.message.reply_text(wallet_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        else:
            await update.callback_query.edit_message_text(wallet_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
            
    except Exception as e:
        logger.error(f"Error in enhanced wallet handler: {e}")
        error_msg = wallet_error("عرض تفاصيل المحفظة")
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
        
        # Check if waiting for recharge cards issue
        if context.user_data.get('awaiting_card_issue'):
            from bot_modules.admin_functions import process_recharge_cards_issue
            return await process_recharge_cards_issue(update, context)
        
        # Check if waiting for broadcast message
        if context.user_data.get('awaiting_broadcast'):
            from bot_modules.admin_functions import process_broadcast_message
            return await process_broadcast_message(update, context)
        
        # WiFi search removed - now handled by unified search in main bot
        
        # Check if waiting for transfer step 1 (wallet number)
        if context.user_data.get('awaiting_transfer_step1'):
            return await process_transfer_step1(update, context)
        
        # Check if waiting for transfer step 2 (amount)
        if context.user_data.get('awaiting_transfer_step2'):
            return await process_transfer_step2(update, context)
        
        # Check if waiting for simple admin send
        if context.user_data.get('awaiting_simple_send'):
            return await process_simple_admin_send(update, context)
        
        # Check if waiting for simple transfer
        if context.user_data.get('awaiting_simple_transfer'):
            return await process_simple_transfer(update, context)
        
        # Check if waiting for network name
        if context.user_data.get('awaiting_network_name'):
            return await process_network_creation(update, context, update.message.text)
        
        # Check if waiting for network description
        if context.user_data.get('awaiting_network_description'):
            return await process_network_description(update, context, update.message.text)
        
        # Check if waiting for network location
        if context.user_data.get('awaiting_network_location'):
            return await process_network_location(update, context, update.message.text)
        
        # Check if waiting for network search
        if context.user_data.get('awaiting_network_search'):
            return await process_network_search(update, context, update.message.text)
        
        # Check if admin is adding network
        if context.user_data.get('admin_adding_network'):
            from bot_modules.admin_functions import admin_process_network_creation
            return await admin_process_network_creation(update, context)
        
        # Check if supplier is adding network
        if context.user_data.get('adding_network'):
            return await process_supplier_network_creation(update, context)
        
        # Check if admin is uploading cards
        if context.user_data.get('admin_uploading_card'):
            from bot_modules.admin_functions import admin_process_card_upload
            return await admin_process_card_upload(update, context)
        
        # Check if admin is creating coupon
        if context.user_data.get('admin_creating_coupon'):
            from bot_modules.admin_functions import process_coupon_creation
            return await process_coupon_creation(update, context)
        
        # Check if user is redeeming coupon
        if context.user_data.get('redeeming_coupon'):
            return await process_coupon_redemption(update, context)
        
        # Check if waiting for user search
        if context.user_data.get('awaiting_user_search'):
            return await process_user_search(update, context, update.message.text)
        
        # Check if waiting for balance send (old method - keep for compatibility)
        if context.user_data.get('awaiting_balance_send'):
            return await process_balance_send(update, context)
        
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
        await update.message.reply_text(unexpected_error("معالجة الرسالة النصية"))

# Enhanced User Features

# wifi_search_handler removed - unified with search_networks_handler in main bot

# process_wifi_search removed - unified with search_networks_handler in main bot

async def send_balance_handler(update: Update, context: CallbackContext):
    """إرسال رصيد مع البحث المتقدم"""
    try:
        user = get_user(update.effective_user.id)
        if not user:
            if update.message:
                await update.message.reply_text("❌ يرجى التسجيل أولاً /start")
            else:
                await update.callback_query.edit_message_text("❌ يرجى التسجيل أولاً /start")
            return
        
        if user['balance'] <= 10:
            error_msg = f"❌ رصيدك غير كافي\nرصيدك: {user['balance']:.2f} ريال\nالحد الأدنى: 60 ريال (50 + 10 رسوم)"
            if update.message:
                await update.message.reply_text(error_msg)
            else:
                await update.callback_query.edit_message_text(error_msg)
            return
        
        text = f"""
💸 **تحويل رصيد** 💸

👤 مرحباً **{user['full_name']}**
💰 رصيدك: **{user['balance']:,.2f}** ريال

🎯 **اختر طريقة التحويل:**

1️⃣ **البحث المتقدم**
   ابحث عن المستخدم بالاسم، المحفظة، الهاتف أو المعرف

2️⃣ **التحويل السريع**
   اكتب رقم المحفظة والمبلغ مباشرة
   مثال: `791234567 100`

⚠️ **ملاحظات مهمة:**
• رسوم التحويل: مجاني 🆓
• الحد الأدنى: 50 ريال
• الحد الأقصى: {min(user['balance'] - 10, 50000):,.0f} ريال
"""
        
        keyboard = [
            [InlineKeyboardButton('🔍 البحث المتقدم', callback_data='advanced_search_transfer'),
             InlineKeyboardButton('⚡ تحويل سريع', callback_data='quick_transfer')],
            [InlineKeyboardButton('📋 سجل التحويلات', callback_data='transfer_history'),
             InlineKeyboardButton('💳 محفظتي', callback_data='enhanced_wallet')],
            [InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
        ]
        
        if update.message:
            await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        else:
            await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in send balance handler: {e}")
        error_text = "❌ حدث خطأ"
        if update.message:
            await update.message.reply_text(error_text)
        else:
            await update.callback_query.edit_message_text(error_text)

async def process_balance_send(update: Update, context: CallbackContext):
    """Process balance sending to another user"""
    try:
        if not context.user_data.get('awaiting_balance_send'):
            return
        
        user = get_user(update.effective_user.id)
        if not user:
            await update.message.reply_text(f"{EMOJIS['error']} يرجى التسجيل أولاً /start")
            return
        
        # Parse input
        parts = update.message.text.strip().split()
        if len(parts) < 2:
            await update.message.reply_text(f"{EMOJIS['error']} تنسيق غير صحيح. أدخل: رقم_المحفظة المبلغ السبب")
            return
        
        target_wallet = parts[0]
        try:
            amount = float(parts[1])
        except ValueError:
            await update.message.reply_text(f"{EMOJIS['error']} المبلغ يجب أن يكون رقماً صحيحاً.")
            return
        
        reason = ' '.join(parts[2:]) if len(parts) > 2 else 'تحويل رصيد من صديق'
        
        # Validate amount
        if amount <= 0:
            await update.message.reply_text(f"{EMOJIS['error']} المبلغ يجب أن يكون أكبر من صفر.")
            return
        
        # FREE transfers - no fees
        transfer_fee = 0.0
        total_deduction = amount  # No fees!
        
        if total_deduction > user['balance']:
            await update.message.reply_text(f"""
{EMOJIS['error']} **رصيدك غير كافي!**

💰 المبلغ المطلوب: **{amount:.2f}** ريال
🆓 التحويل: **مجاني بدون رسوم**
📊 إجمالي الخصم: **{total_deduction:.2f}** ريال
💵 رصيدك الحالي: **{user['balance']:.2f}** ريال
❌ النقص: **{total_deduction - user['balance']:.2f}** ريال
""", parse_mode='Markdown')
            return
        
        # Find target user
        from bot_modules.database import get_db_connection
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM users WHERE wallet_number = ?', (target_wallet,))
        target_user = cursor.fetchone()
        
        if not target_user:
            await update.message.reply_text(f"""
{EMOJIS['error']} **لم يتم العثور على المستخدم!**

🔍 رقم المحفظة: `{target_wallet}`

💡 **تأكد من:**
• صحة رقم المحفظة
• أن الرقم يتكون من 9 أرقام
• أن الرقم يبدأ بـ 79
""", parse_mode='Markdown')
            conn.close()
            return
        
        if target_user['id'] == user['id']:
            await update.message.reply_text(f"{EMOJIS['error']} لا يمكنك إرسال رصيد لنفسك!")
            conn.close()
            return
        
        # Create transactions
        import uuid
        from datetime import datetime
        
        # Transfer transaction
        transfer_id = str(uuid.uuid4())
        cursor.execute('''
            INSERT INTO transactions 
            (id, from_user, to_user, amount, type, description, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (transfer_id, user['id'], target_user['id'], amount, 'transfer', reason, datetime.now()))
        
        # Fee transaction
        fee_id = str(uuid.uuid4())
        cursor.execute('''
            INSERT INTO transactions 
            (id, from_user, amount, type, description, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (fee_id, user['id'], transfer_fee, 'transfer_fee', f'رسوم تحويل رصيد إلى {target_user["full_name"]}', datetime.now()))
        
        # Update balances
        from bot_modules.utils import recalc_and_set_user_balance
        sender_new_balance = recalc_and_set_user_balance(user['id'])
        receiver_new_balance = recalc_and_set_user_balance(target_user['id'])
        
        conn.commit()
        conn.close()
        
        # Clear user state
        context.user_data.pop('awaiting_balance_send', None)
        
        # Send confirmation to sender
        success_text = f"""
✅ **تم إرسال الرصيد بنجاح!**

📤 **تفاصيل التحويل:**
👤 المستلم: **{target_user['full_name']}**
💰 المبلغ المرسل: **{amount:.2f}** ريال
🆓 التحويل: **مجاني بدون رسوم**
📊 إجمالي الخصم: **{total_deduction:.2f}** ريال

💵 **الأرصدة:**
🔻 رصيدك الجديد: **{sender_new_balance:.2f}** ريال
🔺 رصيد المستلم: **{receiver_new_balance:.2f}** ريال

💬 **السبب:** {reason}
🕐 **وقت التحويل:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

📱 سيتم إشعار المستلم فوراً
"""
        
        await update.message.reply_text(success_text, parse_mode='Markdown')
        
        # Send notification to receiver (about receiving money)
        try:
            receiver_notification = f"""
💰 **تم استلام رصيد جديد!** 💰

📥 **تفاصيل الاستلام:**
👤 المرسل: **{user['full_name']}**
💰 المبلغ المستلم: **{amount:.2f}** ريال
💵 رصيدك الجديد: **{receiver_new_balance:.2f}** ريال

💬 **السبب:** {reason}
🕐 **وقت التحويل:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

───────────────────
💡 استخدم /wallet لعرض محفظتك
"""
            
            await context.bot.send_message(
                chat_id=target_user['telegram_id'],
                text=receiver_notification,
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.warning(f"Failed to send notification to receiver {target_user['telegram_id']}: {e}")

        # Send notification to sender (about sending money)
        try:
            sender_notification = f"""
📤 **تم خصم رصيد من محفظتك** 📤

💸 **تفاصيل الخصم:**
👤 المستلم: **{target_user['full_name']}**
💰 المبلغ المخصوم: **{amount:.2f}** ريال
🆓 الرسوم: **مجاني**
💵 رصيدك الجديد: **{sender_new_balance:.2f}** ريال

💬 **السبب:** {reason}
🕐 **وقت التحويل:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

───────────────────
💡 استخدم /wallet لعرض محفظتك
"""
            
            await context.bot.send_message(
                chat_id=user['telegram_id'],
                text=sender_notification,
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.warning(f"Failed to send notification to sender {user['telegram_id']}: {e}")
        
        # Log the transfer
        logger.info(f"User {user['full_name']} sent {amount} YER to {target_user['full_name']} (fee: {transfer_fee})")
        
    except Exception as e:
        logger.error(f"Error in process balance send: {e}")
        await update.message.reply_text(wallet_error("إرسال الرصيد"))

# New Enhanced Transfer System

async def process_transfer_step1(update: Update, context: CallbackContext):
    """Process step 1 - Find user by phone or wallet number"""
    try:
        if not context.user_data.get('awaiting_transfer_step1'):
            return
        
        user = get_user(update.effective_user.id)
        if not user:
            await update.message.reply_text(f"{EMOJIS['error']} يرجى التسجيل أولاً /start")
            return
        
        search_input = update.message.text.strip()
        
        # Find target user by phone or wallet number
        from bot_modules.database import get_db_connection
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Search by wallet number first, then by phone
        cursor.execute('SELECT * FROM users WHERE wallet_number = ? OR phone = ?', (search_input, search_input))
        target_user = cursor.fetchone()
        
        if not target_user:
            await update.message.reply_text(f"""
{EMOJIS['error']} **لم يتم العثور على المستخدم!**

🔍 البحث عن: `{search_input}`

💡 **تأكد من:**
• صحة رقم الهاتف أو رقم المحفظة
• أن المستخدم مسجل في البوت
• أن الرقم مكتوب بالطريقة الصحيحة

📝 جرب مرة أخرى أو اكتب /cancel للإلغاء
""", parse_mode='Markdown')
            conn.close()
            return
        
        if target_user['id'] == user['id']:
            await update.message.reply_text(f"{EMOJIS['error']} لا يمكنك إرسال رصيد لنفسك!")
            conn.close()
            return
        
        conn.close()
        
        # Save target user info and move to step 2
        context.user_data['target_user_id'] = target_user['id']
        context.user_data['target_user_name'] = target_user['full_name']
        context.user_data['target_wallet'] = target_user['wallet_number'] if 'wallet_number' in target_user.keys() else 'غير محدد'
        context.user_data.pop('awaiting_transfer_step1', None)
        context.user_data['awaiting_transfer_step2'] = True
        
        text = f"""
✅ **تم العثور على المستخدم!**

👤 **المستلم:** {target_user['full_name']}
🆔 **رقم المحفظة:** {target_user['wallet_number'] if 'wallet_number' in target_user.keys() else 'غير محدد'}
📱 **رقم الهاتف:** {target_user['phone']}

💰 **رصيدك الحالي:** {user['balance']:,.2f} ريال

📋 **الخطوة الثانية:**
أدخل المبلغ الذي تريد إرساله

💡 **مثال:** `100`

⚠️ **ملاحظة:** التحويل مجاني بدون رسوم 🆓

📝 أدخل المبلغ:

أو اكتب /cancel للإلغاء
"""
        
        await update.message.reply_text(text, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in process transfer step 1: {e}")
        await update.message.reply_text(search_error("المستخدم", "قاعدة البيانات"))

async def process_transfer_step2(update: Update, context: CallbackContext):
    """Process step 2 - Get amount and show confirmation"""
    try:
        if not context.user_data.get('awaiting_transfer_step2'):
            return
        
        user = get_user(update.effective_user.id)
        if not user:
            await update.message.reply_text(f"{EMOJIS['error']} يرجى التسجيل أولاً /start")
            return
        
        # Parse amount
        try:
            amount = float(update.message.text.strip())
        except ValueError:
            await update.message.reply_text(f"{EMOJIS['error']} المبلغ يجب أن يكون رقماً صحيحاً.")
            return
        
        # Validate amount
        if amount <= 0:
            await update.message.reply_text(f"{EMOJIS['error']} المبلغ يجب أن يكون أكبر من صفر.")
            return
        
        # FREE transfers - no fees
        transfer_fee = 0.0
        total_deduction = amount  # No fees!
        
        if total_deduction > user['balance']:
            await update.message.reply_text(f"""
{EMOJIS['error']} **رصيدك غير كافي!**

💰 المبلغ المطلوب: **{amount:.2f}** ريال
🆓 التحويل: **مجاني بدون رسوم**
📊 إجمالي الخصم: **{total_deduction:.2f}** ريال
💵 رصيدك الحالي: **{user['balance']:.2f}** ريال
❌ النقص: **{total_deduction - user['balance']:.2f}** ريال

📝 جرب مبلغاً أقل أو اكتب /cancel للإلغاء
""", parse_mode='Markdown')
            return
        
        # Save amount and show confirmation
        context.user_data['transfer_amount'] = amount
        context.user_data['transfer_fee'] = transfer_fee
        
        target_name = context.user_data.get('target_user_name', 'غير محدد')
        target_wallet = context.user_data.get('target_wallet', 'غير محدد')
        
        confirmation_text = f"""
🔍 **تأكيد التحويل** 🔍

📤 **تفاصيل التحويل:**
👤 المستلم: **{target_name}**
🆔 رقم المحفظة: **{target_wallet}**
💰 المبلغ: **{amount:,.2f}** ريال
🆓 التحويل: **مجاني بدون رسوم**
📊 إجمالي الخصم: **{total_deduction:.2f}** ريال

💵 **رصيدك بعد التحويل:** **{user['balance'] - amount:.2f}** ريال

❓ **هل تريد المتابعة؟**
"""
        
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        keyboard = [
            [InlineKeyboardButton('✅ نعم، أرسل الرصيد', callback_data='confirm_transfer_yes'),
             InlineKeyboardButton('❌ لا، إلغاء العملية', callback_data='confirm_transfer_no')]
        ]
        
        await update.message.reply_text(
            confirmation_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
        context.user_data.pop('awaiting_transfer_step2', None)
        context.user_data['awaiting_transfer_confirmation'] = True
        
    except Exception as e:
        logger.error(f"Error in process transfer step 2: {e}")
        await update.message.reply_text(wallet_error("معالجة مبلغ التحويل"))

async def process_simple_admin_send(update: Update, context: CallbackContext):
    """Simple admin money sending"""
    try:
        if not context.user_data.get('awaiting_simple_send'):
            return
        
        user = get_user(update.effective_user.id)
        if not user or user['role'] != 'super_admin':
            await update.message.reply_text("❌ ليس لديك صلاحية.")
            return
        
        # Parse input: wallet_number amount
        parts = update.message.text.strip().split()
        if len(parts) < 2:
            await update.message.reply_text("❌ اكتب: رقم المحفظة والمبلغ\nمثال: 791234567 100")
            return
        
        wallet_number = parts[0]
        try:
            amount = float(parts[1])
        except ValueError:
            await update.message.reply_text("❌ المبلغ يجب أن يكون رقماً.")
            return
        
        if amount <= 0:
            await update.message.reply_text("❌ المبلغ يجب أن يكون أكبر من صفر.")
            return
        
        if amount > user['balance']:
            await update.message.reply_text(f"❌ رصيدك غير كافي.\nرصيدك: {user['balance']:,.0f} ريال")
            return
        
        # Find target user
        from bot_modules.database import get_db_connection
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM users WHERE wallet_number = ?', (wallet_number,))
        target_user = cursor.fetchone()
        
        if not target_user:
            await update.message.reply_text(f"❌ لم يتم العثور على محفظة: {wallet_number}")
            conn.close()
            return
        
        # Transfer money
        import uuid
        from datetime import datetime
        
        transaction_id = str(uuid.uuid4())
        cursor.execute('''
            INSERT INTO transactions 
            (id, from_user, to_user, amount, type, description, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (transaction_id, user['id'], target_user['id'], amount, 'admin_transfer', 'تحويل من المدير', datetime.now()))
        
        # Update balances
        from bot_modules.utils import recalc_and_set_user_balance
        admin_new_balance = recalc_and_set_user_balance(user['id'])
        target_new_balance = recalc_and_set_user_balance(target_user['id'])
        
        conn.commit()
        conn.close()
        
        # Clear state
        context.user_data.pop('awaiting_simple_send', None)
        
        # Send confirmation
        await update.message.reply_text(f"""
✅ **تم الإرسال بنجاح!**

👤 المستلم: {target_user['full_name']}
💰 المبلغ: {amount:,.0f} ريال
💵 رصيدك الجديد: {admin_new_balance:,.0f} ريال
""", parse_mode='Markdown')
        
        # Notify receiver
        try:
            await context.bot.send_message(
                chat_id=target_user['telegram_id'],
                text=f"💰 تم استلام {amount:,.0f} ريال من الإدارة\n💵 رصيدك الجديد: {target_new_balance:,.0f} ريال"
            )
        except Exception:
            pass
        
        logger.info(f"Admin {user['full_name']} sent {amount} to {target_user['full_name']}")
        
    except Exception as e:
        logger.error(f"Error in simple admin send: {e}")
        await update.message.reply_text(wallet_error("إرسال الرصيد"))

async def process_simple_transfer(update: Update, context: CallbackContext):
    """Simple user-to-user transfer"""
    try:
        if not context.user_data.get('awaiting_simple_transfer'):
            return
        
        user = get_user(update.effective_user.id)
        if not user:
            await update.message.reply_text("❌ يرجى التسجيل أولاً.")
            return
        
        # Parse input: wallet_number amount
        parts = update.message.text.strip().split()
        if len(parts) < 2:
            await update.message.reply_text("❌ اكتب: رقم المحفظة والمبلغ\nمثال: 791234567 50")
            return
        
        wallet_number = parts[0]
        try:
            amount = float(parts[1])
        except ValueError:
            await update.message.reply_text("❌ المبلغ يجب أن يكون رقماً.")
            return
        
        if amount <= 0:
            await update.message.reply_text("❌ المبلغ يجب أن يكون أكبر من صفر.")
            return
        
        if amount < 10:
            await update.message.reply_text("❌ أقل مبلغ للتحويل هو 10 ريال.")
            return
        
        # FREE transfers - no fees
        transfer_fee = 0.0
        total_deduction = amount  # No fees!
        
        if total_deduction > user['balance']:
            await update.message.reply_text(f"""❌ رصيدك غير كافي

💰 المبلغ: {amount:.0f} ريال
🆓 الرسوم: مجاني
📊 المطلوب: {total_deduction:.0f} ريال
💵 رصيدك: {user['balance']:.0f} ريال""")
            return
        
        # Find target user
        from bot_modules.database import get_db_connection
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM users WHERE wallet_number = ?', (wallet_number,))
        target_user = cursor.fetchone()
        
        if not target_user:
            await update.message.reply_text(f"❌ لم يتم العثور على محفظة: {wallet_number}")
            conn.close()
            return
        
        if target_user['id'] == user['id']:
            await update.message.reply_text("❌ لا يمكنك إرسال رصيد لنفسك!")
            conn.close()
            return
        
        # Transfer money
        import uuid
        from datetime import datetime
        
        # Transfer transaction
        transfer_id = str(uuid.uuid4())
        cursor.execute('''
            INSERT INTO transactions 
            (id, from_user, to_user, amount, type, description, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (transfer_id, user['id'], target_user['id'], amount, 'transfer', 'تحويل رصيد', datetime.now()))
        
        # Fee transaction
        fee_id = str(uuid.uuid4())
        cursor.execute('''
            INSERT INTO transactions 
            (id, from_user, amount, type, description, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (fee_id, user['id'], transfer_fee, 'transfer_fee', 'رسوم تحويل', datetime.now()))
        
        # Update balances
        from bot_modules.utils import recalc_and_set_user_balance
        sender_new_balance = recalc_and_set_user_balance(user['id'])
        receiver_new_balance = recalc_and_set_user_balance(target_user['id'])
        
        conn.commit()
        conn.close()
        
        # Clear state
        context.user_data.pop('awaiting_simple_transfer', None)
        
        # Send confirmation
        await update.message.reply_text(f"""
✅ **تم الإرسال بنجاح!**

👤 المستلم: {target_user['full_name']}
💰 المبلغ: {amount:.0f} ريال
🆓 الرسوم: مجاني
💵 رصيدك الجديد: {sender_new_balance:.0f} ريال
""", parse_mode='Markdown')
        
        # Send notification to receiver (about receiving money)
        try:
            receiver_notification = f"""
💰 **تم استلام رصيد جديد!** 💰

📥 **تفاصيل الاستلام:**
👤 المرسل: **{user['full_name']}**
💰 المبلغ المستلم: **{amount:.0f}** ريال
💵 رصيدك الجديد: **{receiver_new_balance:.0f}** ريال

🕐 **وقت التحويل:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

───────────────────
💡 استخدم /wallet لعرض محفظتك
"""
            
            await context.bot.send_message(
                chat_id=target_user['telegram_id'],
                text=receiver_notification,
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.warning(f"Failed to send notification to receiver {target_user['telegram_id']}: {e}")

        # Send notification to sender (about sending money)
        try:
            sender_notification = f"""
📤 **تم خصم رصيد من محفظتك** 📤

💸 **تفاصيل الخصم:**
👤 المستلم: **{target_user['full_name']}**
💰 المبلغ المخصوم: **{amount:.0f}** ريال
🆓 الرسوم: **مجاني**
💵 رصيدك الجديد: **{sender_new_balance:.0f}** ريال

🕐 **وقت التحويل:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

───────────────────
💡 استخدم /wallet لعرض محفظتك
"""
            
            await context.bot.send_message(
                chat_id=user['telegram_id'],
                text=sender_notification,
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.warning(f"Failed to send notification to sender {user['telegram_id']}: {e}")
        
        logger.info(f"User {user['full_name']} sent {amount} to {target_user['full_name']} (fee: {transfer_fee})")
        
    except Exception as e:
        logger.error(f"Error in simple transfer: {e}")
        await update.message.reply_text(wallet_error("تنفيذ التحويل"))

async def enhanced_placeholder_handler(update: Update, context: CallbackContext, title: str, description: str):
    """Enhanced placeholder for future features"""
    try:
        user = get_user(update.effective_user.id)
        if not user:
            if update.message:
                await update.message.reply_text("❌ يرجى التسجيل أولاً /start")
            else:
                await update.callback_query.edit_message_text("❌ يرجى التسجيل أولاً /start")
            return
        
        text = f"""
✨ **{title}** ✨

👤 مرحباً **{user['full_name']}**

✅ **الميزة متاحة الآن!**
{description}

🎯 **المميزات الحالية:**
• واجهة محسنة ومطورة
• أداء سريع وموثوق  
• تجربة أفضل

🔔 سيتم إشعارك فور توفر هذه الميزة!
"""
        
        keyboard = [
            [InlineKeyboardButton('🏠 العودة للقائمة الرئيسية', callback_data='main_menu'),
             InlineKeyboardButton('🔄 تحديث', callback_data='main_menu')]
        ]
        
        if update.message:
            await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        else:
            await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
            
    except Exception as e:
        logger.error(f"Error in enhanced placeholder: {e}")
        error_text = "❌ حدث خطأ مؤقت"
        if update.message:
            await update.message.reply_text(error_text)
        else:
            await update.callback_query.edit_message_text(error_text)

async def personal_reports_handler(update: Update, context: CallbackContext):
    try:
        user = get_user(update.effective_user.id)
        if not user:
            if update.message:
                await update.message.reply_text("❌ يرجى التسجيل أولاً /start")
            else:
                await update.callback_query.edit_message_text("❌ يرجى التسجيل أولاً /start")
            return
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT 
                COUNT(*) as total_transactions,
                COALESCE(SUM(CASE WHEN type IN ('wallet_recharge','coupon_redeem','p2p_credit') THEN amount ELSE 0 END), 0) as total_in,
                COALESCE(SUM(CASE WHEN type IN ('card_purchase','p2p_debit') THEN amount ELSE 0 END), 0) as total_out
            FROM transactions WHERE from_user = ? OR to_user = ?
        ''', (user['id'], user['id']))
        summary = cursor.fetchone()
        cursor.execute('''
            SELECT type, amount, description, created_at
            FROM transactions 
            WHERE from_user = ? OR to_user = ?
            ORDER BY created_at DESC LIMIT 5
        ''', (user['id'], user['id']))
        recent = cursor.fetchall()
        conn.close()
        total_in = (summary['total_in'] or 0)
        total_out = (summary['total_out'] or 0)
        net = total_in - total_out
        text = f"""
📊 تقاريري الشخصية

🔹 الوارد: {total_in:,.2f} ريال
🔸 الصادر: {total_out:,.2f} ريال
⚖️ الصافي: {net:,.2f} ريال

🕘 آخر المعاملات:
"""
        if recent:
            for r in recent:
                text += f"• {r['type']} - {r['amount']:,.2f} - {str(r['created_at'])[:16]}\n"
        else:
            text += "لا توجد معاملات حديثة."
        keyboard = [[InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]]
        if update.message:
            await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    except Exception as e:
        logger.error(f"Error in personal_reports_handler: {e}")
        if update.message:
            await update.message.reply_text(ErrorMessages.report_error("الشخصية"))
        else:
            await update.callback_query.edit_message_text(ErrorMessages.report_error("الشخصية"))

# promotions_handler removed - unified with enhanced promotions_handler in main bot

async def my_notifications_handler(update: Update, context: CallbackContext):
    try:
        text = """
🔔 إشعاراتي

لا توجد إشعارات جديدة حالياً.
"""
        kb = [[InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]]
        if update.message:
            await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb))
        else:
            await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb))
    except Exception as e:
        logger.error(f"Error in my_notifications_handler: {e}")

async def account_settings_handler(update: Update, context: CallbackContext):
    try:
        user = get_user(update.effective_user.id)
        if not user:
            if update.message:
                await update.message.reply_text("❌ يرجى التسجيل أولاً /start")
            else:
                await update.callback_query.edit_message_text("❌ يرجى التسجيل أولاً /start")
            return
        text = f"""
⚙️ إعدادات الحساب

👤 الاسم: {user['full_name']}
📱 الهاتف: {user.get('phone','غير محدد')}
👑 الدور: {user['role']}
"""
        kb = [[InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]]
        if update.message:
            await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb))
        else:
            await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb))
    except Exception as e:
        logger.error(f"Error in account_settings_handler: {e}")

async def my_ratings_handler(update: Update, context: CallbackContext):
    try:
        text = """
⭐ تقييماتي

لا توجد تقييمات متاحة حالياً.
"""
        kb = [[InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]]
        if update.message:
            await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb))
        else:
            await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb))
    except Exception as e:
        logger.error(f"Error in my_ratings_handler: {e}")

async def help_handler(update: Update, context: CallbackContext):
    """Enhanced help and support"""
    try:
        user = get_user(update.effective_user.id)
        if not user:
            if update.message:
                await update.message.reply_text("❌ يرجى التسجيل أولاً /start")
            else:
                await update.callback_query.edit_message_text("❌ يرجى التسجيل أولاً /start")
            return
        
        help_text = f"""
❓ **المساعدة والدعم** ❓

👤 مرحباً **{user['full_name']}**
🆔 رقم محفظتك: **{user['wallet_number']}**

📋 **الأوامر الأساسية:**
• `/start` - بدء أو إعادة تشغيل البوت
• `/menu` - عرض القائمة الرئيسية
• `/wallet` - عرض محفظتك
• `/cancel` - إلغاء العملية الحالية

💡 **طريقة الاستخدام:**
1️⃣ اختر الميزة من القائمة الرئيسية
2️⃣ اتبع التعليمات المعروضة
3️⃣ استخدم الأزرار للتنقل

🛒 **لشراء الكروت:**
• اختر "🛒 شراء كروت"
• اختر الشبكة والفئة
• ادفع واستلم الكرت

💸 **لتحويل الرصيد:**
• اختر "💸 تحويل رصيد"
• اكتب: رقم المحفظة المبلغ
• مثال: `791234567 100`

📞 **للدعم الفني:**
• تواصل مع الإدارة
• اشرح مشكلتك بوضوح
• ستتم الإجابة في أسرع وقت

🔧 **نصائح مهمة:**
• احتفظ برقم محفظتك آمناً
• لا تشارك معلوماتك مع أحد
• تأكد من صحة البيانات قبل التأكيد
"""
        
        keyboard = [
            [InlineKeyboardButton('📞 التواصل مع الإدارة', callback_data='contact_admin'),
             InlineKeyboardButton('🔔 الإشعارات', callback_data='my_notifications')],
            [InlineKeyboardButton('⚙️ إعدادات الحساب', callback_data='account_settings'),
             InlineKeyboardButton('📊 حالة الحساب', callback_data='account_status')],
            [InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
        ]
        
        if update.message:
            await update.message.reply_text(help_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        else:
            await update.callback_query.edit_message_text(help_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
            
    except Exception as e:
        logger.error(f"Error in help handler: {e}")
        error_text = "❌ حدث خطأ في تحميل المساعدة"
        if update.message:
            await update.message.reply_text(error_text)
        else:
            await update.callback_query.edit_message_text(error_text)

async def search_user_for_transfer(update: Update, context: CallbackContext):
    """البحث عن مستخدم لإرسال رصيد"""
    try:
        user = get_user(update.effective_user.id)
        if not user:
            await update.callback_query.edit_message_text("❌ يرجى التسجيل أولاً /start")
            return

        search_text = f"""
🔍 **البحث عن مستخدم لإرسال الرصيد** 🔍

👤 مرحباً **{user['full_name']}**
💰 رصيدك: **{user['balance']:,.2f}** ريال

📝 **طرق البحث المتاحة:**

1️⃣ **بالاسم الكامل**
   اكتب: الاسم أحمد محمد

2️⃣ **برقم المحفظة**
   اكتب: المحفظة 791234567

3️⃣ **برقم الهاتف**
   اكتب: الهاتف 770123456

4️⃣ **بمعرف التلغرام**
   اكتب: المعرف @username

💡 **أمثلة:**
• `الاسم أحمد محمد علي`
• `المحفظة 791234567`
• `الهاتف 770123456`
• `المعرف @ahmed123`

اكتب طريقة البحث والقيمة:
"""

        keyboard = [
            [InlineKeyboardButton('💳 البحث بالمحفظة', callback_data='search_by_wallet'),
             InlineKeyboardButton('👤 البحث بالاسم', callback_data='search_by_name')],
            [InlineKeyboardButton('📱 البحث بالهاتف', callback_data='search_by_phone'),
             InlineKeyboardButton('🆔 البحث بالمعرف', callback_data='search_by_username')],
            [InlineKeyboardButton('🔙 عودة', callback_data='main_menu'),
             InlineKeyboardButton('❌ إلغاء', callback_data='cancel')]
        ]

        await update.callback_query.edit_message_text(
            search_text, 
            reply_markup=InlineKeyboardMarkup(keyboard), 
            parse_mode='Markdown'
        )
        
        context.user_data['awaiting_user_search'] = True

    except Exception as e:
        logger.error(f"Error in search user for transfer: {e}")
        await update.callback_query.edit_message_text("❌ حدث خطأ في البحث")

async def process_user_search(update: Update, context: CallbackContext, search_text: str):
    """معالجة البحث عن المستخدم"""
    try:
        user = get_user(update.effective_user.id)
        if not user:
            await update.message.reply_text("❌ يرجى التسجيل أولاً /start")
            return

        # تحليل نص البحث
        search_text = search_text.strip()
        search_results = []
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if search_text.startswith('الاسم '):
            # البحث بالاسم
            name = search_text[5:].strip()
            cursor.execute("""
                SELECT id, full_name, wallet_number, phone, telegram_id, balance, is_active, role
                FROM users 
                WHERE full_name LIKE ? AND id != ?
                ORDER BY full_name
                LIMIT 10
            """, (f"%{name}%", user['id']))
            
        elif search_text.startswith('المحفظة '):
            # البحث برقم المحفظة
            wallet = search_text[8:].strip()
            cursor.execute("""
                SELECT id, full_name, wallet_number, phone, telegram_id, balance, is_active, role
                FROM users 
                WHERE wallet_number = ? AND id != ?
            """, (wallet, user['id']))
            
        elif search_text.startswith('الهاتف '):
            # البحث برقم الهاتف
            phone = search_text[7:].strip()
            cursor.execute("""
                SELECT id, full_name, wallet_number, phone, telegram_id, balance, is_active, role
                FROM users 
                WHERE phone LIKE ? AND id != ?
                ORDER BY full_name
                LIMIT 10
            """, (f"%{phone}%", user['id']))
            
        elif search_text.startswith('المعرف '):
            # البحث بمعرف التلغرام
            username = search_text[7:].strip().replace('@', '')
            cursor.execute("""
                SELECT id, full_name, wallet_number, phone, telegram_id, balance, is_active, role
                FROM users 
                WHERE CAST(telegram_id AS TEXT) LIKE ? AND id != ?
                ORDER BY full_name
                LIMIT 10
            """, (f"%{username}%", user['id']))
        else:
            # بحث عام في جميع الحقول
            cursor.execute("""
                SELECT id, full_name, wallet_number, phone, telegram_id, balance, is_active, role
                FROM users 
                WHERE (full_name LIKE ? OR wallet_number LIKE ? OR phone LIKE ? OR CAST(telegram_id AS TEXT) LIKE ?) 
                AND id != ?
                ORDER BY full_name
                LIMIT 10
            """, (f"%{search_text}%", f"%{search_text}%", f"%{search_text}%", f"%{search_text}%", user['id']))

        search_results = cursor.fetchall()
        conn.close()

        if not search_results:
            await update.message.reply_text(
                f"❌ **لم يتم العثور على نتائج**\n\n"
                f"🔍 تم البحث عن: `{search_text}`\n"
                f"💡 تأكد من صحة البيانات وحاول مرة أخرى\n\n"
                f"🔄 للبحث مرة أخرى: /transfer",
                parse_mode='Markdown'
            )
            context.user_data.pop('awaiting_user_search', None)
            return

        # عرض النتائج
        result_text = f"""
🔍 **نتائج البحث** 🔍

👤 **{user['full_name']}**
💰 رصيدك: **{user['balance']:,.2f}** ريال

📊 **تم العثور على {len(search_results)} نتيجة:**

"""

        keyboard = []
        for i, result in enumerate(search_results, 1):
            user_id, full_name, wallet_number, phone, telegram_id, balance, is_active, role = result
            status_emoji = "✅" if is_active else "⏳"
            role_emoji = "👑" if role == 'admin' else "🏪" if role == 'supplier' else "👤"
            
            result_text += f"""
{i}️⃣ {status_emoji} **{full_name}** {role_emoji}
   💳 المحفظة: `{wallet_number}`
   📱 الهاتف: {phone or 'غير متاح'}
   💰 الرصيد: {balance:,.2f} ريال
   ━━━━━━━━━━━━━━━━━━━━━━━━━
"""
            
            # إضافة زر للاختيار
            keyboard.append([InlineKeyboardButton(
                f"{i}️⃣ {full_name[:20]}... - {wallet_number}",
                callback_data=f"select_user_{user_id}"
            )])

        # إضافة أزرار إضافية
        keyboard.extend([
            [InlineKeyboardButton('🔍 بحث جديد', callback_data='transfer_to_friend'),
             InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')],
            [InlineKeyboardButton('❌ إلغاء', callback_data='cancel')]
        ])

        await update.message.reply_text(
            result_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
        # حفظ النتائج للاختيار
        context.user_data['search_results'] = {str(result[0]): result for result in search_results}
        context.user_data.pop('awaiting_user_search', None)

    except sqlite3.OperationalError as db_error:
        logger.error(f"Database error in user search: {db_error}")
        await update.message.reply_text(
            "❌ **خطأ في قاعدة البيانات** ❌\n\n"
            "🔄 يرجى المحاولة مرة أخرى بعد قليل",
            parse_mode='Markdown'
        )
        context.user_data.pop('awaiting_user_search', None)
    except Exception as e:
        logger.error(f"Error in process user search: {e}")
        await update.message.reply_text(
            "❌ **حدث خطأ في البحث** ❌\n\n"
            f"🔍 **التفاصيل:** {str(e)[:100]}...\n\n"
            "🔄 **يرجى المحاولة مرة أخرى**",
            parse_mode='Markdown'
        )
        context.user_data.pop('awaiting_user_search', None)

async def select_user_for_transfer(update: Update, context: CallbackContext, selected_user_id: str):
    """اختيار مستخدم لإرسال الرصيد"""
    try:
        user = get_user(update.effective_user.id)
        if not user:
            await update.callback_query.edit_message_text("❌ يرجى التسجيل أولاً /start")
            return

        # الحصول على بيانات المستخدم المختار
        search_results = context.user_data.get('search_results', {})
        if selected_user_id not in search_results:
            await update.callback_query.edit_message_text("❌ المستخدم غير موجود")
            return

        selected_user = search_results[selected_user_id]
        target_id, target_name, target_wallet, target_phone, target_username, target_balance, target_active, target_role = selected_user

        if not target_active:
            await update.callback_query.edit_message_text(
                "❌ **المستخدم غير مفعل**\n\n"
                f"👤 {target_name}\n"
                f"💳 {target_wallet}\n\n"
                "لا يمكن إرسال رصيد لمستخدم غير مفعل"
            )
            return

        # طلب المبلغ
        transfer_text = f"""
💸 **تحويل رصيد** 💸

👤 **المرسل:** {user['full_name']}
💰 **رصيدك:** {user['balance']:,.2f} ريال

📤 **المستقبل:**
👤 الاسم: **{target_name}**
💳 المحفظة: **{target_wallet}**
📱 الهاتف: {target_phone or 'غير متاح'}
💰 رصيده: {target_balance:,.2f} ريال

💡 **اكتب المبلغ الذي تريد إرساله:**

⚠️ **ملاحظات مهمة:**
• رسوم التحويل: مجاني 🆓
• الحد الأدنى: 50 ريال
• الحد الأقصى: {min(user['balance'] - 10, 50000):,.0f} ريال
• تأكد من صحة البيانات قبل التأكيد
"""

        keyboard = [
            [InlineKeyboardButton('💰 100 ريال', callback_data=f'amount_100_{selected_user_id}'),
             InlineKeyboardButton('💰 500 ريال', callback_data=f'amount_500_{selected_user_id}')],
            [InlineKeyboardButton('💰 1000 ريال', callback_data=f'amount_1000_{selected_user_id}'),
             InlineKeyboardButton('💰 5000 ريال', callback_data=f'amount_5000_{selected_user_id}')],
            [InlineKeyboardButton('🔙 اختيار مستخدم آخر', callback_data='transfer_to_friend'),
             InlineKeyboardButton('❌ إلغاء', callback_data='cancel')]
        ]

        await update.callback_query.edit_message_text(
            transfer_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

        # حفظ بيانات التحويل
        context.user_data['transfer_target'] = {
            'id': target_id,
            'name': target_name,
            'wallet': target_wallet,
            'phone': target_phone
        }
        context.user_data['awaiting_transfer_amount'] = True

    except Exception as e:
        logger.error(f"Error in select user for transfer: {e}")
        await update.callback_query.edit_message_text("❌ حدث خطأ في اختيار المستخدم")

# show_all_networks removed - "view all networks" option eliminated as requested

async def show_network_details(update: Update, context: CallbackContext, network_id: str):
    """عرض تفاصيل شبكة معينة"""
    try:
        user = get_user(update.effective_user.id)
        if not user:
            await update.callback_query.edit_message_text("❌ يرجى التسجيل أولاً /start")
            return

        conn = get_db_connection()
        cursor = conn.cursor()
        
        # الحصول على بيانات الشبكة
        cursor.execute('SELECT * FROM networks WHERE id = ? AND is_active = 1', (network_id,))
        network = cursor.fetchone()
        
        if not network:
            await update.callback_query.edit_message_text("❌ الشبكة غير موجودة أو غير متاحة")
            return
        
        # الحصول على فئات الكروت
        cursor.execute('''
            SELECT id, name, value, price, stock_count
            FROM card_categories 
            WHERE network_id = ? AND is_available = 1
            ORDER BY price
        ''', (network_id,))
        
        categories = cursor.fetchall()
        conn.close()
        
        # تنسيق معلومات الشبكة
        text = f"""
🏢 **{network[1]}** - {network[2]}

👤 **{user['full_name']}**
💰 رصيدك: **{user['balance']:,.2f}** ريال

📝 **الوصف:**
{network[3] or 'شبكة إنترنت موثوقة وسريعة'}

💳 **فئات الكروت المتاحة:**

"""

        keyboard = []
        
        if categories:
            for category in categories:
                cat_id, cat_name, cat_value, cat_price, cat_stock = category
                
                # تحديد حالة التوفر
                availability = "✅ متوفر" if cat_stock > 0 else "❌ نفذ"
                stock_info = f"({cat_stock} كرت)" if cat_stock > 0 else "(نفذ)"
                
                # تنسيق القيمة
                if cat_value >= 1024:
                    value_text = f"{cat_value/1024:.0f} جيجا" if cat_value >= 1024 else f"{cat_value} ميجا"
                else:
                    value_text = f"{cat_value} ريال" if cat_value >= 100 else f"{cat_value} ميجا"
                
                text += f"""
💳 **{cat_name}**
📊 القيمة: {value_text}
💰 السعر: **{cat_price:,.0f}** ريال
📦 {availability} {stock_info}
━━━━━━━━━━━━━━━━━━━━━━━━━

"""
                
                # إضافة زر شراء إذا كان متوفراً
                if cat_stock > 0 and user['balance'] >= cat_price:
                    keyboard.append([InlineKeyboardButton(
                        f"🛒 شراء {cat_name} - {cat_price:,.0f} ريال",
                        callback_data=f"buy_card_{cat_id}"
                    )])
                elif cat_stock > 0:
                    keyboard.append([InlineKeyboardButton(
                        f"💰 رصيد غير كافي - {cat_price:,.0f} ريال",
                        callback_data=f"insufficient_balance"
                    )])
        else:
            text += "❌ لا توجد فئات متاحة حالياً\n"

        # إضافة أزرار إضافية
        keyboard.extend([
            [InlineKeyboardButton('💳 محفظتي', callback_data='enhanced_wallet'),
             InlineKeyboardButton('🔙 العودة', callback_data='search_networks')],
            [InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
        ])

        await update.callback_query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

    except Exception as e:
        logger.error(f"Error in show network details: {e}")
        await update.callback_query.edit_message_text("❌ حدث خطأ في عرض تفاصيل الشبكة")

async def show_mobile_networks(update: Update, context: CallbackContext):
    """عرض شبكات المحمول"""
    try:
        user = get_user(update.effective_user.id)
        if not user:
            await update.callback_query.edit_message_text("❌ يرجى التسجيل أولاً /start")
            return

        conn = get_db_connection()
        cursor = conn.cursor()
        
        # البحث عن شبكات المحمول
        cursor.execute('''
            SELECT 
                n.id, n.name, n.provider, n.description,
                COUNT(cc.id) as card_types,
                SUM(cc.stock_count) as total_stock,
                MIN(cc.price) as min_price,
                MAX(cc.price) as max_price
            FROM networks n
            LEFT JOIN card_categories cc ON n.id = cc.network_id AND cc.is_available = 1
            WHERE n.is_active = 1 AND (
                n.name LIKE '%سبأفون%' OR 
                n.name LIKE '%إم تي إن%' OR 
                n.name LIKE '%واي%' OR
                n.name LIKE '%تيليمن%' OR
                n.provider LIKE '%محمول%' OR
                n.provider LIKE '%موبايل%'
            )
            GROUP BY n.id, n.name, n.provider, n.description
            ORDER BY n.name
        ''')
        
        networks = cursor.fetchall()
        conn.close()
        
        text = f"""
📱 **شبكات المحمول** 📱

👤 **{user['full_name']}**
💰 رصيدك: **{user['balance']:,.2f}** ريال

📊 **تم العثور على:** {len(networks)} شبكة محمول

"""

        keyboard = []
        
        if networks:
            for network in networks:
                network_id, name, provider, description, card_types, total_stock, min_price, max_price = network
                
                stock_status = "📦" if total_stock and total_stock > 0 else "❌"
                text += f"""
📱 **{name}**
📝 {description or 'شبكة محمول موثوقة'}
💳 الفئات: {card_types or 0} فئة
📦 المخزون: {total_stock or 0} كرت
━━━━━━━━━━━━━━━━━━━━━━━━━

"""
                
                keyboard.append([InlineKeyboardButton(
                    f"{stock_status} {name}",
                    callback_data=f"network_{network_id}"
                )])
        else:
            text += "❌ لا توجد شبكات محمول متاحة حالياً\n"

        # إضافة أزرار إضافية
        keyboard.extend([
            [InlineKeyboardButton('🏠 إنترنت منزلي', callback_data='home_networks'),
             InlineKeyboardButton('🔍 بحث ذكي', callback_data='search_networks')],
            [InlineKeyboardButton('🔙 عودة', callback_data='search_networks'),
             InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
        ])

        await update.callback_query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

    except Exception as e:
        logger.error(f"Error in show mobile networks: {e}")
        await update.callback_query.edit_message_text("❌ حدث خطأ في عرض شبكات المحمول")

async def show_home_networks(update: Update, context: CallbackContext):
    """عرض شبكات الإنترنت المنزلي"""
    try:
        user = get_user(update.effective_user.id)
        if not user:
            await update.callback_query.edit_message_text("❌ يرجى التسجيل أولاً /start")
            return

        conn = get_db_connection()
        cursor = conn.cursor()
        
        # البحث عن شبكات الإنترنت المنزلي
        cursor.execute('''
            SELECT 
                n.id, n.name, n.provider, n.description,
                COUNT(cc.id) as card_types,
                SUM(cc.stock_count) as total_stock,
                MIN(cc.price) as min_price,
                MAX(cc.price) as max_price
            FROM networks n
            LEFT JOIN card_categories cc ON n.id = cc.network_id AND cc.is_available = 1
            WHERE n.is_active = 1 AND (
                n.name LIKE '%نت%' OR 
                n.name LIKE '%ماكس%' OR 
                n.name LIKE '%برودباند%' OR
                n.provider LIKE '%إنترنت%' OR
                n.description LIKE '%منزلي%' OR
                n.description LIKE '%واي فاي%'
            )
            GROUP BY n.id, n.name, n.provider, n.description
            ORDER BY n.name
        ''')
        
        networks = cursor.fetchall()
        conn.close()
        
        text = f"""
🏠 **إنترنت منزلي** 🏠

👤 **{user['full_name']}**
💰 رصيدك: **{user['balance']:,.2f}** ريال

📊 **تم العثور على:** {len(networks)} شبكة إنترنت منزلي

"""

        keyboard = []
        
        if networks:
            for network in networks:
                network_id, name, provider, description, card_types, total_stock, min_price, max_price = network
                
                stock_status = "📦" if total_stock and total_stock > 0 else "❌"
                text += f"""
🏠 **{name}**
📝 {description or 'شبكة إنترنت منزلي موثوقة'}
💳 الفئات: {card_types or 0} فئة
📦 المخزون: {total_stock or 0} كرت
━━━━━━━━━━━━━━━━━━━━━━━━━

"""
                
                keyboard.append([InlineKeyboardButton(
                    f"{stock_status} {name}",
                    callback_data=f"network_{network_id}"
                )])
        else:
            text += "❌ لا توجد شبكات إنترنت منزلي متاحة حالياً\n"

        # إضافة أزرار إضافية
        keyboard.extend([
            [InlineKeyboardButton('📱 شبكات المحمول', callback_data='mobile_networks'),
             InlineKeyboardButton('🔍 بحث ذكي', callback_data='search_networks')],
            [InlineKeyboardButton('🔙 عودة', callback_data='search_networks'),
             InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
        ])

        await update.callback_query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

    except Exception as e:
        logger.error(f"Error in show home networks: {e}")
        await update.callback_query.edit_message_text("❌ حدث خطأ في عرض شبكات الإنترنت المنزلي")

async def quick_transfer_handler(update: Update, context: CallbackContext):
    """التحويل السريع"""
    try:
        user = get_user(update.effective_user.id)
        if not user:
            await update.callback_query.edit_message_text("❌ يرجى التسجيل أولاً /start")
            return
        
        text = f"""
⚡ **تحويل سريع** ⚡

👤 **{user['full_name']}**
💰 رصيدك: **{user['balance']:,.2f}** ريال

📝 **اكتب: رقم المحفظة والمبلغ**
💡 مثال: `791234567 100`

⚠️ **ملاحظات مهمة:**
• رسوم التحويل: مجاني 🆓
• الحد الأدنى: 50 ريال
• الحد الأقصى: {min(user['balance'] - 10, 50000):,.0f} ريال
• تأكد من صحة البيانات قبل الإرسال

📋 **خطوات التحويل:**
1️⃣ اكتب رقم المحفظة والمبلغ
2️⃣ تأكيد البيانات
3️⃣ إتمام التحويل فوراً
"""
        
        keyboard = [
            [InlineKeyboardButton('🔍 البحث المتقدم', callback_data='advanced_search_transfer'),
             InlineKeyboardButton('📋 سجل التحويلات', callback_data='transfer_history')],
            [InlineKeyboardButton('🔙 عودة', callback_data='transfer_to_friend'),
             InlineKeyboardButton('❌ إلغاء', callback_data='cancel')]
        ]
        
        await update.callback_query.edit_message_text(
            text, 
            reply_markup=InlineKeyboardMarkup(keyboard), 
            parse_mode='Markdown'
        )
        
        context.user_data['awaiting_simple_transfer'] = True
        
    except Exception as e:
        logger.error(f"Error in quick transfer handler: {e}")
        await update.callback_query.edit_message_text("❌ حدث خطأ في التحويل السريع")

async def search_by_type_handler(update: Update, context: CallbackContext, search_type: str):
    """البحث حسب النوع"""
    try:
        user = get_user(update.effective_user.id)
        if not user:
            await update.callback_query.edit_message_text("❌ يرجى التسجيل أولاً /start")
            return
        
        type_names = {
            "wallet": "رقم المحفظة",
            "name": "الاسم الكامل", 
            "phone": "رقم الهاتف",
            "username": "معرف التلغرام"
        }
        
        type_examples = {
            "wallet": "791234567",
            "name": "أحمد محمد علي",
            "phone": "770123456", 
            "username": "@ahmed123"
        }
        
        search_name = type_names.get(search_type, "غير محدد")
        example = type_examples.get(search_type, "")
        
        text = f"""
🔍 **البحث بـ{search_name}** 🔍

👤 **{user['full_name']}**
💰 رصيدك: **{user['balance']:,.2f}** ريال

📝 **اكتب {search_name} للمستخدم:**

💡 **مثال:** `{example}`

⚠️ **ملاحظات:**
• اكتب البيانات بدقة
• يمكن البحث بالجزء أو الكامل
• سيتم عرض النتائج المطابقة
"""
        
        keyboard = [
            [InlineKeyboardButton('🔙 طرق البحث الأخرى', callback_data='advanced_search_transfer'),
             InlineKeyboardButton('❌ إلغاء', callback_data='cancel')]
        ]
        
        await update.callback_query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
        context.user_data['awaiting_user_search'] = True
        context.user_data['search_type'] = search_type
        
    except Exception as e:
        logger.error(f"Error in search by type handler: {e}")
        await update.callback_query.edit_message_text("❌ حدث خطأ في البحث")

async def process_amount_selection(update: Update, context: CallbackContext, amount: str, user_id: str):
    """معالجة اختيار المبلغ"""
    try:
        user = get_user(update.effective_user.id)
        if not user:
            await update.callback_query.edit_message_text("❌ يرجى التسجيل أولاً /start")
            return
        
        # التحقق من البيانات المحفوظة
        search_results = context.user_data.get('search_results', {})
        if user_id not in search_results:
            await update.callback_query.edit_message_text("❌ بيانات المستخدم غير متاحة")
            return
        
        selected_user = search_results[user_id]
        target_id, target_name, target_wallet, target_phone, target_username, target_balance, target_active, target_role = selected_user
        
        transfer_amount = float(amount)
        fee = 0  # FREE transfers - no fees
        total_needed = transfer_amount + fee
        
        # التحقق من الرصيد
        if user['balance'] < total_needed:
            await update.callback_query.edit_message_text(
                f"❌ **رصيد غير كافي**\n\n"
                f"💰 رصيدك: {user['balance']:,.2f} ريال\n"
                f"💸 المطلوب: {total_needed:,.2f} ريال\n"
                f"   • المبلغ: {transfer_amount:,.2f} ريال\n"
                f"   • الرسوم: {fee:,.2f} ريال\n\n"
                f"💡 تحتاج {total_needed - user['balance']:,.2f} ريال إضافية"
            )
            return
        
        # عرض تأكيد التحويل
        confirmation_text = f"""
✅ **تأكيد التحويل** ✅

👤 **من:** {user['full_name']}
💳 محفظتك: {user['wallet_number']}

📤 **إلى:** {target_name}
💳 محفظة المستقبل: {target_wallet}

💰 **تفاصيل التحويل:**
💸 المبلغ: **{transfer_amount:,.2f}** ريال
💳 الرسوم: **{fee:,.2f}** ريال
💵 الإجمالي: **{total_needed:,.2f}** ريال

💰 **رصيدك بعد التحويل:** {user['balance'] - total_needed:,.2f} ريال

⚠️ **هل تريد إتمام التحويل؟**
"""
        
        keyboard = [
            [InlineKeyboardButton('✅ تأكيد التحويل', callback_data=f'confirm_transfer_{user_id}_{amount}'),
             InlineKeyboardButton('❌ إلغاء', callback_data='cancel')],
            [InlineKeyboardButton('🔙 تغيير المبلغ', callback_data=f'select_user_{user_id}')]
        ]
        
        await update.callback_query.edit_message_text(
            confirmation_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Error in process amount selection: {e}")
        await update.callback_query.edit_message_text("❌ حدث خطأ في معالجة المبلغ")

async def process_card_purchase(update: Update, context: CallbackContext, category_id: str):
    """معالجة شراء الكرت"""
    try:
        user = get_user(update.effective_user.id)
        if not user:
            await update.callback_query.edit_message_text("❌ يرجى التسجيل أولاً /start")
            return
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # الحصول على بيانات فئة الكرت
        cursor.execute('''
            SELECT cc.*, n.name as network_name
            FROM card_categories cc
            JOIN networks n ON cc.network_id = n.id
            WHERE cc.id = ? AND cc.is_available = 1
        ''', (category_id,))
        
        category = cursor.fetchone()
        
        if not category:
            await update.callback_query.edit_message_text("❌ فئة الكرت غير متاحة")
            return
        
        cat_id, network_id, cat_name, cat_value, cat_price, currency, is_available, stock_count, created_at, updated_at, network_name = category
        
        # التحقق من التوفر
        if stock_count <= 0:
            await update.callback_query.edit_message_text(
                f"❌ **الكرت غير متوفر**\n\n"
                f"💳 {cat_name}\n"
                f"🏢 {network_name}\n"
                f"📦 المخزون: نفذ\n\n"
                f"💡 تحقق لاحقاً أو اختر فئة أخرى"
            )
            return
        
        # التحقق من الرصيد
        if user['balance'] < cat_price:
            await update.callback_query.edit_message_text(
                f"❌ **رصيد غير كافي**\n\n"
                f"💳 {cat_name}\n"
                f"💰 السعر: {cat_price:,.2f} ريال\n"
                f"💵 رصيدك: {user['balance']:,.2f} ريال\n"
                f"💡 تحتاج {cat_price - user['balance']:,.2f} ريال إضافية"
            )
            return
        
        # عرض تأكيد الشراء
        confirmation_text = f"""
🛒 **تأكيد الشراء** 🛒

👤 **المشتري:** {user['full_name']}
💳 محفظتك: {user['wallet_number']}

🛒 **تفاصيل الشراء:**
🏢 الشبكة: **{network_name}**
💳 الكرت: **{cat_name}**
📊 القيمة: {cat_value} {"جيجا" if cat_value >= 1024 else "ميجا" if cat_value < 100 else "ريال"}
💰 السعر: **{cat_price:,.2f}** ريال

💰 **رصيدك بعد الشراء:** {user['balance'] - cat_price:,.2f} ريال

⚠️ **هل تريد إتمام الشراء؟**
"""
        
        keyboard = [
            [InlineKeyboardButton('✅ تأكيد الشراء', callback_data=f'confirm_purchase_{category_id}'),
             InlineKeyboardButton('❌ إلغاء', callback_data='cancel')],
            [InlineKeyboardButton('🔙 اختيار كرت آخر', callback_data=f'network_{network_id}')]
        ]
        
        await update.callback_query.edit_message_text(
            confirmation_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
        conn.close()
        
    except Exception as e:
        logger.error(f"Error in process card purchase: {e}")
        await update.callback_query.edit_message_text("❌ حدث خطأ في معالجة الشراء")

# Export main handlers for use in main bot file
COMMAND_HANDLERS = {
    'start': start,
    'wallet': wallet_handler,
    'admin': admin_handler,
    'cancel': cancel,
    # wifi_search and search_networks now handled by unified system in main bot
    'send_balance': send_balance_handler,
    'transfer_to_friend': send_balance_handler,
    'personal_reports': personal_reports_handler,
    # promotions now handled by enhanced system in main bot
    'my_notifications': my_notifications_handler,
    'account_settings': account_settings_handler,
    'my_ratings': my_ratings_handler,

    'supplier_panel': lambda u, c: enhanced_placeholder_handler(u, c, "🏪 لوحة المزود", "لوحة تحكم خاصة بالمزودين"),
    'manage_networks': lambda u, c: supplier_manage_networks(u, c),
    'upload_cards': lambda u, c: enhanced_placeholder_handler(u, c, "📤 رفع كروت", "رفع وإدارة كروت الشحن"),
    'sales_reports': lambda u, c: enhanced_placeholder_handler(u, c, "📈 تقارير المبيعات", "تقارير مفصلة عن مبيعاتك"),
    'buy_cards': lambda u, c: enhanced_placeholder_handler(u, c, "🛒 شراء الكروت", "شراء كروت الشحن من الشبكات المتاحة"),
    'help': help_handler,
    'transaction_details': lambda u, c: enhanced_placeholder_handler(u, c, "📊 تفاصيل المعاملات", "عرض تفاصيل معاملاتك المالية"),
    'wallet_stats': lambda u, c: enhanced_placeholder_handler(u, c, "📈 إحصائيات المحفظة", "إحصائيات مفصلة عن محفظتك"),
    'account_statement': lambda u, c: enhanced_placeholder_handler(u, c, "📄 كشف الحساب", "كشف حساب مفصل بجميع المعاملات"),
    'deposit_balance': lambda u, c: enhanced_placeholder_handler(u, c, "💰 إيداع رصيد", "إيداع رصيد في محفظتك"),
    'wallet_settings': lambda u, c: enhanced_placeholder_handler(u, c, "⚙️ إعدادات المحفظة", "إعدادات وتخصيص محفظتك"),
    'contact_admin': lambda u, c: enhanced_placeholder_handler(u, c, "📞 التواصل مع الإدارة", "التواصل مع فريق الدعم"),
    'account_status': lambda u, c: enhanced_placeholder_handler(u, c, "📊 حالة الحساب", "عرض حالة وإحصائيات حسابك"),
    'advanced_search_transfer': search_user_for_transfer,
    'quick_transfer': quick_transfer_handler,
    'transfer_history': lambda u, c: enhanced_placeholder_handler(u, c, "📋 سجل التحويلات", "سجل جميع عمليات التحويل"),
    'search_by_wallet': lambda u, c: search_by_type_handler(u, c, "wallet"),
    'search_by_name': lambda u, c: search_by_type_handler(u, c, "name"),
    'search_by_phone': lambda u, c: search_by_type_handler(u, c, "phone"),
    'search_by_username': lambda u, c: search_by_type_handler(u, c, "username"),
    # 'all_networks' removed - "view all networks" option eliminated
    'mobile_networks': show_mobile_networks,
    'home_networks': show_home_networks,
    'search_by_network_name': lambda u, c: search_networks_by_name(u, c),
    'networks_by_price': lambda u, c: enhanced_placeholder_handler(u, c, "💰 ترتيب بالسعر", "ترتيب الشبكات حسب السعر"),
    'popular_networks': lambda u, c: enhanced_placeholder_handler(u, c, "⭐ الأكثر طلباً", "الشبكات الأكثر شعبية"),
    'insufficient_balance': lambda u, c: enhanced_placeholder_handler(u, c, "💰 رصيد غير كافي", "تحتاج لشحن رصيدك أولاً"),
    'supplier_manage_networks': lambda u, c: supplier_manage_networks(u, c),
    'add_new_network': lambda u, c: add_new_network_handler(u, c),
    'network_sales_reports': lambda u, c: enhanced_placeholder_handler(u, c, "📊 تقارير المبيعات", "عرض تقارير مفصلة عن مبيعات شبكاتك"),
    'manage_stock': lambda u, c: enhanced_placeholder_handler(u, c, "📦 إدارة المخزون", "إدارة مخزون الكروت والشبكات"),
    'profit_analysis': lambda u, c: enhanced_placeholder_handler(u, c, "📈 تحليل الأرباح", "تحليل مفصل للأرباح والعوائد"),
}

from telegram.ext import MessageHandler, CallbackQueryHandler, filters

CONVERSATION_STATES = {
    GET_FULL_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_full_name)],
    GET_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_phone)],
    CHOOSE_ROLE: [CallbackQueryHandler(choose_role, pattern='^role_')],
}

async def supplier_manage_networks(update: Update, context: CallbackContext):
    """إدارة الشبكات للمزودين"""
    try:
        user = get_user(update.effective_user.id)
        if not user:
            await update.callback_query.edit_message_text("❌ يرجى التسجيل أولاً /start")
            return
        
        if user['role'] != 'supplier':
            await update.callback_query.edit_message_text("❌ هذه الميزة متاحة للمزودين فقط")
            return
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # الحصول على شبكات المزود
        cursor.execute('''
            SELECT id, name, description, location, is_active, created_at
            FROM networks 
            WHERE created_by = ?
            ORDER BY created_at DESC
        ''', (user['id'],))
        
        my_networks = cursor.fetchall()
        
        # الحصول على إجمالي الكروت المباعة
        cursor.execute('''
            SELECT COUNT(*) as total_sold, SUM(cc.price) as total_revenue
            FROM cards c
            JOIN card_categories cc ON c.category_id = cc.id
            JOIN networks n ON cc.network_id = n.id
            WHERE n.created_by = ? AND c.is_sold = 1
        ''', (user['id'],))
        
        sales_data = cursor.fetchone()
        total_sold = sales_data[0] if sales_data else 0
        total_revenue = sales_data[1] if sales_data else 0.0
        
        conn.close()
        
        text = f"""
🏪 **إدارة شبكاتي** 🏪

👤 المزود: **{user['full_name']}**
💰 رصيدك: **{user['balance']:,.2f}** ريال

📊 **إحصائيات المبيعات:**
💳 إجمالي الكروت المباعة: **{total_sold:,}** كرت
💰 إجمالي الإيرادات: **{total_revenue:,.2f}** ريال

🌐 **شبكاتي ({len(my_networks)} شبكة):**

"""

        keyboard = []
        
        if my_networks:
            for network in my_networks:
                network_id, name, description, location, is_active, created_at = network
                status_emoji = "✅" if is_active else "⏳"
                
                text += f"""
{status_emoji} **{name}**
📝 {description or 'شبكة واي فاي منزلية'}
📍 الموقع: {location or 'غير محدد'}
📅 أضيفت: {created_at[:10]}
━━━━━━━━━━━━━━━━━━━━━━━━━

"""
                
                keyboard.append([InlineKeyboardButton(
                    f"{status_emoji} {name}",
                    callback_data=f"manage_network_{network_id}"
                )])
        else:
            text += """
📋 **لم تقم بإضافة أي شبكات بعد**

💡 **لإضافة شبكة جديدة:**
• اضغط على "إضافة شبكة جديدة"
• أدخل اسم الشبكة
• أضف وصفاً للشبكة
• أضف فئات الكروت والأسعار

🎯 **فوائد إضافة الشبكات:**
• زيادة مبيعاتك
• وصول أكبر للعملاء
• إدارة سهلة للمخزون
"""

        # إضافة أزرار الإدارة
        keyboard.extend([
            [InlineKeyboardButton('➕ إضافة شبكة جديدة', callback_data='add_new_network'),
             InlineKeyboardButton('📊 تقارير المبيعات', callback_data='network_sales_reports')],
            [InlineKeyboardButton('📦 إدارة المخزون', callback_data='manage_stock'),
             InlineKeyboardButton('💰 تحليل الأرباح', callback_data='profit_analysis')],
            [InlineKeyboardButton('🏪 لوحة المزود', callback_data='supplier_panel'),
             InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
        ])

        await update.callback_query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

    except Exception as e:
        logger.error(f"Error in supplier manage networks: {e}")
        await update.callback_query.edit_message_text("❌ حدث خطأ في إدارة الشبكات")

async def add_new_network_handler(update: Update, context: CallbackContext):
    """إضافة شبكة جديدة"""
    try:
        user = get_user(update.effective_user.id)
        if not user:
            await update.callback_query.edit_message_text("❌ يرجى التسجيل أولاً /start")
            return
        
        if user['role'] != 'supplier':
            await update.callback_query.edit_message_text("❌ هذه الميزة متاحة للمزودين فقط")
            return
        
        text = f"""
➕ **إضافة شبكة واي فاي جديدة** ➕

👤 المزود: **{user['full_name']}**

📝 **أدخل اسم الشبكة:**

💡 **أمثلة على أسماء الشبكات:**
• `واي فاي الرحمن`
• `شبكة النور للإنترنت`
• `واي فاي البركة`
• `إنترنت الأمل المنزلي`

⚠️ **ملاحظات مهمة:**
• اختر اسماً واضحاً وجذاباً
• تجنب الأسماء المكررة
• يفضل أن يعكس الاسم منطقتك أو خدمتك
• لا تستخدم رموز غريبة

📝 **اكتب اسم الشبكة:**
"""
        
        keyboard = [
            [InlineKeyboardButton('🔙 إدارة شبكاتي', callback_data='manage_networks'),
             InlineKeyboardButton('❌ إلغاء', callback_data='cancel')]
        ]
        
        await update.callback_query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
        context.user_data['awaiting_network_name'] = True
        
    except Exception as e:
        logger.error(f"Error in add new network handler: {e}")
        await update.callback_query.edit_message_text("❌ حدث خطأ في إضافة شبكة جديدة")

async def process_network_creation(update: Update, context: CallbackContext, network_name: str):
    """معالجة إنشاء شبكة جديدة"""
    try:
        user = get_user(update.effective_user.id)
        if not user:
            await update.message.reply_text("❌ يرجى التسجيل أولاً /start")
            return
        
        if user['role'] != 'supplier':
            await update.message.reply_text("❌ هذه الميزة متاحة للمزودين فقط")
            return
        
        network_name = network_name.strip()
        
        if len(network_name) < 3:
            await update.message.reply_text("❌ اسم الشبكة قصير جداً. يجب أن يكون على الأقل 3 أحرف")
            return
        
        if len(network_name) > 50:
            await update.message.reply_text("❌ اسم الشبكة طويل جداً. الحد الأقصى 50 حرف")
            return
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # التحقق من عدم تكرار الاسم
        cursor.execute('SELECT id FROM networks WHERE name = ?', (network_name,))
        if cursor.fetchone():
            await update.message.reply_text("❌ اسم الشبكة موجود بالفعل. اختر اسماً آخر")
            return
        
        # إضافة الشبكة الجديدة
        cursor.execute('''
            INSERT INTO networks (supplier_id, name, provider, description, created_by, is_active, is_approved)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (user['id'], network_name, user['full_name'], f'شبكة واي فاي منزلية - {network_name}', user['id'], 1, 1))
        
        network_id = cursor.lastrowid
        
        conn.commit()
        conn.close()
        
        # طلب وصف الشبكة
        text = f"""
✅ **تم إنشاء الشبكة بنجاح!** ✅

🌐 **اسم الشبكة:** {network_name}
👤 **المزود:** {user['full_name']}
📅 **تاريخ الإنشاء:** اليوم

📝 **الآن أدخل وصفاً للشبكة:**

💡 **أمثلة على الوصف:**
• `شبكة واي فاي منزلية عالية السرعة في منطقة الصافية`
• `إنترنت منزلي مستقر للألعاب والدراسة`
• `واي فاي منزلي سريع ومناسب للعائلات`

⚠️ **نصائح للوصف:**
• اذكر المنطقة إذا أمكن
• أشر إلى جودة الخدمة
• اذكر الاستخدامات المناسبة
• لا تتجاوز 100 حرف

📝 **اكتب وصف الشبكة:**
"""
        
        keyboard = [
            [InlineKeyboardButton('⏭️ تخطي الوصف', callback_data=f'skip_description_{network_id}'),
             InlineKeyboardButton('❌ إلغاء', callback_data='cancel')]
        ]
        
        await update.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
        context.user_data['awaiting_network_description'] = True
        context.user_data['new_network_id'] = network_id
        context.user_data.pop('awaiting_network_name', None)
        
    except Exception as e:
        logger.error(f"Error in process network creation: {e}")
        await update.message.reply_text("❌ حدث خطأ في إنشاء الشبكة")

async def process_network_description(update: Update, context: CallbackContext, description: str):
    """معالجة وصف الشبكة"""
    try:
        user = get_user(update.effective_user.id)
        if not user:
            await update.message.reply_text("❌ يرجى التسجيل أولاً /start")
            return
        
        if user['role'] != 'supplier':
            await update.message.reply_text("❌ هذه الميزة متاحة للمزودين فقط")
            return
        
        network_id = context.user_data.get('new_network_id')
        if not network_id:
            await update.message.reply_text("❌ لم يتم العثور على معرف الشبكة")
            return
        
        description = description.strip()
        
        if len(description) > 100:
            await update.message.reply_text("❌ الوصف طويل جداً. الحد الأقصى 100 حرف")
            return
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # تحديث وصف الشبكة
        cursor.execute('''
            UPDATE networks 
            SET description = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND created_by = ?
        ''', (description, network_id, user['id']))
        
        conn.commit()
        conn.close()
        
        # طلب الموقع
        text = f"""
✅ **تم تحديث وصف الشبكة بنجاح!** ✅

📝 **الوصف المضاف:** {description}

📍 **الآن أدخل موقع الشبكة:**

💡 **أمثلة على المواقع:**
• `منطقة الصافية - صنعاء`
• `حي الزراعة - عدن`
• `شارع هائل - تعز`
• `مدينة الحديدة - المدينة`
• `إب - جبلة`

⚠️ **نصائح لكتابة الموقع:**
• اذكر الحي أو المنطقة بوضوح
• أضف المحافظة إذا أمكن
• استخدم أسماء معروفة محلياً
• لا تتجاوز 50 حرف
• يمكن تخطي هذه الخطوة

📍 **اكتب موقع الشبكة:**

🎯 **خطوات إضافة فئة كرت:**
1️⃣ اختر نوع الكرت (جيجا أو رصيد)
2️⃣ حدد القيمة (مثل: 1 جيجا أو 1000 ريال)
3️⃣ حدد السعر للكرت الواحد
4️⃣ حدد عدد الكروت المتوفرة

💡 **أمثلة على فئات الكروت:**
• كرت 500 ميجا - 1000 ريال (50 كرت متوفر)
• كرت 1 جيجا - 1800 ريال (30 كرت متوفر)
• كرت 2 جيجا - 3200 ريال (20 كرت متوفر)

🚀 **بدء إضافة الفئات:**
"""
        
        keyboard = [
            [InlineKeyboardButton('⏭️ تخطي الموقع', callback_data=f'skip_location_{network_id}'),
             InlineKeyboardButton('❌ إلغاء', callback_data='cancel')]
        ]
        
        await update.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
        context.user_data['awaiting_network_location'] = True
        context.user_data.pop('awaiting_network_description', None)
        
    except Exception as e:
        logger.error(f"Error in process network description: {e}")
        await update.message.reply_text("❌ حدث خطأ في معالجة وصف الشبكة")

async def process_network_location(update: Update, context: CallbackContext, location: str):
    """معالجة موقع الشبكة"""
    try:
        user = get_user(update.effective_user.id)
        if not user:
            await update.message.reply_text("❌ يرجى التسجيل أولاً /start")
            return
        
        if user['role'] != 'supplier':
            await update.message.reply_text("❌ هذه الميزة متاحة للمزودين فقط")
            return
        
        network_id = context.user_data.get('new_network_id')
        if not network_id:
            await update.message.reply_text("❌ لم يتم العثور على معرف الشبكة")
            return
        
        location = location.strip()
        
        if len(location) > 50:
            await update.message.reply_text("❌ الموقع طويل جداً. الحد الأقصى 50 حرف")
            return
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # تحديث موقع الشبكة
        cursor.execute('''
            UPDATE networks 
            SET location = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND created_by = ?
        ''', (location, network_id, user['id']))
        
        conn.commit()
        conn.close()
        
        # عرض خيارات إضافة فئات الكروت
        text = f"""
✅ **تم تحديث موقع الشبكة بنجاح!** ✅

📍 **الموقع المضاف:** {location}

💳 **الآن أضف فئات الكروت:**

🎯 **خطوات إضافة فئة كرت:**
1️⃣ اختر نوع الكرت (جيجا أو رصيد)
2️⃣ حدد القيمة (مثل: 1 جيجا أو 1000 ريال)
3️⃣ حدد السعر للكرت الواحد
4️⃣ حدد عدد الكروت المتوفرة

💡 **أمثلة على فئات الكروت:**
• كرت 500 ميجا - 1000 ريال (50 كرت متوفر)
• كرت 1 جيجا - 1800 ريال (30 كرت متوفر)
• كرت 2 جيجا - 3200 ريال (20 كرت متوفر)

🚀 **بدء إضافة الفئات:**
"""
        
        keyboard = [
            [InlineKeyboardButton('💳 إضافة فئة كرت جديدة', callback_data=f'add_card_category_{network_id}'),
             InlineKeyboardButton('⏭️ إنهاء لاحقاً', callback_data='manage_networks')],
            [InlineKeyboardButton('🔙 إدارة شبكاتي', callback_data='manage_networks'),
             InlineKeyboardButton('❌ إلغاء', callback_data='cancel')]
        ]
        
        await update.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
        context.user_data.pop('awaiting_network_location', None)
        context.user_data.pop('new_network_id', None)
        
    except Exception as e:
        logger.error(f"Error in process network location: {e}")
        await update.message.reply_text("❌ حدث خطأ في معالجة موقع الشبكة")

async def skip_network_location(update: Update, context: CallbackContext, network_id: str):
    """تخطي إضافة الموقع"""
    try:
        user = get_user(update.effective_user.id)
        if not user:
            await update.callback_query.edit_message_text("❌ يرجى التسجيل أولاً /start")
            return
        
        if user['role'] != 'supplier':
            await update.callback_query.edit_message_text("❌ هذه الميزة متاحة للمزودين فقط")
            return
        
        # عرض خيارات إضافة فئات الكروت
        text = f"""
⏭️ **تم تخطي إضافة الموقع** ⏭️

💳 **الآن أضف فئات الكروت:**

🎯 **خطوات إضافة فئة كرت:**
1️⃣ اختر نوع الكرت (جيجا أو رصيد)
2️⃣ حدد القيمة (مثل: 1 جيجا أو 1000 ريال)
3️⃣ حدد السعر للكرت الواحد
4️⃣ حدد عدد الكروت المتوفرة

💡 **أمثلة على فئات الكروت:**
• كرت 500 ميجا - 1000 ريال (50 كرت متوفر)
• كرت 1 جيجا - 1800 ريال (30 كرت متوفر)
• كرت 2 جيجا - 3200 ريال (20 كرت متوفر)

🚀 **بدء إضافة الفئات:**
"""
        
        keyboard = [
            [InlineKeyboardButton('💳 إضافة فئة كرت جديدة', callback_data=f'add_card_category_{network_id}'),
             InlineKeyboardButton('⏭️ إنهاء لاحقاً', callback_data='manage_networks')],
            [InlineKeyboardButton('🔙 إدارة شبكاتي', callback_data='manage_networks'),
             InlineKeyboardButton('❌ إلغاء', callback_data='cancel')]
        ]
        
        await update.callback_query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
        context.user_data.pop('awaiting_network_location', None)
        context.user_data.pop('new_network_id', None)
        
    except Exception as e:
        logger.error(f"Error in skip network location: {e}")
        await update.callback_query.edit_message_text("❌ حدث خطأ في تخطي الموقع")

async def search_networks_by_name(update: Update, context: CallbackContext):
    """البحث عن الشبكات بالاسم أو الموقع"""
    try:
        user = get_user(update.effective_user.id)
        if not user:
            await update.callback_query.edit_message_text("❌ يرجى التسجيل أولاً /start")
            return
        
        text = f"""
🔍 **البحث عن شبكة واي فاي** 🔍

👤 مرحباً **{user['full_name']}**
💰 رصيدك: **{user['balance']:,.2f}** ريال

📝 **اكتب للبحث:**

💡 **يمكنك البحث بـ:**
• اسم الشبكة (مثل: واي فاي الرحمن)
• الموقع (مثل: الصافية، صنعاء)
• المزود (مثل: أحمد محمد)

🔍 **أمثلة للبحث:**
• `الرحمن`
• `الصافية`
• `صنعاء`
• `واي فاي`

📝 **اكتب كلمة البحث:**
"""
        
        keyboard = [
            [InlineKeyboardButton('📍 بحث بالموقع', callback_data='search_by_location'),
             InlineKeyboardButton('🔍 بحث ذكي', callback_data='search_networks')],
            [InlineKeyboardButton('🔙 عودة', callback_data='search_networks'),
             InlineKeyboardButton('❌ إلغاء', callback_data='cancel')]
        ]
        
        await update.callback_query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
        context.user_data['awaiting_network_search'] = True
        
    except Exception as e:
        logger.error(f"Error in search networks by name: {e}")
        await update.callback_query.edit_message_text("❌ حدث خطأ في البحث")

async def process_network_search(update: Update, context: CallbackContext, search_term: str):
    """معالجة البحث عن الشبكات"""
    try:
        user = get_user(update.effective_user.id)
        if not user:
            await update.message.reply_text("❌ يرجى التسجيل أولاً /start")
            return
        
        search_term = search_term.strip()
        
        if len(search_term) < 2:
            await update.message.reply_text("❌ كلمة البحث قصيرة جداً. أدخل على الأقل حرفين")
            return
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # البحث في الشبكات
        cursor.execute('''
            SELECT 
                n.id, n.name, n.provider, n.description, n.location,
                COUNT(DISTINCT nc.card_value) as card_types,
                COUNT(nc.id) as total_stock,
                MIN(nc.card_value) as min_price,
                MAX(nc.card_value) as max_price
            FROM networks n
            LEFT JOIN network_cards nc ON n.id = nc.network_id AND nc.is_sold = 0
            LEFT JOIN supplier_codes sc ON sc.supplier_id = n.supplier_id
            WHERE n.is_active = 1 AND n.is_approved = 1 AND (
                n.name LIKE ? OR 
                n.location LIKE ? OR 
                n.provider LIKE ? OR 
                n.description LIKE ? OR
                n.network_code LIKE ? OR
                sc.supplier_code LIKE ?
            )
            GROUP BY n.id, n.name, n.provider, n.description, n.location
            ORDER BY n.name
            LIMIT 10
        ''', (
            f"%{search_term}%", f"%{search_term}%", f"%{search_term}%", f"%{search_term}%",
            f"%{search_term}%", f"%{search_term}%"
        ))
        
        search_results = cursor.fetchall()
        conn.close()
        
        if not search_results:
            text = f"""
❌ **لم يتم العثور على نتائج** ❌

🔍 تم البحث عن: `{search_term}`

💡 **نصائح للبحث:**
• تأكد من صحة كتابة كلمة البحث
• جرب البحث بكلمات أقل
• ابحث بالموقع بدلاً من الاسم
• تأكد من وجود شبكات متاحة

🔄 **جرب البحث مرة أخرى:**
"""
            
            keyboard = [
                [InlineKeyboardButton('🔍 بحث جديد', callback_data='search_by_network_name'),
                 InlineKeyboardButton('🔍 بحث ذكي', callback_data='search_networks')],
                [InlineKeyboardButton('🔙 عودة', callback_data='search_networks')]
            ]
            
            await update.message.reply_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            return
        
        # عرض نتائج البحث
        text = f"""
🔍 **نتائج البحث** 🔍

👤 **{user['full_name']}**
💰 رصيدك: **{user['balance']:,.2f}** ريال

📊 **تم العثور على {len(search_results)} شبكة:**

"""

        keyboard = []
        for i, network in enumerate(search_results, 1):
            network_id, name, provider, description, location, card_types, total_stock, min_price, max_price = network
            
            stock_status = "📦" if total_stock and total_stock > 0 else "❌"
            price_range = ""
            if min_price and max_price:
                if min_price == max_price:
                    price_range = f"{min_price:,.0f} ريال"
                else:
                    price_range = f"{min_price:,.0f} - {max_price:,.0f} ريال"
            
            text += f"""
{i}️⃣ **{name}** {stock_status}
📍 {location or 'غير محدد'}
👤 المزود: {provider}
💳 {card_types or 0} فئة • 📦 {total_stock or 0} كرت
💰 {price_range or 'غير محدد'}
━━━━━━━━━━━━━━━━━━━━━━━━━

"""
            
            button_text = f"{i}️⃣ {name[:15]}..."
            if total_stock and total_stock > 0:
                button_text += f" ({total_stock})"
            
            keyboard.append([InlineKeyboardButton(
                button_text,
                callback_data=f"network_{network_id}"
            )])

        # إضافة أزرار إضافية
        keyboard.extend([
            [InlineKeyboardButton('🔍 بحث جديد', callback_data='search_by_network_name'),
             InlineKeyboardButton('🔍 بحث ذكي', callback_data='search_networks')],
            [InlineKeyboardButton('🔙 عودة', callback_data='search_networks'),
             InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
        ])

        await update.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
        context.user_data.pop('awaiting_network_search', None)

    except Exception as e:
        logger.error(f"Error in process network search: {e}")
        await update.message.reply_text("❌ حدث خطأ في البحث")
        context.user_data.pop('awaiting_network_search', None)

async def redeem_coupon_handler(update: Update, context: CallbackContext):
    """معالج شحن الرصيد بكوبون"""
    try:
        # دعم كل من الأوامر المباشرة والأزرار
        if update.callback_query:
            query = update.callback_query
            await query.answer()
            user = get_user(query.from_user.id)
            is_callback = True
        else:
            user = get_user(update.message.from_user.id)
            is_callback = False
            
        if not user:
            error_text = f"{EMOJIS['error']} يرجى إرسال /start أولاً."
            if is_callback:
                await update.callback_query.edit_message_text(error_text)
            else:
                await update.message.reply_text(error_text)
            return
        
        # تنظيف أي حالات سابقة
        context.user_data.clear()
        context.user_data['redeeming_coupon'] = True
        
        text = f"""
🎟️ **شحن الرصيد بكوبون** 🎟️

{EMOJIS['user']} مرحباً **{user['full_name']}**
💰 رصيدك الحالي: **{user['balance']:,.2f}** ريال

📝 **كيفية الاستخدام:**
🔸 أدخل رقم الكوبون المكون من 9 أرقام
🔸 يجب أن يبدأ الكوبون بالحرف A
🔸 مثال: A12345678

⚠️ **ملاحظات مهمة:**
• كل كوبون يُستخدم مرة واحدة فقط
• تأكد من صحة رقم الكوبون
• الكوبون المنتهي الصلاحية لا يعمل
• سيتم إضافة القيمة فوراً ومباشرة لرصيدك عند الاستخدام

💡 **أدخل رقم الكوبون الآن:**
"""
        
        keyboard = [
            [InlineKeyboardButton('❌ إلغاء', callback_data='cancel_coupon'),
             InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
        ]
        
        if is_callback:
            await update.callback_query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
        
    except Exception as e:
        logger.error(f"Error in redeem coupon handler: {e}")
        error_text = coupon_error("شحن الكوبون")
        try:
            if update.callback_query:
                await update.callback_query.edit_message_text(error_text)
            else:
                await update.message.reply_text(error_text)
        except:
            pass

async def process_coupon_redemption(update: Update, context: CallbackContext):
    """معالجة استخدام الكوبون"""
    try:
        if not context.user_data.get('redeeming_coupon'):
            return
        
        user = get_user(update.effective_user.id)
        if not user:
            await update.message.reply_text(f"{EMOJIS['error']} يرجى إرسال /start أولاً.")
            context.user_data.clear()
            return
        
        coupon_code = update.message.text.strip().upper()
        
        # التحقق من صحة تنسيق الكوبون
        if not validate_coupon_format(coupon_code):
            await update.message.reply_text(
                "❌ **تنسيق الكوبون غير صحيح** ❌\n\n"
                "📝 **التنسيق المطلوب:**\n"
                "🔸 يجب أن يبدأ بالحرف A\n"
                "🔸 متبوع بـ 8 أرقام\n"
                "🔸 مثال: A12345678\n\n"
                "💡 **يرجى إدخال رقم صحيح:**",
                parse_mode='Markdown'
            )
            return
        
        # رسالة تأكيد التحقق
        await update.message.reply_text(
            "✅ **تنسيق الكوبون صحيح** ✅\n🔍 جاري التحقق من صحة الكوبون...",
            parse_mode='Markdown'
        )
        
        # البحث عن الكوبون في قاعدة البيانات
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, amount, is_used, used_by, expiry_date, description
            FROM coupons 
            WHERE coupon_code = ?
        ''', (coupon_code,))
        
        coupon = cursor.fetchone()
        
        if not coupon:
            conn.close()
            await update.message.reply_text(
                "❌ **كوبون غير صحيح** ❌\n\n"
                "🔍 **رقم الكوبون غير موجود**\n\n"
                "💡 **تأكد من:**\n"
                "🔸 صحة رقم الكوبون\n"
                "🔸 عدم وجود مسافات إضافية\n"
                "🔸 استخدام الأرقام والحروف الصحيحة\n\n"
                "🎟️ **أدخل رقم كوبون صحيح:**",
                parse_mode='Markdown'
            )
            return
        
        # فحص إذا كان الكوبون مستخدم
        if coupon['is_used']:
            # الحصول على معلومات المستخدم الذي استخدم الكوبون
            cursor.execute('SELECT full_name FROM users WHERE id = ?', (coupon['used_by'],))
            used_by_user = cursor.fetchone()
            used_by_name = used_by_user['full_name'] if used_by_user else "مستخدم غير معروف"
            
            conn.close()
            await update.message.reply_text(
                "❌ **كوبون مستخدم مسبقاً** ❌\n\n"
                f"🎟️ **رقم الكوبون:** {coupon_code}\n"
                f"👤 **مستخدم بواسطة:** {used_by_name}\n"
                f"💰 **قيمة الكوبون:** {coupon['amount']:,.0f} ريال\n\n"
                "🔍 **كل كوبون يُستخدم مرة واحدة فقط**\n"
                "🎟️ **أدخل كوبون آخر:**",
                parse_mode='Markdown'
            )
            return
        
        # فحص انتهاء الصلاحية
        from datetime import datetime
        if coupon['expiry_date']:
            expiry_date = datetime.fromisoformat(coupon['expiry_date'].replace('Z', '+00:00'))
            if datetime.now() > expiry_date:
                conn.close()
                await update.message.reply_text(
                    "❌ **كوبون منتهي الصلاحية** ❌\n\n"
                    f"🎟️ **رقم الكوبون:** {coupon_code}\n"
                    f"💰 **قيمة الكوبون:** {coupon['amount']:,.0f} ريال\n"
                    f"📅 **انتهى في:** {expiry_date.strftime('%Y-%m-%d')}\n\n"
                    "⏰ **لا يمكن استخدام الكوبونات المنتهية الصلاحية**\n"
                    "🎟️ **أدخل كوبون صالح:**",
                    parse_mode='Markdown'
                )
                return
        
        # رسالة تأكيد قبل الاستخدام
        await update.message.reply_text(
            "✅ **كوبون صالح للاستخدام** ✅\n💳 جاري إضافة القيمة لرصيدك...",
            parse_mode='Markdown'
        )
        
        # تطبيق الكوبون
        coupon_amount = coupon['amount']
        old_balance = user['balance']
        new_balance = old_balance + coupon_amount
        
        # تحديث رصيد المستخدم
        cursor.execute('UPDATE users SET balance = ? WHERE id = ?', (new_balance, user['id']))
        
        # تسجيل استخدام الكوبون
        cursor.execute('''
            UPDATE coupons 
            SET is_used = 1, used_by = ?, used_at = CURRENT_TIMESTAMP 
            WHERE id = ?
        ''', (user['id'], coupon['id']))
        
        # إنشاء معاملة في سجل المعاملات
        cursor.execute('''
            INSERT INTO transactions (from_user, to_user, amount, type, description, created_at)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (None, user['id'], coupon_amount, 'coupon_redeem', f"شحن بكوبون {coupon_code}"))
        
        conn.commit()
        conn.close()
        
        # رسالة النجاح
        success_text = f"""
🎉 **تم شحن الرصيد بنجاح!** 🎉

👤 **اسم المستخدم:** {user['full_name']}
🎟️ **رقم الكوبون:** {coupon_code}

💰 **تفاصيل الشحن:**
📊 رصيدك السابق: **{old_balance:,.2f}** ريال
💎 قيمة الكوبون: **+{coupon_amount:,.2f}** ريال
💳 رصيدك الجديد: **{new_balance:,.2f}** ريال

📅 **تاريخ الاستخدام:** {datetime.now().strftime('%Y-%m-%d %H:%M')}
🔖 **وصف الكوبون:** {coupon.get('description', 'كوبون شحن رصيد')}

✅ **تم إضافة المبلغ فوراً لرصيدك**
🛒 **يمكنك الآن استخدام رصيدك لشراء الكروت**

🎊 شكراً لك على استخدام خدماتنا!
"""
        
        keyboard = [
            [InlineKeyboardButton('💳 عرض محفظتي', callback_data='enhanced_wallet'),
             InlineKeyboardButton('🛒 شراء كروت', callback_data='buy_cards')],
            [InlineKeyboardButton('🎟️ شحن كوبون آخر', callback_data='redeem_coupon'),
             InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
        ]
        
        await update.message.reply_text(
            success_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
        # تنظيف الحالة
        context.user_data.clear()
        
        # تسجيل العملية
        logger.info(f"User {user['full_name']} redeemed coupon {coupon_code} worth {coupon_amount:,.2f}")
        
    except Exception as e:
        logger.error(f"Error in process coupon redemption: {e}")
        await update.message.reply_text(
            f"❌ **حدث خطأ في استخدام الكوبون** ❌\n\n"
            f"🔍 **تفاصيل الخطأ:** {str(e)}\n\n"
            f"🔄 **يرجى المحاولة مرة أخرى**",
            parse_mode='Markdown'
        )
        context.user_data.clear()

def validate_coupon_format(coupon_code: str) -> bool:
    """التحقق من صحة تنسيق الكوبون"""
    try:
        # يجب أن يكون 9 أحرف: A + 8 أرقام
        if len(coupon_code) != 9:
            return False
        
        # يجب أن يبدأ بالحرف A
        if not coupon_code.startswith('A'):
            return False
        
        # الباقي يجب أن يكون أرقام
        if not coupon_code[1:].isdigit():
            return False
        
        return True
        
    except Exception:
        return False

async def cancel_coupon_handler(update: Update, context: CallbackContext):
    """إلغاء عملية شحن الكوبون"""
    try:
        query = update.callback_query
        await query.answer()
        
        context.user_data.clear()
        
        await query.edit_message_text(
            "❌ **تم إلغاء عملية شحن الكوبون** ❌\n\n"
            "🏠 يمكنك العودة للقائمة الرئيسية",
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Error in cancel coupon handler: {e}")
        await query.edit_message_text(unexpected_error("إلغاء العملية"))

# معالجات الميزات الجديدة


async def contact_support_handler(update: Update, context: CallbackContext):
    """التواصل مع الدعم"""
    try:
        query = update.callback_query
        await query.answer()
        
        text = """
📞 **التواصل مع الدعم** 📞

🎯 **طرق التواصل:**

📱 **واتساب:**
   رقم الدعم: +967-77-777-7777
   متاح: 24/7

📧 **البريد الإلكتروني:**
   support@yemennet.com
   يتم الرد خلال 24 ساعة

💬 **التلغرام:**
   @YemenNetSupport
   دعم فوري

🕐 **أوقات العمل:**
   السبت - الخميس: 8 صباحاً - 10 مساءً
   الجمعة: 2 ظهراً - 10 مساءً

❓ **الأسئلة الشائعة:**
   • كيفية شحن الرصيد
   • استخدام الكوبونات
   • مشاكل الشراء
   • استرداد الأموال

💡 **للاستفسارات السريعة استخدم الواتساب**
"""
        
        keyboard = [
            [InlineKeyboardButton('📱 واتساب', url='https://wa.me/967777777777'),
             InlineKeyboardButton('💬 تلغرام', url='https://t.me/YemenNetSupport')],
            [InlineKeyboardButton('❓ الأسئلة الشائعة', callback_data='faq'),
             InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
        ]
        
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in contact support handler: {e}")
        await query.edit_message_text(menu_error("معلومات الدعم", "تحميل البيانات"))

async def process_supplier_network_creation(update: Update, context: CallbackContext):
    """معالجة إضافة الشبكة للمزود خطوة بخطوة"""
    try:
        text = update.message.text.strip()
        user = get_user(update.effective_user.id)
        step = context.user_data.get('network_step', 'name')
        
        if step == 'name':
            # حفظ اسم الشبكة
            context.user_data['network_name'] = text
            context.user_data['network_step'] = 'provider'
            
            await update.message.reply_text(
                f"✅ **تم حفظ اسم الشبكة:** {text}\n\n🔸 **الخطوة 2 من 4**\n👤 **أدخل اسم المزود:**",
                parse_mode='Markdown'
            )
            
        elif step == 'provider':
            # حفظ اسم المزود
            context.user_data['network_provider'] = text
            context.user_data['network_step'] = 'description'
            
            await update.message.reply_text(
                f"✅ **تم حفظ اسم المزود:** {text}\n\n🔸 **الخطوة 3 من 4**\n📝 **أدخل وصف الشبكة:**",
                parse_mode='Markdown'
            )
            
        elif step == 'description':
            # حفظ الوصف
            context.user_data['network_description'] = text
            context.user_data['network_step'] = 'location'
            
            await update.message.reply_text(
                f"✅ **تم حفظ وصف الشبكة:** {text}\n\n�� **الخطوة 4 من 4**\n📍 **أدخل موقع الشبكة:**",
                parse_mode='Markdown'
            )
            
        elif step == 'location':
            # إنشاء الشبكة
            network_name = context.user_data.get('network_name')
            provider = context.user_data.get('network_provider')
            description = context.user_data.get('network_description')
            
            try:
                conn = get_db_connection()
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO networks (supplier_id, name, city, provider, description, location, created_by, is_active, is_approved, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 1, 1, CURRENT_TIMESTAMP)
                ''', (user['id'], network_name, text, provider, description, text, user['id']))
                
                network_id = cursor.lastrowid
                conn.commit()
                conn.close()
                
                context.user_data.clear()
                
                await update.message.reply_text(
                    f"✅ **تم إنشاء الشبكة بنجاح!**\n\n🌐 **{network_name}**\n👤 {provider}\n📍 {text}\n🆔 معرف: #{network_id}",
                    parse_mode='Markdown'
                )
                
            except Exception as e:
                await update.message.reply_text(f"❌ خطأ في إنشاء الشبكة: {e}")
                context.user_data.clear()
        
    except Exception as e:
        await update.message.reply_text(f"❌ خطأ في معالجة الشبكة: {e}")
        context.user_data.clear()
