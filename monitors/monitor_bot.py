#!/usr/bin/env python3
import time
import subprocess
import os
import datetime
import sys

def log_with_time(message):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")
    with open("monitor.log", "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {message}\n")

def check_bot_status():
    try:
        result = subprocess.run(['pgrep', '-f', 'python3 main.py'], 
                              capture_output=True, text=True)
        return bool(result.stdout.strip())
    except:
        return False

def start_bot():
    try:
        subprocess.Popen(['nohup', 'python3', 'main.py'], 
                        stdout=open('bot.log', 'a'), 
                        stderr=subprocess.STDOUT)
        log_with_time("✅ تم تشغيل البوت")
        return True
    except Exception as e:
        log_with_time(f"❌ فشل في تشغيل البوت: {e}")
        return False

def check_errors():
    try:
        with open("bot.log", "r", encoding="utf-8") as f:
            lines = f.readlines()
            recent_lines = lines[-50:]  # آخر 50 سطر
            errors = [line for line in recent_lines if "ERROR" in line]
            return errors
    except:
        return []

def monitor_bot():
    log_with_time("🚀 بدء مراقبة البوت لمدة 24 ساعة")
    start_time = time.time()
    error_count = 0
    restart_count = 0
    
    while True:
        current_time = time.time()
        elapsed_hours = (current_time - start_time) / 3600
        
        # إنهاء المراقبة بعد 24 ساعة
        if elapsed_hours >= 24:
            log_with_time("✅ انتهت مراقبة 24 ساعة بنجاح")
            break
        
        # فحص حالة البوت
        if not check_bot_status():
            log_with_time("⚠️ البوت متوقف! إعادة تشغيل...")
            if start_bot():
                restart_count += 1
                time.sleep(10)  # انتظار التشغيل
        
        # فحص الأخطاء
        errors = check_errors()
        if errors:
            new_errors = len(errors)
            if new_errors > error_count:
                log_with_time(f"❌ تم اكتشاف {new_errors - error_count} أخطاء جديدة")
                for error in errors[error_count:]:
                    log_with_time(f"خطأ: {error.strip()}")
                error_count = new_errors
        
        # تقرير دوري كل ساعة
        if int(elapsed_hours) > 0 and int(elapsed_hours * 60) % 60 == 0:
            log_with_time(f"📊 تقرير الساعة {int(elapsed_hours)}: أخطاء={error_count}, إعادة تشغيل={restart_count}")
        
        time.sleep(60)  # فحص كل دقيقة

if __name__ == "__main__":
    monitor_bot()
