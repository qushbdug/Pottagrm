"""
Custom exceptions for Yemen Net Bot
"""

class BotException(Exception):
    """Base exception for bot errors"""
    pass

class DatabaseException(BotException):
    """Database-related errors"""
    pass

class ValidationException(BotException):
    """Data validation errors"""
    pass

class AuthenticationException(BotException):
    """Authentication and authorization errors"""
    pass

class PaymentException(BotException):
    """Payment processing errors"""
    pass

class NetworkException(BotException):
    """Network and API errors"""
    pass

class ConfigurationException(BotException):
    """Configuration errors"""
    pass

class RateLimitException(BotException):
    """Rate limiting errors"""
    pass