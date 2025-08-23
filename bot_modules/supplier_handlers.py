#!/usr/bin/env python3
"""
Supplier Handlers Module
Handles supplier-related functionality
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext
from bot_modules.config import *
from bot_modules.utils import *
from bot_modules.database import get_db_connection
from bot_modules.callback_utils import create_callback

logger = logging.getLogger(__name__)

async def supplier_panel_handler(update: Update, context: CallbackContext):
    """Handle supplier panel"""
    try:
        query = update.callback_query
        user = get_user(query.from_user.id)
        
        if not user or user['role'] != 'supplier':
            await query.edit_message_text("❌ هذه الميزة متاحة للمزودين فقط.")
            return
        
        panel_text = f"""
🏪 **لوحة المزود** 🏪

👤 **{user['full_name']}**
💰 **رصيدك:** {user['balance']:,.2f} ريال
🌐 **شبكاتك:** 0 شبكة

💡 **اختر الإجراء المطلوب:**
"""
        
        keyboard = [
            [InlineKeyboardButton('🌐 إدارة الشبكات', callback_data='manage_networks')],
            [InlineKeyboardButton('📤 رفع كروت', callback_data='upload_cards')],
            [InlineKeyboardButton('📊 تقارير المبيعات', callback_data='sales_reports')],
            [InlineKeyboardButton('💰 محفظتي', callback_data='enhanced_wallet')],
            [InlineKeyboardButton('🔙 القائمة الرئيسية', callback_data='main_menu')]
        ]
        
        await query.edit_message_text(panel_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in supplier panel handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في عرض لوحة المزود.")

async def manage_networks_handler(update: Update, context: CallbackContext):
    """Handle network management for suppliers"""
    try:
        query = update.callback_query
        user = get_user(query.from_user.id)
        
        if not user or user['role'] != 'supplier':
            await query.edit_message_text("❌ هذه الميزة متاحة للمزودين فقط.")
            return
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get supplier's networks
        cursor.execute('''
            SELECT id, name, provider, city, is_active, is_approved
            FROM networks 
            WHERE supplier_id = ? AND is_active = 1
            ORDER BY name
        ''', (user['id'],))
        
        networks = cursor.fetchall()
        conn.close()
        
        if not networks:
            networks_text = """
🌐 **إدارة الشبكات** 🌐

❌ **لا توجد شبكات لك حالياً**

💡 **يمكنك إدارة الشبكات الموجودة**
"""
            keyboard = [
                [InlineKeyboardButton('🔙 عودة للوحة المزود', callback_data='supplier_panel')]
            ]
        else:
            networks_text = f"""
🌐 **إدارة الشبكات** 🌐

📊 **عدد الشبكات:** {len(networks)} شبكة

"""
            
            keyboard = []
            for network in networks:
                net_id, name, provider, city, is_active, is_approved = network
                status = "✅ معتمدة" if is_approved else "⏳ في انتظار الاعتماد"
                
                networks_text += f"🌐 **{name}**\n👤 {provider}\n📍 {city or 'غير محدد'}\n{status}\n\n"
                
                keyboard.append([
                    InlineKeyboardButton(f'⚙️ إدارة {name}', callback_data=create_callback('manage_network', network_id=net_id))
                ])
            
            keyboard.extend([
                [InlineKeyboardButton('🔙 عودة للوحة المزود', callback_data='supplier_panel')]
            ])
        
        await query.edit_message_text(networks_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in manage networks handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في إدارة الشبكات.")

async def upload_cards_handler(update: Update, context: CallbackContext):
    """Handle card upload for suppliers"""
    try:
        query = update.callback_query
        user = get_user(query.from_user.id)
        
        if not user or user['role'] != 'supplier':
            await query.edit_message_text("❌ هذه الميزة متاحة للمزودين فقط.")
            return
        
        upload_text = f"""
📤 **رفع كروت جديدة** 📤

👤 **{user['full_name']}**
🌐 **عدد الشبكات:** 0 شبكة

💡 **اختر طريقة رفع الكروت:**
"""
        
        keyboard = [
            [InlineKeyboardButton('📁 رفع ملف', callback_data='file_upload')],
            [InlineKeyboardButton('✏️ إدخال يدوي', callback_data='manual_card_input')],
            [InlineKeyboardButton('🔙 عودة للوحة المزود', callback_data='supplier_panel')]
        ]
        
        await query.edit_message_text(upload_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in upload cards handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في رفع الكروت.")

async def manual_card_input_handler(update: Update, context: CallbackContext):
    """Handle manual card input for suppliers"""
    try:
        query = update.callback_query
        user = get_user(query.from_user.id)
        
        if not user or user['role'] != 'supplier':
            await query.edit_message_text("❌ هذه الميزة متاحة للمزودين فقط.")
            return
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get supplier's active and approved networks
        cursor.execute('''
            SELECT id, name, provider, city
            FROM networks 
            WHERE supplier_id = ? AND is_active = 1 AND is_approved = 1
            ORDER BY name
        ''', (user['id'],))
        
        networks = cursor.fetchall()
        conn.close()
        
        if not networks:
            no_networks_text = """
✏️ **إدخال يدوي للكروت** ✏️

❌ **لا توجد شبكات متاحة لك**

💡 **يجب إنشاء شبكة أولاً:**
• اذهب لإدارة الشبكات
• أنشئ شبكة جديدة
• انتظر اعتماد المشرف
"""
            keyboard = [
                [InlineKeyboardButton('🌐 إدارة الشبكات', callback_data='manage_networks')],
                [InlineKeyboardButton('🔙 عودة لرفع الكروت', callback_data='upload_cards')]
            ]
        else:
            networks_text = f"""
✏️ **إدخال يدوي للكروت** ✏️

👤 **{user['full_name']}**
🌐 **الشبكات المتاحة:** {len(networks)} شبكة

💡 **اختر الشبكة لإضافة الكروت:**
"""
            
            keyboard = []
            for network in networks:
                net_id, name, provider, city = network
                keyboard.append([
                    InlineKeyboardButton(f'🌐 {name} - {provider}', 
                                       callback_data=f'manual_network_{net_id}')
                ])
            
            keyboard.extend([
                [InlineKeyboardButton('🔙 عودة لرفع الكروت', callback_data='upload_cards')]
            ])
        
        await query.edit_message_text(networks_text if networks else no_networks_text, 
                                     reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in manual card input handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في إعداد الإدخال اليدوي.")

async def manual_network_selection_handler(update: Update, context: CallbackContext, network_id: str):
    """Handle network selection for manual card input"""
    try:
        query = update.callback_query
        user = get_user(query.from_user.id)
        
        if not user or user['role'] != 'supplier':
            await query.edit_message_text("❌ هذه الميزة متاحة للمزودين فقط.")
            return
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT name, provider, city, description
            FROM networks 
            WHERE id = ? AND supplier_id = ? AND is_active = 1 AND is_approved = 1
        ''', (network_id, user['id']))
        network = cursor.fetchone()
        conn.close()
        
        if not network:
            await query.edit_message_text("❌ شبكة غير صحيحة أو غير مفعلة.")
            return
        
        # Clear any previous search states to avoid conflicts
        if 'customer_searching_network' in context.user_data:
            del context.user_data['customer_searching_network']
        if 'searching_network' in context.user_data:
            del context.user_data['searching_network']
        
        # Store network ID
        context.user_data['manual_network_id'] = network_id
        
        text = f"""
✏️ **إضافة كروت جديدة** ✏️

🌐 **الشبكة:** {network[0]}
👤 **المزود:** {network[1]}
🏙️ **المدينة:** {network[2] or 'غير محدد'}

💰 **اختر سعر الكرت:**
"""
        
        # Price buttons
        keyboard = [
            [InlineKeyboardButton('💳 100 ريال', callback_data=f'price_100_{network_id}'),
             InlineKeyboardButton('💳 200 ريال', callback_data=f'price_200_{network_id}')],
            [InlineKeyboardButton('💳 300 ريال', callback_data=f'price_300_{network_id}'),
             InlineKeyboardButton('💳 500 ريال', callback_data=f'price_500_{network_id}')],
            [InlineKeyboardButton('💳 1000 ريال', callback_data=f'price_1000_{network_id}'),
             InlineKeyboardButton('💳 2000 ريال', callback_data=f'price_2000_{network_id}')],
            [InlineKeyboardButton('✏️ سعر مخصص', callback_data=f'custom_price_{network_id}')],
            [InlineKeyboardButton('🔙 عودة', callback_data='manual_card_input')],
            [InlineKeyboardButton('🏪 لوحة المزود', callback_data='supplier_panel')]
        ]
        
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in manual network selection handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في اختيار الشبكة.")

async def price_selection_handler(update: Update, context: CallbackContext, price: str, network_id: str):
    """Handle price selection for card upload"""
    try:
        query = update.callback_query
        user = get_user(query.from_user.id)
        
        if not user or user['role'] != 'supplier':
            await query.edit_message_text("❌ هذه الميزة متاحة للمزودين فقط.")
            return
        
        # Store price and network
        context.user_data['selected_price'] = int(price)
        context.user_data['manual_network_id'] = network_id
        context.user_data['awaiting_card_size'] = True
        
        # Get network info
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT name FROM networks WHERE id = ?', (network_id,))
        network_name = cursor.fetchone()[0]
        conn.close()
        
        text = f"""
✏️ **إضافة كروت جديدة** ✏️

🌐 **الشبكة:** {network_name}
💰 **السعر المختار:** {price} ريال

📏 **أدخل حجم الكرت:**
• مثال: `1 جيجا` → 1000 ميجابايت
• مثال: `500 ميجابايت` → 500 ميجابايت
• مثال: `2 جيجا` → 2000 ميجابايت

💡 **اكتب الحجم الآن:**
"""
        
        keyboard = [
            [InlineKeyboardButton('🔙 عودة لاختيار السعر', callback_data=f'manual_network_{network_id}')],
            [InlineKeyboardButton('🏪 لوحة المزود', callback_data='supplier_panel')]
        ]
        
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in price selection handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في اختيار السعر.")

async def custom_price_handler(update: Update, context: CallbackContext, network_id: str):
    """Handle custom price input for card upload"""
    try:
        query = update.callback_query
        user = get_user(query.from_user.id)
        
        if not user or user['role'] != 'supplier':
            await query.edit_message_text("❌ هذه الميزة متاحة للمزودين فقط.")
            return
        
        # Store network ID and set custom price state
        context.user_data['manual_network_id'] = network_id
        context.user_data['awaiting_custom_price'] = True
        
        text = f"""
✏️ **إضافة كروت جديدة** ✏️

🌐 **الشبكة:** {network_id}

💰 **أدخل السعر المخصص:**
• اكتب السعر بالريال (مثال: 750)
• يجب أن يكون رقماً صحيحاً
• الحد الأدنى: 50 ريال

💡 **اكتب السعر الآن:**
"""
        
        keyboard = [
            [InlineKeyboardButton('🔙 عودة لاختيار السعر', callback_data=f'manual_network_{network_id}')],
            [InlineKeyboardButton('🏪 لوحة المزود', callback_data='supplier_panel')]
        ]
        
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in custom price handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في إعداد السعر المخصص.")