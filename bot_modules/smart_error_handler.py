#!/usr/bin/env python3
"""
Smart Error Handler - معالج الأخطاء الذكي
يوفر معالجة ذكية ومتقدمة للأخطاء مع إعادة المحاولة التلقائية والتعافي
"""

import logging
import asyncio
import traceback
import sys
from typing import Dict, Any, Optional, Callable, List, Tuple
from datetime import datetime, timedelta
from enum import Enum
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext
from telegram.error import TelegramError, NetworkError, TimedOut, BadRequest, Forbidden

logger = logging.getLogger(__name__)

class ErrorSeverity(Enum):
    """مستويات خطورة الأخطاء"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ErrorCategory(Enum):
    """فئات الأخطاء"""
    DATABASE = "database"
    NETWORK = "network"
    TELEGRAM_API = "telegram_api"
    VALIDATION = "validation"
    PERMISSION = "permission"
    BUSINESS_LOGIC = "business_logic"
    SYSTEM = "system"
    USER_INPUT = "user_input"

class SmartErrorHandler:
    """معالج الأخطاء الذكي"""
    
    def __init__(self):
        self.error_stats = {}
        self.retry_strategies = {
            ErrorCategory.NETWORK: {'max_retries': 3, 'delay': 2.0},
            ErrorCategory.TELEGRAM_API: {'max_retries': 2, 'delay': 1.0},
            ErrorCategory.DATABASE: {'max_retries': 2, 'delay': 0.5},
        }
        self.error_patterns = self._initialize_error_patterns()
        self.recovery_actions = self._initialize_recovery_actions()
    
    def _initialize_error_patterns(self) -> Dict[str, Dict[str, Any]]:
        """تهيئة أنماط الأخطاء المعروفة"""
        return {
            # أخطاء قاعدة البيانات
            'database is locked': {
                'category': ErrorCategory.DATABASE,
                'severity': ErrorSeverity.MEDIUM,
                'message': 'قاعدة البيانات مشغولة حالياً',
                'solution': 'سيتم إعادة المحاولة تلقائياً خلال ثوان',
                'retry': True
            },
            'no such table': {
                'category': ErrorCategory.DATABASE,
                'severity': ErrorSeverity.CRITICAL,
                'message': 'خطأ في بنية قاعدة البيانات',
                'solution': 'يرجى التواصل مع الدعم الفني',
                'retry': False
            },
            
            # أخطاء الشبكة
            'connection timeout': {
                'category': ErrorCategory.NETWORK,
                'severity': ErrorSeverity.MEDIUM,
                'message': 'انتهت مهلة الاتصال',
                'solution': 'تحقق من اتصال الإنترنت وحاول مرة أخرى',
                'retry': True
            },
            'connection refused': {
                'category': ErrorCategory.NETWORK,
                'severity': ErrorSeverity.HIGH,
                'message': 'فشل في الاتصال بالخادم',
                'solution': 'الخادم غير متاح حالياً، حاول لاحقاً',
                'retry': True
            },
            
            # أخطاء تيليجرام
            'message is too long': {
                'category': ErrorCategory.TELEGRAM_API,
                'severity': ErrorSeverity.LOW,
                'message': 'الرسالة طويلة جداً',
                'solution': 'سيتم تقسيم المحتوى إلى رسائل متعددة',
                'retry': False
            },
            'bot was blocked': {
                'category': ErrorCategory.TELEGRAM_API,
                'severity': ErrorSeverity.LOW,
                'message': 'المستخدم حظر البوت',
                'solution': 'لا يمكن إرسال رسائل لهذا المستخدم',
                'retry': False
            },
            
            # أخطاء التحقق
            'insufficient balance': {
                'category': ErrorCategory.VALIDATION,
                'severity': ErrorSeverity.LOW,
                'message': 'الرصيد غير كافي',
                'solution': 'يرجى شحن رصيدك أولاً',
                'retry': False
            },
            'user not found': {
                'category': ErrorCategory.VALIDATION,
                'severity': ErrorSeverity.MEDIUM,
                'message': 'المستخدم غير موجود',
                'solution': 'تأكد من تسجيلك في النظام',
                'retry': False
            },
            
            # أخطاء الصلاحيات
            'permission denied': {
                'category': ErrorCategory.PERMISSION,
                'severity': ErrorSeverity.MEDIUM,
                'message': 'ليس لديك صلاحية لهذه العملية',
                'solution': 'تواصل مع الإدارة للحصول على الصلاحيات',
                'retry': False
            }
        }
    
    def _initialize_recovery_actions(self) -> Dict[ErrorCategory, Callable]:
        """تهيئة إجراءات التعافي"""
        return {
            ErrorCategory.DATABASE: self._recover_database_error,
            ErrorCategory.NETWORK: self._recover_network_error,
            ErrorCategory.TELEGRAM_API: self._recover_telegram_error,
        }
    
    async def handle_error(self, error: Exception, update: Update = None, 
                         context: CallbackContext = None, 
                         operation_name: str = "العملية") -> Tuple[bool, Optional[str]]:
        """معالجة ذكية للأخطاء"""
        error_info = self._analyze_error(error)
        
        # تسجيل الخطأ
        self._log_error(error, error_info, update, operation_name)
        
        # تحديث إحصائيات الأخطاء
        self._update_error_stats(error_info)
        
        # محاولة التعافي التلقائي
        recovery_success = await self._attempt_recovery(error, error_info, update, context)
        
        if recovery_success:
            return True, None
        
        # إنشاء رسالة خطأ مناسبة للمستخدم
        user_message = self._create_user_error_message(error_info, operation_name)
        
        # إرسال رسالة الخطأ للمستخدم إذا أمكن
        if update and context:
            await self._send_error_message_to_user(update, context, user_message, error_info)
        
        return False, user_message
    
    def _analyze_error(self, error: Exception) -> Dict[str, Any]:
        """تحليل الخطأ وتصنيفه"""
        error_str = str(error).lower()
        error_type = type(error).__name__
        
        # البحث عن نمط مطابق
        for pattern, info in self.error_patterns.items():
            if pattern in error_str:
                return {
                    'pattern': pattern,
                    'category': info['category'],
                    'severity': info['severity'],
                    'message': info['message'],
                    'solution': info['solution'],
                    'retry': info['retry'],
                    'original_error': str(error),
                    'error_type': error_type
                }
        
        # تصنيف تلقائي للأخطاء غير المعروفة
        if isinstance(error, (NetworkError, TimedOut)):
            category = ErrorCategory.NETWORK
            severity = ErrorSeverity.MEDIUM
        elif isinstance(error, (BadRequest, Forbidden)):
            category = ErrorCategory.TELEGRAM_API
            severity = ErrorSeverity.LOW
        elif isinstance(error, ValueError):
            category = ErrorCategory.VALIDATION
            severity = ErrorSeverity.LOW
        elif isinstance(error, PermissionError):
            category = ErrorCategory.PERMISSION
            severity = ErrorSeverity.MEDIUM
        else:
            category = ErrorCategory.SYSTEM
            severity = ErrorSeverity.HIGH
        
        return {
            'pattern': 'unknown',
            'category': category,
            'severity': severity,
            'message': f'خطأ غير متوقع: {error_type}',
            'solution': 'يرجى إعادة المحاولة أو التواصل مع الدعم الفني',
            'retry': category in [ErrorCategory.NETWORK, ErrorCategory.TELEGRAM_API],
            'original_error': str(error),
            'error_type': error_type
        }
    
    def _log_error(self, error: Exception, error_info: Dict[str, Any], 
                  update: Update = None, operation_name: str = "العملية"):
        """تسجيل تفصيلي للخطأ"""
        user_id = update.effective_user.id if update and update.effective_user else "unknown"
        
        log_message = f"""
Smart Error Handler - {operation_name}:
- User ID: {user_id}
- Error Type: {error_info['error_type']}
- Category: {error_info['category'].value}
- Severity: {error_info['severity'].value}
- Pattern: {error_info['pattern']}
- Original Error: {error_info['original_error']}
- Traceback: {traceback.format_exc()}
"""
        
        if error_info['severity'] == ErrorSeverity.CRITICAL:
            logger.critical(log_message)
        elif error_info['severity'] == ErrorSeverity.HIGH:
            logger.error(log_message)
        elif error_info['severity'] == ErrorSeverity.MEDIUM:
            logger.warning(log_message)
        else:
            logger.info(log_message)
    
    def _update_error_stats(self, error_info: Dict[str, Any]):
        """تحديث إحصائيات الأخطاء"""
        pattern = error_info['pattern']
        category = error_info['category'].value
        
        if pattern not in self.error_stats:
            self.error_stats[pattern] = {
                'count': 0,
                'category': category,
                'severity': error_info['severity'].value,
                'first_occurrence': datetime.now(),
                'last_occurrence': datetime.now()
            }
        
        self.error_stats[pattern]['count'] += 1
        self.error_stats[pattern]['last_occurrence'] = datetime.now()
    
    async def _attempt_recovery(self, error: Exception, error_info: Dict[str, Any],
                              update: Update = None, context: CallbackContext = None) -> bool:
        """محاولة التعافي التلقائي من الخطأ"""
        category = error_info['category']
        
        if not error_info['retry']:
            return False
        
        if category in self.recovery_actions:
            try:
                return await self.recovery_actions[category](error, error_info, update, context)
            except Exception as recovery_error:
                logger.error(f"Recovery attempt failed: {recovery_error}")
                return False
        
        return False
    
    async def _recover_database_error(self, error: Exception, error_info: Dict[str, Any],
                                    update: Update = None, context: CallbackContext = None) -> bool:
        """التعافي من أخطاء قاعدة البيانات"""
        if 'database is locked' in error_info['original_error'].lower():
            # انتظار قصير وإعادة المحاولة
            await asyncio.sleep(0.5)
            return True  # سيتم إعادة المحاولة
        
        return False
    
    async def _recover_network_error(self, error: Exception, error_info: Dict[str, Any],
                                   update: Update = None, context: CallbackContext = None) -> bool:
        """التعافي من أخطاء الشبكة"""
        strategy = self.retry_strategies.get(ErrorCategory.NETWORK, {})
        delay = strategy.get('delay', 1.0)
        
        await asyncio.sleep(delay)
        return True  # سيتم إعادة المحاولة
    
    async def _recover_telegram_error(self, error: Exception, error_info: Dict[str, Any],
                                    update: Update = None, context: CallbackContext = None) -> bool:
        """التعافي من أخطاء تيليجرام API"""
        if isinstance(error, TimedOut):
            await asyncio.sleep(1.0)
            return True
        
        return False
    
    def _create_user_error_message(self, error_info: Dict[str, Any], operation_name: str) -> str:
        """إنشاء رسالة خطأ مناسبة للمستخدم"""
        severity_emoji = {
            ErrorSeverity.LOW: "⚠️",
            ErrorSeverity.MEDIUM: "❌",
            ErrorSeverity.HIGH: "🚨",
            ErrorSeverity.CRITICAL: "💥"
        }
        
        emoji = severity_emoji.get(error_info['severity'], "❌")
        
        message = f"{emoji} **خطأ في {operation_name}**\n\n"
        message += f"🔍 **المشكلة:** {error_info['message']}\n"
        message += f"💡 **الحل:** {error_info['solution']}\n\n"
        
        if error_info['retry']:
            message += "🔄 سيتم إعادة المحاولة تلقائياً..."
        else:
            message += "📞 إذا استمرت المشكلة، تواصل مع الدعم الفني"
        
        return message
    
    async def _send_error_message_to_user(self, update: Update, context: CallbackContext,
                                        message: str, error_info: Dict[str, Any]):
        """إرسال رسالة الخطأ للمستخدم"""
        try:
            keyboard = None
            
            # إضافة أزرار حسب نوع الخطأ
            if error_info['category'] == ErrorCategory.VALIDATION:
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔄 إعادة المحاولة", callback_data="retry_operation")],
                    [InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="main_menu")]
                ])
            elif error_info['severity'] in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]:
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("📞 الدعم الفني", callback_data="contact_support")],
                    [InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="main_menu")]
                ])
            
            if hasattr(update, 'callback_query') and update.callback_query:
                await update.callback_query.edit_message_text(
                    message, parse_mode='Markdown', reply_markup=keyboard
                )
            elif update.message:
                await update.message.reply_text(
                    message, parse_mode='Markdown', reply_markup=keyboard
                )
                
        except Exception as send_error:
            logger.error(f"Failed to send error message to user: {send_error}")
    
    async def retry_with_strategy(self, operation: Callable, error_category: ErrorCategory,
                                *args, **kwargs) -> Any:
        """إعادة تنفيذ عملية مع استراتيجية إعادة المحاولة"""
        strategy = self.retry_strategies.get(error_category, {'max_retries': 1, 'delay': 1.0})
        max_retries = strategy['max_retries']
        delay = strategy['delay']
        
        last_error = None
        
        for attempt in range(max_retries + 1):
            try:
                if attempt > 0:
                    await asyncio.sleep(delay * attempt)  # تأخير متزايد
                
                result = await operation(*args, **kwargs)
                return result
                
            except Exception as e:
                last_error = e
                if attempt < max_retries:
                    logger.warning(f"Attempt {attempt + 1} failed, retrying: {e}")
                    continue
                else:
                    logger.error(f"All {max_retries + 1} attempts failed: {e}")
                    break
        
        raise last_error
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """الحصول على إحصائيات الأخطاء"""
        total_errors = sum(stats['count'] for stats in self.error_stats.values())
        
        # الأخطاء الأكثر شيوعاً
        most_common = sorted(
            self.error_stats.items(),
            key=lambda x: x[1]['count'],
            reverse=True
        )[:5]
        
        # الأخطاء الحرجة
        critical_errors = {
            pattern: stats for pattern, stats in self.error_stats.items()
            if stats['severity'] == ErrorSeverity.CRITICAL.value
        }
        
        return {
            'total_errors': total_errors,
            'unique_patterns': len(self.error_stats),
            'most_common_errors': most_common,
            'critical_errors': critical_errors,
            'error_categories': self._get_category_stats()
        }
    
    def _get_category_stats(self) -> Dict[str, int]:
        """إحصائيات حسب فئة الخطأ"""
        category_stats = {}
        
        for stats in self.error_stats.values():
            category = stats['category']
            category_stats[category] = category_stats.get(category, 0) + stats['count']
        
        return category_stats

# إنشاء مثيل عام للاستخدام
smart_error_handler = SmartErrorHandler()

# ديكوريتر للاستخدام السهل
def handle_errors(operation_name: str = "العملية"):
    """ديكوريتر لمعالجة الأخطاء تلقائياً"""
    def decorator(func):
        async def wrapper(update: Update, context: CallbackContext, *args, **kwargs):
            try:
                return await func(update, context, *args, **kwargs)
            except Exception as e:
                success, message = await smart_error_handler.handle_error(
                    e, update, context, operation_name
                )
                if not success:
                    logger.error(f"Unhandled error in {func.__name__}: {e}")
                return None
        return wrapper
    return decorator