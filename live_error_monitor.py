#!/usr/bin/env python3
"""
مراقب الأخطاء الفوري - إصلاح المشاكل أثناء الاستخدام
Live Error Monitor - Fix issues during usage
"""

import os
import time
import subprocess
import datetime
from collections import defaultdict
import re

class LiveErrorMonitor:
    def __init__(self):
        self.workspace = "/workspace"
        self.log_files = [
            "bot_coupon_fixed.log",
            "bot_fixed.log", 
            "bot_new.log",
            "bot.log"
        ]
        self.error_patterns = {
            "database_locked": r"database is locked",
            "null_constraint": r"NOT NULL constraint failed",
            "import_error": r"ImportError|ModuleNotFoundError",
            "attribute_error": r"AttributeError",
            "key_error": r"KeyError",
            "value_error": r"ValueError",
            "telegram_error": r"telegram\.error",
            "connection_error": r"ConnectionError|TimeoutError"
        }
        self.error_counts = defaultdict(int)
        self.last_position = {}
        
        # تهيئة مواضع الملفات
        for log_file in self.log_files:
            log_path = os.path.join(self.workspace, log_file)
            if os.path.exists(log_path):
                self.last_position[log_file] = os.path.getsize(log_path)
            else:
                self.last_position[log_file] = 0
    
    def get_new_log_lines(self, log_file):
        """الحصول على السطور الجديدة من ملف السجل"""
        log_path = os.path.join(self.workspace, log_file)
        
        if not os.path.exists(log_path):
            return []
        
        current_size = os.path.getsize(log_path)
        last_pos = self.last_position.get(log_file, 0)
        
        if current_size <= last_pos:
            return []
        
        try:
            with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                f.seek(last_pos)
                new_lines = f.readlines()
                self.last_position[log_file] = f.tell()
                return new_lines
        except Exception as e:
            print(f"❌ خطأ في قراءة {log_file}: {e}")
            return []
    
    def analyze_error(self, line):
        """تحليل سطر الخطأ وتحديد نوعه"""
        for error_type, pattern in self.error_patterns.items():
            if re.search(pattern, line, re.IGNORECASE):
                return error_type, line.strip()
        return None, None
    
    def fix_database_locked_error(self):
        """إصلاح مشكلة قفل قاعدة البيانات"""
        print("🔧 إصلاح مشكلة قفل قاعدة البيانات...")
        try:
            # تشغيل محسن قاعدة البيانات
            subprocess.run([
                "python3", 
                os.path.join(self.workspace, "database_optimizer.py")
            ], capture_output=True, text=True, timeout=30)
            print("✅ تم تشغيل محسن قاعدة البيانات")
        except Exception as e:
            print(f"❌ خطأ في إصلاح قاعدة البيانات: {e}")
    
    def fix_import_error(self, error_line):
        """إصلاح أخطاء الاستيراد"""
        print(f"🔧 إصلاح خطأ الاستيراد: {error_line}")
        
        # إعادة تشغيل البوت إذا كان خطأ استيراد حرج
        if "bot_modules" in error_line or "handlers" in error_line:
            self.restart_bot()
    
    def fix_null_constraint_error(self, error_line):
        """إصلاح أخطاء القيود الفارغة"""
        print(f"🔧 إصلاح خطأ القيد الفارغ: {error_line}")
        
        if "transactions.type" in error_line:
            print("🔍 مشكلة في جدول المعاملات - تم إصلاحها مسبقاً")
        
        # قد نحتاج لإعادة تشغيل البوت
        if self.error_counts["null_constraint"] > 3:
            print("⚠️ أخطاء متكررة في القيود - إعادة تشغيل البوت")
            self.restart_bot()
    
    def restart_bot(self):
        """إعادة تشغيل البوت"""
        print("🔄 إعادة تشغيل البوت...")
        try:
            # إيقاف البوت الحالي
            subprocess.run(["pkill", "-f", "python3 main.py"], timeout=10)
            time.sleep(3)
            
            # تشغيل البوت الجديد
            log_file = f"bot_restart_{datetime.datetime.now().strftime('%H%M%S')}.log"
            subprocess.Popen([
                "nohup", "python3", "main.py"
            ], stdout=open(log_file, 'w'), stderr=subprocess.STDOUT, 
               cwd=self.workspace)
            
            time.sleep(5)
            print("✅ تم إعادة تشغيل البوت")
            
        except Exception as e:
            print(f"❌ خطأ في إعادة تشغيل البوت: {e}")
    
    def get_bot_status(self):
        """فحص حالة البوت"""
        try:
            result = subprocess.run(
                ["ps", "aux"], 
                capture_output=True, text=True, timeout=5
            )
            
            for line in result.stdout.split('\n'):
                if 'python3 main.py' in line and 'grep' not in line:
                    parts = line.split()
                    if len(parts) >= 2:
                        return {
                            'running': True,
                            'pid': parts[1],
                            'cpu': parts[2],
                            'memory': parts[3]
                        }
            
            return {'running': False}
            
        except Exception:
            return {'running': False}
    
    def monitor_loop(self):
        """حلقة المراقبة الرئيسية"""
        print("👁️ ================================================================ 👁️")
        print("                    مراقب الأخطاء الفوري - نشط")
        print("👁️ ================================================================ 👁️")
        print(f"⏰ بدء المراقبة: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("🔍 مراقبة الملفات:", ", ".join(self.log_files))
        print("⚡ جاهز لإصلاح الأخطاء فوراً!")
        print()
        
        try:
            while True:
                # فحص حالة البوت
                bot_status = self.get_bot_status()
                
                if not bot_status['running']:
                    print(f"⚠️ [{datetime.datetime.now().strftime('%H:%M:%S')}] البوت متوقف - إعادة التشغيل...")
                    self.restart_bot()
                
                # فحص الأخطاء في جميع ملفات السجلات
                errors_found = False
                
                for log_file in self.log_files:
                    new_lines = self.get_new_log_lines(log_file)
                    
                    for line in new_lines:
                        error_type, error_line = self.analyze_error(line)
                        
                        if error_type:
                            errors_found = True
                            self.error_counts[error_type] += 1
                            
                            timestamp = datetime.datetime.now().strftime('%H:%M:%S')
                            print(f"🚨 [{timestamp}] خطأ {error_type} في {log_file}:")
                            print(f"   {error_line}")
                            
                            # إصلاح فوري حسب نوع الخطأ
                            if error_type == "database_locked":
                                self.fix_database_locked_error()
                            elif error_type == "import_error":
                                self.fix_import_error(error_line)
                            elif error_type == "null_constraint":
                                self.fix_null_constraint_error(error_line)
                            
                            print()
                
                # عرض حالة دورية
                if not errors_found:
                    current_time = datetime.datetime.now()
                    if current_time.second % 30 == 0:  # كل 30 ثانية
                        status_emoji = "🟢" if bot_status['running'] else "🔴"
                        print(f"{status_emoji} [{current_time.strftime('%H:%M:%S')}] البوت يعمل - لا توجد أخطاء")
                
                time.sleep(1)  # فحص كل ثانية
                
        except KeyboardInterrupt:
            print("\n⏹️ تم إيقاف المراقبة بواسطة المستخدم")
        except Exception as e:
            print(f"\n❌ خطأ في نظام المراقبة: {e}")
            print("🔄 محاولة إعادة تشغيل المراقبة...")
            time.sleep(5)
            self.monitor_loop()  # إعادة تشغيل المراقبة

def main():
    monitor = LiveErrorMonitor()
    monitor.monitor_loop()

if __name__ == "__main__":
    main()