"""
خدمة التقارير المتقدمة
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from bot.database.connection import db_manager
from bot.models.rating import RatingSystem

logger = logging.getLogger(__name__)

class ReportService:
    """خدمة إنشاء التقارير المتقدمة"""
    
    @staticmethod
    def generate_sales_report(supplier_id: Optional[int] = None, days: int = 30) -> str:
        """إنشاء تقرير المبيعات والربحية"""
        
        try:
            with db_manager.get_cursor() as (conn, cursor):
                end_date = datetime.now()
                start_date = end_date - timedelta(days=days)
                
                # استعلام أساسي للمبيعات
                base_query = '''
                    SELECT 
                        COUNT(*) as total_sales,
                        SUM(t.amount) as total_revenue,
                        AVG(t.amount) as avg_sale_amount,
                        DATE(t.created_at) as sale_date
                    FROM transactions t
                    WHERE t.type = 'card_purchase' 
                    AND t.status = 'completed'
                    AND t.created_at >= ? AND t.created_at <= ?
                '''
                
                params = [start_date.isoformat(), end_date.isoformat()]
                
                if supplier_id:
                    base_query += ' AND t.to_user = ?'
                    params.append(supplier_id)
                
                base_query += ' GROUP BY DATE(t.created_at) ORDER BY sale_date DESC'
                
                cursor.execute(base_query, params)
                daily_sales = cursor.fetchall()
                
                # إحصائيات عامة
                cursor.execute('''
                    SELECT 
                        COUNT(*) as total_transactions,
                        SUM(amount) as total_amount,
                        AVG(amount) as avg_amount
                    FROM transactions 
                    WHERE type = 'card_purchase' 
                    AND status = 'completed'
                    AND created_at >= ? AND created_at <= ?
                ''' + (' AND to_user = ?' if supplier_id else ''), 
                params[:2] + ([supplier_id] if supplier_id else []))
                
                general_stats = cursor.fetchone()
                
                # أفضل العملاء
                cursor.execute('''
                    SELECT 
                        u.full_name,
                        COUNT(*) as purchase_count,
                        SUM(t.amount) as total_spent
                    FROM transactions t
                    JOIN users u ON t.from_user = u.id
                    WHERE t.type = 'card_purchase' 
                    AND t.status = 'completed'
                    AND t.created_at >= ? AND t.created_at <= ?
                ''' + (' AND t.to_user = ?' if supplier_id else '') + '''
                    GROUP BY t.from_user, u.full_name
                    ORDER BY total_spent DESC
                    LIMIT 5
                ''', params[:2] + ([supplier_id] if supplier_id else []))
                
                top_customers = cursor.fetchall()
                
                # بناء التقرير
                report = f"""📊 تقرير المبيعات والربحية
📅 الفترة: {days} يوم الماضية

📈 الإحصائيات العامة:
• إجمالي المعاملات: {general_stats[0] if general_stats[0] else 0}
• إجمالي الإيرادات: {general_stats[1]:.2f if general_stats[1] else 0:.2f} ريال
• متوسط قيمة المعاملة: {general_stats[2]:.2f if general_stats[2] else 0:.2f} ريال

📊 المبيعات اليومية (آخر 7 أيام):"""
                
                for sale in daily_sales[:7]:
                    date_str = sale[3]
                    report += f"\n• {date_str}: {sale[0]} معاملة - {sale[1]:.2f} ريال"
                
                if top_customers:
                    report += "\n\n👥 أفضل العملاء:"
                    for i, customer in enumerate(top_customers, 1):
                        report += f"\n{i}. {customer[0]} - {customer[2]:.2f} ريال ({customer[1]} معاملة)"
                
                return report
                
        except Exception as e:
            logger.error(f"خطأ في إنشاء تقرير المبيعات: {e}")
            return "حدث خطأ في إنشاء التقرير"
    
    @staticmethod
    def generate_user_activity_report(days: int = 30) -> str:
        """تقرير نشاط المستخدمين"""
        
        try:
            with db_manager.get_cursor() as (conn, cursor):
                end_date = datetime.now()
                start_date = end_date - timedelta(days=days)
                
                # إحصائيات المستخدمين
                cursor.execute('''
                    SELECT 
                        role,
                        COUNT(*) as user_count,
                        COUNT(CASE WHEN is_active = 1 THEN 1 END) as active_count
                    FROM users 
                    GROUP BY role
                ''')
                
                user_stats = cursor.fetchall()
                
                # المستخدمين الجدد
                cursor.execute('''
                    SELECT COUNT(*) 
                    FROM users 
                    WHERE created_at >= ? AND created_at <= ?
                ''', (start_date.isoformat(), end_date.isoformat()))
                
                new_users = cursor.fetchone()[0]
                
                # النشاط اليومي
                cursor.execute('''
                    SELECT 
                        DATE(created_at) as activity_date,
                        COUNT(DISTINCT user_id) as active_users,
                        COUNT(*) as total_actions
                    FROM activity_log 
                    WHERE created_at >= ? AND created_at <= ?
                    GROUP BY DATE(created_at)
                    ORDER BY activity_date DESC
                    LIMIT 7
                ''', (start_date.isoformat(), end_date.isoformat()))
                
                daily_activity = cursor.fetchall()
                
                # بناء التقرير
                report = f"""👥 تقرير نشاط المستخدمين
📅 الفترة: {days} يوم الماضية

📊 إحصائيات المستخدمين:"""
                
                total_users = 0
                total_active = 0
                
                for stat in user_stats:
                    role, count, active = stat
                    total_users += count
                    total_active += active
                    report += f"\n• {role}: {count} ({active} نشط)"
                
                report += f"\n\n📈 إجمالي المستخدمين: {total_users}"
                report += f"\n✅ المستخدمين النشطين: {total_active}"
                report += f"\n🆕 مستخدمين جدد: {new_users}"
                
                if daily_activity:
                    report += "\n\n📅 النشاط اليومي:"
                    for activity in daily_activity:
                        date_str, active_users, actions = activity
                        report += f"\n• {date_str}: {active_users} مستخدم نشط - {actions} إجراء"
                
                return report
                
        except Exception as e:
            logger.error(f"خطأ في تقرير النشاط: {e}")
            return "حدث خطأ في إنشاء التقرير"
    
    @staticmethod
    def generate_financial_report(days: int = 30) -> str:
        """التقرير المالي المفصل"""
        
        try:
            with db_manager.get_cursor() as (conn, cursor):
                end_date = datetime.now()
                start_date = end_date - timedelta(days=days)
                
                # الإيرادات والمصروفات
                cursor.execute('''
                    SELECT 
                        type,
                        SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END) as total_in,
                        SUM(CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END) as total_out,
                        COUNT(*) as transaction_count
                    FROM transactions 
                    WHERE created_at >= ? AND created_at <= ?
                    AND status = 'completed'
                    GROUP BY type
                ''', (start_date.isoformat(), end_date.isoformat()))
                
                financial_data = cursor.fetchall()
                
                # إجمالي الأرصدة
                cursor.execute('SELECT SUM(balance) FROM users WHERE is_active = 1')
                total_balance = cursor.fetchone()[0] or 0
                
                # طلبات السحب المعلقة
                cursor.execute('''
                    SELECT COUNT(*), SUM(amount) 
                    FROM withdrawal_requests 
                    WHERE status = 'pending'
                ''')
                
                pending_withdrawals = cursor.fetchone()
                
                # بناء التقرير
                report = f"""💰 التقرير المالي
📅 الفترة: {days} يوم الماضية

💳 إجمالي الأرصدة: {total_balance:.2f} ريال
⏳ طلبات سحب معلقة: {pending_withdrawals[0]} طلب بقيمة {pending_withdrawals[1] or 0:.2f} ريال

📊 المعاملات المالية:"""
                
                total_revenue = 0
                total_expenses = 0
                
                type_names = {
                    'card_purchase': 'مبيعات الكروت',
                    'balance_recharge': 'شحن الرصيد',
                    'commission': 'العمولات',
                    'referral_bonus': 'مكافآت الإحالة',
                    'withdrawal': 'عمليات السحب',
                    'transfer': 'التحويلات'
                }
                
                for data in financial_data:
                    type_name = type_names.get(data[0], data[0])
                    total_in = data[1]
                    total_out = data[2]
                    count = data[3]
                    
                    total_revenue += total_in
                    total_expenses += total_out
                    
                    report += f"\n• {type_name}: +{total_in:.2f} / -{total_out:.2f} ريال ({count} معاملة)"
                
                net_profit = total_revenue - total_expenses
                report += f"\n\n💵 إجمالي الإيرادات: {total_revenue:.2f} ريال"
                report += f"\n💸 إجمالي المصروفات: {total_expenses:.2f} ريال"
                report += f"\n{'📈' if net_profit >= 0 else '📉'} صافي الربح: {net_profit:.2f} ريال"
                
                return report
                
        except Exception as e:
            logger.error(f"خطأ في التقرير المالي: {e}")
            return "حدث خطأ في إنشاء التقرير"
    
    @staticmethod
    def generate_comprehensive_report(supplier_id: Optional[int] = None) -> str:
        """تقرير شامل"""
        
        try:
            reports = []
            
            # تقرير المبيعات
            reports.append(ReportService.generate_sales_report(supplier_id, 30))
            
            # تقرير التقييمات
            reports.append(RatingSystem.generate_rating_report())
            
            if not supplier_id:  # التقارير الإدارية فقط
                reports.append(ReportService.generate_user_activity_report(30))
                reports.append(ReportService.generate_financial_report(30))
            
            return "\n\n" + "="*50 + "\n\n".join(reports)
            
        except Exception as e:
            logger.error(f"خطأ في التقرير الشامل: {e}")
            return "حدث خطأ في إنشاء التقرير الشامل"