#!/usr/bin/env python3
"""
Notification and Report Handlers Module
معالجات الإشعارات والتقارير
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext

# Import utilities
from bot_modules.utils import get_user
from bot_modules.database import get_db_connection
from bot_modules.config import EMOJIS
from bot_modules.enhanced_error_messages import ErrorMessages

logger = logging.getLogger(__name__)

async def my_notifications_handler(update: Update, context):
    """Show user notifications"""
    try:
        query = update.callback_query
        user = get_user(query.from_user.id)
        
        # الحصول على الإشعارات
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT title, message, created_at, is_read 
            FROM smart_notifications 
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT 10
        ''', (user['id'],))
        
        notifications = cursor.fetchall()
        
        cursor.execute('''
            SELECT COUNT(*) as unread_count 
            FROM smart_notifications 
            WHERE user_id = ? AND is_read = 0
        ''', (user['id'],))
        
        result = cursor.fetchone()
        unread_count = result['unread_count'] if result else 0
        conn.close()
        
        notif_text = f"""
🔔 **إشعاراتي وتنبيهاتي** 🔔

👤 **{user['full_name']}**
📬 إشعارات غير مقروءة: **{unread_count}**

📋 **آخر الإشعارات:**
"""
        
        if notifications:
            for notification in notifications:
                title, message, created_at, is_read = notification
                read_icon = "📖" if is_read else "📩"
                date_str = created_at[:10] if created_at else "غير محدد"
                
                notif_text += f"""
{read_icon} **{title}**
📝 {message[:50]}{'...' if len(message) > 50 else ''}
📅 {date_str}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        else:
            notif_text += """
❌ **لا توجد إشعارات**

💡 ستظهر هنا الإشعارات المهمة مثل:
• تأكيد العمليات المالية
• تحديثات النظام
• عروض وخصومات جديدة
• تنبيهات أمنية
"""
        
        keyboard = [
            [InlineKeyboardButton('🔔 تحديد الكل كمقروء', callback_data='mark_all_read')],
            [InlineKeyboardButton('💳 محفظتي', callback_data='enhanced_wallet'),
             InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
        ]
        
        await query.edit_message_text(notif_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in my notifications handler: {e}")
        await query.edit_message_text(ErrorMessages.notification_error("عرض الإشعارات"))

async def personal_reports_handler(update: Update, context):
    """Handle personal reports"""
    try:
        query = update.callback_query
        user = get_user(query.from_user.id)
        
        # الحصول على إحصائيات المستخدم
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # إحصائيات شاملة
        cursor.execute('''
            SELECT 
                COUNT(*) as total_trans,
                COALESCE(SUM(CASE WHEN from_user = ? THEN amount END), 0) as sent_amount,
                COALESCE(SUM(CASE WHEN to_user = ? THEN amount END), 0) as received_amount,
                COUNT(CASE WHEN from_user = ? THEN 1 END) as sent_count,
                COUNT(CASE WHEN to_user = ? THEN 1 END) as received_count
            FROM transactions 
            WHERE from_user = ? OR to_user = ?
        ''', (user['id'], user['id'], user['id'], user['id'], user['id'], user['id']))
        
        stats = cursor.fetchone()
        if stats:
            total_trans, sent_amount, received_amount, sent_count, received_count = stats
        else:
            total_trans, sent_amount, received_amount, sent_count, received_count = 0, 0, 0, 0, 0
        
        # إحصائيات هذا الشهر
        cursor.execute('''
            SELECT 
                COUNT(*) as monthly_transactions,
                COALESCE(SUM(amount), 0) as monthly_amount
            FROM transactions 
            WHERE (from_user = ? OR to_user = ?) 
            AND DATE(created_at) >= DATE('now', 'start of month')
        ''', (user['id'], user['id']))
        
        monthly_stats = cursor.fetchone()
        if monthly_stats:
            monthly_trans, monthly_amount = monthly_stats
        else:
            monthly_trans, monthly_amount = 0, 0
        
        conn.close()
        
        reports_text = f"""
📊 **تقاريري الشخصية** 📊

👤 **{user['full_name']}**
💳 محفظتك: **{user['wallet_number']}**
💰 رصيدك الحالي: **{user['balance']:,.2f}** ريال

📈 **إجمالي النشاط:**
🔄 إجمالي المعاملات: **{total_trans}** معاملة
📤 معاملات مرسلة: **{sent_count}** معاملة
📥 معاملات مستلمة: **{received_count}** معاملة

💰 **الحركة المالية:**
📤 إجمالي المرسل: **{sent_amount:,.2f}** ريال
📥 إجمالي المستلم: **{received_amount:,.2f}** ريال
📊 الفرق الصافي: **{received_amount - sent_amount:,.2f}** ريال

📅 **نشاط هذا الشهر:**
🔄 معاملات الشهر: **{monthly_trans}** معاملة
💰 حركة مالية: **{monthly_amount:,.2f}** ريال

💡 **نصائح لتحسين نشاطك:**
• استخدم ميزة الإحالات لكسب عمولات
• تابع العروض والخصومات الجديدة
• حافظ على أمان الحساب
• تفاعل مع العروض الجديدة
"""
        
        keyboard = [
            [InlineKeyboardButton('📊 تقاريري الشخصية', callback_data='personal_reports'),
             InlineKeyboardButton('📈 إحصائيات المحفظة', callback_data='wallet_stats')],
            [InlineKeyboardButton('🔔 إشعاراتي', callback_data='my_notifications')],
            [InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
        ]
        
        await query.edit_message_text(reports_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in personal reports handler: {e}")
        await query.edit_message_text(ErrorMessages.report_error("الشخصية"))

async def transaction_details_handler(update: Update, context):
    """Handle transaction details"""
    try:
        query = update.callback_query
        user = get_user(query.from_user.id)
        
        # الحصول على معاملات المستخدم
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # آخر المعاملات
        cursor.execute('''
            SELECT from_user, to_user, amount, type, description, created_at
            FROM transactions 
            WHERE from_user = ? OR to_user = ?
            ORDER BY created_at DESC
            LIMIT 10
        ''', (user['id'], user['id']))
        transactions = cursor.fetchall()
        
        # إحصائيات المعاملات
        cursor.execute('''
            SELECT 
                COUNT(CASE WHEN from_user = ? THEN 1 END) as sent_count,
                COUNT(CASE WHEN to_user = ? THEN 1 END) as received_count,
                COALESCE(SUM(CASE WHEN from_user = ? THEN amount END), 0) as sent_amount,
                COALESCE(SUM(CASE WHEN to_user = ? THEN amount END), 0) as received_amount
            FROM transactions
            WHERE from_user = ? OR to_user = ?
        ''', (user['id'], user['id'], user['id'], user['id'], user['id'], user['id']))
        stats = cursor.fetchone()
        if stats:
            sent_count, received_count, sent_amount, received_amount = stats
        else:
            sent_count, received_count, sent_amount, received_amount = 0, 0, 0, 0
        
        conn.close()
        
        details_text = f"""
📊 **تفاصيل المعاملات** 📊

👤 **{user['full_name']}**
💰 رصيدك: **{user['balance']:,.2f}** ريال

📈 **ملخص المعاملات:**
📤 معاملات مرسلة: **{sent_count}** ({sent_amount:,.2f} ريال)
📥 معاملات مستلمة: **{received_count}** ({received_amount:,.2f} ريال)
📊 إجمالي المعاملات: **{sent_count + received_count}**

📋 **آخر المعاملات:**
"""
        
        if transactions:
            for transaction in transactions:
                from_user_id, to_user_id, amount, trans_type, description, created_at = transaction
                
                # تحديد اتجاه المعاملة
                if from_user_id == user['id']:
                    direction = "📤 أرسلت"
                    color = "🔻"
                else:
                    direction = "📥 استلمت"
                    color = "🔺"
                
                # رموز أنواع المعاملات
                type_icons = {
                    'card_purchase': '🛒',
                    'transfer': '💸',
                    'coupon_redeem': '🎟️',
                    'commission': '💼',
                    'admin_profit': '👑',
                    'transfer_fee': 'رسوم تحويل'
                }
                
                type_names = {
                    'card_purchase': 'شراء كرت',
                    'transfer': 'تحويل رصيد',
                    'coupon_redeem': 'شحن بكوبون',
                    'commission': 'عمولة إحالة',
                    'admin_profit': 'حصة إدارية',
                    'transfer_fee': 'رسوم تحويل'
                }
                
                type_icon = type_icons.get(trans_type, '💼')
                type_name = type_names.get(trans_type, 'معاملة')
                
                # تنسيق التاريخ
                date_formatted = created_at[:16] if created_at else 'غير محدد'
                
                details_text += f"""
{type_icon} **{type_name}**
{direction} {color} **{amount:,.2f}** ريال
📅 {date_formatted}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        else:
            details_text += """
❌ **لا توجد معاملات**

💡 ابدأ أول معاملة عبر:
• شراء كروت إنترنت
• تحويل رصيد لصديق
• شحن رصيدك بكوبون
"""
        
        keyboard = [
            [InlineKeyboardButton(f'💳 محفظتي', callback_data='enhanced_wallet')],
            [InlineKeyboardButton(f'{EMOJIS["home"]} القائمة الرئيسية', callback_data='main_menu')]
        ]
        
        await query.edit_message_text(details_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in transaction details handler: {e}")
        await query.edit_message_text(ErrorMessages.custom_error(
            "تفاصيل المعاملات",
            "فشل في تحميل بيانات المعاملات",
            "تحقق من الاتصال وحاول مرة أخرى",
            "TRANSACTION_DETAILS_ERROR"
        ))

async def promotions_handler(update: Update, context: CallbackContext):
    """Handle promotions and offers"""
    try:
        query = update.callback_query
        user = get_user(query.from_user.id)
        
        promotions_text = f"""
🎁 **العروض والخصومات** 🎁

👤 **{user['full_name']}**

🔥 **العروض النشطة:**

🎯 **عرض الإحالات:**
• احصل على 5% عمولة من كل مشترى لأصدقائك
• لا يوجد حد أقصى للعمولات
• العمولة تُضاف فوراً لرصيدك

💳 **عروض الكروت:**
• خصومات موسمية على كروت مختارة
• عروض خاصة للعملاء الدائمين
• باقات مجمعة بأسعار مخفضة

🎟️ **كوبونات الشحن:**
• كوبونات مجانية للمستخدمين النشطين
• مكافآت الولاء الشهرية
• جوائز المسابقات

📱 **كيفية الاستفادة:**
• تابع الإشعارات للعروض الجديدة
• شارك رابط الإحالة مع الأصدقاء
• استخدم المنصة بانتظام للحصول على مكافآت

🕐 **صالح حتى:** نهاية الشهر الحالي
"""
        
        keyboard = [
            [InlineKeyboardButton('👥 رابط الإحالة', callback_data='referral_stats'),
             InlineKeyboardButton('🛒 تصفح العروض', callback_data='browse_offers')],
            [InlineKeyboardButton('🔔 إشعاراتي', callback_data='my_notifications')],
            [InlineKeyboardButton('💳 محفظتي', callback_data='enhanced_wallet'),
             InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
        ]
        
        await query.edit_message_text(promotions_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in promotions handler: {e}")
        await query.edit_message_text(ErrorMessages.custom_error(
            "العروض والخصومات",
            "فشل في تحميل العروض المتاحة",
            "تحقق من الاتصال وحاول مرة أخرى",
            "PROMOTIONS_ERROR"
        ))

async def help_handler(update: Update, context):
    """Show help information"""
    try:
        query = update.callback_query if update.callback_query else None
        
        help_text = f"""
❓ **المساعدة والدعم** ❓

🏠 **الوظائف الأساسية:**
💳 **المحفظة:** عرض الرصيد والمعاملات
🛒 **الشراء:** شراء كروت من الشبكات المتاحة
💸 **التحويل:** إرسال رصيد للأصدقاء (مجاناً)
🎟️ **الشحن:** شحن الرصيد بالكوبونات

👥 **نظام الإحالات:**
• احصل على 5% عمولة من مشتريات أصدقائك
• شارك رابط الإحالة الخاص بك
• اكسب بدون حدود!

🏪 **للمزودين:**
📶 **الشبكات:** إدارة شبكة واحدة لكل مزود
📤 **رفع الكروت:** رفع ملفات الكروت بسهولة
💰 **السحب:** طلب سحب الأرباح كل جمعة
🔗 **المشاركة:** روابط مباشرة لشبكتك

👑 **للمشرفين:**
👥 **إدارة المستخدمين:** تفعيل وإدارة الحسابات
💰 **إدارة الأرصدة:** إضافة وإدارة الأرصدة
📊 **التقارير:** تقارير شاملة عن النشاط
💰 **طلبات السحب:** موافقة على طلبات المزودين

📞 **الدعم الفني:**
• متاح 24/7 للمساعدة
• استجابة سريعة للاستفسارات
• حل المشاكل التقنية

🔒 **الأمان:**
• حماية كاملة للبيانات
• تشفير المعلومات الحساسة
• مراقبة العمليات المشبوهة
"""
        
        keyboard = [
            [InlineKeyboardButton('📞 تواصل مع الدعم', callback_data='contact_support'),
             InlineKeyboardButton('🔔 الإشعارات', callback_data='my_notifications')],
            [InlineKeyboardButton('💳 محفظتي', callback_data='enhanced_wallet'),
             InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
        ]
        
        if query:
            await query.edit_message_text(help_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        else:
            await update.message.reply_text(help_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in help handler: {e}")
        error_msg = ErrorMessages.custom_error(
            "المساعدة والدعم",
            "فشل في تحميل معلومات المساعدة",
            "حاول مرة أخرى أو تواصل مع الدعم",
            "HELP_ERROR"
        )
        if query:
            await query.edit_message_text(error_msg)
        else:
            await update.message.reply_text(error_msg)