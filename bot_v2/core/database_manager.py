"""
Enhanced database manager with connection pooling and async support
"""

import sqlite3
import asyncio
import logging
from typing import Optional, List, Dict, Any, Union
from contextlib import asynccontextmanager
from dataclasses import dataclass
from queue import Queue, Empty
import threading
import time

from .exceptions import DatabaseError

logger = logging.getLogger(__name__)

@dataclass
class DatabaseConfig:
    """Database configuration"""
    database_path: str
    max_connections: int = 10
    connection_timeout: int = 30
    check_same_thread: bool = False
    enable_foreign_keys: bool = True
    enable_wal_mode: bool = True
    journal_mode: str = "WAL"
    synchronous: str = "NORMAL"
    cache_size: int = -64000  # 64MB
    temp_store: str = "MEMORY"
    mmap_size: int = 268435456  # 256MB

class DatabaseConnection:
    """Individual database connection wrapper"""
    
    def __init__(self, config: DatabaseConfig):
        self.config = config
        self.connection: Optional[sqlite3.Connection] = None
        self.last_used: float = time.time()
        self.in_use: bool = False
        self._lock = threading.Lock()
    
    def connect(self) -> sqlite3.Connection:
        """Create new database connection"""
        try:
            conn = sqlite3.connect(
                self.config.database_path,
                timeout=self.config.connection_timeout,
                check_same_thread=self.config.check_same_thread
            )
            
            # Configure connection
            conn.execute(f"PRAGMA journal_mode = {self.config.journal_mode}")
            conn.execute(f"PRAGMA synchronous = {self.config.synchronous}")
            conn.execute(f"PRAGMA cache_size = {self.config.cache_size}")
            conn.execute(f"PRAGMA temp_store = {self.config.temp_store}")
            conn.execute(f"PRAGMA mmap_size = {self.config.mmap_size}")
            
            if self.config.enable_foreign_keys:
                conn.execute("PRAGMA foreign_keys = ON")
            
            if self.config.enable_wal_mode:
                conn.execute("PRAGMA wal_autocheckpoint = 1000")
            
            # Set row factory for dictionary-like access
            conn.row_factory = sqlite3.Row
            
            self.connection = conn
            return conn
            
        except Exception as e:
            logger.error(f"Failed to create database connection: {e}")
            raise DatabaseError(f"Connection failed: {e}")
    
    def get_connection(self) -> sqlite3.Connection:
        """Get connection, creating if necessary"""
        if self.connection is None:
            self.connect()
        return self.connection
    
    def close(self):
        """Close the connection"""
        if self.connection:
            try:
                self.connection.close()
                self.connection = None
            except Exception as e:
                logger.error(f"Error closing connection: {e}")
    
    def is_expired(self, max_idle_time: int = 300) -> bool:
        """Check if connection is expired"""
        return time.time() - self.last_used > max_idle_time
    
    def mark_used(self):
        """Mark connection as used"""
        self.last_used = time.time()

class DatabaseManager:
    """
    Database manager with connection pooling and async support
    """
    
    def __init__(self, config: DatabaseConfig):
        self.config = config
        self.connection_pool: Queue = Queue(maxsize=config.max_connections)
        self.active_connections: List[DatabaseConnection] = []
        self._lock = threading.Lock()
        self._initialized = False
        
        # Initialize connection pool
        self._init_pool()
    
    def _init_pool(self):
        """Initialize connection pool"""
        try:
            for _ in range(self.config.max_connections):
                conn_wrapper = DatabaseConnection(self.config)
                self.connection_pool.put(conn_wrapper)
                self.active_connections.append(conn_wrapper)
            
            self._initialized = True
            logger.info(f"Database pool initialized with {self.config.max_connections} connections")
            
        except Exception as e:
            logger.error(f"Failed to initialize database pool: {e}")
            raise DatabaseError(f"Pool initialization failed: {e}")
    
    def get_connection(self) -> DatabaseConnection:
        """Get connection from pool"""
        if not self._initialized:
            raise DatabaseError("Database pool not initialized")
        
        try:
            # Try to get connection from pool
            conn_wrapper = self.connection_pool.get(timeout=5)
            conn_wrapper.in_use = True
            conn_wrapper.mark_used()
            
            # Check if connection is expired
            if conn_wrapper.is_expired():
                conn_wrapper.close()
                conn_wrapper.connect()
            
            return conn_wrapper
            
        except Empty:
            raise DatabaseError("No available database connections")
    
    def return_connection(self, conn_wrapper: DatabaseConnection):
        """Return connection to pool"""
        try:
            conn_wrapper.in_use = False
            conn_wrapper.mark_used()
            self.connection_pool.put(conn_wrapper, timeout=1)
        except Exception as e:
            logger.error(f"Error returning connection to pool: {e}")
    
    @asynccontextmanager
    async def get_db_context(self):
        """Async context manager for database operations"""
        conn_wrapper = None
        try:
            conn_wrapper = self.get_connection()
            yield conn_wrapper.get_connection()
        finally:
            if conn_wrapper:
                self.return_connection(conn_wrapper)
    
    async def execute_query(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """Execute SELECT query asynchronously"""
        def _execute():
            with self.get_db_context() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                results = cursor.fetchall()
                return [dict(row) for row in results]
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _execute)
    
    async def execute_update(self, query: str, params: tuple = ()) -> int:
        """Execute INSERT/UPDATE/DELETE query asynchronously"""
        def _execute():
            with self.get_db_context() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                conn.commit()
                return cursor.rowcount
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _execute)
    
    async def execute_many(self, query: str, params_list: List[tuple]) -> int:
        """Execute multiple queries asynchronously"""
        def _execute():
            with self.get_db_context() as conn:
                cursor = conn.cursor()
                cursor.executemany(query, params_list)
                conn.commit()
                return cursor.rowcount
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _execute)
    
    async def execute_script(self, script: str) -> bool:
        """Execute SQL script asynchronously"""
        def _execute():
            with self.get_db_context() as conn:
                conn.executescript(script)
                conn.commit()
                return True
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _execute)
    
    async def table_exists(self, table_name: str) -> bool:
        """Check if table exists"""
        query = """
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name=?
        """
        result = await self.execute_query(query, (table_name,))
        return len(result) > 0
    
    async def get_table_info(self, table_name: str) -> List[Dict[str, Any]]:
        """Get table schema information"""
        query = "PRAGMA table_info(?)"
        return await self.execute_query(query, (table_name,))
    
    async def get_table_names(self) -> List[str]:
        """Get all table names"""
        query = "SELECT name FROM sqlite_master WHERE type='table'"
        result = await self.execute_query(query)
        return [row['name'] for row in result]
    
    async def check_integrity(self) -> Dict[str, Any]:
        """Check database integrity"""
        try:
            integrity_result = await self.execute_query("PRAGMA integrity_check")
            foreign_key_result = await self.execute_query("PRAGMA foreign_key_check")
            
            return {
                'integrity': integrity_result[0]['integrity_check'] if integrity_result else 'unknown',
                'foreign_keys': len(foreign_key_result) == 0,
                'foreign_key_errors': foreign_key_result
            }
        except Exception as e:
            logger.error(f"Integrity check failed: {e}")
            return {
                'integrity': 'error',
                'foreign_keys': False,
                'error': str(e)
            }
    
    async def optimize(self):
        """Optimize database"""
        try:
            await self.execute_query("PRAGMA optimize")
            await self.execute_query("VACUUM")
            logger.info("Database optimization completed")
        except Exception as e:
            logger.error(f"Database optimization failed: {e}")
    
    def close_all(self):
        """Close all connections"""
        for conn_wrapper in self.active_connections:
            conn_wrapper.close()
        
        self.active_connections.clear()
        self._initialized = False
        logger.info("All database connections closed")

# Global database manager instance
db_manager: Optional[DatabaseManager] = None

def init_database_manager(config: DatabaseConfig) -> DatabaseManager:
    """Initialize global database manager"""
    global db_manager
    if db_manager is None:
        db_manager = DatabaseManager(config)
    return db_manager

def get_database_manager() -> DatabaseManager:
    """Get global database manager"""
    if db_manager is None:
        raise DatabaseError("Database manager not initialized")
    return db_manager