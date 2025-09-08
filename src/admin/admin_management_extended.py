#!/usr/bin/env python3
"""
Extended Admin Management Functions
وظائف إدارة المشرفين الموسعة
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
    check_permission_or_deny
)

logger = logging.getLogger(__name__)

class AdminManagementExtended:
    """وظائف إدارة المشرفين الموسعة"""

    @staticmethod
    async def search_admin_handler(update: Update, context: CallbackContext):
        """🔍 البحث عن مشرف"""
        try:
            query = update.callback_query
            await query.answer()
            
            user = get_user(query.from_user.id)
            if not user or user['role'] != 'super_admin':
                await query.edit_message_text(f"{EMOJIS['error']} هذه الميزة مقتصرة على المشرف الأعلى فقط.")
                return
            
            search_text = f"""
🔍 **البحث عن مشرف** 🔍

🎯 **طرق البحث المتاحة:**

**1️⃣ البحث بمعرف التلجرام**
أدخل معرف تلجرام للمشرف (مثال: 123456789)

**2️⃣ البحث برقم الهاتف**  
أدخل رقم الهاتف للمشرف (مثال: 967777123456)

💡 **اختر طريقة البحث:**
"""
            
            keyboard = [
                [InlineKeyboardButton('🔢 البحث بمعرف التلجرام', callback_data='search_admin_by_id')],
                [InlineKeyboardButton('📱 البحث برقم الهاتف', callback_data='search_admin_by_phone')],
                [InlineKeyboardButton('📋 عرض جميع المشرفين', callback_data='admin_manage_admins')],
                [InlineKeyboardButton('🔙 العودة للوحة الإدارة', callback_data='admin_dashboard')]
            ]
            
            await query.edit_message_text(
                search_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Error in search admin handler: {e}")
            await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في البحث عن المشرفين.")

    @staticmethod
    async def search_admin_by_id_handler(update: Update, context: CallbackContext):
        """البحث بالمعرف"""
        try:
            query = update.callback_query
            await query.answer()
            
            # تعيين حالة انتظار معرف البحث
            context.user_data['awaiting_admin_search_id'] = True
            context.user_data['search_type'] = 'by_id'
            
            search_id_text = f"""
🔢 **البحث بالمعرف** 🔢

🔍 **أرسل معرف تلجرام للمشرف:**

مثال: `123456789`

⚠️ **ملاحظة:**
• أدخل المعرف بدون أي إضافات
• يجب أن يكون المستخدم مشرف مسجل
• سيتم عرض جميع تفاصيل المشرف

❌ **للإلغاء اكتب:** `إلغاء`
"""
            
            keyboard = [
                [InlineKeyboardButton('❌ إلغاء البحث', callback_data='search_admin_cancel')],
                [InlineKeyboardButton('🔙 العودة', callback_data='admin_search_admin')]
            ]
            
            await query.edit_message_text(
                search_id_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Error in search admin by ID: {e}")
            await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في البحث بالمعرف.")

    @staticmethod
    async def search_admin_by_phone_handler(update: Update, context: CallbackContext):
        """البحث برقم الهاتف"""
        try:
            query = update.callback_query
            await query.answer()
            
            # تعيين حالة انتظار رقم الهاتف
            context.user_data['awaiting_admin_search_phone'] = True
            context.user_data['search_type'] = 'by_phone'
            
            search_phone_text = f"""
📱 **البحث برقم الهاتف** 📱

📞 **أرسل رقم الهاتف للمشرف:**

مثال: `967777123456` أو `777123456`

💡 **إرشادات:**
• أدخل الرقم بدون فراغات أو رموز
• يمكن إدخال الرقم مع أو بدون مفتاح الدولة
• سيتم البحث في المشرفين المسجلين فقط

❌ **للإلغاء اكتب:** `إلغاء`
"""
            
            keyboard = [
                [InlineKeyboardButton('❌ إلغاء البحث', callback_data='search_admin_cancel')],
                [InlineKeyboardButton('🔙 العودة', callback_data='admin_search_admin')]
            ]
            
            await query.edit_message_text(
                search_phone_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Error in search admin by phone: {e}")
            await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في البحث برقم الهاتف.")

    @staticmethod
    async def perform_admin_search(search_term: str, search_type: str, update: Update, context: CallbackContext):
        """تنفيذ البحث عن المشرفين"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            if search_type == 'by_id':
                # البحث بالمعرف
                try:
                    telegram_id = int(search_term.strip())
                    cursor.execute('''
                        SELECT * FROM users 
                        WHERE telegram_id = ? AND role IN ('admin', 'super_admin')
                    ''', (telegram_id,))
                    results = cursor.fetchall()
                except ValueError:
                    results = []
            
            elif search_type == 'by_phone':
                # البحث برقم الهاتف
                phone_clean = search_term.strip().replace(' ', '').replace('-', '').replace('+', '')
                # البحث بعدة صيغ للرقم
                cursor.execute('''
                    SELECT * FROM users 
                    WHERE role IN ('admin', 'super_admin') AND (
                        phone = ? OR 
                        phone = ? OR 
                        phone LIKE ? OR 
                        phone LIKE ?
                    )
                    ORDER BY full_name
                ''', (phone_clean, f"+{phone_clean}", f"%{phone_clean}", f"%{phone_clean[-9:]}"))
                results = cursor.fetchall()
            
            conn.close()
            
            if not results:
                no_results_text = f"""
❌ **لا توجد نتائج** ❌

لم يتم العثور على أي مشرفين مطابقين لـ: `{search_term}`

💡 **اقتراحات:**
• تحقق من صحة المعرف/الاسم
• جرب البحث بجزء من الاسم
• استخدم البحث المتقدم

🔄 **جرب مرة أخرى:**
"""
                
                keyboard = [
                    [InlineKeyboardButton('🔢 البحث بالمعرف', callback_data='search_admin_by_id')],
                    [InlineKeyboardButton('📝 البحث بالاسم', callback_data='search_admin_by_name')],
                    [InlineKeyboardButton('🔍 البحث المتقدم', callback_data='search_admin_advanced')],
                    [InlineKeyboardButton('🔙 العودة', callback_data='admin_search_admin')]
                ]
                
                if hasattr(update, 'callback_query') and update.callback_query:
                    await update.callback_query.edit_message_text(
                        no_results_text,
                        reply_markup=InlineKeyboardMarkup(keyboard),
                        parse_mode='Markdown'
                    )
                else:
                    await update.message.reply_text(
                        no_results_text,
                        reply_markup=InlineKeyboardMarkup(keyboard),
                        parse_mode='Markdown'
                    )
                return
            
            # عرض النتائج
            await AdminManagementExtended.show_search_results(
                results, search_term, search_type, update, context
            )
            
        except Exception as e:
            logger.error(f"Error performing admin search: {e}")
            error_text = f"{EMOJIS['error']} حدث خطأ في تنفيذ البحث."
            
            if hasattr(update, 'callback_query') and update.callback_query:
                await update.callback_query.edit_message_text(error_text)
            else:
                await update.message.reply_text(error_text)

    @staticmethod
    async def show_search_results(results, search_term: str, search_type: str, update: Update, context: CallbackContext):
        """عرض نتائج البحث"""
        try:
            search_type_ar = "المعرف" if search_type == 'by_id' else "الاسم"
            
            results_text = f"""
🎯 **نتائج البحث** 🎯

🔍 **البحث بـ{search_type_ar}:** `{search_term}`
📊 **عدد النتائج:** {len(results)} مشرف

"""
            
            keyboard = []
            
            for admin in results:
                # الحصول على صلاحيات المشرف
                permissions = get_admin_permissions(admin['id'])
                active_perms = sum(1 for perm, value in permissions.items() if value)
                
                role_emoji = "👑" if admin['role'] == 'super_admin' else "🛡️"
                status_emoji = "✅" if admin['is_active'] else "❌"
                
                results_text += f"""
{role_emoji} **{admin['full_name']}** {status_emoji}
🆔 المعرف: `{admin['telegram_id']}`
🛡️ الدور: {admin['role']}
🔑 الصلاحيات النشطة: {active_perms}/{len(AVAILABLE_PERMISSIONS)}
📅 آخر نشاط: {admin.get('last_activity', 'غير محدد')[:16] if admin.get('last_activity') else 'غير محدد'}
───────────────────
"""
                
                # زر للوصول السريع لتفاصيل المشرف
                keyboard.append([
                    InlineKeyboardButton(
                        f"👤 {admin['full_name'][:20]}",
                        callback_data=f"admin_profile_{admin['id']}"
                    )
                ])
            
            # أزرار إضافية
            keyboard.extend([
                [InlineKeyboardButton('🔍 بحث جديد', callback_data='admin_search_admin')],
                [InlineKeyboardButton('📋 عرض جميع المشرفين', callback_data='admin_manage_admins')],
                [InlineKeyboardButton('🔙 العودة للوحة الإدارة', callback_data='admin_dashboard')]
            ])
            
            if hasattr(update, 'callback_query') and update.callback_query:
                await update.callback_query.edit_message_text(
                    results_text,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text(
                    results_text,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='Markdown'
                )
                
        except Exception as e:
            logger.error(f"Error showing search results: {e}")
            error_text = f"{EMOJIS['error']} حدث خطأ في عرض نتائج البحث."
            
            if hasattr(update, 'callback_query') and update.callback_query:
                await update.callback_query.edit_message_text(error_text)
            else:
                await update.message.reply_text(error_text)

    @staticmethod
    async def admin_activity_log_handler(update: Update, context: CallbackContext):
        """📋 سجل النشاطات"""
        try:
            query = update.callback_query
            await query.answer()
            
            user = get_user(query.from_user.id)
            if not user or user['role'] != 'super_admin':
                await query.edit_message_text(f"{EMOJIS['error']} هذه الميزة مقتصرة على المشرف الأعلى فقط.")
                return
            
            # الحصول على آخر العمليات
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT 
                    aml.*,
                    performer.full_name as performer_name,
                    target.full_name as target_name
                FROM admin_management_logs aml
                LEFT JOIN users performer ON aml.performed_by = performer.id
                LEFT JOIN users target ON aml.target_admin_id = target.id
                ORDER BY aml.created_at DESC
                LIMIT 20
            ''')
            
            logs = cursor.fetchall()
            
            # إحصائيات سريعة
            cursor.execute('''
                SELECT action_type, COUNT(*) as count
                FROM admin_management_logs
                WHERE created_at >= datetime('now', '-7 days')
                GROUP BY action_type
                ORDER BY count DESC
            ''')
            
            stats = cursor.fetchall()
            conn.close()
            
            log_text = f"""
📋 **سجل إدارة المشرفين** 📋

📊 **إحصائيات آخر 7 أيام:**
"""
            
            if stats:
                for stat in stats:
                    action_type_ar = {
                        'create': 'إنشاء مشرف',
                        'update': 'تحديث بيانات',
                        'delete': 'حذف مشرف',
                        'permission_change': 'تغيير صلاحية',
                        'status_change': 'تغيير حالة'
                    }.get(stat['action_type'], stat['action_type'])
                    
                    log_text += f"• {action_type_ar}: **{stat['count']}** عملية\n"
            else:
                log_text += "• لا توجد عمليات في آخر 7 أيام\n"
            
            log_text += f"\n🔥 **آخر العمليات:**\n\n"
            
            if logs:
                for log in logs[:10]:
                    action_type_ar = {
                        'create': '➕ إنشاء',
                        'update': '✏️ تحديث',
                        'delete': '🗑️ حذف',
                        'permission_change': '🔑 صلاحية',
                        'status_change': '🔄 حالة'
                    }.get(log['action_type'], log['action_type'])
                    
                    performer_name = log['performer_name'] or "مجهول"
                    target_name = log['target_name'] or "مجهول"
                    created_at = log['created_at'][:16] if log['created_at'] else "غير محدد"
                    
                    log_text += f"""
{action_type_ar} **{target_name}**
👤 بواسطة: {performer_name}
📅 التاريخ: {created_at}
📝 التفاصيل: {log['action_details'] or 'غير محدد'}
───────────────────
"""
            else:
                log_text += "• لا توجد عمليات مسجلة\n"
            
            keyboard = [
                [InlineKeyboardButton('📊 تقرير مفصل', callback_data='admin_logs_detailed')],
                [InlineKeyboardButton('🔍 فلترة حسب النوع', callback_data='admin_logs_filter')],
                [InlineKeyboardButton('📅 فلترة حسب التاريخ', callback_data='admin_logs_date_filter')],
                [InlineKeyboardButton('💾 تصدير السجل', callback_data='admin_logs_export')],
                [InlineKeyboardButton('🔙 العودة للوحة الإدارة', callback_data='admin_dashboard')]
            ]
            
            await query.edit_message_text(
                log_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Error in admin activity log: {e}")
            await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في عرض سجل النشاطات.")

    @staticmethod
    async def admin_settings_handler(update: Update, context: CallbackContext):
        """⚙️ إعدادات الإدارة"""
        try:
            query = update.callback_query
            await query.answer()
            
            user = get_user(query.from_user.id)
            if not user or user['role'] != 'super_admin':
                await query.edit_message_text(f"{EMOJIS['error']} هذه الميزة مقتصرة على المشرف الأعلى فقط.")
                return
            
            # الحصول على الإعدادات الحالية
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM admin_system_settings ORDER BY setting_key')
            settings = cursor.fetchall()
            
            # إحصائيات سريعة
            cursor.execute('SELECT COUNT(*) FROM users WHERE role IN ("admin", "super_admin")')
            total_admins = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM users WHERE role IN ("admin", "super_admin") AND is_active = 1')
            active_admins = cursor.fetchone()[0]
            
            conn.close()
            
            settings_text = f"""
⚙️ **إعدادات إدارة المشرفين** ⚙️

📊 **معلومات النظام:**
• إجمالي المشرفين: **{total_admins}** مشرف
• المشرفين النشطين: **{active_admins}** مشرف
• نسبة النشاط: **{(active_admins/total_admins*100) if total_admins > 0 else 0:.1f}%**

🔧 **الإعدادات الحالية:**

"""
            
            keyboard = []
            
            for setting in settings:
                # تحويل القيم للعرض
                if setting['setting_type'] == 'boolean':
                    value_display = "✅ مفعل" if setting['setting_value'].lower() == 'true' else "❌ معطل"
                    toggle_value = 'false' if setting['setting_value'].lower() == 'true' else 'true'
                    
                    settings_text += f"• **{setting['description']}**\n"
                    settings_text += f"  الحالة: {value_display}\n\n"
                    
                    # زر التبديل
                    button_text = "❌ تعطيل" if setting['setting_value'].lower() == 'true' else "✅ تفعيل"
                    keyboard.append([
                        InlineKeyboardButton(
                            f"{button_text} {setting['description'][:20]}",
                            callback_data=f"toggle_setting_{setting['setting_key']}_{toggle_value}"
                        )
                    ])
                
                elif setting['setting_type'] == 'integer':
                    settings_text += f"• **{setting['description']}**\n"
                    settings_text += f"  القيمة: **{setting['setting_value']}**\n\n"
                    
                    keyboard.append([
                        InlineKeyboardButton(
                            f"✏️ تعديل {setting['description'][:15]}",
                            callback_data=f"edit_setting_{setting['setting_key']}"
                        )
                    ])
            
            # أزرار إضافية
            keyboard.extend([
                [InlineKeyboardButton('🔄 إعادة تحميل الإعدادات', callback_data='admin_settings_reload')],
                [InlineKeyboardButton('📊 إحصائيات مفصلة', callback_data='admin_settings_stats')],
                [InlineKeyboardButton('💾 نسخ احتياطي للإعدادات', callback_data='admin_settings_backup')],
                [InlineKeyboardButton('🔙 العودة للوحة الإدارة', callback_data='admin_dashboard')]
            ])
            
            await query.edit_message_text(
                settings_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Error in admin settings: {e}")
            await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في إعدادات الإدارة.")

    @staticmethod
    async def toggle_admin_setting(setting_key: str, new_value: str, update: Update, context: CallbackContext):
        """تبديل إعداد إداري"""
        try:
            query = update.callback_query
            await query.answer()
            
            user = get_user(query.from_user.id)
            if not user or user['role'] != 'super_admin':
                await query.edit_message_text(f"{EMOJIS['error']} ليس لديك صلاحية لهذه العملية.")
                return
            
            # تحديث الإعداد
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE admin_system_settings 
                SET setting_value = ?, updated_by = ?, updated_at = CURRENT_TIMESTAMP 
                WHERE setting_key = ?
            ''', (new_value, user['id'], setting_key))
            
            # الحصول على وصف الإعداد
            cursor.execute('SELECT description FROM admin_system_settings WHERE setting_key = ?', (setting_key,))
            setting_description = cursor.fetchone()['description']
            
            conn.commit()
            conn.close()
            
            # رسالة التأكيد
            status = "تم تفعيل" if new_value.lower() == 'true' else "تم تعطيل"
            
            await query.answer(f"✅ {status} {setting_description} بنجاح!", show_alert=True)
            
            # إعادة عرض الإعدادات
            await AdminManagementExtended.admin_settings_handler(update, context)
            
        except Exception as e:
            logger.error(f"Error toggling admin setting: {e}")
            await query.answer("❌ حدث خطأ في تبديل الإعداد!", show_alert=True)

    @staticmethod
    async def admin_reports_handler(update: Update, context: CallbackContext):
        """📊 تقارير المشرفين"""
        try:
            query = update.callback_query
            await query.answer()
            
            user = get_user(query.from_user.id)
            if not user or user['role'] != 'super_admin':
                await query.edit_message_text(f"{EMOJIS['error']} هذه الميزة مقتصرة على المشرف الأعلى فقط.")
                return
            
            # جمع بيانات التقارير
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # إحصائيات عامة
            cursor.execute('''
                SELECT 
                    COUNT(*) as total_admins,
                    COUNT(CASE WHEN role = 'super_admin' THEN 1 END) as super_admins,
                    COUNT(CASE WHEN role = 'admin' THEN 1 END) as regular_admins,
                    COUNT(CASE WHEN is_active = 1 THEN 1 END) as active_admins,
                    COUNT(CASE WHEN last_activity >= datetime('now', '-7 days') THEN 1 END) as recent_active
                FROM users 
                WHERE role IN ('admin', 'super_admin')
            ''')
            
            stats = cursor.fetchone()
            
            # أكثر المشرفين نشاطاً
            cursor.execute('''
                SELECT 
                    u.full_name,
                    u.role,
                    COUNT(aml.id) as actions_count
                FROM users u
                LEFT JOIN admin_management_logs aml ON u.id = aml.performed_by
                WHERE u.role IN ('admin', 'super_admin')
                AND aml.created_at >= datetime('now', '-30 days')
                GROUP BY u.id, u.full_name, u.role
                ORDER BY actions_count DESC
                LIMIT 5
            ''')
            
            top_active = cursor.fetchall()
            
            # عمليات حسب النوع
            cursor.execute('''
                SELECT action_type, COUNT(*) as count
                FROM admin_management_logs
                WHERE created_at >= datetime('now', '-30 days')
                GROUP BY action_type
                ORDER BY count DESC
            ''')
            
            actions_stats = cursor.fetchall()
            
            conn.close()
            
            reports_text = f"""
📊 **تقارير المشرفين** 📊

📈 **إحصائيات عامة:**
• إجمالي المشرفين: **{stats['total_admins']}**
• مشرفين أعلى: **{stats['super_admins']}**
• مشرفين عاديين: **{stats['regular_admins']}**
• نشطين حالياً: **{stats['active_admins']}**
• نشطين في آخر 7 أيام: **{stats['recent_active']}**

🏆 **أكثر المشرفين نشاطاً (آخر 30 يوم):**
"""
            
            if top_active:
                for i, admin in enumerate(top_active, 1):
                    role_emoji = "👑" if admin['role'] == 'super_admin' else "🛡️"
                    reports_text += f"{i}️⃣ {role_emoji} **{admin['full_name']}** - {admin['actions_count']} عملية\n"
            else:
                reports_text += "• لا توجد عمليات مسجلة\n"
            
            reports_text += f"\n📋 **العمليات حسب النوع (آخر 30 يوم):**\n"
            
            if actions_stats:
                for action in actions_stats:
                    action_type_ar = {
                        'create': 'إنشاء مشرف',
                        'update': 'تحديث بيانات',
                        'delete': 'حذف مشرف',
                        'permission_change': 'تغيير صلاحية',
                        'status_change': 'تغيير حالة'
                    }.get(action['action_type'], action['action_type'])
                    
                    reports_text += f"• {action_type_ar}: **{action['count']}** عملية\n"
            else:
                reports_text += "• لا توجد عمليات مسجلة\n"
            
            keyboard = [
                [InlineKeyboardButton('📅 تقرير شهري', callback_data='admin_report_monthly')],
                [InlineKeyboardButton('📊 تقرير الأداء', callback_data='admin_report_performance')],
                [InlineKeyboardButton('🔍 تقرير الصلاحيات', callback_data='admin_report_permissions')],
                [InlineKeyboardButton('📈 اتجاهات النشاط', callback_data='admin_report_trends')],
                [InlineKeyboardButton('💾 تصدير التقرير', callback_data='admin_report_export')],
                [InlineKeyboardButton('🔙 العودة للوحة الإدارة', callback_data='admin_dashboard')]
            ]
            
            await query.edit_message_text(
                reports_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Error in admin reports: {e}")
            await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في تقارير المشرفين.")

# Export for use
__all__ = ['AdminManagementExtended']