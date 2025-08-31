#!/usr/bin/env python3
"""
Transaction Manager - إدارة المعاملات الآمنة
يحمي من Race Conditions ويضمن سلامة البيانات المالية
"""

import logging
import sqlite3
import threading
import time
from contextlib import contextmanager
from typing import Optional, Dict, Any, Callable, List
from datetime import datetime
from bot_modules.database import get_db_connection

logger = logging.getLogger(__name__)

class TransactionManager:
    """مدير المعاملات الآمنة مع حماية من Race Conditions وRollback متقدم"""
    
    def __init__(self):
        self._locks = {}  # Dictionary to store per-user locks
        self._global_lock = threading.RLock()
        self._active_transactions = {}  # Track active transactions for rollback
    
    def _get_user_lock(self, user_id: int) -> threading.RLock:
        """الحصول على قفل خاص بالمستخدم"""
        with self._global_lock:
            if user_id not in self._locks:
                self._locks[user_id] = threading.RLock()
            return self._locks[user_id]
    
    @contextmanager
    def safe_balance_transaction(self, *user_ids):
        """
        معاملة آمنة لتحديث أرصدة المستخدمين
        يحمي من Race Conditions عبر الـ locking
        """
        # ترتيب المستخدمين لمنع Deadlocks
        sorted_user_ids = sorted(set(user_ids))
        locks = [self._get_user_lock(uid) for uid in sorted_user_ids]
        
        # الحصول على جميع الأقفال بالترتيب
        acquired_locks = []
        try:
            for lock in locks:
                if lock.acquire(timeout=10):  # 10 seconds timeout
                    acquired_locks.append(lock)
                else:
                    raise TimeoutError("Failed to acquire lock for transaction")
            
            # إنشاء اتصال قاعدة بيانات مع معاملة
            conn = get_db_connection()
            try:
                conn.execute('BEGIN IMMEDIATE')  # Immediate lock
                yield conn
                conn.commit()
                logger.info(f"Safe transaction completed for users: {sorted_user_ids}")
            except Exception as e:
                conn.rollback()
                logger.error(f"Transaction failed for users {sorted_user_ids}: {e}")
                raise
            finally:
                conn.close()
                
        finally:
            # تحرير جميع الأقفال بالعكس
            for lock in reversed(acquired_locks):
                lock.release()
    
    def safe_balance_update(self, user_id: int, amount_change: float, 
                          operation_type: str, description: str = None,
                          reference_id: str = None) -> Dict[str, Any]:
        """
        تحديث آمن لرصيد المستخدم مع حماية من Race Conditions
        """
        with self.safe_balance_transaction(user_id) as conn:
            cursor = conn.cursor()
            
            # قراءة الرصيد الحالي مع القفل
            cursor.execute('''
                SELECT balance, telegram_id, full_name 
                FROM users 
                WHERE id = ?
            ''', (user_id,))
            
            user_data = cursor.fetchone()
            if not user_data:
                raise ValueError(f"User {user_id} not found")
            
            current_balance = float(user_data['balance'])
            new_balance = current_balance + amount_change
            
            # التحقق من صحة الرصيد الجديد
            if new_balance < 0:
                raise ValueError(f"Insufficient balance. Current: {current_balance}, Required: {abs(amount_change)}")
            
            # تحديث الرصيد
            cursor.execute('''
                UPDATE users 
                SET balance = ?, last_activity = ?
                WHERE id = ?
            ''', (new_balance, datetime.now(), user_id))
            
            # تسجيل المعاملة
            transaction_id = self._log_balance_transaction(
                cursor, user_id, current_balance, new_balance, 
                amount_change, operation_type, description, reference_id
            )
            
            return {
                'transaction_id': transaction_id,
                'user_id': user_id,
                'previous_balance': current_balance,
                'new_balance': new_balance,
                'amount_change': amount_change,
                'operation_type': operation_type
            }
    
    def safe_transfer(self, from_user_id: int, to_user_id: int, 
                     amount: float, description: str = None,
                     reference_id: str = None) -> Dict[str, Any]:
        """
        تحويل آمن بين مستخدمين مع حماية من Race Conditions
        """
        if from_user_id == to_user_id:
            raise ValueError("Cannot transfer to the same user")
        
        if amount <= 0:
            raise ValueError("Transfer amount must be positive")
        
        with self.safe_balance_transaction(from_user_id, to_user_id) as conn:
            cursor = conn.cursor()
            
            # قراءة بيانات المرسل
            cursor.execute('''
                SELECT balance, telegram_id, full_name 
                FROM users WHERE id = ?
            ''', (from_user_id,))
            
            sender_data = cursor.fetchone()
            if not sender_data:
                raise ValueError(f"Sender user {from_user_id} not found")
            
            sender_balance = float(sender_data['balance'])
            if sender_balance < amount:
                raise ValueError(f"Insufficient balance. Available: {sender_balance}, Required: {amount}")
            
            # قراءة بيانات المستقبل
            cursor.execute('''
                SELECT balance, telegram_id, full_name 
                FROM users WHERE id = ?
            ''', (to_user_id,))
            
            receiver_data = cursor.fetchone()
            if not receiver_data:
                raise ValueError(f"Receiver user {to_user_id} not found")
            
            receiver_balance = float(receiver_data['balance'])
            
            # تحديث أرصدة كلا المستخدمين
            new_sender_balance = sender_balance - amount
            new_receiver_balance = receiver_balance + amount
            
            cursor.execute('''
                UPDATE users 
                SET balance = ?, last_activity = ?
                WHERE id = ?
            ''', (new_sender_balance, datetime.now(), from_user_id))
            
            cursor.execute('''
                UPDATE users 
                SET balance = ?, last_activity = ?
                WHERE id = ?
            ''', (new_receiver_balance, datetime.now(), to_user_id))
            
            # تسجيل معاملة التحويل
            transfer_id = self._log_transfer_transaction(
                cursor, from_user_id, to_user_id, amount, 
                sender_balance, receiver_balance,
                new_sender_balance, new_receiver_balance,
                description, reference_id
            )
            
            return {
                'transfer_id': transfer_id,
                'from_user_id': from_user_id,
                'to_user_id': to_user_id,
                'amount': amount,
                'sender_previous_balance': sender_balance,
                'sender_new_balance': new_sender_balance,
                'receiver_previous_balance': receiver_balance,
                'receiver_new_balance': new_receiver_balance
            }
    
    def _log_balance_transaction(self, cursor, user_id: int, old_balance: float,
                               new_balance: float, amount_change: float,
                               operation_type: str, description: str = None,
                               reference_id: str = None) -> str:
        """تسجيل معاملة تغيير الرصيد"""
        import uuid
        transaction_id = str(uuid.uuid4())
        
        cursor.execute('''
            INSERT INTO wallet_transactions 
            (id, user_id, transaction_type, amount, balance_before, 
             balance_after, reference_id, description, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (transaction_id, user_id, operation_type, amount_change,
              old_balance, new_balance, reference_id, 
              description or f'{operation_type} transaction', 
              datetime.now()))
        
        return transaction_id
    
    def _log_transfer_transaction(self, cursor, from_user_id: int, to_user_id: int,
                                amount: float, sender_old_balance: float,
                                receiver_old_balance: float, sender_new_balance: float,
                                receiver_new_balance: float, description: str = None,
                                reference_id: str = None) -> str:
        """تسجيل معاملة التحويل"""
        import uuid
        transfer_id = str(uuid.uuid4())
        
        # تسجيل معاملة المرسل
        cursor.execute('''
            INSERT INTO wallet_transactions 
            (id, user_id, transaction_type, amount, balance_before, 
             balance_after, reference_id, description, created_at)
            VALUES (?, ?, 'transfer_out', ?, ?, ?, ?, ?, ?)
        ''', (f"{transfer_id}_out", from_user_id, -amount,
              sender_old_balance, sender_new_balance, reference_id,
              description or f'Transfer to user {to_user_id}', datetime.now()))
        
        # تسجيل معاملة المستقبل
        cursor.execute('''
            INSERT INTO wallet_transactions 
            (id, user_id, transaction_type, amount, balance_before, 
             balance_after, reference_id, description, created_at)
            VALUES (?, ?, 'transfer_in', ?, ?, ?, ?, ?, ?)
        ''', (f"{transfer_id}_in", to_user_id, amount,
              receiver_old_balance, receiver_new_balance, reference_id,
              description or f'Transfer from user {from_user_id}', datetime.now()))
        
        return transfer_id
    
    @contextmanager
    def complex_transaction(self, transaction_id: str, *user_ids):
        """
        معاملة معقدة مع إمكانية Rollback شاملة
        تدعم عدة عمليات مترابطة مع rollback تلقائي عند الفشل
        """
        # ترتيب المستخدمين لمنع Deadlocks
        sorted_user_ids = sorted(set(user_ids))
        locks = [self._get_user_lock(uid) for uid in sorted_user_ids]
        
        # تتبع حالة المعاملة
        transaction_state = {
            'id': transaction_id,
            'user_ids': sorted_user_ids,
            'operations': [],
            'snapshots': {},
            'status': 'started',
            'created_at': datetime.now()
        }
        
        self._active_transactions[transaction_id] = transaction_state
        
        # الحصول على جميع الأقفال
        acquired_locks = []
        try:
            for lock in locks:
                if lock.acquire(timeout=15):  # 15 seconds timeout for complex transactions
                    acquired_locks.append(lock)
                else:
                    raise TimeoutError(f"Failed to acquire lock for complex transaction {transaction_id}")
            
            # إنشاء اتصال قاعدة بيانات مع معاملة
            conn = get_db_connection()
            try:
                conn.execute('BEGIN IMMEDIATE')
                
                # أخذ snapshot للأرصدة قبل البدء
                self._take_balance_snapshots(conn, transaction_state, sorted_user_ids)
                
                yield conn, transaction_state
                
                # تأكيد المعاملة إذا نجحت
                conn.commit()
                transaction_state['status'] = 'committed'
                logger.info(f"Complex transaction {transaction_id} committed successfully")
                
            except Exception as e:
                # Rollback تلقائي عند الفشل
                conn.rollback()
                transaction_state['status'] = 'rolled_back'
                
                # محاولة استعادة الأرصدة إذا كان هناك تضارب
                try:
                    self._emergency_rollback(transaction_state)
                except Exception as rollback_error:
                    logger.error(f"Emergency rollback failed for {transaction_id}: {rollback_error}")
                
                logger.error(f"Complex transaction {transaction_id} failed and rolled back: {e}")
                raise
            finally:
                conn.close()
                
        finally:
            # تحرير جميع الأقفال
            for lock in reversed(acquired_locks):
                lock.release()
            
            # تنظيف تتبع المعاملة
            if transaction_id in self._active_transactions:
                del self._active_transactions[transaction_id]
    
    def _take_balance_snapshots(self, conn, transaction_state: Dict, user_ids: List[int]):
        """أخذ snapshot للأرصدة قبل بدء المعاملة المعقدة"""
        cursor = conn.cursor()
        
        for user_id in user_ids:
            cursor.execute('SELECT balance, telegram_id, full_name FROM users WHERE id = ?', (user_id,))
            user_data = cursor.fetchone()
            
            if user_data:
                transaction_state['snapshots'][user_id] = {
                    'balance': float(user_data['balance']),
                    'telegram_id': user_data['telegram_id'],
                    'full_name': user_data['full_name'],
                    'snapshot_time': datetime.now().isoformat()
                }
    
    def _emergency_rollback(self, transaction_state: Dict):
        """
        Rollback طارئ في حالة فشل المعاملة المعقدة
        يحاول استعادة الأرصدة إلى الحالة السابقة
        """
        if not transaction_state.get('snapshots'):
            logger.warning(f"No snapshots available for emergency rollback of {transaction_state['id']}")
            return
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            conn.execute('BEGIN IMMEDIATE')
            
            for user_id, snapshot in transaction_state['snapshots'].items():
                # استعادة الرصيد من الـ snapshot
                cursor.execute('''
                    UPDATE users 
                    SET balance = ?, last_activity = ?
                    WHERE id = ?
                ''', (snapshot['balance'], datetime.now(), user_id))
                
                # تسجيل عملية الاستعادة
                cursor.execute('''
                    INSERT INTO wallet_transactions 
                    (id, user_id, transaction_type, amount, balance_before, 
                     balance_after, reference_id, description, created_at)
                    VALUES (?, ?, 'emergency_rollback', ?, ?, ?, ?, ?, ?)
                ''', (
                    f"rollback_{transaction_state['id']}_{user_id}",
                    user_id, 0, snapshot['balance'], snapshot['balance'],
                    transaction_state['id'],
                    f"Emergency rollback for failed transaction {transaction_state['id']}",
                    datetime.now()
                ))
            
            conn.commit()
            logger.info(f"Emergency rollback completed for transaction {transaction_state['id']}")
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Emergency rollback failed for {transaction_state['id']}: {e}")
            raise
        finally:
            conn.close()
    
    def safe_multi_operation(self, transaction_id: str, operations: List[Dict]) -> Dict[str, Any]:
        """
        تنفيذ عدة عمليات مالية في معاملة واحدة آمنة
        operations: قائمة بالعمليات، كل عملية dict تحتوي على:
        - type: نوع العملية (transfer, balance_update, etc.)
        - params: معاملات العملية
        """
        # جمع جميع المستخدمين المتأثرين
        affected_users = set()
        for op in operations:
            if op['type'] == 'transfer':
                affected_users.add(op['params']['from_user_id'])
                affected_users.add(op['params']['to_user_id'])
            elif op['type'] == 'balance_update':
                affected_users.add(op['params']['user_id'])
        
        results = []
        
        with self.complex_transaction(transaction_id, *affected_users) as (conn, transaction_state):
            cursor = conn.cursor()
            
            for i, operation in enumerate(operations):
                try:
                    if operation['type'] == 'transfer':
                        result = self._execute_transfer_operation(cursor, operation['params'], transaction_state)
                    elif operation['type'] == 'balance_update':
                        result = self._execute_balance_update_operation(cursor, operation['params'], transaction_state)
                    else:
                        raise ValueError(f"Unsupported operation type: {operation['type']}")
                    
                    results.append({
                        'operation_index': i,
                        'type': operation['type'],
                        'status': 'success',
                        'result': result
                    })
                    
                    # تسجيل العملية في حالة المعاملة
                    transaction_state['operations'].append({
                        'index': i,
                        'type': operation['type'],
                        'params': operation['params'],
                        'result': result,
                        'timestamp': datetime.now().isoformat()
                    })
                    
                except Exception as e:
                    logger.error(f"Operation {i} failed in transaction {transaction_id}: {e}")
                    raise Exception(f"Operation {i} ({operation['type']}) failed: {e}")
        
        return {
            'transaction_id': transaction_id,
            'total_operations': len(operations),
            'successful_operations': len(results),
            'results': results,
            'status': 'completed'
        }
    
    def _execute_transfer_operation(self, cursor, params: Dict, transaction_state: Dict) -> Dict:
        """تنفيذ عملية تحويل داخل معاملة معقدة"""
        from_user_id = params['from_user_id']
        to_user_id = params['to_user_id']
        amount = params['amount']
        description = params.get('description', '')
        
        # قراءة الأرصدة الحالية
        cursor.execute('SELECT balance FROM users WHERE id = ?', (from_user_id,))
        sender_balance = float(cursor.fetchone()['balance'])
        
        cursor.execute('SELECT balance FROM users WHERE id = ?', (to_user_id,))
        receiver_balance = float(cursor.fetchone()['balance'])
        
        # التحقق من كفاية الرصيد
        if sender_balance < amount:
            raise ValueError(f"Insufficient balance: {sender_balance} < {amount}")
        
        # تحديث الأرصدة
        new_sender_balance = sender_balance - amount
        new_receiver_balance = receiver_balance + amount
        
        cursor.execute('UPDATE users SET balance = ?, last_activity = ? WHERE id = ?',
                      (new_sender_balance, datetime.now(), from_user_id))
        
        cursor.execute('UPDATE users SET balance = ?, last_activity = ? WHERE id = ?',
                      (new_receiver_balance, datetime.now(), to_user_id))
        
        return {
            'from_user_id': from_user_id,
            'to_user_id': to_user_id,
            'amount': amount,
            'sender_old_balance': sender_balance,
            'sender_new_balance': new_sender_balance,
            'receiver_old_balance': receiver_balance,
            'receiver_new_balance': new_receiver_balance
        }
    
    def _execute_balance_update_operation(self, cursor, params: Dict, transaction_state: Dict) -> Dict:
        """تنفيذ عملية تحديث رصيد داخل معاملة معقدة"""
        user_id = params['user_id']
        amount_change = params['amount_change']
        operation_type = params.get('operation_type', 'balance_update')
        
        # قراءة الرصيد الحالي
        cursor.execute('SELECT balance FROM users WHERE id = ?', (user_id,))
        current_balance = float(cursor.fetchone()['balance'])
        
        new_balance = current_balance + amount_change
        
        # التحقق من صحة الرصيد الجديد
        if new_balance < 0:
            raise ValueError(f"Balance would become negative: {new_balance}")
        
        # تحديث الرصيد
        cursor.execute('UPDATE users SET balance = ?, last_activity = ? WHERE id = ?',
                      (new_balance, datetime.now(), user_id))
        
        return {
            'user_id': user_id,
            'old_balance': current_balance,
            'new_balance': new_balance,
            'amount_change': amount_change,
            'operation_type': operation_type
        }
    
    def get_active_transactions(self) -> Dict[str, Dict]:
        """الحصول على المعاملات النشطة حالياً"""
        return self._active_transactions.copy()
    
    def verify_user_balance_integrity(self, user_id: int) -> Dict[str, Any]:
        """التحقق من سلامة رصيد المستخدم"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            # الرصيد الحالي
            cursor.execute('SELECT balance FROM users WHERE id = ?', (user_id,))
            current_balance = cursor.fetchone()
            if not current_balance:
                return {'error': 'User not found'}
            
            current_balance = float(current_balance['balance'])
            
            # حساب الرصيد من المعاملات
            cursor.execute('''
                SELECT COALESCE(SUM(amount), 0) as calculated_balance
                FROM wallet_transactions 
                WHERE user_id = ?
            ''', (user_id,))
            
            calculated_balance = float(cursor.fetchone()['calculated_balance'])
            
            # مقارنة الأرصدة
            difference = abs(current_balance - calculated_balance)
            is_consistent = difference < 0.01  # Allow small floating point differences
            
            return {
                'user_id': user_id,
                'current_balance': current_balance,
                'calculated_balance': calculated_balance,
                'difference': difference,
                'is_consistent': is_consistent
            }
            
        finally:
            conn.close()

# إنشاء مثيل عام للاستخدام
transaction_manager = TransactionManager()