"""
Configuration settings for Yemen Net Bot v2
"""

import os
import logging
from typing import Dict, Any, Optional
from pathlib import Path

# Base directory
BASE_DIR = Path(__file__).parent.parent.parent

# Environment
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
DEBUG = ENVIRONMENT == "development"

# Bot Configuration
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
BOT_NAME = "Yemen Net Bot v2"
BOT_VERSION = "2.0.0"
BOT_DESCRIPTION = "Enhanced Yemen Net Bot with modern architecture"

# Database Configuration
DB_PATH = os.getenv("DB_PATH", str(BASE_DIR / "yemen_net.db"))
DB_MAX_CONNECTIONS = int(os.getenv("DB_MAX_CONNECTIONS", "10"))
DB_CONNECTION_TIMEOUT = int(os.getenv("DB_CONNECTION_TIMEOUT", "30"))
DB_ENABLE_WAL = os.getenv("DB_ENABLE_WAL", "true").lower() == "true"

# Cache Configuration
CACHE_MAX_SIZE = int(os.getenv("CACHE_MAX_SIZE", "1000"))
CACHE_CLEANUP_INTERVAL = int(os.getenv("CACHE_CLEANUP_INTERVAL", "60"))
CACHE_DEFAULT_TTL = int(os.getenv("CACHE_DEFAULT_TTL", "300"))

# Rate Limiting Configuration
RATE_LIMIT_MESSAGE = int(os.getenv("RATE_LIMIT_MESSAGE", "20"))
RATE_LIMIT_BUTTON_CLICK = int(os.getenv("RATE_LIMIT_BUTTON_CLICK", "30"))
RATE_LIMIT_PAYMENT = int(os.getenv("RATE_LIMIT_PAYMENT", "5"))
RATE_LIMIT_ADMIN_ACTION = int(os.getenv("RATE_LIMIT_ADMIN_ACTION", "10"))
RATE_LIMIT_FILE_UPLOAD = int(os.getenv("RATE_LIMIT_FILE_UPLOAD", "3"))
RATE_LIMIT_API_CALL = int(os.getenv("RATE_LIMIT_API_CALL", "50"))

# Security Configuration
SECURITY_MAX_LOGIN_ATTEMPTS = int(os.getenv("SECURITY_MAX_LOGIN_ATTEMPTS", "3"))
SECURITY_LOGIN_LOCKOUT_DURATION = int(os.getenv("SECURITY_LOGIN_LOCKOUT_DURATION", "300"))
SECURITY_SESSION_TIMEOUT = int(os.getenv("SECURITY_SESSION_TIMEOUT", "3600"))
SECURITY_PASSWORD_MIN_LENGTH = int(os.getenv("SECURITY_PASSWORD_MIN_LENGTH", "8"))

# Logging Configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO" if not DEBUG else "DEBUG")
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_FILE = BASE_DIR / "logs" / "bot.log"
LOG_MAX_SIZE = int(os.getenv("LOG_MAX_SIZE", "10"))  # MB
LOG_BACKUP_COUNT = int(os.getenv("LOG_BACKUP_COUNT", "5"))

# Performance Configuration
PERFORMANCE_MAX_WORKERS = int(os.getenv("PERFORMANCE_MAX_WORKERS", "4"))
PERFORMANCE_REQUEST_TIMEOUT = int(os.getenv("PERFORMANCE_REQUEST_TIMEOUT", "30"))
PERFORMANCE_CONNECTION_POOL_SIZE = int(os.getenv("PERFORMANCE_CONNECTION_POOL_SIZE", "10"))

# Notification Configuration
NOTIFICATION_ENABLED = os.getenv("NOTIFICATION_ENABLED", "true").lower() == "true"
NOTIFICATION_TELEGRAM_ADMIN_ID = os.getenv("NOTIFICATION_TELEGRAM_ADMIN_ID", "")
NOTIFICATION_EMAIL_ENABLED = os.getenv("NOTIFICATION_EMAIL_ENABLED", "false").lower() == "true"
NOTIFICATION_EMAIL_SMTP_HOST = os.getenv("NOTIFICATION_EMAIL_SMTP_HOST", "")
NOTIFICATION_EMAIL_SMTP_PORT = int(os.getenv("NOTIFICATION_EMAIL_SMTP_PORT", "587"))
NOTIFICATION_EMAIL_USERNAME = os.getenv("NOTIFICATION_EMAIL_USERNAME", "")
NOTIFICATION_EMAIL_PASSWORD = os.getenv("NOTIFICATION_EMAIL_PASSWORD", "")

# Payment Configuration
PAYMENT_ENABLED = os.getenv("PAYMENT_ENABLED", "true").lower() == "true"
PAYMENT_MIN_AMOUNT = float(os.getenv("PAYMENT_MIN_AMOUNT", "1.0"))
PAYMENT_MAX_AMOUNT = float(os.getenv("PAYMENT_MAX_AMOUNT", "999999.99"))
PAYMENT_CURRENCY = os.getenv("PAYMENT_CURRENCY", "YER")
PAYMENT_COMMISSION_RATE = float(os.getenv("PAYMENT_COMMISSION_RATE", "0.05"))  # 5%

# File Upload Configuration
FILE_UPLOAD_ENABLED = os.getenv("FILE_UPLOAD_ENABLED", "true").lower() == "true"
FILE_UPLOAD_MAX_SIZE = int(os.getenv("FILE_UPLOAD_MAX_SIZE", "10"))  # MB
FILE_UPLOAD_ALLOWED_TYPES = os.getenv("FILE_UPLOAD_ALLOWED_TYPES", "jpg,jpeg,png,pdf,doc,docx").split(",")
FILE_UPLOAD_PATH = BASE_DIR / "uploads"

# API Configuration
API_ENABLED = os.getenv("API_ENABLED", "false").lower() == "true"
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))
API_DEBUG = DEBUG
API_RELOAD = DEBUG

# Monitoring Configuration
MONITORING_ENABLED = os.getenv("MONITORING_ENABLED", "true").lower() == "true"
MONITORING_HEALTH_CHECK_INTERVAL = int(os.getenv("MONITORING_HEALTH_CHECK_INTERVAL", "60"))
MONITORING_METRICS_ENABLED = os.getenv("MONITORING_METRICS_ENABLED", "true").lower() == "true"
MONITORING_ALERT_ENABLED = os.getenv("MONITORING_ALERT_ENABLED", "true").lower() == "true"

# Backup Configuration
BACKUP_ENABLED = os.getenv("BACKUP_ENABLED", "true").lower() == "true"
BACKUP_INTERVAL_HOURS = int(os.getenv("BACKUP_INTERVAL_HOURS", "24"))
BACKUP_RETENTION_DAYS = int(os.getenv("BACKUP_RETENTION_DAYS", "30"))
BACKUP_PATH = BASE_DIR / "backups"

# Feature Flags
FEATURES = {
    "wallet": os.getenv("FEATURE_WALLET", "true").lower() == "true",
    "cards": os.getenv("FEATURE_CARDS", "true").lower() == "true",
    "transactions": os.getenv("FEATURE_TRANSACTIONS", "true").lower() == "true",
    "reports": os.getenv("FEATURE_REPORTS", "true").lower() == "true",
    "commissions": os.getenv("FEATURE_COMMISSIONS", "true").lower() == "true",
    "admin_panel": os.getenv("FEATURE_ADMIN_PANEL", "true").lower() == "true",
    "supplier_panel": os.getenv("FEATURE_SUPPLIER_PANEL", "true").lower() == "true",
    "agent_panel": os.getenv("FEATURE_AGENT_PANEL", "true").lower() == "true",
}

# Emojis and UI Configuration
EMOJIS = {
    "success": "✅",
    "error": "❌",
    "warning": "⚠️",
    "info": "ℹ️",
    "money": "💰",
    "card": "💳",
    "wallet": "👛",
    "user": "👤",
    "admin": "👨‍💼",
    "supplier": "🏪",
    "agent": "👨‍💻",
    "settings": "⚙️",
    "help": "❓",
    "back": "⬅️",
    "next": "➡️",
    "home": "🏠",
    "refresh": "🔄",
    "download": "📥",
    "upload": "📤",
    "search": "🔍",
    "filter": "🔧",
    "sort": "📊",
    "export": "📋",
    "import": "📥",
    "delete": "🗑️",
    "edit": "✏️",
    "add": "➕",
    "remove": "➖",
    "check": "☑️",
    "uncheck": "⬜",
    "star": "⭐",
    "heart": "❤️",
    "fire": "🔥",
    "rocket": "🚀",
    "trophy": "🏆",
    "gift": "🎁",
    "clock": "⏰",
    "calendar": "📅",
    "location": "📍",
    "phone": "📞",
    "email": "📧",
    "link": "🔗",
    "lock": "🔒",
    "unlock": "🔓",
    "shield": "🛡️",
    "key": "🔑",
    "gear": "⚙️",
    "tools": "🛠️",
    "database": "🗄️",
    "server": "🖥️",
    "network": "🌐",
    "cloud": "☁️",
    "mobile": "📱",
    "computer": "💻",
    "printer": "🖨️",
    "camera": "📷",
    "video": "🎥",
    "audio": "🎵",
    "file": "📄",
    "folder": "📁",
    "archive": "📦",
    "package": "📦",
    "box": "📦",
    "bag": "👜",
    "shopping": "🛒",
    "cart": "🛒",
    "receipt": "🧾",
    "invoice": "🧾",
    "contract": "📋",
    "document": "📄",
    "certificate": "📜",
    "diploma": "🎓",
    "book": "📚",
    "newspaper": "📰",
    "magazine": "📖",
    "notebook": "📓",
    "pen": "✒️",
    "pencil": "✏️",
    "marker": "🖍️",
    "crayon": "🖍️",
    "paint": "🎨",
    "brush": "🖌️",
    "palette": "🎨",
    "canvas": "🖼️",
    "frame": "🖼️",
    "picture": "🖼️",
    "photo": "📸",
    "selfie": "🤳",
    "group": "👥",
    "team": "👨‍👩‍👧‍👦",
    "family": "👨‍👩‍👧‍👦",
    "couple": "👫",
    "friends": "👭",
    "business": "💼",
    "meeting": "🤝",
    "handshake": "🤝",
    "agreement": "🤝",
    "partnership": "🤝",
    "collaboration": "🤝",
    "support": "🆘",
    "emergency": "🚨",
    "alert": "🚨",
    "warning": "⚠️",
    "danger": "☠️",
    "poison": "☠️",
    "biohazard": "☣️",
    "radioactive": "☢️",
    "nuclear": "☢️",
    "atomic": "☢️",
    "military": "🎖️",
    "police": "👮",
    "firefighter": "👨‍🚒",
    "ambulance": "🚑",
    "hospital": "🏥",
    "clinic": "🏥",
    "pharmacy": "💊",
    "medicine": "💊",
    "pill": "💊",
    "syringe": "💉",
    "thermometer": "🌡️",
    "stethoscope": "🩺",
    "bandage": "🩹",
    "plaster": "🩹",
    "ointment": "🧴",
    "cream": "🧴",
    "lotion": "🧴",
    "soap": "🧼",
    "shampoo": "🧴",
    "toothpaste": "🪥",
    "toothbrush": "🪥",
    "mirror": "🪞",
    "comb": "🪮",
    "scissors": "✂️",
    "razor": "🪒",
    "tweezers": "🔧",
    "nail_clipper": "✂️",
}

# Quick Commands
QUICK_COMMANDS = {
    "start": "بدء استخدام البوت",
    "help": "عرض المساعدة",
    "status": "حالة النظام",
    "wallet": "إدارة المحفظة",
    "cards": "شراء البطاقات",
    "transactions": "المعاملات",
    "reports": "التقارير",
    "settings": "الإعدادات",
    "profile": "الملف الشخصي",
    "support": "الدعم الفني"
}

# User Roles
USER_ROLES = {
    "user": "مستخدم عادي",
    "agent": "وكيل مبيعات",
    "supplier": "مورد بطاقات",
    "admin": "مدير النظام",
    "super_admin": "مدير عام"
}

# Permissions
PERMISSIONS = {
    "user": ["basic_operations", "view_profile", "manage_wallet", "view_transactions"],
    "agent": ["user_permissions", "view_sales", "view_commissions", "manage_customers"],
    "supplier": ["user_permissions", "manage_cards", "view_supplier_reports", "upload_cards"],
    "admin": ["agent_permissions", "supplier_permissions", "manage_users", "system_admin", "financial_admin"],
    "super_admin": ["admin_permissions", "activate_suppliers", "override_restrictions", "full_access"]
}

# Database Tables
DATABASE_TABLES = [
    "users",
    "user_roles",
    "permissions",
    "wallets",
    "transactions",
    "cards",
    "card_categories",
    "networks",
    "suppliers",
    "agents",
    "commissions",
    "notifications",
    "system_logs",
    "audit_logs",
    "backups",
    "settings"
]

# Validation Rules
VALIDATION_RULES = {
    "phone_number": {
        "pattern": r"^(\+?967|0)?[0-9]{9}$",
        "message": "رقم الهاتف يجب أن يكون بصيغة صحيحة (مثال: +967XXXXXXXXX)"
    },
    "email": {
        "pattern": r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
        "message": "البريد الإلكتروني يجب أن يكون بصيغة صحيحة"
    },
    "amount": {
        "min": 0.01,
        "max": 999999.99,
        "message": "المبلغ يجب أن يكون بين 0.01 و 999,999.99"
    },
    "card_number": {
        "pattern": r"^[0-9]{16,19}$",
        "message": "رقم البطاقة يجب أن يكون 16-19 رقم"
    },
    "username": {
        "min_length": 3,
        "max_length": 30,
        "pattern": r"^[a-zA-Z0-9_]+$",
        "message": "اسم المستخدم يجب أن يكون 3-30 حرف، أحرف وأرقام وشرطة سفلية فقط"
    },
    "password": {
        "min_length": 8,
        "max_length": 128,
        "message": "كلمة المرور يجب أن تكون 8 أحرف على الأقل"
    }
}

# Error Messages
ERROR_MESSAGES = {
    "database_error": "حدث خطأ في قاعدة البيانات. يرجى المحاولة مرة أخرى لاحقاً.",
    "network_error": "حدث خطأ في الاتصال. يرجى التحقق من اتصال الإنترنت والمحاولة مرة أخرى.",
    "permission_denied": "ليس لديك الصلاحية لتنفيذ هذا الإجراء.",
    "validation_error": "البيانات المدخلة غير صحيحة. يرجى التحقق والمحاولة مرة أخرى.",
    "rate_limit_exceeded": "تم تجاوز الحد المسموح من الطلبات. يرجى الانتظار قليلاً.",
    "user_not_found": "المستخدم غير موجود.",
    "insufficient_funds": "رصيد غير كافي.",
    "card_not_found": "البطاقة غير موجودة.",
    "card_already_sold": "البطاقة مباعة بالفعل.",
    "invalid_amount": "مبلغ غير صحيح.",
    "system_error": "حدث خطأ في النظام. يرجى المحاولة مرة أخرى أو التواصل مع الإدارة."
}

# Success Messages
SUCCESS_MESSAGES = {
    "operation_completed": "تم إنجاز العملية بنجاح.",
    "user_created": "تم إنشاء المستخدم بنجاح.",
    "user_updated": "تم تحديث بيانات المستخدم بنجاح.",
    "transaction_completed": "تم إنجاز المعاملة بنجاح.",
    "card_purchased": "تم شراء البطاقة بنجاح.",
    "card_uploaded": "تم رفع البطاقة بنجاح.",
    "payment_received": "تم استلام الدفع بنجاح.",
    "withdrawal_completed": "تم إنجاز السحب بنجاح.",
    "profile_updated": "تم تحديث الملف الشخصي بنجاح.",
    "settings_saved": "تم حفظ الإعدادات بنجاح."
}

# System Messages
SYSTEM_MESSAGES = {
    "welcome": "مرحباً بك في بوت شبكة اليمن المحسن v2.0",
    "maintenance": "النظام في حالة صيانة. يرجى المحاولة لاحقاً.",
    "update_available": "يتوفر تحديث جديد للنظام.",
    "backup_completed": "تم إنجاز النسخة الاحتياطية بنجاح.",
    "system_restart": "سيتم إعادة تشغيل النظام خلال دقائق.",
    "emergency_mode": "النظام في وضع الطوارئ. الوظائف محدودة."
}

def get_setting(key: str, default: Any = None) -> Any:
    """Get configuration setting"""
    return globals().get(key, default)

def get_emoji(name: str) -> str:
    """Get emoji by name"""
    return EMOJIS.get(name, "")

def is_feature_enabled(feature: str) -> bool:
    """Check if feature is enabled"""
    return FEATURES.get(feature, False)

def get_error_message(error_type: str) -> str:
    """Get error message by type"""
    return ERROR_MESSAGES.get(error_type, "حدث خطأ غير متوقع.")

def get_success_message(message_type: str) -> str:
    """Get success message by type"""
    return SUCCESS_MESSAGES.get(message_type, "تم إنجاز العملية بنجاح.")

def get_system_message(message_type: str) -> str:
    """Get system message by type"""
    return SYSTEM_MESSAGES.get(message_type, "")

def validate_configuration() -> bool:
    """Validate configuration settings"""
    required_settings = ["BOT_TOKEN"]
    
    for setting in required_settings:
        if not get_setting(setting):
            logging.error(f"Required setting '{setting}' is missing")
            return False
    
    return True

def setup_logging():
    """Setup logging configuration"""
    # Create logs directory if it doesn't exist
    log_dir = Path(LOG_FILE).parent
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL),
        format=LOG_FORMAT,
        handlers=[
            logging.FileHandler(LOG_FILE, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    
    # Set specific logger levels
    logging.getLogger("telegram").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

# Initialize logging
setup_logging()

# Validate configuration
if not validate_configuration():
    logging.error("Configuration validation failed. Please check your settings.")
    raise ValueError("Invalid configuration")