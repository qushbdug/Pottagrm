"""
Advanced Database Manager for Yemen Net Bot
Provides connection pooling, async operations, and improved error handling
"""

import sqlite3
import asyncio
import aiosqlite
import logging
import time
from contextlib import asynccontextmanager, contextmanager
from typing import Optional, List, Dict, Any, Union, Tuple
from pathlib import Path
import threading
from queue import Queue, Empty
from dataclasses import dataclass
from datetime import datetime, timedelta

from core.exceptions import DatabaseError, ValidationError, map_sqlite_error
from core.logger import log_async_function_call, get_performance_logger


@dataclass
class ConnectionStats:
    """Statistics for database connections"""
    total_connections: int = 0
    active_connections: int = 0
    queries_executed: int = 0
    average_query_time: float = 0.0
    errors_count: int = 0
    last_error: Optional[str] = None


class ConnectionPool:
    """Thread-safe connection pool for SQLite"""
    
    def __init__(self, database_path: str, pool_size: int = 10, timeout: int = 30):
        self.database_path = database_path
        self.pool_size = pool_size
        self.timeout = timeout
        self.pool = Queue(maxsize=pool_size)
        self.stats = ConnectionStats()
        self.logger = logging.getLogger(__name__)
        self._lock = threading.Lock()
        self._initialize_pool()
    
    def _initialize_pool(self):
        """Initialize the connection pool"""
        for _ in range(self.pool_size):
            try:
                conn = self._create_connection()
                self.pool.put(conn)
                self.stats.total_connections += 1
            except Exception as e:
                self.logger.error(f"Failed to create database connection: {e}")
                raise DatabaseError(f"Failed to initialize connection pool: {e}")
    
    def _create_connection(self) -> sqlite3.Connection:
        """Create a new database connection with optimized settings"""
        conn = sqlite3.connect(
            self.database_path,
            timeout=self.timeout,
            check_same_thread=False,
            isolation_level=None  # Autocommit mode
        )
        
        # Set row factory for dict-like access
        conn.row_factory = sqlite3.Row
        
        # Enable WAL mode for better concurrency
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA cache_size=10000")
        conn.execute("PRAGMA temp_store=MEMORY")
        conn.execute("PRAGMA mmap_size=268435456")  # 256MB
        conn.execute("PRAGMA foreign_keys=ON")
        
        return conn
    
    @contextmanager
    def get_connection(self):
        """Get a connection from the pool (context manager)"""
        conn = None
        try:
            conn = self.pool.get(timeout=self.timeout)
            with self._lock:
                self.stats.active_connections += 1
            yield conn
        except Empty:
            raise DatabaseError("Connection pool timeout")
        except Exception as e:
            with self._lock:
                self.stats.errors_count += 1
                self.stats.last_error = str(e)
            raise map_sqlite_error(str(e), e)
        finally:
            if conn:
                with self._lock:
                    self.stats.active_connections -= 1
                self.pool.put(conn)
    
    def close_all(self):
        """Close all connections in the pool"""
        while not self.pool.empty():
            try:
                conn = self.pool.get_nowait()
                conn.close()
            except Empty:
                break
        self.stats.active_connections = 0


class DatabaseManager:
    """Advanced database manager with async support and connection pooling"""
    
    def __init__(self, database_path: str, pool_size: int = 10):
        self.database_path = Path(database_path)
        self.pool_size = pool_size
        self.logger = logging.getLogger(__name__)
        self.perf_logger = get_performance_logger()
        self.pool: Optional[ConnectionPool] = None
        self._async_connections = {}
        self._lock = asyncio.Lock()
        
    async def initialize(self):
        """Initialize the database manager"""
        try:
            # Create database directory if it doesn't exist
            self.database_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Initialize connection pool
            self.pool = ConnectionPool(str(self.database_path), self.pool_size)
            
            # Create tables if they don't exist
            await self._create_tables()
            
            # Perform integrity check
            await self._check_database_integrity()
            
            self.logger.info("✅ Database manager initialized successfully")
            
        except Exception as e:
            self.logger.error(f"❌ Database initialization failed: {e}")
            raise DatabaseError(f"Database initialization failed: {e}")
    
    async def _create_tables(self):
        """Create database tables if they don't exist"""
        tables_sql = [
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER UNIQUE NOT NULL,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                full_name TEXT,
                phone TEXT,
                email TEXT,
                role TEXT DEFAULT 'user',
                balance REAL DEFAULT 0.0,
                is_active BOOLEAN DEFAULT 1,
                is_verified BOOLEAN DEFAULT 0,
                registration_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                last_activity DATETIME DEFAULT CURRENT_TIMESTAMP,
                settings TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS networks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                supplier_id INTEGER,
                is_active BOOLEAN DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (supplier_id) REFERENCES users(id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS card_categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                network_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                price REAL NOT NULL,
                description TEXT,
                is_active BOOLEAN DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (network_id) REFERENCES networks(id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS cards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category_id INTEGER NOT NULL,
                serial_number TEXT UNIQUE,
                pin_code TEXT,
                value REAL,
                is_sold BOOLEAN DEFAULT 0,
                sold_to INTEGER,
                sold_at DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (category_id) REFERENCES card_categories(id),
                FOREIGN KEY (sold_to) REFERENCES users(id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_user INTEGER,
                to_user INTEGER,
                type TEXT NOT NULL,
                amount REAL NOT NULL,
                description TEXT,
                reference_id TEXT,
                status TEXT DEFAULT 'completed',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (from_user) REFERENCES users(id),
                FOREIGN KEY (to_user) REFERENCES users(id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                type TEXT DEFAULT 'info',
                is_read BOOLEAN DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS bot_settings (
                key TEXT PRIMARY KEY,
                value TEXT,
                description TEXT,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                action TEXT NOT NULL,
                entity_type TEXT,
                entity_id INTEGER,
                old_values TEXT,
                new_values TEXT,
                ip_address TEXT,
                user_agent TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
            """
        ]
        
        # Create indexes
        indexes_sql = [
            "CREATE INDEX IF NOT EXISTS idx_users_user_id ON users(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_users_role ON users(role)",
            "CREATE INDEX IF NOT EXISTS idx_cards_category_id ON cards(category_id)",
            "CREATE INDEX IF NOT EXISTS idx_cards_is_sold ON cards(is_sold)",
            "CREATE INDEX IF NOT EXISTS idx_transactions_from_user ON transactions(from_user)",
            "CREATE INDEX IF NOT EXISTS idx_transactions_to_user ON transactions(to_user)",
            "CREATE INDEX IF NOT EXISTS idx_transactions_type ON transactions(type)",
            "CREATE INDEX IF NOT EXISTS idx_notifications_user_id ON notifications(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_notifications_is_read ON notifications(is_read)",
            "CREATE INDEX IF NOT EXISTS idx_audit_log_user_id ON audit_log(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_audit_log_action ON audit_log(action)"
        ]
        
        async with self._get_async_connection() as conn:
            # Create tables
            for sql in tables_sql:
                await conn.execute(sql)
            
            # Create indexes
            for sql in indexes_sql:
                await conn.execute(sql)
            
            await conn.commit()
    
    async def _check_database_integrity(self):
        """Check database integrity"""
        async with self._get_async_connection() as conn:
            cursor = await conn.execute("PRAGMA integrity_check")
            result = await cursor.fetchone()
            
            if result[0] != "ok":
                raise DatabaseError(f"Database integrity check failed: {result[0]}")
            
            self.logger.info("✅ Database integrity check passed")
    
    @asynccontextmanager
    async def _get_async_connection(self):
        """Get an async database connection"""
        thread_id = threading.get_ident()
        
        if thread_id not in self._async_connections:
            self._async_connections[thread_id] = await aiosqlite.connect(
                str(self.database_path),
                timeout=30
            )
            
            # Configure connection
            conn = self._async_connections[thread_id]
            await conn.execute("PRAGMA journal_mode=WAL")
            await conn.execute("PRAGMA foreign_keys=ON")
            conn.row_factory = aiosqlite.Row
        
        conn = self._async_connections[thread_id]
        try:
            yield conn
        except Exception as e:
            await conn.rollback()
            raise map_sqlite_error(str(e), e)
    
    @log_async_function_call(logging.getLogger(__name__))
    async def execute_query(self, query: str, params: tuple = None, fetch_one: bool = False, fetch_all: bool = False) -> Any:
        """Execute a database query asynchronously"""
        start_time = time.time()
        params = params or ()
        
        try:
            async with self._get_async_connection() as conn:
                cursor = await conn.execute(query, params)
                
                if fetch_one:
                    result = await cursor.fetchone()
                    result = dict(result) if result else None
                elif fetch_all:
                    rows = await cursor.fetchall()
                    result = [dict(row) for row in rows]
                else:
                    result = cursor.lastrowid
                
                await conn.commit()
                
                # Log performance
                duration = time.time() - start_time
                self.perf_logger.info(
                    f"Query executed in {duration:.3f}s",
                    extra={
                        'query': query[:100] + "..." if len(query) > 100 else query,
                        'duration': duration,
                        'params_count': len(params)
                    }
                )
                
                return result
                
        except Exception as e:
            duration = time.time() - start_time
            self.logger.error(f"Query failed after {duration:.3f}s: {e}")
            raise map_sqlite_error(str(e), e)
    
    @log_async_function_call(logging.getLogger(__name__))
    async def execute_many(self, query: str, params_list: List[tuple]) -> int:
        """Execute many queries asynchronously"""
        start_time = time.time()
        
        try:
            async with self._get_async_connection() as conn:
                await conn.executemany(query, params_list)
                await conn.commit()
                
                duration = time.time() - start_time
                self.perf_logger.info(
                    f"Batch query executed in {duration:.3f}s",
                    extra={
                        'query': query[:100] + "..." if len(query) > 100 else query,
                        'duration': duration,
                        'batch_size': len(params_list)
                    }
                )
                
                return len(params_list)
                
        except Exception as e:
            duration = time.time() - start_time
            self.logger.error(f"Batch query failed after {duration:.3f}s: {e}")
            raise map_sqlite_error(str(e), e)
    
    @log_async_function_call(logging.getLogger(__name__))
    async def execute_transaction(self, queries: List[Tuple[str, tuple]]) -> bool:
        """Execute multiple queries in a transaction"""
        start_time = time.time()
        
        try:
            async with self._get_async_connection() as conn:
                await conn.execute("BEGIN")
                
                try:
                    for query, params in queries:
                        await conn.execute(query, params or ())
                    
                    await conn.commit()
                    
                    duration = time.time() - start_time
                    self.perf_logger.info(
                        f"Transaction completed in {duration:.3f}s",
                        extra={
                            'duration': duration,
                            'queries_count': len(queries)
                        }
                    )
                    
                    return True
                    
                except Exception:
                    await conn.rollback()
                    raise
                    
        except Exception as e:
            duration = time.time() - start_time
            self.logger.error(f"Transaction failed after {duration:.3f}s: {e}")
            raise map_sqlite_error(str(e), e)
    
    def execute_sync_query(self, query: str, params: tuple = None, fetch_one: bool = False, fetch_all: bool = False) -> Any:
        """Execute a synchronous query using connection pool"""
        if not self.pool:
            raise DatabaseError("Database not initialized")
        
        start_time = time.time()
        params = params or ()
        
        try:
            with self.pool.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                
                if fetch_one:
                    result = cursor.fetchone()
                    result = dict(result) if result else None
                elif fetch_all:
                    rows = cursor.fetchall()
                    result = [dict(row) for row in rows]
                else:
                    result = cursor.lastrowid
                
                conn.commit()
                
                # Update pool statistics
                duration = time.time() - start_time
                with self.pool._lock:
                    self.pool.stats.queries_executed += 1
                    self.pool.stats.average_query_time = (
                        (self.pool.stats.average_query_time * (self.pool.stats.queries_executed - 1) + duration) /
                        self.pool.stats.queries_executed
                    )
                
                return result
                
        except Exception as e:
            duration = time.time() - start_time
            self.logger.error(f"Sync query failed after {duration:.3f}s: {e}")
            raise map_sqlite_error(str(e), e)
    
    async def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        try:
            # Pool statistics
            pool_stats = {
                'total_connections': self.pool.stats.total_connections if self.pool else 0,
                'active_connections': self.pool.stats.active_connections if self.pool else 0,
                'queries_executed': self.pool.stats.queries_executed if self.pool else 0,
                'average_query_time': self.pool.stats.average_query_time if self.pool else 0,
                'errors_count': self.pool.stats.errors_count if self.pool else 0
            }
            
            # Database size
            db_size = self.database_path.stat().st_size if self.database_path.exists() else 0
            
            # Table counts
            table_counts = {}
            tables = ['users', 'networks', 'card_categories', 'cards', 'transactions', 'notifications']
            
            for table in tables:
                count = await self.execute_query(f"SELECT COUNT(*) as count FROM {table}", fetch_one=True)
                table_counts[table] = count['count'] if count else 0
            
            return {
                'database_size_bytes': db_size,
                'database_size_mb': round(db_size / (1024 * 1024), 2),
                'pool_stats': pool_stats,
                'table_counts': table_counts,
                'database_path': str(self.database_path)
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get database stats: {e}")
            raise DatabaseError(f"Failed to get database stats: {e}")
    
    async def backup_database(self, backup_path: str = None) -> str:
        """Create a database backup"""
        if not backup_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"backup_yemen_net_{timestamp}.db"
        
        try:
            async with self._get_async_connection() as conn:
                # Use SQLite's backup API
                await conn.execute(f"VACUUM INTO '{backup_path}'")
            
            self.logger.info(f"✅ Database backup created: {backup_path}")
            return backup_path
            
        except Exception as e:
            self.logger.error(f"❌ Database backup failed: {e}")
            raise DatabaseError(f"Database backup failed: {e}")
    
    async def optimize_database(self):
        """Optimize database performance"""
        try:
            async with self._get_async_connection() as conn:
                # Analyze tables for query optimization
                await conn.execute("ANALYZE")
                
                # Rebuild indexes
                await conn.execute("REINDEX")
                
                # Clean up unused space
                await conn.execute("VACUUM")
            
            self.logger.info("✅ Database optimization completed")
            
        except Exception as e:
            self.logger.error(f"❌ Database optimization failed: {e}")
            raise DatabaseError(f"Database optimization failed: {e}")
    
    async def close(self):
        """Close all database connections"""
        try:
            # Close async connections
            for conn in self._async_connections.values():
                await conn.close()
            self._async_connections.clear()
            
            # Close connection pool
            if self.pool:
                self.pool.close_all()
            
            self.logger.info("✅ Database manager closed")
            
        except Exception as e:
            self.logger.error(f"❌ Error closing database manager: {e}")
            raise DatabaseError(f"Error closing database manager: {e}")