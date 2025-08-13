#!/usr/bin/env python3
"""
Yemen Net Bot - البوت الكامل في ملف واحد
نظام بوت تليجرام متطور لبيع كروت الشبكة مع ميزات متقدمة
"""

import logging
import asyncio
import os
import sys
import sqlite3
import json
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import (
    Application, 
    CommandHandler, 
    CallbackQueryHandler,
    PicklePersistence
)

# ============================================================================
# إعدادات البوت
# ============================================================================

# توكن البوت - محفوظ في الكود
BOT_TOKEN = '7766964799:AAHex-hGfjPX6g_R2aZ7-UPrgnFxQKAjSa0'

# إعدادات قاعدة البيانات
DB_PATH = 'yemen_net.db'

# إعدادات النظام
MIN_TRANSFER_AMOUNT = 1.0
MAX_TRANSFER_AMOUNT = 10000.0
MIN_WITHDRAWAL_AMOUNT = 10.0
REFERRAL_BONUS_AMOUNT = 5.0

# أوامر القائمة السريعة
QUICK_COMMANDS = [
    BotCommand('start', 'بدء استخدام البوت'),
    BotCommand('menu', 'القائمة الرئيسية'),
    BotCommand('balance', 'عرض الرصيد'),
    BotCommand('wallet', 'إدارة المحفظة'),
    BotCommand('stats', 'الإحصائيات'),
    BotCommand('rating', 'نظام التقييم'),
    BotCommand('help', 'المساعدة'),
]

# ============================================================================
# إعداد نظام السجلات
# ============================================================================

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ============================================================================
# إدارة قاعدة البيانات
# ============================================================================

class DatabaseManager:
    """مدير قاعدة البيانات"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """تهيئة قاعدة البيانات"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # جدول المستخدمين
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        telegram_id INTEGER UNIQUE NOT NULL,
                        username TEXT,
                        full_name TEXT NOT NULL,
                        wallet_number TEXT UNIQUE,
                        balance REAL DEFAULT 0.0,
                        is_active BOOLEAN DEFAULT 1,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # جدول المعاملات
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS transactions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        type TEXT NOT NULL,
                        amount REAL NOT NULL,
                        description TEXT,
                        status TEXT DEFAULT 'pending',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (id)
                    )
                ''')
                
                # جدول التقييمات
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS ratings (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
                        comment TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (id)
                    )
                ''')
                
                # جدول الإشعارات
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS notifications (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        title TEXT NOT NULL,
                        message TEXT NOT NULL,
                        is_read BOOLEAN DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (id)
                    )
                ''')
                
                conn.commit()
                logger.info("تم تهيئة قاعدة البيانات بنجاح")
                
        except Exception as e:
            logger.error(f"خطأ في تهيئة قاعدة البيانات: {e}")
            raise
    
    def get_cursor(self):
        """الحصول على cursor لقاعدة البيانات"""
        conn = sqlite3.connect(self.db_path)
        return conn, conn.cursor()
    
    def close_connection(self, conn):
        """إغلاق الاتصال بقاعدة البيانات"""
        if conn:
            conn.close()

# إنشاء مدير قاعدة البيانات
db_manager = DatabaseManager(DB_PATH)

# ============================================================================
# خدمات النظام
# ============================================================================

class NotificationService:
    """خدمة الإشعارات"""
    
    @staticmethod
    def send_notification(user_id: int, title: str, message: str) -> bool:
        """إرسال إشعار للمستخدم"""
        try:
            with db_manager.get_cursor() as (conn, cursor):
                cursor.execute('''
                    INSERT INTO notifications (user_id, title, message)
                    VALUES (?, ?, ?)
                ''', (user_id, title, message))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"خطأ في إرسال الإشعار: {e}")
            return False
    
    @staticmethod
    def mark_as_read(user_id: int, notification_id: int = None) -> bool:
        """تحديد الإشعار كمقروء"""
        try:
            with db_manager.get_cursor() as (conn, cursor):
                if notification_id:
                    cursor.execute('''
                        UPDATE notifications 
                        SET is_read = 1 
                        WHERE id = ? AND user_id = ?
                    ''', (notification_id, user_id))
                else:
                    cursor.execute('''
                        UPDATE notifications 
                        SET is_read = 1 
                        WHERE user_id = ?
                    ''', (user_id,))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"خطأ في تحديث الإشعار: {e}")
            return False

class RatingService:
    """خدمة التقييمات"""
    
    @staticmethod
    def add_rating(user_id: int, rating: int, comment: str = None) -> bool:
        """إضافة تقييم جديد"""
        try:
            with db_manager.get_cursor() as (conn, cursor):
                cursor.execute('''
                    INSERT INTO ratings (user_id, rating, comment)
                    VALUES (?, ?, ?)
                ''', (user_id, rating, comment))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"خطأ في إضافة التقييم: {e}")
            return False
    
    @staticmethod
    def get_average_rating() -> float:
        """الحصول على متوسط التقييم"""
        try:
            with db_manager.get_cursor() as (conn, cursor):
                cursor.execute('SELECT AVG(rating) FROM ratings')
                result = cursor.fetchone()
                return result[0] if result[0] else 0.0
        except Exception as e:
            logger.error(f"خطأ في جلب متوسط التقييم: {e}")
            return 0.0

class WalletService:
    """خدمة المحفظة"""
    
    @staticmethod
    def create_wallet(telegram_id: int, username: str, full_name: str) -> Optional[str]:
        """إنشاء محفظة جديدة"""
        try:
            with db_manager.get_cursor() as (conn, cursor):
                # إنشاء رقم محفظة فريد
                wallet_number = f"YN-{datetime.now().year}-{telegram_id:06d}"
                
                cursor.execute('''
                    INSERT INTO users (telegram_id, username, full_name, wallet_number, balance)
                    VALUES (?, ?, ?, ?, ?)
                ''', (telegram_id, username, full_name, wallet_number, 0.0))
                
                conn.commit()
                return wallet_number
        except Exception as e:
            logger.error(f"خطأ في إنشاء المحفظة: {e}")
            return None
    
    @staticmethod
    def get_wallet_info(telegram_id: int) -> Optional[Dict[str, Any]]:
        """الحصول على معلومات المحفظة"""
        try:
            with db_manager.get_cursor() as (conn, cursor):
                cursor.execute('''
                    SELECT wallet_number, balance, created_at, last_activity
                    FROM users WHERE telegram_id = ?
                ''', (telegram_id,))
                
                result = cursor.fetchone()
                if result:
                    return {
                        'wallet_number': result[0],
                        'balance': result[1],
                        'created_at': result[2],
                        'last_activity': result[3]
                    }
                return None
        except Exception as e:
            logger.error(f"خطأ في جلب معلومات المحفظة: {e}")
            return None
    
    @staticmethod
    def update_balance(telegram_id: int, amount: float, transaction_type: str, description: str) -> bool:
        """تحديث رصيد المحفظة"""
        try:
            with db_manager.get_cursor() as (conn, cursor):
                # تحديث الرصيد
                cursor.execute('''
                    UPDATE users 
                    SET balance = balance + ?, last_activity = CURRENT_TIMESTAMP
                    WHERE telegram_id = ?
                ''', (amount, telegram_id))
                
                # الحصول على user_id
                cursor.execute('SELECT id FROM users WHERE telegram_id = ?', (telegram_id,))
                user_id = cursor.fetchone()[0]
                
                # إضافة المعاملة
                cursor.execute('''
                    INSERT INTO transactions (user_id, type, amount, description, status)
                    VALUES (?, ?, ?, ?, 'completed')
                ''', (user_id, transaction_type, amount, description))
                
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"خطأ في تحديث الرصيد: {e}")
            return False

# إنشاء الخدمات
notification_service = NotificationService()
rating_service = RatingService()
wallet_service = WalletService()

# ============================================================================
# الفئة الرئيسية للبوت
# ============================================================================

class YemenNetBot:
    """الفئة الرئيسية للبوت"""
    
    def __init__(self):
        self.application = None
        self.setup_bot()
    
    def setup_bot(self):
        """إعداد البوت"""
        try:
            # إعداد البوت
            persistence = PicklePersistence(filepath='bot_data')
            self.application = Application.builder().token(BOT_TOKEN).persistence(persistence).build()
            
            # إعداد معالجات الأوامر
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
        self.application.add_handler(CommandHandler('help', self.help_command))
        self.application.add_handler(CommandHandler('balance', self.balance_command))
        self.application.add_handler(CommandHandler('wallet', self.wallet_command))
        self.application.add_handler(CommandHandler('stats', self.stats_command))
        self.application.add_handler(CommandHandler('rating', self.rating_command))
        self.application.add_handler(CommandHandler('notifications', self.notifications_command))
        
        # معالج الأزرار
        self.application.add_handler(CallbackQueryHandler(self.button_handler))
    
    async def start_command(self, update: Update, context):
        """أمر البداية"""
        user = update.effective_user
        
        try:
            # التحقق من وجود المستخدم
            wallet_info = wallet_service.get_wallet_info(user.id)
            
            if not wallet_info:
                # إنشاء محفظة جديدة
                wallet_number = wallet_service.create_wallet(
                    user.id, 
                    user.username, 
                    user.full_name
                )
                
                if wallet_number:
                    # إرسال إشعار ترحيب
                    with db_manager.get_cursor() as (conn, cursor):
                        cursor.execute('SELECT id FROM users WHERE telegram_id = ?', (user.id,))
                        user_id = cursor.fetchone()[0]
                        notification_service.send_notification(
                            user_id, 
                            "مرحباً بك!", 
                            "تم إنشاء محفظتك بنجاح!"
                        )
            
            welcome_text = """🌟 مرحباً بك في بوت يمن نت!

أهلاً وسهلاً بك! أنا بوت متطور لبيع كروت الشبكة
مع ميزات متقدمة ونظام محاسبي شامل.

اختر من القائمة أدناه:"""
            
            keyboard = [
                [InlineKeyboardButton("💰 المحفظة", callback_data="wallet_menu")],
                [InlineKeyboardButton("📊 الإحصائيات", callback_data="stats_menu")],
                [InlineKeyboardButton("⭐ التقييم", callback_data="rating_menu")],
                [InlineKeyboardButton("🔔 الإشعارات", callback_data="notifications_menu")],
                [InlineKeyboardButton("❓ المساعدة", callback_data="help_menu")]
            ]
            
            await update.message.reply_text(
                welcome_text,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        except Exception as e:
            logger.error(f"خطأ في أمر البداية: {e}")
            await update.message.reply_text("❌ حدث خطأ، يرجى المحاولة مرة أخرى.")
    
    async def menu_command(self, update: Update, context):
        """أمر القائمة الرئيسية"""
        await self.show_main_menu(update, context)
    
    async def help_command(self, update: Update, context):
        """أمر المساعدة"""
        help_text = """📚 دليل المساعدة - بوت يمن نت

الأوامر المتاحة:

🚀 الأوامر الأساسية:
/start - بدء استخدام البوت
/menu - القائمة الرئيسية
/help - عرض هذه المساعدة

💰 الأوامر المالية:
/balance - عرض الرصيد
/wallet - إدارة المحفظة

📊 الأوامر الإدارية:
/stats - الإحصائيات
/rating - التقييمات

🔔 الأوامر الأخرى:
/notifications - الإشعارات

💡 استخدم الأزرار للتنقل بين القوائم!"""
        
        await update.message.reply_text(help_text)
    
    async def balance_command(self, update: Update, context):
        """أمر عرض الرصيد"""
        user = update.effective_user
        
        try:
            wallet_info = wallet_service.get_wallet_info(user.id)
            
            if wallet_info:
                balance_text = f"""💰 رصيد المحفظة

🆔 رقم المحفظة: {wallet_info['wallet_number']}
💰 الرصيد الحالي: {wallet_info['balance']:.2f} ريال
📅 آخر تحديث: {wallet_info['last_activity']}

💡 استخدم /wallet لإدارة محفظتك"""
                
                keyboard = [[InlineKeyboardButton("🔙 العودة للقائمة", callback_data="main_menu")]]
                
                await update.message.reply_text(
                    balance_text,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            else:
                await update.message.reply_text("❌ لم يتم العثور على محفظتك. استخدم /start لإنشاء محفظة جديدة.")
                
        except Exception as e:
            logger.error(f"خطأ في أمر الرصيد: {e}")
            await update.message.reply_text("❌ حدث خطأ في جلب الرصيد.")
    
    async def wallet_command(self, update: Update, context):
        """أمر إدارة المحفظة"""
        await self.show_wallet_menu(update, context)
    
    async def stats_command(self, update: Update, context):
        """أمر الإحصائيات"""
        await self.show_stats_menu(update, context)
    
    async def rating_command(self, update: Update, context):
        """أمر التقييم"""
        await self.show_rating_menu(update, context)
    
    async def notifications_command(self, update: Update, context):
        """أمر الإشعارات"""
        await self.show_notifications_menu(update, context)
    
    async def show_main_menu(self, update: Update, context):
        """عرض القائمة الرئيسية"""
        text = """🏠 القائمة الرئيسية

اختر من الخيارات أدناه:"""
        
        keyboard = [
            [InlineKeyboardButton("💰 المحفظة", callback_data="wallet_menu")],
            [InlineKeyboardButton("📊 الإحصائيات", callback_data="stats_menu")],
            [InlineKeyboardButton("⭐ التقييم", callback_data="rating_menu")],
            [InlineKeyboardButton("🔔 الإشعارات", callback_data="notifications_menu")],
            [InlineKeyboardButton("❓ المساعدة", callback_data="help_menu")]
        ]
        
        if update.callback_query:
            await update.callback_query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            await update.message.reply_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
    
    async def show_wallet_menu(self, update: Update, context):
        """عرض قائمة المحفظة"""
        text = """💰 إدارة المحفظة

اختر من الخيارات أدناه:"""
        
        keyboard = [
            [InlineKeyboardButton("💳 معلومات المحفظة", callback_data="wallet_info")],
            [InlineKeyboardButton("💰 إضافة رصيد", callback_data="add_balance")],
            [InlineKeyboardButton("💸 سحب رصيد", callback_data="withdraw_balance")],
            [InlineKeyboardButton("📊 سجل المعاملات", callback_data="transaction_history")],
            [InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="main_menu")]
        ]
        
        if update.callback_query:
            await update.callback_query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            await update.message.reply_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
    
    async def show_stats_menu(self, update: Update, context):
        """عرض قائمة الإحصائيات"""
        try:
            with db_manager.get_cursor() as (conn, cursor):
                # إحصائيات المستخدمين
                cursor.execute('SELECT COUNT(*) FROM users')
                total_users = cursor.fetchone()[0]
                
                cursor.execute('SELECT COUNT(*) FROM users WHERE is_active = 1')
                active_users = cursor.fetchone()[0]
                
                # إحصائيات المعاملات
                cursor.execute('SELECT COUNT(*) FROM transactions')
                total_transactions = cursor.fetchone()[0]
                
                cursor.execute('SELECT SUM(amount) FROM transactions WHERE type = "deposit"')
                total_deposits = cursor.fetchone()[0] or 0.0
                
                # متوسط التقييم
                avg_rating = rating_service.get_average_rating()
            
            stats_text = f"""📊 الإحصائيات الشاملة

👥 المستخدمين:
• إجمالي المستخدمين: {total_users}
• المستخدمين النشطين: {active_users}

💰 المالية:
• إجمالي المعاملات: {total_transactions}
• إجمالي الإيداعات: {total_deposits:.2f} ريال

⭐ التقييمات:
• متوسط التقييم: {avg_rating:.1f}/5"""
            
            keyboard = [[InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="main_menu")]]
            
            if update.callback_query:
                await update.callback_query.edit_message_text(
                    stats_text,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            else:
                await update.message.reply_text(
                    stats_text,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                
        except Exception as e:
            logger.error(f"خطأ في عرض الإحصائيات: {e}")
            await update.message.reply_text("❌ حدث خطأ في جلب الإحصائيات.")
    
    async def show_rating_menu(self, update: Update, context):
        """عرض قائمة التقييم"""
        text = """⭐ نظام التقييم

اختر من الخيارات أدناه:"""
        
        keyboard = [
            [InlineKeyboardButton("⭐ تقييم الخدمة", callback_data="rate_service")],
            [InlineKeyboardButton("📊 التقييمات العامة", callback_data="view_ratings")],
            [InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="main_menu")]
        ]
        
        if update.callback_query:
            await update.callback_query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            await update.message.reply_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
    
    async def show_notifications_menu(self, update: Update, context):
        """عرض قائمة الإشعارات"""
        try:
            user = update.effective_user
            
            with db_manager.get_cursor() as (conn, cursor):
                cursor.execute('SELECT id FROM users WHERE telegram_id = ?', (user.id,))
                user_row = cursor.fetchone()
                
                if user_row:
                    user_id = user_row[0]
                    
                    # جلب الإشعارات
                    cursor.execute('''
                        SELECT id, title, message, is_read, created_at
                        FROM notifications 
                        WHERE user_id = ? 
                        ORDER BY created_at DESC 
                        LIMIT 10
                    ''', (user_id,))
                    
                    notifications = cursor.fetchall()
                    
                    if notifications:
                        text = "🔔 آخر الإشعارات:\n\n"
                        for notif in notifications:
                            status = "✅" if notif[3] else "🔔"
                            text += f"{status} {notif[1]}\n{notif[2]}\n\n"
                    else:
                        text = "🔔 لا توجد إشعارات جديدة"
                    
                    keyboard = [
                        [InlineKeyboardButton("✅ تحديد كمقروءة", callback_data="mark_read")],
                        [InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="main_menu")]
                    ]
                    
                    if update.callback_query:
                        await update.callback_query.edit_message_text(
                            text,
                            reply_markup=InlineKeyboardMarkup(keyboard)
                        )
                    else:
                        await update.message.reply_text(
                            text,
                            reply_markup=InlineKeyboardMarkup(keyboard)
                        )
                else:
                    await update.message.reply_text("❌ لم يتم العثور على حسابك.")
                    
        except Exception as e:
            logger.error(f"خطأ في عرض الإشعارات: {e}")
            await update.message.reply_text("❌ حدث خطأ في جلب الإشعارات.")
    
    async def button_handler(self, update: Update, context):
        """معالج الأزرار"""
        query = update.callback_query
        await query.answer()
        
        try:
            if query.data == "main_menu":
                await self.show_main_menu(update, context)
            elif query.data == "wallet_menu":
                await self.show_wallet_menu(update, context)
            elif query.data == "stats_menu":
                await self.show_stats_menu(update, context)
            elif query.data == "rating_menu":
                await self.show_rating_menu(update, context)
            elif query.data == "notifications_menu":
                await self.show_notifications_menu(update, context)
            elif query.data == "help_menu":
                await self.help_command(update, context)
            elif query.data == "wallet_info":
                await self.show_wallet_info(query)
            elif query.data == "add_balance":
                await self.show_add_balance_menu(query)
            elif query.data == "withdraw_balance":
                await self.show_withdraw_balance_menu(query)
            elif query.data == "transaction_history":
                await self.show_transaction_history(query)
            elif query.data == "rate_service":
                await self.show_rating_options(query)
            elif query.data == "view_ratings":
                await self.show_general_ratings(query)
            elif query.data == "mark_read":
                await self.mark_notifications_read(query)
            elif query.data.startswith("rate_"):
                rating = int(query.data.split("_")[1])
                await self.process_rating(query, rating)
            else:
                await query.edit_message_text("❌ خيار غير معروف")
                
        except Exception as e:
            logger.error(f"خطأ في معالج الأزرار: {e}")
            await query.edit_message_text("❌ حدث خطأ، يرجى المحاولة مرة أخرى.")
    
    async def show_wallet_info(self, query):
        """عرض معلومات المحفظة"""
        user = query.from_user
        
        try:
            wallet_info = wallet_service.get_wallet_info(user.id)
            
            if wallet_info:
                text = f"""📱 معلومات المحفظة

🆔 رقم المحفظة: {wallet_info['wallet_number']}
💰 الرصيد: {wallet_info['balance']:.2f} ريال
📅 تاريخ الإنشاء: {wallet_info['created_at']}
👤 المالك: {user.full_name}

🔒 محفظتك آمنة ومحمية بأحدث تقنيات التشفير"""
                
                keyboard = [[InlineKeyboardButton("🔙 العودة للمحفظة", callback_data="wallet_menu")]]
                
                await query.edit_message_text(
                    text,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            else:
                await query.edit_message_text("❌ لم يتم العثور على معلومات المحفظة.")
                
        except Exception as e:
            logger.error(f"خطأ في معلومات المحفظة: {e}")
            await query.edit_message_text("❌ حدث خطأ في جلب معلومات المحفظة.")
    
    async def show_add_balance_menu(self, query):
        """عرض قائمة إضافة الرصيد"""
        text = """💰 إضافة رصيد

اختر طريقة الدفع المناسبة:"""
        
        keyboard = [
            [InlineKeyboardButton("💳 بطاقة ائتمان/مدى", callback_data="pay_card")],
            [InlineKeyboardButton("🏦 تحويل بنكي", callback_data="pay_bank")],
            [InlineKeyboardButton("📱 محفظة إلكترونية", callback_data="pay_wallet")],
            [InlineKeyboardButton("🔙 العودة للمحفظة", callback_data="wallet_menu")]
        ]
        
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def show_withdraw_balance_menu(self, query):
        """عرض قائمة سحب الرصيد"""
        user = query.from_user
        
        try:
            wallet_info = wallet_service.get_wallet_info(user.id)
            
            if wallet_info and wallet_info['balance'] >= MIN_WITHDRAWAL_AMOUNT:
                text = f"""💸 سحب رصيد

💰 الرصيد المتاح: {wallet_info['balance']:.2f} ريال
💳 الحد الأدنى للسحب: {MIN_WITHDRAWAL_AMOUNT:.2f} ريال

اختر طريقة السحب:"""
                
                keyboard = [
                    [InlineKeyboardButton("🏦 تحويل بنكي", callback_data="withdraw_bank")],
                    [InlineKeyboardButton("📱 محفظة إلكترونية", callback_data="withdraw_wallet")],
                    [InlineKeyboardButton("🔙 العودة للمحفظة", callback_data="wallet_menu")]
                ]
            else:
                text = f"❌ رصيد غير كافي. الحد الأدنى للسحب: {MIN_WITHDRAWAL_AMOUNT:.2f} ريال"
                keyboard = [[InlineKeyboardButton("🔙 العودة للمحفظة", callback_data="wallet_menu")]]
            
            await query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
                
        except Exception as e:
            logger.error(f"خطأ في عرض قائمة السحب: {e}")
            await query.edit_message_text("❌ حدث خطأ في عرض قائمة السحب.")
    
    async def show_transaction_history(self, query):
        """عرض سجل المعاملات"""
        user = query.from_user
        
        try:
            with db_manager.get_cursor() as (conn, cursor):
                cursor.execute('SELECT id FROM users WHERE telegram_id = ?', (user.id,))
                user_row = cursor.fetchone()
                
                if user_row:
                    user_id = user_row[0]
                    
                    cursor.execute('''
                        SELECT type, amount, description, status, created_at
                        FROM transactions 
                        WHERE user_id = ? 
                        ORDER BY created_at DESC 
                        LIMIT 10
                    ''', (user_id,))
                    
                    transactions = cursor.fetchall()
                    
                    if transactions:
                        text = "📊 سجل المعاملات:\n\n"
                        for trans in transactions:
                            emoji = "💰" if trans[0] == "deposit" else "💸"
                            text += f"{emoji} {trans[0]}: {trans[1]:.2f} ريال\n"
                            text += f"📝 {trans[2]}\n"
                            text += f"📅 {trans[4]}\n\n"
                    else:
                        text = "📊 لا توجد معاملات حتى الآن"
                    
                    keyboard = [[InlineKeyboardButton("🔙 العودة للمحفظة", callback_data="wallet_menu")]]
                    
                    await query.edit_message_text(
                        text,
                        reply_markup=InlineKeyboardMarkup(keyboard)
                    )
                else:
                    await query.edit_message_text("❌ لم يتم العثور على حسابك.")
                    
        except Exception as e:
            logger.error(f"خطأ في عرض سجل المعاملات: {e}")
            await query.edit_message_text("❌ حدث خطأ في جلب سجل المعاملات.")
    
    async def show_rating_options(self, query):
        """عرض خيارات التقييم"""
        text = """⭐ تقييم الخدمة

كيف تقيم خدمتنا؟ اختر عدد النجوم:"""
        
        keyboard = [
            [InlineKeyboardButton("⭐", callback_data="rate_1")],
            [InlineKeyboardButton("⭐⭐", callback_data="rate_2")],
            [InlineKeyboardButton("⭐⭐⭐", callback_data="rate_3")],
            [InlineKeyboardButton("⭐⭐⭐⭐", callback_data="rate_4")],
            [InlineKeyboardButton("⭐⭐⭐⭐⭐", callback_data="rate_5")],
            [InlineKeyboardButton("🔙 العودة", callback_data="rating_menu")]
        ]
        
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def process_rating(self, query, rating):
        """معالجة التقييم"""
        user = query.from_user
        
        try:
            with db_manager.get_cursor() as (conn, cursor):
                cursor.execute('SELECT id FROM users WHERE telegram_id = ?', (user.id,))
                user_row = cursor.fetchone()
                
                if user_row:
                    user_id = user_row[0]
                    
                    if rating_service.add_rating(user_id, rating):
                        text = f"""✅ تم إرسال تقييمك بنجاح!

⭐ تقييمك: {rating}/5
👤 المستخدم: {user.full_name}
📅 التاريخ: {datetime.now().strftime('%Y-%m-%d %H:%M')}

شكراً لك على تقييمك! 🙏"""
                        
                        # إرسال إشعار
                        notification_service.send_notification(
                            user_id,
                            "تم إرسال تقييمك",
                            f"شكراً لك على تقييمك: {rating}/5 نجوم"
                        )
                    else:
                        text = "❌ حدث خطأ في إرسال التقييم"
                    
                    keyboard = [[InlineKeyboardButton("🔙 العودة للتقييم", callback_data="rating_menu")]]
                    
                    await query.edit_message_text(
                        text,
                        reply_markup=InlineKeyboardMarkup(keyboard)
                    )
                else:
                    await query.edit_message_text("❌ لم يتم العثور على حسابك.")
                    
        except Exception as e:
            logger.error(f"خطأ في معالجة التقييم: {e}")
            await query.edit_message_text("❌ حدث خطأ في إرسال التقييم.")
    
    async def show_general_ratings(self, query):
        """عرض التقييمات العامة"""
        try:
            with db_manager.get_cursor() as (conn, cursor):
                cursor.execute('SELECT COUNT(*) FROM ratings')
                total_ratings = cursor.fetchone()[0]
                
                avg_rating = rating_service.get_average_rating()
                
                cursor.execute('SELECT COUNT(*) FROM ratings WHERE rating = 5')
                five_star = cursor.fetchone()[0]
                
                text = f"""📊 التقييمات العامة

⭐ متوسط التقييم: {avg_rating:.1f}/5
📊 إجمالي التقييمات: {total_ratings}
🏆 تقييمات 5 نجوم: {five_star}

💡 ساعدنا في تحسين الخدمة بتقييمك!"""
                
                keyboard = [
                    [InlineKeyboardButton("⭐ تقييم الخدمة", callback_data="rate_service")],
                    [InlineKeyboardButton("🔙 العودة", callback_data="rating_menu")]
                ]
                
                await query.edit_message_text(
                    text,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                
        except Exception as e:
            logger.error(f"خطأ في عرض التقييمات العامة: {e}")
            await query.edit_message_text("❌ حدث خطأ في جلب التقييمات.")
    
    async def mark_notifications_read(self, query):
        """تحديد الإشعارات كمقروءة"""
        user = query.from_user
        
        try:
            with db_manager.get_cursor() as (conn, cursor):
                cursor.execute('SELECT id FROM users WHERE telegram_id = ?', (user.id,))
                user_row = cursor.fetchone()
                
                if user_row:
                    user_id = user_row[0]
                    
                    if notification_service.mark_as_read(user_id):
                        text = "✅ تم تحديد جميع الإشعارات كمقروءة"
                    else:
                        text = "❌ حدث خطأ في تحديث الإشعارات"
                    
                    keyboard = [[InlineKeyboardButton("🔙 العودة للإشعارات", callback_data="notifications_menu")]]
                    
                    await query.edit_message_text(
                        text,
                        reply_markup=InlineKeyboardMarkup(keyboard)
                    )
                else:
                    await query.edit_message_text("❌ لم يتم العثور على حسابك.")
                    
        except Exception as e:
            logger.error(f"خطأ في تحديد الإشعارات كمقروءة: {e}")
            await query.edit_message_text("❌ حدث خطأ في العملية.")
    
    async def setup_commands(self):
        """إعداد الأوامر السريعة"""
        try:
            await self.application.bot.set_my_commands(QUICK_COMMANDS)
            logger.info("تم إعداد الأوامر السريعة بنجاح")
        except Exception as e:
            logger.warning(f"فشل إعداد الأوامر السريعة: {e}")

# ============================================================================
# الدالة الرئيسية
# ============================================================================

async def main():
    """الدالة الرئيسية"""
    try:
        logger.info("🚀 بدء تشغيل بوت يمن نت...")
        
        # إنشاء البوت
        bot = YemenNetBot()
        
        # إعداد الأوامر السريعة
        await bot.setup_commands()
        
        # تشغيل البوت
        await bot.application.initialize()
        await bot.application.start()
        await bot.application.updater.start_polling(drop_pending_updates=True)
        
        logger.info("✅ البوت يعمل بنجاح!")
        
        # الانتظار إلى ما لا نهاية
        await asyncio.Event().wait()
        
    except KeyboardInterrupt:
        logger.info("تم إيقاف البوت بواسطة المستخدم")
    except Exception as e:
        logger.error(f"خطأ حرج في التشغيل: {e}")
        raise

if __name__ == '__main__':
    # تشغيل البوت
    asyncio.run(main())