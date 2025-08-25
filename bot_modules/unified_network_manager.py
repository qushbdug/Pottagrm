#!/usr/bin/env python3
"""
Unified Network Manager for Pottagrm Enhanced Bot
Consolidates all network-related functions to eliminate conflicts

This module merges all network functions from:
- yemen_net_bot_new.py
- bot_modules/handlers.py  
- bot_modules/admin_functions.py
- bot_modules/network_handlers.py

Author: Software Maintainer
Version: 1.0.0 (Unified)
"""

import logging
import uuid
from datetime import datetime
from typing import Optional, Dict, List, Tuple, Any

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext

from bot_modules.config import *
from bot_modules.database import get_db_connection
from bot_modules.utils import get_user, update_user_activity

logger = logging.getLogger(__name__)

# =============================================================================
# UNIFIED NETWORK CREATION - SUPPORTS ALL USER ROLES
# =============================================================================

async def unified_network_creation_handler(update: Update, context: CallbackContext):
    """
    Unified network creation handler that supports all user roles
    Merges logic from: add_network_handler, add_new_network_handler, admin_add_network_handler
    """
    try:
        # Determine if this is a callback query or message
        if hasattr(update, 'callback_query') and update.callback_query:
            query = update.callback_query
            await query.answer()
            user = get_user(query.from_user.id)
            is_callback = True
        else:
            user = get_user(update.effective_user.id)
            is_callback = False
        
        if not user:
            error_msg = f"{EMOJIS['error']} يرجى التسجيل أولاً /start"
            if is_callback:
                await update.callback_query.edit_message_text(error_msg)
            else:
                await update.message.reply_text(error_msg)
            return
        
        # Check permissions - supports supplier, admin, super_admin
        if user['role'] not in ['supplier', 'admin', 'super_admin']:
            error_msg = f"""
{EMOJIS['error']} **غير مسموح**

هذه الميزة متاحة للمزودين والمشرفين فقط.
للحصول على حساب مزود، تواصل مع الإدارة.
"""
            if is_callback:
                await update.callback_query.edit_message_text(error_msg, parse_mode='Markdown')
            else:
                await update.message.reply_text(error_msg, parse_mode='Markdown')
            return
        
        # Clear any existing data and start fresh
        context.user_data.clear()
        context.user_data['unified_adding_network'] = True
        context.user_data['network_step'] = 'name'
        context.user_data['user_role'] = user['role']
        
        # Create appropriate message based on user role
        if user['role'] in ['admin', 'super_admin']:
            role_title = "مشرف"
            additional_info = "\n🔧 **كمشرف، يمكنك إضافة شبكات لأي مزود**"
        else:
            role_title = "مزود معتمد"
            additional_info = ""
        
        add_text = f"""
➕ **إضافة شبكة جديدة** ➕

👤 **{user['full_name']}** ({role_title}){additional_info}

📝 **سنقوم بإضافة الشبكة خطوة بخطوة:**

🔸 **الخطوة 1 من 5**
📋 **أدخل اسم الشبكة:**

مثال: "شبكة النور للإنترنت"

💡 **ملاحظة:**
• اختر اسماً واضحاً ومميزاً
• سيتم عرض الاسم للعملاء
• تأكد من صحة الاسم قبل الإرسال

📤 **أرسل اسم الشبكة الآن:**
"""
        
        keyboard = [
            [InlineKeyboardButton('❌ إلغاء', callback_data='cancel_network_creation')],
            [InlineKeyboardButton('📶 إدارة الشبكات', callback_data='unified_manage_networks')]
        ]
        
        if is_callback:
            await update.callback_query.edit_message_text(
                add_text, 
                reply_markup=InlineKeyboardMarkup(keyboard), 
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                add_text, 
                reply_markup=InlineKeyboardMarkup(keyboard), 
                parse_mode='Markdown'
            )
        
    except Exception as e:
        logger.error(f"Error in unified network creation handler: {e}")
        error_msg = f"{EMOJIS['error']} حدث خطأ في إضافة الشبكة."
        if is_callback:
            await update.callback_query.edit_message_text(error_msg)
        else:
            await update.message.reply_text(error_msg)

async def process_unified_network_creation(update: Update, context: CallbackContext):
    """
    Process network creation steps - unified for all roles
    Merges logic from: process_supplier_network_creation, admin_process_network_creation, process_unified_network_creation
    """
    try:
        if not context.user_data.get('unified_adding_network'):
            return
            
        text = update.message.text.strip()
        user = get_user(update.effective_user.id)
        step = context.user_data.get('network_step', 'name')
        user_role = context.user_data.get('user_role', user['role'])
        
        # Verify permissions
        if user['role'] not in ['supplier', 'admin', 'super_admin']:
            await update.message.reply_text(f"{EMOJIS['error']} ليس لديك صلاحية لإضافة الشبكات.")
            context.user_data.clear()
            return
        
        if step == 'name':
            # Step 1: Network Name
            context.user_data['network_name'] = text
            context.user_data['network_step'] = 'provider'
            
            await update.message.reply_text(
                f"✅ **تم حفظ اسم الشبكة:** {text}\n\n🔸 **الخطوة 2 من 5**\n👤 **أدخل اسم المزود:**",
                parse_mode='Markdown'
            )
            
        elif step == 'provider':
            # Step 2: Provider Name
            context.user_data['network_provider'] = text
            context.user_data['network_step'] = 'description'
            
            await update.message.reply_text(
                f"✅ **تم حفظ اسم المزود:** {text}\n\n🔸 **الخطوة 3 من 5**\n📝 **أدخل وصف الشبكة:**",
                parse_mode='Markdown'
            )
            
        elif step == 'description':
            # Step 3: Network Description
            context.user_data['network_description'] = text
            context.user_data['network_step'] = 'location'
            
            await update.message.reply_text(
                f"✅ **تم حفظ وصف الشبكة:** {text}\n\n🔸 **الخطوة 4 من 5**\n📍 **أدخل موقع الشبكة:**",
                parse_mode='Markdown'
            )
            
        elif step == 'location':
            # Step 4: Network Location
            context.user_data['network_location'] = text
            context.user_data['network_step'] = 'categories'
            
            categories_text = f"""
✅ **تم حفظ موقع الشبكة:** {text}

🔸 **الخطوة 5 من 5**
💳 **اختر فئات الكروت المتاحة:**

يمكنك اختيار فئة واحدة أو أكثر من الفئات التالية:
• 1000 ريال
• 2000 ريال  
• 5000 ريال
• 10000 ريال
• 20000 ريال

📝 **أدخل قيم الفئات مفصولة بفاصلة:**
مثال: 1000,2000,5000

أو اكتب **تخطي** لإضافة الفئات لاحقاً
"""
            await update.message.reply_text(categories_text, parse_mode='Markdown')
            
        elif step == 'categories':
            # Step 5: Create Network with Categories
            await create_network_with_categories(update, context, text, user, user_role)
        
    except Exception as e:
        logger.error(f"Error in unified network creation process: {e}")
        await update.message.reply_text(f"❌ خطأ في معالجة الشبكة: {e}")
        context.user_data.clear()

async def create_network_with_categories(update: Update, context: CallbackContext, 
                                       categories_text: str, user: dict, user_role: str):
    """
    Create network with categories - supports all roles
    """
    try:
        network_name = context.user_data.get('network_name')
        provider = context.user_data.get('network_provider')
        description = context.user_data.get('network_description')
        location = context.user_data.get('network_location')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Determine supplier_id based on role
        if user_role in ['admin', 'super_admin']:
            # Admins can add networks and assign to themselves or specified supplier
            supplier_id = user['id']  # For now, assign to admin; can be enhanced to select supplier
        else:
            supplier_id = user['id']
        
        # Insert network
        cursor.execute('''
            INSERT INTO networks (supplier_id, name, city, provider, description, location, created_by, is_active, is_approved, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, 1, 1, CURRENT_TIMESTAMP)
        ''', (supplier_id, network_name, location, provider, description, location, user['id']))
        
        network_id = cursor.lastrowid
        
        # Process categories
        categories_info = ""
        if categories_text.lower().strip() != 'تخطي':
            try:
                category_values = [int(val.strip()) for val in categories_text.split(',') if val.strip().isdigit()]
                
                for value in category_values:
                    cursor.execute('''
                        INSERT INTO card_categories (network_id, category_name, category_value, max_cards, is_available, created_at)
                        VALUES (?, ?, ?, 10000, 1, CURRENT_TIMESTAMP)
                    ''', (network_id, f"كرت {value} ريال", value))
                
                categories_info = f"\n💳 **تم إضافة {len(category_values)} فئة:** {', '.join([f'{v} ريال' for v in category_values])}"
            except:
                categories_info = "\n⚠️ **لم يتم إضافة فئات** - يمكن إضافتها لاحقاً"
        else:
            categories_info = "\n⚠️ **تم تخطي إضافة الفئات** - يمكن إضافتها لاحقاً"
        
        conn.commit()
        conn.close()
        context.user_data.clear()
        
        # Create success keyboard
        keyboard = [
            [InlineKeyboardButton('💳 إضافة فئات كروت', callback_data=f'unified_add_categories_{network_id}'),
             InlineKeyboardButton('📤 رفع كروت', callback_data=f'unified_upload_to_network_{network_id}')],
            [InlineKeyboardButton('📶 إدارة الشبكات', callback_data='unified_manage_networks'),
             InlineKeyboardButton('🏪 القائمة الرئيسية', callback_data='main_menu')]
        ]
        
        success_text = f"""
✅ **تم إنشاء الشبكة بنجاح!**

🌐 **{network_name}**
👤 **المزود:** {provider}
📍 **الموقع:** {location}
🆔 **معرف الشبكة:** #{network_id}{categories_info}

🔧 **الخيارات المتاحة:**
"""
        
        await update.message.reply_text(
            success_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Error creating network with categories: {e}")
        await update.message.reply_text(f"❌ خطأ في إنشاء الشبكة: {e}")
        context.user_data.clear()

# =============================================================================
# UNIFIED NETWORK MANAGEMENT - SUPPORTS ALL USER ROLES
# =============================================================================

async def unified_manage_networks_handler(update: Update, context: CallbackContext):
    """
    Unified network management handler
    Merges logic from: manage_networks_handler, supplier_manage_networks, admin_manage_networks_handler
    """
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user:
            await query.edit_message_text(f"{EMOJIS['error']} يرجى التسجيل أولاً /start")
            return
        
        update_user_activity(user['id'])
        
        # Get networks based on user role
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if user['role'] in ['admin', 'super_admin']:
            # Admins see all networks
            cursor.execute('''
                SELECT n.id, n.name, n.provider, n.location, n.is_active, n.is_approved, n.created_at,
                       u.full_name as supplier_name
                FROM networks n
                LEFT JOIN users u ON n.supplier_id = u.id
                ORDER BY n.created_at DESC
            ''')
        else:
            # Suppliers see only their networks
            cursor.execute('''
                SELECT n.id, n.name, n.provider, n.location, n.is_active, n.is_approved, n.created_at,
                       u.full_name as supplier_name
                FROM networks n
                LEFT JOIN users u ON n.supplier_id = u.id
                WHERE n.supplier_id = ?
                ORDER BY n.created_at DESC
            ''', (user['id'],))
        
        networks = cursor.fetchall()
        conn.close()
        
        if not networks:
            # No networks found
            role_text = "مشرف" if user['role'] in ['admin', 'super_admin'] else "مزود"
            empty_text = f"""
📶 **إدارة الشبكات** 📶

👤 **{user['full_name']}** ({role_text})

❌ **لا توجد شبكات للإدارة**

🔧 **يجب إضافة شبكة أولاً**
"""
            keyboard = [
                [InlineKeyboardButton('🌐 إضافة شبكة جديدة', callback_data='unified_add_network')],
                [InlineKeyboardButton('🔙 عودة', callback_data='main_menu')]
            ]
        else:
            # Networks found
            role_text = "مشرف" if user['role'] in ['admin', 'super_admin'] else "مزود"
            networks_text = f"""
📶 **إدارة الشبكات** 📶

👤 **{user['full_name']}** ({role_text})

📊 **إجمالي الشبكات:** {len(networks)} شبكة

🔧 **اختر شبكة للإدارة:**
"""
            
            keyboard = []
            for network in networks:
                status_emoji = "✅" if network['is_active'] else "⚠️"
                approval_emoji = "✅" if network['is_approved'] else "⏳"
                
                button_text = f"{status_emoji}{approval_emoji} {network['name']}"
                if user['role'] in ['admin', 'super_admin'] and network['supplier_name']:
                    button_text += f" ({network['supplier_name']})"
                
                # Truncate if too long
                if len(button_text) > 60:
                    button_text = button_text[:57] + "..."
                
                keyboard.append([InlineKeyboardButton(
                    button_text,
                    callback_data=f'unified_network_details_{network["id"]}'
                )])
            
            keyboard.extend([
                [InlineKeyboardButton('🌐 إضافة شبكة جديدة', callback_data='unified_add_network')],
                [InlineKeyboardButton('🔙 عودة', callback_data='main_menu')]
            ])
            
            empty_text = networks_text
        
        await query.edit_message_text(
            empty_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Error in unified manage networks handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في إدارة الشبكات.")

# =============================================================================
# UNIFIED NETWORK SEARCH - COMBINES ALL SEARCH METHODS
# =============================================================================

async def unified_search_networks_handler(update: Update, context: CallbackContext):
    """
    Unified network search handler  
    Merges logic from all search_networks_handler functions
    """
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user:
            await query.edit_message_text(f"{EMOJIS['error']} يرجى التسجيل أولاً /start")
            return
        
        update_user_activity(user['id'])
        
        search_text = f"""
🔍 **البحث في الشبكات** 🔍

👤 **{user['full_name']}**

📱 **أنواع البحث المتاحة:**

🔸 **البحث بالاسم:** ابحث عن الشبكات بالاسم
🔸 **البحث بالموقع:** ابحث بالمدينة أو المنطقة  
🔸 **البحث بالمزود:** ابحث باسم مزود الخدمة
🔸 **تصفية الشبكات:** عرض شبكات محددة

💡 **اختر نوع البحث:**
"""
        
        keyboard = [
            [InlineKeyboardButton('📝 البحث بالاسم', callback_data='unified_search_by_name'),
             InlineKeyboardButton('📍 البحث بالموقع', callback_data='unified_search_by_location')],
            [InlineKeyboardButton('👤 البحث بالمزود', callback_data='unified_search_by_provider'),
             InlineKeyboardButton('📶 جميع الشبكات', callback_data='unified_view_all_networks')],
            [InlineKeyboardButton('📱 شبكات المحمول', callback_data='unified_mobile_networks'),
             InlineKeyboardButton('🏠 شبكات منزلية', callback_data='unified_home_networks')],
            [InlineKeyboardButton('🏪 القائمة الرئيسية', callback_data='main_menu')]
        ]
        
        await query.edit_message_text(search_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in unified search networks handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في البحث عن الشبكات.")

# =============================================================================
# HELPER FUNCTIONS FOR NETWORK OPERATIONS
# =============================================================================

async def cancel_network_operation(update: Update, context: CallbackContext):
    """Cancel any ongoing network operation"""
    try:
        query = update.callback_query
        await query.answer()
        
        # Clear all network-related data
        network_keys = [k for k in context.user_data.keys() if 'network' in k.lower() or 'adding' in k.lower()]
        for key in network_keys:
            context.user_data.pop(key, None)
        
        await query.edit_message_text(
            f"{EMOJIS['cancel']} تم إلغاء العملية.\n\n"
            f"يمكنك العودة للقائمة الرئيسية أو المحاولة مرة أخرى.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton('🔙 القائمة الرئيسية', callback_data='main_menu')]
            ])
        )
        
    except Exception as e:
        logger.error(f"Error cancelling network operation: {e}")

def get_networks_for_user(user_id: int, user_role: str) -> List[Dict]:
    """Get networks based on user role - unified function"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if user_role in ['admin', 'super_admin']:
            cursor.execute('''
                SELECT n.*, u.full_name as supplier_name
                FROM networks n
                LEFT JOIN users u ON n.supplier_id = u.id
                WHERE n.is_active = 1
                ORDER BY n.created_at DESC
            ''')
        else:
            cursor.execute('''
                SELECT n.*, u.full_name as supplier_name
                FROM networks n
                LEFT JOIN users u ON n.supplier_id = u.id
                WHERE n.supplier_id = ? AND n.is_active = 1
                ORDER BY n.created_at DESC
            ''', (user_id,))
        
        networks = cursor.fetchall()
        conn.close()
        
        return networks
    except Exception as e:
        logger.error(f"Error getting networks for user: {e}")
        return []

# =============================================================================
# UNIFIED CALLBACK HANDLERS MAPPING
# =============================================================================

UNIFIED_NETWORK_CALLBACKS = {
    'unified_add_network': unified_network_creation_handler,
    'unified_manage_networks': unified_manage_networks_handler,
    'unified_search_networks': unified_search_networks_handler,
    'cancel_network_creation': cancel_network_operation,
}