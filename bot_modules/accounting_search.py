#!/usr/bin/env python3
"""
Accounting Search System - نظام البحث في المعاملات المحاسبية
"""

import logging
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext

from bot_modules.database import get_db_connection, get_db_context
from bot_modules.utils import get_user
from bot_modules.config import EMOJIS

logger = logging.getLogger(__name__)

class AccountingSearch:
    """نظام البحث في المعاملات المحاسبية"""
    
    @staticmethod
    async def show_search_options(update: Update, context: CallbackContext):
        """عرض خيارات البحث"""
        try:
            query = update.callback_query
            await query.answer()
            
            user = get_user(query.from_user.id)
            if not user or user['role'] not in ['admin', 'super_admin']:
                await query.edit_message_text(f"{EMOJIS['error']} هذه الميزة مقتصرة على الإدارة.")
                return
            
            search_text = f"""
🔍 **البحث في المعاملات المحاسبية** 🔍

👑 **المشرف:** {user['full_name']}

📋 **خيارات البحث المتاحة:**

👤 **البحث بالمستخدم:**
• البحث بالاسم
• البحث برقم الهاتف
• البحث برقم المحفظة

💰 **البحث بالمعاملة:**
• البحث برقم المعاملة
• البحث بنوع المعاملة
• البحث بالمبلغ

📅 **البحث بالتاريخ:**
• معاملات يوم محدد
• معاملات فترة محددة
• آخر المعاملات

🔍 اختر نوع البحث المطلوب:
"""
            
            keyboard = [
                [InlineKeyboardButton('👤 البحث بالمستخدم', callback_data='search_by_user'),
                 InlineKeyboardButton('💰 البحث بالمعاملة', callback_data='search_by_transaction')],
                [InlineKeyboardButton('📅 البحث بالتاريخ', callback_data='search_by_date'),
                 InlineKeyboardButton('💵 البحث بالمبلغ', callback_data='search_by_amount')],
                [InlineKeyboardButton('📊 إحصائيات سريعة', callback_data='quick_stats'),
                 InlineKeyboardButton('📈 تقرير سريع', callback_data='quick_transaction_report')],
                [InlineKeyboardButton('🔙 العودة للنظام المحاسبي', callback_data='accounting_system')]
            ]
            
            await query.edit_message_text(
                search_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Error showing search options: {e}")
            await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في عرض خيارات البحث.")

    @staticmethod
    async def quick_stats_handler(update: Update, context: CallbackContext):
        """إحصائيات سريعة للمعاملات"""
        try:
            query = update.callback_query
            await query.answer()
            
            user = get_user(query.from_user.id)
            if not user or user['role'] not in ['admin', 'super_admin']:
                await query.edit_message_text(f"{EMOJIS['error']} هذه الميزة مقتصرة على الإدارة.")
                return
            
            with get_db_context() as conn:

            
                cursor = conn.cursor()
            # إحصائيات اليوم
            cursor.execute('''
                SELECT type, COUNT(*), SUM(amount)
                FROM transactions 
                WHERE DATE(created_at) = DATE('now')
                GROUP BY type
            ''')
            today_stats = cursor.fetchall()
            
            # إحصائيات الأسبوع
            cursor.execute('''
                SELECT type, COUNT(*), SUM(amount)
                FROM transactions 
                WHERE created_at >= datetime('now', '-7 days')
                GROUP BY type
            ''')
            week_stats = cursor.fetchall()
            
            # إجمالي المعاملات
            cursor.execute('SELECT COUNT(*), SUM(amount) FROM transactions')
            total_stats = cursor.fetchone()            stats_text = f"""
📊 **إحصائيات المعاملات السريعة** 📊

📅 **معاملات اليوم:**
"""
            
            if today_stats:
                for stat in today_stats:
                    stats_text += f"• {stat[0]}: {stat[1]} معاملة ({stat[2]:,.2f} ريال)\n"
            else:
                stats_text += "• لا توجد معاملات اليوم\n"
            
            stats_text += f"""
📅 **معاملات آخر 7 أيام:**
"""
            
            if week_stats:
                for stat in week_stats:
                    stats_text += f"• {stat[0]}: {stat[1]} معاملة ({stat[2]:,.2f} ريال)\n"
            else:
                stats_text += "• لا توجد معاملات هذا الأسبوع\n"
            
            stats_text += f"""
📈 **الإجماليات:**
• إجمالي المعاملات: {total_stats[0]:,} معاملة
• إجمالي المبالغ: {total_stats[1]:,.2f} ريال
• متوسط المعاملة: {(total_stats[1] / max(total_stats[0], 1)):,.2f} ريال

⏰ **آخر تحديث:** {datetime.now().strftime('%Y-%m-%d %H:%M')}
"""
            
            keyboard = [
                [InlineKeyboardButton('📊 تقرير مفصل', callback_data='accounting_transactions'),
                 InlineKeyboardButton('💾 تصدير البيانات', callback_data='export_profits')],
                [InlineKeyboardButton('🔍 بحث متقدم', callback_data='accounting_search'),
                 InlineKeyboardButton('🔙 العودة', callback_data='accounting_system')]
            ]
            
            await query.edit_message_text(
                stats_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Error in quick stats: {e}")
            await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في عرض الإحصائيات.")

    @staticmethod
    async def quick_transaction_report(update: Update, context: CallbackContext):
        """تقرير معاملات سريع"""
        try:
            query = update.callback_query
            await query.answer()
            
            user = get_user(query.from_user.id)
            if not user or user['role'] not in ['admin', 'super_admin']:
                await query.edit_message_text(f"{EMOJIS['error']} هذه الميزة مقتصرة على الإدارة.")
                return
            
            with get_db_context() as conn:

            
                cursor = conn.cursor()
            # آخر 10 معاملات
            cursor.execute('''
                SELECT t.id, t.type, t.amount, t.description, t.created_at,
                       COALESCE(uf.full_name, ut.full_name, 'غير محدد') as user_name
                FROM transactions t
                LEFT JOIN users uf ON t.from_user = uf.id
                LEFT JOIN users ut ON t.to_user = ut.id
                ORDER BY t.created_at DESC
                LIMIT 10
            ''')
            
            recent_transactions = cursor.fetchall()            report_text = f"""
📋 **تقرير المعاملات السريع** 📋

⏰ **آخر 10 معاملات:**

"""
            
            if recent_transactions:
                for i, trans in enumerate(recent_transactions, 1):
                    trans_id, trans_type, amount, description, created_at, user_name = trans
                    
                    # أيقونات أنواع المعاملات
                    type_icons = {
                        'transfer': '🔄',
                        'card_purchase': '🛒',
                        'coupon_redeem': '🎟️',
                        'commission': '🎯',
                        'money_creation': '💰',
                        'transfer_fee': '💳'
                    }
                    
                    type_icon = type_icons.get(trans_type, '💼')
                    
                    report_text += f"""
{i}️⃣ **{type_icon} {trans_type}**
👤 المستخدم: {user_name}
💰 المبلغ: {amount:,.2f} ريال
📅 التاريخ: {created_at[:16]}
🆔 المعرف: {trans_id[:8]}...
━━━━━━━━━━━━━━━━━━━
"""
            else:
                report_text += "❌ لا توجد معاملات حديثة"
            
            keyboard = [
                [InlineKeyboardButton('📊 تقرير مفصل', callback_data='accounting_transactions'),
                 InlineKeyboardButton('💾 تصدير كامل', callback_data='export_comprehensive_30')],
                [InlineKeyboardButton('🔍 بحث متقدم', callback_data='accounting_search'),
                 InlineKeyboardButton('🔙 العودة', callback_data='accounting_system')]
            ]
            
            await query.edit_message_text(
                report_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Error in quick transaction report: {e}")
            await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في تقرير المعاملات.")

# دوال مساعدة للاستدعاء
async def accounting_search_handler(update: Update, context: CallbackContext):
    """معالج البحث في المعاملات"""
    return await AccountingSearch.show_search_options(update, context)

async def quick_stats_handler(update: Update, context: CallbackContext):
    """معالج الإحصائيات السريعة"""
    return await AccountingSearch.quick_stats_handler(update, context)

async def quick_transaction_report_handler(update: Update, context: CallbackContext):
    """معالج تقرير المعاملات السريع"""
    return await AccountingSearch.quick_transaction_report(update, context)