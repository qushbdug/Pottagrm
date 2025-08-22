"""
Advanced Database Service with Connection Pooling and Async Operations
"""
import sqlite3
import asyncio
import threading
import time
from contextlib import contextmanager
from queue import Queue, Empty
from typing import Optional, Dict, List, Any, Union, Tuple
from functools import wraps
from concurrent.futures import ThreadPoolExecutor

from ..core.exceptions import (
    DatabaseException, 
    ConnectionPoolException, 
    TransactionException,
    EmergencyShutdownException
)
from ..core.logger import logger


class ConnectionPool:
    """Thread-safe SQLite connection pool"""
    
    def __init__(self, database_path: str, max_connections: int = 20, 
                 timeout: float = 30.0):
        self.database_path = database_path
        self.max_connections = max_connections
        self.timeout = timeout
        self._pool = Queue(maxsize=max_connections)
        self._created_connections = 0
        self._lock = threading.Lock()
        
        # Pre-populate pool with initial connections
        for _ in range(min(5, max_connections)):
            self._create_connection()
            
    def _create_connection(self) -> sqlite3.Connection:
        """Create a new database connection with optimized settings"""
        try:
            conn = sqlite3.connect(
                self.database_path,
                check_same_thread=False,
                timeout=self.timeout
            )
            
            # Optimize connection settings
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("PRAGMA cache_size=-64000")  # 64MB cache
            conn.execute("PRAGMA temp_store=memory")
            conn.execute("PRAGMA foreign_keys=ON")
            
            conn.row_factory = sqlite3.Row
            
            with self._lock:
                self._created_connections += 1
                
            logger.debug(f"Created new database connection. Total: {self._created_connections}")
            return conn
            
        except sqlite3.Error as e:
            logger.error("Failed to create database connection", e)
            raise ConnectionPoolException(f"Failed to create connection: {e}")
            
    @contextmanager
    def get_connection(self):
        """Get a connection from the pool"""
        conn = None
        try:
            # Try to get existing connection
            try:
                conn = self._pool.get(timeout=5.0)
            except Empty:
                # Create new connection if pool is empty and we haven't hit limit
                with self._lock:
                    if self._created_connections < self.max_connections:
                        conn = self._create_connection()
                    else:
                        # Wait longer for a connection to become available
                        conn = self._pool.get(timeout=self.timeout)
                        
            yield conn
            
        except Exception as e:
            logger.error("Error in connection context", e)
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                try:
                    # Return connection to pool
                    self._pool.put_nowait(conn)
                except:
                    # Pool is full, close the connection
                    conn.close()
                    with self._lock:
                        self._created_connections -= 1
                        
    def close_all(self):
        """Close all connections in the pool"""
        logger.info("Closing all database connections")
        closed_count = 0
        
        while not self._pool.empty():
            try:
                conn = self._pool.get_nowait()
                conn.close()
                closed_count += 1
            except Empty:
                break
                
        logger.info(f"Closed {closed_count} database connections")


class DatabaseService:
    """Advanced database service with async operations and caching"""
    
    def __init__(self, database_path: str = "yemen_net.db"):
        self.database_path = database_path
        self.pool = ConnectionPool(database_path)
        self.executor = ThreadPoolExecutor(max_workers=10)
        self._query_cache = {}
        self._cache_ttl = 300  # 5 minutes
        self._cache_timestamps = {}
        
        # Initialize database schema
        self._initialize_database()
        
    def _initialize_database(self):
        """Initialize database with required tables and optimizations"""
        try:
            with self.pool.get_connection() as conn:
                cursor = conn.cursor()
                
                # Check database integrity
                cursor.execute("PRAGMA integrity_check")
                result = cursor.fetchone()
                if result[0] != "ok":
                    logger.critical("Database integrity check failed")
                    raise EmergencyShutdownException("Database corruption detected")
                
                # Create indexes for performance
                indexes = [
                    "CREATE INDEX IF NOT EXISTS idx_users_telegram_id ON users(telegram_id)",
                    "CREATE INDEX IF NOT EXISTS idx_transactions_user ON transactions(from_user, to_user)",
                    "CREATE INDEX IF NOT EXISTS idx_transactions_date ON transactions(created_at)",
                    "CREATE INDEX IF NOT EXISTS idx_cards_category ON cards(category_id)",
                    "CREATE INDEX IF NOT EXISTS idx_cards_sold ON cards(is_sold)",
                ]
                
                for index_sql in indexes:
                    cursor.execute(index_sql)
                    
                conn.commit()
                logger.info("Database initialized successfully")
                
        except sqlite3.Error as e:
            logger.critical("Failed to initialize database", e)
            raise DatabaseException(f"Database initialization failed: {e}")
            
    def _is_cache_valid(self, key: str) -> bool:
        """Check if cached result is still valid"""
        if key not in self._cache_timestamps:
            return False
        return time.time() - self._cache_timestamps[key] < self._cache_ttl
        
    def _cache_result(self, key: str, result: Any):
        """Cache query result"""
        self._query_cache[key] = result
        self._cache_timestamps[key] = time.time()
        
    def _get_cached_result(self, key: str) -> Optional[Any]:
        """Get cached result if valid"""
        if self._is_cache_valid(key):
            return self._query_cache.get(key)
        return None
        
    async def execute_async(self, query: str, params: Tuple = (), 
                          fetch_type: str = "none") -> Optional[Any]:
        """Execute query asynchronously"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor, 
            self._execute_sync, 
            query, 
            params, 
            fetch_type
        )
        
    def _execute_sync(self, query: str, params: Tuple = (), 
                     fetch_type: str = "none") -> Optional[Any]:
        """Execute query synchronously"""
        try:
            with self.pool.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                
                if fetch_type == "one":
                    result = cursor.fetchone()
                elif fetch_type == "all":
                    result = cursor.fetchall()
                elif fetch_type == "many":
                    result = cursor.fetchmany()
                else:
                    result = None
                    
                conn.commit()
                return result
                
        except sqlite3.IntegrityError as e:
            logger.error(f"Database integrity error: {query}", e)
            raise TransactionException(f"Integrity constraint violation: {e}")
        except sqlite3.OperationalError as e:
            logger.error(f"Database operational error: {query}", e)
            raise DatabaseException(f"Database operation failed: {e}")
        except sqlite3.Error as e:
            logger.error(f"Database error: {query}", e)
            raise DatabaseException(f"Database error: {e}")
            
    async def get_user(self, telegram_id: int) -> Optional[Dict]:
        """Get user by telegram ID with caching"""
        cache_key = f"user_{telegram_id}"
        cached_result = self._get_cached_result(cache_key)
        if cached_result:
            return cached_result
            
        query = "SELECT * FROM users WHERE telegram_id = ?"
        result = await self.execute_async(query, (telegram_id,), "one")
        
        if result:
            user_dict = dict(result)
            self._cache_result(cache_key, user_dict)
            return user_dict
        return None
        
    async def create_user(self, telegram_id: int, full_name: str, 
                         phone: Optional[str] = None) -> bool:
        """Create new user"""
        try:
            query = """
                INSERT INTO users (telegram_id, full_name, phone, balance, role, is_active)
                VALUES (?, ?, ?, 0.0, 'user', 1)
            """
            await self.execute_async(query, (telegram_id, full_name, phone))
            
            # Invalidate cache
            cache_key = f"user_{telegram_id}"
            if cache_key in self._query_cache:
                del self._query_cache[cache_key]
                del self._cache_timestamps[cache_key]
                
            logger.log_user_action(telegram_id, "user_created", f"Name: {full_name}")
            return True
            
        except Exception as e:
            logger.error("Failed to create user", e)
            raise DatabaseException(f"User creation failed: {e}")
            
    async def update_user_balance(self, user_id: int, amount: float, 
                                 operation: str = "add") -> bool:
        """Update user balance atomically"""
        try:
            if operation == "add":
                query = "UPDATE users SET balance = balance + ? WHERE id = ?"
            elif operation == "subtract":
                query = "UPDATE users SET balance = balance - ? WHERE id = ?"
            else:
                query = "UPDATE users SET balance = ? WHERE id = ?"
                
            await self.execute_async(query, (amount, user_id))
            
            # Invalidate user cache
            user = await self.get_user_by_id(user_id)
            if user:
                cache_key = f"user_{user['telegram_id']}"
                if cache_key in self._query_cache:
                    del self._query_cache[cache_key]
                    del self._cache_timestamps[cache_key]
                    
            return True
            
        except Exception as e:
            logger.error("Failed to update user balance", e)
            raise TransactionException(f"Balance update failed: {e}")
            
    async def get_user_by_id(self, user_id: int) -> Optional[Dict]:
        """Get user by ID"""
        query = "SELECT * FROM users WHERE id = ?"
        result = await self.execute_async(query, (user_id,), "one")
        return dict(result) if result else None
        
    async def create_transaction(self, from_user: int, to_user: Optional[int], 
                               amount: float, transaction_type: str, 
                               description: str) -> str:
        """Create transaction with proper validation"""
        try:
            import uuid
            transaction_id = str(uuid.uuid4())
            
            query = """
                INSERT INTO transactions 
                (id, from_user, to_user, amount, type, description, created_at)
                VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
            """
            
            await self.execute_async(
                query, 
                (transaction_id, from_user, to_user, amount, transaction_type, description)
            )
            
            logger.log_transaction(transaction_id, from_user, amount, transaction_type)
            return transaction_id
            
        except Exception as e:
            logger.error("Failed to create transaction", e)
            raise TransactionException(f"Transaction creation failed: {e}")
            
    async def get_user_transactions(self, user_id: int, limit: int = 10) -> List[Dict]:
        """Get user transactions with caching"""
        cache_key = f"transactions_{user_id}_{limit}"
        cached_result = self._get_cached_result(cache_key)
        if cached_result:
            return cached_result
            
        query = """
            SELECT * FROM transactions 
            WHERE from_user = ? OR to_user = ?
            ORDER BY created_at DESC 
            LIMIT ?
        """
        
        result = await self.execute_async(query, (user_id, user_id, limit), "all")
        transactions = [dict(row) for row in result] if result else []
        
        self._cache_result(cache_key, transactions)
        return transactions
        
    async def get_network_stats(self) -> Dict:
        """Get network statistics"""
        cache_key = "network_stats"
        cached_result = self._get_cached_result(cache_key)
        if cached_result:
            return cached_result
            
        queries = {
            "total_users": "SELECT COUNT(*) as count FROM users WHERE is_active = 1",
            "total_transactions": "SELECT COUNT(*) as count FROM transactions",
            "total_revenue": "SELECT SUM(amount) as total FROM transactions WHERE type = 'credit'",
            "active_cards": "SELECT COUNT(*) as count FROM cards WHERE is_sold = 0"
        }
        
        stats = {}
        for key, query in queries.items():
            result = await self.execute_async(query, (), "one")
            stats[key] = result[0] if result else 0
            
        self._cache_result(cache_key, stats)
        return stats
        
    def health_check(self) -> Dict[str, Any]:
        """Perform database health check"""
        try:
            with self.pool.get_connection() as conn:
                cursor = conn.cursor()
                
                # Basic connectivity test
                cursor.execute("SELECT 1")
                
                # Check WAL mode
                cursor.execute("PRAGMA journal_mode")
                journal_mode = cursor.fetchone()[0]
                
                # Check database size
                cursor.execute("PRAGMA page_count")
                page_count = cursor.fetchone()[0]
                cursor.execute("PRAGMA page_size")
                page_size = cursor.fetchone()[0]
                db_size_mb = (page_count * page_size) / (1024 * 1024)
                
                # Check connection pool status
                pool_status = {
                    "created_connections": self.pool._created_connections,
                    "max_connections": self.pool.max_connections,
                    "queue_size": self.pool._pool.qsize()
                }
                
                return {
                    "status": "healthy",
                    "journal_mode": journal_mode,
                    "database_size_mb": round(db_size_mb, 2),
                    "connection_pool": pool_status,
                    "cache_entries": len(self._query_cache)
                }
                
        except Exception as e:
            logger.error("Database health check failed", e)
            return {
                "status": "unhealthy",
                "error": str(e)
            }
            
    def cleanup(self):
        """Cleanup resources"""
        logger.info("Cleaning up database service")
        self.executor.shutdown(wait=True)
        self.pool.close_all()
        self._query_cache.clear()
        self._cache_timestamps.clear()


# Global database service instance
db_service = DatabaseService()