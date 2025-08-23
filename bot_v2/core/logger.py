"""
Advanced logging configuration for Yemen Net Bot
"""
import logging
import logging.handlers
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from .exceptions import EmergencyShutdownException


class BotLogger:
    """Advanced logger for the bot with multiple handlers and emergency shutdown capability"""
    
    def __init__(self, name: str = "YemenNetBot", log_dir: str = "logs"):
        self.name = name
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        # Create main logger
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)
        
        # Prevent duplicate logs
        if self.logger.handlers:
            return
            
        # Create formatters
        self.detailed_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(funcName)s - %(message)s'
        )
        self.simple_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )
        
        # Setup handlers
        self._setup_console_handler()
        self._setup_file_handlers()
        self._setup_error_handler()
        
    def _setup_console_handler(self):
        """Setup console handler for immediate feedback"""
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(self.simple_formatter)
        self.logger.addHandler(console_handler)
        
    def _setup_file_handlers(self):
        """Setup rotating file handlers"""
        # General log file
        general_handler = logging.handlers.RotatingFileHandler(
            self.log_dir / "bot.log",
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        general_handler.setLevel(logging.DEBUG)
        general_handler.setFormatter(self.detailed_formatter)
        self.logger.addHandler(general_handler)
        
        # Daily log file
        daily_handler = logging.handlers.TimedRotatingFileHandler(
            self.log_dir / "daily.log",
            when='midnight',
            backupCount=30
        )
        daily_handler.setLevel(logging.INFO)
        daily_handler.setFormatter(self.detailed_formatter)
        self.logger.addHandler(daily_handler)
        
    def _setup_error_handler(self):
        """Setup dedicated error handler"""
        error_handler = logging.handlers.RotatingFileHandler(
            self.log_dir / "errors.log",
            maxBytes=5*1024*1024,  # 5MB
            backupCount=10
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(self.detailed_formatter)
        self.logger.addHandler(error_handler)
        
    def debug(self, message: str, extra: Optional[dict] = None):
        """Log debug message"""
        self.logger.debug(message, extra=extra)
        
    def info(self, message: str, extra: Optional[dict] = None):
        """Log info message"""
        self.logger.info(message, extra=extra)
        
    def warning(self, message: str, extra: Optional[dict] = None):
        """Log warning message"""
        self.logger.warning(message, extra=extra)
        
    def error(self, message: str, exception: Optional[Exception] = None, extra: Optional[dict] = None):
        """Log error message with optional exception details"""
        if exception:
            self.logger.error(f"{message}: {str(exception)}", exc_info=True, extra=extra)
        else:
            self.logger.error(message, extra=extra)
            
    def critical(self, message: str, exception: Optional[Exception] = None, extra: Optional[dict] = None):
        """Log critical message and potentially trigger emergency shutdown"""
        if exception:
            self.logger.critical(f"{message}: {str(exception)}", exc_info=True, extra=extra)
        else:
            self.logger.critical(message, extra=extra)
            
        # Check if this is an emergency shutdown situation
        if isinstance(exception, EmergencyShutdownException):
            self.emergency_shutdown(message)
            
    def emergency_shutdown(self, reason: str):
        """Trigger emergency shutdown with proper logging"""
        self.logger.critical(f"EMERGENCY SHUTDOWN TRIGGERED: {reason}")
        
        # Create emergency log entry
        emergency_log = self.log_dir / f"emergency_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        with open(emergency_log, 'w') as f:
            f.write(f"Emergency Shutdown Time: {datetime.now()}\n")
            f.write(f"Reason: {reason}\n")
            f.write("=" * 50 + "\n")
            
        # Flush all handlers
        for handler in self.logger.handlers:
            handler.flush()
            
    def log_user_action(self, user_id: int, action: str, details: Optional[str] = None):
        """Log user actions for audit trail"""
        message = f"User {user_id} performed action: {action}"
        if details:
            message += f" - Details: {details}"
        self.info(message, extra={'user_id': user_id, 'action': action})
        
    def log_transaction(self, transaction_id: str, user_id: int, amount: float, transaction_type: str):
        """Log financial transactions"""
        message = f"Transaction {transaction_id}: User {user_id} {transaction_type} {amount}"
        self.info(message, extra={
            'transaction_id': transaction_id,
            'user_id': user_id,
            'amount': amount,
            'type': transaction_type
        })
        
    def log_security_event(self, event_type: str, user_id: Optional[int] = None, details: Optional[str] = None):
        """Log security-related events"""
        message = f"Security Event: {event_type}"
        if user_id:
            message += f" - User: {user_id}"
        if details:
            message += f" - Details: {details}"
        self.warning(message, extra={'security_event': event_type, 'user_id': user_id})


# Global logger instance
logger = BotLogger()

# Convenience functions for backward compatibility
def debug(message: str, extra: Optional[dict] = None):
    logger.debug(message, extra)

def info(message: str, extra: Optional[dict] = None):
    logger.info(message, extra)

def warning(message: str, extra: Optional[dict] = None):
    logger.warning(message, extra)

def error(message: str, exception: Optional[Exception] = None, extra: Optional[dict] = None):
    logger.error(message, exception, extra)

def critical(message: str, exception: Optional[Exception] = None, extra: Optional[dict] = None):
    logger.critical(message, exception, extra)