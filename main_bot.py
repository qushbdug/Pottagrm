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
    
    async def button_handler(self, update: Update, context):
        """معالج الأزرار المحسن"""
        query = update.callback_query
        await query.answer()
        
        try:
            data = query.data
            
            # معالجة التقييمات
            if data.startswith("rate_"):
                await self.handle_rating(query, int(data.split("_")[1]))
            
            # معالجة المحفظة
            elif data == "wallet_menu":
                await self.show_wallet_menu(query)
            elif data == "transfer_money":
                await self.initiate_transfer(query)
            elif data == "transaction_history":
                await self.show_transaction_history(query)
            
            # معالجة التقارير
            elif data == "reports_menu":
                await self.show_reports_menu(query)
            elif data.startswith("report_"):
                await self.generate_report(query, data)
            
            # معالجة الإشعارات
            elif data == "notifications_menu":
                await self.show_notifications_menu(query)
            
            # القوائم الأساسية
            elif data == "main_menu":
                await self.show_main_menu(query)
            
            else:
                await query.edit_message_text("هذه الميزة قيد التطوير...")
                
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
    
    def run(self):
        """تشغيل البوت"""
        try:
            # إعداد الأوامر السريعة
            asyncio.run(self.setup_commands())
            
            # تشغيل البوت
            logger.info("🚀 بدء تشغيل البوت المحسن...")
            self.application.run_polling(drop_pending_updates=True)
            
        except Exception as e:
            logger.error(f"خطأ حرج في تشغيل البوت: {e}")
            raise
    
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
        # إنشاء وتشغيل البوت
        bot = YemenNetBot()
        bot.run()
        
    except KeyboardInterrupt:
        logger.info("تم إيقاف البوت بواسطة المستخدم")
    except Exception as e:
        logger.error(f"خطأ حرج في main: {e}")
        raise

if __name__ == '__main__':
    main()