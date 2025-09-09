#!/usr/bin/env python3
"""
Purchase and Card Handlers Module
معالجات الشراء والكروت
"""

import logging
import uuid
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext

# Import utilities
from bot_modules.utils import get_user, get_or_create_supplier_code
from bot_modules.database import get_db_connection
from bot_modules.config import EMOJIS
from bot_modules.enhanced_error_messages import ErrorMessages, menu_error

logger = logging.getLogger(__name__)

async def buy_cards_handler(update: Update, context):
    """Handle buy cards request"""
    try:
        query = update.callback_query
        user = get_user(query.from_user.id)
        
        # الحصول على الشبكات المتاحة
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT n.id, n.name, n.provider, n.location, COUNT(cc.id) as categories_count,
                   MIN(cc.price) as min_price, MAX(cc.price) as max_price
            FROM networks n
            LEFT JOIN card_categories cc ON n.id = cc.network_id AND cc.is_available = 1
            WHERE n.is_active = 1 AND n.is_approved = 1
            GROUP BY n.id, n.name, n.provider, n.location
            HAVING categories_count > 0
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
                net_id, name, provider, location, cat_count, min_price, max_price = network
                location_text = f"📍 {location}" if location else ""
                price_range = f"{min_price:,.0f} - {max_price:,.0f}" if min_price != max_price else f"{min_price:,.0f}"
                
                buy_text += f"""
🌐 **{name}**
👤 {provider} {location_text}
💳 {cat_count} فئة متاحة
💰 {price_range} ريال
━━━━━━━━━━━━━━━━━━━━━━━
"""
        else:
            buy_text += "❌ لا توجد شبكات متاحة حالياً"
        
        keyboard = []
        
        # إضافة أزرار الشبكات للشراء
        if networks:
            for network in networks[:6]:  # أول 6 شبكات
                net_id = network[0]
                name = network[1]
                keyboard.append([
                    InlineKeyboardButton(f'🛒 شراء من {name}', callback_data=f'buy_from_network_{net_id}')
                ])
        
        keyboard.extend([
            [InlineKeyboardButton(f'📊 جميع الشبكات', callback_data='view_all_networks'),
             InlineKeyboardButton(f'🔍 البحث في الشبكات', callback_data='search_networks')],
            [InlineKeyboardButton(f'💰 شحن الرصيد', callback_data='recharge_balance'),
             InlineKeyboardButton(f'📈 إحصائياتي', callback_data='my_purchase_stats')],
            [InlineKeyboardButton(f'{EMOJIS["home"]} القائمة الرئيسية', callback_data='main_menu')]
        ])
        
        await query.edit_message_text(buy_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in buy cards handler: {e}")
        await query.edit_message_text(menu_error("صفحة الشراء", "شراء الكروت"))

async def show_network_categories(update: Update, context: CallbackContext, network_id: str):
    """عرض فئات الكروت المتاحة في الشبكة للشراء"""
    try:
        query = update.callback_query
        user = get_user(query.from_user.id)
        
        if not user:
            await query.edit_message_text(
                "❌ يرجى التسجيل أولاً /start",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
                ])
            )
            return
        
        # الحصول على معلومات الشبكة وفئاتها
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # معلومات الشبكة
        cursor.execute('SELECT name, provider, location FROM networks WHERE id = ? AND is_active = 1', (network_id,))
        network = cursor.fetchone()
        
        if not network:
            await query.edit_message_text(
                "❌ الشبكة غير موجودة أو غير متاحة",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton('🛒 شراء كروت', callback_data='buy_cards')]
                ])
            )
            return
        
        network_name, provider, location = network
        
        # الحصول على الفئات المتاحة مع عدد الكروت
        cursor.execute('''
            SELECT DISTINCT card_value, COUNT(*) as available_count
            FROM network_cards 
            WHERE network_id = ? AND is_sold = 0
            GROUP BY card_value
            ORDER BY card_value ASC
        ''', (network_id,))
        
        categories = cursor.fetchall()
        conn.close()
        
        location_text = f" - {location}" if location else ""
        
        categories_text = f"""
🛒 **شراء من {network_name}** 🛒

🌐 **{network_name}**
👤 المزود: **{provider}**{location_text}
💰 رصيدك: **{user['balance']:,.2f}** ريال

💳 **الفئات المتاحة:**
"""
        
        keyboard = []
        
        if categories:
            for category in categories:
                card_value, available_count = category
                
                categories_text += f"""
💳 **{card_value:,.0f} ريال** - متوفر: {available_count} كرت
"""
                
                # إضافة زر للفئة
                keyboard.append([
                    InlineKeyboardButton(
                        f'💳 {card_value:,.0f} ريال ({available_count} متوفر)', 
                        callback_data=f'confirm_purchase_{network_id}_{card_value}'
                    )
                ])
        else:
            categories_text += "❌ لا توجد كروت متاحة في هذه الشبكة حالياً"
        
        keyboard.extend([
            [InlineKeyboardButton('🔙 العودة للشبكات', callback_data='buy_cards')],
            [InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
        ])
        
        await query.edit_message_text(categories_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in show network categories: {e}")
        await query.edit_message_text(ErrorMessages.custom_error(
            "عرض فئات الشبكة",
            "فشل في تحميل الفئات المتاحة للشبكة",
            "تأكد من وجود الشبكة وحاول مرة أخرى",
            "CATEGORIES_ERROR"
        ))

async def confirm_card_purchase(update: Update, context: CallbackContext, network_id: str, price: str):
    """تأكيد شراء الكرت"""
    try:
        query = update.callback_query
        user = get_user(query.from_user.id)
        
        if not user:
            await query.edit_message_text("❌ يرجى التسجيل أولاً /start")
            return
        
        # الحصول على معلومات الشبكة
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT name, provider FROM networks WHERE id = ? AND is_active = 1', (network_id,))
        network = cursor.fetchone()
        
        if not network:
            await query.edit_message_text("❌ الشبكة غير موجودة أو غير متاحة")
            return
        
        network_name, provider = network
        card_price = float(price)
        
        # التحقق من توفر الكرت
        cursor.execute('''
            SELECT COUNT(*) FROM network_cards 
            WHERE network_id = ? AND card_value = ? AND is_sold = 0
        ''', (network_id, card_price))
        result = cursor.fetchone()
        available_count = result[0] if result else 0
        
        conn.close()
        
        if available_count == 0:
            await query.edit_message_text(
                f"❌ عذراً، لا توجد كروت متاحة بقيمة {card_price:,.0f} ريال",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton('🔙 العودة للفئات', callback_data=f'buy_from_network_{network_id}')
                ]])
            )
            return
        
        # التحقق من الرصيد
        if user['balance'] < card_price:
            await query.edit_message_text(
                f"❌ رصيدك ({user['balance']:,.2f} ريال) غير كافي لشراء كرت بقيمة {card_price:,.0f} ريال",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton('💳 شحن الرصيد', callback_data='enhanced_wallet'),
                    InlineKeyboardButton('🔙 العودة', callback_data=f'buy_from_network_{network_id}')
                ]])
            )
            return
        
        # عرض تأكيد الشراء
        confirm_text = f"""
💳 **تأكيد شراء الكرت** 💳

🌐 **الشبكة:** {network_name}
👤 **المزود:** {provider}
💰 **قيمة الكرت:** {card_price:,.0f} ريال
✅ **متوفر:** {available_count} كرت

💵 **ملخص العملية:**
💰 رصيدك الحالي: **{user['balance']:,.2f}** ريال
💳 سعر الكرت: **{card_price:,.0f}** ريال
💵 رصيدك بعد الشراء: **{user['balance'] - card_price:,.2f}** ريال

⚠️ **هل تريد إتمام عملية الشراء؟**
"""
        
        keyboard = [
            [InlineKeyboardButton('✅ تأكيد الشراء', callback_data=f'process_purchase_{network_id}_{price}')],
            [InlineKeyboardButton('❌ إلغاء', callback_data=f'buy_from_network_{network_id}')],
            [InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
        ]
        
        await query.edit_message_text(confirm_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in confirm card purchase: {e}")
        await query.edit_message_text(ErrorMessages.custom_error(
            "تأكيد الشراء",
            "فشل في تحميل معلومات التأكيد",
            "حاول مرة أخرى أو تواصل مع الدعم",
            "CONFIRM_ERROR"
        ))

async def process_card_purchase(update: Update, context: CallbackContext, network_id: str, price: str):
    """تنفيذ شراء الكرت"""
    try:
        query = update.callback_query
        user = get_user(query.from_user.id)
        
        if not user:
            await query.edit_message_text("❌ يرجى التسجيل أولاً /start")
            return
        
        # حماية ضد الضغط المتعدد
        if context.user_data.get('purchase_processing'):
            await query.answer("⏳ عملية الشراء قيد التنفيذ، يرجى الانتظار...", show_alert=True)
            return
        
        # تعيين حالة المعالجة
        context.user_data['purchase_processing'] = True
        
        # الحصول على معلومات الشبكة
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # بدء معاملة قاعدة البيانات
        cursor.execute('BEGIN TRANSACTION')
        
        try:
            cursor.execute('SELECT name, provider, supplier_id FROM networks WHERE id = ? AND is_active = 1', (network_id,))
            network = cursor.fetchone()
            
            if not network:
                raise Exception("الشبكة غير موجودة أو غير متاحة")
            
            network_name, provider, supplier_id = network
            card_price = float(price)
            
            # التحقق من توفر الكرت (مع قفل للصف لتجنب التضارب)
            cursor.execute('''
                SELECT id FROM network_cards 
                WHERE network_id = ? AND card_value = ? AND is_sold = 0
                LIMIT 1
            ''', (network_id, card_price))
            
            card_result = cursor.fetchone()
            if not card_result:
                raise Exception(f"لا توجد كروت متاحة بقيمة {card_price:,.0f} ريال")
            
            card_id = card_result[0]
            
            # التحقق من الرصيد مرة أخرى
            cursor.execute('SELECT balance FROM users WHERE telegram_id = ?', (user['telegram_id'],))
            result = cursor.fetchone()
            if not result:
                raise Exception("خطأ في استرداد بيانات المستخدم")
            current_balance = result[0]
            
            if current_balance < card_price:
                raise Exception(f"رصيدك ({current_balance:,.2f} ريال) غير كافي")
            
            # تحديث حالة الكرت إلى مباع
            cursor.execute('UPDATE network_cards SET is_sold = 1, sold_at = datetime("now") WHERE id = ?', (card_id,))
            
            # خصم المبلغ من رصيد المشتري
            cursor.execute('UPDATE users SET balance = balance - ? WHERE telegram_id = ?', (card_price, user['telegram_id']))
            
            # إضافة المبلغ لرصيد المزود
            cursor.execute('UPDATE users SET balance = balance + ? WHERE id = ?', (card_price, supplier_id))
            
            # إنشاء معاملة في السجل
            transaction_id = str(uuid.uuid4())
            
            cursor.execute('''
                INSERT INTO transactions (id, from_user, to_user, amount, type, description, created_at)
                VALUES (?, ?, ?, ?, ?, ?, datetime("now"))
            ''', (transaction_id, user['id'], supplier_id, card_price, 'card_purchase', 
                  f"شراء كرت {card_price:,.0f} ريال من شبكة {network_name}"))
            
            # الحصول على معلومات الكرت
            cursor.execute('SELECT card_code FROM network_cards WHERE id = ?', (card_id,))
            result = cursor.fetchone()
            if not result:
                raise Exception("خطأ في استرداد بيانات الكرت")
            card_code = result[0]
            
            # تسجيل القيد المحاسبي لشراء الكرت (معطل مؤقتاً لتحسين الأداء)
            # record_purchase_accounting(card_price, user['id'], transaction_id)
            
            # تأكيد المعاملة
            cursor.execute('COMMIT')
            
            # معالجة عمولة الإحالة (5% للمحيل)
            try:
                from bot_modules.utils import process_referral_commission
                process_referral_commission(user['id'], card_price, transaction_id)
            except Exception as e:
                logger.warning(f"Failed to process referral commission: {e}")
            
            # معالجة تقسيم الأرباح (70% للمزود، 30% للمشرف الأعلى)
            try:
                from bot_modules.utils import process_purchase_profit_sharing
                process_purchase_profit_sharing(card_price, supplier_id, transaction_id)
            except Exception as e:
                logger.warning(f"Failed to process profit sharing: {e}")
            
            # عرض نتيجة الشراء الناجح
            success_text = f"""
✅ **تم الشراء بنجاح!** ✅

👤 **{user['full_name']}**

📋 **تفاصيل الشراء:**
🏪 الشبكة: **{network_name}**
👤 المزود: **{provider}**
💰 المبلغ المدفوع: **{card_price:,.0f}** ريال

🎫 **بيانات الكرت:**
🔢 رقم الكرت: `{card_code}`
💰 القيمة: **{card_price:,.0f}** ريال

💳 **رصيدك الجديد:** {current_balance - card_price:,.2f} ريال

🎉 **شكراً لك على الشراء!**
💡 احتفظ برقم الكرت في مكان آمن
"""
            
            keyboard = [
                [InlineKeyboardButton('🛒 شراء كرت آخر', callback_data=f'buy_from_network_{network_id}')],
                [InlineKeyboardButton('💳 محفظتي', callback_data='enhanced_wallet'),
                 InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
            ]
            
            await query.edit_message_text(success_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
            
        except Exception as e:
            # Rollback the transaction
            cursor.execute('ROLLBACK')
            conn.close()
            
            # Clear processing state
            context.user_data.pop('purchase_processing', None)
            
            logger.error(f"Purchase failed: {e}")
            await query.edit_message_text(
                f"❌ **فشل في الشراء**\n\n{str(e)}",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton('🔙 العودة للفئات', callback_data=f'buy_from_network_{network_id}')],
                    [InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
                ])
            )
            return
        
        # Clear processing state
        context.user_data.pop('purchase_processing', None)
        
    except Exception as e:
        # Clear processing state
        context.user_data.pop('purchase_processing', None)
        logger.error(f"Error in process card purchase: {e}")
        await query.edit_message_text(ErrorMessages.custom_error(
            "معالجة الشراء",
            "فشل في تنفيذ عملية الشراء",
            "تأكد من رصيدك وحاول مرة أخرى",
            "PURCHASE_ERROR"
        ))