"""
Advanced logging configuration for Yemen Net Bot
"""

import logging
import logging.handlers
import sys
import os
from datetime import datetime
from typing import Optional
import json


class ColoredFormatter(logging.Formatter):
    """Colored console formatter for better readability"""
    
    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[32m',      # Green
        'WARNING': '\033[33m',   # Yellow
        'ERROR': '\033[31m',     # Red
        'CRITICAL': '\033[35m',  # Magenta
        'RESET': '\033[0m'       # Reset
    }
    
    def format(self, record):
        # Add color to the level name
        if hasattr(record, 'levelname'):
            color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
            record.levelname = f"{color}{record.levelname}{self.COLORS['RESET']}"
        
        return super().format(record)


class StructuredFormatter(logging.Formatter):
    """JSON formatter for structured logging"""
    
    def format(self, record):
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Add extra fields if present
        if hasattr(record, 'user_id'):
            log_entry['user_id'] = record.user_id
        if hasattr(record, 'error_type'):
            log_entry['error_type'] = record.error_type
        if hasattr(record, 'update'):
            log_entry['update'] = record.update
        
        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_entry, ensure_ascii=False, separators=(',', ':'))


class BotLogger:
    """Enhanced logger for the bot with multiple handlers"""
    
    def __init__(self, name: str = "YemenNetBot", log_level: str = "INFO", log_file: str = "bot.log"):
        self.name = name
        self.log_level = getattr(logging, log_level.upper(), logging.INFO)
        self.log_file = log_file
        self.logger = None
        self._setup_logger()
    
    def _setup_logger(self):
        """Setup logger with multiple handlers"""
        self.logger = logging.getLogger(self.name)
        self.logger.setLevel(self.log_level)
        
        # Clear existing handlers to avoid duplicates
        self.logger.handlers.clear()
        
        # Console handler with colored output
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(self.log_level)
        console_formatter = ColoredFormatter(
            '%(asctime)s | %(levelname)s | %(name)s:%(lineno)d | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)
        
        # File handler with rotation
        try:
            file_handler = logging.handlers.RotatingFileHandler(
                self.log_file,
                maxBytes=10 * 1024 * 1024,  # 10MB
                backupCount=5,
                encoding='utf-8'
            )
            file_handler.setLevel(logging.DEBUG)  # Log everything to file
            file_formatter = logging.Formatter(
                '%(asctime)s | %(levelname)s | %(name)s:%(lineno)d | %(funcName)s | %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(file_formatter)
            self.logger.addHandler(file_handler)
        except Exception as e:
            self.logger.warning(f"Could not setup file handler: {e}")
        
        # Error file handler for errors and above
        try:
            error_handler = logging.handlers.RotatingFileHandler(
                'error.log',
                maxBytes=5 * 1024 * 1024,  # 5MB
                backupCount=3,
                encoding='utf-8'
            )
            error_handler.setLevel(logging.ERROR)
            error_formatter = StructuredFormatter()
            error_handler.setFormatter(error_formatter)
            self.logger.addHandler(error_handler)
        except Exception as e:
            self.logger.warning(f"Could not setup error handler: {e}")
        
        # Prevent propagation to root logger
        self.logger.propagate = False
    
    def get_logger(self):
        """Get the configured logger instance"""
        return self.logger
    
    def log_user_action(self, user_id: int, action: str, details: Optional[dict] = None):
        """Log user actions with structured data"""
        message = f"User {user_id} performed action: {action}"
        if details:
            message += f" | Details: {details}"
        
        # Use extra parameter to add structured data
        self.logger.info(message, extra={
            'user_id': user_id,
            'action': action,
            'details': details or {}
        })
    
    def log_error_with_context(self, error: Exception, context: dict = None):
        """Log errors with additional context"""
        context = context or {}
        self.logger.error(
            f"Error occurred: {error}",
            exc_info=True,
            extra={
                'error_type': type(error).__name__,
                'context': context
            }
        )
    
    def log_performance(self, operation: str, duration: float, details: Optional[dict] = None):
        """Log performance metrics"""
        message = f"Performance: {operation} took {duration:.3f}s"
        if details:
            message += f" | {details}"
        
        self.logger.info(message, extra={
            'operation': operation,
            'duration': duration,
            'performance_details': details or {}
        })
    
    def log_security_event(self, event_type: str, user_id: Optional[int] = None, details: Optional[dict] = None):
        """Log security-related events"""
        message = f"Security event: {event_type}"
        if user_id:
            message += f" | User: {user_id}"
        if details:
            message += f" | Details: {details}"
        
        self.logger.warning(message, extra={
            'security_event': event_type,
            'user_id': user_id,
            'security_details': details or {}
        })


def setup_logger(name: str = "YemenNetBot", log_level: str = "INFO", log_file: str = "bot.log") -> logging.Logger:
    """Setup and return a configured logger"""
    bot_logger = BotLogger(name, log_level, log_file)
    return bot_logger.get_logger()


def get_performance_logger() -> logging.Logger:
    """Get a dedicated performance logger"""
    perf_logger = logging.getLogger("Performance")
    
    if not perf_logger.handlers:
        # Setup performance file handler
        try:
            perf_handler = logging.handlers.RotatingFileHandler(
                'performance.log',
                maxBytes=5 * 1024 * 1024,  # 5MB
                backupCount=2,
                encoding='utf-8'
            )
            perf_handler.setLevel(logging.INFO)
            perf_formatter = StructuredFormatter()
            perf_handler.setFormatter(perf_formatter)
            perf_logger.addHandler(perf_handler)
            perf_logger.setLevel(logging.INFO)
            perf_logger.propagate = False
        except Exception:
            # Fall back to main logger if performance logger setup fails
            return setup_logger()
    
    return perf_logger


def get_security_logger() -> logging.Logger:
    """Get a dedicated security logger"""
    sec_logger = logging.getLogger("Security")
    
    if not sec_logger.handlers:
        # Setup security file handler
        try:
            sec_handler = logging.handlers.RotatingFileHandler(
                'security.log',
                maxBytes=5 * 1024 * 1024,  # 5MB
                backupCount=10,  # Keep more security logs
                encoding='utf-8'
            )
            sec_handler.setLevel(logging.WARNING)
            sec_formatter = StructuredFormatter()
            sec_handler.setFormatter(sec_formatter)
            sec_logger.addHandler(sec_handler)
            sec_logger.setLevel(logging.WARNING)
            sec_logger.propagate = False
        except Exception:
            # Fall back to main logger if security logger setup fails
            return setup_logger()
    
    return sec_logger


# Utility functions for common logging patterns
def log_function_call(logger: logging.Logger):
    """Decorator to log function calls"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            start_time = datetime.now()
            logger.debug(f"Calling {func.__name__} with args={args}, kwargs={kwargs}")
            
            try:
                result = func(*args, **kwargs)
                duration = (datetime.now() - start_time).total_seconds()
                logger.debug(f"{func.__name__} completed in {duration:.3f}s")
                return result
            except Exception as e:
                duration = (datetime.now() - start_time).total_seconds()
                logger.error(f"{func.__name__} failed after {duration:.3f}s: {e}", exc_info=True)
                raise
        
        return wrapper
    return decorator


def log_async_function_call(logger: logging.Logger):
    """Decorator to log async function calls"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            start_time = datetime.now()
            logger.debug(f"Calling async {func.__name__} with args={args}, kwargs={kwargs}")
            
            try:
                result = await func(*args, **kwargs)
                duration = (datetime.now() - start_time).total_seconds()
                logger.debug(f"Async {func.__name__} completed in {duration:.3f}s")
                return result
            except Exception as e:
                duration = (datetime.now() - start_time).total_seconds()
                logger.error(f"Async {func.__name__} failed after {duration:.3f}s: {e}", exc_info=True)
                raise
        
        return wrapper
    return decorator