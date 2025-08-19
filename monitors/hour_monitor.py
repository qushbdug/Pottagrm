#!/usr/bin/env python3
"""
مراقب البوت لمدة ساعة كاملة - ضمان عدم التوقف
"""

import time
import subprocess
import os
import sqlite3
from datetime import datetime, timedelta

class HourMonitor:
    def __init__(self):
        self.start_time = datetime.now()
        self.end_time = self.start_time + timedelta(hours=1)
        self.errors_found = []
        self.restarts_count = 0
        self.check_count = 0
        
    def log(self, message, level="INFO"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        symbols = {"INFO": "ℹ️", "SUCCESS": "✅", "WARNING": "⚠️", "ERROR": "❌", "FIX": "🔧"}
        print(f"[{timestamp}] {symbols.get(level, 'ℹ️')} {message}")
    
    def ensure_bot_running(self):
        """ضمان تشغيل البوت"""
        try:
            result = subprocess.run(['pgrep', '-f', 'python.*main.py'], capture_output=True, text=True)
            is_running = len(result.stdout.strip()) > 0
            
            if not is_running:
                self.log("البوت متوقف - إعادة التشغيل فوراً...", "WARNING")
                return self.restart_bot()
            
            return True
        except Exception as e:
            self.log(f"خطأ في فحص البوت: {e}", "ERROR")
            return False
    
    def restart_bot(self):
        """إعادة تشغيل البوت"""
        try:
            self.restarts_count += 1
            self.log(f"إعادة تشغيل #{self.restarts_count}...", "FIX")
            
            # إيقاف أي عمليات قديمة
            subprocess.run(['pkill', '-f', 'python.*main.py'], capture_output=True)
            time.sleep(3)
            
            # تشغيل البوت الجديد
            log_file = f"bot_hour_{self.restarts_count}.log"
            with open(log_file, 'w') as f:
                subprocess.Popen(['python3', 'main.py'], stdout=f, stderr=subprocess.STDOUT)
            
            time.sleep(5)  # انتظار التشغيل
            
            # التحقق من نجاح التشغيل
            result = subprocess.run(['pgrep', '-f', 'python.*main.py'], capture_output=True, text=True)
            if result.stdout.strip():
                self.log(f"✅ تم إعادة التشغيل بنجاح (PID: {result.stdout.strip()})", "SUCCESS")
                return True
            else:
                self.log("❌ فشل في إعادة التشغيل", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"خطأ في إعادة التشغيل: {e}", "ERROR")
            return False
    
    def check_for_errors(self):
        """فحص الأخطاء الحديثة"""
        errors = []
        try:
            # فحص جميع ملفات السجل
            log_files = ['bot_hour_1.log', 'bot_hour_2.log', 'bot_hour_3.log', 'test_bot.log']
            
            for log_file in log_files:
                if os.path.exists(log_file):
                    with open(log_file, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                    
                    # فحص آخر 20 سطر
                    recent_lines = lines[-20:] if len(lines) > 20 else lines
                    
                    for line in recent_lines:
                        if any(word in line.lower() for word in ['error', 'exception', 'failed']):
                            errors.append(line.strip())
        except:
            pass
        
        return errors
    
    def fix_database_if_needed(self):
        """إصلاح قاعدة البيانات عند الحاجة"""
        try:
            conn = sqlite3.connect('yemen_net.db', timeout=10.0)
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
            conn.execute("PRAGMA busy_timeout=30000;")
            conn.close()
            return True
        except Exception as e:
            self.log(f"خطأ في إصلاح قاعدة البيانات: {e}", "ERROR")
            return False
    
    def monitoring_cycle(self):
        """دورة مراقبة واحدة"""
        self.check_count += 1
        elapsed = (datetime.now() - self.start_time).total_seconds() / 60
        remaining = 60 - elapsed
        
        # فحص حالة البوت
        bot_running = self.ensure_bot_running()
        
        # فحص الأخطاء
        recent_errors = self.check_for_errors()
        
        # تقرير حالة
        status = "✅ يعمل" if bot_running else "❌ متوقف"
        error_status = f"⚠️ {len(recent_errors)} أخطاء" if recent_errors else "✅ بدون أخطاء"
        
        self.log(f"فحص #{self.check_count} | البوت: {status} | {error_status} | المدة: {elapsed:.1f}د | المتبقي: {remaining:.1f}د")
        
        # معالجة الأخطاء
        if recent_errors:
            self.errors_found.extend(recent_errors)
            
            # إصلاح قاعدة البيانات إذا لزم الأمر
            if any('database' in err.lower() for err in recent_errors):
                self.fix_database_if_needed()
        
        # تقرير كل 10 دقائق
        if self.check_count % 20 == 0:  # كل 10 دقائق تقريباً
            self.print_progress_report(elapsed)
    
    def print_progress_report(self, elapsed):
        """تقرير التقدم"""
        self.log("=" * 40, "INFO")
        self.log(f"📊 تقرير التقدم - {elapsed:.1f} دقيقة", "INFO")
        self.log(f"🔍 الفحوصات: {self.check_count}", "INFO")
        self.log(f"⚠️ الأخطاء: {len(self.errors_found)}", "INFO")
        self.log(f"🔄 إعادة التشغيل: {self.restarts_count}", "INFO")
        self.log(f"🚀 البوت: {'يعمل' if self.ensure_bot_running() else 'متوقف'}", "INFO")
        self.log("=" * 40, "INFO")
    
    def run_hour_monitoring(self):
        """مراقبة لمدة ساعة كاملة"""
        self.log("🚀 بدء مراقبة البوت لمدة ساعة كاملة")
        self.log(f"⏰ من {self.start_time.strftime('%H:%M:%S')} إلى {self.end_time.strftime('%H:%M:%S')}")
        
        # التأكد من تشغيل البوت في البداية
        if not self.ensure_bot_running():
            self.log("البوت لا يعمل - تشغيل أولي...", "WARNING")
            self.restart_bot()
        
        try:
            while datetime.now() < self.end_time:
                self.monitoring_cycle()
                time.sleep(30)  # فحص كل 30 ثانية
        
        except KeyboardInterrupt:
            self.log("تم إيقاف المراقبة يدوياً", "WARNING")
        
        self.print_final_report()
    
    def print_final_report(self):
        """التقرير النهائي"""
        actual_duration = (datetime.now() - self.start_time).total_seconds() / 60
        
        self.log("🎉 انتهت مراقبة الساعة!", "SUCCESS")
        self.log("=" * 50, "INFO")
        self.log("📋 التقرير النهائي", "INFO")
        self.log("=" * 50, "INFO")
        
        self.log(f"⏱️ المدة الفعلية: {actual_duration:.1f} دقيقة", "INFO")
        self.log(f"🔍 إجمالي الفحوصات: {self.check_count}", "INFO")
        self.log(f"⚠️ إجمالي الأخطاء: {len(self.errors_found)}", "INFO")
        self.log(f"🔄 إعادة التشغيل: {self.restarts_count}", "INFO")
        
        # الحالة النهائية
        final_status = self.ensure_bot_running()
        self.log(f"🚀 الحالة النهائية: {'✅ البوت يعمل' if final_status else '❌ البوت متوقف'}", 
                "SUCCESS" if final_status else "ERROR")
        
        # ملخص الأخطاء
        if self.errors_found:
            error_types = {}
            for error in self.errors_found:
                if 'database' in error.lower():
                    error_types['قاعدة البيانات'] = error_types.get('قاعدة البيانات', 0) + 1
                elif 'not defined' in error.lower():
                    error_types['متغير غير معرف'] = error_types.get('متغير غير معرف', 0) + 1
                elif 'connection' in error.lower():
                    error_types['اتصال'] = error_types.get('اتصال', 0) + 1
                else:
                    error_types['عام'] = error_types.get('عام', 0) + 1
            
            self.log("📊 تصنيف الأخطاء:", "INFO")
            for error_type, count in error_types.items():
                self.log(f"  • {error_type}: {count} مرة", "WARNING")
        
        self.log("=" * 50, "INFO")
        
        # تقييم الأداء
        if self.restarts_count == 0:
            self.log("🏆 أداء ممتاز - لم يحتج البوت لإعادة تشغيل!", "SUCCESS")
        elif self.restarts_count <= 2:
            self.log("👍 أداء جيد - إعادة تشغيل قليلة", "SUCCESS")
        else:
            self.log("⚠️ يحتاج تحسين - إعادة تشغيل كثيرة", "WARNING")

if __name__ == "__main__":
    monitor = HourMonitor()
    monitor.run_hour_monitoring()