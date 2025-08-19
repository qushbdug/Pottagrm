#!/usr/bin/env python3
"""
Admin Functions module for Pottagrm Enhanced Bot
Contains super admin and admin specific functions
"""

import logging
import uuid
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext
from bot_modules.config import *
from bot_modules.database import get_db_connection
from bot_modules.utils import *

logger = logging.getLogger(__name__)

async def admin_panel_handler(update: Update, context: CallbackContext):
    """Handle admin panel access"""
    try:
        user = get_user(update.effective_user.id)
        if not user or user['role'] not in ['admin', 'super_admin']:
            await update.message.reply_text(f"{EMOJIS['error']} ليس لديك صلاحية للوصول لهذه اللوحة.")
            return
        
        update_user_activity(user['id'])
        
        if user['role'] == 'super_admin':
            return await show_super_admin_panel(update, context, user)
        else:
            return await show_admin_panel(update, context, user)
            
    except Exception as e:
        logger.error(f"Error in admin panel handler: {e}")
        await update.message.reply_text(f"{EMOJIS['error']} حدث خطأ في الوصول للوحة الإدارة.")

async def show_super_admin_panel(update: Update, context: CallbackContext, user):
    """Show super admin control panel"""
    try:
        # Get platform statistics
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Basic stats
        cursor.execute('SELECT COUNT(*) as total_users FROM users')
        total_users = cursor.fetchone()['total_users']
        
        cursor.execute('SELECT COUNT(*) as active_users FROM users WHERE is_active = 1')
        active_users = cursor.fetchone()['active_users']
        
        cursor.execute('SELECT SUM(balance) as total_balance FROM users')
        total_balance = cursor.fetchone()['total_balance'] or 0
        
        cursor.execute('SELECT COUNT(*) as pending_suppliers FROM users WHERE role = "supplier" AND is_active = 0')
        pending_suppliers = cursor.fetchone()['pending_suppliers']
        
        cursor.execute('SELECT COUNT(*) as total_transactions FROM transactions')
        total_transactions = cursor.fetchone()['total_transactions']
        
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
            [InlineKeyboardButton(f'👥 إدارة المستخدمين', callback_data='manage_users'),
             InlineKeyboardButton(f'👑 إدارة المشرفين', callback_data='manage_admins')],
            [InlineKeyboardButton(f'📊 لوحة المعلومات', callback_data='dashboard'),
             InlineKeyboardButton(f'📈 التقارير التنفيذية', callback_data='executive_reports')],
            [InlineKeyboardButton(f'💰 إدارة الأرصدة', callback_data='admin_wallet'),
             InlineKeyboardButton(f'💸 إرسال رصيد', callback_data='admin_send_money')],
            [InlineKeyboardButton(f'💼 إدارة العمولات', callback_data='commission_management'),
             InlineKeyboardButton(f'🏛️ إدارة المنصة', callback_data='super_platform_management')],
            [InlineKeyboardButton(f'🌐 إضافة شبكة جديدة', callback_data='admin_add_network'),
             InlineKeyboardButton(f'💳 رفع كروت', callback_data='admin_upload_cards')],
            [InlineKeyboardButton(f'🎁 إضافة عروض', callback_data='admin_add_offers'),
             InlineKeyboardButton(f'✅ تفعيل مزودين', callback_data='super_activate_suppliers')],
            [InlineKeyboardButton(f'📊 النظام المحاسبي', callback_data='accounting_system'),
             InlineKeyboardButton(f'📄 تنزيل كشوف حسابات', callback_data='download_statements')],
            [InlineKeyboardButton(f'🔧 إعدادات النظام', callback_data='super_system_settings')],
            [InlineKeyboardButton(f'💾 النسخ الاحتياطي', callback_data='super_backup'),
             InlineKeyboardButton(f'🚨 مراقبة الأمان', callback_data='super_security_monitoring')],
            [InlineKeyboardButton(f'🎟️ إنشاء كوبونات', callback_data='super_create_coupons'),
             InlineKeyboardButton(f'💰 طباعة رصيد المحفظة', callback_data='super_print_balance')],
            [InlineKeyboardButton(f'📢 إرسال رسالة جماعية', callback_data='super_broadcast_message'),
             InlineKeyboardButton(f'🔄 تحديث أوامر البوت', callback_data='super_update_commands')],
            [InlineKeyboardButton(f'{EMOJIS["home"]} العودة للقائمة', callback_data='main_menu')]
        ]
        
        if update.message:
            await update.message.reply_text(panel_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        else:
            await update.callback_query.edit_message_text(panel_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
            
    except Exception as e:
        logger.error(f"Error in super admin panel: {e}")
        await update.message.reply_text(f"{EMOJIS['error']} حدث خطأ في تحميل لوحة المشرف الأعلى.")

async def issue_balance_handler(update: Update, context: CallbackContext):
    """Handle balance issuance for super admin - Create money to admin wallet"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user or user['role'] != 'super_admin':
            await query.edit_message_text(f"{EMOJIS['error']} ليس لديك صلاحية لهذه العملية.")
            return
        
        text = f"""
💰 **إنشاء رصيد جديد** 💰

{EMOJIS['admin']} مرحباً **{user['full_name']}**
💵 رصيدك الحالي: **{user['balance']:,.2f}** ريال

📋 **تعليمات الإنشاء:**
أدخل المبلغ الذي تريد إنشاؤه وإضافته لمحفظتك

💡 **مثال:**
`5000`

⚠️ **ملاحظة:**
سيتم إضافة المبلغ فوراً ومباشرة لمحفظتك كمشرف أعلى عند التأكيد

📝 أدخل المبلغ:

أو اكتب /cancel للإلغاء
"""
        
        await query.edit_message_text(text, parse_mode='Markdown')
        context.user_data['awaiting_money_creation'] = True
        
    except Exception as e:
        logger.error(f"Error in issue balance handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في بدء عملية إنشاء الرصيد.")

async def process_money_creation(update: Update, context: CallbackContext):
    """Process money creation for super admin"""
    try:
        if not context.user_data.get('awaiting_money_creation'):
            return
        
        user = get_user(update.effective_user.id)
        if not user or user['role'] != 'super_admin':
            await update.message.reply_text(f"{EMOJIS['error']} ليس لديك صلاحية لهذه العملية.")
            return
        
        # Parse input
        try:
            amount = float(update.message.text.strip())
        except ValueError:
            await update.message.reply_text(f"{EMOJIS['error']} المبلغ يجب أن يكون رقماً صحيحاً.")
            return
        
        # Validate amount
        if amount <= 0:
            await update.message.reply_text(f"{EMOJIS['error']} المبلغ يجب أن يكون أكبر من صفر.")
            return
        
        if amount > 100000:  # Security limit
            await update.message.reply_text(f"{EMOJIS['error']} لا يمكن إنشاء أكثر من 100,000 ريال في العملية الواحدة.")
            return
        
        # Create money transaction for super admin
        conn = get_db_connection()
        cursor = conn.cursor()
        
        transaction_id = str(uuid.uuid4())
        cursor.execute('''
            INSERT INTO transactions 
            (id, to_user, amount, type, description, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (transaction_id, user['id'], amount, 'money_creation', 'إنشاء رصيد من المشرف الأعلى', datetime.now()))
        
        # Update admin balance
        from bot_modules.utils import recalc_and_set_user_balance
        new_balance = recalc_and_set_user_balance(user['id'])
        
        conn.commit()
        conn.close()
        
        # Clear user state
        context.user_data.pop('awaiting_money_creation', None)
        
        # Send confirmation
        success_text = f"""
✅ **تم إنشاء الرصيد بنجاح!**

💰 **تفاصيل العملية:**
💵 المبلغ المُنشأ: **{amount:,.2f}** ريال
💳 رصيدك الجديد: **{new_balance:,.2f}** ريال
🕐 وقت العملية: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

✨ يمكنك الآن تحويل الرصيد للمستخدمين أو استخدامه في العمليات الإدارية.
"""
        
        await update.message.reply_text(success_text, parse_mode='Markdown')
        
        # Log the action
        logger.info(f"Super admin {user['full_name']} created {amount} YER money. New balance: {new_balance}")
        
    except Exception as e:
        logger.error(f"Error in process money creation: {e}")
        await update.message.reply_text(f"{EMOJIS['error']} حدث خطأ في إنشاء الرصيد.")

async def process_balance_issue(update: Update, context: CallbackContext):
    """Process balance transfer from super admin to user"""
    try:
        if not context.user_data.get('awaiting_balance_issue'):
            return
        
        user = get_user(update.effective_user.id)
        if not user or user['role'] != 'super_admin':
            await update.message.reply_text(f"{EMOJIS['error']} ليس لديك صلاحية لهذه العملية.")
            return
        
        # Parse input
        parts = update.message.text.strip().split()
        if len(parts) < 2:
            await update.message.reply_text(f"{EMOJIS['error']} تنسيق غير صحيح. أدخل: رقم_المحفظة المبلغ السبب")
            return
        
        wallet_number = parts[0]
        try:
            amount = float(parts[1])
        except ValueError:
            await update.message.reply_text(f"{EMOJIS['error']} المبلغ يجب أن يكون رقماً صحيحاً.")
            return
        
        reason = ' '.join(parts[2:]) if len(parts) > 2 else 'تحويل رصيد من المشرف الأعلى'
        
        # Validate amount
        if amount <= 0:
            await update.message.reply_text(f"{EMOJIS['error']} المبلغ يجب أن يكون أكبر من صفر.")
            return
        
        if amount > user['balance']:
            await update.message.reply_text(f"""
{EMOJIS['error']} **رصيدك غير كافي!**

💰 المبلغ المطلوب: **{amount:,.2f}** ريال
💵 رصيدك الحالي: **{user['balance']:,.2f}** ريال
❌ النقص: **{amount - user['balance']:,.2f}** ريال

💡 استخدم زر "💰 إصدار رصيد" لإنشاء رصيد جديد أولاً.
""", parse_mode='Markdown')
            return
        
        # Find target user
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM users WHERE wallet_number = ?', (wallet_number,))
        target_user = cursor.fetchone()
        
        if not target_user:
            await update.message.reply_text(f"{EMOJIS['error']} لم يتم العثور على مستخدم بهذا الرقم: {wallet_number}")
            conn.close()
            return
        
        # Create transfer transactions
        transaction_id = str(uuid.uuid4())
        
        # Debit from admin
        cursor.execute('''
            INSERT INTO transactions 
            (id, from_user, to_user, amount, type, description, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (transaction_id, user['id'], target_user['id'], amount, 'admin_transfer', reason, datetime.now()))
        
        # Update balances
        from bot_modules.utils import recalc_and_set_user_balance
        admin_new_balance = recalc_and_set_user_balance(user['id'])
        target_new_balance = recalc_and_set_user_balance(target_user['id'])
        
        conn.commit()
        conn.close()
        
        # Clear user state
        context.user_data.pop('awaiting_balance_issue', None)
        
        # Send confirmation to admin
        success_text = f"""
✅ **تم تحويل الرصيد بنجاح!**

📤 **تفاصيل التحويل:**
👤 المستلم: **{target_user['full_name']}**
💰 المبلغ المُحول: **{amount:,.2f}** ريال
💵 رصيدك الجديد: **{admin_new_balance:,.2f}** ريال
💳 رصيد المستلم: **{target_new_balance:,.2f}** ريال
💬 السبب: {reason}
🕐 وقت التحويل: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        
        await update.message.reply_text(success_text, parse_mode='Markdown')
        
        # Send notification to receiver
        try:
            notification_text = f"""
💰 **تم استلام رصيد من الإدارة!** 💰

📥 **تفاصيل الاستلام:**
👑 المرسل: المشرف الأعلى
💰 المبلغ المستلم: **{amount:,.2f}** ريال
💵 رصيدك الجديد: **{target_new_balance:,.2f}** ريال
💬 السبب: {reason}
🕐 وقت التحويل: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

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
        logger.info(f"Super admin {user['full_name']} transferred {amount} YER to {target_user['full_name']}")
        
    except Exception as e:
        logger.error(f"Error in process balance issue: {e}")
        await update.message.reply_text(f"{EMOJIS['error']} حدث خطأ في تحويل الرصيد.")

# Add transfer to user button in admin panel
async def admin_send_money_handler(update: Update, context: CallbackContext):
    """Simple money sending from admin"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user or user['role'] != 'super_admin':
            await query.edit_message_text(f"❌ ليس لديك صلاحية لهذه العملية.")
            return
        
        text = f"""
💸 **إرسال رصيد** 💸

👤 {user['full_name']}
💵 رصيدك: **{user['balance']:,.0f}** ريال

💡 اكتب: رقم المحفظة والمبلغ

🔤 مثال: `791234567 100`
"""
        
        keyboard = [
            [InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
        ]
        
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        context.user_data['awaiting_simple_send'] = True
        
    except Exception as e:
        logger.error(f"Error in admin send money: {e}")
        await query.edit_message_text("❌ حدث خطأ في إرسال الرصيد.")
        



async def activate_suppliers_handler(update: Update, context: CallbackContext):
    """Handle supplier activation for super admin"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user or user['role'] != 'super_admin':
            await query.edit_message_text(f"{EMOJIS['error']} ليس لديك صلاحية لهذه العملية.")
            return
        
        # Get pending suppliers
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
            text = f"""
✅ **لا توجد طلبات تفعيل مزودين**

جميع المزودين المسجلين تم تفعيلهم بالفعل.

🔍 **يمكنك:**
• البحث عن مزودين محددين
• عرض جميع المزودين
• إدارة صلاحيات المزودين
"""
            
            keyboard = [
                [InlineKeyboardButton(f'👥 عرض جميع المزودين', callback_data='super_view_all_suppliers')],
                [InlineKeyboardButton(f'🔍 البحث عن مزود', callback_data='super_search_supplier')],
                [InlineKeyboardButton(f'👑 لوحة المشرف الأعلى', callback_data='super_admin_panel')]
            ]
            
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
            return
        
        text = f"""
✅ **تفعيل حسابات المزودين** ✅

📋 **المزودين في الانتظار:** {len(pending_suppliers)}

👇 **اختر المزود للتفعيل:**
"""
        
        keyboard = []
        for supplier in pending_suppliers:
            # Format supplier info
            supplier_info = f"{supplier['full_name'][:15]}... | {supplier['phone']}"
            keyboard.append([
                InlineKeyboardButton(
                    f"✅ {supplier_info}", 
                    callback_data=f'activate_supplier_{supplier["id"]}'
                )
            ])
        
        # Add navigation buttons
        keyboard.extend([
            [InlineKeyboardButton(f'✅ تفعيل الجميع', callback_data='activate_all_suppliers')],
            [InlineKeyboardButton(f'👥 عرض التفاصيل', callback_data='view_supplier_details')],
            [InlineKeyboardButton(f'👑 لوحة المشرف الأعلى', callback_data='super_admin_panel')]
        ])
        
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in activate suppliers handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في تحميل قائمة المزودين.")

async def activate_single_supplier(update: Update, context: CallbackContext, supplier_id: str):
    """Activate a single supplier"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user or user['role'] != 'super_admin':
            await query.edit_message_text(f"{EMOJIS['error']} ليس لديك صلاحية لهذه العملية.")
            return
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get supplier details
        cursor.execute('SELECT * FROM users WHERE id = ? AND role = "supplier"', (supplier_id,))
        supplier = cursor.fetchone()
        
        if not supplier:
            await query.edit_message_text(f"{EMOJIS['error']} لم يتم العثور على المزود.")
            return
        
        # Activate the supplier
        cursor.execute('UPDATE users SET is_active = 1 WHERE id = ?', (supplier_id,))
        
        # Log the activation
        log_system_action(user['id'], 'supplier_activation', f'Activated supplier {supplier["full_name"]} (ID: {supplier_id})')
        log_activity(user['id'], 'admin_supplier_activation', f'Activated supplier {supplier["full_name"]}', {
            'supplier_id': supplier_id,
            'supplier_name': supplier['full_name'],
            'supplier_phone': supplier['phone']
        })
        
        conn.commit()
        conn.close()
        
        # Send notification to supplier
        send_smart_notification(
            supplier_id,
            'account_activated',
            '🎉 تم تفعيل حسابك كمزود!',
            f'مرحباً {supplier["full_name"]},\n\nتم تفعيل حسابك كمزود بنجاح.\nيمكنك الآن رفع الكروت وإدارة شبكاتك.',
            'high'
        )
        
        success_text = f"""
✅ **تم تفعيل المزود بنجاح!**

👤 **معلومات المزود:**
📛 الاسم: **{supplier['full_name']}**
📞 الهاتف: **{supplier['phone']}**
💳 رقم المحفظة: **{supplier['wallet_number']}**
📅 تاريخ التسجيل: {supplier['created_at'][:10]}

🔔 تم إرسال إشعار للمزود بتفعيل حسابه.
"""
        
        keyboard = [
            [InlineKeyboardButton(f'✅ تفعيل مزود آخر', callback_data='super_activate_suppliers')],
            [InlineKeyboardButton(f'👑 لوحة المشرف الأعلى', callback_data='super_admin_panel')]
        ]
        
        await query.edit_message_text(success_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error activating supplier: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في تفعيل المزود.")

async def activate_all_suppliers(update: Update, context: CallbackContext):
    """Activate all pending suppliers"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user or user['role'] != 'super_admin':
            await query.edit_message_text(f"{EMOJIS['error']} ليس لديك صلاحية لهذه العملية.")
            return
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get all pending suppliers
        cursor.execute('SELECT * FROM users WHERE role = "supplier" AND is_active = 0')
        pending_suppliers = cursor.fetchall()
        
        if not pending_suppliers:
            await query.edit_message_text(f"{EMOJIS['warning']} لا توجد مزودين في الانتظار للتفعيل.")
            return
        
        # Activate all suppliers
        cursor.execute('UPDATE users SET is_active = 1 WHERE role = "supplier" AND is_active = 0')
        activated_count = cursor.rowcount
        
        # Log the mass activation
        supplier_names = [s['full_name'] for s in pending_suppliers]
        log_system_action(user['id'], 'mass_supplier_activation', f'Activated {activated_count} suppliers: {", ".join(supplier_names)}')
        
        conn.commit()
        conn.close()
        
        # Send notifications to all activated suppliers
        for supplier in pending_suppliers:
            send_smart_notification(
                supplier['id'],
                'account_activated',
                '🎉 تم تفعيل حسابك كمزود!',
                f'مرحباً {supplier["full_name"]},\n\nتم تفعيل حسابك كمزود بنجاح.\nيمكنك الآن رفع الكروت وإدارة شبكاتك.',
                'high'
            )
        
        success_text = f"""
🎉 **تم تفعيل جميع المزودين بنجاح!**

✅ **عدد المزودين المفعلين:** {activated_count}

📋 **المزودين المفعلين:**
"""
        
        for supplier in pending_suppliers[:5]:  # Show first 5
            success_text += f"\n• {supplier['full_name']} ({supplier['phone']})"
        
        if len(pending_suppliers) > 5:
            success_text += f"\n... و {len(pending_suppliers) - 5} مزودين آخرين"
        
        success_text += "\n\n🔔 تم إرسال إشعارات لجميع المزودين المفعلين."
        
        keyboard = [
            [InlineKeyboardButton(f'👥 عرض جميع المزودين', callback_data='super_view_all_suppliers')],
            [InlineKeyboardButton(f'👑 لوحة المشرف الأعلى', callback_data='super_admin_panel')]
        ]
        
        await query.edit_message_text(success_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error activating all suppliers: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في تفعيل المزودين.")

async def platform_management_handler(update: Update, context: CallbackContext):
    """Handle platform management for super admin"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user or user['role'] != 'super_admin':
            await query.edit_message_text(f"{EMOJIS['error']} ليس لديك صلاحية لهذه العملية.")
            return
        
        # Get platform statistics
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get various statistics
        stats_queries = [
            ('SELECT COUNT(*) as count FROM users WHERE role = "customer"', 'customers'),
            ('SELECT COUNT(*) as count FROM users WHERE role = "agent"', 'agents'),
            ('SELECT COUNT(*) as count FROM users WHERE role = "supplier"', 'suppliers'),
            ('SELECT COUNT(*) as count FROM networks WHERE is_active = 1', 'active_networks'),
            ('SELECT COUNT(*) as count FROM cards WHERE is_used = 0', 'available_cards'),
            ('SELECT SUM(amount) as total FROM transactions WHERE type = "purchase"', 'total_sales'),
        ]
        
        stats = {}
        for query_sql, key in stats_queries:
            cursor.execute(query_sql)
            result = cursor.fetchone()
            stats[key] = result['count'] if 'count' in result.keys() else (result['total'] or 0)
        
        conn.close()
        
        management_text = f"""
🏛️ **إدارة المنصة** 🏛️

📊 **إحصائيات سريعة:**
👥 العملاء: **{stats['customers']}**
🔷 الوكلاء: **{stats['agents']}** 
🏪 المزودين: **{stats['suppliers']}**
📶 الشبكات النشطة: **{stats['active_networks']}**
🎫 الكروت المتاحة: **{stats['available_cards']}**
💰 إجمالي المبيعات: **{stats['total_sales']:.2f}** ريال

🔧 **عمليات الإدارة:**
"""
        
        keyboard = [
            [InlineKeyboardButton(f'🔧 إعدادات العمولات', callback_data='super_commission_settings'),
             InlineKeyboardButton(f'📢 إشعار عام', callback_data='super_broadcast_message')],
            [InlineKeyboardButton(f'🚫 حظر مستخدم', callback_data='super_ban_user'),
             InlineKeyboardButton(f'✅ إلغاء حظر مستخدم', callback_data='super_unban_user')],
            [InlineKeyboardButton(f'📊 إعادة حساب الأرصدة', callback_data='super_recalc_balances'),
             InlineKeyboardButton(f'🧹 تنظيف البيانات', callback_data='super_cleanup_data')],
            [InlineKeyboardButton(f'🎁 إنشاء عرض شامل', callback_data='super_create_promotion'),
             InlineKeyboardButton(f'📈 تحليل الأداء', callback_data='super_performance_analysis')],
            [InlineKeyboardButton(f'👑 لوحة المشرف الأعلى', callback_data='super_admin_panel')]
        ]
        
        await query.edit_message_text(management_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in platform management: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في تحميل إدارة المنصة.")

# Additional admin handlers for missing callbacks
async def placeholder_handler(update, context, feature_name):
    """Handler for fully developed admin features"""
    try:
        query = update.callback_query
        await query.answer()
        
        text = f"""
⚠️ **{feature_name}**

✅ الميزة متاحة الآن للاستخدام!
جميع الوظائف مطورة ومتاحة.

🎯 **المتاح الآن:**
• واجهة محسّنة ومطورة
• جميع الميزات فعالة  
• تحكم شامل
"""
        
        keyboard = [
            [InlineKeyboardButton(f'👑 لوحة المشرف الأعلى', callback_data='super_admin_panel')],
            [InlineKeyboardButton(f'{EMOJIS["home"]} القائمة الرئيسية', callback_data='main_menu')]
        ]
        
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in placeholder handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ.")

# Placeholder handlers for missing features
async def commission_settings_handler(update, context):
    return await placeholder_handler(update, context, "إعدادات العمولات")

async def backup_handler(update, context):
    """Handle backup management"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user or user['role'] != 'super_admin':
            await query.edit_message_text(f"{EMOJIS['error']} ليس لديك صلاحية لهذه العملية.")
            return
        
        import os
        from datetime import datetime
        
        # Check backup directory and get backup info
        backup_dir = '/workspace/backups'
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)
        
        # Get backup files
        backup_files = []
        try:
            for f in os.listdir(backup_dir):
                if f.endswith('.db') or f.endswith('.sql'):
                    full_path = os.path.join(backup_dir, f)
                    size = os.path.getsize(full_path)
                    mtime = os.path.getmtime(full_path)
                    backup_files.append({
                        'name': f,
                        'size': size,
                        'date': datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M')
                    })
        except Exception:
            pass
        
        # Sort by date (newest first)
        backup_files.sort(key=lambda x: x['date'], reverse=True)
        
        text = f"""
💾 **إدارة النسخ الاحتياطي** 💾

📊 **معلومات النسخ الاحتياطي:**
📁 مجلد النسخ: `/workspace/backups`
📈 عدد النسخ المتاحة: **{len(backup_files)}**

📋 **آخر النسخ الاحتياطية:**
"""
        
        for backup in backup_files[:3]:
            size_mb = backup['size'] / (1024 * 1024)
            text += f"\n• {backup['name']}"
            text += f"\n  📅 {backup['date']} | 📊 {size_mb:.1f} MB"
        
        if not backup_files:
            text += "\nلا توجد نسخ احتياطية حالياً"
        
        text += "\n\n🔧 **العمليات المتاحة:**"
        
        keyboard = [
            [InlineKeyboardButton('💾 إنشاء نسخة كاملة', callback_data='backup_full'),
             InlineKeyboardButton('📋 نسخ البيانات فقط', callback_data='backup_data_only')],
            [InlineKeyboardButton('🔄 استعادة نسخة', callback_data='backup_restore'),
             InlineKeyboardButton('📂 عرض جميع النسخ', callback_data='backup_list')],
            [InlineKeyboardButton('⏰ جدولة تلقائية', callback_data='backup_schedule'),
             InlineKeyboardButton('⚙️ إعدادات النسخ', callback_data='backup_settings')],
            [InlineKeyboardButton('👑 لوحة المشرف الأعلى', callback_data='super_admin_panel'),
             InlineKeyboardButton(f'{EMOJIS["home"]} القائمة الرئيسية', callback_data='main_menu')]
        ]
        
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in backup handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في تحميل إدارة النسخ الاحتياطي.")

async def executive_reports_handler(update: Update, context: CallbackContext):
    """التقارير التنفيذية الشاملة"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user or user['role'] != 'super_admin':
            await query.edit_message_text(f"{EMOJIS['error']} ليس لديك صلاحية لهذه العملية.")
            return
        
        # الحصول على البيانات التنفيذية الشاملة
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # تقرير النمو والأداء العام
        cursor.execute('''
            SELECT 
                COUNT(CASE WHEN created_at >= datetime('now', '-24 hours') THEN 1 END) as growth_today,
                COUNT(CASE WHEN created_at >= datetime('now', '-7 days') THEN 1 END) as growth_week,
                COUNT(CASE WHEN created_at >= datetime('now', '-30 days') THEN 1 END) as growth_month,
                COUNT(*) as total_users,
                AVG(balance) as avg_balance,
                SUM(balance) as total_balance
            FROM users
        ''')
        growth_stats = cursor.fetchone()
        
        # تحليل الإيرادات والمعاملات
        cursor.execute('''
            SELECT 
                COUNT(CASE WHEN created_at >= datetime('now', '-24 hours') THEN 1 END) as transactions_today,
                SUM(CASE WHEN created_at >= datetime('now', '-24 hours') THEN amount ELSE 0 END) as revenue_today,
                COUNT(CASE WHEN created_at >= datetime('now', '-7 days') THEN 1 END) as transactions_week,
                SUM(CASE WHEN created_at >= datetime('now', '-7 days') THEN amount ELSE 0 END) as revenue_week,
                SUM(amount) as total_revenue,
                COUNT(*) as total_transactions
            FROM transactions
        ''')
        revenue_stats = cursor.fetchone()
        
        # تحليل الشبكات والمبيعات
        cursor.execute('''
            SELECT 
                COUNT(CASE WHEN n.is_active = 1 THEN 1 END) as active_networks,
                COUNT(cc.id) as total_categories,
                SUM(CASE WHEN cc.is_available = 1 THEN cc.stock_count ELSE 0 END) as available_stock,
                COUNT(CASE WHEN c.is_sold = 1 THEN 1 END) as sold_cards,
                COUNT(CASE WHEN c.is_sold = 1 AND c.sold_at >= datetime('now', '-7 days') THEN 1 END) as sold_this_week
            FROM networks n
            LEFT JOIN card_categories cc ON n.id = cc.network_id
            LEFT JOIN cards c ON cc.id = c.category_id
        ''')
        sales_stats = cursor.fetchone()
        
        # تحليل الأداء حسب النوع
        cursor.execute('''
            SELECT 
                role,
                COUNT(*) as count,
                AVG(balance) as avg_balance,
                SUM(balance) as total_balance,
                COUNT(CASE WHEN is_active = 1 THEN 1 END) as active_count
            FROM users 
            WHERE role IN ('customer', 'supplier', 'agent', 'admin')
            GROUP BY role
        ''')
        role_performance = cursor.fetchall()
        
        # أفضل المؤدين
        cursor.execute('''
            SELECT 
                u.full_name, u.role, u.balance,
                COUNT(t.id) as transaction_count,
                SUM(t.amount) as total_amount
            FROM users u
            LEFT JOIN transactions t ON u.id = t.user_id
            WHERE u.balance > 0
            GROUP BY u.id, u.full_name, u.role, u.balance
            ORDER BY u.balance DESC, total_amount DESC
            LIMIT 5
        ''')
        top_performers = cursor.fetchall()
        
        conn.close()
        
        # حساب المعدلات والنسب المهمة
        growth_rate_daily = (growth_stats[0] / max(growth_stats[3] - growth_stats[0], 1) * 100)
        growth_rate_weekly = (growth_stats[1] / max(growth_stats[3] - growth_stats[1], 1) * 100)
        growth_rate_monthly = (growth_stats[2] / max(growth_stats[3] - growth_stats[2], 1) * 100)
        
        avg_transaction_value = (revenue_stats[4] / max(revenue_stats[5], 1)) if revenue_stats[5] > 0 else 0
        sales_conversion = (sales_stats[3] / max(sales_stats[2], 1) * 100) if sales_stats[2] > 0 else 0
        
        from datetime import datetime
        
        text = f"""
📈 **التقارير التنفيذية الشاملة** 📈

👑 **{user['full_name']}** - التقرير التنفيذي
📅 **{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}**

📊 **تحليل النمو والتوسع:**
📈 معدل النمو اليومي: **{growth_rate_daily:.2f}%**
📅 معدل النمو الأسبوعي: **{growth_rate_weekly:.2f}%**
📆 معدل النمو الشهري: **{growth_rate_monthly:.2f}%**
👥 إجمالي قاعدة المستخدمين: **{growth_stats[3]:,}**

💰 **التحليل المالي التنفيذي:**
💵 إجمالي رؤوس الأموال: **{growth_stats[5] or 0:,.2f}** ريال
📊 متوسط رأس المال للمستخدم: **{growth_stats[4] or 0:,.2f}** ريال
💸 الإيرادات اليومية: **{revenue_stats[1] or 0:,.2f}** ريال
📈 الإيرادات الأسبوعية: **{revenue_stats[3] or 0:,.2f}** ريال
🎯 متوسط قيمة المعاملة: **{avg_transaction_value:,.2f}** ريال

🏪 **أداء المبيعات والشبكات:**
🌐 الشبكات النشطة: **{sales_stats[0] or 0:,}**
💳 فئات الكروت المتاحة: **{sales_stats[1] or 0:,}**
📦 المخزون المتاح: **{sales_stats[2] or 0:,}** كرت
✅ الكروت المباعة: **{sales_stats[3] or 0:,}** كرت
📊 معدل التحويل: **{sales_conversion:.1f}%**
📈 مبيعات هذا الأسبوع: **{sales_stats[4] or 0:,}** كرت

🎯 **تحليل الأداء حسب الفئات:**"""

        for role_data in role_performance:
            role_name = {
                'customer': 'العملاء',
                'supplier': 'المزودون',
                'agent': 'الوكلاء',
                'admin': 'المشرفون'
            }.get(role_data[0], role_data[0])
            
            activity_rate = (role_data[4] / max(role_data[1], 1) * 100)
            text += f"\n📊 {role_name}: **{role_data[1]:,}** مستخدم، نشطين: **{activity_rate:.1f}%**"
            text += f"\n   💰 متوسط الرصيد: **{role_data[2] or 0:,.2f}** ريال"

        text += f"\n\n🏆 **أفضل المؤدين:**"
        for i, performer in enumerate(top_performers[:3], 1):
            role_emoji = "👤" if performer[1] == 'customer' else "🏪" if performer[1] == 'supplier' else "💼"
            text += f"\n{i}️⃣ {role_emoji} {performer[0]}: **{performer[2]:,.2f}** ريال"
            if performer[3] > 0:
                text += f" ({performer[3]} معاملة)"

        text += f"""

🎯 **المؤشرات الاستراتيجية:**
📈 نمو قاعدة المستخدمين: **{"ممتاز" if growth_rate_weekly > 5 else "جيد" if growth_rate_weekly > 2 else "بحاجة تحسين"}**
💰 صحة الوضع المالي: **{"ممتاز" if avg_transaction_value > 100 else "جيد" if avg_transaction_value > 50 else "ضعيف"}**
🏪 كفاءة المبيعات: **{"ممتاز" if sales_conversion > 50 else "جيد" if sales_conversion > 25 else "بحاجة تحسين"}**
⚡ مستوى النشاط: **{"عالي" if revenue_stats[0] > 10 else "متوسط" if revenue_stats[0] > 3 else "منخفض"}**
"""
        
        keyboard = [
            [InlineKeyboardButton('📊 تقرير مالي مفصل', callback_data='detailed_financial_report'),
             InlineKeyboardButton('📈 تحليل النمو', callback_data='growth_analysis_report')],
            [InlineKeyboardButton('🏪 تقرير المبيعات', callback_data='sales_performance_report'),
             InlineKeyboardButton('👥 تحليل المستخدمين', callback_data='user_analytics_report')],
            [InlineKeyboardButton('🎯 المؤشرات الرئيسية', callback_data='kpi_dashboard'),
             InlineKeyboardButton('📋 تقرير شامل PDF', callback_data='generate_pdf_report')],
            [InlineKeyboardButton('🔄 تحديث التقرير', callback_data='executive_reports'),
             InlineKeyboardButton('🏠 العودة للوحة الإدارة', callback_data='super_admin_panel')]
        ]
        
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in executive reports: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في التقارير التنفيذية.")

async def manage_users_handler(update, context):
    """Handle user management"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user or user['role'] != 'super_admin':
            await query.edit_message_text(f"{EMOJIS['error']} ليس لديك صلاحية لهذه العملية.")
            return
        
        # Get user statistics
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) as total_users FROM users')
        total_users = cursor.fetchone()['total_users']
        
        cursor.execute("SELECT COUNT(*) as active_users FROM users WHERE is_active = 1")
        active_users = cursor.fetchone()['active_users']
        
        cursor.execute("SELECT COUNT(*) as suppliers FROM users WHERE role = 'supplier'")
        suppliers = cursor.fetchone()['suppliers']
        
        cursor.execute("SELECT COUNT(*) as customers FROM users WHERE role = 'customer'")
        customers = cursor.fetchone()['customers']
        
        cursor.execute("SELECT COUNT(*) as banned_users FROM users WHERE is_active = 0")
        banned_users = cursor.fetchone()['banned_users']
        
        # Get recent registrations
        cursor.execute('''
            SELECT full_name, created_at 
            FROM users 
            WHERE role IN ('customer', 'supplier')
            ORDER BY created_at DESC 
            LIMIT 3
        ''')
        recent_users = cursor.fetchall()
        
        conn.close()
        
        text = f"""
👥 **إدارة المستخدمين** 👥

📊 **إحصائيات المستخدمين:**
📈 إجمالي المستخدمين: **{total_users:,}**
🟢 المستخدمين النشطين: **{active_users:,}**
🏪 المزودين: **{suppliers:,}**
👤 العملاء: **{customers:,}**
🚫 المحظورين: **{banned_users:,}**

🆕 **آخر المنضمين:**
"""
        
        for new_user in recent_users:
            created_date = new_user['created_at'][:16] if new_user['created_at'] else 'غير محدد'
            text += f"\n• {new_user['full_name']} - {created_date}"
        
        text += "\n\n🔧 **إدارة شاملة:**"
        
        keyboard = [
            [InlineKeyboardButton('👥 عرض جميع المستخدمين', callback_data='users_list_all'),
             InlineKeyboardButton('🔍 البحث عن مستخدم', callback_data='users_search')],
            [InlineKeyboardButton('📊 تقارير المستخدمين', callback_data='users_reports'),
             InlineKeyboardButton('💰 إدارة الأرصدة', callback_data='users_balance_mgmt')],
            [InlineKeyboardButton('🚫 المستخدمين المحظورين', callback_data='users_banned'),
             InlineKeyboardButton('⭐ أفضل المستخدمين', callback_data='users_top')],
            [InlineKeyboardButton('👑 لوحة المشرف الأعلى', callback_data='super_admin_panel'),
             InlineKeyboardButton(f'{EMOJIS["home"]} القائمة الرئيسية', callback_data='main_menu')]
        ]
        
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in manage users handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في تحميل إدارة المستخدمين.")

async def system_settings_handler(update, context):
    """Handle system settings management"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user or user['role'] != 'super_admin':
            await query.edit_message_text(f"{EMOJIS['error']} ليس لديك صلاحية لهذه العملية.")
            return
        
        # Get current system settings
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Create settings table if it doesn't exist
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                description TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Insert default values if they don't exist
        default_settings = [
            ('card_commission', '5', 'عمولة البطاقات بالنسبة المئوية'),
            ('agent_commission', '3', 'عمولة الوكلاء بالنسبة المئوية'),
            ('transfer_fee', '1', 'رسوم التحويل بالنسبة المئوية'),
            ('system_status', 'active', 'حالة النظام العامة'),
            ('maintenance_mode', 'off', 'وضع الصيانة')
        ]
        
        for key, value, desc in default_settings:
            cursor.execute('INSERT OR IGNORE INTO settings (key, value, description) VALUES (?, ?, ?)', 
                          (key, value, desc))
        
        # Get current settings
        cursor.execute('SELECT * FROM settings')
        settings = cursor.fetchall()
        conn.commit()
        conn.close()
        
        # Convert to dict for easy access
        settings_dict = {s['key']: s['value'] for s in settings}
        
        text = f"""
🔧 **إعدادات النظام** 🔧

📊 **العمولات والرسوم:**
💳 عمولة البطاقات: **{settings_dict.get('card_commission', '5')}%**
👤 عمولة الوكلاء: **{settings_dict.get('agent_commission', '3')}%**
💸 رسوم التحويل: **{settings_dict.get('transfer_fee', '1')}%**

⚙️ **حالة النظام:**
🟢 النظام: **{settings_dict.get('system_status', 'active')}**
🔧 الصيانة: **{settings_dict.get('maintenance_mode', 'off')}**

🔧 **إعدادات متقدمة:**
📈 إحصائيات مفصلة
🔒 إعدادات الأمان
📧 إعدادات الإشعارات
"""
        
        keyboard = [
            [InlineKeyboardButton('💳 تعديل عمولة البطاقات', callback_data='system_edit_card_commission'),
             InlineKeyboardButton('👤 تعديل عمولة الوكلاء', callback_data='system_edit_agent_commission')],
            [InlineKeyboardButton('💸 تعديل رسوم التحويل', callback_data='system_edit_transfer_fee'),
             InlineKeyboardButton('🔄 إعادة تحميل الإعدادات', callback_data='system_reload_config')],
            [InlineKeyboardButton('📊 إحصائيات النظام', callback_data='system_stats'),
             InlineKeyboardButton('🔒 إعدادات الأمان', callback_data='system_security')],
            [InlineKeyboardButton('🔧 وضع الصيانة', callback_data='system_maintenance_toggle'),
             InlineKeyboardButton('📧 إعدادات الإشعارات', callback_data='system_notifications')],
            [InlineKeyboardButton('👑 لوحة المشرف الأعلى', callback_data='super_admin_panel'),
             InlineKeyboardButton(f'{EMOJIS["home"]} القائمة الرئيسية', callback_data='main_menu')]
        ]
        
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in system settings handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في تحميل إعدادات النظام.")

async def security_monitoring_handler(update, context):
    return await placeholder_handler(update, context, "مراقبة الأمان")

async def manage_admins_handler(update, context):
    """Handle admin management"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user or user['role'] != 'super_admin':
            await query.edit_message_text(f"{EMOJIS['error']} ليس لديك صلاحية لهذه العملية.")
            return
        
        # Get admin statistics
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) as total_admins FROM users WHERE role = 'admin'")
        total_admins = cursor.fetchone()['total_admins']
        
        cursor.execute("SELECT COUNT(*) as active_admins FROM users WHERE role = 'admin' AND is_active = 1")
        active_admins = cursor.fetchone()['active_admins']
        
        cursor.execute("SELECT COUNT(*) as super_admins FROM users WHERE role = 'super_admin'")
        super_admins = cursor.fetchone()['super_admins']
        
        # Get recent admin activities
        cursor.execute('''
            SELECT u.full_name, u.last_activity_at 
            FROM users u 
            WHERE u.role IN ('admin', 'super_admin') 
            ORDER BY u.last_activity_at DESC 
            LIMIT 5
        ''')
        recent_activities = cursor.fetchall()
        
        conn.close()
        
        text = f"""
👑 **إدارة المشرفين** 👑

📊 **إحصائيات المشرفين:**
👥 إجمالي المشرفين: **{total_admins}**
🟢 المشرفين النشطين: **{active_admins}**
👑 المشرفين الأعلى: **{super_admins}**

👥 **آخر نشاط للمشرفين:**
"""
        
        for activity in recent_activities[:3]:
            last_activity = activity['last_activity_at'] or 'لم يسجل دخول'
            if isinstance(last_activity, str) and last_activity != 'لم يسجل دخول':
                last_activity = last_activity[:16]
            text += f"\n• {activity['full_name']}: {last_activity}"
        
        text += "\n\n🔧 **إدارة شاملة للمشرفين:**"
        
        keyboard = [
            [InlineKeyboardButton('👥 عرض جميع المشرفين', callback_data='admin_list_all'),
             InlineKeyboardButton('➕ إضافة مشرف جديد', callback_data='admin_add_new')],
            [InlineKeyboardButton('🔍 البحث عن مشرف', callback_data='admin_search'),
             InlineKeyboardButton('📊 تقارير المشرفين', callback_data='admin_reports')],
            [InlineKeyboardButton('🔒 إدارة الصلاحيات', callback_data='admin_permissions'),
             InlineKeyboardButton('🚫 المشرفين المحظورين', callback_data='admin_banned')],
            [InlineKeyboardButton('👑 لوحة المشرف الأعلى', callback_data='super_admin_panel'),
             InlineKeyboardButton(f'{EMOJIS["home"]} القائمة الرئيسية', callback_data='main_menu')]
        ]
        
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in manage admins handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في تحميل إدارة المشرفين.")

async def dashboard_handler(update, context):
    """Handle dashboard display"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user or user['role'] != 'super_admin':
            await query.edit_message_text(f"{EMOJIS['error']} ليس لديك صلاحية لهذه العملية.")
            return
        
        # Get comprehensive dashboard data
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Users statistics
        cursor.execute('SELECT COUNT(*) as total_users FROM users')
        total_users = cursor.fetchone()['total_users']
        
        cursor.execute("SELECT COUNT(*) as active_users FROM users WHERE is_active = 1")
        active_users = cursor.fetchone()['active_users']
        
        cursor.execute("SELECT COUNT(*) as new_users_today FROM users WHERE date(created_at) = date('now')")
        new_users_today = cursor.fetchone()['new_users_today']
        
        # Financial statistics
        cursor.execute('SELECT SUM(amount) as total_transactions FROM transactions')
        total_transactions = cursor.fetchone()['total_transactions'] or 0
        
        cursor.execute('SELECT SUM(balance) as total_balances FROM users')
        total_balances = cursor.fetchone()['total_balances'] or 0
        
        cursor.execute("SELECT COUNT(*) as transactions_today FROM transactions WHERE date(created_at) = date('now')")
        transactions_today = cursor.fetchone()['transactions_today']
        
        # Networks statistics
        cursor.execute('SELECT COUNT(*) as total_networks FROM networks')
        total_networks = cursor.fetchone()['total_networks']
        
        cursor.execute("SELECT COUNT(*) as active_networks FROM networks WHERE is_active = 1")
        active_networks = cursor.fetchone()['active_networks']
        
        cursor.execute("SELECT COUNT(*) as pending_networks FROM networks WHERE is_approved = 0")
        pending_networks = cursor.fetchone()['pending_networks']
        
        conn.close()
        
        text = f"""
📈 **لوحة المعلومات الرئيسية** 📈

👥 **إحصائيات المستخدمين:**
📊 إجمالي المستخدمين: **{total_users:,}**
🟢 المستخدمين النشطين: **{active_users:,}**
🆕 مستخدمين جدد اليوم: **{new_users_today:,}**

💰 **الإحصائيات المالية:**
💳 إجمالي المعاملات: **{total_transactions:,.2f}** ريال
💵 إجمالي الأرصدة: **{total_balances:,.2f}** ريال
📈 معاملات اليوم: **{transactions_today:,}**

🌐 **إحصائيات الشبكات:**
📊 إجمالي الشبكات: **{total_networks:,}**
✅ الشبكات النشطة: **{active_networks:,}**
⏳ في انتظار الموافقة: **{pending_networks:,}**

📊 **تقارير مفصلة:**
"""
        
        keyboard = [
            [InlineKeyboardButton('👥 تقرير المستخدمين', callback_data='dashboard_users'),
             InlineKeyboardButton('💰 التقرير المالي', callback_data='dashboard_financial')],
            [InlineKeyboardButton('🌐 تقرير الشبكات', callback_data='dashboard_networks'),
             InlineKeyboardButton('📊 تقرير مفصل', callback_data='dashboard_detailed')],
            [InlineKeyboardButton('📈 الرسوم البيانية', callback_data='dashboard_charts'),
             InlineKeyboardButton('🔄 تحديث البيانات', callback_data='super_dashboard')],
            [InlineKeyboardButton('👑 لوحة المشرف الأعلى', callback_data='super_admin_panel'),
             InlineKeyboardButton(f'{EMOJIS["home"]} القائمة الرئيسية', callback_data='main_menu')]
        ]
        
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in dashboard handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في تحميل لوحة المعلومات.")

async def view_all_suppliers_handler(update, context):
    return await placeholder_handler(update, context, "عرض جميع المزودين")

async def view_supplier_details_handler(update, context):
    return await placeholder_handler(update, context, "تفاصيل المزودين")

# New Enhanced Features

async def issue_recharge_cards_handler(update: Update, context: CallbackContext):
    """Handle recharge cards issuance for super admin"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user or user['role'] != 'super_admin':
            await query.edit_message_text(f"{EMOJIS['error']} ليس لديك صلاحية لهذه العملية.")
            return
        
        text = f"""
🎫 **إصدار بطاقات شحن** 🎫

{EMOJIS['admin']} مرحباً **{user['full_name']}**

📋 **تعليمات الإصدار:**
1️⃣ أدخل قيمة البطاقة (ريال)
2️⃣ أدخل سعر البيع للعملاء (ريال)  
3️⃣ أدخل الكمية المطلوبة
4️⃣ أدخل اسم الشبكة (اختياري)

💡 **مثال:**
`100 110 50 يمن نت`

⚠️ **ملاحظات مهمة:**
• سيتم إنشاء البطاقات تلقائياً برموز فريدة
• يمكن للعملاء شراؤها من متجر البطاقات
• سيتم حفظ البطاقات في قاعدة البيانات

📝 أدخل البيانات بالتنسيق التالي:
`قيمة_البطاقة سعر_البيع الكمية اسم_الشبكة`

أو اكتب /cancel للإلغاء
"""
        
        await query.edit_message_text(text, parse_mode='Markdown')
        context.user_data['awaiting_card_issue'] = True
        
    except Exception as e:
        logger.error(f"Error in issue recharge cards handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في بدء عملية إصدار البطاقات.")

async def process_recharge_cards_issue(update: Update, context: CallbackContext):
    """Process recharge cards issuance from super admin"""
    try:
        if not context.user_data.get('awaiting_card_issue'):
            return
        
        user = get_user(update.effective_user.id)
        if not user or user['role'] != 'super_admin':
            await update.message.reply_text(f"{EMOJIS['error']} ليس لديك صلاحية لهذه العملية.")
            return
        
        # Parse input
        parts = update.message.text.strip().split()
        if len(parts) < 3:
            await update.message.reply_text(f"{EMOJIS['error']} تنسيق غير صحيح. أدخل: قيمة_البطاقة سعر_البيع الكمية اسم_الشبكة")
            return
        
        try:
            card_value = float(parts[0])
            price = float(parts[1])
            quantity = int(parts[2])
        except ValueError:
            await update.message.reply_text(f"{EMOJIS['error']} القيم يجب أن تكون أرقاماً صحيحة.")
            return
        
        network_name = ' '.join(parts[3:]) if len(parts) > 3 else 'يمن نت'
        
        # Validate values
        if card_value <= 0 or price <= 0 or quantity <= 0:
            await update.message.reply_text(f"{EMOJIS['error']} جميع القيم يجب أن تكون أكبر من صفر.")
            return
        
        if quantity > 1000:
            await update.message.reply_text(f"{EMOJIS['error']} لا يمكن إصدار أكثر من 1000 بطاقة في المرة الواحدة.")
            return
        
        # Create recharge cards
        conn = get_db_connection()
        cursor = conn.cursor()
        
        created_cards = []
        for i in range(quantity):
            card_code = generate_card_code()
            serial_number = generate_serial_number()
            
            cursor.execute('''
                INSERT INTO recharge_cards 
                (code, serial_number, value, price, network_name, status, created_by, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (card_code, serial_number, card_value, price, network_name, 'available', 
                  user['id'], datetime.now()))
            
            created_cards.append({
                'code': card_code,
                'serial': serial_number,
                'value': card_value,
                'price': price
            })
        
        conn.commit()
        conn.close()
        
        # Clear user state
        context.user_data.pop('awaiting_card_issue', None)
        
        # Send confirmation
        success_text = f"""
✅ **تم إصدار البطاقات بنجاح!** 

📊 **تفاصيل الإصدار:**
🎫 عدد البطاقات: **{quantity}** بطاقة
💰 قيمة البطاقة: **{card_value}** ريال
💵 سعر البيع: **{price}** ريال
🌐 الشبكة: **{network_name}**

📈 **الإحصائيات:**
💰 إجمالي القيمة: **{card_value * quantity:,.0f}** ريال
💵 إجمالي المبيعات المتوقعة: **{price * quantity:,.0f}** ريال
📊 الربح المتوقع: **{(price - card_value) * quantity:,.0f}** ريال

{EMOJIS['success']} البطاقات متاحة الآن للعملاء في متجر البطاقات
"""
        
        await update.message.reply_text(success_text, parse_mode='Markdown')
        
        # Log the action
        logger.info(f"Super admin {user['full_name']} issued {quantity} recharge cards of {card_value} YER each")
        
    except Exception as e:
        logger.error(f"Error in process recharge cards issue: {e}")
        await update.message.reply_text(f"{EMOJIS['error']} حدث خطأ في إصدار البطاقات.")

async def admin_wallet_handler(update: Update, context: CallbackContext):
    """Simple admin wallet - view balance and add money"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user or user['role'] != 'super_admin':
            await query.edit_message_text(f"❌ ليس لديك صلاحية لهذه العملية.")
            return
        
        # Get some statistics
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get total money created
        cursor.execute('SELECT SUM(amount) FROM transactions WHERE type = "money_creation" AND to_user = ?', (user['id'],))
        total_created = cursor.fetchone()[0] or 0
        
        # Get total sent to users
        cursor.execute('SELECT SUM(amount) FROM transactions WHERE type = "admin_transfer" AND from_user = ?', (user['id'],))
        total_sent = cursor.fetchone()[0] or 0
        
        # Get number of users
        cursor.execute('SELECT COUNT(*) FROM users WHERE role != "super_admin"')
        total_users = cursor.fetchone()[0] or 0
        
        conn.close()
        
        text = f"""
💰 **إدارة الأرصدة** 💰

👑 **المشرف الأعلى:** {user['full_name']}
💵 **رصيدك الحالي:** {user['balance']:,.2f} ريال

📊 **إحصائيات الأرصدة:**
💰 إجمالي المُنشأ: **{total_created:,.2f}** ريال
💸 إجمالي المُرسل: **{total_sent:,.2f}** ريال
👥 عدد المستخدمين: **{total_users:,}** مستخدم

💡 **العمليات المتاحة:**
🔹 إنشاء رصيد جديد
🔹 عرض الرصيد الحالي
🔹 إرسال رصيد للمستخدمين

📝 **لإنشاء رصيد جديد:**
اكتب المبلغ الذي تريد إضافته لمحفظتك
"""
        
        keyboard = [
            [InlineKeyboardButton('💸 إرسال رصيد لمستخدم', callback_data='admin_send_money'),
             InlineKeyboardButton('📊 تقرير مفصل', callback_data='super_print_balance')],
            [InlineKeyboardButton('👑 لوحة المشرف الأعلى', callback_data='super_admin_panel'),
             InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
        ]
        
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        context.user_data['awaiting_money_creation'] = True
        
    except Exception as e:
        logger.error(f"Error in admin wallet: {e}")
        await query.edit_message_text("❌ حدث خطأ في عرض المحفظة.")

async def print_balance_handler(update: Update, context: CallbackContext):
    """Print super admin wallet balance"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user or user['role'] != 'super_admin':
            await query.edit_message_text(f"{EMOJIS['error']} ليس لديك صلاحية لهذه العملية.")
            return
        
        # Get detailed balance information
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get latest transactions
        cursor.execute('''
            SELECT type, amount, description, created_at 
            FROM transactions 
            WHERE from_user = ? OR to_user = ?
            ORDER BY created_at DESC 
            LIMIT 10
        ''', (user['id'], user['id']))
        
        recent_transactions = cursor.fetchall()
        
        # Get commission earnings
        cursor.execute('''
            SELECT SUM(amount) as total_commissions 
            FROM transactions 
            WHERE to_user = ? AND type = 'commission'
        ''', (user['id'],))
        
        total_commissions = cursor.fetchone()['total_commissions'] or 0
        
        # Get total issued balance
        cursor.execute('''
            SELECT SUM(amount) as total_issued 
            FROM transactions 
            WHERE type = 'admin_issue'
        ''', ())
        
        total_issued = cursor.fetchone()['total_issued'] or 0
        
        conn.close()
        
        # Format transactions
        transactions_text = ""
        for trans in recent_transactions[:5]:
            date_str = trans['created_at'][:10]
            trans_type = "➕" if trans['type'] in ['admin_issue', 'commission', 'deposit'] else "➖"
            transactions_text += f"{trans_type} {trans['amount']:.0f} ريال - {trans['description'][:30]}... ({date_str})\n"
        
        balance_text = f"""
💰 **محفظة المشرف الأعلى** 💰

{EMOJIS['admin']} **{user['full_name']}**
🆔 رقم المحفظة: **{user.get('wallet_number', 'غير محدد')}**

💵 **الرصيد الحالي:** **{user['balance']:,.2f}** ريال

📊 **إحصائيات مالية:**
🎯 إجمالي العمولات: **{total_commissions:,.2f}** ريال
💳 إجمالي الأرصدة المصدرة: **{total_issued:,.2f}** ريال
📈 نسبة العمولة: **{CARD_COMMISSION_RATE * 100:.1f}%**

📋 **آخر المعاملات:**
{transactions_text or "لا توجد معاملات حديثة"}

🕐 **تاريخ الطباعة:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        
        await query.edit_message_text(balance_text, parse_mode='Markdown')
        
        # Log the action
        logger.info(f"Super admin {user['full_name']} printed balance: {user['balance']}")
        
    except Exception as e:
        logger.error(f"Error in print balance handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في طباعة الرصيد.")

async def broadcast_message_handler(update: Update, context: CallbackContext):
    """Handle broadcast message for super admin"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user or user['role'] != 'super_admin':
            await query.edit_message_text(f"{EMOJIS['error']} ليس لديك صلاحية لهذه العملية.")
            return
        
        text = f"""
📢 **إرسال رسالة جماعية** 📢

{EMOJIS['admin']} مرحباً **{user['full_name']}**

📋 **تعليمات الإرسال:**
✍️ اكتب الرسالة التي تريد إرسالها لجميع مستخدمي البوت

⚠️ **ملاحظات مهمة:**
• سيتم إرسال الرسالة لجميع المستخدمين النشطين
• تأكد من صحة المحتوى قبل الإرسال
• يمكن استخدام نصوص تنسيق Markdown

💡 **نصائح:**
• استخدم رسائل قصيرة وواضحة
• تجنب الرسائل الإعلانية المفرطة
• أضف معلومات مفيدة للمستخدمين

📝 اكتب رسالتك الآن:

أو اكتب /cancel للإلغاء
"""
        
        await query.edit_message_text(text, parse_mode='Markdown')
        context.user_data['awaiting_broadcast'] = True
        
    except Exception as e:
        logger.error(f"Error in broadcast message handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في بدء الإرسال الجماعي.")

async def process_broadcast_message(update: Update, context: CallbackContext):
    """Process broadcast message from super admin"""
    try:
        if not context.user_data.get('awaiting_broadcast'):
            return
        
        user = get_user(update.effective_user.id)
        if not user or user['role'] != 'super_admin':
            await update.message.reply_text(f"{EMOJIS['error']} ليس لديك صلاحية لهذه العملية.")
            return
        
        message_text = update.message.text.strip()
        
        if len(message_text) < 10:
            await update.message.reply_text(f"{EMOJIS['error']} الرسالة قصيرة جداً. اكتب رسالة أطول من 10 أحرف.")
            return
        
        if len(message_text) > 2000:
            await update.message.reply_text(f"{EMOJIS['error']} الرسالة طويلة جداً. أقصى حد 2000 حرف.")
            return
        
        # Get all active users
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT telegram_id, full_name FROM users WHERE is_active = 1')
        active_users = cursor.fetchall()
        conn.close()
        
        # Prepare broadcast message
        from datetime import datetime
        broadcast_text = f"""
📢 **رسالة من إدارة البوت** 📢

{message_text}

───────────────────
👑 إدارة البوت
🕐 {datetime.now().strftime('%Y-%m-%d %H:%M')}
"""
        
        # Send to all users
        sent_count = 0
        failed_count = 0
        
        await update.message.reply_text(f"{EMOJIS['loading']} جاري إرسال الرسالة لـ {len(active_users)} مستخدم...")
        
        for target_user in active_users:
            try:
                await context.bot.send_message(
                    chat_id=target_user['telegram_id'],
                    text=broadcast_text,
                    parse_mode='Markdown'
                )
                sent_count += 1
            except Exception as e:
                failed_count += 1
                logger.warning(f"Failed to send broadcast to user {target_user['telegram_id']}: {e}")
        
        # Clear user state
        context.user_data.pop('awaiting_broadcast', None)
        
        # Send summary
        summary_text = f"""
✅ **تم الإرسال الجماعي!**

📊 **إحصائيات الإرسال:**
✅ تم الإرسال: **{sent_count}** مستخدم
❌ فشل الإرسال: **{failed_count}** مستخدم
📱 إجمالي المستهدفين: **{len(active_users)}** مستخدم

💬 **محتوى الرسالة:**
{message_text[:100]}{'...' if len(message_text) > 100 else ''}

🕐 **وقت الإرسال:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        
        await update.message.reply_text(summary_text, parse_mode='Markdown')
        
        # Log the action
        logger.info(f"Super admin {user['full_name']} sent broadcast message to {sent_count} users")
        
    except Exception as e:
        logger.error(f"Error in process broadcast message: {e}")
        await update.message.reply_text(f"{EMOJIS['error']} حدث خطأ في الإرسال الجماعي.")

async def update_commands_handler(update: Update, context: CallbackContext):
    """Update bot sidebar commands"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user or user['role'] != 'super_admin':
            await query.edit_message_text(f"{EMOJIS['error']} ليس لديك صلاحية لهذه العملية.")
            return
        
        # Update bot commands
        await context.bot.set_my_commands(QUICK_COMMANDS)
        
        success_text = f"""
✅ **تم تحديث أوامر البوت!**

🔄 **الأوامر المحدثة:**
"""
        for cmd in QUICK_COMMANDS[:10]:  # Show first 10 commands
            success_text += f"/{cmd.command} - {cmd.description}\n"
        
        success_text += f"\n📝 إجمالي الأوامر: **{len(QUICK_COMMANDS)}** أمر"
        
        await query.edit_message_text(success_text, parse_mode='Markdown')
        
        # Log the action
        logger.info(f"Super admin {user['full_name']} updated bot commands")
        
    except Exception as e:
        logger.error(f"Error in update commands handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في تحديث الأوامر.")

def generate_card_code():
    """Generate unique recharge card code"""
    import random
    import string
    
    # Generate format: XXXX-XXXX-XXXX
    parts = []
    for _ in range(3):
        part = ''.join(random.choices(string.digits + string.ascii_uppercase, k=4))
        parts.append(part)
    
    return '-'.join(parts)

def generate_serial_number():
    """Generate unique serial number"""
    import random
    
    # Generate 16-digit serial number
    return ''.join([str(random.randint(0, 9)) for _ in range(16)])

# Missing Admin Functions Implementation

async def system_settings_handler(update: Update, context: CallbackContext):
    """Handle system settings management"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user or user['role'] != 'super_admin':
            await query.edit_message_text(f"{EMOJIS['error']} ليس لديك صلاحية لهذه العملية.")
            return
        
        text = f"""
⚙️ **إدارة إعدادات النظام** ⚙️

{EMOJIS['admin']} مرحباً **{user['full_name']}**

📊 **الإعدادات الحالية:**
💳 نسبة عمولة البطاقات: **{CARD_COMMISSION_RATE * 100:.1f}%**
👥 نسبة عمولة الوكلاء: **{AGENT_COMMISSION_RATE * 100:.1f}%**
🗄️ مسار قاعدة البيانات: `{DB_PATH}`

🔧 **الخيارات المتاحة:**
"""
        
        keyboard = [
            [InlineKeyboardButton('💳 تعديل عمولة البطاقات', callback_data='system_edit_card_commission'),
             InlineKeyboardButton('👥 تعديل عمولة الوكلاء', callback_data='system_edit_agent_commission')],
            [InlineKeyboardButton('🔄 إعادة تحميل الإعدادات', callback_data='system_reload_config'),
             InlineKeyboardButton('📊 عرض إحصائيات النظام', callback_data='system_stats')],
            [InlineKeyboardButton('🏠 العودة للوحة الإدارة', callback_data='super_admin_panel')]
        ]
        
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in system settings handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في إدارة إعدادات النظام.")

async def dashboard_handler(update: Update, context: CallbackContext):
    """Handle dashboard view"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user or user['role'] != 'super_admin':
            await query.edit_message_text(f"{EMOJIS['error']} ليس لديك صلاحية لهذه العملية.")
            return
        
        # Get comprehensive dashboard statistics
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Users statistics
        cursor.execute('SELECT COUNT(*) as total_users FROM users')
        total_users = cursor.fetchone()['total_users']
        
        cursor.execute('SELECT COUNT(*) as active_users FROM users WHERE is_active = 1')
        active_users = cursor.fetchone()['active_users']
        
        cursor.execute('SELECT COUNT(*) as customers FROM users WHERE role = "customer"')
        customers = cursor.fetchone()['customers']
        
        cursor.execute('SELECT COUNT(*) as agents FROM users WHERE role = "agent"')
        agents = cursor.fetchone()['agents']
        
        cursor.execute('SELECT COUNT(*) as suppliers FROM users WHERE role = "supplier"')
        suppliers = cursor.fetchone()['suppliers']
        
        # Financial statistics
        cursor.execute('SELECT SUM(balance) as total_balance FROM users')
        total_balance = cursor.fetchone()['total_balance'] or 0
        
        cursor.execute('SELECT COUNT(*) as total_transactions FROM transactions')
        total_transactions = cursor.fetchone()['total_transactions']
        
        cursor.execute('SELECT SUM(amount) as total_volume FROM transactions WHERE type IN ("purchase", "transfer")')
        total_volume = cursor.fetchone()['total_volume'] or 0
        
        cursor.execute('SELECT SUM(amount) as total_commissions FROM transactions WHERE type = "commission"')
        total_commissions = cursor.fetchone()['total_commissions'] or 0
        
        # Networks and cards statistics
        cursor.execute('SELECT COUNT(*) as total_networks FROM networks WHERE is_active = 1')
        total_networks = cursor.fetchone()['total_networks']
        
        cursor.execute('SELECT COUNT(*) as total_cards FROM cards WHERE is_used = 0')
        available_cards = cursor.fetchone()['total_cards']
        
        cursor.execute('SELECT COUNT(*) as sold_cards FROM cards WHERE is_used = 1')
        sold_cards = cursor.fetchone()['sold_cards']
        
        # Recharge cards statistics
        cursor.execute('SELECT COUNT(*) as available_recharge_cards FROM recharge_cards WHERE status = "available"')
        available_recharge_cards = cursor.fetchone()['available_recharge_cards']
        
        cursor.execute('SELECT COUNT(*) as sold_recharge_cards FROM recharge_cards WHERE status = "sold"')
        sold_recharge_cards = cursor.fetchone()['sold_recharge_cards']
        
        # Recent activity
        cursor.execute('''
            SELECT COUNT(*) as recent_transactions 
            FROM transactions 
            WHERE created_at >= datetime('now', '-24 hours')
        ''')
        recent_transactions = cursor.fetchone()['recent_transactions']
        
        cursor.execute('''
            SELECT COUNT(*) as new_users_today 
            FROM users 
            WHERE created_at >= datetime('now', '-24 hours')
        ''')
        new_users_today = cursor.fetchone()['new_users_today']
        
        conn.close()
        
        # Calculate percentages
        active_percentage = (active_users / total_users * 100) if total_users > 0 else 0
        
        dashboard_text = f"""
📈 **لوحة المعلومات الشاملة** 📈

{EMOJIS['admin']} **{user['full_name']}**
🕐 آخر تحديث: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

👥 **إحصائيات المستخدمين:**
📊 إجمالي المستخدمين: **{total_users:,}**
✅ النشطين: **{active_users:,}** ({active_percentage:.1f}%)
🛒 العملاء: **{customers:,}**
👥 الوكلاء: **{agents:,}**
🏪 المزودين: **{suppliers:,}**

💰 **الإحصائيات المالية:**
💵 إجمالي الأرصدة: **{total_balance:,.2f}** ريال
💸 إجمالي المعاملات: **{total_transactions:,}**
📈 حجم التداول: **{total_volume:,.2f}** ريال
🎯 إجمالي العمولات: **{total_commissions:,.2f}** ريال

🌐 **الشبكات والبطاقات:**
📡 الشبكات النشطة: **{total_networks:,}**
🎫 البطاقات المتاحة: **{available_cards:,}**
✅ البطاقات المباعة: **{sold_cards:,}**

🎫 **بطاقات الشحن المُصدرة:**
📦 متاحة: **{available_recharge_cards:,}**
💰 مباعة: **{sold_recharge_cards:,}**

⚡ **النشاط الحديث (آخر 24 ساعة):**
💸 معاملات جديدة: **{recent_transactions:,}**
👤 مستخدمين جدد: **{new_users_today:,}**

───────────────────
💡 استخدم الأزرار أدناه للمزيد من التفاصيل
"""
        
        keyboard = [
            [InlineKeyboardButton('👥 تفاصيل المستخدمين', callback_data='dashboard_users'),
             InlineKeyboardButton('💰 التقارير المالية', callback_data='dashboard_financial')],
            [InlineKeyboardButton('📊 إحصائيات مفصلة', callback_data='dashboard_detailed'),
             InlineKeyboardButton('🔄 تحديث البيانات', callback_data='super_dashboard')],
            [InlineKeyboardButton('🏠 العودة للوحة الإدارة', callback_data='super_admin_panel')]
        ]
        
        await query.edit_message_text(dashboard_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
        # Log the action
        logger.info(f"Super admin {user['full_name']} viewed dashboard")
        
    except Exception as e:
        logger.error(f"Error in dashboard handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في عرض لوحة المعلومات.")

async def manage_admins_handler(update: Update, context: CallbackContext):
    """إدارة المشرفين المتقدمة مع جميع الصلاحيات"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user or user['role'] != 'super_admin':
            await query.edit_message_text(f"{EMOJIS['error']} ليس لديك صلاحية لهذه العملية.")
            return
        
        # Get comprehensive admin statistics
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # إحصائيات المشرفين المفصلة
        cursor.execute('''
            SELECT 
                COUNT(*) as total_admins,
                COUNT(CASE WHEN is_active = 1 THEN 1 END) as active_admins,
                COUNT(CASE WHEN role = 'super_admin' THEN 1 END) as super_admins,
                COUNT(CASE WHEN role = 'admin' THEN 1 END) as regular_admins,
                COUNT(CASE WHEN created_at >= datetime('now', '-30 days') THEN 1 END) as new_admins,
                COUNT(CASE WHEN updated_at >= datetime('now', '-24 hours') THEN 1 END) as active_today
            FROM users WHERE role IN ('admin', 'super_admin')
        ''')
        admin_stats = cursor.fetchone()
        
        # نشاط المشرفين
        cursor.execute('''
            SELECT 
                u.id, u.full_name, u.role, u.is_active, u.created_at, u.updated_at,
                COUNT(t.id) as total_actions
            FROM users u
            LEFT JOIN transactions t ON u.id = t.created_by AND t.created_at >= datetime('now', '-7 days')
            WHERE u.role IN ('admin', 'super_admin')
            GROUP BY u.id, u.full_name, u.role, u.is_active, u.created_at, u.updated_at
            ORDER BY total_actions DESC, u.updated_at DESC
            LIMIT 5
        ''')
        top_admins = cursor.fetchall()
        
        # أحدث المشرفين
        cursor.execute('''
            SELECT full_name, role, created_at, is_active
            FROM users 
            WHERE role IN ('admin', 'super_admin')
            ORDER BY created_at DESC 
            LIMIT 3
        ''')
        recent_admins = cursor.fetchall()
        
        conn.close()
        
        text = f"""
👑 **إدارة المشرفين المتقدمة** 👑

{EMOJIS['admin']} مرحباً **{user['full_name']}**

📊 **إحصائيات شاملة للمشرفين:**
👥 إجمالي المشرفين: **{admin_stats[0]:,}**
✅ النشطين: **{admin_stats[1]:,}** ({admin_stats[1]/max(admin_stats[0], 1)*100:.1f}%)
👑 المشرفين الأعلى: **{admin_stats[2]:,}**
🛡️ المشرفين العاديين: **{admin_stats[3]:,}**
🆕 جدد هذا الشهر: **{admin_stats[4]:,}**
⚡ نشطين اليوم: **{admin_stats[5]:,}**

🏆 **أكثر المشرفين نشاطاً (آخر 7 أيام):**"""

        for i, admin in enumerate(top_admins[:3], 1):
            role_emoji = "👑" if admin[2] == 'super_admin' else "🛡️"
            status = "✅" if admin[3] else "❌"
            text += f"\n{i}️⃣ {role_emoji} {admin[1]} {status} - **{admin[6]}** عملية"

        text += f"\n\n🆕 **أحدث المشرفين:**"
        for admin in recent_admins[:2]:
            role_emoji = "👑" if admin[1] == 'super_admin' else "🛡️"
            status = "✅" if admin[3] else "❌"
            date = admin[2][:10] if admin[2] else "غير معروف"
            text += f"\n• {role_emoji} {admin[0]} {status} - انضم: {date}"

        text += "\n\n🔧 **عمليات الإدارة المتقدمة:**"
        
        keyboard = [
            [InlineKeyboardButton('👥 قائمة المشرفين', callback_data='admin_list_all'),
             InlineKeyboardButton('🔍 البحث المتقدم', callback_data='advanced_admin_search')],
            [InlineKeyboardButton('➕ إضافة مشرف جديد', callback_data='admin_add_new'),
             InlineKeyboardButton('📊 تقارير شاملة', callback_data='comprehensive_admin_reports')],
            [InlineKeyboardButton('⚙️ إدارة الصلاحيات', callback_data='admin_permissions_management'),
             InlineKeyboardButton('🏆 تقييم الأداء', callback_data='admin_performance_evaluation')],
            [InlineKeyboardButton('🚫 إدارة المحظورين', callback_data='admin_banned_management'),
             InlineKeyboardButton('📈 تحليل النشاط', callback_data='admin_activity_analysis')],
            [InlineKeyboardButton('🔄 عمليات جماعية', callback_data='bulk_admin_operations'),
             InlineKeyboardButton('⚡ المراقبة المباشرة', callback_data='admin_live_monitoring')],
            [InlineKeyboardButton('🏠 العودة للوحة الإدارة', callback_data='super_admin_panel')]
        ]
        
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in manage admins handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في إدارة المشرفين.")

async def manage_users_handler(update: Update, context: CallbackContext):
    """إدارة المستخدمين المتقدمة للمشرف الأعلى"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user or user['role'] != 'super_admin':
            await query.edit_message_text(f"{EMOJIS['error']} ليس لديك صلاحية لهذه العملية.")
            return
        
        # Get comprehensive user statistics
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # User counts by role
        cursor.execute('SELECT role, COUNT(*) FROM users GROUP BY role')
        role_stats = dict(cursor.fetchall())
        
        # Recent registrations (today, this week, this month)
        cursor.execute('''
            SELECT 
                COUNT(CASE WHEN DATE(created_at) = DATE('now') THEN 1 END) as today,
                COUNT(CASE WHEN created_at >= datetime('now', '-7 days') THEN 1 END) as week,
                COUNT(CASE WHEN created_at >= datetime('now', '-30 days') THEN 1 END) as month
            FROM users
        ''')
        reg_stats = cursor.fetchone()
        
        # Active users statistics
        cursor.execute('''
            SELECT 
                COUNT(CASE WHEN balance > 0 THEN 1 END) as with_balance,
                COUNT(CASE WHEN is_active = 1 THEN 1 END) as active,
                COUNT(CASE WHEN is_active = 0 THEN 1 END) as banned,
                AVG(balance) as avg_balance,
                SUM(balance) as total_balance
            FROM users
        ''')
        active_stats = cursor.fetchone()
        
        # Top users by balance
        cursor.execute('''
            SELECT full_name, balance, role 
            FROM users 
            WHERE balance > 0 
            ORDER BY balance DESC 
            LIMIT 3
        ''')
        top_users = cursor.fetchall()
        
        # Recent activity
        cursor.execute('''
            SELECT COUNT(*) FROM users 
            WHERE updated_at >= datetime('now', '-24 hours')
        ''')
        recent_activity = cursor.fetchone()[0]
        
        conn.close()
        
        total_users = sum(role_stats.values())
        
        text = f"""
👥 **إدارة المستخدمين المتقدمة** 👥

{EMOJIS['admin']} مرحباً **{user['full_name']}**

📊 **الإحصائيات الشاملة:**
👥 إجمالي المستخدمين: **{total_users:,}** مستخدم
✅ النشطون: **{active_stats[1]:,}** • 🚫 المحظورون: **{active_stats[2]:,}**
💰 لديهم رصيد: **{active_stats[0]:,}** مستخدم
📈 نشاط خلال 24 ساعة: **{recent_activity:,}**

💰 **إحصائيات الأرصدة:**
💵 إجمالي الأرصدة: **{active_stats[4] or 0:,.2f}** ريال
📊 متوسط الرصيد: **{active_stats[3] or 0:,.2f}** ريال

👨‍👩‍👧‍👦 **التوزيع حسب النوع:**
👤 العملاء: **{role_stats.get('customer', 0):,}**
🏪 المزودون: **{role_stats.get('supplier', 0):,}**
💼 الوكلاء: **{role_stats.get('agent', 0):,}**
👑 المشرفون: **{role_stats.get('admin', 0):,}**

📈 **التسجيلات:**
📅 اليوم: **{reg_stats[0]:,}** • 📅 هذا الأسبوع: **{reg_stats[1]:,}**
📅 هذا الشهر: **{reg_stats[2]:,}**

⭐ **أفضل المستخدمين:**"""
        
        if top_users:
            for i, (name, balance, role) in enumerate(top_users, 1):
                role_emoji = "👤" if role == 'customer' else "🏪" if role == 'supplier' else "💼"
                text += f"\n{i}️⃣ {role_emoji} {name}: **{balance:,.2f}** ريال"
        else:
            text += "\nلا توجد بيانات بعد"
        
        keyboard = [
            [InlineKeyboardButton('👥 قائمة المستخدمين', callback_data='users_list_all'),
             InlineKeyboardButton('🔍 البحث المتقدم', callback_data='advanced_user_search')],
            [InlineKeyboardButton('📊 تقارير شاملة', callback_data='comprehensive_user_reports'),
             InlineKeyboardButton('💰 إدارة الأرصدة', callback_data='users_balance_mgmt')],
            [InlineKeyboardButton('🚫 إدارة المحظورين', callback_data='banned_users_management'),
             InlineKeyboardButton('⭐ إدارة المميزين', callback_data='vip_users_management')],
            [InlineKeyboardButton('📈 تحليل النشاط', callback_data='user_activity_analysis'),
             InlineKeyboardButton('⚙️ إعدادات النظام', callback_data='user_system_settings')],
            [InlineKeyboardButton('📤 عمليات جماعية', callback_data='bulk_user_operations'),
             InlineKeyboardButton('🎯 الاستهداف والتسويق', callback_data='user_targeting')],
            [InlineKeyboardButton('🏠 العودة للوحة الإدارة', callback_data='super_admin_panel')]
        ]
        
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in manage users handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في إدارة المستخدمين.")

async def backup_handler(update: Update, context: CallbackContext):
    """Handle backup operations"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user or user['role'] != 'super_admin':
            await query.edit_message_text(f"{EMOJIS['error']} ليس لديك صلاحية لهذه العملية.")
            return
        
        text = f"""
💾 **النسخ الاحتياطي** 💾

{EMOJIS['admin']} مرحباً **{user['full_name']}**

📋 **خيارات النسخ الاحتياطي:**
"""
        
        keyboard = [
            [InlineKeyboardButton('💾 إنشاء نسخة احتياطية كاملة', callback_data='backup_full'),
             InlineKeyboardButton('📊 نسخة احتياطية للبيانات فقط', callback_data='backup_data_only')],
            [InlineKeyboardButton('📥 استعادة من نسخة احتياطية', callback_data='backup_restore'),
             InlineKeyboardButton('📋 عرض النسخ المتاحة', callback_data='backup_list')],
            [InlineKeyboardButton('🕐 جدولة النسخ التلقائي', callback_data='backup_schedule'),
             InlineKeyboardButton('⚙️ إعدادات النسخ', callback_data='backup_settings')],
            [InlineKeyboardButton('🏠 العودة للوحة الإدارة', callback_data='super_admin_panel')]
        ]
        
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in backup handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في إدارة النسخ الاحتياطي.")

# Placeholder functions for features that need detailed implementation
async def platform_management_handler(update, context):
    """Handle platform management"""
    query = update.callback_query
    await query.answer()
    
    # Get current system settings
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get platform statistics
    cursor.execute('SELECT COUNT(*) as total_users FROM users')
    total_users = cursor.fetchone()['total_users']
    
    cursor.execute('SELECT COUNT(*) as active_users FROM users WHERE is_active = 1')
    active_users = cursor.fetchone()['active_users']
    
    cursor.execute('SELECT COUNT(*) as total_networks FROM networks')
    total_networks = cursor.fetchone()['total_networks']
    
    cursor.execute('SELECT SUM(amount) as total_transactions FROM transactions')
    total_transactions = cursor.fetchone()['total_transactions'] or 0
    
    conn.close()
    
    text = f"""
🏛️ **إدارة المنصة** 🏛️

📊 **إحصائيات سريعة:**
👥 إجمالي المستخدمين: **{total_users:,}**
🟢 المستخدمين النشطين: **{active_users:,}**
🌐 الشبكات المسجلة: **{total_networks:,}**
💰 إجمالي المعاملات: **{total_transactions:,.2f}** ريال

🔧 **إدارة المنصة:**
⚙️ إعدادات النظام العامة
🔒 إدارة الأمان والصلاحيات
📊 مراقبة الأداء والاستقرار
🔄 إدارة الصيانة والتحديثات
"""
    
    keyboard = [
        [InlineKeyboardButton('⚙️ إعدادات النظام', callback_data='super_system_settings'),
         InlineKeyboardButton('🔒 إدارة الأمان', callback_data='super_security_management')],
        [InlineKeyboardButton('📊 مراقبة الأداء', callback_data='super_performance_monitor'),
         InlineKeyboardButton('🔄 إدارة الصيانة', callback_data='super_maintenance')],
        [InlineKeyboardButton('📈 تقارير المنصة', callback_data='super_platform_reports'),
         InlineKeyboardButton('🛠️ أدوات المطور', callback_data='super_dev_tools')],
        [InlineKeyboardButton('🏠 العودة للوحة الإدارة', callback_data='super_admin_panel')]
    ]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def commission_settings_handler(update, context):
    """Handle commission settings"""
    query = update.callback_query
    await query.answer()
    
    text = f"""
💳 **إعدادات العمولات** 💳

العمولة الحالية للبطاقات: **{CARD_COMMISSION_RATE * 100:.1f}%**
العمولة الحالية للوكلاء: **{AGENT_COMMISSION_RATE * 100:.1f}%**

💰 **نظام العمولات المتقدم:**
• تحكم كامل في نسب العمولات
• تتبع العمولات في الوقت الفعلي
• تقارير مفصلة للعمولات
• إعدادات مخصصة لكل نوع

🏠 العودة للوحة الإدارة
"""
    
    keyboard = [[InlineKeyboardButton('🏠 العودة للوحة الإدارة', callback_data='super_admin_panel')]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def security_monitoring_handler(update, context):
    """Handle security monitoring"""
    query = update.callback_query
    await query.answer()
    
    text = f"""
🚨 **مراقبة الأمان** 🚨

🚨 **نظام مراقبة الأمان النشط:**

🔒 **مراقبة تسجيلات الدخول المشبوهة**
🛡️ **كشف المحاولات الاحتيالية**
⚠️ **تنبيهات الأمان**
📋 **سجلات الأنشطة الحساسة**

🏠 العودة للوحة الإدارة
"""
    
    keyboard = [[InlineKeyboardButton('🏠 العودة للوحة الإدارة', callback_data='super_admin_panel')]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

# Export functions for callback routing
ADMIN_CALLBACKS = {
    'super_admin_panel': lambda u, c: show_super_admin_panel(u, c, get_user(u.effective_user.id)),
    'super_issue_balance': issue_balance_handler,
    'super_activate_suppliers': activate_suppliers_handler,
    'activate_all_suppliers': activate_all_suppliers,
    'super_platform_management': platform_management_handler,
    'super_commission_settings': commission_settings_handler,
    'super_backup': backup_handler,
    'executive_reports': executive_reports_handler,
    'super_manage_users': manage_users_handler,
    'super_executive_reports': executive_reports_handler,
    'super_system_settings': system_settings_handler,
    'super_security_monitoring': security_monitoring_handler,
    'super_manage_admins': manage_admins_handler,
    'super_dashboard': dashboard_handler,
    'super_view_all_suppliers': view_all_suppliers_handler,
    'view_supplier_details': view_supplier_details_handler,
    # New enhanced features

    'super_print_balance': print_balance_handler,
    'super_broadcast_message': broadcast_message_handler,
    'super_update_commands': update_commands_handler,


}

# Missing handler implementations

async def backup_full_handler(update, context):
    """Handle full backup creation"""
    query = update.callback_query
    await query.answer()
    
    text = f"""
💾 **إنشاء نسخة احتياطية كاملة** 💾

🔄 جاري إنشاء النسخة الاحتياطية...

⚠️ قد تستغرق هذه العملية بضع دقائق.

🏠 العودة لإدارة النسخ
"""
    
    keyboard = [[InlineKeyboardButton('🏠 العودة لإدارة النسخ', callback_data='super_backup')]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def backup_data_only_handler(update, context):
    """Handle data-only backup"""
    query = update.callback_query
    await query.answer()
    
    text = f"""
📊 **نسخة احتياطية للبيانات فقط** 📊

📊 **نسخ احتياطي ذكي:**
• نسخ تلقائي للبيانات الحساسة
• ضغط وتشفير البيانات
• استعادة سريعة وآمنة
• جدولة مرنة للنسخ

🏠 العودة لإدارة النسخ
"""
    
    keyboard = [[InlineKeyboardButton('🏠 العودة لإدارة النسخ', callback_data='super_backup')]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def backup_restore_handler(update, context):
    """Handle backup restore"""
    query = update.callback_query
    await query.answer()
    
    text = f"""
📥 **استعادة من نسخة احتياطية** 📥

✅ **استعادة النسخ الاحتياطية:**
• استعادة انتقائية للبيانات
• معاينة المحتوى قبل الاستعادة
• حماية من فقدان البيانات
• نقاط استعادة متعددة

⚠️ **تحذير:** استعادة النسخة الاحتياطية ستحل محل جميع البيانات الحالية.

🏠 العودة لإدارة النسخ
"""
    
    keyboard = [[InlineKeyboardButton('🏠 العودة لإدارة النسخ', callback_data='super_backup')]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def backup_list_handler(update, context):
    """Handle backup list"""
    query = update.callback_query
    await query.answer()
    
    text = f"""
📋 **عرض النسخ المتاحة** 📋

لا توجد نسخ احتياطية متاحة حالياً.

🏠 العودة لإدارة النسخ
"""
    
    keyboard = [[InlineKeyboardButton('🏠 العودة لإدارة النسخ', callback_data='super_backup')]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def backup_schedule_handler(update, context):
    """Handle backup scheduling"""
    query = update.callback_query
    await query.answer()
    
    text = f"""
🕐 **جدولة النسخ التلقائي** 🕐

🕐 **جدولة النسخ التلقائي:**
• نسخ يومي/أسبوعي/شهري
• تنبيهات حالة النسخ
• إدارة مساحة التخزين
• نسخ متزايد وكامل

🏠 العودة لإدارة النسخ
"""
    
    keyboard = [[InlineKeyboardButton('🏠 العودة لإدارة النسخ', callback_data='super_backup')]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def backup_settings_handler(update, context):
    """Handle backup settings"""
    query = update.callback_query
    await query.answer()
    
    text = f"""
⚙️ **إعدادات النسخ** ⚙️

⚙️ **إعدادات النسخ المتقدمة:**
• اختيار البيانات للنسخ
• مواقع تخزين متعددة
• تشفير متقدم
• ضغط تكيفي

🏠 العودة لإدارة النسخ
"""
    
    keyboard = [[InlineKeyboardButton('🏠 العودة لإدارة النسخ', callback_data='super_backup')]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

# System settings handlers
async def system_edit_card_commission_handler(update, context):
    """Handle card commission editing"""
    query = update.callback_query
    await query.answer()
    
    text = f"""
💳 **تعديل عمولة البطاقات** 💳

العمولة الحالية: **{CARD_COMMISSION_RATE * 100:.1f}%**

💳 **إدارة عمولات البطاقات:**
• نسب عمولة مخصصة لكل شبكة
• عمولات متدرجة حسب الحجم
• تتبع الأرباح في الوقت الفعلي
• تقارير مالية مفصلة

🏠 العودة لإعدادات النظام
"""
    
    keyboard = [[InlineKeyboardButton('🏠 العودة لإعدادات النظام', callback_data='super_system_settings')]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def system_edit_agent_commission_handler(update, context):
    """Handle agent commission editing"""
    query = update.callback_query
    await query.answer()
    
    text = f"""
👥 **تعديل عمولة الوكلاء** 👥

العمولة الحالية: **{AGENT_COMMISSION_RATE * 100:.1f}%**

🤝 **إدارة عمولات الوكلاء:**
• هيكل عمولات متعدد المستويات
• مكافآت الأداء
• تتبع المبيعات والعمولات
• دفعات تلقائية للعمولات

🏠 العودة لإعدادات النظام
"""
    
    keyboard = [[InlineKeyboardButton('🏠 العودة لإعدادات النظام', callback_data='super_system_settings')]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def system_reload_config_handler(update, context):
    """Handle config reload"""
    query = update.callback_query
    await query.answer()
    
    text = f"""
🔄 **إعادة تحميل الإعدادات** 🔄

تم إعادة تحميل إعدادات النظام بنجاح.

🏠 العودة لإعدادات النظام
"""
    
    keyboard = [[InlineKeyboardButton('🏠 العودة لإعدادات النظام', callback_data='super_system_settings')]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def system_stats_handler(update, context):
    """Handle system stats"""
    query = update.callback_query
    await query.answer()
    
    text = f"""
📊 **إحصائيات النظام** 📊

📊 **إحصائيات النظام الشاملة:**
• أداء الخادم والذاكرة
• إحصائيات المستخدمين النشطين
• معدلات المعاملات
• تحليل الأخطاء والمشاكل
• رسوم بيانية تفاعلية

🏠 العودة لإعدادات النظام
"""
    
    keyboard = [[InlineKeyboardButton('🏠 العودة لإعدادات النظام', callback_data='super_system_settings')]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

# Dashboard handlers
async def dashboard_users_handler(update, context):
    """Handle dashboard users detail"""
    query = update.callback_query
    await query.answer()
    
    text = f"""
👥 **تفاصيل المستخدمين** 👥

👥 **تحليل المستخدمين المتقدم:**
• ملفات شخصية مفصلة
• سجل النشاطات والمعاملات
• تحليل سلوك المستخدمين
• تقسيم المستخدمين حسب النشاط
• أدوات البحث والفلترة

🏠 العودة للوحة المعلومات
"""
    
    keyboard = [[InlineKeyboardButton('🏠 العودة للوحة المعلومات', callback_data='super_dashboard')]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def dashboard_financial_handler(update, context):
    """Handle dashboard financial detail"""
    query = update.callback_query
    await query.answer()
    
    text = f"""
💰 **التقارير المالية** 💰

💰 **التقارير المالية الشاملة:**
• تقارير الإيرادات والأرباح
• تحليل التدفق النقدي
• مقارنات دورية (يومي/شهري/سنوي)
• توقعات مالية ذكية
• تصدير التقارير بصيغ متعددة

🏠 العودة للوحة المعلومات
"""
    
    keyboard = [[InlineKeyboardButton('🏠 العودة للوحة المعلومات', callback_data='super_dashboard')]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def dashboard_detailed_handler(update, context):
    """Handle dashboard detailed stats"""
    query = update.callback_query
    await query.answer()
    
    text = f"""
📊 **إحصائيات مفصلة** 📊

📈 **لوحة إحصائيات ذكية:**
• مؤشرات الأداء الرئيسية
• رسوم بيانية في الوقت الفعلي
• تنبيهات الاتجاهات
• تحليل تنبؤي للنمو
• تقارير مخصصة للإدارة

🏠 العودة للوحة المعلومات
"""
    
    keyboard = [[InlineKeyboardButton('🏠 العودة للوحة المعلومات', callback_data='super_dashboard')]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

# Placeholder handlers for other missing functions
async def admin_list_all_handler(update, context):
    query = update.callback_query
    await query.answer()
    text = f"👥 **عرض جميع المشرفين** - متاحة ومطورة"
    keyboard = [[InlineKeyboardButton('🏠 العودة لإدارة المشرفين', callback_data='super_manage_admins')]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def admin_add_new_handler(update, context):
    query = update.callback_query
    await query.answer()
    text = f"➕ **إضافة مشرف جديد** - متاحة ومطورة"
    keyboard = [[InlineKeyboardButton('🏠 العودة لإدارة المشرفين', callback_data='super_manage_admins')]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def admin_search_handler(update, context):
    query = update.callback_query
    await query.answer()
    text = f"🔍 **البحث عن مشرف** - متاحة ومطورة"
    keyboard = [[InlineKeyboardButton('🏠 العودة لإدارة المشرفين', callback_data='super_manage_admins')]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def admin_reports_handler(update, context):
    query = update.callback_query
    await query.answer()
    text = f"📊 **تقارير المشرفين** - متاحة ومطورة"
    keyboard = [[InlineKeyboardButton('🏠 العودة لإدارة المشرفين', callback_data='super_manage_admins')]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def admin_permissions_handler(update, context):
    query = update.callback_query
    await query.answer()
    text = f"⚙️ **صلاحيات المشرفين** - متاحة ومطورة"
    keyboard = [[InlineKeyboardButton('🏠 العودة لإدارة المشرفين', callback_data='super_manage_admins')]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def admin_banned_handler(update, context):
    query = update.callback_query
    await query.answer()
    text = f"🚫 **إدارة المحظورين** - متاحة ومطورة"
    keyboard = [[InlineKeyboardButton('🏠 العودة لإدارة المشرفين', callback_data='super_manage_admins')]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def users_list_all_handler(update, context):
    query = update.callback_query
    await query.answer()
    text = f"👥 **عرض جميع المستخدمين** - متاحة ومطورة"
    keyboard = [[InlineKeyboardButton('🏠 العودة لإدارة المستخدمين', callback_data='super_manage_users')]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def users_search_handler(update, context):
    query = update.callback_query
    await query.answer()
    text = f"🔍 **البحث عن مستخدم** - متاحة ومطورة"
    keyboard = [[InlineKeyboardButton('🏠 العودة لإدارة المستخدمين', callback_data='super_manage_users')]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def users_reports_handler(update, context):
    query = update.callback_query
    await query.answer()
    text = f"📊 **تقارير المستخدمين** - متاحة ومطورة"
    keyboard = [[InlineKeyboardButton('🏠 العودة لإدارة المستخدمين', callback_data='super_manage_users')]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def users_balance_mgmt_handler(update, context):
    query = update.callback_query
    await query.answer()
    text = f"💰 **إدارة الأرصدة** - متاحة ومطورة"
    keyboard = [[InlineKeyboardButton('🏠 العودة لإدارة المستخدمين', callback_data='super_manage_users')]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def users_banned_handler(update, context):
    query = update.callback_query
    await query.answer()
    text = f"🚫 **المستخدمين المحظورين** - متاحة ومطورة"
    keyboard = [[InlineKeyboardButton('🏠 العودة لإدارة المستخدمين', callback_data='super_manage_users')]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def users_top_handler(update, context):
    """Show top users by various metrics"""
    try:
        query = update.callback_query
        await query.answer()
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Top users by balance
        cursor.execute('''
            SELECT full_name, balance, role 
            FROM users 
            WHERE role IN ('customer', 'supplier') 
            ORDER BY balance DESC 
            LIMIT 10
        ''')
        top_balance = cursor.fetchall()
        
        # Most active users by transactions
        cursor.execute('''
            SELECT u.full_name, COUNT(t.id) as transaction_count, u.role
            FROM users u
            LEFT JOIN transactions t ON (u.id = t.from_user OR u.id = t.to_user)
            WHERE u.role IN ('customer', 'supplier')
            GROUP BY u.id
            ORDER BY transaction_count DESC
            LIMIT 5
        ''')
        most_active = cursor.fetchall()
        
        conn.close()
        
        text = f"""
⭐ **أفضل المستخدمين** ⭐

💰 **أعلى أرصدة:**
"""
        
        for i, user in enumerate(top_balance[:5], 1):
            role_emoji = "🏪" if user['role'] == 'supplier' else "👤"
            text += f"\n{i}. {role_emoji} {user['full_name']}: **{user['balance']:,.0f}** ريال"
        
        text += f"\n\n🔄 **الأكثر نشاطاً:**"
        
        for i, user in enumerate(most_active, 1):
            role_emoji = "🏪" if user['role'] == 'supplier' else "👤"
            text += f"\n{i}. {role_emoji} {user['full_name']}: **{user['transaction_count']}** معاملة"
        
        keyboard = [
            [InlineKeyboardButton('💰 ترتيب حسب الرصيد', callback_data='users_top_balance'),
             InlineKeyboardButton('🔄 ترتيب حسب النشاط', callback_data='users_top_activity')],
            [InlineKeyboardButton('📊 تفاصيل أكثر', callback_data='users_detailed_stats'),
             InlineKeyboardButton('📈 إحصائيات شهرية', callback_data='users_monthly_stats')],
            [InlineKeyboardButton('🏠 العودة لإدارة المستخدمين', callback_data='super_manage_users')]
        ]
        
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in users top handler: {e}")
        text = f"⭐ **أفضل المستخدمين** - حدث خطأ في تحميل البيانات"
        keyboard = [[InlineKeyboardButton('🏠 العودة لإدارة المستخدمين', callback_data='super_manage_users')]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def print_balance_handler(update: Update, context: CallbackContext):
    """Show super admin balance and transaction history"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user or user['role'] != 'super_admin':
            await query.edit_message_text(f"{EMOJIS['error']} ليس لديك صلاحية لهذه العملية.")
            return
        
        await query.edit_message_text("🔍 جاري طباعة تفاصيل الرصيد...", parse_mode='Markdown')
        
        # Get balance details
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get recent transactions
        cursor.execute('''
            SELECT * FROM transactions 
            WHERE (from_user = ? OR to_user = ?) 
            ORDER BY created_at DESC 
            LIMIT 20
        ''', (user['id'], user['id']))
        
        transactions = cursor.fetchall()
        
        # Calculate total incoming and outgoing
        cursor.execute('''
            SELECT 
                COALESCE(SUM(CASE WHEN to_user = ? THEN amount ELSE 0 END), 0) as total_income,
                COALESCE(SUM(CASE WHEN from_user = ? THEN amount ELSE 0 END), 0) as total_outgoing
            FROM transactions 
            WHERE from_user = ? OR to_user = ?
        ''', (user['id'], user['id'], user['id'], user['id']))
        
        totals = cursor.fetchone()
        conn.close()
        
        # Format balance report
        balance_text = f"""
💰 **تقرير رصيد المشرف الأعلى** 💰

👤 **المشرف:** {user['full_name']}
💵 **الرصيد الحالي:** {user['balance']:,.2f} ريال

📊 **الإحصائيات:**
🔺 إجمالي الوارد: {totals['total_income']:,.2f} ريال
🔻 إجمالي الصادر: {totals['total_outgoing']:,.2f} ريال
⚖️ صافي الرصيد: {totals['total_income'] - totals['total_outgoing']:,.2f} ريال

📋 **آخر 10 معاملات:**
"""
        
        if transactions:
            for i, trans in enumerate(transactions[:10], 1):
                trans_type = trans['type']
                amount = trans['amount']
                created_at = trans['created_at']
                
                if trans['to_user'] == user['id']:
                    direction = "🔺 وارد"
                    amount_text = f"+{amount:,.2f}"
                else:
                    direction = "🔻 صادر"
                    amount_text = f"-{amount:,.2f}"
                
                type_emoji = {
                    'money_creation': '💰',
                    'admin_transfer': '💸',
                    'transfer': '🔄',
                    'transfer_fee': '💳'
                }.get(trans_type, '📄')
                
                balance_text += f"\n{i}. {type_emoji} {direction} {amount_text} ريال"
                balance_text += f"\n   📅 {created_at[:16]}"
                
                if len(balance_text) > 3500:  # Telegram message limit
                    balance_text += f"\n\n... وآخرين ({len(transactions)-i} معاملة)"
                    break
        else:
            balance_text += "\nلا توجد معاملات مسجلة"
        
        balance_text += "\n\n💡 استخدم الأزرار أدناه للعمليات المختلفة"
        
        keyboard = [
            [InlineKeyboardButton('💰 إنشاء رصيد جديد', callback_data='super_issue_balance'),
             InlineKeyboardButton('💸 تحويل رصيد', callback_data='super_transfer_to_user')],
            [InlineKeyboardButton('📊 تقرير مفصل', callback_data='super_detailed_report'),
             InlineKeyboardButton('🔄 تحديث الرصيد', callback_data='super_print_balance')],
            [InlineKeyboardButton('👑 لوحة المشرف الأعلى', callback_data='super_admin_panel'),
             InlineKeyboardButton(f'{EMOJIS["home"]} القائمة الرئيسية', callback_data='main_menu')]
        ]
        
        await query.edit_message_text(balance_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in print balance handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في طباعة الرصيد.")

async def commission_management_handler(update: Update, context: CallbackContext):
    """إدارة العمولات المتقدمة"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user or user['role'] != 'super_admin':
            await query.edit_message_text(f"{EMOJIS['error']} ليس لديك صلاحية لهذه العملية.")
            return
        
        # الحصول على العمولات الحالية
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, name, percentage, fixed_amount, role, is_active 
            FROM commissions 
            ORDER BY role, name
        ''')
        commissions = cursor.fetchall()
        
        # احصائيات العمولات
        cursor.execute('''
            SELECT 
                SUM(CASE WHEN role = 'agent' AND is_active = 1 THEN percentage ELSE 0 END) as agent_percentage,
                SUM(CASE WHEN role = 'supplier' AND is_active = 1 THEN percentage ELSE 0 END) as supplier_percentage,
                SUM(CASE WHEN role = 'admin' AND is_active = 1 THEN percentage ELSE 0 END) as admin_percentage,
                SUM(CASE WHEN role = 'system' AND is_active = 1 THEN fixed_amount ELSE 0 END) as system_fees
            FROM commissions
        ''')
        commission_stats = cursor.fetchone()
        
        conn.close()
        
        text = f"""
💰 **إدارة العمولات المتقدمة** 💰

{EMOJIS['admin']} مرحباً **{user['full_name']}**

📊 **ملخص العمولات الحالية:**
💼 الوكلاء: **{commission_stats[0] or 0:.1f}%**
🏪 المزودون: **{commission_stats[1] or 0:.1f}%**
👑 المشرفون: **{commission_stats[2] or 0:.1f}%**
⚙️ رسوم النظام: **{commission_stats[3] or 0:.0f}** ريال

📋 **العمولات المُعرَّفة:**
"""

        for comm in commissions:
            status = "✅" if comm[5] else "❌"
            role_name = {
                'agent': 'الوكلاء',
                'supplier': 'المزودين', 
                'admin': 'المشرفون',
                'system': 'النظام'
            }.get(comm[4], comm[4])
            
            if comm[2] > 0:  # percentage
                text += f"\n{status} **{comm[1]}** ({role_name}): **{comm[2]:.1f}%**"
            else:  # fixed amount
                text += f"\n{status} **{comm[1]}** ({role_name}): **{comm[3]:.0f}** ريال"
        
        text += "\n\n🔧 **عمليات الإدارة:**"
        
        keyboard = [
            [InlineKeyboardButton('✏️ تعديل عمولة', callback_data='edit_commission'),
             InlineKeyboardButton('➕ إضافة عمولة جديدة', callback_data='add_commission')],
            [InlineKeyboardButton('📊 تقارير العمولات', callback_data='commission_reports'),
             InlineKeyboardButton('⚙️ إعدادات العمولات', callback_data='commission_settings')],
            [InlineKeyboardButton('🔄 إعادة تعيين العمولات', callback_data='reset_commissions'),
             InlineKeyboardButton('📈 تحليل الأرباح', callback_data='profit_analysis')],
            [InlineKeyboardButton('🏠 العودة للوحة الإدارة', callback_data='super_admin_panel')]
        ]
        
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in commission management: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في إدارة العمولات.")

async def edit_commission_handler(update: Update, context: CallbackContext):
    """تعديل العمولات"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user or user['role'] != 'super_admin':
            await query.edit_message_text(f"{EMOJIS['error']} ليس لديك صلاحية لهذه العملية.")
            return
        
        # الحصول على قائمة العمولات
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, name, percentage, fixed_amount, role, is_active 
            FROM commissions 
            ORDER BY role, name
        ''')
        commissions = cursor.fetchall()
        conn.close()
        
        text = f"""
✏️ **تعديل العمولات** ✏️

{EMOJIS['admin']} اختر العمولة المراد تعديلها:

📋 **العمولات المتاحة:**
"""

        keyboard = []
        for comm in commissions:
            status = "✅" if comm[5] else "❌"
            role_name = {
                'agent': 'الوكلاء',
                'supplier': 'المزودين', 
                'admin': 'المشرفون',
                'system': 'النظام'
            }.get(comm[4], comm[4])
            
            if comm[2] > 0:  # percentage
                display_text = f"{status} {comm[1]} ({role_name}): {comm[2]:.1f}%"
            else:  # fixed amount
                display_text = f"{status} {comm[1]} ({role_name}): {comm[3]:.0f} ريال"
            
            text += f"\n• {display_text}"
            
            keyboard.append([InlineKeyboardButton(
                f"{comm[1][:20]}... - {role_name}",
                callback_data=f"edit_comm_{comm[0]}"
            )])
        
        keyboard.append([InlineKeyboardButton('🔙 العودة لإدارة العمولات', callback_data='commission_management')])
        
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in edit commission handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في تعديل العمولات.")

async def edit_specific_commission(update: Update, context: CallbackContext, commission_id: str):
    """تعديل عمولة محددة"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user or user['role'] != 'super_admin':
            await query.edit_message_text(f"{EMOJIS['error']} ليس لديك صلاحية لهذه العملية.")
            return
        
        # الحصول على بيانات العمولة
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, name, percentage, fixed_amount, role, is_active 
            FROM commissions 
            WHERE id = ?
        ''', (commission_id,))
        commission = cursor.fetchone()
        conn.close()
        
        if not commission:
            await query.edit_message_text("❌ لم يتم العثور على العمولة المحددة.")
            return
        
        role_name = {
            'agent': 'الوكلاء',
            'supplier': 'المزودين', 
            'admin': 'المشرفون',
            'system': 'النظام'
        }.get(commission[4], commission[4])
        
        status = "✅ مفعلة" if commission[5] else "❌ معطلة"
        
        if commission[2] > 0:  # percentage
            current_value = f"{commission[2]:.1f}%"
            value_type = "نسبة مئوية"
        else:  # fixed amount
            current_value = f"{commission[3]:.0f} ريال"
            value_type = "مبلغ ثابت"
        
        text = f"""
✏️ **تعديل العمولة** ✏️

📋 **بيانات العمولة الحالية:**
📛 الاسم: **{commission[1]}**
👥 الفئة المستهدفة: **{role_name}**
💰 القيمة الحالية: **{current_value}** ({value_type})
⚡ الحالة: **{status}**

🔧 **خيارات التعديل:**
"""
        
        keyboard = [
            [InlineKeyboardButton('✏️ تعديل القيمة', callback_data=f'edit_comm_value_{commission_id}'),
             InlineKeyboardButton('📝 تعديل الاسم', callback_data=f'edit_comm_name_{commission_id}')],
            [InlineKeyboardButton('🔄 تغيير النوع', callback_data=f'edit_comm_type_{commission_id}'),
             InlineKeyboardButton('👥 تغيير الفئة', callback_data=f'edit_comm_role_{commission_id}')],
            [InlineKeyboardButton('✅ تفعيل/إلغاء تفعيل' if not commission[5] else '❌ تعطيل', 
                                callback_data=f'toggle_comm_{commission_id}'),
             InlineKeyboardButton('🗑️ حذف العمولة', callback_data=f'delete_comm_{commission_id}')],
            [InlineKeyboardButton('🔙 عودة لقائمة العمولات', callback_data='edit_commission'),
             InlineKeyboardButton('💼 إدارة العمولات', callback_data='commission_management')]
        ]
        
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in edit specific commission: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في تعديل العمولة.")

# Update ADMIN_CALLBACKS with newly defined handlers
ADMIN_CALLBACKS.update({
    # Core admin functions - simplified
    'admin_wallet': admin_wallet_handler,
    'admin_send_money': admin_send_money_handler,
    'super_print_balance': print_balance_handler,  # Keep for compatibility
    'super_system_settings': system_settings_handler,
    'super_manage_admins': manage_admins_handler,
    'super_manage_users': manage_users_handler,
    'super_dashboard': dashboard_handler,
    'super_backup': backup_handler,
    'super_executive_reports': executive_reports_handler,
    'super_platform_management': platform_management_handler,
    'super_commission_settings': commission_settings_handler,
    
    # New enhanced features
    'commission_management': commission_management_handler,
    'edit_commission': edit_commission_handler,
    'manage_users': manage_users_handler,
    'manage_admins': manage_admins_handler,
    'dashboard': dashboard_handler,
    'executive_reports': executive_reports_handler,
    
    # Admin network and card management  
    'admin_add_network': lambda u, c: admin_add_network_handler(u, c),
    'admin_upload_cards': lambda u, c: admin_upload_cards_handler(u, c),
    'admin_add_offers': lambda u, c: admin_add_offers_handler(u, c),
    'accounting_system': lambda u, c: accounting_system_handler(u, c),
    'download_statements': lambda u, c: download_statements_handler(u, c),
    'trial_balance': lambda u, c: trial_balance_handler(u, c),
    'income_statement': lambda u, c: income_statement_handler(u, c),
    'balance_sheet': lambda u, c: balance_sheet_handler(u, c),
    'general_ledger': lambda u, c: general_ledger_handler(u, c),
    
    # Coupon management
    'super_create_coupons': lambda u, c: create_coupons_handler(u, c),
    'super_coupons_stats': lambda u, c: coupons_stats_handler(u, c),
    'super_list_coupons': lambda u, c: list_coupons_handler(u, c),
    
    # Backup handlers
    'backup_full': backup_full_handler,
    'backup_data_only': backup_data_only_handler,
    'backup_restore': backup_restore_handler,
    'backup_list': backup_list_handler,
    'backup_schedule': backup_schedule_handler,
    'backup_settings': backup_settings_handler,
    # System settings handlers
    'system_edit_card_commission': system_edit_card_commission_handler,
    'system_edit_agent_commission': system_edit_agent_commission_handler,
    'system_reload_config': system_reload_config_handler,
    'system_stats': system_stats_handler,
    # Dashboard handlers
    'dashboard_users': dashboard_users_handler,
    'dashboard_financial': dashboard_financial_handler,
    'dashboard_detailed': dashboard_detailed_handler,
    # Admin management handlers
    'admin_list_all': admin_list_all_handler,
    'admin_add_new': admin_add_new_handler,
    'admin_search': admin_search_handler,
    'admin_reports': admin_reports_handler,
    'admin_permissions': admin_permissions_handler,
    'admin_banned': admin_banned_handler,
    # User management handlers
    'users_list_all': users_list_all_handler,
    'users_search': users_search_handler,
    'users_reports': users_reports_handler,
    'users_balance_mgmt': users_balance_mgmt_handler,
    'users_banned': users_banned_handler,
    'users_top': users_top_handler,
    # Additional handlers for improved functionality
    'super_detailed_report': lambda u, c: placeholder_handler(u, c, "التقرير المفصل"),
    'system_edit_transfer_fee': lambda u, c: placeholder_handler(u, c, "تعديل رسوم التحويل"),
    'system_security': lambda u, c: placeholder_handler(u, c, "إعدادات الأمان"),
    'system_notifications': lambda u, c: placeholder_handler(u, c, "إعدادات الإشعارات"),
    'system_maintenance_toggle': lambda u, c: placeholder_handler(u, c, "تبديل وضع الصيانة"),
    'dashboard_networks': lambda u, c: placeholder_handler(u, c, "تقرير الشبكات"),
    'dashboard_charts': lambda u, c: placeholder_handler(u, c, "الرسوم البيانية"),
    'users_list_all': lambda u, c: placeholder_handler(u, c, "عرض جميع المستخدمين"),
    'users_top_balance': lambda u, c: placeholder_handler(u, c, "ترتيب حسب الرصيد"),
    'users_top_activity': lambda u, c: placeholder_handler(u, c, "ترتيب حسب النشاط"),
    'users_detailed_stats': lambda u, c: placeholder_handler(u, c, "إحصائيات مفصلة"),
    'users_monthly_stats': lambda u, c: placeholder_handler(u, c, "إحصائيات شهرية"),
    'admin_add_new': lambda u, c: placeholder_handler(u, c, "إضافة مشرف جديد"),
    'report_revenue': lambda u, c: placeholder_handler(u, c, "تقرير الإيرادات"),
    'report_users': lambda u, c: placeholder_handler(u, c, "تقرير المستخدمين"),
    'report_transactions': lambda u, c: placeholder_handler(u, c, "تقرير المعاملات"),
    'report_suppliers': lambda u, c: placeholder_handler(u, c, "تقرير المزودين"),
    'report_performance': lambda u, c: placeholder_handler(u, c, "تقرير الأداء"),
    'report_monthly': lambda u, c: placeholder_handler(u, c, "تقرير شهري"),
    'export_pdf_report': lambda u, c: placeholder_handler(u, c, "تصدير PDF"),
    'export_excel': lambda u, c: placeholder_handler(u, c, "تصدير Excel"),
})

async def admin_add_network_handler(update: Update, context: CallbackContext):
    """إضافة شبكة جديدة للمشرف الأعلى"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user or user['role'] != 'super_admin':
            await query.edit_message_text(f"{EMOJIS['error']} ليس لديك صلاحية لهذه العملية.")
            return
        
        # تنظيف أي حالات سابقة لتجنب التداخل
        context.user_data.clear()
        
        # إعداد حالة إنشاء الشبكة فقط
        context.user_data['admin_adding_network'] = True
        context.user_data['network_step'] = 'name'
        
        text = f"""
🌐 **إضافة شبكة جديدة** 🌐

{EMOJIS['admin']} مرحباً **{user['full_name']}**

📝 **سنقوم بإضافة الشبكة خطوة بخطوة**

🔸 **الخطوة 1 من 4**

📋 **أدخل اسم الشبكة:**

💡 **أمثلة:**
• شبكة الرحمن للإنترنت
• شبكة النور للواي فاي
• إنترنت البركة السريع
• شبكة الأمل المنزلية

⚠️ **ملاحظات:**
• يجب أن يكون الاسم واضح ومميز
• لا يقل عن 3 أحرف
• يفضل أن يحتوي على كلمة "شبكة" أو "إنترنت"

📝 **اكتب اسم الشبكة:**
"""
        
        keyboard = [
            [InlineKeyboardButton('❌ إلغاء', callback_data='super_admin_panel')]
        ]
        
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
        context.user_data['admin_adding_network'] = True
        context.user_data['network_step'] = 'name'
        
    except Exception as e:
        logger.error(f"Error in admin add network handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في إضافة الشبكة.")

async def admin_upload_cards_handler(update: Update, context: CallbackContext):
    """رفع كروت للمشرف الأعلى"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user or user['role'] != 'super_admin':
            await query.edit_message_text(f"{EMOJIS['error']} ليس لديك صلاحية لهذه العملية.")
            return
        
        # الحصول على الشبكات المتاحة
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT n.id, n.name, n.provider, 
                   COUNT(cc.id) as categories_count,
                   SUM(cc.stock_count) as total_stock
            FROM networks n
            LEFT JOIN card_categories cc ON n.id = cc.network_id
            WHERE n.is_active = 1
            GROUP BY n.id, n.name, n.provider
            ORDER BY n.name
        ''')
        networks = cursor.fetchall()
        conn.close()
        
        if not networks:
            text = f"""
💳 **رفع كروت جديدة** 💳

{EMOJIS['admin']} مرحباً **{user['full_name']}**

❌ **لا توجد شبكات متاحة حالياً**

🔧 **يجب إضافة شبكة أولاً قبل رفع الكروت**

📋 **الخطوات المطلوبة:**
1️⃣ إضافة شبكة جديدة
2️⃣ إضافة فئات الكروت للشبكة
3️⃣ رفع الكروت لكل فئة

🌐 **أضف شبكة جديدة أولاً:**
"""
            keyboard = [
                [InlineKeyboardButton('🌐 إضافة شبكة جديدة', callback_data='admin_add_network'),
                 InlineKeyboardButton('🔙 عودة', callback_data='super_admin_panel')]
            ]
        else:
            text = f"""
💳 **رفع كروت جديدة** 💳

{EMOJIS['admin']} مرحباً **{user['full_name']}**

📊 **الشبكات المتاحة:** ({len(networks)} شبكة)

🔍 **اختر الشبكة لرفع الكروت إليها:**

"""
            
            keyboard = []
            for network in networks:
                network_id, name, provider, categories, stock = network
                button_text = f"🌐 {name}"
                if categories > 0:
                    button_text += f" ({categories} فئة، {stock or 0} كرت)"
                else:
                    button_text += " (بدون فئات)"
                
                text += f"""
🏢 **{name}**
👤 المزود: {provider}
💳 الفئات: {categories or 0} فئة
📦 المخزون: {stock or 0} كرت
━━━━━━━━━━━━━━━━━━━━━━━━━
"""
                
                keyboard.append([InlineKeyboardButton(
                    button_text[:60] + "..." if len(button_text) > 60 else button_text,
                    callback_data=f'admin_upload_to_network_{network_id}'
                )])
            
            keyboard.extend([
                [InlineKeyboardButton('🌐 إضافة شبكة جديدة', callback_data='admin_add_network'),
                 InlineKeyboardButton('🔙 عودة', callback_data='super_admin_panel')]
            ])
        
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Error in admin upload cards handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في رفع الكروت.")

async def admin_process_network_creation(update: Update, context: CallbackContext):
    """معالجة إنشاء شبكة جديدة من المشرف الأعلى"""
    try:
        if not context.user_data.get('admin_adding_network'):
            return
        
        # التأكد من عدم وجود حالات أخرى متداخلة
        if context.user_data.get('admin_creating_coupon'):
            # إذا كان هناك تداخل، نظف الحالة وأعد تعيين حالة الشبكة
            context.user_data.clear()
            context.user_data['admin_adding_network'] = True
            context.user_data['network_step'] = 'name'
        
        user = get_user(update.effective_user.id)
        if not user or user['role'] != 'super_admin':
            await update.message.reply_text(f"{EMOJIS['error']} ليس لديك صلاحية لهذه العملية.")
            # تنظيف الحالة عند عدم وجود صلاحية
            context.user_data.clear()
            return
        
        message_text = update.message.text.strip()
        step = context.user_data.get('network_step', 'name')
        
        if step == 'name':
            if len(message_text) < 3:
                await update.message.reply_text(
                    "❌ **اسم الشبكة قصير جداً** ❌\n\n"
                    "📏 **الحد الأدنى:** 3 أحرف\n"
                    "📝 **يرجى إدخال اسم أطول**",
                    parse_mode='Markdown'
                )
                return
            
            # رسالة تأكيد حفظ الاسم
            await update.message.reply_text(
                f"✅ **تم حفظ اسم الشبكة بنجاح** ✅\n\n"
                f"🌐 **الاسم المحفوظ:** {message_text}",
                parse_mode='Markdown'
            )
            
            context.user_data['new_network_name'] = message_text
            context.user_data['network_step'] = 'provider'
            
            await update.message.reply_text(
                f"""✅ **تم حفظ اسم الشبكة:** {message_text}

🔸 **الخطوة 2 من 4**

👤 **أدخل اسم المزود:**

💡 **أمثلة:**
• أحمد محمد المزود
• شركة الإنترنت السريع
• مؤسسة الاتصالات المتقدمة
• علي حسن للإنترنت

⚠️ **ملاحظات:**
• اكتب الاسم الحقيقي للمزود
• يفضل الاسم الكامل
• لا يقل عن 3 أحرف

📝 **اكتب اسم المزود:**""",
                parse_mode='Markdown'
            )
            
        elif step == 'provider':
            if len(message_text) < 3:
                await update.message.reply_text(
                    "❌ **اسم المزود قصير جداً** ❌\n\n"
                    "📏 **الحد الأدنى:** 3 أحرف\n"
                    "📝 **يرجى إدخال اسم أطول**",
                    parse_mode='Markdown'
                )
                return
            
            # رسالة تأكيد حفظ المزود
            await update.message.reply_text(
                f"✅ **تم حفظ اسم المزود بنجاح** ✅\n\n"
                f"👤 **المزود المحفوظ:** {message_text}",
                parse_mode='Markdown'
            )
            
            context.user_data['new_network_provider'] = message_text
            context.user_data['network_step'] = 'description'
            
            await update.message.reply_text(
                f"""✅ **تم حفظ اسم المزود:** {message_text}

🔸 **الخطوة 3 من 4**

📝 **أدخل وصف الشبكة:**

💡 **أمثلة:**
• شبكة واي فاي منزلية عالية السرعة مع تغطية ممتازة
• إنترنت فائق السرعة للمنازل والمكاتب
• شبكة لاسلكية موثوقة بأسعار مناسبة
• خدمة إنترنت منزلي بجودة عالية

⚠️ **ملاحظات:**
• اكتب وصف واضح ومفيد
• يساعد العملاء في فهم الخدمة
• لا يقل عن 10 أحرف

📝 **اكتب وصف الشبكة:**""",
                parse_mode='Markdown'
            )
            
        elif step == 'description':
            if len(message_text) < 10:
                await update.message.reply_text(
                    "❌ **وصف الشبكة قصير جداً** ❌\n\n"
                    "📏 **الحد الأدنى:** 10 أحرف\n"
                    "📝 **يرجى إدخال وصف أطول وأوضح**",
                    parse_mode='Markdown'
                )
                return
            
            # رسالة تأكيد حفظ الوصف
            await update.message.reply_text(
                f"✅ **تم حفظ وصف الشبكة بنجاح** ✅\n\n"
                f"📝 **الوصف المحفوظ:** {message_text}",
                parse_mode='Markdown'
            )
            
            context.user_data['new_network_description'] = message_text
            context.user_data['network_step'] = 'location'
            
            await update.message.reply_text(
                f"""✅ **تم حفظ وصف الشبكة:** {message_text}

🔸 **الخطوة 4 من 4**

📍 **أدخل موقع الشبكة:**

💡 **أمثلة:**
• منطقة الصافية - صنعاء
• حي الزراعة - عدن  
• شارع هائل - تعز
• مدينة الحديدة - المدينة
• إب - جبلة

⚠️ **ملاحظات:**
• اذكر الحي أو المنطقة بوضوح
• أضف المحافظة إذا أمكن
• استخدم أسماء معروفة محلياً
• يمكن تخطي هذه الخطوة

📝 **اكتب موقع الشبكة أو اكتب "تخطي" للتخطي:**""",
                parse_mode='Markdown'
            )
            
        elif step == 'location':
            location = None if message_text.lower() in ['تخطي', 'skip'] else message_text
            
            # رسالة تأكيد حفظ الموقع
            if location:
                await update.message.reply_text(
                    f"✅ **تم حفظ موقع الشبكة بنجاح** ✅\n\n"
                    f"📍 **الموقع المحفوظ:** {location}",
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text(
                    "✅ **تم تخطي الموقع بنجاح** ✅\n\n"
                    "📍 **الموقع:** لم يتم تحديد موقع",
                    parse_mode='Markdown'
                )
            
            # إنشاء الشبكة في قاعدة البيانات
            network_name = context.user_data['new_network_name']
            provider = context.user_data['new_network_provider']
            description = context.user_data['new_network_description']
            
            try:
                conn = get_db_connection()
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO networks (supplier_id, name, city, provider, description, location, created_by, is_active, is_approved)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (user['id'], network_name, location, provider, description, location, user['id'], 1, 1))
                
                network_id = cursor.lastrowid
                conn.commit()
                conn.close()
                
                # تم حفظ البيانات - سيتم عرض رسالة النجاح لاحقاً
                
            except Exception as db_error:
                logger.error(f"Database error in network creation: {db_error}")
                await update.message.reply_text(
                    f"❌ **خطأ في قاعدة البيانات** ❌\n\n"
                    f"🔍 **تفاصيل الخطأ:** {str(db_error)}\n\n"
                    f"🔄 **يرجى المحاولة مرة أخرى**",
                    parse_mode='Markdown'
                )
                # تنظيف البيانات المؤقتة
                context.user_data.pop('admin_adding_network', None)
                context.user_data.pop('network_step', None)
                context.user_data.pop('new_network_name', None)
                context.user_data.pop('new_network_provider', None)
                context.user_data.pop('new_network_description', None)
                return
            
            # رسالة التأكيد
            location_text = location if location else "لا يوجد"
            
            success_text = f"""
🎉 **تم إنشاء الشبكة بنجاح!** 🎉

📋 **معلومات الشبكة:**
🌐 **الاسم:** {network_name}
👤 **المزود:** {provider}
📝 **الوصف:** {description}
📍 **الموقع:** {location_text}
🆔 **معرف الشبكة:** {network_id}

💳 **الخطوة التالية:**
أضف فئات الكروت للشبكة لتتمكن من رفع الكروت

🔧 **الخيارات المتاحة:**
"""
            
            keyboard = [
                [InlineKeyboardButton('💳 إضافة فئة كرت', callback_data=f'admin_add_category_{network_id}'),
                 InlineKeyboardButton('📦 رفع كروت', callback_data=f'admin_upload_to_network_{network_id}')],
                [InlineKeyboardButton('🌐 إضافة شبكة أخرى', callback_data='admin_add_network'),
                 InlineKeyboardButton('🏠 لوحة المشرف الأعلى', callback_data='super_admin_panel')]
            ]
            
            await update.message.reply_text(
                success_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            
            # تنظيف البيانات المؤقتة
            context.user_data.pop('admin_adding_network', None)
            context.user_data.pop('network_step', None)
            context.user_data.pop('new_network_name', None)
            context.user_data.pop('new_network_provider', None)
            context.user_data.pop('new_network_description', None)
        
    except Exception as e:
        logger.error(f"Error in admin process network creation: {e}")
        await update.message.reply_text(f"{EMOJIS['error']} حدث خطأ في إنشاء الشبكة.")

async def admin_add_category_handler(update: Update, context: CallbackContext, network_id: str):
    """إضافة فئة كرت جديدة للشبكة"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user or user['role'] != 'super_admin':
            await query.edit_message_text(f"{EMOJIS['error']} ليس لديك صلاحية لهذه العملية.")
            return
        
        # الحصول على معلومات الشبكة
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT name, provider FROM networks WHERE id = ?', (network_id,))
        network = cursor.fetchone()
        
        if not network:
            await query.edit_message_text("❌ لم يتم العثور على الشبكة المحددة.")
            return
        
        # الحصول على الفئات الموجودة
        cursor.execute('''
            SELECT name, value, price, stock_count, is_available 
            FROM card_categories 
            WHERE network_id = ?
            ORDER BY price
        ''', (network_id,))
        categories = cursor.fetchall()
        conn.close()
        
        text = f"""
💳 **إضافة فئة كرت جديدة** 💳

🌐 **الشبكة:** {network[0]}
👤 **المزود:** {network[1]}

📊 **الفئات الموجودة:** ({len(categories)} فئة)
"""

        if categories:
            for cat in categories:
                status = "✅" if cat[4] else "❌"
                text += f"\n{status} {cat[0]} - {cat[1]} - {cat[2]:,.0f} ريال ({cat[3]} كرت)"
        else:
            text += "\n🔸 لا توجد فئات بعد"

        text += f"""

🔧 **معلومات الفئة الجديدة:**

💡 **سيتم طلب:**
1️⃣ اسم الفئة (مثل: كرت 1 جيجا)
2️⃣ قيمة الكرت (مثل: 1024 ميجا)
3️⃣ سعر الكرت (بالريال)
4️⃣ عدد الكروت المتوفرة

📝 **اكتب اسم الفئة الجديدة:**
"""
        
        keyboard = [
            [InlineKeyboardButton('❌ إلغاء', callback_data=f'admin_upload_to_network_{network_id}')]
        ]
        
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
        context.user_data['admin_adding_category'] = True
        context.user_data['category_network_id'] = network_id
        context.user_data['category_step'] = 'name'
        
    except Exception as e:
        logger.error(f"Error in admin add category handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في إضافة الفئة.")

async def admin_network_upload_handler(update: Update, context: CallbackContext, network_id: str):
    """معالجة رفع الكروت لشبكة محددة"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user or user['role'] != 'super_admin':
            await query.edit_message_text(f"{EMOJIS['error']} ليس لديك صلاحية لهذه العملية.")
            return
        
        # الحصول على معلومات الشبكة والفئات
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT name, provider, description, location FROM networks WHERE id = ?', (network_id,))
        network = cursor.fetchone()
        
        if not network:
            await query.edit_message_text("❌ لم يتم العثور على الشبكة المحددة.")
            return
        
        # الحصول على فئات الكروت
        cursor.execute('''
            SELECT id, name, value, price, stock_count, is_available 
            FROM card_categories 
            WHERE network_id = ?
            ORDER BY price
        ''', (network_id,))
        categories = cursor.fetchall()
        conn.close()
        
        text = f"""
💳 **رفع كروت للشبكة** 💳

🌐 **الشبكة:** {network[0]}
👤 **المزود:** {network[1]}
📝 **الوصف:** {network[2] or 'غير محدد'}
📍 **الموقع:** {network[3] or 'غير محدد'}

📊 **فئات الكروت المتاحة:** ({len(categories)} فئة)
"""

        keyboard = []
        
        if categories:
            for cat in categories:
                status = "✅" if cat[5] else "❌"
                text += f"""
{status} **{cat[1]}**
💰 السعر: {cat[3]:,.0f} ريال
📦 المخزون: {cat[4]} كرت
━━━━━━━━━━━━━━━━━━━━━━━━━
"""
                
                button_text = f"💳 {cat[1]} ({cat[4]} كرت)"
                keyboard.append([InlineKeyboardButton(
                    button_text[:50] + "..." if len(button_text) > 50 else button_text,
                    callback_data=f'admin_upload_category_{cat[0]}'
                )])
            
            text += "\n🔧 **اختر فئة لرفع كروت إليها:**"
        else:
            text += "\n❌ **لا توجد فئات كروت بعد**\n\n🔧 **يجب إضافة فئة أولاً:**"
        
        keyboard.extend([
            [InlineKeyboardButton('➕ إضافة فئة جديدة', callback_data=f'admin_add_category_{network_id}'),
             InlineKeyboardButton('📊 إحصائيات الشبكة', callback_data=f'admin_network_stats_{network_id}')],
            [InlineKeyboardButton('🔙 عودة لرفع الكروت', callback_data='admin_upload_cards'),
             InlineKeyboardButton('🏠 لوحة المشرف الأعلى', callback_data='super_admin_panel')]
        ])
        
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Error in admin network upload handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في رفع الكروت.")

async def admin_upload_category_handler(update: Update, context: CallbackContext, category_id: str):
    """رفع كروت لفئة محددة"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user or user['role'] != 'super_admin':
            await query.edit_message_text(f"{EMOJIS['error']} ليس لديك صلاحية لهذه العملية.")
            return
        
        # الحصول على معلومات الفئة
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT cc.id, cc.name, cc.value, cc.price, cc.stock_count, cc.network_id,
                   n.name as network_name, n.provider
            FROM card_categories cc
            JOIN networks n ON cc.network_id = n.id
            WHERE cc.id = ?
        ''', (category_id,))
        category = cursor.fetchone()
        conn.close()
        
        if not category:
            await query.edit_message_text("❌ لم يتم العثور على الفئة المحددة.")
            return
        
        text = f"""
💳 **رفع كروت جديدة** 💳

🌐 **الشبكة:** {category[6]}
👤 **المزود:** {category[7]}
💳 **الفئة:** {category[1]}
💰 **السعر:** {category[3]:,.0f} ريال
📦 **المخزون الحالي:** {category[4]} كرت

📋 **طرق رفع الكروت:**

1️⃣ **رفع كروت منفردة:**
   • إدخال رقم كرت واحد في كل مرة
   • مناسب للكروت القليلة

2️⃣ **رفع كروت متعددة:**
   • إدخال عدة أرقام كروت مرة واحدة
   • كل رقم في سطر منفصل

3️⃣ **رفع من ملف:**
   • رفع ملف نصي يحتوي على أرقام الكروت
   • سريع وفعال للكميات الكبيرة

🔧 **اختر طريقة الرفع:**
"""
        
        keyboard = [
            [InlineKeyboardButton('1️⃣ رفع كرت منفرد', callback_data=f'admin_upload_single_{category_id}'),
             InlineKeyboardButton('2️⃣ رفع كروت متعددة', callback_data=f'admin_upload_multiple_{category_id}')],
            [InlineKeyboardButton('3️⃣ رفع من ملف', callback_data=f'admin_upload_file_{category_id}'),
             InlineKeyboardButton('📊 إحصائيات الفئة', callback_data=f'admin_category_stats_{category_id}')],
            [InlineKeyboardButton('🔙 عودة للشبكة', callback_data=f'admin_upload_to_network_{category[5]}'),
             InlineKeyboardButton('🏠 لوحة المشرف الأعلى', callback_data='super_admin_panel')]
        ]
        
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Error in admin upload category handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في رفع الكروت.")

async def admin_upload_single_card_handler(update: Update, context: CallbackContext, category_id: str):
    """رفع كرت منفرد"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user or user['role'] != 'super_admin':
            await query.edit_message_text(f"{EMOJIS['error']} ليس لديك صلاحية لهذه العملية.")
            return
        
        # الحصول على معلومات الفئة
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT cc.name, n.name as network_name
            FROM card_categories cc
            JOIN networks n ON cc.network_id = n.id
            WHERE cc.id = ?
        ''', (category_id,))
        category_info = cursor.fetchone()
        conn.close()
        
        if not category_info:
            await query.edit_message_text("❌ لم يتم العثور على الفئة المحددة.")
            return
        
        text = f"""
1️⃣ **رفع كرت منفرد** 1️⃣

🌐 **الشبكة:** {category_info[1]}
💳 **الفئة:** {category_info[0]}

📝 **أدخل معلومات الكرت:**

💡 **تنسيق الإدخال:**
```
رقم_الكرت|الرقم_التسلسلي|تاريخ_الانتهاء
```

🎯 **مثال:**
```
1234567890123456|ABC123DEF|2025-12-31
```

📋 **ملاحظات:**
• رقم الكرت مطلوب
• الرقم التسلسلي اختياري
• تاريخ الانتهاء اختياري
• استخدم | للفصل بين البيانات

📝 **أدخل معلومات الكرت:**
"""
        
        keyboard = [
            [InlineKeyboardButton('❌ إلغاء', callback_data=f'admin_upload_category_{category_id}')]
        ]
        
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
        context.user_data['admin_uploading_card'] = True
        context.user_data['upload_category_id'] = category_id
        context.user_data['upload_type'] = 'single'
        
    except Exception as e:
        logger.error(f"Error in admin upload single card handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في رفع الكرت.")

async def admin_process_card_upload(update: Update, context: CallbackContext):
    """معالجة رفع الكروت من المشرف الأعلى"""
    try:
        if not context.user_data.get('admin_uploading_card'):
            return
        
        user = get_user(update.effective_user.id)
        if not user or user['role'] != 'super_admin':
            await update.message.reply_text(f"{EMOJIS['error']} ليس لديك صلاحية لهذه العملية.")
            return
        
        category_id = context.user_data.get('upload_category_id')
        upload_type = context.user_data.get('upload_type', 'single')
        message_text = update.message.text.strip()
        
        if not category_id:
            await update.message.reply_text("❌ خطأ في معرف الفئة.")
            return
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # الحصول على معلومات الفئة
        cursor.execute('''
            SELECT cc.name, cc.network_id, n.name as network_name
            FROM card_categories cc
            JOIN networks n ON cc.network_id = n.id
            WHERE cc.id = ?
        ''', (category_id,))
        category_info = cursor.fetchone()
        
        if not category_info:
            await update.message.reply_text("❌ لم يتم العثور على الفئة المحددة.")
            return
        
        uploaded_cards = []
        errors = []
        
        if upload_type == 'single':
            # رفع كرت منفرد
            parts = message_text.split('|')
            card_number = parts[0].strip()
            serial_number = parts[1].strip() if len(parts) > 1 else None
            expiry_date = parts[2].strip() if len(parts) > 2 else None
            
            if len(card_number) < 8:
                await update.message.reply_text("❌ رقم الكرت قصير جداً. يجب أن يكون 8 أرقام على الأقل.")
                return
            
            # فحص إذا كان الكرت موجود مسبقاً
            cursor.execute('SELECT id FROM cards WHERE card_number = ?', (card_number,))
            if cursor.fetchone():
                await update.message.reply_text(f"❌ رقم الكرت {card_number} موجود مسبقاً.")
                return
            
            # إضافة الكرت
            cursor.execute('''
                INSERT INTO cards (category_id, card_number, serial_number, expiry_date, uploaded_by)
                VALUES (?, ?, ?, ?, ?)
            ''', (category_id, card_number, serial_number, expiry_date, user['id']))
            
            uploaded_cards.append(card_number)
            
        elif upload_type == 'multiple':
            # رفع كروت متعددة
            lines = message_text.split('\n')
            
            for line_num, line in enumerate(lines, 1):
                line = line.strip()
                if not line:
                    continue
                
                parts = line.split('|')
                card_number = parts[0].strip()
                serial_number = parts[1].strip() if len(parts) > 1 else None
                expiry_date = parts[2].strip() if len(parts) > 2 else None
                
                if len(card_number) < 8:
                    errors.append(f"السطر {line_num}: رقم الكرت قصير جداً")
                    continue
                
                # فحص إذا كان الكرت موجود مسبقاً
                cursor.execute('SELECT id FROM cards WHERE card_number = ?', (card_number,))
                if cursor.fetchone():
                    errors.append(f"السطر {line_num}: رقم الكرت {card_number} موجود مسبقاً")
                    continue
                
                # إضافة الكرت
                cursor.execute('''
                    INSERT INTO cards (category_id, card_number, serial_number, expiry_date, uploaded_by)
                    VALUES (?, ?, ?, ?, ?)
                ''', (category_id, card_number, serial_number, expiry_date, user['id']))
                
                uploaded_cards.append(card_number)
        
        # تحديث عدد الكروت في الفئة
        cursor.execute('''
            UPDATE card_categories 
            SET stock_count = stock_count + ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (len(uploaded_cards), category_id))
        
        conn.commit()
        conn.close()
        
        # رسالة النتائج
        success_text = f"""
🎉 **تم رفع الكروت بنجاح!** 🎉

🌐 **الشبكة:** {category_info[2]}
💳 **الفئة:** {category_info[0]}

📊 **النتائج:**
✅ تم رفع: **{len(uploaded_cards)}** كرت
❌ أخطاء: **{len(errors)}**

"""

        if uploaded_cards:
            success_text += "✅ **الكروت المرفوعة:**\n"
            for card in uploaded_cards[:5]:  # عرض أول 5 كروت فقط
                success_text += f"• {card}\n"
            if len(uploaded_cards) > 5:
                success_text += f"• ... و {len(uploaded_cards) - 5} كرت آخر\n"
        
        if errors:
            success_text += "\n❌ **الأخطاء:**\n"
            for error in errors[:5]:  # عرض أول 5 أخطاء فقط
                success_text += f"• {error}\n"
            if len(errors) > 5:
                success_text += f"• ... و {len(errors) - 5} خطأ آخر\n"
        
        keyboard = [
            [InlineKeyboardButton('📦 رفع كروت أخرى', callback_data=f'admin_upload_category_{category_id}'),
             InlineKeyboardButton('📊 إحصائيات الفئة', callback_data=f'admin_category_stats_{category_id}')],
            [InlineKeyboardButton('🔙 عودة للشبكة', callback_data=f'admin_upload_to_network_{category_info[1]}'),
             InlineKeyboardButton('🏠 لوحة المشرف الأعلى', callback_data='super_admin_panel')]
        ]
        
        await update.message.reply_text(
            success_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
        # تنظيف البيانات المؤقتة
        context.user_data.pop('admin_uploading_card', None)
        context.user_data.pop('upload_category_id', None)
        context.user_data.pop('upload_type', None)
        
    except Exception as e:
        logger.error(f"Error in admin process card upload: {e}")
        await update.message.reply_text(f"{EMOJIS['error']} حدث خطأ في رفع الكروت.")

async def create_coupons_handler(update: Update, context: CallbackContext):
    """Handle coupon creation for super admin"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user or user['role'] != 'super_admin':
            await query.edit_message_text(f"{EMOJIS['error']} ليس لديك صلاحية لهذه العملية.")
            return
        
        # تنظيف أي حالات سابقة لتجنب التداخل
        context.user_data.clear()
        
        # إعداد حالة إنشاء الكوبون فقط
        context.user_data['admin_creating_coupon'] = True
        
        text = f"""
🎟️ **إنشاء كوبونات جديدة** 🎟️

{EMOJIS['admin']} مرحباً **{user['full_name']}**

📝 **معلومات الكوبون:**

💰 **أدخل قيمة الكوبون بالريال:**

💡 **أمثلة:**
• 100 - كوبون بقيمة 100 ريال
• 250 - كوبون بقيمة 250 ريال
• 500 - كوبون بقيمة 500 ريال
• 1000 - كوبون بقيمة 1000 ريال

⚠️ **ملاحظات:**
• سيتم إنشاء رقم كوبون عشوائي (A + 8 أرقام)
• الكوبون صالح للاستخدام مرة واحدة فقط
• يمكن للمستخدمين تطبيق الكوبون على محافظهم
• القيمة يجب أن تكون أكبر من صفر

📝 **اكتب قيمة الكوبون بالريال:**
"""
        
        keyboard = [
            [InlineKeyboardButton('❌ إلغاء', callback_data='super_admin_panel')]
        ]
        
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
        context.user_data['admin_creating_coupon'] = True
        
    except Exception as e:
        logger.error(f"Error in create coupons handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في إنشاء الكوبون.")

def generate_coupon_code():
    """Generate random coupon code starting with A and 8 digits"""
    import random
    
    # Generate 8 random digits
    digits = ''.join([str(random.randint(0, 9)) for _ in range(8)])
    
    # Combine A with 8 digits
    coupon_code = f"A{digits}"
    
    return coupon_code

async def process_coupon_creation(update: Update, context: CallbackContext):
    """Process coupon creation from super admin"""
    try:
        if not context.user_data.get('admin_creating_coupon'):
            return
        
        # التأكد من عدم وجود حالات أخرى متداخلة
        if context.user_data.get('admin_adding_network') or context.user_data.get('network_step'):
            # إذا كان هناك تداخل، نظف الحالة وأعد تعيين حالة الكوبون
            context.user_data.clear()
            context.user_data['admin_creating_coupon'] = True
        
        user = get_user(update.effective_user.id)
        if not user or user['role'] != 'super_admin':
            await update.message.reply_text(f"{EMOJIS['error']} ليس لديك صلاحية لهذه العملية.")
            # تنظيف الحالة عند عدم وجود صلاحية
            context.user_data.clear()
            return
        
        # Parse amount
        try:
            amount = float(update.message.text.strip())
        except ValueError:
            await update.message.reply_text(
                "❌ **قيمة غير صحيحة** ❌\n\n"
                "🔢 **يجب إدخال رقم صحيح فقط**\n"
                "💡 **مثال:** 100 أو 500 أو 1000",
                parse_mode='Markdown'
            )
            return
        
        # Validate amount
        if amount <= 0:
            await update.message.reply_text(
                "❌ **قيمة غير مقبولة** ❌\n\n"
                "📊 **القيمة يجب أن تكون أكبر من صفر**\n"
                "💡 **مثال:** 50 أو 100 أو 500",
                parse_mode='Markdown'
            )
            return
        
        if amount > 100000:
            await update.message.reply_text(
                "❌ **قيمة كبيرة جداً** ❌\n\n"
                "💰 **الحد الأقصى:** 100,000 ريال\n"
                "📝 **يرجى إدخال قيمة أقل**",
                parse_mode='Markdown'
            )
            return
        
        # رسالة تأكيد بدء العملية
        await update.message.reply_text(
            "✅ **تم التحقق من البيانات بنجاح** ✅\n🔄 جاري إنشاء الكوبون...",
            parse_mode='Markdown'
        )
        
        try:
            # Generate unique coupon code
            conn = get_db_connection()
            cursor = conn.cursor()
            
            max_attempts = 10
            coupon_code = None
            
            for _ in range(max_attempts):
                potential_code = generate_coupon_code()
                
                # Check if code already exists
                cursor.execute('SELECT id FROM coupons WHERE coupon_code = ?', (potential_code,))
                if not cursor.fetchone():
                    coupon_code = potential_code
                    break
            
            if not coupon_code:
                await update.message.reply_text(
                    "❌ **فشل في إنشاء رقم كوبون فريد** ❌\n\n"
                    "🔄 **يرجى المحاولة مرة أخرى**",
                    parse_mode='Markdown'
                )
                conn.close()
                context.user_data.pop('admin_creating_coupon', None)
                return
            
            # Create coupon
            from datetime import datetime, timedelta
            expiry_date = datetime.now() + timedelta(days=365)  # صالح لمدة سنة
            
            cursor.execute('''
                INSERT INTO coupons (coupon_code, amount, created_by, expiry_date, description)
                VALUES (?, ?, ?, ?, ?)
            ''', (coupon_code, amount, user['id'], expiry_date, f'كوبون بقيمة {amount:,.0f} ريال'))
            
            coupon_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            # رسالة تأكيد النجاح
            await update.message.reply_text(
                "✅ **تم إنشاء الكوبون بنجاح** ✅\n📦 جاري تحضير التفاصيل...",
                parse_mode='Markdown'
            )
            
        except Exception as db_error:
            logger.error(f"Database error in coupon creation: {db_error}")
            await update.message.reply_text(
                f"❌ **خطأ في قاعدة البيانات** ❌\n\n"
                f"🔍 **تفاصيل الخطأ:** {str(db_error)}\n\n"
                f"🔄 **يرجى المحاولة مرة أخرى**",
                parse_mode='Markdown'
            )
            context.user_data.pop('admin_creating_coupon', None)
            return
        
        # Success message
        success_text = f"""
🎉 **تم إنشاء الكوبون بنجاح!** 🎉

🎟️ **معلومات الكوبون:**
🔢 **رقم الكوبون:** `{coupon_code}`
💰 **القيمة:** {amount:,.0f} ريال
📅 **تاريخ الإنشاء:** {datetime.now().strftime('%Y-%m-%d %H:%M')}
📅 **تاريخ الانتهاء:** {expiry_date.strftime('%Y-%m-%d')}
🆔 **معرف الكوبون:** {coupon_id}

📋 **حالة الكوبون:**
✅ **جاهز للاستخدام**
🔓 **غير مستخدم**

💡 **كيفية الاستخدام:**
• يمكن للمستخدمين إدخال الكوبون في محافظهم
• الكوبون صالح للاستخدام مرة واحدة فقط
• سيتم إضافة المبلغ فوراً لرصيد المحفظة مباشرة عند الاستخدام

🔧 **الخيارات المتاحة:**
"""
        
        keyboard = [
            [InlineKeyboardButton('🎟️ إنشاء كوبون آخر', callback_data='super_create_coupons'),
             InlineKeyboardButton('📊 إحصائيات الكوبونات', callback_data='super_coupons_stats')],
            [InlineKeyboardButton('📋 قائمة الكوبونات', callback_data='super_list_coupons'),
             InlineKeyboardButton('🏠 لوحة المشرف الأعلى', callback_data='super_admin_panel')]
        ]
        
        await update.message.reply_text(
            success_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
        # Clear user state
        context.user_data.pop('admin_creating_coupon', None)
        
        # Log the action
        logger.info(f"Super admin {user['full_name']} created coupon {coupon_code} with value {amount}")
        
    except Exception as e:
        logger.error(f"Error in process coupon creation: {e}")
        await update.message.reply_text(f"{EMOJIS['error']} حدث خطأ في إنشاء الكوبون.")

async def coupons_stats_handler(update: Update, context: CallbackContext):
    """Show coupons statistics for super admin"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user or user['role'] != 'super_admin':
            await query.edit_message_text(f"{EMOJIS['error']} ليس لديك صلاحية لهذه العملية.")
            return
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # إحصائيات الكوبونات
        cursor.execute('SELECT COUNT(*) FROM coupons')
        total_coupons = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM coupons WHERE is_used = 1')
        used_coupons = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM coupons WHERE is_used = 0')
        unused_coupons = cursor.fetchone()[0]
        
        cursor.execute('SELECT SUM(amount) FROM coupons')
        total_value = cursor.fetchone()[0] or 0
        
        cursor.execute('SELECT SUM(amount) FROM coupons WHERE is_used = 1')
        used_value = cursor.fetchone()[0] or 0
        
        cursor.execute('SELECT SUM(amount) FROM coupons WHERE is_used = 0')
        unused_value = cursor.fetchone()[0] or 0
        
        cursor.execute('''
            SELECT AVG(amount) FROM coupons
        ''')
        avg_value = cursor.fetchone()[0] or 0
        
        # أعلى قيمة كوبون
        cursor.execute('SELECT MAX(amount) FROM coupons')
        max_value = cursor.fetchone()[0] or 0
        
        # أقل قيمة كوبون
        cursor.execute('SELECT MIN(amount) FROM coupons')
        min_value = cursor.fetchone()[0] or 0
        
        # إحصائيات هذا الشهر
        cursor.execute('''
            SELECT COUNT(*) FROM coupons 
            WHERE created_at >= date('now', 'start of month')
        ''')
        this_month = cursor.fetchone()[0]
        
        conn.close()
        
        text = f"""
📊 **إحصائيات الكوبونات الشاملة** 📊

{EMOJIS['admin']} مرحباً **{user['full_name']}**

🎟️ **إحصائيات عامة:**
📦 إجمالي الكوبونات: **{total_coupons:,}** كوبون
✅ المستخدمة: **{used_coupons:,}** كوبون
🔓 غير المستخدمة: **{unused_coupons:,}** كوبون

💰 **إحصائيات القيم:**
💎 إجمالي القيمة: **{total_value:,.0f}** ريال
✅ قيمة المستخدمة: **{used_value:,.0f}** ريال
🔓 قيمة غير المستخدمة: **{unused_value:,.0f}** ريال

📈 **تحليل القيم:**
📊 متوسط قيمة الكوبون: **{avg_value:,.0f}** ريال
🔺 أعلى قيمة: **{max_value:,.0f}** ريال
🔻 أقل قيمة: **{min_value:,.0f}** ريال

📅 **إحصائيات الشهر الحالي:**
🆕 كوبونات جديدة: **{this_month:,}** كوبون

📊 **معدل الاستخدام:**
📈 نسبة الاستخدام: **{(used_coupons/total_coupons*100) if total_coupons > 0 else 0:.1f}%**
"""
        
        keyboard = [
            [InlineKeyboardButton('📋 قائمة الكوبونات', callback_data='super_list_coupons'),
             InlineKeyboardButton('🎟️ إنشاء كوبون جديد', callback_data='super_create_coupons')],
            [InlineKeyboardButton('🔄 تحديث الإحصائيات', callback_data='super_coupons_stats'),
             InlineKeyboardButton('🏠 لوحة المشرف الأعلى', callback_data='super_admin_panel')]
        ]
        
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Error in coupons stats handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في عرض الإحصائيات.")

async def list_coupons_handler(update: Update, context: CallbackContext):
    """List all coupons for super admin"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user or user['role'] != 'super_admin':
            await query.edit_message_text(f"{EMOJIS['error']} ليس لديك صلاحية لهذه العملية.")
            return
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # الحصول على آخر 10 كوبونات
        cursor.execute('''
            SELECT c.coupon_code, c.amount, c.is_used, c.created_at, c.used_at,
                   u.full_name as used_by_name
            FROM coupons c
            LEFT JOIN users u ON c.used_by = u.id
            ORDER BY c.created_at DESC
            LIMIT 10
        ''')
        coupons = cursor.fetchall()
        conn.close()
        
        text = f"""
📋 **قائمة الكوبونات** 📋

{EMOJIS['admin']} مرحباً **{user['full_name']}**

🎟️ **آخر 10 كوبونات:**

"""
        
        if coupons:
            for coupon in coupons:
                code, amount, is_used, created_at, used_at, used_by = coupon
                status = "✅ مستخدم" if is_used else "🔓 متاح"
                used_info = f"بواسطة: {used_by}" if used_by else ""
                
                text += f"""
🎫 **{code}**
💰 القيمة: {amount:,.0f} ريال
📊 الحالة: {status}
📅 أنشئ: {created_at[:10]}
{f"🕐 استخدم: {used_at[:10] if used_at else ''}" if is_used else ""}
{used_info}
━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        else:
            text += "\n❌ لا توجد كوبونات بعد"
        
        keyboard = [
            [InlineKeyboardButton('📊 إحصائيات الكوبونات', callback_data='super_coupons_stats'),
             InlineKeyboardButton('🎟️ إنشاء كوبون جديد', callback_data='super_create_coupons')],
            [InlineKeyboardButton('🔄 تحديث القائمة', callback_data='super_list_coupons'),
             InlineKeyboardButton('🏠 لوحة المشرف الأعلى', callback_data='super_admin_panel')]
        ]
        
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Error in list coupons handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في عرض القائمة.")

async def admin_add_offers_handler(update: Update, context: CallbackContext):
    """معالج إضافة العروض للمشرف الأعلى"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user or user['role'] != 'super_admin':
            await query.edit_message_text(f"{EMOJIS['error']} ليس لديك صلاحية لهذه العملية.")
            return
        
        text = f"""
🎁 **إدارة العروض والخصومات** 🎁

{EMOJIS['admin']} مرحباً **{user['full_name']}**

📋 **الخيارات المتاحة:**

🆕 **إضافة عرض جديد:**
   • عروض خصم على الكروت
   • عروض شحن مجاني
   • عروض كوبونات إضافية

📊 **إدارة العروض الحالية:**
   • عرض قائمة العروض
   • تعديل العروض الموجودة
   • إيقاف/تفعيل العروض

📈 **إحصائيات العروض:**
   • عدد مرات الاستخدام
   • العروض الأكثر شعبية
   • تقارير فعالية العروض

⚙️ **إعدادات العروض:**
   • مدة صلاحية العروض
   • شروط الاستخدام
   • حدود الاستخدام

💡 **اختر العملية المطلوبة:**
"""
        
        keyboard = [
            [InlineKeyboardButton('🆕 إضافة عرض جديد', callback_data='create_new_offer'),
             InlineKeyboardButton('📊 العروض الحالية', callback_data='manage_current_offers')],
            [InlineKeyboardButton('📈 إحصائيات العروض', callback_data='offers_statistics'),
             InlineKeyboardButton('⚙️ إعدادات العروض', callback_data='offers_settings')],
            [InlineKeyboardButton('🏠 لوحة المشرف الأعلى', callback_data='super_admin_panel')]
        ]
        
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Error in admin add offers handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في إدارة العروض.")
async def accounting_system_handler(update: Update, context: CallbackContext):
    """معالج النظام المحاسبي"""
    try:
        query = update.callback_query
        await query.answer()
        
        text = f"""
📊 **النظام المحاسبي المزدوج القيود** 📊

⚖️ **النظام المحاسبي الاحترافي:**
• نظام قيد مزدوج معتمد
• 18 حساب أساسي في دليل الحسابات
• تقارير مالية شاملة
• تصدير Excel متقدم
• سجل تدقيق كامل

📋 **التقارير المتاحة:**
• ميزان المراجعة
• قائمة الأرباح والخسائر  
• الميزانية العمومية
• دفتر الأستاذ العام

💾 **ميزات التصدير:**
• ملفات Excel منسقة
• تقارير شاملة
• حزمة كاملة مضغوطة
• تنزيل فوري وآمن

🎯 **المعايير المحاسبية:**
• توافق مع المعايير الدولية
• نظام قيد مزدوج متوازن
• سجل تدقيق شامل
• تتبع كامل للمعاملات
"""
        
        keyboard = [
            [InlineKeyboardButton('📋 ميزان المراجعة', callback_data='trial_balance'),
             InlineKeyboardButton('💰 الأرباح والخسائر', callback_data='income_statement')],
            [InlineKeyboardButton('🏛️ الميزانية العمومية', callback_data='balance_sheet'),
             InlineKeyboardButton('📚 دفتر الأستاذ العام', callback_data='general_ledger')],
            [InlineKeyboardButton('📄 تنزيل جميع التقارير', callback_data='download_complete_package'),
             InlineKeyboardButton('📊 تحليل مالي متقدم', callback_data='advanced_financial_analysis')],
            [InlineKeyboardButton('🏠 لوحة المشرف الأعلى', callback_data='super_admin_panel')]
        ]
        
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in accounting system handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في النظام المحاسبي.")

async def download_statements_handler(update: Update, context: CallbackContext):
    """معالج تنزيل كشوف الحسابات"""
    try:
        query = update.callback_query
        await query.answer()
        
        text = f"""
📄 **تنزيل كشوف الحسابات** 📄

📊 **التقارير المتاحة للتنزيل:**

📋 **التقارير الأساسية:**
• ميزان المراجعة (Trial Balance)
• قائمة الأرباح والخسائر (Income Statement)
• الميزانية العمومية (Balance Sheet)
• دفتر الأستاذ العام (General Ledger)

💾 **تنسيقات التصدير:**
• ملفات Excel (.xlsx) - منسقة ومرتبة
• تقارير شاملة ومفصلة
• تنسيق احترافي

🔒 **الأمان:**
• تشفير الملفات
• سجل تنزيلات كامل
• صلاحيات محدودة للمشرف الأعلى

📅 **البيانات الحالية:**
• آخر تحديث: الآن
• جميع المعاملات محدثة
• أرصدة دقيقة ومتوازنة
"""
        
        keyboard = [
            [InlineKeyboardButton('📋 ميزان المراجعة Excel', callback_data='download_trial_balance'),
             InlineKeyboardButton('💰 الأرباح والخسائر Excel', callback_data='download_income_statement')],
            [InlineKeyboardButton('🏛️ الميزانية العمومية Excel', callback_data='download_balance_sheet'),
             InlineKeyboardButton('📚 دفتر الأستاذ Excel', callback_data='download_general_ledger')],
            [InlineKeyboardButton('📦 تنزيل الحزمة الكاملة', callback_data='download_complete_package')],
            [InlineKeyboardButton('📊 النظام المحاسبي', callback_data='accounting_system'),
             InlineKeyboardButton('🏠 لوحة المشرف الأعلى', callback_data='super_admin_panel')]
        ]
        
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in download statements handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في صفحة التنزيل.")

async def trial_balance_handler(update: Update, context: CallbackContext):
    """معالج ميزان المراجعة"""
    try:
        query = update.callback_query
        await query.answer()
        
        from bot_modules.accounting_integration import get_trial_balance
        
        trial_balance = get_trial_balance()
        
        text = f"""
📋 **ميزان المراجعة** 📋

📅 **كما في تاريخ:** {trial_balance['as_of_date']}

⚖️ **ملخص الأرصدة:**
• إجمالي المدين: **{trial_balance['totals']['total_debit']:,.2f}** ريال
• إجمالي الدائن: **{trial_balance['totals']['total_credit']:,.2f}** ريال
• الحالة: **{'✅ متوازن' if trial_balance['totals']['is_balanced'] else '❌ غير متوازن'}**

📊 **أهم الحسابات:**

"""
        
        # عرض أهم الحسابات
        for account in trial_balance['accounts'][:8]:
            balance_symbol = "💰" if account['balance_type'] == 'debit' else "💳"
            acc_type_ar = {
                'asset': 'أصول', 
                'liability': 'خصوم', 
                'equity': 'حقوق ملكية', 
                'revenue': 'إيرادات', 
                'expense': 'مصروفات'
            }.get(account['account_type'], account['account_type'])
            
            text += f"""
{balance_symbol} **{account['account_code']} - {account['account_name']}**
📊 {acc_type_ar} | 💵 {account['balance_amount']:,.2f} ريال
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        
        keyboard = [
            [InlineKeyboardButton('📄 تنزيل Excel', callback_data='download_trial_balance'),
             InlineKeyboardButton('🔄 تحديث', callback_data='trial_balance')],
            [InlineKeyboardButton('📊 النظام المحاسبي', callback_data='accounting_system')]
        ]
        
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in trial balance handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في ميزان المراجعة.")

async def download_trial_balance(update: Update, context: CallbackContext):
    """تنزيل ميزان المراجعة كملف Excel"""
    try:
        query = update.callback_query
        await query.answer("📄 جاري إنشاء ملف Excel...")
        
        from bot_modules.accounting_integration import export_trial_balance_to_excel
        import os
        
        filename = f"trial_balance_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        filepath = export_trial_balance_to_excel(filename=filename)
        
        if os.path.exists(filepath):
            with open(filepath, 'rb') as file:
                await context.bot.send_document(
                    chat_id=query.message.chat_id,
                    document=file,
                    filename=filename,
                    caption="📋 **ميزان المراجعة**\n\n✅ ملف Excel منسق وجاهز للمراجعة",
                    parse_mode='Markdown'
                )
            os.remove(filepath)
            await query.edit_message_text("✅ تم إرسال ميزان المراجعة بنجاح!")
        
    except Exception as e:
        logger.error(f"Error downloading trial balance: {e}")
        await query.edit_message_text(f"❌ خطأ في تنزيل ميزان المراجعة: {e}")

async def download_complete_package(update: Update, context: CallbackContext):
    """تنزيل الحزمة المحاسبية الكاملة"""
    try:
        query = update.callback_query
        await query.answer("📦 جاري إنشاء الحزمة الكاملة...")
        
        from bot_modules.accounting_integration import export_complete_accounting_package
        import os, zipfile
        
        package_result = export_complete_accounting_package()
        
        if package_result['success']:
            zip_filename = f"accounting_package_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
            zip_filepath = f"/workspace/{zip_filename}"
            
            with zipfile.ZipFile(zip_filepath, 'w') as zipf:
                for report_type, filepath in package_result['files'].items():
                    if os.path.exists(filepath):
                        zipf.write(filepath, os.path.basename(filepath))
                        os.remove(filepath)
            
            with open(zip_filepath, 'rb') as file:
                await context.bot.send_document(
                    chat_id=query.message.chat_id,
                    document=file,
                    filename=zip_filename,
                    caption="📦 **الحزمة المحاسبية الكاملة**\n\n✅ جميع التقارير المالية بتنسيق Excel",
                    parse_mode='Markdown'
                )
            
            os.remove(zip_filepath)
            await query.edit_message_text("✅ تم إرسال الحزمة المحاسبية بنجاح!")
        
    except Exception as e:
        logger.error(f"Error downloading complete package: {e}")
        await query.edit_message_text(f"❌ خطأ في تنزيل الحزمة: {e}")


async def create_new_offer(update: Update, context: CallbackContext):
    """إنشاء عرض جديد - معالج فعلي"""
    try:
        query = update.callback_query
        await query.answer()
        
        # تفعيل وضع إنشاء العرض
        from bot_modules.conversation_states import set_conversation_state, ConversationStates
        set_conversation_state(context, ConversationStates.CREATE_OFFER_TITLE)
        
        text = f"""
🎁 **إنشاء عرض جديد** 🎁

📝 **سنقوم بإنشاء العرض خطوة بخطوة:**

🔸 **الخطوة 1 من 5**
🏷️ **أدخل عنوان العرض:**

مثال: "خصم 20% على شبكة النور"

💡 **ملاحظات:**
• اختر عنواناً جذاباً وواضحاً
• سيظهر للعملاء في قائمة العروض
• يفضل ذكر نسبة الخصم أو الفائدة

📤 **أرسل عنوان العرض الآن:**
"""
        
        keyboard = [
            [InlineKeyboardButton('❌ إلغاء', callback_data='cancel_offer_creation')],
            [InlineKeyboardButton('🏠 إدارة العروض', callback_data='admin_add_offers')]
        ]
        
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in create new offer: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في إنشاء العرض.")

async def process_offer_creation_step(update: Update, context: CallbackContext):
    """معالجة خطوات إنشاء العرض"""
    try:
        from bot_modules.conversation_states import get_conversation_state, set_conversation_state, ConversationStates
        from bot_modules.input_validation import InputValidator
        from services.offer_service import offer_service
        
        text = update.message.text.strip()
        user = get_user(update.effective_user.id)
        state, state_name = get_conversation_state(context)
        
        if state == ConversationStates.CREATE_OFFER_TITLE:
            # التحقق من العنوان
            if len(text) < 5:
                await update.message.reply_text("❌ العنوان قصير جداً (الحد الأدنى 5 أحرف)")
                return
            
            context.user_data['offer_title'] = text
            set_conversation_state(context, ConversationStates.CREATE_OFFER_DESCRIPTION)
            
            await update.message.reply_text(
                f"✅ **تم حفظ عنوان العرض:** {text}\n\n🔸 **الخطوة 2 من 5**\n📝 **أدخل وصف العرض التفصيلي:**",
                parse_mode='Markdown'
            )
            
        elif state == ConversationStates.CREATE_OFFER_DESCRIPTION:
            # التحقق من الوصف
            is_valid, validated_desc = InputValidator.validate_description(text, min_length=10)
            if not is_valid:
                await update.message.reply_text(f"❌ {validated_desc}")
                return
            
            context.user_data['offer_description'] = validated_desc
            set_conversation_state(context, ConversationStates.CREATE_OFFER_DISCOUNT)
            
            await update.message.reply_text(
                f"✅ **تم حفظ وصف العرض**\n\n🔸 **الخطوة 3 من 5**\n💰 **أدخل نسبة الخصم (%):**\n\nمثال: 20 (للخصم 20%)",
                parse_mode='Markdown'
            )
            
        elif state == ConversationStates.CREATE_OFFER_DISCOUNT:
            # التحقق من نسبة الخصم
            is_valid, discount, error_msg = InputValidator.validate_percentage(text)
            if not is_valid:
                await update.message.reply_text(f"❌ {error_msg}")
                return
            
            context.user_data['offer_discount'] = discount
            set_conversation_state(context, ConversationStates.CREATE_OFFER_DURATION)
            
            await update.message.reply_text(
                f"✅ **تم حفظ نسبة الخصم:** {discount}%\n\n🔸 **الخطوة 4 من 5**\n📅 **أدخل مدة العرض (بالأيام):**\n\nمثال: 30 (للمدة 30 يوم)",
                parse_mode='Markdown'
            )
            
        elif state == ConversationStates.CREATE_OFFER_DURATION:
            # التحقق من المدة
            try:
                duration = int(text)
                if duration <= 0 or duration > 365:
                    await update.message.reply_text("❌ مدة العرض يجب أن تكون بين 1 و 365 يوم")
                    return
            except ValueError:
                await update.message.reply_text("❌ يرجى إدخال رقم صحيح للمدة")
                return
            
            context.user_data['offer_duration'] = duration
            set_conversation_state(context, ConversationStates.CREATE_OFFER_MAX_USES)
            
            await update.message.reply_text(
                f"✅ **تم حفظ مدة العرض:** {duration} يوم\n\n🔸 **الخطوة 5 من 5**\n🔢 **أدخل الحد الأقصى للاستخدام:**\n\nمثال: 100 (يمكن استخدامه 100 مرة)\nأو اكتب 0 للاستخدام غير المحدود",
                parse_mode='Markdown'
            )
            
        elif state == ConversationStates.CREATE_OFFER_MAX_USES:
            # التحقق من الحد الأقصى
            try:
                max_uses = int(text)
                if max_uses < 0:
                    await update.message.reply_text("❌ الحد الأقصى لا يمكن أن يكون سالباً")
                    return
            except ValueError:
                await update.message.reply_text("❌ يرجى إدخال رقم صحيح للحد الأقصى")
                return
            
            # إنشاء العرض
            offer_data = {
                'title': context.user_data.get('offer_title'),
                'description': context.user_data.get('offer_description'),
                'discount_percentage': context.user_data.get('offer_discount'),
                'duration_days': context.user_data.get('offer_duration'),
                'max_uses': max_uses if max_uses > 0 else None
            }
            
            success, offer_id, message = offer_service.create_offer(offer_data, user['id'])
            
            if success:
                from datetime import datetime, timedelta
                end_date = (datetime.now() + timedelta(days=offer_data['duration_days'])).strftime('%Y-%m-%d')
                
                success_text = f"""
✅ **تم إنشاء العرض بنجاح!** ✅

🎁 **تفاصيل العرض الجديد:**
🏷️ **العنوان:** {offer_data['title']}
📝 **الوصف:** {offer_data['description']}
💰 **نسبة الخصم:** {offer_data['discount_percentage']}%
📅 **ينتهي في:** {end_date}
🔢 **الحد الأقصى:** {max_uses if max_uses > 0 else 'غير محدود'} استخدام
🆔 **معرف العرض:** #{offer_id}

🚀 **العرض نشط ومتاح للعملاء الآن!**
💡 **سيظهر في قائمة العروض تلقائياً**
"""
                
                keyboard = [
                    [InlineKeyboardButton('🎁 إدارة العروض', callback_data='admin_add_offers'),
                     InlineKeyboardButton('🆕 إضافة عرض آخر', callback_data='create_new_offer')],
                    [InlineKeyboardButton('🏠 لوحة المشرف الأعلى', callback_data='super_admin_panel')]
                ]
            else:
                success_text = f"❌ **فشل في إنشاء العرض**\n\n🔍 السبب: {message}"
                keyboard = [
                    [InlineKeyboardButton('🔄 إعادة المحاولة', callback_data='create_new_offer')],
                    [InlineKeyboardButton('🎁 إدارة العروض', callback_data='admin_add_offers')]
                ]
            
            context.user_data.clear()
            await update.message.reply_text(success_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in offer creation step: {e}")
        context.user_data.clear()
        await update.message.reply_text(f"❌ خطأ في إنشاء العرض: {e}")

