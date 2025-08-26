#!/usr/bin/env python3
"""
Configuration file for Pottagrm Enhanced Bot
Contains all constants, settings, and configurations
UNIFIED VERSION - All configurations are centralized here
"""

import os
from telegram import BotCommand

# =============================================================================
# CORE BOT CONFIGURATION - SINGLE SOURCE OF TRUTH
# =============================================================================

# Bot Token - Single source of truth
BOT_TOKEN = '7766964799:AAHex-hGfjPX6g_R2aZ7-UPrgnFxQKAjSa0'

# Database Configuration
DB_PATH = os.getenv('DB_PATH', os.path.abspath('yemen_net.db'))

# =============================================================================
# ACCOUNTING SYSTEM CONFIGURATION
# =============================================================================

# Account Types
ACCOUNT_TYPE_ASSET = 'asset'
ACCOUNT_TYPE_LIABILITY = 'liability'
ACCOUNT_TYPE_EQUITY = 'equity'
ACCOUNT_TYPE_REVENUE = 'revenue'
ACCOUNT_TYPE_EXPENSE = 'expense'

# Account Codes
ACCOUNT_CODE_ISSUANCE_EXPENSE = '5000'
ACCOUNT_CODE_BOT_COMMISSION_REVENUE = '4100'

# =============================================================================
# BUSINESS RULES CONFIGURATION
# =============================================================================

# Commission Rates
CARD_COMMISSION_RATE = float(os.getenv('CARD_COMMISSION_RATE', '0.10'))
AGENT_COMMISSION_RATE = float(os.getenv('AGENT_COMMISSION_RATE', '0.05'))

# =============================================================================
# BOT COMMANDS MENU - UNIFIED COMMANDS
# =============================================================================

QUICK_COMMANDS = [
    BotCommand('start', '🏠 البداية - القائمة الرئيسية'),
    BotCommand('menu', '📋 القائمة السريعة'),
    BotCommand('wallet', '💳 محفظتي المطورة'),
    BotCommand('buy', '🛒 شراء كروت الشبكة'),
    BotCommand('transfer', '💸 تحويل رصيد لصديق'),
    BotCommand('balance', '💰 عرض الرصيد والمعاملات'),
    BotCommand('reports', '📊 تقاريري الشخصية'),
    BotCommand('ratings', '⭐ تقييماتي ومراجعاتي'),
    BotCommand('notifications', '🔔 إشعاراتي وتنبيهاتي'),
    BotCommand('promotions', '🎁 العروض والخصومات'),
    BotCommand('settings', '⚙️ إعدادات الحساب'),
    BotCommand('invite', '👥 دعوة الأصدقاء'),
    BotCommand('wifi_search', '🔍 البحث عن شبكة واي فاي'),
    BotCommand('send_balance', '💸 إرسال رصيد لصديق'),
    BotCommand('admin', '👑 لوحة الإدارة'),
    BotCommand('help', '❓ المساعدة والدعم'),
    BotCommand('cancel', '❌ إلغاء العملية الحالية'),
]

# =============================================================================
# EMOJIS DICTIONARY - UNIFIED UI ELEMENTS
# =============================================================================

EMOJIS = {
    # Status Emojis
    'success': '✅',
    'error': '❌',
    'warning': '⚠️',
    'info': 'ℹ️',
    'loading': '⏳',
    
    # Action Emojis
    'back': '↩️',
    'cancel': '❌',
    'confirm': '✅',
    'search': '🔍',
    'settings': '⚙️',
    'upload': '📤',
    'download': '📥',
    
    # Business Emojis
    'money': '💰',
    'card': '🎫',
    'wallet': '💳',
    'transfer': '💸',
    'purchase': '🛒',
    'network': '📶',
    
    # User Interface
    'user': '👤',
    'admin': '👑',
    'stats': '📊',
    'home': '🏠',
    
    # Contact & Communication
    'phone': '📱',
    'email': '📧',
    'id': '🆔',
    
    # Time & Date
    'time': '⏰',
    'date': '📅',
    
    # Rating & Status
    'star': '⭐',
    'fire': '🔥',
    'new': '🆕',
    'hot': '🔥',
    'cool': '😎'
}

# =============================================================================
# CONVERSATION STATES - UNIFIED STATE MANAGEMENT
# =============================================================================

# Basic registration states
GET_FULL_NAME, GET_PHONE, CHOOSE_ROLE = range(3)

# Purchase flow states
SELECT_NETWORK, SELECT_CATEGORY, CONFIRM_PURCHASE = range(3, 6)

# Transfer flow states
TRANSFER_TARGET, TRANSFER_AMOUNT, TRANSFER_CONFIRM = range(6, 9)

# =============================================================================
# USER ROLES & PERMISSIONS - UNIFIED ACCESS CONTROL
# =============================================================================

# User Roles - Single source of truth
USER_ROLES = {
    'customer': 'عميل',
    'agent': 'وكيل',
    'supplier': 'مزود',
    'admin': 'مشرف',
    'super_admin': 'مشرف أعلى'
}

# Permissions System
PERMISSIONS = {
    'create_users': 'إنشاء مستخدمين',
    'manage_balance': 'إدارة الأرصدة',
    'approve_suppliers': 'الموافقة على المزودين',
    'view_reports': 'عرض التقارير',
    'manage_promotions': 'إدارة العروض',
    'system_admin': 'إدارة النظام'
}

# =============================================================================
# OPTIONAL LIBRARIES DETECTION - UNIFIED FEATURE FLAGS
# =============================================================================

# Initialize availability flags
AIOFILES_AVAILABLE = False
PANDAS_AVAILABLE = False
PLOTTING_AVAILABLE = False
IMAGE_AVAILABLE = False
CRYPTO_AVAILABLE = False

# Cryptography
try:
    from cryptography.fernet import Fernet
    CRYPTO_AVAILABLE = True
except ImportError:
    Fernet = None
    CRYPTO_AVAILABLE = False

# Async File Operations
try:
    import aiofiles
    AIOFILES_AVAILABLE = True
except ImportError:
    AIOFILES_AVAILABLE = False

# Data Analysis
try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

# Plotting
try:
    import matplotlib.pyplot as plt
    import seaborn as sns
    PLOTTING_AVAILABLE = True
except ImportError:
    PLOTTING_AVAILABLE = False

# Image Processing
try:
    from PIL import Image
    import qrcode
    IMAGE_AVAILABLE = True
except ImportError:
    IMAGE_AVAILABLE = False

# =============================================================================
# LOGGING CONFIGURATION
# =============================================================================

# Logging levels and formats
LOGGING_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOGGING_LEVEL = 'INFO'

# =============================================================================
# FEATURE FLAGS - UNIFIED FEATURE CONTROL
# =============================================================================

# Enable/Disable features based on available libraries
FEATURES = {
    'advanced_analytics': PANDAS_AVAILABLE and PLOTTING_AVAILABLE,
    'image_processing': IMAGE_AVAILABLE,
    'encryption': CRYPTO_AVAILABLE,
    'async_file_ops': AIOFILES_AVAILABLE,
    'qr_codes': IMAGE_AVAILABLE,
}