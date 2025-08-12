import logging
import sqlite3
import uuid
import csv
import io
import re
import os
import random
from typing import Optional
from datetime import datetime
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

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', 
    level=logging.INFO
)
logger = logging.getLogger(__name__)

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

# Bot command menu
QUICK_COMMANDS = [
    BotCommand('start', '🏠 القائمة الرئيسية'),
    BotCommand('menu', '📋 القائمة السريعة'),
    BotCommand('balance', '💳 عرض الرصيد'),
    BotCommand('buy', '🛒 شراء كرت'),
    BotCommand('transfer', '💸 تحويل رصيد'),
    BotCommand('stats', '📊 الإحصائيات'),
    BotCommand('help', '❓ المساعدة'),
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

# Encryption functions
def _load_cipher_suite() -> Fernet:
    """Load or generate encryption key for secure data storage"""
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
    return Fernet(key_bytes)

cipher_suite = _load_cipher_suite()

def encrypt_data(data: str) -> str:
    """Encrypt sensitive data"""
    try:
        return cipher_suite.encrypt(data.encode()).decode()
    except Exception as e:
        logger.error(f"Encryption error: {e}")
        return data

def decrypt_data(encrypted_data: str) -> str:
    """Decrypt sensitive data"""
    try:
        return cipher_suite.decrypt(encrypted_data.encode()).decode()
    except Exception as e:
        logger.error(f"Decryption error: {e}")
        return encrypted_data

# Database connection with error handling
def get_db_connection():
    """Get database connection with error handling"""
    try:
        conn = sqlite3.connect(DB_PATH, timeout=30.0)
        conn.execute('PRAGMA foreign_keys = ON')
        return conn
    except sqlite3.Error as e:
        logger.error(f"Database connection error: {e}")
        raise

def execute_db_query(query: str, params: tuple = (), fetch_one: bool = False, fetch_all: bool = False):
    """Execute database query with proper error handling"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(query, params)
        
        if fetch_one:
            result = cursor.fetchone()
        elif fetch_all:
            result = cursor.fetchall()
        else:
            result = cursor.lastrowid
            
        conn.commit()
        return result
    except sqlite3.Error as e:
        logger.error(f"Database query error: {e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()

def init_db():
    """Initialize database with all required tables"""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Users table with enhanced fields
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE NOT NULL,
                full_name TEXT NOT NULL,
                phone TEXT UNIQUE NOT NULL,
                role TEXT NOT NULL DEFAULT 'customer',
                balance REAL DEFAULT 0.0,
                invite_code TEXT UNIQUE,
                is_active BOOLEAN DEFAULT 0,
                bank_account TEXT,
                total_referrals INTEGER DEFAULT 0,
                referral_bonus REAL DEFAULT 0.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                wallet_number TEXT UNIQUE,
                last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_verified BOOLEAN DEFAULT 0,
                verification_code TEXT,
                total_purchases INTEGER DEFAULT 0,
                total_spent REAL DEFAULT 0.0
            )
        ''')

        # Networks table with enhanced fields including unique ID system
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS networks (
                id TEXT PRIMARY KEY,
                supplier_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                city TEXT NOT NULL,
                network_code TEXT UNIQUE NOT NULL,
                is_active BOOLEAN DEFAULT 0,
                is_approved BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                approved_at TIMESTAMP,
                approved_by INTEGER,
                description TEXT,
                contact_info TEXT,
                FOREIGN KEY(supplier_id) REFERENCES users(id),
                FOREIGN KEY(approved_by) REFERENCES users(id)
            )
        ''')

        # Card categories table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS card_categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                network_id TEXT NOT NULL,
                value REAL NOT NULL,
                price REAL NOT NULL,
                is_available BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                category_name TEXT,
                description TEXT,
                FOREIGN KEY(network_id) REFERENCES networks(id)
            )
        ''')

        # Cards table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cards (
                id TEXT PRIMARY KEY,
                category_id INTEGER NOT NULL,
                code TEXT NOT NULL,
                is_used BOOLEAN DEFAULT 0,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                used_at TIMESTAMP,
                used_by INTEGER,
                expiry_date TEXT,
                FOREIGN KEY(category_id) REFERENCES card_categories(id),
                FOREIGN KEY(used_by) REFERENCES users(id)
            )
        ''')

        # Enhanced transactions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id TEXT PRIMARY KEY,
                from_user INTEGER,
                to_user INTEGER,
                amount REAL NOT NULL,
                type TEXT NOT NULL,
                status TEXT DEFAULT 'completed',
                reference_id TEXT,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_withdrawable BOOLEAN DEFAULT 0,
                commission_amount REAL DEFAULT 0.0,
                FOREIGN KEY(from_user) REFERENCES users(id),
                FOREIGN KEY(to_user) REFERENCES users(id)
            )
        ''')

        # Withdrawal requests table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS withdrawal_requests (
                id TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                amount REAL NOT NULL,
                status TEXT DEFAULT 'pending',
                request_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                approval_time TIMESTAMP,
                admin_id INTEGER,
                admin_notes TEXT,
                bank_details TEXT,
                FOREIGN KEY(user_id) REFERENCES users(id),
                FOREIGN KEY(admin_id) REFERENCES users(id)
            )
        ''')

        # Referrals table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS referrals (
                id TEXT PRIMARY KEY,
                referrer_id INTEGER NOT NULL,
                referred_id INTEGER NOT NULL,
                bonus_amount REAL DEFAULT 0.0,
                awarded BOOLEAN DEFAULT 0,
                awarded_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(referrer_id) REFERENCES users(id),
                FOREIGN KEY(referred_id) REFERENCES users(id)
            )
        ''')

        # System logs table for admin monitoring
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS system_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                action TEXT NOT NULL,
                details TEXT,
                ip_address TEXT,
                user_agent TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        ''')

        # Admin notifications table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS admin_notifications (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                type TEXT DEFAULT 'info',
                is_read BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by INTEGER,
                target_admin INTEGER,
                FOREIGN KEY(created_by) REFERENCES users(id),
                FOREIGN KEY(target_admin) REFERENCES users(id)
            )
        ''')

        # Accounting tables (keeping existing structure)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE,
                name TEXT NOT NULL,
                type TEXT NOT NULL,
                parent_id INTEGER,
                is_active BOOLEAN DEFAULT 1
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_accounts (
                user_id INTEGER UNIQUE NOT NULL,
                account_id INTEGER NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id),
                FOREIGN KEY(account_id) REFERENCES accounts(id)
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS journal_entries (
                id TEXT PRIMARY KEY,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by INTEGER
            )
        ''')

        cursor.execute('''
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
        ''')

        # Migration: Add missing columns
        try:
            cursor.execute('ALTER TABLE users ADD COLUMN wallet_number TEXT UNIQUE')
        except sqlite3.OperationalError:
            pass

        try:
            cursor.execute('ALTER TABLE users ADD COLUMN last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP')
        except sqlite3.OperationalError:
            pass

        try:
            cursor.execute('ALTER TABLE users ADD COLUMN is_verified BOOLEAN DEFAULT 0')
        except sqlite3.OperationalError:
            pass

        try:
            cursor.execute('ALTER TABLE users ADD COLUMN total_purchases INTEGER DEFAULT 0')
        except sqlite3.OperationalError:
            pass

        try:
            cursor.execute('ALTER TABLE users ADD COLUMN total_spent REAL DEFAULT 0.0')
        except sqlite3.OperationalError:
            pass

        try:
            cursor.execute('ALTER TABLE networks ADD COLUMN network_code TEXT UNIQUE')
        except sqlite3.OperationalError:
            pass

        try:
            cursor.execute('ALTER TABLE networks ADD COLUMN is_approved BOOLEAN DEFAULT 0')
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

        # Backfill missing network codes
        cursor.execute("SELECT id, supplier_id FROM networks WHERE network_code IS NULL OR network_code = ''")
        missing_codes = cursor.fetchall()
        for network_id, supplier_id in missing_codes:
            for _ in range(20):
                code = ''.join(str(random.randint(0, 9)) for _ in range(5))
                cursor.execute('SELECT 1 FROM networks WHERE network_code = ?', (code,))
                if not cursor.fetchone():
                    cursor.execute('UPDATE networks SET network_code = ? WHERE id = ?', (code, network_id))
                    break

        ensure_base_accounts(cursor)
        conn.commit()
        logger.info("Database initialized successfully")

    except Exception as e:
        logger.error(f"Database initialization error: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

def ensure_base_accounts(cursor: sqlite3.Cursor) -> None:
    """Ensure base accounting accounts exist"""
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
    """Get or create user wallet account for accounting"""
    cursor.execute('SELECT account_id FROM user_accounts WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()
    if row:
        return row[0]
    code = f'2{user_id:06d}'
    name = f'User Wallet #{user_id}'
    cursor.execute('INSERT INTO accounts (code, name, type) VALUES (?, ?, ?)', 
                  (code, name, ACCOUNT_TYPE_LIABILITY))
    account_id = cursor.lastrowid
    cursor.execute('INSERT INTO user_accounts (user_id, account_id) VALUES (?, ?)', 
                  (user_id, account_id))
    return account_id

def post_journal(description: str, created_by: Optional[int], lines: list[dict]) -> str:
    """Post accounting journal entry"""
    total_debit = round(sum(l.get('debit', 0.0) for l in lines), 2)
    total_credit = round(sum(l.get('credit', 0.0) for l in lines), 2)
    if abs(total_debit - total_credit) > 0.0001:
        raise ValueError('Unbalanced journal entry')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        entry_id = str(uuid.uuid4())
        cursor.execute('INSERT INTO journal_entries (id, description, created_by) VALUES (?, ?, ?)', 
                      (entry_id, description, created_by))
        
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
        return entry_id
    except Exception as e:
        conn.rollback()
        logger.error(f"Journal posting error: {e}")
        raise
    finally:
        conn.close()

def get_user_ledger_balance(user_id: int) -> float:
    """Get user's balance from ledger"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        account_id = get_or_create_user_wallet_account(cursor, user_id)
        cursor.execute('SELECT COALESCE(SUM(credit - debit), 0) FROM journal_lines WHERE account_id = ?', 
                      (account_id,))
        bal = cursor.fetchone()[0] or 0.0
        return round(bal, 2)
    finally:
        conn.close()

def recalc_and_set_user_balance(user_id: int) -> float:
    """Recalculate and update user balance"""
    bal = get_user_ledger_balance(user_id)
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('UPDATE users SET balance = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?', 
                      (bal, user_id))
        conn.commit()
        return bal
    finally:
        conn.close()

def issue_balance_to_user(super_admin_id: int, target_user_id: int, amount: float, note: str = '') -> str:
    """Issue balance to user by super admin"""
    if amount <= 0:
        raise ValueError('Amount must be positive')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT id FROM accounts WHERE code = ?', (ACCOUNT_CODE_ISSUANCE_EXPENSE,))
        row = cursor.fetchone()
        if not row:
            ensure_base_accounts(cursor)
            cursor.execute('SELECT id FROM accounts WHERE code = ?', (ACCOUNT_CODE_ISSUANCE_EXPENSE,))
            row = cursor.fetchone()
        issuance_acc_id = row[0]
        
        wallet_acc_id = get_or_create_user_wallet_account(cursor, target_user_id)
        conn.commit()
    finally:
        conn.close()
    
    entry_id = post_journal(
        description=f'Balance issuance to user {target_user_id}. {note}',
        created_by=super_admin_id,
        lines=[
            {'account_id': issuance_acc_id, 'debit': amount, 'credit': 0.0, 
             'user_id': None, 'ref_type': 'issuance', 'ref_id': str(target_user_id)},
            {'account_id': wallet_acc_id, 'debit': 0.0, 'credit': amount, 
             'user_id': target_user_id, 'ref_type': 'issuance', 'ref_id': str(target_user_id)},
        ],
    )
    recalc_and_set_user_balance(target_user_id)
    
    # Log the action
    log_system_action(super_admin_id, 'balance_issuance', 
                     f'Issued {amount} to user {target_user_id}. {note}')
    
    return entry_id

# User management functions
def create_user(telegram_id, full_name, phone, role='customer', is_active=False):
    """Create new user with enhanced validation"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        invite_code = str(uuid.uuid4())[:8].upper()
        
        # Generate unique wallet number
        wallet_number = None
        for _ in range(10):
            trial = '79' + ''.join(str(random.randint(0, 9)) for _ in range(7))
            cursor.execute('SELECT 1 FROM users WHERE wallet_number = ?', (trial,))
            if not cursor.fetchone():
                wallet_number = trial
                break
        
        if not wallet_number:
            raise RuntimeError('Failed to generate unique wallet number')
        
        # Auto-activate customers, require admin approval for agents/suppliers
        is_active_val = 1 if role == 'customer' else (1 if is_active else 0)
        
        cursor.execute('''
            INSERT INTO users (telegram_id, full_name, phone, role, invite_code, 
                             is_active, wallet_number, is_verified, created_at, last_activity) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        ''', (telegram_id, full_name, phone, role, invite_code, is_active_val, wallet_number, 1))
        
        user_id = cursor.lastrowid
        conn.commit()
        
        # Log user creation
        log_system_action(user_id, 'user_registration', f'New {role} registered: {full_name}')
        
        return user_id
    except sqlite3.IntegrityError as e:
        logger.error(f'Error creating user: {e}')
        return None
    finally:
        conn.close()

def _row_to_dict(cursor, row):
    """Convert database row to dictionary"""
    if row is None:
        return None
    columns = [col[0] for col in cursor.description]
    return dict(zip(columns, row))

def get_user(telegram_id):
    """Get user by Telegram ID"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT * FROM users WHERE telegram_id = ?', (telegram_id,))
        row = cursor.fetchone()
        return _row_to_dict(cursor, row)
    finally:
        conn.close()

def get_user_by_phone(phone):
    """Get user by phone number"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT * FROM users WHERE phone = ?', (phone,))
        row = cursor.fetchone()
        return _row_to_dict(cursor, row)
    finally:
        conn.close()

def get_user_by_wallet(wallet_number: str):
    """Get user by wallet number"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT * FROM users WHERE wallet_number = ?', (wallet_number,))
        row = cursor.fetchone()
        return _row_to_dict(cursor, row)
    finally:
        conn.close()

def get_user_by_id(user_id):
    """Get user by ID"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
        row = cursor.fetchone()
        return _row_to_dict(cursor, row)
    finally:
        conn.close()

def update_user_activity(user_id):
    """Update user's last activity timestamp"""
    try:
        execute_db_query(
            'UPDATE users SET last_activity = CURRENT_TIMESTAMP WHERE id = ?',
            (user_id,)
        )
    except Exception as e:
        logger.error(f"Error updating user activity: {e}")

def create_transaction(from_user_id, to_user_id, amount, txn_type, reference_id=None, 
                     is_withdrawable=False, description='', commission_amount=0.0):
    """Create transaction record"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        txn_id = str(uuid.uuid4())
        cursor.execute('''
            INSERT INTO transactions (id, from_user, to_user, amount, type, reference_id, 
                                    is_withdrawable, description, commission_amount) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (txn_id, from_user_id, to_user_id, amount, txn_type, reference_id, 
              1 if is_withdrawable else 0, description, commission_amount))
        conn.commit()
        return txn_id
    finally:
        conn.close()

def log_system_action(user_id, action, details='', ip_address='', user_agent=''):
    """Log system actions for monitoring"""
    try:
        execute_db_query('''
            INSERT INTO system_logs (user_id, action, details, ip_address, user_agent) 
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, action, details, ip_address, user_agent))
    except Exception as e:
        logger.error(f"Error logging system action: {e}")

def create_admin_notification(title, message, notification_type='info', created_by=None, target_admin=None):
    """Create admin notification"""
    try:
        notification_id = str(uuid.uuid4())
        execute_db_query('''
            INSERT INTO admin_notifications (id, title, message, type, created_by, target_admin) 
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (notification_id, title, message, notification_type, created_by, target_admin))
        return notification_id
    except Exception as e:
        logger.error(f"Error creating admin notification: {e}")
        return None

def setup_super_admin():
    """Setup super admin account"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT * FROM users WHERE telegram_id = ?', (7684780523,))
        admin = cursor.fetchone()
        if not admin:
            # Generate unique wallet for super admin
            wallet_number = None
            for _ in range(10):
                trial = '79' + ''.join(str(random.randint(0, 9)) for _ in range(7))
                cursor.execute('SELECT 1 FROM users WHERE wallet_number = ?', (trial,))
                if not cursor.fetchone():
                    wallet_number = trial
                    break
            
            cursor.execute('''
                INSERT INTO users (telegram_id, full_name, phone, role, is_active, 
                                 invite_code, wallet_number, is_verified) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (7684780523, 'المشرف الأعلى 👑', '000000000', 'super_admin', 1, 'ADMIN123', wallet_number, 1))
            conn.commit()
            logger.info('Super admin created successfully')
    finally:
        conn.close()

# Conversation states
(
    GET_FULL_NAME, GET_PHONE, CHOOSE_ROLE,
    SUPPLIER_MENU, AGENT_MENU, ADMIN_MENU, SUPER_ADMIN_MENU,
    UPLOAD_CARDS, CONFIRM_UPLOAD, SELECT_NETWORK, SELECT_CATEGORY, CONFIRM_PURCHASE,
    SELECT_CUSTOMER, GET_RECHARGE_AMOUNT, CONFIRM_RECHARGE,
    GET_WITHDRAW_AMOUNT, CONFIRM_WITHDRAWAL,
    ADMIN_ACTIVATE_ACCOUNTS, ADMIN_APPROVE_NETWORKS,
    ISSUE_TARGET, ISSUE_AMOUNT, ISSUE_CONFIRM,
    PASTE_CARDS, ADD_NETWORK_NAME, ADD_NETWORK_CITY, ADD_NETWORK_DESCRIPTION,
    TRANSFER_TARGET, TRANSFER_AMOUNT, TRANSFER_CONFIRM,
    SEARCH_NETWORK_INPUT, MANAGE_INVENTORY_MENU,
    VIEW_STATS_MENU, ADMIN_REPORTS_MENU,
) = range(33)

# Enhanced message templates
def format_user_info(user):
    """Format user information display"""
    role_emoji = {
        'customer': '👤',
        'agent': '🔷',
        'supplier': '🏪',
        'admin': '👨‍💼',
        'super_admin': '👑'
    }
    
    status = f"{EMOJIS['success']} مفعل" if user['is_active'] else f"{EMOJIS['warning']} غير مفعل"
    
    return f"""
{role_emoji.get(user['role'], '👤')} **{user['full_name']}**
{EMOJIS['phone']} الهاتف: {user['phone']}
{EMOJIS['wallet']} المحفظة: {user.get('wallet_number', 'غير محدد')}
{EMOJIS['money']} الرصيد: {user['balance']:.2f} ريال
{EMOJIS['stats']} المشتريات: {user.get('total_purchases', 0)}
📊 الحالة: {status}
{EMOJIS['date']} التسجيل: {user.get('created_at', 'غير محدد')[:10]}
"""

def format_network_info(network, supplier_name=''):
    """Format network information display"""
    status = f"{EMOJIS['success']} مفعلة" if network[5] else f"{EMOJIS['warning']} غير مفعلة"
    approval = f"{EMOJIS['success']} معتمدة" if network[6] else f"{EMOJIS['warning']} في انتظار الموافقة"
    
    return f"""
{EMOJIS['network']} **{network[2]}**
{EMOJIS['id']} الرمز: {network[7] if len(network) > 7 else 'غير محدد'}
{EMOJIS['user']} المزود: {supplier_name}
🏙️ المدينة: {network[3]}
📊 الحالة: {status}
✅ الاعتماد: {approval}
{EMOJIS['date']} الإنشاء: {network[8][:10] if len(network) > 8 else 'غير محدد'}
"""

# Enhanced UI functions
def create_main_keyboard(role):
    """Create main menu keyboard based on user role"""
    if role == 'customer':
        return [
            [InlineKeyboardButton(f'{EMOJIS["purchase"]} شراء كروت إنترنت', callback_data='buy_cards')],
            [InlineKeyboardButton(f'{EMOJIS["money"]} شحن رصيد', callback_data='recharge_balance')],
            [InlineKeyboardButton(f'{EMOJIS["transfer"]} تحويل لصديق', callback_data='transfer_to_friend')],
            [InlineKeyboardButton(f'{EMOJIS["user"]} دعوة أصدقاء', callback_data='invite_friends')],
            [InlineKeyboardButton(f'{EMOJIS["stats"]} إحصائياتي', callback_data='my_stats')],
            [InlineKeyboardButton(f'{EMOJIS["wallet"]} محفظتي', callback_data='show_balance')],
            [InlineKeyboardButton(f'❓ المساعدة', callback_data='customer_help')],
        ]
    elif role == 'supplier':
        return [
            [InlineKeyboardButton(f'{EMOJIS["upload"]} رفع كروت جديدة', callback_data='upload_cards')],
            [InlineKeyboardButton(f'📝 لصق أكواد يدوياً', callback_data='paste_cards')],
            [InlineKeyboardButton(f'{EMOJIS["network"]} إدارة الشبكات', callback_data='manage_networks')],
            [InlineKeyboardButton(f'{EMOJIS["settings"]} إدارة المخزون', callback_data='manage_inventory')],
            [InlineKeyboardButton(f'{EMOJIS["money"]} سحب الأرباح', callback_data='withdraw_earnings')],
            [InlineKeyboardButton(f'{EMOJIS["stats"]} تقارير المبيعات', callback_data='sales_reports')],
        ]
    elif role == 'agent':
        return [
            [InlineKeyboardButton(f'🔋 شحن عملاء', callback_data='recharge_customers')],
            [InlineKeyboardButton(f'{EMOJIS["purchase"]} شراء للعملاء', callback_data='buy_for_customers')],
            [InlineKeyboardButton(f'{EMOJIS["money"]} سحب الأرباح', callback_data='agent_withdraw')],
            [InlineKeyboardButton(f'{EMOJIS["stats"]} سجل العمولات', callback_data='commission_history')],
            [InlineKeyboardButton(f'👥 إدارة العملاء', callback_data='manage_customers')],
        ]
    elif role == 'admin':
        return [
            [InlineKeyboardButton(f'{EMOJIS["user"]} تفعيل حسابات', callback_data='activate_accounts')],
            [InlineKeyboardButton(f'{EMOJIS["network"]} موافقة شبكات', callback_data='approve_networks')],
            [InlineKeyboardButton(f'🔍 مراقبة التحويلات', callback_data='monitor_transactions')],
            [InlineKeyboardButton(f'💼 طلبات السحب', callback_data='withdrawal_requests')],
            [InlineKeyboardButton(f'{EMOJIS["stats"]} التقارير الإدارية', callback_data='admin_reports')],
            [InlineKeyboardButton(f'🔔 الإشعارات', callback_data='admin_notifications')],
        ]
    elif role == 'super_admin':
        return [
            [InlineKeyboardButton(f'{EMOJIS["admin"]} إدارة المشرفين', callback_data='manage_admins')],
            [InlineKeyboardButton(f'{EMOJIS["settings"]} إعدادات النظام', callback_data='system_settings')],
            [InlineKeyboardButton(f'💾 النسخ الاحتياطي', callback_data='backup_database')],
            [InlineKeyboardButton(f'{EMOJIS["stats"]} التقارير الشاملة', callback_data='global_reports')],
            [InlineKeyboardButton(f'{EMOJIS["money"]} إصدار رصيد', callback_data='issue_balance')],
            [InlineKeyboardButton(f'📊 إحصائيات المنصة', callback_data='platform_stats')],
        ]
    
    return [[InlineKeyboardButton(f'{EMOJIS["home"]} القائمة الرئيسية', callback_data='main_menu')]]

# Handler functions start here

async def start(update: Update, context: CallbackContext) -> int:
    """Start command handler with enhanced welcome message"""
    try:
        user = get_user(update.effective_user.id)
        
        if user:
            update_user_activity(user['id'])
            role = user['role']
            
            welcome_message = f"""
{EMOJIS['star']} **مرحباً بك {user['full_name']}!** {EMOJIS['star']}

{format_user_info(user)}

{EMOJIS['fire']} اختر من القائمة أدناه:
"""
            
            keyboard = create_main_keyboard(role)
            keyboard.append([InlineKeyboardButton(f'{EMOJIS["home"]} القائمة الرئيسية', callback_data='main_menu')])
            
            if update.message:
                await update.message.reply_text(welcome_message, 
                                              reply_markup=InlineKeyboardMarkup(keyboard),
                                              parse_mode='Markdown')
            else:
                await update.callback_query.edit_message_text(welcome_message,
                                                            reply_markup=InlineKeyboardMarkup(keyboard),
                                                            parse_mode='Markdown')
            return ConversationHandler.END
        
        # Handle referral codes
        if context.args and context.args[0].startswith('ref_'):
            context.user_data['referral_code'] = context.args[0][4:]
        
        welcome_text = f"""
{EMOJIS['star']} **مرحباً بك في بوت كروت الإنترنت اليمني!** {EMOJIS['network']}

{EMOJIS['new']} للبدء، يرجى إدخال اسمك الرباعي الكامل:
{EMOJIS['warning']} مثال: أحمد محمد علي سالم
"""
        
        await update.message.reply_text(welcome_text, 
                                      reply_markup=ReplyKeyboardRemove(),
                                      parse_mode='Markdown')
        return GET_FULL_NAME
        
    except Exception as e:
        logger.error(f"Error in start handler: {e}")
        await update.message.reply_text(f"{EMOJIS['error']} حدث خطأ. يرجى المحاولة مرة أخرى.")
        return ConversationHandler.END

async def get_full_name(update: Update, context: CallbackContext) -> int:
    """Get user's full name with validation"""
    try:
        full_name = update.message.text.strip()
        
        # Validate Arabic name with at least 4 parts
        if len(full_name.split()) < 4:
            await update.message.reply_text(
                f"{EMOJIS['warning']} يرجى إدخال الاسم الرباعي كاملاً (أربعة أجزاء على الأقل)\n"
                f"مثال: أحمد محمد علي سالم"
            )
            return GET_FULL_NAME
        
        # Basic Arabic name validation
        if not re.match(r'^[\u0600-\u06FF\s]+$', full_name):
            await update.message.reply_text(
                f"{EMOJIS['warning']} يرجى إدخال الاسم باللغة العربية فقط"
            )
            return GET_FULL_NAME
        
        context.user_data['full_name'] = full_name
        
        phone_text = f"""
{EMOJIS['phone']} **الآن أدخل رقم هاتفك:**

{EMOJIS['warning']} **مهم:** أدخل 9 أرقام فقط (بدون الصفر الأول)
{EMOJIS['star']} مثال: 733456789

أو اختر من الأمثلة أدناه:
"""
        
        await update.message.reply_text(
            phone_text,
            reply_markup=ReplyKeyboardMarkup([
                ['711234567', '733456789', '755678901'],
                ['777890123', '799012345', '70123456'],
            ], one_time_keyboard=True, resize_keyboard=True),
            parse_mode='Markdown'
        )
        return GET_PHONE
        
    except Exception as e:
        logger.error(f"Error in get_full_name: {e}")
        await update.message.reply_text(f"{EMOJIS['error']} حدث خطأ. يرجى المحاولة مرة أخرى.")
        return ConversationHandler.END

async def get_phone(update: Update, context: CallbackContext) -> int:
    """Get and validate phone number"""
    try:
        phone = update.message.text.strip()
        
        # Validate Yemen phone number format
        if not re.fullmatch(r'[7][0-9]{8}', phone):
            await update.message.reply_text(
                f"{EMOJIS['warning']} **رقم الهاتف غير صحيح!**\n\n"
                f"يرجى إدخال رقم يمني صحيح:\n"
                f"• 9 أرقام تبدأ بالرقم 7\n"
                f"• بدون الصفر الأول\n"
                f"• مثال: 733456789",
                parse_mode='Markdown'
            )
            return GET_PHONE
        
        # Check if phone already exists
        if get_user_by_phone(phone):
            await update.message.reply_text(
                f"{EMOJIS['warning']} **هذا الرقم مسجل مسبقاً!**\n"
                f"يرجى استخدام رقم آخر أو التواصل مع الدعم إذا كان هذا رقمك."
            )
            return GET_PHONE
        
        context.user_data['phone'] = phone
        
        role_text = f"""
{EMOJIS['user']} **اختر دورك في المنصة:**

{EMOJIS['star']} **العميل:** شراء كروت الإنترنت
{EMOJIS['cool']} **الوكيل:** بيع الكروت والحصول على عمولة  
{EMOJIS['fire']} **المزود:** توفير كروت الإنترنت
"""
        
        await update.message.reply_text(
            role_text,
            reply_markup=ReplyKeyboardMarkup([
                [f"{EMOJIS['user']} عميل", f"{EMOJIS['cool']} وكيل", f"{EMOJIS['fire']} مزود"]
            ], one_time_keyboard=True, resize_keyboard=True),
            parse_mode='Markdown'
        )
        return CHOOSE_ROLE
        
    except Exception as e:
        logger.error(f"Error in get_phone: {e}")
        await update.message.reply_text(f"{EMOJIS['error']} حدث خطأ. يرجى المحاولة مرة أخرى.")
        return ConversationHandler.END

async def choose_role(update: Update, context: CallbackContext) -> int:
    """Handle role selection with enhanced validation"""
    try:
        role_choice = update.message.text.strip()
        role_map = {
            f"{EMOJIS['user']} عميل": 'customer',
            f"{EMOJIS['cool']} وكيل": 'agent', 
            f"{EMOJIS['fire']} مزود": 'supplier',
            'عميل': 'customer',
            'وكيل': 'agent',
            'مزود': 'supplier'
        }
        
        if role_choice not in role_map:
            await update.message.reply_text(
                f"{EMOJIS['warning']} اختيار غير صحيح! يرجى الاختيار من القائمة.",
                reply_markup=ReplyKeyboardMarkup([
                    [f"{EMOJIS['user']} عميل", f"{EMOJIS['cool']} وكيل", f"{EMOJIS['fire']} مزود"]
                ], one_time_keyboard=True, resize_keyboard=True)
            )
            return CHOOSE_ROLE
        
        role = role_map[role_choice]
        full_name = context.user_data['full_name']
        phone = context.user_data['phone']
        telegram_id = update.effective_user.id
        
        # Auto-activate customers, require approval for agents/suppliers
        is_active = True if role == 'customer' else False
        
        user_id = create_user(telegram_id, full_name, phone, role, is_active)
        
        if not user_id:
            await update.message.reply_text(
                f"{EMOJIS['error']} **حدث خطأ أثناء التسجيل!**\n"
                f"يرجى المحاولة لاحقاً أو التواصل مع الدعم.",
                parse_mode='Markdown'
            )
            return ConversationHandler.END
        
        # Handle referral
        referral_code = context.user_data.get('referral_code')
        if referral_code:
            conn = get_db_connection()
            cursor = conn.cursor()
            try:
                cursor.execute('SELECT id, full_name FROM users WHERE invite_code = ?', (referral_code,))
                referrer = cursor.fetchone()
                if referrer:
                    referrer_id = referrer[0]
                    referral_id = str(uuid.uuid4())
                    cursor.execute('''
                        INSERT INTO referrals (id, referrer_id, referred_id, bonus_amount) 
                        VALUES (?, ?, ?, ?)
                    ''', (referral_id, referrer_id, user_id, 100.0))  # 100 riyal bonus
                    conn.commit()
                    
                    await update.message.reply_text(
                        f"{EMOJIS['success']} تم تسجيلك بدعوة من **{referrer[1]}**!\n"
                        f"{EMOJIS['money']} ستحصل على مكافأة عند أول شحن!",
                        parse_mode='Markdown'
                    )
            finally:
                conn.close()
        
        # Success message
        role_names = {'customer': 'عميل', 'agent': 'وكيل', 'supplier': 'مزود'}
        success_message = f"""
{EMOJIS['success']} **تم تسجيلك بنجاح كـ {role_names[role]}!**

{EMOJIS['user']} الاسم: {full_name}
{EMOJIS['phone']} الهاتف: {phone}
{EMOJIS['wallet']} رقم المحفظة: {get_user(telegram_id)['wallet_number']}
"""
        
        if role in ['agent', 'supplier']:
            success_message += f"""
{EMOJIS['warning']} **انتظار التفعيل:**
سيتم مراجعة طلبك من قبل الإدارة خلال 24 ساعة.
سيتم إشعارك فور الموافقة على حسابك.
"""
            # Notify admins
            await notify_admins(context, f"""
{EMOJIS['new']} **طلب تفعيل حساب جديد**

{EMOJIS['user']} الاسم: {full_name}
{EMOJIS['phone']} الهاتف: {phone}
{EMOJIS['star']} الدور: {role_names[role]}
{EMOJIS['id']} معرف التلغرام: {telegram_id}
{EMOJIS['date']} وقت التسجيل: {datetime.now().strftime('%Y-%m-%d %H:%M')}

للموافقة: /approve_user_{user_id}
""")
        
        # Get updated user data and show invite link
        user = get_user(telegram_id)
        invite_link = f"https://t.me/Vsjsgshh_bot?start=ref_{user['invite_code']}"
        
        success_message += f"""
{EMOJIS['user']} **رابط دعوتك:**
{invite_link}

{EMOJIS['money']} احصل على مكافآت من دعوة الأصدقاء!
"""
        
        await update.message.reply_text(
            success_message,
            reply_markup=ReplyKeyboardRemove(),
            parse_mode='Markdown'
        )
        
        # Show appropriate menu
        return await show_main_menu(update, context, role)
        
    except Exception as e:
        logger.error(f"Error in choose_role: {e}")
        await update.message.reply_text(f"{EMOJIS['error']} حدث خطأ. يرجى المحاولة مرة أخرى.")
        return ConversationHandler.END

async def show_main_menu(update: Update, context: CallbackContext, role: str):
    """Show main menu based on user role"""
    try:
        user = get_user(update.effective_user.id)
        if not user:
            return await start(update, context)
        
        update_user_activity(user['id'])
        
        # Recalculate balance
        recalc_and_set_user_balance(user['id'])
        user = get_user(update.effective_user.id)  # Refresh user data
        
        role_emojis = {
            'customer': '👤',
            'agent': '🔷', 
            'supplier': '🏪',
            'admin': '👨‍💼',
            'super_admin': '👑'
        }
        
        role_names = {
            'customer': 'العميل',
            'agent': 'الوكيل',
            'supplier': 'المزود',
            'admin': 'المشرف',
            'super_admin': 'المشرف الأعلى'
        }
        
        menu_text = f"""
{role_emojis.get(role, '👤')} **لوحة تحكم {role_names.get(role, 'المستخدم')}**

{EMOJIS['user']} مرحباً **{user['full_name']}**
{EMOJIS['wallet']} رصيدك: **{user['balance']:.2f}** ريال
{EMOJIS['id']} محفظتك: `{user['wallet_number']}`

{EMOJIS['fire']} اختر الإجراء المطلوب:
"""
        
        keyboard = create_main_keyboard(role)
        
        if update.message:
            await update.message.reply_text(
                menu_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
        else:
            await update.callback_query.edit_message_text(
                menu_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
        
        return ConversationHandler.END
        
    except Exception as e:
        logger.error(f"Error in show_main_menu: {e}")
        error_text = f"{EMOJIS['error']} حدث خطأ في تحميل القائمة. يرجى المحاولة مرة أخرى."
        
        if update.message:
            await update.message.reply_text(error_text)
        else:
            await update.callback_query.edit_message_text(error_text)
        
        return ConversationHandler.END

# ... continuing with rest of the handlers ...

# Utility functions for admin notifications
async def notify_admins(context: CallbackContext, message: str):
    """Send notification to super admin"""
    try:
        logger.info(f'Admin Notification: {message}')
        await context.bot.send_message(chat_id=7684780523, text=message, parse_mode='Markdown')
        
        # Also create admin notification in database
        create_admin_notification(
            title="إشعار إداري جديد", 
            message=message, 
            notification_type='info'
        )
    except Exception as e:
        logger.error(f"Error sending admin notification: {e}")

# Enhanced handler functions

async def cancel(update: Update, context: CallbackContext) -> int:
    """Cancel current operation"""
    try:
        message = f"{EMOJIS['cancel']} تم إلغاء العملية."
        
        if update.message:
            await update.message.reply_text(message, reply_markup=ReplyKeyboardRemove())
        else:
            await update.callback_query.edit_message_text(message)
        
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"Error in cancel handler: {e}")
        return ConversationHandler.END

async def main_menu_handler(update: Update, context: CallbackContext) -> int:
    """Handle main menu button press"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if user:
            return await show_main_menu(update, context, user['role'])
        
        return await start(update, context)
    except Exception as e:
        logger.error(f"Error in main menu handler: {e}")
        await update.callback_query.edit_message_text(f"{EMOJIS['error']} حدث خطأ. يرجى المحاولة مرة أخرى.")
        return ConversationHandler.END

# Quick menu and balance display
async def quick_menu(update: Update, context: CallbackContext) -> int:
    """Show quick menu for fast access"""
    try:
        user = get_user(update.effective_user.id)
        if not user:
            return await start(update, context)
        
        update_user_activity(user['id'])
        
        buttons = [
            [InlineKeyboardButton(f'{EMOJIS["home"]} القائمة الرئيسية', callback_data='main_menu')],
            [InlineKeyboardButton(f'{EMOJIS["wallet"]} رصيدي', callback_data='show_balance')],
            [InlineKeyboardButton(f'{EMOJIS["purchase"]} شراء كرت', callback_data='buy_cards')],
            [InlineKeyboardButton(f'{EMOJIS["transfer"]} تحويل رصيد', callback_data='transfer_to_friend')],
            [InlineKeyboardButton(f'{EMOJIS["stats"]} إحصائياتي', callback_data='my_stats')],
        ]
        
        text = f"""
{EMOJIS['fire']} **القائمة السريعة**

{EMOJIS['user']} مرحباً **{user['full_name']}**
{EMOJIS['wallet']} رصيدك: **{user['balance']:.2f}** ريال

اختر الإجراء المطلوب:
"""
        
        if update.message:
            await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode='Markdown')
        else:
            await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode='Markdown')
        
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"Error in quick menu: {e}")
        error_msg = f"{EMOJIS['error']} حدث خطأ في تحميل القائمة السريعة."
        
        if update.message:
            await update.message.reply_text(error_msg)
        else:
            await update.callback_query.edit_message_text(error_msg)
        
        return ConversationHandler.END

async def show_balance(update: Update, context: CallbackContext) -> int:
    """Show user balance and wallet info"""
    try:
        user = get_user(update.effective_user.id)
        if not user:
            return await start(update, context)
        
        # Recalculate and update balance
        recalc_and_set_user_balance(user['id'])
        user = get_user(update.effective_user.id)  # Refresh data
        
        update_user_activity(user['id'])
        
        # Get additional stats
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT COUNT(*), COALESCE(SUM(amount),0) FROM transactions WHERE from_user = ? AND type = 'card_purchase'", (user['id'],))
            purchases_count, purchases_total = cursor.fetchone()
            
            cursor.execute("SELECT COALESCE(SUM(amount),0) FROM transactions WHERE to_user = ? AND type != 'card_purchase'", (user['id'],))
            incoming_total = cursor.fetchone()[0] or 0
            
            cursor.execute("SELECT COALESCE(SUM(amount),0) FROM transactions WHERE from_user = ? AND type = 'p2p_transfer'", (user['id'],))
            outgoing_transfers = cursor.fetchone()[0] or 0
            
            cursor.execute("SELECT COUNT(*) FROM referrals WHERE referrer_id = ?", (user['id'],))
            referrals_count = cursor.fetchone()[0] or 0
            
            cursor.execute("SELECT COALESCE(SUM(bonus_amount),0) FROM referrals WHERE referrer_id = ? AND awarded = 1", (user['id'],))
            referral_earnings = cursor.fetchone()[0] or 0
            
            # Get last transaction
            cursor.execute("SELECT type, amount, created_at FROM transactions WHERE from_user = ? OR to_user = ? ORDER BY created_at DESC LIMIT 1", (user['id'], user['id']))
            last_transaction = cursor.fetchone()
        finally:
            conn.close()
        
        last_tx_text = "لا توجد معاملات"
        if last_transaction:
            tx_type_map = {
                'card_purchase': 'شراء كرت',
                'p2p_transfer': 'تحويل رصيد',
                'wallet_recharge': 'شحن رصيد',
                'agent_commission': 'عمولة وكيل'
            }
            tx_type = tx_type_map.get(last_transaction[0], last_transaction[0])
            last_tx_text = f"{tx_type} - {last_transaction[1]} ريال ({last_transaction[2][:10]})"
        
        role_names = {
            'customer': 'عميل',
            'agent': 'وكيل',
            'supplier': 'مزود',
            'admin': 'مشرف',
            'super_admin': 'مشرف أعلى'
        }
        
        text = f"""
{EMOJIS['wallet']} **معلومات المحفظة**

{EMOJIS['user']} الاسم: **{user['full_name']}**
{EMOJIS['wallet']} رقم المحفظة: `{user['wallet_number']}`
{EMOJIS['money']} الرصيد الحالي: **{user['balance']:.2f}** ريال

{EMOJIS['stats']} **الإحصائيات:**
{EMOJIS['purchase']} عدد المشتريات: **{purchases_count}**
{EMOJIS['money']} إجمالي الإنفاق: **{purchases_total:.2f}** ريال

{EMOJIS['transfer']} **التحويلات:**
التحويلات الصادرة: **{outgoing_transfers:.2f}** ريال
التحويلات الواردة: **{incoming_total:.2f}** ريال

{EMOJIS['user']} **الإحالات:**
عدد الدعوات: **{referrals_count}**
أرباح الإحالة: **{referral_earnings:.2f}** ريال

{EMOJIS['time']} **آخر معاملة:**
{last_tx_text}

{EMOJIS['date']} **تاريخ التسجيل:**
{user.get('created_at', 'غير محدد')[:10]}
"""
        
        keyboard = [
            [InlineKeyboardButton(f'{EMOJIS["purchase"]} شراء كرت', callback_data='buy_cards')],
            [InlineKeyboardButton(f'{EMOJIS["transfer"]} تحويل رصيد', callback_data='transfer_to_friend')],
            [InlineKeyboardButton(f'{EMOJIS["user"]} دعوة أصدقاء', callback_data='invite_friends')],
            [InlineKeyboardButton(f'{EMOJIS["home"]} القائمة الرئيسية', callback_data='main_menu')]
        ]
        
        if update.message:
            await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        else:
            await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"Error in show_balance: {e}")
        error_msg = f"{EMOJIS['error']} حدث خطأ في عرض الرصيد."
        
        if update.message:
            await update.message.reply_text(error_msg)
        else:
            await update.callback_query.edit_message_text(error_msg)
        
        return ConversationHandler.END

# Network and supplier functions
async def _ensure_supplier_network(cursor: sqlite3.Cursor, supplier_user_id: int) -> str:
    """Ensure supplier has a default network"""
    cursor.execute('SELECT id FROM networks WHERE supplier_id = ?', (supplier_user_id,))
    row = cursor.fetchone()
    if row:
        return row[0]
    
    # Generate unique network code
    network_code = None
    for _ in range(20):
        code = ''.join(str(random.randint(0, 9)) for _ in range(5))
        cursor.execute('SELECT 1 FROM networks WHERE network_code = ?', (code,))
        if not cursor.fetchone():
            network_code = code
            break
    
    if not network_code:
        raise RuntimeError('Failed to generate unique network code')
    
    network_id = str(uuid.uuid4())
    cursor.execute('''
        INSERT INTO networks (id, supplier_id, name, city, network_code, is_active, is_approved) 
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (network_id, supplier_user_id, 'شبكة المزود الافتراضية', 'غير محدد', network_code, 0, 0))
    
    return network_id

# Card management functions
async def buy_cards(update: Update, context: CallbackContext) -> int:
    """Handle card purchase flow"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user:
            await query.edit_message_text(f"{EMOJIS['error']} يرجى التسجيل أولاً.")
            return ConversationHandler.END
        
        update_user_activity(user['id'])
        
        loading_msg = await query.edit_message_text(f"{EMOJIS['loading']} جاري تحميل الشبكات المتاحة...")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                SELECT n.id, n.name, n.network_code, u.full_name 
                FROM networks n 
                JOIN users u ON n.supplier_id = u.id 
                WHERE n.is_active = 1 AND n.is_approved = 1
            ''')
            networks = cursor.fetchall()
        finally:
            conn.close()
        
        if not networks:
            await context.bot.edit_message_text(
                chat_id=query.message.chat_id, 
                message_id=loading_msg.message_id, 
                text=f"{EMOJIS['warning']} لا تتوفر شبكات مفعلة حالياً. يرجى المحاولة لاحقاً."
            )
            return ConversationHandler.END
        
        keyboard = []
        for network in networks:
            network_text = f"{EMOJIS['network']} {network[1]} ({network[2]})"
            keyboard.append([InlineKeyboardButton(network_text, callback_data=f'network_{network[0]}')])
        
        keyboard.append([InlineKeyboardButton(f'{EMOJIS["search"]} بحث بالرمز', callback_data='search_networks')])
        keyboard.append([InlineKeyboardButton(f'{EMOJIS["cancel"]} إلغاء', callback_data='main_menu')])
        
        text = f"""
{EMOJIS['purchase']} **شراء كروت الإنترنت**

{EMOJIS['network']} اختر الشبكة المطلوبة:
{EMOJIS['star']} يمكنك البحث بالرمز المكون من 5 أرقام
"""
        
        await context.bot.edit_message_text(
            chat_id=query.message.chat_id, 
            message_id=loading_msg.message_id, 
            text=text, 
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
        return SELECT_NETWORK
    except Exception as e:
        logger.error(f"Error in buy_cards: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في تحميل الشبكات.")
        return ConversationHandler.END

async def select_category(update: Update, context: CallbackContext) -> int:
    """Handle network selection and show categories"""
    try:
        query = update.callback_query
        await query.answer()
        
        network_id = query.data.split('_')[1]
        context.user_data['selected_network'] = network_id
        
        loading_msg = await query.edit_message_text(f"{EMOJIS['loading']} جاري تحميل الفئات المتاحة...")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            # Get network info
            cursor.execute('SELECT name, network_code FROM networks WHERE id = ?', (network_id,))
            network_info = cursor.fetchone()
            
            # Get available categories
            cursor.execute('''
                SELECT id, value, price, category_name 
                FROM card_categories 
                WHERE network_id = ? AND is_available = 1
            ''', (network_id,))
            categories = cursor.fetchall()
        finally:
            conn.close()
        
        if not categories:
            await context.bot.edit_message_text(
                chat_id=query.message.chat_id, 
                message_id=loading_msg.message_id, 
                text=f"{EMOJIS['warning']} لا تتوفر فئات كروت لهذه الشبكة حالياً.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(f'{EMOJIS["back"]} رجوع', callback_data='buy_cards')]])
            )
            return ConversationHandler.END
        
        keyboard = []
        for category in categories:
            category_name = category[3] if category[3] else f"فئة {category[1]} ريال"
            category_text = f"{EMOJIS['card']} {category_name} - {category[2]} ريال"
            keyboard.append([InlineKeyboardButton(category_text, callback_data=f'category_{category[0]}')])
        
        keyboard.append([InlineKeyboardButton(f'{EMOJIS["back"]} رجوع', callback_data='buy_cards')])
        keyboard.append([InlineKeyboardButton(f'{EMOJIS["cancel"]} إلغاء', callback_data='main_menu')])
        
        text = f"""
{EMOJIS['purchase']} **اختيار فئة الكرت**

{EMOJIS['network']} الشبكة: **{network_info[0]}** ({network_info[1]})

{EMOJIS['money']} اختر الفئة السعرية:
"""
        
        await context.bot.edit_message_text(
            chat_id=query.message.chat_id, 
            message_id=loading_msg.message_id, 
            text=text, 
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
        return SELECT_CATEGORY
    except Exception as e:
        logger.error(f"Error in select_category: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في تحميل الفئات.")
        return ConversationHandler.END

async def confirm_purchase(update: Update, context: CallbackContext) -> int:
    """Show purchase confirmation"""
    try:
        query = update.callback_query
        await query.answer()
        
        category_id = query.data.split('_')[1]
        context.user_data['selected_category'] = category_id
        
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                SELECT cc.value, cc.price, cc.category_name, n.name, n.network_code 
                FROM card_categories cc 
                JOIN networks n ON cc.network_id = n.id 
                WHERE cc.id = ?
            ''', (category_id,))
            row = cursor.fetchone()
            
            if not row:
                await query.edit_message_text(f"{EMOJIS['error']} الفئة المحددة غير متوفرة!")
                return ConversationHandler.END
            
            value, price, category_name, network_name, network_code = row
            
            # Check card availability
            cursor.execute('SELECT COUNT(*) FROM cards WHERE category_id = ? AND is_used = 0', (category_id,))
            available_cards = cursor.fetchone()[0] or 0
        finally:
            conn.close()
        
        user = get_user(query.from_user.id)
        balance = user['balance']
        
        if available_cards == 0:
            await query.edit_message_text(
                f"{EMOJIS['warning']} **عذراً، الكروت نفذت لهذه الفئة!**\n\n"
                f"يرجى اختيار فئة أخرى أو المحاولة لاحقاً.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(f'{EMOJIS["back"]} اختيار فئة أخرى', callback_data=f'network_{context.user_data.get("selected_network")}')],
                    [InlineKeyboardButton(f'{EMOJIS["home"]} القائمة الرئيسية', callback_data='main_menu')]
                ]),
                parse_mode='Markdown'
            )
            return ConversationHandler.END
        
        if balance < price:
            await query.edit_message_text(
                f"{EMOJIS['warning']} **رصيدك غير كافي!**\n\n"
                f"{EMOJIS['card']} سعر الكرت: **{price}** ريال\n"
                f"{EMOJIS['wallet']} رصيدك الحالي: **{balance}** ريال\n\n"
                f"يرجى شحن رصيدك أولاً.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(f'{EMOJIS["money"]} شحن الرصيد', callback_data='recharge_balance')],
                    [InlineKeyboardButton(f'{EMOJIS["home"]} القائمة الرئيسية', callback_data='main_menu')]
                ]),
                parse_mode='Markdown'
            )
            return ConversationHandler.END
        
        category_display = category_name if category_name else f"فئة {value} ريال"
        
        text = f"""
{EMOJIS['purchase']} **تأكيد الشراء**

{EMOJIS['network']} الشبكة: **{network_name}** ({network_code})
{EMOJIS['card']} الفئة: **{category_display}**
{EMOJIS['money']} القيمة: **{value}** ريال
{EMOJIS['wallet']} السعر: **{price}** ريال

{EMOJIS['user']} رصيدك الحالي: **{balance}** ريال
{EMOJIS['stats']} الرصيد بعد الشراء: **{balance - price}** ريال
{EMOJIS['card']} الكروت المتاحة: **{available_cards}**

هل تريد تأكيد الشراء؟
"""
        
        keyboard = [
            [InlineKeyboardButton(f'{EMOJIS["confirm"]} تأكيد الشراء', callback_data='complete_purchase')],
            [InlineKeyboardButton(f'{EMOJIS["back"]} رجوع', callback_data=f'network_{context.user_data.get("selected_network")}')],
            [InlineKeyboardButton(f'{EMOJIS["cancel"]} إلغاء', callback_data='main_menu')]
        ]
        
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        return CONFIRM_PURCHASE
    except Exception as e:
        logger.error(f"Error in confirm_purchase: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في تأكيد الشراء.")
        return ConversationHandler.END

async def complete_purchase(update: Update, context: CallbackContext) -> int:
    """Complete the card purchase"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        category_id = context.user_data.get('selected_category')
        
        if not category_id:
            await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في عملية الشراء.")
            return ConversationHandler.END
        
        processing_msg = await query.edit_message_text(f"{EMOJIS['loading']} جاري معالجة عملية الشراء...")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            # Get category and network info
            cursor.execute('''
                SELECT cc.price, cc.value, n.supplier_id, n.name 
                FROM card_categories cc 
                JOIN networks n ON cc.network_id = n.id 
                WHERE cc.id = ?
            ''', (category_id,))
            row = cursor.fetchone()
            
            if not row:
                await context.bot.edit_message_text(
                    chat_id=query.message.chat_id,
                    message_id=processing_msg.message_id,
                    text=f"{EMOJIS['error']} الفئة المحددة غير متوفرة!"
                )
                return ConversationHandler.END
            
            price, value, supplier_id, network_name = row
            
            # Get available card
            cursor.execute('SELECT id, code FROM cards WHERE category_id = ? AND is_used = 0 LIMIT 1', (category_id,))
            card = cursor.fetchone()
            
            if not card:
                await context.bot.edit_message_text(
                    chat_id=query.message.chat_id,
                    message_id=processing_msg.message_id,
                    text=f"{EMOJIS['warning']} عذراً، الكروت نفذت لهذه الفئة!"
                )
                return ConversationHandler.END
            
            card_id, encrypted_code = card
            decrypted_code = decrypt_data(encrypted_code)
            
            # Perform accounting transactions
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
            
            supplier_share = round(price * (1.0 - CARD_COMMISSION_RATE), 2)
            bot_commission = round(price * CARD_COMMISSION_RATE, 2)
            
            # Mark card as used and update user stats
            cursor.execute('UPDATE cards SET is_used = 1, used_at = CURRENT_TIMESTAMP, used_by = ? WHERE id = ?', (user['id'], card_id))
            cursor.execute('UPDATE users SET total_purchases = total_purchases + 1, total_spent = total_spent + ? WHERE id = ?', (price, user['id']))
            
            conn.commit()
        finally:
            conn.close()
        
        # Post journal entries
        post_journal(
            description=f'Card purchase {card_id} by user {user["id"]}',
            created_by=user['id'],
            lines=[
                {'account_id': buyer_acc, 'debit': price, 'credit': 0.0, 'user_id': user['id'], 'ref_type': 'card_purchase', 'ref_id': card_id},
                {'account_id': supplier_acc, 'debit': 0.0, 'credit': supplier_share, 'user_id': supplier_id, 'ref_type': 'card_purchase', 'ref_id': card_id},
                {'account_id': commission_acc, 'debit': 0.0, 'credit': bot_commission, 'user_id': None, 'ref_type': 'card_purchase', 'ref_id': card_id},
            ],
        )
        
        # Create transaction record
        create_transaction(
            user['id'], supplier_id, price, 'card_purchase', card_id,
            description=f'Purchase of {value} riyal card from {network_name}',
            commission_amount=bot_commission
        )
        
        # Update balances
        recalc_and_set_user_balance(user['id'])
        recalc_and_set_user_balance(supplier_id)
        
        # Log the purchase
        log_system_action(user['id'], 'card_purchase', f'Purchased card {card_id} for {price} riyal')
        
        # Send success message
        await context.bot.edit_message_text(
            chat_id=query.message.chat_id,
            message_id=processing_msg.message_id,
            text=f"{EMOJIS['success']} **تم الشراء بنجاح!**\n\nكود الكرت سيرسل لك في الرسالة التالية...",
            parse_mode='Markdown'
        )
        
        # Send card code in separate message for security
        card_message = f"""
{EMOJIS['card']} **كود الكرت الخاص بك:**

`{decrypted_code}`

{EMOJIS['network']} الشبكة: **{network_name}**
{EMOJIS['money']} القيمة: **{value}** ريال

{EMOJIS['warning']} **تنبيه مهم:**
• احفظ الكود في مكان آمن
• لا تشارك الكود مع أحد
• استخدم الكود قبل انتهاء صلاحيته
"""
        
        await context.bot.send_message(
            chat_id=query.message.chat_id, 
            text=card_message,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(f'{EMOJIS["purchase"]} شراء كرت آخر', callback_data='buy_cards')],
                [InlineKeyboardButton(f'{EMOJIS["home"]} القائمة الرئيسية', callback_data='main_menu')]
            ]),
            parse_mode='Markdown'
        )
        
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"Error completing purchase: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ أثناء عملية الشراء. يرجى المحاولة لاحقاً.")
        return ConversationHandler.END

# Transfer functionality
async def transfer_to_friend_handler(update: Update, context: CallbackContext) -> int:
    """Start transfer process"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user:
            await query.edit_message_text(f"{EMOJIS['error']} يرجى التسجيل أولاً.")
            return ConversationHandler.END
        
        update_user_activity(user['id'])
        
        # Recalculate balance
        recalc_and_set_user_balance(user['id'])
        user = get_user(query.from_user.id)  # Refresh data
        
        if user['balance'] <= 0:
            await query.edit_message_text(
                f"{EMOJIS['warning']} **رصيدك غير كافي للتحويل!**\n\n"
                f"{EMOJIS['wallet']} رصيدك الحالي: **{user['balance']:.2f}** ريال\n\n"
                f"يرجى شحن رصيدك أولاً.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(f'{EMOJIS["money"]} شحن الرصيد', callback_data='recharge_balance')],
                    [InlineKeyboardButton(f'{EMOJIS["home"]} القائمة الرئيسية', callback_data='main_menu')]
                ]),
                parse_mode='Markdown'
            )
            return ConversationHandler.END
        
        text = f"""
{EMOJIS['transfer']} **تحويل رصيد لصديق**

{EMOJIS['wallet']} رصيدك الحالي: **{user['balance']:.2f}** ريال

{EMOJIS['id']} أدخل رقم محفظة المستلم:
{EMOJIS['star']} يجب أن يكون 9 أرقام ويبدأ بـ 79
{EMOJIS['warning']} مثال: 791234567

أو اكتب /cancel للإلغاء
"""
        
        await query.edit_message_text(text, parse_mode='Markdown')
        return TRANSFER_TARGET
    except Exception as e:
        logger.error(f"Error in transfer_to_friend_handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في بدء التحويل.")
        return ConversationHandler.END

async def transfer_target(update: Update, context: CallbackContext) -> int:
    """Get transfer target wallet"""
    try:
        wallet = update.message.text.strip()
        
        if wallet.lower() == '/cancel':
            return await cancel(update, context)
        
        if not re.fullmatch(r'79\d{7}', wallet):
            await update.message.reply_text(
                f"{EMOJIS['warning']} **رقم المحفظة غير صحيح!**\n\n"
                f"يرجى إدخال رقم محفظة صحيح:\n"
                f"• 9 أرقام تبدأ بـ 79\n"
                f"• مثال: 791234567\n\n"
                f"أعد المحاولة أو اكتب /cancel للإلغاء",
                parse_mode='Markdown'
            )
            return TRANSFER_TARGET
        
        sender = get_user(update.message.from_user.id)
        if wallet == sender['wallet_number']:
            await update.message.reply_text(
                f"{EMOJIS['warning']} **لا يمكنك التحويل لنفسك!**\n\n"
                f"يرجى إدخال رقم محفظة مختلف."
            )
            return TRANSFER_TARGET
        
        target_user = get_user_by_wallet(wallet)
        if not target_user:
            await update.message.reply_text(
                f"{EMOJIS['warning']} **لم يتم العثور على محفظة بهذا الرقم!**\n\n"
                f"تأكد من صحة الرقم وأعد المحاولة:\n"
                f"أو اكتب /cancel للإلغاء"
            )
            return TRANSFER_TARGET
        
        context.user_data['transfer_target_id'] = target_user['id']
        context.user_data['transfer_target_name'] = target_user['full_name']
        context.user_data['transfer_target_wallet'] = target_user['wallet_number']
        
        await update.message.reply_text(
            f"{EMOJIS['confirm']} **تم العثور على المستلم:**\n\n"
            f"{EMOJIS['user']} الاسم: **{target_user['full_name']}**\n"
            f"{EMOJIS['wallet']} المحفظة: `{target_user['wallet_number']}`\n\n"
            f"{EMOJIS['money']} الآن أدخل مبلغ التحويل (بالريال):\n"
            f"{EMOJIS['warning']} الحد الأدنى: 10 ريال\n\n"
            f"أو اكتب /cancel للإلغاء",
            parse_mode='Markdown'
        )
        return TRANSFER_AMOUNT
    except Exception as e:
        logger.error(f"Error in transfer_target: {e}")
        await update.message.reply_text(f"{EMOJIS['error']} حدث خطأ. يرجى المحاولة مرة أخرى.")
        return ConversationHandler.END

async def transfer_amount(update: Update, context: CallbackContext) -> int:
    """Get transfer amount"""
    try:
        amount_text = update.message.text.strip()
        
        if amount_text.lower() == '/cancel':
            return await cancel(update, context)
        
        try:
            amount = float(amount_text)
            if amount <= 0:
                raise ValueError()
            if amount < 10:
                await update.message.reply_text(
                    f"{EMOJIS['warning']} **المبلغ أقل من الحد الأدنى!**\n\n"
                    f"الحد الأدنى للتحويل: **10** ريال\n"
                    f"أدخل مبلغاً أكبر من أو يساوي 10 ريال."
                )
                return TRANSFER_AMOUNT
        except ValueError:
            await update.message.reply_text(
                f"{EMOJIS['warning']} **مبلغ غير صحيح!**\n\n"
                f"يرجى إدخال مبلغ صحيح بالأرقام فقط\n"
                f"مثال: 100 أو 50.5\n\n"
                f"أو اكتب /cancel للإلغاء"
            )
            return TRANSFER_AMOUNT
        
        sender = get_user(update.message.from_user.id)
        # Recalculate balance
        recalc_and_set_user_balance(sender['id'])
        sender = get_user(update.message.from_user.id)  # Refresh data
        
        if amount > sender['balance']:
            await update.message.reply_text(
                f"{EMOJIS['warning']} **رصيدك غير كافي!**\n\n"
                f"{EMOJIS['money']} المبلغ المطلوب: **{amount}** ريال\n"
                f"{EMOJIS['wallet']} رصيدك الحالي: **{sender['balance']:.2f}** ريال\n\n"
                f"أدخل مبلغاً أقل أو اشحن رصيدك.",
                parse_mode='Markdown'
            )
            return TRANSFER_AMOUNT
        
        context.user_data['transfer_amount'] = round(amount, 2)
        
        target_name = context.user_data['transfer_target_name']
        target_wallet = context.user_data['transfer_target_wallet']
        
        confirmation_text = f"""
{EMOJIS['transfer']} **تأكيد التحويل**

{EMOJIS['user']} المرسل: **{sender['full_name']}**
{EMOJIS['wallet']} محفظتك: `{sender['wallet_number']}`

{EMOJIS['user']} المستلم: **{target_name}**
{EMOJIS['wallet']} محفظة المستلم: `{target_wallet}`

{EMOJIS['money']} المبلغ: **{amount}** ريال
{EMOJIS['wallet']} رصيدك الحالي: **{sender['balance']:.2f}** ريال
{EMOJIS['stats']} رصيدك بعد التحويل: **{sender['balance'] - amount:.2f}** ريال

هل تريد تأكيد التحويل؟
"""
        
        await update.message.reply_text(
            confirmation_text,
            reply_markup=ReplyKeyboardMarkup([
                [f'{EMOJIS["confirm"]} نعم، أكد التحويل'],
                [f'{EMOJIS["cancel"]} إلغاء العملية']
            ], one_time_keyboard=True, resize_keyboard=True),
            parse_mode='Markdown'
        )
        return TRANSFER_CONFIRM
    except Exception as e:
        logger.error(f"Error in transfer_amount: {e}")
        await update.message.reply_text(f"{EMOJIS['error']} حدث خطأ. يرجى المحاولة مرة أخرى.")
        return ConversationHandler.END

async def transfer_confirm(update: Update, context: CallbackContext) -> int:
    """Confirm and execute transfer"""
    try:
        choice = update.message.text.strip()
        
        if choice != f'{EMOJIS["confirm"]} نعم، أكد التحويل':
            await update.message.reply_text(
                f"{EMOJIS['cancel']} تم إلغاء عملية التحويل.",
                reply_markup=ReplyKeyboardRemove()
            )
            return ConversationHandler.END
        
        sender = get_user(update.message.from_user.id)
        target_id = context.user_data.get('transfer_target_id')
        amount = float(context.user_data.get('transfer_amount', 0))
        
        if not target_id or amount <= 0:
            await update.message.reply_text(
                f"{EMOJIS['error']} حدث خطأ في البيانات. يرجى المحاولة مرة أخرى.",
                reply_markup=ReplyKeyboardRemove()
            )
            return ConversationHandler.END
        
        processing_msg = await update.message.reply_text(
            f"{EMOJIS['loading']} جاري معالجة التحويل...",
            reply_markup=ReplyKeyboardRemove()
        )
        
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            sender_acc = get_or_create_user_wallet_account(cur, sender['id'])
            recv_acc = get_or_create_user_wallet_account(cur, target_id)
            conn.commit()
            conn.close()
            
            # Post journal entry
            post_journal(
                description=f'P2P transfer from {sender["id"]} to {target_id}',
                created_by=sender['id'],
                lines=[
                    {'account_id': sender_acc, 'debit': amount, 'credit': 0.0, 'user_id': sender['id'], 'ref_type': 'p2p_transfer', 'ref_id': str(target_id)},
                    {'account_id': recv_acc, 'debit': 0.0, 'credit': amount, 'user_id': target_id, 'ref_type': 'p2p_transfer', 'ref_id': str(sender['id'])},
                ],
            )
            
            # Create transaction record
            create_transaction(
                sender['id'], target_id, amount, 'p2p_transfer',
                description=f'Transfer from {sender["full_name"]} to {context.user_data["transfer_target_name"]}'
            )
            
            # Update balances
            recalc_and_set_user_balance(sender['id'])
            recalc_and_set_user_balance(target_id)
            
            # Log the transfer
            log_system_action(sender['id'], 'p2p_transfer', f'Transferred {amount} riyal to user {target_id}')
            
            # Get updated sender data
            sender = get_user(update.message.from_user.id)
            
            success_message = f"""
{EMOJIS['success']} **تم التحويل بنجاح!**

{EMOJIS['money']} تم تحويل **{amount}** ريال
{EMOJIS['user']} إلى: **{context.user_data['transfer_target_name']}**
{EMOJIS['wallet']} رصيدك الحالي: **{sender['balance']:.2f}** ريال

{EMOJIS['time']} وقت التحويل: {datetime.now().strftime('%Y-%m-%d %H:%M')}
"""
            
            await context.bot.edit_message_text(
                chat_id=update.message.chat_id,
                message_id=processing_msg.message_id,
                text=success_message,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(f'{EMOJIS["transfer"]} تحويل آخر', callback_data='transfer_to_friend')],
                    [InlineKeyboardButton(f'{EMOJIS["home"]} القائمة الرئيسية', callback_data='main_menu')]
                ]),
                parse_mode='Markdown'
            )
            
            # Notify receiver
            try:
                target_user = get_user_by_id(target_id)
                await context.bot.send_message(
                    target_user['telegram_id'],
                    f"{EMOJIS['money']} **تم استلام تحويل جديد!**\n\n"
                    f"{EMOJIS['user']} من: **{sender['full_name']}**\n"
                    f"{EMOJIS['money']} المبلغ: **{amount}** ريال\n"
                    f"{EMOJIS['time']} الوقت: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                    parse_mode='Markdown'
                )
            except Exception:
                pass  # If we can't notify receiver, that's okay
            
            return ConversationHandler.END
        except Exception as e:
            logger.error(f"Error processing transfer: {e}")
            await context.bot.edit_message_text(
                chat_id=update.message.chat_id,
                message_id=processing_msg.message_id,
                text=f"{EMOJIS['error']} حدث خطأ أثناء التحويل. يرجى المحاولة لاحقاً."
            )
            return ConversationHandler.END
    except Exception as e:
        logger.error(f"Error in transfer_confirm: {e}")
        await update.message.reply_text(f"{EMOJIS['error']} حدث خطأ. يرجى المحاولة مرة أخرى.")
        return ConversationHandler.END

# Statistics and user info
async def my_stats(update: Update, context: CallbackContext) -> int:
    """Show user statistics"""
    try:
        user = get_user(update.effective_user.id)
        if not user:
            return await start(update, context)
        
        update_user_activity(user['id'])
        
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            # Get comprehensive statistics
            cursor.execute("SELECT COUNT(*), COALESCE(SUM(amount),0) FROM transactions WHERE from_user = ? AND type = 'card_purchase'", (user['id'],))
            purchases_count, purchases_total = cursor.fetchone()
            
            cursor.execute("SELECT COALESCE(SUM(amount),0) FROM transactions WHERE to_user = ? AND type != 'card_purchase'", (user['id'],))
            incoming_total = cursor.fetchone()[0] or 0
            
            cursor.execute("SELECT COALESCE(SUM(amount),0) FROM transactions WHERE from_user = ? AND type = 'p2p_transfer'", (user['id'],))
            outgoing_transfers = cursor.fetchone()[0] or 0
            
            cursor.execute("SELECT COUNT(*) FROM referrals WHERE referrer_id = ?", (user['id'],))
            referrals_count = cursor.fetchone()[0] or 0
            
            cursor.execute("SELECT COALESCE(SUM(bonus_amount),0) FROM referrals WHERE referrer_id = ? AND awarded = 1", (user['id'],))
            referral_earnings = cursor.fetchone()[0] or 0
            
            # Get last transaction
            cursor.execute("SELECT type, amount, created_at FROM transactions WHERE from_user = ? OR to_user = ? ORDER BY created_at DESC LIMIT 1", (user['id'], user['id']))
            last_transaction = cursor.fetchone()
        finally:
            conn.close()
        
        last_tx_text = "لا توجد معاملات"
        if last_transaction:
            tx_type_map = {
                'card_purchase': 'شراء كرت',
                'p2p_transfer': 'تحويل رصيد',
                'wallet_recharge': 'شحن رصيد',
                'agent_commission': 'عمولة وكيل'
            }
            tx_type = tx_type_map.get(last_transaction[0], last_transaction[0])
            last_tx_text = f"{tx_type} - {last_transaction[1]} ريال ({last_transaction[2][:10]})"
        
        role_names = {
            'customer': 'عميل',
            'agent': 'وكيل',
            'supplier': 'مزود',
            'admin': 'مشرف',
            'super_admin': 'مشرف أعلى'
        }
        
        text = f"""
{EMOJIS['stats']} **إحصائياتك الشاملة**

{EMOJIS['user']} **المعلومات الأساسية:**
الاسم: **{user['full_name']}**
الدور: **{role_names.get(user['role'], user['role'])}**
{EMOJIS['wallet']} المحفظة: `{user['wallet_number']}`
{EMOJIS['money']} الرصيد: **{user['balance']:.2f}** ريال

{EMOJIS['purchase']} **عمليات الشراء:**
عدد المشتريات: **{purchases_count}**
إجمالي الإنفاق: **{purchases_total:.2f}** ريال

{EMOJIS['transfer']} **التحويلات:**
التحويلات الصادرة: **{outgoing_transfers:.2f}** ريال
التحويلات الواردة: **{incoming_total:.2f}** ريال

{EMOJIS['user']} **الإحالات:**
عدد الدعوات: **{referrals_count}**
أرباح الإحالة: **{referral_earnings:.2f}** ريال

{EMOJIS['time']} **آخر معاملة:**
{last_tx_text}

{EMOJIS['date']} **تاريخ التسجيل:**
{user.get('created_at', 'غير محدد')[:10]}
"""
        
        keyboard = [
            [InlineKeyboardButton(f'{EMOJIS["purchase"]} شراء كرت', callback_data='buy_cards')],
            [InlineKeyboardButton(f'{EMOJIS["transfer"]} تحويل رصيد', callback_data='transfer_to_friend')],
            [InlineKeyboardButton(f'{EMOJIS["user"]} دعوة أصدقاء', callback_data='invite_friends')],
            [InlineKeyboardButton(f'{EMOJIS["home"]} القائمة الرئيسية', callback_data='main_menu')]
        ]
        
        if update.message:
            await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        else:
            await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"Error in my_stats: {e}")
        error_msg = f"{EMOJIS['error']} حدث خطأ في عرض الإحصائيات."
        
        if update.message:
            await update.message.reply_text(error_msg)
        else:
            await update.callback_query.edit_message_text(error_msg)
        
        return ConversationHandler.END

# Placeholder handlers for missing features
async def invite_friends_handler(update: Update, context: CallbackContext):
    """Handle invite friends"""
    try:
        user = get_user(update.callback_query.from_user.id)
        invite_link = f"https://t.me/Vsjsgshh_bot?start=ref_{user['invite_code']}"
        
        text = f"""
{EMOJIS['user']} **دعوة الأصدقاء**

{EMOJIS['star']} رابط دعوتك الخاص:
{invite_link}

{EMOJIS['money']} **المكافآت:**
• احصل على مكافأة عند تسجيل كل صديق
• 10% من أول شحن لكل صديق يدعوه
• مكافآت إضافية للمستخدمين النشطين

{EMOJIS['fire']} **كيفية الاستخدام:**
1. انسخ الرابط أعلاه
2. شاركه مع أصدقائك
3. عندما يسجلون سيتم احتساب المكافأة لك تلقائياً

{EMOJIS['stats']} دعواتك المقبولة: {user.get('total_referrals', 0)}
"""
        
        await update.callback_query.edit_message_text(
            text, 
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(f'{EMOJIS["home"]} القائمة الرئيسية', callback_data='main_menu')
            ]]),
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Error in invite_friends_handler: {e}")
        await update.callback_query.edit_message_text(f"{EMOJIS['error']} حدث خطأ.")

async def recharge_balance_handler(update: Update, context: CallbackContext):
    """Handle balance recharge"""
    try:
        user = get_user(update.callback_query.from_user.id)
        text = f"""
{EMOJIS['money']} **شحن الرصيد**

{EMOJIS['wallet']} رقم محفظتك: `{user['wallet_number']}`
{EMOJIS['money']} رصيدك الحالي: **{user['balance']:.2f}** ريال

{EMOJIS['warning']} **طرق الشحن:**
• تحويل من صديق
• شحن من وكيل معتمد
• الحصول على مكافآت الإحالة

{EMOJIS['phone']} **للشحن الفوري:**
تواصل مع الدعم عبر الرقم المرفق في المساعدة

{EMOJIS['star']} **نصائح:**
• تأكد من رقم المحفظة قبل إعطائه للوكيل
• احتفظ بإيصال التحويل للمراجعة
"""
        
        await update.callback_query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(f'{EMOJIS["transfer"]} تحويل من صديق', callback_data='transfer_to_friend')],
                [InlineKeyboardButton(f'❓ المساعدة', callback_data='customer_help')],
                [InlineKeyboardButton(f'{EMOJIS["home"]} القائمة الرئيسية', callback_data='main_menu')]
            ]),
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Error in recharge_balance_handler: {e}")
        await update.callback_query.edit_message_text(f"{EMOJIS['error']} حدث خطأ.")

async def customer_help_handler(update: Update, context: CallbackContext):
    """Handle customer help"""
    try:
        text = f"""
{EMOJIS['star']} **مركز المساعدة**

{EMOJIS['fire']} **الأسئلة الشائعة:**

❓ **كيف أشتري كرت؟**
• اختر "شراء كروت" من القائمة
• اختر الشبكة والفئة المطلوبة
• تأكد من وجود رصيد كافي

❓ **كيف أشحن رصيدي؟**
• من خلال تحويل من صديق
• من خلال وكيل معتمد
• مكافآت الإحالة

❓ **كيف أدعو أصدقاء؟**
• اختر "دعوة أصدقاء" من القائمة
• انسخ رابط الدعوة وشاركه
• احصل على مكافآت عند تسجيلهم

{EMOJIS['phone']} **التواصل:**
• للاستفسارات: @YemenNetSupport
• للشكاوى: @YemenNetAdmin
• الطوارئ: 967712345678

{EMOJIS['time']} **ساعات العمل:**
السبت - الخميس: 8 صباحاً - 10 مساءً
الجمعة: 2 ظهراً - 10 مساءً
"""
        
        await update.callback_query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(f'{EMOJIS["home"]} القائمة الرئيسية', callback_data='main_menu')
            ]]),
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Error in customer_help_handler: {e}")
        await update.callback_query.edit_message_text(f"{EMOJIS['error']} حدث خطأ.")

# Main button handler
async def button_click_handler(update: Update, context: CallbackContext):
    """Handle all button clicks"""
    try:
        query = update.callback_query
        await query.answer()
        data = query.data
        
        logger.info(f'Received callback: {data} from user {query.from_user.id}')
        
        # Route to appropriate handler
        if data == 'buy_cards':
            return await buy_cards(update, context)
        elif data == 'recharge_balance':
            return await recharge_balance_handler(update, context)
        elif data == 'transfer_to_friend':
            return await transfer_to_friend_handler(update, context)
        elif data == 'invite_friends':
            return await invite_friends_handler(update, context)
        elif data == 'customer_help':
            return await customer_help_handler(update, context)
        elif data == 'show_balance':
            return await show_balance(update, context)
        elif data == 'my_stats':
            return await my_stats(update, context)
        elif data == 'main_menu':
            return await main_menu_handler(update, context)
        elif data.startswith('network_'):
            return await select_category(update, context)
        elif data.startswith('category_'):
            return await confirm_purchase(update, context)
        elif data == 'complete_purchase':
            return await complete_purchase(update, context)
        else:
            # Handle not implemented features
            await query.edit_message_text(
                f"{EMOJIS['warning']} **هذه الميزة قيد التطوير**\n\n"
                f"سيتم إضافتها في التحديث القادم قريباً.\n"
                f"شكراً لصبركم!",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(f'{EMOJIS["home"]} القائمة الرئيسية', callback_data='main_menu')
                ]]),
                parse_mode='Markdown'
            )
        
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"Error in button_click_handler: {e}")
        try:
            await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ غير متوقع. يرجى المحاولة مرة أخرى.")
        except:
            pass
        return ConversationHandler.END

def main() -> None:
    """Main function to run the bot"""
    try:
        # Initialize database and setup
        init_db()
        setup_super_admin()
        
        # Create application
        persistence = PicklePersistence(filepath='yemen_net_bot_data')
        application = Application.builder().token(BOT_TOKEN).persistence(persistence).build()
        
        # Set bot commands
        try:
            logger.info("Setting bot commands...")
            application.bot.set_my_commands(QUICK_COMMANDS)
            application.bot.set_chat_menu_button(menu_button=MenuButtonCommands())
            logger.info("Bot commands set successfully")
        except Exception as e:
            logger.warning(f'Failed setting commands/menu: {e}')
        
        # Create conversation handler
        conv_handler = ConversationHandler(
            entry_points=[
                CommandHandler('start', start),
                CommandHandler('menu', quick_menu),
                CommandHandler('balance', show_balance),
                CommandHandler('buy', lambda u, c: buy_cards(u, c)),
                CommandHandler('stats', my_stats),
                CommandHandler('transfer', transfer_to_friend_handler),
                CommandHandler('help', customer_help_handler),
            ],
            states={
                GET_FULL_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_full_name)],
                GET_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_phone)],
                CHOOSE_ROLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_role)],
                SELECT_NETWORK: [CallbackQueryHandler(select_category, pattern='^network_')],
                SELECT_CATEGORY: [CallbackQueryHandler(confirm_purchase, pattern='^category_')],
                CONFIRM_PURCHASE: [CallbackQueryHandler(complete_purchase, pattern='^complete_purchase$')],
                TRANSFER_TARGET: [MessageHandler(filters.TEXT & ~filters.COMMAND, transfer_target)],
                TRANSFER_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, transfer_amount)],
                TRANSFER_CONFIRM: [MessageHandler(filters.TEXT & ~filters.COMMAND, transfer_confirm)],
            },
            fallbacks=[
                CommandHandler('cancel', cancel),
                CallbackQueryHandler(main_menu_handler, pattern='^main_menu$'),
                CallbackQueryHandler(cancel, pattern='^cancel'),
                MessageHandler(filters.TEXT & filters.Regex(r'^/cancel$'), cancel),
            ],
            name='yemen_net_conversation',
            persistent=True,
            allow_reentry=True,
        )
        
        # Add handlers
        application.add_handler(conv_handler)
        application.add_handler(CallbackQueryHandler(button_click_handler))
        
        # Start the bot
        logger.info(f'{EMOJIS["fire"]} بدء تشغيل بوت كروت الإنترنت اليمني...')
        application.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True
        )
        
    except Exception as e:
        logger.error(f"Critical error in main: {e}")
        raise

if __name__ == '__main__':
    main()