#!/usr/bin/env python3
"""
Simplified and Fixed Network Display Manager for Yemen Net Bot
Fixes all issues and provides simplified, user-friendly network display

Issues Fixed:
1. ❌ no such column: u.phone_number → ✅ Fixed to use correct column 'phone'
2. ❌ Complex network display → ✅ Simplified and user-friendly
3. ❌ Errors in network details → ✅ Robust error handling

Features:
- Simple and clear network listing
- Correct database column references
- Better error handling
- Unified display approach

Author: Software Maintenance Engineer
Version: 2.0.0 (Simplified & Fixed)
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
# SIMPLIFIED NETWORK DISPLAY FUNCTIONS
# =============================================================================

async def simple_buy_cards_handler(update: Update, context: CallbackContext):
    """
    SIMPLIFIED: Buy cards handler - clean and simple display
    """
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user:
            await query.edit_message_text(f"{EMOJIS['error']} يرجى التسجيل أولاً /start")
            return
        
        # Get all active networks with simple query
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # SIMPLIFIED SQL - easier to understand and maintain
        cursor.execute('''
            SELECT n.id, n.name, n.provider, n.location, 
                   COUNT(cc.id) as category_count,
                   MIN(cc.price) as min_price, 
                   MAX(cc.price) as max_price
            FROM networks n
            LEFT JOIN card_categories cc ON n.id = cc.network_id AND cc.is_available = 1
            WHERE n.is_active = 1 AND n.is_approved = 1
            GROUP BY n.id, n.name, n.provider, n.location
            ORDER BY category_count DESC, n.name
        ''')
        networks = cursor.fetchall()
        conn.close()
        
        # SIMPLIFIED display
        buy_text = f"""
🛒 **شراء كروت الإنترنت**

👤 **{user['full_name']}**
💰 رصيدك: **{user['balance']:,.0f}** ريال

📶 **الشبكات المتاحة: {len(networks)} شبكة**

"""
        
        if networks:
            for network in networks:
                net_id, name, provider, location, cat_count, min_price, max_price = network
                
                # Simple status
                if cat_count > 0:
                    status = "✅ متاحة"
                    price_text = f"{min_price:,.0f}" if min_price == max_price else f"{min_price:,.0f}-{max_price:,.0f}"
                else:
                    status = "🔄 قريباً"
                    price_text = "قيد التحضير"
                
                # Simple format
                buy_text += f"""
🌐 **{name}**
👤 {provider}
📍 {location or 'غير محدد'}
💳 {cat_count} فئة | 💰 {price_text} ريال
🔖 {status}
━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        else:
            buy_text += "❌ لا توجد شبكات متاحة حالياً"
        
        # Simple buttons
        keyboard = []
        
        if networks:
            for network in networks[:6]:  # First 6 networks
                net_id, name, provider, location, cat_count = network[0], network[1], network[2], network[3], network[4]
                
                if cat_count > 0:
                    # Shorten name if too long
                    display_name = name[:25] + "..." if len(name) > 25 else name
                    keyboard.append([InlineKeyboardButton(
                        f"🛒 {display_name}", 
                        callback_data=f'simple_buy_from_{net_id}'
                    )])
        
        # Simple navigation
        keyboard.extend([
            [InlineKeyboardButton('📊 عرض كل الشبكات', callback_data='simple_view_all'),
             InlineKeyboardButton('🔍 البحث', callback_data='simple_search')],
            [InlineKeyboardButton('💰 شحن رصيد', callback_data='recharge_balance'),
             InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
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
            SELECT n.id, n.name, n.provider, n.location, n.created_at,
                   COUNT(cc.id) as category_count
            FROM networks n
            LEFT JOIN card_categories cc ON n.id = cc.network_id AND cc.is_available = 1
            WHERE n.is_active = 1 AND n.is_approved = 1
            GROUP BY n.id, n.name, n.provider, n.location, n.created_at
            ORDER BY category_count DESC, n.created_at DESC
        ''')
        networks = cursor.fetchall()
        conn.close()
        
        # Simple display
        text = f"""
📶 **جميع الشبكات ({len(networks)} شبكة)**

👤 **{user['full_name']}**

"""
        
        if networks:
            for i, network in enumerate(networks, 1):
                net_id, name, provider, location, created_at, cat_count = network
                
                # Simple status
                status = "✅" if cat_count > 0 else "🔄"
                date = created_at[:10] if created_at else "غير محدد"
                
                text += f"""
{i}. {status} **{name}**
👤 {provider}
📍 {location or 'غير محدد'}
💳 {cat_count} فئة
📅 {date}
━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        else:
            text += "❌ لا توجد شبكات متاحة"
        
        # Simple buttons for details
        keyboard = []
        if networks:
            for network in networks[:5]:  # First 5 for details
                net_id, name = network[0], network[1]
                display_name = name[:20] + "..." if len(name) > 20 else name
                keyboard.append([InlineKeyboardButton(
                    f'👁️ {display_name}',
                    callback_data=f'simple_details_{net_id}'
                )])
        
        keyboard.extend([
            [InlineKeyboardButton('🛒 شراء كروت', callback_data='buy_cards'),
             InlineKeyboardButton('🔍 البحث', callback_data='simple_search')],
            [InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
        ])
        
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in simple view all networks: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في عرض الشبكات.")

async def simple_network_details(update: Update, context: CallbackContext, network_id: str):
    """
    SIMPLIFIED: Network details - FIXED phone column issue
    """
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user:
            await query.edit_message_text(f"{EMOJIS['error']} يرجى التسجيل أولاً /start")
            return
        
        # Get network details with CORRECT column name
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # FIXED: Use 'phone' instead of 'phone_number'
        cursor.execute('''
            SELECT n.id, n.name, n.provider, n.location, n.description, n.created_at,
                   u.full_name as supplier_name, u.phone as supplier_phone,
                   COUNT(cc.id) as category_count,
                   MIN(cc.price) as min_price, 
                   MAX(cc.price) as max_price
            FROM networks n
            LEFT JOIN users u ON n.supplier_id = u.id
            LEFT JOIN card_categories cc ON n.id = cc.network_id AND cc.is_available = 1
            WHERE n.id = ? AND n.is_active = 1
            GROUP BY n.id, n.name, n.provider, n.location, n.description, n.created_at, u.full_name, u.phone
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
        
        (net_id, name, provider, location, description, created_at,
         supplier_name, supplier_phone, cat_count, min_price, max_price) = network
        
        # Get card categories (simple)
        cursor.execute('''
            SELECT name, value, price, stock_count
            FROM card_categories
            WHERE network_id = ? AND is_available = 1
            ORDER BY price ASC
        ''', (network_id,))
        categories = cursor.fetchall()
        
        conn.close()
        
        # SIMPLIFIED details display
        details_text = f"""
🌐 **{name}**

📋 **المعلومات:**
👤 المزود: {supplier_name or provider}
📍 الموقع: {location or 'غير محدد'}
📝 الوصف: {description or 'غير متاح'}
📅 تاريخ الإضافة: {created_at[:10] if created_at else 'غير محدد'}
"""

        # Add supplier contact if available
        if supplier_phone:
            details_text += f"📱 هاتف المزود: {supplier_phone}\n"

        # Simple category display
        details_text += f"\n💳 **الفئات المتاحة: {cat_count}**\n\n"
        
        if categories:
            for cat_name, cat_value, price, stock in categories:
                stock_text = f"({stock} كرت)" if stock > 0 else "(نفدت)"
                details_text += f"""
🎫 **{cat_name}**
💰 السعر: {price:,.0f} ريال
📦 المخزون: {stock_text}
━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        else:
            details_text += """
⚠️ **لا توجد فئات متاحة حالياً**

هذه الشبكة قيد التحضير وستكون متاحة قريباً.
"""
        
        # Simple action buttons
        keyboard = []
        
        if cat_count > 0:
            keyboard.append([InlineKeyboardButton(
                f'🛒 شراء من {name[:15]}...', 
                callback_data=f'simple_buy_from_{net_id}'
            )])
        
        keyboard.extend([
            [InlineKeyboardButton('🔙 العودة لكل الشبكات', callback_data='simple_view_all'),
             InlineKeyboardButton('🔍 البحث', callback_data='simple_search')],
            [InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
        ])
        
        await query.edit_message_text(details_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in simple network details: {e}")
        await query.edit_message_text(
            f"{EMOJIS['error']} حدث خطأ في عرض تفاصيل الشبكة.\n\nالخطأ: {str(e)}",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton('🔙 العودة', callback_data='simple_view_all')
            ]])
        )

async def simple_search_networks(update: Update, context: CallbackContext):
    """
    SIMPLIFIED: Search networks - basic search functionality
    """
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user:
            await query.edit_message_text(f"{EMOJIS['error']} يرجى التسجيل أولاً /start")
            return
        
        # Simple search display
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT n.id, n.name, n.provider, n.location,
                   COUNT(cc.id) as category_count
            FROM networks n
            LEFT JOIN card_categories cc ON n.id = cc.network_id AND cc.is_available = 1
            WHERE n.is_active = 1 AND n.is_approved = 1
            GROUP BY n.id, n.name, n.provider, n.location
            ORDER BY category_count DESC, n.name
        ''')
        networks = cursor.fetchall()
        conn.close()
        
        search_text = f"""
🔍 **البحث في الشبكات**

👤 **{user['full_name']}**

📊 **المتاح: {len(networks)} شبكة**

🌐 **الشبكات:**

"""
        
        if networks:
            # Show networks with simple format
            for network in networks[:8]:  # First 8
                net_id, name, provider, location, cat_count = network
                status = "✅" if cat_count > 0 else "🔄"
                
                search_text += f"""
{status} **{name}**
👤 {provider} | 📍 {location or 'غير محدد'}
💳 {cat_count} فئة متاحة
━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        else:
            search_text += "❌ لا توجد شبكات"
        
        # Simple search buttons
        keyboard = []
        if networks:
            for network in networks[:4]:  # First 4 for buttons
                net_id, name = network[0], network[1]
                cat_count = network[4]
                status = "✅" if cat_count > 0 else "🔄"
                display_name = name[:15] + "..." if len(name) > 15 else name
                
                keyboard.append([InlineKeyboardButton(
                    f'{status} {display_name}',
                    callback_data=f'simple_details_{net_id}'
                )])
        
        keyboard.extend([
            [InlineKeyboardButton('📊 عرض الكل', callback_data='simple_view_all'),
             InlineKeyboardButton('🛒 شراء كروت', callback_data='buy_cards')],
            [InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
        ])
        
        await query.edit_message_text(search_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in simple search networks: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في البحث.")

# =============================================================================
# CALLBACK HANDLERS MAPPING
# =============================================================================

SIMPLE_NETWORK_CALLBACKS = {
    'buy_cards': simple_buy_cards_handler,
    'simple_view_all': simple_view_all_networks,
    'simple_search': simple_search_networks,
}

async def handle_simple_network_callbacks(update: Update, context: CallbackContext, callback_data: str):
    """Handle simple network callbacks"""
    try:
        if callback_data.startswith('simple_details_'):
            network_id = callback_data.split('_')[-1]
            await simple_network_details(update, context, network_id)
        elif callback_data.startswith('simple_buy_from_'):
            network_id = callback_data.split('_')[-1]
            # Redirect to purchase flow (to be implemented)
            query = update.callback_query
            await query.answer("🔄 سيتم توجيهك لصفحة الشراء...")
            await simple_network_details(update, context, network_id)
        else:
            # Handle other simple callbacks
            if callback_data in SIMPLE_NETWORK_CALLBACKS:
                await SIMPLE_NETWORK_CALLBACKS[callback_data](update, context)
    except Exception as e:
        logger.error(f"Error in simple network callback handler: {e}")
        query = update.callback_query
        await query.edit_message_text(
            f"{EMOJIS['error']} حدث خطأ. يرجى المحاولة مرة أخرى.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')
            ]])
        )