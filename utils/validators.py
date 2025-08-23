"""
Input validation utilities for Yemen Net Bot
Provides comprehensive validation for user inputs and system requirements
"""

import re
import os
import sys
import logging
from typing import Any, Optional, Dict, List, Union
from pathlib import Path
import sqlite3
from datetime import datetime

from core.exceptions import ValidationError, ConfigurationError


class Validators:
    """Collection of validation methods"""
    
    # Regular expressions for validation
    PHONE_REGEX = re.compile(r'^(\+967|967|0)?[1-9][0-9]{7,8}$')
    EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    USERNAME_REGEX = re.compile(r'^[a-zA-Z0-9_]{3,20}$')
    CARD_SERIAL_REGEX = re.compile(r'^[A-Z0-9]{8,20}$')
    PIN_CODE_REGEX = re.compile(r'^[0-9]{4,8}$')
    
    @staticmethod
    def validate_user_id(user_id: Any) -> int:
        """Validate Telegram user ID"""
        try:
            user_id = int(user_id)
            if user_id <= 0:
                raise ValidationError("User ID must be positive", field="user_id", value=user_id)
            return user_id
        except (ValueError, TypeError):
            raise ValidationError("Invalid user ID format", field="user_id", value=user_id)
    
    @staticmethod
    def validate_phone(phone: str) -> str:
        """Validate phone number"""
        if not phone or not isinstance(phone, str):
            raise ValidationError("Phone number is required", field="phone", value=phone)
        
        # Clean phone number
        phone = re.sub(r'[^\d+]', '', phone.strip())
        
        if not Validators.PHONE_REGEX.match(phone):
            raise ValidationError(
                "Invalid phone number format. Use Yemen format: +967xxxxxxxx",
                field="phone",
                value=phone
            )
        
        # Normalize to +967 format
        if phone.startswith('967'):
            phone = '+' + phone
        elif phone.startswith('0'):
            phone = '+967' + phone[1:]
        elif not phone.startswith('+967'):
            phone = '+967' + phone
        
        return phone
    
    @staticmethod
    def validate_email(email: str) -> str:
        """Validate email address"""
        if not email or not isinstance(email, str):
            raise ValidationError("Email is required", field="email", value=email)
        
        email = email.strip().lower()
        
        if not Validators.EMAIL_REGEX.match(email):
            raise ValidationError("Invalid email format", field="email", value=email)
        
        return email
    
    @staticmethod
    def validate_username(username: str) -> str:
        """Validate username"""
        if not username or not isinstance(username, str):
            raise ValidationError("Username is required", field="username", value=username)
        
        username = username.strip()
        
        if not Validators.USERNAME_REGEX.match(username):
            raise ValidationError(
                "Username must be 3-20 characters, alphanumeric and underscore only",
                field="username",
                value=username
            )
        
        return username
    
    @staticmethod
    def validate_name(name: str, field_name: str = "name") -> str:
        """Validate person name"""
        if not name or not isinstance(name, str):
            raise ValidationError(f"{field_name.title()} is required", field=field_name, value=name)
        
        name = name.strip()
        
        if len(name) < 2:
            raise ValidationError(f"{field_name.title()} must be at least 2 characters", field=field_name, value=name)
        
        if len(name) > 50:
            raise ValidationError(f"{field_name.title()} must be less than 50 characters", field=field_name, value=name)
        
        # Check for valid characters (Arabic, English, spaces)
        if not re.match(r'^[\u0600-\u06FFa-zA-Z\s]+$', name):
            raise ValidationError(
                f"{field_name.title()} can only contain Arabic or English letters",
                field=field_name,
                value=name
            )
        
        return name
    
    @staticmethod
    def validate_amount(amount: Any, min_amount: float = 0.01, max_amount: float = 100000) -> float:
        """Validate monetary amount"""
        try:
            amount = float(amount)
        except (ValueError, TypeError):
            raise ValidationError("Invalid amount format", field="amount", value=amount)
        
        if amount < min_amount:
            raise ValidationError(f"Amount must be at least {min_amount}", field="amount", value=amount)
        
        if amount > max_amount:
            raise ValidationError(f"Amount cannot exceed {max_amount}", field="amount", value=amount)
        
        # Round to 2 decimal places
        return round(amount, 2)
    
    @staticmethod
    def validate_card_serial(serial: str) -> str:
        """Validate card serial number"""
        if not serial or not isinstance(serial, str):
            raise ValidationError("Card serial is required", field="serial", value=serial)
        
        serial = serial.strip().upper()
        
        if not Validators.CARD_SERIAL_REGEX.match(serial):
            raise ValidationError(
                "Invalid card serial format. Must be 8-20 alphanumeric characters",
                field="serial",
                value=serial
            )
        
        return serial
    
    @staticmethod
    def validate_pin_code(pin: str) -> str:
        """Validate PIN code"""
        if not pin or not isinstance(pin, str):
            raise ValidationError("PIN code is required", field="pin", value=pin)
        
        pin = pin.strip()
        
        if not Validators.PIN_CODE_REGEX.match(pin):
            raise ValidationError(
                "Invalid PIN format. Must be 4-8 digits",
                field="pin",
                value=pin
            )
        
        return pin
    
    @staticmethod
    def validate_role(role: str, valid_roles: List[str]) -> str:
        """Validate user role"""
        if not role or not isinstance(role, str):
            raise ValidationError("Role is required", field="role", value=role)
        
        role = role.strip().lower()
        
        if role not in valid_roles:
            raise ValidationError(
                f"Invalid role. Must be one of: {', '.join(valid_roles)}",
                field="role",
                value=role
            )
        
        return role
    
    @staticmethod
    def validate_transaction_type(transaction_type: str) -> str:
        """Validate transaction type"""
        valid_types = ['credit', 'debit', 'transfer', 'purchase', 'refund', 'commission']
        
        if not transaction_type or not isinstance(transaction_type, str):
            raise ValidationError("Transaction type is required", field="type", value=transaction_type)
        
        transaction_type = transaction_type.strip().lower()
        
        if transaction_type not in valid_types:
            raise ValidationError(
                f"Invalid transaction type. Must be one of: {', '.join(valid_types)}",
                field="type",
                value=transaction_type
            )
        
        return transaction_type
    
    @staticmethod
    def validate_network_name(name: str) -> str:
        """Validate network name"""
        if not name or not isinstance(name, str):
            raise ValidationError("Network name is required", field="name", value=name)
        
        name = name.strip()
        
        if len(name) < 2:
            raise ValidationError("Network name must be at least 2 characters", field="name", value=name)
        
        if len(name) > 50:
            raise ValidationError("Network name must be less than 50 characters", field="name", value=name)
        
        return name
    
    @staticmethod
    def validate_file_upload(file_data: bytes, max_size: int = 10485760, allowed_types: List[str] = None) -> bool:
        """Validate uploaded file"""
        if not file_data:
            raise ValidationError("File data is required", field="file")
        
        if len(file_data) > max_size:
            raise ValidationError(
                f"File size exceeds maximum allowed size of {max_size // 1048576}MB",
                field="file"
            )
        
        # Basic file type detection by magic bytes
        if allowed_types:
            file_type = None
            
            # Excel files
            if file_data.startswith(b'PK'):
                file_type = 'xlsx'
            # CSV files (check for common patterns)
            elif b',' in file_data[:1024] and file_data.decode('utf-8', errors='ignore').count('\n') > 0:
                file_type = 'csv'
            # Text files
            elif file_data.decode('utf-8', errors='ignore').isprintable():
                file_type = 'txt'
            
            if file_type not in allowed_types:
                raise ValidationError(
                    f"Invalid file type. Allowed types: {', '.join(allowed_types)}",
                    field="file"
                )
        
        return True
    
    @staticmethod
    def validate_pagination(page: Any, limit: Any, max_limit: int = 100) -> tuple:
        """Validate pagination parameters"""
        try:
            page = int(page) if page else 1
            limit = int(limit) if limit else 20
        except (ValueError, TypeError):
            raise ValidationError("Invalid pagination parameters")
        
        if page < 1:
            raise ValidationError("Page must be at least 1", field="page", value=page)
        
        if limit < 1:
            raise ValidationError("Limit must be at least 1", field="limit", value=limit)
        
        if limit > max_limit:
            raise ValidationError(f"Limit cannot exceed {max_limit}", field="limit", value=limit)
        
        offset = (page - 1) * limit
        return page, limit, offset
    
    @staticmethod
    def validate_date_range(start_date: str = None, end_date: str = None) -> tuple:
        """Validate date range"""
        start_dt = None
        end_dt = None
        
        if start_date:
            try:
                start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            except ValueError:
                raise ValidationError("Invalid start date format. Use ISO format", field="start_date", value=start_date)
        
        if end_date:
            try:
                end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            except ValueError:
                raise ValidationError("Invalid end date format. Use ISO format", field="end_date", value=end_date)
        
        if start_dt and end_dt and start_dt > end_dt:
            raise ValidationError("Start date cannot be after end date")
        
        return start_dt, end_dt
    
    @staticmethod
    def sanitize_text(text: str, max_length: int = 1000, strip_html: bool = True) -> str:
        """Sanitize text input"""
        if not text or not isinstance(text, str):
            return ""
        
        text = text.strip()
        
        if strip_html:
            # Remove basic HTML tags
            text = re.sub(r'<[^>]+>', '', text)
        
        # Remove potentially dangerous characters
        text = re.sub(r'[<>"\']', '', text)
        
        if len(text) > max_length:
            text = text[:max_length]
        
        return text
    
    @staticmethod
    def validate_search_query(query: str) -> str:
        """Validate search query"""
        if not query or not isinstance(query, str):
            raise ValidationError("Search query is required", field="query", value=query)
        
        query = query.strip()
        
        if len(query) < 2:
            raise ValidationError("Search query must be at least 2 characters", field="query", value=query)
        
        if len(query) > 100:
            raise ValidationError("Search query must be less than 100 characters", field="query", value=query)
        
        # Remove special SQL characters
        query = re.sub(r'[\'";\\]', '', query)
        
        return query


def validate_environment() -> bool:
    """Validate system environment and requirements"""
    logger = logging.getLogger(__name__)
    
    try:
        # Check Python version
        if sys.version_info < (3, 8):
            raise ConfigurationError("Python 3.8 or higher is required")
        
        # Check required environment variables
        required_vars = ['BOT_TOKEN']
        missing_vars = []
        
        for var in required_vars:
            if not os.getenv(var):
                # Try to find in config files
                config_files = ['bot_modules/config.py', 'config.py', '.env']
                found = False
                
                for config_file in config_files:
                    if os.path.exists(config_file):
                        try:
                            with open(config_file, 'r') as f:
                                content = f.read()
                                if f'{var}=' in content:
                                    found = True
                                    break
                        except Exception:
                            continue
                
                if not found:
                    missing_vars.append(var)
        
        if missing_vars:
            logger.warning(f"Missing environment variables: {', '.join(missing_vars)}")
            # Don't fail completely, as token might be in config files
        
        # Check write permissions
        try:
            test_file = Path('test_write_permission.tmp')
            test_file.write_text('test')
            test_file.unlink()
        except Exception:
            raise ConfigurationError("No write permission in current directory")
        
        # Check SQLite availability
        try:
            conn = sqlite3.connect(':memory:')
            conn.execute('CREATE TABLE test (id INTEGER)')
            conn.close()
        except Exception as e:
            raise ConfigurationError(f"SQLite not available: {e}")
        
        # Check required Python packages
        required_packages = [
            'telegram',
            'aiosqlite',
            'asyncio'
        ]
        
        missing_packages = []
        for package in required_packages:
            try:
                __import__(package)
            except ImportError:
                missing_packages.append(package)
        
        if missing_packages:
            logger.warning(f"Missing optional packages: {', '.join(missing_packages)}")
        
        logger.info("✅ Environment validation passed")
        return True
        
    except ConfigurationError:
        raise
    except Exception as e:
        logger.error(f"❌ Environment validation failed: {e}")
        raise ConfigurationError(f"Environment validation failed: {e}")


def create_validation_middleware():
    """Create validation middleware for handlers"""
    def validate_input(required_fields: Dict[str, str] = None, 
                      optional_fields: Dict[str, str] = None):
        """Decorator for input validation"""
        def decorator(handler_func):
            async def wrapper(update, context, *args, **kwargs):
                try:
                    # Validate required fields
                    if required_fields:
                        for field, field_type in required_fields.items():
                            value = getattr(update, field, None)
                            if value is None:
                                raise ValidationError(f"Required field '{field}' is missing")
                            
                            # Type validation
                            if field_type == 'user_id':
                                Validators.validate_user_id(value)
                            elif field_type == 'text':
                                if not isinstance(value, str) or len(value.strip()) == 0:
                                    raise ValidationError(f"Field '{field}' must be non-empty text")
                    
                    # Continue with handler
                    return await handler_func(update, context, *args, **kwargs)
                    
                except ValidationError as e:
                    logger = logging.getLogger(__name__)
                    logger.warning(f"Validation error in {handler_func.__name__}: {e}")
                    
                    if update and update.effective_chat:
                        await context.bot.send_message(
                            chat_id=update.effective_chat.id,
                            text=f"❌ {e.message}"
                        )
                    return None
                
            return wrapper
        return decorator
    
    return validate_input