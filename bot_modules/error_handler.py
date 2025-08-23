"""
مدير معالجة الأخطاء المتسق
لضمان معالجة صحيحة للأخطاء في جميع الدوال
"""

import logging
import traceback
from typing import Optional, Callable, Any
from contextlib import contextmanager
from telegram import Update
from telegram.ext import CallbackContext

logger = logging.getLogger(__name__)

class DatabaseTransactionManager:
    """مدير معاملات قاعدة البيانات مع rollback تلقائي"""
    
    def __init__(self, connection):
        self.connection = connection
        self.cursor = connection.cursor()
        self._transaction_started = False
    
    def __enter__(self):
        """بدء المعاملة"""
        self._transaction_started = True
        return self.cursor
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """إنهاء المعاملة مع rollback في حالة الخطأ"""
        if exc_type is not None:
            # حدث خطأ - rollback
            try:
                self.connection.rollback()
                logger.warning(f"تم عمل rollback للمعاملة بسبب الخطأ: {exc_val}")
            except Exception as rollback_error:
                logger.error(f"فشل في عمل rollback: {rollback_error}")
        else:
            # لا يوجد خطأ - commit
            try:
                self.connection.commit()
                logger.debug("تم commit المعاملة بنجاح")
            except Exception as commit_error:
                logger.error(f"فشل في commit المعاملة: {commit_error}")
                try:
                    self.connection.rollback()
                    logger.warning("تم عمل rollback بعد فشل commit")
                except Exception as rollback_error:
                    logger.error(f"فشل في rollback بعد commit: {rollback_error}")
        
        # إغلاق cursor
        try:
            self.cursor.close()
        except Exception as close_error:
            logger.error(f"فشل في إغلاق cursor: {close_error}")

@contextmanager
def safe_database_transaction(connection):
    """
    مدير سياق آمن للمعاملات
    
    Usage:
        with safe_database_transaction(conn) as cursor:
            cursor.execute("INSERT INTO ...")
            cursor.execute("UPDATE ...")
    """
    manager = DatabaseTransactionManager(connection)
    try:
        yield manager.cursor
    except Exception as e:
        # سيتم التعامل مع الخطأ تلقائياً في __exit__
        raise

class ErrorHandler:
    """معالج الأخطاء المركزي"""
    
    @staticmethod
    def handle_database_error(error: Exception, operation: str, user_id: Optional[int] = None) -> str:
        """معالجة أخطاء قاعدة البيانات"""
        error_msg = f"خطأ في قاعدة البيانات أثناء {operation}: {str(error)}"
        logger.error(error_msg, exc_info=True)
        
        # تسجيل الخطأ للمستخدم
        if user_id:
            try:
                from .database import log_error
                log_error(user_id, 'database_error', error_msg, {
                    'operation': operation,
                    'error_type': type(error).__name__,
                    'error_details': str(error)
                })
            except Exception as log_error:
                logger.error(f"فشل في تسجيل الخطأ: {log_error}")
        
        # رسائل خطأ مناسبة للمستخدم
        if "UNIQUE constraint failed" in str(error):
            return "❌ البيانات موجودة مسبقاً"
        elif "NOT NULL constraint failed" in str(error):
            return "❌ بيانات مطلوبة مفقودة"
        elif "FOREIGN KEY constraint failed" in str(error):
            return "❌ مرجع غير صحيح"
        elif "database is locked" in str(error):
            return "⚠️ النظام مشغول حالياً، يرجى المحاولة لاحقاً"
        else:
            return "❌ حدث خطأ في قاعدة البيانات"
    
    @staticmethod
    def handle_telegram_error(error: Exception, operation: str, update: Optional[Update] = None) -> str:
        """معالجة أخطاء تيليجرام"""
        error_msg = f"خطأ في تيليجرام أثناء {operation}: {str(error)}"
        logger.error(error_msg, exc_info=True)
        
        # تسجيل معلومات إضافية
        if update:
            try:
                user_id = update.effective_user.id if update.effective_user else None
                chat_id = update.effective_chat.id if update.effective_chat else None
                logger.error(f"تفاصيل الخطأ - User: {user_id}, Chat: {chat_id}")
            except Exception as log_error:
                logger.error(f"فشل في تسجيل تفاصيل الخطأ: {log_error}")
        
        # رسائل خطأ مناسبة
        if "message is not modified" in str(error).lower():
            return "✅ الرسالة محدثة بالفعل"
        elif "message to edit not found" in str(error).lower():
            return "⚠️ الرسالة غير موجودة للتعديل"
        elif "bot was blocked by the user" in str(error).lower():
            return "❌ تم حظر البوت من قبل المستخدم"
        else:
            return "❌ حدث خطأ في تيليجرام"
    
    @staticmethod
    def handle_general_error(error: Exception, operation: str, context: Optional[Any] = None) -> str:
        """معالجة الأخطاء العامة"""
        error_msg = f"خطأ عام أثناء {operation}: {str(error)}"
        logger.error(error_msg, exc_info=True)
        
        # تسجيل السياق إذا كان متاحاً
        if context:
            try:
                logger.error(f"سياق الخطأ: {context}")
            except Exception as log_error:
                logger.error(f"فشل في تسجيل سياق الخطأ: {log_error}")
        
        return "❌ حدث خطأ غير متوقع"

def safe_execute(error_message: str = "حدث خطأ", 
                fallback_response: str = "❌ حدث خطأ في تنفيذ العملية"):
    """
    مزخرف لتنفيذ آمن للدوال
    
    Usage:
        @safe_execute("شراء الكرت", "❌ فشل في شراء الكرت")
        def buy_card(update, context):
            # كود الشراء
    """
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(f"{error_message}: {e}", exc_info=True)
                return fallback_response
        return wrapper
    return decorator

def safe_async_execute(error_message: str = "حدث خطأ", 
                      fallback_response: str = "❌ حدث خطأ في تنفيذ العملية"):
    """
    مزخرف لتنفيذ آمن للدوال غير المتزامنة
    
    Usage:
        @safe_async_execute("شراء الكرت", "❌ فشل في شراء الكرت")
        async def buy_card(update, context):
            # كود الشراء
    """
    def decorator(func: Callable) -> Callable:
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                logger.error(f"{error_message}: {e}", exc_info=True)
                return fallback_response
        return wrapper
    return decorator

# دوال مساعدة سريعة
def log_and_handle_error(error: Exception, operation: str, user_id: Optional[int] = None) -> str:
    """تسجيل ومعالجة سريعة للخطأ"""
    return ErrorHandler.handle_database_error(error, operation, user_id)

def safe_db_operation(connection, operation_name: str):
    """مدير سياق آمن لعمليات قاعدة البيانات"""
    return safe_database_transaction(connection)