#!/usr/bin/env python3
"""
Balance Verifier - نظام التحقق من توازن الحسابات
يتحقق دورياً من سلامة الأرصدة والحسابات المحاسبية
"""

import logging
import schedule
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from bot_modules.database import get_db_connection
from bot_modules.accounting_engine import AccountingEngine

logger = logging.getLogger(__name__)

class BalanceVerifier:
    """نظام التحقق من توازن الحسابات"""
    
    def __init__(self):
        self.running = False
        self.verifier_thread = None
        self.last_verification = None
        self.verification_results = []
        
        # تكوين الجدولة
        self._setup_schedule()
    
    def _setup_schedule(self):
        """تكوين جدولة التحقق من الأرصدة"""
        # تحقق كامل كل 6 ساعات
        schedule.every(6).hours.do(self.run_full_verification)
        
        # تحقق سريع كل ساعة
        schedule.every().hour.do(self.run_quick_verification)
        
        # تحقق شامل يومي في الساعة 4 صباحاً
        schedule.every().day.at("04:00").do(self.run_comprehensive_verification)
    
    def start_scheduler(self):
        """بدء المجدول التلقائي للتحقق"""
        if self.running:
            return
        
        self.running = True
        self.verifier_thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.verifier_thread.start()
        logger.info("Balance verifier scheduler started")
    
    def stop_scheduler(self):
        """إيقاف المجدول التلقائي"""
        self.running = False
        if self.verifier_thread:
            self.verifier_thread.join(timeout=5)
        logger.info("Balance verifier scheduler stopped")
    
    def _run_scheduler(self):
        """تشغيل المجدول في thread منفصل"""
        while self.running:
            try:
                schedule.run_pending()
                time.sleep(300)  # فحص كل 5 دقائق
            except Exception as e:
                logger.error(f"Balance verifier scheduler error: {e}")
                time.sleep(300)
    
    def run_quick_verification(self) -> Dict:
        """تحقق سريع من الأرصدة الأساسية"""
        try:
            results = {
                'timestamp': datetime.now().isoformat(),
                'verification_type': 'quick',
                'issues_found': [],
                'summary': {}
            }
            
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # 1. التحقق من الأرصدة السالبة
            cursor.execute('SELECT id, telegram_id, full_name, balance FROM users WHERE balance < 0')
            negative_balances = cursor.fetchall()
            
            if negative_balances:
                results['issues_found'].append({
                    'type': 'negative_balance',
                    'severity': 'high',
                    'count': len(negative_balances),
                    'details': [dict(user) for user in negative_balances]
                })
            
            # 2. التحقق من إجمالي الأرصدة مقابل المعاملات
            cursor.execute('SELECT COALESCE(SUM(balance), 0) as total_balance FROM users')
            total_user_balance = float(cursor.fetchone()['total_balance'])
            
            cursor.execute('''
                SELECT COALESCE(SUM(CASE 
                    WHEN transaction_type LIKE '%_in' OR transaction_type = 'deposit' THEN amount
                    WHEN transaction_type LIKE '%_out' OR transaction_type = 'withdrawal' THEN -amount
                    ELSE 0 
                END), 0) as calculated_balance 
                FROM wallet_transactions
            ''')
            calculated_balance = float(cursor.fetchone()['calculated_balance'])
            
            balance_difference = abs(total_user_balance - calculated_balance)
            
            if balance_difference > 1.0:  # تسامح 1 ريال للأخطاء العائمة
                results['issues_found'].append({
                    'type': 'balance_mismatch',
                    'severity': 'high',
                    'total_user_balance': total_user_balance,
                    'calculated_balance': calculated_balance,
                    'difference': balance_difference
                })
            
            # 3. ملخص النتائج
            results['summary'] = {
                'total_users': self._get_total_users(),
                'total_balance': total_user_balance,
                'issues_count': len(results['issues_found']),
                'status': 'healthy' if not results['issues_found'] else 'issues_found'
            }
            
            conn.close()
            self.last_verification = datetime.now()
            self._save_verification_result(results)
            
            if results['issues_found']:
                logger.warning(f"Quick verification found {len(results['issues_found'])} issues")
            else:
                logger.info("Quick verification completed - no issues found")
            
            return results
            
        except Exception as e:
            logger.error(f"Quick verification failed: {e}")
            return {'error': str(e), 'timestamp': datetime.now().isoformat()}
    
    def run_full_verification(self) -> Dict:
        """تحقق كامل من الأرصدة والحسابات"""
        try:
            results = {
                'timestamp': datetime.now().isoformat(),
                'verification_type': 'full',
                'issues_found': [],
                'summary': {},
                'user_checks': []
            }
            
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # تشغيل التحقق السريع أولاً
            quick_results = self.run_quick_verification()
            if 'issues_found' in quick_results:
                results['issues_found'].extend(quick_results['issues_found'])
            
            # 4. التحقق من كل مستخدم على حدة
            cursor.execute('SELECT id, telegram_id, full_name, balance FROM users LIMIT 1000')
            users = cursor.fetchall()
            
            inconsistent_users = []
            
            for user in users:
                user_verification = self._verify_single_user(user['id'])
                if not user_verification['is_consistent']:
                    inconsistent_users.append({
                        'user_id': user['id'],
                        'telegram_id': user['telegram_id'],
                        'full_name': user['full_name'],
                        'current_balance': user['balance'],
                        'calculated_balance': user_verification['calculated_balance'],
                        'difference': user_verification['difference']
                    })
            
            if inconsistent_users:
                results['issues_found'].append({
                    'type': 'user_balance_inconsistency',
                    'severity': 'medium',
                    'count': len(inconsistent_users),
                    'details': inconsistent_users
                })
            
            # 5. التحقق من المعاملات المعلقة
            cursor.execute('''
                SELECT COUNT(*) as pending_count 
                FROM transactions 
                WHERE created_at > datetime('now', '-1 hour') 
                AND status IS NULL
            ''')
            pending_transactions = cursor.fetchone()['pending_count']
            
            if pending_transactions > 10:
                results['issues_found'].append({
                    'type': 'high_pending_transactions',
                    'severity': 'medium',
                    'count': pending_transactions
                })
            
            # 6. ملخص النتائج
            results['summary'] = {
                'total_users_checked': len(users),
                'inconsistent_users': len(inconsistent_users),
                'pending_transactions': pending_transactions,
                'total_issues': len(results['issues_found']),
                'status': 'healthy' if not results['issues_found'] else 'issues_found'
            }
            
            conn.close()
            self.last_verification = datetime.now()
            self._save_verification_result(results)
            
            logger.info(f"Full verification completed - found {len(results['issues_found'])} issues")
            return results
            
        except Exception as e:
            logger.error(f"Full verification failed: {e}")
            return {'error': str(e), 'timestamp': datetime.now().isoformat()}
    
    def run_comprehensive_verification(self) -> Dict:
        """تحقق شامل يتضمن النظام المحاسبي"""
        try:
            results = {
                'timestamp': datetime.now().isoformat(),
                'verification_type': 'comprehensive',
                'issues_found': [],
                'summary': {},
                'accounting_check': {}
            }
            
            # تشغيل التحقق الكامل أولاً
            full_results = self.run_full_verification()
            if 'issues_found' in full_results:
                results['issues_found'].extend(full_results['issues_found'])
            
            # 7. التحقق من النظام المحاسبي
            accounting_verification = self._verify_accounting_system()
            results['accounting_check'] = accounting_verification
            
            if not accounting_verification.get('balanced', True):
                results['issues_found'].append({
                    'type': 'accounting_imbalance',
                    'severity': 'critical',
                    'details': accounting_verification
                })
            
            # 8. التحقق من سلامة العلاقات
            relationship_issues = self._verify_data_relationships()
            if relationship_issues:
                results['issues_found'].extend(relationship_issues)
            
            # 9. ملخص شامل
            results['summary'] = {
                'verification_duration': (datetime.now() - datetime.fromisoformat(results['timestamp'])).total_seconds(),
                'total_issues': len(results['issues_found']),
                'critical_issues': len([i for i in results['issues_found'] if i.get('severity') == 'critical']),
                'high_issues': len([i for i in results['issues_found'] if i.get('severity') == 'high']),
                'medium_issues': len([i for i in results['issues_found'] if i.get('severity') == 'medium']),
                'status': 'healthy' if not results['issues_found'] else 'critical' if any(i.get('severity') == 'critical' for i in results['issues_found']) else 'issues_found'
            }
            
            self.last_verification = datetime.now()
            self._save_verification_result(results)
            
            logger.info(f"Comprehensive verification completed - Status: {results['summary']['status']}")
            return results
            
        except Exception as e:
            logger.error(f"Comprehensive verification failed: {e}")
            return {'error': str(e), 'timestamp': datetime.now().isoformat()}
    
    def _verify_single_user(self, user_id: int) -> Dict:
        """التحقق من رصيد مستخدم واحد"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            # الرصيد الحالي
            cursor.execute('SELECT balance FROM users WHERE id = ?', (user_id,))
            user_data = cursor.fetchone()
            if not user_data:
                return {'error': 'User not found'}
            
            current_balance = float(user_data['balance'])
            
            # حساب الرصيد من المعاملات
            cursor.execute('''
                SELECT COALESCE(SUM(amount), 0) as calculated_balance
                FROM wallet_transactions 
                WHERE user_id = ?
            ''', (user_id,))
            
            calculated_balance = float(cursor.fetchone()['calculated_balance'])
            
            # مقارنة الأرصدة
            difference = abs(current_balance - calculated_balance)
            is_consistent = difference < 0.01  # تسامح للأخطاء العائمة
            
            return {
                'user_id': user_id,
                'current_balance': current_balance,
                'calculated_balance': calculated_balance,
                'difference': difference,
                'is_consistent': is_consistent
            }
            
        finally:
            conn.close()
    
    def _verify_accounting_system(self) -> Dict:
        """التحقق من توازن النظام المحاسبي"""
        try:
            # استخدام دالة التحقق من النظام المحاسبي
            integrity_result = AccountingEngine.verify_balance_integrity()
            
            return {
                'balanced': integrity_result.get('balanced', False),
                'total_debit': integrity_result.get('total_debit', 0),
                'total_credit': integrity_result.get('total_credit', 0),
                'difference': integrity_result.get('difference', 0),
                'accounts_checked': integrity_result.get('accounts_count', 0)
            }
            
        except Exception as e:
            logger.error(f"Accounting verification failed: {e}")
            return {'error': str(e), 'balanced': False}
    
    def _verify_data_relationships(self) -> List[Dict]:
        """التحقق من سلامة العلاقات في قاعدة البيانات"""
        issues = []
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            # التحقق من المعاملات بدون مستخدمين
            cursor.execute('''
                SELECT COUNT(*) as orphaned_transactions
                FROM transactions t
                LEFT JOIN users u1 ON t.from_user = u1.id
                LEFT JOIN users u2 ON t.to_user = u2.id
                WHERE u1.id IS NULL OR u2.id IS NULL
            ''')
            
            orphaned_count = cursor.fetchone()['orphaned_transactions']
            if orphaned_count > 0:
                issues.append({
                    'type': 'orphaned_transactions',
                    'severity': 'high',
                    'count': orphaned_count,
                    'description': 'معاملات مرتبطة بمستخدمين غير موجودين'
                })
            
            # التحقق من الشبكات بدون موردين
            cursor.execute('''
                SELECT COUNT(*) as orphaned_networks
                FROM networks n
                LEFT JOIN users u ON n.supplier_id = u.id
                WHERE u.id IS NULL
            ''')
            
            orphaned_networks = cursor.fetchone()['orphaned_networks']
            if orphaned_networks > 0:
                issues.append({
                    'type': 'orphaned_networks',
                    'severity': 'medium',
                    'count': orphaned_networks,
                    'description': 'شبكات مرتبطة بموردين غير موجودين'
                })
            
        except Exception as e:
            logger.error(f"Relationship verification failed: {e}")
            issues.append({
                'type': 'verification_error',
                'severity': 'medium',
                'error': str(e)
            })
        
        finally:
            conn.close()
        
        return issues
    
    def _get_total_users(self) -> int:
        """الحصول على إجمالي عدد المستخدمين"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('SELECT COUNT(*) as total FROM users')
            return cursor.fetchone()['total']
        finally:
            conn.close()
    
    def _save_verification_result(self, result: Dict):
        """حفظ نتائج التحقق"""
        # الاحتفاظ بآخر 50 نتيجة فقط
        self.verification_results.append(result)
        if len(self.verification_results) > 50:
            self.verification_results = self.verification_results[-50:]
    
    def get_verification_history(self, limit: int = 10) -> List[Dict]:
        """الحصول على تاريخ التحقق"""
        return self.verification_results[-limit:]
    
    def get_verification_status(self) -> Dict:
        """الحصول على حالة نظام التحقق"""
        return {
            'scheduler_running': self.running,
            'last_verification': self.last_verification.isoformat() if self.last_verification else None,
            'total_verifications': len(self.verification_results),
            'latest_result': self.verification_results[-1] if self.verification_results else None
        }
    
    def fix_balance_inconsistency(self, user_id: int) -> Dict:
        """إصلاح عدم تطابق رصيد مستخدم"""
        try:
            verification = self._verify_single_user(user_id)
            
            if verification.get('is_consistent', True):
                return {'status': 'no_fix_needed', 'message': 'الرصيد متطابق'}
            
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # تحديث الرصيد للرصيد المحسوب
            cursor.execute('''
                UPDATE users 
                SET balance = ?, last_activity = ?
                WHERE id = ?
            ''', (verification['calculated_balance'], datetime.now(), user_id))
            
            # تسجيل عملية الإصلاح
            cursor.execute('''
                INSERT INTO wallet_transactions 
                (id, user_id, transaction_type, amount, balance_before, 
                 balance_after, description, created_at)
                VALUES (?, ?, 'balance_correction', ?, ?, ?, ?, ?)
            ''', (
                f"fix_{user_id}_{int(time.time())}", user_id, 
                verification['calculated_balance'] - verification['current_balance'],
                verification['current_balance'], verification['calculated_balance'],
                f"تصحيح رصيد - فرق: {verification['difference']:.2f}",
                datetime.now()
            ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Fixed balance inconsistency for user {user_id}: {verification['difference']:.2f}")
            
            return {
                'status': 'fixed',
                'old_balance': verification['current_balance'],
                'new_balance': verification['calculated_balance'],
                'correction_amount': verification['calculated_balance'] - verification['current_balance']
            }
            
        except Exception as e:
            logger.error(f"Failed to fix balance for user {user_id}: {e}")
            return {'status': 'error', 'error': str(e)}

# إنشاء مثيل عام للاستخدام
balance_verifier = BalanceVerifier()