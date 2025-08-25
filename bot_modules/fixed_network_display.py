#!/usr/bin/env python3
"""
Fixed Network Display Manager for Yemen Net Bot
Fixes all network display issues and unifies network-related functions

Issues Fixed:
1. Networks showing 0 even when they exist (SQL queries were filtering out networks without categories)
2. Network details showing errors (references to non-existent card_categories fields)
3. Duplicate network display functions

Author: Software Maintenance Engineer
Version: 1.0.0 (Fixed)
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
# FIXED NETWORK DISPLAY FUNCTIONS
# =============================================================================

async def fixed_buy_cards_handler(update: Update, context: CallbackContext):
    """
    FIXED: Handle buy cards request - shows all networks even without categories
    """
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user:
            await query.edit_message_text(f"{EMOJIS['error']} يرجى التسجيل أولاً /start")
            return
        
        # Get all active networks (FIXED: don't filter by categories)
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # FIXED SQL: Get networks info with proper category and card counts
        cursor.execute('''
            SELECT n.id, n.name, n.provider, n.location, n.description,
                   COALESCE(cc_count.categories_count, 0) as categories_count,
                   COALESCE(cc_count.min_price, 0) as min_price,
                   COALESCE(cc_count.max_price, 0) as max_price,
                   COALESCE(cards_count.available_cards, 0) as available_cards
            FROM networks n
            LEFT JOIN (
                SELECT network_id, 
                       COUNT(*) as categories_count,
                       MIN(price) as min_price,
                       MAX(price) as max_price
                FROM card_categories 
                WHERE is_available = 1
                GROUP BY network_id
            ) cc_count ON n.id = cc_count.network_id
            LEFT JOIN (
                SELECT cc.network_id,
                       COUNT(CASE WHEN c.is_sold = 0 THEN 1 END) as available_cards
                FROM card_categories cc
                LEFT JOIN cards c ON cc.id = c.category_id
                GROUP BY cc.network_id
            ) cards_count ON n.id = cards_count.network_id
            WHERE n.is_active = 1 AND n.is_approved = 1
            ORDER BY n.name
        ''')
        networks = cursor.fetchall()
        conn.close()
        
        buy_text = f"""
🛒 **شراء كروت الإنترنت** 🛒

👤 **{user['full_name']}**
💰 رصيدك: **{user['balance']:,.2f}** ريال

📶 **الشبكات المتاحة ({len(networks)} شبكة):**

"""
        
        if networks:
            for network in networks:
                net_id, name, provider, location, description, cat_count, min_price, max_price, available_cards = network
                location_text = f"📍 {location}" if location else "📍 غير محدد"
                
                # Handle price range display
                if min_price and max_price and min_price != max_price:
                    price_range = f"{min_price:,.0f} - {max_price:,.0f} ريال"
                elif min_price:
                    price_range = f"{min_price:,.0f} ريال"
                else:
                    price_range = "لم يتم تحديد الأسعار بعد"
                
                # Status indicators
                status_emoji = "✅" if cat_count > 0 else "⚠️"
                cards_emoji = "📦" if available_cards > 0 else "📭"
                
                buy_text += f"""
{status_emoji} **{name}**
👤 المزود: {provider}
{location_text}
💳 الفئات: {cat_count} فئة متاحة
💰 الأسعار: {price_range}
{cards_emoji} الكروت: {available_cards or 0} كرت متاح
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        else:
            buy_text += "❌ لا توجد شبكات متاحة حالياً"
        
        keyboard = []
        
        # Add network buttons for purchase (show ALL networks)
        if networks:
            for network in networks[:8]:  # Show first 8 networks
                net_id, name = network[0], network[1]
                cat_count = network[5]
                
                if cat_count > 0:
                    button_text = f'🛒 شراء من {name}'
                    callback_data = f'buy_from_network_{net_id}'
                else:
                    button_text = f'👁️ عرض {name} (قريباً)'
                    callback_data = f'view_network_{net_id}'
                
                keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])
        
        keyboard.extend([
            [InlineKeyboardButton('📊 عرض جميع الشبكات', callback_data='fixed_view_all_networks'),
             InlineKeyboardButton('🔍 البحث في الشبكات', callback_data='fixed_search_networks')],
            [InlineKeyboardButton('💰 شحن الرصيد', callback_data='recharge_balance'),
             InlineKeyboardButton('📈 إحصائياتي', callback_data='my_purchase_stats')],
            [InlineKeyboardButton(f'{EMOJIS["home"]} القائمة الرئيسية', callback_data='main_menu')]
        ])
        
        await query.edit_message_text(buy_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in fixed buy cards handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في عرض صفحة الشراء: {e}")

async def fixed_view_networks_handler(update: Update, context: CallbackContext):
    """
    FIXED: Handle view all networks - shows all networks with correct data
    """
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user:
            await query.edit_message_text(f"{EMOJIS['error']} يرجى التسجيل أولاً /start")
            return
        
        update_user_activity(user['id'])
        
        # Get all networks with detailed info (FIXED SQL)
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT n.id, n.name, n.provider, n.location, n.description, n.created_at,
                   COALESCE(cc_count.categories_count, 0) as categories_count,
                   COALESCE(cc_count.min_price, 0) as min_price,
                   COALESCE(cc_count.max_price, 0) as max_price,
                   COALESCE(cards_count.available_cards, 0) as available_cards,
                   u.full_name as supplier_name
            FROM networks n
            LEFT JOIN users u ON n.supplier_id = u.id
            LEFT JOIN (
                SELECT network_id, 
                       COUNT(*) as categories_count,
                       MIN(price) as min_price,
                       MAX(price) as max_price
                FROM card_categories 
                WHERE is_available = 1
                GROUP BY network_id
            ) cc_count ON n.id = cc_count.network_id
            LEFT JOIN (
                SELECT cc.network_id,
                       COUNT(CASE WHEN c.is_sold = 0 THEN 1 END) as available_cards
                FROM card_categories cc
                LEFT JOIN cards c ON cc.id = c.category_id
                GROUP BY cc.network_id
            ) cards_count ON n.id = cards_count.network_id
            WHERE n.is_active = 1 AND n.is_approved = 1
            ORDER BY n.created_at DESC
        ''')
        networks = cursor.fetchall()
        conn.close()
        
        networks_text = f"""
📶 **جميع الشبكات المتاحة ({len(networks)} شبكة)** 📶

👤 **{user['full_name']}**

🌐 **الشبكات المعتمدة والمتاحة:**

"""
        
        if networks:
            for i, network in enumerate(networks, 1):
                (net_id, name, provider, location, description, created_at, 
                 cat_count, min_price, max_price, available_cards, supplier_name) = network
                
                location_text = f"📍 {location}" if location else "📍 غير محدد"
                supplier_text = f"👤 المزود: {supplier_name or provider}"
                
                # Handle price range
                if min_price and max_price and min_price != max_price:
                    price_range = f"{min_price:,.0f} - {max_price:,.0f} ريال"
                elif min_price:
                    price_range = f"{min_price:,.0f} ريال"
                else:
                    price_range = "لم يتم تحديد الأسعار بعد"
                
                # Status indicators
                status_emoji = "✅" if cat_count > 0 else "⚠️"
                readiness = "جاهزة للشراء" if cat_count > 0 and available_cards > 0 else "قيد التحضير"
                
                networks_text += f"""
{i}. {status_emoji} **{name}**
{supplier_text}
{location_text}
📝 الوصف: {description or 'غير متاح'}
💳 الفئات: {cat_count} فئة
💰 الأسعار: {price_range}
📦 الكروت المتاحة: {available_cards or 0}
📅 تاريخ الإضافة: {created_at[:10] if created_at else 'غير محدد'}
🔖 الحالة: {readiness}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        else:
            networks_text += "❌ لا توجد شبكات متاحة حالياً"
        
        keyboard = []
        
        # Add buttons to view network details
        if networks:
            for network in networks[:6]:  # First 6 networks
                net_id, name = network[0], network[1]
                cat_count = network[6]
                
                if len(name) > 25:
                    display_name = name[:22] + "..."
                else:
                    display_name = name
                
                keyboard.append([InlineKeyboardButton(
                    f'👁️ عرض تفاصيل {display_name}',
                    callback_data=f'fixed_network_details_{net_id}'
                )])
        
        keyboard.extend([
            [InlineKeyboardButton('🛒 شراء كروت', callback_data='buy_cards'),
             InlineKeyboardButton('🔍 البحث في الشبكات', callback_data='fixed_search_networks')],
            [InlineKeyboardButton(f'{EMOJIS["home"]} القائمة الرئيسية', callback_data='main_menu')]
        ])
        
        await query.edit_message_text(networks_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in fixed view networks handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في عرض الشبكات: {e}")

async def fixed_show_network_details(update: Update, context: CallbackContext, network_id: str):
    """
    FIXED: Show detailed information about a specific network
    """
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user:
            await query.edit_message_text(f"{EMOJIS['error']} يرجى التسجيل أولاً /start")
            return
        
        # Get network details (FIXED SQL - handles missing categories gracefully)
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT n.id, n.name, n.provider, n.location, n.description, n.created_at, n.is_active,
                   u.full_name as supplier_name, u.phone_number as supplier_phone,
                   COALESCE(cc_count.categories_count, 0) as categories_count,
                   COALESCE(cc_count.min_price, 0) as min_price,
                   COALESCE(cc_count.max_price, 0) as max_price,
                   COALESCE(cards_count.available_cards, 0) as available_cards
            FROM networks n
            LEFT JOIN users u ON n.supplier_id = u.id
            LEFT JOIN (
                SELECT network_id, 
                       COUNT(*) as categories_count,
                       MIN(price) as min_price,
                       MAX(price) as max_price
                FROM card_categories 
                WHERE is_available = 1
                GROUP BY network_id
            ) cc_count ON n.id = cc_count.network_id
            LEFT JOIN (
                SELECT cc.network_id,
                       COUNT(CASE WHEN c.is_sold = 0 THEN 1 END) as available_cards
                FROM card_categories cc
                LEFT JOIN cards c ON cc.id = c.category_id
                GROUP BY cc.network_id
            ) cards_count ON n.id = cards_count.network_id
            WHERE n.id = ?
        ''', (network_id,))
        network = cursor.fetchone()
        
        if not network:
            await query.edit_message_text(
                "❌ الشبكة غير موجودة أو غير متاحة",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton('🔙 العودة', callback_data='fixed_view_all_networks')
                ]])
            )
            conn.close()
            return
        
        (net_id, name, provider, location, description, created_at, is_active,
         supplier_name, supplier_phone, cat_count, min_price, max_price, available_cards) = network
        
        # Get available card categories (FIXED: handle empty categories)
        cursor.execute('''
            SELECT id, name, value, price, stock_count, created_at
            FROM card_categories
            WHERE network_id = ? AND is_available = 1
            ORDER BY price ASC
        ''', (network_id,))
        categories = cursor.fetchall()
        
        conn.close()
        
        # Build details text
        location_text = f"📍 **الموقع:** {location}" if location else "📍 **الموقع:** غير محدد"
        status_text = "✅ نشطة" if is_active else "❌ غير نشطة"
        supplier_text = f"👤 **المزود:** {supplier_name or provider}"
        
        if supplier_phone:
            supplier_text += f" (📱 {supplier_phone})"
        
        # Handle price range
        if min_price and max_price and min_price != max_price:
            price_range = f"{min_price:,.0f} - {max_price:,.0f} ريال"
        elif min_price:
            price_range = f"{min_price:,.0f} ريال"
        else:
            price_range = "لم يتم تحديد الأسعار بعد"
        
        details_text = f"""
🌐 **تفاصيل الشبكة** 🌐

📋 **المعلومات الأساسية:**
🏷️ **الاسم:** {name}
{supplier_text}
{location_text}
📝 **الوصف:** {description or 'غير متاح'}
📅 **تاريخ الإضافة:** {created_at[:10] if created_at else 'غير محدد'}
🔖 **الحالة:** {status_text}

📊 **الإحصائيات:**
💳 **عدد الفئات:** {cat_count} فئة
💰 **نطاق الأسعار:** {price_range}
📦 **الكروت المتاحة:** {available_cards or 0} كرت

💳 **فئات الكروت المتاحة:**

"""
        
        if categories:
            for cat_id, cat_name, cat_value, price, stock, cat_created in categories:
                stock_status = f"✅ متوفر ({stock} كرت)" if stock > 0 else "⚠️ نفدت الكمية"
                details_text += f"""
🎫 **{cat_name}**
💰 **السعر:** {price:,.0f} ريال
📊 **المخزون:** {stock_status}
🆔 **القيمة:** {cat_value} ريال
📅 **تاريخ الإضافة:** {cat_created[:10] if cat_created else 'غير محدد'}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        else:
            details_text += """
⚠️ **لا توجد فئات كروت متاحة حالياً**

هذه الشبكة قيد التحضير وستكون متاحة للشراء قريباً.
يمكنك الاطلاع على الشبكات الأخرى أو التحقق لاحقاً.
"""
        
        # Build keyboard
        keyboard = []
        
        if cat_count > 0 and available_cards > 0:
            keyboard.append([InlineKeyboardButton(f'🛒 شراء من {name}', callback_data=f'buy_from_network_{net_id}')])
        else:
            keyboard.append([InlineKeyboardButton(f'📞 التواصل مع المزود', callback_data=f'contact_supplier_{net_id}')])
        
        keyboard.extend([
            [InlineKeyboardButton('🔙 العودة للشبكات', callback_data='fixed_view_all_networks'),
             InlineKeyboardButton('🔍 البحث في الشبكات', callback_data='fixed_search_networks')],
            [InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
        ])
        
        await query.edit_message_text(details_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in fixed show network details: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في عرض تفاصيل الشبكة: {e}")

async def fixed_search_networks_handler(update: Update, context: CallbackContext):
    """
    FIXED: Handle network search with all networks visible
    """
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user:
            await query.edit_message_text(f"{EMOJIS['error']} يرجى التسجيل أولاً /start")
            return
        
        update_user_activity(user['id'])
        
        # Get all networks for search (FIXED: shows all regardless of categories)
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT n.id, n.name, n.provider, n.location,
                   COALESCE(cc_count.categories_count, 0) as categories_count,
                   COALESCE(cc_count.min_price, 0) as min_price,
                   COALESCE(cc_count.max_price, 0) as max_price,
                   COALESCE(cards_count.available_cards, 0) as available_cards
            FROM networks n
            LEFT JOIN (
                SELECT network_id, 
                       COUNT(*) as categories_count,
                       MIN(price) as min_price,
                       MAX(price) as max_price
                FROM card_categories 
                WHERE is_available = 1
                GROUP BY network_id
            ) cc_count ON n.id = cc_count.network_id
            LEFT JOIN (
                SELECT cc.network_id,
                       COUNT(CASE WHEN c.is_sold = 0 THEN 1 END) as available_cards
                FROM card_categories cc
                LEFT JOIN cards c ON cc.id = c.category_id
                GROUP BY cc.network_id
            ) cards_count ON n.id = cards_count.network_id
            WHERE n.is_active = 1 AND n.is_approved = 1
            ORDER BY available_cards DESC, categories_count DESC, n.created_at DESC
        ''')
        networks = cursor.fetchall()
        conn.close()
        
        search_text = f"""
🔍 **البحث في الشبكات** 🔍

👤 **{user['full_name']}**

📊 **إجمالي الشبكات المتاحة:** {len(networks)} شبكة

🌐 **الشبكات المتاحة:**

"""
        
        if networks:
            for network in networks[:10]:  # Show first 10 networks
                net_id, name, provider, location, cat_count, min_price, max_price, available_cards = network
                location_text = f"📍 {location}" if location else "📍 غير محدد"
                
                # Handle price range
                if min_price and max_price and min_price != max_price:
                    price_range = f"{min_price:,.0f} - {max_price:,.0f}"
                elif min_price:
                    price_range = f"{min_price:,.0f}"
                else:
                    price_range = "غير محدد"
                
                # Status indicators
                status_emoji = "✅" if cat_count > 0 and available_cards > 0 else "⚠️" if cat_count > 0 else "🔄"
                
                search_text += f"""
{status_emoji} **{name}**
👤 {provider} {location_text}
💳 {cat_count} فئة | 💰 {price_range} ريال
📦 متاح: {available_cards or 0} كرت
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
            
            if len(networks) > 10:
                search_text += f"\n📄 **عرض أول 10 شبكات من {len(networks)} شبكة**"
        else:
            search_text += "❌ لا توجد شبكات متاحة حالياً"
        
        keyboard = []
        
        # Add network detail buttons
        if networks:
            for network in networks[:6]:  # First 6 networks for buttons
                net_id, name = network[0], network[1]
                cat_count = network[4]
                
                if len(name) > 20:
                    display_name = name[:17] + "..."
                else:
                    display_name = name
                
                status_icon = "✅" if cat_count > 0 else "⚠️"
                keyboard.append([InlineKeyboardButton(
                    f'{status_icon} {display_name}',
                    callback_data=f'fixed_network_details_{net_id}'
                )])
        
        keyboard.extend([
            [InlineKeyboardButton('🛒 شراء كروت', callback_data='buy_cards'),
             InlineKeyboardButton('📊 عرض جميع الشبكات', callback_data='fixed_view_all_networks')],
            [InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
        ])
        
        await query.edit_message_text(search_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in fixed search networks handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في البحث عن الشبكات: {e}")

# =============================================================================
# CALLBACK MAPPINGS FOR FIXED HANDLERS
# =============================================================================

FIXED_NETWORK_CALLBACKS = {
    'buy_cards': fixed_buy_cards_handler,
    'fixed_view_all_networks': fixed_view_networks_handler,
    'fixed_search_networks': fixed_search_networks_handler,
}

# Function to handle network details callbacks dynamically
async def handle_fixed_network_details_callback(update: Update, context: CallbackContext, callback_data: str):
    """Handle fixed network details callbacks"""
    if callback_data.startswith('fixed_network_details_'):
        network_id = callback_data.split('_')[-1]
        await fixed_show_network_details(update, context, network_id)
    elif callback_data.startswith('view_network_'):
        network_id = callback_data.split('_')[-1]
        await fixed_show_network_details(update, context, network_id)