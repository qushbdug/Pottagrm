"""
Input Validation Utilities for Yemen Net Bot
"""
import re
import ipaddress
from typing import Optional, Dict, Any, List
from decimal import Decimal, InvalidOperation

from ..core.exceptions import ValidationException, InvalidInput, InvalidPhoneNumber
from ..core.logger import logger
from ..config.settings import PAYMENT_CONFIG, SECURITY_CONFIG


def validate_phone_number(phone: str) -> str:
    """
    Validate and normalize phone number
    
    Args:
        phone: Phone number string
        
    Returns:
        Normalized phone number
        
    Raises:
        InvalidPhoneNumber: If phone number is invalid
    """
    try:
        if not phone:
            raise InvalidPhoneNumber("رقم الهاتف مطلوب")
            
        # Remove all non-digit characters
        phone_digits = re.sub(r'\D', '', phone)
        
        if not phone_digits:
            raise InvalidPhoneNumber("رقم الهاتف يجب أن يحتوي على أرقام")
            
        # Yemen phone number patterns
        yemen_patterns = [
            r'^967[0-9]{7,9}$',      # International format without +
            r'^00967[0-9]{7,9}$',    # International format with 00
            r'^0[0-9]{8,9}$',        # National format with leading 0
            r'^[0-9]{8,9}$'          # National format without leading 0
        ]
        
        # Normalize to international format
        if phone_digits.startswith('00967'):
            normalized = phone_digits[2:]  # Remove 00
        elif phone_digits.startswith('967'):
            normalized = phone_digits
        elif phone_digits.startswith('0'):
            normalized = '967' + phone_digits[1:]
        elif len(phone_digits) in [8, 9]:
            normalized = '967' + phone_digits
        else:
            normalized = phone_digits
            
        # Validate against patterns
        for pattern in yemen_patterns:
            if re.match(pattern, normalized) or re.match(pattern, phone_digits):
                # Return in international format
                if not normalized.startswith('967'):
                    if normalized.startswith('0'):
                        normalized = '967' + normalized[1:]
                    elif len(normalized) in [8, 9]:
                        normalized = '967' + normalized
                        
                logger.debug(f"Phone number validated: {phone} -> {normalized}")
                return normalized
                
        raise InvalidPhoneNumber(
            "رقم هاتف غير صحيح. يجب أن يكون رقم يمني صحيح "
            "(مثال: 967771234567 أو 0771234567)"
        )
        
    except InvalidPhoneNumber:
        raise
    except Exception as e:
        logger.error(f"Error validating phone number: {phone}", e)
        raise InvalidPhoneNumber("خطأ في التحقق من رقم الهاتف")


def validate_amount(amount_str: str) -> float:
    """
    Validate monetary amount
    
    Args:
        amount_str: Amount as string
        
    Returns:
        Validated amount as float
        
    Raises:
        InvalidInput: If amount is invalid
    """
    try:
        if not amount_str:
            raise InvalidInput("المبلغ مطلوب")
            
        # Remove currency symbols and spaces
        clean_amount = re.sub(r'[^\d.,]', '', amount_str.strip())
        
        if not clean_amount:
            raise InvalidInput("المبلغ يجب أن يحتوي على أرقام")
            
        # Handle different decimal separators
        if ',' in clean_amount and '.' in clean_amount:
            # Assume comma is thousands separator
            clean_amount = clean_amount.replace(',', '')
        elif ',' in clean_amount:
            # Check if comma is decimal separator (only one comma, appears near end)
            parts = clean_amount.split(',')
            if len(parts) == 2 and len(parts[1]) <= 2:
                clean_amount = clean_amount.replace(',', '.')
            else:
                clean_amount = clean_amount.replace(',', '')
                
        try:
            amount = float(clean_amount)
        except ValueError:
            raise InvalidInput("تنسيق المبلغ غير صحيح")
            
        if amount < 0:
            raise InvalidInput("المبلغ لا يمكن أن يكون سالباً")
            
        if amount == 0:
            raise InvalidInput("المبلغ لا يمكن أن يكون صفراً")
            
        # Check decimal places (max 2)
        decimal_amount = Decimal(str(amount))
        if decimal_amount.as_tuple().exponent < -2:
            raise InvalidInput("المبلغ لا يمكن أن يحتوي على أكثر من منزلتين عشريتين")
            
        # Check against configured limits
        if amount > PAYMENT_CONFIG.max_transfer_amount:
            raise InvalidInput(
                f"المبلغ يتجاوز الحد الأقصى المسموح: {PAYMENT_CONFIG.max_transfer_amount}"
            )
            
        logger.debug(f"Amount validated: {amount_str} -> {amount}")
        return amount
        
    except InvalidInput:
        raise
    except InvalidOperation:
        raise InvalidInput("تنسيق المبلغ غير صحيح")
    except Exception as e:
        logger.error(f"Error validating amount: {amount_str}", e)
        raise InvalidInput("خطأ في التحقق من المبلغ")


def validate_username(username: str) -> str:
    """
    Validate Telegram username
    
    Args:
        username: Username string
        
    Returns:
        Validated username
        
    Raises:
        InvalidInput: If username is invalid
    """
    try:
        if not username:
            raise InvalidInput("اسم المستخدم مطلوب")
            
        # Remove @ if present
        clean_username = username.strip().lstrip('@')
        
        if not clean_username:
            raise InvalidInput("اسم المستخدم لا يمكن أن يكون فارغاً")
            
        # Telegram username rules
        if len(clean_username) < 5:
            raise InvalidInput("اسم المستخدم يجب أن يكون 5 أحرف على الأقل")
            
        if len(clean_username) > 32:
            raise InvalidInput("اسم المستخدم لا يمكن أن يتجاوز 32 حرف")
            
        if not re.match(r'^[a-zA-Z0-9_]+$', clean_username):
            raise InvalidInput("اسم المستخدم يمكن أن يحتوي فقط على أحرف إنجليزية وأرقام و_")
            
        if not re.match(r'^[a-zA-Z]', clean_username):
            raise InvalidInput("اسم المستخدم يجب أن يبدأ بحرف")
            
        if clean_username.endswith('_'):
            raise InvalidInput("اسم المستخدم لا يمكن أن ينتهي بـ _")
            
        if '__' in clean_username:
            raise InvalidInput("اسم المستخدم لا يمكن أن يحتوي على __ متتاليين")
            
        return clean_username
        
    except InvalidInput:
        raise
    except Exception as e:
        logger.error(f"Error validating username: {username}", e)
        raise InvalidInput("خطأ في التحقق من اسم المستخدم")


def validate_password(password: str) -> str:
    """
    Validate password strength
    
    Args:
        password: Password string
        
    Returns:
        Validated password
        
    Raises:
        InvalidInput: If password is invalid
    """
    try:
        if not password:
            raise InvalidInput("كلمة المرور مطلوبة")
            
        if len(password) < SECURITY_CONFIG.password_min_length:
            raise InvalidInput(
                f"كلمة المرور يجب أن تكون {SECURITY_CONFIG.password_min_length} أحرف على الأقل"
            )
            
        if len(password) > 128:
            raise InvalidInput("كلمة المرور لا يمكن أن تتجاوز 128 حرف")
            
        # Check for at least one letter
        if not re.search(r'[a-zA-Z]', password):
            raise InvalidInput("كلمة المرور يجب أن تحتوي على حرف واحد على الأقل")
            
        # Check for at least one digit
        if not re.search(r'\d', password):
            raise InvalidInput("كلمة المرور يجب أن تحتوي على رقم واحد على الأقل")
            
        # Check for common passwords
        common_passwords = [
            'password', '123456', '123456789', 'qwerty', 'abc123',
            'password123', 'admin', 'root', '111111', '000000'
        ]
        
        if password.lower() in common_passwords:
            raise InvalidInput("كلمة المرور ضعيفة جداً، يرجى اختيار كلمة مرور أقوى")
            
        logger.debug("Password validated successfully")
        return password
        
    except InvalidInput:
        raise
    except Exception as e:
        logger.error("Error validating password", e)
        raise InvalidInput("خطأ في التحقق من كلمة المرور")


def validate_email(email: str) -> str:
    """
    Validate email address
    
    Args:
        email: Email address string
        
    Returns:
        Validated email address
        
    Raises:
        InvalidInput: If email is invalid
    """
    try:
        if not email:
            raise InvalidInput("البريد الإلكتروني مطلوب")
            
        email = email.strip().lower()
        
        # Basic email regex
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        
        if not re.match(email_pattern, email):
            raise InvalidInput("تنسيق البريد الإلكتروني غير صحيح")
            
        if len(email) > 254:
            raise InvalidInput("البريد الإلكتروني طويل جداً")
            
        # Check for dangerous characters
        dangerous_chars = ['<', '>', '"', "'", '&', '\n', '\r', '\t']
        if any(char in email for char in dangerous_chars):
            raise InvalidInput("البريد الإلكتروني يحتوي على أحرف غير مسموحة")
            
        logger.debug(f"Email validated: {email}")
        return email
        
    except InvalidInput:
        raise
    except Exception as e:
        logger.error(f"Error validating email: {email}", e)
        raise InvalidInput("خطأ في التحقق من البريد الإلكتروني")


def validate_ip_address(ip: str) -> str:
    """
    Validate IP address
    
    Args:
        ip: IP address string
        
    Returns:
        Validated IP address
        
    Raises:
        InvalidInput: If IP address is invalid
    """
    try:
        if not ip:
            raise InvalidInput("عنوان IP مطلوب")
            
        # Try to parse as IPv4 or IPv6
        ip_obj = ipaddress.ip_address(ip.strip())
        
        # Check if it's a private/reserved address
        if ip_obj.is_private:
            logger.debug(f"Private IP address: {ip}")
        elif ip_obj.is_loopback:
            logger.debug(f"Loopback IP address: {ip}")
        elif ip_obj.is_reserved:
            logger.debug(f"Reserved IP address: {ip}")
            
        return str(ip_obj)
        
    except ValueError:
        raise InvalidInput("تنسيق عنوان IP غير صحيح")
    except Exception as e:
        logger.error(f"Error validating IP address: {ip}", e)
        raise InvalidInput("خطأ في التحقق من عنوان IP")


def validate_network_name(name: str) -> str:
    """
    Validate network name
    
    Args:
        name: Network name string
        
    Returns:
        Validated network name
        
    Raises:
        InvalidInput: If network name is invalid
    """
    try:
        if not name:
            raise InvalidInput("اسم الشبكة مطلوب")
            
        name = name.strip()
        
        if len(name) < 3:
            raise InvalidInput("اسم الشبكة يجب أن يكون 3 أحرف على الأقل")
            
        if len(name) > 50:
            raise InvalidInput("اسم الشبكة لا يمكن أن يتجاوز 50 حرف")
            
        # Allow Arabic, English, numbers, spaces, and some special chars
        if not re.match(r'^[a-zA-Z0-9\u0600-\u06FF\s\-_.()]+$', name):
            raise InvalidInput("اسم الشبكة يحتوي على أحرف غير مسموحة")
            
        # Remove extra spaces
        name = ' '.join(name.split())
        
        logger.debug(f"Network name validated: {name}")
        return name
        
    except InvalidInput:
        raise
    except Exception as e:
        logger.error(f"Error validating network name: {name}", e)
        raise InvalidInput("خطأ في التحقق من اسم الشبكة")


def validate_card_number(card_number: str) -> str:
    """
    Validate card number
    
    Args:
        card_number: Card number string
        
    Returns:
        Validated card number
        
    Raises:
        InvalidInput: If card number is invalid
    """
    try:
        if not card_number:
            raise InvalidInput("رقم البطاقة مطلوب")
            
        # Remove spaces and dashes
        clean_number = re.sub(r'[\s\-]', '', card_number.strip())
        
        if not clean_number:
            raise InvalidInput("رقم البطاقة لا يمكن أن يكون فارغاً")
            
        # Check if contains only alphanumeric characters
        if not re.match(r'^[A-Z0-9]+$', clean_number.upper()):
            raise InvalidInput("رقم البطاقة يجب أن يحتوي فقط على أحرف وأرقام")
            
        if len(clean_number) < 8:
            raise InvalidInput("رقم البطاقة قصير جداً")
            
        if len(clean_number) > 20:
            raise InvalidInput("رقم البطاقة طويل جداً")
            
        return clean_number.upper()
        
    except InvalidInput:
        raise
    except Exception as e:
        logger.error(f"Error validating card number: {card_number}", e)
        raise InvalidInput("خطأ في التحقق من رقم البطاقة")


def validate_text_input(text: str, min_length: int = 1, max_length: int = 1000, 
                       field_name: str = "النص") -> str:
    """
    Validate general text input
    
    Args:
        text: Text to validate
        min_length: Minimum length
        max_length: Maximum length
        field_name: Name of the field for error messages
        
    Returns:
        Validated text
        
    Raises:
        InvalidInput: If text is invalid
    """
    try:
        if not text:
            raise InvalidInput(f"{field_name} مطلوب")
            
        text = text.strip()
        
        if len(text) < min_length:
            raise InvalidInput(f"{field_name} يجب أن يكون {min_length} أحرف على الأقل")
            
        if len(text) > max_length:
            raise InvalidInput(f"{field_name} لا يمكن أن يتجاوز {max_length} حرف")
            
        # Check for dangerous characters
        dangerous_chars = ['<script', '</script', 'javascript:', 'onload=', 'onerror=']
        text_lower = text.lower()
        
        for dangerous in dangerous_chars:
            if dangerous in text_lower:
                raise InvalidInput(f"{field_name} يحتوي على محتوى غير مسموح")
                
        return text
        
    except InvalidInput:
        raise
    except Exception as e:
        logger.error(f"Error validating text input: {text}", e)
        raise InvalidInput(f"خطأ في التحقق من {field_name}")


def validate_environment() -> Dict[str, Any]:
    """
    Validate the overall environment setup
    
    Returns:
        Dictionary with validation results
    """
    try:
        results = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        # Check bot token
        from ..config.settings import TELEGRAM_CONFIG
        if not TELEGRAM_CONFIG.token or TELEGRAM_CONFIG.token == "YOUR_BOT_TOKEN_HERE":
            results['errors'].append("Telegram bot token not configured")
            results['valid'] = False
            
        # Check database path
        from ..config.settings import DATABASE_CONFIG
        if not DATABASE_CONFIG.path:
            results['errors'].append("Database path not configured")
            results['valid'] = False
            
        # Check payment configuration
        if PAYMENT_CONFIG.enable_payments:
            if PAYMENT_CONFIG.min_transfer_amount <= 0:
                results['errors'].append("Invalid minimum transfer amount")
                results['valid'] = False
                
            if PAYMENT_CONFIG.max_transfer_amount <= PAYMENT_CONFIG.min_transfer_amount:
                results['errors'].append("Invalid maximum transfer amount")
                results['valid'] = False
                
        # Check security configuration
        if SECURITY_CONFIG.password_min_length < 4:
            results['warnings'].append("Password minimum length is too low")
            
        if SECURITY_CONFIG.max_login_attempts < 1:
            results['errors'].append("Invalid max login attempts")
            results['valid'] = False
            
        logger.debug(f"Environment validation completed: {results}")
        return results
        
    except Exception as e:
        logger.error("Error validating environment", e)
        return {
            'valid': False,
            'errors': [f"Environment validation error: {str(e)}"],
            'warnings': []
        }