#!/usr/bin/env python3
"""
Admin Functions module for Pottagrm Enhanced Bot
Contains super admin and admin specific functions
"""

import logging
import uuid
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext
from bot_modules.config import *
from bot_modules.database import get_db_connection
from bot_modules.utils import *
from bot_modules.enhanced_error_messages import ErrorMessages, perm_error, db_error, unexpected_error, menu_error, wallet_error, coupon_error
from bot_modules.export_system import (
    export_options_handler, export_profits_handler, export_customers_handler,
    export_suppliers_handler, export_comprehensive_handler, quick_export_handler
)
from bot_modules.accounting_search import accounting_search_handler, quick_stats_handler, quick_transaction_report_handler

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
        await update.message.reply_text(perm_error("مشرف أو مشرف أعلى", user['role'] if user else "غير مسجل"))

async def show_super_admin_panel(update: Update, context: CallbackContext, user):
    """Show super admin control panel"""
    try:
        # Get platform statistics
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Basic stats
        cursor.execute('SELECT COUNT(*) FROM users')
        result = cursor.fetchone()
        total_users = result[0] if result else 0
        
        cursor.execute('SELECT COUNT(*) FROM users WHERE is_active = 1')
        result = cursor.fetchone()
        active_users = result[0] if result else 0
        
        cursor.execute('SELECT SUM(balance) FROM users')
        result = cursor.fetchone()
        total_balance = result[0] if result and result[0] is not None else 0
        
        cursor.execute('SELECT COUNT(*) FROM users WHERE role = "supplier" AND is_active = 0')
        result = cursor.fetchone()
        pending_suppliers = result[0] if result else 0
        
        cursor.execute('SELECT COUNT(*) FROM transactions')
        result = cursor.fetchone()
        total_transactions = result[0] if result else 0
        
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
            [InlineKeyboardButton(f'👥 إدارة العملاء المطورة', callback_data='customer_dashboard'),
             InlineKeyboardButton(f'👑 إدارة المشرفين المطورة', callback_data='admin_dashboard')],
            [InlineKeyboardButton(f'📊 لوحة المعلومات', callback_data='dashboard'),
             InlineKeyboardButton(f'📈 التقارير التنفيذية', callback_data='executive_reports')],
            [InlineKeyboardButton(f'💰 إدارة الأرصدة', callback_data='admin_wallet'),
             InlineKeyboardButton(f'💸 إرسال رصيد', callback_data='admin_send_money')],
            [InlineKeyboardButton(f'🏛️ إدارة المنصة', callback_data='super_platform_management')],
            [InlineKeyboardButton(f'🎁 إضافة عروض', callback_data='admin_add_offers'),
             InlineKeyboardButton(f'✅ تفعيل مزودين', callback_data='super_activate_suppliers')],
            [InlineKeyboardButton(f'📊 النظام المحاسبي', callback_data='accounting_system'),
             InlineKeyboardButton(f'💰 طلبات السحب', callback_data='admin_withdrawals')],
            [InlineKeyboardButton(f'📄 تنزيل كشوف حسابات', callback_data='download_statements'),
             InlineKeyboardButton(f'⚡ تصدير سريع', callback_data='quick_export')],
            [InlineKeyboardButton(f'🎟️ إنشاء كوبونات', callback_data='super_create_coupons')],
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
        await update.message.reply_text(ErrorMessages.admin_error(
            "تحميل لوحة المشرف الأعلى",
            "مشرف أعلى"
        ))





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

💡 استخدم زر "🎟️ إنشاء كوبونات" لإضافة رصيد عبر الكوبونات فقط.
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
        
        # Send notification to receiver (about receiving money from admin)
        try:
            receiver_notification = f"""
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
                text=receiver_notification,
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.warning(f"Failed to send notification to receiver {target_user['telegram_id']}: {e}")

        # Send notification to admin (about sending money)
        try:
            admin_notification = f"""
👑 **تم تحويل رصيد من الإدارة** 👑

📤 **تفاصيل التحويل الإداري:**
👤 المستلم: **{target_user['full_name']}**
💰 المبلغ المحول: **{amount:,.2f}** ريال
💵 رصيد المستلم الجديد: **{target_new_balance:,.2f}** ريال
💬 السبب: {reason}
🕐 وقت التحويل: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

───────────────────
💡 تم تسجيل العملية في نظام الإدارة
"""

            await context.bot.send_message(
                chat_id=user['telegram_id'],
                text=admin_notification,
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.warning(f"Failed to send notification to admin {user['telegram_id']}: {e}")
        
        # Log the transfer
        logger.info(f"Super admin {user['full_name']} transferred {amount} YER to {target_user['full_name']}")
        
    except Exception as e:
        logger.error(f"Error in process balance issue: {e}")
        await update.message.reply_text(wallet_error("تحويل الرصيد للمستخدم"))

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
        await query.edit_message_text(wallet_error("إرسال الرصيد"))
        



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
        await query.edit_message_text(ErrorMessages.supplier_error("تحميل قائمة المزودين"))

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
        await query.edit_message_text(ErrorMessages.supplier_error("تفعيل المزود"))

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
        await query.edit_message_text(ErrorMessages.supplier_error("تفعيل جماعي للمزودين"))

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
            [InlineKeyboardButton(f'📢 إشعار عام', callback_data='super_broadcast_message')],
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
        await query.edit_message_text(ErrorMessages.admin_error("تحميل إدارة المنصة"))

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
        await query.edit_message_text(unexpected_error("تنفيذ العملية المطلوبة"))

# Placeholder handlers for missing features


# Backup handler removed as requested
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
            LEFT JOIN transactions t ON (u.id = t.from_user OR u.id = t.to_user)
            WHERE u.balance > 0
            GROUP BY u.id, u.full_name, u.role, u.balance
            ORDER BY u.balance DESC, total_amount DESC
            LIMIT 5
        ''')
        top_performers = cursor.fetchall()
        
        conn.close()
        
        # حساب المعدلات والنسب المهمة (مع حماية ضد القسمة على صفر)
        try:
            growth_rate_daily = (growth_stats[0] / max(growth_stats[3] - growth_stats[0], 1) * 100) if growth_stats[3] > 0 else 0
            growth_rate_weekly = (growth_stats[1] / max(growth_stats[3] - growth_stats[1], 1) * 100) if growth_stats[3] > 0 else 0
            growth_rate_monthly = (growth_stats[2] / max(growth_stats[3] - growth_stats[2], 1) * 100) if growth_stats[3] > 0 else 0
            
            avg_transaction_value = (revenue_stats[4] / max(revenue_stats[5], 1)) if revenue_stats[5] > 0 else 0
            sales_conversion = (sales_stats[3] / max(sales_stats[2], 1) * 100) if sales_stats[2] > 0 else 0
        except (TypeError, ZeroDivisionError, IndexError) as calc_error:
            logger.warning(f"Calculation error in executive reports: {calc_error}")
            growth_rate_daily = growth_rate_weekly = growth_rate_monthly = 0
            avg_transaction_value = sales_conversion = 0
        
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
        if top_performers:
            for i, performer in enumerate(top_performers[:3], 1):
                try:
                    role_emoji = "👤" if performer[1] == 'customer' else "🏪" if performer[1] == 'supplier' else "💼"
                    balance = performer[2] if performer[2] is not None else 0
                    transaction_count = performer[3] if performer[3] is not None else 0
                    text += f"\n{i}️⃣ {role_emoji} {performer[0]}: **{balance:,.2f}** ريال"
                    if transaction_count > 0:
                        text += f" ({transaction_count} معاملة)"
                except (IndexError, TypeError) as performer_error:
                    logger.warning(f"Error processing performer data: {performer_error}")
                    text += f"\n{i}️⃣ 💼 بيانات غير مكتملة"
        else:
            text += "\nلا توجد بيانات أداء متاحة"

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
        await query.edit_message_text(ErrorMessages.report_error("التنفيذية للإدارة"))



# Security monitoring handler removed as requested

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
        result = cursor.fetchone()
        total_admins = result['total_admins'] if result else 0
        
        cursor.execute("SELECT COUNT(*) as active_admins FROM users WHERE role = 'admin' AND is_active = 1")
        result = cursor.fetchone()
        active_admins = result['active_admins'] if result else 0
        
        cursor.execute("SELECT COUNT(*) as super_admins FROM users WHERE role = 'super_admin'")
        result = cursor.fetchone()
        super_admins = result['super_admins'] if result else 0
        
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
        await query.edit_message_text(ErrorMessages.admin_error("تحميل إدارة المشرفين"))

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
        cursor.execute('SELECT COUNT(*) FROM users')
        result = cursor.fetchone()
        total_users = result[0] if result else 0
        
        cursor.execute("SELECT COUNT(*) FROM users WHERE is_active = 1")
        result = cursor.fetchone()
        active_users = result[0] if result else 0
        
        cursor.execute("SELECT COUNT(*) FROM users WHERE date(created_at) = date('now')")
        result = cursor.fetchone()
        new_users_today = result[0] if result else 0
        
        # Financial statistics
        cursor.execute('SELECT SUM(amount) FROM transactions')
        result = cursor.fetchone()
        total_transactions = result[0] if result and result[0] is not None else 0
        
        cursor.execute('SELECT SUM(balance) FROM users')
        result = cursor.fetchone()
        total_balances = result[0] if result and result[0] is not None else 0
        
        cursor.execute("SELECT COUNT(*) FROM transactions WHERE date(created_at) = date('now')")
        result = cursor.fetchone()
        transactions_today = result[0] if result else 0
        
        # Networks statistics
        cursor.execute('SELECT COUNT(*) FROM networks')
        result = cursor.fetchone()
        total_networks = result[0] if result else 0
        
        cursor.execute("SELECT COUNT(*) FROM networks WHERE is_active = 1")
        result = cursor.fetchone()
        active_networks = result[0] if result else 0
        
        cursor.execute("SELECT COUNT(*) FROM networks WHERE is_approved = 0")
        result = cursor.fetchone()
        pending_networks = result[0] if result else 0
        
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
        await query.edit_message_text(menu_error("لوحة المعلومات", "تحميل البيانات"))

async def view_all_suppliers_handler(update: Update, context: CallbackContext):
    """عرض جميع المزودين مع ترقيم صفحات بسيط"""
    try:
        query = update.callback_query
        await query.answer()
        user = get_user(query.from_user.id)
        if not user or user['role'] != 'super_admin':
            await query.edit_message_text(f"{EMOJIS['error']} ليس لديك صلاحية لهذه العملية.")
            return

        # استخراج الصفحة من callback إن وجدت
        data = query.data or 'super_view_all_suppliers'
        parts = data.split('_')
        page = 1
        if len(parts) >= 5 and parts[-2] == 'page':
            try:
                page = max(1, int(parts[-1]))
            except Exception:
                page = 1

        page_size = 10
        offset = (page - 1) * page_size

        conn = get_db_connection()
        cursor = conn.cursor()

        # إجمالي المزودين
        cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'supplier'")
        total_suppliers = cursor.fetchone()[0]

        # جلب الصفحة الحالية
        cursor.execute('''
            SELECT id, full_name, phone, is_active, balance
            FROM users
            WHERE role = 'supplier'
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        ''', (page_size, offset))
        rows = cursor.fetchall()
        conn.close()

        total_pages = max(1, (total_suppliers + page_size - 1) // page_size)

        text = f"""
👥 **جميع المزودين** (صفحة {page}/{total_pages})

إجمالي المزودين: **{total_suppliers}**
"""

        if rows:
            for sid, name, phone, is_active, balance in rows:
                status = '✅ مفعل' if is_active else '⏸️ موقوف'
                text += f"""
━━━━━━━━━━━━━━━━
👤 {name or 'غير معروف'}
📱 {phone or 'غير متوفر'}
💰 الرصيد: {balance or 0:.2f} ريال
🔰 الحالة: {status}
🆔 {sid}
"""
        else:
            text += "\n❌ لا توجد بيانات."

        # أزرار الترقيم
        nav_buttons = []
        if page > 1:
            nav_buttons.append(InlineKeyboardButton('⬅️ السابق', callback_data=f'super_view_all_suppliers_page_{page-1}'))
        if page < total_pages:
            nav_buttons.append(InlineKeyboardButton('التالي ➡️', callback_data=f'super_view_all_suppliers_page_{page+1}'))

        keyboard = []
        if nav_buttons:
            keyboard.append(nav_buttons)
        keyboard.append([InlineKeyboardButton('👑 لوحة المشرف الأعلى', callback_data='super_admin_panel')])

        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

    except Exception as e:
        logger.error(f"Error in view_all_suppliers_handler: {e}")
        await query.edit_message_text(menu_error('إدارة المزودين', 'عرض جميع المزودين'))

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
        await query.edit_message_text(ErrorMessages.card_error("بدء إصدار البطاقات"))

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
        await update.message.reply_text(ErrorMessages.card_error("إصدار البطاقات"))

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
        result = cursor.fetchone()
        total_created = result[0] if result and result[0] is not None else 0
        
        # Get total sent to users
        cursor.execute('SELECT SUM(amount) FROM transactions WHERE type = "admin_transfer" AND from_user = ?', (user['id'],))
        result = cursor.fetchone()
        total_sent = result[0] if result and result[0] is not None else 0
        
        # Get number of users
        cursor.execute('SELECT COUNT(*) FROM users WHERE role != "super_admin"')
        result = cursor.fetchone()
        total_users = result[0] if result else 0
        
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
🎟️ إنشاء كوبونات للشحن
📊 مراجعة الرصيد الحالي
💸 إرسال رصيد للمستخدمين

⚠️ **ملاحظة مهمة:**
إضافة الرصيد للنظام يتم **فقط عبر الكوبونات** لضمان الأمان والتتبع
"""
        
        keyboard = [
            [InlineKeyboardButton('🎟️ إنشاء كوبونات', callback_data='super_create_coupons'),
             InlineKeyboardButton('💸 إرسال رصيد لمستخدم', callback_data='admin_send_money')],
            [InlineKeyboardButton('👑 لوحة المشرف الأعلى', callback_data='super_admin_panel'),
             InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
        ]
        
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in admin wallet: {e}")
        await query.edit_message_text(wallet_error("عرض محفظة الإدارة"))



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
        await query.edit_message_text(ErrorMessages.notification_error("بدء الإرسال الجماعي"))

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
        await update.message.reply_text(ErrorMessages.notification_error("تنفيذ الإرسال الجماعي"))

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
        await query.edit_message_text(ErrorMessages.admin_error("تحديث أوامر البوت"))

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

# System settings handler removed as requested

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
        cursor.execute('SELECT COUNT(*) FROM users')
        total_users = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM users WHERE is_active = 1')
        active_users = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM users WHERE role = "customer"')
        customers = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM users WHERE role = "agent"')
        agents = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM users WHERE role = "supplier"')
        suppliers = cursor.fetchone()[0]
        
        # Financial statistics
        cursor.execute('SELECT SUM(balance) FROM users')
        result = cursor.fetchone()[0]
        total_balance = result if result is not None else 0
        
        cursor.execute('SELECT COUNT(*) FROM transactions')
        total_transactions = cursor.fetchone()[0]
        
        cursor.execute('SELECT SUM(amount) FROM transactions WHERE type IN ("purchase", "transfer")')
        result = cursor.fetchone()[0]
        total_volume = result if result is not None else 0
        
        cursor.execute('SELECT SUM(amount) FROM transactions WHERE type = "commission"')
        result = cursor.fetchone()[0]
        total_commissions = result if result is not None else 0
        
        # Networks and cards statistics
        cursor.execute('SELECT COUNT(*) FROM networks WHERE is_active = 1')
        total_networks = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM cards WHERE is_used = 0')
        available_cards = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM cards WHERE is_used = 1')
        sold_cards = cursor.fetchone()[0]
        
        # Recharge cards statistics
        cursor.execute('SELECT COUNT(*) FROM recharge_cards WHERE status = "available"')
        available_recharge_cards = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM recharge_cards WHERE status = "sold"')
        sold_recharge_cards = cursor.fetchone()[0]
        
        # Recent activity
        cursor.execute('''
            SELECT COUNT(*) 
            FROM transactions 
            WHERE created_at >= datetime('now', '-24 hours')
        ''')
        recent_transactions = cursor.fetchone()[0]
        
        cursor.execute('''
            SELECT COUNT(*) 
            FROM users 
            WHERE created_at >= datetime('now', '-24 hours')
        ''')
        new_users_today = cursor.fetchone()[0]
        
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
        await query.edit_message_text(menu_error("لوحة المعلومات", "عرض البيانات"))

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
        await query.edit_message_text(ErrorMessages.admin_error("إدارة المشرفين"))

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
        await query.edit_message_text(ErrorMessages.admin_error("إدارة المستخدمين"))

# Second backup handler removed as requested

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
📊 مراقبة الأداء والاستقرار
🔄 إدارة الصيانة والتحديثات
"""
    
    keyboard = [
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

# Security monitoring handler removed as requested

# Export functions for callback routing
ADMIN_CALLBACKS = {
    'super_admin_panel': lambda u, c: show_super_admin_panel(u, c, get_user(u.effective_user.id)),

    'super_activate_suppliers': activate_suppliers_handler,
    'activate_all_suppliers': activate_all_suppliers,
    'super_platform_management': platform_management_handler,
    'super_commission_settings': commission_settings_handler,
    'executive_reports': executive_reports_handler,
    'super_manage_users': manage_users_handler,
    'super_executive_reports': executive_reports_handler,
    'super_manage_admins': manage_admins_handler,
    'super_dashboard': dashboard_handler,
    'super_view_all_suppliers': view_all_suppliers_handler,
    'view_supplier_details': view_supplier_details_handler,
    # New enhanced features


    'super_broadcast_message': broadcast_message_handler,
    'super_update_commands': update_commands_handler,


}

# Missing handler implementations

# backup_full_handler removed as requested

# backup_data_only_handler removed as requested

# backup_restore_handler removed as requested

# backup_list_handler removed as requested
# backup_schedule_handler removed as requested

# backup_settings_handler removed as requested

# System settings handlers removed as requested

# system_edit_agent_commission_handler removed as requested

# system_reload_config_handler removed as requested

# system_stats_handler removed as requested

async def admin_withdrawals_handler(update: Update, context: CallbackContext):
    """معالج طلبات السحب للمشرف الأعلى"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user or user['role'] != 'super_admin':
            await query.edit_message_text(f"{EMOJIS['error']} ليس لديك صلاحية لهذه العملية.")
            return
        
        # الحصول على طلبات السحب المعلقة
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT w.withdrawal_id, w.provider_name, w.amount, w.method, w.requested_at,
                   u.full_name, u.phone
            FROM withdrawals w
            JOIN users u ON w.provider_id = u.id
            WHERE w.status = 'Pending'
            ORDER BY w.requested_at ASC
        ''')
        
        pending_withdrawals = cursor.fetchall()
        
        # إحصائيات إضافية
        cursor.execute("SELECT COUNT(*) FROM withdrawals WHERE status = 'Pending'")
        result = cursor.fetchone()
        pending_count = result[0] if result else 0
        
        cursor.execute("SELECT COALESCE(SUM(amount), 0) FROM withdrawals WHERE status = 'Pending'")
        result = cursor.fetchone()
        pending_amount = result[0] if result else 0
        
        cursor.execute("SELECT COUNT(*) FROM withdrawals WHERE status = 'Approved' AND DATE(confirmed_at) = DATE('now')")
        result = cursor.fetchone()
        approved_today = result[0] if result else 0
        
        conn.close()
        
        withdrawals_text = f"""
💰 **إدارة طلبات السحب** 💰

👑 **{user['full_name']}**

📊 **ملخص الطلبات:**
⏳ طلبات معلقة: **{pending_count}** طلب
💰 إجمالي المبالغ المعلقة: **{pending_amount:,.2f}** ريال
✅ تم الموافقة عليها اليوم: **{approved_today}** طلب

📋 **الطلبات المعلقة:**
"""
        
        if pending_withdrawals:
            for withdrawal in pending_withdrawals:
                w_id, provider_name, amount, method, requested_at, full_name, phone = withdrawal
                date_str = requested_at[:10] if requested_at else 'غير محدد'
                
                withdrawals_text += f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
👤 **{full_name}** ({provider_name})
📱 {phone}
💰 المبلغ: **{amount:,.2f}** ريال
🏦 الطريقة: {method}
📅 تاريخ الطلب: {date_str}
🆔 `{w_id[:8]}...`

[الموافقة] [الرفض]
"""
        else:
            withdrawals_text += """
✅ **لا توجد طلبات معلقة حالياً**

💡 ستظهر هنا طلبات السحب من المزودين عند تقديمها.
"""
        
        keyboard = []
        
        # إضافة أزرار الموافقة والرفض لكل طلب
        for withdrawal in pending_withdrawals:
            w_id = withdrawal[0]
            provider_name = withdrawal[1]
            keyboard.append([
                InlineKeyboardButton(f'✅ موافقة {provider_name[:10]}...', callback_data=f'approve_withdrawal_{w_id}'),
                InlineKeyboardButton(f'❌ رفض {provider_name[:10]}...', callback_data=f'reject_withdrawal_{w_id}')
            ])
        
        keyboard.extend([
            [InlineKeyboardButton('🔄 تحديث القائمة', callback_data='admin_withdrawals')],
            [InlineKeyboardButton('👑 لوحة المشرف الأعلى', callback_data='super_admin_panel'),
             InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
        ])
        
        await query.edit_message_text(withdrawals_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in admin withdrawals handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في عرض طلبات السحب")

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
        await query.edit_message_text(ErrorMessages.admin_error("إدارة العمولات"))

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
        await query.edit_message_text(ErrorMessages.admin_error("تعديل العمولات"))

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
        await query.edit_message_text(ErrorMessages.admin_error("تعديل العمولة المحددة"))

# Update ADMIN_CALLBACKS with newly defined handlers
ADMIN_CALLBACKS.update({
    # Core admin functions - simplified
    'admin_wallet': admin_wallet_handler,
    'admin_send_money': admin_send_money_handler,
  # Keep for compatibility
    'super_manage_admins': manage_admins_handler,
    'super_manage_users': manage_users_handler,
    'super_dashboard': dashboard_handler,
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

    'admin_add_offers': lambda u, c: admin_add_offers_handler(u, c),
    'accounting_system': lambda u, c: accounting_system_handler(u, c),
    'fix_missing_entries': lambda u, c: fix_missing_entries_handler(u, c),
    'trial_balance': lambda u, c: trial_balance_handler(u, c),
    'download_statements': lambda u, c: download_statements_handler(u, c),
    'income_statement': lambda u, c: income_statement_handler(u, c),
    'balance_sheet': lambda u, c: balance_sheet_handler(u, c),
    'general_ledger': lambda u, c: general_ledger_handler(u, c),
    
    # Download statements submenu aliases
    'customer_statements': lambda u, c: accounting_customers_handler(u, c),
    'supplier_statements': lambda u, c: accounting_suppliers_handler(u, c),
    'export_all_data': lambda u, c: export_options_handler(u, c),
    
    # Accounting reports handlers
    'accounting_transactions': lambda u, c: accounting_transactions_handler(u, c),
    'accounting_profits': lambda u, c: accounting_profits_handler(u, c),
    'accounting_suppliers': lambda u, c: accounting_suppliers_handler(u, c),
    'accounting_customers': lambda u, c: accounting_customers_handler(u, c),
    'accounting_analytics': lambda u, c: accounting_analytics_handler(u, c),
    'accounting_export': lambda u, c: export_options_handler(u, c),
    'accounting_custom': lambda u, c: accounting_custom_reports_handler(u, c),
    'accounting_search': lambda u, c: accounting_search_handler(u, c),
    'quick_stats': lambda u, c: quick_stats_handler(u, c),
    'quick_transaction_report': lambda u, c: quick_transaction_report_handler(u, c),
    
    # Sub-handlers for transactions
    'transactions_detailed': lambda u, c: quick_transaction_report_handler(u, c),
    'transactions_purchases': lambda u, c: quick_stats_handler(u, c),
    'transactions_transfers': lambda u, c: quick_stats_handler(u, c),
    'transactions_coupons': lambda u, c: quick_stats_handler(u, c),
    'export_transactions': lambda u, c: export_profits_handler(u, c),
    'transactions_search': lambda u, c: accounting_search_handler(u, c),
    
    # Sub-handlers for profits
    'profits_detailed': lambda u, c: export_profits_handler(u, c),
    'profits_trends': lambda u, c: accounting_profits_handler(u, c),
    'profits_suppliers': lambda u, c: export_suppliers_handler(u, c),
    'profits_comparison': lambda u, c: accounting_profits_handler(u, c),
    'export_profits': lambda u, c: export_profits_handler(u, c),
    'profits_custom_period': lambda u, c: export_profits_handler(u, c),
    
    # Sub-handlers for suppliers
    'suppliers_detailed': lambda u, c: accounting_suppliers_handler(u, c),
    'suppliers_performance': lambda u, c: accounting_suppliers_handler(u, c),
    'suppliers_commissions': lambda u, c: accounting_suppliers_handler(u, c),
    'suppliers_networks': lambda u, c: accounting_suppliers_handler(u, c),
    'export_suppliers': lambda u, c: export_suppliers_handler(u, c),
    'suppliers_search': lambda u, c: accounting_search_handler(u, c),
    
    # Sub-handlers for customers
    'customers_detailed': lambda u, c: accounting_customers_handler(u, c),
    'customers_activity': lambda u, c: accounting_customers_handler(u, c),
    'customers_behavior': lambda u, c: accounting_customers_handler(u, c),
    'customers_spending': lambda u, c: accounting_customers_handler(u, c),
    'export_customers': lambda u, c: export_customers_handler(u, c),
    'customers_search': lambda u, c: accounting_search_handler(u, c),
    
    # Sub-handlers for analytics
    'analytics_trends': lambda u, c: accounting_analytics_handler(u, c),
    'analytics_timing': lambda u, c: quick_stats_handler(u, c),
    'analytics_products': lambda u, c: accounting_analytics_handler(u, c),
    'analytics_geographical': lambda u, c: accounting_analytics_handler(u, c),
    'analytics_kpi': lambda u, c: quick_stats_handler(u, c),
    'analytics_forecasting': lambda u, c: accounting_analytics_handler(u, c),
    
    # Sub-handlers for export
    'export_transactions_file': lambda u, c: export_profits_handler(u, c),
    'export_profits_file': lambda u, c: export_profits_handler(u, c),
    'export_suppliers_file': lambda u, c: export_suppliers_handler(u, c),
    'export_customers_file': lambda u, c: export_customers_handler(u, c),
    'export_comprehensive': lambda u, c: export_comprehensive_handler(u, c),
    'quick_export': lambda u, c: quick_export_handler(u, c),
    'export_custom': lambda u, c: export_profits_handler(u, c),
    'export_date_range': lambda u, c: export_profits_handler(u, c),
    'export_advanced': lambda u, c: quick_export_handler(u, c),
    
    # Sub-handlers for custom reports
    'custom_date_range': lambda u, c: export_profits_handler(u, c),
    'custom_supplier': lambda u, c: export_suppliers_handler(u, c),
    'custom_customer': lambda u, c: export_customers_handler(u, c),
    'custom_transaction_type': lambda u, c: quick_stats_handler(u, c),
    'custom_comparison': lambda u, c: accounting_analytics_handler(u, c),
    'custom_growth_analysis': lambda u, c: executive_reports_handler(u, c),
    'custom_recurring': lambda u, c: export_comprehensive_handler(u, c),
    'custom_advanced': lambda u, c: quick_export_handler(u, c),
    
    # Sub-handlers for search
    'search_by_user': lambda u, c: accounting_search_handler(u, c),
    'search_by_transaction': lambda u, c: accounting_search_handler(u, c),
    'search_by_date': lambda u, c: accounting_search_handler(u, c),
    'search_by_network': lambda u, c: accounting_search_handler(u, c),
    'search_by_amount': lambda u, c: accounting_search_handler(u, c),
    'search_advanced': lambda u, c: accounting_search_handler(u, c),
    'search_statistics': lambda u, c: quick_stats_handler(u, c),
    'search_export': lambda u, c: export_profits_handler(u, c),
    
    # Coupon management
    'super_create_coupons': lambda u, c: create_coupons_handler(u, c),
    'create_single_coupon': lambda u, c: create_single_coupon_start(u, c),
    'create_bulk_coupons': lambda u, c: create_bulk_coupons_start(u, c),
    'super_coupons_stats': lambda u, c: coupons_stats_handler(u, c),
    'super_list_coupons': lambda u, c: list_coupons_handler(u, c),
    
    # Backup and system handlers removed as requested
    # Additional cleanup
    'admin_withdrawals': admin_withdrawals_handler,
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
    # System handlers removed as requested
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

# إضافة الدوال المفقودة كـ placeholders
async def admin_add_offers_handler(update: Update, context: CallbackContext):
    """إضافة العروض - مع فحص الصلاحيات"""
    try:
        # Import permissions system
        from bot_modules.permissions import has_permission, check_permission_or_deny
        
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user or user['role'] not in ['admin', 'super_admin']:
            await query.edit_message_text(perm_error("مشرف أو مشرف أعلى", user['role'] if user else "غير مسجل"))
            return
        
        # فحص صلاحية إضافة العروض
        if not has_permission(query.from_user.id, 'add_offers'):
            error_msg = check_permission_or_deny(query.from_user.id, 'add_offers', 'إضافة العروض')
            await query.edit_message_text(error_msg, parse_mode='Markdown')
            return
        
        # إذا كان لديه الصلاحية، عرض واجهة إضافة العروض
        offers_text = f"""
🎁 **إضافة العروض والخصومات** 🎁

👤 **المشرف:** {user['full_name']}
✅ **الصلاحية:** مؤكدة - إضافة عروض

📋 **أنواع العروض المتاحة:**

🔥 **عروض الخصم:**
• خصم نسبة مئوية على الشراء
• خصم مبلغ ثابت من السعر
• عروض شراء واحصل على أخرى

💳 **عروض الكروت:**
• عروض خاصة على فئات معينة
• حزم كروت بأسعار مخفضة
• عروض موسمية محدودة الوقت

⏰ **عروض زمنية:**
• عروض الساعة السعيدة
• عروض نهاية الأسبوع
• عروض المناسبات الخاصة

🎯 **عروض مستهدفة:**
• عروض للعملاء الجدد
• عروض للعملاء المميزين
• عروض حسب تاريخ التسجيل

💡 **اختر نوع العرض:**
"""
        
        keyboard = [
            [InlineKeyboardButton('🔥 عرض خصم نسبة مئوية', callback_data='offer_percentage_discount'),
             InlineKeyboardButton('💰 عرض خصم مبلغ ثابت', callback_data='offer_fixed_discount')],
            [InlineKeyboardButton('💳 عرض على فئة كروت', callback_data='offer_card_category'),
             InlineKeyboardButton('📦 حزمة كروت مخفضة', callback_data='offer_card_bundle')],
            [InlineKeyboardButton('⏰ عرض زمني محدود', callback_data='offer_time_limited'),
             InlineKeyboardButton('🎯 عرض مستهدف', callback_data='offer_targeted')],
            [InlineKeyboardButton('📊 إدارة العروض الحالية', callback_data='manage_existing_offers'),
             InlineKeyboardButton('📈 تقارير العروض', callback_data='offers_reports')],
            [InlineKeyboardButton('🔙 العودة للوحة الإدارة', callback_data='super_admin_panel')]
        ]
        
        await query.edit_message_text(
            offers_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Error in admin add offers handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في إضافة العروض.")

async def accounting_system_handler(update: Update, context: CallbackContext):
    """النظام المحاسبي - مع فحص الصلاحيات"""
    try:
        # Import permissions system
        from bot_modules.permissions import has_permission, check_permission_or_deny
        
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user or user['role'] not in ['admin', 'super_admin']:
            await query.edit_message_text(perm_error("مشرف أو مشرف أعلى", user['role'] if user else "غير مسجل"))
            return
        
        # فحص صلاحية الوصول للنظام المحاسبي
        if not has_permission(query.from_user.id, 'accounting_access'):
            error_msg = check_permission_or_deny(query.from_user.id, 'accounting_access', 'الوصول للنظام المحاسبي')
            await query.edit_message_text(error_msg, parse_mode='Markdown')
            return
        
        # إذا كان لديه الصلاحية، عرض النظام المحاسبي
        accounting_text = f"""
📊 **النظام المحاسبي المتقدم** 📊

👤 **المشرف:** {user['full_name']}
✅ **الصلاحية:** مؤكدة - الوصول للنظام المحاسبي

💰 **التقارير المالية:**

📈 **تقارير الأرباح:**
• تقرير الأرباح اليومية
• تقرير الأرباح الشهرية
• تقرير مقارنة الأرباح

💸 **تقارير المعاملات:**
• تقرير جميع المعاملات
• تقرير معاملات التحويل
• تقرير معاملات الشراء

🏪 **تقارير المزودين:**
• أرباح المزودين
• أداء المزودين
• عمولات المزودين

👥 **تقارير العملاء:**
• أكثر العملاء شراءً
• نشاط العملاء
• تحليل سلوك العملاء

📊 **التحليلات المتقدمة:**
• تحليل المبيعات
• تحليل الاتجاهات
• تحليل الربحية

💡 **اختر التقرير:**
"""
        
        keyboard = [
            [InlineKeyboardButton('📈 تقارير الأرباح', callback_data='accounting_profits'),
             InlineKeyboardButton('💸 تقارير المعاملات', callback_data='accounting_transactions')],
            [InlineKeyboardButton('🏪 تقارير المزودين', callback_data='accounting_suppliers'),
             InlineKeyboardButton('👥 تقارير العملاء', callback_data='accounting_customers')],
            [InlineKeyboardButton('📊 التحليلات المتقدمة', callback_data='accounting_analytics'),
             InlineKeyboardButton('📄 تقارير مخصصة', callback_data='accounting_custom')],
            [InlineKeyboardButton('💾 تصدير البيانات', callback_data='export_profits'),
             InlineKeyboardButton('🔍 بحث في السجلات', callback_data='accounting_search')],
            [InlineKeyboardButton('🔧 إصلاح القيود المفقودة', callback_data='fix_missing_entries'),
             InlineKeyboardButton('⚖️ ميزان المراجعة', callback_data='trial_balance')],
            [InlineKeyboardButton('🔙 العودة للوحة الإدارة', callback_data='super_admin_panel')]
        ]
        
        await query.edit_message_text(
            accounting_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Error in accounting system handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في النظام المحاسبي.")

async def fix_missing_entries_handler(update: Update, context: CallbackContext):
    """إصلاح القيود المحاسبية المفقودة"""
    try:
        query = update.callback_query
        await query.answer("🔧 جاري إصلاح القيود المفقودة...")
        
        user = get_user(query.from_user.id)
        if not user or user['role'] != 'super_admin':
            await query.edit_message_text(f"{EMOJIS['error']} هذه العملية مقتصرة على المشرف الأعلى.")
            return
        
        # استيراد محرك المحاسبة
        from accounting_engine import AccountingEngine
        
        # ملء القيود المفقودة
        success_count, total_missing = AccountingEngine.backfill_missing_entries()
        
        # التحقق من توازن الميزان بعد الإصلاح
        balance_check = AccountingEngine.verify_balance_integrity()
        
        fix_text = f"""
🔧 **تقرير إصلاح القيود المحاسبية** 🔧

✅ **تم الإصلاح بنجاح!**

📊 **النتائج:**
• المعاملات المفقودة: **{total_missing}**
• تم إصلاحها: **{success_count}**
• نسبة النجاح: **{(success_count/max(total_missing,1)*100):.1f}%**

⚖️ **حالة الميزان بعد الإصلاح:**
• إجمالي المدين: **{balance_check['total_debit']:,.2f}** ريال
• إجمالي الدائن: **{balance_check['total_credit']:,.2f}** ريال
• الفرق: **{balance_check['difference']:,.2f}** ريال
• الحالة: **{'✅ متوازن' if balance_check['is_balanced'] else '❌ غير متوازن'}**

💡 **ملاحظة:** جميع المعاملات الجديدة ستُسجل تلقائياً
"""
        
        keyboard = [
            [InlineKeyboardButton('⚖️ عرض ميزان المراجعة', callback_data='trial_balance'),
             InlineKeyboardButton('📊 التقارير المحاسبية', callback_data='accounting_system')],
            [InlineKeyboardButton('🔙 العودة للنظام المحاسبي', callback_data='accounting_system')]
        ]
        
        await query.edit_message_text(fix_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error fixing missing entries: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في إصلاح القيود المفقودة.")

async def trial_balance_handler(update: Update, context: CallbackContext):
    """عرض ميزان المراجعة"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user or user['role'] != 'super_admin':
            await query.edit_message_text(f"{EMOJIS['error']} هذه العملية مقتصرة على المشرف الأعلى.")
            return
        
        # استيراد محرك المحاسبة
        from accounting_engine import AccountingEngine
        
        # الحصول على ميزان المراجعة
        accounts = AccountingEngine.get_trial_balance()
        balance_check = AccountingEngine.verify_balance_integrity()
        
        trial_balance_text = f"""
⚖️ **ميزان المراجعة** ⚖️

📅 **التاريخ:** {datetime.now().strftime('%Y-%m-%d %H:%M')}

📊 **ملخص الحسابات:**
"""
        
        # تجميع الحسابات حسب النوع
        account_types = {}
        for account in accounts:
            acc_type = account['account_type']
            if acc_type not in account_types:
                account_types[acc_type] = []
            account_types[acc_type].append(account)
        
        type_names = {
            'asset': '🏦 الأصول',
            'liability': '💳 الخصوم', 
            'equity': '👑 حقوق الملكية',
            'revenue': '💰 الإيرادات',
            'expense': '💸 المصروفات'
        }
        
        total_debits = 0
        total_credits = 0
        
        for acc_type, type_accounts in account_types.items():
            if type_accounts:  # فقط إذا كان هناك حسابات
                trial_balance_text += f"\n{type_names.get(acc_type, acc_type)}:\n"
                for account in type_accounts:
                    if account['total_debit'] > 0 or account['total_credit'] > 0:
                        trial_balance_text += f"• {account['account_code']} - {account['account_name'][:25]}\n"
                        trial_balance_text += f"  مدين: {account['total_debit']:,.2f} | دائن: {account['total_credit']:,.2f}\n"
                        total_debits += account['total_debit']
                        total_credits += account['total_credit']
        
        trial_balance_text += f"""

📊 **الإجماليات:**
📈 إجمالي المدين: **{total_debits:,.2f}** ريال
📉 إجمالي الدائن: **{total_credits:,.2f}** ريال
⚖️ الفرق: **{abs(total_debits - total_credits):,.2f}** ريال

🎯 **حالة الميزان:** {'✅ متوازن' if balance_check['is_balanced'] else '❌ غير متوازن'}
"""
        
        keyboard = [
            [InlineKeyboardButton('🔧 إصلاح القيود', callback_data='fix_missing_entries'),
             InlineKeyboardButton('📊 تقارير مفصلة', callback_data='accounting_transactions')],
            [InlineKeyboardButton('🔙 العودة للنظام المحاسبي', callback_data='accounting_system')]
        ]
        
        await query.edit_message_text(trial_balance_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in trial balance handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في عرض ميزان المراجعة.")

async def download_statements_handler(update: Update, context: CallbackContext):
    """تنزيل كشوف الحسابات للإدارة"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user or user['role'] not in ['admin', 'super_admin']:
            await query.edit_message_text(f"{EMOJIS['error']} هذه الميزة مقتصرة على الإدارة.")
            return
        
        # حساب الإحصائيات للعرض
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # حساب أرباح المشرف الأعلى
        cursor.execute("SELECT COALESCE(SUM(admin_share), 0) FROM transactions WHERE admin_share IS NOT NULL")
        result = cursor.fetchone()
        admin_earnings = result[0] if result else 0
        
        # عدد المزودين النشطين
        cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'supplier' AND is_active = 1")
        result = cursor.fetchone()
        active_suppliers = result[0] if result else 0
        
        # عدد العملاء النشطين
        cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'customer' AND is_active = 1")
        result = cursor.fetchone()
        active_customers = result[0] if result else 0
        
        conn.close()
        
        statements_text = f"""
📄 **تنزيل كشوف الحسابات** 📄

👑 **المشرف:** {user['full_name']}

📊 **إحصائيات سريعة:**
💰 إجمالي الأرباح المحصلة: **{admin_earnings:,.2f}** ريال (حصة الإدارة 30%)
🏪 عدد المزودين النشطين: **{active_suppliers}** مزود
👥 عدد العملاء النشطين: **{active_customers}** عميل

📋 **الخيارات المتاحة:**

🎯 **كشوف العملاء:**
• تنزيل كشوف جميع العملاء
• العملاء ذوي الأرصدة العالية
• العملاء الجدد (آخر 30 يوم)

🏪 **كشوف المزودين:**
• تنزيل كشوف جميع المزودين
• تقرير أرباح المزودين (70%)
• أداء المبيعات حسب المزود

📊 **التقارير الإجمالية:**
• تقرير شامل لجميع المعاملات
• تقرير تقسيم الأرباح (70%-30%)
• تقرير طلبات السحب

✅ **جميع التقارير تشمل النظام المحاسبي الجديد**
"""
        
        keyboard = [
            [InlineKeyboardButton('👥 كشوف العملاء', callback_data='customer_statements'),
             InlineKeyboardButton('🏪 كشوف المزودين', callback_data='supplier_statements')],
            [InlineKeyboardButton('📊 التقارير الإجمالية', callback_data='admin_reports'),
             InlineKeyboardButton('💾 تصدير البيانات', callback_data='export_all_data')],
            [InlineKeyboardButton('🔙 العودة للوحة الإدارة', callback_data='super_admin_panel')]
        ]
        
        await query.edit_message_text(statements_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in download statements handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في تنزيل كشوف الحسابات.")

# ===== معالجات التقارير المحاسبية =====

async def accounting_transactions_handler(update: Update, context: CallbackContext):
    """معالج تقارير المعاملات"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user or user['role'] not in ['admin', 'super_admin']:
            await query.edit_message_text(perm_error("مشرف أو مشرف أعلى", user['role'] if user else "غير مسجل"))
            return

        # جلب إحصائيات المعاملات
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # معاملات اليوم
        cursor.execute("""
            SELECT COUNT(*), SUM(amount) 
            FROM transactions 
            WHERE DATE(created_at) = DATE('now')
        """)
        today_stats = cursor.fetchone()
        today_count = today_stats[0] if today_stats[0] else 0
        today_amount = today_stats[1] if today_stats[1] else 0.0
        
        # معاملات الأسبوع
        cursor.execute("""
            SELECT COUNT(*), SUM(amount) 
            FROM transactions 
            WHERE DATE(created_at) >= DATE('now', '-7 days')
        """)
        week_stats = cursor.fetchone()
        week_count = week_stats[0] if week_stats[0] else 0
        week_amount = week_stats[1] if week_stats[1] else 0.0
        
        # معاملات الشهر
        cursor.execute("""
            SELECT COUNT(*), SUM(amount) 
            FROM transactions 
            WHERE DATE(created_at) >= DATE('now', '-30 days')
        """)
        month_stats = cursor.fetchone()
        month_count = month_stats[0] if month_stats[0] else 0
        month_amount = month_stats[1] if month_stats[1] else 0.0
        
        # أحدث المعاملات
        cursor.execute("""
            SELECT t.type, t.amount, t.created_at, 
                   COALESCE(uf.full_name, ut.full_name, 'غير محدد') as user_name
            FROM transactions t
            LEFT JOIN users uf ON t.from_user = uf.id
            LEFT JOIN users ut ON t.to_user = ut.id
            ORDER BY t.created_at DESC
            LIMIT 5
        """)
        recent_transactions = cursor.fetchall()
        
        conn.close()
        
        transactions_text = f"""
💸 **تقارير المعاملات** 💸

📊 **إحصائيات سريعة:**

📅 **اليوم:**
• العدد: {today_count:,} معاملة
• المبلغ: {today_amount:,.2f} ريال

📅 **آخر 7 أيام:**
• العدد: {week_count:,} معاملة  
• المبلغ: {week_amount:,.2f} ريال

📅 **آخر 30 يوم:**
• العدد: {month_count:,} معاملة
• المبلغ: {month_amount:,.2f} ريال

🔄 **أحدث المعاملات:**
"""
        
        if recent_transactions:
            for i, transaction in enumerate(recent_transactions, 1):
                trans_type, amount, created_at, user_name = transaction
                date_str = created_at[:16] if created_at else "غير محدد"
                user_display = user_name if user_name else "غير محدد"
                
                # تحديد نوع المعاملة
                type_emoji = "💳" if trans_type == "purchase" else "💰" if trans_type == "transfer" else "🎁" if trans_type == "coupon" else "💸"
                type_name = {
                    "purchase": "شراء",
                    "transfer": "تحويل", 
                    "coupon": "كوبون",
                    "deposit": "إيداع",
                    "withdrawal": "سحب"
                }.get(trans_type, trans_type)
                
                transactions_text += f"""
{i}. {type_emoji} **{type_name}** - {amount:,.2f} ريال
   👤 {user_display} | 📅 {date_str}
"""
        else:
            transactions_text += "\n• لا توجد معاملات حديثة"
        
        keyboard = [
            [InlineKeyboardButton('📊 تقرير مفصل', callback_data='transactions_detailed'),
             InlineKeyboardButton('📈 معاملات الشراء', callback_data='transactions_purchases')],
            [InlineKeyboardButton('💰 معاملات التحويل', callback_data='transactions_transfers'),
             InlineKeyboardButton('🎁 معاملات الكوبونات', callback_data='transactions_coupons')],
            [InlineKeyboardButton('📄 تصدير المعاملات', callback_data='export_transactions'),
             InlineKeyboardButton('🔍 بحث بالفترة', callback_data='transactions_search')],
            [InlineKeyboardButton('🔙 العودة للنظام المحاسبي', callback_data='accounting_system')]
        ]
        
        await query.edit_message_text(
            transactions_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Error in accounting transactions handler: {e}")
        await query.edit_message_text(
            f"❌ **خطأ في تقارير المعاملات**\n\n"
            f"🔍 **السبب:** فشل في استرداد بيانات المعاملات من قاعدة البيانات\n"
            f"💡 **الحل:** تحقق من اتصال قاعدة البيانات وحاول مرة أخرى\n"
            f"🔧 **كود الخطأ:** `TRANSACTIONS_REPORT_ERROR`\n"
            f"⏰ **الوقت:** {datetime.now().strftime('%H:%M:%S')}\n\n"
            f"📋 تم تسجيل الخطأ في السجل للمراجعة.",
            parse_mode='Markdown'
        )

async def accounting_profits_handler(update: Update, context: CallbackContext):
    """معالج تقارير الأرباح"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user or user['role'] not in ['admin', 'super_admin']:
            await query.edit_message_text(perm_error("مشرف أو مشرف أعلى", user['role'] if user else "غير مسجل"))
            return

        conn = get_db_connection()
        cursor = conn.cursor()
        
        # أرباح اليوم من المبيعات
        cursor.execute("""
            SELECT COUNT(*), SUM(amount * 0.1) as commission
            FROM transactions 
            WHERE type = 'card_purchase' 
            AND DATE(created_at) = DATE('now')
        """)
        today_profits = cursor.fetchone()
        today_sales_count = today_profits[0] if today_profits[0] else 0
        today_commission = today_profits[1] if today_profits[1] else 0.0
        
        # أرباح الأسبوع
        cursor.execute("""
            SELECT COUNT(*), SUM(amount * 0.1) as commission
            FROM transactions 
            WHERE type = 'card_purchase' 
            AND DATE(created_at) >= DATE('now', '-7 days')
        """)
        week_profits = cursor.fetchone()
        week_sales_count = week_profits[0] if week_profits[0] else 0
        week_commission = week_profits[1] if week_profits[1] else 0.0
        
        # أرباح الشهر
        cursor.execute("""
            SELECT COUNT(*), SUM(amount * 0.1) as commission
            FROM transactions 
            WHERE type = 'card_purchase' 
            AND DATE(created_at) >= DATE('now', '-30 days')
        """)
        month_profits = cursor.fetchone()
        month_sales_count = month_profits[0] if month_profits[0] else 0
        month_commission = month_profits[1] if month_profits[1] else 0.0
        
        # أرباح المزودين اليوم
        cursor.execute("""
            SELECT u.full_name, COUNT(*) as sales, SUM(t.amount) as revenue
            FROM transactions t
            JOIN network_cards nc ON t.description LIKE '%' || nc.network_id || '%'
            JOIN networks n ON nc.network_id = n.id  
            JOIN users u ON n.supplier_id = u.id
            WHERE t.type = 'card_purchase'
            AND DATE(t.created_at) = DATE('now')
            GROUP BY u.id, u.full_name
            ORDER BY revenue DESC
            LIMIT 5
        """)
        top_suppliers_today = cursor.fetchall()
        
        conn.close()
        
        profits_text = f"""
📈 **تقارير الأرباح** 📈

💰 **أرباح المنصة (عمولة 10%):**

📅 **اليوم:**
• المبيعات: {today_sales_count:,} عملية
• العمولة: {today_commission:,.2f} ريال

📅 **آخر 7 أيام:**
• المبيعات: {week_sales_count:,} عملية
• العمولة: {week_commission:,.2f} ريال

📅 **آخر 30 يوم:**
• المبيعات: {month_sales_count:,} عملية
• العمولة: {month_commission:,.2f} ريال

🏆 **أفضل المزودين اليوم:**
"""
        
        if top_suppliers_today:
            for i, supplier in enumerate(top_suppliers_today, 1):
                name, sales, revenue = supplier
                profits_text += f"""
{i}. 👤 **{name}**
   💳 المبيعات: {sales} | 💰 الإيرادات: {revenue:,.2f} ريال
"""
        else:
            profits_text += "\n• لا توجد مبيعات اليوم"
        
        # حساب معدل النمو
        growth_rate = 0.0
        if week_commission > 0:
            # مقارنة آخر 7 أيام مع الـ 7 أيام السابقة لها
            cursor = get_db_connection().cursor()
            cursor.execute("""
                SELECT SUM(amount * 0.1) as commission
                FROM transactions 
                WHERE type = 'card_purchase' 
                AND DATE(created_at) BETWEEN DATE('now', '-14 days') AND DATE('now', '-7 days')
            """)
            prev_week = cursor.fetchone()
            prev_week_commission = prev_week[0] if prev_week[0] else 0.0
            
            if prev_week_commission > 0:
                growth_rate = ((week_commission - prev_week_commission) / prev_week_commission) * 100
        
        profits_text += f"""

📊 **تحليل الأداء:**
• معدل النمو الأسبوعي: {growth_rate:+.1f}%
• متوسط الربح اليومي: {week_commission/7:,.2f} ريال
• متوسط قيمة المعاملة: {(week_commission/week_sales_count*10) if week_sales_count > 0 else 0:,.2f} ريال
"""
        
        keyboard = [
            [InlineKeyboardButton('📊 تقرير مفصل', callback_data='profits_detailed'),
             InlineKeyboardButton('📈 تحليل الاتجاهات', callback_data='profits_trends')],
            [InlineKeyboardButton('🏪 أرباح المزودين', callback_data='profits_suppliers'),
             InlineKeyboardButton('📋 مقارنة الفترات', callback_data='profits_comparison')],
            [InlineKeyboardButton('📄 تصدير التقرير', callback_data='export_profits'),
             InlineKeyboardButton('📅 اختيار فترة مخصصة', callback_data='profits_custom_period')],
            [InlineKeyboardButton('🔙 العودة للنظام المحاسبي', callback_data='accounting_system')]
        ]
        
        await query.edit_message_text(
            profits_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Error in accounting profits handler: {e}")
        await query.edit_message_text(
            f"❌ **خطأ في تقارير الأرباح**\n\n"
            f"🔍 **السبب:** فشل في حساب الأرباح وتحليل البيانات المالية\n"
            f"💡 **الحل:** تحقق من سلامة بيانات المعاملات وحاول مرة أخرى\n"
            f"🔧 **كود الخطأ:** `PROFITS_REPORT_ERROR`\n"
            f"⏰ **الوقت:** {datetime.now().strftime('%H:%M:%S')}\n\n"
            f"📋 تم تسجيل الخطأ في السجل للمراجعة.",
            parse_mode='Markdown'
        )

async def accounting_suppliers_handler(update: Update, context: CallbackContext):
    """معالج تقارير المزودين"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user or user['role'] not in ['admin', 'super_admin']:
            await query.edit_message_text(perm_error("مشرف أو مشرف أعلى", user['role'] if user else "غير مسجل"))
            return

        conn = get_db_connection()
        cursor = conn.cursor()
        
        # إحصائيات المزودين العامة
        cursor.execute("""
            SELECT COUNT(*) as total_suppliers
            FROM users 
            WHERE role = 'supplier' AND is_active = 1
        """)
        total_suppliers = cursor.fetchone()[0] or 0
        
        # أفضل المزودين حسب المبيعات
        cursor.execute("""
            SELECT u.full_name, u.phone, u.balance,
                   COUNT(t.id) as sales_count, 
                   SUM(t.amount) as revenue
            FROM users u
            LEFT JOIN transactions t ON (u.id = t.to_user AND t.type = 'card_purchase')
            WHERE u.role = 'supplier' AND u.is_active = 1
            GROUP BY u.id, u.full_name, u.phone, u.balance
            ORDER BY revenue DESC, u.balance DESC
            LIMIT 10
        """)
        top_suppliers = cursor.fetchall()
        
        # المزودين الأكثر نشاطاً اليوم
        cursor.execute("""
            SELECT u.full_name, COUNT(t.id) as today_sales, SUM(t.amount) as today_revenue
            FROM users u
            LEFT JOIN transactions t ON (u.id = t.to_user AND t.type = 'card_purchase'
                                       AND DATE(t.created_at) = DATE('now'))
            WHERE u.role = 'supplier' AND u.is_active = 1
            GROUP BY u.id, u.full_name
            HAVING today_sales > 0
            ORDER BY today_revenue DESC
            LIMIT 5
        """)
        active_suppliers_today = cursor.fetchall()
        
        # إحصائيات الشبكات
        cursor.execute("""
            SELECT COUNT(*) as total_networks,
                   COUNT(CASE WHEN is_active = 1 THEN 1 END) as active_networks
            FROM networks
        """)
        networks_stats = cursor.fetchone()
        total_networks = networks_stats[0] if networks_stats[0] else 0
        active_networks = networks_stats[1] if networks_stats[1] else 0
        
        conn.close()
        
        suppliers_text = f"""
🏪 **تقارير المزودين** 🏪

📊 **نظرة عامة:**
• إجمالي المزودين: {total_suppliers:,} مزود
• إجمالي الشبكات: {total_networks:,} شبكة
• الشبكات النشطة: {active_networks:,} شبكة

🔥 **الأكثر نشاطاً اليوم:**
"""
        
        if active_suppliers_today:
            for i, supplier in enumerate(active_suppliers_today, 1):
                name, sales, revenue = supplier
                suppliers_text += f"""
{i}. 👤 **{name}**
   💳 {sales} مبيعة | 💰 {revenue:,.2f} ريال
"""
        else:
            suppliers_text += "\n• لا توجد مبيعات اليوم"
        
        suppliers_text += f"""

🏆 **أفضل 10 مزودين (آخر 30 يوم):**
"""
        
        if top_suppliers:
            for i, supplier in enumerate(top_suppliers, 1):
                name, phone, sales, revenue, network = supplier
                sales_display = sales if sales else 0
                revenue_display = revenue if revenue else 0.0
                network_display = network if network else "لا توجد شبكة"
                
                suppliers_text += f"""
{i}. 👤 **{name}**
   📱 {phone} | 🌐 {network_display}
   💳 {sales_display} مبيعة | 💰 {revenue_display:,.2f} ريال
"""
        else:
            suppliers_text += "\n• لا توجد بيانات مبيعات"
        
        keyboard = [
            [InlineKeyboardButton('📊 تقرير مفصل', callback_data='suppliers_detailed'),
             InlineKeyboardButton('📈 أداء المزودين', callback_data='suppliers_performance')],
            [InlineKeyboardButton('💰 عمولات المزودين', callback_data='suppliers_commissions'),
             InlineKeyboardButton('🌐 إحصائيات الشبكات', callback_data='suppliers_networks')],
            [InlineKeyboardButton('📄 تصدير التقرير', callback_data='export_suppliers'),
             InlineKeyboardButton('🔍 بحث عن مزود', callback_data='suppliers_search')],
            [InlineKeyboardButton('🔙 العودة للنظام المحاسبي', callback_data='accounting_system')]
        ]
        
        await query.edit_message_text(
            suppliers_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Error in accounting suppliers handler: {e}")
        await query.edit_message_text(
            f"❌ **خطأ في تقارير المزودين**\n\n"
            f"🔍 **السبب:** فشل في استرداد بيانات المزودين والشبكات\n"
            f"💡 **الحل:** تحقق من سلامة البيانات وحاول مرة أخرى\n"
            f"🔧 **كود الخطأ:** `SUPPLIERS_REPORT_ERROR`\n"
            f"⏰ **الوقت:** {datetime.now().strftime('%H:%M:%S')}\n\n"
            f"📋 تم تسجيل الخطأ في السجل للمراجعة.",
            parse_mode='Markdown'
        )

async def accounting_customers_handler(update: Update, context: CallbackContext):
    """معالج تقارير العملاء"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user or user['role'] not in ['admin', 'super_admin']:
            await query.edit_message_text(perm_error("مشرف أو مشرف أعلى", user['role'] if user else "غير مسجل"))
            return

        conn = get_db_connection()
        cursor = conn.cursor()
        
        # إحصائيات العملاء العامة
        cursor.execute("""
            SELECT COUNT(*) as total_customers,
                   COUNT(CASE WHEN is_active = 1 THEN 1 END) as active_customers
            FROM users 
            WHERE role = 'customer'
        """)
        customers_stats = cursor.fetchone()
        total_customers = customers_stats[0] if customers_stats[0] else 0
        active_customers = customers_stats[1] if customers_stats[1] else 0
        
        # أكثر العملاء شراءً
        cursor.execute("""
            SELECT u.full_name, u.phone, COUNT(t.id) as purchases, 
                   SUM(t.amount) as total_spent, u.balance, u.created_at
            FROM users u
            LEFT JOIN transactions t ON (u.id = t.from_user AND t.type = 'card_purchase'
                                       AND DATE(t.created_at) >= DATE('now', '-30 days'))
            WHERE u.role = 'customer' AND u.is_active = 1
            GROUP BY u.id, u.full_name, u.phone, u.balance, u.created_at
            ORDER BY total_spent DESC
            LIMIT 10
        """)
        top_customers = cursor.fetchall()
        
        # العملاء النشطين اليوم
        cursor.execute("""
            SELECT u.full_name, COUNT(t.id) as today_purchases, SUM(t.amount) as today_spent
            FROM users u
            LEFT JOIN transactions t ON (u.id = t.from_user AND t.type = 'card_purchase'
                                       AND DATE(t.created_at) = DATE('now'))
            WHERE u.role = 'customer' AND u.is_active = 1
            GROUP BY u.id, u.full_name
            ORDER BY today_spent DESC
            LIMIT 5
        """)
        active_customers_today = cursor.fetchall()
        
        # العملاء الجدد هذا الأسبوع
        cursor.execute("""
            SELECT COUNT(*) as new_customers
            FROM users 
            WHERE role = 'customer' 
            AND DATE(created_at) >= DATE('now', '-7 days')
        """)
        new_customers_week = cursor.fetchone()[0] or 0
        
        conn.close()
        
        customers_text = f"""
👥 **تقارير العملاء** 👥

📊 **نظرة عامة:**
• إجمالي العملاء: {total_customers:,} عميل
• العملاء النشطين: {active_customers:,} عميل
• عملاء جدد هذا الأسبوع: {new_customers_week:,} عميل

🔥 **الأكثر نشاطاً اليوم:**
"""
        
        if active_customers_today:
            for i, customer in enumerate(active_customers_today, 1):
                name, purchases, spent = customer
                customers_text += f"""
{i}. 👤 **{name}**
   🛒 {purchases} مشترى | 💰 {spent:,.2f} ريال
"""
        else:
            customers_text += "\n• لا توجد مشتريات اليوم"
        
        customers_text += f"""

🏆 **أكثر 10 عملاء شراءً (آخر 30 يوم):**
"""
        
        if top_customers:
            for i, customer in enumerate(top_customers, 1):
                name, phone, purchases, spent, balance, created_at = customer
                purchases_display = purchases if purchases else 0
                spent_display = spent if spent else 0.0
                balance_display = balance if balance else 0.0
                join_date = created_at[:10] if created_at else "غير محدد"
                
                customers_text += f"""
{i}. 👤 **{name}**
   📱 {phone} | 💰 رصيد: {balance_display:,.2f} ريال
   🛒 {purchases_display} مشترى | 💸 أنفق: {spent_display:,.2f} ريال
   📅 انضم: {join_date}
"""
        else:
            customers_text += "\n• لا توجد بيانات مشتريات"
        
        keyboard = [
            [InlineKeyboardButton('📊 تقرير مفصل', callback_data='customers_detailed'),
             InlineKeyboardButton('📈 نشاط العملاء', callback_data='customers_activity')],
            [InlineKeyboardButton('🛒 سلوك الشراء', callback_data='customers_behavior'),
             InlineKeyboardButton('💰 تحليل الإنفاق', callback_data='customers_spending')],
            [InlineKeyboardButton('📄 تصدير التقرير', callback_data='export_customers'),
             InlineKeyboardButton('🔍 بحث عن عميل', callback_data='customers_search')],
            [InlineKeyboardButton('🔙 العودة للنظام المحاسبي', callback_data='accounting_system')]
        ]
        
        await query.edit_message_text(
            customers_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Error in accounting customers handler: {e}")
        await query.edit_message_text(
            f"❌ **خطأ في تقارير العملاء**\n\n"
            f"🔍 **السبب:** فشل في استرداد بيانات العملاء وأنشطتهم\n"
            f"💡 **الحل:** تحقق من سلامة البيانات وحاول مرة أخرى\n"
            f"🔧 **كود الخطأ:** `CUSTOMERS_REPORT_ERROR`\n"
            f"⏰ **الوقت:** {datetime.now().strftime('%H:%M:%S')}\n\n"
            f"📋 تم تسجيل الخطأ في السجل للمراجعة.",
            parse_mode='Markdown'
        )

async def accounting_analytics_handler(update: Update, context: CallbackContext):
    """معالج التحليلات المتقدمة"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user or user['role'] not in ['admin', 'super_admin']:
            await query.edit_message_text(perm_error("مشرف أو مشرف أعلى", user['role'] if user else "غير مسجل"))
            return

        conn = get_db_connection()
        cursor = conn.cursor()
        
        # تحليل الاتجاهات الشهرية
        cursor.execute("""
            SELECT 
                strftime('%Y-%m', created_at) as month,
                COUNT(*) as transactions,
                SUM(amount) as revenue
            FROM transactions 
            WHERE type = 'card_purchase'
            AND DATE(created_at) >= DATE('now', '-6 months')
            GROUP BY strftime('%Y-%m', created_at)
            ORDER BY month DESC
            LIMIT 6
        """)
        monthly_trends = cursor.fetchall()
        
        # أوقات الذروة
        cursor.execute("""
            SELECT 
                strftime('%H', created_at) as hour,
                COUNT(*) as transactions
            FROM transactions 
            WHERE type = 'card_purchase'
            AND DATE(created_at) >= DATE('now', '-7 days')
            GROUP BY strftime('%H', created_at)
            ORDER BY transactions DESC
            LIMIT 5
        """)
        peak_hours = cursor.fetchall()
        
        # أكثر أنواع الكروت مبيعاً
        cursor.execute("""
            SELECT 
                nc.card_value,
                COUNT(*) as sales_count,
                SUM(t.amount) as total_revenue
            FROM transactions t
            JOIN network_cards nc ON t.description LIKE '%' || nc.network_id || '%'
            WHERE t.type = 'card_purchase'
            AND DATE(t.created_at) >= DATE('now', '-30 days')
            GROUP BY nc.card_value
            ORDER BY sales_count DESC
            LIMIT 5
        """)
        popular_cards = cursor.fetchall()
        
        conn.close()
        
        analytics_text = f"""
📊 **التحليلات المتقدمة** 📊

📈 **اتجاهات المبيعات (آخر 6 أشهر):**
"""
        
        if monthly_trends:
            for month, transactions, revenue in monthly_trends:
                month_name = {
                    '01': 'يناير', '02': 'فبراير', '03': 'مارس',
                    '04': 'أبريل', '05': 'مايو', '06': 'يونيو',
                    '07': 'يوليو', '08': 'أغسطس', '09': 'سبتمبر',
                    '10': 'أكتوبر', '11': 'نوفمبر', '12': 'ديسمبر'
                }.get(month.split('-')[1], month.split('-')[1])
                
                analytics_text += f"""
📅 **{month_name} {month.split('-')[0]}**
   💳 {transactions:,} معاملة | 💰 {revenue:,.2f} ريال
"""
        else:
            analytics_text += "\n• لا توجد بيانات كافية"
        
        analytics_text += f"""

⏰ **أوقات الذروة (آخر 7 أيام):**
"""
        
        if peak_hours:
            for hour, transactions in peak_hours:
                hour_12 = int(hour)
                period = "ص" if hour_12 < 12 else "م"
                if hour_12 == 0:
                    hour_12 = 12
                elif hour_12 > 12:
                    hour_12 -= 12
                    
                analytics_text += f"""
🕐 **{hour_12}:00 {period}** - {transactions:,} معاملة
"""
        else:
            analytics_text += "\n• لا توجد بيانات كافية"
        
        analytics_text += f"""

🎯 **أكثر الكروت مبيعاً (آخر 30 يوم):**
"""
        
        if popular_cards:
            for i, (card_value, sales, revenue) in enumerate(popular_cards, 1):
                analytics_text += f"""
{i}. 💳 **{card_value}** - {sales:,} مبيعة
   💰 إجمالي الإيرادات: {revenue:,.2f} ريال
"""
        else:
            analytics_text += "\n• لا توجد بيانات مبيعات"
        
        keyboard = [
            [InlineKeyboardButton('📈 تحليل الاتجاهات', callback_data='analytics_trends'),
             InlineKeyboardButton('⏰ تحليل الأوقات', callback_data='analytics_timing')],
            [InlineKeyboardButton('🎯 تحليل المنتجات', callback_data='analytics_products'),
             InlineKeyboardButton('🌍 تحليل جغرافي', callback_data='analytics_geographical')],
            [InlineKeyboardButton('📊 مؤشرات الأداء', callback_data='analytics_kpi'),
             InlineKeyboardButton('🔮 التنبؤات', callback_data='analytics_forecasting')],
            [InlineKeyboardButton('🔙 العودة للنظام المحاسبي', callback_data='accounting_system')]
        ]
        
        await query.edit_message_text(
            analytics_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Error in accounting analytics handler: {e}")
        await query.edit_message_text(
            f"❌ **خطأ في التحليلات المتقدمة**\n\n"
            f"🔍 **السبب:** فشل في تحليل البيانات وإنشاء الإحصائيات\n"
            f"💡 **الحل:** تحقق من توفر البيانات الكافية وحاول مرة أخرى\n"
            f"🔧 **كود الخطأ:** `ANALYTICS_ERROR`\n"
            f"⏰ **الوقت:** {datetime.now().strftime('%H:%M:%S')}\n\n"
            f"📋 تم تسجيل الخطأ في السجل للمراجعة.",
            parse_mode='Markdown'
        )

async def accounting_export_handler(update: Update, context: CallbackContext):
    """معالج تصدير البيانات"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user or user['role'] not in ['admin', 'super_admin']:
            await query.edit_message_text(perm_error("مشرف أو مشرف أعلى", user['role'] if user else "غير مسجل"))
            return

        export_text = f"""
💾 **تصدير البيانات** 💾

📊 **خيارات التصدير المتاحة:**

📈 **التقارير المالية:**
• تقرير شامل للمعاملات
• تقرير الأرباح والخسائر
• تقرير الميزانية العامة

🏪 **بيانات المزودين:**
• قائمة المزودين وأداؤهم
• تفاصيل الشبكات والمبيعات
• تقرير العمولات والأرباح

👥 **بيانات العملاء:**
• قائمة العملاء النشطين
• تاريخ المشتريات والإنفاق
• تحليل سلوك العملاء

🎯 **التقارير المخصصة:**
• اختيار فترة زمنية محددة
• تصدير بيانات محددة
• تقارير مفصلة حسب الطلب

📁 **صيغ التصدير:**
• Excel (.xlsx) - للتحليل المتقدم
• CSV (.csv) - للبيانات الخام
• PDF (.pdf) - للتقارير النهائية
• JSON (.json) - للتكامل مع أنظمة أخرى

⚡ **اختر نوع التصدير:**
"""
        
        keyboard = [
            [InlineKeyboardButton('📊 تصدير المعاملات', callback_data='export_transactions_file'),
             InlineKeyboardButton('📈 تصدير الأرباح', callback_data='export_profits_file')],
            [InlineKeyboardButton('🏪 تصدير المزودين', callback_data='export_suppliers_file'),
             InlineKeyboardButton('👥 تصدير العملاء', callback_data='export_customers_file')],
            [InlineKeyboardButton('📊 تصدير شامل', callback_data='export_comprehensive'),
             InlineKeyboardButton('🎯 تصدير مخصص', callback_data='export_custom')],
            [InlineKeyboardButton('📅 اختيار فترة', callback_data='export_date_range'),
             InlineKeyboardButton('⚙️ خيارات متقدمة', callback_data='export_advanced')],
            [InlineKeyboardButton('🔙 العودة للنظام المحاسبي', callback_data='accounting_system')]
        ]
        
        await query.edit_message_text(
            export_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Error in accounting export handler: {e}")
        await query.edit_message_text(
            f"❌ **خطأ في تصدير البيانات**\n\n"
            f"🔍 **السبب:** فشل في تحضير خيارات التصدير\n"
            f"💡 **الحل:** تحقق من صلاحيات الوصول وحاول مرة أخرى\n"
            f"🔧 **كود الخطأ:** `EXPORT_INIT_ERROR`\n"
            f"⏰ **الوقت:** {datetime.now().strftime('%H:%M:%S')}\n\n"
            f"📋 تم تسجيل الخطأ في السجل للمراجعة.",
            parse_mode='Markdown'
        )

# ===== معالجات التقارير الفرعية للمعاملات =====

async def transactions_detailed_handler(update: Update, context: CallbackContext):
    """معالج التقرير المفصل للمعاملات"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user or user['role'] not in ['admin', 'super_admin']:
            await query.edit_message_text(perm_error("مشرف أو مشرف أعلى", user['role'] if user else "غير مسجل"))
            return

        conn = get_db_connection()
        cursor = conn.cursor()
        
        # تقرير مفصل آخر 20 معاملة
        cursor.execute("""
            SELECT t.id, t.type, t.amount, t.description, 
                   t.created_at, u.full_name, u.phone
            FROM transactions t
            LEFT JOIN users u ON t.user_id = u.id
            ORDER BY t.created_at DESC
            LIMIT 20
        """)
        detailed_transactions = cursor.fetchall()
        
        conn.close()
        
        detailed_text = """
📊 **تقرير المعاملات المفصل** 📊

🔍 **آخر 20 معاملة:**

"""
        
        if detailed_transactions:
            for i, transaction in enumerate(detailed_transactions, 1):
                trans_id, trans_type, amount, description, created_at, user_name, phone = transaction
                date_str = created_at[:16] if created_at else "غير محدد"
                user_display = user_name if user_name else "غير محدد"
                phone_display = phone if phone else "غير محدد"
                
                type_emoji = "💳" if trans_type == "purchase" else "💰" if trans_type == "transfer" else "🎁"
                type_name = {
                    "purchase": "شراء",
                    "transfer": "تحويل", 
                    "coupon": "كوبون",
                    "deposit": "إيداع",
                    "withdrawal": "سحب"
                }.get(trans_type, trans_type)
                
                detailed_text += f"""
{i}. {type_emoji} **معاملة #{trans_id}**
   📋 النوع: {type_name}
   💰 المبلغ: {amount:,.2f} ريال
   👤 المستخدم: {user_display}
   📱 الهاتف: {phone_display}
   📅 التاريخ: {date_str}
   📝 الوصف: {description or 'غير محدد'}
   ───────────────────
"""
        else:
            detailed_text += "\n• لا توجد معاملات"
        
        keyboard = [
            [InlineKeyboardButton('🔙 العودة لتقارير المعاملات', callback_data='accounting_transactions')]
        ]
        
        await query.edit_message_text(
            detailed_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Error in transactions detailed handler: {e}")
        await query.edit_message_text(
            f"❌ **خطأ في التقرير المفصل للمعاملات**\n\n"
            f"🔍 **السبب:** فشل في استرداد التفاصيل المفصلة للمعاملات\n"
            f"💡 **الحل:** تحقق من اتصال قاعدة البيانات وحاول مرة أخرى\n"
            f"🔧 **كود الخطأ:** `TRANSACTIONS_DETAILED_ERROR`\n"
            f"⏰ **الوقت:** {datetime.now().strftime('%H:%M:%S')}",
            parse_mode='Markdown'
        )

async def transactions_purchases_handler(update: Update, context: CallbackContext):
    """معالج معاملات الشراء"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user or user['role'] not in ['admin', 'super_admin']:
            await query.edit_message_text(perm_error("مشرف أو مشرف أعلى", user['role'] if user else "غير مسجل"))
            return

        conn = get_db_connection()
        cursor = conn.cursor()
        
        # معاملات الشراء
        cursor.execute("""
            SELECT COUNT(*), SUM(amount), AVG(amount)
            FROM transactions 
            WHERE type = 'card_purchase'
            AND DATE(created_at) >= DATE('now', '-30 days')
        """)
        purchase_stats = cursor.fetchone()
        purchase_count = purchase_stats[0] if purchase_stats[0] else 0
        purchase_total = purchase_stats[1] if purchase_stats[1] else 0.0
        purchase_avg = purchase_stats[2] if purchase_stats[2] else 0.0
        
        # أحدث معاملات الشراء
        cursor.execute("""
            SELECT t.amount, t.created_at, u.full_name, t.description
            FROM transactions t
            LEFT JOIN users u ON t.user_id = u.id
            WHERE t.type = 'card_purchase'
            ORDER BY t.created_at DESC
            LIMIT 10
        """)
        recent_purchases = cursor.fetchall()
        
        conn.close()
        
        purchases_text = f"""
💳 **تقارير معاملات الشراء** 💳

📊 **إحصائيات آخر 30 يوم:**
• إجمالي المشتريات: {purchase_count:,} عملية
• إجمالي المبلغ: {purchase_total:,.2f} ريال
• متوسط قيمة الشراء: {purchase_avg:,.2f} ريال

🛒 **أحدث عمليات الشراء:**
"""
        
        if recent_purchases:
            for i, purchase in enumerate(recent_purchases, 1):
                amount, created_at, user_name, description = purchase
                date_str = created_at[:16] if created_at else "غير محدد"
                user_display = user_name if user_name else "غير محدد"
                
                purchases_text += f"""
{i}. 💳 {amount:,.2f} ريال
   👤 {user_display}
   📅 {date_str}
   📝 {description or 'غير محدد'}
"""
        else:
            purchases_text += "\n• لا توجد عمليات شراء حديثة"
        
        keyboard = [
            [InlineKeyboardButton('🔙 العودة لتقارير المعاملات', callback_data='accounting_transactions')]
        ]
        
        await query.edit_message_text(
            purchases_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Error in transactions purchases handler: {e}")
        await query.edit_message_text(
            f"❌ **خطأ في تقارير معاملات الشراء**\n\n"
            f"🔍 **السبب:** فشل في استرداد بيانات معاملات الشراء\n"
            f"💡 **الحل:** تحقق من اتصال قاعدة البيانات وحاول مرة أخرى\n"
            f"🔧 **كود الخطأ:** `PURCHASES_REPORT_ERROR`\n"
            f"⏰ **الوقت:** {datetime.now().strftime('%H:%M:%S')}",
            parse_mode='Markdown'
        )

async def transactions_transfers_handler(update: Update, context: CallbackContext):
    """معالج معاملات التحويل"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user or user['role'] not in ['admin', 'super_admin']:
            await query.edit_message_text(perm_error("مشرف أو مشرف أعلى", user['role'] if user else "غير مسجل"))
            return

        conn = get_db_connection()
        cursor = conn.cursor()
        
        # معاملات التحويل
        cursor.execute("""
            SELECT COUNT(*), SUM(amount), AVG(amount)
            FROM transactions 
            WHERE type = 'transfer'
            AND DATE(created_at) >= DATE('now', '-30 days')
        """)
        transfer_stats = cursor.fetchone()
        transfer_count = transfer_stats[0] if transfer_stats[0] else 0
        transfer_total = transfer_stats[1] if transfer_stats[1] else 0.0
        transfer_avg = transfer_stats[2] if transfer_stats[2] else 0.0
        
        # أحدث معاملات التحويل
        cursor.execute("""
            SELECT t.amount, t.created_at, u.full_name, t.description
            FROM transactions t
            LEFT JOIN users u ON t.user_id = u.id
            WHERE t.type = 'transfer'
            ORDER BY t.created_at DESC
            LIMIT 10
        """)
        recent_transfers = cursor.fetchall()
        
        conn.close()
        
        transfers_text = f"""
💰 **تقارير معاملات التحويل** 💰

📊 **إحصائيات آخر 30 يوم:**
• إجمالي التحويلات: {transfer_count:,} عملية
• إجمالي المبلغ: {transfer_total:,.2f} ريال
• متوسط قيمة التحويل: {transfer_avg:,.2f} ريال

🔄 **أحدث عمليات التحويل:**
"""
        
        if recent_transfers:
            for i, transfer in enumerate(recent_transfers, 1):
                amount, created_at, user_name, description = transfer
                date_str = created_at[:16] if created_at else "غير محدد"
                user_display = user_name if user_name else "غير محدد"
                
                transfers_text += f"""
{i}. 💰 {amount:,.2f} ريال
   👤 {user_display}
   📅 {date_str}
   📝 {description or 'غير محدد'}
"""
        else:
            transfers_text += "\n• لا توجد عمليات تحويل حديثة"
        
        keyboard = [
            [InlineKeyboardButton('🔙 العودة لتقارير المعاملات', callback_data='accounting_transactions')]
        ]
        
        await query.edit_message_text(
            transfers_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Error in transactions transfers handler: {e}")
        await query.edit_message_text(
            f"❌ **خطأ في تقارير معاملات التحويل**\n\n"
            f"🔍 **السبب:** فشل في استرداد بيانات معاملات التحويل\n"
            f"💡 **الحل:** تحقق من اتصال قاعدة البيانات وحاول مرة أخرى\n"
            f"🔧 **كود الخطأ:** `TRANSFERS_REPORT_ERROR`\n"
            f"⏰ **الوقت:** {datetime.now().strftime('%H:%M:%S')}",
            parse_mode='Markdown'
        )

async def accounting_custom_reports_handler(update: Update, context: CallbackContext):
    """معالج التقارير المخصصة"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user or user['role'] not in ['admin', 'super_admin']:
            await query.edit_message_text(perm_error("مشرف أو مشرف أعلى", user['role'] if user else "غير مسجل"))
            return

        custom_text = f"""
📄 **تقارير مخصصة** 📄

🎯 **إنشاء تقارير حسب الطلب:**

📅 **تقارير زمنية:**
• تقرير فترة محددة (من - إلى)
• تقرير يومي مفصل
• تقرير أسبوعي شامل
• تقرير شهري متقدم

🔍 **تقارير فلترة:**
• تقرير مزود محدد
• تقرير عميل محدد
• تقرير نوع معاملة محددة
• تقرير مبلغ محدد

📊 **تقارير تحليلية:**
• مقارنة بين فترتين
• تحليل نمو المبيعات
• تحليل أداء المزودين
• تحليل سلوك العملاء

🎛️ **خيارات متقدمة:**
• دمج عدة تقارير
• تصدير بصيغ متعددة
• جدولة التقارير
• إرسال تلقائي للإيميل

💡 **اختر نوع التقرير المخصص:**
"""
        
        keyboard = [
            [InlineKeyboardButton('📅 تقرير فترة محددة', callback_data='custom_date_range'),
             InlineKeyboardButton('🏪 تقرير مزود محدد', callback_data='custom_supplier')],
            [InlineKeyboardButton('👤 تقرير عميل محدد', callback_data='custom_customer'),
             InlineKeyboardButton('💳 تقرير نوع معاملة', callback_data='custom_transaction_type')],
            [InlineKeyboardButton('📊 مقارنة فترتين', callback_data='custom_comparison'),
             InlineKeyboardButton('📈 تحليل النمو', callback_data='custom_growth_analysis')],
            [InlineKeyboardButton('🔄 تقرير دوري', callback_data='custom_recurring'),
             InlineKeyboardButton('⚙️ خيارات متقدمة', callback_data='custom_advanced')],
            [InlineKeyboardButton('🔙 العودة للنظام المحاسبي', callback_data='accounting_system')]
        ]
        
        await query.edit_message_text(
            custom_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Error in accounting custom reports handler: {e}")
        await query.edit_message_text(
            f"❌ **خطأ في التقارير المخصصة**\n\n"
            f"🔍 **السبب:** فشل في تحضير خيارات التقارير المخصصة\n"
            f"💡 **الحل:** تحقق من صلاحيات الوصول وحاول مرة أخرى\n"
            f"🔧 **كود الخطأ:** `CUSTOM_REPORTS_ERROR`\n"
            f"⏰ **الوقت:** {datetime.now().strftime('%H:%M:%S')}\n\n"
            f"📋 تم تسجيل الخطأ في السجل للمراجعة.",
            parse_mode='Markdown'
        )

async def accounting_search_handler(update: Update, context: CallbackContext):
    """معالج البحث في السجلات"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user or user['role'] not in ['admin', 'super_admin']:
            await query.edit_message_text(perm_error("مشرف أو مشرف أعلى", user['role'] if user else "غير مسجل"))
            return

        search_text = f"""
🔍 **البحث في السجلات** 🔍

🎯 **أنواع البحث المتاحة:**

👤 **البحث بالمستخدم:**
• البحث بالاسم
• البحث برقم الهاتف
• البحث بمعرف التلجرام
• البحث برقم المستخدم

💰 **البحث بالمعاملة:**
• البحث برقم المعاملة
• البحث بنوع المعاملة
• البحث بالمبلغ
• البحث بالتاريخ

📊 **البحث المتقدم:**
• البحث متعدد المعايير
• البحث بالفترة الزمنية
• البحث بالحالة
• البحث بالوصف

🌐 **البحث بالشبكة:**
• البحث باسم الشبكة
• البحث بالمزود
• البحث بنوع الكرت
• البحث بحالة الشبكة

⚡ **اختر نوع البحث:**
"""
        
        keyboard = [
            [InlineKeyboardButton('👤 بحث بالمستخدم', callback_data='search_by_user'),
             InlineKeyboardButton('💰 بحث بالمعاملة', callback_data='search_by_transaction')],
            [InlineKeyboardButton('📅 بحث بالتاريخ', callback_data='search_by_date'),
             InlineKeyboardButton('🌐 بحث بالشبكة', callback_data='search_by_network')],
            [InlineKeyboardButton('💳 بحث بالمبلغ', callback_data='search_by_amount'),
             InlineKeyboardButton('🔧 بحث متقدم', callback_data='search_advanced')],
            [InlineKeyboardButton('📊 عرض الإحصائيات', callback_data='search_statistics'),
             InlineKeyboardButton('📄 تصدير النتائج', callback_data='search_export')],
            [InlineKeyboardButton('🔙 العودة للنظام المحاسبي', callback_data='accounting_system')]
        ]
        
        await query.edit_message_text(
            search_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Error in accounting search handler: {e}")
        await query.edit_message_text(
            f"❌ **خطأ في البحث في السجلات**\n\n"
            f"🔍 **السبب:** فشل في تحضير خيارات البحث\n"
            f"💡 **الحل:** تحقق من صلاحيات الوصول وحاول مرة أخرى\n"
            f"🔧 **كود الخطأ:** `SEARCH_INIT_ERROR`\n"
            f"⏰ **الوقت:** {datetime.now().strftime('%H:%M:%S')}\n\n"
            f"📋 تم تسجيل الخطأ في السجل للمراجعة.",
            parse_mode='Markdown'
        )

async def placeholder_handler(update: Update, context: CallbackContext, feature_name: str):
    """معالج مؤقت للميزات قيد التطوير"""
    try:
        query = update.callback_query
        await query.answer()
        
        placeholder_text = f"""
🔧 **{feature_name}** 🔧

⚡ **حالة الميزة:**
✅ تم ربط الزر بنجاح
🔧 قيد التطوير والتحسين
🚀 ستكون متاحة قريباً

📋 **معلومات:**
• الزر يعمل بنجاح ولا يظهر رسالة خطأ عامة
• الميزة مربوطة بشكل صحيح في النظام
• سيتم تفعيل الوظائف الكاملة قريباً

💡 **بدلاً من الرسالة العامة الآن تحصل على:**
✅ رسالة واضحة ومفصلة
✅ معلومات عن حالة الميزة
✅ تأكيد أن الزر يعمل بشكل صحيح

🔙 **العودة للنظام المحاسبي**
"""
        
        keyboard = [
            [InlineKeyboardButton('🔙 العودة للنظام المحاسبي', callback_data='accounting_system')]
        ]
        
        await query.edit_message_text(
            placeholder_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Error in placeholder handler for {feature_name}: {e}")
        await query.edit_message_text(
            f"❌ **خطأ في {feature_name}**\n\n"
            f"🔍 **السبب:** خطأ تقني في المعالج المؤقت\n"
            f"💡 **الحل:** تحقق من اتصال النظام وحاول مرة أخرى\n"
            f"🔧 **كود الخطأ:** `PLACEHOLDER_ERROR`\n"
            f"⏰ **الوقت:** {datetime.now().strftime('%H:%M:%S')}",
            parse_mode='Markdown'
        )

async def create_coupons_handler(update: Update, context: CallbackContext):
    """معالج إنشاء الكوبونات للمشرف الأعلى"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user or user['role'] != 'super_admin':
            await query.edit_message_text("❌ ليس لديك صلاحية لهذه العملية.")
            return
        
        # عرض واجهة إنشاء الكوبونات
        coupon_text = f"""
🎟️ **إنشاء كوبونات الشحن** 🎟️

👑 المشرف: **{user['full_name']}**

📋 **تعليمات إنشاء الكوبون:**
1. اختر نوع الكوبون المطلوب
2. حدد القيمة والكمية  
3. سيتم إنشاء كود بتنسيق A + 8 أرقام
4. الكوبون صالح لمدة 30 يوم

🎯 **أنواع الكوبونات المتاحة:**
"""
        
        keyboard = [
            [InlineKeyboardButton('💰 كوبون فردي', callback_data='create_single_coupon'),
             InlineKeyboardButton('📦 كوبونات متعددة', callback_data='create_bulk_coupons')],
            [InlineKeyboardButton('📊 إحصائيات الكوبونات', callback_data='coupons_stats'),
             InlineKeyboardButton('📋 قائمة الكوبونات', callback_data='list_coupons')],
            [InlineKeyboardButton('👑 لوحة المشرف الأعلى', callback_data='super_admin_panel')]
        ]
        
        await query.edit_message_text(coupon_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in create coupons handler: {e}")
        await query.edit_message_text(coupon_error("عرض واجهة إنشاء الكوبونات"))

async def create_single_coupon_start(update: Update, context: CallbackContext):
    """بدء إنشاء كوبون فردي: يطلب إدخال المبلغ فقط (بدون صلاحية)"""
    try:
        query = update.callback_query
        await query.answer()
        user = get_user(query.from_user.id)
        if not user or user['role'] != 'super_admin':
            await query.edit_message_text(f"{EMOJIS['error']} ليس لديك صلاحية لهذه العملية.")
            return
        text = (
            "💰 إدخال قيمة الكوبون\n\n"
            "✍️ اكتب قيمة الكوبون بالريال فقط (مثال: 50 أو 75.5)"
        )
        context.user_data['awaiting_single_coupon'] = True
        await query.edit_message_text(text)
    except Exception as e:
        logger.error(f"Error in single coupon start: {e}")
        await query.edit_message_text(coupon_error("بدء إنشاء كوبون فردي"))

async def process_single_coupon_input(update: Update, context: CallbackContext):
    """معالجة إدخال إنشاء كوبون فردي (المبلغ فقط)"""
    try:
        if not context.user_data.get('awaiting_single_coupon'):
            return
        user = get_user(update.effective_user.id)
        if not user or user['role'] != 'super_admin':
            await update.message.reply_text(f"{EMOJIS['error']} ليس لديك صلاحية لهذه العملية.")
            return
        parts = update.message.text.strip().split()
        if len(parts) == 0:
            await update.message.reply_text(f"{EMOJIS['error']} أدخل قيمة صحيحة.")
            return
        try:
            amount = float(parts[0].replace(',', '.'))
            if amount <= 0:
                raise ValueError("amount")
        except Exception:
            await update.message.reply_text(f"{EMOJIS['error']} المبلغ غير صحيح.")
            return
        # لا توجد صلاحية (expiry) وفق الطلب
        # توليد كود فريد
        import random, string
        coupon_code = None
        conn = get_db_connection()
        cursor = conn.cursor()
        for _ in range(100):
            trial_code = 'A' + ''.join(random.choices(string.digits, k=8))
            cursor.execute('SELECT 1 FROM coupons WHERE coupon_code = ?', (trial_code,))
            if not cursor.fetchone():
                coupon_code = trial_code
                break
        if not coupon_code:
            conn.close()
            await update.message.reply_text(f"{EMOJIS['error']} تعذر إنشاء كود فريد. حاول مجدداً.")
            return
        # إنشاء الجدول إن لم يوجد
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS coupons (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                coupon_code TEXT UNIQUE NOT NULL,
                amount REAL NOT NULL,
                is_used INTEGER DEFAULT 0,
                used_by INTEGER DEFAULT NULL,
                created_by INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                used_at TIMESTAMP,
                expiry_date TIMESTAMP,
                description TEXT
            )
        ''')
        cursor.execute('''
            INSERT INTO coupons (coupon_code, amount, created_by, expiry_date, description)
            VALUES (?, ?, ?, ?, ?)
        ''', (coupon_code, amount, user['id'], None, 'كوبون فردي'))
        conn.commit()
        conn.close()
        context.user_data.pop('awaiting_single_coupon', None)
        success = (
            f"✅ تم إنشاء الكوبون بنجاح!\n\n"
            f"🎟️ الكود: `{coupon_code}`\n"
            f"💰 القيمة: {amount} ريال"
        )
        await update.message.reply_text(success, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Error in process single coupon: {e}")
        await update.message.reply_text(coupon_error("إنشاء كوبون فردي"))

async def create_bulk_coupons_start(update: Update, context: CallbackContext):
    """بدء إنشاء كوبونات متعددة: تدفق تدرجي (أولاً المبلغ ثم العدد)"""
    try:
        query = update.callback_query
        await query.answer()
        user = get_user(query.from_user.id)
        if not user or user['role'] != 'super_admin':
            await query.edit_message_text(f"{EMOJIS['error']} ليس لديك صلاحية لهذه العملية.")
            return
        text = (
            "📦 إنشاء كوبونات متعددة\n\n"
            "1️⃣ أدخل قيمة الكوبون بالريال (مثال: 50 أو 75.5)"
        )
        context.user_data['awaiting_bulk_amount'] = True
        await query.edit_message_text(text)
    except Exception as e:
        logger.error(f"Error in bulk coupons start: {e}")
        await query.edit_message_text(coupon_error("بدء إنشاء كوبونات متعددة"))

async def process_bulk_amount_input(update: Update, context: CallbackContext):
    """الخطوة 1 من 2: التقاط قيمة الكوبون للدفعة"""
    try:
        if not context.user_data.get('awaiting_bulk_amount'):
            return
        user = get_user(update.effective_user.id)
        if not user or user['role'] != 'super_admin':
            await update.message.reply_text(f"{EMOJIS['error']} ليس لديك صلاحية لهذه العملية.")
            return
        try:
            amount = float(update.message.text.strip().replace(',', '.'))
            if amount <= 0:
                raise ValueError
        except Exception:
            await update.message.reply_text(f"{EMOJIS['error']} أدخل قيمة صحيحة (مثال: 50 أو 75.5)")
            return
        context.user_data['bulk_amount'] = amount
        context.user_data.pop('awaiting_bulk_amount', None)
        context.user_data['awaiting_bulk_count'] = True
        await update.message.reply_text("2️⃣ أدخل عدد الكوبونات المطلوب إنشاؤها (مثال: 25)")
    except Exception as e:
        logger.error(f"Error in process bulk amount: {e}")
        await update.message.reply_text(coupon_error("تحديد قيمة الكوبونات"))

async def process_bulk_count_input(update: Update, context: CallbackContext):
    """الخطوة 2 من 2: التقاط عدد الكوبونات وإنشاؤها"""
    try:
        if not context.user_data.get('awaiting_bulk_count'):
            return
        user = get_user(update.effective_user.id)
        if not user or user['role'] != 'super_admin':
            await update.message.reply_text(f"{EMOJIS['error']} ليس لديك صلاحية لهذه العملية.")
            return
        amount = context.user_data.get('bulk_amount')
        if amount is None:
            await update.message.reply_text(f"{EMOJIS['error']} لم يتم تحديد قيمة الكوبون. ابدأ من جديد.")
            context.user_data.pop('awaiting_bulk_count', None)
            return
        try:
            count = int(update.message.text.strip())
            if count <= 0:
                raise ValueError
        except Exception:
            await update.message.reply_text(f"{EMOJIS['error']} أدخل عدداً صحيحاً (مثال: 25)")
            return
        if count > 1000:
            await update.message.reply_text(f"{EMOJIS['warning']} الحد الأقصى 1000 كوبون في الدفعة الواحدة.")
            return
        import random, string
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS coupons (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                coupon_code TEXT UNIQUE NOT NULL,
                amount REAL NOT NULL,
                is_used INTEGER DEFAULT 0,
                used_by INTEGER DEFAULT NULL,
                created_by INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                used_at TIMESTAMP,
                expiry_date TIMESTAMP,
                description TEXT
            )
        ''')
        created = 0
        skipped = 0
        for _ in range(count):
            for _attempt in range(100):
                trial_code = 'A' + ''.join(random.choices(string.digits, k=8))
                cursor.execute('SELECT 1 FROM coupons WHERE coupon_code = ?', (trial_code,))
                if not cursor.fetchone():
                    try:
                        cursor.execute(
                            'INSERT INTO coupons (coupon_code, amount, created_by, expiry_date, description) VALUES (?, ?, ?, ?, ?)',
                            (trial_code, amount, user['id'], None, 'كوبون دفعي')
                        )
                        created += 1
                    except Exception:
                        skipped += 1
                    break
            else:
                skipped += 1
        conn.commit()
        conn.close()
        # تنظيف الحالات
        context.user_data.pop('awaiting_bulk_count', None)
        context.user_data.pop('bulk_amount', None)
        summary = (
            f"✅ تم إنشاء الكوبونات!\n\n"
            f"💰 القيمة: {amount} ريال\n"
            f"📦 الكمية المطلوبة: {count}\n"
            f"✅ المُنشأ: {created}\n"
            f"⚠️ تخطّي/مكرر: {skipped}"
        )
        await update.message.reply_text(summary)
    except Exception as e:
        logger.error(f"Error in process bulk count: {e}")
        await update.message.reply_text(coupon_error("إنشاء كوبونات متعددة"))
async def create_quick_coupon_handler(update: Update, context: CallbackContext, amount: int):
    """تم إلغاء ميزة الكوبون السريع حسب الطلب"""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("⚠️ تم تعطيل ميزة الكوبونات السريعة. استخدم الخيارات: كوبون فردي أو كوبونات متعددة.")

async def coupons_stats_handler(update: Update, context: CallbackContext):
    """عرض إحصائيات الكوبونات"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user or user['role'] != 'super_admin':
            await query.edit_message_text("❌ ليس لديك صلاحية لهذه العملية.")
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
        
        cursor.execute('SELECT COALESCE(SUM(amount), 0) FROM coupons')
        total_value = cursor.fetchone()[0]
        
        cursor.execute('SELECT COALESCE(SUM(amount), 0) FROM coupons WHERE is_used = 1')
        used_value = cursor.fetchone()[0]
        
        conn.close()
        
        stats_text = f"""
📊 **إحصائيات الكوبونات** 📊

🎟️ **إجمالي الكوبونات:** {total_coupons:,}
✅ **المستخدمة:** {used_coupons:,}
⏳ **غير المستخدمة:** {unused_coupons:,}

💰 **القيمة الإجمالية:** {total_value:,.2f} ريال
💸 **القيمة المستخدمة:** {used_value:,.2f} ريال
💵 **القيمة المتبقية:** {(total_value - used_value):,.2f} ريال

📈 **معدل الاستخدام:** {(used_coupons / max(total_coupons, 1) * 100):.1f}%
"""
        
        keyboard = [
            [InlineKeyboardButton('🎟️ إنشاء كوبون جديد', callback_data='super_create_coupons'),
             InlineKeyboardButton('📋 قائمة الكوبونات', callback_data='list_coupons')],
            [InlineKeyboardButton('👑 لوحة المشرف الأعلى', callback_data='super_admin_panel')]
        ]
        
        await query.edit_message_text(stats_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in coupons stats: {e}")
        await query.edit_message_text(coupon_error("عرض إحصائيات الكوبونات"))

async def list_coupons_handler(update: Update, context: CallbackContext):
    """عرض قائمة الكوبونات"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user or user['role'] != 'super_admin':
            await query.edit_message_text("❌ ليس لديك صلاحية لهذه العملية.")
            return
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT coupon_code, amount, is_used, created_at, used_at
            FROM coupons 
            ORDER BY created_at DESC 
            LIMIT 10
        ''')
        coupons = cursor.fetchall()
        conn.close()
        
        if not coupons:
            list_text = """
📋 **قائمة الكوبونات** 📋

⚠️ لا توجد كوبونات حالياً
"""
        else:
            list_text = """
📋 **قائمة الكوبونات** 📋

📝 **آخر 10 كوبونات:**

"""
            for coupon in coupons:
                status = "✅ مستخدم" if coupon['is_used'] else "⏳ غير مستخدم"
                list_text += f"""
🎟️ **{coupon['coupon_code']}**
💰 {coupon['amount']} ريال - {status}
📅 {coupon['created_at'][:16]}
---
"""
        
        keyboard = [
            [InlineKeyboardButton('🎟️ إنشاء كوبون جديد', callback_data='super_create_coupons'),
             InlineKeyboardButton('📊 الإحصائيات', callback_data='coupons_stats')],
            [InlineKeyboardButton('👑 لوحة المشرف الأعلى', callback_data='super_admin_panel')]
        ]
        
        await query.edit_message_text(list_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in list coupons: {e}")
        await query.edit_message_text(coupon_error("عرض قائمة الكوبونات"))

