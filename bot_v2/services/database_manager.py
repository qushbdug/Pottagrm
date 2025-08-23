"""
Enhanced Database Manager for Yemen Net Bot v2
Implements connection pooling, async operations, and proper error handling
"""

import sqlite3
import asyncio
import logging
import threading
import time
from typing import Dict, List, Any, Optional, Tuple, Union
from contextlib import contextmanager
from queue import Queue, Empty
from dataclasses import dataclass
from functools import wraps

from ..core.exceptions import DatabaseException, ConfigurationException
from ..core.config import config

@dataclass
class DatabaseStats:
    """Database performance statistics"""
    total_queries: int = 0
    successful_queries: int = 0
    failed_queries: int = 0
    slow_queries: int = 0
    avg_query_time: float = 0.0
    total_query_time: float = 0.0
    connection_errors: int = 0
    last_error: Optional[str] = None
    last_error_time: Optional[float] = None

class ConnectionPool:
    """SQLite connection pool for better performance"""
    
    def __init__(self, db_path: str, max_connections: int = 10, timeout: float = 30.0):
        self.db_path = db_path
        self.max_connections = max_connections
        self.timeout = timeout
        self.connections: Queue = Queue(maxsize=max_connections)
        self.active_connections = 0
        self.lock = threading.Lock()
        self.logger = logging.getLogger('DatabasePool')
        
        # Initialize pool
        self._initialize_pool()
    
    def _initialize_pool(self):
        """Initialize connection pool"""
        try:
            for _ in range(self.max_connections):
                conn = self._create_connection()
                if conn:
                    self.connections.put(conn)
            self.logger.info(f"Connection pool initialized with {self.max_connections} connections")
        except Exception as e:
            self.logger.error(f"Failed to initialize connection pool: {e}")
            raise DatabaseException(f"Connection pool initialization failed: {e}")
    
    def _create_connection(self) -> Optional[sqlite3.Connection]:
        """Create a new database connection"""
        try:
            conn = sqlite3.connect(
                self.db_path,
                timeout=self.timeout,
                check_same_thread=False
            )
            conn.row_factory = sqlite3.Row
            
            # Enable foreign keys and WAL mode for better performance
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute("PRAGMA journal_mode = WAL")
            conn.execute("PRAGMA synchronous = NORMAL")
            conn.execute("PRAGMA cache_size = 10000")
            conn.execute("PRAGMA temp_store = MEMORY")
            
            return conn
        except Exception as e:
            self.logger.error(f"Failed to create database connection: {e}")
            return None
    
    @contextmanager
    def get_connection(self):
        """Get a connection from the pool"""
        conn = None
        try:
            # Try to get connection from pool
            try:
                conn = self.connections.get(timeout=5.0)
            except Empty:
                # Create new connection if pool is empty
                with self.lock:
                    if self.active_connections < self.max_connections * 2:
                        conn = self._create_connection()
                        if conn:
                            self.active_connections += 1
                        else:
                            raise DatabaseException("Failed to create new database connection")
                    else:
                        raise DatabaseException("Maximum database connections exceeded")
            
            yield conn
            
        except Exception as e:
            if conn:
                try:
                    conn.rollback()
                except:
                    pass
            raise e
        finally:
            if conn:
                try:
                    # Return connection to pool if it's still valid
                    if conn.total_changes >= 0:  # Check if connection is still valid
                        self.connections.put(conn)
                    else:
                        # Connection is invalid, create new one
                        new_conn = self._create_connection()
                        if new_conn:
                            self.connections.put(new_conn)
                        else:
                            with self.lock:
                                self.active_connections -= 1
                except:
                    # If returning to pool fails, create new connection
                    try:
                        new_conn = self._create_connection()
                        if new_conn:
                            self.connections.put(new_conn)
                        else:
                            with self.lock:
                                self.active_connections -= 1
                    except:
                        pass
    
    def close_all(self):
        """Close all connections in the pool"""
        while not self.connections.empty():
            try:
                conn = self.connections.get_nowait()
                conn.close()
            except Empty:
                break
        self.logger.info("All database connections closed")

class DatabaseManager:
    """Enhanced database manager with connection pooling and async support"""
    
    def __init__(self):
        self.config = config
        self.logger = logging.getLogger('DatabaseManager')
        self.stats = DatabaseStats()
        self.pool = ConnectionPool(
            db_path=self.config.DB_PATH,
            max_connections=self.config.DB_MAX_CONNECTIONS,
            timeout=self.config.DB_TIMEOUT
        )
        
        # Initialize database
        self._initialize_database()
    
    def _initialize_database(self):
        """Initialize database tables and indexes"""
        try:
            with self.pool.get_connection() as conn:
                cursor = conn.cursor()
                
                # Create tables if they don't exist
                self._create_tables(cursor)
                
                # Create indexes for better performance
                self._create_indexes(cursor)
                
                # Verify database integrity
                self._verify_integrity(cursor)
                
                conn.commit()
                self.logger.info("Database initialized successfully")
                
        except Exception as e:
            self.logger.error(f"Database initialization failed: {e}")
            raise DatabaseException(f"Database initialization failed: {e}")
    
    def _create_tables(self, cursor: sqlite3.Cursor):
        """Create database tables"""
        # Users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE NOT NULL,
                username TEXT,
                full_name TEXT NOT NULL,
                phone TEXT,
                email TEXT,
                role TEXT DEFAULT 'user',
                balance REAL DEFAULT 0.0,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                login_attempts INTEGER DEFAULT 0,
                locked_until TIMESTAMP,
                referral_code TEXT,
                referred_by INTEGER,
                FOREIGN KEY (referred_by) REFERENCES users (id)
            )
        ''')
        
        # Transactions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                transaction_id TEXT UNIQUE NOT NULL,
                from_user INTEGER,
                to_user INTEGER,
                type TEXT NOT NULL,
                amount REAL NOT NULL,
                description TEXT,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT,
                FOREIGN KEY (from_user) REFERENCES users (id),
                FOREIGN KEY (to_user) REFERENCES users (id)
            )
        ''')
        
        # Cards table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                card_number TEXT NOT NULL,
                card_type TEXT NOT NULL,
                denomination REAL NOT NULL,
                is_sold BOOLEAN DEFAULT 0,
                supplier_id INTEGER,
                agent_id INTEGER,
                sold_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (supplier_id) REFERENCES users (id),
                FOREIGN KEY (agent_id) REFERENCES users (id)
            )
        ''')
        
        # Networks table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS networks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                supplier_id INTEGER,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (supplier_id) REFERENCES users (id)
            )
        ''')
        
        # Card categories table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS card_categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                network_id INTEGER,
                denomination REAL NOT NULL,
                price REAL NOT NULL,
                stock INTEGER DEFAULT 0,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (network_id) REFERENCES networks (id)
            )
        ''')
        
        # User sessions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                session_token TEXT UNIQUE NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # Audit log table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                action TEXT NOT NULL,
                details TEXT,
                ip_address TEXT,
                user_agent TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
    
    def _create_indexes(self, cursor: sqlite3.Cursor):
        """Create database indexes for better performance"""
        # Users table indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_telegram_id ON users(telegram_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_role ON users(role)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_created_at ON users(created_at)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_last_activity ON users(last_activity)')
        
        # Transactions table indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_transactions_from_user ON transactions(from_user)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_transactions_to_user ON transactions(to_user)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_transactions_type ON transactions(type)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_transactions_created_at ON transactions(created_at)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_transactions_status ON transactions(status)')
        
        # Cards table indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_cards_supplier_id ON cards(supplier_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_cards_agent_id ON cards(agent_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_cards_is_sold ON cards(is_sold)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_cards_created_at ON cards(created_at)')
        
        # Networks table indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_networks_supplier_id ON networks(supplier_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_networks_is_active ON networks(is_active)')
        
        # Card categories table indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_card_categories_network_id ON card_categories(network_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_card_categories_denomination ON card_categories(denomination)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_card_categories_price ON card_categories(price)')
        
        # User sessions table indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_sessions_user_id ON user_sessions(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_sessions_token ON user_sessions(session_token)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_sessions_expires_at ON user_sessions(expires_at)')
        
        # Audit log table indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_audit_log_user_id ON audit_log(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_audit_log_action ON audit_log(action)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_audit_log_created_at ON audit_log(created_at)')
    
    def _verify_integrity(self, cursor: sqlite3.Cursor):
        """Verify database integrity"""
        try:
            cursor.execute("PRAGMA integrity_check")
            result = cursor.fetchone()
            if result and result[0] != 'ok':
                raise DatabaseException(f"Database integrity check failed: {result[0]}")
            
            cursor.execute("PRAGMA foreign_key_check")
            result = cursor.fetchone()
            if result:
                raise DatabaseException("Foreign key constraint violation detected")
                
        except Exception as e:
            self.logger.error(f"Database integrity verification failed: {e}")
            raise DatabaseException(f"Database integrity verification failed: {e}")
    
    def execute_query(self, query: str, params: tuple = (), fetch: bool = True) -> Union[List[Dict], int]:
        """Execute a database query with proper error handling"""
        start_time = time.time()
        self.stats.total_queries += 1
        
        try:
            with self.pool.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                
                if fetch:
                    if query.strip().upper().startswith('SELECT'):
                        result = cursor.fetchall()
                        return [dict(row) for row in result]
                    else:
                        conn.commit()
                        return cursor.rowcount
                else:
                    conn.commit()
                    return cursor.rowcount
                    
        except sqlite3.IntegrityError as e:
            self.stats.failed_queries += 1
            self.stats.last_error = str(e)
            self.stats.last_error_time = time.time()
            self.logger.error(f"Database integrity error: {e}")
            raise DatabaseException(f"Database integrity error: {e}", operation="execute", details={"query": query, "params": params})
            
        except sqlite3.OperationalError as e:
            self.stats.failed_queries += 1
            self.stats.last_error = str(e)
            self.stats.last_error_time = time.time()
            self.logger.error(f"Database operational error: {e}")
            raise DatabaseException(f"Database operational error: {e}", operation="execute", details={"query": query, "params": params})
            
        except Exception as e:
            self.stats.failed_queries += 1
            self.stats.last_error = str(e)
            self.stats.last_error_time = time.time()
            self.logger.error(f"Database error: {e}")
            raise DatabaseException(f"Database error: {e}", operation="execute", details={"query": query, "params": params})
            
        finally:
            query_time = time.time() - start_time
            self.stats.total_query_time += query_time
            self.stats.avg_query_time = self.stats.total_query_time / self.stats.total_queries
            
            if query_time > 1.0:  # Log slow queries
                self.stats.slow_queries += 1
                self.logger.warning(f"Slow query detected: {query_time:.2f}s - {query[:100]}...")
            
            if self.stats.total_queries % 100 == 0:  # Log stats every 100 queries
                self.logger.info(f"Database stats: {self.stats.successful_queries}/{self.stats.total_queries} successful, "
                               f"avg time: {self.stats.avg_query_time:.3f}s")
    
    async def execute_query_async(self, query: str, params: tuple = (), fetch: bool = True) -> Union[List[Dict], int]:
        """Execute database query asynchronously"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.execute_query, query, params, fetch)
    
    def execute_many(self, query: str, params_list: List[tuple]) -> int:
        """Execute multiple queries in batch"""
        start_time = time.time()
        self.stats.total_queries += len(params_list)
        
        try:
            with self.pool.get_connection() as conn:
                cursor = conn.cursor()
                cursor.executemany(query, params_list)
                conn.commit()
                return cursor.rowcount
                
        except Exception as e:
            self.stats.failed_queries += len(params_list)
            self.stats.last_error = str(e)
            self.stats.last_error_time = time.time()
            self.logger.error(f"Batch execution error: {e}")
            raise DatabaseException(f"Batch execution error: {e}", operation="execute_many", details={"query": query, "params_count": len(params_list)})
            
        finally:
            query_time = time.time() - start_time
            self.stats.total_query_time += query_time
    
    def get_user_by_telegram_id(self, telegram_id: int) -> Optional[Dict]:
        """Get user by Telegram ID"""
        query = "SELECT * FROM users WHERE telegram_id = ?"
        result = self.execute_query(query, (telegram_id,))
        return result[0] if result else None
    
    def create_user(self, telegram_id: int, full_name: str, username: str = None) -> int:
        """Create a new user"""
        query = '''
            INSERT INTO users (telegram_id, full_name, username, created_at, updated_at, last_activity)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        '''
        self.execute_query(query, (telegram_id, full_name, username), fetch=False)
        return self.execute_query("SELECT last_insert_rowid()", fetch=True)[0]['last_insert_rowid()']
    
    def update_user_activity(self, user_id: int):
        """Update user's last activity"""
        query = "UPDATE users SET last_activity = CURRENT_TIMESTAMP WHERE id = ?"
        self.execute_query(query, (user_id,), fetch=False)
    
    def get_user_balance(self, user_id: int) -> float:
        """Get user's current balance"""
        query = "SELECT balance FROM users WHERE id = ?"
        result = self.execute_query(query, (user_id,))
        return result[0]['balance'] if result else 0.0
    
    def update_user_balance(self, user_id: int, amount: float, operation: str = 'add'):
        """Update user's balance"""
        if operation == 'add':
            query = "UPDATE users SET balance = balance + ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?"
        else:
            query = "UPDATE users SET balance = balance - ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?"
        
        self.execute_query(query, (abs(amount), user_id), fetch=False)
    
    def create_transaction(self, from_user: int, to_user: int, amount: float, 
                          transaction_type: str, description: str = None) -> str:
        """Create a new transaction"""
        import uuid
        transaction_id = str(uuid.uuid4())
        
        query = '''
            INSERT INTO transactions (transaction_id, from_user, to_user, type, amount, description, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        '''
        self.execute_query(query, (transaction_id, from_user, to_user, transaction_type, amount, description), fetch=False)
        return transaction_id
    
    def get_user_transactions(self, user_id: int, limit: int = 10) -> List[Dict]:
        """Get user's recent transactions"""
        query = '''
            SELECT t.*, u.full_name as related_user
            FROM transactions t
            LEFT JOIN users u ON (
                CASE
                    WHEN t.type = 'credit' THEN NULL
                    ELSE u.id = CASE WHEN t.from_user = ? THEN t.to_user ELSE t.from_user END
                END
            )
            WHERE t.from_user = ? OR t.to_user = ?
            ORDER BY t.created_at DESC
            LIMIT ?
        '''
        return self.execute_query(query, (user_id, user_id, user_id, limit))
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        try:
            with self.pool.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get table sizes
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = cursor.fetchall()
                
                table_stats = {}
                for table in tables:
                    table_name = table[0]
                    cursor.execute(f"SELECT COUNT(*) as count FROM {table_name}")
                    count = cursor.fetchone()[0]
                    table_stats[table_name] = count
                
                # Get database size
                cursor.execute("SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size()")
                db_size = cursor.fetchone()[0]
                
                return {
                    'table_stats': table_stats,
                    'database_size_bytes': db_size,
                    'database_size_mb': round(db_size / (1024 * 1024), 2),
                    'pool_stats': {
                        'max_connections': self.pool.max_connections,
                        'active_connections': self.pool.active_connections,
                        'pool_size': self.pool.connections.qsize()
                    },
                    'performance_stats': {
                        'total_queries': self.stats.total_queries,
                        'successful_queries': self.stats.successful_queries,
                        'failed_queries': self.stats.failed_queries,
                        'slow_queries': self.stats.slow_queries,
                        'avg_query_time': round(self.stats.avg_query_time, 3),
                        'total_query_time': round(self.stats.total_query_time, 3)
                    }
                }
                
        except Exception as e:
            self.logger.error(f"Failed to get database stats: {e}")
            return {}
    
    def backup_database(self, backup_path: str) -> bool:
        """Create database backup"""
        try:
            import shutil
            shutil.copy2(self.config.DB_PATH, backup_path)
            self.logger.info(f"Database backup created: {backup_path}")
            return True
        except Exception as e:
            self.logger.error(f"Database backup failed: {e}")
            return False
    
    def close(self):
        """Close database manager and all connections"""
        try:
            self.pool.close_all()
            self.logger.info("Database manager closed successfully")
        except Exception as e:
            self.logger.error(f"Error closing database manager: {e}")

# Global database manager instance
db_manager = DatabaseManager()