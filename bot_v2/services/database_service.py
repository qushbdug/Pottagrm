#!/usr/bin/env python3
"""
Enhanced Database Service with Connection Pooling and Error Handling
Version 2.0 - Completely Restructured
"""

import sqlite3
import logging
import asyncio
import threading
from contextlib import contextmanager
from typing import Generator, Optional, Dict, Any, List, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import time
import queue
import weakref

from bot_v2.config.settings import (
    DB_PATH, DB_TIMEOUT, DB_MAX_CONNECTIONS, DB_POOL_TIMEOUT,
    DATABASE_OPTIMIZATION, LOGGING_CONFIG_DETAILED
)

logger = logging.getLogger(__name__)

@dataclass
class DatabaseStats:
    """Database performance statistics"""
    total_queries: int = 0
    successful_queries: int = 0
    failed_queries: int = 0
    slow_queries: int = 0
    avg_query_time: float = 0.0
    total_query_time: float = 0.0
    connection_count: int = 0
    pool_size: int = 0
    last_reset: datetime = None

class DatabaseConnection:
    """Individual database connection wrapper"""
    
    def __init__(self, connection: sqlite3.Connection, pool: 'DatabasePool'):
        self.connection = connection
        self.pool = pool
        self.created_at = datetime.now()
        self.last_used = datetime.now()
        self.query_count = 0
        self.is_active = True
        
    def execute(self, query: str, params: tuple = ()) -> sqlite3.Cursor:
        """Execute a query and track statistics"""
        start_time = time.time()
        try:
            cursor = self.connection.execute(query, params)
            self.query_count += 1
            self.last_used = datetime.now()
            
            # Track query performance
            query_time = time.time() - start_time
            self.pool.stats.total_queries += 1
            self.pool.stats.successful_queries += 1
            self.pool.stats.total_query_time += query_time
            self.pool.stats.avg_query_time = (
                self.pool.stats.total_query_time / self.pool.stats.total_queries
            )
            
            # Track slow queries
            if query_time > 1.0:  # Queries taking more than 1 second
                self.pool.stats.slow_queries += 1
                logger.warning(f"Slow query detected: {query_time:.3f}s - {query[:100]}...")
            
            return cursor
            
        except Exception as e:
            self.pool.stats.failed_queries += 1
            logger.error(f"Query execution failed: {e}")
            raise
    
    def executemany(self, query: str, params_list: List[tuple]) -> sqlite3.Cursor:
        """Execute multiple queries and track statistics"""
        start_time = time.time()
        try:
            cursor = self.connection.executemany(query, params_list)
            self.query_count += len(params_list)
            self.last_used = datetime.now()
            
            # Track batch performance
            query_time = time.time() - start_time
            self.pool.stats.total_queries += len(params_list)
            self.pool.stats.successful_queries += len(params_list)
            self.pool.stats.total_query_time += query_time
            
            return cursor
            
        except Exception as e:
            self.pool.stats.failed_queries += len(params_list)
            logger.error(f"Batch query execution failed: {e}")
            raise
    
    def commit(self):
        """Commit transaction"""
        self.connection.commit()
        self.last_used = datetime.now()
    
    def rollback(self):
        """Rollback transaction"""
        self.connection.rollback()
        self.last_used = datetime.now()
    
    def close(self):
        """Close connection and return to pool"""
        if self.is_active:
            self.is_active = False
            self.pool.return_connection(self)
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

class DatabasePool:
    """Database connection pool with advanced features"""
    
    def __init__(self, db_path: str, max_connections: int = 10, timeout: float = 30.0):
        self.db_path = db_path
        self.max_connections = max_connections
        self.timeout = timeout
        self.pool = queue.Queue(maxsize=max_connections)
        self.active_connections = weakref.WeakSet()
        self.stats = DatabaseStats()
        self.stats.last_reset = datetime.now()
        self.lock = threading.Lock()
        self.health_check_thread = None
        self.shutdown_event = threading.Event()
        
        # Initialize pool
        self._initialize_pool()
        self._start_health_check()
    
    def _initialize_pool(self):
        """Initialize the connection pool"""
        try:
            for _ in range(self.max_connections):
                conn = self._create_connection()
                if conn:
                    self.pool.put(conn)
                    self.stats.pool_size += 1
        except Exception as e:
            logger.error(f"Failed to initialize connection pool: {e}")
            raise
    
    def _create_connection(self) -> Optional[DatabaseConnection]:
        """Create a new database connection"""
        try:
            conn = sqlite3.connect(
                self.db_path,
                timeout=self.timeout,
                check_same_thread=False
            )
            
            # Apply optimizations
            conn.execute('PRAGMA foreign_keys = ON')
            conn.execute('PRAGMA journal_mode = WAL')
            conn.execute('PRAGMA synchronous = NORMAL')
            conn.execute('PRAGMA cache_size = 1000')
            conn.execute('PRAGMA temp_store = memory')
            conn.execute('PRAGMA auto_vacuum = INCREMENTAL')
            conn.execute('PRAGMA incremental_vacuum = 1000')
            conn.row_factory = sqlite3.Row
            
            return DatabaseConnection(conn, self)
            
        except Exception as e:
            logger.error(f"Failed to create database connection: {e}")
            return None
    
    def get_connection(self, timeout: float = None) -> DatabaseConnection:
        """Get a connection from the pool"""
        if timeout is None:
            timeout = self.timeout
        
        try:
            # Try to get connection from pool
            conn = self.pool.get(timeout=timeout)
            self.active_connections.add(conn)
            self.stats.connection_count = len(self.active_connections)
            return conn
            
        except queue.Empty:
            # Pool is empty, create new connection if possible
            if len(self.active_connections) < self.max_connections * 2:
                conn = self._create_connection()
                if conn:
                    self.active_connections.add(conn)
                    self.stats.connection_count = len(self.active_connections)
                    logger.warning("Created emergency connection - pool exhausted")
                    return conn
            
            # All connections exhausted
            raise Exception("Database connection pool exhausted")
    
    def return_connection(self, connection: DatabaseConnection):
        """Return a connection to the pool"""
        try:
            if connection.is_active:
                # Reset connection state
                connection.connection.rollback()
                
                # Check if connection is still healthy
                if self._is_connection_healthy(connection):
                    self.pool.put(connection, timeout=1.0)
                else:
                    # Replace unhealthy connection
                    self._replace_connection(connection)
            else:
                # Connection was closed, create replacement
                self._replace_connection(connection)
                
        except Exception as e:
            logger.error(f"Error returning connection to pool: {e}")
            self._replace_connection(connection)
    
    def _is_connection_healthy(self, connection: DatabaseConnection) -> bool:
        """Check if connection is still healthy"""
        try:
            # Simple health check
            connection.connection.execute("SELECT 1")
            return True
        except Exception:
            return False
    
    def _replace_connection(self, old_connection: DatabaseConnection):
        """Replace an unhealthy connection"""
        try:
            # Close old connection
            if hasattr(old_connection.connection, 'close'):
                old_connection.connection.close()
            
            # Create new connection
            new_connection = self._create_connection()
            if new_connection:
                self.pool.put(new_connection, timeout=1.0)
                logger.info("Replaced unhealthy database connection")
            
        except Exception as e:
            logger.error(f"Failed to replace database connection: {e}")
    
    def _start_health_check(self):
        """Start background health check thread"""
        def health_check_worker():
            while not self.shutdown_event.is_set():
                try:
                    self._perform_health_check()
                    time.sleep(60)  # Check every minute
                except Exception as e:
                    logger.error(f"Health check error: {e}")
                    time.sleep(30)  # Retry sooner on error
        
        self.health_check_thread = threading.Thread(
            target=health_check_worker,
            daemon=True,
            name="DatabaseHealthCheck"
        )
        self.health_check_thread.start()
    
    def _perform_health_check(self):
        """Perform health check on all connections"""
        try:
            # Check pool size
            current_pool_size = self.pool.qsize()
            if current_pool_size < self.max_connections * 0.5:
                logger.warning(f"Pool size low: {current_pool_size}/{self.max_connections}")
                
                # Replenish pool
                for _ in range(self.max_connections - current_pool_size):
                    conn = self._create_connection()
                    if conn:
                        self.pool.put(conn, timeout=1.0)
                        self.stats.pool_size += 1
            
            # Check for stale connections
            current_time = datetime.now()
            stale_connections = []
            
            for conn in list(self.active_connections):
                if (current_time - conn.last_used).total_seconds() > 3600:  # 1 hour
                    stale_connections.append(conn)
            
            # Close stale connections
            for conn in stale_connections:
                conn.close()
                logger.info("Closed stale database connection")
            
            # Reset statistics daily
            if (current_time - self.stats.last_reset).days >= 1:
                self._reset_statistics()
                
        except Exception as e:
            logger.error(f"Health check failed: {e}")
    
    def _reset_statistics(self):
        """Reset daily statistics"""
        with self.lock:
            self.stats = DatabaseStats()
            self.stats.last_reset = datetime.now()
            logger.info("Database statistics reset")
    
    def get_statistics(self) -> DatabaseStats:
        """Get current database statistics"""
        with self.lock:
            return self.stats
    
    def close_all_connections(self):
        """Close all connections in the pool"""
        try:
            # Close active connections
            for conn in list(self.active_connections):
                conn.close()
            
            # Close pool connections
            while not self.pool.empty():
                try:
                    conn = self.pool.get_nowait()
                    if hasattr(conn.connection, 'close'):
                        conn.connection.close()
                except queue.Empty:
                    break
            
            # Signal shutdown
            self.shutdown_event.set()
            
            # Wait for health check thread
            if self.health_check_thread and self.health_check_thread.is_alive():
                self.health_check_thread.join(timeout=5.0)
            
            logger.info("All database connections closed")
            
        except Exception as e:
            logger.error(f"Error closing connections: {e}")

class DatabaseManager:
    """Main database manager class"""
    
    def __init__(self, db_path: str = None, max_connections: int = None):
        self.db_path = db_path or DB_PATH
        self.max_connections = max_connections or DB_MAX_CONNECTIONS
        self.pool = DatabasePool(self.db_path, self.max_connections, DB_TIMEOUT)
        self.transaction_depth = 0
        self._local = threading.local()
        
        # Initialize database schema
        self._initialize_schema()
    
    def _initialize_schema(self):
        """Initialize database schema"""
        try:
            with self.get_connection() as conn:
                self._create_tables(conn)
                self._create_indexes(conn)
                self._insert_initial_data(conn)
                logger.info("Database schema initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize database schema: {e}")
            raise
    
    def _create_tables(self, conn: DatabaseConnection):
        """Create all required tables"""
        tables = [
            # Users table
            """
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
                email TEXT,
                password_hash TEXT,
                two_factor_enabled BOOLEAN DEFAULT 0,
                two_factor_secret TEXT,
                login_attempts INTEGER DEFAULT 0,
                locked_until TIMESTAMP,
                preferences TEXT,  -- JSON string
                FOREIGN KEY(referred_by) REFERENCES users(id)
            )
            """,
            
            # Networks table
            """
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
                network_type TEXT DEFAULT 'mobile',
                coverage_area TEXT,
                speed_info TEXT,
                pricing_info TEXT,
                status TEXT DEFAULT 'active',
                FOREIGN KEY(supplier_id) REFERENCES users(id),
                FOREIGN KEY(approved_by) REFERENCES users(id),
                FOREIGN KEY(created_by) REFERENCES users(id)
            )
            """,
            
            # Card categories table
            """
            CREATE TABLE IF NOT EXISTS card_categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                network_id INTEGER,
                name TEXT NOT NULL,
                value REAL NOT NULL,
                price REAL NOT NULL,
                currency TEXT DEFAULT 'YER',
                is_available BOOLEAN DEFAULT 1,
                stock_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                category_name TEXT,
                description TEXT,
                validity_period INTEGER DEFAULT 30,  -- days
                activation_fee REAL DEFAULT 0.0,
                discount_rate REAL DEFAULT 0.0,
                bulk_discounts TEXT,  -- JSON string
                FOREIGN KEY(network_id) REFERENCES networks(id)
            )
            """,
            
            # Cards table
            """
            CREATE TABLE IF NOT EXISTS cards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category_id INTEGER,
                card_number TEXT NOT NULL,
                card_value REAL NOT NULL,
                card_price REAL NOT NULL,
                is_sold BOOLEAN DEFAULT 0,
                sold_at TIMESTAMP,
                sold_to INTEGER,
                sold_by INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                status TEXT DEFAULT 'available',
                batch_id TEXT,
                supplier_id INTEGER,
                network_id INTEGER,
                activation_code TEXT,
                pin_code TEXT,
                serial_number TEXT,
                card_type TEXT DEFAULT 'internet',
                FOREIGN KEY(category_id) REFERENCES card_categories(id),
                FOREIGN KEY(sold_to) REFERENCES users(id),
                FOREIGN KEY(sold_by) REFERENCES users(id),
                FOREIGN KEY(supplier_id) REFERENCES users(id),
                FOREIGN KEY(network_id) REFERENCES networks(id)
            )
            """,
            
            # Transactions table
            """
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_user INTEGER,
                to_user INTEGER,
                amount REAL NOT NULL,
                type TEXT NOT NULL,  -- 'credit', 'debit', 'transfer'
                status TEXT DEFAULT 'pending',
                reference_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_withdrawable BOOLEAN DEFAULT 1,
                description TEXT,
                accounting_entry_id INTEGER,
                transaction_hash TEXT,
                fee_amount REAL DEFAULT 0.0,
                tax_amount REAL DEFAULT 0.0,
                currency TEXT DEFAULT 'YER',
                exchange_rate REAL DEFAULT 1.0,
                metadata TEXT,  -- JSON string
                FOREIGN KEY(from_user) REFERENCES users(id),
                FOREIGN KEY(to_user) REFERENCES users(id)
            )
            """,
            
            # Wallet transactions table
            """
            CREATE TABLE IF NOT EXISTS wallet_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                transaction_type TEXT NOT NULL,  -- 'credit', 'debit'
                amount REAL NOT NULL,
                balance_before REAL NOT NULL,
                balance_after REAL NOT NULL,
                reference_id TEXT,
                description TEXT,
                status TEXT DEFAULT 'completed',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT,  -- JSON string
                fee_amount REAL DEFAULT 0.0,
                tax_amount REAL DEFAULT 0.0,
                currency TEXT DEFAULT 'YER',
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
            """,
            
            # Commissions table
            """
            CREATE TABLE IF NOT EXISTS commissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                amount REAL NOT NULL,
                commission_rate REAL NOT NULL,
                commission_amount REAL NOT NULL,
                transaction_id INTEGER,
                network_id INTEGER,
                card_category_id INTEGER,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                paid_at TIMESTAMP,
                payment_method TEXT,
                reference_number TEXT,
                notes TEXT,
                FOREIGN KEY(user_id) REFERENCES users(id),
                FOREIGN KEY(transaction_id) REFERENCES transactions(id),
                FOREIGN KEY(network_id) REFERENCES networks(id),
                FOREIGN KEY(card_category_id) REFERENCES card_categories(id)
            )
            """,
            
            # Referrals table
            """
            CREATE TABLE IF NOT EXISTS referrals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                referrer_id INTEGER NOT NULL,
                referred_id INTEGER NOT NULL,
                status TEXT DEFAULT 'pending',
                bonus_amount REAL DEFAULT 0.0,
                bonus_paid BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                referral_code TEXT,
                bonus_type TEXT DEFAULT 'fixed',  -- 'fixed', 'percentage'
                bonus_value REAL DEFAULT 0.0,
                FOREIGN KEY(referrer_id) REFERENCES users(id),
                FOREIGN KEY(referred_id) REFERENCES users(id)
            )
            """,
            
            # Notifications table
            """
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                type TEXT DEFAULT 'info',  -- 'info', 'warning', 'error', 'success'
                is_read BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                read_at TIMESTAMP,
                priority TEXT DEFAULT 'normal',  -- 'low', 'normal', 'high', 'urgent'
                category TEXT DEFAULT 'general',
                action_url TEXT,
                expires_at TIMESTAMP,
                metadata TEXT,  -- JSON string
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
            """,
            
            # Audit log table
            """
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                action TEXT NOT NULL,
                table_name TEXT,
                record_id INTEGER,
                old_values TEXT,  -- JSON string
                new_values TEXT,  -- JSON string
                ip_address TEXT,
                user_agent TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                session_id TEXT,
                severity TEXT DEFAULT 'info',  -- 'info', 'warning', 'error', 'critical'
                description TEXT,
                metadata TEXT,  -- JSON string
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
            """,
            
            # System settings table
            """
            CREATE TABLE IF NOT EXISTS system_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                setting_key TEXT UNIQUE NOT NULL,
                setting_value TEXT NOT NULL,
                setting_type TEXT DEFAULT 'string',  -- 'string', 'integer', 'float', 'boolean', 'json'
                description TEXT,
                is_public BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_by INTEGER,
                category TEXT DEFAULT 'general',
                validation_rules TEXT,  -- JSON string
                FOREIGN KEY(updated_by) REFERENCES users(id)
            )
            """,
            
            # API keys table
            """
            CREATE TABLE IF NOT EXISTS api_keys (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                key_name TEXT NOT NULL,
                api_key TEXT UNIQUE NOT NULL,
                permissions TEXT,  -- JSON string
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_used TIMESTAMP,
                expires_at TIMESTAMP,
                rate_limit_requests INTEGER DEFAULT 1000,
                rate_limit_window INTEGER DEFAULT 3600,
                ip_whitelist TEXT,  -- JSON string
                metadata TEXT,  -- JSON string
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
            """,
            
            # Rate limiting table
            """
            CREATE TABLE IF NOT EXISTS rate_limits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                ip_address TEXT,
                endpoint TEXT NOT NULL,
                request_count INTEGER DEFAULT 1,
                window_start TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_blocked BOOLEAN DEFAULT 0,
                blocked_until TIMESTAMP,
                reason TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
            """,
            
            # Performance metrics table
            """
            CREATE TABLE IF NOT EXISTS performance_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                metric_name TEXT NOT NULL,
                metric_value REAL NOT NULL,
                metric_unit TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                category TEXT DEFAULT 'general',
                tags TEXT,  -- JSON string
                metadata TEXT  -- JSON string
            )
            """,
            
            # Error logs table
            """
            CREATE TABLE IF NOT EXISTS error_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                error_type TEXT NOT NULL,
                error_message TEXT NOT NULL,
                stack_trace TEXT,
                user_id INTEGER,
                ip_address TEXT,
                user_agent TEXT,
                request_data TEXT,  -- JSON string
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                severity TEXT DEFAULT 'error',
                resolved BOOLEAN DEFAULT 0,
                resolved_at TIMESTAMP,
                resolved_by INTEGER,
                notes TEXT,
                FOREIGN KEY(user_id) REFERENCES users(id),
                FOREIGN KEY(resolved_by) REFERENCES users(id)
            )
            """
        ]
        
        for table_sql in tables:
            try:
                conn.execute(table_sql)
            except Exception as e:
                logger.error(f"Failed to create table: {e}")
                raise
    
    def _create_indexes(self, conn: DatabaseConnection):
        """Create database indexes for performance"""
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_users_telegram_id ON users(telegram_id)",
            "CREATE INDEX IF NOT EXISTS idx_users_phone ON users(phone)",
            "CREATE INDEX IF NOT EXISTS idx_users_wallet_number ON users(wallet_number)",
            "CREATE INDEX IF NOT EXISTS idx_users_role ON users(role)",
            "CREATE INDEX IF NOT EXISTS idx_users_is_active ON users(is_active)",
            "CREATE INDEX IF NOT EXISTS idx_users_created_at ON users(created_at)",
            "CREATE INDEX IF NOT EXISTS idx_users_last_activity ON users(last_activity)",
            
            "CREATE INDEX IF NOT EXISTS idx_networks_supplier_id ON networks(supplier_id)",
            "CREATE INDEX IF NOT EXISTS idx_networks_network_code ON networks(network_code)",
            "CREATE INDEX IF NOT EXISTS idx_networks_is_active ON networks(is_active)",
            "CREATE INDEX IF NOT EXISTS idx_networks_network_type ON networks(network_type)",
            
            "CREATE INDEX IF NOT EXISTS idx_card_categories_network_id ON card_categories(network_id)",
            "CREATE INDEX IF NOT EXISTS idx_card_categories_is_available ON card_categories(is_available)",
            "CREATE INDEX IF NOT EXISTS idx_card_categories_value ON card_categories(value)",
            
            "CREATE INDEX IF NOT EXISTS idx_cards_category_id ON cards(category_id)",
            "CREATE INDEX IF NOT EXISTS idx_cards_is_sold ON cards(is_sold)",
            "CREATE INDEX IF NOT EXISTS idx_cards_supplier_id ON cards(supplier_id)",
            "CREATE INDEX IF NOT EXISTS idx_cards_status ON cards(status)",
            
            "CREATE INDEX IF NOT EXISTS idx_transactions_from_user ON transactions(from_user)",
            "CREATE INDEX IF NOT EXISTS idx_transactions_to_user ON transactions(to_user)",
            "CREATE INDEX IF NOT EXISTS idx_transactions_type ON transactions(type)",
            "CREATE INDEX IF NOT EXISTS idx_transactions_status ON transactions(status)",
            "CREATE INDEX IF NOT EXISTS idx_transactions_created_at ON transactions(created_at)",
            
            "CREATE INDEX IF NOT EXISTS idx_wallet_transactions_user_id ON wallet_transactions(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_wallet_transactions_type ON wallet_transactions(transaction_type)",
            "CREATE INDEX IF NOT EXISTS idx_wallet_transactions_created_at ON wallet_transactions(created_at)",
            
            "CREATE INDEX IF NOT EXISTS idx_commissions_user_id ON commissions(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_commissions_status ON commissions(status)",
            "CREATE INDEX IF NOT EXISTS idx_commissions_created_at ON commissions(created_at)",
            
            "CREATE INDEX IF NOT EXISTS idx_referrals_referrer_id ON referrals(referrer_id)",
            "CREATE INDEX IF NOT EXISTS idx_referrals_referred_id ON referrals(referred_id)",
            "CREATE INDEX IF NOT EXISTS idx_referrals_status ON referrals(status)",
            
            "CREATE INDEX IF NOT EXISTS idx_notifications_user_id ON notifications(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_notifications_is_read ON notifications(is_read)",
            "CREATE INDEX IF NOT EXISTS idx_notifications_created_at ON notifications(created_at)",
            
            "CREATE INDEX IF NOT EXISTS idx_audit_log_user_id ON audit_log(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_audit_log_action ON audit_log(action)",
            "CREATE INDEX IF NOT EXISTS idx_audit_log_created_at ON audit_log(created_at)",
            
            "CREATE INDEX IF NOT EXISTS idx_rate_limits_user_ip ON rate_limits(user_id, ip_address)",
            "CREATE INDEX IF NOT EXISTS idx_rate_limits_endpoint ON rate_limits(endpoint)",
            "CREATE INDEX IF NOT EXISTS idx_rate_limits_window ON rate_limits(window_start)",
            
            "CREATE INDEX IF NOT EXISTS idx_performance_metrics_name ON performance_metrics(metric_name)",
            "CREATE INDEX IF NOT EXISTS idx_performance_metrics_timestamp ON performance_metrics(timestamp)",
            
            "CREATE INDEX IF NOT EXISTS idx_error_logs_type ON error_logs(error_type)",
            "CREATE INDEX IF NOT EXISTS idx_error_logs_severity ON error_logs(severity)",
            "CREATE INDEX IF NOT EXISTS idx_error_logs_created_at ON error_logs(created_at)"
        ]
        
        for index_sql in indexes:
            try:
                conn.execute(index_sql)
            except Exception as e:
                logger.error(f"Failed to create index: {e}")
                # Continue with other indexes
    
    def _insert_initial_data(self, conn: DatabaseConnection):
        """Insert initial system data"""
        try:
            # Insert default system settings
            default_settings = [
                ('system_version', '2.0.0', 'string', 'Current system version'),
                ('maintenance_mode', 'false', 'boolean', 'System maintenance mode'),
                ('registration_enabled', 'true', 'boolean', 'User registration enabled'),
                ('max_login_attempts', '3', 'integer', 'Maximum login attempts'),
                ('session_timeout', '3600', 'integer', 'Session timeout in seconds'),
                ('default_commission_rate', '0.05', 'float', 'Default commission rate'),
                ('min_transfer_amount', '100.0', 'float', 'Minimum transfer amount'),
                ('max_transfer_amount', '100000.0', 'float', 'Maximum transfer amount'),
                ('support_telegram', '@admin_username', 'string', 'Support Telegram username'),
                ('support_email', 'support@example.com', 'string', 'Support email address')
            ]
            
            for key, value, value_type, description in default_settings:
                conn.execute('''
                    INSERT OR IGNORE INTO system_settings 
                    (setting_key, setting_value, setting_type, description)
                    VALUES (?, ?, ?, ?)
                ''', (key, value, value_type, description))
            
            conn.commit()
            logger.info("Initial system data inserted")
            
        except Exception as e:
            logger.error(f"Failed to insert initial data: {e}")
            conn.rollback()
    
    @contextmanager
    def get_connection(self, timeout: float = None) -> Generator[DatabaseConnection, None, None]:
        """Get a database connection from the pool"""
        connection = None
        try:
            connection = self.pool.get_connection(timeout)
            yield connection
        except Exception as e:
            if connection:
                connection.rollback()
            logger.error(f"Database operation failed: {e}")
            raise
        finally:
            if connection:
                connection.close()
    
    @contextmanager
    def transaction(self, timeout: float = None) -> Generator[DatabaseConnection, None, None]:
        """Get a database connection with transaction support"""
        connection = None
        try:
            connection = self.pool.get_connection(timeout)
            yield connection
            connection.commit()
        except Exception as e:
            if connection:
                connection.rollback()
            logger.error(f"Transaction failed: {e}")
            raise
        finally:
            if connection:
                connection.close()
    
    def execute_query(self, query: str, params: tuple = (), timeout: float = None) -> List[Dict[str, Any]]:
        """Execute a query and return results as list of dictionaries"""
        try:
            with self.get_connection(timeout) as conn:
                cursor = conn.execute(query, params)
                columns = [description[0] for description in cursor.description]
                return [dict(zip(columns, row)) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            raise
    
    def execute_single(self, query: str, params: tuple = (), timeout: float = None) -> Optional[Dict[str, Any]]:
        """Execute a query and return single result"""
        try:
            with self.get_connection(timeout) as conn:
                cursor = conn.execute(query, params)
                columns = [description[0] for description in cursor.description]
                row = cursor.fetchone()
                return dict(zip(columns, row)) if row else None
        except Exception as e:
            logger.error(f"Single query execution failed: {e}")
            raise
    
    def execute_update(self, query: str, params: tuple = (), timeout: float = None) -> int:
        """Execute an update query and return affected rows"""
        try:
            with self.transaction(timeout) as conn:
                cursor = conn.execute(query, params)
                return cursor.rowcount
        except Exception as e:
            logger.error(f"Update query execution failed: {e}")
            raise
    
    def execute_many(self, query: str, params_list: List[tuple], timeout: float = None) -> int:
        """Execute multiple queries and return total affected rows"""
        try:
            with self.transaction(timeout) as conn:
                cursor = conn.executemany(query, params_list)
                return cursor.rowcount
        except Exception as e:
            logger.error(f"Batch query execution failed: {e}")
            raise
    
    def table_exists(self, table_name: str) -> bool:
        """Check if a table exists"""
        try:
            with self.get_connection() as conn:
                cursor = conn.execute('''
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name=?
                ''', (table_name,))
                return cursor.fetchone() is not None
        except Exception as e:
            logger.error(f"Table existence check failed: {e}")
            return False
    
    def get_table_info(self, table_name: str) -> List[Dict[str, Any]]:
        """Get table structure information"""
        try:
            with self.get_connection() as conn:
                cursor = conn.execute('PRAGMA table_info(?)', (table_name,))
                columns = [description[0] for description in cursor.description]
                return [dict(zip(columns, row)) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Table info retrieval failed: {e}")
            return []
    
    def get_table_count(self, table_name: str) -> int:
        """Get row count for a table"""
        try:
            with self.get_connection() as conn:
                cursor = conn.execute(f'SELECT COUNT(*) as count FROM {table_name}')
                result = cursor.fetchone()
                return result['count'] if result else 0
        except Exception as e:
            logger.error(f"Table count retrieval failed: {e}")
            return 0
    
    def backup_database(self, backup_path: str) -> bool:
        """Create a database backup"""
        try:
            import shutil
            shutil.copy2(self.db_path, backup_path)
            logger.info(f"Database backup created: {backup_path}")
            return True
        except Exception as e:
            logger.error(f"Database backup failed: {e}")
            return False
    
    def optimize_database(self) -> bool:
        """Optimize database performance"""
        try:
            with self.get_connection() as conn:
                # Analyze tables
                conn.execute('ANALYZE')
                
                # Vacuum database
                conn.execute('VACUUM')
                
                # Reindex
                conn.execute('REINDEX')
                
                logger.info("Database optimization completed")
                return True
        except Exception as e:
            logger.error(f"Database optimization failed: {e}")
            return False
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Get comprehensive database statistics"""
        try:
            stats = self.pool.get_statistics()
            
            # Get table sizes
            table_sizes = {}
            with self.get_connection() as conn:
                cursor = conn.execute('''
                    SELECT name FROM sqlite_master 
                    WHERE type='table'
                ''')
                tables = [row['name'] for row in cursor.fetchall()]
                
                for table in tables:
                    try:
                        cursor = conn.execute(f'SELECT COUNT(*) as count FROM {table}')
                        result = cursor.fetchone()
                        table_sizes[table] = result['count'] if result else 0
                    except Exception:
                        table_sizes[table] = 0
            
            return {
                'pool_stats': {
                    'total_queries': stats.total_queries,
                    'successful_queries': stats.successful_queries,
                    'failed_queries': stats.failed_queries,
                    'slow_queries': stats.slow_queries,
                    'avg_query_time': round(stats.avg_query_time, 4),
                    'connection_count': stats.connection_count,
                    'pool_size': stats.pool_size
                },
                'table_sizes': table_sizes,
                'database_size': self._get_database_size(),
                'last_optimization': self._get_last_optimization()
            }
            
        except Exception as e:
            logger.error(f"Database statistics retrieval failed: {e}")
            return {}
    
    def _get_database_size(self) -> int:
        """Get database file size in bytes"""
        try:
            import os
            return os.path.getsize(self.db_path)
        except Exception:
            return 0
    
    def _get_last_optimization(self) -> Optional[datetime]:
        """Get last database optimization time"""
        try:
            with self.get_connection() as conn:
                cursor = conn.execute('''
                    SELECT value FROM system_settings 
                    WHERE setting_key = 'last_optimization'
                ''')
                result = cursor.fetchone()
                if result:
                    return datetime.fromisoformat(result['value'])
        except Exception:
            pass
        return None
    
    def close(self):
        """Close database manager and all connections"""
        try:
            self.pool.close_all_connections()
            logger.info("Database manager closed")
        except Exception as e:
            logger.error(f"Error closing database manager: {e}")

# Global database manager instance
_db_manager: Optional[DatabaseManager] = None

def get_database_manager() -> DatabaseManager:
    """Get global database manager instance"""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager

def close_database_manager():
    """Close global database manager"""
    global _db_manager
    if _db_manager:
        _db_manager.close()
        _db_manager = None

# Convenience functions for backward compatibility
def get_db_connection():
    """Get database connection (backward compatibility)"""
    return get_database_manager().get_connection()

def execute_query(query: str, params: tuple = ()) -> List[Dict[str, Any]]:
    """Execute query (backward compatibility)"""
    return get_database_manager().execute_query(query, params)

def execute_single(query: str, params: tuple = ()) -> Optional[Dict[str, Any]]:
    """Execute single query (backward compatibility)"""
    return get_database_manager().execute_single(query, params)

def execute_update(query: str, params: tuple = ()) -> int:
    """Execute update (backward compatibility)"""
    return get_database_manager().execute_update(query, params)

# Cleanup on module unload
import atexit
atexit.register(close_database_manager)

if __name__ == "__main__":
    # Test database manager
    try:
        db_manager = DatabaseManager()
        print("✅ Database manager initialized successfully")
        
        # Test connection
        with db_manager.get_connection() as conn:
            result = conn.execute("SELECT 1 as test").fetchone()
            print(f"✅ Test query successful: {result['test']}")
        
        # Get statistics
        stats = db_manager.get_database_stats()
        print(f"✅ Database statistics: {stats}")
        
        db_manager.close()
        print("✅ Database manager closed successfully")
        
    except Exception as e:
        print(f"❌ Database manager test failed: {e}")
        exit(1)