"""
Conversation states for Yemen Net Bot v2
Defines all conversation states for multi-step interactions
"""

from enum import Enum, auto

class ConversationStates(Enum):
    """Conversation states for the bot"""
    
    # Main menu state
    MAIN_MENU = auto()
    
    # Profile management
    PROFILE_EDIT = auto()
    PROFILE_VIEW = auto()
    
    # Wallet operations
    WALLET_VIEW = auto()
    WALLET_DEPOSIT = auto()
    WALLET_WITHDRAW = auto()
    
    # Transfer operations
    TRANSFER_SELECT_USER = auto()
    TRANSFER_AMOUNT = auto()
    TRANSFER_CONFIRM = auto()
    TRANSFER_COMPLETE = auto()
    
    # Card operations
    CARD_SELECT = auto()
    CARD_PURCHASE = auto()
    CARD_UPLOAD = auto()
    CARD_MANAGE = auto()
    
    # Settings
    SETTINGS_MAIN = auto()
    SETTINGS_NOTIFICATIONS = auto()
    SETTINGS_LANGUAGE = auto()
    SETTINGS_SECURITY = auto()
    
    # Admin operations
    ADMIN_PANEL = auto()
    ADMIN_USERS = auto()
    ADMIN_REPORTS = auto()
    ADMIN_SETTINGS = auto()
    
    # Support
    SUPPORT_MAIN = auto()
    SUPPORT_TICKET = auto()
    SUPPORT_CHAT = auto()
    
    # Payment operations
    PAYMENT_SELECT = auto()
    PAYMENT_AMOUNT = auto()
    PAYMENT_CONFIRM = auto()
    PAYMENT_PROCESSING = auto()
    
    # End conversation
    END = auto()

# State descriptions for debugging
STATE_DESCRIPTIONS = {
    ConversationStates.MAIN_MENU: "القائمة الرئيسية",
    ConversationStates.PROFILE_EDIT: "تعديل الملف الشخصي",
    ConversationStates.PROFILE_VIEW: "عرض الملف الشخصي",
    ConversationStates.WALLET_VIEW: "عرض المحفظة",
    ConversationStates.WALLET_DEPOSIT: "إيداع في المحفظة",
    ConversationStates.WALLET_WITHDRAW: "سحب من المحفظة",
    ConversationStates.TRANSFER_SELECT_USER: "اختيار المستخدم للتحويل",
    ConversationStates.TRANSFER_AMOUNT: "إدخال مبلغ التحويل",
    ConversationStates.TRANSFER_CONFIRM: "تأكيد التحويل",
    ConversationStates.TRANSFER_COMPLETE: "اكتمال التحويل",
    ConversationStates.CARD_SELECT: "اختيار البطاقة",
    ConversationStates.CARD_PURCHASE: "شراء البطاقة",
    ConversationStates.CARD_UPLOAD: "رفع البطاقة",
    ConversationStates.CARD_MANAGE: "إدارة البطاقات",
    ConversationStates.SETTINGS_MAIN: "الإعدادات الرئيسية",
    ConversationStates.SETTINGS_NOTIFICATIONS: "إعدادات الإشعارات",
    ConversationStates.SETTINGS_LANGUAGE: "إعدادات اللغة",
    ConversationStates.SETTINGS_SECURITY: "إعدادات الأمان",
    ConversationStates.ADMIN_PANEL: "لوحة الإدارة",
    ConversationStates.ADMIN_USERS: "إدارة المستخدمين",
    ConversationStates.ADMIN_REPORTS: "التقارير الإدارية",
    ConversationStates.ADMIN_SETTINGS: "إعدادات النظام",
    ConversationStates.SUPPORT_MAIN: "الدعم الفني",
    ConversationStates.SUPPORT_TICKET: "إنشاء تذكرة دعم",
    ConversationStates.SUPPORT_CHAT: "محادثة الدعم",
    ConversationStates.PAYMENT_SELECT: "اختيار طريقة الدفع",
    ConversationStates.PAYMENT_AMOUNT: "إدخال مبلغ الدفع",
    ConversationStates.PAYMENT_CONFIRM: "تأكيد الدفع",
    ConversationStates.PAYMENT_PROCESSING: "معالجة الدفع",
    ConversationStates.END: "إنهاء المحادثة"
}

def get_state_description(state: ConversationStates) -> str:
    """Get human-readable description of a conversation state"""
    return STATE_DESCRIPTIONS.get(state, "حالة غير معروفة")

def is_valid_state(state: ConversationStates) -> bool:
    """Check if a state is valid"""
    return state in ConversationStates

def get_all_states() -> list:
    """Get all available conversation states"""
    return list(ConversationStates)

def get_user_states() -> list:
    """Get states available to regular users"""
    return [
        ConversationStates.MAIN_MENU,
        ConversationStates.PROFILE_EDIT,
        ConversationStates.PROFILE_VIEW,
        ConversationStates.WALLET_VIEW,
        ConversationStates.WALLET_DEPOSIT,
        ConversationStates.WALLET_WITHDRAW,
        ConversationStates.TRANSFER_SELECT_USER,
        ConversationStates.TRANSFER_AMOUNT,
        ConversationStates.TRANSFER_CONFIRM,
        ConversationStates.TRANSFER_COMPLETE,
        ConversationStates.CARD_SELECT,
        ConversationStates.CARD_PURCHASE,
        ConversationStates.CARD_UPLOAD,
        ConversationStates.CARD_MANAGE,
        ConversationStates.SETTINGS_MAIN,
        ConversationStates.SETTINGS_NOTIFICATIONS,
        ConversationStates.SETTINGS_LANGUAGE,
        ConversationStates.SETTINGS_SECURITY,
        ConversationStates.SUPPORT_MAIN,
        ConversationStates.SUPPORT_TICKET,
        ConversationStates.SUPPORT_CHAT,
        ConversationStates.PAYMENT_SELECT,
        ConversationStates.PAYMENT_AMOUNT,
        ConversationStates.PAYMENT_CONFIRM,
        ConversationStates.PAYMENT_PROCESSING
    ]

def get_admin_states() -> list:
    """Get states available to administrators"""
    return [
        ConversationStates.ADMIN_PANEL,
        ConversationStates.ADMIN_USERS,
        ConversationStates.ADMIN_REPORTS,
        ConversationStates.ADMIN_SETTINGS
    ]

def get_payment_states() -> list:
    """Get states related to payment operations"""
    return [
        ConversationStates.PAYMENT_SELECT,
        ConversationStates.PAYMENT_AMOUNT,
        ConversationStates.PAYMENT_CONFIRM,
        ConversationStates.PAYMENT_PROCESSING
    ]

def get_transfer_states() -> list:
    """Get states related to transfer operations"""
    return [
        ConversationStates.TRANSFER_SELECT_USER,
        ConversationStates.TRANSFER_AMOUNT,
        ConversationStates.TRANSFER_CONFIRM,
        ConversationStates.TRANSFER_COMPLETE
    ]