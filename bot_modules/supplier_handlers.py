#!/usr/bin/env python3
"""
Supplier and Network Handlers Module
معالجات المزودين والشبكات
"""

import logging
import uuid
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext

# Import utilities
from bot_modules.utils import (
    get_user, get_or_create_supplier_code, get_cards_stats_by_category,
    get_provider_withdrawable_amount, get_network_share_info, generate_supplier_share_link
)
from bot_modules.database import get_db_connection
from bot_modules.config import EMOJIS
from bot_modules.enhanced_error_messages import ErrorMessages

logger = logging.getLogger(__name__)

async def supplier_panel_handler(update: Update, context):
    """Handle enhanced supplier panel"""
    try:
        query = update.callback_query
        user = get_user(query.from_user.id)
        
        # Get supplier code
        supplier_code = get_or_create_supplier_code(user['id'])
        
        # Get statistics
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Count networks
        cursor.execute('SELECT COUNT(*) as count FROM networks WHERE supplier_id = ?', (user['id'],))
        result = cursor.fetchone()
        networks_count = result['count'] if result else 0
        
        # Count active cards
        cursor.execute('SELECT COUNT(*) as count FROM network_cards WHERE supplier_id = ? AND is_sold = 0', (user['id'],))
        result = cursor.fetchone()
        active_cards = result['count'] if result else 0
        
        # Count sold cards
        cursor.execute('SELECT COUNT(*) as count FROM network_cards WHERE supplier_id = ? AND is_sold = 1', (user['id'],))
        result = cursor.fetchone()
        sold_cards = result['count'] if result else 0
        
        # Recent uploads
        cursor.execute('SELECT COUNT(*) as count FROM card_upload_batches WHERE supplier_id = ?', (user['id'],))
        result = cursor.fetchone()
        recent_uploads = result['count'] if result else 0
        
        conn.close()
        
        # الحصول على معلومات الأرباح
        profit_info = get_provider_withdrawable_amount(user['id'])
        
        # تحديد حالة الشبكة
        network_status = "✅ متاحة" if networks_count == 0 else "📶 مُنشأة"
        can_add_network = networks_count == 0 and user['is_active']
        
        panel_text = f"""
🏪 **لوحة المزود المطورة** 🏪

👤 **{user['full_name']}**
💰 رصيدك: **{user['balance']:.2f}** ريال
🆔 **معرف المزود: `{supplier_code}`**
🔰 حالة التفعيل: **{'✅ مفعل' if user['is_active'] else '⏳ في الانتظار'}**

📊 **إحصائيات المزود:**
📶 شبكتك: **{network_status}** ({networks_count}/1)
📋 كروت متاحة: **{active_cards}**
✅ كروت مباعة: **{sold_cards}**
📤 رفع حديث (7 أيام): **{recent_uploads}**

💰 **ملخص الأرباح (70% من المبيعات):**
💵 إجمالي الأرباح: **{profit_info['total_earnings']:,.2f}** ريال
📤 تم سحبه/معلق: **{profit_info['withdrawn_amount']:,.2f}** ريال
✅ متاح للسحب: **{profit_info['available_amount']:,.2f}** ريال

🎯 **إدارة الكروت والشبكات:**
💡 **ملاحظة:** يُسمح بشبكة واحدة فقط لكل مزود
"""
        
        keyboard = [
            [InlineKeyboardButton(f'📶 إدارة الشبكات', callback_data='manage_networks'),
             InlineKeyboardButton(f'📤 رفع كروت', callback_data='upload_cards')],
            [InlineKeyboardButton(f'📊 تقارير الكروت', callback_data='cards_reports'),
             InlineKeyboardButton(f'📈 إحصائيات المبيعات', callback_data='sales_stats')],
            [InlineKeyboardButton(f'💰 طلب سحب الأرباح', callback_data='request_withdrawal'),
             InlineKeyboardButton(f'📋 سجل الرفع', callback_data='upload_history')],
            [InlineKeyboardButton(f'⚙️ إعدادات المزود', callback_data='supplier_settings'),
             InlineKeyboardButton(f'{EMOJIS["home"]} القائمة الرئيسية', callback_data='main_menu')]
        ]
        
        await query.edit_message_text(panel_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in supplier panel handler: {e}")
        await query.edit_message_text(ErrorMessages.supplier_error(
            "تحميل لوحة التحكم", 
            "فشل في الوصول إلى بيانات المزود"
        ))

async def view_networks_handler(update: Update, context):
    """Handle view networks"""
    try:
        query = update.callback_query
        
        # الحصول على الشبكات المتاحة من قاعدة البيانات
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT n.id, n.name, n.provider, n.location, n.created_at,
                   COUNT(cc.id) as categories_count,
                   MIN(cc.price) as min_price, MAX(cc.price) as max_price,
                   COUNT(CASE WHEN c.is_sold = 0 THEN 1 END) as available_cards
            FROM networks n
            LEFT JOIN card_categories cc ON n.id = cc.network_id AND cc.is_available = 1
            LEFT JOIN cards c ON cc.id = c.category_id
            WHERE n.is_active = 1 AND n.is_approved = 1
            GROUP BY n.id, n.name, n.provider, n.location, n.created_at
            HAVING categories_count > 0
            ORDER BY n.created_at DESC
        ''')
        networks = cursor.fetchall()
        conn.close()
        
        networks_text = f"""
📶 **الشبكات المتاحة ({len(networks)} شبكة)** 📶

🛒 **اختر الشبكة للشراء:**

"""
        
        keyboard = []
        
        if networks:
            for network in networks:
                net_id, name, provider, location, created_at, cat_count, min_price, max_price, available = network
                location_text = f" - {location}" if location else ""
                price_range = f"{min_price:,.0f}-{max_price:,.0f}" if min_price != max_price else f"{min_price:,.0f}"
                
                networks_text += f"""
🌐 **{name}**
👤 {provider}{location_text}
💳 {cat_count} فئة | 💰 {price_range} ريال
📦 متوفر: {available} كرت
━━━━━━━━━━━━━━━━━━━━━━━━━
"""
                
                # إضافة زر للشبكة
                keyboard.append([
                    InlineKeyboardButton(f'🛒 {name}', callback_data=f'buy_from_network_{net_id}')
                ])
        else:
            networks_text += "❌ لا توجد شبكات متاحة حالياً"
        
        keyboard.extend([
            [InlineKeyboardButton(f'🔍 البحث في الشبكات', callback_data='search_networks')],
            [InlineKeyboardButton(f'{EMOJIS["home"]} القائمة الرئيسية', callback_data='main_menu')]
        ])
        
        await query.edit_message_text(networks_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in view networks handler: {e}")
        await query.edit_message_text(ErrorMessages.network_error("عرض الشبكات"))

async def manage_networks_handler(update: Update, context):
    """Handle network management"""
    try:
        query = update.callback_query
        user = get_user(query.from_user.id)
        
        # Get user's networks
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM networks WHERE supplier_id = ? ORDER BY id DESC', (user['id'],))
        networks = cursor.fetchall()
        conn.close()
        
        networks_text = f"""
📶 **إدارة الشبكات** 📶

👤 **{user['full_name']}**
📊 شبكاتك: **{len(networks)}/1** (الحد الأقصى)
🔰 حالة التفعيل: **{'✅ مفعل' if user['is_active'] else '⏳ في الانتظار'}**

📋 **شبكتك:**
"""
        
        if networks:
            network = networks[0]  # عرض الشبكة الوحيدة
            status = "✅ مفعلة" if network['is_active'] else "⏸️ متوقفة"
            approval = "✅ معتمدة" if network['is_approved'] else "⏳ في انتظار الموافقة"
            networks_text += f"""
📶 **{network['name']}**
🏢 المزود: {network['provider']}
🏙️ المدينة: {network['city']}
📊 الحالة: {status}
✅ الاعتماد: {approval}

💡 **ملاحظة:** يُسمح بشبكة واحدة فقط لكل مزود
"""
        else:
            networks_text += """
⚠️ لا توجد شبكة مسجلة بعد

💡 **يمكنك إنشاء شبكة واحدة فقط**
"""
        
        # تحديد الأزرار حسب الحالة
        keyboard = []
        
        if networks:
            # إذا كانت توجد شبكة، عرض أزرار الإدارة
            network_id = networks[0]['id']
            keyboard = [
                [InlineKeyboardButton('📊 تفاصيل الشبكة', callback_data='network_details'),
                 InlineKeyboardButton('🔗 مشاركة الشبكة', callback_data=f'share_network_{network_id}')],
                [InlineKeyboardButton('📤 رفع كروت', callback_data='upload_cards')],
                [InlineKeyboardButton('🏪 لوحة المزود', callback_data='supplier_panel')]
            ]
        else:
            # إذا لم تكن توجد شبكة ومفعل، إظهار زر الإضافة
            if user['is_active']:
                keyboard = [
                    [InlineKeyboardButton('➕ إضافة شبكة جديدة', callback_data='add_network')],
                    [InlineKeyboardButton('🏪 لوحة المزود', callback_data='supplier_panel')]
                ]
            else:
                keyboard = [
                    [InlineKeyboardButton('🏪 لوحة المزود', callback_data='supplier_panel')]
                ]
        
        await query.edit_message_text(networks_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in manage networks handler: {e}")
        await query.edit_message_text(ErrorMessages.supplier_error(
            "إدارة الشبكات",
            "لا يمكن الوصول إلى بيانات الشبكات الخاصة بك حالياً"
        ))

async def share_network_handler(update: Update, context: CallbackContext, network_id: str):
    """معالج مشاركة الشبكة"""
    try:
        query = update.callback_query
        user = get_user(query.from_user.id)
        
        if not user or user['role'] != 'supplier':
            await query.edit_message_text(f"{EMOJIS['error']} غير مخول لك الوصول لهذه الميزة")
            return
        
        # الحصول على معلومات الشبكة
        network_info = get_network_share_info(network_id, user['id'])
        if not network_info:
            await query.edit_message_text(f"{EMOJIS['error']} الشبكة غير موجودة أو لا تملك صلاحية الوصول إليها")
            return
        
        # إنشاء رابط المشاركة
        bot_username = context.bot.username or "YemenNetBot"
        share_link = generate_supplier_share_link(network_id, bot_username)
        
        share_text = f"""
🔗 **مشاركة شبكتك** 🔗

📶 **{network_info['name']}**
🏢 المزود: **{network_info['provider']}**
🏙️ الموقع: **{network_info['location']}, {network_info['city']}**

📊 **إحصائيات الشبكة:**
💳 إجمالي الكروت: **{network_info['total_cards']:,}** كرت
✅ الكروت المتاحة: **{network_info['available_cards']:,}** كرت
💰 نطاق الأسعار: **{network_info['min_price']:,.0f} - {network_info['max_price']:,.0f}** ريال

🎯 **رابط المشاركة:**
`{share_link}`

💡 **كيفية الاستخدام:**
• شارك هذا الرابط مع العملاء
• عند النقر عليه سيفتح شبكتك مباشرة
• يمكن للعملاء الشراء فوراً من شبكتك
• احصل على المزيد من المبيعات!

📱 **طرق المشاركة:**
• انسخ الرابط وشاركه في الواتساب
• انشره في مجموعات التليجرام
• ضعه في منشوراتك على وسائل التواصل
• أرسله للعملاء مباشرة

🎊 **مزايا الرابط المباشر:**
• وصول سريع لشبكتك
• تجربة شراء محسنة
• زيادة في المبيعات
• سهولة في التسويق
"""
        
        keyboard = [
            [InlineKeyboardButton('📋 نسخ الرابط', callback_data=f'copy_share_link_{network_id}')],
            [InlineKeyboardButton('🔙 العودة لإدارة الشبكات', callback_data='manage_networks'),
             InlineKeyboardButton('🏪 لوحة المزود', callback_data='supplier_panel')]
        ]
        
        await query.edit_message_text(share_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in share network handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في إنشاء رابط المشاركة")

async def upload_cards_handler(update: Update, context):
    """Handle card upload process"""
    try:
        query = update.callback_query
        user = get_user(query.from_user.id)
        
        if user['role'] != 'supplier':
            await query.edit_message_text(f"{EMOJIS['error']} هذه الميزة متاحة للمزودين فقط.")
            return
        
        # التحقق من وجود شبكة مفعلة
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM networks WHERE supplier_id = ?', (user['id'],))
        result = cursor.fetchone()
        existing_networks = result[0] if result else 0
        conn.close()
        
        if existing_networks > 0:
            upload_text = f"""
📤 **رفع كروت جديدة** 📤

👤 **{user['full_name']}**
🔰 حالة التفعيل: **{'✅ مفعل' if user['is_active'] else '⏳ في الانتظار'}**

📋 **تعليمات الرفع:**
1️⃣ أرسل ملف نصي (.txt) يحتوي على أرقام الكروت
2️⃣ كل رقم كرت في سطر منفصل
3️⃣ تأكد من صحة الأرقام قبل الرفع

💡 **مثال على تنسيق الملف:**
```
1234567890123456
2345678901234567
3456789012345678
```

📤 **قم برفع الملف الآن:**
"""
        else:
            upload_text = f"""
❌ **لا يمكن رفع الكروت**

👤 **{user['full_name']}**

⚠️ **يجب إنشاء شبكة أولاً:**
• اذهب لإدارة الشبكات
• أضف شبكة جديدة
• انتظر موافقة الإدارة
• ثم يمكنك رفع الكروت

💡 **ملاحظة:** يُسمح بشبكة واحدة فقط لكل مزود
"""
        
        keyboard = [
            [InlineKeyboardButton('📶 إدارة الشبكات', callback_data='manage_networks')],
            [InlineKeyboardButton('🏪 لوحة المزود', callback_data='supplier_panel')]
        ]
        
        if existing_networks > 0:
            context.user_data['awaiting_card_upload'] = True
        
        await query.edit_message_text(upload_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in upload cards handler: {e}")
        await query.edit_message_text(ErrorMessages.upload_error("رفع الكروت"))

async def cards_reports_handler(update: Update, context):
    """Handle cards reports"""
    try:
        query = update.callback_query
        user = get_user(query.from_user.id)
        
        # Get cards statistics
        stats_by_category = get_cards_stats_by_category(user['id'])
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                COUNT(*) as total_cards,
                SUM(CASE WHEN is_sold = 0 THEN 1 ELSE 0 END) as available_cards,
                SUM(CASE WHEN is_sold = 1 THEN 1 ELSE 0 END) as sold_cards,
                SUM(CASE WHEN is_sold = 0 THEN card_value ELSE 0 END) as available_value,
                SUM(CASE WHEN is_sold = 1 THEN card_value ELSE 0 END) as sold_value
            FROM network_cards 
            WHERE supplier_id = ?
        ''', (user['id'],))
        
        stats = cursor.fetchone()
        if not stats:
            stats = (0, 0, 0, 0, 0, 0)
        conn.close()
        
        reports_text = f"""
📊 **تقارير الكروت المفصلة** 📊

👤 **{user['full_name']}**

📈 **إحصائيات شاملة:**
📦 إجمالي الكروت: **{stats[0]}** كرت
✅ متاحة للبيع: **{stats[1]}** كرت
💰 قيمة المتاح: **{stats[3]:,.2f}** ريال

🎯 **الكروت المباعة:**
✅ كروت مباعة: **{stats[2]}** كرت
💰 قيمة المباع: **{stats[4]:,.2f}** ريال

📊 **معدل المبيعات:**
📈 نسبة البيع: **{(stats[2] / stats[0] * 100) if stats[0] > 0 else 0:.1f}%**

📋 **تفاصيل حسب الفئة:**
"""
        
        if stats_by_category:
            for category_stat in stats_by_category:
                category = category_stat['card_category']
                total = category_stat['total_cards']
                available = category_stat['available_cards']
                sold = category_stat['sold_cards']
                available_value = category_stat['available_value']
                sold_value = category_stat['sold_value']
                
                reports_text += f"""
💳 **فئة {category} ريال:**
📦 المجموع: {total} | ✅ متاح: {available} | ✅ مباع: {sold}
💰 قيمة متاحة: {available_value:,.2f} | 💰 قيمة مباعة: {sold_value:,.2f}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        else:
            reports_text += "❌ لا توجد كروت مرفوعة بعد"
        
        keyboard = [
            [InlineKeyboardButton('📤 رفع كروت جديدة', callback_data='upload_cards'),
             InlineKeyboardButton('📈 إحصائيات المبيعات', callback_data='sales_stats')],
            [InlineKeyboardButton('💳 محفظتي', callback_data='enhanced_wallet'),
             InlineKeyboardButton('🏪 لوحة المزود', callback_data='supplier_panel')]
        ]
        
        await query.edit_message_text(reports_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in cards reports handler: {e}")
        await query.edit_message_text(ErrorMessages.report_error("الكروت"))

async def sales_stats_handler(update: Update, context):
    """Handle sales statistics"""
    try:
        query = update.callback_query
        user = get_user(query.from_user.id)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # إحصائيات المبيعات العامة
        cursor.execute('''
            SELECT 
                COUNT(*) as total_sales,
                COALESCE(SUM(amount), 0) as total_revenue
            FROM transactions 
            WHERE type = 'card_purchase'
        ''')
        result = cursor.fetchone()
        total_sales, total_revenue = result if result else (0, 0)
        
        # مبيعات هذا الشهر
        cursor.execute('''
            SELECT 
                COUNT(*) as monthly_sales,
                COALESCE(SUM(amount), 0) as monthly_revenue
            FROM transactions 
            WHERE type = 'card_purchase' 
            AND DATE(created_at) >= DATE('now', 'start of month')
        ''')
        result = cursor.fetchone()
        monthly_sales, monthly_revenue = result if result else (0, 0)
        
        # مبيعات اليوم
        cursor.execute('''
            SELECT 
                COUNT(*) as daily_sales,
                COALESCE(SUM(amount), 0) as daily_revenue
            FROM transactions 
            WHERE type = 'card_purchase' 
            AND DATE(created_at) = DATE('now')
        ''')
        result = cursor.fetchone()
        daily_sales, daily_revenue = result if result else (0, 0)
        
        # أفضل الشبكات مبيعاً (تقديري)
        cursor.execute('''
            SELECT n.name, n.provider, COUNT(t.id) as sales_count, SUM(t.amount) as network_revenue
            FROM transactions t
            JOIN users u ON t.to_user = u.id
            JOIN networks n ON u.id = n.supplier_id
            WHERE t.type = 'card_purchase'
            GROUP BY n.id, n.name, n.provider
            ORDER BY sales_count DESC
            LIMIT 5
        ''')
        top_networks = cursor.fetchall()
        
        conn.close()
        
        # حساب المتوسطات
        avg_daily = monthly_revenue / 30 if monthly_revenue else 0
        avg_per_sale = total_revenue / total_sales if total_sales else 0
        
        stats_text = f"""
📈 **إحصائيات المبيعات العامة** 📈

👤 **{user['full_name']}**

📊 **إجمالي المبيعات:**
🛒 إجمالي المبيعات: **{total_sales:,}** عملية
💰 إجمالي الإيرادات: **{total_revenue:,.2f}** ريال
💳 متوسط قيمة البيع: **{avg_per_sale:,.2f}** ريال

📅 **مبيعات هذا الشهر:**
🛒 عدد المبيعات: **{monthly_sales:,}** عملية
💰 إيرادات الشهر: **{monthly_revenue:,.2f}** ريال
📈 متوسط يومي: **{avg_daily:,.2f}** ريال

📅 **مبيعات اليوم:**
🛒 مبيعات اليوم: **{daily_sales:,}** عملية
💰 إيرادات اليوم: **{daily_revenue:,.2f}** ريال

🏆 **أفضل الشبكات مبيعاً:**
"""
        
        if top_networks:
            for i, network in enumerate(top_networks, 1):
                name, provider, sales_count, revenue = network
                stats_text += f"{i}️⃣ **{name}** ({provider}) - {sales_count} مبيعة\n"
        else:
            stats_text += "لا توجد بيانات مبيعات بعد"
        
        keyboard = [
            [InlineKeyboardButton('📊 تقارير الكروت', callback_data='cards_reports')],
            [InlineKeyboardButton('🏪 لوحة المزود', callback_data='supplier_panel'),
             InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
        ]
        
        await query.edit_message_text(stats_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in sales stats handler: {e}")
        await query.edit_message_text(ErrorMessages.report_error("إحصائيات المبيعات"))

async def upload_history_handler(update: Update, context):
    """Handle upload history"""
    try:
        query = update.callback_query
        user = get_user(query.from_user.id)
        
        # الحصول على سجل الرفع
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT filename, upload_status, total_cards, successful_cards, 
                   failed_cards, created_at
            FROM card_upload_batches 
            WHERE supplier_id = ?
            ORDER BY created_at DESC
            LIMIT 10
        ''', (user['id'],))
        
        uploads = cursor.fetchall()
        conn.close()
        
        history_text = f"""
📋 **سجل رفع الكروت** 📋

👤 **{user['full_name']}**

📊 **آخر عمليات الرفع:**
"""
        
        if uploads:
            for upload in uploads:
                status_emoji = {"processing": "⏳", "completed": "✅", "completed_with_errors": "⚠️", "failed": "❌"}
                status = status_emoji.get(upload['upload_status'], "❓")
                
                history_text += f"""
{status} **{upload['filename'] or 'ملف مجهول'}**
📊 المجموع: {upload['total_cards']} | ✅ نجح: {upload['successful_cards']} | ❌ فشل: {upload['failed_cards']}
📅 التاريخ: {upload['created_at'][:16] if upload['created_at'] else 'غير محدد'}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        else:
            history_text += """
❌ **لا توجد عمليات رفع سابقة**

💡 يمكنك رفع أول ملف كروت باستخدام زر "رفع كروت" من لوحة المزود.
"""
        
        keyboard = [
            [InlineKeyboardButton('📤 رفع كروت جديدة', callback_data='upload_cards')],
            [InlineKeyboardButton('🏪 لوحة المزود', callback_data='supplier_panel'),
             InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
        ]
        
        await query.edit_message_text(history_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in upload history handler: {e}")
        await query.edit_message_text(ErrorMessages.upload_error("عرض سجل الرفع"))

async def supplier_settings_handler(update: Update, context):
    """Handle supplier settings"""
    try:
        query = update.callback_query
        user = get_user(query.from_user.id)
        
        supplier_code = get_or_create_supplier_code(user['id'])
        
        # الحصول على معلومات المزود التفصيلية
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # إحصائيات المزود
        cursor.execute('''
            SELECT COUNT(*) FROM networks WHERE created_by = ? AND is_active = 1
        ''', (user['id'],))
        active_networks = cursor.fetchone()[0] or 0
        
        cursor.execute('''
            SELECT COUNT(*) FROM cards c
            JOIN card_categories cc ON c.category_id = cc.id
            JOIN networks n ON cc.network_id = n.id
            WHERE n.created_by = ? AND c.is_sold = 0
        ''', (user['id'],))
        available_cards = cursor.fetchone()[0] or 0
        
        cursor.execute('''
            SELECT COUNT(*) FROM cards c
            JOIN card_categories cc ON c.category_id = cc.id
            JOIN networks n ON cc.network_id = n.id
            WHERE n.created_by = ? AND c.is_sold = 1
        ''', (user['id'],))
        sold_cards = cursor.fetchone()[0] or 0
        
        conn.close()
        
        # تحديد نوع الحساب
        role_names = {
            'user': 'عميل', 
            'supplier': 'مزود', 
            'admin': 'مشرف', 
            'super_admin': 'مشرف أعلى'
        }
        
        settings_text = f"""
⚙️ **إعدادات المزود المتقدمة** ⚙️

👤 **{user['full_name']}**
🆔 **معرف المزود: `{supplier_code}`**

📊 **إحصائيات سريعة:**
🌐 الشبكات النشطة: **{active_networks}** شبكة
📦 الكروت المتاحة: **{available_cards}** كرت
✅ الكروت المباعة: **{sold_cards}** كرت

⚙️ **الإعدادات المتاحة:**

🏢 **معلومات المزود:**
• اسم الشركة: {user['full_name'] if user['full_name'] else 'غير محدد'}
• رقم الهاتف: {user['phone'] if user['phone'] else 'غير محدد'}
• البريد الإلكتروني: غير محدد
• العنوان: غير محدد

🔔 **إعدادات الإشعارات:**
• إشعارات المبيعات: مفعل ✅
• إشعارات نفاد المخزون: مفعل ✅
• إشعارات الطلبات الجديدة: مفعل ✅
• التقارير اليومية: مفعل ✅

💰 **إعدادات العمولات:**
• عمولة المبيعات: 5% (افتراضي)
• نظام الدفع: شهري
• طريقة الاستلام: تحويل مباشر

🔧 **إعدادات المزود:**
• حالة الحساب: نشط ✅
• مستوى التحقق: مؤكد ✅
• آخر تحديث: اليوم
"""
        
        keyboard = [
            [InlineKeyboardButton('🔔 إعدادات الإشعارات', callback_data='supplier_notifications'),
             InlineKeyboardButton('💰 إعدادات العمولات', callback_data='supplier_commissions')],
            [InlineKeyboardButton('🏢 تحديث معلومات الشركة', callback_data='update_company_info'),
             InlineKeyboardButton('🔐 إعدادات الأمان', callback_data='supplier_security')],
            [InlineKeyboardButton('🏪 لوحة المزود', callback_data='supplier_panel'),
             InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
        ]
        
        await query.edit_message_text(settings_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in supplier settings handler: {e}")
        await query.edit_message_text(ErrorMessages.supplier_error("عرض الإعدادات"))

async def search_networks_handler(update: Update, context: CallbackContext):
    """Handle network search functionality - interactive search"""
    try:
        # دعم كل من الأوامر المباشرة والأزرار
        if hasattr(update, 'callback_query') and update.callback_query:
            query = update.callback_query
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
        
        search_text = f"""
🔍 **البحث في الشبكات** 🔍

👤 **{user['full_name']}**
💰 رصيدك: **{user['balance']:,.2f}** ريال

🎯 **طرق البحث المتاحة:**

📱 **البحث السريع:**
• ابحث بالاسم أو المزود
• فلترة حسب المدينة
• ترتيب حسب السعر

🏷️ **البحث حسب النوع:**
• شبكات المحمول
• شبكات المنزل
• جميع الشبكات

💰 **البحث حسب السعر:**
• كروت رخيصة (أقل من 50 ريال)
• كروت متوسطة (50-200 ريال)  
• كروت مكلفة (أكثر من 200 ريال)
"""
        
        keyboard = [
            [InlineKeyboardButton('📱 شبكات المحمول', callback_data='search_by_mobile'),
             InlineKeyboardButton('🏠 شبكات المنزل', callback_data='search_by_home')],
            [InlineKeyboardButton('💰 حسب السعر', callback_data='search_by_price'),
             InlineKeyboardButton('🏙️ حسب المدينة', callback_data='search_by_city')],
            [InlineKeyboardButton('📊 جميع الشبكات', callback_data='view_all_networks'),
             InlineKeyboardButton('🔍 بحث متقدم', callback_data='advanced_search')],
            [InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
        ]
        
        if is_callback:
            await update.callback_query.edit_message_text(search_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        else:
            await update.message.reply_text(search_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in search networks handler: {e}")
        error_msg = ErrorMessages.search_error("البحث في الشبكات")
        if hasattr(update, 'callback_query') and update.callback_query:
            await update.callback_query.edit_message_text(error_msg)
        else:
            await update.message.reply_text(error_msg)

async def show_network_details(update: Update, context: CallbackContext, network_id: str):
    """Show detailed information about a specific network"""
    try:
        query = update.callback_query
        user = get_user(query.from_user.id)
        
        # الحصول على تفاصيل الشبكة الكاملة
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT n.name, n.provider, n.location, n.city, n.created_at, n.is_active,
                   COUNT(nc.id) as total_cards,
                   COUNT(CASE WHEN nc.is_sold = 0 THEN 1 END) as available_cards,
                   COUNT(CASE WHEN nc.is_sold = 1 THEN 1 END) as sold_cards,
                   MIN(nc.card_value) as min_price, MAX(nc.card_value) as max_price,
                   u.full_name as supplier_name
            FROM networks n
            LEFT JOIN network_cards nc ON n.id = nc.network_id
            LEFT JOIN users u ON n.supplier_id = u.id
            WHERE n.id = ?
            GROUP BY n.id
        ''', (network_id,))
        
        network = cursor.fetchone()
        conn.close()
        
        if not network:
            await query.edit_message_text(
                "❌ الشبكة غير موجودة",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton('🔍 البحث في الشبكات', callback_data='search_networks')]
                ])
            )
            return
        
        (name, provider, location, city, created_at, is_active, total_cards, 
         available_cards, sold_cards, min_price, max_price, supplier_name) = network
        
        # تنسيق البيانات
        location_full = f"{location}, {city}" if location and city else (location or city or "غير محدد")
        price_range = f"{min_price:,.0f} - {max_price:,.0f}" if min_price != max_price else f"{min_price:,.0f}" if min_price else "غير محدد"
        created_date = created_at[:10] if created_at else "غير محدد"
        status = "✅ نشطة" if is_active else "⏸️ متوقفة"
        
        details_text = f"""
📶 **تفاصيل الشبكة** 📶

🌐 **{name}**
👤 **المزود:** {provider}
🏙️ **الموقع:** {location_full}
📅 **تاريخ الإنشاء:** {created_date}
📊 **الحالة:** {status}

👨‍💼 **بيانات المزود:**
👤 الاسم: {supplier_name or 'غير محدد'}

📊 **إحصائيات الكروت:**
📦 إجمالي الكروت: **{total_cards or 0}**
✅ متاح للبيع: **{available_cards or 0}**
✅ تم بيعه: **{sold_cards or 0}**
💰 نطاق الأسعار: **{price_range}** ريال

📈 **معدل الأداء:**
📊 نسبة المبيعات: **{(sold_cards / total_cards * 100) if total_cards > 0 else 0:.1f}%**
"""
        
        keyboard = []
        
        # إضافة زر الشراء إذا كانت الشبكة نشطة ولديها كروت
        if is_active and available_cards > 0:
            keyboard.append([InlineKeyboardButton('🛒 شراء من هذه الشبكة', callback_data=f'buy_from_network_{network_id}')])
        
        keyboard.extend([
            [InlineKeyboardButton('🔍 البحث في الشبكات', callback_data='search_networks'),
             InlineKeyboardButton('📊 جميع الشبكات', callback_data='view_networks')],
            [InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
        ])
        
        await query.edit_message_text(details_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in show network details: {e}")
        await query.edit_message_text(ErrorMessages.network_error("عرض تفاصيل الشبكة"))

async def add_network_handler(update: Update, context: CallbackContext):
    """Handle add network"""
    try:
        query = update.callback_query
        user = get_user(query.from_user.id)
        
        if user['role'] != 'supplier' or not user['is_active']:
            await query.edit_message_text(f"{EMOJIS['error']} يجب أن تكون مزود مفعل لإضافة شبكة.")
            return
        
        # التحقق من عدم وجود شبكة مسبقاً
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM networks WHERE supplier_id = ?', (user['id'],))
        result = cursor.fetchone()
        existing_networks = result[0] if result else 0
        conn.close()
        
        if existing_networks > 0:
            await query.edit_message_text(
                f"""
❌ **لديك شبكة مسجلة بالفعل**

💡 **ملاحظة:** يُسمح بشبكة واحدة فقط لكل مزود
🔧 يمكنك إدارة شبكتك الحالية من "إدارة الشبكات"
""",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton('📶 إدارة الشبكات', callback_data='manage_networks')],
                    [InlineKeyboardButton('🏪 لوحة المزود', callback_data='supplier_panel')]
                ])
            )
            return
        
        # بدء عملية إضافة شبكة جديدة
        context.user_data['network_step'] = 'name'
        
        add_text = f"""
➕ **إضافة شبكة جديدة** ➕

👤 **{user['full_name']}**

📋 **خطوات إضافة الشبكة:**
1️⃣ اسم الشبكة
2️⃣ اسم مزود الخدمة  
3️⃣ الموقع/المدينة

💡 **يرجى كتابة اسم الشبكة:**

مثال: شبكة يمن نت، شبكة عدن نت، شبكة تعز الحديثة
"""
        
        keyboard = [
            [InlineKeyboardButton('❌ إلغاء', callback_data='manage_networks')]
        ]
        
        await query.edit_message_text(add_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in add network handler: {e}")
        await query.edit_message_text(ErrorMessages.supplier_error("إضافة شبكة جديدة"))