#!/usr/bin/env python3
"""
Network Handler Module for Yemen Net Bot
Handles network display, card categories, and purchase flow
"""

import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext
from database import get_db_connection, get_user, update_user_balance, update_inventory_stock
from utils import generate_card_code, log_transaction

logger = logging.getLogger(__name__)

async def show_network_details_enhanced(update: Update, context: CallbackContext, network_id: str):
    """عرض تفاصيل شبكة مع فئات الكروت والأسعار بشكل منظم"""
    try:
        user = get_user(update.effective_user.id)
        if not user:
            await update.callback_query.edit_message_text("❌ يرجى التسجيل أولاً /start")
            return

        conn = get_db_connection()
        cursor = conn.cursor()
        
        # الحصول على بيانات الشبكة
        cursor.execute('''
            SELECT id, name, provider, description, location 
            FROM networks WHERE id = ? AND is_active = 1
        ''', (network_id,))
        network = cursor.fetchone()
        
        if not network:
            await update.callback_query.edit_message_text("❌ الشبكة غير موجودة أو غير متاحة")
            return
        
        # الحصول على فئات الكروت مع ترتيب أفضل
        cursor.execute('''
            SELECT id, name, value, price, stock_count, description
            FROM card_categories 
            WHERE network_id = ? AND is_available = 1
            ORDER BY value ASC, price ASC
        ''', (network_id,))
        
        categories = cursor.fetchall()
        conn.close()
        
        # تنسيق معلومات الشبكة
        # network = (id, name, provider, description, location)
        text = f"""
🏢 **{network[1]}** - {network[2]}

👤 **{user['full_name']}**
💰 رصيدك: **{user['balance']:,.2f}** ريال

📝 **الوصف:**
{network[3] or 'شبكة إنترنت موثوقة وسريعة'}

📍 **الموقع:** {network[4] or 'غير محدد'}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💳 **فئات الكروت المتاحة والأسعار:**

"""

        keyboard = []
        
        if categories:
            for i, category in enumerate(categories):
                cat_id, cat_name, cat_value, cat_price, cat_stock, cat_desc = category
                
                # تحديد حالة التوفر
                availability = "✅ متوفر" if cat_stock > 0 else "❌ نفذ"
                stock_info = f"({cat_stock} كرت)" if cat_stock > 0 else "(نفذ)"
                
                # تنسيق القيمة
                if cat_value >= 1024:
                    value_text = f"{cat_value/1024:.0f} جيجا"
                elif cat_value >= 100:
                    value_text = f"{cat_value} ريال"
                else:
                    value_text = f"{cat_value} ميجا"
                
                # إضافة رقم تسلسلي
                text += f"""
**{i+1}. {cat_name}** {availability}
📊 القيمة: {value_text}
💰 السعر: **{cat_price:,.0f}** ريال
📦 {stock_info}
"""
                
                if cat_desc:
                    text += f"📝 {cat_desc}\n"
                
                text += "━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                
                # إضافة زر شراء إذا كان متوفراً
                if cat_stock > 0 and user['balance'] >= cat_price:
                    keyboard.append([InlineKeyboardButton(
                        f"🛒 شراء {cat_name} - {cat_price:,.0f} ريال",
                        callback_data=f"buy_card_{cat_id}"
                    )])
                elif cat_stock > 0:
                    keyboard.append([InlineKeyboardButton(
                        f"💰 رصيد غير كافي - {cat_price:,.0f} ريال",
                        callback_data=f"insufficient_balance"
                    )])
                else:
                    keyboard.append([InlineKeyboardButton(
                        f"❌ نفذ - {cat_name}",
                        callback_data=f"out_of_stock_{cat_id}"
                    )])
        else:
            text += "❌ لا توجد فئات متاحة حالياً\n"

        # إضافة أزرار إضافية
        keyboard.extend([
            [InlineKeyboardButton('🔙 جميع الشبكات', callback_data='all_networks'),
             InlineKeyboardButton('💳 محفظتي', callback_data='enhanced_wallet')],
            [InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
        ])

        await update.callback_query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

    except Exception as e:
        logger.error(f"Error in show network details enhanced: {e}")
        await update.callback_query.edit_message_text("❌ حدث خطأ في عرض تفاصيل الشبكة")

async def process_card_purchase_enhanced(update: Update, context: CallbackContext, category_id: str):
    """معالجة شراء الكرت مع رسالة تأكيد محسنة"""
    try:
        user = get_user(update.effective_user.id)
        if not user:
            await update.callback_query.edit_message_text("❌ يرجى التسجيل أولاً /start")
            return
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # الحصول على بيانات فئة الكرت
        cursor.execute('''
            SELECT cc.id, cc.network_id, cc.name, cc.value, cc.price, cc.currency, 
                   cc.is_available, cc.stock_count, cc.created_at, cc.updated_at,
                   n.name as network_name, n.provider
            FROM card_categories cc
            JOIN networks n ON cc.network_id = n.id
            WHERE cc.id = ? AND cc.is_available = 1
        ''', (category_id,))
        
        category = cursor.fetchone()
        
        if not category:
            await update.callback_query.edit_message_text("❌ فئة الكرت غير متاحة")
            return
        
        cat_id, network_id, cat_name, cat_value, cat_price, currency, is_available, stock_count, created_at, updated_at, network_name, provider = category
        
        # التحقق من التوفر
        if stock_count <= 0:
            await update.callback_query.edit_message_text(
                f"❌ **الكرت غير متوفر**\n\n"
                f"💳 {cat_name}\n"
                f"🏢 {network_name}\n"
                f"📦 المخزون: نفذ\n\n"
                f"💡 تحقق لاحقاً أو اختر فئة أخرى"
            )
            return
        
        # التحقق من الرصيد
        if user['balance'] < cat_price:
            await update.callback_query.edit_message_text(
                f"❌ **رصيد غير كافي**\n\n"
                f"💳 {cat_name}\n"
                f"💰 السعر: {cat_price:,.2f} ريال\n"
                f"💵 رصيدك: {user['balance']:,.2f} ريال\n"
                f"💡 تحتاج {cat_price - user['balance']:,.2f} ريال إضافية"
            )
            return
        
        # عرض رسالة تأكيد الشراء
        confirmation_text = f"""
🛒 **تأكيد الشراء** 🛒

👤 **المشتري:** {user['full_name']}
💳 محفظتك: {user['wallet_number']}

🛒 **تفاصيل الشراء:**
🏢 الشبكة: **{network_name}**
🏭 المزود: **{provider}**
💳 الكرت: **{cat_name}**
📊 القيمة: {cat_value} {"جيجا" if cat_value >= 1024 else "ميجا" if cat_value < 100 else "ريال"}
💰 السعر: **{cat_price:,.2f}** ريال

💰 **رصيدك بعد الشراء:** {user['balance'] - cat_price:,.2f} ريال

⚠️ **هل تريد تأكيد شراء الكرت؟**
"""
        
        keyboard = [
            [InlineKeyboardButton('✅ نعم', callback_data=f'confirm_purchase_{category_id}'),
             InlineKeyboardButton('❌ لا', callback_data='cancel')],
            [InlineKeyboardButton('🔙 اختيار كرت آخر', callback_data=f'network_{network_id}')]
        ]
        
        await update.callback_query.edit_message_text(
            confirmation_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
        conn.close()
        
    except Exception as e:
        logger.error(f"Error in process card purchase enhanced: {e}")
        await update.callback_query.edit_message_text("❌ حدث خطأ في معالجة الشراء")

async def confirm_card_purchase(update: Update, context: CallbackContext, category_id: str):
    """تأكيد شراء الكرت وإتمام العملية"""
    try:
        user = get_user(update.effective_user.id)
        if not user:
            await update.callback_query.edit_message_text("❌ يرجى التسجيل أولاً /start")
            return
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # الحصول على بيانات فئة الكرت
        cursor.execute('''
            SELECT cc.id, cc.network_id, cc.name, cc.value, cc.price, cc.currency, 
                   cc.is_available, cc.stock_count, cc.created_at, cc.updated_at,
                   n.name as network_name, n.provider
            FROM card_categories cc
            JOIN networks n ON cc.network_id = n.id
            WHERE cc.id = ? AND cc.is_available = 1
        ''', (category_id,))
        
        category = cursor.fetchone()
        
        if not category:
            await update.callback_query.edit_message_text("❌ فئة الكرت غير متاحة")
            return
        
        cat_id, network_id, cat_name, cat_value, cat_price, currency, is_available, stock_count, created_at, updated_at, network_name, provider = category
        
        # التحقق من التوفر مرة أخرى
        if stock_count <= 0:
            await update.callback_query.edit_message_text(
                f"❌ **الكرت غير متوفر**\n\n"
                f"💳 {cat_name}\n"
                f"🏢 {network_name}\n"
                f"📦 المخزون: نفذ\n\n"
                f"💡 تحقق لاحقاً أو اختر فئة أخرى"
            )
            return
        
        # التحقق من الرصيد مرة أخرى
        if user['balance'] < cat_price:
            await update.callback_query.edit_message_text(
                f"❌ **رصيد غير كافي**\n\n"
                f"💳 {cat_name}\n"
                f"💰 السعر: {cat_price:,.2f} ريال\n"
                f"💵 رصيدك: {user['balance']:,.2f} ريال\n"
                f"💡 تحتاج {cat_price - user['balance']:,.2f} ريال إضافية"
            )
            return
        
        # إتمام عملية الشراء
        try:
            # خصم المبلغ من رصيد المستخدم
            new_balance = user['balance'] - cat_price
            update_user_balance(user['id'], new_balance)
            
            # تقليل المخزون
            update_inventory_stock(network_id, cat_id, -1)
            
            # إنشاء كرت جديد
            card_code = generate_card_code()
            purchase_date = datetime.now()
            
            # تسجيل الكرت في قاعدة البيانات
            cursor.execute('''
                INSERT INTO cards (category_id, card_number, is_sold, sold_to, sold_at)
                VALUES (?, ?, 1, ?, ?)
            ''', (cat_id, card_code, user['id'], purchase_date))
            
            # تسجيل المعاملة
            transaction_id = f"TXN_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{user['id']}"
            log_transaction(
                transaction_id=transaction_id,
                user_id=user['id'],
                transaction_type='purchase',
                amount=cat_price,
                description=f"شراء كرت {cat_name} من {network_name}",
                status='completed'
            )
            
            conn.commit()
            
            # رسالة نجاح الشراء
            success_text = f"""
✅ **تم الشراء بنجاح!** ✅

🎫 **رقم الكرت:** `{card_code}`
🏢 **اسم الشبكة:** {network_name}
🏭 **المزود:** {provider}
💳 **نوع الكرت:** {cat_name}
📊 **القيمة:** {cat_value} {"جيجا" if cat_value >= 1024 else "ميجا" if cat_value < 100 else "ريال"}
💰 **السعر:** {cat_price:,.2f} ريال
📅 **تاريخ الشراء:** {purchase_date.strftime('%Y-%m-%d %H:%M:%S')}

💳 **رصيدك الجديد:** {new_balance:,.2f} ريال

🔐 **احتفظ برقم الكرت في مكان آمن!**
"""
            
            keyboard = [
                [InlineKeyboardButton('🛒 شراء كرت آخر', callback_data=f'network_{network_id}')],
                [InlineKeyboardButton('💳 محفظتي', callback_data='enhanced_wallet'),
                 InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
            ]
            
            await update.callback_query.edit_message_text(
                success_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            
            logger.info(f"تم شراء كرت {cat_name} من {network_name} بواسطة {user['full_name']} (ID: {user['id']})")
            
        except Exception as db_error:
            conn.rollback()
            logger.error(f"Database error in card purchase: {db_error}")
            await update.callback_query.edit_message_text(
                "❌ **فشل في إتمام الشراء**\n\n"
                "🔍 حدث خطأ في قاعدة البيانات\n"
                "💡 يرجى المحاولة مرة أخرى"
            )
        
        conn.close()
        
    except Exception as e:
        logger.error(f"Error in confirm card purchase: {e}")
        await update.callback_query.edit_message_text("❌ حدث خطأ في تأكيد الشراء")

async def handle_insufficient_balance(update: Update, context: CallbackContext):
    """معالجة حالة الرصيد غير الكافي"""
    try:
        text = """
❌ **رصيد غير كافي** ❌

💰 **لشراء هذا الكرت، تحتاج إلى:**
• شحن محفظتك
• أو اختيار كرت بسعر أقل

💡 **خيارات متاحة:**
• شحن المحفظة
• عرض جميع الشبكات
• العودة للقائمة الرئيسية
"""
        
        keyboard = [
            [InlineKeyboardButton('💳 شحن المحفظة', callback_data='enhanced_wallet')],
            [InlineKeyboardButton('🔍 جميع الشبكات', callback_data='all_networks')],
            [InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
        ]
        
        await update.callback_query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Error in handle insufficient balance: {e}")
        await update.callback_query.edit_message_text("❌ حدث خطأ في معالجة الطلب")

async def handle_out_of_stock(update: Update, context: CallbackContext, category_id: str):
    """معالجة حالة نفاد المخزون"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # الحصول على معلومات الكرت
        cursor.execute('''
            SELECT cc.name, n.name as network_name
            FROM card_categories cc
            JOIN networks n ON cc.network_id = n.id
            WHERE cc.id = ?
        ''', (category_id,))
        
        category = cursor.fetchone()
        conn.close()
        
        if category:
            cat_name, network_name = category
            text = f"""
❌ **نفذ المخزون** ❌

💳 **الكرت:** {cat_name}
🏢 **الشبكة:** {network_name}

📦 **المخزون:** نفذ تماماً

💡 **خيارات متاحة:**
• اختيار كرت آخر من نفس الشبكة
• البحث عن شبكات أخرى
• العودة للقائمة الرئيسية
"""
        else:
            text = """
❌ **نفذ المخزون** ❌

💡 **خيارات متاحة:**
• اختيار كرت آخر
• البحث عن شبكات أخرى
• العودة للقائمة الرئيسية
"""
        
        keyboard = [
            [InlineKeyboardButton('🔍 شبكات أخرى', callback_data='all_networks')],
            [InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
        ]
        
        await update.callback_query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Error in handle out of stock: {e}")
        await update.callback_query.edit_message_text("❌ حدث خطأ في معالجة الطلب")