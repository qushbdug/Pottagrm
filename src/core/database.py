#!/usr/bin/env python3
"""
Professional Database Management for Yemen Net Bot
Advanced database operations with connection pooling, error handling, and security.
"""

import logging
import sqlite3
import uuid
import random
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from .config import config, USER_ROLES

logger = logging.getLogger(__name__)


@dataclass
class User:
    """User data model."""
    id: int
    telegram_id: int
    full_name: str
    phone: str
    role: str
    balance: float
    invite_code: Optional[str]
    is_active: bool
    bank_account: Optional[str]
    total_referrals: int
    total_purchases: int
    total_spent: float
    created_at: datetime
    last_activity: datetime
    referred_by: Optional[int]
    wallet_number: Optional[str]


@dataclass
class Network:
    """Network data model."""
    id: str
    supplier_id: int
    name: str
    city: str
    network_code: str
    is_active: bool
    is_approved: bool
    created_at: datetime
    approved_at: Optional[datetime]
    approved_by: Optional[int]


class DatabaseManager:
    """Professional database manager with connection pooling and error handling."""
    
    def __init__(self):
        self.db_path = config.database.path
        self._init_database()
    
    def _init_database(self) -> None:
        """Initialize database with all required tables."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                self._create_missing_tables(cursor)
                conn.commit()
                logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    def _create_missing_tables(self, cursor: sqlite3.Cursor) -> None:
        """Create only missing tables to avoid conflicts."""
        # Check if transactions table has the new structure
        cursor.execute("PRAGMA table_info(transactions)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'user_id' not in columns:
            # Create new transactions table with updated structure
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS transactions_new (
                    id TEXT PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    transaction_type TEXT NOT NULL,
                    amount REAL NOT NULL,
                    balance_before REAL NOT NULL,
                    balance_after REAL NOT NULL,
                    description TEXT,
                    reference_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(user_id) REFERENCES users(id)
                )
            ''')
            
            # Migrate existing data if possible
            try:
                cursor.execute('''
                    INSERT INTO transactions_new (id, user_id, transaction_type, amount, 
                    balance_before, balance_after, description, reference_id, created_at)
                    SELECT id, from_user, type, amount, 0, 0, description, reference_id, created_at
                    FROM transactions WHERE from_user IS NOT NULL
                ''')
                
                cursor.execute('''
                    INSERT INTO transactions_new (id, user_id, transaction_type, amount, 
                    balance_before, balance_after, description, reference_id, created_at)
                    SELECT id || '_to', to_user, 'received', amount, 0, 0, description, reference_id, created_at
                    FROM transactions WHERE to_user IS NOT NULL
                ''')
                
                # Drop old table and rename new one
                cursor.execute('DROP TABLE transactions')
                cursor.execute('ALTER TABLE transactions_new RENAME TO transactions')
                
                logger.info("Successfully migrated transactions table")
                
            except Exception as e:
                logger.warning(f"Could not migrate transactions table: {e}")
                # Keep the new table structure
                pass
        
        # Create missing indexes if they don't exist
        try:
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_transactions_user ON transactions(user_id)')
        except Exception as e:
            logger.warning(f"Could not create transactions index: {e}")
        
        try:
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_telegram_id ON users(telegram_id)')
        except Exception as e:
            logger.warning(f"Could not create users index: {e}")
        
        try:
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_phone ON users(phone)')
        except Exception as e:
            logger.warning(f"Could not create phone index: {e}")
    
    @contextmanager
    def get_connection(self):
        """Get database connection with proper error handling."""
        conn = None
        try:
            conn = sqlite3.connect(
                self.db_path,
                timeout=config.database.timeout
            )
            conn.execute(f'PRAGMA journal_mode = {config.database.journal_mode}')
            conn.execute(f'PRAGMA synchronous = {config.database.synchronous}')
            conn.execute(f'PRAGMA cache_size = {config.database.cache_size}')
            conn.execute(f'PRAGMA temp_store = {config.database.temp_store}')
            conn.execute('PRAGMA foreign_keys = ON')
            conn.row_factory = sqlite3.Row
            yield conn
        except Exception as e:
            logger.error(f"Database connection error: {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()
    
    def create_user(self, telegram_id: int, full_name: str, phone: str, role: str = 'customer') -> Optional[User]:
        """Create a new user with proper validation."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Generate unique invite code and wallet number
                invite_code = self._generate_invite_code()
                wallet_number = self._generate_wallet_number()
                
                cursor.execute('''
                    INSERT INTO users (
                        telegram_id, full_name, phone, role, invite_code, wallet_number,
                        balance, is_active, total_referrals, total_purchases, total_spent,
                        created_at, last_activity
                    ) VALUES (?, ?, ?, ?, ?, ?, 0.0, 1, 0, 0, 0.0, 
                    CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                ''', (telegram_id, full_name, phone, role, invite_code, wallet_number))
                
                user_id = cursor.lastrowid
                conn.commit()
                
                logger.info(f"Created user {user_id} with telegram_id {telegram_id}")
                return self.get_user_by_id(user_id)
                
        except sqlite3.IntegrityError as e:
            logger.warning(f"User creation failed - integrity error: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to create user: {e}")
            return None
    
    def get_user(self, telegram_id: int) -> Optional[User]:
        """Get user by telegram ID."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM users WHERE telegram_id = ?', (telegram_id,))
                row = cursor.fetchone()
                
                if row:
                    return self._row_to_user(row)
                return None
                
        except Exception as e:
            logger.error(f"Failed to get user {telegram_id}: {e}")
            return None
    
    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Get user by internal ID."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
                row = cursor.fetchone()
                
                if row:
                    return self._row_to_user(row)
                return None
                
        except Exception as e:
            logger.error(f"Failed to get user by ID {user_id}: {e}")
            return None
    
    def get_user_by_phone(self, phone: str) -> Optional[User]:
        """Get user by phone number."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM users WHERE phone = ?', (phone,))
                row = cursor.fetchone()
                
                if row:
                    return self._row_to_user(row)
                return None
                
        except Exception as e:
            logger.error(f"Failed to get user by phone {phone}: {e}")
            return None
    
    def update_user_balance(self, user_id: int, amount: float, transaction_type: str, description: str = "") -> bool:
        """Update user balance with transaction logging."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get current balance
                cursor.execute('SELECT balance FROM users WHERE id = ?', (user_id,))
                current_balance = cursor.fetchone()['balance']
                new_balance = current_balance + amount
                
                # Update balance
                cursor.execute('UPDATE users SET balance = ? WHERE id = ?', (new_balance, user_id))
                
                # Log transaction
                transaction_id = str(uuid.uuid4())
                cursor.execute('''
                    INSERT INTO transactions (
                        id, user_id, transaction_type, amount, balance_before, 
                        balance_after, description
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (transaction_id, user_id, transaction_type, amount, current_balance, new_balance, description))
                
                conn.commit()
                logger.info(f"Updated balance for user {user_id}: {amount} -> {new_balance}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to update user balance: {e}")
            return False
    
    def update_user_activity(self, user_id: int) -> bool:
        """Update user's last activity timestamp."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE users SET last_activity = CURRENT_TIMESTAMP 
                    WHERE id = ?
                ''', (user_id,))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Failed to update user activity: {e}")
            return False
    
    def get_user_transactions(self, user_id: int, limit: int = 10) -> List[Dict]:
        """Get user's recent transactions."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM transactions 
                    WHERE user_id = ? 
                    ORDER BY created_at DESC 
                    LIMIT ?
                ''', (user_id, limit))
                
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
                
        except Exception as e:
            logger.error(f"Failed to get user transactions: {e}")
            return []
    
    def _generate_invite_code(self) -> str:
        """Generate unique invite code."""
        while True:
            code = ''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=8))
            try:
                with self.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute('SELECT id FROM users WHERE invite_code = ?', (code,))
                    if not cursor.fetchone():
                        return code
            except Exception:
                continue
    
    def _generate_wallet_number(self) -> str:
        """Generate unique wallet number."""
        while True:
            number = ''.join(random.choices('0123456789', k=10))
            try:
                with self.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute('SELECT id FROM users WHERE wallet_number = ?', (number,))
                    if not cursor.fetchone():
                        return number
            except Exception:
                continue
    
    def _row_to_user(self, row: sqlite3.Row) -> User:
        """Convert database row to User object."""
        return User(
            id=row['id'],
            telegram_id=row['telegram_id'],
            full_name=row['full_name'],
            phone=row['phone'],
            role=row['role'],
            balance=row['balance'],
            invite_code=row['invite_code'],
            is_active=bool(row['is_active']),
            bank_account=row.get('bank_account'),
            total_referrals=row.get('total_referrals', 0),
            total_purchases=row.get('total_purchases', 0),
            total_spent=row.get('total_spent', 0.0),
            created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else datetime.now(),
            last_activity=datetime.fromisoformat(row['last_activity']) if row['last_activity'] else datetime.now(),
            referred_by=row.get('referred_by'),
            wallet_number=row.get('wallet_number')
        )


# Global database instance
db = DatabaseManager()