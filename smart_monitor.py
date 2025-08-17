#!/usr/bin/env python3
import time
import subprocess
import os
import datetime
import requests
import json

class BotMonitor:
    def __init__(self):
        self.start_time = time.time()
        self.error_count = 0
        self.restart_count = 0
        self.last_check = time.time()
        self.bot_token = "7766964799:AAHex-hGfjPX6g_R2aZ7-UPrgnFxQKAjSa0"
        
    def log(self, message):
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_msg = f"[{timestamp}] {message}"
        print(log_msg)
        with open("smart_monitor.log", "a", encoding="utf-8") as f:
            f.write(log_msg + "\n")
    
    def is_bot_running(self):
        try:
            result = subprocess.run(['pgrep', '-f', 'python3 main.py'], 
                                  capture_output=True, text=True)
            return bool(result.stdout.strip())
        except:
            return False
    
    def is_bot_responsive(self):
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/getMe"
            response = requests.get(url, timeout=10)
            return response.status_code == 200
        except:
            return False
    
    def check_recent_errors(self):
        try:
            with open("bot.log", "r", encoding="utf-8") as f:
                lines = f.readlines()
                recent_lines = lines[-20:]
                errors = [line for line in recent_lines if "ERROR" in line.upper()]
                return errors
        except:
            return []
    
    def get_bot_stats(self):
        try:
            result = subprocess.run(['ps', '-o', 'pid,etime,rss,cpu', '-p', 
                                   subprocess.check_output(['pgrep', '-f', 'python3 main.py']).decode().strip()], 
                                  capture_output=True, text=True)
            return result.stdout.strip()
        except:
            return "غير متاح"
    
    def restart_bot(self):
        self.log("⚠️ إعادة تشغيل البوت...")
        try:
            subprocess.run(['pkill', '-f', 'python3 main.py'])
            time.sleep(3)
            subprocess.Popen(['nohup', 'python3', 'main.py'], 
                           stdout=open('bot.log', 'a'), 
                           stderr=subprocess.STDOUT)
            self.restart_count += 1
            self.log("✅ تم إعادة تشغيل البوت")
            return True
        except Exception as e:
            self.log(f"❌ فشل في إعادة التشغيل: {e}")
            return False
    
    def generate_hourly_report(self, hours_elapsed):
        stats = self.get_bot_stats()
        errors = self.check_recent_errors()
        
        report = f"""
📊 === تقرير الساعة {int(hours_elapsed)} ===
🕐 وقت التشغيل: {hours_elapsed:.1f} ساعة
🔄 إعادة التشغيل: {self.restart_count} مرة
❌ الأخطاء المكتشفة: {len(errors)}
📈 إحصائيات العملية: {stats.split()[1] if stats != 'غير متاح' else 'غير متاح'}
🌐 حالة الاتصال: {"✅ متصل" if self.is_bot_responsive() else "❌ منقطع"}
"""
        self.log(report)
    
    def monitor(self):
        self.log("🚀 بدء المراقبة الذكية للبوت (24 ساعة)")
        
        while True:
            current_time = time.time()
            hours_elapsed = (current_time - self.start_time) / 3600
            
            # إنهاء بعد 24 ساعة
            if hours_elapsed >= 24:
                self.log("✅ انتهت مراقبة 24 ساعة بنجاح")
                self.log(f"📊 إحصائيات نهائية: إعادة تشغيل={self.restart_count}, أخطاء={self.error_count}")
                break
            
            # فحص حالة البوت
            if not self.is_bot_running():
                self.log("❌ البوت متوقف!")
                if self.restart_bot():
                    time.sleep(15)  # انتظار أطول بعد إعادة التشغيل
                else:
                    self.log("💀 فشل في إعادة تشغيل البوت - انتظار 5 دقائق")
                    time.sleep(300)
                    continue
            
            # فحص الاستجابة
            elif not self.is_bot_responsive():
                self.log("⚠️ البوت لا يستجيب لـ Telegram API")
                if self.restart_bot():
                    time.sleep(15)
                else:
                    time.sleep(300)
                    continue
            
            # فحص الأخطاء الجديدة
            errors = self.check_recent_errors()
            if len(errors) > self.error_count:
                new_errors = len(errors) - self.error_count
                self.log(f"🔍 اكتشاف {new_errors} أخطاء جديدة")
                for error in errors[self.error_count:]:
                    self.log(f"خطأ: {error.strip()}")
                self.error_count = len(errors)
            
            # تقرير كل ساعة
            if int(hours_elapsed) > 0 and (current_time - self.last_check) >= 3600:
                self.generate_hourly_report(hours_elapsed)
                self.last_check = current_time
            
            # انتظار دقيقة واحدة
            time.sleep(60)

if __name__ == "__main__":
    monitor = BotMonitor()
    monitor.monitor()
