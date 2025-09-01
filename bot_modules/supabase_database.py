#!/usr/bin/env python3
"""
Supabase Database Layer - طبقة قاعدة بيانات Supabase
طبقة جديدة للتعامل مع Supabase بدلاً من SQLite
"""

import logging
import asyncio
import asyncpg
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from supabase import create_client
from bot_modules.supabase_config import SUPABASE_URL, SUPABASE_KEY

logger = logging.getLogger(__name__)

class SupabaseDatabase:
    """فئة إدارة قاعدة بيانات Supabase"""
    
    def __init__(self):
        self.supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        self.connection_pool = None
    
    async def init_connection_pool(self):
        """تهيئة مجموعة الاتصالات"""
        try:
            # سنحتاج لإعداد connection string مع كلمة المرور
            # هذا مثال - يحتاج تعديل كلمة المرور الفعلية
            connection_string = "postgresql://postgres:YOUR_PASSWORD@db.poxdecozxjnzbmumvqzx.supabase.co:5432/postgres"
            
            self.connection_pool = await asyncpg.create_pool(
                connection_string,
                min_size=5,
                max_size=20,
                command_timeout=60
            )
            logger.info("Supabase connection pool initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize Supabase connection pool: {e}")
            raise
    
    async def create_tables_schema(self):
        """إنشاء مخطط الجداول في Supabase"""
        
        # مخطط الجداول بـ PostgreSQL
        tables_sql = {
            'users': '''
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    telegram_id BIGINT UNIQUE NOT NULL,
                    full_name VARCHAR(255) NOT NULL CHECK (LENGTH(full_name) >= 2),
                    phone VARCHAR(20) UNIQUE NOT NULL CHECK (LENGTH(phone) >= 9),
                    role VARCHAR(20) NOT NULL DEFAULT 'customer' 
                        CHECK (role IN ('customer', 'supplier', 'agent', 'admin', 'super_admin')),
                    balance DECIMAL(15,2) DEFAULT 0.00 CHECK (balance >= 0),
                    invite_code VARCHAR(50) UNIQUE,
                    is_active BOOLEAN DEFAULT FALSE,
                    bank_account VARCHAR(100),
                    total_referrals INTEGER DEFAULT 0 CHECK (total_referrals >= 0),
                    total_purchases INTEGER DEFAULT 0 CHECK (total_purchases >= 0),
                    total_spent DECIMAL(15,2) DEFAULT 0.00 CHECK (total_spent >= 0),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    referred_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
                    wallet_number VARCHAR(20) UNIQUE,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            ''',
            
            'networks': '''
                CREATE TABLE IF NOT EXISTS networks (
                    id SERIAL PRIMARY KEY,
                    supplier_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    name VARCHAR(255) NOT NULL,
                    provider VARCHAR(255) NOT NULL,
                    description TEXT,
                    logo_url TEXT,
                    city VARCHAR(100),
                    location VARCHAR(255),
                    network_code VARCHAR(50) UNIQUE,
                    is_active BOOLEAN DEFAULT TRUE,
                    is_approved BOOLEAN DEFAULT FALSE,
                    created_by INTEGER REFERENCES users(id),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    approved_at TIMESTAMP,
                    approved_by INTEGER REFERENCES users(id)
                );
            ''',
            
            'network_cards': '''
                CREATE TABLE IF NOT EXISTS network_cards (
                    id SERIAL PRIMARY KEY,
                    network_id INTEGER NOT NULL REFERENCES networks(id) ON DELETE CASCADE,
                    card_code VARCHAR(255) NOT NULL,
                    card_value DECIMAL(10,2) NOT NULL CHECK (card_value > 0),
                    is_sold BOOLEAN DEFAULT FALSE,
                    sold_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    batch_id VARCHAR(100),
                    serial_number VARCHAR(100)
                );
            ''',
            
            'transactions': '''
                CREATE TABLE IF NOT EXISTS transactions (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    from_user INTEGER NOT NULL REFERENCES users(id),
                    to_user INTEGER NOT NULL REFERENCES users(id),
                    amount DECIMAL(15,2) NOT NULL CHECK (amount > 0),
                    type VARCHAR(50) NOT NULL,
                    description TEXT,
                    status VARCHAR(20) DEFAULT 'completed',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    reference_id VARCHAR(100),
                    metadata JSONB,
                    CHECK (from_user != to_user OR type != 'transfer')
                );
            ''',
            
            'wallet_transactions': '''
                CREATE TABLE IF NOT EXISTS wallet_transactions (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    transaction_type VARCHAR(50) NOT NULL,
                    amount DECIMAL(15,2) NOT NULL,
                    balance_before DECIMAL(15,2) NOT NULL,
                    balance_after DECIMAL(15,2) NOT NULL,
                    reference_id VARCHAR(100),
                    description TEXT,
                    status VARCHAR(20) DEFAULT 'completed',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata JSONB
                );
            ''',
            
            'coupons': '''
                CREATE TABLE IF NOT EXISTS coupons (
                    id SERIAL PRIMARY KEY,
                    coupon_code VARCHAR(50) UNIQUE NOT NULL,
                    amount DECIMAL(10,2) NOT NULL CHECK (amount > 0),
                    is_used BOOLEAN DEFAULT FALSE,
                    used_by INTEGER REFERENCES users(id),
                    used_at TIMESTAMP,
                    created_by INTEGER NOT NULL REFERENCES users(id),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP,
                    description TEXT,
                    usage_limit INTEGER DEFAULT 1,
                    usage_count INTEGER DEFAULT 0
                );
            ''',
            
            'chart_of_accounts': '''
                CREATE TABLE IF NOT EXISTS chart_of_accounts (
                    id SERIAL PRIMARY KEY,
                    account_code VARCHAR(20) UNIQUE NOT NULL,
                    account_name VARCHAR(255) NOT NULL,
                    account_type VARCHAR(50) NOT NULL 
                        CHECK (account_type IN ('asset', 'liability', 'equity', 'revenue', 'expense')),
                    parent_account INTEGER REFERENCES chart_of_accounts(id),
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            ''',
            
            'general_ledger': '''
                CREATE TABLE IF NOT EXISTS general_ledger (
                    id SERIAL PRIMARY KEY,
                    account_id INTEGER NOT NULL REFERENCES chart_of_accounts(id),
                    debit_amount DECIMAL(15,2) DEFAULT 0.00,
                    credit_amount DECIMAL(15,2) DEFAULT 0.00,
                    description TEXT,
                    reference_type VARCHAR(50),
                    reference_id VARCHAR(100),
                    currency VARCHAR(3) DEFAULT 'YER',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_by INTEGER REFERENCES users(id),
                    CHECK ((debit_amount > 0 AND credit_amount = 0) OR (credit_amount > 0 AND debit_amount = 0))
                );
            '''
        }
        
        try:
            for table_name, table_sql in tables_sql.items():
                try:
                    # استخدام Supabase client لإنشاء الجداول
                    result = self.supabase.rpc('exec_sql', {'sql': table_sql})
                    logger.info(f"Created/verified table: {table_name}")
                except Exception as e:
                    logger.warning(f"Error creating table {table_name}: {e}")
            
            # إنشاء الفهارس
            await self.create_indexes()
            
            logger.info("Supabase schema created successfully")
            
        except Exception as e:
            logger.error(f"Failed to create Supabase schema: {e}")
            raise
    
    async def create_indexes(self):
        """إنشاء الفهارس المحسنة"""
        indexes_sql = [
            'CREATE INDEX IF NOT EXISTS idx_users_telegram_id ON users(telegram_id)',
            'CREATE INDEX IF NOT EXISTS idx_users_phone ON users(phone)',
            'CREATE INDEX IF NOT EXISTS idx_users_role ON users(role)',
            'CREATE INDEX IF NOT EXISTS idx_users_balance ON users(balance)',
            'CREATE INDEX IF NOT EXISTS idx_users_wallet_number ON users(wallet_number)',
            
            'CREATE INDEX IF NOT EXISTS idx_networks_supplier ON networks(supplier_id)',
            'CREATE INDEX IF NOT EXISTS idx_networks_active ON networks(is_active, is_approved)',
            
            'CREATE INDEX IF NOT EXISTS idx_cards_network ON network_cards(network_id)',
            'CREATE INDEX IF NOT EXISTS idx_cards_sold ON network_cards(is_sold)',
            'CREATE INDEX IF NOT EXISTS idx_cards_value ON network_cards(card_value)',
            
            'CREATE INDEX IF NOT EXISTS idx_transactions_from_user ON transactions(from_user)',
            'CREATE INDEX IF NOT EXISTS idx_transactions_to_user ON transactions(to_user)',
            'CREATE INDEX IF NOT EXISTS idx_transactions_type ON transactions(type)',
            'CREATE INDEX IF NOT EXISTS idx_transactions_created_at ON transactions(created_at)',
            
            'CREATE INDEX IF NOT EXISTS idx_wallet_trans_user ON wallet_transactions(user_id)',
            'CREATE INDEX IF NOT EXISTS idx_wallet_trans_type ON wallet_transactions(transaction_type)',
            'CREATE INDEX IF NOT EXISTS idx_wallet_trans_created_at ON wallet_transactions(created_at)',
            
            'CREATE INDEX IF NOT EXISTS idx_coupons_code ON coupons(coupon_code)',
            'CREATE INDEX IF NOT EXISTS idx_coupons_used ON coupons(is_used)',
            
            'CREATE INDEX IF NOT EXISTS idx_ledger_account ON general_ledger(account_id)',
            'CREATE INDEX IF NOT EXISTS idx_ledger_date ON general_ledger(created_at)',
        ]
        
        for index_sql in indexes_sql:
            try:
                self.supabase.rpc('exec_sql', {'sql': index_sql})
                logger.info(f"Created index: {index_sql}")
            except Exception as e:
                logger.warning(f"Failed to create index: {e}")
    
    async def migrate_sqlite_data(self, sqlite_db_path: str):
        """نقل البيانات من SQLite إلى Supabase"""
        import sqlite3
        
        logger.info("Starting data migration from SQLite to Supabase...")
        
        # الاتصال بـ SQLite
        sqlite_conn = sqlite3.connect(sqlite_db_path)
        sqlite_conn.row_factory = sqlite3.Row
        sqlite_cursor = sqlite_conn.cursor()
        
        try:
            # نقل المستخدمين
            await self._migrate_users(sqlite_cursor)
            
            # نقل الشبكات
            await self._migrate_networks(sqlite_cursor)
            
            # نقل البطاقات
            await self._migrate_network_cards(sqlite_cursor)
            
            # نقل المعاملات
            await self._migrate_transactions(sqlite_cursor)
            
            # نقل معاملات المحفظة
            await self._migrate_wallet_transactions(sqlite_cursor)
            
            # نقل الكوبونات
            await self._migrate_coupons(sqlite_cursor)
            
            # نقل الحسابات المحاسبية
            await self._migrate_accounting_data(sqlite_cursor)
            
            logger.info("Data migration completed successfully")
            
        except Exception as e:
            logger.error(f"Data migration failed: {e}")
            raise
        finally:
            sqlite_conn.close()
    
    async def _migrate_users(self, sqlite_cursor):
        """نقل بيانات المستخدمين"""
        logger.info("Migrating users...")
        
        sqlite_cursor.execute('''
            SELECT telegram_id, full_name, phone, role, balance, invite_code, 
                   is_active, total_referrals, total_purchases, total_spent,
                   created_at, last_activity, referred_by, wallet_number
            FROM users
        ''')
        
        users = sqlite_cursor.fetchall()
        
        for user in users:
            try:
                user_data = {
                    'telegram_id': user['telegram_id'],
                    'full_name': user['full_name'],
                    'phone': user['phone'],
                    'role': user['role'],
                    'balance': float(user['balance']),
                    'invite_code': user['invite_code'],
                    'is_active': bool(user['is_active']),
                    'total_referrals': user['total_referrals'],
                    'total_purchases': user['total_purchases'],
                    'total_spent': float(user['total_spent']),
                    'created_at': user['created_at'],
                    'last_activity': user['last_activity'],
                    'wallet_number': user['wallet_number']
                }
                
                # إدراج في Supabase
                result = self.supabase.table('users').insert(user_data).execute()
                
                if result.data:
                    logger.info(f"Migrated user: {user['full_name']}")
                
            except Exception as e:
                logger.error(f"Failed to migrate user {user['full_name']}: {e}")
    
    async def _migrate_networks(self, sqlite_cursor):
        """نقل بيانات الشبكات"""
        logger.info("Migrating networks...")
        
        sqlite_cursor.execute('''
            SELECT supplier_id, name, provider, description, city, location,
                   network_code, is_active, is_approved, created_at
            FROM networks
        ''')
        
        networks = sqlite_cursor.fetchall()
        
        for network in networks:
            try:
                network_data = {
                    'supplier_id': network['supplier_id'],
                    'name': network['name'],
                    'provider': network['provider'],
                    'description': network['description'],
                    'city': network['city'],
                    'location': network['location'],
                    'network_code': network['network_code'],
                    'is_active': bool(network['is_active']),
                    'is_approved': bool(network['is_approved']),
                    'created_at': network['created_at']
                }
                
                result = self.supabase.table('networks').insert(network_data).execute()
                
                if result.data:
                    logger.info(f"Migrated network: {network['name']}")
                
            except Exception as e:
                logger.error(f"Failed to migrate network {network['name']}: {e}")
    
    async def _migrate_network_cards(self, sqlite_cursor):
        """نقل بيانات البطاقات"""
        logger.info("Migrating network cards...")
        
        sqlite_cursor.execute('''
            SELECT network_id, card_code, card_value, is_sold, sold_at, created_at
            FROM network_cards
        ''')
        
        cards = sqlite_cursor.fetchall()
        
        for card in cards:
            try:
                card_data = {
                    'network_id': card['network_id'],
                    'card_code': card['card_code'],
                    'card_value': float(card['card_value']),
                    'is_sold': bool(card['is_sold']),
                    'sold_at': card['sold_at'],
                    'created_at': card['created_at']
                }
                
                result = self.supabase.table('network_cards').insert(card_data).execute()
                
            except Exception as e:
                logger.error(f"Failed to migrate card {card['card_code']}: {e}")
        
        logger.info(f"Migrated {len(cards)} network cards")
    
    async def _migrate_transactions(self, sqlite_cursor):
        """نقل بيانات المعاملات"""
        logger.info("Migrating transactions...")
        
        sqlite_cursor.execute('''
            SELECT id, from_user, to_user, amount, type, description, created_at
            FROM transactions
        ''')
        
        transactions = sqlite_cursor.fetchall()
        
        for transaction in transactions:
            try:
                transaction_data = {
                    'id': transaction['id'],
                    'from_user': transaction['from_user'],
                    'to_user': transaction['to_user'],
                    'amount': float(transaction['amount']),
                    'type': transaction['type'],
                    'description': transaction['description'],
                    'created_at': transaction['created_at']
                }
                
                result = self.supabase.table('transactions').insert(transaction_data).execute()
                
            except Exception as e:
                logger.error(f"Failed to migrate transaction {transaction['id']}: {e}")
        
        logger.info(f"Migrated {len(transactions)} transactions")
    
    async def _migrate_wallet_transactions(self, sqlite_cursor):
        """نقل معاملات المحفظة"""
        logger.info("Migrating wallet transactions...")
        
        sqlite_cursor.execute('''
            SELECT id, user_id, transaction_type, amount, balance_before, 
                   balance_after, reference_id, description, created_at
            FROM wallet_transactions
        ''')
        
        wallet_transactions = sqlite_cursor.fetchall()
        
        for wt in wallet_transactions:
            try:
                wt_data = {
                    'id': wt['id'],
                    'user_id': wt['user_id'],
                    'transaction_type': wt['transaction_type'],
                    'amount': float(wt['amount']),
                    'balance_before': float(wt['balance_before']),
                    'balance_after': float(wt['balance_after']),
                    'reference_id': wt['reference_id'],
                    'description': wt['description'],
                    'created_at': wt['created_at']
                }
                
                result = self.supabase.table('wallet_transactions').insert(wt_data).execute()
                
            except Exception as e:
                logger.error(f"Failed to migrate wallet transaction {wt['id']}: {e}")
        
        logger.info(f"Migrated {len(wallet_transactions)} wallet transactions")
    
    async def _migrate_coupons(self, sqlite_cursor):
        """نقل بيانات الكوبونات"""
        logger.info("Migrating coupons...")
        
        sqlite_cursor.execute('''
            SELECT coupon_code, amount, is_used, used_by, used_at, 
                   created_by, created_at, expires_at, description
            FROM coupons
        ''')
        
        coupons = sqlite_cursor.fetchall()
        
        for coupon in coupons:
            try:
                coupon_data = {
                    'coupon_code': coupon['coupon_code'],
                    'amount': float(coupon['amount']),
                    'is_used': bool(coupon['is_used']),
                    'used_by': coupon['used_by'],
                    'used_at': coupon['used_at'],
                    'created_by': coupon['created_by'],
                    'created_at': coupon['created_at'],
                    'expires_at': coupon['expires_at'],
                    'description': coupon['description']
                }
                
                result = self.supabase.table('coupons').insert(coupon_data).execute()
                
            except Exception as e:
                logger.error(f"Failed to migrate coupon {coupon['coupon_code']}: {e}")
        
        logger.info(f"Migrated {len(coupons)} coupons")
    
    async def _migrate_accounting_data(self, sqlite_cursor):
        """نقل البيانات المحاسبية"""
        logger.info("Migrating accounting data...")
        
        # نقل دليل الحسابات
        try:
            sqlite_cursor.execute('''
                SELECT account_code, account_name, account_type, is_active, created_at
                FROM chart_of_accounts
            ''')
            
            accounts = sqlite_cursor.fetchall()
            
            for account in accounts:
                account_data = {
                    'account_code': account['account_code'],
                    'account_name': account['account_name'],
                    'account_type': account['account_type'],
                    'is_active': bool(account['is_active']),
                    'created_at': account['created_at']
                }
                
                result = self.supabase.table('chart_of_accounts').insert(account_data).execute()
            
            logger.info(f"Migrated {len(accounts)} chart of accounts")
            
        except Exception as e:
            logger.error(f"Failed to migrate chart of accounts: {e}")
        
        # نقل دفتر الأستاذ العام
        try:
            sqlite_cursor.execute('''
                SELECT account_id, debit_amount, credit_amount, description,
                       reference_type, reference_id, created_at, created_by
                FROM general_ledger
            ''')
            
            ledger_entries = sqlite_cursor.fetchall()
            
            for entry in ledger_entries:
                entry_data = {
                    'account_id': entry['account_id'],
                    'debit_amount': float(entry['debit_amount']),
                    'credit_amount': float(entry['credit_amount']),
                    'description': entry['description'],
                    'reference_type': entry['reference_type'],
                    'reference_id': entry['reference_id'],
                    'created_at': entry['created_at'],
                    'created_by': entry['created_by']
                }
                
                result = self.supabase.table('general_ledger').insert(entry_data).execute()
            
            logger.info(f"Migrated {len(ledger_entries)} ledger entries")
            
        except Exception as e:
            logger.error(f"Failed to migrate general ledger: {e}")
    
    # دوال الاستعلام الجديدة
    def get_user_by_telegram_id(self, telegram_id: int) -> Optional[Dict]:
        """الحصول على مستخدم بـ telegram_id"""
        try:
            result = self.supabase.table('users').select('*').eq('telegram_id', telegram_id).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Error getting user by telegram_id: {e}")
            return None
    
    def get_user_by_id(self, user_id: int) -> Optional[Dict]:
        """الحصول على مستخدم بـ ID"""
        try:
            result = self.supabase.table('users').select('*').eq('id', user_id).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Error getting user by id: {e}")
            return None
    
    def update_user_balance(self, user_id: int, new_balance: float) -> bool:
        """تحديث رصيد المستخدم"""
        try:
            result = self.supabase.table('users').update({
                'balance': new_balance,
                'last_activity': datetime.now().isoformat()
            }).eq('id', user_id).execute()
            
            return len(result.data) > 0
        except Exception as e:
            logger.error(f"Error updating user balance: {e}")
            return False
    
    def create_transaction(self, from_user: int, to_user: int, amount: float,
                          transaction_type: str, description: str) -> Optional[str]:
        """إنشاء معاملة جديدة"""
        try:
            transaction_data = {
                'from_user': from_user,
                'to_user': to_user,
                'amount': amount,
                'type': transaction_type,
                'description': description,
                'created_at': datetime.now().isoformat()
            }
            
            result = self.supabase.table('transactions').insert(transaction_data).execute()
            
            if result.data:
                return result.data[0]['id']
            return None
            
        except Exception as e:
            logger.error(f"Error creating transaction: {e}")
            return None
    
    def get_user_transactions(self, user_id: int, limit: int = 50) -> List[Dict]:
        """الحصول على معاملات المستخدم"""
        try:
            result = self.supabase.table('transactions').select('*').or_(
                f'from_user.eq.{user_id},to_user.eq.{user_id}'
            ).order('created_at', desc=True).limit(limit).execute()
            
            return result.data if result.data else []
        except Exception as e:
            logger.error(f"Error getting user transactions: {e}")
            return []
    
    def get_available_cards(self, network_id: int, card_value: float = None) -> List[Dict]:
        """الحصول على البطاقات المتاحة"""
        try:
            query = self.supabase.table('network_cards').select('*').eq('network_id', network_id).eq('is_sold', False)
            
            if card_value:
                query = query.eq('card_value', card_value)
            
            result = query.execute()
            return result.data if result.data else []
        except Exception as e:
            logger.error(f"Error getting available cards: {e}")
            return []

# إنشاء مثيل عام للاستخدام
supabase_db = SupabaseDatabase()