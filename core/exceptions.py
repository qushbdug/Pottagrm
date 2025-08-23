"""
Custom exceptions for Yemen Net Bot
Provides specific exception types for better error handling
"""

from typing import Optional, Dict, Any


class BotError(Exception):
    """Base exception for all bot-related errors"""
    
    def __init__(self, message: str, error_code: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}
    
    def __str__(self):
        if self.error_code:
            return f"[{self.error_code}] {self.message}"
        return self.message


class DatabaseError(BotError):
    """Database-related errors"""
    
    def __init__(self, message: str, error_code: Optional[str] = None, details: Optional[Dict[str, Any]] = None, query: Optional[str] = None):
        super().__init__(message, error_code, details)
        self.query = query


class NetworkError(BotError):
    """Network-related errors"""
    
    def __init__(self, message: str, error_code: Optional[str] = None, details: Optional[Dict[str, Any]] = None, url: Optional[str] = None):
        super().__init__(message, error_code, details)
        self.url = url


class ValidationError(BotError):
    """Input validation errors"""
    
    def __init__(self, message: str, field: Optional[str] = None, value: Optional[Any] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "VALIDATION_ERROR", details)
        self.field = field
        self.value = value


class AuthenticationError(BotError):
    """Authentication and authorization errors"""
    
    def __init__(self, message: str, user_id: Optional[int] = None, required_role: Optional[str] = None):
        super().__init__(message, "AUTH_ERROR")
        self.user_id = user_id
        self.required_role = required_role


class PermissionError(BotError):
    """Permission-related errors"""
    
    def __init__(self, message: str, user_id: Optional[int] = None, required_permission: Optional[str] = None):
        super().__init__(message, "PERMISSION_ERROR")
        self.user_id = user_id
        self.required_permission = required_permission


class RateLimitError(BotError):
    """Rate limiting errors"""
    
    def __init__(self, message: str, user_id: Optional[int] = None, retry_after: Optional[int] = None):
        super().__init__(message, "RATE_LIMIT_ERROR")
        self.user_id = user_id
        self.retry_after = retry_after


class BusinessLogicError(BotError):
    """Business logic violations"""
    
    def __init__(self, message: str, error_code: Optional[str] = None, context: Optional[Dict[str, Any]] = None):
        super().__init__(message, error_code)
        self.context = context or {}


class PaymentError(BusinessLogicError):
    """Payment processing errors"""
    
    def __init__(self, message: str, transaction_id: Optional[str] = None, amount: Optional[float] = None):
        super().__init__(message, "PAYMENT_ERROR")
        self.transaction_id = transaction_id
        self.amount = amount


class InsufficientBalanceError(PaymentError):
    """Insufficient balance for transaction"""
    
    def __init__(self, message: str, current_balance: float, required_amount: float):
        super().__init__(message, "INSUFFICIENT_BALANCE")
        self.current_balance = current_balance
        self.required_amount = required_amount


class CardNotAvailableError(BusinessLogicError):
    """Card is not available for purchase"""
    
    def __init__(self, message: str, card_id: Optional[int] = None, category_id: Optional[int] = None):
        super().__init__(message, "CARD_NOT_AVAILABLE")
        self.card_id = card_id
        self.category_id = category_id


class FileProcessingError(BotError):
    """File processing errors"""
    
    def __init__(self, message: str, filename: Optional[str] = None, file_type: Optional[str] = None):
        super().__init__(message, "FILE_PROCESSING_ERROR")
        self.filename = filename
        self.file_type = file_type


class ConfigurationError(BotError):
    """Configuration-related errors"""
    
    def __init__(self, message: str, config_key: Optional[str] = None):
        super().__init__(message, "CONFIG_ERROR")
        self.config_key = config_key


class ExternalServiceError(BotError):
    """External service integration errors"""
    
    def __init__(self, message: str, service_name: Optional[str] = None, status_code: Optional[int] = None):
        super().__init__(message, "EXTERNAL_SERVICE_ERROR")
        self.service_name = service_name
        self.status_code = status_code


class CacheError(BotError):
    """Cache-related errors"""
    
    def __init__(self, message: str, cache_key: Optional[str] = None):
        super().__init__(message, "CACHE_ERROR")
        self.cache_key = cache_key


class CriticalError(BotError):
    """Critical errors that require immediate attention"""
    
    def __init__(self, message: str, component: Optional[str] = None, severity: str = "HIGH"):
        super().__init__(message, "CRITICAL_ERROR")
        self.component = component
        self.severity = severity


# Exception mapping for common SQLite errors
SQLITE_ERROR_MAP = {
    "UNIQUE constraint failed": ValidationError,
    "NOT NULL constraint failed": ValidationError,
    "FOREIGN KEY constraint failed": ValidationError,
    "database is locked": DatabaseError,
    "no such table": DatabaseError,
    "no such column": DatabaseError,
    "syntax error": DatabaseError,
}


def map_sqlite_error(error_message: str, original_exception: Exception = None) -> BotError:
    """Map SQLite errors to appropriate custom exceptions"""
    error_message_lower = error_message.lower()
    
    for sqlite_error, exception_class in SQLITE_ERROR_MAP.items():
        if sqlite_error.lower() in error_message_lower:
            if exception_class == ValidationError:
                # Extract field name from constraint error if possible
                field = None
                if "." in error_message:
                    parts = error_message.split(".")
                    if len(parts) > 1:
                        field = parts[-1].strip()
                return exception_class(
                    message=error_message,
                    field=field,
                    details={"original_error": str(original_exception)} if original_exception else None
                )
            else:
                return exception_class(
                    message=error_message,
                    details={"original_error": str(original_exception)} if original_exception else None
                )
    
    # Default to DatabaseError if no specific mapping found
    return DatabaseError(
        message=error_message,
        details={"original_error": str(original_exception)} if original_exception else None
    )


def handle_exception(func):
    """Decorator to handle and convert exceptions to custom ones"""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except BotError:
            # Re-raise custom exceptions as-is
            raise
        except Exception as e:
            # Convert generic exceptions to custom ones
            error_message = str(e)
            
            # Check if it's a database error
            if any(db_error in error_message.lower() for db_error in ["sqlite", "database", "sql"]):
                raise map_sqlite_error(error_message, e)
            
            # Check if it's a network error
            if any(net_error in error_message.lower() for net_error in ["network", "connection", "timeout", "http"]):
                raise NetworkError(message=error_message, details={"original_error": str(e)})
            
            # Default to generic BotError
            raise BotError(message=error_message, details={"original_error": str(e)})
    
    return wrapper


async def handle_async_exception(func):
    """Async version of exception handler decorator"""
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except BotError:
            # Re-raise custom exceptions as-is
            raise
        except Exception as e:
            # Convert generic exceptions to custom ones
            error_message = str(e)
            
            # Check if it's a database error
            if any(db_error in error_message.lower() for db_error in ["sqlite", "database", "sql"]):
                raise map_sqlite_error(error_message, e)
            
            # Check if it's a network error
            if any(net_error in error_message.lower() for net_error in ["network", "connection", "timeout", "http"]):
                raise NetworkError(message=error_message, details={"original_error": str(e)})
            
            # Default to generic BotError
            raise BotError(message=error_message, details={"original_error": str(e)})
    
    return wrapper