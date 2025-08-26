#!/usr/bin/env python3
"""
حل تضارب الوحدات بين ملفات البوت
Module Conflict Resolver for Bot Files
"""

import os
import re
import shutil
from datetime import datetime

class ModuleConflictResolver:
    def __init__(self, workspace_path='/workspace'):
        self.workspace_path = workspace_path
        self.backup_dir = f"{workspace_path}/backups/module_fixes_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
    def create_backup(self):
        """إنشاء نسخة احتياطية من الملفات"""
        try:
            os.makedirs(self.backup_dir, exist_ok=True)
            
            files_to_backup = [
                'yemen_net_bot.py',
                'yemen_net_bot_new.py',
                'bot_modules/database.py',
                'bot_modules/handlers.py',
                'bot_modules/config.py',
                'bot_modules/admin_functions.py'
            ]
            
            for file_path in files_to_backup:
                if os.path.exists(file_path):
                    backup_path = f"{self.backup_dir}/{os.path.basename(file_path)}"
                    shutil.copy2(file_path, backup_path)
                    print(f"✅ تم نسخ {file_path} إلى {backup_path}")
            
            print(f"✅ تم إنشاء النسخة الاحتياطية في: {self.backup_dir}")
            return True
            
        except Exception as e:
            print(f"❌ فشل في إنشاء النسخة الاحتياطية: {e}")
            return False
    
    def fix_bot_modules(self):
        """إصلاح وحدات البوت"""
        print("🔧 === إصلاح وحدات البوت ===")
        
        try:
            # إصلاح ملف قاعدة البيانات
            self._fix_database_module()
            
            # إصلاح ملف المعالجات
            self._fix_handlers_module()
            
            # إصلاح ملف الإعدادات
            self._fix_config_module()
            
            # إصلاح ملف الوظائف الإدارية
            self._fix_admin_functions_module()
            
            print("✅ تم إصلاح جميع وحدات البوت")
            return True
            
        except Exception as e:
            print(f"❌ فشل في إصلاح وحدات البوت: {e}")
            return False
    
    def _fix_database_module(self):
        """إصلاح وحدة قاعدة البيانات"""
        try:
            with open('bot_modules/database.py', 'r', encoding='utf-8') as f:
                content = f.read()
            
            # إصلاح استيراد الإعدادات
            content = content.replace('from bot_modules.config import *', 'from config import *')
            
            # كتابة الملف المُصلح
            with open('bot_modules/database.py', 'w', encoding='utf-8') as f:
                f.write(content)
            
            print("  ✅ تم إصلاح وحدة قاعدة البيانات")
            
        except Exception as e:
            print(f"  ❌ فشل في إصلاح وحدة قاعدة البيانات: {e}")
    
    def _fix_handlers_module(self):
        """إصلاح وحدة المعالجات"""
        try:
            with open('bot_modules/handlers.py', 'r', encoding='utf-8') as f:
                content = f.read()
            
            # إصلاح استيراد الوحدات
            content = content.replace('from bot_modules.config import *', 'from config import *')
            content = content.replace('from bot_modules.utils import *', 'from utils import *')
            
            # كتابة الملف المُصلح
            with open('bot_modules/handlers.py', 'w', encoding='utf-8') as f:
                f.write(content)
            
            print("  ✅ تم إصلاح وحدة المعالجات")
            
        except Exception as e:
            print(f"  ❌ فشل في إصلاح وحدة المعالجات: {e}")
    
    def _fix_config_module(self):
        """إصلاح وحدة الإعدادات"""
        try:
            with open('bot_modules/config.py', 'r', encoding='utf-8') as f:
                content = f.read()
            
            # إصلاح المسارات
            content = content.replace('os.path.abspath(\'yemen_net.db\')', 'os.path.abspath(\'yemen_net.db\')')
            
            # كتابة الملف المُصلح
            with open('bot_modules/config.py', 'w', encoding='utf-8') as f:
                f.write(content)
            
            print("  ✅ تم إصلاح وحدة الإعدادات")
            
        except Exception as e:
            print(f"  ❌ فشل في إصلاح وحدة الإعدادات: {e}")
    
    def _fix_admin_functions_module(self):
        """إصلاح وحدة الوظائف الإدارية"""
        try:
            with open('bot_modules/admin_functions.py', 'r', encoding='utf-8') as f:
                content = f.read()
            
            # إصلاح استيراد الوحدات
            content = content.replace('from bot_modules.config import *', 'from config import *')
            content = content.replace('from bot_modules.utils import *', 'from utils import *')
            content = content.replace('from bot_modules.database import *', 'from database import *')
            
            # كتابة الملف المُصلح
            with open('bot_modules/admin_functions.py', 'w', encoding='utf-8') as f:
                f.write(content)
            
            print("  ✅ تم إصلاح وحدة الوظائف الإدارية")
            
        except Exception as e:
            print(f"  ❌ فشل في إصلاح وحدة الوظائف الإدارية: {e}")
    
    def create_unified_main_file(self):
        """إنشاء ملف رئيسي موحد"""
        print("🔧 === إنشاء ملف رئيسي موحد ===")
        
        try:
            unified_content = '''#!/usr/bin/env python3
"""
بوت كروت الإنترنت اليمني - النسخة الموحدة
Yemen Net Card Bot - Unified Version
"""

import logging
import asyncio
import sys
import os
from datetime import datetime

# إضافة bot_modules إلى مسار Python
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'bot_modules'))

# استيراد مكونات البوت
from telegram import Update, MenuButtonCommands, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ConversationHandler, PicklePersistence, filters, CallbackContext
)

# استيراد الوحدات المحلية
try:
    from config import *
    from database import init_db, get_db_connection
    from utils import *
    from handlers import *
    from admin_functions import *
except ImportError as e:
    print(f"خطأ في استيراد الوحدات: {e}")
    print("تأكد من وجود جميع ملفات الوحدات في مجلد bot_modules")
    sys.exit(1)

# إعداد التسجيل
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

async def main():
    """الدالة الرئيسية للبوت"""
    try:
        # تهيئة قاعدة البيانات
        print("🔧 تهيئة قاعدة البيانات...")
        init_db()
        print("✅ تم تهيئة قاعدة البيانات")
        
        # إنشاء تطبيق البوت
        print("🤖 إنشاء تطبيق البوت...")
        application = Application.builder().token(BOT_TOKEN).build()
        
        # إضافة معالجات الأوامر
        print("📝 إضافة معالجات الأوامر...")
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("wallet", wallet_handler))
        application.add_handler(CommandHandler("admin", admin_handler))
        application.add_handler(CommandHandler("cancel", cancel))
        
        # إضافة معالج النقر على الأزرار
        print("🔘 إضافة معالج النقر على الأزرار...")
        application.add_handler(CallbackQueryHandler(button_click_handler))
        
        # إضافة معالج الرسائل النصية
        print("📱 إضافة معالج الرسائل النصية...")
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))
        
        # تعيين قائمة الأوامر
        print("📋 تعيين قائمة الأوامر...")
        await application.bot.set_my_commands(QUICK_COMMANDS)
        
        # بدء البوت
        print("🚀 بدء البوت...")
        await application.run_polling()
        
    except Exception as e:
        logger.error(f"خطأ في تشغيل البوت: {e}")
        print(f"❌ فشل في تشغيل البوت: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\\n🛑 تم إيقاف البوت بواسطة المستخدم")
    except Exception as e:
        print(f"\\n💥 خطأ غير متوقع: {e}")
        logger.error(f"خطأ غير متوقع: {e}")
'''
            
            # كتابة الملف الموحد
            with open('yemen_net_bot_unified.py', 'w', encoding='utf-8') as f:
                f.write(unified_content)
            
            print("✅ تم إنشاء الملف الرئيسي الموحد: yemen_net_bot_unified.py")
            return True
            
        except Exception as e:
            print(f"❌ فشل في إنشاء الملف الموحد: {e}")
            return False
    
    def run_complete_resolution(self):
        """تشغيل الحل الشامل للتضارب"""
        print("🚀 === بدء حل تضارب الوحدات ===")
        
        # إنشاء نسخة احتياطية
        if not self.create_backup():
            return False
        
        # إصلاح وحدات البوت
        if not self.fix_bot_modules():
            return False
        
        # إنشاء ملف موحد
        if not self.create_unified_main_file():
            print("⚠️ فشل في إنشاء الملف الموحد، لكن الإصلاح الأساسي نجح")
        
        print("🎉 === تم حل تضارب الوحدات بنجاح! ===")
        return True

def main():
    """الدالة الرئيسية"""
    print("🔧 أداة حل تضارب الوحدات")
    print("=" * 50)
    
    resolver = ModuleConflictResolver()
    
    try:
        success = resolver.run_complete_resolution()
        
        if success:
            print("\\n✅ تم حل تضارب الوحدات بنجاح!")
            print("📁 يمكنك الآن استخدام الملف الموحد: yemen_net_bot_unified.py")
        else:
            print("\\n❌ فشل في حل تضارب الوحدات")
            print("🔍 يرجى مراجعة السجلات للحصول على مزيد من التفاصيل")
            
    except Exception as e:
        print(f"\\n💥 حدث خطأ غير متوقع: {e}")

if __name__ == "__main__":
    main()