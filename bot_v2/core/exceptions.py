"""
Custom exceptions for Yemen Net Bot v2
"""

class BotError(Exception):
    """Base exception for bot errors"""
    pass

class DatabaseError(BotError):
    """Database related errors"""
    pass

class ValidationError(BotError):
    """Data validation errors"""
    pass

class PermissionError(BotError):
    """Permission related errors"""
    pass

class RateLimitError(BotError):
    """Rate limiting errors"""
    pass

class NetworkError(BotError):
    """Network related errors"""
    pass

class PaymentError(BotError):
    """Payment related errors"""
    pass

class ConfigurationError(BotError):
    """Configuration related errors"""
    pass