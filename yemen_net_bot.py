import logging
import sqlite3
import uuid
import csv
import io
import re
import os
import random
from typing import Optional
from cryptography.fernet import Fernet
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    BotCommand,
    MenuButtonCommands,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackContext,
    CallbackQueryHandler,
    ConversationHandler,
    PicklePersistence,
    filters,
)
from dotenv import load_dotenv

# Load env
load_dotenv()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

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

# Quick menu commands
QUICK_COMMANDS = [
    BotCommand('menu', 'فتح القائمة الرئيسية'),
    BotCommand('balance', 'عرض الرصيد'),
    BotCommand('buy', 'شراء كرت'),
    BotCommand('transfer', 'تحويل إلى محفظة'),
    BotCommand('stats', 'إحصائياتي'),
]

# Encryption

def _load_cipher_suite() -> Fernet:
    key_b64: Optional[str] = os.getenv('ENCRYPTION_KEY_B64')
    if key_b64 and key_b64.strip():
        key_bytes = key_b64.strip().encode()
    else:
        key_file = os.path.abspath('encryption.key')
        if os.path.exists(key_file):
            with open(key_file, 'rb') as f:
                key_bytes = f.read().strip()
        else:
            key_bytes = Fernet.generate_key()
            with open(key_file, 'wb') as f:
                f.write(key_bytes)
            logger.warning('Generated new encryption.key (development only). Set ENCRYPTION_KEY_B64 in production.')
    return Fernet(key_bytes)  # type: ignore[arg-type]

cipher_suite = _load_cipher_suite()

def encrypt_data(data: str) -> str:
    return cipher_suite.encrypt(data.encode()).decode()

def decrypt_data(encrypted_data: str) -> str:
    return cipher_suite.decrypt(encrypted_data.encode()).decode()

# DB helpers

def get_db_connection():
    return sqlite3.connect(DB_PATH)


def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        '''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER UNIQUE NOT NULL,
            full_name TEXT NOT NULL,
            phone TEXT UNIQUE NOT NULL,
            role TEXT NOT NULL,
            balance REAL DEFAULT 0.0,
            invite_code TEXT UNIQUE,
            is_active BOOLEAN DEFAULT 0,
            bank_account TEXT,
            total_referrals INTEGER DEFAULT 0,
            referral_bonus REAL DEFAULT 0.0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            wallet_number TEXT UNIQUE
        )
        '''
    )

    # Migration: add wallet_number if missing
    try:
        cursor.execute('ALTER TABLE users ADD COLUMN wallet_number TEXT UNIQUE')
    except sqlite3.OperationalError:
        pass

    # Backfill missing wallet numbers
    cursor.execute("SELECT id FROM users WHERE wallet_number IS NULL OR wallet_number = ''")
    missing = [row[0] for row in cursor.fetchall()]
    for user_id in missing:
        for _ in range(20):
            trial = '79' + ''.join(str(random.randint(0, 9)) for _ in range(7))
            cursor.execute('SELECT 1 FROM users WHERE wallet_number = ?', (trial,))
            if not cursor.fetchone():
                cursor.execute('UPDATE users SET wallet_number = ? WHERE id = ?', (trial, user_id))
                break

    cursor.execute(
        '''
        CREATE TABLE IF NOT EXISTS networks (
            id TEXT PRIMARY KEY,
            supplier_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            city TEXT NOT NULL,
            is_active BOOLEAN DEFAULT 1,
            FOREIGN KEY(supplier_id) REFERENCES users(id)
        )
        '''
    )

    cursor.execute(
        '''
        CREATE TABLE IF NOT EXISTS card_categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            network_id TEXT NOT NULL,
            value REAL NOT NULL,
            price REAL NOT NULL,
            is_available BOOLEAN DEFAULT 1,
            FOREIGN KEY(network_id) REFERENCES networks(id)
        )
        '''
    )

    cursor.execute(
        '''
        CREATE TABLE IF NOT EXISTS cards (
            id TEXT PRIMARY KEY,
            category_id INTEGER NOT NULL,
            code TEXT NOT NULL,
            is_used BOOLEAN DEFAULT 0,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(category_id) REFERENCES card_categories(id)
        )
        '''
    )

    cursor.execute(
        '''
        CREATE TABLE IF NOT EXISTS transactions (
            id TEXT PRIMARY KEY,
            from_user INTEGER,
            to_user INTEGER,
            amount REAL NOT NULL,
            type TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            reference_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_withdrawable BOOLEAN DEFAULT 0,
            FOREIGN KEY(from_user) REFERENCES users(id),
            FOREIGN KEY(to_user) REFERENCES users(id)
        )
        '''
    )

    cursor.execute(
        '''
        CREATE TABLE IF NOT EXISTS withdrawal_requests (
            id TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            status TEXT DEFAULT 'pending',
            request_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            approval_time TIMESTAMP,
            admin_id INTEGER,
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(admin_id) REFERENCES users(id)
        )
        '''
    )

    cursor.execute(
        '''
        CREATE TABLE IF NOT EXISTS referrals (
            id TEXT PRIMARY KEY,
            referrer_id INTEGER NOT NULL,
            referred_id INTEGER NOT NULL,
            bonus_amount REAL,
            awarded BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(referrer_id) REFERENCES users(id),
            FOREIGN KEY(referred_id) REFERENCES users(id)
        )
        '''
    )

    # Accounting
    cursor.execute(
        '''
        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE,
            name TEXT NOT NULL,
            type TEXT NOT NULL,
            parent_id INTEGER,
            is_active BOOLEAN DEFAULT 1
        )
        '''
    )
    cursor.execute(
        '''
        CREATE TABLE IF NOT EXISTS user_accounts (
            user_id INTEGER UNIQUE NOT NULL,
            account_id INTEGER NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(account_id) REFERENCES accounts(id)
        )
        '''
    )
    cursor.execute(
        '''
        CREATE TABLE IF NOT EXISTS journal_entries (
            id TEXT PRIMARY KEY,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_by INTEGER
        )
        '''
    )
    cursor.execute(
        '''
        CREATE TABLE IF NOT EXISTS journal_lines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entry_id TEXT NOT NULL,
            account_id INTEGER NOT NULL,
            debit REAL DEFAULT 0.0,
            credit REAL DEFAULT 0.0,
            user_id INTEGER,
            ref_type TEXT,
            ref_id TEXT,
            FOREIGN KEY(entry_id) REFERENCES journal_entries(id),
            FOREIGN KEY(account_id) REFERENCES accounts(id)
        )
        '''
    )

    ensure_base_accounts(cursor)

    conn.commit()
    conn.close()


def ensure_base_accounts(cursor: sqlite3.Cursor) -> None:
    cursor.execute('SELECT id FROM accounts WHERE code = ?', (ACCOUNT_CODE_ISSUANCE_EXPENSE,))
    if not cursor.fetchone():
        cursor.execute(
            'INSERT INTO accounts (code, name, type) VALUES (?, ?, ?)',
            (ACCOUNT_CODE_ISSUANCE_EXPENSE, 'Issuance Expense', ACCOUNT_TYPE_EXPENSE),
        )
    cursor.execute('SELECT id FROM accounts WHERE code = ?', (ACCOUNT_CODE_BOT_COMMISSION_REVENUE,))
    if not cursor.fetchone():
        cursor.execute(
            'INSERT INTO accounts (code, name, type) VALUES (?, ?, ?)',
            (ACCOUNT_CODE_BOT_COMMISSION_REVENUE, 'Bot Commission Revenue', ACCOUNT_TYPE_REVENUE),
        )


def get_or_create_user_wallet_account(cursor: sqlite3.Cursor, user_id: int) -> int:
    cursor.execute('SELECT account_id FROM user_accounts WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()
    if row:
        return row[0]
    code = f'2{user_id:06d}'
    name = f'User Wallet #{user_id}'
    cursor.execute('INSERT INTO accounts (code, name, type) VALUES (?, ?, ?)', (code, name, ACCOUNT_TYPE_LIABILITY))
    account_id = cursor.lastrowid
    cursor.execute('INSERT INTO user_accounts (user_id, account_id) VALUES (?, ?)', (user_id, account_id))
    return account_id


def post_journal(description: str, created_by: Optional[int], lines: list[dict]) -> str:
    total_debit = round(sum(l.get('debit', 0.0) for l in lines), 2)
    total_credit = round(sum(l.get('credit', 0.0) for l in lines), 2)
    if abs(total_debit - total_credit) > 0.0001:
        raise ValueError('Unbalanced journal entry')
    conn = get_db_connection()
    cursor = conn.cursor()
    entry_id = str(uuid.uuid4())
    cursor.execute('INSERT INTO journal_entries (id, description, created_by) VALUES (?, ?, ?)', (entry_id, description, created_by))
    for l in lines:
        cursor.execute(
            'INSERT INTO journal_lines (entry_id, account_id, debit, credit, user_id, ref_type, ref_id) VALUES (?, ?, ?, ?, ?, ?, ?)',
            (
                entry_id,
                l['account_id'],
                float(l.get('debit', 0.0) or 0.0),
                float(l.get('credit', 0.0) or 0.0),
                l.get('user_id'),
                l.get('ref_type'),
                l.get('ref_id'),
            ),
        )
    conn.commit()
    conn.close()
    return entry_id


def get_user_ledger_balance(user_id: int) -> float:
    conn = get_db_connection()
    cursor = conn.cursor()
    account_id = get_or_create_user_wallet_account(cursor, user_id)
    cursor.execute('SELECT COALESCE(SUM(credit - debit), 0) FROM journal_lines WHERE account_id = ?', (account_id,))
    bal = cursor.fetchone()[0] or 0.0
    conn.close()
    return round(bal, 2)


def recalc_and_set_user_balance(user_id: int) -> float:
    bal = get_user_ledger_balance(user_id)
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET balance = ? WHERE id = ?', (bal, user_id))
    conn.commit()
    conn.close()
    return bal


def issue_balance_to_user(super_admin_id: int, target_user_id: int, amount: float, note: str = '') -> str:
    if amount <= 0:
        raise ValueError('Amount must be positive')
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM accounts WHERE code = ?', (ACCOUNT_CODE_ISSUANCE_EXPENSE,))
    row = cursor.fetchone()
    if not row:
        ensure_base_accounts(cursor)
        cursor.execute('SELECT id FROM accounts WHERE code = ?', (ACCOUNT_CODE_ISSUANCE_EXPENSE,))
        row = cursor.fetchone()
    issuance_acc_id = row[0]
    wallet_acc_id = get_or_create_user_wallet_account(cursor, target_user_id)
    conn.commit()
    conn.close()
    entry_id = post_journal(
        description=f'Issuance to user {target_user_id}. {note}',
        created_by=super_admin_id,
        lines=[
            {'account_id': issuance_acc_id, 'debit': amount, 'credit': 0.0, 'user_id': None, 'ref_type': 'issuance', 'ref_id': str(target_user_id)},
            {'account_id': wallet_acc_id, 'debit': 0.0, 'credit': amount, 'user_id': target_user_id, 'ref_type': 'issuance', 'ref_id': str(target_user_id)},
        ],
    )
    recalc_and_set_user_balance(target_user_id)
    return entry_id

# Simple DB functions (legacy balance kept for display caching)

def create_user(telegram_id, full_name, phone, role='customer', is_active=False):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        invite_code = str(uuid.uuid4())[:8].upper()
        # Generate wallet number: 9 digits, starts with 79
        wallet_number = None
        for _ in range(10):
            trial = '79' + ''.join(str(random.randint(0, 9)) for _ in range(7))
            cursor.execute('SELECT 1 FROM users WHERE wallet_number = ?', (trial,))
            if not cursor.fetchone():
                wallet_number = trial
                break
        if not wallet_number:
            raise RuntimeError('Failed to generate wallet number')
        cursor.execute(
            'INSERT INTO users (telegram_id, full_name, phone, role, invite_code, is_active, wallet_number) VALUES (?, ?, ?, ?, ?, ?, ?)',
            (telegram_id, full_name, phone, role, invite_code, 1 if role == 'customer' else (1 if is_active else 0), wallet_number),
        )
        conn.commit()
        return cursor.lastrowid
    except sqlite3.IntegrityError as e:
        logger.error(f'Error creating user: {e}')
        return None
    finally:
        conn.close()


def _row_to_dict(cursor, row):
    if row is None:
        return None
    columns = [col[0] for col in cursor.description]
    return dict(zip(columns, row))


def get_user(telegram_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE telegram_id = ?', (telegram_id,))
    row = cursor.fetchone()
    user = _row_to_dict(cursor, row)
    conn.close()
    return user


def get_user_by_phone(phone):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE phone = ?', (phone,))
    row = cursor.fetchone()
    user = _row_to_dict(cursor, row)
    conn.close()
    return user


def get_user_by_wallet(wallet_number: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE wallet_number = ?', (wallet_number,))
    row = cursor.fetchone()
    user = _row_to_dict(cursor, row)
    conn.close()
    return user


def get_user_by_id(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
    row = cursor.fetchone()
    user = _row_to_dict(cursor, row)
    conn.close()
    return user


def update_user_balance(user_id, amount):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET balance = balance + ? WHERE id = ?', (amount, user_id))
    conn.commit()
    conn.close()


def create_transaction(from_user_id, to_user_id, amount, txn_type, reference_id=None, is_withdrawable=False):
    conn = get_db_connection()
    cursor = conn.cursor()
    txn_id = str(uuid.uuid4())
    cursor.execute(
        'INSERT INTO transactions (id, from_user, to_user, amount, type, reference_id, is_withdrawable) VALUES (?, ?, ?, ?, ?, ?, ?)',
        (txn_id, from_user_id, to_user_id, amount, txn_type, reference_id, 1 if is_withdrawable else 0),
    )
    conn.commit()
    conn.close()
    return txn_id

# Super admin

def setup_super_admin():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE telegram_id = ?', (7684780523,))
    admin = cursor.fetchone()
    if not admin:
        cursor.execute(
            'INSERT INTO users (telegram_id, full_name, phone, role, is_active, invite_code) VALUES (?, ?, ?, ?, ?, ?)',
            (7684780523, 'Master 👾', '000000000', 'super_admin', 1, 'ADMIN123'),
        )
        conn.commit()
        logger.info('تم إضافة المشرف الأعلى بنجاح')
    conn.close()

# Conversation states
(
    GET_FULL_NAME, GET_PHONE, CHOOSE_ROLE,
    SUPPLIER_MENU, AGENT_MENU, ADMIN_MENU, SUPER_ADMIN_MENU,
    UPLOAD_CARDS, CONFIRM_UPLOAD, SELECT_NETWORK, SELECT_CATEGORY, CONFIRM_PURCHASE,
    SELECT_CUSTOMER, GET_RECHARGE_AMOUNT, CONFIRM_RECHARGE,
    GET_WITHDRAW_AMOUNT, CONFIRM_WITHDRAWAL,
    ADMIN_ACTIVATE_ACCOUNTS,
    ISSUE_TARGET, ISSUE_AMOUNT, ISSUE_CONFIRM,
    # New states
    PASTE_CARDS,
    TRANSFER_TARGET, TRANSFER_AMOUNT, TRANSFER_CONFIRM,
) = range(25)

# Handlers
async def start(update: Update, context: CallbackContext) -> int:
    user = get_user(update.message.from_user.id)
    if user:
        role = user['role']
        if role == 'supplier':
            return await supplier_menu(update, context)
        elif role == 'agent':
            return await agent_menu(update, context)
        elif role == 'admin':
            return await admin_menu(update, context)
        elif role == 'super_admin':
            return await super_admin_menu(update, context)
        else:
            return await customer_menu(update, context)
    if context.args and context.args[0].startswith('ref_'):
        context.user_data['referral_code'] = context.args[0][4:]
    await update.message.reply_text('مرحباً بك في بوت كروت الإنترنت اليمني! 📶\nالرجاء إدخال الاسم الرباعي:', reply_markup=ReplyKeyboardRemove())
    return GET_FULL_NAME

async def get_full_name(update: Update, context: CallbackContext) -> int:
    full_name = update.message.text.strip()
    if len(full_name.split()) < 4:
        await update.message.reply_text('⚠️ الرجاء إدخال اسم رباعي كامل (أربعة أجزاء على الأقل)')
        return GET_FULL_NAME
    context.user_data['full_name'] = full_name
    await update.message.reply_text(
        '📱 الرجاء إدخال رقم هاتفك (9 أرقام بدون الصفر الأول):',
        reply_markup=ReplyKeyboardMarkup([
            ['711234567', '733456789', '755678901'],
            ['777890123', '799012345'],
        ], one_time_keyboard=True, resize_keyboard=True),
    )
    return GET_PHONE

async def get_phone(update: Update, context: CallbackContext) -> int:
    phone = update.message.text.strip()
    if not re.fullmatch(r'\d{9}', phone):
        await update.message.reply_text('⚠️ رقم الهاتف غير صحيح! الرجاء إدخال 9 أرقام (بدون الصفر الأول)')
        return GET_PHONE
    if get_user_by_phone(phone):
        await update.message.reply_text('⚠️ رقم الهاتف مسجل مسبقاً! الرجاء استخدام رقم آخر.')
        return GET_PHONE
    context.user_data['phone'] = phone
    await update.message.reply_text('👤 اختر دورك:', reply_markup=ReplyKeyboardMarkup([["عميل", "وكيل", "مزود"]], one_time_keyboard=True, resize_keyboard=True))
    return CHOOSE_ROLE

async def choose_role(update: Update, context: CallbackContext) -> int:
    role_choice = update.message.text
    role_map = {'عميل': 'customer', 'وكيل': 'agent', 'مزود': 'supplier'}
    if role_choice not in role_map:
        await update.message.reply_text('⚠️ اختيار غير صحيح! الرجاء الاختيار من القائمة.', reply_markup=ReplyKeyboardMarkup([["عميل", "وكيل", "مزود"]], one_time_keyboard=True, resize_keyboard=True))
        return CHOOSE_ROLE
    role = role_map[role_choice]
    full_name = context.user_data['full_name']
    phone = context.user_data['phone']
    telegram_id = update.message.from_user.id
    is_active = True if role == 'customer' else False
    user_id = create_user(telegram_id, full_name, phone, role, is_active)
    if not user_id:
        await update.message.reply_text('❌ حدث خطأ أثناء التسجيل! الرجاء المحاولة لاحقاً.')
        return ConversationHandler.END
    referral_code = context.user_data.get('referral_code')
    if referral_code:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM users WHERE invite_code = ?', (referral_code,))
        referrer = cursor.fetchone()
        if referrer:
            referrer_id = referrer[0]
            cursor.execute('INSERT INTO referrals (id, referrer_id, referred_id) VALUES (?, ?, ?)', (str(uuid.uuid4()), referrer_id, user_id))
            conn.commit()
            await update.message.reply_text(f'🎉 تم تسجيلك بدعوة من المستخدم {referrer_id}!')
        conn.close()
    await update.message.reply_text(f'✅ تم تسجيلك بنجاح كـ {role_choice}!')
    if role in ['agent', 'supplier']:
        await update.message.reply_text('⏳ سيتصل بك المشرف لتفعيل حسابك خلال 24 ساعة.')
        await notify_admins(context, f'📬 طلب تفعيل حساب جديد:\n👤 الاسم: {full_name}\n📱 الهاتف: {phone}\n🎯 الدور: {role_choice}\n🆔 الرابط: t.me/Vsjsgshh_bot?start=user_{telegram_id}')
    user = get_user(telegram_id)
    await update.message.reply_text(
        f"📨 رابط دعوتك: https://t.me/Vsjsgshh_bot?start=ref_{user.get('invite_code')}\n"
        '💰 احصل على 10% من أول شحن لأصدقائك!',
        reply_markup=ReplyKeyboardRemove(),
    )
    return await show_main_menu(update, context, role)

async def cancel(update: Update, context: CallbackContext) -> int:
    await update.message.reply_text('تم إلغاء العملية.', reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

async def show_main_menu(update: Update, context: CallbackContext, role: str):
    if role == 'customer':
        return await customer_menu(update, context)
    if role == 'supplier':
        return await supplier_menu(update, context)
    if role == 'agent':
        return await agent_menu(update, context)
    if role == 'admin':
        return await admin_menu(update, context)
    if role == 'super_admin':
        return await super_admin_menu(update, context)
    return ConversationHandler.END

async def customer_menu(update: Update, context: CallbackContext) -> int:
    user = get_user(update.effective_user.id)
    if not user:
        return await start(update, context)
    recalc_and_set_user_balance(user['id'])
    user = get_user(update.effective_user.id)
    keyboard = [
        [InlineKeyboardButton('🛒 شراء كروت إنترنت', callback_data='buy_cards')],
        [InlineKeyboardButton('💰 شحن رصيد', callback_data='recharge_balance')],
        [InlineKeyboardButton('👥 تحويل لصديق', callback_data='transfer_to_friend')],
        [InlineKeyboardButton('📨 دعوة أصدقاء', callback_data='invite_friends')],
        [InlineKeyboardButton('📜 سجل المعاملات', callback_data='transaction_history')],
        [InlineKeyboardButton('🆘 المساعدة', callback_data='customer_help')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = (
        f"👋 مرحباً بك {user['full_name']}!\n"
        f"💳 رصيدك الحالي: {user['balance']:.2f} ريال\n"
        '📱 اختر من القائمة:'
    )
    if update.message:
        await update.message.reply_text(text, reply_markup=reply_markup)
    else:
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup)
    return ConversationHandler.END

async def _ensure_supplier_network(cursor: sqlite3.Cursor, supplier_user_id: int) -> str:
    cursor.execute('SELECT id FROM networks WHERE supplier_id = ?', (supplier_user_id,))
    row = cursor.fetchone()
    if row:
        return row[0]
    network_id = str(uuid.uuid4())
    cursor.execute('INSERT INTO networks (id, supplier_id, name, city) VALUES (?, ?, ?, ?)', (network_id, supplier_user_id, 'شبكة المزود', 'غير محدد'))
    return network_id

async def supplier_menu(update: Update, context: CallbackContext) -> int:
    user = get_user(update.effective_user.id)
    if not user or not user['is_active']:
        if update.message:
            await update.message.reply_text('⚠️ حسابك غير مفعل! الرجاء الانتظار حتى التفعيل من المشرف.')
        else:
            await update.callback_query.edit_message_text('⚠️ حسابك غير مفعل! الرجاء الانتظار حتى التفعيل من المشرف.')
        return ConversationHandler.END
    keyboard = [
        [InlineKeyboardButton('📤 رفع كروت جديدة', callback_data='upload_cards')],
        [InlineKeyboardButton('📝 لصق أكواد يدويًا', callback_data='paste_cards')],
        [InlineKeyboardButton('📊 إدارة المخزون', callback_data='manage_inventory')],
        [InlineKeyboardButton('💸 سحب الأرباح', callback_data='withdraw_earnings')],
        [InlineKeyboardButton('📈 سجل المبيعات', callback_data='sales_history')],
        [InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = '👨‍💼 لوحة تحكم المزود\nاختر الإجراء المطلوب:'
    if update.message:
        await update.message.reply_text(text, reply_markup=reply_markup)
    else:
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup)
    return SUPPLIER_MENU

async def agent_menu(update: Update, context: CallbackContext) -> int:
    user = get_user(update.effective_user.id)
    if not user or not user['is_active']:
        if update.message:
            await update.message.reply_text('⚠️ حسابك غير مفعل! الرجاء الانتظار حتى التفعيل من المشرف.')
        else:
            await update.callback_query.edit_message_text('⚠️ حسابك غير مفعل! الرجاء الانتظار حتى التفعيل من المشرف.')
        return ConversationHandler.END
    keyboard = [
        [InlineKeyboardButton('🔋 شحن عملاء', callback_data='recharge_customers')],
        [InlineKeyboardButton('🛒 شراء كروت للعملاء', callback_data='buy_for_customers')],
        [InlineKeyboardButton('💳 سحب الأرباح', callback_data='agent_withdraw')],
        [InlineKeyboardButton('📊 سجل العمولات', callback_data='commission_history')],
        [InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = '👨‍💼 لوحة تحكم الوكيل\nاختر الإجراء المطلوب:'
    if update.message:
        await update.message.reply_text(text, reply_markup=reply_markup)
    else:
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup)
    return AGENT_MENU

async def admin_menu(update: Update, context: CallbackContext) -> int:
    keyboard = [
        [InlineKeyboardButton('👤 تفعيل حسابات', callback_data='activate_accounts')],
        [InlineKeyboardButton('🔍 مراقبة التحويلات', callback_data='monitor_transactions')],
        [InlineKeyboardButton('💼 طلبات السحب', callback_data='withdrawal_requests')],
        [InlineKeyboardButton('📊 التقارير الإدارية', callback_data='admin_reports')],
        [InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = '👑 لوحة تحكم المشرف\nاختر الإجراء المطلوب:'
    if update.message:
        await update.message.reply_text(text, reply_markup=reply_markup)
    else:
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup)
    return ADMIN_MENU

async def super_admin_menu(update: Update, context: CallbackContext) -> int:
    keyboard = [
        [InlineKeyboardButton('👑 إدارة المشرفين', callback_data='manage_admins')],
        [InlineKeyboardButton('⚙️ إعدادات النظام', callback_data='system_settings')],
        [InlineKeyboardButton('💾 النسخ الاحتياطي', callback_data='backup_database')],
        [InlineKeyboardButton('📈 التقارير الشاملة', callback_data='global_reports')],
        [InlineKeyboardButton('➕ إنشاء رصيد', callback_data='issue_balance')],
        [InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = '👑 لوحة تحكم المشرف الأعلى\nاختر الإجراء المطلوب:'
    if update.message:
        await update.message.reply_text(text, reply_markup=reply_markup)
    else:
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup)
    return SUPER_ADMIN_MENU

async def main_menu(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    await query.answer()
    user = get_user(query.from_user.id)
    if user:
        return await show_main_menu(update, context, user['role'])
    return await start(update, context)

# Cards flow
async def upload_cards(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        '📤 لرفك كروت جديدة:\n'
        '1. أعد ملف CSV بالتنسيق التالي:\n'
        '   card_code,value,price,expiration_date\n'
        '   مثال: ABC123,10000,9500,2025-12-31\n'
        '2. أرسل الملف الآن\n\n'
        '❌ /cancel للإلغاء',
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('❌ إلغاء', callback_data='cancel_upload')]]),
    )
    return UPLOAD_CARDS

async def handle_document(update: Update, context: CallbackContext) -> int:
    document = update.message.document
    processing_msg = await update.message.reply_text('⏳ جاري معالجة الملف...')
    file = await context.bot.get_file(document.file_id)
    file_stream = io.BytesIO()
    await file.download_to_memory(out=file_stream)
    file_stream.seek(0)
    try:
        csv_reader = csv.reader(io.TextIOWrapper(file_stream, encoding='utf-8-sig'))
        _ = next(csv_reader, None)
        cards = []
        for row in csv_reader:
            if len(row) >= 3:
                cards.append({
                    'code': row[0].strip(),
                    'value': float(row[1]),
                    'price': float(row[2]),
                    'expiry': row[3].strip() if len(row) > 3 else ''
                })
        context.user_data['cards_to_upload'] = cards
        await context.bot.delete_message(chat_id=update.message.chat_id, message_id=processing_msg.message_id)
        await update.message.reply_text(
            f'✅ تم استلام {len(cards)} كرت!\nهل تريد رفعهم الآن؟',
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton('✅ نعم', callback_data='confirm_upload')],
                [InlineKeyboardButton('✏️ تعديل وإعادة الإرسال', callback_data='edit_and_upload')],
                [InlineKeyboardButton('❌ إلغاء', callback_data='cancel_upload')],
            ]),
        )
        return CONFIRM_UPLOAD
    except Exception as e:
        logger.error(f'Error processing CSV: {e}')
        await update.message.reply_text('⚠️ حدث خطأ في معالجة الملف. الرجاء التحقق من التنسيق وإعادة المحاولة.', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔄 إعادة المحاولة', callback_data='upload_cards')]]))
        return ConversationHandler.END

async def confirm_upload(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    await query.answer()
    if query.data == 'edit_and_upload':
        await query.edit_message_text('✏️ قم بتعديل الملف وأعد إرساله الآن.')
        return UPLOAD_CARDS
    cards = context.user_data.get('cards_to_upload', [])
    user = get_user(query.from_user.id)
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        network_id = await _ensure_supplier_network(cursor, user['id'])
        uploaded_count = 0
        for card in cards:
            cursor.execute('SELECT id FROM card_categories WHERE value = ? AND price = ? AND network_id = ?', (card['value'], card['price'], network_id))
            category = cursor.fetchone()
            if not category:
                cursor.execute('INSERT INTO card_categories (network_id, value, price) VALUES (?, ?, ?)', (network_id, card['value'], card['price']))
                category_id = cursor.lastrowid
            else:
                category_id = category[0]
            encrypted_code = encrypt_data(card['code'])
            cursor.execute('INSERT INTO cards (id, category_id, code) VALUES (?, ?, ?)', (str(uuid.uuid4()), category_id, encrypted_code))
            uploaded_count += 1
        conn.commit()
        await query.edit_message_text(f'✅ تم رفع {uploaded_count} كرت بنجاح!')
        await context.bot.send_message(chat_id=query.message.chat_id, text='🛍️ يمكنك الآن البدء ببيع الكروت!', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]]))
    except Exception as e:
        logger.error(f'Error saving cards: {e}')
        await query.edit_message_text('⚠️ حدث خطأ أثناء حفظ الكروت. الرجاء المحاولة لاحقاً.')
    finally:
        conn.close()
    return ConversationHandler.END

# Buying flow
async def buy_cards(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    await query.answer()
    loading_msg = await query.edit_message_text('⏳ جاري تحميل الشبكات المتاحة...')
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id, name FROM networks WHERE is_active = 1')
    networks = cursor.fetchall()
    conn.close()
    if not networks:
        await context.bot.edit_message_text(chat_id=query.message.chat_id, message_id=loading_msg.message_id, text='⚠️ لا تتوفر شبكات حالياً. الرجاء المحاولة لاحقاً.')
        return ConversationHandler.END
    keyboard = [[InlineKeyboardButton(n[1], callback_data=f'network_{n[0]}')] for n in networks]
    keyboard.append([InlineKeyboardButton('🔍 بحث', callback_data='search_networks')])
    keyboard.append([InlineKeyboardButton('❌ إلغاء', callback_data='cancel_purchase')])
    await context.bot.edit_message_text(chat_id=query.message.chat_id, message_id=loading_msg.message_id, text='📶 اختر شبكة الإنترنت:', reply_markup=InlineKeyboardMarkup(keyboard))
    return SELECT_NETWORK

async def select_category(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    await query.answer()
    network_id = query.data.split('_')[1]
    context.user_data['selected_network'] = network_id
    loading_msg = await query.edit_message_text('⏳ جاري تحميل الفئات المتاحة...')
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id, value, price FROM card_categories WHERE network_id = ? AND is_available = 1', (network_id,))
    categories = cursor.fetchall()
    conn.close()
    if not categories:
        await context.bot.edit_message_text(chat_id=query.message.chat_id, message_id=loading_msg.message_id, text='⚠️ لا تتوفر فئات كروت لهذه الشبكة حالياً.')
        return ConversationHandler.END
    keyboard = [[InlineKeyboardButton(f'{c[1]} ريال - {c[2]} ريال', callback_data=f'category_{c[0]}')] for c in categories]
    keyboard.append([InlineKeyboardButton('↩️ رجوع', callback_data='buy_cards')])
    keyboard.append([InlineKeyboardButton('❌ إلغاء', callback_data='cancel_purchase')])
    await context.bot.edit_message_text(chat_id=query.message.chat_id, message_id=loading_msg.message_id, text='💰 اختر الفئة السعرية:', reply_markup=InlineKeyboardMarkup(keyboard))
    return SELECT_CATEGORY

async def confirm_purchase(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    await query.answer()
    category_id = query.data.split('_')[1]
    context.user_data['selected_category'] = category_id
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT value, price FROM card_categories WHERE id = ?', (category_id,))
    row = cursor.fetchone()
    if not row:
        await query.edit_message_text('⚠️ الفئة المحددة غير متوفرة!')
        return ConversationHandler.END
    value, price = row
    user = get_user(query.from_user.id)
    balance = user['balance']
    if balance < price:
        await query.edit_message_text(
            f'⚠️ رصيدك غير كافي!\nسعر الكرت: {price} ريال\nرصيدك الحالي: {balance} ريال\n\nالرجاء شحن رصيدك أولاً.',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('💰 شحن الرصيد', callback_data='recharge_balance')], [InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]]),
        )
        return ConversationHandler.END
    await query.edit_message_text(
        f'🧾 تفاصيل الشراء:\n📶 القيمة: {value} ريال\n💰 السعر: {price} ريال\n💳 رصيدك الحالي: {balance} ريال\n\nهل تريد تأكيد الشراء؟',
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('✅ تأكيد الشراء', callback_data='complete_purchase')], [InlineKeyboardButton('❌ إلغاء', callback_data='cancel_purchase')]]),
    )
    return CONFIRM_PURCHASE

async def complete_purchase(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    await query.answer()
    user = get_user(query.from_user.id)
    category_id = context.user_data.get('selected_category')
    if not category_id:
        await query.edit_message_text('⚠️ حدث خطأ في عملية الشراء.')
        return ConversationHandler.END
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT price, network_id FROM card_categories WHERE id = ?', (category_id,))
        row = cursor.fetchone()
        if not row:
            await query.edit_message_text('⚠️ الفئة المحددة غير متوفرة!')
            return ConversationHandler.END
        price, network_id = row
        cursor.execute('SELECT supplier_id FROM networks WHERE id = ?', (network_id,))
        row = cursor.fetchone()
        if not row:
            await query.edit_message_text('⚠️ الشبكة المحددة غير متوفرة!')
            return ConversationHandler.END
        supplier_id = row[0]
        cursor.execute('SELECT id, code FROM cards WHERE category_id = ? AND is_used = 0 LIMIT 1', (category_id,))
        card = cursor.fetchone()
        if not card:
            await query.edit_message_text('⚠️ عذراً، الكروت نفذت لهذه الفئة!')
            return ConversationHandler.END
        card_id, encrypted_code = card
        decrypted_code = decrypt_data(encrypted_code)
        # Accounting postings
        cur2 = conn.cursor()
        buyer_acc = get_or_create_user_wallet_account(cur2, user['id'])
        supplier_acc = get_or_create_user_wallet_account(cur2, supplier_id)
        cur2.execute('SELECT id FROM accounts WHERE code = ?', (ACCOUNT_CODE_BOT_COMMISSION_REVENUE,))
        row_acc = cur2.fetchone()
        if not row_acc:
            ensure_base_accounts(cur2)
            cur2.execute('SELECT id FROM accounts WHERE code = ?', (ACCOUNT_CODE_BOT_COMMISSION_REVENUE,))
            row_acc = cur2.fetchone()
        commission_acc = row_acc[0]
        conn.commit()
        supplier_share = round(price * (1.0 - CARD_COMMISSION_RATE), 2)
        bot_commission = round(price * CARD_COMMISSION_RATE, 2)
        post_journal(
            description=f'Card purchase {card_id} by user {user["id"]}',
            created_by=user['id'],
            lines=[
                {'account_id': buyer_acc, 'debit': price, 'credit': 0.0, 'user_id': user['id'], 'ref_type': 'card_purchase', 'ref_id': card_id},
                {'account_id': supplier_acc, 'debit': 0.0, 'credit': supplier_share, 'user_id': supplier_id, 'ref_type': 'card_purchase', 'ref_id': card_id},
                {'account_id': commission_acc, 'debit': 0.0, 'credit': bot_commission, 'user_id': None, 'ref_type': 'card_purchase', 'ref_id': card_id},
            ],
        )
        cursor.execute('UPDATE cards SET is_used = 1 WHERE id = ?', (card_id,))
        create_transaction(user['id'], supplier_id, price, 'card_purchase', card_id)
        conn.commit()
        recalc_and_set_user_balance(user['id'])
        recalc_and_set_user_balance(supplier_id)
        await query.edit_message_text('✅ تم الشراء بنجاح!\nكود الكرت سيرسل لك في الرسالة التالية...', reply_markup=ReplyKeyboardRemove())
        await context.bot.send_message(chat_id=query.message.chat_id, text=('🔐 كود الكرت الخاص بك:\n' f'📶 {decrypted_code}\n\n' '⚠️ الرجاء حفظ الكود في مكان آمن ولا تشاركه مع أحد!'), reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]]))
    except Exception as e:
        logger.error(f'Error completing purchase: {e}')
        await query.edit_message_text('⚠️ حدث خطأ أثناء عملية الشراء. الرجاء المحاولة لاحقاً.')
    finally:
        conn.close()
    return ConversationHandler.END

# Agent recharge
async def recharge_customers(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text('🔋 لشحن رصيد عميل:\nالرجاء إدخال رقم هاتف العميل (9 أرقام):', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('❌ إلغاء', callback_data='cancel_recharge')]]))
    return SELECT_CUSTOMER

async def select_customer(update: Update, context: CallbackContext) -> int:
    phone = update.message.text.strip()
    customer = get_user_by_phone(phone)
    if not customer:
        await update.message.reply_text('⚠️ لم يتم العثور على عميل بهذا الرقم!\nالرجاء إدخال رقم هاتف العميل (9 أرقام):', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('❌ إلغاء', callback_data='cancel_recharge')]]))
        return SELECT_CUSTOMER
    context.user_data['recharge_customer'] = customer['id']
    await update.message.reply_text('💰 الرجاء إدخال مبلغ الشحن:', reply_markup=ReplyKeyboardMarkup([['5000', '10000', '20000'], ['50000', '100000', '200000'], ['❌ إلغاء']], one_time_keyboard=True, resize_keyboard=True))
    return GET_RECHARGE_AMOUNT

async def get_recharge_amount(update: Update, context: CallbackContext) -> int:
    try:
        amount = float(update.message.text)
        if amount <= 0:
            raise ValueError()
        context.user_data['recharge_amount'] = amount
        customer_id = context.user_data.get('recharge_customer')
        customer = get_user_by_id(customer_id)
        await update.message.reply_text('🧾 تفاصيل الشحن:\n' f'👤 العميل: {customer["full_name"]}\n' f'📱 رقم الهاتف: {customer["phone"]}\n' f'💰 المبلغ: {amount} ريال\n\n' 'هل تريد تأكيد عملية الشحن?', reply_markup=ReplyKeyboardMarkup([['✅ نعم', '❌ إلغاء']], one_time_keyboard=True, resize_keyboard=True))
        return CONFIRM_RECHARGE
    except Exception:
        await update.message.reply_text('⚠️ الرجاء إدخال مبلغ صحيح!', reply_markup=ReplyKeyboardMarkup([['5000', '10000', '20000'], ['50000', '100000', '200000'], ['❌ إلغاء']], one_time_keyboard=True, resize_keyboard=True))
        return GET_RECHARGE_AMOUNT

async def confirm_recharge(update: Update, context: CallbackContext) -> int:
    if update.message.text != '✅ نعم':
        await update.message.reply_text('تم إلغاء عملية الشحن.', reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END
    customer_id = context.user_data.get('recharge_customer')
    amount = float(context.user_data.get('recharge_amount', 0))
    agent = get_user(update.message.from_user.id)
    if not customer_id or amount <= 0:
        await update.message.reply_text('⚠️ حدث خطأ في البيانات!')
        return ConversationHandler.END
    agent_commission = round(amount * AGENT_COMMISSION_RATE, 2)
    customer_amount = round(amount - agent_commission, 2)
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        agent_acc = get_or_create_user_wallet_account(cur, agent['id'])
        cust_acc = get_or_create_user_wallet_account(cur, customer_id)
        conn.commit()
        conn.close()
        post_journal(
            description=f'Agent recharge from {agent["id"]} to {customer_id}',
            created_by=agent['id'],
            lines=[
                {'account_id': agent_acc, 'debit': amount, 'credit': 0.0, 'user_id': agent['id'], 'ref_type': 'wallet_recharge', 'ref_id': str(customer_id)},
                {'account_id': cust_acc, 'debit': 0.0, 'credit': customer_amount, 'user_id': customer_id, 'ref_type': 'wallet_recharge', 'ref_id': str(customer_id)},
                {'account_id': agent_acc, 'debit': 0.0, 'credit': agent_commission, 'user_id': agent['id'], 'ref_type': 'agent_commission', 'ref_id': str(customer_id)},
            ],
        )
        create_transaction(agent['id'], customer_id, customer_amount, 'wallet_recharge')
        create_transaction(None, agent['id'], agent_commission, 'agent_commission', is_withdrawable=True)
        recalc_and_set_user_balance(agent['id'])
        recalc_and_set_user_balance(customer_id)
        await update.message.reply_text(f'✅ تم شحن {customer_amount} ريال بنجاح للعميل!\n💰 عمولتك: {agent_commission} ريال', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]]))
    except Exception as e:
        logger.error(f'Error in recharge: {e}')
        await update.message.reply_text('⚠️ حدث خطأ أثناء عملية الشحن. الرجاء المحاولة لاحقاً.')
    return ConversationHandler.END

# Withdrawals (unchanged business rules)
async def start_withdrawal(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    await query.answer()
    user = get_user(query.from_user.id)
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT SUM(amount) FROM transactions WHERE to_user = ? AND is_withdrawable = 1', (user['id'],))
    withdrawable = cursor.fetchone()[0] or 0
    conn.close()
    if withdrawable <= 0:
        await query.edit_message_text('⚠️ لا يوجد رصيد قابل للسحب!')
        return ConversationHandler.END
    min_withdraw = 20000 if user['role'] == 'agent' else 50000
    if withdrawable < min_withdraw:
        await query.edit_message_text(f'⚠️ الحد الأدنى للسحب هو {min_withdraw} ريال!\nرصيدك القابل للسحب: {withdrawable} ريال')
        return ConversationHandler.END
    context.user_data['withdrawable'] = withdrawable
    await query.edit_message_text(f'💳 رصيدك القابل للسحب: {withdrawable} ريال\n' f'🔻 الحد الأدنى للسحب: {min_withdraw} ريال\n' 'الرجاء إدخال المبلغ المراد سحبه:', reply_markup=ReplyKeyboardMarkup([['20000', '50000', '100000'], ['200000', '500000', '1000000'], ['❌ إلغاء']], one_time_keyboard=True, resize_keyboard=True))
    return GET_WITHDRAW_AMOUNT

async def get_withdraw_amount(update: Update, context: CallbackContext) -> int:
    try:
        amount = float(update.message.text)
        user = get_user(update.message.from_user.id)
        min_withdraw = 20000 if user['role'] == 'agent' else 50000
        max_withdraw = context.user_data.get('withdrawable', 0)
        if amount < min_withdraw:
            await update.message.reply_text(f'⚠️ المبلغ أقل من الحد الأدنى ({min_withdraw} ريال)!', reply_markup=ReplyKeyboardMarkup([['20000', '50000', '100000'], ['200000', '500000', '1000000'], ['❌ إلغاء']], one_time_keyboard=True, resize_keyboard=True))
            return GET_WITHDRAW_AMOUNT
        if amount > max_withdraw:
            await update.message.reply_text(f'⚠️ المبلغ أكبر من الرصيد القابل للسحب ({max_withdraw} ريال)!', reply_markup=ReplyKeyboardMarkup([['20000', '50000', '100000'], ['200000', '500000', '1000000'], ['❌ إلغاء']], one_time_keyboard=True, resize_keyboard=True))
            return GET_WITHDRAW_AMOUNT
        context.user_data['withdraw_amount'] = amount
        await update.message.reply_text(f'💸 المبلغ المطلوب سحبه: {amount} ريال\n\nهل تريد تأكيد طلب السحب؟', reply_markup=ReplyKeyboardMarkup([['✅ نعم', '❌ إلغاء']], one_time_keyboard=True, resize_keyboard=True))
        return CONFIRM_WITHDRAWAL
    except Exception:
        await update.message.reply_text('⚠️ الرجاء إدخال مبلغ صحيح!', reply_markup=ReplyKeyboardMarkup([['20000', '50000', '100000'], ['200000', '500000', '1000000'], ['❌ إلغاء']], one_time_keyboard=True, resize_keyboard=True))
        return GET_WITHDRAW_AMOUNT

async def confirm_withdrawal(update: Update, context: CallbackContext) -> int:
    if update.message.text != '✅ نعم':
        await update.message.reply_text('تم إلغاء طلب السحب.', reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END
    user = get_user(update.message.from_user.id)
    amount = context.user_data.get('withdraw_amount')
    if not amount:
        await update.message.reply_text('⚠️ حدث خطأ في البيانات! الرجاء المحاولة مرة أخرى.')
        return ConversationHandler.END
    conn = get_db_connection()
    try:
        request_id = str(uuid.uuid4())
        cursor = conn.cursor()
        cursor.execute('INSERT INTO withdrawal_requests (id, user_id, amount) VALUES (?, ?, ?)', (request_id, user['id'], amount))
        conn.commit()
        await notify_admins(context, '📬 طلب سحب جديد:\n' f'👤 المستخدم: {user["full_name"]}\n' f'📱 الهاتف: {user["phone"]}\n' f'💳 المبلغ: {amount} ريال\n' f'🆔 رابط الطلب: /review_withdrawal_{request_id}')
        await update.message.reply_text('✅ تم إرسال طلب السحب للمراجعة.\nسيتم إعلامك عند الموافقة على طلبك.', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]]))
    except Exception as e:
        logger.error(f'Error in withdrawal request: {e}')
        await update.message.reply_text('⚠️ حدث خطأ أثناء إنشاء طلب السحب. الرجاء المحاولة لاحقاً.')
    finally:
        conn.close()
    return ConversationHandler.END

# Admin activation
async def activate_accounts(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    await query.answer()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE is_active = 0 AND role IN ('agent', 'supplier')")
    inactive_users = cursor.fetchall()
    conn.close()
    if not inactive_users:
        await query.edit_message_text('✅ لا توجد حسابات بحاجة للتفعيل.')
        return ConversationHandler.END
    context.user_data['inactive_users'] = inactive_users
    keyboard = [[InlineKeyboardButton(f'{u[2]} ({u[4]}) - {u[3]}', callback_data=f'activate_{u[0]}')] for u in inactive_users]
    keyboard.append([InlineKeyboardButton('🔄 تحديث القائمة', callback_data='activate_accounts')])
    keyboard.append([InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')])
    await query.edit_message_text('📋 الحسابات غير المفعلة:', reply_markup=InlineKeyboardMarkup(keyboard))
    return ADMIN_ACTIVATE_ACCOUNTS

async def activate_user(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    await query.answer()
    user_id = int(query.data.split('_')[1])
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET is_active = 1 WHERE id = ?', (user_id,))
        conn.commit()
        user = get_user_by_id(user_id)
        if user:
            await context.bot.send_message(user['telegram_id'], '🎉 مبروك! تم تفعيل حسابك بنجاح.\nيمكنك الآن استخدام جميع ميزات البوت.')
        await query.edit_message_text('✅ تم تفعيل حساب ' + user['full_name'] + ' بنجاح!', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔙 العودة للقائمة', callback_data='activate_accounts')]]))
    except Exception as e:
        logger.error(f'Error activating user: {e}')
        await query.edit_message_text('⚠️ حدث خطأ أثناء التفعيل. الرجاء المحاولة لاحقاً.')
    finally:
        conn.close()
    return ConversationHandler.END

# Super admin issuance flow
async def start_issue_balance(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    await query.answer()
    admin_user = get_user(query.from_user.id)
    if not admin_user or admin_user['role'] != 'super_admin':
        await query.edit_message_text('⚠️ هذه الميزة متاحة للمشرف الأعلى فقط.')
        return ConversationHandler.END
    await query.edit_message_text('➕ إصدار رصيد:\nأدخل رقم هاتف المستخدم (9 أرقام) أو معرف التلغرام:', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('❌ إلغاء', callback_data='main_menu')]]))
    return ISSUE_TARGET

async def get_issue_target(update: Update, context: CallbackContext) -> int:
    text = update.message.text.strip()
    target = None
    if re.fullmatch(r'\d{9}', text):
        target = get_user_by_phone(text)
    elif re.fullmatch(r'\d{6,}', text):
        target = get_user(int(text))
    if not target:
        await update.message.reply_text('⚠️ لم يتم العثور على المستخدم. أعد الإدخال أو اضغط إلغاء.')
        return ISSUE_TARGET
    context.user_data['issue_target_user_id'] = target['id']
    await update.message.reply_text('أدخل المبلغ المطلوب إصداره:', reply_markup=ReplyKeyboardMarkup([['10000', '50000', '100000'], ['250000', '500000', '1000000'], ['❌ إلغاء']], one_time_keyboard=True, resize_keyboard=True))
    return ISSUE_AMOUNT

async def get_issue_amount(update: Update, context: CallbackContext) -> int:
    try:
        amount = float(update.message.text)
        if amount <= 0:
            raise ValueError()
    except Exception:
        await update.message.reply_text('⚠️ الرجاء إدخال مبلغ صحيح (> 0).')
        return ISSUE_AMOUNT
    context.user_data['issue_amount'] = amount
    target_id = context.user_data.get('issue_target_user_id')
    target = get_user_by_id(target_id)
    await update.message.reply_text('تأكيد الإصدار:\n' f'المستخدم: {target["full_name"]} ({target["phone"]})\n' f'المبلغ: {amount:.2f} ريال\n' 'هل تريد المتابعة؟', reply_markup=ReplyKeyboardMarkup([['✅ نعم', '❌ إلغاء']], one_time_keyboard=True, resize_keyboard=True))
    return ISSUE_CONFIRM

async def confirm_issue(update: Update, context: CallbackContext) -> int:
    if update.message.text != '✅ نعم':
        await update.message.reply_text('تم الإلغاء.', reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END
    admin = get_user(update.message.from_user.id)
    if not admin or admin['role'] != 'super_admin':
        await update.message.reply_text('⚠️ صلاحيات غير كافية.', reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END
    target_id = context.user_data.get('issue_target_user_id')
    amount = float(context.user_data.get('issue_amount', 0))
    try:
        issue_balance_to_user(admin['id'], target_id, amount, note='Manual issuance')
        recalc_and_set_user_balance(target_id)
        target = get_user_by_id(target_id)
        await update.message.reply_text(f'✅ تم إصدار {amount:.2f} ريال إلى {target["full_name"]}.', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]]))
        try:
            await context.bot.send_message(target['telegram_id'], f'تم إضافة {amount:.2f} ريال إلى رصيدك بواسطة الإدارة.')
        except Exception:
            pass
    except Exception as e:
        logger.error(f'Issuance error: {e}')
        await update.message.reply_text('⚠️ فشل إصدار الرصيد.')
    return ConversationHandler.END

# Misc
async def notify_admins(context: CallbackContext, message: str):
    logger.info(f'Admin Notification: {message}')
    await context.bot.send_message(chat_id=7684780523, text=message)

async def quick_menu(update: Update, context: CallbackContext) -> int:
    user = get_user(update.effective_user.id)
    if not user:
        return await start(update, context)
    buttons = [
        [InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')],
        [InlineKeyboardButton('💳 رصيدي', callback_data='show_balance')],
        [InlineKeyboardButton('🛒 شراء كرت', callback_data='buy_cards')],
        [InlineKeyboardButton('🔁 تحويل إلى محفظة', callback_data='transfer_to_friend')],
        [InlineKeyboardButton('📊 إحصائياتي', callback_data='my_stats')],
    ]
    if update.message:
        await update.message.reply_text('⚡️ قائمة الأوامر السريعة:', reply_markup=InlineKeyboardMarkup(buttons))
    else:
        await update.callback_query.edit_message_text('⚡️ قائمة الأوامر السريعة:', reply_markup=InlineKeyboardMarkup(buttons))
    return ConversationHandler.END

async def show_balance(update: Update, context: CallbackContext) -> int:
    user = get_user(update.effective_user.id)
    recalc_and_set_user_balance(user['id'])
    user = get_user(update.effective_user.id)
    text = f"💳 رصيدك: {user['balance']:.2f} ريال\n🪪 رقم المحفظة: {user.get('wallet_number','-')}"
    if update.message:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]]))
    else:
        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]]))
    return ConversationHandler.END

# Supplier text paste cards upload (0..13 digit codes separated by newline)
async def paste_cards_prompt(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text('📋 أرسل الآن قائمة الأكواد (سطر لكل كرت). يمكن أن تكون الأكواد من 0 إلى 13 رقم/حرف لكل كرت.\nاكتب /cancel للإلغاء.')
    return PASTE_CARDS

async def handle_pasted_cards(update: Update, context: CallbackContext) -> int:
    supplier = get_user(update.message.from_user.id)
    if not supplier or supplier['role'] != 'supplier' or not supplier['is_active']:
        await update.message.reply_text('⚠️ الميزة للمزودين المفعّلين فقط.')
        return ConversationHandler.END
    raw = update.message.text.strip()
    lines = [l.strip() for l in raw.splitlines() if l.strip()]
    if not lines:
        await update.message.reply_text('⚠️ لم يتم العثور على أكواد.')
        return ConversationHandler.END
    # Default value/price: ask not implemented; assume equal pricing by length? Use placeholders 0 value/price
    # We'll store as value=0, price=0 and supplier can set categories later in inventory
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        network_id = await _ensure_supplier_network(cur, supplier['id'])
        # Use single category per paste with value=0 price=0
        cur.execute('SELECT id FROM card_categories WHERE network_id = ? AND value = ? AND price = ?', (network_id, 0, 0))
        row = cur.fetchone()
        if row:
            category_id = row[0]
        else:
            cur.execute('INSERT INTO card_categories (network_id, value, price) VALUES (?, ?, ?)', (network_id, 0, 0))
            category_id = cur.lastrowid
        uploaded = 0
        for code in lines:
            if not re.fullmatch(r'\d{1,13}', code):
                continue
            enc = encrypt_data(code)
            cur.execute('INSERT INTO cards (id, category_id, code) VALUES (?, ?, ?)', (str(uuid.uuid4()), category_id, enc))
            uploaded += 1
        conn.commit()
        await update.message.reply_text(f'✅ تم حفظ {uploaded} كرت من أصل {len(lines)}.', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]]))
    except Exception as e:
        logger.error(f'Paste upload error: {e}')
        await update.message.reply_text('⚠️ فشل الحفظ.')
    finally:
        conn.close()
    return ConversationHandler.END

# P2P transfer by wallet number
async def transfer_to_friend_handler(update: Update, context: CallbackContext) -> int:
    await update.callback_query.edit_message_text('🔁 أدخل رقم محفظة المستلم (9 أرقام وتبدأ بـ 79):')
    return TRANSFER_TARGET

async def transfer_target(update: Update, context: CallbackContext) -> int:
    wallet = update.message.text.strip()
    if not re.fullmatch(r'79\d{7}', wallet):
        await update.message.reply_text('⚠️ رقم المحفظة غير صحيح. يجب أن يكون 9 أرقام ويبدأ بـ 79.')
        return TRANSFER_TARGET
    user = get_user_by_wallet(wallet)
    if not user:
        await update.message.reply_text('⚠️ لم يتم العثور على محفظة بهذا الرقم. أعد الإدخال:')
        return TRANSFER_TARGET
    context.user_data['transfer_target_id'] = user['id']
    await update.message.reply_text('💰 أدخل مبلغ التحويل (بالريال):')
    return TRANSFER_AMOUNT

async def transfer_amount(update: Update, context: CallbackContext) -> int:
    try:
        amount = float(update.message.text)
        if amount <= 0:
            raise ValueError()
    except Exception:
        await update.message.reply_text('⚠️ أدخل مبلغاً صحيحاً (> 0):')
        return TRANSFER_AMOUNT
    context.user_data['transfer_amount'] = round(amount, 2)
    target = get_user_by_id(context.user_data['transfer_target_id'])
    await update.message.reply_text(
        f"تأكيد التحويل:\nالمستلم: {target['full_name']} ({target['wallet_number']})\nالمبلغ: {amount:.2f} ريال\nتأكيد؟",
        reply_markup=ReplyKeyboardMarkup([['✅ نعم', '❌ إلغاء']], one_time_keyboard=True, resize_keyboard=True),
    )
    return TRANSFER_CONFIRM

async def transfer_confirm(update: Update, context: CallbackContext) -> int:
    if update.message.text != '✅ نعم':
        await update.message.reply_text('تم الإلغاء.', reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END
    sender = get_user(update.message.from_user.id)
    target_id = context.user_data.get('transfer_target_id')
    amount = float(context.user_data.get('transfer_amount', 0))
    if not target_id or amount <= 0:
        await update.message.reply_text('⚠️ خطأ في البيانات.')
        return ConversationHandler.END
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        sender_acc = get_or_create_user_wallet_account(cur, sender['id'])
        recv_acc = get_or_create_user_wallet_account(cur, target_id)
        conn.commit()
        conn.close()
        post_journal(
            description=f'P2P transfer from {sender["id"]} to {target_id}',
            created_by=sender['id'],
            lines=[
                {'account_id': sender_acc, 'debit': amount, 'credit': 0.0, 'user_id': sender['id'], 'ref_type': 'p2p_transfer', 'ref_id': str(target_id)},
                {'account_id': recv_acc, 'debit': 0.0, 'credit': amount, 'user_id': target_id, 'ref_type': 'p2p_transfer', 'ref_id': str(sender['id'])},
            ],
        )
        create_transaction(sender['id'], target_id, amount, 'p2p_transfer')
        recalc_and_set_user_balance(sender['id'])
        recalc_and_set_user_balance(target_id)
        await update.message.reply_text('✅ تم التحويل بنجاح.', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]]))
    except Exception as e:
        logger.error(f'P2P transfer error: {e}')
        await update.message.reply_text('⚠️ فشل التحويل.')
    return ConversationHandler.END

# Stats handlers
async def my_stats(update: Update, context: CallbackContext) -> int:
    user = get_user(update.effective_user.id)
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        # Total purchases
        cur.execute("SELECT COUNT(*), COALESCE(SUM(amount),0) FROM transactions WHERE from_user = ? AND type = 'card_purchase'", (user['id'],))
        cnt_p, sum_p = cur.fetchone()
        # Total incoming transfers
        cur.execute("SELECT COALESCE(SUM(amount),0) FROM transactions WHERE to_user = ?", (user['id'],))
        incoming = cur.fetchone()[0] or 0
        # Total outgoing transfers
        cur.execute("SELECT COALESCE(SUM(amount),0) FROM transactions WHERE from_user = ?", (user['id'],))
        outgoing = cur.fetchone()[0] or 0
        text = (
            f"📊 إحصائياتك:\n"
            f"🧾 عدد عمليات الشراء: {cnt_p}\n"
            f"💵 إجمالي المبالغ الخارجة: {outgoing:.2f} ريال\n"
            f"💳 إجمالي المبالغ الداخلة: {incoming:.2f} ريال\n"
        )
    finally:
        conn.close()
    if update.message:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]]))
    else:
        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]]))
    return ConversationHandler.END

async def button_click_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    data = query.data
    logger.info(f'Received callback: {data}')
    if data == 'buy_cards':
        await buy_cards(update, context)
    elif data == 'upload_cards':
        await upload_cards(update, context)
    elif data == 'recharge_balance':
        await recharge_balance_handler(update, context)
    elif data == 'transfer_to_friend':
        await transfer_to_friend_handler(update, context)
    elif data == 'invite_friends':
        await invite_friends_handler(update, context)
    elif data == 'transaction_history':
        await transaction_history_handler(update, context)
    elif data == 'customer_help':
        await customer_help_handler(update, context)
    elif data.startswith('network_'):
        await select_category(update, context)
    elif data.startswith('category_'):
        await confirm_purchase(update, context)
    elif data == 'complete_purchase':
        await complete_purchase(update, context)
    elif data == 'main_menu':
        await main_menu(update, context)
    elif data == 'activate_accounts':
        await activate_accounts(update, context)
    elif data.startswith('activate_'):
        await activate_user(update, context)
    elif data == 'recharge_customers':
        await recharge_customers(update, context)
    elif data in ('withdraw_earnings', 'agent_withdraw'):
        await start_withdrawal(update, context)
    elif data == 'issue_balance':
        await start_issue_balance(update, context)
    elif data == 'show_balance':
        await show_balance(update, context)
    elif data == 'my_stats':
        await my_stats(update, context)
    elif data == 'paste_cards':
        await paste_cards_prompt(update, context)
    else:
        await query.edit_message_text('⚠️ هذا الزر غير مفعل حالياً')

async def recharge_balance_handler(update: Update, context: CallbackContext):
    await update.callback_query.edit_message_text('💳 رقم محفظتك: ' + (get_user(update.callback_query.from_user.id).get('wallet_number') or '-') + '\n⏳ هذه الميزة قيد التطوير...')

async def transfer_to_friend_handler(update: Update, context: CallbackContext):
    await update.callback_query.edit_message_text('🔁 أدخل رقم محفظة المستلم (9 أرقام وتبدأ بـ 79):')
    return TRANSFER_TARGET

async def transfer_target(update: Update, context: CallbackContext) -> int:
    wallet = update.message.text.strip()
    if not re.fullmatch(r'79\d{7}', wallet):
        await update.message.reply_text('⚠️ رقم المحفظة غير صحيح. يجب أن يكون 9 أرقام ويبدأ بـ 79.')
        return TRANSFER_TARGET
    user = get_user_by_wallet(wallet)
    if not user:
        await update.message.reply_text('⚠️ لم يتم العثور على محفظة بهذا الرقم. أعد الإدخال:')
        return TRANSFER_TARGET
    context.user_data['transfer_target_id'] = user['id']
    await update.message.reply_text('💰 أدخل مبلغ التحويل (بالريال):')
    return TRANSFER_AMOUNT

async def transfer_amount(update: Update, context: CallbackContext) -> int:
    try:
        amount = float(update.message.text)
        if amount <= 0:
            raise ValueError()
    except Exception:
        await update.message.reply_text('⚠️ أدخل مبلغاً صحيحاً (> 0):')
        return TRANSFER_AMOUNT
    context.user_data['transfer_amount'] = round(amount, 2)
    target = get_user_by_id(context.user_data['transfer_target_id'])
    await update.message.reply_text(
        f"تأكيد التحويل:\nالمستلم: {target['full_name']} ({target['wallet_number']})\nالمبلغ: {amount:.2f} ريال\nتأكيد؟",
        reply_markup=ReplyKeyboardMarkup([['✅ نعم', '❌ إلغاء']], one_time_keyboard=True, resize_keyboard=True),
    )
    return TRANSFER_CONFIRM

async def transfer_confirm(update: Update, context: CallbackContext) -> int:
    if update.message.text != '✅ نعم':
        await update.message.reply_text('تم الإلغاء.', reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END
    sender = get_user(update.message.from_user.id)
    target_id = context.user_data.get('transfer_target_id')
    amount = float(context.user_data.get('transfer_amount', 0))
    if not target_id or amount <= 0:
        await update.message.reply_text('⚠️ خطأ في البيانات.')
        return ConversationHandler.END
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        sender_acc = get_or_create_user_wallet_account(cur, sender['id'])
        recv_acc = get_or_create_user_wallet_account(cur, target_id)
        conn.commit()
        conn.close()
        post_journal(
            description=f'P2P transfer from {sender["id"]} to {target_id}',
            created_by=sender['id'],
            lines=[
                {'account_id': sender_acc, 'debit': amount, 'credit': 0.0, 'user_id': sender['id'], 'ref_type': 'p2p_transfer', 'ref_id': str(target_id)},
                {'account_id': recv_acc, 'debit': 0.0, 'credit': amount, 'user_id': target_id, 'ref_type': 'p2p_transfer', 'ref_id': str(sender['id'])},
            ],
        )
        create_transaction(sender['id'], target_id, amount, 'p2p_transfer')
        recalc_and_set_user_balance(sender['id'])
        recalc_and_set_user_balance(target_id)
        await update.message.reply_text('✅ تم التحويل بنجاح.', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]]))
    except Exception as e:
        logger.error(f'P2P transfer error: {e}')
        await update.message.reply_text('⚠️ فشل التحويل.')
    return ConversationHandler.END

# Stats handlers
async def my_stats(update: Update, context: CallbackContext) -> int:
    user = get_user(update.effective_user.id)
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        # Total purchases
        cur.execute("SELECT COUNT(*), COALESCE(SUM(amount),0) FROM transactions WHERE from_user = ? AND type = 'card_purchase'", (user['id'],))
        cnt_p, sum_p = cur.fetchone()
        # Total incoming transfers
        cur.execute("SELECT COALESCE(SUM(amount),0) FROM transactions WHERE to_user = ?", (user['id'],))
        incoming = cur.fetchone()[0] or 0
        # Total outgoing transfers
        cur.execute("SELECT COALESCE(SUM(amount),0) FROM transactions WHERE from_user = ?", (user['id'],))
        outgoing = cur.fetchone()[0] or 0
        text = (
            f"📊 إحصائياتك:\n"
            f"🧾 عدد عمليات الشراء: {cnt_p}\n"
            f"💵 إجمالي المبالغ الخارجة: {outgoing:.2f} ريال\n"
            f"💳 إجمالي المبالغ الداخلة: {incoming:.2f} ريال\n"
        )
    finally:
        conn.close()
    if update.message:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]]))
    else:
        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]]))
    return ConversationHandler.END

def main() -> None:
    init_db()
    setup_super_admin()
    token = os.getenv('7766964799:AAHex-hGfjPX6g_R2aZ7-UPrgnFxQKAjSa0') or os.getenv('7766964799:AAHex-hGfjPX6g_R2aZ7-UPrgnFxQKAjSa0')
    if not token:
        logger.error('لم يتم ضبط BOT_TOKEN. يُرجى ضبط متغير البيئة BOT_TOKEN في Render.')
        raise SystemExit(1)
    persistence = PicklePersistence(filepath='conversationbot')
    application = Application.builder().token(token).persistence(persistence).build()

    # Set quick action menu (bot commands)
    try:
        application.bot.set_my_commands(QUICK_COMMANDS)
        application.bot.set_chat_menu_button(menu_button=MenuButtonCommands())
    except Exception as e:
        logger.warning(f'Failed setting commands/menu: {e}')

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start), CommandHandler('menu', quick_menu), CommandHandler('balance', show_balance), CommandHandler('buy', lambda u, c: buy_cards(u, c)), CommandHandler('stats', my_stats), CommandHandler('transfer', transfer_to_friend_handler)],
        states={
            GET_FULL_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_full_name)],
            GET_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_phone)],
            CHOOSE_ROLE: [MessageHandler(filters.Regex('^(عميل|وكيل|مزود)$'), choose_role)],
            UPLOAD_CARDS: [MessageHandler(filters.Document.FileExtension('csv'), handle_document)],
            CONFIRM_UPLOAD: [CallbackQueryHandler(confirm_upload, pattern='^(confirm_upload|edit_and_upload)$')],
            SELECT_NETWORK: [CallbackQueryHandler(select_category, pattern='^network_')],
            SELECT_CATEGORY: [CallbackQueryHandler(confirm_purchase, pattern='^category_')],
            CONFIRM_PURCHASE: [CallbackQueryHandler(complete_purchase, pattern='^complete_purchase$')],
            SELECT_CUSTOMER: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_customer)],
            GET_RECHARGE_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_recharge_amount)],
            CONFIRM_RECHARGE: [MessageHandler(filters.Regex('^(✅ نعم|❌ إلغاء)$'), confirm_recharge)],
            GET_WITHDRAW_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_withdraw_amount)],
            CONFIRM_WITHDRAWAL: [MessageHandler(filters.Regex('^(✅ نعم|❌ إلغاء)$'), confirm_withdrawal)],
            ADMIN_ACTIVATE_ACCOUNTS: [CallbackQueryHandler(activate_user, pattern='^activate_')],
            ISSUE_TARGET: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_issue_target)],
            ISSUE_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_issue_amount)],
            ISSUE_CONFIRM: [MessageHandler(filters.Regex('^(✅ نعم|❌ إلغاء)$'), confirm_issue)],
            # New
            PASTE_CARDS: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_pasted_cards)],
            TRANSFER_TARGET: [MessageHandler(filters.TEXT & ~filters.COMMAND, transfer_target)],
            TRANSFER_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, transfer_amount)],
            TRANSFER_CONFIRM: [MessageHandler(filters.Regex('^(✅ نعم|❌ إلغاء)$'), transfer_confirm)],
        },
        fallbacks=[
            CommandHandler('cancel', cancel),
            CallbackQueryHandler(main_menu, pattern='^main_menu$'),
            CallbackQueryHandler(cancel, pattern='^cancel_'),
        ],
        name='main_conversation',
        persistent=True,
    )
    application.add_handler(conv_handler)
    application.add_handler(CallbackQueryHandler(button_click_handler))
    application.run_polling()
    logger.info('🤖 تم بدء تشغيل البوت بنجاح!')

if __name__ == '__main__':
    main()