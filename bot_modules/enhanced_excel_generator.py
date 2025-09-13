#!/usr/bin/env python3
"""
Enhanced Excel Generator - مولد Excel محسّن
يوفر تصميم احترافي مع pivot tables وصيغ تلخيصية
"""

import io
import logging
from datetime import datetime
from typing import Optional, List, Dict
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side, NamedStyle
from openpyxl.utils import get_column_letter
from openpyxl.chart import BarChart, LineChart, PieChart, Reference
from openpyxl.formatting.rule import ColorScaleRule, DataBarRule
from openpyxl.worksheet.table import Table, TableStyleInfo

logger = logging.getLogger(__name__)

class EnhancedExcelGenerator:
    """مولد Excel محسّن مع تصميم احترافي"""
    
    @staticmethod
    def create_styles():
        """إنشاء أنماط التنسيق"""
        styles = {}
        
        # نمط العنوان الرئيسي
        styles['main_title'] = NamedStyle(name='main_title')
        styles['main_title'].font = Font(bold=True, size=20, color="0066CC")
        styles['main_title'].alignment = Alignment(horizontal="center", vertical="center")
        
        # نمط العناوين الفرعية
        styles['subtitle'] = NamedStyle(name='subtitle')
        styles['subtitle'].font = Font(bold=True, size=14, color="333333")
        styles['subtitle'].alignment = Alignment(horizontal="center", vertical="center")
        
        # نمط رؤوس الجداول
        styles['header'] = NamedStyle(name='header')
        styles['header'].font = Font(bold=True, size=12, color="FFFFFF")
        styles['header'].fill = PatternFill(start_color="0066CC", end_color="0066CC", fill_type="solid")
        styles['header'].alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        styles['header'].border = Border(
            left=Side(style='medium'),
            right=Side(style='medium'),
            top=Side(style='medium'),
            bottom=Side(style='medium')
        )
        
        # نمط البيانات
        styles['data'] = NamedStyle(name='data')
        styles['data'].font = Font(size=11)
        styles['data'].alignment = Alignment(horizontal="right", vertical="center")
        styles['data'].border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )
        
        # نمط الأرقام
        styles['number'] = NamedStyle(name='number')
        styles['number'].font = Font(size=11)
        styles['number'].alignment = Alignment(horizontal="right", vertical="center")
        styles['number'].border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )
        styles['number'].number_format = '#,##0.00'
        
        # نمط التواريخ
        styles['date'] = NamedStyle(name='date')
        styles['date'].font = Font(size=11)
        styles['date'].alignment = Alignment(horizontal="center", vertical="center")
        styles['date'].border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )
        styles['date'].number_format = 'YYYY-MM-DD'
        
        return styles
    
    @staticmethod
    def generate_enhanced_statement(user: dict, transactions: list, days: Optional[int] = None) -> io.BytesIO:
        """إنشاء كشف حساب محسّن مع تحليلات"""
        wb = Workbook()
        
        # إضافة الأنماط
        styles = EnhancedExcelGenerator.create_styles()
        for style in styles.values():
            wb.add_named_style(style)
        
        # ======= الورقة الأولى: ملخص تنفيذي =======
        ws_summary = wb.active
        ws_summary.title = "ملخص تنفيذي"
        ws_summary.sheet_view.rightToLeft = True
        
        # شعار وعنوان
        ws_summary.merge_cells('A1:H1')
        ws_summary['A1'] = "Yemen Net - شبكة اليمن"
        ws_summary['A1'].style = 'main_title'
        ws_summary.row_dimensions[1].height = 35
        
        ws_summary.merge_cells('A2:H2')
        ws_summary['A2'] = f"كشف حساب تفصيلي - {user['full_name']}"
        ws_summary['A2'].style = 'subtitle'
        ws_summary.row_dimensions[2].height = 25
        
        # معلومات أساسية في صندوق منسق
        info_fill = PatternFill(start_color="E6F3FF", end_color="E6F3FF", fill_type="solid")
        
        row = 4
        ws_summary[f'A{row}'] = "معلومات الحساب"
        ws_summary[f'A{row}'].font = Font(bold=True, size=14)
        ws_summary.merge_cells(f'A{row}:H{row}')
        
        row += 1
        # صف المعلومات الأول
        ws_summary[f'A{row}'] = "رقم المحفظة"
        ws_summary[f'A{row}'].fill = info_fill
        ws_summary[f'B{row}'] = user['wallet_number']
        ws_summary[f'B{row}'].font = Font(bold=True)
        
        ws_summary[f'C{row}'] = "الاسم"
        ws_summary[f'C{row}'].fill = info_fill
        ws_summary[f'D{row}'] = user['full_name']
        
        ws_summary[f'E{row}'] = "الهاتف"
        ws_summary[f'E{row}'].fill = info_fill
        # التعامل مع sqlite3.Row
        try:
            phone = user['phone'] if user['phone'] else 'غير محدد'
        except:
            phone = 'غير محدد'
        ws_summary[f'F{row}'] = phone
        
        ws_summary[f'G{row}'] = "النوع"
        ws_summary[f'G{row}'].fill = info_fill
        ws_summary[f'H{row}'] = user['role']
        
        # حساب الإحصائيات
        total_in = sum(t[2] for t in transactions if t[5] == 'incoming')
        total_out = sum(t[2] for t in transactions if t[5] == 'outgoing')
        net_movement = total_in - total_out
        
        # إحصائيات مالية
        row += 2
        ws_summary[f'A{row}'] = "الإحصائيات المالية"
        ws_summary[f'A{row}'].font = Font(bold=True, size=14)
        ws_summary.merge_cells(f'A{row}:H{row}')
        
        row += 1
        stats_headers = ['المؤشر', 'القيمة', 'النسبة', 'الحالة']
        for col, header in enumerate(stats_headers, 1):
            ws_summary.cell(row=row, column=col).value = header
            ws_summary.cell(row=row, column=col).style = 'header'
        
        # البيانات المالية
        row += 1
        financial_data = [
            ['الرصيد الحالي', user['balance'], '', '✅ نشط' if user['balance'] > 0 else '⚠️ منخفض'],
            ['إجمالي الوارد', total_in, f"{(total_in/(total_in+total_out)*100) if (total_in+total_out) > 0 else 0:.1f}%", ''],
            ['إجمالي الصادر', total_out, f"{(total_out/(total_in+total_out)*100) if (total_in+total_out) > 0 else 0:.1f}%", ''],
            ['صافي الحركة', net_movement, '', '📈' if net_movement > 0 else '📉'],
            ['عدد المعاملات', len(transactions), '', f"{len(transactions)/30:.1f} معاملة/يوم" if days == 30 else '']
        ]
        
        for data in financial_data:
            ws_summary.cell(row=row, column=1).value = data[0]
            ws_summary.cell(row=row, column=2).value = data[1]
            ws_summary.cell(row=row, column=2).style = 'number' if isinstance(data[1], (int, float)) else 'data'
            ws_summary.cell(row=row, column=3).value = data[2]
            ws_summary.cell(row=row, column=4).value = data[3]
            row += 1
        
        # إضافة رسم بياني للحركة المالية
        if transactions:
            row += 2
            ws_summary[f'A{row}'] = "الرسم البياني للحركة المالية"
            ws_summary[f'A{row}'].font = Font(bold=True, size=14)
            ws_summary.merge_cells(f'A{row}:H{row}')
            
            # إعداد البيانات للرسم البياني
            chart_data = [
                ['النوع', 'المبلغ'],
                ['الوارد', total_in],
                ['الصادر', total_out]
            ]
            
            for r, row_data in enumerate(chart_data, row + 2):
                for c, value in enumerate(row_data, 1):
                    ws_summary.cell(row=r, column=c).value = value
            
            # إنشاء رسم بياني دائري
            pie = PieChart()
            labels = Reference(ws_summary, min_col=1, min_row=row+3, max_row=row+4)
            data = Reference(ws_summary, min_col=2, min_row=row+2, max_row=row+4)
            pie.add_data(data, titles_from_data=True)
            pie.set_categories(labels)
            pie.title = "توزيع الحركة المالية"
            ws_summary.add_chart(pie, f"E{row+2}")
        
        # ======= الورقة الثانية: المعاملات التفصيلية =======
        ws_transactions = wb.create_sheet("المعاملات")
        ws_transactions.sheet_view.rightToLeft = True
        
        # العنوان
        ws_transactions.merge_cells('A1:J1')
        ws_transactions['A1'] = "سجل المعاملات التفصيلي"
        ws_transactions['A1'].style = 'subtitle'
        
        # رؤوس الجدول
        headers = [
            'م', 'التاريخ', 'الوقت', 'النوع', 'الاتجاه', 
            'المبلغ', 'الرصيد بعد', 'الوصف', 'المرجع', 'الحالة'
        ]
        
        for col, header in enumerate(headers, 1):
            cell = ws_transactions.cell(row=3, column=col)
            cell.value = header
            cell.style = 'header'
        
        # البيانات
        running_balance = user['balance']
        for idx, transaction in enumerate(transactions, 1):
            row = idx + 3
            
            # حساب الرصيد التراكمي (من الأحدث للأقدم)
            if transaction[5] == 'incoming':
                running_balance -= transaction[2]
                amount_display = f"+{transaction[2]:,.2f}"
                amount_color = "008000"
            else:
                running_balance += transaction[2]
                amount_display = f"-{transaction[2]:,.2f}"
                amount_color = "FF0000"
            
            # إدخال البيانات
            ws_transactions.cell(row=row, column=1).value = idx
            ws_transactions.cell(row=row, column=2).value = transaction[4][:10]
            ws_transactions.cell(row=row, column=2).style = 'date'
            ws_transactions.cell(row=row, column=3).value = transaction[4][11:19]
            ws_transactions.cell(row=row, column=4).value = transaction[1]
            ws_transactions.cell(row=row, column=5).value = "وارد" if transaction[5] == 'incoming' else "صادر"
            
            # المبلغ بلون مميز
            amount_cell = ws_transactions.cell(row=row, column=6)
            amount_cell.value = transaction[2]
            amount_cell.style = 'number'
            amount_cell.font = Font(color=amount_color, bold=True)
            
            ws_transactions.cell(row=row, column=7).value = running_balance + transaction[2] if transaction[5] == 'incoming' else running_balance - transaction[2]
            ws_transactions.cell(row=row, column=7).style = 'number'
            ws_transactions.cell(row=row, column=8).value = transaction[3] or '-'
            ws_transactions.cell(row=row, column=9).value = f"TRX{transaction[0]}"
            ws_transactions.cell(row=row, column=10).value = "✓ مكتمل"
        
        # تحويل إلى جدول Excel
        if transactions:
            tab = Table(displayName="TransactionsTable", ref=f"A3:J{len(transactions)+3}")
            style = TableStyleInfo(
                name="TableStyleMedium2", 
                showFirstColumn=False,
                showLastColumn=False, 
                showRowStripes=True, 
                showColumnStripes=False
            )
            tab.tableStyleInfo = style
            ws_transactions.add_table(tab)
        
        # إضافة صيغ تلخيصية
        summary_row = len(transactions) + 5
        ws_transactions[f'E{summary_row}'] = "الإجمالي:"
        ws_transactions[f'E{summary_row}'].font = Font(bold=True)
        ws_transactions[f'F{summary_row}'] = f"=SUMIF(E4:E{len(transactions)+3},\"وارد\",F4:F{len(transactions)+3})-SUMIF(E4:E{len(transactions)+3},\"صادر\",F4:F{len(transactions)+3})"
        ws_transactions[f'F{summary_row}'].style = 'number'
        ws_transactions[f'F{summary_row}'].font = Font(bold=True)
        
        # ======= الورقة الثالثة: التحليلات =======
        ws_analysis = wb.create_sheet("التحليلات")
        ws_analysis.sheet_view.rightToLeft = True
        
        # تحليل حسب نوع المعاملة
        transaction_summary = {}
        for t in transactions:
            t_type = t[1]
            if t_type not in transaction_summary:
                transaction_summary[t_type] = {'count': 0, 'total': 0}
            transaction_summary[t_type]['count'] += 1
            transaction_summary[t_type]['total'] += t[2] if t[5] == 'incoming' else -t[2]
        
        # عرض التحليل
        ws_analysis['A1'] = "تحليل المعاملات حسب النوع"
        ws_analysis['A1'].style = 'subtitle'
        ws_analysis.merge_cells('A1:D1')
        
        ws_analysis['A3'] = "نوع المعاملة"
        ws_analysis['B3'] = "العدد"
        ws_analysis['C3'] = "الإجمالي"
        ws_analysis['D3'] = "المتوسط"
        
        for i in range(1, 5):
            ws_analysis.cell(row=3, column=i).style = 'header'
        
        row = 4
        for t_type, data in transaction_summary.items():
            ws_analysis[f'A{row}'] = t_type
            ws_analysis[f'B{row}'] = data['count']
            ws_analysis[f'C{row}'] = data['total']
            ws_analysis[f'C{row}'].style = 'number'
            ws_analysis[f'D{row}'] = data['total'] / data['count'] if data['count'] > 0 else 0
            ws_analysis[f'D{row}'].style = 'number'
            row += 1
        
        # ضبط عرض الأعمدة
        for sheet in wb.worksheets:
            for column in sheet.columns:
                max_length = 0
                column_letter = None
                
                # البحث عن خلية غير مدمجة للحصول على رقم العمود
                for cell in column:
                    if hasattr(cell, 'column_letter'):
                        try:
                            column_letter = cell.column_letter
                            break
                        except:
                            continue
                
                if not column_letter:
                    continue
                    
                # حساب أقصى طول
                for cell in column:
                    try:
                        if hasattr(cell, 'value') and cell.value:
                            cell_length = len(str(cell.value))
                            if cell_length > max_length:
                                max_length = cell_length
                    except:
                        pass
                
                adjusted_width = min(max_length + 2, 50)
                if adjusted_width > 0:
                    sheet.column_dimensions[column_letter].width = adjusted_width
        
        # حفظ في الذاكرة
        excel_buffer = io.BytesIO()
        wb.save(excel_buffer)
        excel_buffer.seek(0)
        return excel_buffer