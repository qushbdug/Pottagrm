"""
Enhanced error handling system for Yemen Net Bot v2
"""

import logging
import traceback
import asyncio
from typing import Optional, Callable, Any, Dict
from functools import wraps
from telegram import Update
from telegram.ext import CallbackContext
from .exceptions import *
from .rate_limiter import ActionRateLimiter

logger = logging.getLogger(__name__)

class ErrorHandler:
    """Centralized error handling system"""
    
    def __init__(self):
        """Initialize error handler"""
        self.error_callbacks: Dict[type, Callable] = {}
        self.fallback_callback: Optional[Callable] = None
        self.rate_limiter = ActionRateLimiter()
        
        # Register default error handlers
        self._register_default_handlers()
    
    def _register_default_handlers(self):
        """Register default error handlers"""
        # Database errors
        self.register_handler(DatabaseError, self._handle_database_error)
        self.register_handler(sqlite3.OperationalError, self._handle_database_error)
        self.register_handler(sqlite3.IntegrityError, self._handle_database_error)
        
        # Network errors
        self.register_handler(NetworkError, self._handle_network_error)
        self.register_handler(ConnectionError, self._handle_network_error)
        self.register_handler(TimeoutError, self._handle_network_error)
        
        # Rate limiting errors
        self.register_handler(RateLimitError, self._handle_rate_limit_error)
        
        # Permission errors
        self.register_handler(PermissionError, self._handle_permission_error)
        
        # Validation errors
        self.register_handler(ValidationError, self._handle_validation_error)
        
        # Payment errors
        self.register_handler(PaymentError, self._handle_payment_error)
        
        # Configuration errors
        self.register_handler(ConfigurationError, self._handle_configuration_error)
    
    def register_handler(self, exception_type: type, handler: Callable):
        """
        Register error handler for specific exception type
        
        Args:
            exception_type: Exception class to handle
            handler: Handler function
        """
        self.error_callbacks[exception_type] = handler
    
    def set_fallback_handler(self, handler: Callable):
        """
        Set fallback error handler
        
        Args:
            handler: Fallback handler function
        """
        self.fallback_callback = handler
    
    async def handle_error(self, update: Update, context: CallbackContext, error: Exception) -> bool:
        """
        Handle error with appropriate handler
        
        Args:
            update: Telegram update object
            context: Callback context
            error: Exception that occurred
            
        Returns:
            True if error was handled, False otherwise
        """
        try:
            # Log error details
            self._log_error(update, context, error)
            
            # Find appropriate handler
            handler = self._find_handler(error)
            if handler:
                await handler(update, context, error)
                return True
            
            # Use fallback handler if available
            if self.fallback_callback:
                await self.fallback_callback(update, context, error)
                return True
            
            # Default error handling
            await self._handle_generic_error(update, context, error)
            return True
            
        except Exception as handler_error:
            logger.error(f"Error in error handler: {handler_error}")
            # Last resort - send generic error message
            try:
                await self._send_generic_error_message(update, context)
            except:
                pass
            return False
    
    def _find_handler(self, error: Exception) -> Optional[Callable]:
        """Find appropriate handler for exception"""
        # Check exact type match
        if type(error) in self.error_callbacks:
            return self.error_callbacks[type(error)]
        
        # Check base class matches
        for exception_type, handler in self.error_callbacks.items():
            if isinstance(error, exception_type):
                return handler
        
        return None
    
    def _log_error(self, update: Update, context: CallbackContext, error: Exception):
        """Log error details"""
        user_info = self._get_user_info(update)
        error_details = {
            "error_type": type(error).__name__,
            "error_message": str(error),
            "user_id": user_info.get("user_id"),
            "username": user_info.get("username"),
            "chat_id": user_info.get("chat_id"),
            "update_type": update.update_id if update else "unknown",
            "traceback": traceback.format_exc()
        }
        
        logger.error(f"Bot error: {error_details}")
        
        # Log to separate error file if needed
        if hasattr(context, 'bot_data') and context.bot_data.get('log_errors_to_file'):
            self._log_to_file(error_details)
    
    def _get_user_info(self, update: Update) -> Dict[str, Any]:
        """Extract user information from update"""
        user_info = {"user_id": None, "username": None, "chat_id": None}
        
        try:
            if update.effective_user:
                user_info["user_id"] = update.effective_user.id
                user_info["username"] = update.effective_user.username
            
            if update.effective_chat:
                user_info["chat_id"] = update.effective_chat.id
                
        except Exception as e:
            logger.error(f"Error extracting user info: {e}")
        
        return user_info
    
    def _log_to_file(self, error_details: Dict[str, Any]):
        """Log error to file"""
        try:
            with open("error_log.txt", "a", encoding="utf-8") as f:
                f.write(f"{error_details}\n{'='*50}\n")
        except Exception as e:
            logger.error(f"Failed to log error to file: {e}")
    
    async def _handle_database_error(self, update: Update, context: CallbackContext, error: Exception):
        """Handle database errors"""
        error_message = "حدث خطأ في قاعدة البيانات. يرجى المحاولة مرة أخرى لاحقاً."
        
        if "database is locked" in str(error).lower():
            error_message = "قاعدة البيانات مشغولة حالياً. يرجى المحاولة بعد قليل."
        elif "no such table" in str(error).lower():
            error_message = "خطأ في هيكل قاعدة البيانات. يرجى التواصل مع الإدارة."
        elif "foreign key constraint failed" in str(error).lower():
            error_message = "خطأ في العلاقات بين البيانات. يرجى التحقق من المدخلات."
        
        await self._send_error_message(update, context, error_message)
    
    async def _handle_network_error(self, update: Update, context: CallbackContext, error: Exception):
        """Handle network errors"""
        error_message = "حدث خطأ في الاتصال. يرجى التحقق من اتصال الإنترنت والمحاولة مرة أخرى."
        
        if isinstance(error, TimeoutError):
            error_message = "انتهت مهلة الاتصال. يرجى المحاولة مرة أخرى."
        elif isinstance(error, ConnectionError):
            error_message = "فشل الاتصال بالخادم. يرجى المحاولة لاحقاً."
        
        await self._send_error_message(update, context, error_message)
    
    async def _handle_rate_limit_error(self, update: Update, context: CallbackContext, error: Exception):
        """Handle rate limiting errors"""
        error_message = str(error) if str(error) else "تم تجاوز الحد المسموح من الطلبات. يرجى الانتظار قليلاً."
        await self._send_error_message(update, context, error_message)
    
    async def _handle_permission_error(self, update: Update, context: CallbackContext, error: Exception):
        """Handle permission errors"""
        error_message = "ليس لديك الصلاحية لتنفيذ هذا الإجراء."
        await self._send_error_message(update, context, error_message)
    
    async def _handle_validation_error(self, update: Update, context: CallbackContext, error: Exception):
        """Handle validation errors"""
        error_message = f"خطأ في المدخلات: {str(error)}"
        await self._send_error_message(update, context, error_message)
    
    async def _handle_payment_error(self, update: Update, context: CallbackContext, error: Exception):
        """Handle payment errors"""
        error_message = "حدث خطأ في معالجة الدفع. يرجى المحاولة مرة أخرى."
        await self._send_error_message(update, context, error_message)
    
    async def _handle_configuration_error(self, update: Update, context: CallbackContext, error: Exception):
        """Handle configuration errors"""
        error_message = "خطأ في إعدادات النظام. يرجى التواصل مع الإدارة."
        await self._send_error_message(update, context, error_message)
    
    async def _handle_generic_error(self, update: Update, context: CallbackContext, error: Exception):
        """Handle generic errors"""
        error_message = "حدث خطأ غير متوقع. يرجى المحاولة مرة أخرى أو التواصل مع الإدارة."
        await self._send_error_message(update, context, error_message)
    
    async def _send_error_message(self, update: Update, context: CallbackContext, message: str):
        """Send error message to user"""
        try:
            if update and update.effective_chat:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=f"❌ {message}",
                    parse_mode='HTML'
                )
        except Exception as e:
            logger.error(f"Failed to send error message: {e}")
    
    async def _send_generic_error_message(self, update: Update, context: CallbackContext):
        """Send generic error message as last resort"""
        try:
            if update and update.effective_chat:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="❌ حدث خطأ في النظام. يرجى المحاولة لاحقاً.",
                    parse_mode='HTML'
                )
        except Exception:
            pass

# Error handling decorator
def handle_errors(func: Callable) -> Callable:
    """Decorator to automatically handle errors in handlers"""
    @wraps(func)
    async def wrapper(update: Update, context: CallbackContext, *args, **kwargs):
        try:
            return await func(update, context, *args, **kwargs)
        except Exception as error:
            # Get error handler from context
            error_handler = getattr(context, 'error_handler', None)
            if error_handler:
                await error_handler.handle_error(update, context, error)
            else:
                # Log error if no handler available
                logger.error(f"Unhandled error in {func.__name__}: {error}")
                logger.error(traceback.format_exc())
            
            # Re-raise critical errors
            if isinstance(error, (KeyboardInterrupt, SystemExit)):
                raise
    
    return wrapper

# Rate limiting decorator
def rate_limit(action: str):
    """Decorator to apply rate limiting to handlers"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(update: Update, context: CallbackContext, *args, **kwargs):
            try:
                # Get user ID
                user_id = update.effective_user.id if update.effective_user else None
                if user_id:
                    # Check rate limit
                    rate_limiter = getattr(context, 'rate_limiter', None)
                    if rate_limiter:
                        await rate_limiter.check_action(action, user_id)
                
                return await func(update, context, *args, **kwargs)
                
            except RateLimitError as e:
                # Handle rate limit error
                error_handler = getattr(context, 'error_handler', None)
                if error_handler:
                    await error_handler.handle_error(update, context, e)
                else:
                    await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text=f"⚠️ {str(e)}",
                        parse_mode='HTML'
                    )
        
        return wrapper
    return decorator

# Global error handler instance
error_handler = ErrorHandler()

# Import sqlite3 for error handling
import sqlite3