#!/usr/bin/env python3
"""
نظام مراقبة مكثف للبوت لمدة ساعة
يفحص الأخطاء ويصلحها تلقائياً
"""

import time
import subprocess
import os
import sqlite3
import re
from datetime import datetime, timedelta

class IntensiveMonitor:
    def __init__(self):
        self.start_time = datetime.now()
        self.errors_found = []
        self.fixes_applied = []
        self.check_count = 0
        self.last_error_count = 0
        
    def log_message(self, message, level="INFO"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        prefix = {
            "INFO": "ℹ️",
            "SUCCESS": "✅", 
            "WARNING": "⚠️",
            "ERROR": "❌",
            "FIX": "🔧"
        }.get(level, "ℹ️")
        
        print(f"[{timestamp}] {prefix} {message}")
        
    def check_bot_running(self):
        """فحص إذا كان البوت يعمل"""
        try:
            result = subprocess.run(['pgrep', '-f', 'python.*main.py'], 
                                  capture_output=True, text=True)
            pids = result.stdout.strip().split('\n') if result.stdout.strip() else []
            return len([p for p in pids if p]) > 0
        except:
            return False
    
    def get_bot_pid(self):
        """الحصول على معرف عملية البوت"""
        try:
            result = subprocess.run(['pgrep', '-f', 'python.*main.py'], 
                                  capture_output=True, text=True)
            pids = result.stdout.strip().split('\n')
            return pids[0] if pids and pids[0] else None
        except:
            return None
    
    def analyze_log_errors(self):
        """تحليل أخطاء السجل"""
        errors = []
        warnings = []
        
        try:
            if os.path.exists('test_bot.log'):
                with open('test_bot.log', 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                # فحص آخر 100 سطر
                recent_lines = lines[-100:] if len(lines) > 100 else lines
                
                for line in recent_lines:
                    line_lower = line.lower()
                    
                    # أخطاء حرجة
                    if any(word in line_lower for word in ['error', 'exception', 'traceback', 'failed', 'crash']):
                        if 'database is locked' in line_lower:
                            errors.append(('DATABASE_LOCK', line.strip()))
                        elif 'connection' in line_lower and 'error' in line_lower:
                            errors.append(('CONNECTION_ERROR', line.strip()))
                        elif 'import' in line_lower and 'error' in line_lower:
                            errors.append(('IMPORT_ERROR', line.strip()))
                        else:
                            errors.append(('GENERAL_ERROR', line.strip()))
                    
                    # تحذيرات
                    elif 'warning' in line_lower:
                        warnings.append(line.strip())
        
        except Exception as e:
            errors.append(('LOG_READ_ERROR', str(e)))
        
        return errors, warnings
    
    def fix_database_issues(self):
        """إصلاح مشاكل قاعدة البيانات"""
        try:
            self.log_message("إصلاح مشاكل قاعدة البيانات...", "FIX")
            
            # إعدادات SQLite محسنة
            conn = sqlite3.connect('yemen_net.db', timeout=30.0)
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
            conn.execute("PRAGMA busy_timeout=30000;")
            conn.execute("PRAGMA cache_size=10000;")
            conn.execute("PRAGMA temp_store=MEMORY;")
            conn.close()
            
            self.fixes_applied.append("إصلاح قاعدة البيانات")
            self.log_message("تم إصلاح قاعدة البيانات", "SUCCESS")
            return True
            
        except Exception as e:
            self.log_message(f"فشل في إصلاح قاعدة البيانات: {e}", "ERROR")
            return False
    
    def restart_bot(self):
        """إعادة تشغيل البوت"""
        try:
            self.log_message("إعادة تشغيل البوت...", "FIX")
            
            # إيقاف البوت القديم
            subprocess.run(['pkill', '-f', 'python.*main.py'], capture_output=True)
            time.sleep(3)
            
            # تشغيل البوت الجديد
            with open('test_bot.log', 'a') as log_file:
                subprocess.Popen(['python3', 'main.py'], 
                               stdout=log_file, stderr=subprocess.STDOUT)
            
            time.sleep(5)  # انتظار التشغيل
            
            if self.check_bot_running():
                self.fixes_applied.append("إعادة تشغيل البوت")
                self.log_message("تم إعادة تشغيل البوت بنجاح", "SUCCESS")
                return True
            else:
                self.log_message("فشل في إعادة تشغيل البوت", "ERROR")
                return False
                
        except Exception as e:
            self.log_message(f"خطأ في إعادة التشغيل: {e}", "ERROR")
            return False
    
    def apply_fixes(self, errors):
        """تطبيق الإصلاحات حسب نوع الخطأ"""
        fixes_applied = 0
        
        error_types = [error[0] for error in errors]
        
        # إصلاح مشاكل قاعدة البيانات
        if 'DATABASE_LOCK' in error_types:
            if self.fix_database_issues():
                fixes_applied += 1
        
        # إعادة تشغيل للأخطاء الحرجة
        if any(error_type in ['CONNECTION_ERROR', 'IMPORT_ERROR'] for error_type in error_types):
            if self.restart_bot():
                fixes_applied += 1
        
        # إعادة تشغيل إذا كان البوت متوقف
        if not self.check_bot_running():
            if self.restart_bot():
                fixes_applied += 1
        
        return fixes_applied
    
    def monitoring_cycle(self):
        """دورة مراقبة واحدة"""
        self.check_count += 1
        elapsed_minutes = (datetime.now() - self.start_time).total_seconds() / 60
        
        self.log_message(f"فحص #{self.check_count} - المدة: {elapsed_minutes:.1f} دقيقة")
        
        # فحص حالة البوت
        is_running = self.check_bot_running()
        pid = self.get_bot_pid()
        
        if is_running:
            self.log_message(f"البوت يعمل (PID: {pid})", "SUCCESS")
        else:
            self.log_message("البوت متوقف!", "ERROR")
            self.restart_bot()
            return
        
        # تحليل الأخطاء
        errors, warnings = self.analyze_log_errors()
        
        if errors:
            self.log_message(f"وُجد {len(errors)} خطأ", "WARNING")
            for error_type, error_msg in errors[-3:]:  # آخر 3 أخطاء
                self.log_message(f"[{error_type}] {error_msg[:80]}...", "ERROR")
            
            # تطبيق الإصلاحات
            fixes = self.apply_fixes(errors)
            if fixes > 0:
                self.log_message(f"تم تطبيق {fixes} إصلاح", "FIX")
            
            self.errors_found.extend(errors)
        else:
            self.log_message("لا توجد أخطاء جديدة", "SUCCESS")
        
        if warnings:
            self.log_message(f"وُجد {len(warnings)} تحذير", "WARNING")
    
    def print_progress_report(self):
        """تقرير التقدم"""
        elapsed = (datetime.now() - self.start_time).total_seconds() / 60
        remaining = 60 - elapsed
        
        self.log_message("=" * 50, "INFO")
        self.log_message(f"📊 تقرير التقدم", "INFO")
        self.log_message(f"⏱️ المدة المنقضية: {elapsed:.1f} دقيقة", "INFO")
        self.log_message(f"⏳ المدة المتبقية: {remaining:.1f} دقيقة", "INFO")
        self.log_message(f"🔍 عدد الفحوصات: {self.check_count}", "INFO")
        self.log_message(f"⚠️ الأخطاء المكتشفة: {len(self.errors_found)}", "INFO")
        self.log_message(f"🔧 الإصلاحات المطبقة: {len(self.fixes_applied)}", "INFO")
        self.log_message(f"✅ حالة البوت: {'يعمل' if self.check_bot_running() else 'متوقف'}", "INFO")
        self.log_message("=" * 50, "INFO")
    
    def print_final_report(self):
        """التقرير النهائي"""
        elapsed = (datetime.now() - self.start_time).total_seconds() / 60
        
        self.log_message("🎉 انتهت المراقبة المكثفة!", "SUCCESS")
        self.log_message("=" * 60, "INFO")
        self.log_message("📋 التقرير النهائي", "INFO")
        self.log_message("=" * 60, "INFO")
        
        self.log_message(f"⏱️ إجمالي المدة: {elapsed:.1f} دقيقة", "INFO")
        self.log_message(f"🔍 إجمالي الفحوصات: {self.check_count}", "INFO")
        self.log_message(f"⚠️ إجمالي الأخطاء: {len(self.errors_found)}", "INFO")
        self.log_message(f"🔧 إجمالي الإصلاحات: {len(self.fixes_applied)}", "INFO")
        
        # الإصلاحات المطبقة
        if self.fixes_applied:
            self.log_message("🔧 الإصلاحات المطبقة:", "INFO")
            for i, fix in enumerate(self.fixes_applied, 1):
                self.log_message(f"  {i}. {fix}", "SUCCESS")
        
        # أنواع الأخطاء
        if self.errors_found:
            error_types = {}
            for error_type, _ in self.errors_found:
                error_types[error_type] = error_types.get(error_type, 0) + 1
            
            self.log_message("⚠️ أنواع الأخطاء المكتشفة:", "INFO")
            for error_type, count in error_types.items():
                self.log_message(f"  • {error_type}: {count} مرة", "WARNING")
        
        # الحالة النهائية
        final_status = self.check_bot_running()
        self.log_message(f"🚀 الحالة النهائية: {'✅ البوت يعمل بنجاح' if final_status else '❌ البوت متوقف'}", 
                        "SUCCESS" if final_status else "ERROR")
        
        self.log_message("=" * 60, "INFO")
    
    def run_intensive_monitoring(self):
        """تشغيل المراقبة المكثفة لمدة ساعة"""
        self.log_message("🚀 بدء المراقبة المكثفة للبوت لمدة ساعة", "INFO")
        self.log_message(f"⏰ وقت البدء: {self.start_time.strftime('%H:%M:%S')}", "INFO")
        
        end_time = self.start_time + timedelta(hours=1)
        next_report_time = self.start_time + timedelta(minutes=15)
        
        try:
            while datetime.now() < end_time:
                # دورة مراقبة
                self.monitoring_cycle()
                
                # تقرير تقدم كل 15 دقيقة
                if datetime.now() >= next_report_time:
                    self.print_progress_report()
                    next_report_time += timedelta(minutes=15)
                
                # انتظار 30 ثانية بين الفحوصات
                time.sleep(30)
        
        except KeyboardInterrupt:
            self.log_message("تم إيقاف المراقبة يدوياً", "WARNING")
        
        except Exception as e:
            self.log_message(f"خطأ في المراقبة: {e}", "ERROR")
        
        finally:
            self.print_final_report()

if __name__ == "__main__":
    monitor = IntensiveMonitor()
    monitor.run_intensive_monitoring()