"""
Yemen Net Bot - البوت الرئيسي المحسن
نظام بوت تليجرام متطور لبيع كروت الشبكة مع ميزات متقدمة
"""

import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, 
    CommandHandler, 
    CallbackQueryHandler,
    PicklePersistence
)

# استيراد الوحدات المحسنة
from bot.config import BOT_TOKEN, QUICK_COMMANDS
from bot.database.migrations import run_migrations
from bot.models.user import UserRole
from bot.models.wallet import EWallet
from bot.models.rating import RatingSystem
from bot.services.notification_service import notification_service
from bot.services.report_service import ReportService
from bot.database.connection import db_manager

# إعداد نظام السجلات
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class YemenNetBot:
    """الفئة الرئيسية للبوت المحسن"""
    
    def __init__(self):
        self.application = None
        self.setup_bot()
    
    def setup_bot(self):
        """إعداد البوت"""
        try:
            # تشغيل ترحيل قاعدة البيانات
            run_migrations()
            
            # إعداد البوت
            persistence = PicklePersistence(filepath='bot_data')
            self.application = Application.builder().token(BOT_TOKEN).persistence(persistence).build()
            
            # إعداد الأوامر
            self.setup_handlers()
            
            # سيتم إعداد الأوامر السريعة عند التشغيل
            # لا نحتاج لتشغيلها هنا لتجنب مشاكل event loop
            
            logger.info("تم إعداد البوت بنجاح")
            
        except Exception as e:
            logger.error(f"خطأ حرج في إعداد البوت: {e}")
            raise
    
    def setup_handlers(self):
        """إعداد معالجات الأوامر"""
        
        # الأوامر الأساسية
        self.application.add_handler(CommandHandler('start', self.start_command))
        self.application.add_handler(CommandHandler('menu', self.menu_command))
        self.application.add_handler(CommandHandler('balance', self.balance_command))
        self.application.add_handler(CommandHandler('stats', self.stats_command))
        
        # الأوامر الجديدة
        self.application.add_handler(CommandHandler('wallet', self.wallet_command))
        self.application.add_handler(CommandHandler('rating', self.rating_command))
        self.application.add_handler(CommandHandler('notifications', self.notifications_command))
        self.application.add_handler(CommandHandler('reports', self.reports_command))
        
        # معالج الأزرار
        self.application.add_handler(CallbackQueryHandler(self.button_handler))
    
    async def start_command(self, update: Update, context):
        """أمر البداية المحسن"""
        user = update.effective_user
        
        try:
            # التحقق من وجود المستخدم
            with db_manager.get_cursor() as (conn, cursor):
                cursor.execute('SELECT id, is_active FROM users WHERE telegram_id = ?', (user.id,))
                user_data = cursor.fetchone()
                
                if user_data:
                    user_id = user_data[0]
                    # إرسال إشعار ترحيب للمستخدمين العائدين
                    if user_data[1]:  # نشط
                        await notification_service.send_push_notification(
                            user_id, 
                            "مرحباً بعودتك!", 
                            "نحن سعداء لرؤيتك مرة أخرى في بوت يمن نت المحسن!"
                        )
            
            welcome_text = """🌟 مرحباً بك في بوت يمن نت المحسن!

🆕 الميزات الجديدة:
• 💳 المحفظة الإلكترونية المتطورة
• ⭐ نظام التقييم التفاعلي  
• 🔔 الإشعارات الذكية
• 📊 التقارير المتقدمة
• 🔒 أمان محسن للبيانات

استخدم الأزرار أدناه للبدء:"""
            
            keyboard = [
                [InlineKeyboardButton("📋 القائمة الرئيسية", callback_data="main_menu")],
                [InlineKeyboardButton("💰 المحفظة", callback_data="wallet_menu")],
                [InlineKeyboardButton("⭐ تقييم الخدمة", callback_data="rating_menu")]
            ]
            
            await update.message.reply_text(
                welcome_text,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        except Exception as e:
            logger.error(f"خطأ في أمر البداية: {e}")
            await update.message.reply_text("حدث خطأ. يرجى المحاولة مرة أخرى.")
    
    async def menu_command(self, update: Update, context):
        """القائمة الرئيسية المحسنة"""
        
        keyboard = [
            [
                InlineKeyboardButton("💳 شراء كرت", callback_data="buy_card"),
                InlineKeyboardButton("💰 الرصيد", callback_data="show_balance")
            ],
            [
                InlineKeyboardButton("🔄 المحفظة الإلكترونية", callback_data="wallet_menu"),
                InlineKeyboardButton("📊 إحصائياتي", callback_data="my_stats")
            ],
            [
                InlineKeyboardButton("⭐ التقييم", callback_data="rating_menu"),
                InlineKeyboardButton("🔔 الإشعارات", callback_data="notifications_menu")
            ],
            [
                InlineKeyboardButton("📈 التقارير", callback_data="reports_menu"),
                InlineKeyboardButton("⚙️ الإعدادات", callback_data="settings_menu")
            ]
        ]
        
        await update.message.reply_text(
            "🏠 القائمة الرئيسية المحسنة\nاختر الخدمة المطلوبة:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def wallet_command(self, update: Update, context):
        """أمر المحفظة الإلكترونية"""
        
        keyboard = [
            [
                InlineKeyboardButton("💸 تحويل أموال", callback_data="transfer_money"),
                InlineKeyboardButton("📝 سجل المعاملات", callback_data="transaction_history")
            ],
            [
                InlineKeyboardButton("🏪 الدفع للتجار", callback_data="pay_vendor"),
                InlineKeyboardButton("💰 الرصيد المتاح", callback_data="wallet_balance")
            ],
            [InlineKeyboardButton("🔙 العودة للقائمة", callback_data="main_menu")]
        ]
        
        await update.message.reply_text(
            "💳 المحفظة الإلكترونية المتقدمة\n\nاختر العملية المطلوبة:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def rating_command(self, update: Update, context):
        """أمر التقييم"""
        
        # عرض متوسط التقييم الحالي
        avg_rating = RatingSystem.get_average_rating()
        
        keyboard = [
            [InlineKeyboardButton("⭐", callback_data="rate_1"),
             InlineKeyboardButton("⭐⭐", callback_data="rate_2"),
             InlineKeyboardButton("⭐⭐⭐", callback_data="rate_3")],
            [InlineKeyboardButton("⭐⭐⭐⭐", callback_data="rate_4"),
             InlineKeyboardButton("⭐⭐⭐⭐⭐", callback_data="rate_5")],
            [InlineKeyboardButton("📊 إحصائيات التقييم", callback_data="rating_stats")],
            [InlineKeyboardButton("🔙 العودة للقائمة", callback_data="main_menu")]
        ]
        
        text = f"""⭐ نظام التقييم

متوسط التقييم الحالي: {avg_rating}/5 ⭐

كيف تقيم خدماتنا؟ اختر عدد النجوم:"""
        
        await update.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def balance_command(self, update: Update, context):
        """أمر عرض الرصيد"""
        user = update.effective_user
        
        try:
            with db_manager.get_cursor() as (conn, cursor):
                cursor.execute('SELECT balance, wallet_number FROM users WHERE telegram_id = ?', (user.id,))
                user_data = cursor.fetchone()
                
                if not user_data:
                    await update.message.reply_text("❌ لم يتم العثور على حسابك. يرجى التسجيل أولاً.")
                    return
                
                balance = user_data[0] or 0.0
                wallet_number = user_data[1] or "غير محدد"
                
                keyboard = [
                    [InlineKeyboardButton("💳 المحفظة الإلكترونية", callback_data="wallet_menu")],
                    [InlineKeyboardButton("💰 إضافة رصيد", callback_data="add_balance")],
                    [InlineKeyboardButton("📊 سجل المعاملات", callback_data="transaction_history")],
                    [InlineKeyboardButton("🔙 العودة للقائمة", callback_data="main_menu")]
                ]
                
                text = f"""💰 معلومات الرصيد

👤 الاسم: {user.full_name}
💳 رقم المحفظة: {wallet_number}
💰 الرصيد الحالي: {balance:.2f} ريال

اختر العملية المطلوبة:"""
                
                await update.message.reply_text(
                    text,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                
        except Exception as e:
            logger.error(f"خطأ في عرض الرصيد: {e}")
            await update.message.reply_text("❌ حدث خطأ في جلب معلومات الرصيد.")
    
    async def stats_command(self, update: Update, context):
        """أمر عرض الإحصائيات"""
        user = update.effective_user
        
        try:
            with db_manager.get_cursor() as (conn, cursor):
                # إحصائيات المستخدم
                cursor.execute('SELECT balance, total_referrals, referral_bonus FROM users WHERE telegram_id = ?', (user.id,))
                user_data = cursor.fetchone()
                
                if not user_data:
                    await update.message.reply_text("❌ لم يتم العثور على حسابك.")
                    return
                
                balance, total_referrals, referral_bonus = user_data
                
                # إحصائيات المعاملات
                cursor.execute('''
                    SELECT COUNT(*), COALESCE(SUM(amount), 0) 
                    FROM transactions 
                    WHERE from_user = (SELECT id FROM users WHERE telegram_id = ?) 
                    AND status = 'completed'
                ''', (user.id,))
                
                transaction_data = cursor.fetchone()
                total_transactions = transaction_data[0]
                total_spent = transaction_data[1]
                
                # إحصائيات عامة للبوت
                cursor.execute('SELECT COUNT(*) FROM users WHERE is_active = 1')
                active_users = cursor.fetchone()[0]
                
                keyboard = [
                    [InlineKeyboardButton("📊 التقارير المفصلة", callback_data="reports_menu")],
                    [InlineKeyboardButton("🔙 العودة للقائمة", callback_data="main_menu")]
                ]
                
                text = f"""📊 إحصائياتك الشخصية

💰 الرصيد الحالي: {balance:.2f} ريال
🎯 عدد الإحالات: {total_referrals}
💵 مكافآت الإحالة: {referral_bonus:.2f} ريال
🛒 إجمالي المعاملات: {total_transactions}
💸 إجمالي المصروفات: {total_spent:.2f} ريال

📈 إحصائيات عامة:
👥 المستخدمين النشطين: {active_users}"""
                
                await update.message.reply_text(
                    text,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                
        except Exception as e:
            logger.error(f"خطأ في عرض الإحصائيات: {e}")
            await update.message.reply_text("❌ حدث خطأ في جلب الإحصائيات.")
    
    async def notifications_command(self, update: Update, context):
        """أمر عرض الإشعارات"""
        await self.show_notifications_menu_from_command(update)
    
    async def reports_command(self, update: Update, context):
        """أمر عرض التقارير"""
        user = update.effective_user
        
        try:
            # التحقق من صلاحيات المستخدم
            with db_manager.get_cursor() as (conn, cursor):
                cursor.execute('SELECT role FROM users WHERE telegram_id = ?', (user.id,))
                user_data = cursor.fetchone()
                
                if not user_data or user_data[0] not in ['admin', 'agent']:
                    await update.message.reply_text("❌ ليس لديك صلاحية للوصول للتقارير.")
                    return
            
            keyboard = [
                [InlineKeyboardButton("📊 تقرير المبيعات", callback_data="report_sales")],
                [InlineKeyboardButton("👥 تقرير النشاط", callback_data="report_activity")],
                [InlineKeyboardButton("💰 التقرير المالي", callback_data="report_financial")],
                [InlineKeyboardButton("⭐ تقرير التقييمات", callback_data="report_ratings")],
                [InlineKeyboardButton("📋 التقرير الشامل", callback_data="report_comprehensive")],
                [InlineKeyboardButton("🔙 العودة للقائمة", callback_data="main_menu")]
            ]
            
            await update.message.reply_text(
                "📈 قائمة التقارير المتقدمة\n\nاختر نوع التقرير المطلوب:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        except Exception as e:
            logger.error(f"خطأ في أمر التقارير: {e}")
            await update.message.reply_text("❌ حدث خطأ في الوصول للتقارير.")
    
    async def show_notifications_menu_from_command(self, update):
        """عرض قائمة الإشعارات من الأمر"""
        user = update.effective_user
        
        try:
            # البحث عن المستخدم
            with db_manager.get_cursor() as (conn, cursor):
                cursor.execute('SELECT id FROM users WHERE telegram_id = ?', (user.id,))
                user_row = cursor.fetchone()
                
                if not user_row:
                    await update.message.reply_text("يجب التسجيل أولاً.")
                    return
                
                user_id = user_row[0]
            
            # جلب الإشعارات
            notifications = notification_service.get_user_notifications(user_id, limit=10)
            unread_count = notification_service.get_unread_count(user_id)
            
            if notifications:
                text = f"🔔 الإشعارات ({unread_count} غير مقروء)\n\n"
                
                for notif in notifications[:5]:
                    status = "🔴" if not notif['is_read'] else "✅"
                    text += f"{status} {notif['title']}\n{notif['message'][:50]}...\n\n"
                
                keyboard = [
                    [InlineKeyboardButton("✅ تحديد الكل كمقروء", callback_data="mark_all_read")],
                    [InlineKeyboardButton("🔙 العودة للقائمة", callback_data="main_menu")]
                ]
            else:
                text = "📭 لا توجد إشعارات"
                keyboard = [[InlineKeyboardButton("🔙 العودة للقائمة", callback_data="main_menu")]]
            
            await update.message.reply_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        except Exception as e:
            logger.error(f"خطأ في عرض الإشعارات: {e}")
            await update.message.reply_text("حدث خطأ في جلب الإشعارات.")
    
    async def show_main_menu(self, query):
        """عرض القائمة الرئيسية"""
        keyboard = [
            [InlineKeyboardButton("💰 الرصيد", callback_data="balance_menu"),
             InlineKeyboardButton("💳 المحفظة", callback_data="wallet_menu")],
            [InlineKeyboardButton("🛒 شراء كرت", callback_data="buy_card"),
             InlineKeyboardButton("📊 الإحصائيات", callback_data="stats_menu")],
            [InlineKeyboardButton("⭐ التقييم", callback_data="rating_menu"),
             InlineKeyboardButton("🔔 الإشعارات", callback_data="notifications_menu")],
            [InlineKeyboardButton("📈 التقارير", callback_data="reports_menu"),
             InlineKeyboardButton("ℹ️ المساعدة", callback_data="help_menu")]
        ]
        
        text = """🏠 القائمة الرئيسية

مرحباً بك في بوت يمن نت المحسن!
اختر الخدمة المطلوبة من القائمة أدناه:"""
        
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def show_wallet_menu(self, query):
        """عرض قائمة المحفظة الإلكترونية"""
        user = query.from_user
        
        try:
            # جلب معلومات المحفظة
            wallet = EWallet(user.id)
            balance = wallet.get_balance()
            
            keyboard = [
                [InlineKeyboardButton("💸 تحويل أموال", callback_data="transfer_money")],
                [InlineKeyboardButton("📊 سجل المعاملات", callback_data="transaction_history")],
                [InlineKeyboardButton("💰 إضافة رصيد", callback_data="add_balance")],
                [InlineKeyboardButton("📱 معلومات المحفظة", callback_data="wallet_info")],
                [InlineKeyboardButton("🔙 العودة للقائمة", callback_data="main_menu")]
            ]
            
            text = f"""💳 المحفظة الإلكترونية

👤 المستخدم: {user.full_name}
💰 الرصيد: {balance:.2f} ريال
🆔 معرف المحفظة: {user.id}

اختر العملية المطلوبة:"""
            
            await query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        except Exception as e:
            logger.error(f"خطأ في عرض قائمة المحفظة: {e}")
            await query.edit_message_text("❌ حدث خطأ في جلب معلومات المحفظة.")
    
    async def initiate_transfer(self, query):
        """بدء عملية التحويل"""
        text = """💸 تحويل الأموال

لبدء عملية التحويل، يرجى إرسال المعلومات التالية:

📝 الصيغة: /transfer <رقم_المحفظة> <المبلغ>
مثال: /transfer 123456789 100

⚠️ ملاحظات مهمة:
• تأكد من صحة رقم المحفظة
• الحد الأدنى للتحويل: 1 ريال
• الحد الأقصى للتحويل: 10000 ريال"""
        
        keyboard = [[InlineKeyboardButton("🔙 العودة للمحفظة", callback_data="wallet_menu")]]
        
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def show_transaction_history(self, query):
        """عرض سجل المعاملات"""
        user = query.from_user
        
        try:
            with db_manager.get_cursor() as (conn, cursor):
                cursor.execute('''
                    SELECT t.amount, t.type, t.status, t.created_at,
                           u1.full_name as from_name, u2.full_name as to_name
                    FROM transactions t
                    LEFT JOIN users u1 ON t.from_user = u1.id
                    LEFT JOIN users u2 ON t.to_user = u2.id
                    WHERE t.from_user = (SELECT id FROM users WHERE telegram_id = ?)
                       OR t.to_user = (SELECT id FROM users WHERE telegram_id = ?)
                    ORDER BY t.created_at DESC
                    LIMIT 10
                ''', (user.id, user.id))
                
                transactions = cursor.fetchall()
                
                if transactions:
                    text = "📊 سجل المعاملات (آخر 10)\n\n"
                    
                    for trans in transactions:
                        amount, trans_type, status, created_at, from_name, to_name = trans
                        
                        # تحديد اتجاه المعاملة
                        if from_name == user.full_name:
                            direction = f"➡️ إلى: {to_name}"
                            amount_text = f"-{amount:.2f}"
                        else:
                            direction = f"⬅️ من: {from_name}"
                            amount_text = f"+{amount:.2f}"
                        
                        status_emoji = "✅" if status == "completed" else "⏳" if status == "pending" else "❌"
                        
                        text += f"{status_emoji} {amount_text} ريال\n"
                        text += f"   {direction}\n"
                        text += f"   📅 {created_at}\n\n"
                else:
                    text = "📭 لا توجد معاملات"
                
                keyboard = [
                    [InlineKeyboardButton("🔄 تحديث", callback_data="transaction_history")],
                    [InlineKeyboardButton("🔙 العودة للمحفظة", callback_data="wallet_menu")]
                ]
                
                await query.edit_message_text(
                    text,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                
        except Exception as e:
            logger.error(f"خطأ في عرض سجل المعاملات: {e}")
            await query.edit_message_text("❌ حدث خطأ في جلب سجل المعاملات.")
    
    async def button_handler(self, update: Update, context):
        """معالج الأزرار المحسن"""
        query = update.callback_query
        await query.answer()
        
        try:
            data = query.data
            
            # معالجة التقييمات
            if data.startswith("rate_"):
                await self.handle_rating(query, int(data.split("_")[1]))
            elif data == "rating_menu":
                await self.show_rating_menu(query)
            elif data == "rating_stats":
                await self.show_rating_stats(query)
            
            # معالجة المحفظة
            elif data == "wallet_menu":
                await self.show_wallet_menu(query)
            elif data == "transfer_money":
                await self.initiate_transfer(query)
            elif data == "transaction_history":
                await self.show_transaction_history(query)
            elif data == "add_balance":
                await self.show_add_balance_menu(query)
            elif data == "wallet_info":
                await self.show_wallet_info(query)
            
            # معالجة القوائم الرئيسية
            elif data == "balance_menu":
                await self.show_balance_menu(query)
            elif data == "stats_menu":
                await self.show_stats_menu(query)
            elif data == "buy_card":
                await self.show_buy_card_menu(query)
            elif data == "help_menu":
                await self.show_help_menu(query)
            
            # معالجة التقارير
            elif data == "reports_menu":
                await self.show_reports_menu(query)
            elif data.startswith("report_"):
                await self.generate_report(query, data)
            
            # معالجة الإشعارات
            elif data == "notifications_menu":
                await self.show_notifications_menu(query)
            elif data == "mark_all_read":
                await self.mark_all_notifications_read(query)
            
            # القوائم الأساسية
            elif data == "main_menu":
                await self.show_main_menu(query)
            
            else:
                await query.edit_message_text("هذه الميزة قيد التطوير... 🚧")
                
        except Exception as e:
            logger.error(f"خطأ في معالج الأزرار: {e}")
            await query.edit_message_text("حدث خطأ. يرجى المحاولة مرة أخرى.")
    
    async def handle_rating(self, query, stars: int):
        """معالجة التقييم"""
        user = query.from_user
        
        try:
            # البحث عن المستخدم في قاعدة البيانات
            with db_manager.get_cursor() as (conn, cursor):
                cursor.execute('SELECT id FROM users WHERE telegram_id = ?', (user.id,))
                user_row = cursor.fetchone()
                
                if not user_row:
                    await query.edit_message_text("يجب التسجيل أولاً لإضافة تقييم.")
                    return
                
                user_id = user_row[0]
            
            # إضافة التقييم
            result = RatingSystem.add_rating(user_id, stars)
            
            if result['success']:
                # إرسال إشعار للمستخدم
                await notification_service.send_push_notification(
                    user_id,
                    "تم إرسال التقييم",
                    f"شكراً لك على تقييم خدماتنا بـ {stars} نجوم!"
                )
                
                await query.edit_message_text(
                    f"✅ تم إرسال تقييمك بنجاح!\n\n⭐ تقييمك: {stars}/5\n\nشكراً لك على رأيك القيم."
                )
            else:
                await query.edit_message_text(f"❌ {result['message']}")
                
        except Exception as e:
            logger.error(f"خطأ في التقييم: {e}")
            await query.edit_message_text("حدث خطأ في إرسال التقييم.")
    
    async def show_reports_menu(self, query):
        """عرض قائمة التقارير"""
        
        keyboard = [
            [InlineKeyboardButton("📊 تقرير المبيعات", callback_data="report_sales")],
            [InlineKeyboardButton("👥 تقرير النشاط", callback_data="report_activity")],
            [InlineKeyboardButton("💰 التقرير المالي", callback_data="report_financial")],
            [InlineKeyboardButton("⭐ تقرير التقييمات", callback_data="report_ratings")],
            [InlineKeyboardButton("📋 التقرير الشامل", callback_data="report_comprehensive")],
            [InlineKeyboardButton("🔙 العودة للقائمة", callback_data="main_menu")]
        ]
        
        await query.edit_message_text(
            "📈 قائمة التقارير المتقدمة\n\nاختر نوع التقرير المطلوب:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def generate_report(self, query, report_type: str):
        """إنشاء التقارير"""
        
        await query.edit_message_text("⏳ جاري إنشاء التقرير...")
        
        try:
            report_data = report_type.split("_")[1]
            
            if report_data == "sales":
                report = ReportService.generate_sales_report()
            elif report_data == "activity":
                report = ReportService.generate_user_activity_report()
            elif report_data == "financial":
                report = ReportService.generate_financial_report()
            elif report_data == "ratings":
                report = RatingSystem.generate_rating_report()
            elif report_data == "comprehensive":
                report = ReportService.generate_comprehensive_report()
            else:
                report = "نوع التقرير غير مدعوم"
            
            # إرسال التقرير مع زر العودة
            keyboard = [[InlineKeyboardButton("🔙 العودة للتقارير", callback_data="reports_menu")]]
            
            await query.edit_message_text(
                report,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        except Exception as e:
            logger.error(f"خطأ في إنشاء التقرير: {e}")
            await query.edit_message_text("حدث خطأ في إنشاء التقرير.")
    
    async def show_notifications_menu(self, query):
        """عرض قائمة الإشعارات"""
        user = query.from_user
        
        try:
            # البحث عن المستخدم
            with db_manager.get_cursor() as (conn, cursor):
                cursor.execute('SELECT id FROM users WHERE telegram_id = ?', (user.id,))
                user_row = cursor.fetchone()
                
                if not user_row:
                    await query.edit_message_text("يجب التسجيل أولاً.")
                    return
                
                user_id = user_row[0]
            
            # جلب الإشعارات
            notifications = notification_service.get_user_notifications(user_id, limit=10)
            unread_count = notification_service.get_unread_count(user_id)
            
            if notifications:
                text = f"🔔 الإشعارات ({unread_count} غير مقروء)\n\n"
                
                for notif in notifications[:5]:
                    status = "🔴" if not notif['is_read'] else "✅"
                    text += f"{status} {notif['title']}\n{notif['message'][:50]}...\n\n"
                
                keyboard = [
                    [InlineKeyboardButton("✅ تحديد الكل كمقروء", callback_data="mark_all_read")],
                    [InlineKeyboardButton("🔙 العودة للقائمة", callback_data="main_menu")]
                ]
            else:
                text = "📭 لا توجد إشعارات"
                keyboard = [[InlineKeyboardButton("🔙 العودة للقائمة", callback_data="main_menu")]]
            
            await query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        except Exception as e:
            logger.error(f"خطأ في عرض الإشعارات: {e}")
            await query.edit_message_text("حدث خطأ في جلب الإشعارات.")
    
    # دوال مساعدة إضافية للقوائم والميزات
    async def show_rating_menu(self, query):
        """عرض قائمة التقييم"""
        avg_rating = RatingSystem.get_average_rating()
        
        keyboard = [
            [InlineKeyboardButton("⭐", callback_data="rate_1"),
             InlineKeyboardButton("⭐⭐", callback_data="rate_2"),
             InlineKeyboardButton("⭐⭐⭐", callback_data="rate_3")],
            [InlineKeyboardButton("⭐⭐⭐⭐", callback_data="rate_4"),
             InlineKeyboardButton("⭐⭐⭐⭐⭐", callback_data="rate_5")],
            [InlineKeyboardButton("📊 إحصائيات التقييم", callback_data="rating_stats")],
            [InlineKeyboardButton("🔙 العودة للقائمة", callback_data="main_menu")]
        ]
        
        text = f"""⭐ نظام التقييم

متوسط التقييم الحالي: {avg_rating}/5 ⭐

كيف تقيم خدماتنا؟ اختر عدد النجوم:"""
        
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    
    async def show_rating_stats(self, query):
        """عرض إحصائيات التقييم"""
        try:
            report = RatingSystem.generate_rating_report()
            keyboard = [[InlineKeyboardButton("🔙 العودة للتقييم", callback_data="rating_menu")]]
            await query.edit_message_text(report, reply_markup=InlineKeyboardMarkup(keyboard))
        except Exception as e:
            logger.error(f"خطأ في إحصائيات التقييم: {e}")
            await query.edit_message_text("❌ حدث خطأ في جلب الإحصائيات.")
    
    async def show_balance_menu(self, query):
        """عرض قائمة الرصيد"""
        user = query.from_user
        
        try:
            with db_manager.get_cursor() as (conn, cursor):
                cursor.execute('SELECT balance, wallet_number FROM users WHERE telegram_id = ?', (user.id,))
                user_data = cursor.fetchone()
                
                if not user_data:
                    await query.edit_message_text("❌ لم يتم العثور على حسابك.")
                    return
                
                balance = user_data[0] or 0.0
                wallet_number = user_data[1] or "غير محدد"
                
                keyboard = [
                    [InlineKeyboardButton("💳 المحفظة الإلكترونية", callback_data="wallet_menu")],
                    [InlineKeyboardButton("💰 إضافة رصيد", callback_data="add_balance")],
                    [InlineKeyboardButton("📊 سجل المعاملات", callback_data="transaction_history")],
                    [InlineKeyboardButton("🔙 العودة للقائمة", callback_data="main_menu")]
                ]
                
                text = f"""💰 معلومات الرصيد

👤 الاسم: {user.full_name}
💳 رقم المحفظة: {wallet_number}
💰 الرصيد الحالي: {balance:.2f} ريال

اختر العملية المطلوبة:"""
                
                await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
                
        except Exception as e:
            logger.error(f"خطأ في قائمة الرصيد: {e}")
            await query.edit_message_text("❌ حدث خطأ في جلب معلومات الرصيد.")
    
    async def show_stats_menu(self, query):
        """عرض قائمة الإحصائيات"""
        user = query.from_user
        
        try:
            with db_manager.get_cursor() as (conn, cursor):
                cursor.execute('SELECT balance, total_referrals, referral_bonus FROM users WHERE telegram_id = ?', (user.id,))
                user_data = cursor.fetchone()
                
                if not user_data:
                    await query.edit_message_text("❌ لم يتم العثور على حسابك.")
                    return
                
                balance, total_referrals, referral_bonus = user_data
                
                keyboard = [
                    [InlineKeyboardButton("📊 التقارير المفصلة", callback_data="reports_menu")],
                    [InlineKeyboardButton("🔙 العودة للقائمة", callback_data="main_menu")]
                ]
                
                text = f"""📊 إحصائياتك الشخصية

💰 الرصيد الحالي: {balance:.2f} ريال
🎯 عدد الإحالات: {total_referrals}
💵 مكافآت الإحالة: {referral_bonus:.2f} ريال"""
                
                await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
                
        except Exception as e:
            logger.error(f"خطأ في قائمة الإحصائيات: {e}")
            await query.edit_message_text("❌ حدث خطأ في جلب الإحصائيات.")
    
    async def show_buy_card_menu(self, query):
        """عرض قائمة شراء الكروت"""
        keyboard = [
            [InlineKeyboardButton("🌐 يمن موبايل", callback_data="network_yemen_mobile")],
            [InlineKeyboardButton("📱 سبأفون", callback_data="network_sabafon")],
            [InlineKeyboardButton("📶 يو", callback_data="network_y")],
            [InlineKeyboardButton("🌐 واي", callback_data="network_why")],
            [InlineKeyboardButton("🔙 العودة للقائمة", callback_data="main_menu")]
        ]
        
        text = """🛒 شراء كرت شحن

اختر شبكة الاتصال المطلوبة:"""
        
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    
    async def show_help_menu(self, query):
        """عرض قائمة المساعدة"""
        keyboard = [
            [InlineKeyboardButton("❓ الأسئلة الشائعة", callback_data="faq")],
            [InlineKeyboardButton("📞 التواصل معنا", callback_data="contact")],
            [InlineKeyboardButton("📋 دليل الاستخدام", callback_data="guide")],
            [InlineKeyboardButton("🔙 العودة للقائمة", callback_data="main_menu")]
        ]
        
        text = """ℹ️ المساعدة والدعم

مرحباً! كيف يمكننا مساعدتك؟"""
        
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    
    async def show_add_balance_menu(self, query):
        """عرض قائمة إضافة الرصيد"""
        keyboard = [
            [InlineKeyboardButton("🏦 تحويل بنكي", callback_data="bank_transfer")],
            [InlineKeyboardButton("💳 بطاقة ائتمان", callback_data="credit_card")],
            [InlineKeyboardButton("📱 محفظة إلكترونية", callback_data="e_wallet_pay")],
            [InlineKeyboardButton("🔙 العودة للمحفظة", callback_data="wallet_menu")]
        ]
        
        text = """💰 إضافة رصيد

اختر طريقة الدفع المناسبة:"""
        
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    
    async def show_wallet_info(self, query):
        """عرض معلومات المحفظة"""
        user = query.from_user
        
        try:
            with db_manager.get_cursor() as (conn, cursor):
                cursor.execute('SELECT wallet_number, balance, created_at FROM users WHERE telegram_id = ?', (user.id,))
                user_data = cursor.fetchone()
                
                if not user_data:
                    await query.edit_message_text("❌ لم يتم العثور على معلومات المحفظة.")
                    return
                
                wallet_number, balance, created_at = user_data
                
                keyboard = [[InlineKeyboardButton("🔙 العودة للمحفظة", callback_data="wallet_menu")]]
                
                text = f"""📱 معلومات المحفظة

🆔 رقم المحفظة: {wallet_number}
💰 الرصيد: {balance:.2f} ريال
📅 تاريخ الإنشاء: {created_at}
👤 المالك: {user.full_name}

🔒 محفظتك آمنة ومحمية بأحدث تقنيات التشفير"""
                
                await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
                
        except Exception as e:
            logger.error(f"خطأ في معلومات المحفظة: {e}")
            await query.edit_message_text("❌ حدث خطأ في جلب معلومات المحفظة.")
    
    async def mark_all_notifications_read(self, query):
        """تحديد جميع الإشعارات كمقروءة"""
        user = query.from_user
        
        try:
            with db_manager.get_cursor() as (conn, cursor):
                cursor.execute('SELECT id FROM users WHERE telegram_id = ?', (user.id,))
                user_row = cursor.fetchone()
                
                if not user_row:
                    await query.edit_message_text("❌ لم يتم العثور على حسابك.")
                    return
                
                user_id = user_row[0]
            
            # تحديد جميع الإشعارات كمقروءة
            result = notification_service.mark_all_as_read(user_id)
            
            if result:
                await query.edit_message_text("✅ تم تحديد جميع الإشعارات كمقروءة.")
                # العودة لقائمة الإشعارات
                await asyncio.sleep(1)
                await self.show_notifications_menu(query)
            else:
                await query.edit_message_text("❌ حدث خطأ في تحديث الإشعارات.")
                
        except Exception as e:
            logger.error(f"خطأ في تحديد الإشعارات كمقروءة: {e}")
            await query.edit_message_text("❌ حدث خطأ في العملية.")
    
    def get_application(self):
        """إرجاع كائن Application للاستخدام الخارجي"""
        return self.application
    
    async def setup_commands(self):
        """إعداد الأوامر السريعة"""
        try:
            await self.application.bot.set_my_commands(QUICK_COMMANDS)
            logger.info("تم إعداد الأوامر السريعة بنجاح")
        except Exception as e:
            logger.warning(f"فشل إعداد الأوامر السريعة: {e}")

def main():
    """الدالة الرئيسية"""
    try:
        # إنشاء البوت
        bot = YemenNetBot()
        
        # تشغيل البوت باستخدام polling
        logger.info("🚀 بدء تشغيل البوت بـ polling...")
        bot.application.run_polling(drop_pending_updates=True)
        
    except KeyboardInterrupt:
        logger.info("تم إيقاف البوت بواسطة المستخدم")
    except Exception as e:
        logger.error(f"خطأ حرج في main: {e}")
        raise

if __name__ == '__main__':
    main()