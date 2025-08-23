#!/usr/bin/env python3
"""
Admin Handlers Module
Handles super admin functionality
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext
from bot_modules.config import *
from bot_modules.utils import *
from bot_modules.database import get_db_connection

logger = logging.getLogger(__name__)

async def super_admin_panel_handler(update: Update, context: CallbackContext):
    """Handle super admin panel"""
    try:
        query = update.callback_query
        user = get_user(query.from_user.id)
        
        if not user or user['role'] != 'super_admin':
            await query.edit_message_text("❌ هذه الميزة متاحة للمشرف الأعلى فقط.")
            return
        
        panel_text = f"""
👑 **لوحة المشرف الأعلى** 👑

👤 **{user['full_name']}**
💰 **رصيدك:** {user['balance']:,.2f} ريال

💡 **اختر الإجراء المطلوب:**
"""
        
        keyboard = [
            [InlineKeyboardButton('👥 إدارة المستخدمين', callback_data='admin_manage_users')],
            [InlineKeyboardButton('🌐 إدارة الشبكات', callback_data='admin_manage_networks')],
            [InlineKeyboardButton('📤 رفع كروت', callback_data='admin_upload_cards')],
            [InlineKeyboardButton('💰 إدارة الأرصدة', callback_data='admin_manage_balances')],
            [InlineKeyboardButton('📊 تقارير النظام', callback_data='admin_system_reports')],
            [InlineKeyboardButton('🔙 القائمة الرئيسية', callback_data='main_menu')]
        ]
        
        await query.edit_message_text(panel_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in super admin panel handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في عرض لوحة المشرف الأعلى.")

async def admin_manage_users_handler(update: Update, context: CallbackContext):
    """Handle user management for super admin"""
    try:
        query = update.callback_query
        user = get_user(query.from_user.id)
        
        if not user or user['role'] != 'super_admin':
            await query.edit_message_text("❌ هذه الميزة متاحة للمشرف الأعلى فقط.")
            return
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get user statistics
        cursor.execute('''
            SELECT role, COUNT(*) as count
            FROM users
            GROUP BY role
        ''')
        
        role_stats = cursor.fetchall()
        
        # Get total users
        cursor.execute('SELECT COUNT(*) FROM users')
        total_users = cursor.fetchone()[0]
        
        conn.close()
        
        users_text = f"""
👥 **إدارة المستخدمين** 👥

📊 **إحصائيات المستخدمين:**
👤 **إجمالي المستخدمين:** {total_users}

"""
        
        for role, count in role_stats:
            role_name = {
                'customer': '👤 العملاء',
                'supplier': '🏪 المزودين',
                'super_admin': '👑 المشرف الأعلى'
            }.get(role, role)
            
            users_text += f"{role_name}: **{count}** مستخدم\n"
        
        users_text += """
💡 **اختر الإجراء المطلوب:**
"""
        
        keyboard = [
            [InlineKeyboardButton('👤 عرض جميع المستخدمين', callback_data='admin_list_users')],
            [InlineKeyboardButton('🔍 البحث عن مستخدم', callback_data='admin_search_user')],
            [InlineKeyboardButton('✅ تفعيل مزود', callback_data='admin_activate_supplier')],
            [InlineKeyboardButton('❌ تعطيل مستخدم', callback_data='admin_disable_user')],
            [InlineKeyboardButton('🔙 عودة للوحة المشرف', callback_data='super_admin_panel')]
        ]
        
        await query.edit_message_text(users_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in admin manage users handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في إدارة المستخدمين.")

async def admin_manage_networks_handler(update: Update, context: CallbackContext):
    """Handle network management for super admin"""
    try:
        query = update.callback_query
        user = get_user(query.from_user.id)
        
        if not user or user['role'] != 'super_admin':
            await query.edit_message_text("❌ هذه الميزة متاحة للمشرف الأعلى فقط.")
            return
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get network statistics
        cursor.execute('''
            SELECT 
                COUNT(*) as total_networks,
                SUM(CASE WHEN is_approved = 1 THEN 1 ELSE 0 END) as approved_networks,
                SUM(CASE WHEN is_approved = 0 THEN 1 ELSE 0 END) as pending_networks,
                SUM(CASE WHEN is_active = 1 THEN 1 ELSE 0 END) as active_networks
            FROM networks
        ''')
        
        stats = cursor.fetchone()
        total, approved, pending, active = stats
        
        # Get networks by supplier
        cursor.execute('''
            SELECT u.full_name, COUNT(n.id) as network_count
            FROM users u
            LEFT JOIN networks n ON u.id = n.supplier_id
            WHERE u.role = 'supplier'
            GROUP BY u.id, u.full_name
            ORDER BY network_count DESC
        ''')
        
        supplier_networks = cursor.fetchall()
        conn.close()
        
        networks_text = f"""
🌐 **إدارة الشبكات** 🌐

📊 **إحصائيات الشبكات:**
🌐 **إجمالي الشبكات:** {total}
✅ **الشبكات المعتمدة:** {approved}
⏳ **الشبكات في الانتظار:** {pending}
🟢 **الشبكات النشطة:** {active}

👥 **الشبكات حسب المزود:**
"""
        
        for supplier_name, network_count in supplier_networks:
            networks_text += f"👤 **{supplier_name}:** {network_count} شبكة\n"
        
        networks_text += """
💡 **اختر الإجراء المطلوب:**
"""
        
        keyboard = [
            [InlineKeyboardButton('🌐 عرض جميع الشبكات', callback_data='admin_list_networks')],
            [InlineKeyboardButton('✅ اعتماد شبكة', callback_data='admin_approve_network')],
            [InlineKeyboardButton('❌ رفض شبكة', callback_data='admin_reject_network')],
            [InlineKeyboardButton('🗑️ حذف شبكة', callback_data='admin_delete_network')],
            [InlineKeyboardButton('🔙 عودة للوحة المشرف', callback_data='super_admin_panel')]
        ]
        
        await query.edit_message_text(networks_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in admin manage networks handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في إدارة الشبكات.")

async def admin_upload_cards_handler(update: Update, context: CallbackContext):
    """Handle card upload for super admin"""
    try:
        query = update.callback_query
        user = get_user(query.from_user.id)
        
        if not user or user['role'] != 'super_admin':
            await query.edit_message_text("❌ هذه الميزة متاحة للمشرف الأعلى فقط.")
            return
        
        upload_text = f"""
📤 **رفع كروت (المشرف الأعلى)** 📤

👤 **{user['full_name']}**
👑 **الصلاحية:** المشرف الأعلى

💡 **اختر طريقة رفع الكروت:**
"""
        
        keyboard = [
            [InlineKeyboardButton('📁 رفع ملف', callback_data='admin_file_upload')],
            [InlineKeyboardButton('✏️ إدخال يدوي', callback_data='admin_manual_upload')],
            [InlineKeyboardButton('🔙 عودة للوحة المشرف', callback_data='super_admin_panel')]
        ]
        
        await query.edit_message_text(upload_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in admin upload cards handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في رفع الكروت.")

async def admin_manage_balances_handler(update: Update, context: CallbackContext):
    """Handle balance management for super admin"""
    try:
        query = update.callback_query
        user = get_user(query.from_user.id)
        
        if not user or user['role'] != 'super_admin':
            await query.edit_message_text("❌ هذه الميزة متاحة للمشرف الأعلى فقط.")
            return
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get balance statistics
        cursor.execute('''
            SELECT 
                COUNT(*) as total_users,
                SUM(balance) as total_balance,
                AVG(balance) as avg_balance,
                MIN(balance) as min_balance,
                MAX(balance) as max_balance
            FROM users
        ''')
        
        stats = cursor.fetchone()
        total_users, total_balance, avg_balance, min_balance, max_balance = stats
        
        conn.close()
        
        balance_text = f"""
💰 **إدارة الأرصدة** 💰

👤 **{user['full_name']}**
👑 **الصلاحية:** المشرف الأعلى

📊 **إحصائيات الأرصدة:**
👥 **إجمالي المستخدمين:** {total_users}
💰 **إجمالي الأرصدة:** {total_balance:,.2f} ريال
📊 **متوسط الرصيد:** {avg_balance:,.2f} ريال
📉 **أقل رصيد:** {min_balance:,.2f} ريال
📈 **أعلى رصيد:** {max_balance:,.2f} ريال

💡 **اختر الإجراء المطلوب:**
"""
        
        keyboard = [
            [InlineKeyboardButton('💰 إضافة رصيد', callback_data='admin_add_balance')],
            [InlineKeyboardButton('💸 خصم رصيد', callback_data='admin_deduct_balance')],
            [InlineKeyboardButton('🔄 إعادة تعيين رصيد', callback_data='admin_reset_balance')],
            [InlineKeyboardButton('📊 تقرير الأرصدة', callback_data='admin_balance_report')],
            [InlineKeyboardButton('🔙 عودة للوحة المشرف', callback_data='super_admin_panel')]
        ]
        
        await query.edit_message_text(balance_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in admin manage balances handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في إدارة الأرصدة.")

async def admin_system_reports_handler(update: Update, context: CallbackContext):
    """Handle system reports for super admin"""
    try:
        query = update.callback_query
        user = get_user(query.from_user.id)
        
        if not user or user['role'] != 'super_admin':
            await query.edit_message_text("❌ هذه الميزة متاحة للمشرف الأعلى فقط.")
            return
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get system statistics
        cursor.execute('SELECT COUNT(*) FROM users')
        total_users = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM networks')
        total_networks = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM card_categories')
        total_categories = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM cards')
        total_cards = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM transactions')
        total_transactions = cursor.fetchone()[0]
        
        conn.close()
        
        reports_text = f"""
📊 **تقارير النظام** 📊

👤 **{user['full_name']}**
👑 **الصلاحية:** المشرف الأعلى

📈 **إحصائيات النظام:**
👥 **المستخدمين:** {total_users}
🌐 **الشبكات:** {total_networks}
📂 **فئات الكروت:** {total_categories}
💳 **الكروت:** {total_cards}
💰 **المعاملات:** {total_transactions}

💡 **اختر التقرير المطلوب:**
"""
        
        keyboard = [
            [InlineKeyboardButton('📊 تقرير المستخدمين', callback_data='admin_users_report')],
            [InlineKeyboardButton('🌐 تقرير الشبكات', callback_data='admin_networks_report')],
            [InlineKeyboardButton('💳 تقرير الكروت', callback_data='admin_cards_report')],
            [InlineKeyboardButton('💰 تقرير المعاملات', callback_data='admin_transactions_report')],
            [InlineKeyboardButton('🔙 عودة للوحة المشرف', callback_data='super_admin_panel')]
        ]
        
        await query.edit_message_text(reports_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in admin system reports handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في عرض تقارير النظام.")

def setup_admin_handlers(application):
    """Setup admin handlers"""
    # Admin handlers are called via callback handlers
    pass