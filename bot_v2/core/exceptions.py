"""
Custom exceptions for Yemen Net Bot v2
Replaces generic Exception handling with specific exceptions
"""

class BotException(Exception):
    """Base exception for bot operations"""
    def __init__(self, message: str, error_code: str = None, details: dict = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}
    
    def __str__(self):
        return f"[{self.error_code}] {self.message}" if self.error_code else self.message

class DatabaseException(BotException):
    """Database operation exceptions"""
    def __init__(self, message: str, operation: str = None, table: str = None, details: dict = None):
        super().__init__(message, "DB_ERROR", details)
        self.operation = operation
        self.table = table

class ValidationException(BotException):
    """Data validation exceptions"""
    def __init__(self, message: str, field: str = None, value: any = None, details: dict = None):
        super().__init__(message, "VALIDATION_ERROR", details)
        self.field = field
        self.value = value

class AuthenticationException(BotException):
    """Authentication and authorization exceptions"""
    def __init__(self, message: str, user_id: int = None, required_role: str = None, details: dict = None):
        super().__init__(message, "AUTH_ERROR", details)
        self.user_id = user_id
        self.required_role = required_role

class PaymentException(BotException):
    """Payment and transaction exceptions"""
    def __init__(self, message: str, transaction_id: str = None, amount: float = None, details: dict = None):
        super().__init__(message, "PAYMENT_ERROR", details)
        self.transaction_id = transaction_id
        self.amount = amount

class NetworkException(BotException):
    """Network and API exceptions"""
    def __init__(self, message: str, endpoint: str = None, status_code: int = None, details: dict = None):
        super().__init__(message, "NETWORK_ERROR", details)
        self.endpoint = endpoint
        self.status_code = status_code

class RateLimitException(BotException):
    """Rate limiting exceptions"""
    def __init__(self, message: str, user_id: int = None, limit_type: str = None, retry_after: int = None, details: dict = None):
        super().__init__(message, "RATE_LIMIT_ERROR", details)
        self.user_id = user_id
        self.limit_type = limit_type
        self.retry_after = retry_after

class ConfigurationException(BotException):
    """Configuration and setup exceptions"""
    def __init__(self, message: str, config_key: str = None, config_value: any = None, details: dict = None):
        super().__init__(message, "CONFIG_ERROR", details)
        self.config_key = config_key
        self.config_value = config_value