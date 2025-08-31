#!/usr/bin/env python3
"""
Account Statement Generator
مولد كشف الحساب للعملاء والمزودين
"""

import os
import io
import logging
from datetime import datetime, timedelta
from typing import Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext

# PDF Generation
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

# Excel Generation
try:
    from openpyxl import Workbook
    from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
    from openpyxl.utils import get_column_letter
    EXCEL_AVAILABLE = True
except ImportError:
    EXCEL_AVAILABLE = False

from bot_modules.database import get_db_connection
from bot_modules.utils import get_user
from bot_modules.config import EMOJIS, USER_ROLES
from bot_modules.enhanced_error_messages import ErrorMessages

logger = logging.getLogger(__name__)

class AccountStatementGenerator:
    """مولد كشف الحساب"""
    
    @staticmethod
    async def show_statement_options(update: Update, context: CallbackContext):
        """عرض خيارات كشف الحساب"""
        try:
            query = update.callback_query
            await query.answer()
            
            user = get_user(query.from_user.id)
            if not user:
                await query.edit_message_text(f"{EMOJIS['error']} لم يتم العثور على بيانات المستخدم.")
                return
            
            # التحقق من أن المستخدم عميل أو مزود
            if user['role'] not in ['customer', 'supplier']:
                await query.edit_message_text(f"{EMOJIS['error']} هذه الميزة متاحة للعملاء والمزودين فقط.")
                return
            
            statement_text = f"""
🎟️ **كشف الحساب** 🎟️

👤 **{user['full_name']}**
🎭 **{USER_ROLES.get(user['role'], user['role'])}**
💳 **رقم المحفظة:** {user['wallet_number']}

📋 **خيارات التنزيل المتاحة:**

📊 **Excel (.xlsx):**
• سهل التعديل والتحليل
• يحتوي على جميع المعاملات
• متوافق مع جميع البرامج

📄 **PDF (.pdf):**
• تنسيق احترافي للطباعة
• لا يمكن تعديله (آمن)
• سهل المشاركة

📅 **الفترة الزمنية:**
• آخر 30 يوم (افتراضي)
• آخر 90 يوم
• جميع المعاملات

🎟️ اختر التنسيق المفضل لديك:
"""
            
            keyboard = [
                [InlineKeyboardButton('📊 تنزيل Excel - آخر 30 يوم', callback_data='download_excel_30'),
                 InlineKeyboardButton('📄 تنزيل PDF - آخر 30 يوم', callback_data='download_pdf_30')],
                [InlineKeyboardButton('📊 تنزيل Excel - آخر 90 يوم', callback_data='download_excel_90'),
                 InlineKeyboardButton('📄 تنزيل PDF - آخر 90 يوم', callback_data='download_pdf_90')],
                [InlineKeyboardButton('📊 تنزيل Excel - جميع المعاملات', callback_data='download_excel_all'),
                 InlineKeyboardButton('📄 تنزيل PDF - جميع المعاملات', callback_data='download_pdf_all')],
                [InlineKeyboardButton('🏠 العودة للقائمة الرئيسية', callback_data='main_menu')]
            ]
            
            await query.edit_message_text(
                statement_text, 
                reply_markup=InlineKeyboardMarkup(keyboard), 
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Error showing statement options: {e}")
            await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في عرض خيارات كشف الحساب.")

    @staticmethod
    def get_user_transactions(user_id: int, days: Optional[int] = None):
        """الحصول على معاملات المستخدم"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            if days:
                cursor.execute('''
                    SELECT id, type, amount, description, created_at, details
                    FROM transactions 
                    WHERE user_id = ? AND created_at >= datetime('now', '-' || ? || ' days')
                    ORDER BY created_at DESC
                ''', (user_id, days))
            else:
                cursor.execute('''
                    SELECT id, type, amount, description, created_at, details
                    FROM transactions 
                    WHERE user_id = ?
                    ORDER BY created_at DESC
                ''', (user_id,))
            
            transactions = cursor.fetchall()
            conn.close()
            return transactions
            
        except Exception as e:
            logger.error(f"Error getting user transactions: {e}")
            return []

    @staticmethod
    def generate_excel_statement(user: dict, transactions: list, days: Optional[int] = None) -> io.BytesIO:
        """إنشاء كشف حساب بصيغة Excel"""
        if not EXCEL_AVAILABLE:
            raise ImportError("مكتبة openpyxl غير متوفرة")
        
        wb = Workbook()
        ws = wb.active
        ws.title = "كشف الحساب"
        
        # تنسيق الألوان والخطوط
        header_font = Font(bold=True, size=14, color="FFFFFF")
        header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
        data_font = Font(size=11)
        border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )
        
        # معلومات المستخدم
        ws['A1'] = "🎟️ كشف الحساب"
        ws['A1'].font = Font(bold=True, size=16)
        ws['A1'].alignment = Alignment(horizontal='center')
        ws.merge_cells('A1:F1')
        
        ws['A3'] = "اسم العميل:"
        ws['B3'] = user['full_name']
        ws['A4'] = "رقم المحفظة:"
        ws['B4'] = user['wallet_number']
        ws['A5'] = "الرصيد الحالي:"
        ws['B5'] = f"{user['balance']:,.2f} ريال"
        
        period_text = f"آخر {days} يوم" if days else "جميع المعاملات"
        ws['A6'] = "الفترة:"
        ws['B6'] = period_text
        ws['A7'] = "تاريخ الإنشاء:"
        ws['B7'] = datetime.now().strftime('%Y-%m-%d %H:%M')
        
        # عناوين الجدول
        headers = ['التاريخ', 'نوع المعاملة', 'المبلغ', 'الوصف', 'التفاصيل']
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=9, column=col, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal='center')
            cell.border = border
        
        # بيانات المعاملات
        transaction_types = {
            'purchase': 'شراء',
            'transfer': 'تحويل',
            'coupon_redeem': 'شحن بكوبون',
            'commission': 'عمولة',
            'refund': 'استرداد'
        }
        
        for row, transaction in enumerate(transactions, 10):
            ws.cell(row=row, column=1, value=transaction[4][:16]).border = border
            ws.cell(row=row, column=2, value=transaction_types.get(transaction[1], transaction[1])).border = border
            ws.cell(row=row, column=3, value=f"{transaction[2]:,.2f}").border = border
            ws.cell(row=row, column=4, value=transaction[3] or '').border = border
            ws.cell(row=row, column=5, value=transaction[5] or '').border = border
        
        # تنسيق عرض الأعمدة
        for col in range(1, 6):
            ws.column_dimensions[get_column_letter(col)].width = 20
        
        # حفظ في ذاكرة
        excel_buffer = io.BytesIO()
        wb.save(excel_buffer)
        excel_buffer.seek(0)
        return excel_buffer

    @staticmethod
    def generate_pdf_statement(user: dict, transactions: list, days: Optional[int] = None) -> io.BytesIO:
        """إنشاء كشف حساب بصيغة PDF"""
        if not PDF_AVAILABLE:
            raise ImportError("مكتبة reportlab غير متوفرة")
        
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        styles = getSampleStyleSheet()
        
        # إنشاء نمط للنص العربي
        arabic_style = ParagraphStyle(
            'Arabic',
            parent=styles['Normal'],
            fontSize=12,
            alignment=1,  # محاذاة وسط
            spaceAfter=12
        )
        
        story = []
        
        # العنوان الرئيسي
        title = Paragraph("🎟️ كشف الحساب", styles['Title'])
        story.append(title)
        story.append(Spacer(1, 12))
        
        # معلومات المستخدم
        user_info = f"""
        <b>اسم العميل:</b> {user['full_name']}<br/>
        <b>رقم المحفظة:</b> {user['wallet_number']}<br/>
        <b>الرصيد الحالي:</b> {user['balance']:,.2f} ريال<br/>
        <b>الفترة:</b> {"آخر " + str(days) + " يوم" if days else "جميع المعاملات"}<br/>
        <b>تاريخ الإنشاء:</b> {datetime.now().strftime('%Y-%m-%d %H:%M')}
        """
        
        user_para = Paragraph(user_info, arabic_style)
        story.append(user_para)
        story.append(Spacer(1, 20))
        
        # جدول المعاملات
        if transactions:
            # عناوين الجدول
            data = [['التاريخ', 'نوع المعاملة', 'المبلغ', 'الوصف']]
            
            transaction_types = {
                'purchase': 'شراء',
                'transfer': 'تحويل', 
                'coupon_redeem': 'شحن بكوبون',
                'commission': 'عمولة',
                'refund': 'استرداد'
            }
            
            for transaction in transactions:
                data.append([
                    transaction[4][:16],  # created_at
                    transaction_types.get(transaction[1], transaction[1]),  # type
                    f"{transaction[2]:,.2f} ريال",  # amount
                    (transaction[3] or '')[:30]  # description
                ])
            
            table = Table(data)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            story.append(table)
        else:
            no_trans = Paragraph("لا توجد معاملات في الفترة المحددة", arabic_style)
            story.append(no_trans)
        
        # إنشاء PDF
        doc.build(story)
        buffer.seek(0)
        return buffer

    @staticmethod
    async def download_statement_handler(update: Update, context: CallbackContext, format_type: str, days: Optional[int] = None):
        """معالج تنزيل كشف الحساب"""
        try:
            query = update.callback_query
            await query.answer("🎟️ جاري إنشاء كشف الحساب...")
            
            user = get_user(query.from_user.id)
            if not user:
                await query.edit_message_text(f"{EMOJIS['error']} لم يتم العثور على بيانات المستخدم.")
                return
            
            # التحقق من الصلاحيات
            if user['role'] not in ['customer', 'supplier']:
                await query.edit_message_text(f"{EMOJIS['error']} هذه الميزة متاحة للعملاء والمزودين فقط.")
                return
            
            # الحصول على المعاملات
            transactions = AccountStatementGenerator.get_user_transactions(user['id'], days)
            
            period_text = f"آخر {days} يوم" if days else "جميع المعاملات"
            filename_date = datetime.now().strftime('%Y%m%d_%H%M')
            
            if format_type == 'excel':
                if not EXCEL_AVAILABLE:
                    await query.edit_message_text(f"{EMOJIS['error']} ميزة Excel غير متوفرة حالياً.")
                    return
                
                # إنشاء ملف Excel
                excel_buffer = AccountStatementGenerator.generate_excel_statement(user, transactions, days)
                filename = f"كشف_حساب_{user['wallet_number']}_{filename_date}.xlsx"
                
                # إرسال الملف
                await context.bot.send_document(
                    chat_id=query.message.chat_id,
                    document=excel_buffer,
                    filename=filename,
                    caption=f"🎟️ **كشف الحساب - Excel**\n\n👤 **{user['full_name']}**\n📅 **الفترة:** {period_text}\n⏰ **تم الإنشاء:** {datetime.now().strftime('%Y-%m-%d %H:%M')}"
                )
                
            elif format_type == 'pdf':
                if not PDF_AVAILABLE:
                    await query.edit_message_text(f"{EMOJIS['error']} ميزة PDF غير متوفرة حالياً.")
                    return
                
                # إنشاء ملف PDF
                pdf_buffer = AccountStatementGenerator.generate_pdf_statement(user, transactions, days)
                filename = f"كشف_حساب_{user['wallet_number']}_{filename_date}.pdf"
                
                # إرسال الملف
                await context.bot.send_document(
                    chat_id=query.message.chat_id,
                    document=pdf_buffer,
                    filename=filename,
                    caption=f"🎟️ **كشف الحساب - PDF**\n\n👤 **{user['full_name']}**\n📅 **الفترة:** {period_text}\n⏰ **تم الإنشاء:** {datetime.now().strftime('%Y-%m-%d %H:%M')}"
                )
            
            # رسالة تأكيد
            success_text = f"""
✅ **تم إنشاء كشف الحساب بنجاح!** ✅

🎟️ **تم إرسال الملف أعلاه**
📋 **التنسيق:** {format_type.upper()}
📅 **الفترة:** {period_text}
📊 **عدد المعاملات:** {len(transactions)}

💡 **ملاحظة:** يمكنك تنزيل كشف حساب جديد في أي وقت
"""
            
            keyboard = [
                [InlineKeyboardButton('🎟️ تنزيل كشف آخر', callback_data='account_statement'),
                 InlineKeyboardButton('💳 محفظتي', callback_data='enhanced_wallet')],
                [InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
            ]
            
            await query.edit_message_text(
                success_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Error downloading statement: {e}")
            await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في إنشاء كشف الحساب.")

# دوال مساعدة للاستدعاء السريع
async def account_statement_handler(update: Update, context: CallbackContext):
    """معالج عرض خيارات كشف الحساب"""
    return await AccountStatementGenerator.show_statement_options(update, context)

async def download_excel_30_handler(update: Update, context: CallbackContext):
    """تنزيل Excel - آخر 30 يوم"""
    return await AccountStatementGenerator.download_statement_handler(update, context, 'excel', 30)

async def download_excel_90_handler(update: Update, context: CallbackContext):
    """تنزيل Excel - آخر 90 يوم"""
    return await AccountStatementGenerator.download_statement_handler(update, context, 'excel', 90)

async def download_excel_all_handler(update: Update, context: CallbackContext):
    """تنزيل Excel - جميع المعاملات"""
    return await AccountStatementGenerator.download_statement_handler(update, context, 'excel', None)

async def download_pdf_30_handler(update: Update, context: CallbackContext):
    """تنزيل PDF - آخر 30 يوم"""
    return await AccountStatementGenerator.download_statement_handler(update, context, 'pdf', 30)

async def download_pdf_90_handler(update: Update, context: CallbackContext):
    """تنزيل PDF - آخر 90 يوم"""
    return await AccountStatementGenerator.download_statement_handler(update, context, 'pdf', 90)

async def download_pdf_all_handler(update: Update, context: CallbackContext):
    """تنزيل PDF - جميع المعاملات"""
    return await AccountStatementGenerator.download_statement_handler(update, context, 'pdf', None)