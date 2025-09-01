#!/usr/bin/env python3
"""
Timeout Manager - مدير المهلة الزمنية
يمنع تعليق العمليات عبر تطبيق timeout على العمليات الحساسة
"""

import asyncio
import logging
import sqlite3
from contextlib import asynccontextmanager
from typing import Any, Callable, Optional
from datetime import datetime
from bot_modules.database import get_db_connection

logger = logging.getLogger(__name__)

class TimeoutManager:
    """مدير المهلة الزمنية للعمليات"""
    
    def __init__(self):
        self.default_timeout = 15.0  # 15 seconds default
        self.db_timeout = 10.0       # 10 seconds for database operations
        self.api_timeout = 5.0       # 5 seconds for API calls
    
    async def execute_with_timeout(self, operation: Callable, timeout: float = None, 
                                 operation_name: str = "العملية") -> Any:
        """تنفيذ عملية مع timeout"""
        if timeout is None:
            timeout = self.default_timeout
        
        try:
            logger.debug(f"Starting {operation_name} with timeout {timeout}s")
            result = await asyncio.wait_for(operation(), timeout=timeout)
            logger.debug(f"Completed {operation_name} successfully")
            return result
            
        except asyncio.TimeoutError:
            logger.error(f"Timeout in {operation_name} after {timeout}s")
            raise TimeoutError(f"انتهت مهلة {operation_name} ({timeout} ثانية)")
        except Exception as e:
            logger.error(f"Error in {operation_name}: {e}")
            raise
    
    @asynccontextmanager
    async def safe_db_transaction(self, timeout: float = None):
        """معاملة قاعدة بيانات آمنة مع timeout"""
        if timeout is None:
            timeout = self.db_timeout
        
        conn = None
        try:
            # إنشاء اتصال مباشر (SQLite لا يدعم async بشكل طبيعي)
            conn = get_db_connection()
            
            cursor = conn.cursor()
            cursor.execute('PRAGMA busy_timeout = 5000')  # 5 seconds busy timeout
            cursor.execute('BEGIN IMMEDIATE')
            
            yield conn, cursor
            
            # تأكيد المعاملة
            conn.commit()
            logger.debug("Database transaction committed successfully")
            
        except asyncio.TimeoutError:
            if conn:
                try:
                    conn.rollback()
                except:
                    pass
            logger.error(f"Database transaction timeout after {timeout}s")
            raise TimeoutError(f"انتهت مهلة معاملة قاعدة البيانات ({timeout} ثانية)")
            
        except Exception as e:
            if conn:
                try:
                    conn.rollback()
                except:
                    pass
            logger.error(f"Database transaction failed: {e}")
            raise
            
        finally:
            if conn:
                try:
                    conn.close()
                except:
                    pass
    
    def safe_purchase_transaction(self, user_id: int, supplier_id: int, 
                                   card_id: int, card_price: float, 
                                   transaction_id: str, network_name: str):
        """معاملة شراء آمنة مع timeout"""
        
        def purchase_operation():
            conn = get_db_connection()
            cursor = conn.cursor()
            
            try:
                cursor.execute('PRAGMA busy_timeout = 10000')
                cursor.execute('BEGIN IMMEDIATE')
                # التحقق من الرصيد
                cursor.execute('SELECT balance FROM users WHERE id = ?', (user_id,))
                balance_result = cursor.fetchone()
                if not balance_result:
                    raise Exception("المستخدم غير موجود")
                
                current_balance = float(balance_result['balance'])
                if current_balance < card_price:
                    raise Exception(f"الرصيد غير كافي: {current_balance} < {card_price}")
                
                # التحقق من توفر البطاقة
                cursor.execute('SELECT card_code FROM network_cards WHERE id = ? AND is_sold = 0', (card_id,))
                card_result = cursor.fetchone()
                if not card_result:
                    raise Exception("البطاقة غير متاحة")
                
                card_code = card_result['card_code']
                
                # تحديث الأرصدة
                new_balance = current_balance - card_price
                
                cursor.execute('UPDATE users SET balance = ?, last_activity = ? WHERE id = ?', 
                              (new_balance, datetime.now(), user_id))
                
                cursor.execute('UPDATE users SET balance = balance + ?, last_activity = ? WHERE id = ?', 
                              (card_price, datetime.now(), supplier_id))
                
                # تحديث حالة البطاقة
                cursor.execute('UPDATE network_cards SET is_sold = 1, sold_at = ? WHERE id = ?', 
                              (datetime.now(), card_id))
                
                # تسجيل المعاملة
                cursor.execute('''
                    INSERT INTO transactions (id, from_user, to_user, amount, type, description, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (transaction_id, user_id, supplier_id, card_price, 'card_purchase', 
                      f"شراء كرت {card_price:,.0f} ريال من شبكة {network_name}", datetime.now()))
                
                conn.commit()
                
                return {
                    'card_code': card_code,
                    'new_balance': new_balance,
                    'transaction_id': transaction_id
                }
                
            except Exception as e:
                conn.rollback()
                raise e
            finally:
                conn.close()
        
        # تنفيذ العملية مباشرة (SQLite لا يحتاج async)
        return purchase_operation()

# إنشاء مثيل عام للاستخدام
timeout_manager = TimeoutManager()