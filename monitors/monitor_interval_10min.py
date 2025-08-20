#!/usr/bin/env python3
"""
مراقب البوت لمدة 10 دقائق - فحص الأخطاء وإصلاحها
"""

import time
import subprocess
import os
import sqlite3
from datetime import datetime, timedelta

class BotMonitor10Min:
    def __init__(self):
        self.start_time = datetime.now()
        self.end_time = self.start_time + timedelta(minutes=10)
        self.errors_found = []
        self.fixes_applied = []
        self.check_count = 0
        
    def log(self, message, level="INFO"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        symbols = {"INFO": "ℹ️", "SUCCESS": "✅", "WARNING": "⚠️", "ERROR": "❌", "FIX": "🔧"}
        print(f"[{timestamp}] {symbols.get(level, 'ℹ️')} {message}")
    
    def check_bot_running(self):
        """فحص إذا كان البوت يعمل"""
        try:
            result = subprocess.run(['pgrep', '-f', 'python.*main.py'], capture_output=True, text=True)
            return len(result.stdout.strip()) > 0
        except:
            return False
    
    def get_recent_errors(self):
        """الحصول على الأخطاء الحديثة"""
        errors = []
        try:
            if os.path.exists('bot_10min_test.log'):
                with open('bot_10min_test.log', 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                # فحص آخر 50 سطر
                recent_lines = lines[-50:] if len(lines) > 50 else lines
                
                for line in recent_lines:
                    line_lower = line.lower()
                    if any(word in line_lower for word in ['error', 'exception', 'traceback', 'failed', 'crash']):
                        # تصنيف الأخطاء
                        if 'database is locked' in line_lower:
                            errors.append(('DATABASE_LOCK', line.strip()))
                        elif 'not defined' in line_lower or 'nameError' in line_lower:
                            errors.append(('NAME_ERROR', line.strip()))
                        elif 'no such column' in line_lower:
                            errors.append(('COLUMN_ERROR', line.strip()))
                        elif 'import' in line_lower:
                            errors.append(('IMPORT_ERROR', line.strip()))
                        elif 'connection' in line_lower:
                            errors.append(('CONNECTION_ERROR', line.strip()))
                        else:
                            errors.append(('GENERAL_ERROR', line.strip()))
        except Exception as e:
            errors.append(('LOG_ERROR', f'خطأ في قراءة السجل: {e}'))
        
        return errors
    
    def fix_database_lock(self):
        """إصلاح قفل قاعدة البيانات"""
        try:
            self.log("إصلاح قفل قاعدة البيانات...", "FIX")
            conn = sqlite3.connect('yemen_net.db', timeout=30.0)
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
            conn.execute("PRAGMA busy_timeout=30000;")
            conn.close()
            self.fixes_applied.append("إصلاح قفل قاعدة البيانات")
            self.log("تم إصلاح قفل قاعدة البيانات", "SUCCESS")
            return True
        except Exception as e:
            self.log(f"فشل إصلاح قاعدة البيانات: {e}", "ERROR")
            return False
    
    def restart_bot(self):
        """إعادة تشغيل البوت"""
        try:
            self.log("إعادة تشغيل البوت...", "FIX")
            subprocess.run(['pkill', '-f', 'python.*main.py'], capture_output=True)
            time.sleep(3)
            
            with open('bot_10min_test.log', 'a') as log_file:
                subprocess.Popen(['python3', 'main.py'], stdout=log_file, stderr=subprocess.STDOUT)
            
            time.sleep(5)
            if self.check_bot_running():
                self.fixes_applied.append("إعادة تشغيل البوت")
                self.log("تم إعادة تشغيل البوت بنجاح", "SUCCESS")
                return True
            else:
                self.log("فشل في إعادة التشغيل", "ERROR")
                return False
        except Exception as e:
            self.log(f"خطأ في إعادة التشغيل: {e}", "ERROR")
            return False
    
    def apply_fixes(self, errors):
        """تطبيق الإصلاحات"""
        fixes_count = 0
        error_types = [error[0] for error in errors]
        
        # إصلاح قفل قاعدة البيانات
        if 'DATABASE_LOCK' in error_types:
            if self.fix_database_lock():
                fixes_count += 1
        
        # إعادة تشغيل للأخطاء الحرجة
        if any(etype in ['NAME_ERROR', 'IMPORT_ERROR', 'CONNECTION_ERROR'] for etype in error_types):
            if self.restart_bot():
                fixes_count += 1
        
        # إعادة تشغيل إذا توقف البوت
        if not self.check_bot_running():
            if self.restart_bot():
                fixes_count += 1
        
        return fixes_count
    
    def monitoring_cycle(self):
        """دورة مراقبة واحدة"""
        self.check_count += 1
        elapsed = (datetime.now() - self.start_time).total_seconds() / 60
        remaining = 10 - elapsed
        
        self.log(f"فحص #{self.check_count} - المدة: {elapsed:.1f}د - المتبقي: {remaining:.1f}د")
        
        # فحص حالة البوت
        is_running = self.check_bot_running()
        if is_running:
            pid = subprocess.run(['pgrep', '-f', 'python.*main.py'], capture_output=True, text=True).stdout.strip()
            self.log(f"البوت يعمل (PID: {pid})", "SUCCESS")
        else:
            self.log("البوت متوقف!", "ERROR")
            self.restart_bot()
            return
        
        # فحص الأخطاء
        recent_errors = self.get_recent_errors()
        
        if recent_errors:
            self.log(f"وُجد {len(recent_errors)} خطأ حديث", "WARNING")
            
            # عرض آخر 3 أخطاء
            for error_type, error_msg in recent_errors[-3:]:
                self.log(f"[{error_type}] {error_msg[:80]}...", "ERROR")
            
            # تطبيق الإصلاحات
            fixes = self.apply_fixes(recent_errors)
            if fixes > 0:
                self.log(f"تم تطبيق {fixes} إصلاح", "FIX")
            
            self.errors_found.extend(recent_errors)
        else:
            self.log("لا توجد أخطاء حديثة", "SUCCESS")
    
    def run_monitoring(self):
        """تشغيل المراقبة لمدة 10 دقائق"""
        self.log("🚀 بدء مراقبة البوت لمدة 10 دقائق")
        self.log(f"⏰ من {self.start_time.strftime('%H:%M:%S')} إلى {self.end_time.strftime('%H:%M:%S')}")
        
        # تقرير كل دقيقتين
        next_report = self.start_time + timedelta(minutes=2)
        
        try:
            while datetime.now() < self.end_time:
                self.monitoring_cycle()
                
                # تقرير دوري
                if datetime.now() >= next_report:
                    elapsed = (datetime.now() - self.start_time).total_seconds() / 60
                    self.log("=" * 40, "INFO")
                    self.log(f"📊 تقرير التقدم - {elapsed:.1f} دقيقة", "INFO")
                    self.log(f"🔍 الفحوصات: {self.check_count}", "INFO")
                    self.log(f"⚠️ الأخطاء: {len(self.errors_found)}", "INFO")
                    self.log(f"🔧 الإصلاحات: {len(self.fixes_applied)}", "INFO")
                    self.log(f"🚀 البوت: {'يعمل' if self.check_bot_running() else 'متوقف'}", "INFO")
                    self.log("=" * 40, "INFO")
                    next_report += timedelta(minutes=2)
                
                time.sleep(30)  # فحص كل 30 ثانية
        
        except KeyboardInterrupt:
            self.log("تم إيقاف المراقبة يدوياً", "WARNING")
        
        self.print_final_report()
    
    def print_final_report(self):
        """التقرير النهائي"""
        elapsed = (datetime.now() - self.start_time).total_seconds() / 60
        
        self.log("🎉 انتهت مراقبة البوت!", "SUCCESS")
        self.log("=" * 50, "INFO")
        self.log("📋 التقرير النهائي", "INFO")
        self.log("=" * 50, "INFO")
        
        self.log(f"⏱️ المدة الإجمالية: {elapsed:.1f} دقيقة", "INFO")
        self.log(f"🔍 إجمالي الفحوصات: {self.check_count}", "INFO")
        self.log(f"⚠️ إجمالي الأخطاء: {len(self.errors_found)}", "INFO")
        self.log(f"🔧 إجمالي الإصلاحات: {len(self.fixes_applied)}", "INFO")
        
        # تصنيف الأخطاء
        if self.errors_found:
            error_types = {}
            for error_type, _ in self.errors_found:
                error_types[error_type] = error_types.get(error_type, 0) + 1
            
            self.log("⚠️ أنواع الأخطاء:", "INFO")
            for error_type, count in error_types.items():
                self.log(f"  • {error_type}: {count} مرة", "WARNING")
        
        # الإصلاحات المطبقة
        if self.fixes_applied:
            self.log("🔧 الإصلاحات المطبقة:", "INFO")
            for i, fix in enumerate(self.fixes_applied, 1):
                self.log(f"  {i}. {fix}", "SUCCESS")
        
        # الحالة النهائية
        final_status = self.check_bot_running()
        self.log(f"🚀 الحالة النهائية: {'✅ البوت يعمل' if final_status else '❌ البوت متوقف'}", 
                "SUCCESS" if final_status else "ERROR")
        
        # فحص آخر أخطاء
        final_errors = self.get_recent_errors()
        if final_errors:
            self.log(f"⚠️ أخطاء في النهاية: {len(final_errors)}", "WARNING")
            for error_type, error_msg in final_errors[-3:]:
                self.log(f"  [{error_type}] {error_msg[:60]}...", "ERROR")
        else:
            self.log("✅ لا توجد أخطاء في النهاية", "SUCCESS")
        
        self.log("=" * 50, "INFO")

if __name__ == "__main__":
    monitor = BotMonitor10Min()
    monitor.run_monitoring()