"""
Custom exception classes for Yemen Net Bot v2
Provides specific exception handling for different error types
"""

import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class BotError(Exception):
    """Base exception for all bot errors"""
    
    def __init__(self, message: str, error_code: Optional[str] = None, 
                 context: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.context = context or {}
        
        # Log the error
        logger.error(f"BotError: {message} (Code: {error_code})", 
                    extra={'context': self.context})
    
    def __str__(self):
        return f"{self.__class__.__name__}: {self.message}"


class DatabaseError(BotError):
    """Database operation errors"""
    
    def __init__(self, message: str, sql: Optional[str] = None, 
                 params: Optional[tuple] = None, original_error: Optional[Exception] = None):
        super().__init__(message, "DB_ERROR", {
            'sql': sql,
            'params': params,
            'original_error': str(original_error) if original_error else None
        })
        self.sql = sql
        self.params = params
        self.original_error = original_error


class ValidationError(BotError):
    """Data validation errors"""
    
    def __init__(self, message: str, field: Optional[str] = None, 
                 value: Optional[Any] = None, validation_rules: Optional[Dict] = None):
        super().__init__(message, "VALIDATION_ERROR", {
            'field': field,
            'value': value,
            'validation_rules': validation_rules
        })
        self.field = field
        self.value = value
        self.validation_rules = validation_rules


class PermissionError(BotError):
    """Permission and authorization errors"""
    
    def __init__(self, message: str, user_id: Optional[int] = None, 
                 required_role: Optional[str] = None, user_role: Optional[str] = None):
        super().__init__(message, "PERMISSION_ERROR", {
            'user_id': user_id,
            'required_role': required_role,
            'user_role': user_role
        })
        self.user_id = user_id
        self.required_role = required_role
        self.user_role = user_role


class RateLimitError(BotError):
    """Rate limiting errors"""
    
    def __init__(self, message: str, user_id: Optional[int] = None, 
                 limit_type: Optional[str] = None, retry_after: Optional[int] = None):
        super().__init__(message, "RATE_LIMIT_ERROR", {
            'user_id': user_id,
            'limit_type': limit_type,
            'retry_after': retry_after
        })
        self.user_id = user_id
        self.limit_type = limit_type
        self.retry_after = retry_after


class NetworkError(BotError):
    """Network and API errors"""
    
    def __init__(self, message: str, endpoint: Optional[str] = None, 
                 status_code: Optional[int] = None, response: Optional[str] = None):
        super().__init__(message, "NETWORK_ERROR", {
            'endpoint': endpoint,
            'status_code': status_code,
            'response': response
        })
        self.endpoint = endpoint
        self.status_code = status_code
        self.response = response


class PaymentError(BotError):
    """Payment processing errors"""
    
    def __init__(self, message: str, transaction_id: Optional[str] = None, 
                 amount: Optional[float] = None, payment_method: Optional[str] = None):
        super().__init__(message, "PAYMENT_ERROR", {
            'transaction_id': transaction_id,
            'amount': amount,
            'payment_method': payment_method
        })
        self.transaction_id = transaction_id
        self.amount = amount
        self.payment_method = payment_method


class ConfigurationError(BotError):
    """Configuration and setup errors"""
    
    def __init__(self, message: str, config_key: Optional[str] = None, 
                 config_value: Optional[Any] = None, config_file: Optional[str] = None):
        super().__init__(message, "CONFIG_ERROR", {
            'config_key': config_key,
            'config_value': config_value,
            'config_file': config_file
        })
        self.config_key = config_key
        self.config_value = config_value
        self.config_file = config_file


class ConversationError(BotError):
    """Conversation and state management errors"""
    
    def __init__(self, message: str, user_id: Optional[int] = None, 
                 current_state: Optional[str] = None, expected_state: Optional[str] = None):
        super().__init__(message, "CONVERSATION_ERROR", {
            'user_id': user_id,
            'current_state': current_state,
            'expected_state': expected_state
        })
        self.user_id = user_id
        self.current_state = current_state
        self.expected_state = expected_state


def handle_exception(func):
    """Decorator to handle exceptions and convert them to custom exceptions"""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            # Convert common exceptions to custom ones
            if isinstance(e, BotError):
                raise
            
            # Handle specific exception types
            if "database" in str(e).lower() or "sqlite" in str(e).lower():
                raise DatabaseError(f"Database operation failed: {str(e)}", original_error=e)
            elif "permission" in str(e).lower() or "unauthorized" in str(e).lower():
                raise PermissionError(f"Permission denied: {str(e)}")
            elif "validation" in str(e).lower() or "invalid" in str(e).lower():
                raise ValidationError(f"Validation failed: {str(e)}")
            elif "network" in str(e).lower() or "connection" in str(e).lower():
                raise NetworkError(f"Network error: {str(e)}")
            else:
                # Convert to generic bot error
                raise BotError(f"Unexpected error: {str(e)}", original_error=e)
    
    return wrapper


def safe_execute(func, *args, **kwargs):
    """Safely execute a function and return result or error"""
    try:
        return {'success': True, 'result': func(*args, **kwargs)}
    except BotError as e:
        return {'success': False, 'error': e, 'error_code': e.error_code}
    except Exception as e:
        logger.error(f"Unexpected error in safe_execute: {e}")
        return {'success': False, 'error': BotError(f"Unexpected error: {str(e)}")}


def log_and_raise(error_class, message: str, **kwargs):
    """Log an error and raise a custom exception"""
    logger.error(f"{error_class.__name__}: {message}", extra=kwargs)
    raise error_class(message, **kwargs)