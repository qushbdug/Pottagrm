#!/usr/bin/env python3
"""
Enhanced Error Messages System
نظام رسائل الخطأ المحسن والوصفي
"""

import logging
from datetime import datetime
from bot_modules.config import EMOJIS

logger = logging.getLogger(__name__)

class ErrorMessages:
    """فئة رسائل الخطأ المحسنة والوصفية"""
    
    @staticmethod
    def format_error(error_type: str, specific_error: str = None, user_action: str = None, error_code: str = None) -> str:
        """تنسيق رسالة خطأ وصفية وشاملة"""
        
        timestamp = datetime.now().strftime('%H:%M')
        
        # رسالة أساسية
        base_message = f"{EMOJIS['error']} **خطأ في {error_type}**\n"
        
        # إضافة تفاصيل محددة
        if specific_error:
            base_message += f"🔍 **السبب:** {specific_error}\n"
        
        # إضافة الإجراء المطلوب
        if user_action:
            base_message += f"💡 **الحل:** {user_action}\n"
        
        # إضافة كود الخطأ للمطورين
        if error_code:
            base_message += f"🔧 **كود الخطأ:** `{error_code}`\n"
        
        # إضافة الوقت
        base_message += f"⏰ **الوقت:** {timestamp}"
        
        return base_message

    @staticmethod
    def database_error(operation: str, details: str = None) -> str:
        """خطأ قاعدة البيانات"""
        return ErrorMessages.format_error(
            error_type="قاعدة البيانات",
            specific_error=f"فشل في تنفيذ عملية {operation}" + (f" - {details}" if details else ""),
            user_action="تأكد من اتصال الإنترنت وحاول مرة أخرى خلال دقائق قليلة",
            error_code="DB_ERROR"
        )
    
    @staticmethod
    def permission_error(required_role: str, current_role: str = None) -> str:
        """خطأ الصلاحيات"""
        return ErrorMessages.format_error(
            error_type="الصلاحيات",
            specific_error=f"تحتاج إلى صلاحية '{required_role}'" + (f" (دورك الحالي: {current_role})" if current_role else ""),
            user_action="تواصل مع الإدارة للحصول على الصلاحيات المطلوبة",
            error_code="PERM_ERROR"
        )
    
    @staticmethod
    def validation_error(field: str, expected: str, received: str = None) -> str:
        """خطأ التحقق من البيانات"""
        return ErrorMessages.format_error(
            error_type="البيانات المدخلة",
            specific_error=f"حقل '{field}' غير صحيح، متوقع: {expected}" + (f" (تم إدخال: {received})" if received else ""),
            user_action="راجع البيانات المدخلة وأعد المحاولة بالتنسيق الصحيح",
            error_code="VALID_ERROR"
        )
    
    @staticmethod
    def network_error(operation: str, api_error: str = None) -> str:
        """خطأ الشبكة والاتصال"""
        return ErrorMessages.format_error(
            error_type="الاتصال",
            specific_error=f"فشل في {operation}" + (f" - {api_error}" if api_error else " - انقطاع الاتصال"),
            user_action="تحقق من اتصال الإنترنت وحاول مرة أخرى خلال دقائق",
            error_code="NET_ERROR"
        )
    
    @staticmethod
    def file_error(operation: str, file_type: str = None, file_size: str = None) -> str:
        """خطأ الملفات"""
        details = f"في معالجة ملف {operation}"
        if file_type:
            details += f" من نوع {file_type}"
        if file_size:
            details += f" بحجم {file_size}"
            
        return ErrorMessages.format_error(
            error_type="الملف",
            specific_error=details,
            user_action="تأكد من نوع وحجم الملف ثم أعد المحاولة",
            error_code="FILE_ERROR"
        )
    
    @staticmethod
    def balance_error(current_balance: float, required_amount: float) -> str:
        """خطأ الرصيد"""
        return ErrorMessages.format_error(
            error_type="الرصيد",
            specific_error=f"رصيدك ({current_balance:.2f} ريال) غير كافي للمبلغ المطلوب ({required_amount:.2f} ريال)",
            user_action="قم بشحن رصيدك أولاً أو قلل من المبلغ المطلوب",
            error_code="BALANCE_ERROR"
        )
    
    @staticmethod
    def card_error(operation: str, card_info: str = None) -> str:
        """خطأ الكروت"""
        return ErrorMessages.format_error(
            error_type="كروت الشحن",
            specific_error=f"مشكلة في {operation}" + (f" للكرت {card_info}" if card_info else ""),
            user_action="تحقق من بيانات الكرت أو تواصل مع الدعم الفني",
            error_code="CARD_ERROR"
        )
    
    @staticmethod
    def supplier_error(operation: str, supplier_status: str = None) -> str:
        """خطأ المزودين"""
        details = f"في عملية {operation}"
        if supplier_status:
            details += f" (حالة المزود: {supplier_status})"
            
        return ErrorMessages.format_error(
            error_type="المزود",
            specific_error=details,
            user_action="تأكد من تفعيل حسابك كمزود أو تواصل مع الإدارة",
            error_code="SUPPLIER_ERROR"
        )
    
    @staticmethod
    def admin_error(operation: str, admin_level: str = None) -> str:
        """خطأ الإدارة"""
        return ErrorMessages.format_error(
            error_type="الإدارة",
            specific_error=f"فشل في تنفيذ عملية {operation}" + (f" للمستوى {admin_level}" if admin_level else ""),
            user_action="تحقق من صلاحياتك الإدارية أو تواصل مع المشرف الأعلى",
            error_code="ADMIN_ERROR"
        )
    
    @staticmethod
    def transaction_error(transaction_type: str, transaction_id: str = None, reason: str = None) -> str:
        """خطأ المعاملات"""
        details = f"في معاملة {transaction_type}"
        if transaction_id:
            details += f" رقم {transaction_id}"
        if reason:
            details += f" - {reason}"
            
        return ErrorMessages.format_error(
            error_type="المعاملة",
            specific_error=details,
            user_action="راجع بيانات المعاملة أو تواصل مع الدعم إذا استمرت المشكلة",
            error_code="TRANS_ERROR"
        )
    
    @staticmethod
    def upload_error(upload_type: str, file_count: int = None, failed_count: int = None) -> str:
        """خطأ الرفع"""
        details = f"في رفع {upload_type}"
        if file_count and failed_count:
            details += f" - فشل {failed_count} من أصل {file_count} ملف"
            
        return ErrorMessages.format_error(
            error_type="الرفع",
            specific_error=details,
            user_action="تأكد من تنسيق الملفات وحجمها ثم أعد المحاولة",
            error_code="UPLOAD_ERROR"
        )
    
    @staticmethod
    def session_error(action: str) -> str:
        """خطأ الجلسة"""
        return ErrorMessages.format_error(
            error_type="الجلسة",
            specific_error=f"انتهت صلاحية الجلسة أثناء {action}",
            user_action="أعد تسجيل الدخول وحاول مرة أخرى",
            error_code="SESSION_ERROR"
        )
    
    @staticmethod
    def custom_error(error_type: str, problem: str, solution: str, code: str = None) -> str:
        """خطأ مخصص"""
        return ErrorMessages.format_error(
            error_type=error_type,
            specific_error=problem,
            user_action=solution,
            error_code=code
        )

# دوال مساعدة للاستخدام السريع
def db_error(operation: str, details: str = None) -> str:
    """اختصار لخطأ قاعدة البيانات"""
    return ErrorMessages.database_error(operation, details)

def perm_error(required_role: str, current_role: str = None) -> str:
    """اختصار لخطأ الصلاحيات"""
    return ErrorMessages.permission_error(required_role, current_role)

def net_error(operation: str, api_error: str = None) -> str:
    """اختصار لخطأ الشبكة"""
    return ErrorMessages.network_error(operation, api_error)

def file_error(operation: str, file_type: str = None, file_size: str = None) -> str:
    """اختصار لخطأ الملفات"""
    return ErrorMessages.file_error(operation, file_type, file_size)

def balance_error(current: float, required: float) -> str:
    """اختصار لخطأ الرصيد"""
    return ErrorMessages.balance_error(current, required)

# قاموس رسائل الخطأ المحسنة للاستخدام المباشر
ENHANCED_ERRORS = {
    # أخطاء قاعدة البيانات
    'db_connection': "فشل في الاتصال بقاعدة البيانات - تحقق من الخادم",
    'db_query': "خطأ في استعلام قاعدة البيانات - البيانات قد تكون تالفة",
    'db_insert': "فشل في إدراج البيانات - قد يكون هناك تضارب في المعرفات",
    'db_update': "فشل في تحديث البيانات - تحقق من وجود السجل المطلوب",
    'db_delete': "فشل في حذف البيانات - قد تكون مرتبطة ببيانات أخرى",
    
    # أخطاء الشبكة
    'network_timeout': "انتهت مهلة الاتصال - تحقق من سرعة الإنترنت",
    'api_error': "خطأ في واجهة برمجة التطبيقات - المعدات مؤقتاً غير متاحة",
    'telegram_error': "خطأ في خوادم Telegram - حاول مرة أخرى خلال دقائق",
    
    # أخطاء الملفات
    'file_too_large': "حجم الملف كبير جداً - الحد الأقصى 50 ميجا",
    'file_invalid_format': "تنسيق الملف غير مدعوم - استخدم Excel أو CSV فقط",
    'file_corrupted': "الملف تالف أو غير قابل للقراءة - أعد تصديره",
    
    # أخطاء المستخدمين
    'user_not_found': "المستخدم غير موجود في النظام",
    'user_inactive': "حساب المستخدم غير مفعل - تواصل مع الإدارة",
    'user_banned': "تم حظر هذا المستخدم - تواصل مع الدعم",
    
    # أخطاء العمليات
    'operation_cancelled': "تم إلغاء العملية بناء على طلب المستخدم",
    'operation_timeout': "انتهت مهلة العملية - العملية تستغرق وقتاً أطول من المتوقع",
    'operation_failed': "فشلت العملية لأسباب تقنية - أعد المحاولة"
}

# تصدير الفئات والدوال
__all__ = ['ErrorMessages', 'db_error', 'perm_error', 'net_error', 'file_error', 'balance_error', 'ENHANCED_ERRORS']