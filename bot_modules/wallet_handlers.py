#!/usr/bin/env python3
"""
Wallet and Transfer Handlers Module
معالجات المحفظة والتحويلات
"""

import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext

# Import utilities
from bot_modules.utils import get_user, recalc_and_set_user_balance
from bot_modules.database import get_db_connection
from bot_modules.config import EMOJIS
from bot_modules.enhanced_error_messages import ErrorMessages, wallet_error

logger = logging.getLogger(__name__)

async def transfer_handler(update: Update, context):
    """Handle transfer request"""
    try:
        query = update.callback_query
        user = get_user(query.from_user.id)
        
        transfer_text = f"""
💸 **تحويل رصيد لصديق** 💸

👤 **{user['full_name']}**
💰 رصيدك: **{user['balance']:.2f}** ريال

📋 **تعليمات التحويل:**
1️⃣ أدخل رقم محفظة المستلم (9 أرقام)
2️⃣ أدخل المبلغ المراد تحويله
3️⃣ تأكيد العملية

💡 **للتحويل السريع:**
• استخدم زر "🔍 البحث عن مستخدم" أدناه
• ابحث بالاسم أو رقم المحفظة أو الهاتف
• أدخل المبلغ المطلوب تحويله
• تأكيد العملية بأمان

🔒 **ضمانات الأمان:**
• تأكيد مزدوج قبل التحويل
• إشعار فوري للطرفين
• سجل كامل للمعاملة
"""
        
        keyboard = [
            [InlineKeyboardButton(f'🔍 البحث عن مستخدم', callback_data='search_user')],
            [InlineKeyboardButton(f'📋 آخر التحويلات', callback_data='transfer_history')],
            [InlineKeyboardButton(f'{EMOJIS["home"]} القائمة الرئيسية', callback_data='main_menu')]
        ]
        
        await query.edit_message_text(transfer_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in transfer handler: {e}")
        await query.edit_message_text(wallet_error("عرض صفحة التحويل"))

async def wallet_stats_handler(update: Update, context):
    """Handle wallet statistics"""
    try:
        query = update.callback_query
        user = get_user(query.from_user.id)
        
        # الحصول على إحصائيات المحفظة التفصيلية
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # إحصائيات هذا الشهر
        cursor.execute('''
            SELECT 
                COUNT(CASE WHEN from_user = ? THEN 1 END) as sent_month,
                COUNT(CASE WHEN to_user = ? THEN 1 END) as received_month,
                COALESCE(SUM(CASE WHEN from_user = ? THEN amount END), 0) as spent_month,
                COALESCE(SUM(CASE WHEN to_user = ? THEN amount END), 0) as earned_month
            FROM transactions 
            WHERE (from_user = ? OR to_user = ?) 
            AND DATE(created_at) >= DATE('now', 'start of month')
        ''', (user['id'], user['id'], user['id'], user['id'], user['id'], user['id']))
        monthly_stats = cursor.fetchone()
        
        # إحصائيات هذا الأسبوع
        cursor.execute('''
            SELECT 
                COUNT(*) as weekly_transactions,
                COALESCE(SUM(amount), 0) as weekly_change
            FROM transactions 
            WHERE (from_user = ? OR to_user = ?) 
            AND DATE(created_at) >= DATE('now', '-7 days')
        ''', (user['id'], user['id'], user['id']))
        weekly_stats = cursor.fetchone()
        
        # أكثر أنواع المعاملات
        cursor.execute('''
            SELECT type, COUNT(*) as count, SUM(amount) as total_amount
            FROM transactions
            WHERE from_user = ? OR to_user = ?
            GROUP BY type
            ORDER BY count DESC
            LIMIT 3
        ''', (user['id'], user['id']))
        top_transaction_types = cursor.fetchall()
        
        conn.close()
        
        if monthly_stats:
            sent_month, received_month, spent_month, earned_month = monthly_stats
        else:
            sent_month, received_month, spent_month, earned_month = 0, 0, 0, 0
        
        if weekly_stats:
            weekly_transactions, weekly_change = weekly_stats
        else:
            weekly_transactions, weekly_change = 0, 0
        
        # حساب متوسط الإنفاق اليومي
        daily_avg = spent_month / 30 if spent_month else 0
        
        stats_text = f"""
📈 **إحصائيات المحفظة المتقدمة** 📈

👤 **{user['full_name']}**
💰 رصيدك الحالي: **{user['balance']:,.2f}** ريال

📅 **إحصائيات هذا الشهر:**
📤 معاملات مرسلة: **{sent_month}** معاملة
📥 معاملات مستلمة: **{received_month}** معاملة
💸 إجمالي الإنفاق: **{spent_month:,.2f}** ريال
💰 إجمالي الإيرادات: **{earned_month:,.2f}** ريال

📊 **إحصائيات هذا الأسبوع:**
🔄 المعاملات: **{weekly_transactions}** معاملة
💹 التغيير المالي: **{weekly_change:,.2f}** ريال

📈 **تحليل الإنفاق:**
💳 متوسط الإنفاق اليومي: **{daily_avg:,.2f}** ريال
📊 صافي التغيير الشهري: **{earned_month - spent_month:,.2f}** ريال

🏆 **أكثر أنواع المعاملات:**
"""
        
        if top_transaction_types:
            for trans_type, count, total in top_transaction_types:
                type_names = {
                    'card_purchase': 'شراء كروت',
                    'transfer': 'تحويلات',
                    'coupon_redeem': 'شحن بكوبون',
                    'commission': 'عمولات'
                }.get(trans_type, trans_type)
                
                stats_text += f"• {type_name}: **{count}** معاملة ({total:,.2f} ريال)\n"
        else:
            stats_text += "• لا توجد معاملات بعد\n"
        
        keyboard = [
            [InlineKeyboardButton(f'💳 محفظتي', callback_data='enhanced_wallet')],
            [InlineKeyboardButton(f'{EMOJIS["home"]} القائمة الرئيسية', callback_data='main_menu')]
        ]
        
        await query.edit_message_text(stats_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in wallet stats handler: {e}")
        await query.edit_message_text(wallet_error("حساب إحصائيات المحفظة"))

async def transfer_to_friend_handler(update: Update, context: CallbackContext):
    """معالج تحويل الرصيد للأصدقاء"""
    try:
        query = update.callback_query
        user = get_user(query.from_user.id)
        
        if not user:
            await query.edit_message_text(f"{EMOJIS['error']} يرجى التسجيل أولاً /start")
            return
        
        transfer_text = f"""
💸 **تحويل رصيد** 💸

👤 **{user['full_name']}**
💰 رصيدك الحالي: **{user['balance']:,.2f}** ريال
💳 محفظتك: **{user['wallet_number']}**

🔍 **البحث عن المستلم:**
يمكنك البحث بأي من الطرق التالية:
• رقم المحفظة (9 أرقام)
• رقم الهاتف
• اسم المستخدم

💡 **نصائح:**
• تأكد من صحة البيانات قبل التحويل
• التحويلات مجانية بدون رسوم
• يتم الإشعار فوراً للطرفين
"""
        
        keyboard = [
            [InlineKeyboardButton('🔍 البحث عن مستخدم', callback_data='search_user')],
            [InlineKeyboardButton('📋 سجل التحويلات', callback_data='transfer_history')],
            [InlineKeyboardButton('💳 محفظتي', callback_data='enhanced_wallet'),
             InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
        ]
        
        await query.edit_message_text(transfer_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in transfer to friend handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في عرض صفحة التحويل")

async def transfer_history_handler(update: Update, context: CallbackContext):
    """معالج سجل التحويلات"""
    try:
        query = update.callback_query
        user = get_user(query.from_user.id)
        
        # الحصول على آخر التحويلات
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT from_user, to_user, amount, description, created_at
            FROM transactions 
            WHERE (from_user = ? OR to_user = ?) AND type = 'transfer'
            ORDER BY created_at DESC
            LIMIT 10
        ''', (user['id'], user['id']))
        
        transfers = cursor.fetchall()
        
        # إحصائيات التحويلات
        cursor.execute('''
            SELECT 
                COUNT(*) as total_count,
                COALESCE(SUM(CASE WHEN from_user = ? THEN amount END), 0) as sent_total,
                COALESCE(SUM(CASE WHEN to_user = ? THEN amount END), 0) as received_total
            FROM transactions 
            WHERE from_user = ? OR to_user = ?
        ''', (user['id'], user['id'], user['id'], user['id']))
        
        stats = cursor.fetchone()
        if stats:
            total_count, sent_amount, received_amount = stats
        else:
            total_count, sent_amount, received_amount = 0, 0, 0
        
        conn.close()
        
        # حساب التقييم (محذوف)
        rating_data = {'total_ratings': 0, 'average_rating': 0.0}
        
        history_text = f"""
📋 **سجل التحويلات** 📋

👤 **{user['full_name']}**
💳 محفظتك: **{user['wallet_number']}**

📊 **إجمالي التحويلات:**
🔄 عدد التحويلات: **{total_count}** معاملة
📤 إجمالي المرسل: **{sent_amount:,.2f}** ريال
📥 إجمالي المستلم: **{received_amount:,.2f}** ريال
📊 الفرق الصافي: **{received_amount - sent_amount:,.2f}** ريال

📋 **آخر التحويلات:**
"""
        
        if transfers:
            for transfer in transfers:
                from_user, to_user, amount, description, created_at = transfer
                
                if from_user == user['id']:
                    # تحويل مرسل
                    direction = "📤 أرسلت"
                    other_user_id = to_user
                else:
                    # تحويل مستلم
                    direction = "📥 استلمت"
                    other_user_id = from_user
                
                # الحصول على اسم المستخدم الآخر
                try:
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute('SELECT full_name FROM users WHERE id = ?', (other_user_id,))
                    other_user = cursor.fetchone()
                    other_name = other_user[0] if other_user else 'مستخدم محذوف'
                    conn.close()
                except:
                    other_name = 'غير محدد'
                
                date_str = created_at[:10] if created_at else 'غير محدد'
                
                history_text += f"""
{direction} **{amount:,.2f}** ريال
👤 {'إلى' if from_user == user['id'] else 'من'}: {other_name}
📅 التاريخ: {date_str}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        else:
            history_text += """
❌ **لا توجد تحويلات**

💡 يمكنك بدء أول تحويل لك باستخدام زر "تحويل رصيد" من المحفظة.
"""
        
        keyboard = [
            [InlineKeyboardButton('💸 تحويل جديد', callback_data='transfer_to_friend')],
            [InlineKeyboardButton('💳 محفظتي', callback_data='enhanced_wallet'),
             InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
        ]
        
        await query.edit_message_text(history_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in transfer history handler: {e}")
        await query.edit_message_text(wallet_error("عرض سجل التحويلات"))

async def recharge_balance_handler(update: Update, context: CallbackContext):
    """Handle balance recharge"""
    try:
        query = update.callback_query
        user = get_user(query.from_user.id)
        
        if not user:
            await query.edit_message_text(f"{EMOJIS['error']} يرجى التسجيل أولاً /start")
            return
        
        recharge_text = f"""
💳 **شحن الرصيد** 💳

👤 **{user['full_name']}**
💰 رصيدك الحالي: **{user['balance']:,.2f}** ريال
💳 محفظتك: **{user['wallet_number']}**

💡 **طرق شحن الرصيد:**

🎟️ **بالكوبونات:**
• احصل على كوبون شحن من الإدارة
• أدخل رمز الكوبون
• يتم إضافة الرصيد فوراً

📞 **التواصل مع الإدارة:**
• تواصل مع المشرف لشحن الرصيد
• حوّل المبلغ للحساب المحدد
• أرسل إثبات التحويل
• سيتم إضافة الرصيد خلال ساعات

🔒 **ضمانات الأمان:**
• جميع المعاملات محفوظة ومؤرخة
• إشعار فوري عند إضافة الرصيد
• دعم فني متاح 24/7
"""
        
        keyboard = [
            [InlineKeyboardButton('🎟️ شحن بكوبون', callback_data='redeem_coupon')],
            [InlineKeyboardButton('📞 تواصل مع الإدارة', callback_data='contact_admin')],
            [InlineKeyboardButton('💳 محفظتي', callback_data='enhanced_wallet')],
            [InlineKeyboardButton(f'{EMOJIS["home"]} القائمة الرئيسية', callback_data='main_menu')]
        ]
        
        await query.edit_message_text(recharge_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in recharge balance handler: {e}")
        await query.edit_message_text(wallet_error("شحن الرصيد"))

async def confirm_transfer_handler(update: Update, context: CallbackContext, confirmed: bool):
    """Handle transfer confirmation"""
    try:
        query = update.callback_query
        # تجنب خطأ Query is too old
        try:
            await query.answer()
        except Exception as e:
            if "too old" in str(e):
                logger.debug("Query too old, continuing with transfer")
            else:
                raise
        
        user = get_user(query.from_user.id)
        if not user:
            await query.edit_message_text(f"{EMOJIS['error']} يرجى التسجيل أولاً /start")
            return
        
        if not confirmed:
            # User cancelled the transfer
            context.user_data.clear()
            await query.edit_message_text(f"""
❌ **تم إلغاء التحويل**

العملية ألغيت بنجاح. لم يتم خصم أي مبلغ من رصيدك.

💰 رصيدك الحالي: **{user['balance']:,.2f}** ريال

💡 يمكنك استخدام /send_balance لبدء تحويل جديد
""", parse_mode='Markdown')
            return
        
        # User confirmed the transfer - execute it
        if not context.user_data.get('awaiting_transfer_confirmation'):
            await query.edit_message_text(f"{EMOJIS['error']} انتهت صلاحية العملية. يرجى البدء من جديد.")
            return
        
        # حماية ضد الضغط المتعدد
        if context.user_data.get('transfer_processing'):
            await query.answer("⏳ العملية قيد التنفيذ، يرجى الانتظار...", show_alert=True)
            return
        
        # تعيين حالة المعالجة
        context.user_data['transfer_processing'] = True
        
        # Get transfer details
        target_user_id = context.user_data.get('target_user_id')
        target_user_name = context.user_data.get('target_user_name')
        amount = context.user_data.get('transfer_amount')
        transfer_fee = 0.0  # FREE transfers
        
        if not all([target_user_id, amount]):
            await query.edit_message_text(f"{EMOJIS['error']} معلومات التحويل مفقودة. يرجى البدء من جديد.")
            return
        
        # Execute the transfer
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # بدء معاملة قاعدة البيانات
            cursor.execute('BEGIN IMMEDIATE')
            
            # Get target user details
            cursor.execute('SELECT * FROM users WHERE id = ?', (target_user_id,))
            target_user = cursor.fetchone()
            
            if not target_user:
                conn.rollback()
                conn.close()
                await query.edit_message_text(f"{EMOJIS['error']} المستخدم المستهدف غير موجود.")
                return
            
            # التحقق من الرصيد مرة أخيرة
            cursor.execute('SELECT balance FROM users WHERE id = ?', (user['id'],))
            current_balance_result = cursor.fetchone()
            if not current_balance_result or current_balance_result[0] < amount:
                conn.rollback()
                conn.close()
                await query.edit_message_text(f"{EMOJIS['error']} رصيدك غير كافي للتحويل.")
                return
            
            current_balance = current_balance_result[0]
            
            # تحديث الأرصدة مباشرة (أسرع من إعادة الحساب)
            cursor.execute('UPDATE users SET balance = balance - ? WHERE id = ?', (amount, user['id']))
            cursor.execute('UPDATE users SET balance = balance + ? WHERE id = ?', (amount, target_user_id))
            
            # إنشاء معاملة التحويل
            import uuid
            from datetime import datetime
            
            transfer_id = str(uuid.uuid4())
            cursor.execute('''
                INSERT INTO transactions 
                (id, from_user, to_user, amount, type, description, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (transfer_id, user['id'], target_user_id, amount, 'transfer', 'تحويل رصيد من صديق', datetime.now()))
            
            # الحصول على الأرصدة الجديدة
            cursor.execute('SELECT balance FROM users WHERE id = ?', (user['id'],))
            sender_new_balance = cursor.fetchone()[0]
            
            cursor.execute('SELECT balance FROM users WHERE id = ?', (target_user_id,))
            receiver_new_balance = cursor.fetchone()[0]
            
            # تأكيد المعاملة
            conn.commit()
            conn.close()
            
            # تسجيل القيد المحاسبي في الخلفية (لا نريد أن يبطئ التحويل)
            # تم تعطيل المحاسبة مؤقتاً لتحسين الأداء
            # يمكن تفعيلها لاحقاً إذا لزم الأمر
                
        except Exception as e:
            try:
                conn.rollback()
                conn.close()
            except:
                pass
            logger.error(f"Transfer failed: {e}")
            await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في التحويل. يرجى المحاولة مرة أخرى.")
            context.user_data.clear()
            return
        
        # Clear user state
        context.user_data.clear()
        
        # Send confirmation to sender
        success_text = f"""
✅ **تم إرسال الرصيد بنجاح!**

📤 **تفاصيل التحويل:**
👤 المستلم: **{target_user['full_name']}**
💰 المبلغ المرسل: **{amount:.2f}** ريال
🆓 التحويل: **مجاني بدون رسوم**
📊 إجمالي الخصم: **{amount:.2f}** ريال (بدون رسوم)

💵 **الأرصدة:**
🔻 رصيدك الجديد: **{sender_new_balance:.2f}** ريال
🔺 رصيد المستلم: **{receiver_new_balance:.2f}** ريال

🕐 **وقت التحويل:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

📱 سيتم إشعار المستلم فوراً
"""
        
        # تعديل الرسالة مع معالجة الأخطاء
        try:
            await query.edit_message_text(success_text, parse_mode='Markdown')
        except Exception as e:
            if "not modified" in str(e):
                # الرسالة لم تتغير، لا نحتاج لفعل شيء
                logger.debug("Message not modified, skipping edit")
            else:
                # إرسال رسالة جديدة بدلاً من التعديل
                await query.message.reply_text(success_text, parse_mode='Markdown')
        
        # Send notification to receiver (about receiving money)
        try:
            receiver_notification = f"""
💰 **تم استلام رصيد جديد!** 💰

👤 **من:** {user['full_name']}
💰 **المبلغ:** {amount:.2f} ريال
🕐 **الوقت:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

💳 **رصيدك الجديد:** {receiver_new_balance:.2f} ريال

🎉 **مبروك! تم إضافة الرصيد لحسابك**
"""
            
            # Send notification to receiver
            await context.bot.send_message(
                chat_id=target_user['telegram_id'],
                text=receiver_notification,
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.warning(f"Failed to notify receiver: {e}")
        
        # Log the successful transfer
        logger.info(f"User {user['full_name']} sent {amount} YER to {target_user['full_name']} (fee: {transfer_fee})")
        
    except Exception as e:
        logger.error(f"Error in confirm transfer handler: {e}")
        # Clear any processing state
        context.user_data.pop('transfer_processing', None)
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في معالجة التحويل")

async def enhanced_wallet_handler(update: Update, context: CallbackContext):
    """معالج المحفظة المحسنة مع نظام التصفح بالصفحات"""
    try:
        # تحديد نوع التحديث (callback أو message)
        if hasattr(update, 'callback_query') and update.callback_query:
            query = update.callback_query
            user = get_user(query.from_user.id)
            is_callback = True
        else:
            user = get_user(update.effective_user.id)
            is_callback = False
        
        if not user:
            error_msg = f"{EMOJIS['error']} يرجى التسجيل أولاً."
            if is_callback:
                await update.callback_query.edit_message_text(error_msg)
            else:
                await update.message.reply_text(error_msg)
            return
        
        # صفحة افتراضية (الصفحة الأولى)
        page = 1
        return await show_wallet_page(update, context, user, page, is_callback)
        
    except Exception as e:
        logger.error(f"Error in enhanced wallet handler: {e}")
        from bot_modules.enhanced_error_messages import ErrorMessages
        error_msg = ErrorMessages.custom_error(
            "المحفظة المطورة",
            "فشل في تحميل بيانات المحفظة",
            "تحقق من الاتصال وحاول مرة أخرى",
            "WALLET_LOAD_ERROR"
        )
        
        if hasattr(update, 'callback_query') and update.callback_query:
            await update.callback_query.edit_message_text(error_msg)
        else:
            await update.message.reply_text(error_msg)

async def show_wallet_page(update: Update, context: CallbackContext, user: dict, page: int, is_callback: bool = True):
    """عرض صفحة محددة من المحفظة مع نظام التصفح"""
    try:
        TRANSACTIONS_PER_PAGE = 4  # 4 معاملات لكل صفحة
        
        # الحصول على جميع المعاملات مع إحصائيات التصفح
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # إجمالي عدد المعاملات
        cursor.execute('''
            SELECT COUNT(*) FROM transactions 
            WHERE from_user = ? OR to_user = ?
        ''', (user['id'], user['id']))
        result = cursor.fetchone()
        total_transactions = result[0] if result else 0
        
        # حساب إجمالي الصفحات
        total_pages = max(1, (total_transactions + TRANSACTIONS_PER_PAGE - 1) // TRANSACTIONS_PER_PAGE)
        
        # التأكد من صحة رقم الصفحة
        page = max(1, min(page, total_pages))
        
        # حساب offset للصفحة الحالية
        offset = (page - 1) * TRANSACTIONS_PER_PAGE
        
        # الحصول على المعاملات للصفحة الحالية
        cursor.execute('''
            SELECT from_user, to_user, amount, type, description, created_at
            FROM transactions 
            WHERE from_user = ? OR to_user = ?
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        ''', (user['id'], user['id'], TRANSACTIONS_PER_PAGE, offset))
        
        transactions = cursor.fetchall()
        
        # إحصائيات المحفظة
        cursor.execute('''
            SELECT 
                COUNT(*) as total_count,
                COALESCE(SUM(CASE WHEN from_user = ? THEN amount END), 0) as sent_total,
                COALESCE(SUM(CASE WHEN to_user = ? THEN amount END), 0) as received_total
            FROM transactions 
            WHERE from_user = ? OR to_user = ?
        ''', (user['id'], user['id'], user['id'], user['id']))
        
        stats = cursor.fetchone()
        if stats:
            total_count, sent_amount, received_amount = stats
        else:
            total_count, sent_amount, received_amount = 0, 0, 0
        
        conn.close()
        
        # بناء نص المحفظة
        wallet_text = f"""
💳 **محفظتي المطورة** 💳

👤 **{user['full_name']}**
💰 **رصيدك:** {user['balance']:,.2f} ريال
💳 **رقم المحفظة:** {user['wallet_number']}

📊 **ملخص المعاملات:**
🔄 إجمالي المعاملات: **{total_count}** معاملة
📤 إجمالي المرسل: **{sent_amount:,.2f}** ريال  
📥 إجمالي المستلم: **{received_amount:,.2f}** ريال
📊 الفرق الصافي: **{received_amount - sent_amount:,.2f}** ريال

📋 **آخر المعاملات** (الصفحة {page} من {total_pages}):
"""
        
        # عرض المعاملات
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
                
                wallet_text += f"""
{type_icon} **{type_name}**
{direction} {color} **{amount:,.2f}** ريال
📅 {date_formatted}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        else:
            wallet_text += """
❌ **لا توجد معاملات**

💡 **ابدأ أول معاملة:**
• قم بشراء كروت من الشبكات المتاحة
• حوّل رصيد لصديق
• اشحن رصيدك بكوبون
"""
        
        # إنشاء أزرار التصفح
        keyboard = []
        
        # أزرار التصفح (فقط إذا كانت هناك صفحات متعددة)
        if total_pages > 1:
            navigation_row = []
            if page > 1:
                navigation_row.append(InlineKeyboardButton('◀️ السابق', callback_data=f'wallet_page_{page-1}'))
            
            navigation_row.append(InlineKeyboardButton(f'📄 {page}/{total_pages}', callback_data='current_page'))
            
            if page < total_pages:
                navigation_row.append(InlineKeyboardButton('▶️ التالي', callback_data=f'wallet_page_{page+1}'))
            
            # تقسيم أزرار التصفح إلى صفوف إذا كانت كثيرة
            if len(navigation_row) > 5:
                keyboard.append(navigation_row[:3])
                keyboard.append(navigation_row[3:])
            else:
                keyboard.append(navigation_row)
        
        # أزرار الوظائف الرئيسية
        keyboard.extend([
            [InlineKeyboardButton('💸 تحويل رصيد', callback_data='transfer_to_friend'),
             InlineKeyboardButton('🛒 شراء كروت', callback_data='buy_cards')],
            [InlineKeyboardButton('🎟️ شحن بكوبون', callback_data='redeem_coupon'),
             InlineKeyboardButton('📊 تفاصيل المعاملات', callback_data='transaction_details')],
            [InlineKeyboardButton('👥 إحالاتي وعمولاتي', callback_data='referral_stats'),
             InlineKeyboardButton('📈 إحصائيات المحفظة', callback_data='wallet_stats')],
            [InlineKeyboardButton('🎟️ كشف الحساب', callback_data='account_statement'),
             InlineKeyboardButton('🔄 تحديث الرصيد', callback_data='refresh_balance')],
            [InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
        ])
        
        if is_callback:
            await update.callback_query.edit_message_text(wallet_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        else:
            await update.message.reply_text(wallet_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in show wallet page: {e}")
        from bot_modules.enhanced_error_messages import ErrorMessages
        error_msg = ErrorMessages.custom_error(
            "صفحة المحفظة",
            f"فشل في تحميل الصفحة رقم {page}",
            "حاول تحديث المحفظة أو العودة للصفحة الأولى",
            "WALLET_PAGE_ERROR"
        )
        
        if is_callback:
            await update.callback_query.edit_message_text(error_msg)
        else:
            await update.message.reply_text(error_msg)

async def wallet_page_handler(update: Update, context: CallbackContext):
    """معالج التنقل بين صفحات المحفظة"""
    try:
        query = update.callback_query
        user = get_user(query.from_user.id)
        
        if not user:
            await query.edit_message_text(f"{EMOJIS['error']} يرجى التسجيل أولاً.")
            return
        
        # استخراج رقم الصفحة من callback_data
        page = int(query.data.split('_')[2])
        
        return await show_wallet_page(update, context, user, page, is_callback=True)
        
    except Exception as e:
        logger.error(f"Error in wallet page handler: {e}")
        from bot_modules.enhanced_error_messages import ErrorMessages
        await query.edit_message_text(ErrorMessages.custom_error(
            "التنقل بين الصفحات",
            "فشل في تحميل الصفحة المطلوبة",
            "حاول العودة للمحفظة الرئيسية وأعد المحاولة",
            "PAGE_NAV_ERROR"
        ))

async def confirm_user_transfer(update: Update, context: CallbackContext, user_id: str, amount: str):
    """تأكيد التحويل للمستخدم - معالج مفقود"""
    try:
        query = update.callback_query
        user = get_user(query.from_user.id)
        
        if not user:
            await query.edit_message_text(f"{EMOJIS['error']} يرجى التسجيل أولاً /start")
            return
        
        # Get target user details
        target_user = get_user(int(user_id))
        if not target_user:
            await query.edit_message_text(
                f"{EMOJIS['error']} المستخدم غير موجود",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
                ])
            )
            return
        
        amount = float(amount)
        
        # التحقق من الرصيد
        if user['balance'] < amount:
            await query.edit_message_text(
                f"{EMOJIS['error']} رصيدك ({user['balance']:,.2f} ريال) غير كافي لتحويل {amount:,.2f} ريال",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton('💳 شحن الرصيد', callback_data='recharge_balance')],
                    [InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
                ])
            )
            return
        
        # Set up context for confirm_transfer_handler
        context.user_data['target_user_id'] = int(user_id)
        context.user_data['target_user_name'] = target_user['full_name']
        context.user_data['transfer_amount'] = float(amount)
        context.user_data['awaiting_transfer_confirmation'] = True
        
        # Call the existing confirm_transfer_handler with confirmed=True
        return await confirm_transfer_handler(update, context, confirmed=True)
        
    except Exception as e:
        logger.error(f"Error in confirm user transfer: {e}")
        query = update.callback_query
        await query.edit_message_text(
            f"{EMOJIS['error']} حدث خطأ في تأكيد التحويل. يرجى المحاولة مرة أخرى.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
            ])
        )