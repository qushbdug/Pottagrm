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
from bot_modules.utils import get_user, get_user_by_id, update_user_activity
from bot_modules.utils import log_admin_invocation
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
            try:
                log_admin_invocation(update, 'AdminManagement.get_admin_dashboard', {'user_role': user['role']})
            except Exception:
                pass
            
            # إحصائيات المشرفين
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # عدد المشرفين
            cursor.execute("SELECT COUNT(*) FROM users WHERE role IN ('admin', 'super_admin')")
            result = cursor.fetchone()
            total_admins = result[0] if result else 0
            
            # المشرفين النشطين (آخر 7 أيام)
            cursor.execute("""
                SELECT COUNT(*) FROM users 
                WHERE role IN ('admin', 'super_admin') 
                AND last_activity >= datetime('now', '-7 days')
            """)
            result = cursor.fetchone()
            active_admins = result[0] if result else 0
            
            # المشرفين حسب النوع
            cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'admin'")
            result = cursor.fetchone()
            regular_admins = result[0] if result else 0
            
            cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'super_admin'")
            result = cursor.fetchone()
            super_admins = result[0] if result else 0
            
            # نشاطات المشرفين اليوم
            cursor.execute("""
                SELECT COUNT(*) FROM activity_logs
                WHERE user_id IN (SELECT id FROM users WHERE role IN ('admin', 'super_admin'))
                AND DATE(created_at) = DATE('now')
            """)
            result = cursor.fetchone()
            today_activities = result[0] if result else 0
            
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
                [InlineKeyboardButton('➕ إضافة مشرف', callback_data='admin_add_new'),
                 InlineKeyboardButton('👤 قائمة المشرفين', callback_data='admin_manage_admins')],
                [InlineKeyboardButton('🔐 تعديل الصلاحيات', callback_data='admin_permissions'),
                 InlineKeyboardButton('🗑️ حذف مشرف', callback_data='admin_manage_admins')],
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
            try:
                log_admin_invocation(update, 'AdminManagement.manage_admins')
            except Exception:
                pass
            
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
            
            admins_text = f"""
👑 **قائمة المشرفين** 👑

📊 **إجمالي المشرفين:** {len(admins)}

"""
            
            admin_buttons = []
            
            for i, admin in enumerate(admins, 1):
                admin_id, name, phone, role, is_active, created_at, last_activity = admin
                
                # رموز الحالة
                role_emoji = "👑" if role == 'super_admin' else "🛡️"
                status_emoji = "🟢" if is_active else "🔴"
                
                # حساب آخر نشاط
                if last_activity:
                    try:
                        # محاولة تحويل التاريخ مع معالجة الأخطاء
                        if '.' in last_activity:
                            # إزالة الجزء الكسري من الثواني
                            last_activity = last_activity.split('.')[0]
                        last_activity_date = datetime.strptime(last_activity, '%Y-%m-%d %H:%M:%S')
                        days_ago = (datetime.now() - last_activity_date).days
                        activity_text = f"منذ {days_ago} يوم" if days_ago > 0 else "اليوم"
                    except (ValueError, TypeError):
                        activity_text = "غير محدد"
                else:
                    activity_text = "لا يوجد نشاط"
                
                admins_text += f"""
{i}️⃣ {status_emoji} {role_emoji} **{name}**
📱 {phone or 'غير محدد'} | 🏷️ {'مشرف أعلى' if role == 'super_admin' else 'مشرف عادي'}

"""
                
                # إضافة زر للمشرف
                button_text = f"{role_emoji} {name[:20]}{'...' if len(name) > 20 else ''}"
                admin_buttons.append([InlineKeyboardButton(
                    button_text, 
                    callback_data=f'admin_profile_{admin_id}'
                )])
            
            # إضافة أزرار التحكم
            admin_buttons.extend([
                [InlineKeyboardButton('➕ إضافة مشرف', callback_data='admin_add_new')],
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
            result = cursor.fetchone()
            monthly_activities = result[0] if result else 0
            
            cursor.execute("""
                SELECT COUNT(*) FROM activity_logs 
                WHERE user_id = ? AND DATE(created_at) = DATE('now')
            """, (admin_id,))
            result = cursor.fetchone()
            daily_activities = result[0] if result else 0
            
            # آخر النشاطات
            cursor.execute("""
                SELECT activity_type, description, created_at 
                FROM activity_logs 
                WHERE user_id = ? 
                ORDER BY created_at DESC 
                LIMIT 5
            """, (admin_id,))
            recent_activities = cursor.fetchall()
            
            # الصلاحيات (باستخدام admin_permissions)
            perms_dict = get_admin_permissions(admin_id)
            permissions = [k for k, v in perms_dict.items() if v]
            
            conn.close()
            
            # إعداد المعلومات
            role_emoji = "👑" if admin['role'] == 'super_admin' else "🛡️"
            status_emoji = "🟢" if admin['is_active'] else "🔴"
            
            # حساب مدة العضوية
            try:
                created_at = admin['created_at']
                if '.' in created_at:
                    created_at = created_at.split('.')[0]
                created_date = datetime.strptime(created_at, '%Y-%m-%d %H:%M:%S')
                membership_days = (datetime.now() - created_date).days
            except (ValueError, TypeError):
                membership_days = 0
            
            # آخر نشاط
            if admin['last_activity']:
                try:
                    last_activity = admin['last_activity']
                    if '.' in last_activity:
                        last_activity = last_activity.split('.')[0]
                    last_activity_date = datetime.strptime(last_activity, '%Y-%m-%d %H:%M:%S')
                    days_since_activity = (datetime.now() - last_activity_date).days
                    activity_status = f"منذ {days_since_activity} يوم" if days_since_activity > 0 else "نشط اليوم"
                except (ValueError, TypeError):
                    activity_status = "غير محدد"
            else:
                activity_status = "لم يسجل نشاط"
            
            profile_text = f"""
{role_emoji} **ملف المشرف** {role_emoji}

👤 **{admin['full_name']}**
📱 الهاتف: **{admin['phone'] or 'غير محدد'}**
🆔 المعرف: **{admin['telegram_id']}**
🏷️ الدور: **{'مشرف أعلى' if admin['role'] == 'super_admin' else 'مشرف عادي'}**
{status_emoji} الحالة: **{'مفعل' if admin['is_active'] else 'غير مفعل'}**

📅 تاريخ الإضافة: **{admin['created_at'][:10]}**
"""
            
            keyboard = [
                [InlineKeyboardButton('🔐 تعديل الصلاحيات', callback_data=f'perm_quick_edit_{admin_id}')],
                [InlineKeyboardButton('🗑️ حذف المشرف', callback_data=f'admin_delete_{admin_id}')],
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
                SELECT a.activity_type, COUNT(*) as count
                FROM activity_logs a
                JOIN users u ON a.user_id = u.id
                WHERE u.role IN ('admin', 'super_admin')
                AND a.created_at >= datetime('now', '-30 days')
                GROUP BY a.activity_type
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
🔐 **تعديل صلاحيات المشرفين** 🔐

👥 **إجمالي المشرفين:** {len(admins_with_permissions)}

💡 **اختر مشرف لتعديل صلاحياته:**
"""
            
            keyboard = [
                [InlineKeyboardButton('📋 قائمة المشرفين', callback_data='perm_list_all_admins')],
                [InlineKeyboardButton('🔙 العودة', callback_data='admin_dashboard')]
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
📋 **المشرفين والصلاحيات** 📋

👥 **إجمالي المشرفين:** {len(admins_list)}

"""
            
            for admin in current_admins:
                role_emoji = "👑" if admin['role'] == 'super_admin' else "🛡️"
                
                list_text += f"""
{role_emoji} **{admin['full_name']}**
🆔 `{admin['telegram_id']}` | 🏷️ {admin['role']}

"""
            
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
                # أزرار سريعة للمشرفين
                for admin in current_admins:
                    role_emoji = "👑" if admin['role'] == 'super_admin' else "🛡️"
                    keyboard.append([InlineKeyboardButton(
                        f"{role_emoji} {admin['full_name'][:20]}",
                        callback_data=f"perm_quick_edit_{admin['id']}"
                    )])
            
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
            try:
                log_admin_invocation(update, 'AdminManagement.edit_admin_permissions', {'admin_id': admin_id})
            except Exception:
                pass
            
            # التحقق من المشرف الأعلى
            user = get_user(query.from_user.id)
            if not user or user['role'] != 'super_admin':
                await query.edit_message_text(f"{EMOJIS['error']} هذه الميزة مقتصرة على المشرف الأعلى.")
                return
            
            # الحصول على معلومات المشرف المستهدف
            target_admin = get_user_by_id(admin_id)
            if not target_admin or target_admin['role'] not in ['admin', 'super_admin']:
                await query.edit_message_text(f"{EMOJIS['error']} المشرف المستهدف غير موجود.")
                return
            
            # الحصول على صلاحيات المشرف الحالية
            admin_permissions = get_admin_permissions(admin_id)
            
            edit_text = f"""
🔐 **تعديل صلاحيات المشرف** 🔐

👤 **المشرف:** {target_admin['full_name']}
🛡️ **الرتبة:** {target_admin['role']}

🔑 **الصلاحيات:**

"""
            
            # الصلاحيات المطلوبة حسب الطلب
            basic_permissions = {
                'manage_clients': {'name': 'إدارة العملاء', 'icon': '👥'},
                'manage_admins': {'name': 'إدارة المشرفين', 'icon': '🛡️'},
                'withdrawals': {'name': 'طلبات السحب', 'icon': '💸'},
                'broadcast': {'name': 'إرسال رسالة جماعية', 'icon': '📢'},
                'accounting_access': {'name': 'النظام المحاسبي', 'icon': '💰'}
            }
            
            # عرض الصلاحيات مع إمكانية التبديل
            keyboard = []
            
            for perm_key, perm_info in basic_permissions.items():
                has_perm = admin_permissions.get(perm_key, False)
                status_emoji = "✅" if has_perm else "❌"
                action = "revoke" if has_perm else "grant"
                
                edit_text += f"{perm_info['icon']} **{perm_info['name']}**: {status_emoji}\n"
                
                # زر التبديل
                button_text = f"{perm_info['icon']} {perm_info['name']} {status_emoji}"
                keyboard.append([
                    InlineKeyboardButton(
                        button_text,
                        callback_data=f"perm_{action}_{admin_id}_{perm_key}"
                    )
                ])
            
            edit_text += "\n💡 **اضغط على الزر لتفعيل أو إلغاء الصلاحية**"
            
            keyboard.extend([
                [InlineKeyboardButton('🔙 العودة', callback_data='admin_manage_admins')],
                [InlineKeyboardButton('🔙 العودة', callback_data='perm_list_all_admins')]
            ])
            
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
            try:
                log_admin_invocation(update, 'AdminManagement.toggle_permission', {'action': action, 'admin_id': admin_id, 'permission': permission})
            except Exception:
                pass
            
            user = get_user(query.from_user.id)
            if not user or user['role'] != 'super_admin':
                await query.edit_message_text(f"{EMOJIS['error']} ليس لديك صلاحية لهذه العملية.")
                return
            
            target_admin = get_user_by_id(admin_id)
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
                # الحصول على اسم الصلاحية
                basic_permissions = {
                    'accounting_system': 'النظام المحاسبي',
                    'customer_management': 'إدارة العملاء',
                    'withdrawal_requests': 'طلبات السحب',
                    'broadcast_messages': 'إرسال رسالة جماعية',
                    'dashboard_access': 'لوحة المعلومات'
                }
                perm_name = basic_permissions.get(permission, permission)
                
                if action == "grant":
                    await query.answer(f"✅ تم تفعيل صلاحية {perm_name}", show_alert=True)
                else:
                    await query.answer(f"❌ تم إلغاء صلاحية {perm_name}", show_alert=True)
                
                # إعادة عرض صفحة التعديل
                await AdminManagement.edit_admin_permissions(update, context, admin_id)
            else:
                await query.answer(f"❌ فشل في {action_text} الصلاحية!", show_alert=True)
            
        except Exception as e:
            logger.error(f"Error toggling permission: {e}")
            await query.answer("❌ حدث خطأ في تبديل الصلاحية!", show_alert=True)

    @staticmethod
    async def grant_all_permissions(update: Update, context: CallbackContext, admin_id: int):
        """منح جميع الصلاحيات لمشرف"""
        try:
            query = update.callback_query
            await query.answer()
            try:
                log_admin_invocation(update, 'AdminManagement.grant_all_permissions', {'admin_id': admin_id})
            except Exception:
                pass
            
            user = get_user(query.from_user.id)
            if not user or user['role'] != 'super_admin':
                await query.edit_message_text(f"{EMOJIS['error']} ليس لديك صلاحية لهذه العملية.")
                return
            
            target_admin = get_user_by_id(admin_id)
            if not target_admin:
                await query.edit_message_text(f"{EMOJIS['error']} المشرف المستهدف غير موجود.")
                return
            
            # الصلاحيات الأساسية
            basic_permissions = [
                'accounting_system',
                'customer_management', 
                'withdrawal_requests',
                'broadcast_messages',
                'dashboard_access'
            ]
            
            # منح جميع الصلاحيات
            for permission in basic_permissions:
                grant_permission(admin_id, permission, user['id'])
            
            await query.answer("✅ تم منح جميع الصلاحيات بنجاح!", show_alert=True)
            
            # إعادة عرض صفحة التعديل
            await AdminManagement.edit_admin_permissions(update, context, admin_id)
            
        except Exception as e:
            logger.error(f"Error granting all permissions: {e}")
            await query.answer("❌ حدث خطأ في منح الصلاحيات!", show_alert=True)
    
    @staticmethod
    async def revoke_all_permissions(update: Update, context: CallbackContext, admin_id: int):
        """سحب جميع الصلاحيات من مشرف"""
        try:
            query = update.callback_query
            await query.answer()
            try:
                log_admin_invocation(update, 'AdminManagement.revoke_all_permissions', {'admin_id': admin_id})
            except Exception:
                pass
            
            user = get_user(query.from_user.id)
            if not user or user['role'] != 'super_admin':
                await query.edit_message_text(f"{EMOJIS['error']} ليس لديك صلاحية لهذه العملية.")
                return
            
            target_admin = get_user_by_id(admin_id)
            if not target_admin:
                await query.edit_message_text(f"{EMOJIS['error']} المشرف المستهدف غير موجود.")
                return
            
            # الصلاحيات الأساسية
            basic_permissions = [
                'accounting_system',
                'customer_management', 
                'withdrawal_requests',
                'broadcast_messages',
                'dashboard_access'
            ]
            
            # سحب جميع الصلاحيات
            for permission in basic_permissions:
                revoke_permission(admin_id, permission, user['id'])
            
            await query.answer("❌ تم سحب جميع الصلاحيات بنجاح!", show_alert=True)
            
            # إعادة عرض صفحة التعديل
            await AdminManagement.edit_admin_permissions(update, context, admin_id)
            
        except Exception as e:
            logger.error(f"Error revoking all permissions: {e}")
            await query.answer("❌ حدث خطأ في سحب الصلاحيات!", show_alert=True)

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
            
            # تعيين حالة انتظار إدخال رقم المحفظة
            context.user_data['awaiting_admin_wallet'] = True
            context.user_data['admin_add_step'] = 'enter_wallet'
            
            add_admin_text = f"""
➕ **إضافة مشرف جديد** ➕

💳 **أرسل رقم محفظة المستخدم المراد ترقيته:**

📋 **معلومات مهمة:**
• رقم المحفظة يجب أن يكون مسجل في النظام
• سيتم ترقية المستخدم إلى مشرف
• سيحصل على صلاحيات أساسية افتراضية

⚡ **مثال:** `12345`

❌ **للإلغاء اكتب:** `إلغاء`
"""
            
            keyboard = [
                [InlineKeyboardButton('❌ إلغاء', callback_data='add_admin_cancel')],
                [InlineKeyboardButton('🔙 العودة', callback_data='admin_dashboard')]
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
    async def process_admin_wallet_input(update: Update, context: CallbackContext):
        """معالجة إدخال رقم محفظة المشرف الجديد"""
        try:
            wallet_number = update.message.text.strip()
            
            # التحقق من الإلغاء
            if wallet_number.lower() == 'إلغاء':
                context.user_data.pop('awaiting_admin_wallet', None)
                context.user_data.pop('admin_add_step', None)
                await update.message.reply_text(
                    "❌ تم إلغاء عملية إضافة المشرف.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton('👑 لوحة إدارة المشرفين', callback_data='admin_dashboard')]
                    ])
                )
                return
            
            # التحقق من صحة رقم المحفظة
            if not wallet_number.isdigit():
                await update.message.reply_text(
                    f"{EMOJIS['error']} رقم المحفظة يجب أن يكون أرقام فقط!\n\nأرسل رقم محفظة صحيح أو اكتب 'إلغاء' للإلغاء."
                )
                return
            
            # البحث عن المستخدم بواسطة رقم المحفظة
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE wallet_number = ?", (wallet_number,))
            target_user = cursor.fetchone()
            conn.close()
            
            if not target_user:
                await update.message.reply_text(
                    f"{EMOJIS['error']} لم يتم العثور على مستخدم بهذا رقم المحفظة!\n\nتأكد من الرقم وحاول مجدداً.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton('🔄 المحاولة مجدداً', callback_data='admin_add_new')],
                        [InlineKeyboardButton('👑 لوحة الإدارة', callback_data='admin_dashboard')]
                    ])
                )
                context.user_data.pop('awaiting_admin_wallet', None)
                context.user_data.pop('admin_add_step', None)
                return
            
            # التحقق من أن المستخدم ليس مشرف بالفعل
            if target_user['role'] in ['admin', 'super_admin']:
                await update.message.reply_text(
                    f"⚠️ هذا المستخدم مشرف بالفعل!\n\n👤 الاسم: {target_user['full_name']}\n🛡️ الرتبة: {target_user['role']}",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton('⚙️ تعديل صلاحياته', callback_data=f'perm_quick_edit_{target_user["id"]}')],
                        [InlineKeyboardButton('👑 لوحة الإدارة', callback_data='admin_dashboard')]
                    ])
                )
                context.user_data.pop('awaiting_admin_wallet', None)
                context.user_data.pop('admin_add_step', None)
                return
            
            # حفظ معلومات المستخدم المستهدف
            context.user_data['target_admin'] = target_user
            context.user_data.pop('awaiting_admin_wallet', None)
            
            # عرض تأكيد إضافة كمشرف (فقط مشرف عادي حسب المتطلبات)
            confirm_text = f"""
✅ **تأكيد إضافة كمشرف** ✅

👤 **المستخدم:** {target_user['full_name']}
💳 **رقم المحفظة:** {target_user['wallet_number']}
📱 **الهاتف:** {target_user['phone'] or 'غير محدد'}
💰 **الرصيد:** {target_user['balance']:,.2f} ريال

💡 **سيتم تعيينه كمشرف ويمكن تعديل صلاحياته مباشرةً بعد الإضافة.**
"""
            
            keyboard = [
                [InlineKeyboardButton('➕ إضافة كمشرف', callback_data='promote_to_admin')],
                [InlineKeyboardButton('❌ إلغاء', callback_data='admin_dashboard')]
            ]
            
            await update.message.reply_text(
                confirm_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Error processing admin wallet input: {e}")
            await update.message.reply_text(
                f"{EMOJIS['error']} حدث خطأ في معالجة الطلب.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton('👑 لوحة الإدارة', callback_data='admin_dashboard')]
                ])
            )
            context.user_data.pop('awaiting_admin_wallet', None)
            context.user_data.pop('admin_add_step', None)
    
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
    async def add_admin_cancel_handler(update: Update, context: CallbackContext):
        """إلغاء عملية إضافة مشرف"""
        try:
            query = update.callback_query
            await query.answer()
            
            # مسح بيانات المؤقتة
            context.user_data.pop('awaiting_admin_wallet', None)
            context.user_data.pop('admin_add_step', None)
            context.user_data.pop('target_admin', None)
            
            await query.edit_message_text(
                "❌ تم إلغاء عملية إضافة المشرف.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton('👑 لوحة إدارة المشرفين', callback_data='admin_dashboard')]
                ])
            )
        except Exception as e:
            logger.error(f"Error in cancel admin add: {e}")
            await query.edit_message_text("حدث خطأ.")
    
    @staticmethod
    async def add_admin_enter_phone_handler(update: Update, context: CallbackContext):
        """معالج إدخال رقم الهاتف للمشرف الجديد"""
        try:
            query = update.callback_query
            await query.answer()
            
            # تعيين حالة انتظار رقم الهاتف
            context.user_data['awaiting_admin_phone'] = True
            context.user_data['admin_add_step'] = 'enter_phone'
            
            enter_phone_text = f"""
📱 **إدخال رقم الهاتف** 📱

📞 **أرسل رقم الهاتف للمستخدم:**

مثال: `967777123456` أو `777123456`

⚠️ **تعليمات مهمة:**
• أرسل الرقم بدون فراغات أو رموز
• يمكن إدخال الرقم مع أو بدون مفتاح الدولة
• يجب أن يكون المستخدم مسجل في البوت

❌ **للإلغاء اكتب:** `إلغاء`
"""
            
            keyboard = [
                [InlineKeyboardButton('❌ إلغاء العملية', callback_data='add_admin_cancel')],
                [InlineKeyboardButton('🔙 العودة', callback_data='admin_add_new')]
            ]
            
            await query.edit_message_text(
                enter_phone_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Error in enter admin phone handler: {e}")
            await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في إدخال رقم الهاتف.")



    @staticmethod
    async def process_admin_user_search(search_value: str, search_type: str, update: Update, context: CallbackContext):
        """معالجة البحث عن المستخدم للترقية (بالمعرف أو الهاتف)"""
        try:
            # البحث عن المستخدم
            target_user = None
            
            if search_type == 'telegram_id':
                try:
                    telegram_id = int(search_value)
                    target_user = get_user(telegram_id)
                except ValueError:
                    pass
            elif search_type == 'phone':
                # البحث برقم الهاتف
                phone_clean = search_value.strip().replace(' ', '').replace('-', '').replace('+', '')
                conn = get_db_connection()
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT * FROM users 
                    WHERE phone = ? OR phone = ? OR phone LIKE ? OR phone LIKE ?
                    LIMIT 1
                ''', (phone_clean, f"+{phone_clean}", f"%{phone_clean}", f"%{phone_clean[-9:]}"))
                
                user_row = cursor.fetchone()
                conn.close()
                
                if user_row:
                    # تحويل Row إلى dict
                    target_user = dict(user_row)
            
            if not target_user:
                search_label = "المعرف" if search_type == 'telegram_id' else "رقم الهاتف"
                error_text = f"""
❌ **لم يتم العثور على هذا المستخدم** ❌

{search_label} `{search_value}` غير مسجل في النظام.

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
🔸 الهاتف: {target_user['phone'] if target_user['phone'] else 'غير محدد'}
🔸 الدور الحالي: **{target_user['role']}**

🛡️ **اختر نوع الترقية:**

**1️⃣ مشرف عادي**
• صلاحيات محدودة

**2️⃣ مشرف أعلى**  
• جميع الصلاحيات

💡 **هل أنت متأكد من ترقية هذا المستخدم؟**
"""
            
            # حفظ معرف المستخدم المستهدف
            context.user_data['target_admin_telegram_id'] = target_user['telegram_id']
            context.user_data['target_admin_db_id'] = target_user['id']
            
            keyboard = [
                [InlineKeyboardButton('🛡️ مشرف عادي', callback_data='promote_to_admin')],
                [InlineKeyboardButton('👑 مشرف أعلى', callback_data='promote_to_super_admin')],
                [InlineKeyboardButton('❌ إلغاء', callback_data='add_admin_cancel')]
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
            target_user = context.user_data.get('target_admin')
            
            if not target_user:
                await query.edit_message_text(f"{EMOJIS['error']} انتهت صلاحية العملية. يرجى البدء من جديد.")
                return
            
            target_telegram_id = target_user['telegram_id']
            target_db_id = target_user['id']
            
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
            
            # الانتقال مباشرة لواجهة تعديل الصلاحيات للمشرف الجديد
            await AdminManagement.edit_admin_permissions(update, context, target_db_id)
            
            # تنظيف بيانات السياق
            if 'target_admin_telegram_id' in context.user_data:
                del context.user_data['target_admin_telegram_id']
            if 'target_admin_db_id' in context.user_data:
                del context.user_data['target_admin_db_id']
            
            # TODO: إرسال إشعار للمشرف الجديد
            
        except Exception as e:
            logger.error(f"Error executing admin promotion: {e}")
            await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في ترقية المستخدم.")

    @staticmethod
    async def delete_admin_handler(update: Update, context: CallbackContext, admin_id: int):
        """🗑️ حذف مشرف"""
        try:
            query = update.callback_query
            await query.answer()
            
            current_user = get_user(query.from_user.id)
            if not current_user or current_user['role'] != 'super_admin':
                await query.edit_message_text(f"{EMOJIS['error']} هذه العملية محصورة على المشرف الأعلى فقط.")
                return
            
            # الحصول على معلومات المشرف المراد حذفه
            target_admin = get_user_by_id(admin_id)
            if not target_admin or target_admin['role'] not in ['admin', 'super_admin']:
                await query.edit_message_text(f"{EMOJIS['error']} المشرف المستهدف غير موجود.")
                return
            
            # منع حذف المشرف الأعلى لنفسه
            if target_admin['telegram_id'] == current_user['telegram_id']:
                await query.edit_message_text(f"{EMOJIS['error']} لا يمكنك حذف حسابك الخاص.")
                return
            
            delete_text = f"""
⚠️ **تأكيد حذف المشرف** ⚠️

👤 **بيانات المشرف:**
🔸 الاسم: **{target_admin['full_name']}**
🔸 المعرف: `{target_admin['telegram_id']}`
🔸 الهاتف: {target_admin['phone'] if target_admin['phone'] else 'غير محدد'}
🔸 الدور: **{target_admin['role']}**

❌ **ما سيحدث عند الحذف:**
• تحويل الدور إلى "عميل"
• إزالة جميع الصلاحيات الإدارية
• إيقاف الوصول للوحات الإدارة
• تسجيل العملية في سجل الإدارة

⚠️ **تحذير:** هذه العملية لا يمكن التراجع عنها!

💡 **هل أنت متأكد من حذف هذا المشرف؟**
"""
            
            keyboard = [
                [InlineKeyboardButton('✅ نعم، احذف المشرف', callback_data=f'confirm_delete_admin_{admin_id}')],
                [InlineKeyboardButton('❌ لا، إلغاء العملية', callback_data=f'admin_profile_{admin_id}')],
                [InlineKeyboardButton('🔙 العودة لملف المشرف', callback_data=f'admin_profile_{admin_id}')]
            ]
            
            await query.edit_message_text(
                delete_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Error in delete admin handler: {e}")
            await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في معالجة حذف المشرف.")

    @staticmethod
    async def confirm_delete_admin_handler(update: Update, context: CallbackContext, admin_id: int):
        """✅ تأكيد حذف المشرف"""
        try:
            query = update.callback_query
            await query.answer()
            
            current_user = get_user(query.from_user.id)
            target_admin = get_user_by_id(admin_id)
            
            if not target_admin:
                await query.edit_message_text(f"{EMOJIS['error']} المشرف المستهدف لم يعد موجوداً.")
                return
            
            # تنفيذ عملية الحذف
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # حفظ البيانات القديمة للسجل
            old_data = {
                'role': target_admin['role'],
                'permissions': get_admin_permissions(admin_id)
            }
            
            # تحديث الدور إلى عميل
            cursor.execute('''
                UPDATE users 
                SET role = 'customer', updated_at = CURRENT_TIMESTAMP 
                WHERE id = ?
            ''', (admin_id,))
            
            # حذف جميع الصلاحيات
            cursor.execute('''
                DELETE FROM admin_permissions 
                WHERE admin_id = ?
            ''', (admin_id,))
            
            conn.commit()
            
            # تسجيل العملية
            AdminManagement.log_admin_action(
                action_type='delete',
                target_admin_id=admin_id,
                performed_by=current_user['id'],
                old_data=old_data,
                new_data={'role': 'customer', 'permissions': {}},
                action_details=f"Admin {target_admin['full_name']} demoted to customer"
            )
            
            conn.close()
            
            success_text = f"""
✅ **تم حذف المشرف بنجاح** ✅

👤 **المستخدم السابق:**
🔸 الاسم: **{target_admin['full_name']}**
🔸 المعرف: `{target_admin['telegram_id']}`

✅ **ما تم:**
• تحويل الدور من "{target_admin['role']}" إلى "عميل"
• إزالة جميع الصلاحيات الإدارية
• تسجيل العملية في سجل الإدارة
• إرسال إشعار للمستخدم

⏰ **تاريخ الحذف:** {datetime.now().strftime('%Y-%m-%d %H:%M')}
"""
            
            keyboard = [
                [InlineKeyboardButton('📋 عرض قائمة المشرفين', callback_data='admin_manage_admins')],
                [InlineKeyboardButton('➕ إضافة مشرف جديد', callback_data='admin_add_new')],
                [InlineKeyboardButton('📋 عرض سجل النشاطات', callback_data='admin_activity_log')],
                [InlineKeyboardButton('🔙 العودة للوحة الإدارة', callback_data='admin_dashboard')]
            ]
            
            await query.edit_message_text(
                success_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Error confirming admin deletion: {e}")
            await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في تأكيد حذف المشرف.")

# إضافة الدوال للاستيراد
__all__ = ['AdminManagement']