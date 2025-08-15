#!/usr/bin/env python3
"""
Configuration file for Pottagrm Enhanced Bot
Contains all constants, settings, and configurations
"""

import os
from telegram import BotCommand

# Bot configuration
BOT_TOKEN = '7766964799:AAHex-hGfjPX6g_R2aZ7-UPrgnFxQKAjSa0'
DB_PATH = os.getenv('DB_PATH', os.path.abspath('yemen_net.db'))

# Accounting constants
ACCOUNT_TYPE_ASSET = 'asset'
ACCOUNT_TYPE_LIABILITY = 'liability'
ACCOUNT_TYPE_EQUITY = 'equity'
ACCOUNT_TYPE_REVENUE = 'revenue'
ACCOUNT_TYPE_EXPENSE = 'expense'
ACCOUNT_CODE_ISSUANCE_EXPENSE = '5000'
ACCOUNT_CODE_BOT_COMMISSION_REVENUE = '4100'

# Business configuration
CARD_COMMISSION_RATE = float(os.getenv('CARD_COMMISSION_RATE', '0.10'))
AGENT_COMMISSION_RATE = float(os.getenv('AGENT_COMMISSION_RATE', '0.05'))

# Enhanced Bot command menu
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

# Emojis for better UI
EMOJIS = {
    'success': '✅',
    'error': '❌',
    'warning': '⚠️',
    'loading': '⏳',
    'money': '💰',
    'card': '🎫',
    'network': '📶',
    'user': '👤',
    'admin': '👑',
    'stats': '📊',
    'home': '🏠',
    'back': '↩️',
    'cancel': '❌',
    'confirm': '✅',
    'search': '🔍',
    'settings': '⚙️',
    'wallet': '💳',
    'transfer': '💸',
    'purchase': '🛒',
    'upload': '📤',
    'download': '📥',
    'phone': '📱',
    'email': '📧',
    'id': '🆔',
    'time': '⏰',
    'date': '📅',
    'star': '⭐',
    'fire': '🔥',
    'new': '🆕',
    'hot': '🔥',
    'cool': '😎'
}

# Conversation states
GET_FULL_NAME, GET_PHONE, CHOOSE_ROLE = range(3)
SELECT_NETWORK, SELECT_CATEGORY, CONFIRM_PURCHASE = range(3, 6)
TRANSFER_TARGET, TRANSFER_AMOUNT, TRANSFER_CONFIRM = range(6, 9)

# User roles
USER_ROLES = {
    'customer': 'عميل',
    'agent': 'وكيل',
    'supplier': 'مزود',
    'admin': 'مشرف',
    'super_admin': 'مشرف أعلى'
}

# Permissions
PERMISSIONS = {
    'create_users': 'إنشاء مستخدمين',
    'manage_balance': 'إدارة الأرصدة',
    'approve_suppliers': 'الموافقة على المزودين',
    'view_reports': 'عرض التقارير',
    'manage_promotions': 'إدارة العروض',
    'system_admin': 'إدارة النظام'
}

# Available imports tracking
AIOFILES_AVAILABLE = False
PANDAS_AVAILABLE = False
PLOTTING_AVAILABLE = False
IMAGE_AVAILABLE = False
CRYPTO_AVAILABLE = False

# Try to import optional libraries
try:
    import aiofiles
    AIOFILES_AVAILABLE = True
except ImportError:
    pass

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    pass

try:
    import matplotlib.pyplot as plt
    import seaborn as sns
    PLOTTING_AVAILABLE = True
except ImportError:
    pass

try:
    from PIL import Image
    import qrcode
    IMAGE_AVAILABLE = True
except ImportError:
    pass

try:
    from cryptography.fernet import Fernet
    CRYPTO_AVAILABLE = True
except ImportError:
    Fernet = None