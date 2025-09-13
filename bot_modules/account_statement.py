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
from bot_modules.enhanced_excel_generator import EnhancedExcelGenerator

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
                    SELECT id, type, amount, description, created_at, 
                           CASE 
                               WHEN from_user = ? THEN 'outgoing'
                               WHEN to_user = ? THEN 'incoming'
                               ELSE 'unknown'
                           END as direction,
                           provider_share, admin_share, total_amount
                    FROM transactions 
                    WHERE (from_user = ? OR to_user = ?) 
                    AND created_at >= datetime('now', '-' || ? || ' days')
                    ORDER BY created_at DESC
                ''', (user_id, user_id, user_id, user_id, days))
            else:
                cursor.execute('''
                    SELECT id, type, amount, description, created_at,
                           CASE 
                               WHEN from_user = ? THEN 'outgoing'
                               WHEN to_user = ? THEN 'incoming'
                               ELSE 'unknown'
                           END as direction,
                           provider_share, admin_share, total_amount
                    FROM transactions 
                    WHERE from_user = ? OR to_user = ?
                    ORDER BY created_at DESC
                ''', (user_id, user_id, user_id, user_id))
            
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
        
        # إحصائيات المعاملات (مع دعم الحقول الجديدة)
        incoming_total = sum(t[2] for t in transactions if t[5] == 'incoming')
        outgoing_total = sum(t[2] for t in transactions if t[5] == 'outgoing')
        net_total = incoming_total - outgoing_total
        
        # إحصائيات الأرباح (للمزودين)
        provider_earnings = sum(t[6] for t in transactions if len(t) > 6 and t[6])
        admin_earnings = sum(t[7] for t in transactions if len(t) > 7 and t[7])
        
        ws['D3'] = "إجمالي الوارد:"
        ws['E3'] = f"+{incoming_total:,.2f} ريال"
        ws['D4'] = "إجمالي الصادر:"
        ws['E4'] = f"-{outgoing_total:,.2f} ريال"
        ws['D5'] = "صافي الحركة:"
        ws['E5'] = f"{net_total:+,.2f} ريال"
        ws['D6'] = "عدد المعاملات:"
        ws['E6'] = f"{len(transactions)} معاملة"
        
        # إحصائيات الأرباح (إذا كان مزود)
        if provider_earnings > 0:
            ws['D7'] = "أرباح المزود (70%):"
            ws['E7'] = f"{provider_earnings:,.2f} ريال"
        if admin_earnings > 0:
            ws['D8'] = "حصة الإدارة (30%):"
            ws['E8'] = f"{admin_earnings:,.2f} ريال"
        
        # عناوين الجدول
        headers = ['التاريخ', 'الاتجاه', 'نوع المعاملة', 'المبلغ', 'الوصف', 'حصة المزود', 'حصة الإدارة']
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
            'card_purchase': 'شراء كرت',
            'money_creation': 'إنشاء رصيد',
            'transfer_fee': 'رسوم تحويل',
            'refund': 'استرداد'
        }
        
        for row, transaction in enumerate(transactions, 10):
            # تحديد اتجاه المعاملة مع الأيقونات
            direction = transaction[5]  # الاتجاه من الاستعلام الجديد
            if direction == 'outgoing':
                direction_text = "🔴 صادر"
                amount_text = f"-{transaction[2]:,.2f}"
            elif direction == 'incoming':
                direction_text = "🟢 وارد"
                amount_text = f"+{transaction[2]:,.2f}"
            else:
                direction_text = "💼 غير محدد"
                amount_text = f"{transaction[2]:,.2f}"
            
            # الحصول على بيانات الأرباح إذا متوفرة
            provider_share = transaction[6] if len(transaction) > 6 and transaction[6] else ""
            admin_share = transaction[7] if len(transaction) > 7 and transaction[7] else ""
            
            ws.cell(row=row, column=1, value=transaction[4][:16]).border = border  # التاريخ
            ws.cell(row=row, column=2, value=direction_text).border = border  # الاتجاه
            ws.cell(row=row, column=3, value=transaction_types.get(transaction[1], transaction[1])).border = border  # النوع
            ws.cell(row=row, column=4, value=amount_text).border = border  # المبلغ مع الإشارة
            ws.cell(row=row, column=5, value=transaction[3] or '').border = border  # الوصف
            ws.cell(row=row, column=6, value=f"{provider_share:,.2f}" if provider_share else "").border = border  # حصة المزود
            ws.cell(row=row, column=7, value=f"{admin_share:,.2f}" if admin_share else "").border = border  # حصة الإدارة
        
        # تنسيق عرض الأعمدة (تحديث لـ 7 أعمدة)
        for col in range(1, 8):
            ws.column_dimensions[get_column_letter(col)].width = 18
        
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
        
        # العنوان الرئيسي (بدون أيقونات)
        title = Paragraph("Account Statement - كشف الحساب", styles['Title'])
        story.append(title)
        story.append(Spacer(1, 12))
        
        # حساب الإحصائيات (مع دعم الحقول الجديدة)
        incoming_total = sum(t[2] for t in transactions if t[5] == 'incoming')
        outgoing_total = sum(t[2] for t in transactions if t[5] == 'outgoing')
        
        # إحصائيات الأرباح
        provider_earnings = sum(t[6] for t in transactions if len(t) > 6 and t[6])
        admin_earnings = sum(t[7] for t in transactions if len(t) > 7 and t[7])
        
        # معلومات المستخدم (نص بسيط بدون أيقونات)
        user_info = f"""
        <b>Customer Name:</b> {user['full_name']}<br/>
        <b>Wallet Number:</b> {user['wallet_number']}<br/>
        <b>Current Balance:</b> {user['balance']:,.2f} YER<br/>
        <b>Period:</b> {"Last " + str(days) + " days" if days else "All transactions"}<br/>
        <b>Generated:</b> {datetime.now().strftime('%Y-%m-%d %H:%M')}<br/><br/>
        <b>Transaction Summary:</b><br/>
        <b>Total Incoming:</b> +{incoming_total:,.2f} YER<br/>
        <b>Total Outgoing:</b> -{outgoing_total:,.2f} YER<br/>
        <b>Net Movement:</b> {incoming_total - outgoing_total:+,.2f} YER<br/>
        <b>Total Transactions:</b> {len(transactions)}<br/>
        {f"<b>Provider Earnings (70%):</b> {provider_earnings:,.2f} YER<br/>" if provider_earnings > 0 else ""}
        {f"<b>Admin Share (30%):</b> {admin_earnings:,.2f} YER<br/>" if admin_earnings > 0 else ""}
        """
        
        user_para = Paragraph(user_info, arabic_style)
        story.append(user_para)
        story.append(Spacer(1, 20))
        
        # جدول المعاملات (نص بسيط بدون أيقونات)
        if transactions:
            # عناوين الجدول (بالإنجليزية لتجنب مشاكل العرض)
            data = [['Date', 'Direction', 'Type', 'Amount', 'Description', 'Provider', 'Admin']]
            
            transaction_types = {
                'purchase': 'Purchase',
                'transfer': 'Transfer', 
                'coupon_redeem': 'Coupon Redeem',
                'commission': 'Commission',
                'card_purchase': 'Card Purchase',
                'money_creation': 'Money Creation',
                'transfer_fee': 'Transfer Fee',
                'refund': 'Refund'
            }
            
            for transaction in transactions:
                # تحديد اتجاه المعاملة (بدون أيقونات)
                direction = transaction[5]  # الاتجاه من الاستعلام
                if direction == 'outgoing':
                    direction_text = "OUT"
                    amount_text = f"-{transaction[2]:,.2f}"
                elif direction == 'incoming':
                    direction_text = "IN"
                    amount_text = f"+{transaction[2]:,.2f}"
                else:
                    direction_text = "N/A"
                    amount_text = f"{transaction[2]:,.2f}"
                
                # الحصول على بيانات الأرباح
                provider_share = transaction[6] if len(transaction) > 6 and transaction[6] else ""
                admin_share = transaction[7] if len(transaction) > 7 and transaction[7] else ""
                
                data.append([
                    transaction[4][:16],  # created_at
                    direction_text,  # الاتجاه
                    transaction_types.get(transaction[1], transaction[1]),  # type
                    amount_text + " YER",  # amount مع العملة
                    (transaction[3] or '')[:25],  # description
                    f"{provider_share:,.2f}" if provider_share else "",  # حصة المزود
                    f"{admin_share:,.2f}" if admin_share else ""  # حصة الإدارة
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
                
                # إنشاء ملف Excel محسّن
                excel_buffer = EnhancedExcelGenerator.generate_enhanced_statement(user, transactions, days)
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
    """معالج عرض خيارات كشف الحساب يدعم الأوامر والأزرار"""
    try:
        is_callback = hasattr(update, 'callback_query') and update.callback_query
        if is_callback:
            return await AccountStatementGenerator.show_statement_options(update, context)
        else:
            # محادثة أمر /statement
            return await AccountStatementGenerator.show_statement_options(update, context)
    except Exception as e:
        from bot_modules.enhanced_error_messages import unexpected_error
        if is_callback:
            await update.callback_query.edit_message_text(unexpected_error("كشف الحساب", "عرض الخيارات"))
        else:
            await update.message.reply_text(unexpected_error("كشف الحساب", "عرض الخيارات"))

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