"""
Enhanced database manager with connection pooling for Yemen Net Bot v2
"""

import sqlite3
import asyncio
import logging
from typing import Optional, List, Dict, Any, Tuple
from contextlib import asynccontextmanager
from .exceptions import DatabaseError
from .cache_manager import cache_manager

logger = logging.getLogger(__name__)

class DatabaseConnection:
    """Database connection wrapper with error handling"""
    
    def __init__(self, connection: sqlite3.Connection):
        """
        Initialize database connection wrapper
        
        Args:
            connection: SQLite connection object
        """
        self.connection = connection
        self.connection.row_factory = sqlite3.Row
        self._transaction_depth = 0
    
    def cursor(self):
        """Get cursor from connection"""
        return self.connection.cursor()
    
    def commit(self):
        """Commit transaction"""
        self.connection.commit()
    
    def rollback(self):
        """Rollback transaction"""
        self.connection.rollback()
    
    def close(self):
        """Close connection"""
        self.connection.close()
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        if exc_type is not None:
            self.rollback()
        else:
            self.commit()
        self.close()
    
    async def __aenter__(self):
        """Async context manager entry"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if exc_type is not None:
            self.rollback()
        else:
            self.commit()
        self.close()

class DatabaseManager:
    """Advanced database manager with connection pooling and async support"""
    
    def __init__(self, db_path: str, max_connections: int = 10):
        """
        Initialize database manager
        
        Args:
            db_path: Path to SQLite database file
            max_connections: Maximum number of connections in pool
        """
        self.db_path = db_path
        self.max_connections = max_connections
        self._connection_pool: List[sqlite3.Connection] = []
        self._available_connections: asyncio.Queue = asyncio.Queue()
        self._lock = asyncio.Lock()
        self._initialized = False
        
        # Performance monitoring
        self._stats = {
            "queries_executed": 0,
            "transactions_committed": 0,
            "transactions_rollbacked": 0,
            "connection_errors": 0,
            "query_errors": 0
        }
    
    async def initialize(self):
        """Initialize connection pool"""
        if self._initialized:
            return
        
        async with self._lock:
            if self._initialized:
                return
            
            try:
                # Create initial connections
                for _ in range(self.max_connections):
                    conn = self._create_connection()
                    if conn:
                        self._connection_pool.append(conn)
                        await self._available_connections.put(conn)
                
                self._initialized = True
                logger.info(f"Database pool initialized with {len(self._connection_pool)} connections")
                
            except Exception as e:
                logger.error(f"Failed to initialize database pool: {e}")
                raise DatabaseError(f"Database initialization failed: {e}")
    
    async def cleanup(self):
        """Cleanup all connections"""
        if not self._initialized:
            return
        
        async with self._lock:
            # Close all connections in pool
            for conn in self._connection_pool:
                try:
                    conn.close()
                except Exception as e:
                    logger.error(f"Error closing connection: {e}")
            
            self._connection_pool.clear()
            self._initialized = False
            logger.info("Database pool cleaned up")
    
    def _create_connection(self) -> Optional[sqlite3.Connection]:
        """Create new database connection"""
        try:
            conn = sqlite3.connect(
                self.db_path,
                check_same_thread=False,
                timeout=30.0
            )
            
            # Configure connection
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute("PRAGMA journal_mode = WAL")
            conn.execute("PRAGMA synchronous = NORMAL")
            conn.execute("PRAGMA cache_size = 10000")
            conn.execute("PRAGMA temp_store = MEMORY")
            
            return conn
            
        except Exception as e:
            logger.error(f"Failed to create database connection: {e}")
            self._stats["connection_errors"] += 1
            return None
    
    async def get_connection(self) -> DatabaseConnection:
        """Get database connection from pool"""
        if not self._initialized:
            await self.initialize()
        
        try:
            # Try to get connection from pool
            conn = await asyncio.wait_for(
                self._available_connections.get(),
                timeout=5.0
            )
            
            # Check if connection is still valid
            try:
                conn.execute("SELECT 1")
                return DatabaseConnection(conn)
            except Exception:
                # Connection is invalid, create new one
                conn.close()
                new_conn = self._create_connection()
                if new_conn:
                    return DatabaseConnection(new_conn)
                else:
                    raise DatabaseError("Failed to create valid database connection")
                    
        except asyncio.TimeoutError:
            raise DatabaseError("Timeout waiting for database connection")
        except Exception as e:
            raise DatabaseError(f"Failed to get database connection: {e}")
    
    async def return_connection(self, db_conn: DatabaseConnection):
        """Return connection to pool"""
        try:
            # Check if connection is still valid
            db_conn.connection.execute("SELECT 1")
            
            # Reset connection state
            db_conn.connection.rollback()
            
            # Return to pool
            await self._available_connections.put(db_conn.connection)
            
        except Exception as e:
            logger.error(f"Error returning connection to pool: {e}")
            # Connection is invalid, close it and create new one
            try:
                db_conn.connection.close()
            except:
                pass
            
            new_conn = self._create_connection()
            if new_conn:
                await self._available_connections.put(new_conn)
    
    @asynccontextmanager
    async def get_db_context(self):
        """Get database context manager"""
        db_conn = await self.get_connection()
        try:
            yield db_conn
        finally:
            await self.return_connection(db_conn)
    
    async def execute_query(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """
        Execute SELECT query
        
        Args:
            query: SQL query string
            params: Query parameters
            
        Returns:
            List of result dictionaries
        """
        async with self.get_db_context() as db_conn:
            try:
                cursor = db_conn.cursor()
                cursor.execute(query, params)
                results = cursor.fetchall()
                
                # Convert to list of dictionaries
                return [dict(row) for row in results]
                
            except Exception as e:
                logger.error(f"Query execution error: {e}")
                self._stats["query_errors"] += 1
                raise DatabaseError(f"Query execution failed: {e}")
            finally:
                self._stats["queries_executed"] += 1
    
    async def execute_update(self, query: str, params: tuple = ()) -> int:
        """
        Execute UPDATE/INSERT/DELETE query
        
        Args:
            query: SQL query string
            params: Query parameters
            
        Returns:
            Number of affected rows
        """
        async with self.get_db_context() as db_conn:
            try:
                cursor = db_conn.cursor()
                cursor.execute(query, params)
                affected_rows = cursor.rowcount
                
                return affected_rows
                
            except Exception as e:
                logger.error(f"Update execution error: {e}")
                self._stats["query_errors"] += 1
                raise DatabaseError(f"Update execution failed: {e}")
            finally:
                self._stats["queries_executed"] += 1
    
    async def execute_transaction(self, queries: List[Tuple[str, tuple]]) -> bool:
        """
        Execute multiple queries in transaction
        
        Args:
            queries: List of (query, params) tuples
            
        Returns:
            True if successful, False otherwise
        """
        async with self.get_db_context() as db_conn:
            try:
                cursor = db_conn.cursor()
                
                for query, params in queries:
                    cursor.execute(query, params)
                
                db_conn.commit()
                self._stats["transactions_committed"] += 1
                return True
                
            except Exception as e:
                logger.error(f"Transaction execution error: {e}")
                db_conn.rollback()
                self._stats["transactions_rollbacked"] += 1
                self._stats["query_errors"] += 1
                raise DatabaseError(f"Transaction execution failed: {e}")
    
    async def execute_scalar(self, query: str, params: tuple = ()) -> Any:
        """
        Execute query and return single value
        
        Args:
            query: SQL query string
            params: Query parameters
            
        Returns:
            Single result value
        """
        results = await self.execute_query(query, params)
        if results and len(results) > 0:
            return list(results[0].values())[0]
        return None
    
    async def table_exists(self, table_name: str) -> bool:
        """Check if table exists"""
        query = """
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name=?
        """
        result = await self.execute_scalar(query, (table_name,))
        return result is not None
    
    async def get_table_info(self, table_name: str) -> List[Dict[str, Any]]:
        """Get table schema information"""
        query = "PRAGMA table_info(?)"
        return await self.execute_query(query, (table_name,))
    
    async def get_table_names(self) -> List[str]:
        """Get list of all table names"""
        query = "SELECT name FROM sqlite_master WHERE type='table'"
        results = await self.execute_query(query)
        return [row['name'] for row in results]
    
    async def check_integrity(self) -> Dict[str, Any]:
        """Check database integrity"""
        try:
            integrity_check = await self.execute_scalar("PRAGMA integrity_check")
            return {
                "integrity": integrity_check == "ok",
                "result": integrity_check
            }
        except Exception as e:
            return {
                "integrity": False,
                "error": str(e)
            }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        return {
            **self._stats,
            "pool_size": len(self._connection_pool),
            "available_connections": self._available_connections.qsize(),
            "initialized": self._initialized
        }

# Global database manager instance
db_manager = DatabaseManager("yemen_net.db")

# Convenience functions for backward compatibility
async def get_db_connection():
    """Get database connection (backward compatibility)"""
    return await db_manager.get_connection()

async def execute_query(query: str, params: tuple = ()) -> List[Dict[str, Any]]:
    """Execute query (backward compatibility)"""
    return await db_manager.execute_query(query, params)

async def execute_update(query: str, params: tuple = ()) -> int:
    """Execute update (backward compatibility)"""
    return await db_manager.execute_update(query, params)