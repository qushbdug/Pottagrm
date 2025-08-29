#!/usr/bin/env python3
"""
Enhanced Admin Management System
نظام إدارة المشرفين المطور
"""

import logging
import sqlite3
import json
import re
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext

from bot_modules.config import EMOJIS, USER_ROLES, PERMISSIONS
from bot_modules.database import get_db_connection
from bot_modules.utils import get_user, update_user_activity
from bot_modules.permissions import (
    AVAILABLE_PERMISSIONS, 
    has_permission, 
    grant_permission, 
    revoke_permission,
    get_admin_permissions,
    get_all_admins_with_permissions,
    check_permission_or_deny,
    initialize_admin_permissions
)

logger = logging.getLogger(__name__)

class AdminManagement:
    """نظام إدارة المشرفين المطور"""
    
    @staticmethod
    async def get_admin_dashboard(update: Update, context: CallbackContext):
        """لوحة تحكم إدارة المشرفين"""
        try:
            query = update.callback_query
            await query.answer()
            
            user = get_user(query.from_user.id)
            if not user or user['role'] != 'super_admin':
                await query.edit_message_text(f"{EMOJIS['error']} ليس لديك صلاحية لهذه العملية.")
                return
            
            # إحصائيات المشرفين
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # عدد المشرفين
            cursor.execute("SELECT COUNT(*) FROM users WHERE role IN ('admin', 'super_admin')")
            total_admins = cursor.fetchone()[0]
            
            # المشرفين النشطين (آخر 7 أيام)
            cursor.execute("""
                SELECT COUNT(*) FROM users 
                WHERE role IN ('admin', 'super_admin') 
                AND last_activity >= datetime('now', '-7 days')
            """)
            active_admins = cursor.fetchone()[0]
            
            # المشرفين حسب النوع
            cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'admin'")
            regular_admins = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'super_admin'")
            super_admins = cursor.fetchone()[0]
            
            # نشاطات المشرفين اليوم
            cursor.execute("""
                SELECT COUNT(*) FROM activity_logs 
                WHERE user_id IN (SELECT id FROM users WHERE role IN ('admin', 'super_admin'))
                AND DATE(created_at) = DATE('now')
            """)
            today_activities = cursor.fetchone()[0]
            
            # آخر النشاطات
            cursor.execute("""
                SELECT u.full_name, a.activity_type, a.description, a.created_at, u.role
                FROM activity_logs a
                JOIN users u ON a.user_id = u.id
                WHERE u.role IN ('admin', 'super_admin')
                ORDER BY a.created_at DESC
                LIMIT 5
            """)
            recent_activities = cursor.fetchall()
            
            conn.close()
            
            dashboard_text = f"""
👑 **لوحة إدارة المشرفين** 👑

📊 **إحصائيات شاملة:**

👤 **المشرفين:**
• إجمالي المشرفين: **{total_admins:,}** مشرف
• المشرفين النشطين: **{active_admins:,}** مشرف
• مشرفين عاديين: **{regular_admins:,}** مشرف
• مشرفين أعلى: **{super_admins:,}** مشرف
• معدل النشاط: **{(active_admins/total_admins*100) if total_admins > 0 else 0:.1f}%**

📈 **النشاط:**
• نشاطات اليوم: **{today_activities:,}** نشاط
• متوسط النشاط لكل مشرف: **{(today_activities/active_admins) if active_admins > 0 else 0:.1f}**

🔥 **آخر النشاطات:**
"""
            
            if recent_activities:
                for activity in recent_activities[:3]:
                    role_emoji = "👑" if activity[4] == 'super_admin' else "🛡️"  # role is now index 4
                    activity_text = activity[2] if activity[2] else activity[1]  # use description if available, otherwise activity_type
                    dashboard_text += f"• {role_emoji} **{activity[0]}**: {activity_text[:50]} - {activity[3][:16]}\n"  # created_at is now index 3
            else:
                dashboard_text += "• لا توجد نشاطات حديثة\n"
            
            dashboard_text += f"\n⏰ **آخر تحديث:** {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            
            keyboard = [
                [InlineKeyboardButton('👤 إدارة المشرفين', callback_data='admin_manage_admins'),
                 InlineKeyboardButton('🔍 البحث عن مشرف', callback_data='admin_search_admin')],
                [InlineKeyboardButton('➕ إضافة مشرف جديد', callback_data='admin_add_new'),
                 InlineKeyboardButton('🔐 إدارة الصلاحيات', callback_data='admin_permissions')],
                [InlineKeyboardButton('📊 تقارير المشرفين', callback_data='admin_reports'),
                 InlineKeyboardButton('📈 إحصائيات مفصلة', callback_data='admin_analytics')],
                [InlineKeyboardButton('⚠️ تحذيرات المشرفين', callback_data='admin_warnings'),
                 InlineKeyboardButton('🔒 أمان النظام', callback_data='admin_security')],
                [InlineKeyboardButton('📋 سجل النشاطات', callback_data='admin_activity_log'),
                 InlineKeyboardButton('⚙️ إعدادات الإدارة', callback_data='admin_settings')],
                [InlineKeyboardButton('🔙 العودة للوحة الرئيسية', callback_data='super_admin_panel')]
            ]
            
            await query.edit_message_text(
                dashboard_text, 
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Error in admin dashboard: {e}")
            await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في لوحة إدارة المشرفين.")

    @staticmethod
    async def manage_admins(update: Update, context: CallbackContext):
        """إدارة المشرفين"""
        try:
            query = update.callback_query
            await query.answer()
            
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # قائمة المشرفين
            cursor.execute("""
                SELECT id, full_name, phone, role, is_active, created_at, last_activity
                FROM users 
                WHERE role IN ('admin', 'super_admin')
                ORDER BY 
                    CASE role 
                        WHEN 'super_admin' THEN 1 
                        WHEN 'admin' THEN 2 
                    END,
                    last_activity DESC
            """)
            
            admins = cursor.fetchall()
            conn.close()
            
            if not admins:
                await query.edit_message_text(
                    "👑 **لا يوجد مشرفين في النظام**",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton('➕ إضافة مشرف جديد', callback_data='admin_add_new')],
                        [InlineKeyboardButton('🔙 العودة', callback_data='admin_dashboard')]
                    ])
                )
                return
            
            admins_text = """
👑 **قائمة المشرفين** 👑

📋 **المشرفين المسجلين:**

"""
            
            admin_buttons = []
            
            for i, admin in enumerate(admins, 1):
                admin_id, name, phone, role, is_active, created_at, last_activity = admin
                
                # رموز الحالة
                role_emoji = "👑" if role == 'super_admin' else "🛡️"
                status_emoji = "🟢" if is_active else "🔴"
                
                # حساب آخر نشاط
                if last_activity:
                    last_activity_date = datetime.strptime(last_activity, '%Y-%m-%d %H:%M:%S')
                    days_ago = (datetime.now() - last_activity_date).days
                    activity_text = f"منذ {days_ago} يوم" if days_ago > 0 else "اليوم"
                else:
                    activity_text = "لا يوجد نشاط"
                
                admins_text += f"""
{i}️⃣ {status_emoji} {role_emoji} **{name}**
   📱 الهاتف: {phone or 'غير محدد'}
   🏷️ الدور: **{'مشرف أعلى' if role == 'super_admin' else 'مشرف عادي'}**
   ⏰ آخر نشاط: {activity_text}
   📅 تاريخ الإضافة: {created_at[:10]}

"""
                
                # إضافة زر للمشرف
                button_text = f"{role_emoji} {name[:20]}{'...' if len(name) > 20 else ''}"
                admin_buttons.append([InlineKeyboardButton(
                    button_text, 
                    callback_data=f'admin_profile_{admin_id}'
                )])
            
            # إضافة أزرار التحكم
            admin_buttons.extend([
                [InlineKeyboardButton('➕ إضافة مشرف جديد', callback_data='admin_add_new'),
                 InlineKeyboardButton('🔄 تحديث القائمة', callback_data='admin_manage_admins')],
                [InlineKeyboardButton('🔙 العودة', callback_data='admin_dashboard')]
            ])
            
            await query.edit_message_text(
                admins_text,
                reply_markup=InlineKeyboardMarkup(admin_buttons),
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Error managing admins: {e}")
            await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في إدارة المشرفين.")

    @staticmethod
    async def show_admin_profile(update: Update, context: CallbackContext, admin_id: int):
        """عرض ملف المشرف"""
        try:
            query = update.callback_query
            await query.answer()
            
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # معلومات المشرف
            cursor.execute("""
                SELECT id, telegram_id, full_name, phone, role, is_active, 
                       created_at, last_activity, balance
                FROM users 
                WHERE id = ? AND role IN ('admin', 'super_admin')
            """, (admin_id,))
            
            admin = cursor.fetchone()
            if not admin:
                await query.edit_message_text(f"{EMOJIS['error']} لم يتم العثور على المشرف.")
                return
            
            # إحصائيات النشاط
            cursor.execute("""
                SELECT COUNT(*) FROM activity_logs 
                WHERE user_id = ? AND created_at >= datetime('now', '-30 days')
            """, (admin_id,))
            monthly_activities = cursor.fetchone()[0]
            
            cursor.execute("""
                SELECT COUNT(*) FROM activity_logs 
                WHERE user_id = ? AND DATE(created_at) = DATE('now')
            """, (admin_id,))
            daily_activities = cursor.fetchone()[0]
            
            # آخر النشاطات
            cursor.execute("""
                SELECT action, description, created_at 
                FROM activity_logs 
                WHERE user_id = ? 
                ORDER BY created_at DESC 
                LIMIT 5
            """, (admin_id,))
            recent_activities = cursor.fetchall()
            
            # الصلاحيات
            cursor.execute("""
                SELECT permission_name FROM user_permissions 
                WHERE user_id = ?
            """, (admin_id,))
            permissions = [row[0] for row in cursor.fetchall()]
            
            conn.close()
            
            # إعداد المعلومات
            role_emoji = "👑" if admin['role'] == 'super_admin' else "🛡️"
            status_emoji = "🟢" if admin['is_active'] else "🔴"
            
            # حساب مدة العضوية
            created_date = datetime.strptime(admin['created_at'], '%Y-%m-%d %H:%M:%S')
            membership_days = (datetime.now() - created_date).days
            
            # آخر نشاط
            if admin['last_activity']:
                last_activity_date = datetime.strptime(admin['last_activity'], '%Y-%m-%d %H:%M:%S')
                days_since_activity = (datetime.now() - last_activity_date).days
                activity_status = f"منذ {days_since_activity} يوم" if days_since_activity > 0 else "نشط اليوم"
            else:
                activity_status = "لم يسجل نشاط"
            
            profile_text = f"""
{role_emoji} **ملف المشرف التفصيلي** {role_emoji}

📋 **المعلومات الأساسية:**
👤 الاسم: **{admin['full_name']}**
📱 الهاتف: **{admin['phone'] or 'غير محدد'}**
🆔 معرف Telegram: **{admin['telegram_id']}**
🏷️ الدور: **{'مشرف أعلى' if admin['role'] == 'super_admin' else 'مشرف عادي'}**
{status_emoji} الحالة: **{'مفعل' if admin['is_active'] else 'غير مفعل'}**

📊 **إحصائيات العضوية:**
📅 تاريخ الإضافة: **{admin['created_at'][:10]}**
⏱️ مدة العضوية: **{membership_days}** يوم
🔥 آخر نشاط: **{activity_status}**

📈 **إحصائيات النشاط:**
📅 نشاطات اليوم: **{daily_activities}** نشاط
📊 نشاطات الشهر: **{monthly_activities}** نشاط
📋 متوسط النشاط اليومي: **{(monthly_activities/30):.1f}** نشاط

🔐 **الصلاحيات:**
"""
            
            if permissions:
                for permission in permissions[:5]:  # أول 5 صلاحيات
                    profile_text += f"• {permission}\n"
                if len(permissions) > 5:
                    profile_text += f"• و {len(permissions) - 5} صلاحيات أخرى...\n"
            else:
                profile_text += "• صلاحيات افتراضية حسب الدور\n"
            
            profile_text += "\n🔥 **آخر النشاطات:**\n"
            
            if recent_activities:
                for activity in recent_activities[:3]:
                    profile_text += f"• **{activity[0]}** - {activity[2][:16]}\n"
            else:
                profile_text += "• لا توجد نشاطات مسجلة\n"
            
            keyboard = [
                [InlineKeyboardButton('✏️ تعديل المعلومات', callback_data=f'admin_edit_{admin_id}'),
                 InlineKeyboardButton('🔐 إدارة الصلاحيات', callback_data=f'admin_perms_{admin_id}')],
                [InlineKeyboardButton('📊 تقرير مفصل', callback_data=f'admin_report_{admin_id}'),
                 InlineKeyboardButton('📋 سجل النشاطات', callback_data=f'admin_activities_{admin_id}')],
                [InlineKeyboardButton('💬 إرسال رسالة', callback_data=f'admin_message_{admin_id}'),
                 InlineKeyboardButton('⚠️ إدارة التحذيرات', callback_data=f'admin_warnings_{admin_id}')],
                [InlineKeyboardButton('🔄 تحديث البيانات', callback_data=f'admin_profile_{admin_id}'),
                 InlineKeyboardButton('🗑️ حذف المشرف', callback_data=f'admin_delete_{admin_id}')],
                [InlineKeyboardButton('🔙 العودة للقائمة', callback_data='admin_manage_admins')]
            ]
            
            await query.edit_message_text(
                profile_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Error showing admin profile: {e}")
            await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في عرض ملف المشرف.")

    @staticmethod
    async def get_admin_analytics(update: Update, context: CallbackContext):
        """تحليلات المشرفين المتقدمة"""
        try:
            query = update.callback_query
            await query.answer()
            
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # تحليل نشاط المشرفين
            cursor.execute("""
                SELECT 
                    u.full_name,
                    u.role,
                    COUNT(a.id) as total_activities,
                    COUNT(CASE WHEN DATE(a.created_at) = DATE('now') THEN 1 END) as today_activities,
                    MAX(a.created_at) as last_activity
                FROM users u
                LEFT JOIN activity_logs a ON u.id = a.user_id
                WHERE u.role IN ('admin', 'super_admin')
                GROUP BY u.id, u.full_name, u.role
                ORDER BY total_activities DESC
            """)
            admin_activities = cursor.fetchall()
            
            # أكثر الأنشطة تكراراً
            cursor.execute("""
                SELECT a.action, COUNT(*) as count
                FROM activity_logs a
                JOIN users u ON a.user_id = u.id
                WHERE u.role IN ('admin', 'super_admin')
                AND a.created_at >= datetime('now', '-30 days')
                GROUP BY a.action
                ORDER BY count DESC
                LIMIT 5
            """)
            popular_actions = cursor.fetchall()
            
            # نشاط المشرفين بالأيام
            cursor.execute("""
                SELECT DATE(created_at) as date, COUNT(*) as activities
                FROM activity_logs a
                JOIN users u ON a.user_id = u.id
                WHERE u.role IN ('admin', 'super_admin')
                AND a.created_at >= datetime('now', '-7 days')
                GROUP BY DATE(created_at)
                ORDER BY date DESC
            """)
            daily_activities = cursor.fetchall()
            
            conn.close()
            
            analytics_text = """
📈 **تحليلات المشرفين المتقدمة** 📈

👥 **أداء المشرفين:**
"""
            
            if admin_activities:
                for admin in admin_activities[:5]:  # أول 5 مشرفين
                    name, role, total, today, last = admin
                    role_emoji = "👑" if role == 'super_admin' else "🛡️"
                    analytics_text += f"• {role_emoji} **{name}**: {total} نشاط (اليوم: {today})\n"
            
            analytics_text += "\n🔥 **أكثر الأنشطة تكراراً (آخر 30 يوم):**\n"
            
            if popular_actions:
                for action, count in popular_actions:
                    analytics_text += f"• **{action}**: {count:,} مرة\n"
            else:
                analytics_text += "• لا توجد أنشطة مسجلة\n"
            
            analytics_text += "\n📊 **النشاط الأسبوعي:**\n"
            
            if daily_activities:
                for date, count in daily_activities:
                    analytics_text += f"• **{date}**: {count:,} نشاط\n"
            else:
                analytics_text += "• لا توجد أنشطة أسبوعية\n"
            
            keyboard = [
                [InlineKeyboardButton('📊 تصدير التقرير', callback_data='admin_export_analytics'),
                 InlineKeyboardButton('🔄 تحديث البيانات', callback_data='admin_analytics')],
                [InlineKeyboardButton('📈 رسوم بيانية', callback_data='admin_charts'),
                 InlineKeyboardButton('📋 تقرير مخصص', callback_data='admin_custom_report')],
                [InlineKeyboardButton('⚙️ إعدادات التحليل', callback_data='admin_analytics_settings'),
                 InlineKeyboardButton('📧 إرسال التقرير', callback_data='admin_send_report')],
                [InlineKeyboardButton('🔙 العودة', callback_data='admin_dashboard')]
            ]
            
            await query.edit_message_text(
                analytics_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Error in admin analytics: {e}")
            await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في تحليلات المشرفين.")

    @staticmethod
    async def admin_security_center(update: Update, context: CallbackContext):
        """مركز أمان المشرفين"""
        try:
            query = update.callback_query
            await query.answer()
            
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # فحص أنشطة مشبوهة
            cursor.execute("""
                SELECT 
                    u.full_name,
                    COUNT(a.id) as activities,
                    GROUP_CONCAT(DISTINCT a.action) as actions
                FROM users u
                JOIN activity_logs a ON u.id = a.user_id
                WHERE u.role IN ('admin', 'super_admin')
                AND a.created_at >= datetime('now', '-1 hours')
                GROUP BY u.id
                HAVING activities > 50  -- أكثر من 50 نشاط في الساعة
            """)
            suspicious_activities = cursor.fetchall()
            
            # فحص محاولات الوصول الفاشلة
            cursor.execute("""
                SELECT COUNT(*) FROM activity_logs 
                WHERE action LIKE '%failed%' OR action LIKE '%error%'
                AND created_at >= datetime('now', '-24 hours')
            """)
            failed_attempts = cursor.fetchone()[0]
            
            # آخر تغييرات الصلاحيات
            cursor.execute("""
                SELECT u.full_name, a.action, a.created_at, a.description
                FROM activity_logs a
                JOIN users u ON a.user_id = u.id
                WHERE a.action LIKE '%permission%' OR a.action LIKE '%role%'
                ORDER BY a.created_at DESC
                LIMIT 5
            """)
            permission_changes = cursor.fetchall()
            
            conn.close()
            
            security_text = f"""
🔒 **مركز أمان المشرفين** 🔒

⚠️ **التحذيرات الأمنية:**
"""
            
            if suspicious_activities:
                security_text += f"🚨 **أنشطة مشبوهة مكتشفة:** {len(suspicious_activities)} مشرف\n"
                for admin, count, actions in suspicious_activities:
                    security_text += f"• **{admin}**: {count} نشاط في الساعة الماضية\n"
            else:
                security_text += "✅ لا توجد أنشطة مشبوهة\n"
            
            security_text += f"""

📊 **إحصائيات الأمان:**
❌ محاولات فاشلة (24 ساعة): **{failed_attempts}** محاولة
🔐 مستوى الأمان: **{'مرتفع' if failed_attempts < 10 else 'متوسط' if failed_attempts < 50 else 'منخفض'}**

🔄 **آخر تغييرات الصلاحيات:**
"""
            
            if permission_changes:
                for admin, action, date, desc in permission_changes:
                    security_text += f"• **{admin}**: {action} - {date[:16]}\n"
            else:
                security_text += "• لا توجد تغييرات حديثة\n"
            
            keyboard = [
                [InlineKeyboardButton('🔍 فحص التهديدات', callback_data='admin_security_scan'),
                 InlineKeyboardButton('📋 سجل الأمان', callback_data='admin_security_log')],
                [InlineKeyboardButton('🔐 إعدادات الأمان', callback_data='admin_security_settings'),
                 InlineKeyboardButton('🚨 إنذارات الأمان', callback_data='admin_security_alerts')],
                [InlineKeyboardButton('👤 مراجعة المشرفين', callback_data='admin_security_review'),
                 InlineKeyboardButton('🔄 تدقيق الصلاحيات', callback_data='admin_permissions_audit')],
                [InlineKeyboardButton('🔙 العودة', callback_data='admin_dashboard')]
            ]
            
            await query.edit_message_text(
                security_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Error in admin security center: {e}")
            await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في مركز الأمان.")

    @staticmethod
    async def admin_permissions_handler(update: Update, context: CallbackContext):
        """🔐 نظام إدارة الصلاحيات المتقدم"""
        try:
            query = update.callback_query
            await query.answer()
            
            user = get_user(query.from_user.id)
            if not user or user['role'] != 'super_admin':
                await query.edit_message_text(f"{EMOJIS['error']} هذه الميزة مقتصرة على المشرف الأعلى فقط.")
                return
            
            # الحصول على جميع المشرفين مع صلاحياتهم
            admins_with_permissions = get_all_admins_with_permissions()
            
            permissions_text = f"""
🔐 **نظام إدارة الصلاحيات المتقدم** 🔐

👑 **الصلاحيات الأساسية:**
"""
            
            # عرض الصلاحيات المتاحة
            for perm_key, perm_info in AVAILABLE_PERMISSIONS.items():
                permissions_text += f"• **{perm_info['name_ar']}** (`{perm_key}`)\n"
            
            permissions_text += f"\n👥 **المشرفين المسجلين:** {len(admins_with_permissions)} مشرف\n"
            
            # إحصائيات الصلاحيات
            perm_stats = {}
            for perm_key in AVAILABLE_PERMISSIONS.keys():
                count = sum(1 for admin in admins_with_permissions if admin['permissions'].get(perm_key, False))
                perm_stats[perm_key] = count
            
            permissions_text += f"\n📊 **إحصائيات الصلاحيات:**\n"
            for perm_key, perm_info in AVAILABLE_PERMISSIONS.items():
                count = perm_stats.get(perm_key, 0)
                permissions_text += f"• {perm_info['name_ar']}: **{count}** مشرف\n"
            
            permissions_text += f"\n⚡ **اختر عملية:**"
            
            keyboard = [
                [InlineKeyboardButton('📋 عرض جميع المشرفين', callback_data='perm_list_all_admins'),
                 InlineKeyboardButton('🔍 البحث عن مشرف', callback_data='perm_search_admin')],
                [InlineKeyboardButton('⚙️ تعديل صلاحيات مشرف', callback_data='perm_edit_admin'),
                 InlineKeyboardButton('👥 مقارنة الصلاحيات', callback_data='perm_compare_admins')],
                [InlineKeyboardButton('📊 تقرير الصلاحيات المفصل', callback_data='perm_detailed_report'),
                 InlineKeyboardButton('🔄 مراجعة شاملة', callback_data='perm_full_audit')],
                [InlineKeyboardButton('➕ منح صلاحية جماعية', callback_data='perm_bulk_grant'),
                 InlineKeyboardButton('➖ سحب صلاحية جماعية', callback_data='perm_bulk_revoke')],
                [InlineKeyboardButton('🔙 العودة للوحة الإدارة', callback_data='admin_dashboard')]
            ]
            
            await query.edit_message_text(
                permissions_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Error in admin permissions handler: {e}")
            await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في نظام إدارة الصلاحيات.")

    @staticmethod
    async def list_all_admins_permissions(update: Update, context: CallbackContext):
        """📋 عرض جميع المشرفين مع صلاحياتهم"""
        try:
            query = update.callback_query
            await query.answer()
            
            admins_list = get_all_admins_with_permissions()
            
            if not admins_list:
                await query.edit_message_text(
                    f"{EMOJIS['error']} لا توجد مشرفين مسجلين في النظام.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton('🔙 العودة', callback_data='admin_permissions')]
                    ])
                )
                return
            
            # تقسيم القائمة إلى صفحات (5 مشرفين لكل صفحة)
            page = context.user_data.get('admin_perms_page', 0)
            items_per_page = 5
            start_idx = page * items_per_page
            end_idx = start_idx + items_per_page
            
            current_admins = admins_list[start_idx:end_idx]
            total_pages = (len(admins_list) - 1) // items_per_page + 1
            
            list_text = f"""
📋 **قائمة المشرفين والصلاحيات** 📋

📄 **الصفحة:** {page + 1} من {total_pages}
👥 **إجمالي المشرفين:** {len(admins_list)}

"""
            
            for admin in current_admins:
                role_emoji = "👑" if admin['role'] == 'super_admin' else "🛡️"
                status_emoji = "✅" if admin['is_active'] else "❌"
                
                list_text += f"""
{role_emoji} **{admin['full_name']}** {status_emoji}
🆔 معرف: `{admin['id']}` | 📱 تلجرام: `{admin['telegram_id']}`
🔑 **الصلاحيات:**
"""
                
                for perm_key, perm_info in AVAILABLE_PERMISSIONS.items():
                    has_perm = admin['permissions'].get(perm_key, False)
                    perm_emoji = "✅" if has_perm else "❌"
                    list_text += f"    {perm_emoji} {perm_info['name_ar']}\n"
                
                list_text += "───────────────────\n"
            
            # أزرار التنقل والعمليات
            keyboard = []
            
            # أزرار التنقل
            nav_buttons = []
            if page > 0:
                nav_buttons.append(InlineKeyboardButton('⬅️ السابق', callback_data=f'perm_page_{page-1}'))
            if page < total_pages - 1:
                nav_buttons.append(InlineKeyboardButton('➡️ التالي', callback_data=f'perm_page_{page+1}'))
            
            if nav_buttons:
                keyboard.append(nav_buttons)
            
            # أزرار العمليات للمشرفين الحاليين
            if current_admins:
                keyboard.append([InlineKeyboardButton('⚙️ اختر مشرف لتعديل صلاحياته', callback_data='perm_select_admin')])
                
                # أزرار سريعة للمشرفين
                admin_buttons = []
                for i, admin in enumerate(current_admins[:3]):  # أول 3 مشرفين فقط
                    admin_buttons.append(
                        InlineKeyboardButton(
                            f"⚙️ {admin['full_name'][:10]}",
                            callback_data=f"perm_quick_edit_{admin['id']}"
                        )
                    )
                if admin_buttons:
                    keyboard.append(admin_buttons)
            
            keyboard.append([InlineKeyboardButton('🔙 العودة لإدارة الصلاحيات', callback_data='admin_permissions')])
            
            await query.edit_message_text(
                list_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Error listing admins permissions: {e}")
            await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في عرض قائمة المشرفين.")

    @staticmethod
    async def edit_admin_permissions(update: Update, context: CallbackContext, admin_id: int):
        """⚙️ تعديل صلاحيات مشرف محدد"""
        try:
            query = update.callback_query
            await query.answer()
            
            # التحقق من المشرف الأعلى
            user = get_user(query.from_user.id)
            if not user or user['role'] != 'super_admin':
                await query.edit_message_text(f"{EMOJIS['error']} هذه الميزة مقتصرة على المشرف الأعلى.")
                return
            
            # الحصول على معلومات المشرف المستهدف
            target_admin = get_user(admin_id)
            if not target_admin or target_admin['role'] not in ['admin', 'super_admin']:
                await query.edit_message_text(f"{EMOJIS['error']} المشرف المستهدف غير موجود.")
                return
            
            # الحصول على صلاحيات المشرف الحالية
            admin_permissions = get_admin_permissions(admin_id)
            
            edit_text = f"""
⚙️ **تعديل صلاحيات المشرف** ⚙️

👤 **المشرف:** {target_admin['full_name']}
🆔 **المعرف:** `{admin_id}`
🛡️ **الرتبة:** {target_admin['role']}

🔑 **الصلاحيات الحالية:**

"""
            
            # عرض الصلاحيات مع إمكانية التبديل
            keyboard = []
            
            for perm_key, perm_info in AVAILABLE_PERMISSIONS.items():
                has_perm = admin_permissions.get(perm_key, False)
                status_emoji = "✅" if has_perm else "❌"
                action = "revoke" if has_perm else "grant"
                action_emoji = "❌ إلغاء" if has_perm else "✅ منح"
                
                edit_text += f"{status_emoji} **{perm_info['name_ar']}**\n"
                edit_text += f"    📝 {perm_info['description']}\n\n"
                
                # زر التبديل
                keyboard.append([
                    InlineKeyboardButton(
                        f"{action_emoji} {perm_info['name_ar']}",
                        callback_data=f"perm_{action}_{admin_id}_{perm_key}"
                    )
                ])
            
            edit_text += f"💡 **إرشادات:**\n"
            edit_text += f"• ✅ = الصلاحية مفعلة\n"
            edit_text += f"• ❌ = الصلاحية معطلة\n"
            edit_text += f"• اضغط على الزر لتبديل الحالة\n"
            
            # أزرار إضافية
            keyboard.append([
                InlineKeyboardButton('✅ منح جميع الصلاحيات', callback_data=f'perm_grant_all_{admin_id}'),
                InlineKeyboardButton('❌ سحب جميع الصلاحيات', callback_data=f'perm_revoke_all_{admin_id}')
            ])
            
            keyboard.append([
                InlineKeyboardButton('📋 عرض تقرير مفصل', callback_data=f'perm_report_{admin_id}'),
                InlineKeyboardButton('🔄 تحديث الصفحة', callback_data=f'perm_quick_edit_{admin_id}')
            ])
            
            keyboard.append([InlineKeyboardButton('🔙 العودة لقائمة المشرفين', callback_data='perm_list_all_admins')])
            
            await query.edit_message_text(
                edit_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Error editing admin permissions: {e}")
            await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في تعديل صلاحيات المشرف.")

    @staticmethod
    async def toggle_permission(update: Update, context: CallbackContext, action: str, admin_id: int, permission: str):
        """🔄 تبديل صلاحية محددة للمشرف"""
        try:
            query = update.callback_query
            await query.answer()
            
            user = get_user(query.from_user.id)
            if not user or user['role'] != 'super_admin':
                await query.edit_message_text(f"{EMOJIS['error']} ليس لديك صلاحية لهذه العملية.")
                return
            
            target_admin = get_user(admin_id)
            if not target_admin:
                await query.edit_message_text(f"{EMOJIS['error']} المشرف المستهدف غير موجود.")
                return
            
            # تنفيذ العملية
            success = False
            if action == "grant":
                success = grant_permission(admin_id, permission, user['id'])
                action_text = "منح"
            elif action == "revoke":
                success = revoke_permission(admin_id, permission, user['id'])
                action_text = "سحب"
            
            if success:
                perm_name = AVAILABLE_PERMISSIONS.get(permission, {}).get('name_ar', permission)
                await query.answer(f"✅ تم {action_text} صلاحية '{perm_name}' بنجاح!", show_alert=True)
                
                # إعادة عرض صفحة التعديل
                await AdminManagement.edit_admin_permissions(update, context, admin_id)
            else:
                await query.answer(f"❌ فشل في {action_text} الصلاحية!", show_alert=True)
            
        except Exception as e:
            logger.error(f"Error toggling permission: {e}")
            await query.answer("❌ حدث خطأ في تبديل الصلاحية!", show_alert=True)

    # ========== Complete Admin Management Functions ==========

    @staticmethod
    def log_admin_action(action_type: str, target_admin_id: int, performed_by: int, 
                        old_data: dict = None, new_data: dict = None, 
                        action_details: str = None, ip_address: str = None):
        """تسجيل عمليات إدارة المشرفين"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO admin_management_logs 
                (action_type, target_admin_id, performed_by, old_data, new_data, action_details, ip_address)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                action_type,
                target_admin_id,
                performed_by,
                json.dumps(old_data, ensure_ascii=False) if old_data else None,
                json.dumps(new_data, ensure_ascii=False) if new_data else None,
                action_details,
                ip_address
            ))
            
            conn.commit()
            conn.close()
            logger.info(f"Admin action logged: {action_type} on admin {target_admin_id} by {performed_by}")
            
        except Exception as e:
            logger.error(f"Error logging admin action: {e}")

    @staticmethod
    async def add_new_admin_handler(update: Update, context: CallbackContext):
        """➕ إضافة مشرف جديد"""
        try:
            query = update.callback_query
            await query.answer()
            
            user = get_user(query.from_user.id)
            if not user or user['role'] != 'super_admin':
                await query.edit_message_text(f"{EMOJIS['error']} هذه الميزة مقتصرة على المشرف الأعلى فقط.")
                return
            
            add_admin_text = f"""
➕ **إضافة مشرف جديد** ➕

👤 **خطوات إضافة المشرف:**

1️⃣ **إدخال معرف تلجرام**
   أرسل معرف تلجرام للمستخدم المراد ترقيته

2️⃣ **اختيار نوع المشرف**
   • مشرف عادي (صلاحيات محدودة)
   • مشرف أعلى (صلاحيات كاملة)

3️⃣ **تعيين الصلاحيات الأولية**
   سيتم تعيين صلاحيات افتراضية حسب النوع

⚡ **ملاحظات مهمة:**
• يجب أن يكون المستخدم مسجل في البوت
• لا يمكن إضافة مشرف أعلى إضافي إلا بموافقة خاصة
• سيتم تسجيل العملية في سجل الإدارة

💡 **ابدأ بإدخال معرف تلجرام:**
"""
            
            keyboard = [
                [InlineKeyboardButton('📝 إدخال معرف تلجرام', callback_data='add_admin_enter_id')],
                [InlineKeyboardButton('👥 اختيار من المستخدمين المسجلين', callback_data='add_admin_select_user')],
                [InlineKeyboardButton('📊 عرض حدود النظام', callback_data='add_admin_show_limits')],
                [InlineKeyboardButton('🔙 العودة للوحة الإدارة', callback_data='admin_dashboard')]
            ]
            
            await query.edit_message_text(
                add_admin_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Error in add new admin handler: {e}")
            await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في إضافة مشرف جديد.")

    @staticmethod
    async def add_admin_enter_id_handler(update: Update, context: CallbackContext):
        """معالج إدخال معرف تلجرام للمشرف الجديد"""
        try:
            query = update.callback_query
            await query.answer()
            
            # تعيين حالة انتظار معرف تلجرام
            context.user_data['awaiting_admin_telegram_id'] = True
            context.user_data['admin_add_step'] = 'enter_id'
            
            enter_id_text = f"""
📝 **إدخال معرف تلجرام** 📝

🔢 **أرسل معرف تلجرام للمستخدم:**

مثال: `123456789` أو `987654321`

⚠️ **تعليمات مهمة:**
• أرسل الرقم فقط بدون أي إضافات
• تأكد من صحة المعرف
• يجب أن يكون المستخدم مسجل في البوت

❌ **للإلغاء اكتب:** `إلغاء`
"""
            
            keyboard = [
                [InlineKeyboardButton('❌ إلغاء العملية', callback_data='add_admin_cancel')],
                [InlineKeyboardButton('🔙 العودة', callback_data='admin_add_new')]
            ]
            
            await query.edit_message_text(
                enter_id_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Error in enter admin ID handler: {e}")
            await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في إدخال معرف المشرف.")

    @staticmethod
    async def add_admin_select_user_handler(update: Update, context: CallbackContext):
        """👥 اختيار مشرف من المستخدمين المسجلين"""
        try:
            query = update.callback_query
            await query.answer()
            
            # الحصول على المستخدمين المؤهلين ليصبحوا مشرفين
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, telegram_id, full_name, role, total_purchases, is_active, created_at
                FROM users 
                WHERE role = 'customer' AND is_active = 1
                ORDER BY total_purchases DESC, created_at ASC
                LIMIT 20
            ''')
            
            eligible_users = cursor.fetchall()
            conn.close()
            
            if not eligible_users:
                await query.edit_message_text(
                    f"""
❌ **لا توجد مستخدمين مؤهلين**

لا يوجد مستخدمين عملاء مفعلين يمكن ترقيتهم لمشرفين.

💡 **الشروط المطلوبة:**
• حساب عميل مفعل
• لا يكون مشرف مسبقاً
• حساب نشط في النظام
""",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton('📝 إدخال معرف يدوياً', callback_data='add_admin_enter_id')],
                        [InlineKeyboardButton('🔙 العودة', callback_data='admin_add_new')]
                    ]),
                    parse_mode='Markdown'
                )
                return
            
            # تقسيم المستخدمين إلى صفحات
            page = context.user_data.get('add_admin_users_page', 0)
            items_per_page = 8
            start_idx = page * items_per_page
            end_idx = start_idx + items_per_page
            
            current_users = eligible_users[start_idx:end_idx]
            total_pages = (len(eligible_users) - 1) // items_per_page + 1
            
            select_text = f"""
👥 **اختيار مستخدم للترقية** 👥

📄 **الصفحة:** {page + 1} من {total_pages}
👤 **المستخدمين المؤهلين:** {len(eligible_users)}

"""
            
            keyboard = []
            
            for user_data in current_users:
                user_id, telegram_id, full_name, role, purchases, is_active, created = user_data
                
                # تحضير معلومات المستخدم
                purchases_text = f"{purchases} شراء" if purchases > 0 else "جديد"
                created_date = created[:10] if created else "غير محدد"
                
                select_text += f"""
👤 **{full_name}**
🆔 المعرف: `{telegram_id}`
📊 المشتريات: {purchases_text}
📅 التسجيل: {created_date}
───────────────────
"""
                
                keyboard.append([
                    InlineKeyboardButton(
                        f"✅ اختيار {full_name[:15]}",
                        callback_data=f"select_user_for_admin_{telegram_id}"
                    )
                ])
            
            # أزرار التنقل
            nav_buttons = []
            if page > 0:
                nav_buttons.append(InlineKeyboardButton('⬅️ السابق', callback_data=f'add_admin_users_page_{page-1}'))
            if page < total_pages - 1:
                nav_buttons.append(InlineKeyboardButton('➡️ التالي', callback_data=f'add_admin_users_page_{page+1}'))
            
            if nav_buttons:
                keyboard.append(nav_buttons)
            
            keyboard.extend([
                [InlineKeyboardButton('📝 إدخال معرف يدوياً', callback_data='add_admin_enter_id')],
                [InlineKeyboardButton('🔙 العودة', callback_data='admin_add_new')]
            ])
            
            await query.edit_message_text(
                select_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Error in select user for admin: {e}")
            await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في اختيار المستخدم.")

    @staticmethod
    async def process_admin_telegram_id(telegram_id: int, update: Update, context: CallbackContext):
        """معالجة معرف تلجرام للمشرف الجديد"""
        try:
            # البحث عن المستخدم
            target_user = get_user(telegram_id)
            
            if not target_user:
                error_text = f"""
❌ **مستخدم غير موجود** ❌

المعرف `{telegram_id}` غير مسجل في النظام.

💡 **يجب على المستخدم:**
• التسجيل في البوت أولاً باستخدام /start
• إكمال عملية التسجيل بالكامل

🔄 **جرب مرة أخرى:**
"""
                
                keyboard = [
                    [InlineKeyboardButton('📝 إدخال معرف آخر', callback_data='add_admin_enter_id')],
                    [InlineKeyboardButton('👥 اختيار من القائمة', callback_data='add_admin_select_user')],
                    [InlineKeyboardButton('🔙 العودة', callback_data='admin_add_new')]
                ]
                
                if hasattr(update, 'callback_query') and update.callback_query:
                    await update.callback_query.edit_message_text(
                        error_text,
                        reply_markup=InlineKeyboardMarkup(keyboard),
                        parse_mode='Markdown'
                    )
                else:
                    await update.message.reply_text(
                        error_text,
                        reply_markup=InlineKeyboardMarkup(keyboard),
                        parse_mode='Markdown'
                    )
                return
            
            # التحقق من أن المستخدم ليس مشرف بالفعل
            if target_user['role'] in ['admin', 'super_admin']:
                error_text = f"""
⚠️ **المستخدم مشرف بالفعل** ⚠️

👤 **المستخدم:** {target_user['full_name']}
🛡️ **الدور الحالي:** {target_user['role']}

💡 **خيارات متاحة:**
• تعديل صلاحياته من إدارة الصلاحيات
• البحث عن مستخدم آخر
"""
                
                keyboard = [
                    [InlineKeyboardButton('⚙️ تعديل صلاحياته', callback_data=f'perm_quick_edit_{target_user["id"]}')],
                    [InlineKeyboardButton('📝 إدخال معرف آخر', callback_data='add_admin_enter_id')],
                    [InlineKeyboardButton('🔙 العودة', callback_data='admin_add_new')]
                ]
                
                if hasattr(update, 'callback_query') and update.callback_query:
                    await update.callback_query.edit_message_text(
                        error_text,
                        reply_markup=InlineKeyboardMarkup(keyboard),
                        parse_mode='Markdown'
                    )
                else:
                    await update.message.reply_text(
                        error_text,
                        reply_markup=InlineKeyboardMarkup(keyboard),
                        parse_mode='Markdown'
                    )
                return
            
            # عرض تأكيد الترقية
            await AdminManagement.show_admin_promotion_confirmation(
                target_user, update, context
            )
            
        except Exception as e:
            logger.error(f"Error processing admin telegram ID: {e}")
            error_text = f"{EMOJIS['error']} حدث خطأ في معالجة معرف المشرف."
            
            if hasattr(update, 'callback_query') and update.callback_query:
                await update.callback_query.edit_message_text(error_text)
            else:
                await update.message.reply_text(error_text)

    @staticmethod
    async def show_admin_promotion_confirmation(target_user, update: Update, context: CallbackContext):
        """عرض تأكيد ترقية المستخدم لمشرف"""
        try:
            confirmation_text = f"""
✅ **تأكيد ترقية المستخدم** ✅

👤 **بيانات المستخدم:**
🔸 الاسم: **{target_user['full_name']}**
🔸 المعرف: `{target_user['telegram_id']}`
🔸 الهاتف: {target_user.get('phone', 'غير محدد')}
🔸 الدور الحالي: **{target_user['role']}**
🔸 الرصيد: **{target_user['balance']:.2f}** ريال
🔸 تاريخ التسجيل: {target_user.get('created_at', 'غير محدد')[:10]}

🛡️ **اختر نوع الترقية:**

**1️⃣ مشرف عادي:**
• إدارة العملاء ✅
• إرسال رسائل ✅  
• إضافة عروض ✅
• النظام المحاسبي ❌
• تفعيل مزودين ❌

**2️⃣ مشرف أعلى:**
• جميع الصلاحيات ✅
• إدارة المشرفين ✅
• النظام المحاسبي ✅
• تفعيل مزودين ✅

⚠️ **تحذير:** هذه العملية لا يمكن التراجع عنها بسهولة
"""
            
            # حفظ معرف المستخدم المستهدف
            context.user_data['target_admin_telegram_id'] = target_user['telegram_id']
            context.user_data['target_admin_db_id'] = target_user['id']
            
            keyboard = [
                [InlineKeyboardButton('🛡️ ترقية لمشرف عادي', callback_data='promote_to_admin')],
                [InlineKeyboardButton('👑 ترقية لمشرف أعلى', callback_data='promote_to_super_admin')],
                [InlineKeyboardButton('📋 عرض تفاصيل إضافية', callback_data=f'view_user_details_{target_user["telegram_id"]}')],
                [InlineKeyboardButton('❌ إلغاء العملية', callback_data='add_admin_cancel')],
                [InlineKeyboardButton('🔙 العودة', callback_data='admin_add_new')]
            ]
            
            if hasattr(update, 'callback_query') and update.callback_query:
                await update.callback_query.edit_message_text(
                    confirmation_text,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text(
                    confirmation_text,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='Markdown'
                )
                
        except Exception as e:
            logger.error(f"Error showing promotion confirmation: {e}")
            error_text = f"{EMOJIS['error']} حدث خطأ في عرض تأكيد الترقية."
            
            if hasattr(update, 'callback_query') and update.callback_query:
                await update.callback_query.edit_message_text(error_text)
            else:
                await update.message.reply_text(error_text)

    @staticmethod
    async def execute_admin_promotion(update: Update, context: CallbackContext, new_role: str):
        """تنفيذ ترقية المستخدم لمشرف"""
        try:
            query = update.callback_query
            await query.answer()
            
            current_user = get_user(query.from_user.id)
            target_telegram_id = context.user_data.get('target_admin_telegram_id')
            target_db_id = context.user_data.get('target_admin_db_id')
            
            if not target_telegram_id or not target_db_id:
                await query.edit_message_text(f"{EMOJIS['error']} انتهت صلاحية العملية. يرجى البدء من جديد.")
                return
            
            target_user = get_user(target_telegram_id)
            if not target_user:
                await query.edit_message_text(f"{EMOJIS['error']} المستخدم المستهدف لم يعد موجوداً.")
                return
            
            # تحديث دور المستخدم في قاعدة البيانات
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # حفظ البيانات القديمة للسجل
            old_data = {
                'role': target_user['role'],
                'permissions': get_admin_permissions(target_db_id) if target_user['role'] in ['admin', 'super_admin'] else {}
            }
            
            # تحديث الدور
            cursor.execute('''
                UPDATE users 
                SET role = ?, updated_at = CURRENT_TIMESTAMP 
                WHERE id = ?
            ''', (new_role, target_db_id))
            
            # تهيئة صلاحيات المشرف الجديد
            initialize_admin_permissions(target_db_id)
            
            # إذا كان مشرف أعلى، منح جميع الصلاحيات
            if new_role == 'super_admin':
                for permission in AVAILABLE_PERMISSIONS.keys():
                    grant_permission(target_telegram_id, permission, current_user['id'])
            
            conn.commit()
            
            # حفظ البيانات الجديدة
            new_data = {
                'role': new_role,
                'permissions': get_admin_permissions(target_db_id)
            }
            
            # تسجيل العملية
            AdminManagement.log_admin_action(
                action_type='create',
                target_admin_id=target_db_id,
                performed_by=current_user['id'],
                old_data=old_data,
                new_data=new_data,
                action_details=f"User promoted from {old_data['role']} to {new_role}"
            )
            
            conn.close()
            
            # رسالة النجاح
            role_name = "مشرف أعلى" if new_role == 'super_admin' else "مشرف عادي"
            
            success_text = f"""
🎉 **تم ترقية المستخدم بنجاح!** 🎉

👤 **المشرف الجديد:**
🔸 الاسم: **{target_user['full_name']}**
🔸 المعرف: `{target_telegram_id}`
🔸 الدور الجديد: **{role_name}**

✅ **ما تم:**
• تحديث دور المستخدم في النظام
• تهيئة الصلاحيات الافتراضية
• تسجيل العملية في سجل الإدارة
• إرسال إشعار للمشرف الجديد

📊 **الصلاحيات المفعلة:**
"""
            
            # عرض الصلاحيات
            permissions = get_admin_permissions(target_db_id)
            for perm_key, perm_info in AVAILABLE_PERMISSIONS.items():
                has_perm = permissions.get(perm_key, False)
                status = "✅" if has_perm else "❌"
                success_text += f"{status} {perm_info['name_ar']}\n"
            
            success_text += f"\n⏰ **تاريخ الترقية:** {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            
            keyboard = [
                [InlineKeyboardButton('⚙️ تعديل صلاحياته', callback_data=f'perm_quick_edit_{target_db_id}')],
                [InlineKeyboardButton('👤 عرض ملفه الشخصي', callback_data=f'admin_profile_{target_db_id}')],
                [InlineKeyboardButton('➕ إضافة مشرف آخر', callback_data='admin_add_new')],
                [InlineKeyboardButton('📋 عرض جميع المشرفين', callback_data='admin_manage_admins')],
                [InlineKeyboardButton('🔙 العودة للوحة الإدارة', callback_data='admin_dashboard')]
            ]
            
            await query.edit_message_text(
                success_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            
            # تنظيف بيانات السياق
            if 'target_admin_telegram_id' in context.user_data:
                del context.user_data['target_admin_telegram_id']
            if 'target_admin_db_id' in context.user_data:
                del context.user_data['target_admin_db_id']
            
            # TODO: إرسال إشعار للمشرف الجديد
            
        except Exception as e:
            logger.error(f"Error executing admin promotion: {e}")
            await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في ترقية المستخدم.")

# إضافة الدوال للاستيراد
__all__ = ['AdminManagement']