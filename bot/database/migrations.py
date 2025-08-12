"""
نظام ترحيل قاعدة البيانات المحسن
"""

import sqlite3
import logging
import random
from typing import List
from bot.database.connection import db_manager
from bot.config import (
    ACCOUNT_CODE_ISSUANCE_EXPENSE, 
    ACCOUNT_CODE_BOT_COMMISSION_REVENUE,
    ACCOUNT_TYPE_EXPENSE,
    ACCOUNT_TYPE_REVENUE
)

logger = logging.getLogger(__name__)

def create_base_tables():
    """إنشاء الجداول الأساسية"""
    
    tables_script = """
    -- جدول المستخدمين
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
    );

    -- جدول الشبكات
    CREATE TABLE IF NOT EXISTS networks (
        id TEXT PRIMARY KEY,
        supplier_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        city TEXT NOT NULL,
        is_active BOOLEAN DEFAULT 1,
        network_code TEXT UNIQUE,  -- إضافة العمود المفقود
        FOREIGN KEY(supplier_id) REFERENCES users(id)
    );

    -- جدول فئات الكروت
    CREATE TABLE IF NOT EXISTS card_categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        network_id TEXT NOT NULL,
        value REAL NOT NULL,
        price REAL NOT NULL,
        is_available BOOLEAN DEFAULT 1,
        FOREIGN KEY(network_id) REFERENCES networks(id)
    );

    -- جدول الكروت
    CREATE TABLE IF NOT EXISTS cards (
        id TEXT PRIMARY KEY,
        category_id INTEGER NOT NULL,
        code TEXT NOT NULL,
        is_used BOOLEAN DEFAULT 0,
        added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(category_id) REFERENCES card_categories(id)
    );

    -- جدول المعاملات
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
    );

    -- جدول طلبات السحب
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
    );

    -- جدول الإحالات
    CREATE TABLE IF NOT EXISTS referrals (
        id TEXT PRIMARY KEY,
        referrer_id INTEGER NOT NULL,
        referred_id INTEGER NOT NULL,
        bonus_amount REAL,
        awarded BOOLEAN DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(referrer_id) REFERENCES users(id),
        FOREIGN KEY(referred_id) REFERENCES users(id)
    );

    -- جداول المحاسبة
    CREATE TABLE IF NOT EXISTS accounts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE,
        name TEXT NOT NULL,
        type TEXT NOT NULL,
        parent_id INTEGER,
        is_active BOOLEAN DEFAULT 1
    );

    CREATE TABLE IF NOT EXISTS user_accounts (
        user_id INTEGER UNIQUE NOT NULL,
        account_id INTEGER NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id),
        FOREIGN KEY(account_id) REFERENCES accounts(id)
    );

    CREATE TABLE IF NOT EXISTS journal_entries (
        id TEXT PRIMARY KEY,
        description TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        created_by INTEGER
    );

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
    );
    """
    
    db_manager.execute_script(tables_script)
    logger.info("تم إنشاء الجداول الأساسية بنجاح")

def create_new_tables():
    """إنشاء الجداول الجديدة للميزات المتقدمة"""
    
    new_tables_script = """
    -- جدول التقييمات
    CREATE TABLE IF NOT EXISTS ratings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
        comment TEXT,
        service_type TEXT DEFAULT 'general',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id)
    );

    -- جدول المحفظة الإلكترونية
    CREATE TABLE IF NOT EXISTS e_wallet_transactions (
        id TEXT PRIMARY KEY,
        sender_id INTEGER,
        receiver_id INTEGER,
        amount REAL NOT NULL,
        transaction_type TEXT NOT NULL, -- 'transfer', 'payment', 'refund'
        status TEXT DEFAULT 'pending',
        description TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        completed_at TIMESTAMP,
        FOREIGN KEY(sender_id) REFERENCES users(id),
        FOREIGN KEY(receiver_id) REFERENCES users(id)
    );

    -- جدول التجار والأماكن
    CREATE TABLE IF NOT EXISTS vendors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        category TEXT NOT NULL,
        wallet_number TEXT UNIQUE NOT NULL,
        commission_rate REAL DEFAULT 0.02,
        is_active BOOLEAN DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- جدول الإشعارات
    CREATE TABLE IF NOT EXISTS notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        title TEXT NOT NULL,
        message TEXT NOT NULL,
        type TEXT DEFAULT 'info', -- 'info', 'success', 'warning', 'error'
        is_read BOOLEAN DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id)
    );

    -- جدول سجل الأنشطة
    CREATE TABLE IF NOT EXISTS activity_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        action TEXT NOT NULL,
        details TEXT,
        ip_address TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id)
    );

    -- جدول إعدادات البوت
    CREATE TABLE IF NOT EXISTS bot_settings (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL,
        description TEXT,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- جدول الكوبونات والخصومات
    CREATE TABLE IF NOT EXISTS coupons (
        id TEXT PRIMARY KEY,
        code TEXT UNIQUE NOT NULL,
        discount_type TEXT NOT NULL, -- 'percentage', 'fixed'
        discount_value REAL NOT NULL,
        min_purchase REAL DEFAULT 0,
        max_uses INTEGER DEFAULT 1,
        used_count INTEGER DEFAULT 0,
        expires_at TIMESTAMP,
        is_active BOOLEAN DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- جدول استخدام الكوبونات
    CREATE TABLE IF NOT EXISTS coupon_usage (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        coupon_id TEXT NOT NULL,
        user_id INTEGER NOT NULL,
        transaction_id TEXT,
        used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(coupon_id) REFERENCES coupons(id),
        FOREIGN KEY(user_id) REFERENCES users(id),
        FOREIGN KEY(transaction_id) REFERENCES transactions(id)
    );
    """
    
    db_manager.execute_script(new_tables_script)
    logger.info("تم إنشاء الجداول الجديدة بنجاح")

def create_indexes():
    """إنشاء الفهارس لتحسين الأداء"""
    
    indexes_script = """
    -- فهارس للجداول الأساسية
    CREATE INDEX IF NOT EXISTS idx_users_telegram_id ON users(telegram_id);
    CREATE INDEX IF NOT EXISTS idx_users_phone ON users(phone);
    CREATE INDEX IF NOT EXISTS idx_users_wallet_number ON users(wallet_number);
    
    CREATE INDEX IF NOT EXISTS idx_networks_supplier_id ON networks(supplier_id);
    CREATE INDEX IF NOT EXISTS idx_networks_network_code ON networks(network_code);
    
    CREATE INDEX IF NOT EXISTS idx_cards_category_id ON cards(category_id);
    CREATE INDEX IF NOT EXISTS idx_cards_is_used ON cards(is_used);
    
    CREATE INDEX IF NOT EXISTS idx_transactions_from_user ON transactions(from_user);
    CREATE INDEX IF NOT EXISTS idx_transactions_to_user ON transactions(to_user);
    CREATE INDEX IF NOT EXISTS idx_transactions_type ON transactions(type);
    CREATE INDEX IF NOT EXISTS idx_transactions_status ON transactions(status);
    CREATE INDEX IF NOT EXISTS idx_transactions_created_at ON transactions(created_at);
    
    -- فهارس للجداول الجديدة
    CREATE INDEX IF NOT EXISTS idx_ratings_user_id ON ratings(user_id);
    CREATE INDEX IF NOT EXISTS idx_ratings_created_at ON ratings(created_at);
    
    CREATE INDEX IF NOT EXISTS idx_e_wallet_sender ON e_wallet_transactions(sender_id);
    CREATE INDEX IF NOT EXISTS idx_e_wallet_receiver ON e_wallet_transactions(receiver_id);
    CREATE INDEX IF NOT EXISTS idx_e_wallet_status ON e_wallet_transactions(status);
    
    CREATE INDEX IF NOT EXISTS idx_notifications_user_id ON notifications(user_id);
    CREATE INDEX IF NOT EXISTS idx_notifications_is_read ON notifications(is_read);
    
    CREATE INDEX IF NOT EXISTS idx_activity_log_user_id ON activity_log(user_id);
    CREATE INDEX IF NOT EXISTS idx_activity_log_created_at ON activity_log(created_at);
    """
    
    db_manager.execute_script(indexes_script)
    logger.info("تم إنشاء الفهارس بنجاح")

def add_missing_columns():
    """إضافة الأعمدة المفقودة للجداول الموجودة"""
    
    try:
        with db_manager.get_cursor() as (conn, cursor):
            # إضافة wallet_number إذا كان مفقوداً
            try:
                cursor.execute('ALTER TABLE users ADD COLUMN wallet_number TEXT UNIQUE')
                logger.info("تم إضافة عمود wallet_number إلى جدول المستخدمين")
            except sqlite3.OperationalError:
                pass  # العمود موجود بالفعل
            
            # إضافة network_code إذا كان مفقوداً
            try:
                cursor.execute('ALTER TABLE networks ADD COLUMN network_code TEXT UNIQUE')
                logger.info("تم إضافة عمود network_code إلى جدول الشبكات")
            except sqlite3.OperationalError:
                pass  # العمود موجود بالفعل
                
    except Exception as e:
        logger.error(f"خطأ في إضافة الأعمدة المفقودة: {e}")

def backfill_missing_data():
    """ملء البيانات المفقودة"""
    
    try:
        with db_manager.get_cursor() as (conn, cursor):
            # ملء أرقام المحافظ المفقودة
            cursor.execute("SELECT id FROM users WHERE wallet_number IS NULL OR wallet_number = ''")
            missing_wallets = [row[0] for row in cursor.fetchall()]
            
            for user_id in missing_wallets:
                for _ in range(20):  # محاولة 20 مرة لإيجاد رقم فريد
                    trial = '79' + ''.join(str(random.randint(0, 9)) for _ in range(7))
                    cursor.execute('SELECT 1 FROM users WHERE wallet_number = ?', (trial,))
                    if not cursor.fetchone():
                        cursor.execute('UPDATE users SET wallet_number = ? WHERE id = ?', (trial, user_id))
                        break
            
            logger.info(f"تم ملء {len(missing_wallets)} رقم محفظة مفقود")
            
    except Exception as e:
        logger.error(f"خطأ في ملء البيانات المفقودة: {e}")

def ensure_base_accounts():
    """التأكد من وجود الحسابات الأساسية"""
    
    try:
        with db_manager.get_cursor() as (conn, cursor):
            # حساب مصاريف الإصدار
            cursor.execute('SELECT id FROM accounts WHERE code = ?', (ACCOUNT_CODE_ISSUANCE_EXPENSE,))
            if not cursor.fetchone():
                cursor.execute(
                    'INSERT INTO accounts (code, name, type) VALUES (?, ?, ?)',
                    (ACCOUNT_CODE_ISSUANCE_EXPENSE, 'Issuance Expense', ACCOUNT_TYPE_EXPENSE),
                )
                logger.info("تم إنشاء حساب مصاريف الإصدار")
            
            # حساب عمولة البوت
            cursor.execute('SELECT id FROM accounts WHERE code = ?', (ACCOUNT_CODE_BOT_COMMISSION_REVENUE,))
            if not cursor.fetchone():
                cursor.execute(
                    'INSERT INTO accounts (code, name, type) VALUES (?, ?, ?)',
                    (ACCOUNT_CODE_BOT_COMMISSION_REVENUE, 'Bot Commission Revenue', ACCOUNT_TYPE_REVENUE),
                )
                logger.info("تم إنشاء حساب عمولة البوت")
                
    except Exception as e:
        logger.error(f"خطأ في إنشاء الحسابات الأساسية: {e}")

def insert_default_settings():
    """إدراج الإعدادات الافتراضية"""
    
    default_settings = [
        ('maintenance_mode', 'false', 'وضع الصيانة'),
        ('welcome_message', 'مرحباً بك في بوت يمن نت!', 'رسالة الترحيب'),
        ('max_daily_transactions', '100', 'حد المعاملات اليومية'),
        ('notification_enabled', 'true', 'تفعيل الإشعارات'),
    ]
    
    try:
        with db_manager.get_cursor() as (conn, cursor):
            for key, value, description in default_settings:
                cursor.execute('SELECT 1 FROM bot_settings WHERE key = ?', (key,))
                if not cursor.fetchone():
                    cursor.execute(
                        'INSERT INTO bot_settings (key, value, description) VALUES (?, ?, ?)',
                        (key, value, description)
                    )
            
            logger.info("تم إدراج الإعدادات الافتراضية")
            
    except Exception as e:
        logger.error(f"خطأ في إدراج الإعدادات الافتراضية: {e}")

def run_migrations():
    """تشغيل جميع عمليات الترحيل"""
    
    logger.info("بدء عمليات ترحيل قاعدة البيانات...")
    
    try:
        create_base_tables()
        add_missing_columns()
        create_new_tables()
        create_indexes()
        backfill_missing_data()
        ensure_base_accounts()
        insert_default_settings()
        
        logger.info("تم إكمال جميع عمليات ترحيل قاعدة البيانات بنجاح!")
        
    except Exception as e:
        logger.error(f"خطأ حرج في ترحيل قاعدة البيانات: {e}")
        raise