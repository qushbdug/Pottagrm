#!/usr/bin/env python3
"""
Database module for Pottagrm Enhanced Bot
Contains all database operations and initialization
"""

import logging
import sqlite3
import uuid
import random
from datetime import datetime
from bot_modules.config import *

logger = logging.getLogger(__name__)

def get_db_connection():
    """Get database connection with error handling"""
    try:
        conn = sqlite3.connect(DB_PATH, timeout=30.0)
        conn.execute('PRAGMA foreign_keys = ON')
        conn.execute('PRAGMA journal_mode = WAL')
        conn.execute('PRAGMA synchronous = NORMAL')
        conn.execute('PRAGMA cache_size = 1000')
        conn.execute('PRAGMA temp_store = memory')
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        raise

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
                total_purchases INTEGER DEFAULT 0,
                total_spent REAL DEFAULT 0.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                referred_by INTEGER,
                wallet_number TEXT UNIQUE,
                FOREIGN KEY(referred_by) REFERENCES users(id)
            )
        ''')

        # Networks table (unified schema)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS networks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                supplier_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                provider TEXT NOT NULL,
                description TEXT,
                logo_url TEXT,
                city TEXT,
                location TEXT,
                network_code TEXT UNIQUE,
                is_active BOOLEAN DEFAULT 1,
                is_approved BOOLEAN DEFAULT 0,
                created_by INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                approved_at TIMESTAMP,
                approved_by INTEGER,
                FOREIGN KEY(supplier_id) REFERENCES users(id),
                FOREIGN KEY(approved_by) REFERENCES users(id),
                FOREIGN KEY(created_by) REFERENCES users(id)
            )
        ''')

        # Card categories table (unified schema)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS card_categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                network_id INTEGER,
                name TEXT,
                value REAL NOT NULL,
                price REAL NOT NULL,
                currency TEXT DEFAULT 'YER',
                is_available BOOLEAN DEFAULT 1,
                stock_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                category_name TEXT,
                description TEXT,
                FOREIGN KEY(network_id) REFERENCES networks(id)
            )
        ''')

        # Cards table (unified schema)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category_id INTEGER,
                card_number TEXT NOT NULL,
                serial_number TEXT,
                expiry_date TEXT,
                is_sold BOOLEAN DEFAULT 0,
                sold_to INTEGER,
                sold_at TIMESTAMP,
                uploaded_by INTEGER,
                uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (category_id) REFERENCES card_categories (id),
                FOREIGN KEY (sold_to) REFERENCES users (id),
                FOREIGN KEY (uploaded_by) REFERENCES users (id)
            )
        ''')

        # Transactions table
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

        # Enhanced sales system tables
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sales_reports (
                id TEXT PRIMARY KEY,
                report_type TEXT NOT NULL,
                start_date DATE NOT NULL,
                end_date DATE NOT NULL,
                total_sales REAL DEFAULT 0.0,
                total_commission REAL DEFAULT 0.0,
                total_transactions INTEGER DEFAULT 0,
                generated_by INTEGER NOT NULL,
                generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data TEXT,
                FOREIGN KEY(generated_by) REFERENCES users(id)
            )
        ''')

        # Recharge cards table for super admin issued cards
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS recharge_cards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE NOT NULL,
                serial_number TEXT UNIQUE NOT NULL,
                value REAL NOT NULL,
                price REAL NOT NULL,
                network_name TEXT NOT NULL,
                status TEXT DEFAULT 'available',
                created_by INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                purchased_by INTEGER,
                purchased_at TIMESTAMP,
                used_at TIMESTAMP,
                FOREIGN KEY(created_by) REFERENCES users(id),
                FOREIGN KEY(purchased_by) REFERENCES users(id)
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS product_inventory (
                id TEXT PRIMARY KEY,
                network_id TEXT NOT NULL,
                category_id INTEGER NOT NULL,
                stock_count INTEGER DEFAULT 0,
                reserved_count INTEGER DEFAULT 0,
                low_stock_threshold INTEGER DEFAULT 10,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_by INTEGER,
                FOREIGN KEY(network_id) REFERENCES networks(id),
                FOREIGN KEY(category_id) REFERENCES card_categories(id),
                FOREIGN KEY(updated_by) REFERENCES users(id)
            )
        ''')

        # E-wallet enhanced features
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS wallet_transactions (
                id TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                transaction_type TEXT NOT NULL,
                amount REAL NOT NULL,
                balance_before REAL NOT NULL,
                balance_after REAL NOT NULL,
                reference_id TEXT,
                description TEXT,
                status TEXT DEFAULT 'completed',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS payment_methods (
                id TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                method_type TEXT NOT NULL,
                method_name TEXT NOT NULL,
                account_details TEXT NOT NULL,
                is_active BOOLEAN DEFAULT 1,
                is_verified BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                verified_at TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        ''')

        # Rating and review system
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ratings (
                id TEXT PRIMARY KEY,
                rater_id INTEGER NOT NULL,
                rated_user_id INTEGER NOT NULL,
                transaction_id TEXT,
                rating INTEGER NOT NULL CHECK(rating >= 1 AND rating <= 5),
                review_text TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_visible BOOLEAN DEFAULT 1,
                FOREIGN KEY(rater_id) REFERENCES users(id),
                FOREIGN KEY(rated_user_id) REFERENCES users(id),
                FOREIGN KEY(transaction_id) REFERENCES transactions(id)
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_ratings_summary (
                user_id INTEGER PRIMARY KEY,
                total_ratings INTEGER DEFAULT 0,
                average_rating REAL DEFAULT 0.0,
                rating_1_count INTEGER DEFAULT 0,
                rating_2_count INTEGER DEFAULT 0,
                rating_3_count INTEGER DEFAULT 0,
                rating_4_count INTEGER DEFAULT 0,
                rating_5_count INTEGER DEFAULT 0,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        ''')

        # Smart notifications system
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS notification_preferences (
                user_id INTEGER PRIMARY KEY,
                balance_alerts BOOLEAN DEFAULT 1,
                transaction_alerts BOOLEAN DEFAULT 1,
                promotion_alerts BOOLEAN DEFAULT 1,
                system_alerts BOOLEAN DEFAULT 1,
                low_stock_alerts BOOLEAN DEFAULT 0,
                rating_requests BOOLEAN DEFAULT 1,
                email_notifications BOOLEAN DEFAULT 0,
                sms_notifications BOOLEAN DEFAULT 0,
                quiet_hours_start TIME,
                quiet_hours_end TIME,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS smart_notifications (
                id TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                notification_type TEXT NOT NULL,
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                priority TEXT DEFAULT 'normal',
                is_read BOOLEAN DEFAULT 0,
                is_sent BOOLEAN DEFAULT 0,
                scheduled_for TIMESTAMP,
                sent_at TIMESTAMP,
                read_at TIMESTAMP,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        ''')

        # Enhanced user management
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_permissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                permission_name TEXT NOT NULL,
                granted_by INTEGER NOT NULL,
                granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                is_active BOOLEAN DEFAULT 1,
                FOREIGN KEY(user_id) REFERENCES users(id),
                FOREIGN KEY(granted_by) REFERENCES users(id)
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS activity_logs (
                id TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                activity_type TEXT NOT NULL,
                description TEXT NOT NULL,
                ip_address TEXT,
                user_agent TEXT,
                session_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        ''')

        # Promotions and offers system
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS promotions (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                promotion_type TEXT NOT NULL,
                discount_percentage REAL DEFAULT 0.0,
                discount_amount REAL DEFAULT 0.0,
                min_purchase_amount REAL DEFAULT 0.0,
                max_usage_per_user INTEGER DEFAULT 1,
                start_date TIMESTAMP NOT NULL,
                end_date TIMESTAMP NOT NULL,
                is_active BOOLEAN DEFAULT 1,
                created_by INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                target_user_role TEXT,
                applicable_networks TEXT,
                FOREIGN KEY(created_by) REFERENCES users(id)
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS promotion_usage (
                id TEXT PRIMARY KEY,
                promotion_id TEXT NOT NULL,
                user_id INTEGER NOT NULL,
                transaction_id TEXT NOT NULL,
                discount_applied REAL NOT NULL,
                used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(promotion_id) REFERENCES promotions(id),
                FOREIGN KEY(user_id) REFERENCES users(id),
                FOREIGN KEY(transaction_id) REFERENCES transactions(id)
            )
        ''')

        # Additional tables for accounting and other features
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

        # Migrations for existing databases
        migrations = [
            ('ALTER TABLE users ADD COLUMN wallet_number TEXT UNIQUE', 'wallet_number'),
            ('ALTER TABLE networks ADD COLUMN network_code TEXT UNIQUE', 'network_code'),
        ]

        for migration_sql, column_name in migrations:
            try:
                cursor.execute(migration_sql)
            except sqlite3.OperationalError:
                # Column already exists or other error
                pass

        # Backfill missing wallet numbers
        cursor.execute("SELECT id FROM users WHERE wallet_number IS NULL OR wallet_number = ''")
        missing_wallets = cursor.fetchall()
        for user_id, in missing_wallets:
            for _ in range(20):
                trial = '79' + ''.join(str(random.randint(0, 9)) for _ in range(7))
                cursor.execute('SELECT 1 FROM users WHERE wallet_number = ?', (trial,))
                if not cursor.fetchone():
                    cursor.execute('UPDATE users SET wallet_number = ? WHERE id = ?', (trial, user_id))
                    break

        # Backfill missing network codes (only if column exists)
        try:
            cursor.execute("SELECT id, supplier_id FROM networks WHERE network_code IS NULL OR network_code = ''")
            missing_codes = cursor.fetchall()
            for network_id, supplier_id in missing_codes:
                for _ in range(20):
                    code = ''.join(str(random.randint(0, 9)) for _ in range(5))
                    cursor.execute('SELECT 1 FROM networks WHERE network_code = ?', (code,))
                    if not cursor.fetchone():
                        cursor.execute('UPDATE networks SET network_code = ? WHERE id = ?', (code, network_id))
                        break
        except sqlite3.OperationalError:
            # Column doesn't exist yet, will be handled by migration
            pass

        # Enhanced supplier system tables
        # Add supplier codes table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS supplier_codes (
                id TEXT PRIMARY KEY,
                supplier_id INTEGER UNIQUE NOT NULL,
                supplier_code TEXT UNIQUE NOT NULL, -- 6-digit code starting with 80
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (supplier_id) REFERENCES users (id)
            )
        ''')
        
        # Create cards table for uploaded cards
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS network_cards (
                id TEXT PRIMARY KEY,
                supplier_id INTEGER NOT NULL,
                network_id TEXT NOT NULL,
                card_code TEXT NOT NULL,
                card_value REAL NOT NULL,
                card_category INTEGER DEFAULT 200, -- Card category/denomination
                is_sold BOOLEAN DEFAULT 0,
                sold_to INTEGER NULL,
                sold_at TIMESTAMP NULL,
                upload_batch_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (supplier_id) REFERENCES users (id),
                FOREIGN KEY (network_id) REFERENCES networks (id),
                FOREIGN KEY (sold_to) REFERENCES users (id)
            )
        ''')
        
        # Create card categories reference table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS card_categories_ref (
                category_value INTEGER PRIMARY KEY,
                category_name TEXT NOT NULL,
                display_order INTEGER DEFAULT 0,
                is_active BOOLEAN DEFAULT 1
            )
        ''')
        
        # Insert default card categories if not exist
        categories = [
            (200, '200 ريال', 1),
            (300, '300 ريال', 2),
            (500, '500 ريال', 3),
            (1000, '1000 ريال', 4),
            (2000, '2000 ريال', 5),
            (5000, '5000 ريال', 6),
            (10000, '10000 ريال', 7)
        ]
        
        cursor.executemany('''
            INSERT OR IGNORE INTO card_categories_ref (category_value, category_name, display_order)
            VALUES (?, ?, ?)
        ''', categories)
        
        # Create upload batches table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS card_upload_batches (
                id TEXT PRIMARY KEY,
                supplier_id INTEGER NOT NULL,
                network_id TEXT NOT NULL,
                filename TEXT,
                total_cards INTEGER DEFAULT 0,
                successful_cards INTEGER DEFAULT 0,
                failed_cards INTEGER DEFAULT 0,
                upload_status TEXT DEFAULT 'processing',
                error_details TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (supplier_id) REFERENCES users (id),
                FOREIGN KEY (network_id) REFERENCES networks (id)
            )
        ''')

        # Create settings table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT UNIQUE NOT NULL,
                value TEXT,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create networks table (duplicate call with same unified schema for idempotency)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS networks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                supplier_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                provider TEXT NOT NULL,
                description TEXT,
                logo_url TEXT,
                city TEXT,
                location TEXT,
                network_code TEXT UNIQUE,
                is_active BOOLEAN DEFAULT 1,
                is_approved BOOLEAN DEFAULT 0,
                created_by INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                approved_at TIMESTAMP,
                approved_by INTEGER,
                FOREIGN KEY(supplier_id) REFERENCES users(id),
                FOREIGN KEY(approved_by) REFERENCES users(id),
                FOREIGN KEY(created_by) REFERENCES users(id)
            )
        ''')
        
        # Create card_categories table (duplicate call with same unified schema for idempotency)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS card_categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                network_id INTEGER,
                name TEXT,
                value REAL NOT NULL,
                price REAL NOT NULL,
                currency TEXT DEFAULT 'YER',
                is_available BOOLEAN DEFAULT 1,
                stock_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (network_id) REFERENCES networks (id)
            )
        ''')
        
        # Create cards table (duplicate call with same unified schema for idempotency)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category_id INTEGER,
                card_number TEXT NOT NULL,
                serial_number TEXT,
                expiry_date TEXT,
                is_sold BOOLEAN DEFAULT 0,
                sold_to INTEGER,
                sold_at TIMESTAMP,
                uploaded_by INTEGER,
                uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (category_id) REFERENCES card_categories (id),
                FOREIGN KEY (sold_to) REFERENCES users (id),
                FOREIGN KEY (uploaded_by) REFERENCES users (id)
            )
        ''')
        
        # Create coupons table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS coupons (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                coupon_code TEXT NOT NULL UNIQUE,
                amount REAL NOT NULL,
                is_used BOOLEAN DEFAULT 0,
                used_by INTEGER,
                created_by INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                used_at TIMESTAMP,
                expiry_date TIMESTAMP,
                description TEXT,
                FOREIGN KEY (used_by) REFERENCES users (id),
                FOREIGN KEY (created_by) REFERENCES users (id)
            )
        ''')
        
        # Data insertion is handled separately to avoid conflicts

        conn.commit()
        logger.info("Database initialized successfully")
        
    except Exception as e:
        logger.error(f"Database initialization error: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

def update_user_balance(user_id, new_balance):
    """Update user balance"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE users 
            SET balance = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (new_balance, user_id))
        
        if cursor.rowcount > 0:
            conn.commit()
            conn.close()
            logger.info(f"Updated balance for user {user_id} to {new_balance}")
            return True
        else:
            conn.close()
            logger.warning(f"User {user_id} not found for balance update")
            return False
            
    except Exception as e:
        logger.error(f"Error updating user balance: {e}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return False