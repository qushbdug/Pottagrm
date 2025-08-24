#!/usr/bin/env python3
"""
Enhanced Bot Runner with Comprehensive Error Checking
مشغل البوت المحسن مع فحص شامل للأخطاء

This script provides:
- Pre-flight checks for all dependencies
- Database integrity verification
- Token validation
- Comprehensive error logging
- Graceful restart mechanisms
- Real-time monitoring
"""

import sys
import os
import logging
import sqlite3
import traceback
from datetime import datetime
import asyncio
import signal
import time

# Add bot_modules to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'bot_modules'))

def setup_enhanced_logging():
    """إعداد نظام مراقبة محسن للأخطاء"""
    
    # Create logs directory if it doesn't exist
    os.makedirs('logs', exist_ok=True)
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
    )
    
    simple_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # File handler for detailed logs
    file_handler = logging.FileHandler(f'logs/bot_detailed_{datetime.now().strftime("%Y%m%d")}.log')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(detailed_formatter)
    
    # File handler for errors only
    error_handler = logging.FileHandler(f'logs/bot_errors_{datetime.now().strftime("%Y%m%d")}.log')
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(detailed_formatter)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(simple_formatter)
    
    # Add handlers
    root_logger.addHandler(file_handler)
    root_logger.addHandler(error_handler)
    root_logger.addHandler(console_handler)
    
    return logging.getLogger(__name__)

def check_python_version():
    """فحص إصدار Python"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        raise RuntimeError(f"Python 3.8+ required, but {version.major}.{version.minor} found")
    
    print(f"✅ Python version: {version.major}.{version.minor}.{version.micro}")
    return True

def check_dependencies():
    """فحص شامل للتبعيات المطلوبة"""
    
    required_modules = [
        ('telegram', 'python-telegram-bot'),
        ('requests', 'requests'),
        ('sqlite3', 'built-in'),
        ('asyncio', 'built-in'),
        ('logging', 'built-in'),
        ('datetime', 'built-in'),
        ('json', 'built-in'),
        ('os', 'built-in'),
        ('sys', 'built-in')
    ]
    
    optional_modules = [
        ('deep_translator', 'deep-translator'),
        ('bs4', 'beautifulsoup4'),
        ('httpx', 'httpx'),
        ('dotenv', 'python-dotenv'),
        ('cryptography', 'cryptography'),
        ('pandas', 'pandas'),
        ('matplotlib', 'matplotlib'),
        ('PIL', 'Pillow'),
        ('qrcode', 'qrcode')
    ]
    
    print("🔍 فحص التبعيات المطلوبة...")
    
    # Check required modules
    missing_required = []
    for module, package in required_modules:
        try:
            __import__(module)
            print(f"✅ {module}")
        except ImportError:
            print(f"❌ {module} - مطلوب تثبيت: {package}")
            missing_required.append(package)
    
    if missing_required:
        raise ImportError(f"المكتبات المطلوبة غير مثبتة: {', '.join(missing_required)}")
    
    # Check optional modules
    print("\n🔍 فحص التبعيات الاختيارية...")
    available_optional = []
    for module, package in optional_modules:
        try:
            __import__(module)
            print(f"✅ {module}")
            available_optional.append(module)
        except ImportError:
            print(f"⚠️ {module} - اختياري: {package}")
    
    print(f"\n📊 المكتبات الاختيارية المتاحة: {len(available_optional)}/{len(optional_modules)}")
    return True

def check_bot_configuration():
    """فحص إعدادات البوت"""
    
    print("🔍 فحص إعدادات البوت...")
    
    try:
        from config import BOT_TOKEN, DB_PATH
        
        # Check token format
        if not BOT_TOKEN or len(BOT_TOKEN) < 40:
            raise ValueError("تنسيق التوكن غير صحيح")
        
        if not BOT_TOKEN.count(':') == 1:
            raise ValueError("تنسيق التوكن غير صحيح - يجب أن يحتوي على ':'")
        
        print(f"✅ التوكن: {BOT_TOKEN[:10]}...{BOT_TOKEN[-10:]}")
        print(f"✅ مسار قاعدة البيانات: {DB_PATH}")
        
        return True
        
    except ImportError as e:
        raise ImportError(f"خطأ في استيراد الإعدادات: {e}")
    except Exception as e:
        raise RuntimeError(f"خطأ في فحص الإعدادات: {e}")

def check_database_integrity():
    """فحص سلامة قاعدة البيانات"""
    
    print("🔍 فحص سلامة قاعدة البيانات...")
    
    from config import DB_PATH
    
    if not os.path.exists(DB_PATH):
        print("⚠️ قاعدة البيانات غير موجودة - سيتم إنشاؤها")
        return True
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check database file integrity
        cursor.execute("PRAGMA integrity_check")
        result = cursor.fetchone()
        if result[0] != 'ok':
            raise sqlite3.DatabaseError(f"قاعدة البيانات تالفة: {result[0]}")
        
        # Check tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        essential_tables = ['users', 'transactions', 'networks', 'cards']
        missing_tables = [table for table in essential_tables if table not in tables]
        
        if missing_tables:
            print(f"⚠️ جداول مفقودة (سيتم إنشاؤها): {missing_tables}")
        
        print(f"✅ قاعدة البيانات سليمة - {len(tables)} جدول")
        print(f"✅ حجم قاعدة البيانات: {os.path.getsize(DB_PATH)} بايت")
        
        conn.close()
        return True
        
    except Exception as e:
        raise sqlite3.DatabaseError(f"خطأ في فحص قاعدة البيانات: {e}")

def check_file_permissions():
    """فحص صلاحيات الملفات"""
    
    print("🔍 فحص صلاحيات الملفات...")
    
    # Check write permissions for logs
    try:
        os.makedirs('logs', exist_ok=True)
        test_file = 'logs/test_write.tmp'
        with open(test_file, 'w') as f:
            f.write('test')
        os.remove(test_file)
        print("✅ صلاحيات الكتابة في مجلد logs")
    except Exception as e:
        raise PermissionError(f"لا توجد صلاحيات كتابة في مجلد logs: {e}")
    
    # Check database write permissions
    from config import DB_PATH
    db_dir = os.path.dirname(os.path.abspath(DB_PATH))
    if not os.access(db_dir, os.W_OK):
        raise PermissionError(f"لا توجد صلاحيات كتابة في مجلد قاعدة البيانات: {db_dir}")
    
    print("✅ صلاحيات قاعدة البيانات")
    return True

def pre_flight_checks():
    """فحوصات ما قبل التشغيل"""
    
    print("🚀 بدء فحوصات ما قبل التشغيل...")
    print("=" * 50)
    
    try:
        check_python_version()
        check_dependencies()
        check_bot_configuration()
        check_database_integrity()
        check_file_permissions()
        
        print("=" * 50)
        print("✅ جميع الفحوصات نجحت - البوت جاهز للتشغيل!")
        return True
        
    except Exception as e:
        print("=" * 50)
        print(f"❌ فشل في الفحوصات: {e}")
        print(f"🔍 تفاصيل الخطأ:\n{traceback.format_exc()}")
        return False

class BotMonitor:
    """مراقب البوت للتعامل مع الأخطاء وإعادة التشغيل"""
    
    def __init__(self, logger):
        self.logger = logger
        self.running = False
        self.restart_count = 0
        self.max_restarts = 5
        self.last_restart = 0
        self.restart_delay = 30  # seconds
    
    def signal_handler(self, signum, frame):
        """معالج إشارات النظام"""
        self.logger.info(f"تلقي إشارة {signum} - إيقاف البوت...")
        self.running = False
    
    async def run_bot_safely(self):
        """تشغيل البوت مع معالجة الأخطاء"""
        
        try:
            # Import bot modules
            from database import init_db
            from yemen_net_bot_new import main
            
            # Initialize database
            self.logger.info("تهيئة قاعدة البيانات...")
            init_db()
            
            # Run the bot
            self.logger.info("بدء تشغيل البوت...")
            await main()
            
        except KeyboardInterrupt:
            self.logger.info("تم إيقاف البوت بواسطة المستخدم")
            self.running = False
            
        except Exception as e:
            self.logger.error(f"خطأ في تشغيل البوت: {e}")
            self.logger.error(f"تفاصيل الخطأ:\n{traceback.format_exc()}")
            
            # Check if we should restart
            current_time = time.time()
            if (current_time - self.last_restart) > 300:  # Reset counter after 5 minutes
                self.restart_count = 0
            
            if self.restart_count < self.max_restarts:
                self.restart_count += 1
                self.last_restart = current_time
                
                self.logger.info(f"محاولة إعادة التشغيل {self.restart_count}/{self.max_restarts} بعد {self.restart_delay} ثانية...")
                await asyncio.sleep(self.restart_delay)
                
                # Exponential backoff
                self.restart_delay = min(self.restart_delay * 2, 300)
                
                return True  # Signal to restart
            else:
                self.logger.error("تم الوصول للحد الأقصى من محاولات إعادة التشغيل")
                self.running = False
                
        return False  # Don't restart
    
    async def monitor_loop(self):
        """حلقة مراقبة البوت الرئيسية"""
        
        self.running = True
        
        # Set up signal handlers
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        while self.running:
            try:
                should_restart = await self.run_bot_safely()
                if not should_restart:
                    break
                    
            except Exception as e:
                self.logger.error(f"خطأ في حلقة المراقبة: {e}")
                break
        
        self.logger.info("توقف مراقب البوت")

async def main():
    """الدالة الرئيسية"""
    
    # Setup logging
    logger = setup_enhanced_logging()
    
    print("🤖 مشغل البوت المحسن - Yemen Net Bot")
    print("=" * 50)
    
    # Run pre-flight checks
    if not pre_flight_checks():
        print("\n❌ فشل في فحوصات ما قبل التشغيل - توقف البرنامج")
        sys.exit(1)
    
    print("\n🚀 بدء تشغيل البوت...")
    logger.info("بدء تشغيل البوت مع نظام المراقبة المحسن")
    
    # Start bot monitor
    monitor = BotMonitor(logger)
    
    try:
        await monitor.monitor_loop()
    except KeyboardInterrupt:
        logger.info("تم إيقاف البوت بواسطة المستخدم")
    except Exception as e:
        logger.error(f"خطأ في الدالة الرئيسية: {e}")
        logger.error(traceback.format_exc())
    finally:
        logger.info("انتهى تشغيل البوت")
        print("\n👋 تم إيقاف البوت")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 تم إيقاف البوت")
    except Exception as e:
        print(f"\n❌ خطأ فادح: {e}")
        print(traceback.format_exc())
        sys.exit(1)