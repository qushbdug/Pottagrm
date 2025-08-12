"""
مدير الاتصال بقاعدة البيانات المحسن
"""

import sqlite3
import logging
from contextlib import contextmanager
from typing import Generator, Optional
from bot.config import DB_PATH

logger = logging.getLogger(__name__)

class DatabaseManager:
    """مدير قاعدة البيانات مع إدارة محسنة للاتصالات"""
    
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        
    @contextmanager
    def get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """الحصول على اتصال قاعدة البيانات مع إدارة تلقائية للموارد"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row  # للحصول على نتائج كـ dictionaries
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"خطأ في قاعدة البيانات: {e}")
            raise
        finally:
            if conn:
                conn.close()
    
    @contextmanager
    def get_cursor(self) -> Generator[tuple[sqlite3.Connection, sqlite3.Cursor], None, None]:
        """الحصول على cursor مع إدارة تلقائية للموارد"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                yield conn, cursor
                conn.commit()
            except Exception as e:
                conn.rollback()
                logger.error(f"خطأ في تنفيذ الاستعلام: {e}")
                raise
    
    def execute_query(self, query: str, params: tuple = ()) -> Optional[list]:
        """تنفيذ استعلام واحد وإرجاع النتائج"""
        with self.get_cursor() as (conn, cursor):
            cursor.execute(query, params)
            return cursor.fetchall()
    
    def execute_many(self, query: str, params_list: list) -> int:
        """تنفيذ استعلام متعدد وإرجاع عدد الصفوف المتأثرة"""
        with self.get_cursor() as (conn, cursor):
            cursor.executemany(query, params_list)
            return cursor.rowcount
    
    def execute_script(self, script: str) -> None:
        """تنفيذ سكريبت SQL متعدد الأوامر"""
        with self.get_connection() as conn:
            conn.executescript(script)

# إنشاء مثيل عام لمدير قاعدة البيانات
db_manager = DatabaseManager()

def get_db_connection():
    """دالة للتوافق مع الكود القديم"""
    return sqlite3.connect(DB_PATH)