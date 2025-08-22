"""
Custom exceptions for the Yemen Net Bot
"""

class BotBaseException(Exception):
    """Base exception for all bot-related errors"""
    pass

class DatabaseException(BotBaseException):
    """Database-related exceptions"""
    pass

class ConnectionPoolException(DatabaseException):
    """Database connection pool exceptions"""
    pass

class TransactionException(DatabaseException):
    """Transaction-related exceptions"""
    pass

class UserException(BotBaseException):
    """User-related exceptions"""
    pass

class UserNotFound(UserException):
    """User not found in database"""
    pass

class UserPermissionDenied(UserException):
    """User does not have required permissions"""
    pass

class InsufficientFunds(UserException):
    """User has insufficient funds for transaction"""
    pass

class PaymentException(BotBaseException):
    """Payment processing exceptions"""
    pass

class PaymentFailed(PaymentException):
    """Payment processing failed"""
    pass

class InvalidPaymentAmount(PaymentException):
    """Invalid payment amount"""
    pass

class TelegramException(BotBaseException):
    """Telegram API related exceptions"""
    pass

class MessageSendError(TelegramException):
    """Failed to send message"""
    pass

class CallbackQueryError(TelegramException):
    """Callback query processing error"""
    pass

class ValidationException(BotBaseException):
    """Data validation exceptions"""
    pass

class InvalidInput(ValidationException):
    """Invalid user input"""
    pass

class InvalidPhoneNumber(ValidationException):
    """Invalid phone number format"""
    pass

class NetworkException(BotBaseException):
    """Network service exceptions"""
    pass

class NetworkNotFound(NetworkException):
    """Network not found"""
    pass

class NetworkUnavailable(NetworkException):
    """Network temporarily unavailable"""
    pass

class CardException(BotBaseException):
    """Card-related exceptions"""
    pass

class CardNotFound(CardException):
    """Card not found"""
    pass

class CardAlreadySold(CardException):
    """Card already sold"""
    pass

class SupplierException(BotBaseException):
    """Supplier-related exceptions"""
    pass

class SupplierNotFound(SupplierException):
    """Supplier not found"""
    pass

class SupplierInactive(SupplierException):
    """Supplier is inactive"""
    pass

class RateLimitException(BotBaseException):
    """Rate limiting exceptions"""
    pass

class RateLimitExceeded(RateLimitException):
    """Rate limit exceeded"""
    pass

class CacheException(BotBaseException):
    """Cache-related exceptions"""
    pass

class CacheKeyNotFound(CacheException):
    """Cache key not found"""
    pass

class SecurityException(BotBaseException):
    """Security-related exceptions"""
    pass

class UnauthorizedAccess(SecurityException):
    """Unauthorized access attempt"""
    pass

class InvalidToken(SecurityException):
    """Invalid token provided"""
    pass

class ConfigurationException(BotBaseException):
    """Configuration-related exceptions"""
    pass

class MissingConfiguration(ConfigurationException):
    """Required configuration missing"""
    pass

class InvalidConfiguration(ConfigurationException):
    """Invalid configuration value"""
    pass

class EmergencyShutdownException(BotBaseException):
    """Critical error requiring emergency shutdown"""
    pass