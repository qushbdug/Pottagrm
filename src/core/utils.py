#!/usr/bin/env python3
"""
Professional Utility Functions for Yemen Net Bot
Advanced helper functions with error handling and security features.
"""

import logging
import re
import hashlib
import secrets
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP

from .config import config, EMOJIS
from .database import db

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Custom validation error."""
    pass


class SecurityManager:
    """Security utilities for input validation and sanitization."""
    
    @staticmethod
    def validate_phone_number(phone: str) -> bool:
        """Validate Yemen phone number format."""
        # Yemen phone number patterns
        patterns = [
            r'^\+967[0-9]{9}$',  # +967XXXXXXXXX
            r'^967[0-9]{9}$',    # 967XXXXXXXXX
            r'^[0-9]{9}$',       # XXXXXXXXX
        ]
        
        for pattern in patterns:
            if re.match(pattern, phone):
                return True
        return False
    
    @staticmethod
    def sanitize_input(text: str, max_length: int = 1000) -> str:
        """Sanitize user input to prevent injection attacks."""
        if not text or len(text) > max_length:
            raise ValidationError(f"Input too long. Maximum length is {max_length} characters.")
        
        # Remove potentially dangerous characters
        sanitized = re.sub(r'[<>"\']', '', text)
        return sanitized.strip()
    
    @staticmethod
    def validate_amount(amount: Union[str, float, int]) -> float:
        """Validate and convert amount to float."""
        try:
            if isinstance(amount, str):
                amount = float(amount)
            elif isinstance(amount, int):
                amount = float(amount)
            
            if amount <= 0:
                raise ValidationError("Amount must be positive")
            
            if amount > 1000000:  # Maximum amount limit
                raise ValidationError("Amount exceeds maximum limit")
            
            # Round to 2 decimal places
            return round(amount, 2)
            
        except (ValueError, TypeError):
            raise ValidationError("Invalid amount format")


class TextFormatter:
    """Text formatting utilities for better user experience."""
    
    @staticmethod
    def format_currency(amount: float) -> str:
        """Format amount as currency."""
        return f"{amount:,.2f} ريال"
    
    @staticmethod
    def format_phone(phone: str) -> str:
        """Format phone number for display."""
        if phone.startswith('+967'):
            return f"+967 {phone[4:7]} {phone[7:9]} {phone[9:]}"
        elif phone.startswith('967'):
            return f"+967 {phone[3:6]} {phone[6:8]} {phone[8:]}"
        else:
            return f"+967 {phone[:3]} {phone[3:5]} {phone[5:]}"
    
    @staticmethod
    def format_datetime(dt: datetime) -> str:
        """Format datetime for Arabic users."""
        # Convert to Yemen timezone (UTC+3)
        yemen_time = dt + timedelta(hours=3)
        return yemen_time.strftime("%Y/%m/%d %H:%M")
    
    @staticmethod
    def truncate_text(text: str, max_length: int = 50) -> str:
        """Truncate text with ellipsis."""
        if len(text) <= max_length:
            return text
        return text[:max_length-3] + "..."


class KeyboardBuilder:
    """Build inline keyboards with consistent styling."""
    
    @staticmethod
    def main_menu(user_role: str = 'customer') -> List[List[Dict[str, str]]]:
        """Build main menu keyboard based on user role."""
        keyboard = [
            [{'text': f"{EMOJIS['wallet']} محفظتي المطورة", 'callback_data': 'enhanced_wallet'}],
            [{'text': f"{EMOJIS['purchase']} شراء كروت الشبكة", 'callback_data': 'buy_cards'}],
            [{'text': f"{EMOJIS['transfer']} تحويل رصيد", 'callback_data': 'transfer_balance'}],
            [{'text': f"{EMOJIS['search']} البحث عن شبكات", 'callback_data': 'search_networks'}],
            [{'text': f"{EMOJIS['stats']} تقاريري", 'callback_data': 'my_reports'}],
            [{'text': f"{EMOJIS['settings']} الإعدادات", 'callback_data': 'settings'}]
        ]
        
        # Add admin-specific buttons
        if user_role in ['admin', 'super_admin']:
            keyboard.append([{'text': f"{EMOJIS['admin']} لوحة الإدارة", 'callback_data': 'admin_panel'}])
        
        return keyboard
    
    @staticmethod
    def back_button(callback_data: str = 'main_menu') -> List[List[Dict[str, str]]]:
        """Build back button keyboard."""
        return [[{'text': f"{EMOJIS['back']} رجوع", 'callback_data': callback_data}]]
    
    @staticmethod
    def confirm_cancel(callback_data: str = 'main_menu') -> List[List[Dict[str, str]]]:
        """Build confirm/cancel keyboard."""
        return [
            [
                {'text': f"{EMOJIS['confirm']} تأكيد", 'callback_data': 'confirm'},
                {'text': f"{EMOJIS['cancel']} إلغاء", 'callback_data': callback_data}
            ]
        ]


class ErrorHandler:
    """Centralized error handling utilities."""
    
    @staticmethod
    def handle_database_error(error: Exception, operation: str) -> str:
        """Handle database errors gracefully."""
        logger.error(f"Database error in {operation}: {error}")
        
        if "UNIQUE constraint failed" in str(error):
            return f"{EMOJIS['error']} البيانات موجودة مسبقاً"
        elif "FOREIGN KEY constraint failed" in str(error):
            return f"{EMOJIS['error']} خطأ في العلاقات بين البيانات"
        elif "database is locked" in str(error):
            return f"{EMOJIS['warning']} قاعدة البيانات مشغولة، حاول مرة أخرى"
        else:
            return f"{EMOJIS['error']} حدث خطأ في قاعدة البيانات"
    
    @staticmethod
    def handle_validation_error(error: ValidationError) -> str:
        """Handle validation errors."""
        return f"{EMOJIS['warning']} {str(error)}"
    
    @staticmethod
    def handle_general_error(error: Exception, operation: str) -> str:
        """Handle general errors."""
        logger.error(f"Error in {operation}: {error}")
        return f"{EMOJIS['error']} حدث خطأ غير متوقع"


class RateLimiter:
    """Simple rate limiting for user actions."""
    
    def __init__(self):
        self._user_actions = {}
    
    def can_perform_action(self, user_id: int, action: str, limit: int = 5, window: int = 60) -> bool:
        """Check if user can perform action based on rate limit."""
        current_time = datetime.now()
        key = f"{user_id}_{action}"
        
        if key not in self._user_actions:
            self._user_actions[key] = []
        
        # Remove old actions outside the time window
        self._user_actions[key] = [
            action_time for action_time in self._user_actions[key]
            if (current_time - action_time).seconds < window
        ]
        
        # Check if user has exceeded the limit
        if len(self._user_actions[key]) >= limit:
            return False
        
        # Add current action
        self._user_actions[key].append(current_time)
        return True


class NotificationManager:
    """Manage user notifications and alerts."""
    
    @staticmethod
    def create_notification_message(
        title: str,
        message: str,
        notification_type: str = 'info'
    ) -> str:
        """Create formatted notification message."""
        emoji_map = {
            'success': EMOJIS['success'],
            'error': EMOJIS['error'],
            'warning': EMOJIS['warning'],
            'info': EMOJIS['info']
        }
        
        emoji = emoji_map.get(notification_type, EMOJIS['info'])
        return f"{emoji} **{title}**\n\n{message}"
    
    @staticmethod
    def format_transaction_notification(
        transaction_type: str,
        amount: float,
        balance: float
    ) -> str:
        """Format transaction notification."""
        type_emoji = {
            'deposit': EMOJIS['money'],
            'withdrawal': EMOJIS['money'],
            'transfer_sent': EMOJIS['transfer'],
            'transfer_received': EMOJIS['transfer'],
            'purchase': EMOJIS['purchase']
        }
        
        emoji = type_emoji.get(transaction_type, EMOJIS['info'])
        return f"{emoji} **{transaction_type.replace('_', ' ').title()}**\n" \
               f"المبلغ: {TextFormatter.format_currency(amount)}\n" \
               f"الرصيد الجديد: {TextFormatter.format_currency(balance)}"


# Global instances
security = SecurityManager()
formatter = TextFormatter()
keyboard_builder = KeyboardBuilder()
error_handler = ErrorHandler()
rate_limiter = RateLimiter()
notification_manager = NotificationManager()


def get_user(telegram_id: int):
    """Get user from database with activity update."""
    user = db.get_user(telegram_id)
    if user:
        db.update_user_activity(user.id)
    return user


def update_user_balance(user_id: int, amount: float, transaction_type: str, description: str = ""):
    """Update user balance with proper error handling."""
    try:
        return db.update_user_balance(user_id, amount, transaction_type, description)
    except Exception as e:
        logger.error(f"Failed to update balance: {e}")
        return False


def validate_user_input(text: str, input_type: str = 'text') -> str:
    """Validate and sanitize user input."""
    try:
        if input_type == 'phone':
            if not security.validate_phone_number(text):
                raise ValidationError("رقم الهاتف غير صحيح")
        elif input_type == 'amount':
            return str(security.validate_amount(text))
        
        return security.sanitize_input(text)
    except ValidationError as e:
        raise e
    except Exception as e:
        logger.error(f"Input validation error: {e}")
        raise ValidationError("بيانات غير صحيحة")


def format_response(message: str, emoji: str = None) -> str:
    """Format response message with optional emoji."""
    if emoji:
        return f"{emoji} {message}"
    return message


def is_admin(user_role: str) -> bool:
    """Check if user has admin privileges."""
    return user_role in ['admin', 'super_admin']


def has_permission(user_role: str, permission: str) -> bool:
    """Check if user has specific permission."""
    role_permissions = {
        'customer': [],
        'agent': ['view_reports'],
        'supplier': ['view_reports'],
        'admin': ['create_users', 'manage_balance', 'view_reports', 'manage_promotions'],
        'super_admin': ['create_users', 'manage_balance', 'approve_suppliers', 
                       'view_reports', 'manage_promotions', 'system_admin']
    }
    
    return permission in role_permissions.get(user_role, [])