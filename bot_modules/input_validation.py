#!/usr/bin/env python3
"""
نظام التحقق من مدخلات المستخدم
Input Validation System
"""

import re
import logging
from typing import Tuple, Optional
from decimal import Decimal, InvalidOperation

logger = logging.getLogger(__name__)

class InputValidator:
    """فئة التحقق من المدخلات"""
    
    @staticmethod
    def sanitize_text(text: str) -> str:
        """تطهير النص من الأحرف الخطيرة"""
        if not text:
            return ""
        
        # إزالة الأحرف الخطيرة مع الحفاظ على العربية
        sanitized = re.sub(r'[<>"\';\\]', '', text.strip())
        
        # تحديد الطول الأقصى
        if len(sanitized) > 500:
            sanitized = sanitized[:500]
        
        return sanitized
    
    @staticmethod
    def validate_phone_number(phone: str) -> Tuple[bool, str]:
        """التحقق من رقم الهاتف اليمني"""
        if not phone:
            return False, "رقم الهاتف مطلوب"
        
        # إزالة المسافات والأحرف الخاصة
        phone = re.sub(r'[^\d+]', '', phone)
        
        # أنماط الأرقام اليمنية المقبولة
        yemeni_patterns = [
            r'^(\+967|967|00967)?[0-9]{9}$',  # الشكل الدولي
            r'^[0-9]{9}$',  # بدون كود الدولة
            r'^(77|73|70|71)[0-9]{7}$'  # أرقام الجوال اليمنية
        ]
        
        for pattern in yemeni_patterns:
            if re.match(pattern, phone):
                # توحيد التنسيق
                if phone.startswith('+967'):
                    phone = phone[4:]
                elif phone.startswith('967'):
                    phone = phone[3:]
                elif phone.startswith('00967'):
                    phone = phone[5:]
                
                return True, phone
        
        return False, "رقم هاتف يمني غير صحيح"
    
    @staticmethod
    def validate_amount(amount_str: str) -> Tuple[bool, Optional[float], str]:
        """التحقق من المبلغ المالي"""
        if not amount_str:
            return False, None, "المبلغ مطلوب"
        
        try:
            # إزالة الفواصل والمسافات
            cleaned = re.sub(r'[,\s]', '', amount_str)
            amount = float(cleaned)
            
            # التحقق من النطاق المعقول
            if amount <= 0:
                return False, None, "المبلغ يجب أن يكون أكبر من صفر"
            
            if amount > 1000000:  # مليون ريال كحد أقصى
                return False, None, "المبلغ كبير جداً (الحد الأقصى: 1,000,000 ريال)"
            
            # التحقق من عدد الخانات العشرية
            decimal_places = len(str(amount).split('.')[-1]) if '.' in str(amount) else 0
            if decimal_places > 2:
                return False, None, "المبلغ لا يمكن أن يحتوي على أكثر من خانتين عشريتين"
            
            return True, round(amount, 2), ""
            
        except (ValueError, InvalidOperation):
            return False, None, "المبلغ يجب أن يكون رقماً صحيحاً"
    
    @staticmethod
    def validate_wallet_number(wallet_number: str) -> Tuple[bool, str]:
        """التحقق من رقم المحفظة"""
        if not wallet_number:
            return False, "رقم المحفظة مطلوب"
        
        # إزالة المسافات
        wallet_number = re.sub(r'\s', '', wallet_number)
        
        # التحقق من النمط (9 أرقام)
        if not re.match(r'^\d{9}$', wallet_number):
            return False, "رقم المحفظة يجب أن يكون 9 أرقام بالضبط"
        
        return True, wallet_number
    
    @staticmethod
    def validate_network_name(name: str) -> Tuple[bool, str]:
        """التحقق من اسم الشبكة"""
        if not name:
            return False, "اسم الشبكة مطلوب"
        
        name = InputValidator.sanitize_text(name)
        
        # التحقق من الطول
        if len(name) < 3:
            return False, "اسم الشبكة قصير جداً (الحد الأدنى 3 أحرف)"
        
        if len(name) > 50:
            return False, "اسم الشبكة طويل جداً (الحد الأقصى 50 حرف)"
        
        # التحقق من الأحرف المسموحة
        if not re.match(r'^[\u0600-\u06FF\w\s\-_.]+$', name):
            return False, "اسم الشبكة يحتوي على أحرف غير مسموحة"
        
        return True, name
    
    @staticmethod
    def validate_coupon_code(code: str) -> Tuple[bool, str]:
        """التحقق من رمز الكوبون"""
        if not code:
            return False, "رمز الكوبون مطلوب"
        
        code = code.upper().strip()
        
        # نمط الكوبون: A + 8 أرقام
        if not re.match(r'^A\d{8}$', code):
            return False, "رمز الكوبون يجب أن يبدأ بـ A متبوعاً بـ 8 أرقام"
        
        return True, code
    
    @staticmethod
    def validate_percentage(percentage_str: str) -> Tuple[bool, Optional[float], str]:
        """التحقق من النسبة المئوية"""
        if not percentage_str:
            return False, None, "النسبة مطلوبة"
        
        try:
            percentage = float(percentage_str)
            
            if percentage <= 0:
                return False, None, "النسبة يجب أن تكون أكبر من صفر"
            
            if percentage > 100:
                return False, None, "النسبة لا يمكن أن تزيد عن 100%"
            
            return True, round(percentage, 2), ""
            
        except ValueError:
            return False, None, "النسبة يجب أن تكون رقماً صحيحاً"
    
    @staticmethod
    def validate_description(description: str, min_length: int = 10, max_length: int = 500) -> Tuple[bool, str]:
        """التحقق من الوصف"""
        if not description:
            return False, "الوصف مطلوب"
        
        description = InputValidator.sanitize_text(description)
        
        if len(description) < min_length:
            return False, f"الوصف قصير جداً (الحد الأدنى {min_length} أحرف)"
        
        if len(description) > max_length:
            return False, f"الوصف طويل جداً (الحد الأقصى {max_length} حرف)"
        
        return True, description
    
    @staticmethod
    def validate_search_query(query: str) -> Tuple[bool, str, str]:
        """التحقق من استعلام البحث وتحديد نوعه"""
        if not query:
            return False, "", "استعلام البحث مطلوب"
        
        query = InputValidator.sanitize_text(query)
        
        # تحديد نوع البحث
        if query.startswith('الاسم '):
            search_type = 'name'
            search_value = query[5:].strip()
        elif query.startswith('المحفظة '):
            search_type = 'wallet'
            search_value = query[8:].strip()
            # التحقق من رقم المحفظة
            is_valid, validated_wallet = InputValidator.validate_wallet_number(search_value)
            if not is_valid:
                return False, "", validated_wallet
            search_value = validated_wallet
        elif query.startswith('الهاتف '):
            search_type = 'phone'
            search_value = query[7:].strip()
            # التحقق من رقم الهاتف
            is_valid, validated_phone = InputValidator.validate_phone_number(search_value)
            if not is_valid:
                return False, "", validated_phone
            search_value = validated_phone
        elif query.startswith('المعرف '):
            search_type = 'telegram'
            search_value = query[7:].strip().replace('@', '')
        else:
            # بحث عام
            search_type = 'general'
            search_value = query
        
        if len(search_value) < 2:
            return False, "", "قيمة البحث قصيرة جداً (الحد الأدنى حرفان)"
        
        return True, search_type, search_value

# دوال مساعدة للاستخدام المباشر
def sanitize_input(text: str) -> str:
    """تطهير المدخلات"""
    return InputValidator.sanitize_text(text)

def validate_amount(amount_str: str) -> Tuple[bool, Optional[float], str]:
    """التحقق من المبلغ"""
    return InputValidator.validate_amount(amount_str)

def validate_phone(phone: str) -> Tuple[bool, str]:
    """التحقق من رقم الهاتف"""
    return InputValidator.validate_phone_number(phone)

def validate_wallet(wallet: str) -> Tuple[bool, str]:
    """التحقق من رقم المحفظة"""
    return InputValidator.validate_wallet_number(wallet)