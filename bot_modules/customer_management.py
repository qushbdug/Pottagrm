#!/usr/bin/env python3
"""
Enhanced Customer Management System
نظام إدارة العملاء المطور
"""

import logging
import sqlite3
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext

from bot_modules.config import EMOJIS, USER_ROLES
from bot_modules.database import get_db_connection
from bot_modules.utils import get_user, update_user_activity

logger = logging.getLogger(__name__)

class CustomerManagement:
    """نظام إدارة العملاء المطور"""
    
    @staticmethod
    async def get_customer_dashboard(update: Update, context: CallbackContext):
        """لوحة تحكم إدارة العملاء"""
        try:
            query = update.callback_query
            await query.answer()
            
            user = get_user(query.from_user.id)
            if not user or user['role'] not in ['admin', 'super_admin']:
                await query.edit_message_text(f"{EMOJIS['error']} ليس لديك صلاحية لهذه العملية.")
                return
            
            # إحصائيات العملاء
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # إجمالي العملاء
            cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'customer'")
            total_customers = cursor.fetchone()[0]
            
            # العملاء النشطين (تفاعلوا خلال آخر 30 يوم)
            cursor.execute("""
                SELECT COUNT(*) FROM users 
                WHERE role = 'customer' 
                AND last_activity >= datetime('now', '-30 days')
            """)
            active_customers = cursor.fetchone()[0]
            
            # العملاء الجدد (آخر 7 أيام)
            cursor.execute("""
                SELECT COUNT(*) FROM users 
                WHERE role = 'customer' 
                AND created_at >= datetime('now', '-7 days')
            """)
            new_customers = cursor.fetchone()[0]
            
            # إجمالي المعاملات
            cursor.execute("""
                SELECT COUNT(*), COALESCE(SUM(amount), 0) 
                FROM transactions 
                WHERE from_user IN (SELECT id FROM users WHERE role = 'customer')
            """)
            total_transactions, total_amount = cursor.fetchone()
            
            # أكبر رصيد
            cursor.execute("""
                SELECT MAX(balance), full_name 
                FROM users 
                WHERE role = 'customer' AND balance > 0
            """)
            max_balance_result = cursor.fetchone()
            max_balance = max_balance_result[0] if max_balance_result[0] else 0
            top_customer = max_balance_result[1] if max_balance_result[1] else "لا يوجد"
            
            conn.close()
            
            dashboard_text = f"""
👥 **لوحة إدارة العملاء** 👥

📊 **إحصائيات شاملة:**

👤 **العملاء:**
• إجمالي العملاء: **{total_customers:,}** عميل
• العملاء النشطين: **{active_customers:,}** عميل
• عملاء جدد (7 أيام): **{new_customers:,}** عميل
• معدل النشاط: **{(active_customers/total_customers*100) if total_customers > 0 else 0:.1f}%**

💰 **المعاملات:**
• إجمالي المعاملات: **{total_transactions:,}** معاملة
• قيمة المعاملات: **{total_amount:,.2f}** ريال
• متوسط المعاملة: **{(total_amount/total_transactions) if total_transactions > 0 else 0:.2f}** ريال

🏆 **أعلى رصيد:**
• العميل: **{top_customer}**
• الرصيد: **{max_balance:,.2f}** ريال

⏰ **آخر تحديث:** {datetime.now().strftime('%Y-%m-%d %H:%M')}
"""
            
            keyboard = [
                [InlineKeyboardButton('🔍 البحث عن عميل', callback_data='customer_search'),
                 InlineKeyboardButton('📋 قائمة العملاء', callback_data='customer_list')],
                [InlineKeyboardButton('📊 تقارير مفصلة', callback_data='customer_reports'),
                 InlineKeyboardButton('💰 إدارة الأرصدة', callback_data='customer_balance_mgmt')],
                [InlineKeyboardButton('🚫 العملاء المحظورون', callback_data='customer_banned'),
                 InlineKeyboardButton('📈 إحصائيات متقدمة', callback_data='customer_analytics')],
                [InlineKeyboardButton('📞 دعم العملاء', callback_data='customer_support'),
                 InlineKeyboardButton('🎁 حوافز العملاء', callback_data='customer_incentives')],
                [InlineKeyboardButton('🔙 العودة للإدارة', callback_data='admin_panel')]
            ]
            
            await query.edit_message_text(
                dashboard_text, 
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Error in customer dashboard: {e}")
            await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في لوحة إدارة العملاء.")

    @staticmethod
    async def search_customers(update: Update, context: CallbackContext):
        """البحث عن العملاء"""
        try:
            query = update.callback_query
            await query.answer()
            
            search_text = """
🔍 **البحث عن العملاء** 🔍

💡 **طرق البحث المتاحة:**

📱 **بالهاتف:** أرسل رقم الهاتف
💳 **برقم المحفظة:** أرسل رقم المحفظة  
👤 **بالاسم:** أرسل اسم العميل
🆔 **بالمعرف:** أرسل معرف Telegram

📋 **أو اختر من القوائم:**
"""
            
            keyboard = [
                [InlineKeyboardButton('👥 العملاء النشطين', callback_data='customer_list_active'),
                 InlineKeyboardButton('😴 العملاء غير النشطين', callback_data='customer_list_inactive')],
                [InlineKeyboardButton('💰 أعلى الأرصدة', callback_data='customer_list_top_balance'),
                 InlineKeyboardButton('📈 أكثر نشاطاً', callback_data='customer_list_most_active')],
                [InlineKeyboardButton('🆕 عملاء جدد', callback_data='customer_list_new'),
                 InlineKeyboardButton('⚠️ عملاء مشكوك فيهم', callback_data='customer_list_suspicious')],
                [InlineKeyboardButton('🔙 العودة', callback_data='customer_dashboard')]
            ]
            
            await query.edit_message_text(
                search_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Error in customer search: {e}")
            await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في البحث.")

    @staticmethod
    async def get_customer_details(customer_id: int):
        """الحصول على تفاصيل العميل"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # معلومات العميل الأساسية
            cursor.execute("""
                SELECT id, telegram_id, full_name, phone, balance, wallet_number, 
                       created_at, last_activity, is_active, total_purchases, total_spent
                FROM users WHERE id = ? AND role = 'customer'
            """, (customer_id,))
            
            customer = cursor.fetchone()
            if not customer:
                return None
            
            # إحصائيات المعاملات
            cursor.execute("""
                SELECT COUNT(*) as count, COALESCE(SUM(amount), 0) as total
                FROM transactions WHERE from_user = ?
            """, (customer_id,))
            sent_stats = cursor.fetchone()
            
            cursor.execute("""
                SELECT COUNT(*) as count, COALESCE(SUM(amount), 0) as total
                FROM transactions WHERE to_user = ?
            """, (customer_id,))
            received_stats = cursor.fetchone()
            
            # آخر النشاطات
            cursor.execute("""
                SELECT type, amount, description, created_at
                FROM transactions 
                WHERE from_user = ? OR to_user = ?
                ORDER BY created_at DESC LIMIT 5
            """, (customer_id, customer_id))
            
            recent_activities = cursor.fetchall()
            
            conn.close()
            
            return {
                'customer': customer,
                'sent_stats': sent_stats,
                'received_stats': received_stats,
                'recent_activities': recent_activities
            }
            
        except Exception as e:
            logger.error(f"Error getting customer details: {e}")
            return None

    @staticmethod
    async def show_customer_profile(update: Update, context: CallbackContext, customer_id: int):
        """عرض ملف العميل التفصيلي"""
        try:
            query = update.callback_query
            
            customer_data = await CustomerManagement.get_customer_details(customer_id)
            if not customer_data:
                await query.edit_message_text(f"{EMOJIS['error']} لم يتم العثور على العميل.")
                return
            
            customer = customer_data['customer']
            sent_stats = customer_data['sent_stats']
            received_stats = customer_data['received_stats']
            recent_activities = customer_data['recent_activities']
            
            # حساب مدة العضوية
            created_date = datetime.strptime(customer['created_at'], '%Y-%m-%d %H:%M:%S')
            membership_days = (datetime.now() - created_date).days
            
            # حساب آخر نشاط
            if customer['last_activity']:
                last_activity = datetime.strptime(customer['last_activity'], '%Y-%m-%d %H:%M:%S')
                days_since_activity = (datetime.now() - last_activity).days
                activity_status = "نشط" if days_since_activity <= 7 else f"غير نشط منذ {days_since_activity} يوم"
            else:
                activity_status = "لم يسجل نشاط"
            
            profile_text = f"""
👤 **ملف العميل التفصيلي** 👤

📋 **المعلومات الأساسية:**
👤 الاسم: **{customer['full_name']}**
📱 الهاتف: **{customer['phone'] or 'غير محدد'}**
💳 رقم المحفظة: **{customer['wallet_number']}**
🆔 معرف Telegram: **{customer['telegram_id']}**
💰 الرصيد الحالي: **{customer['balance']:,.2f}** ريال

📊 **إحصائيات العضوية:**
📅 تاريخ التسجيل: **{customer['created_at'][:10]}**
⏱️ مدة العضوية: **{membership_days}** يوم
🟢 حالة النشاط: **{activity_status}**
✅ حالة الحساب: **{'مفعل' if customer['is_active'] else 'غير مفعل'}**

💰 **إحصائيات المعاملات:**
📤 المرسل: **{sent_stats['count']}** معاملة بقيمة **{sent_stats['total']:,.2f}** ريال
📥 المستلم: **{received_stats['count']}** معاملة بقيمة **{received_stats['total']:,.2f}** ريال
🛒 إجمالي المشتريات: **{customer['total_purchases'] or 0}** عملية
💸 إجمالي المصروف: **{customer['total_spent'] or 0:,.2f}** ريال

📈 **نشاطات حديثة:**
"""
            
            if recent_activities:
                for activity in recent_activities[:3]:
                    activity_type = {
                        'transfer': 'تحويل رصيد',
                        'card_purchase': 'شراء كرت',
                        'coupon_redeem': 'استخدام كوبون',
                        'recharge': 'شحن رصيد'
                    }.get(activity['type'], activity['type'])
                    
                    profile_text += f"• **{activity_type}**: {activity['amount']:,.2f} ريال - {activity['created_at'][:10]}\n"
            else:
                profile_text += "• لا توجد نشاطات حديثة\n"
            
            keyboard = [
                [InlineKeyboardButton('💰 إدارة الرصيد', callback_data=f'customer_balance_{customer_id}'),
                 InlineKeyboardButton('📊 تقرير مفصل', callback_data=f'customer_report_{customer_id}')],
                [InlineKeyboardButton('💬 إرسال رسالة', callback_data=f'customer_message_{customer_id}'),
                 InlineKeyboardButton('🚫 إدارة الحظر', callback_data=f'customer_ban_{customer_id}')],
                [InlineKeyboardButton('🔄 تحديث البيانات', callback_data=f'customer_refresh_{customer_id}'),
                 InlineKeyboardButton('📋 سجل النشاطات', callback_data=f'customer_activities_{customer_id}')],
                [InlineKeyboardButton('🔙 العودة للبحث', callback_data='customer_search')]
            ]
            
            await query.edit_message_text(
                profile_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Error showing customer profile: {e}")
            await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في عرض ملف العميل.")

    @staticmethod
    async def get_customer_analytics(update: Update, context: CallbackContext):
        """تحليلات العملاء المتقدمة"""
        try:
            query = update.callback_query
            await query.answer()
            
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # تحليل نشاط العملاء
            cursor.execute("""
                SELECT 
                    COUNT(CASE WHEN last_activity >= datetime('now', '-1 days') THEN 1 END) as daily_active,
                    COUNT(CASE WHEN last_activity >= datetime('now', '-7 days') THEN 1 END) as weekly_active,
                    COUNT(CASE WHEN last_activity >= datetime('now', '-30 days') THEN 1 END) as monthly_active,
                    COUNT(*) as total
                FROM users WHERE role = 'customer'
            """)
            activity_stats = cursor.fetchone()
            
            # أكثر الشبكات شراءً
            cursor.execute("""
                SELECT n.name, COUNT(*) as purchases
                FROM transactions t
                JOIN users u ON t.from_user = u.id
                JOIN networks n ON t.description LIKE '%' || n.name || '%'
                WHERE u.role = 'customer' AND t.type = 'card_purchase'
                GROUP BY n.name
                ORDER BY purchases DESC
                LIMIT 5
            """)
            popular_networks = cursor.fetchall()
            
            # توزيع الأرصدة
            cursor.execute("""
                SELECT 
                    COUNT(CASE WHEN balance = 0 THEN 1 END) as zero_balance,
                    COUNT(CASE WHEN balance BETWEEN 0.01 AND 100 THEN 1 END) as low_balance,
                    COUNT(CASE WHEN balance BETWEEN 100.01 AND 1000 THEN 1 END) as medium_balance,
                    COUNT(CASE WHEN balance > 1000 THEN 1 END) as high_balance
                FROM users WHERE role = 'customer'
            """)
            balance_distribution = cursor.fetchone()
            
            conn.close()
            
            analytics_text = f"""
📈 **تحليلات العملاء المتقدمة** 📈

👥 **نشاط العملاء:**
📅 نشطين اليوم: **{activity_stats[0]:,}** عميل
📅 نشطين هذا الأسبوع: **{activity_stats[1]:,}** عميل  
📅 نشطين هذا الشهر: **{activity_stats[2]:,}** عميل
📊 معدل النشاط الشهري: **{(activity_stats[2]/activity_stats[3]*100) if activity_stats[3] > 0 else 0:.1f}%**

💰 **توزيع الأرصدة:**
⚫ رصيد صفر: **{balance_distribution[0]:,}** عميل
🟡 رصيد منخفض (1-100): **{balance_distribution[1]:,}** عميل
🟠 رصيد متوسط (100-1000): **{balance_distribution[2]:,}** عميل
🟢 رصيد عالي (+1000): **{balance_distribution[3]:,}** عميل

🏆 **أكثر الشبكات شراءً:**
"""
            
            if popular_networks:
                for i, (network, count) in enumerate(popular_networks, 1):
                    analytics_text += f"{i}️⃣ **{network}**: {count:,} عملية شراء\n"
            else:
                analytics_text += "• لا توجد بيانات شراء حتى الآن\n"
            
            keyboard = [
                [InlineKeyboardButton('📊 تصدير التقرير', callback_data='customer_export_analytics'),
                 InlineKeyboardButton('🔄 تحديث البيانات', callback_data='customer_analytics')],
                [InlineKeyboardButton('📈 رسوم بيانية', callback_data='customer_charts'),
                 InlineKeyboardButton('📋 تقرير مخصص', callback_data='customer_custom_report')],
                [InlineKeyboardButton('🔙 العودة', callback_data='customer_dashboard')]
            ]
            
            await query.edit_message_text(
                analytics_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Error in customer analytics: {e}")
            await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في التحليلات.")

# إضافة الدوال للاستيراد
__all__ = ['CustomerManagement']