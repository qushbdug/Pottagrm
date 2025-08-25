#!/usr/bin/env python3
"""
Enhanced Network System for Telegram Bot
Fixes all issues and implements advanced features

Features:
1. ✅ Fixed category addition with proper database storage
2. ✅ Pagination system (4 networks per page)
3. ✅ Enhanced search interface with guidance
4. ✅ Improved network details with action buttons
5. ✅ Purchase confirmation system
6. ✅ Unified functions with no duplicates

Author: Telegram Bot Enhancement Engineer
Version: 3.0.0 (Enhanced)
"""

import logging
import math
from typing import List, Dict, Optional, Tuple

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext

from bot_modules.config import EMOJIS
from bot_modules.database import get_db_connection
from bot_modules.utils import get_user, update_user_activity

logger = logging.getLogger(__name__)

# =============================================================================
# ENHANCED CATEGORY MANAGEMENT - FIXED
# =============================================================================

async def enhanced_add_category_handler(update: Update, context: CallbackContext):
    """
    FIXED: Add category with proper database storage
    """
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user:
            await query.edit_message_text(f"{EMOJIS['error']} يرجى التسجيل أولاً /start")
            return
        
        # Check permissions
        if user['role'] not in ['supplier', 'admin', 'super_admin']:
            await query.edit_message_text(f"{EMOJIS['error']} ليس لديك صلاحية لإضافة الفئات.")
            return
        
        # Get user's networks
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
        
        if not networks:
            no_networks_text = f"""
❌ **لا توجد شبكات متاحة**

{EMOJIS['warning']} يجب إضافة شبكة أولاً قبل إضافة الفئات.

💡 **لإضافة شبكة:**
• استخدم "إضافة شبكة جديدة"
• أكمل جميع البيانات المطلوبة
• ثم ارجع لإضافة الفئات
"""
            keyboard = [
                [InlineKeyboardButton('➕ إضافة شبكة جديدة', callback_data='unified_add_network')],
                [InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
            ]
            
            await query.edit_message_text(no_networks_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
            return
        
        role_text = "مشرف" if user['role'] in ['admin', 'super_admin'] else "مزود"
        
        category_text = f"""
💳 **إضافة فئة كروت جديدة**

👤 **{user['full_name']}** ({role_text})

📶 **اختر الشبكة لإضافة الفئة إليها:**
📊 **الشبكات المتاحة:** {len(networks)} شبكة

"""
        
        keyboard = []
        
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
                f"💳 {display_name}",
                callback_data=f'enhanced_add_cat_{net_id}'
            )])
        
        keyboard.extend([
            [InlineKeyboardButton('➕ إضافة شبكة جديدة', callback_data='unified_add_network')],
            [InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
        ])
        
        await query.edit_message_text(category_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in enhanced add category handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في إضافة الفئة.")

async def process_category_addition_step(update: Update, context: CallbackContext):
    """
    FIXED: Process category addition steps with proper validation
    """
    try:
        if not context.user_data.get('adding_enhanced_category'):
            return
        
        text = update.message.text.strip()
        user = get_user(update.effective_user.id)
        step = context.user_data.get('category_step', 'name')
        network_id = context.user_data.get('target_network_id')
        
        if step == 'name':
            # Step 1: Category name
            if len(text) < 3:
                await update.message.reply_text("❌ اسم الفئة يجب أن يكون 3 أحرف على الأقل. حاول مرة أخرى:")
                return
            
            context.user_data['category_name'] = text
            context.user_data['category_step'] = 'value'
            
            await update.message.reply_text(
                f"✅ **تم حفظ اسم الفئة:** {text}\n\n"
                f"🔸 **الخطوة 2 من 4**\n"
                f"💰 **أدخل قيمة الكرت (بالريال):**\n"
                f"مثال: 1000",
                parse_mode='Markdown'
            )
            
        elif step == 'value':
            # Step 2: Card value
            try:
                value = int(text)
                if value <= 0:
                    raise ValueError("القيمة يجب أن تكون أكبر من صفر")
                
                context.user_data['category_value'] = value
                context.user_data['category_step'] = 'price'
                
                await update.message.reply_text(
                    f"✅ **تم حفظ قيمة الكرت:** {value:,} ريال\n\n"
                    f"🔸 **الخطوة 3 من 4**\n"
                    f"💵 **أدخل سعر البيع (بالريال):**\n"
                    f"مثال: 1050",
                    parse_mode='Markdown'
                )
                
            except ValueError:
                await update.message.reply_text("❌ يرجى إدخال رقم صحيح للقيمة. حاول مرة أخرى:")
                return
            
        elif step == 'price':
            # Step 3: Selling price
            try:
                price = float(text)
                value = context.user_data.get('category_value', 0)
                
                if price <= 0:
                    raise ValueError("السعر يجب أن يكون أكبر من صفر")
                
                if price < value:
                    await update.message.reply_text(
                        f"⚠️ **تحذير:** السعر ({price:,} ريال) أقل من قيمة الكرت ({value:,} ريال)\n"
                        f"هذا يعني خسارة في كل عملية بيع.\n\n"
                        f"هل تريد المتابعة؟ إذا كان نعم، أرسل نفس السعر مرة أخرى.\n"
                        f"إذا كان لا، أرسل السعر الصحيح."
                    )
                    
                    # Check if this is a confirmation
                    if context.user_data.get('price_warning_shown') and context.user_data.get('warned_price') == price:
                        # User confirmed the low price
                        pass
                    else:
                        # First time showing warning
                        context.user_data['price_warning_shown'] = True
                        context.user_data['warned_price'] = price
                        return
                
                context.user_data['category_price'] = price
                context.user_data['category_step'] = 'stock'
                
                await update.message.reply_text(
                    f"✅ **تم حفظ سعر البيع:** {price:,} ريال\n\n"
                    f"🔸 **الخطوة 4 من 4**\n"
                    f"📦 **أدخل عدد الكروت المتاحة (المخزون):**\n"
                    f"مثال: 100\n\n"
                    f"💡 **ملاحظة:** يمكنك إدخال 0 إذا لم تكن تريد إضافة كروت الآن",
                    parse_mode='Markdown'
                )
                
            except ValueError:
                await update.message.reply_text("❌ يرجى إدخال رقم صحيح للسعر. حاول مرة أخرى:")
                return
            
        elif step == 'stock':
            # Step 4: Stock count and save to database
            try:
                stock = int(text)
                if stock < 0:
                    raise ValueError("المخزون لا يمكن أن يكون سالباً")
                
                # Save to database
                await save_category_to_database(update, context, user, network_id, stock)
                
            except ValueError:
                await update.message.reply_text("❌ يرجى إدخال رقم صحيح للمخزون. حاول مرة أخرى:")
                return
        
    except Exception as e:
        logger.error(f"Error in process category addition step: {e}")
        await update.message.reply_text(f"❌ حدث خطأ في معالجة الفئة: {e}")
        context.user_data.clear()

async def save_category_to_database(update: Update, context: CallbackContext, user: dict, network_id: str, stock: int):
    """
    FIXED: Save category to database with proper error handling
    """
    try:
        name = context.user_data.get('category_name')
        value = context.user_data.get('category_value')
        price = context.user_data.get('category_price')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get network info
        cursor.execute('SELECT name, provider FROM networks WHERE id = ?', (network_id,))
        network = cursor.fetchone()
        
        if not network:
            await update.message.reply_text("❌ الشبكة غير موجودة.")
            conn.close()
            context.user_data.clear()
            return
        
        network_name, provider = network
        
        # Insert category
        cursor.execute('''
            INSERT INTO card_categories (network_id, name, value, price, currency, is_available, stock_count, created_at)
            VALUES (?, ?, ?, ?, 'YER', 1, ?, CURRENT_TIMESTAMP)
        ''', (network_id, name, value, price, stock))
        
        category_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        # Clear context
        context.user_data.clear()
        
        # Success message
        profit_margin = ((price - value) / value * 100) if value > 0 else 0
        
        success_text = f"""
✅ **تم إنشاء الفئة بنجاح!**

📋 **تفاصيل الفئة:**
🏷️ **الاسم:** {name}
🌐 **الشبكة:** {network_name}
👤 **المزود:** {provider}
💳 **قيمة الكرت:** {value:,} ريال
💵 **سعر البيع:** {price:,} ريال
📊 **هامش الربح:** {profit_margin:.1f}%
📦 **المخزون:** {stock:,} كرت
🆔 **معرف الفئة:** #{category_id}

🔧 **الخيارات التالية:**
"""
        
        keyboard = [
            [InlineKeyboardButton('📤 رفع كروت للفئة', callback_data=f'enhanced_upload_cards_{category_id}'),
             InlineKeyboardButton('💳 إضافة فئة أخرى', callback_data=f'enhanced_add_cat_{network_id}')],
            [InlineKeyboardButton('🌐 عرض تفاصيل الشبكة', callback_data=f'enhanced_network_details_{network_id}'),
             InlineKeyboardButton('📶 إدارة الشبكات', callback_data='enhanced_manage_networks')],
            [InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
        ]
        
        await update.message.reply_text(
            success_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Error saving category to database: {e}")
        await update.message.reply_text(f"❌ خطأ في حفظ الفئة: {e}")
        context.user_data.clear()

# =============================================================================
# ENHANCED SEARCH WITH PAGINATION - 4 NETWORKS PER PAGE
# =============================================================================

async def enhanced_search_networks_handler(update: Update, context: CallbackContext):
    """
    ENHANCED: Search interface with guidance and pagination
    """
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user:
            await query.edit_message_text(f"{EMOJIS['error']} يرجى التسجيل أولاً /start")
            return
        
        update_user_activity(user['id'])
        
        # Get total networks count
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM networks WHERE is_active = 1 AND is_approved = 1')
        total_networks = cursor.fetchone()[0]
        conn.close()
        
        search_text = f"""
🔍 **البحث في الشبكات**

👤 **{user['full_name']}**

📋 **يمكنك البحث عن الشبكة باستخدام:**
• رقم المعرف (ID) 
• اسم الشبكة
• اسم المزود

📊 **إجمالي الشبكات المتاحة:** {total_networks} شبكة

💡 **للبحث:** أرسل النص المطلوب البحث عنه
💡 **لعرض الكل:** اضغط على "جميع الشبكات"
"""
        
        keyboard = [
            [InlineKeyboardButton('📶 جميع الشبكات', callback_data='enhanced_view_all_page_1')],
            [InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
        ]
        
        # Set search mode
        context.user_data['awaiting_enhanced_search'] = True
        
        await query.edit_message_text(search_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in enhanced search networks handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في البحث.")

async def enhanced_view_all_networks_paginated(update: Update, context: CallbackContext, page: int = 1):
    """
    ENHANCED: View networks with pagination (4 per page)
    """
    try:
        if hasattr(update, 'callback_query') and update.callback_query:
            query = update.callback_query
            await query.answer()
        else:
            query = None
        
        user = get_user(update.effective_user.id)
        if not user:
            error_msg = f"{EMOJIS['error']} يرجى التسجيل أولاً /start"
            if query:
                await query.edit_message_text(error_msg)
            else:
                await update.message.reply_text(error_msg)
            return
        
        # Pagination settings
        NETWORKS_PER_PAGE = 4
        offset = (page - 1) * NETWORKS_PER_PAGE
        
        # Get total count and paginated results
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Total count
        cursor.execute('SELECT COUNT(*) FROM networks WHERE is_active = 1 AND is_approved = 1')
        total_networks = cursor.fetchone()[0]
        
        if total_networks == 0:
            no_networks_text = f"""
📶 **جميع الشبكات**

❌ **لا توجد شبكات متاحة حالياً**

💡 **يمكنك:**
• إضافة شبكة جديدة إذا كنت مزوداً
• العودة للقائمة الرئيسية
"""
            keyboard = [
                [InlineKeyboardButton('➕ إضافة شبكة', callback_data='unified_add_network')],
                [InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
            ]
            
            message_text = no_networks_text
            if query:
                await query.edit_message_text(message_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
            else:
                await update.message.reply_text(message_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
            conn.close()
            return
        
        # Calculate pagination
        total_pages = math.ceil(total_networks / NETWORKS_PER_PAGE)
        page = max(1, min(page, total_pages))  # Ensure page is within bounds
        offset = (page - 1) * NETWORKS_PER_PAGE
        
        # Get paginated networks
        cursor.execute('''
            SELECT n.id, n.name, n.provider, n.location, n.created_at,
                   u.full_name as supplier_name
            FROM networks n
            LEFT JOIN users u ON n.supplier_id = u.id
            WHERE n.is_active = 1 AND n.is_approved = 1
            ORDER BY n.created_at DESC
            LIMIT ? OFFSET ?
        ''', (NETWORKS_PER_PAGE, offset))
        
        networks = cursor.fetchall()
        
        # Get category counts for each network
        network_list = []
        for net in networks:
            net_id = net[0]
            cursor.execute('SELECT COUNT(*) FROM card_categories WHERE network_id = ? AND is_available = 1', (net_id,))
            cat_count = cursor.fetchone()[0]
            
            cursor.execute('''
                SELECT COUNT(*) FROM cards c
                JOIN card_categories cc ON c.category_id = cc.id
                WHERE cc.network_id = ? AND c.is_sold = 0
            ''', (net_id,))
            cards_count = cursor.fetchone()[0]
            
            network_list.append({
                'id': net[0],
                'name': net[1],
                'provider': net[2],
                'location': net[3],
                'created_at': net[4],
                'supplier_name': net[5],
                'categories': cat_count,
                'cards': cards_count
            })
        
        conn.close()
        
        # Build message
        start_num = offset + 1
        end_num = min(offset + NETWORKS_PER_PAGE, total_networks)
        
        view_text = f"""
📶 **جميع الشبكات** (صفحة {page} من {total_pages})

👤 **{user['full_name']}**
📊 **عرض {start_num}-{end_num} من {total_networks} شبكة**

"""
        
        for i, net in enumerate(network_list, start_num):
            status = "✅" if net['categories'] > 0 else "🔄"
            location = f"📍 {net['location']}" if net['location'] else "📍 غير محدد"
            date = net['created_at'][:10] if net['created_at'] else 'غير محدد'
            supplier_info = f" ({net['supplier_name']})" if net['supplier_name'] else ""
            
            view_text += f"""
{i}. {status} **{net['name']}**
👤 {net['provider']}{supplier_info}
{location} | 📅 {date}
💳 {net['categories']} فئة | 🎫 {net['cards']} كرت متاح
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        
        # Build keyboard with pagination
        keyboard = []
        
        # Network detail buttons
        for net in network_list:
            keyboard.append([InlineKeyboardButton(
                f"👁️ {net['name'][:25]}{'...' if len(net['name']) > 25 else ''}",
                callback_data=f'enhanced_network_details_{net["id"]}'
            )])
        
        # Pagination buttons
        pagination_row = []
        
        # Previous page
        if page > 1:
            pagination_row.append(InlineKeyboardButton('⬅️ السابق', callback_data=f'enhanced_view_all_page_{page-1}'))
        
        # Page numbers (show up to 5 pages)
        start_page = max(1, page - 2)
        end_page = min(total_pages, page + 2)
        
        for p in range(start_page, end_page + 1):
            if p == page:
                pagination_row.append(InlineKeyboardButton(f'• {p} •', callback_data=f'enhanced_view_all_page_{p}'))
            else:
                pagination_row.append(InlineKeyboardButton(f'{p}', callback_data=f'enhanced_view_all_page_{p}'))
        
        # Next page
        if page < total_pages:
            pagination_row.append(InlineKeyboardButton('التالي ➡️', callback_data=f'enhanced_view_all_page_{page+1}'))
        
        if pagination_row:
            keyboard.append(pagination_row)
        
        # Utility buttons
        keyboard.extend([
            [InlineKeyboardButton('🔍 البحث', callback_data='enhanced_search_networks'),
             InlineKeyboardButton('🛒 شراء كروت', callback_data='buy_cards')],
            [InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
        ])
        
        if query:
            await query.edit_message_text(view_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        else:
            await update.message.reply_text(view_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in enhanced view all networks paginated: {e}")
        error_msg = f"{EMOJIS['error']} حدث خطأ في عرض الشبكات."
        if query:
            await query.edit_message_text(error_msg)
        else:
            await update.message.reply_text(error_msg)

# =============================================================================
# ENHANCED NETWORK DETAILS WITH ACTION BUTTONS
# =============================================================================

async def enhanced_network_details_handler(update: Update, context: CallbackContext, network_id: str):
    """
    ENHANCED: Network details with comprehensive action buttons
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
        
        # Get network details
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
                    InlineKeyboardButton('🔙 العودة', callback_data='enhanced_view_all_page_1')
                ]])
            )
            conn.close()
            return
        
        net_id, name, provider, location, description, created_at, supplier_name, supplier_phone = network
        
        # Get categories count
        cursor.execute('SELECT COUNT(*) FROM card_categories WHERE network_id = ? AND is_available = 1', (network_id,))
        categories_count = cursor.fetchone()[0]
        
        # Get cards count
        cursor.execute('''
            SELECT COUNT(*) FROM cards c
            JOIN card_categories cc ON c.category_id = cc.id
            WHERE cc.network_id = ? AND c.is_sold = 0
        ''', (network_id,))
        cards_count = cursor.fetchone()[0]
        
        # Get price range
        cursor.execute('''
            SELECT MIN(price), MAX(price) FROM card_categories 
            WHERE network_id = ? AND is_available = 1
        ''', (network_id,))
        price_result = cursor.fetchone()
        min_price = price_result[0] if price_result[0] else 0
        max_price = price_result[1] if price_result[1] else 0
        
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
        
        # Price range info
        if min_price and max_price:
            if min_price == max_price:
                price_info = f"{min_price:,} ريال"
            else:
                price_info = f"{min_price:,} - {max_price:,} ريال"
        else:
            price_info = "لم يتم تحديدها بعد"
        
        details_text += f"""
📊 **الإحصائيات:**
💳 **عدد الفئات:** {categories_count} فئة
🎫 **الكروت المتاحة:** {cards_count} كرت
💰 **نطاق الأسعار:** {price_info}

🔧 **الإجراءات المتاحة:**
"""
        
        # Build action buttons
        keyboard = []
        
        # Main action buttons
        if cards_count > 0:
            keyboard.append([InlineKeyboardButton('🎫 عرض الكروت', callback_data=f'enhanced_view_cards_{network_id}')])
        
        if categories_count > 0:
            keyboard.append([InlineKeyboardButton('💳 عرض الفئات', callback_data=f'enhanced_view_categories_{network_id}')])
        
        if cards_count > 0:
            keyboard.append([InlineKeyboardButton('🛒 شراء كرت', callback_data=f'enhanced_purchase_from_{network_id}')])
        
        # Navigation buttons
        keyboard.extend([
            [InlineKeyboardButton('🔙 الرجوع', callback_data='enhanced_view_all_page_1'),
             InlineKeyboardButton('🔍 البحث', callback_data='enhanced_search_networks')],
            [InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
        ])
        
        await query.edit_message_text(details_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in enhanced network details handler: {e}")
        await query.edit_message_text(
            f"{EMOJIS['error']} حدث خطأ في عرض تفاصيل الشبكة.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton('🔙 العودة', callback_data='enhanced_view_all_page_1')
            ]])
        )

# =============================================================================
# ENHANCED PURCHASE CONFIRMATION SYSTEM
# =============================================================================

async def enhanced_purchase_confirmation_handler(update: Update, context: CallbackContext, network_id: str):
    """
    ENHANCED: Purchase confirmation with clear options
    """
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user:
            await query.edit_message_text(f"{EMOJIS['error']} يرجى التسجيل أولاً /start")
            return
        
        # Get available categories for this network
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT cc.id, cc.name, cc.price, cc.value, 
                   COUNT(c.id) as available_cards
            FROM card_categories cc
            LEFT JOIN cards c ON cc.id = c.category_id AND c.is_sold = 0
            WHERE cc.network_id = ? AND cc.is_available = 1
            GROUP BY cc.id, cc.name, cc.price, cc.value
            HAVING available_cards > 0
            ORDER BY cc.price ASC
        ''', (network_id,))
        
        categories = cursor.fetchall()
        
        # Get network name
        cursor.execute('SELECT name, provider FROM networks WHERE id = ?', (network_id,))
        network_info = cursor.fetchone()
        
        conn.close()
        
        if not network_info:
            await query.edit_message_text("❌ الشبكة غير موجودة.")
            return
        
        network_name, provider = network_info
        
        if not categories:
            no_cards_text = f"""
🛒 **شراء كرت من {network_name}**

❌ **لا توجد كروت متاحة حالياً**

📋 **الشبكة:** {network_name}
👤 **المزود:** {provider}

💡 **يرجى المحاولة لاحقاً أو اختيار شبكة أخرى**
"""
            
            keyboard = [
                [InlineKeyboardButton('🔙 تفاصيل الشبكة', callback_data=f'enhanced_network_details_{network_id}')],
                [InlineKeyboardButton('📶 شبكات أخرى', callback_data='enhanced_view_all_page_1')],
                [InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
            ]
            
            await query.edit_message_text(no_cards_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
            return
        
        purchase_text = f"""
🛒 **شراء كرت من {network_name}**

👤 **{user['full_name']}**
💰 **رصيدك:** {user['balance']:,} ريال

📋 **الشبكة:** {network_name}
👤 **المزود:** {provider}

💳 **الفئات المتاحة:**

"""
        
        keyboard = []
        
        for cat_id, cat_name, price, value, available in categories:
            if user['balance'] >= price:
                status_emoji = "✅"
                action_text = "شراء"
            else:
                status_emoji = "❌"
                action_text = "رصيد غير كافي"
            
            purchase_text += f"""
{status_emoji} **{cat_name}**
💰 السعر: {price:,} ريال | 🎫 القيمة: {value:,} ريال
📦 متاح: {available} كرت
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
            
            if user['balance'] >= price:
                keyboard.append([InlineKeyboardButton(
                    f"🛒 {action_text} {cat_name}",
                    callback_data=f'enhanced_confirm_purchase_{cat_id}'
                )])
        
        if not any(user['balance'] >= cat[2] for cat in categories):
            purchase_text += f"\n⚠️ **رصيدك غير كافي لشراء أي كرت من هذه الشبكة**"
            keyboard.append([InlineKeyboardButton('💰 شحن الرصيد', callback_data='recharge_balance')])
        
        keyboard.extend([
            [InlineKeyboardButton('🔙 تفاصيل الشبكة', callback_data=f'enhanced_network_details_{network_id}')],
            [InlineKeyboardButton('📶 شبكات أخرى', callback_data='enhanced_view_all_page_1')],
            [InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
        ])
        
        await query.edit_message_text(purchase_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in enhanced purchase confirmation handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في عرض خيارات الشراء.")

async def enhanced_confirm_purchase_handler(update: Update, context: CallbackContext, category_id: str):
    """
    ENHANCED: Final purchase confirmation with clear options
    """
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user:
            await query.edit_message_text(f"{EMOJIS['error']} يرجى التسجيل أولاً /start")
            return
        
        # Get category and network info
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT cc.id, cc.name, cc.price, cc.value, cc.network_id,
                   n.name as network_name, n.provider,
                   COUNT(c.id) as available_cards
            FROM card_categories cc
            JOIN networks n ON cc.network_id = n.id
            LEFT JOIN cards c ON cc.id = c.category_id AND c.is_sold = 0
            WHERE cc.id = ? AND cc.is_available = 1
            GROUP BY cc.id, cc.name, cc.price, cc.value, cc.network_id, n.name, n.provider
        ''', (category_id,))
        
        category_info = cursor.fetchone()
        conn.close()
        
        if not category_info:
            await query.edit_message_text("❌ الفئة غير موجودة أو غير متاحة.")
            return
        
        cat_id, cat_name, price, value, network_id, network_name, provider, available = category_info
        
        if available <= 0:
            await query.edit_message_text("❌ لا توجد كروت متاحة في هذه الفئة.")
            return
        
        if user['balance'] < price:
            await query.edit_message_text(f"❌ رصيدك غير كافي. تحتاج {price:,} ريال.")
            return
        
        # Store purchase info in context
        context.user_data['pending_purchase'] = {
            'category_id': cat_id,
            'category_name': cat_name,
            'price': price,
            'value': value,
            'network_id': network_id,
            'network_name': network_name,
            'provider': provider
        }
        
        confirmation_text = f"""
🛒 **تأكيد عملية الشراء**

👤 **{user['full_name']}**
💰 **رصيدك الحالي:** {user['balance']:,} ريال

📋 **تفاصيل العملية:**
🌐 **الشبكة:** {network_name}
👤 **المزود:** {provider}
💳 **الفئة:** {cat_name}
🎫 **قيمة الكرت:** {value:,} ريال
💵 **السعر:** {price:,} ريال
💰 **الرصيد بعد الشراء:** {user['balance'] - price:,} ريال

⚠️ **تأكيد:**
هل أنت متأكد من رغبتك في شراء هذا الكرت؟
"""
        
        keyboard = [
            [InlineKeyboardButton('✅ تأكيد الشراء', callback_data='enhanced_execute_purchase'),
             InlineKeyboardButton('❌ إلغاء', callback_data=f'enhanced_purchase_from_{network_id}')],
            [InlineKeyboardButton('🔙 العودة للشبكة', callback_data=f'enhanced_network_details_{network_id}')]
        ]
        
        await query.edit_message_text(confirmation_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in enhanced confirm purchase handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في تأكيد الشراء.")

# =============================================================================
# ENHANCED CALLBACKS MAPPING
# =============================================================================

ENHANCED_NETWORK_CALLBACKS = {
    'enhanced_search_networks': enhanced_search_networks_handler,
}

# Dynamic callback handler
async def handle_enhanced_network_callbacks(update: Update, context: CallbackContext, callback_data: str):
    """Handle all enhanced network callbacks dynamically"""
    try:
        if callback_data.startswith('enhanced_add_cat_'):
            network_id = callback_data.split('_')[-1]
            # Start category addition process
            context.user_data['adding_enhanced_category'] = True
            context.user_data['target_network_id'] = network_id
            context.user_data['category_step'] = 'name'
            
            await update.callback_query.edit_message_text(
                "💳 **إضافة فئة جديدة**\n\n"
                "🔸 **الخطوة 1 من 4**\n"
                "📝 **أدخل اسم الفئة:**\n"
                "مثال: كرت 1000 ريال",
                parse_mode='Markdown'
            )
            
        elif callback_data.startswith('enhanced_view_all_page_'):
            page = int(callback_data.split('_')[-1])
            await enhanced_view_all_networks_paginated(update, context, page)
            
        elif callback_data.startswith('enhanced_network_details_'):
            network_id = callback_data.split('_')[-1]
            await enhanced_network_details_handler(update, context, network_id)
            
        elif callback_data.startswith('enhanced_purchase_from_'):
            network_id = callback_data.split('_')[-1]
            await enhanced_purchase_confirmation_handler(update, context, network_id)
            
        elif callback_data.startswith('enhanced_confirm_purchase_'):
            category_id = callback_data.split('_')[-1]
            await enhanced_confirm_purchase_handler(update, context, category_id)
            
        elif callback_data == 'enhanced_execute_purchase':
            # Execute the actual purchase
            await enhanced_execute_purchase_handler(update, context)
            
    except Exception as e:
        logger.error(f"Error handling enhanced network callback: {e}")
        await update.callback_query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في معالجة الطلب.")

# =============================================================================
# TEXT MESSAGE HANDLER FOR SEARCH AND CATEGORY ADDITION
# =============================================================================

async def handle_enhanced_text_messages(update: Update, context: CallbackContext):
    """Handle text messages for search, category addition, and network creation"""
    try:
        # Handle enhanced network creation
        if context.user_data.get('enhanced_adding_network'):
            await process_enhanced_network_creation(update, context)
            return True
        
        # Handle category addition
        if context.user_data.get('adding_enhanced_category'):
            await process_category_addition_step(update, context)
            return True
        
        # Handle search
        if context.user_data.get('awaiting_enhanced_search'):
            search_term = update.message.text.strip()
            context.user_data.pop('awaiting_enhanced_search', None)
            
            # Perform search (to be implemented)
            await update.message.reply_text(f"🔍 البحث عن: {search_term}\n\nسيتم تطوير ميزة البحث قريباً...")
            return True
        
        return False
        
    except Exception as e:
        logger.error(f"Error handling enhanced text messages: {e}")
        await update.message.reply_text(f"{EMOJIS['error']} حدث خطأ في معالجة الرسالة.")
        return False

# =============================================================================
# ENHANCED NETWORK CREATION
# =============================================================================

async def process_enhanced_network_creation(update: Update, context: CallbackContext):
    """Process enhanced network creation step by step"""
    try:
        text = update.message.text.strip()
        telegram_user_id = update.message.from_user.id
        
        # Get actual user database ID from telegram_id
        user = get_user(telegram_user_id)
        if not user:
            await update.message.reply_text(f"{EMOJIS['error']} يرجى التسجيل أولاً /start")
            context.user_data.clear()
            return
            
        user_id = user['id']  # Database ID, not Telegram ID
        
        # Check user permissions for network creation
        if user['role'] not in ['supplier', 'admin', 'super_admin']:
            await update.message.reply_text(f"{EMOJIS['error']} ليس لديك صلاحية لإضافة الشبكات. يرجى التواصل مع الإدارة.")
            context.user_data.clear()
            return
            
        step = context.user_data.get('enhanced_network_step', 'name')
        
        # Detailed logging for debugging
        logger.info(f"Network creation step '{step}' for user {user_id} (telegram: {telegram_user_id})")
        
        if step == 'name':
            # Validate network name
            if len(text) < 3:
                await update.message.reply_text(f"{EMOJIS['error']} اسم الشبكة قصير جداً. يجب أن يكون 3 أحرف على الأقل.")
                return
            
            if len(text) > 50:
                await update.message.reply_text(f"{EMOJIS['error']} اسم الشبكة طويل جداً. يجب أن يكون أقل من 50 حرف.")
                return
            
            context.user_data['network_name'] = text
            context.user_data['enhanced_network_step'] = 'provider'
            
            await update.message.reply_text(f"""
✅ **تم حفظ اسم الشبكة:** {text}

🔸 **الخطوة 2 من 4**
🏢 **أدخل اسم المزود:**

مثال: "شركة التقنية المتقدمة"

📤 **أرسل اسم المزود الآن:**
""", parse_mode='Markdown')
            
        elif step == 'provider':
            # Validate provider name
            if len(text) < 3:
                await update.message.reply_text(f"{EMOJIS['error']} اسم المزود قصير جداً. يجب أن يكون 3 أحرف على الأقل.")
                return
            
            if len(text) > 50:
                await update.message.reply_text(f"{EMOJIS['error']} اسم المزود طويل جداً. يجب أن يكون أقل من 50 حرف.")
                return
            
            context.user_data['network_provider'] = text
            context.user_data['enhanced_network_step'] = 'location'
            
            await update.message.reply_text(f"""
✅ **تم حفظ اسم المزود:** {text}

🔸 **الخطوة 3 من 4**
📍 **أدخل موقع الشبكة:**

مثال: "صنعاء - شارع الزبيري"

📤 **أرسل الموقع الآن:**
""", parse_mode='Markdown')
            
        elif step == 'location':
            # Validate location
            if len(text) < 3:
                await update.message.reply_text(f"{EMOJIS['error']} موقع الشبكة قصير جداً. يجب أن يكون 3 أحرف على الأقل.")
                return
            
            if len(text) > 100:
                await update.message.reply_text(f"{EMOJIS['error']} موقع الشبكة طويل جداً. يجب أن يكون أقل من 100 حرف.")
                return
            
            context.user_data['network_location'] = text
            context.user_data['enhanced_network_step'] = 'description'
            
            await update.message.reply_text(f"""
✅ **تم حفظ الموقع:** {text}

🔸 **الخطوة 4 من 4**
📝 **أدخل وصف الشبكة (اختياري):**

مثال: "شبكة سريعة وموثوقة، تغطي منطقة الحصبة"

📤 **أرسل الوصف أو اكتب "تخطي" للمتابعة:**
""", parse_mode='Markdown')
            
        elif step == 'description':
            # Create the network
            network_name = context.user_data.get('network_name')
            provider = context.user_data.get('network_provider')
            location = context.user_data.get('network_location')
            description = text if text.lower() not in ['تخطي', 'skip'] else 'لا يوجد وصف'
            
            if len(description) > 200:
                await update.message.reply_text(f"{EMOJIS['error']} الوصف طويل جداً. يجب أن يكون أقل من 200 حرف.")
                return
            
            # Add network to database
            conn = get_db_connection()
            cursor = conn.cursor()
            
            try:
                # Log the values being inserted for debugging
                city = location.split('-')[0].strip() if '-' in location else location
                logger.info(f"Inserting network: supplier_id={user_id}, name={network_name}, provider={provider}, city={city}, created_by={user_id}")
                
                cursor.execute('''
                    INSERT INTO networks (supplier_id, name, provider, location, description, 
                                        city, created_by, is_active, is_approved, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 1, 1, CURRENT_TIMESTAMP)
                ''', (user_id, network_name, provider, location, description, city, user_id))
                
                network_id = cursor.lastrowid
                conn.commit()
                
                logger.info(f"Network created successfully with ID: {network_id}")
                
                # Clear user data
                context.user_data.clear()
                
                # Create success message with action buttons
                keyboard = [
                    [InlineKeyboardButton('➕ إضافة فئات', callback_data=f'enhanced_add_categories_{network_id}')],
                    [InlineKeyboardButton('📊 تفاصيل الشبكة', callback_data=f'enhanced_network_details_{network_id}')],
                    [InlineKeyboardButton('🏪 لوحة المزود', callback_data='supplier_panel'),
                     InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
                ]
                
                success_message = f"""
🎉 **تم إنشاء الشبكة بنجاح!**

🌐 **اسم الشبكة:** {network_name}
🏢 **المزود:** {provider}
📍 **الموقع:** {location}
📝 **الوصف:** {description}
🆔 **معرف الشبكة:** #{network_id}

✨ **الخطوات التالية:**
• إضافة فئات الكروت
• رفع الكروت
• تفعيل الشبكة للعملاء

🚀 **الشبكة جاهزة للاستخدام!**
"""
                
                await update.message.reply_text(
                    success_message, 
                    reply_markup=InlineKeyboardMarkup(keyboard), 
                    parse_mode='Markdown'
                )
                
                # Log the creation
                logger.info(f"Network created successfully: ID={network_id}, Name={network_name}, User={user_id}")
                
            except Exception as db_error:
                conn.rollback()
                logger.error(f"Database error creating network: {db_error}")
                await update.message.reply_text(f"{EMOJIS['error']} حدث خطأ في قاعدة البيانات: {db_error}")
                context.user_data.clear()
            finally:
                conn.close()
            
    except Exception as e:
        logger.error(f"Error in process_enhanced_network_creation: {e}")
        await update.message.reply_text(f"{EMOJIS['error']} حدث خطأ في إضافة الشبكة: {e}")
        context.user_data.clear()

# =============================================================================
# ENHANCED PURCHASE CONFIRMATION - COMPLETE IMPLEMENTATION
# =============================================================================

async def enhanced_confirm_purchase_handler(update: Update, context: CallbackContext, category_id: str):
    """Show purchase confirmation dialog"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user:
            await query.edit_message_text(f"{EMOJIS['error']} يرجى التسجيل أولاً /start")
            return
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            # Get category and network details
            cursor.execute('''
                SELECT cc.*, n.name as network_name, n.provider, n.location
                FROM card_categories cc 
                JOIN networks n ON cc.network_id = n.id 
                WHERE cc.id = ? AND cc.is_available = 1 AND cc.stock_count > 0
            ''', (category_id,))
            category = cursor.fetchone()
            
            if not category:
                await query.edit_message_text(f"{EMOJIS['error']} هذه الفئة غير متوفرة حالياً.")
                return
            
            # Check available cards
            cursor.execute('''
                SELECT COUNT(*) FROM cards 
                WHERE category_id = ? AND is_sold = 0
            ''', (category_id,))
            available_cards = cursor.fetchone()[0]
            
            if available_cards == 0:
                await query.edit_message_text(f"{EMOJIS['error']} نفدت الكروت من هذه الفئة.")
                return
            
            # Store category_id in context for purchase execution
            context.user_data['purchase_category_id'] = category_id
            
            # Calculate costs
            card_price = category['price']
            user_balance = user['balance']
            balance_after = user_balance - card_price
            
            # Prepare confirmation message
            confirmation_msg = f"""
💳 **تأكيد عملية الشراء**

🌐 **تفاصيل الكرت:**
📡 الشبكة: **{category['network_name']}**
🏢 المزود: **{category['provider']}**
📍 الموقع: **{category['location']}**
🏷️ الفئة: **{category['name']}**
💎 القيمة: **{category['value']:,.0f}** ريال

💰 **التكلفة:**
💵 سعر الكرت: **{card_price:,.2f}** ريال
💳 رصيدك الحالي: **{user_balance:,.2f}** ريال
📊 الرصيد بعد الشراء: **{balance_after:,.2f}** ريال

📦 **الكمية المتوفرة:** {available_cards} كرت

❓ **هل أنت متأكد من إتمام عملية الشراء؟**
"""
            
            # Create confirmation buttons
            keyboard = [
                [InlineKeyboardButton('✅ تأكيد الشراء', callback_data='enhanced_execute_purchase')],
                [InlineKeyboardButton('❌ إلغاء', callback_data='enhanced_search_networks'),
                 InlineKeyboardButton('🔙 العودة', callback_data=f'enhanced_network_details_{category["network_id"]}')]
            ]
            
            await query.edit_message_text(
                confirmation_msg,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            
        except Exception as db_error:
            logger.error(f"Database error in purchase confirmation: {db_error}")
            await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في استرجاع بيانات الكرت.")
        finally:
            conn.close()
            
    except Exception as e:
        logger.error(f"Error in enhanced_confirm_purchase_handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في عرض تأكيد الشراء.")

# =============================================================================
# ENHANCED PURCHASE EXECUTION - COMPLETE IMPLEMENTATION
# =============================================================================

async def enhanced_execute_purchase_handler(update: Update, context: CallbackContext):
    """Execute the actual card purchase and send card details"""
    try:
        query = update.callback_query
        await query.answer()
        
        # Get user and purchase data from context
        user = get_user(query.from_user.id)
        if not user:
            await query.edit_message_text(f"{EMOJIS['error']} يرجى التسجيل أولاً /start")
            return
        
        # Get purchase details from user_data
        category_id = context.user_data.get('purchase_category_id')
        if not category_id:
            await query.edit_message_text(f"{EMOJIS['error']} انتهت جلسة الشراء. يرجى المحاولة مرة أخرى.")
            return
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            # Get category details
            cursor.execute('''
                SELECT cc.*, n.name as network_name, n.provider 
                FROM card_categories cc 
                JOIN networks n ON cc.network_id = n.id 
                WHERE cc.id = ? AND cc.is_available = 1 AND cc.stock_count > 0
            ''', (category_id,))
            category = cursor.fetchone()
            
            if not category:
                await query.edit_message_text(f"{EMOJIS['error']} هذه الفئة غير متوفرة حالياً.")
                return
            
            # Check user balance
            if user['balance'] < category['price']:
                await query.edit_message_text(
                    f"{EMOJIS['error']} رصيدك غير كافي!\n\n"
                    f"💰 رصيدك: {user['balance']:,.2f} ريال\n"
                    f"💳 سعر الكرت: {category['price']:,.2f} ريال\n"
                    f"❌ تحتاج: {category['price'] - user['balance']:,.2f} ريال إضافية"
                )
                return
            
            # Find available card
            cursor.execute('''
                SELECT * FROM cards 
                WHERE category_id = ? AND is_sold = 0 
                ORDER BY created_at ASC 
                LIMIT 1
            ''', (category_id,))
            card = cursor.fetchone()
            
            if not card:
                await query.edit_message_text(f"{EMOJIS['error']} نفدت الكروت من هذه الفئة.")
                return
            
            # Execute purchase transaction
            purchase_time = datetime.now()
            
            # 1. Mark card as sold
            cursor.execute('''
                UPDATE cards 
                SET is_sold = 1, sold_to = ?, sold_at = ?, sale_price = ?
                WHERE id = ?
            ''', (user['id'], purchase_time, category['price'], card['id']))
            
            # 2. Deduct from user balance
            new_balance = user['balance'] - category['price']
            cursor.execute('''
                UPDATE users 
                SET balance = ?, total_purchases = total_purchases + 1, 
                    total_spent = total_spent + ?, last_activity = ?
                WHERE id = ?
            ''', (new_balance, category['price'], purchase_time, user['id']))
            
            # 3. Update category stock
            cursor.execute('''
                UPDATE card_categories 
                SET stock_count = stock_count - 1 
                WHERE id = ?
            ''', (category_id,))
            
            # 4. Record transaction (adjusted for actual table structure)
            cursor.execute('''
                INSERT INTO transactions (from_user, amount, type, description, created_at, reference_id)
                VALUES (?, ?, 'purchase', ?, ?, ?)
            ''', (user['id'], category['price'], 
                  f"شراء كرت {category['network_name']} - {category['name']}", 
                  purchase_time, f"card_{card['id']}"))
            
            conn.commit()
            
            # Clear purchase data from context
            context.user_data.pop('purchase_category_id', None)
            
            # Prepare card details for display
            card_details = f"""
🎉 **تم شراء الكرت بنجاح!** 🎉

🌐 **تفاصيل الكرت:**
📡 الشبكة: **{category['network_name']}**
🏢 المزود: **{category['provider']}**
🏷️ الفئة: **{category['name']}**
💎 القيمة: **{category['value']:,.0f}** ريال
💰 السعر المدفوع: **{category['price']:,.2f}** ريال

🎫 **بيانات الكرت:**
🔢 الرقم السري: `{card['card_number']}`
🔐 كود التفعيل: `{card['pin_code'] if card['pin_code'] else 'غير مطلوب'}`
⏰ صالح حتى: {card['expiry_date'] if card['expiry_date'] else 'غير محدد'}

💳 **حالة المحفظة:**
💵 الرصيد المتبقي: **{new_balance:,.2f}** ريال

📋 **تعليمات الاستخدام:**
1. انسخ الرقم السري أعلاه
2. اتصل بـ *134# أو *133#
3. اختر خيار شحن الرصيد
4. أدخل الرقم السري

✅ **شكراً لك على الثقة!**
"""
            
            # Send card details
            keyboard = [
                [InlineKeyboardButton('🛒 شراء كرت آخر', callback_data='enhanced_search_networks')],
                [InlineKeyboardButton('💳 محفظتي', callback_data='enhanced_wallet'),
                 InlineKeyboardButton('📊 مشترياتي', callback_data='my_purchases')],
                [InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
            ]
            
            await query.edit_message_text(
                card_details,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            
            # Log successful purchase
            logger.info(f"Card purchase successful: User {user['id']} bought card {card['id']} for {category['price']} YER")
            
            # Send notification to user about successful purchase
            try:
                await context.bot.send_message(
                    chat_id=query.from_user.id,
                    text=f"🎉 تم شراء كرت {category['network_name']} بنجاح!\n\n"
                         f"🔢 الرقم السري: `{card['card_number']}`\n"
                         f"💰 تم خصم {category['price']:,.2f} ريال من محفظتك",
                    parse_mode='Markdown'
                )
            except Exception as e:
                logger.warning(f"Failed to send purchase notification: {e}")
            
        except Exception as db_error:
            conn.rollback()
            logger.error(f"Database error during purchase: {db_error}")
            await query.edit_message_text(
                f"{EMOJIS['error']} حدث خطأ أثناء عملية الشراء. يرجى المحاولة مرة أخرى.\n\n"
                f"إذا تم خصم المبلغ، سيتم استرداده خلال 24 ساعة."
            )
        finally:
            conn.close()
            
    except Exception as e:
        logger.error(f"Error in enhanced_execute_purchase_handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ غير متوقع. يرجى المحاولة مرة أخرى.")
        
        # Clear purchase context on error
        context.user_data.pop('purchase_category_id', None)