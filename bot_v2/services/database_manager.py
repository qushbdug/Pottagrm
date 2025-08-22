"""
Enhanced database manager with connection pooling and async support
"""

import sqlite3
import asyncio
import logging
import threading
import time
from typing import Optional, Dict, List, Any, Union
from contextlib import contextmanager
from queue import Queue, Empty
from dataclasses import dataclass
from pathlib import Path

from ..core.exceptions import DatabaseException
from ..core.config import config

logger = logging.getLogger(__name__)

@dataclass
class ConnectionInfo:
    """Database connection information"""
    connection: sqlite3.Connection
    last_used: float
    in_use: bool = False

class DatabaseManager:
    """Enhanced database manager with connection pooling"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or config.database.path
        self.max_connections = config.database.max_connections
        self.connection_timeout = config.database.connection_timeout
        self.connections: Queue = Queue(maxsize=self.max_connections)
        self.active_connections: Dict[int, ConnectionInfo] = {}
        self.connection_lock = threading.Lock()
        self.stats = {
            'total_connections': 0,
            'active_connections': 0,
            'failed_connections': 0,
            'queries_executed': 0,
            'queries_failed': 0
        }
        
        # Initialize database
        self._init_database()
        self._prefill_connections()
    
    def _init_database(self):
        """Initialize database and create tables if they don't exist"""
        try:
            with self.get_connection() as conn:
                self._create_tables(conn)
                self._create_indexes(conn)
                self._insert_initial_data(conn)
                logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise DatabaseException(f"Database initialization failed: {e}")
    
    def _create_tables(self, conn: sqlite3.Connection):
        """Create database tables"""
        cursor = conn.cursor()
        
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
                is_verified BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                settings TEXT,
                permissions TEXT
            )
        ''')
        
        # Networks table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS networks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                supplier_id INTEGER,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (supplier_id) REFERENCES users (id)
            )
        ''')
        
        # Card categories table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS card_categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                network_id INTEGER NOT NULL,
                description TEXT,
                price REAL NOT NULL,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (network_id) REFERENCES networks (id)
            )
        ''')
        
        # Cards table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                card_number TEXT NOT NULL,
                card_pin TEXT NOT NULL,
                category_id INTEGER NOT NULL,
                is_sold BOOLEAN DEFAULT 0,
                sold_to INTEGER,
                sold_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (category_id) REFERENCES card_categories (id),
                FOREIGN KEY (sold_to) REFERENCES users (id)
            )
        ''')
        
        # Transactions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
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
        
        # Notifications table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                type TEXT DEFAULT 'info',
                is_read BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # Commissions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS commissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                amount REAL NOT NULL,
                type TEXT NOT NULL,
                description TEXT,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # System logs table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS system_logs (
                id INTEGER PRIMARY KEY AUTOINESTAMP,
                level TEXT NOT NULL,
                message TEXT NOT NULL,
                user_id INTEGER,
                action TEXT,
                details TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        conn.commit()
    
    def _create_indexes(self, conn: sqlite3.Connection):
        """Create database indexes for better performance"""
        cursor = conn.cursor()
        
        # Users indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_telegram_id ON users(telegram_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_role ON users(role)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_is_active ON users(is_active)')
        
        # Transactions indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_transactions_from_user ON transactions(from_user)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_transactions_to_user ON transactions(to_user)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_transactions_type ON transactions(type)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_transactions_created_at ON transactions(created_at)')
        
        # Cards indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_cards_category_id ON cards(category_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_cards_is_sold ON cards(is_sold)')
        
        # Notifications indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_notifications_user_id ON notifications(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_notifications_is_read ON notifications(is_read)')
        
        conn.commit()
    
    def _insert_initial_data(self, conn: sqlite3.Connection):
        """Insert initial data if tables are empty"""
        cursor = conn.cursor()
        
        # Check if admin user exists
        cursor.execute('SELECT COUNT(*) FROM users WHERE role = "super_admin"')
        if cursor.fetchone()[0] == 0:
            # Create default admin user
            cursor.execute('''
                INSERT INTO users (telegram_id, full_name, role, is_active, is_verified)
                VALUES (?, ?, ?, ?, ?)
            ''', (123456789, 'System Admin', 'super_admin', 1, 1))
            
            # Create default network
            cursor.execute('''
                INSERT INTO networks (name, description, is_active)
                VALUES (?, ?, ?)
            ''', ('Default Network', 'Default network for testing', 1))
            
            logger.info("Initial data inserted")
        
        conn.commit()
    
    def _prefill_connections(self):
        """Pre-fill connection pool"""
        for _ in range(min(5, self.max_connections)):
            try:
                conn = self._create_connection()
                self.connections.put(conn)
                self.stats['total_connections'] += 1
            except Exception as e:
                logger.error(f"Failed to create connection: {e}")
                self.stats['failed_connections'] += 1
    
    def _create_connection(self) -> sqlite3.Connection:
        """Create a new database connection"""
        try:
            conn = sqlite3.connect(
                self.db_path,
                timeout=config.database.timeout,
                check_same_thread=config.database.check_same_thread
            )
            conn.row_factory = sqlite3.Row
            
            # Enable foreign keys
            conn.execute('PRAGMA foreign_keys = ON')
            
            # Enable WAL mode for better concurrency
            conn.execute('PRAGMA journal_mode = WAL')
            
            # Set cache size
            conn.execute('PRAGMA cache_size = 10000')
            
            # Set temp store
            conn.execute('PRAGMA temp_store = MEMORY')
            
            return conn
        except Exception as e:
            logger.error(f"Failed to create database connection: {e}")
            raise DatabaseException(f"Connection creation failed: {e}")
    
    @contextmanager
    def get_connection(self):
        """Get a database connection from the pool"""
        conn = None
        try:
            conn = self._get_connection_from_pool()
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Database operation failed: {e}")
            self.stats['queries_failed'] += 1
            raise DatabaseException(f"Database operation failed: {e}")
        finally:
            if conn:
                self._return_connection_to_pool(conn)
    
    def _get_connection_from_pool(self) -> sqlite3.Connection:
        """Get connection from pool or create new one"""
        try:
            # Try to get from pool
            conn = self.connections.get(timeout=self.connection_timeout)
            return conn
        except Empty:
            # Pool is empty, create new connection
            if len(self.active_connections) < self.max_connections:
                conn = self._create_connection()
                self.stats['total_connections'] += 1
                return conn
            else:
                # Wait for a connection to become available
                conn = self.connections.get(timeout=self.connection_timeout)
                return conn
    
    def _return_connection_to_pool(self, conn: sqlite3.Connection):
        """Return connection to pool"""
        try:
            # Reset connection state
            conn.rollback()
            
            # Return to pool
            self.connections.put(conn)
        except Exception as e:
            logger.error(f"Failed to return connection to pool: {e}")
            # Close connection if it can't be returned
            try:
                conn.close()
            except:
                pass
    
    async def execute_query(self, query: str, params: tuple = ()) -> List[Dict]:
        """Execute a query asynchronously"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._execute_query_sync, query, params)
    
    def _execute_query_sync(self, query: str, params: tuple = ()) -> List[Dict]:
        """Execute a query synchronously"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            
            if query.strip().upper().startswith('SELECT'):
                results = cursor.fetchall()
                return [dict(row) for row in results]
            else:
                conn.commit()
                return [{'affected_rows': cursor.rowcount}]
    
    async def execute_many(self, query: str, params_list: List[tuple]) -> Dict:
        """Execute multiple queries asynchronously"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._execute_many_sync, query, params_list)
    
    def _execute_many_sync(self, query: str, params_list: List[tuple]) -> Dict:
        """Execute multiple queries synchronously"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.executemany(query, params_list)
            conn.commit()
            return {'affected_rows': cursor.rowcount}
    
    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        return {
            **self.stats,
            'pool_size': self.connections.qsize(),
            'active_connections_count': len(self.active_connections)
        }
    
    def health_check(self) -> Dict[str, Any]:
        """Perform database health check"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Check integrity
                cursor.execute('PRAGMA integrity_check')
                integrity = cursor.fetchone()
                
                # Check table count
                cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
                table_count = cursor.fetchone()[0]
                
                # Check database size
                db_size = Path(self.db_path).stat().st_size if Path(self.db_path).exists() else 0
                
                return {
                    'status': 'healthy' if integrity[0] == 'ok' else 'corrupted',
                    'integrity_check': integrity[0],
                    'table_count': table_count,
                    'database_size_bytes': db_size,
                    'database_size_mb': round(db_size / (1024 * 1024), 2)
                }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def backup_database(self, backup_path: str) -> bool:
        """Create database backup"""
        try:
            import shutil
            shutil.copy2(self.db_path, backup_path)
            logger.info(f"Database backed up to {backup_path}")
            return True
        except Exception as e:
            logger.error(f"Database backup failed: {e}")
            return False
    
    def optimize_database(self) -> bool:
        """Optimize database performance"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Analyze tables
                cursor.execute('ANALYZE')
                
                # Vacuum database
                cursor.execute('VACUUM')
                
                # Update statistics
                cursor.execute('ANALYZE')
                
                logger.info("Database optimization completed")
                return True
        except Exception as e:
            logger.error(f"Database optimization failed: {e}")
            return False
    
    def close_all_connections(self):
        """Close all database connections"""
        try:
            # Close connections in pool
            while not self.connections.empty():
                try:
                    conn = self.connections.get_nowait()
                    conn.close()
                except Empty:
                    break
            
            # Close active connections
            for conn_info in self.active_connections.values():
                try:
                    conn_info.connection.close()
                except:
                    pass
            
            self.active_connections.clear()
            logger.info("All database connections closed")
        except Exception as e:
            logger.error(f"Failed to close connections: {e}")

# Global database manager instance
db_manager = DatabaseManager()