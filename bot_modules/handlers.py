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
        error_text = f"{EMOJIS['error']} حدث خطأ في تحميل القائمة الرئيسية."
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
            [InlineKeyboardButton('🔍 البحث عن شبكات', callback_data='search_networks'),
             InlineKeyboardButton('📊 تقاريري الشخصية', callback_data='personal_reports')],
            [InlineKeyboardButton('🎁 العروض والخصومات', callback_data='promotions'),
             InlineKeyboardButton('🔔 إشعاراتي', callback_data='my_notifications')],
            [InlineKeyboardButton('⚙️ إعدادات الحساب', callback_data='account_settings'),
             InlineKeyboardButton('⭐ تقييماتي', callback_data='my_ratings')]
        ]
        
        # Role-specific features
        if role == 'agent':
            base_buttons.extend([
                [InlineKeyboardButton('💼 لوحة الوكيل', callback_data='agent_panel'),
                 InlineKeyboardButton('💰 عمولاتي', callback_data='my_commissions')]
            ])
        elif role == 'supplier':
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
🏷️ نوع الحساب: **{USER_ROLES.get(user.get('role', 'customer'), 'عميل')}**
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
        error_msg = f"{EMOJIS['error']} حدث خطأ في عرض المحفظة."
        if update.message:
            await update.message.reply_text(error_msg)
        else:
            await update.callback_query.edit_message_text(error_msg)

# Message handler for processing admin operations
async def handle_text_message(update: Update, context: CallbackContext):
    """Handle text messages for special operations"""
    try:
        # Check if waiting for money creation
        if context.user_data.get('awaiting_money_creation'):
            from bot_modules.admin_functions import process_money_creation
            return await process_money_creation(update, context)
        
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
        
        # Check if waiting for WiFi search
        if context.user_data.get('awaiting_wifi_search'):
            return await process_wifi_search(update, context)
        
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
        await update.message.reply_text(f"{EMOJIS['error']} حدث خطأ في معالجة الرسالة.")

# Enhanced User Features

async def wifi_search_handler(update: Update, context: CallbackContext):
    """Handle WiFi network search by name or ID"""
    try:
        user = get_user(update.effective_user.id)
        if not user:
            await update.message.reply_text(f"{EMOJIS['error']} يرجى التسجيل أولاً /start")
            return
        
        text = f"""
🔍 **البحث عن شبكة واي فاي** 🔍

{EMOJIS['user']} مرحباً **{user['full_name']}**

📋 **طرق البحث:**
1️⃣ البحث بالاسم: اكتب اسم الشبكة
2️⃣ البحث بالرقم: اكتب رقم المعرف
3️⃣ البحث بالمدينة: اكتب اسم المدينة

💡 **أمثلة:**
• `يمن نت`
• `NET123`
• `صنعاء`

📝 اكتب كلمة البحث:

أو اكتب /cancel للإلغاء
"""
        
        await update.message.reply_text(text, parse_mode='Markdown')
        context.user_data['awaiting_wifi_search'] = True
        
    except Exception as e:
        logger.error(f"Error in WiFi search handler: {e}")
        await update.message.reply_text(f"{EMOJIS['error']} حدث خطأ في بدء البحث.")

async def process_wifi_search(update: Update, context: CallbackContext):
    """Process WiFi search query"""
    try:
        if not context.user_data.get('awaiting_wifi_search'):
            return
        
        user = get_user(update.effective_user.id)
        if not user:
            await update.message.reply_text(f"{EMOJIS['error']} يرجى التسجيل أولاً /start")
            return
        
        search_term = update.message.text.strip()
        
        if len(search_term) < 2:
            await update.message.reply_text(f"{EMOJIS['error']} كلمة البحث قصيرة جداً. أدخل على الأقل حرفين.")
            return
        
        # Search in networks
        from bot_modules.database import get_db_connection
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Search by name, code, or city
        cursor.execute('''
            SELECT n.*, u.full_name as supplier_name 
            FROM networks n
            JOIN users u ON n.supplier_id = u.id
            WHERE (n.name LIKE ? OR COALESCE(n.network_code, '') LIKE ? OR n.city LIKE ?)
            AND n.is_active = 1 AND n.is_approved = 1
            ORDER BY n.name
            LIMIT 20
        ''', (f'%{search_term}%', f'%{search_term}%', f'%{search_term}%'))
        
        networks = cursor.fetchall()
        
        # Get card categories for each network
        results = []
        for network in networks:
            cursor.execute('''
                SELECT COUNT(*) as categories_count, MIN(price) as min_price, MAX(price) as max_price
                FROM card_categories 
                WHERE network_id = ? AND is_available = 1
            ''', (network['id'],))
            
            category_info = cursor.fetchone()
            
            results.append({
                'network': network,
                'categories_count': category_info['categories_count'],
                'min_price': category_info['min_price'],
                'max_price': category_info['max_price']
            })
        
        conn.close()
        
        # Clear user state
        context.user_data.pop('awaiting_wifi_search', None)
        
        if not results:
            await update.message.reply_text(f"""
{EMOJIS['error']} **لم يتم العثور على نتائج**

🔍 **كلمة البحث:** `{search_term}`

💡 **اقتراحات:**
• تأكد من صحة الإملاء
• جرب كلمات أخرى
• ابحث باسم المدينة
• استخدم /wifi_search للبحث مرة أخرى
""", parse_mode='Markdown')
            return
        
        # Format results
        results_text = f"""
🔍 **نتائج البحث عن: {search_term}**

📊 **تم العثور على {len(results)} شبكة**

"""
        
        for i, result in enumerate(results[:10], 1):
            network = result['network']
            min_price = result['min_price'] or 0
            max_price = result['max_price'] or 0
            
            price_range = f"{min_price:.0f}" if min_price == max_price else f"{min_price:.0f} - {max_price:.0f}"
            
            network_code = network.get('network_code') or 'غير محدد'
            supplier_name = result.get('network', {}).get('supplier_name') or network.get('supplier_name', 'غير محدد')
            
            results_text += f"""
**{i}. {network['name']}**
🆔 الكود: `{network_code}`
🌍 المدينة: {network['city']}
👤 المزود: {supplier_name}
🎫 الفئات: {result['categories_count']} فئة
💰 الأسعار: {price_range} ريال

"""
        
        if len(results) > 10:
            results_text += f"\n... و {len(results) - 10} شبكة أخرى"
        
        results_text += f"""
───────────────────
💡 لشراء البطاقات استخدم /buy
🔍 للبحث مرة أخرى استخدم /wifi_search
"""
        
        await update.message.reply_text(results_text, parse_mode='Markdown')
        
        # Log the search
        logger.info(f"User {user['full_name']} searched for WiFi: {search_term} - Found {len(results)} results")
        
    except Exception as e:
        logger.error(f"Error in process WiFi search: {e}")
        await update.message.reply_text(f"{EMOJIS['error']} حدث خطأ في البحث.")

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
• رسوم التحويل: 10 ريال
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
        
        # Calculate transfer fee (1%)
        transfer_fee = amount * 0.01
        total_deduction = amount + transfer_fee
        
        if total_deduction > user['balance']:
            await update.message.reply_text(f"""
{EMOJIS['error']} **رصيدك غير كافي!**

💰 المبلغ المطلوب: **{amount:.2f}** ريال
💳 رسوم التحويل (1%): **{transfer_fee:.2f}** ريال
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
💳 رسوم التحويل: **{transfer_fee:.2f}** ريال
📊 إجمالي الخصم: **{total_deduction:.2f}** ريال

💵 **الأرصدة:**
🔻 رصيدك الجديد: **{sender_new_balance:.2f}** ريال
🔺 رصيد المستلم: **{receiver_new_balance:.2f}** ريال

💬 **السبب:** {reason}
🕐 **وقت التحويل:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

📱 سيتم إشعار المستلم فوراً
"""
        
        await update.message.reply_text(success_text, parse_mode='Markdown')
        
        # Send notification to receiver
        try:
            notification_text = f"""
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
                text=notification_text,
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.warning(f"Failed to send notification to receiver {target_user['telegram_id']}: {e}")
        
        # Log the transfer
        logger.info(f"User {user['full_name']} sent {amount} YER to {target_user['full_name']} (fee: {transfer_fee})")
        
    except Exception as e:
        logger.error(f"Error in process balance send: {e}")
        await update.message.reply_text(f"{EMOJIS['error']} حدث خطأ في إرسال الرصيد.")

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
        context.user_data['target_wallet'] = target_user.get('wallet_number', 'غير محدد')
        context.user_data.pop('awaiting_transfer_step1', None)
        context.user_data['awaiting_transfer_step2'] = True
        
        text = f"""
✅ **تم العثور على المستخدم!**

👤 **المستلم:** {target_user['full_name']}
🆔 **رقم المحفظة:** {target_user.get('wallet_number', 'غير محدد')}
📱 **رقم الهاتف:** {target_user['phone']}

💰 **رصيدك الحالي:** {user['balance']:,.2f} ريال

📋 **الخطوة الثانية:**
أدخل المبلغ الذي تريد إرساله

💡 **مثال:** `100`

⚠️ **ملاحظة:** سيتم خصم 1% رسوم تحويل

📝 أدخل المبلغ:

أو اكتب /cancel للإلغاء
"""
        
        await update.message.reply_text(text, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in process transfer step 1: {e}")
        await update.message.reply_text(f"{EMOJIS['error']} حدث خطأ في البحث عن المستخدم.")

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
        
        # Calculate transfer fee (1%)
        transfer_fee = amount * 0.01
        total_deduction = amount + transfer_fee
        
        if total_deduction > user['balance']:
            await update.message.reply_text(f"""
{EMOJIS['error']} **رصيدك غير كافي!**

💰 المبلغ المطلوب: **{amount:.2f}** ريال
💳 رسوم التحويل (1%): **{transfer_fee:.2f}** ريال
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
💳 رسوم التحويل: **{transfer_fee:.2f}** ريال
📊 إجمالي الخصم: **{total_deduction:.2f}** ريال

💵 **رصيدك بعد التحويل:** **{user['balance'] - total_deduction:.2f}** ريال

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
        await update.message.reply_text(f"{EMOJIS['error']} حدث خطأ في معالجة المبلغ.")

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
        await update.message.reply_text("❌ حدث خطأ في الإرسال.")

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
        
        # Calculate fees
        transfer_fee = amount * 0.01  # 1%
        total_deduction = amount + transfer_fee
        
        if total_deduction > user['balance']:
            await update.message.reply_text(f"""❌ رصيدك غير كافي

💰 المبلغ: {amount:.0f} ريال
💳 الرسوم: {transfer_fee:.0f} ريال
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
💳 الرسوم: {transfer_fee:.0f} ريال
💵 رصيدك الجديد: {sender_new_balance:.0f} ريال
""", parse_mode='Markdown')
        
        # Notify receiver
        try:
            await context.bot.send_message(
                chat_id=target_user['telegram_id'],
                text=f"💰 تم استلام {amount:.0f} ريال من {user['full_name']}\n💵 رصيدك الجديد: {receiver_new_balance:.0f} ريال"
            )
        except Exception:
            pass
        
        logger.info(f"User {user['full_name']} sent {amount} to {target_user['full_name']} (fee: {transfer_fee})")
        
    except Exception as e:
        logger.error(f"Error in simple transfer: {e}")
        await update.message.reply_text("❌ حدث خطأ في التحويل.")

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

🚀 **قريباً جداً!**
{description}

💡 **متوقع قريباً:**
• تحسينات رائعة
• ميزات متقدمة  
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
                SELECT id, full_name, wallet_number, phone, telegram_username, balance, is_active, role
                FROM users 
                WHERE full_name LIKE ? AND id != ?
                ORDER BY full_name
                LIMIT 10
            """, (f"%{name}%", user['id']))
            
        elif search_text.startswith('المحفظة '):
            # البحث برقم المحفظة
            wallet = search_text[8:].strip()
            cursor.execute("""
                SELECT id, full_name, wallet_number, phone, telegram_username, balance, is_active, role
                FROM users 
                WHERE wallet_number = ? AND id != ?
            """, (wallet, user['id']))
            
        elif search_text.startswith('الهاتف '):
            # البحث برقم الهاتف
            phone = search_text[7:].strip()
            cursor.execute("""
                SELECT id, full_name, wallet_number, phone, telegram_username, balance, is_active, role
                FROM users 
                WHERE phone LIKE ? AND id != ?
                ORDER BY full_name
                LIMIT 10
            """, (f"%{phone}%", user['id']))
            
        elif search_text.startswith('المعرف '):
            # البحث بمعرف التلغرام
            username = search_text[7:].strip().replace('@', '')
            cursor.execute("""
                SELECT id, full_name, wallet_number, phone, telegram_username, balance, is_active, role
                FROM users 
                WHERE telegram_username LIKE ? AND id != ?
                ORDER BY full_name
                LIMIT 10
            """, (f"%{username}%", user['id']))
        else:
            # بحث عام في جميع الحقول
            cursor.execute("""
                SELECT id, full_name, wallet_number, phone, telegram_username, balance, is_active, role
                FROM users 
                WHERE (full_name LIKE ? OR wallet_number LIKE ? OR phone LIKE ? OR telegram_username LIKE ?) 
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
            user_id, full_name, wallet_number, phone, telegram_username, balance, is_active, role = result
            status_emoji = "✅" if is_active else "⏳"
            role_emoji = "👑" if role == 'admin' else "🏪" if role == 'supplier' else "💼" if role == 'agent' else "👤"
            
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

    except Exception as e:
        logger.error(f"Error in process user search: {e}")
        await update.message.reply_text("❌ حدث خطأ في البحث")
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
• رسوم التحويل: 10 ريال
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

# Export main handlers for use in main bot file
COMMAND_HANDLERS = {
    'start': start,
    'wallet': wallet_handler,
    'admin': admin_handler,
    'cancel': cancel,
    'wifi_search': wifi_search_handler,
    'send_balance': send_balance_handler,
    'search_networks': wifi_search_handler,
    'transfer_to_friend': send_balance_handler,
    'personal_reports': lambda u, c: enhanced_placeholder_handler(u, c, "📊 تقاريري الشخصية", "عرض تقارير مفصلة عن نشاطك ومعاملاتك"),
    'promotions': lambda u, c: enhanced_placeholder_handler(u, c, "🎁 العروض والخصومات", "عروض حصرية وخصومات على الكروت"),
    'my_notifications': lambda u, c: enhanced_placeholder_handler(u, c, "🔔 إشعاراتي", "إدارة إشعاراتك وتنبيهاتك"),
    'account_settings': lambda u, c: enhanced_placeholder_handler(u, c, "⚙️ إعدادات الحساب", "تعديل بيانات حسابك وإعداداتك"),
    'my_ratings': lambda u, c: enhanced_placeholder_handler(u, c, "⭐ تقييماتي", "عرض وإدارة تقييماتك"),
    'agent_panel': lambda u, c: enhanced_placeholder_handler(u, c, "💼 لوحة الوكيل", "لوحة تحكم خاصة بالوكلاء"),
    'my_commissions': lambda u, c: enhanced_placeholder_handler(u, c, "💰 عمولاتي", "عرض العمولات والأرباح"),
    'supplier_panel': lambda u, c: enhanced_placeholder_handler(u, c, "🏪 لوحة المزود", "لوحة تحكم خاصة بالمزودين"),
    'manage_networks': lambda u, c: enhanced_placeholder_handler(u, c, "📶 إدارة الشبكات", "إضافة وإدارة شبكاتك"),
    'upload_cards': lambda u, c: enhanced_placeholder_handler(u, c, "📤 رفع كروت", "رفع وإدارة كروت الشحن"),
    'sales_reports': lambda u, c: enhanced_placeholder_handler(u, c, "📈 تقارير المبيعات", "تقارير مفصلة عن مبيعاتك"),
    'buy_cards': lambda u, c: enhanced_placeholder_handler(u, c, "🛒 شراء كروت", "تصفح وشراء كروت الإنترنت"),
    'help': help_handler,
    'transaction_details': lambda u, c: enhanced_placeholder_handler(u, c, "📊 تفاصيل المعاملات", "عرض تفاصيل شاملة لجميع معاملاتك"),
    'wallet_stats': lambda u, c: enhanced_placeholder_handler(u, c, "📈 إحصائيات مفصلة", "تحليلات وإحصائيات مفصلة لمحفظتك"),
    'account_statement': lambda u, c: enhanced_placeholder_handler(u, c, "💳 كشف حساب", "كشف حساب شامل لفترة محددة"),
    'deposit_balance': lambda u, c: enhanced_placeholder_handler(u, c, "💰 إيداع رصيد", "إيداع رصيد في محفظتك بطرق مختلفة"),
    'wallet_settings': lambda u, c: enhanced_placeholder_handler(u, c, "⚙️ إعدادات المحفظة", "تخصيص إعدادات وأمان المحفظة"),
    'contact_admin': lambda u, c: enhanced_placeholder_handler(u, c, "📞 التواصل مع الإدارة", "إرسال رسالة للدعم الفني"),
    'account_status': lambda u, c: enhanced_placeholder_handler(u, c, "📊 حالة الحساب", "عرض حالة وتفاصيل حسابك"),
    'advanced_search_transfer': search_user_for_transfer,
    'quick_transfer': quick_transfer_handler,
    'transfer_history': lambda u, c: enhanced_placeholder_handler(u, c, "📋 سجل التحويلات", "عرض سجل جميع تحويلاتك"),
    'search_by_wallet': lambda u, c: search_by_type_handler(u, c, "wallet"),
    'search_by_name': lambda u, c: search_by_type_handler(u, c, "name"),
    'search_by_phone': lambda u, c: search_by_type_handler(u, c, "phone"),
    'search_by_username': lambda u, c: search_by_type_handler(u, c, "username"),
}

from telegram.ext import MessageHandler, CallbackQueryHandler, filters

CONVERSATION_STATES = {
    GET_FULL_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_full_name)],
    GET_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_phone)],
    CHOOSE_ROLE: [CallbackQueryHandler(choose_role, pattern='^role_')],
}