"""
إعدادات البوت والثوابت
"""

import os
from typing import List
from telegram import BotCommand

# معلومات البوت
BOT_TOKEN = os.getenv('BOT_TOKEN')
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN environment variable is required")

# إعدادات قاعدة البيانات  
DB_PATH = os.getenv('DB_PATH', os.path.abspath('yemen_net.db'))

# إعدادات المحاسبة
ACCOUNT_TYPE_ASSET = 'asset'
ACCOUNT_TYPE_LIABILITY = 'liability'
ACCOUNT_TYPE_EQUITY = 'equity'
ACCOUNT_TYPE_REVENUE = 'revenue'
ACCOUNT_TYPE_EXPENSE = 'expense'
ACCOUNT_CODE_ISSUANCE_EXPENSE = '5000'
ACCOUNT_CODE_BOT_COMMISSION_REVENUE = '4100'

# إعدادات العمولات
CARD_COMMISSION_RATE = float(os.getenv('CARD_COMMISSION_RATE', '0.10'))
AGENT_COMMISSION_RATE = float(os.getenv('AGENT_COMMISSION_RATE', '0.05'))

# أوامر القائمة السريعة
QUICK_COMMANDS: List[BotCommand] = [
    BotCommand('menu', 'فتح القائمة الرئيسية'),
    BotCommand('balance', 'عرض الرصيد'),
    BotCommand('buy', 'شراء كرت'),
    BotCommand('transfer', 'تحويل إلى محفظة'),
    BotCommand('stats', 'إحصائياتي'),
    BotCommand('rating', 'تقييم الخدمة'),
    BotCommand('wallet', 'المحفظة الإلكترونية'),
]

# إعدادات التشفير
ENCRYPTION_KEY_ENV = 'ENCRYPTION_KEY_B64'
ENCRYPTION_KEY_FILE = 'encryption.key'

# إعدادات الإشعارات
ENABLE_PUSH_NOTIFICATIONS = True
NOTIFICATION_CHANNELS = {
    'general': '@yemen_net_notifications',
    'admin': '@yemen_net_admin'
}

# إعدادات النظام المالي
MIN_TRANSFER_AMOUNT = 1.0
MAX_TRANSFER_AMOUNT = 10000.0
MIN_WITHDRAWAL_AMOUNT = 10.0
REFERRAL_BONUS_AMOUNT = 5.0

# إعدادات التقييم
MAX_RATING_STARS = 5
MIN_RATING_STARS = 1