#!/usr/bin/env python3
"""
Export System - نظام التصدير الشامل للمشرف الأعلى
يوفر تصدير جميع البيانات بصيغ مختلفة مع اختيار الفترات الزمنية
"""

import io
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext

# Excel Generation
try:
    from openpyxl import Workbook
    from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
    from openpyxl.utils import get_column_letter
    EXCEL_AVAILABLE = True
except ImportError:
    EXCEL_AVAILABLE = False

from bot_modules.database import get_db_connection, get_db_context
from bot_modules.utils import get_user
from bot_modules.config import EMOJIS

logger = logging.getLogger(__name__)

class ExportSystem:
    """نظام التصدير الشامل"""
    
    @staticmethod
    async def show_export_options(update: Update, context: CallbackContext):
        """عرض خيارات التصدير"""
        try:
            query = update.callback_query
            await query.answer()
            
            user = get_user(query.from_user.id)
            if not user or user['role'] != 'super_admin':
                await query.edit_message_text(f"{EMOJIS['error']} هذه الميزة مقتصرة على المشرف الأعلى.")
                return
            
            export_text = f"""
📊 **نظام التصدير الشامل** 📊

👑 **المشرف الأعلى:** {user['full_name']}

📋 **أنواع التصدير المتاحة:**

💰 **تصدير الأرباح:**
• تقرير الأرباح والخسائر
• تحليل الإيرادات
• مقارنة الفترات

👥 **تصدير العملاء:**
• قائمة العملاء الكاملة
• أنشطة العملاء
• إحصائيات الشراء

🏪 **تصدير المزودين:**
• قائمة المزودين النشطين
• أداء المزودين
• عمولات ومبيعات

📊 **تصدير شامل:**
• جميع البيانات المالية
• تقرير شامل للنظام
• ملخص تنفيذي

🕐 **اختر الفترة الزمنية:**
"""
            
            keyboard = [
                [InlineKeyboardButton('💰 تصدير الأرباح', callback_data='export_profits'),
                 InlineKeyboardButton('👥 تصدير العملاء', callback_data='export_customers')],
                [InlineKeyboardButton('🏪 تصدير المزودين', callback_data='export_suppliers'),
                 InlineKeyboardButton('📊 تصدير شامل', callback_data='export_comprehensive')],
                [InlineKeyboardButton('🔙 العودة للنظام المحاسبي', callback_data='accounting_system')]
            ]
            
            await query.edit_message_text(
                export_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Error showing export options: {e}")
            await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في عرض خيارات التصدير.")

    @staticmethod
    async def show_period_selection(update: Update, context: CallbackContext, export_type: str):
        """عرض اختيار الفترة الزمنية"""
        try:
            query = update.callback_query
            await query.answer()
            
            export_names = {
                'profits': 'الأرباح',
                'customers': 'العملاء', 
                'suppliers': 'المزودين',
                'comprehensive': 'الشامل'
            }
            
            export_name = export_names.get(export_type, export_type)
            
            period_text = f"""
🕐 **اختيار الفترة الزمنية** 🕐

📊 **نوع التصدير:** {export_name}

📅 **الفترات المتاحة:**

⚡ **فترات سريعة:**
• آخر 7 أيام
• آخر 30 يوم
• آخر 90 يوم

📆 **فترات شهرية:**
• الشهر الحالي
• الشهر الماضي
• آخر 3 أشهر

🗓️ **فترات سنوية:**
• السنة الحالية
• جميع البيانات

💡 **اختر الفترة المطلوبة:**
"""
            
            keyboard = [
                [InlineKeyboardButton('⚡ آخر 7 أيام', callback_data=f'export_{export_type}_7'),
                 InlineKeyboardButton('⚡ آخر 30 يوم', callback_data=f'export_{export_type}_30')],
                [InlineKeyboardButton('⚡ آخر 90 يوم', callback_data=f'export_{export_type}_90'),
                 InlineKeyboardButton('📆 الشهر الحالي', callback_data=f'export_{export_type}_current_month')],
                [InlineKeyboardButton('📆 الشهر الماضي', callback_data=f'export_{export_type}_last_month'),
                 InlineKeyboardButton('📆 آخر 3 أشهر', callback_data=f'export_{export_type}_3months')],
                [InlineKeyboardButton('🗓️ السنة الحالية', callback_data=f'export_{export_type}_year'),
                 InlineKeyboardButton('🗓️ جميع البيانات', callback_data=f'export_{export_type}_all')],
                [InlineKeyboardButton('🔙 العودة لخيارات التصدير', callback_data='accounting_export')]
            ]
            
            await query.edit_message_text(
                period_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Error showing period selection: {e}")
            await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في عرض اختيار الفترة.")

    @staticmethod
    def get_date_filter(period: str) -> tuple:
        """الحصول على فلتر التاريخ حسب الفترة"""
        now = datetime.now()
        
        if period == '7':
            start_date = now - timedelta(days=7)
            return start_date.strftime('%Y-%m-%d'), 'آخر 7 أيام'
        elif period == '30':
            start_date = now - timedelta(days=30)
            return start_date.strftime('%Y-%m-%d'), 'آخر 30 يوم'
        elif period == '90':
            start_date = now - timedelta(days=90)
            return start_date.strftime('%Y-%m-%d'), 'آخر 90 يوم'
        elif period == 'current_month':
            start_date = now.replace(day=1)
            return start_date.strftime('%Y-%m-%d'), 'الشهر الحالي'
        elif period == 'last_month':
            last_month = now.replace(day=1) - timedelta(days=1)
            start_date = last_month.replace(day=1)
            return start_date.strftime('%Y-%m-%d'), 'الشهر الماضي'
        elif period == '3months':
            start_date = now - timedelta(days=90)
            return start_date.strftime('%Y-%m-%d'), 'آخر 3 أشهر'
        elif period == 'year':
            start_date = now.replace(month=1, day=1)
            return start_date.strftime('%Y-%m-%d'), 'السنة الحالية'
        else:  # 'all'
            return None, 'جميع البيانات'

    @staticmethod
    def export_profits_data(period: str) -> io.BytesIO:
        """تصدير بيانات الأرباح"""
        if not EXCEL_AVAILABLE:
            raise ImportError("مكتبة openpyxl غير متوفرة")
        
        wb = Workbook()
        ws = wb.active
        ws.title = "تقرير الأرباح"
        
        # تنسيق الرأس
        header_font = Font(bold=True, size=14, color="FFFFFF")
        header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
        
        # العنوان
        ws['A1'] = "تقرير الأرباح والإيرادات"
        ws['A1'].font = Font(bold=True, size=16)
        ws['A1'].alignment = Alignment(horizontal='center')
        ws.merge_cells('A1:F1')
        
        start_date, period_name = ExportSystem.get_date_filter(period)
        
        ws['A3'] = "الفترة:"
        ws['B3'] = period_name
        ws['A4'] = "تاريخ التصدير:"
        ws['B4'] = datetime.now().strftime('%Y-%m-%d %H:%M')
        
        # الحصول على البيانات
        with get_db_context() as conn:

            cursor = conn.cursor()
        # استعلام الأرباح
        if start_date:
            cursor.execute('''
                SELECT type, SUM(amount) as total, COUNT(*) as count
                FROM transactions 
                WHERE created_at >= ?
                GROUP BY type
                ORDER BY total DESC
            ''', (start_date,))
        else:
            cursor.execute('''
                SELECT type, SUM(amount) as total, COUNT(*) as count
                FROM transactions 
                GROUP BY type
                ORDER BY total DESC
            ''')
        
        profits_data = cursor.fetchall()
        
        # عناوين الجدول
        headers = ['نوع المعاملة', 'إجمالي المبلغ', 'عدد المعاملات', 'متوسط المعاملة']
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=6, column=col, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal='center')
        
        # بيانات الأرباح
        type_names = {
            'card_purchase': 'شراء الكروت',
            'coupon_redeem': 'شحن الكوبونات',
            'transfer': 'التحويلات',
            'transfer_fee': 'رسوم التحويل',
            'commission': 'العمولات'
        }
        
        total_revenue = 0
        for row, profit in enumerate(profits_data, 7):
            type_name = type_names.get(profit[0], profit[0])
            total = profit[1] or 0
            count = profit[2] or 0
            avg = total / max(count, 1)
            
            ws.cell(row=row, column=1, value=type_name)
            ws.cell(row=row, column=2, value=f"{total:,.2f} ريال")
            ws.cell(row=row, column=3, value=count)
            ws.cell(row=row, column=4, value=f"{avg:,.2f} ريال")
            
            total_revenue += total
        
        # الإجمالي
        summary_row = len(profits_data) + 8
        ws.cell(row=summary_row, column=1, value="الإجمالي").font = Font(bold=True)
        ws.cell(row=summary_row, column=2, value=f"{total_revenue:,.2f} ريال").font = Font(bold=True)        # تنسيق الأعمدة
        for col in range(1, 5):
            ws.column_dimensions[get_column_letter(col)].width = 20
        
        # حفظ في ذاكرة
        buffer = io.BytesIO()
        wb.save(buffer)
        buffer.seek(0)
        return buffer

    @staticmethod
    async def export_data_handler(update: Update, context: CallbackContext, export_type: str, period: str):
        """معالج تصدير البيانات"""
        try:
            query = update.callback_query
            await query.answer("📊 جاري إنشاء التصدير...")
            
            user = get_user(query.from_user.id)
            if not user or user['role'] != 'super_admin':
                await query.edit_message_text(f"{EMOJIS['error']} هذه الميزة مقتصرة على المشرف الأعلى.")
                return
            
            start_date, period_name = ExportSystem.get_date_filter(period)
            filename_date = datetime.now().strftime('%Y%m%d_%H%M')
            
            if export_type == 'profits':
                # تصدير الأرباح
                excel_buffer = ExportSystem.export_profits_data(period)
                filename = f"تقرير_الأرباح_{period_name}_{filename_date}.xlsx"
                caption = f"📊 **تقرير الأرباح**\n📅 **الفترة:** {period_name}"
                
            elif export_type == 'customers':
                # تصدير العملاء
                excel_buffer = ExportSystem.export_customers_data(period)
                filename = f"تقرير_العملاء_{period_name}_{filename_date}.xlsx"
                caption = f"👥 **تقرير العملاء**\n📅 **الفترة:** {period_name}"
                
            elif export_type == 'suppliers':
                # تصدير المزودين
                excel_buffer = ExportSystem.export_suppliers_data(period)
                filename = f"تقرير_المزودين_{period_name}_{filename_date}.xlsx"
                caption = f"🏪 **تقرير المزودين**\n📅 **الفترة:** {period_name}"
                
            elif export_type == 'comprehensive':
                # تصدير شامل
                excel_buffer = ExportSystem.export_comprehensive_data(period)
                filename = f"تقرير_شامل_{period_name}_{filename_date}.xlsx"
                caption = f"📊 **تقرير شامل**\n📅 **الفترة:** {period_name}"
            
            # إرسال الملف
            await context.bot.send_document(
                chat_id=query.message.chat_id,
                document=excel_buffer,
                filename=filename,
                caption=f"{caption}\n⏰ **تم الإنشاء:** {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            )
            
            # رسالة تأكيد
            success_text = f"""
✅ **تم إنشاء التصدير بنجاح!** ✅

📊 **النوع:** {export_type.title()}
📅 **الفترة:** {period_name}
📁 **تم إرسال الملف أعلاه**

💡 يمكنك تصدير تقارير أخرى من نفس القائمة
"""
            
            keyboard = [
                [InlineKeyboardButton('📊 تصدير آخر', callback_data='accounting_export'),
                 InlineKeyboardButton('📈 النظام المحاسبي', callback_data='accounting_system')],
                [InlineKeyboardButton('🏠 لوحة الإدارة', callback_data='super_admin_panel')]
            ]
            
            await query.edit_message_text(
                success_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Error exporting data: {e}")
            await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في تصدير البيانات.")

    @staticmethod
    def export_customers_data(period: str) -> io.BytesIO:
        """تصدير بيانات العملاء"""
        wb = Workbook()
        ws = wb.active
        ws.title = "تقرير العملاء"
        
        start_date, period_name = ExportSystem.get_date_filter(period)
        
        # معلومات التقرير
        ws['A1'] = "تقرير العملاء"
        ws['A1'].font = Font(bold=True, size=16)
        ws.merge_cells('A1:F1')
        
        ws['A3'] = "الفترة:"
        ws['B3'] = period_name
        
        # الحصول على بيانات العملاء
        with get_db_context() as conn:

            cursor = conn.cursor()
        if start_date:
            cursor.execute('''
                SELECT u.full_name, u.phone, u.balance, u.created_at,
                       COUNT(t.id) as transactions,
                       SUM(CASE WHEN t.type = 'card_purchase' THEN t.amount ELSE 0 END) as purchases
                FROM users u
                LEFT JOIN transactions t ON (u.id = t.from_user AND t.created_at >= ?)
                WHERE u.role = 'customer'
                GROUP BY u.id
                ORDER BY purchases DESC, u.balance DESC
            ''', (start_date,))
        else:
            cursor.execute('''
                SELECT u.full_name, u.phone, u.balance, u.created_at,
                       COUNT(t.id) as transactions,
                       SUM(CASE WHEN t.type = 'card_purchase' THEN t.amount ELSE 0 END) as purchases
                FROM users u
                LEFT JOIN transactions t ON u.id = t.from_user
                WHERE u.role = 'customer'
                GROUP BY u.id
                ORDER BY purchases DESC, u.balance DESC
            ''')
        
        customers = cursor.fetchall()        # عناوين الجدول
        headers = ['اسم العميل', 'رقم الهاتف', 'الرصيد الحالي', 'تاريخ التسجيل', 'عدد المعاملات', 'إجمالي المشتريات']
        for col, header in enumerate(headers, 1):
            ws.cell(row=5, column=col, value=header).font = Font(bold=True)
        
        # بيانات العملاء
        for row, customer in enumerate(customers, 6):
            ws.cell(row=row, column=1, value=customer[0])
            ws.cell(row=row, column=2, value=customer[1])
            ws.cell(row=row, column=3, value=f"{customer[2]:,.2f} ريال")
            ws.cell(row=row, column=4, value=customer[3][:10] if customer[3] else '')
            ws.cell(row=row, column=5, value=customer[4] or 0)
            ws.cell(row=row, column=6, value=f"{customer[5] or 0:,.2f} ريال")
        
        # تنسيق الأعمدة
        for col in range(1, 7):
            ws.column_dimensions[get_column_letter(col)].width = 18
        
        buffer = io.BytesIO()
        wb.save(buffer)
        buffer.seek(0)
        return buffer

    @staticmethod
    def export_suppliers_data(period: str) -> io.BytesIO:
        """تصدير بيانات المزودين"""
        wb = Workbook()
        ws = wb.active
        ws.title = "تقرير المزودين"
        
        start_date, period_name = ExportSystem.get_date_filter(period)
        
        # معلومات التقرير
        ws['A1'] = "تقرير المزودين"
        ws['A1'].font = Font(bold=True, size=16)
        ws.merge_cells('A1:F1')
        
        ws['A3'] = "الفترة:"
        ws['B3'] = period_name
        
        # الحصول على بيانات المزودين
        with get_db_context() as conn:

            cursor = conn.cursor()
        if start_date:
            cursor.execute('''
                SELECT u.full_name, u.phone, u.balance, u.created_at,
                       COUNT(t.id) as sales,
                       SUM(CASE WHEN t.type = 'card_purchase' THEN t.amount ELSE 0 END) as revenue
                FROM users u
                LEFT JOIN transactions t ON (u.id = t.to_user AND t.created_at >= ?)
                WHERE u.role = 'supplier'
                GROUP BY u.id
                ORDER BY revenue DESC, u.balance DESC
            ''', (start_date,))
        else:
            cursor.execute('''
                SELECT u.full_name, u.phone, u.balance, u.created_at,
                       COUNT(t.id) as sales,
                       SUM(CASE WHEN t.type = 'card_purchase' THEN t.amount ELSE 0 END) as revenue
                FROM users u
                LEFT JOIN transactions t ON u.id = t.to_user
                WHERE u.role = 'supplier'
                GROUP BY u.id
                ORDER BY revenue DESC, u.balance DESC
            ''')
        
        suppliers = cursor.fetchall()        # عناوين الجدول
        headers = ['اسم المزود', 'رقم الهاتف', 'الرصيد الحالي', 'تاريخ التسجيل', 'عدد المبيعات', 'إجمالي الإيرادات']
        for col, header in enumerate(headers, 1):
            ws.cell(row=5, column=col, value=header).font = Font(bold=True)
        
        # بيانات المزودين
        for row, supplier in enumerate(suppliers, 6):
            ws.cell(row=row, column=1, value=supplier[0])
            ws.cell(row=row, column=2, value=supplier[1])
            ws.cell(row=row, column=3, value=f"{supplier[2]:,.2f} ريال")
            ws.cell(row=row, column=4, value=supplier[3][:10] if supplier[3] else '')
            ws.cell(row=row, column=5, value=supplier[4] or 0)
            ws.cell(row=row, column=6, value=f"{supplier[5] or 0:,.2f} ريال")
        
        # تنسيق الأعمدة
        for col in range(1, 7):
            ws.column_dimensions[get_column_letter(col)].width = 18
        
        buffer = io.BytesIO()
        wb.save(buffer)
        buffer.seek(0)
        return buffer

    @staticmethod
    def export_comprehensive_data(period: str) -> io.BytesIO:
        """تصدير شامل لجميع البيانات"""
        wb = Workbook()
        
        # ورقة الملخص
        ws_summary = wb.active
        ws_summary.title = "الملخص التنفيذي"
        
        start_date, period_name = ExportSystem.get_date_filter(period)
        
        ws_summary['A1'] = "التقرير الشامل للنظام"
        ws_summary['A1'].font = Font(bold=True, size=16)
        ws_summary.merge_cells('A1:D1')
        
        ws_summary['A3'] = "الفترة:"
        ws_summary['B3'] = period_name
        ws_summary['A4'] = "تاريخ التصدير:"
        ws_summary['B4'] = datetime.now().strftime('%Y-%m-%d %H:%M')
        
        # الحصول على الإحصائيات الشاملة
        with get_db_context() as conn:

            cursor = conn.cursor()
        # إحصائيات المستخدمين
        cursor.execute('SELECT role, COUNT(*), SUM(balance) FROM users GROUP BY role')
        user_stats = cursor.fetchall()
        
        # إحصائيات المعاملات
        if start_date:
            cursor.execute('SELECT type, COUNT(*), SUM(amount) FROM transactions WHERE created_at >= ? GROUP BY type', (start_date,))
        else:
            cursor.execute('SELECT type, COUNT(*), SUM(amount) FROM transactions GROUP BY type')
        transaction_stats = cursor.fetchall()        # كتابة الإحصائيات
        ws_summary['A6'] = "إحصائيات المستخدمين:"
        ws_summary['A6'].font = Font(bold=True)
        
        row = 7
        for stat in user_stats:
            ws_summary.cell(row=row, column=1, value=f"{stat[0]}:")
            ws_summary.cell(row=row, column=2, value=f"{stat[1]} مستخدم")
            ws_summary.cell(row=row, column=3, value=f"{stat[2]:,.2f} ريال")
            row += 1
        
        row += 1
        ws_summary.cell(row=row, column=1, value="إحصائيات المعاملات:").font = Font(bold=True)
        row += 1
        
        for stat in transaction_stats:
            ws_summary.cell(row=row, column=1, value=f"{stat[0]}:")
            ws_summary.cell(row=row, column=2, value=f"{stat[1]} معاملة")
            ws_summary.cell(row=row, column=3, value=f"{stat[2]:,.2f} ريال")
            row += 1
        
        buffer = io.BytesIO()
        wb.save(buffer)
        buffer.seek(0)
        return buffer

# دوال مساعدة للاستدعاء السريع
async def export_options_handler(update: Update, context: CallbackContext):
    """عرض خيارات التصدير"""
    return await ExportSystem.show_export_options(update, context)

async def export_profits_handler(update: Update, context: CallbackContext):
    """تصدير الأرباح"""
    return await ExportSystem.show_period_selection(update, context, 'profits')

async def export_customers_handler(update: Update, context: CallbackContext):
    """تصدير العملاء"""
    return await ExportSystem.show_period_selection(update, context, 'customers')

async def export_suppliers_handler(update: Update, context: CallbackContext):
    """تصدير المزودين"""
    return await ExportSystem.show_period_selection(update, context, 'suppliers')

async def export_comprehensive_handler(update: Update, context: CallbackContext):
    """تصدير شامل"""
    return await ExportSystem.show_period_selection(update, context, 'comprehensive')

async def quick_export_handler(update: Update, context: CallbackContext):
    """تصدير سريع للمشرف الأعلى"""
    try:
        query = update.callback_query
        await query.answer("📊 جاري إنشاء التصدير السريع...")
        
        user = get_user(query.from_user.id)
        if not user or user['role'] != 'super_admin':
            await query.edit_message_text(f"{EMOJIS['error']} هذه الميزة مقتصرة على المشرف الأعلى.")
            return
        
        quick_text = f"""
⚡ **تصدير سريع للمشرف الأعلى** ⚡

👑 **{user['full_name']}**

📊 **خيارات التصدير السريع:**

💰 **تقارير مالية (آخر 30 يوم):**
• تقرير الأرباح والإيرادات
• تحليل المعاملات المالية
• ملخص الحركة المالية

👥 **تقارير المستخدمين (آخر 30 يوم):**
• بيانات العملاء وأنشطتهم
• أداء المزودين ومبيعاتهم
• إحصائيات شاملة

📋 **تقارير شاملة:**
• تقرير تنفيذي كامل (آخر 30 يوم)
• تقرير شامل (جميع البيانات)

⚡ اختر نوع التصدير المطلوب:
"""
        
        keyboard = [
            [InlineKeyboardButton('💰 الأرباح (30 يوم)', callback_data='export_profits_30'),
             InlineKeyboardButton('👥 العملاء (30 يوم)', callback_data='export_customers_30')],
            [InlineKeyboardButton('🏪 المزودين (30 يوم)', callback_data='export_suppliers_30'),
             InlineKeyboardButton('📊 شامل (30 يوم)', callback_data='export_comprehensive_30')],
            [InlineKeyboardButton('📋 شامل (جميع البيانات)', callback_data='export_comprehensive_all'),
             InlineKeyboardButton('⚙️ تصدير مخصص', callback_data='export_profits')],
            [InlineKeyboardButton('🔙 العودة للوحة الإدارة', callback_data='super_admin_panel')]
        ]
        
        await query.edit_message_text(
            quick_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Error in quick export handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في التصدير السريع.")