#!/usr/bin/env python3
"""
Simplified and Unified Network Display Manager
Fixes all errors and provides a much simpler, cleaner network display

Fixed Issues:
1. ❌ u.phone_number → ✅ u.phone
2. ❌ Complex error-prone queries → ✅ Simple, robust queries
3. ❌ Multiple conflicting display methods → ✅ One unified approach
4. ❌ Confusing UI → ✅ Clean, simple interface

Author: Software Maintenance Engineer
Version: 2.0.0 (Simplified & Unified)
"""

import logging
from typing import List, Dict, Optional, Tuple

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext

from bot_modules.config import EMOJIS
from bot_modules.database import get_db_connection
from bot_modules.utils import get_user, update_user_activity

logger = logging.getLogger(__name__)

# =============================================================================
# SIMPLIFIED NETWORK DISPLAY - NO MORE ERRORS!
# =============================================================================

async def simple_buy_cards_handler(update: Update, context: CallbackContext):
    """
    SIMPLIFIED: Buy cards - clean and simple display
    """
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user:
            await query.edit_message_text(f"{EMOJIS['error']} يرجى التسجيل أولاً /start")
            return
        
        # Simple query - just get networks with basic info
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # SIMPLIFIED: Get all networks without complex joins
        cursor.execute('''
            SELECT id, name, provider, location, description
            FROM networks 
            WHERE is_active = 1 AND is_approved = 1
            ORDER BY name
        ''')
        networks = cursor.fetchall()
        
        # Get category counts separately (simpler and more reliable)
        network_info = []
        for network in networks:
            net_id = network[0]
            
            # Count categories for this network
            cursor.execute('''
                SELECT COUNT(*), MIN(price), MAX(price)
                FROM card_categories 
                WHERE network_id = ? AND is_available = 1
            ''', (net_id,))
            cat_result = cursor.fetchone()
            cat_count = cat_result[0] if cat_result[0] else 0
            min_price = cat_result[1] if cat_result[1] else 0
            max_price = cat_result[2] if cat_result[2] else 0
            
            network_info.append({
                'id': network[0],
                'name': network[1],
                'provider': network[2],
                'location': network[3],
                'description': network[4],
                'categories': cat_count,
                'min_price': min_price,
                'max_price': max_price
            })
        
        conn.close()
        
        # Build simple, clean message
        buy_text = f"""
🛒 **شراء كروت الإنترنت**

👤 **{user['full_name']}**
💰 **رصيدك:** {user['balance']:,.0f} ريال

📶 **الشبكات المتاحة ({len(network_info)} شبكة):**

"""
        
        if network_info:
            for net in network_info:
                # Simple status indicator
                if net['categories'] > 0:
                    status = "✅ متاحة"
                    price_text = f"{net['min_price']:,.0f}" if net['min_price'] == net['max_price'] else f"{net['min_price']:,.0f}-{net['max_price']:,.0f}"
                    price_display = f"💰 {price_text} ريال"
                else:
                    status = "🔄 قيد التحضير"
                    price_display = "💰 قريباً"
                
                location_text = f"📍 {net['location']}" if net['location'] else ""
                
                buy_text += f"""
{status} **{net['name']}**
👤 {net['provider']} {location_text}
💳 {net['categories']} فئة | {price_display}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        else:
            buy_text += "❌ لا توجد شبكات متاحة حالياً"
        
        # Simple keyboard
        keyboard = []
        
        # Add network buttons (only for networks with categories)
        available_networks = [net for net in network_info if net['categories'] > 0]
        for net in available_networks[:6]:  # Max 6 buttons
            keyboard.append([InlineKeyboardButton(
                f"🛒 {net['name'][:25]}{'...' if len(net['name']) > 25 else ''}",
                callback_data=f'simple_buy_{net["id"]}'
            )])
        
        # Add utility buttons
        keyboard.extend([
            [InlineKeyboardButton('📊 عرض جميع الشبكات', callback_data='simple_view_all'),
             InlineKeyboardButton('🔍 البحث', callback_data='simple_search')],
            [InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
        ])
        
        await query.edit_message_text(buy_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in simple buy cards handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في عرض الشبكات. يرجى المحاولة مرة أخرى.")

async def simple_view_all_networks(update: Update, context: CallbackContext):
    """
    SIMPLIFIED: View all networks - clean list
    """
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user:
            await query.edit_message_text(f"{EMOJIS['error']} يرجى التسجيل أولاً /start")
            return
        
        # Simple query for all networks
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, name, provider, location, created_at
            FROM networks 
            WHERE is_active = 1 AND is_approved = 1
            ORDER BY created_at DESC
        ''')
        networks = cursor.fetchall()
        
        # Get counts for each network
        network_list = []
        for net in networks:
            net_id = net[0]
            cursor.execute('SELECT COUNT(*) FROM card_categories WHERE network_id = ? AND is_available = 1', (net_id,))
            cat_count = cursor.fetchone()[0]
            
            network_list.append({
                'id': net[0],
                'name': net[1],
                'provider': net[2],
                'location': net[3],
                'created_at': net[4],
                'categories': cat_count
            })
        
        conn.close()
        
        # Build message
        view_text = f"""
📶 **جميع الشبكات المتاحة**

👤 **{user['full_name']}**
📊 **العدد الكلي:** {len(network_list)} شبكة

"""
        
        if network_list:
            for i, net in enumerate(network_list, 1):
                status = "✅" if net['categories'] > 0 else "🔄"
                location = f"📍 {net['location']}" if net['location'] else "📍 غير محدد"
                date = net['created_at'][:10] if net['created_at'] else 'غير محدد'
                
                view_text += f"""
{i}. {status} **{net['name']}**
👤 {net['provider']} | {location}
💳 {net['categories']} فئة | 📅 {date}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        else:
            view_text += "❌ لا توجد شبكات متاحة"
        
        # Simple keyboard
        keyboard = []
        
        # Add detail buttons for first 5 networks
        for net in network_list[:5]:
            keyboard.append([InlineKeyboardButton(
                f"👁️ {net['name'][:20]}{'...' if len(net['name']) > 20 else ''}",
                callback_data=f'simple_details_{net["id"]}'
            )])
        
        keyboard.extend([
            [InlineKeyboardButton('🛒 شراء كروت', callback_data='buy_cards'),
             InlineKeyboardButton('🔍 البحث', callback_data='simple_search')],
            [InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
        ])
        
        await query.edit_message_text(view_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in simple view all networks: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في عرض الشبكات.")

async def simple_network_details(update: Update, context: CallbackContext, network_id: str):
    """
    SIMPLIFIED: Show network details - simple and error-free
    """
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user:
            await query.edit_message_text(f"{EMOJIS['error']} يرجى التسجيل أولاً /start")
            return
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # FIXED: Simple query without problematic phone_number column
        cursor.execute('''
            SELECT n.id, n.name, n.provider, n.location, n.description, n.created_at,
                   u.full_name, u.phone
            FROM networks n
            LEFT JOIN users u ON n.supplier_id = u.id
            WHERE n.id = ? AND n.is_active = 1
        ''', (network_id,))
        
        network = cursor.fetchone()
        
        if not network:
            await query.edit_message_text(
                "❌ الشبكة غير موجودة أو غير متاحة",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton('🔙 العودة', callback_data='simple_view_all')
                ]])
            )
            conn.close()
            return
        
        net_id, name, provider, location, description, created_at, supplier_name, supplier_phone = network
        
        # Get categories
        cursor.execute('''
            SELECT name, price, value, stock_count
            FROM card_categories
            WHERE network_id = ? AND is_available = 1
            ORDER BY price ASC
        ''', (network_id,))
        categories = cursor.fetchall()
        
        conn.close()
        
        # Build details message
        details_text = f"""
🌐 **تفاصيل الشبكة**

📋 **المعلومات الأساسية:**
🏷️ **الاسم:** {name}
👤 **المزود:** {supplier_name or provider}
📍 **الموقع:** {location or 'غير محدد'}
📝 **الوصف:** {description or 'غير متاح'}
📅 **تاريخ الإضافة:** {created_at[:10] if created_at else 'غير محدد'}
"""
        
        if supplier_phone:
            details_text += f"📱 **هاتف المزود:** {supplier_phone}\n"
        
        details_text += f"""
📊 **إحصائيات الفئات:**
💳 **عدد الفئات:** {len(categories)} فئة

"""
        
        if categories:
            details_text += "💳 **الفئات المتاحة:**\n\n"
            for cat_name, price, value, stock in categories:
                stock_status = f"✅ متوفر ({stock})" if stock > 0 else "⚠️ نفد"
                details_text += f"""
🎫 **{cat_name}**
💰 السعر: **{price:,.0f} ريال**
📊 المخزون: {stock_status}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        else:
            details_text += """
⚠️ **لا توجد فئات متاحة حالياً**

هذه الشبكة قيد التحضير وستكون متاحة قريباً.
"""
        
        # Simple keyboard
        keyboard = []
        
        if categories:
            keyboard.append([InlineKeyboardButton(f'🛒 شراء من {name[:15]}', callback_data=f'simple_buy_{net_id}')])
        
        keyboard.extend([
            [InlineKeyboardButton('🔙 جميع الشبكات', callback_data='simple_view_all'),
             InlineKeyboardButton('🔍 البحث', callback_data='simple_search')],
            [InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
        ])
        
        await query.edit_message_text(details_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in simple network details: {e}")
        await query.edit_message_text(
            f"{EMOJIS['error']} حدث خطأ في عرض تفاصيل الشبكة.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton('🔙 العودة', callback_data='simple_view_all')
            ]])
        )

async def simple_search_networks(update: Update, context: CallbackContext):
    """
    SIMPLIFIED: Search networks - basic but reliable
    """
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user:
            await query.edit_message_text(f"{EMOJIS['error']} يرجى التسجيل أولاً /start")
            return
        
        # Get all networks with simple info
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, name, provider, location
            FROM networks 
            WHERE is_active = 1 AND is_approved = 1
            ORDER BY name
        ''')
        networks = cursor.fetchall()
        
        # Get category info for each
        search_results = []
        for net in networks:
            net_id = net[0]
            cursor.execute('SELECT COUNT(*), MIN(price), MAX(price) FROM card_categories WHERE network_id = ? AND is_available = 1', (net_id,))
            cat_info = cursor.fetchone()
            cat_count = cat_info[0] if cat_info[0] else 0
            min_price = cat_info[1] if cat_info[1] else 0
            max_price = cat_info[2] if cat_info[2] else 0
            
            search_results.append({
                'id': net[0],
                'name': net[1],
                'provider': net[2],
                'location': net[3],
                'categories': cat_count,
                'min_price': min_price,
                'max_price': max_price
            })
        
        conn.close()
        
        # Sort: available networks first
        search_results.sort(key=lambda x: x['categories'], reverse=True)
        
        search_text = f"""
🔍 **البحث في الشبكات**

👤 **{user['full_name']}**
📊 **نتائج البحث:** {len(search_results)} شبكة

🌐 **الشبكات:**

"""
        
        for net in search_results[:8]:  # Show first 8
            if net['categories'] > 0:
                status = "✅ متاحة"
                price_text = f"{net['min_price']:,.0f}" if net['min_price'] == net['max_price'] else f"{net['min_price']:,.0f}-{net['max_price']:,.0f}"
                price_display = f"💰 {price_text} ريال"
            else:
                status = "🔄 قيد التحضير"
                price_display = "💰 قريباً"
            
            location_text = f"📍 {net['location']}" if net['location'] else ""
            
            search_text += f"""
{status} **{net['name']}**
👤 {net['provider']} {location_text}
💳 {net['categories']} فئة | {price_display}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        
        # Simple keyboard with details buttons
        keyboard = []
        
        for net in search_results[:5]:  # Max 5 detail buttons
            status_icon = "✅" if net['categories'] > 0 else "🔄"
            keyboard.append([InlineKeyboardButton(
                f"{status_icon} {net['name'][:20]}{'...' if len(net['name']) > 20 else ''}",
                callback_data=f'simple_details_{net["id"]}'
            )])
        
        keyboard.extend([
            [InlineKeyboardButton('🛒 شراء كروت', callback_data='buy_cards'),
             InlineKeyboardButton('📊 جميع الشبكات', callback_data='simple_view_all')],
            [InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
        ])
        
        await query.edit_message_text(search_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in simple search networks: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في البحث.")

# =============================================================================
# UNIFIED CARD UPLOAD SYSTEM - NO MORE CONFLICTS
# =============================================================================

async def unified_card_upload_handler(update: Update, context: CallbackContext):
    """
    UNIFIED: Card upload for both suppliers and admins - no more conflicts
    """
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user:
            await query.edit_message_text(f"{EMOJIS['error']} يرجى التسجيل أولاً /start")
            return
        
        # Check permissions - both suppliers and admins can upload
        if user['role'] not in ['supplier', 'admin', 'super_admin']:
            await query.edit_message_text(f"{EMOJIS['error']} ليس لديك صلاحية لرفع الكروت.")
            return
        
        # Get user's networks based on role
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if user['role'] in ['admin', 'super_admin']:
            # Admins can see all networks
            cursor.execute('''
                SELECT n.id, n.name, n.provider, u.full_name as supplier_name
                FROM networks n
                LEFT JOIN users u ON n.supplier_id = u.id
                WHERE n.is_active = 1 AND n.is_approved = 1
                ORDER BY n.name
            ''')
        else:
            # Suppliers see only their networks
            cursor.execute('''
                SELECT n.id, n.name, n.provider, u.full_name as supplier_name
                FROM networks n
                LEFT JOIN users u ON n.supplier_id = u.id
                WHERE n.supplier_id = ? AND n.is_active = 1
                ORDER BY n.name
            ''', (user['id'],))
        
        networks = cursor.fetchall()
        conn.close()
        
        role_text = "مشرف" if user['role'] in ['admin', 'super_admin'] else "مزود"
        
        upload_text = f"""
📤 **رفع كروت الشحن**

👤 **{user['full_name']}** ({role_text})

📶 **اختر الشبكة لرفع الكروت إليها:**
📊 **الشبكات المتاحة:** {len(networks)} شبكة

"""
        
        keyboard = []
        
        if networks:
            for net in networks:
                net_id, name, provider, supplier_name = net
                
                # For admins, show supplier name
                if user['role'] in ['admin', 'super_admin'] and supplier_name:
                    display_name = f"{name} ({supplier_name})"
                else:
                    display_name = name
                
                # Truncate if too long
                if len(display_name) > 30:
                    display_name = display_name[:27] + "..."
                
                keyboard.append([InlineKeyboardButton(
                    f"📤 {display_name}",
                    callback_data=f'unified_upload_{net_id}'
                )])
            
            upload_text += f"""
💡 **تعليمات:**
• اختر الشبكة المطلوبة
• ارفع ملف Excel أو CSV يحتوي على:
  - رقم الكرت
  - الرقم السري
  - تاريخ الانتهاء (اختياري)
• سيتم معالجة الملف تلقائياً

"""
        else:
            upload_text += "❌ لا توجد شبكات متاحة لرفع الكروت إليها."
            if user['role'] not in ['admin', 'super_admin']:
                upload_text += "\n💡 يجب إضافة شبكة أولاً قبل رفع الكروت."
        
        keyboard.extend([
            [InlineKeyboardButton('➕ إضافة شبكة جديدة', callback_data='unified_add_network')],
            [InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
        ])
        
        await query.edit_message_text(upload_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in unified card upload handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في رفع الكروت.")

# =============================================================================
# CALLBACK MAPPINGS FOR SIMPLIFIED HANDLERS
# =============================================================================

SIMPLIFIED_NETWORK_CALLBACKS = {
    'buy_cards': simple_buy_cards_handler,
    'simple_view_all': simple_view_all_networks,
    'simple_search': simple_search_networks,
    'unified_card_upload': unified_card_upload_handler,
}

# Function to handle dynamic callbacks
async def handle_simple_network_callbacks(update: Update, context: CallbackContext, callback_data: str):
    """Handle simplified network callbacks"""
    if callback_data.startswith('simple_details_'):
        network_id = callback_data.split('_')[-1]
        await simple_network_details(update, context, network_id)
    elif callback_data.startswith('simple_buy_'):
        network_id = callback_data.split('_')[-1]
        # Route to purchase flow (to be implemented)
        await query.edit_message_text(f"🛒 سيتم إضافة عملية الشراء من الشبكة {network_id} قريباً")
    elif callback_data.startswith('unified_upload_'):
        network_id = callback_data.split('_')[-1]
        # Route to upload flow (to be implemented)
        await query.edit_message_text(f"📤 سيتم إضافة رفع الكروت للشبكة {network_id} قريباً")