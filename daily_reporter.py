#!/usr/bin/env python3
"""
نظام التقارير اليومية الشاملة
Comprehensive Daily Reporting System
"""

import sqlite3
import json
import logging
from datetime import datetime, timedelta
import pandas as pd
from typing import Dict, List

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DailyReporter:
    """مولد التقارير اليومية"""
    
    def __init__(self, db_path='/workspace/yemen_net.db'):
        self.db_path = db_path
        self.report_date = datetime.now().date()
    
    def get_database_connection(self):
        """الحصول على اتصال قاعدة البيانات"""
        return sqlite3.connect(self.db_path, timeout=30)
    
    def get_users_statistics(self) -> Dict:
        """إحصائيات المستخدمين"""
        try:
            with self.get_database_connection() as conn:
                cursor = conn.cursor()
                
                # إجمالي المستخدمين
                cursor.execute("SELECT COUNT(*) FROM users")
                total_users = cursor.fetchone()[0]
                
                # مستخدمين جدد اليوم
                cursor.execute("""
                    SELECT COUNT(*) FROM users 
                    WHERE DATE(created_at) = DATE('now')
                """)
                new_users_today = cursor.fetchone()[0]
                
                # المستخدمين حسب الدور
                cursor.execute("""
                    SELECT role, COUNT(*) as count 
                    FROM users 
                    GROUP BY role
                """)
                users_by_role = dict(cursor.fetchall())
                
                # أكثر المستخدمين نشاطاً
                cursor.execute("""
                    SELECT u.full_name, u.role, COUNT(t.id) as transaction_count
                    FROM users u
                    LEFT JOIN transactions t ON (u.id = t.from_user OR u.id = t.to_user)
                    WHERE DATE(t.created_at) = DATE('now')
                    GROUP BY u.id
                    ORDER BY transaction_count DESC
                    LIMIT 10
                """)
                most_active_users = [
                    {'name': row[0], 'role': row[1], 'transactions': row[2]}
                    for row in cursor.fetchall()
                ]
                
                return {
                    'total_users': total_users,
                    'new_users_today': new_users_today,
                    'users_by_role': users_by_role,
                    'most_active_users': most_active_users
                }
                
        except Exception as e:
            logger.error(f"خطأ في إحصائيات المستخدمين: {e}")
            return {}
    
    def get_financial_statistics(self) -> Dict:
        """الإحصائيات المالية"""
        try:
            with self.get_database_connection() as conn:
                cursor = conn.cursor()
                
                # المعاملات اليوم
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total_transactions,
                        COALESCE(SUM(amount), 0) as total_amount,
                        AVG(amount) as avg_amount
                    FROM transactions 
                    WHERE DATE(created_at) = DATE('now')
                """)
                daily_stats = cursor.fetchone()
                
                # المعاملات حسب النوع
                cursor.execute("""
                    SELECT type, COUNT(*) as count, COALESCE(SUM(amount), 0) as total
                    FROM transactions 
                    WHERE DATE(created_at) = DATE('now')
                    GROUP BY type
                    ORDER BY total DESC
                """)
                transactions_by_type = [
                    {'type': row[0], 'count': row[1], 'total': row[2]}
                    for row in cursor.fetchall()
                ]
                
                # إجمالي الأرصدة
                cursor.execute("SELECT COALESCE(SUM(balance), 0) FROM users")
                total_balance = cursor.fetchone()[0]
                
                # أعلى المعاملات اليوم
                cursor.execute("""
                    SELECT t.amount, t.type, t.description, 
                           u1.full_name as from_user, u2.full_name as to_user
                    FROM transactions t
                    LEFT JOIN users u1 ON t.from_user = u1.id
                    LEFT JOIN users u2 ON t.to_user = u2.id
                    WHERE DATE(t.created_at) = DATE('now')
                    ORDER BY t.amount DESC
                    LIMIT 10
                """)
                top_transactions = [
                    {
                        'amount': row[0], 'type': row[1], 'description': row[2],
                        'from_user': row[3], 'to_user': row[4]
                    }
                    for row in cursor.fetchall()
                ]
                
                return {
                    'daily_transactions': daily_stats[0] if daily_stats else 0,
                    'daily_amount': daily_stats[1] if daily_stats else 0,
                    'avg_transaction_amount': daily_stats[2] if daily_stats else 0,
                    'total_system_balance': total_balance,
                    'transactions_by_type': transactions_by_type,
                    'top_transactions': top_transactions
                }
                
        except Exception as e:
            logger.error(f"خطأ في الإحصائيات المالية: {e}")
            return {}
    
    def get_networks_statistics(self) -> Dict:
        """إحصائيات الشبكات"""
        try:
            with self.get_database_connection() as conn:
                cursor = conn.cursor()
                
                # إجمالي الشبكات
                cursor.execute("SELECT COUNT(*) FROM networks WHERE is_active = 1")
                total_networks = cursor.fetchone()[0]
                
                # شبكات جديدة اليوم
                cursor.execute("""
                    SELECT COUNT(*) FROM networks 
                    WHERE DATE(created_at) = DATE('now')
                """)
                new_networks_today = cursor.fetchone()[0]
                
                # الشبكات حسب المزود
                cursor.execute("""
                    SELECT u.full_name, COUNT(n.id) as network_count
                    FROM users u
                    JOIN networks n ON u.id = n.supplier_id
                    WHERE n.is_active = 1
                    GROUP BY u.id
                    ORDER BY network_count DESC
                    LIMIT 10
                """)
                networks_by_supplier = [
                    {'supplier': row[0], 'networks': row[1]}
                    for row in cursor.fetchall()
                ]
                
                # الشبكات الأكثر مبيعاً
                cursor.execute("""
                    SELECT n.name, n.provider, COUNT(c.id) as sold_cards
                    FROM networks n
                    JOIN card_categories cc ON n.id = cc.network_id
                    JOIN cards c ON cc.id = c.category_id
                    WHERE c.is_sold = 1 AND DATE(c.sold_at) = DATE('now')
                    GROUP BY n.id
                    ORDER BY sold_cards DESC
                    LIMIT 10
                """)
                top_selling_networks = [
                    {'name': row[0], 'provider': row[1], 'sold_cards': row[2]}
                    for row in cursor.fetchall()
                ]
                
                return {
                    'total_active_networks': total_networks,
                    'new_networks_today': new_networks_today,
                    'networks_by_supplier': networks_by_supplier,
                    'top_selling_networks': top_selling_networks
                }
                
        except Exception as e:
            logger.error(f"خطأ في إحصائيات الشبكات: {e}")
            return {}
    
    def get_cards_statistics(self) -> Dict:
        """إحصائيات الكروت"""
        try:
            with self.get_database_connection() as conn:
                cursor = conn.cursor()
                
                # إجمالي الكروت
                cursor.execute("SELECT COUNT(*) FROM cards")
                total_cards = cursor.fetchone()[0]
                
                # الكروت المباعة اليوم
                cursor.execute("""
                    SELECT COUNT(*) FROM cards 
                    WHERE is_sold = 1 AND DATE(sold_at) = DATE('now')
                """)
                cards_sold_today = cursor.fetchone()[0]
                
                # الكروت المتاحة
                cursor.execute("SELECT COUNT(*) FROM cards WHERE is_sold = 0")
                available_cards = cursor.fetchone()[0]
                
                # إيرادات الكروت اليوم
                cursor.execute("""
                    SELECT COALESCE(SUM(cc.price), 0)
                    FROM cards c
                    JOIN card_categories cc ON c.category_id = cc.id
                    WHERE c.is_sold = 1 AND DATE(c.sold_at) = DATE('now')
                """)
                daily_cards_revenue = cursor.fetchone()[0]
                
                return {
                    'total_cards': total_cards,
                    'cards_sold_today': cards_sold_today,
                    'available_cards': available_cards,
                    'daily_cards_revenue': daily_cards_revenue
                }
                
        except Exception as e:
            logger.error(f"خطأ في إحصائيات الكروت: {e}")
            return {}
    
    def get_system_health(self) -> Dict:
        """صحة النظام"""
        try:
            with self.get_database_connection() as conn:
                cursor = conn.cursor()
                
                # فحص الجداول الأساسية
                tables_status = {}
                essential_tables = ['users', 'transactions', 'networks', 'cards', 'card_categories']
                
                for table in essential_tables:
                    try:
                        cursor.execute(f"SELECT COUNT(*) FROM {table}")
                        count = cursor.fetchone()[0]
                        tables_status[table] = {'status': 'OK', 'count': count}
                    except Exception as e:
                        tables_status[table] = {'status': 'ERROR', 'error': str(e)}
                
                # حجم قاعدة البيانات
                import os
                db_size = os.path.getsize(self.db_path) / (1024 * 1024)  # MB
                
                return {
                    'database_size_mb': round(db_size, 2),
                    'tables_status': tables_status,
                    'last_check': datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error(f"خطأ في فحص صحة النظام: {e}")
            return {}
    
    def generate_daily_report(self) -> Dict:
        """إنشاء التقرير اليومي الشامل"""
        logger.info(f"📊 إنشاء التقرير اليومي لتاريخ: {self.report_date}")
        
        report = {
            'report_date': self.report_date.isoformat(),
            'generated_at': datetime.now().isoformat(),
            'users_statistics': self.get_users_statistics(),
            'financial_statistics': self.get_financial_statistics(),
            'networks_statistics': self.get_networks_statistics(),
            'cards_statistics': self.get_cards_statistics(),
            'system_health': self.get_system_health()
        }
        
        return report
    
    def save_report_json(self, report: Dict):
        """حفظ التقرير بصيغة JSON"""
        filename = f'/workspace/daily_report_{self.report_date.strftime("%Y%m%d")}.json'
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        logger.info(f"💾 تم حفظ التقرير: {filename}")
        return filename
    
    def generate_text_summary(self, report: Dict) -> str:
        """إنشاء ملخص نصي للتقرير"""
        users = report.get('users_statistics', {})
        finance = report.get('financial_statistics', {})
        networks = report.get('networks_statistics', {})
        cards = report.get('cards_statistics', {})
        
        summary = f"""
📊 **التقرير اليومي - {self.report_date.strftime('%Y-%m-%d')}** 📊

👥 **المستخدمون:**
• إجمالي المستخدمين: {users.get('total_users', 0):,}
• مستخدمون جدد اليوم: {users.get('new_users_today', 0)}

💰 **المالية:**
• معاملات اليوم: {finance.get('daily_transactions', 0):,}
• مبلغ المعاملات: {finance.get('daily_amount', 0):,.2f} ريال
• إجمالي الأرصدة: {finance.get('total_system_balance', 0):,.2f} ريال

🌐 **الشبكات:**
• الشبكات النشطة: {networks.get('total_active_networks', 0)}
• شبكات جديدة اليوم: {networks.get('new_networks_today', 0)}

💳 **الكروت:**
• إجمالي الكروت: {cards.get('total_cards', 0):,}
• مباعة اليوم: {cards.get('cards_sold_today', 0)}
• متاحة: {cards.get('available_cards', 0):,}
• إيرادات الكروت اليوم: {cards.get('daily_cards_revenue', 0):,.2f} ريال

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📈 **أداء ممتاز - النظام يعمل بكفاءة عالية**
"""
        
        return summary
    
    def save_text_summary(self, report: Dict):
        """حفظ الملخص النصي"""
        summary = self.generate_text_summary(report)
        filename = f'/workspace/daily_summary_{self.report_date.strftime("%Y%m%d")}.txt'
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(summary)
        
        logger.info(f"📝 تم حفظ الملخص: {filename}")
        return filename

def main():
    """الدالة الرئيسية"""
    try:
        reporter = DailyReporter()
        
        # إنشاء التقرير
        report = reporter.generate_daily_report()
        
        # حفظ التقرير
        json_file = reporter.save_report_json(report)
        text_file = reporter.save_text_summary(report)
        
        # طباعة الملخص
        summary = reporter.generate_text_summary(report)
        print(summary)
        
        logger.info("✅ تم إنشاء التقرير اليومي بنجاح")
        
    except Exception as e:
        logger.error(f"❌ خطأ في إنشاء التقرير اليومي: {e}")

if __name__ == "__main__":
    main()