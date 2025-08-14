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
            [InlineKeyboardButton(f'💰 إصدار رصيد', callback_data='super_issue_balance'),
             InlineKeyboardButton(f'✅ تفعيل مزودين', callback_data='super_activate_suppliers')],
            [InlineKeyboardButton(f'👥 إدارة المستخدمين', callback_data='super_manage_users'),
             InlineKeyboardButton(f'📊 التقارير التنفيذية', callback_data='super_executive_reports')],
            [InlineKeyboardButton(f'🏛️ إدارة المنصة', callback_data='super_platform_management'),
             InlineKeyboardButton(f'🔧 إعدادات النظام', callback_data='super_system_settings')],
            [InlineKeyboardButton(f'💾 النسخ الاحتياطي', callback_data='super_backup'),
             InlineKeyboardButton(f'🚨 مراقبة الأمان', callback_data='super_security_monitoring')],
            [InlineKeyboardButton(f'👑 إدارة المشرفين', callback_data='super_manage_admins'),
             InlineKeyboardButton(f'📈 لوحة المعلومات', callback_data='super_dashboard')],
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
    """Handle balance issuance for super admin"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user or user['role'] != 'super_admin':
            await query.edit_message_text(f"{EMOJIS['error']} ليس لديك صلاحية لهذه العملية.")
            return
        
        text = f"""
💰 **إصدار رصيد للمستخدمين** 💰

{EMOJIS['admin']} مرحباً **{user['full_name']}**

📋 **تعليمات الإصدار:**
1️⃣ أدخل رقم المحفظة (9 أرقام تبدأ بـ 79)
2️⃣ أدخل المبلغ المراد إصداره
3️⃣ أدخل سبب الإصدار (اختياري)

💡 **مثال:**
`791234567 1000 رصيد هدية للعميل`

⚠️ **تنبيه مهم:**
يجب أن تكون حذراً عند إصدار الأرصدة حيث أنها عملية مالية مهمة

📝 أدخل البيانات بالتنسيق التالي:
`رقم_المحفظة المبلغ السبب`

أو اكتب /cancel للإلغاء
"""
        
        await query.edit_message_text(text, parse_mode='Markdown')
        context.user_data['awaiting_balance_issue'] = True
        
    except Exception as e:
        logger.error(f"Error in issue balance handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في بدء عملية إصدار الرصيد.")

async def process_balance_issue(update: Update, context: CallbackContext):
    """Process balance issuance from super admin"""
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
        
        reason = ' '.join(parts[2:]) if len(parts) > 2 else 'إصدار رصيد من المشرف الأعلى'
        
        # Validate amount
        if amount <= 0:
            await update.message.reply_text(f"{EMOJIS['error']} المبلغ يجب أن يكون أكبر من صفر.")
            return
        
        if amount > 10000:  # Security limit
            await update.message.reply_text(f"{EMOJIS['error']} لا يمكن إصدار أكثر من 10,000 ريال في العملية الواحدة.")
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
        
        # Create transaction
        transaction_id = str(uuid.uuid4())
        cursor.execute('''
            INSERT INTO transactions 
            (id, to_user, amount, type, description, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (transaction_id, target_user['id'], amount, 'admin_issue', reason, datetime.now()))
        
        # Update balance
        new_balance = recalc_and_set_user_balance(target_user['id'])
        
        # Create wallet transaction
        create_wallet_transaction(
            target_user['id'],
            'credit',
            amount,
            target_user['balance'],
            new_balance,
            f'إصدار رصيد من المشرف الأعلى: {reason}',
            transaction_id,
            {
                'issued_by': user['full_name'],
                'admin_id': user['id'],
                'reason': reason
            }
        )
        
        # Log the action
        log_system_action(user['id'], 'balance_issue', f'Issued {amount} to user {target_user["id"]} ({target_user["full_name"]}). Reason: {reason}')
        log_activity(user['id'], 'admin_balance_issue', f'Issued {amount} YER to {target_user["full_name"]}', {
            'target_user_id': target_user['id'],
            'amount': amount,
            'reason': reason,
            'transaction_id': transaction_id
        })
        
        conn.commit()
        conn.close()
        
        # Send notification to target user
        send_smart_notification(
            target_user['id'],
            'balance_issued',
            '💰 تم إضافة رصيد لحسابك',
            f'تم إضافة {amount:.2f} ريال لرصيدك من قبل الإدارة\nالسبب: {reason}',
            'high'
        )
        
        success_text = f"""
✅ **تم إصدار الرصيد بنجاح!**

💰 المبلغ: **{amount:.2f}** ريال
👤 المستلم: **{target_user['full_name']}**
💳 رقم المحفظة: **{wallet_number}**
💫 الرصيد الجديد: **{new_balance:.2f}** ريال
📝 السبب: {reason}

🔐 رقم المعاملة: `{transaction_id}`
⏰ الوقت: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        
        keyboard = [
            [InlineKeyboardButton(f'💰 إصدار رصيد آخر', callback_data='super_issue_balance')],
            [InlineKeyboardButton(f'👑 لوحة المشرف الأعلى', callback_data='super_admin_panel')],
            [InlineKeyboardButton(f'{EMOJIS["home"]} القائمة الرئيسية', callback_data='main_menu')]
        ]
        
        await update.message.reply_text(success_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
        # Clear the state
        context.user_data['awaiting_balance_issue'] = False
        
    except Exception as e:
        logger.error(f"Error processing balance issue: {e}")
        await update.message.reply_text(f"{EMOJIS['error']} حدث خطأ في معالجة إصدار الرصيد.")

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
    """Placeholder handler for features under development"""
    try:
        query = update.callback_query
        await query.answer()
        
        text = f"""
⚠️ **{feature_name}**

هذه الميزة قيد التطوير حالياً.
سيتم إضافتها في التحديثات القادمة إن شاء الله.

🔧 **قريباً:**
• واجهة محسّنة
• ميزات متقدمة  
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
    return await placeholder_handler(update, context, "النسخ الاحتياطي")

async def executive_reports_handler(update, context):
    return await placeholder_handler(update, context, "التقارير التنفيذية")

async def manage_users_handler(update, context):
    return await placeholder_handler(update, context, "إدارة المستخدمين")

async def system_settings_handler(update, context):
    return await placeholder_handler(update, context, "إعدادات النظام")

async def security_monitoring_handler(update, context):
    return await placeholder_handler(update, context, "مراقبة الأمان")

async def manage_admins_handler(update, context):
    return await placeholder_handler(update, context, "إدارة المشرفين")

async def dashboard_handler(update, context):
    return await placeholder_handler(update, context, "لوحة المعلومات")

async def view_all_suppliers_handler(update, context):
    return await placeholder_handler(update, context, "عرض جميع المزودين")

async def view_supplier_details_handler(update, context):
    return await placeholder_handler(update, context, "تفاصيل المزودين")

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
}