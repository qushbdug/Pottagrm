#!/usr/bin/env python3
"""
Database optimization utilities for better concurrent access
"""

import logging
import sqlite3
from bot_modules.config import *

logger = logging.getLogger(__name__)

def optimize_database():
    """Optimize database settings for better concurrent access"""
    try:
        conn = sqlite3.connect(DB_PATH, timeout=60.0)
        cursor = conn.cursor()
        
        # Set optimal pragmas for concurrent access
        optimizations = [
            # WAL mode for better concurrency
            "PRAGMA journal_mode = WAL",
            
            # Set synchronous to NORMAL for good balance of safety and performance
            "PRAGMA synchronous = NORMAL",
            
            # Increase cache size for better performance
            "PRAGMA cache_size = 4000",
            
            # Use memory for temp storage
            "PRAGMA temp_store = memory",
            
            # Set busy timeout to handle concurrent access
            "PRAGMA busy_timeout = 30000",
            
            # Enable foreign keys
            "PRAGMA foreign_keys = ON",
            
            # Optimize for read performance
            "PRAGMA optimize",
            
            # Set page size (must be done before any tables are created)
            # "PRAGMA page_size = 4096",  # Commented out as tables already exist
            
            # Enable memory-mapped I/O for better performance
            "PRAGMA mmap_size = 268435456",  # 256MB
            
            # Set WAL autocheckpoint for better performance
            "PRAGMA wal_autocheckpoint = 1000",
        ]
        
        for pragma in optimizations:
            try:
                cursor.execute(pragma)
                logger.info(f"Applied optimization: {pragma}")
            except sqlite3.Error as e:
                logger.warning(f"Could not apply optimization '{pragma}': {e}")
        
        conn.commit()
        conn.close()
        
        logger.info("Database optimization completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Database optimization failed: {e}")
        return False

def create_indexes():
    """Create indexes for better query performance"""
    try:
        conn = sqlite3.connect(DB_PATH, timeout=60.0)
        cursor = conn.cursor()
        
        indexes = [
            # User indexes
            "CREATE INDEX IF NOT EXISTS idx_users_telegram_id ON users(telegram_id)",
            "CREATE INDEX IF NOT EXISTS idx_users_phone ON users(phone)",
            "CREATE INDEX IF NOT EXISTS idx_users_role ON users(role)",
            "CREATE INDEX IF NOT EXISTS idx_users_active ON users(is_active)",
            
            # Transaction indexes
            "CREATE INDEX IF NOT EXISTS idx_transactions_from_user ON transactions(from_user)",
            "CREATE INDEX IF NOT EXISTS idx_transactions_to_user ON transactions(to_user)",
            "CREATE INDEX IF NOT EXISTS idx_transactions_type ON transactions(type)",
            "CREATE INDEX IF NOT EXISTS idx_transactions_created_at ON transactions(created_at)",
            "CREATE INDEX IF NOT EXISTS idx_transactions_status ON transactions(status)",
            
            # Network indexes
            "CREATE INDEX IF NOT EXISTS idx_networks_supplier_id ON networks(supplier_id)",
            "CREATE INDEX IF NOT EXISTS idx_networks_active ON networks(is_active)",
            "CREATE INDEX IF NOT EXISTS idx_networks_approved ON networks(is_approved)",
            
            # Card indexes
            "CREATE INDEX IF NOT EXISTS idx_cards_category_id ON cards(category_id)",
            "CREATE INDEX IF NOT EXISTS idx_cards_sold ON cards(is_sold)",
            "CREATE INDEX IF NOT EXISTS idx_cards_sold_to ON cards(sold_to)",
            
            # Network cards indexes
            "CREATE INDEX IF NOT EXISTS idx_network_cards_supplier_id ON network_cards(supplier_id)",
            "CREATE INDEX IF NOT EXISTS idx_network_cards_network_id ON network_cards(network_id)",
            "CREATE INDEX IF NOT EXISTS idx_network_cards_sold ON network_cards(is_sold)",
            "CREATE INDEX IF NOT EXISTS idx_network_cards_category ON network_cards(card_category)",
            
            # Activity logs indexes
            "CREATE INDEX IF NOT EXISTS idx_activity_logs_user_id ON activity_logs(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_activity_logs_created_at ON activity_logs(created_at)",
            
            # System logs indexes
            "CREATE INDEX IF NOT EXISTS idx_system_logs_user_id ON system_logs(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_system_logs_created_at ON system_logs(created_at)",
        ]
        
        for index_sql in indexes:
            try:
                cursor.execute(index_sql)
                logger.info(f"Created index: {index_sql.split('ON')[1].split('(')[0].strip()}")
            except sqlite3.Error as e:
                logger.warning(f"Could not create index: {e}")
        
        conn.commit()
        conn.close()
        
        logger.info("Database indexes created successfully")
        return True
        
    except Exception as e:
        logger.error(f"Index creation failed: {e}")
        return False

def analyze_database():
    """Analyze database for query optimization"""
    try:
        conn = sqlite3.connect(DB_PATH, timeout=60.0)
        cursor = conn.cursor()
        
        # Run ANALYZE to update statistics
        cursor.execute("ANALYZE")
        
        conn.commit()
        conn.close()
        
        logger.info("Database analysis completed")
        return True
        
    except Exception as e:
        logger.error(f"Database analysis failed: {e}")
        return False

def vacuum_database():
    """Vacuum database to optimize storage and performance"""
    try:
        conn = sqlite3.connect(DB_PATH, timeout=60.0)
        cursor = conn.cursor()
        
        # Run VACUUM to optimize database
        cursor.execute("VACUUM")
        
        conn.close()
        
        logger.info("Database vacuum completed")
        return True
        
    except Exception as e:
        logger.error(f"Database vacuum failed: {e}")
        return False

def full_optimization():
    """Run full database optimization"""
    logger.info("Starting full database optimization...")
    
    success = True
    success &= optimize_database()
    success &= create_indexes()
    success &= analyze_database()
    
    if success:
        logger.info("Full database optimization completed successfully")
    else:
        logger.warning("Database optimization completed with some warnings")
    
    return success

if __name__ == "__main__":
    full_optimization()