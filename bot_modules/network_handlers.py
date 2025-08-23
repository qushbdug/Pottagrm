#!/usr/bin/env python3
"""
Network Handlers Module
Handles network-related functionality
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext
from bot_modules.config import *
from bot_modules.utils import *
from bot_modules.database import get_db_connection
from bot_modules.callback_utils import create_callback

logger = logging.getLogger(__name__)

async def search_networks_handler(update: Update, context: CallbackContext):
    """Handle network search"""
    try:
        query = update.callback_query
        user = get_user(query.from_user.id)
        
        if not user:
            await query.edit_message_text(f"{EMOJIS['error']} يرجى التسجيل أولاً /start")
            return
        
        search_text = """
🔍 **البحث في الشبكات** 🔍

📊 **إجمالي الشبكات المتاحة:** 0 شبكة

💡 **كيفية البحث:**
• اكتب اسم الشبكة (مثال: يمنتل)
• اكتب معرف الشبكة (مثال: 123)
• اكتب اسم المزود (مثال: MTN)

🔍 **ابدأ البحث الآن:**
"""
        
        keyboard = [
            [InlineKeyboardButton('🔍 بحث سريع: يمنتل', callback_data='quick_search_yemen_tel')],
            [InlineKeyboardButton('🔍 بحث سريع: MTN', callback_data='quick_search_mtn')],
            [InlineKeyboardButton('🔙 عودة لشراء الكروت', callback_data='buy_cards')]
        ]
        
        # Set search state for customer
        context.user_data['customer_searching_network'] = True
        
        await query.edit_message_text(search_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in search networks handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في البحث عن الشبكات.")

async def show_network_details(update: Update, context: CallbackContext, network_id: str):
    """Show network details"""
    try:
        query = update.callback_query
        user = get_user(query.from_user.id)
        
        if not user:
            await query.edit_message_text(f"{EMOJIS['error']} يرجى التسجيل أولاً /start")
            return
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get network details
        cursor.execute('''
            SELECT n.id, n.name, n.provider, n.location, n.description,
                   COUNT(cc.id) as categories_count,
                   MIN(cc.price) as min_price, MAX(cc.price) as max_price
            FROM networks n
            LEFT JOIN card_categories cc ON n.id = cc.network_id AND cc.is_available = 1
            WHERE n.id = ? AND n.is_active = 1 AND n.is_approved = 1
            GROUP BY n.id, n.name, n.provider, n.location, n.description
        ''', (network_id,))
        
        network = cursor.fetchone()
        conn.close()
        
        if not network:
            await query.edit_message_text("❌ الشبكة غير موجودة أو غير متاحة.")
            return
        
        net_id, name, provider, location, description, cat_count, min_price, max_price = network
        
        # Build network details text
        details_text = f"""
🌐 **تفاصيل الشبكة** 🌐

📡 **الاسم:** {name}
👤 **المزود:** {provider}
📍 **الموقع:** {location or 'غير محدد'}
📝 **الوصف:** {description or 'لا يوجد وصف'}

💳 **فئات الكروت:** {cat_count} فئة
💰 **نطاق الأسعار:** {min_price:,.0f} - {max_price:,.0f} ريال
"""
        
        # Create keyboard
        keyboard = []
        if cat_count > 0:
            keyboard.append([InlineKeyboardButton('🛒 شراء كرت', callback_data=create_callback('buy_from_network', network_id=net_id))])
        
        keyboard.extend([
            [InlineKeyboardButton('🔙 عودة للشبكات', callback_data='buy_cards')],
            [InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
        ])
        
        await query.edit_message_text(details_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in show network details: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في عرض تفاصيل الشبكة.")

def setup_network_handlers(application):
    """Setup network handlers"""
    # Network handlers are called via callback handlers
    pass

async def view_networks_handler(update: Update, context: CallbackContext):
    """View all available networks"""
    try:
        query = update.callback_query
        user = get_user(query.from_user.id)
        
        if not user:
            await query.edit_message_text(f"{EMOJIS['error']} يرجى التسجيل أولاً /start")
            return
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get all active networks
        cursor.execute('''
            SELECT n.id, n.name, n.provider, n.location,
                   COUNT(cc.id) as categories_count,
                   MIN(cc.price) as min_price, MAX(cc.price) as max_price
            FROM networks n
            LEFT JOIN card_categories cc ON n.id = cc.network_id AND cc.is_available = 1
            WHERE n.is_active = 1 AND n.is_approved = 1
            GROUP BY n.id, n.name, n.provider, n.location
            ORDER BY n.name
        ''')
        
        networks = cursor.fetchall()
        conn.close()
        
        if not networks:
            await query.edit_message_text("❌ لا توجد شبكات متاحة حالياً.")
            return
        
        # Build networks list
        networks_text = f"🌐 **الشبكات المتاحة ({len(networks)} شبكة):**\n\n"
        
        keyboard = []
        for network in networks:
            net_id, name, provider, location, cat_count, min_price, max_price = network
            
            if cat_count > 0:
                price_range = f"{min_price:,.0f} - {max_price:,.0f}" if min_price != max_price else f"{min_price:,.0f}"
                networks_text += f"🌐 **{name}**\n👤 {provider}\n📍 {location or 'غير محدد'}\n💳 {cat_count} فئة | 💰 {price_range} ريال\n\n"
                
                keyboard.append([
                    InlineKeyboardButton(f'🛒 شراء من {name}', callback_data=create_callback('buy_from_network', network_id=net_id))
                ])
            else:
                networks_text += f"🌐 **{name}**\n👤 {provider}\n📍 {location or 'غير محدد'}\n💳 لا توجد فئات كروت بعد\n💰 لم يتم تحديد الأسعار\n\n"
        
        # Add navigation buttons
        keyboard.extend([
            [InlineKeyboardButton('🔍 البحث في الشبكات', callback_data='customer_search_networks')],
            [InlineKeyboardButton('🔙 القائمة الرئيسية', callback_data='main_menu')]
        ])
        
        await query.edit_message_text(networks_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in view networks handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في عرض الشبكات.")

async def buy_from_network_handler(update: Update, context: CallbackContext, network_id: str):
    """Handle buying from specific network"""
    try:
        query = update.callback_query
        user = get_user(query.from_user.id)
        
        if not user:
            await query.edit_message_text(f"{EMOJIS['error']} يرجى التسجيل أولاً /start")
            return
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get network categories
        cursor.execute('''
            SELECT cc.id, cc.name, cc.price, cc.stock_count, cc.value
            FROM card_categories cc
            WHERE cc.network_id = ? AND cc.is_available = 1
            ORDER BY cc.price
        ''', (network_id,))
        
        categories = cursor.fetchall()
        
        # Get network name
        cursor.execute('SELECT name FROM networks WHERE id = ?', (network_id,))
        network_name = cursor.fetchone()[0]
        
        conn.close()
        
        if not categories:
            await query.edit_message_text(f"❌ لا توجد فئات كروت متاحة في {network_name}.")
            return
        
        # Build categories list
        categories_text = f"💳 **فئات الكروت المتاحة في {network_name}:**\n\n"
        
        keyboard = []
        for category in categories:
            cat_id, name, price, stock, value = category
            categories_text += f"💳 **{name}**\n💰 السعر: {price:,.0f} ريال\n📦 المتاح: {stock} كرت\n📊 الحجم: {value} ميجابايت\n\n"
            
            keyboard.append([
                InlineKeyboardButton(f'🛒 شراء {name} - {price:,.0f} ريال', 
                                   callback_data=create_callback('buy_category', category_id=cat_id))
            ])
        
        # Add navigation buttons
        keyboard.extend([
            [InlineKeyboardButton('🔙 عودة للشبكة', callback_data=create_callback('network', network_id=network_id))],
            [InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
        ])
        
        await query.edit_message_text(categories_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in buy from network handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في عرض فئات الكروت.")

async def buy_cards_handler(update: Update, context: CallbackContext):
    """Handle buy cards main menu"""
    try:
        query = update.callback_query
        user = get_user(query.from_user.id)
        
        if not user:
            await query.edit_message_text(f"{EMOJIS['error']} يرجى التسجيل أولاً /start")
            return
        
        buy_text = f"""
🛒 **شراء كروت الإنترنت** 🛒

👤 **{user['full_name']}**
💰 **رصيدك:** {user['balance']:,.2f} ريال

📶 **الشبكات المتاحة:** 0 شبكة

💡 **اختر الشبكة المطلوبة:**
"""
        
        keyboard = [
            [InlineKeyboardButton('🌐 جميع الشبكات', callback_data='all_networks')],
            [InlineKeyboardButton('📱 شبكات الجوال', callback_data='mobile_networks')],
            [InlineKeyboardButton('🏠 شبكات المنزل', callback_data='home_networks')],
            [InlineKeyboardButton('🔍 البحث في الشبكات', callback_data='customer_search_networks')],
            [InlineKeyboardButton('🔙 القائمة الرئيسية', callback_data='main_menu')]
        ]
        
        await query.edit_message_text(buy_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in buy cards handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في عرض قائمة شراء الكروت.")

async def customer_search_networks_handler(update: Update, context: CallbackContext):
    """Handle customer network search"""
    try:
        query = update.callback_query
        user = get_user(query.from_user.id)
        
        if not user:
            await query.edit_message_text(f"{EMOJIS['error']} يرجى التسجيل أولاً /start")
            return
        
        search_text = """
🔍 **البحث في الشبكات** 🔍

📊 **إجمالي الشبكات المتاحة:** 0 شبكة

💡 **كيفية البحث:**
• اكتب اسم الشبكة (مثال: يمنتل)
• اكتب معرف الشبكة (مثال: 123)
• اكتب اسم المزود (مثال: MTN)

🔍 **ابدأ البحث الآن:**
"""
        
        keyboard = [
            [InlineKeyboardButton('🔍 بحث سريع: يمنتل', callback_data='quick_search_yemen_tel')],
            [InlineKeyboardButton('🔍 بحث سريع: MTN', callback_data='quick_search_mtn')],
            [InlineKeyboardButton('🔙 عودة لشراء الكروت', callback_data='buy_cards')]
        ]
        
        # Set search state for customer
        context.user_data['customer_searching_network'] = True
        
        await query.edit_message_text(search_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in customer search networks handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في البحث عن الشبكات.")

async def perform_quick_search(update: Update, context: CallbackContext, search_term: str):
    """Perform quick search for networks"""
    try:
        query = update.callback_query
        user = get_user(query.from_user.id)
        
        if not user:
            await query.edit_message_text(f"{EMOJIS['error']} يرجى التسجيل أولاً /start")
            return
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Search networks
        cursor.execute('''
            SELECT n.id, n.name, n.provider, n.location,
                   COUNT(cc.id) as categories_count,
                   MIN(cc.price) as min_price, MAX(cc.price) as max_price
            FROM networks n
            LEFT JOIN card_categories cc ON n.id = cc.network_id AND cc.is_available = 1
            WHERE n.is_active = 1 AND n.is_approved = 1 
                  AND (n.name LIKE ? OR n.provider LIKE ? OR n.id = ?)
            GROUP BY n.id, n.name, n.provider, n.location
            ORDER BY n.name
        ''', (f'%{search_term}%', f'%{search_term}%', search_term))
        
        networks = cursor.fetchall()
        conn.close()
        
        if not networks:
            search_results = f"""
🔍 **نتائج البحث عن: "{search_term}"**

❌ **لم يتم العثور على شبكات تطابق البحث**

💡 **اقتراحات:**
• تأكد من كتابة الاسم بشكل صحيح
• جرب البحث باسم المزود (مثل: يمنتل، MTN)
• تحقق من معرف الشبكة (رقم)
• تأكد أن الشبكة معتمدة ونشطة
"""
            keyboard = [
                [InlineKeyboardButton('🔍 بحث جديد', callback_data='customer_search_networks')],
                [InlineKeyboardButton('🔙 عودة لشراء الكروت', callback_data='buy_cards')]
            ]
        else:
            search_results = f"""
🔍 **نتائج البحث عن: "{search_term}"**

📊 **تم العثور على {len(networks)} شبكة:**

"""
            
            keyboard = []
            for network in networks:
                net_id, name, provider, location, cat_count, min_price, max_price = network
                
                if cat_count > 0:
                    price_range = f"{min_price:,.0f} - {max_price:,.0f}" if min_price != max_price else f"{min_price:,.0f}"
                    search_results += f"""
🌐 **{name}** (ID: {net_id})
👤 {provider} 📍 {location or 'غير محدد'}
💳 {cat_count} فئة متاحة
💰 {price_range} ريال
━━━━━━━━━━━━━━━━━━━━━━━━━
"""
                    keyboard.append([
                        InlineKeyboardButton(f'🛒 شراء من {name}', callback_data=create_callback('buy_from_network', network_id=net_id))
                    ])
                else:
                    search_results += f"""
🌐 **{name}** (ID: {net_id})
👤 {provider} 📍 {location or 'غير محدد'}
💳 لا توجد فئات كروت بعد
💰 لم يتم تحديد الأسعار
━━━━━━━━━━━━━━━━━━━━━━━━━
"""
                    keyboard.append([
                        InlineKeyboardButton(f'👁️ عرض {name} (لا توجد فئات)', callback_data=create_callback('network', network_id=net_id))
                    ])
            
            keyboard.extend([
                [InlineKeyboardButton('🔍 بحث جديد', callback_data='customer_search_networks')],
                [InlineKeyboardButton('🔙 عودة لشراء الكروت', callback_data='buy_cards')]
            ])
        
        # Remove search state
        if 'customer_searching_network' in context.user_data:
            del context.user_data['customer_searching_network']
        
        await query.edit_message_text(search_results, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in perform quick search: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في البحث.")