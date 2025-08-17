#!/usr/bin/env python3
import time
import subprocess
import os
import requests
from datetime import datetime

def clear_screen():
    os.system('clear' if os.name == 'posix' else 'cls')

def get_process_info(process_name):
    try:
        result = subprocess.run(['pgrep', '-f', process_name], 
                              capture_output=True, text=True)
        if result.stdout.strip():
            pid = result.stdout.strip().split('\n')[0]
            stats = subprocess.run(['ps', '-o', 'pid,etime,rss,cpu', '-p', pid], 
                                 capture_output=True, text=True)
            return stats.stdout.strip().split('\n')[1] if len(stats.stdout.strip().split('\n')) > 1 else "غير متاح"
        return None
    except:
        return None

def check_bot_api():
    try:
        response = requests.get("https://api.telegram.org/bot7766964799:AAHex-hGfjPX6g_R2aZ7-UPrgnFxQKAjSa0/getMe", timeout=5)
        return "✅ متصل" if response.status_code == 200 else "❌ خطأ"
    except:
        return "❌ غير متاح"

def get_file_size(filename):
    try:
        return round(os.path.getsize(filename) / (1024*1024), 2) if os.path.exists(filename) else 0
    except:
        return 0

def count_errors():
    try:
        with open("bot.log", "r") as f:
            return sum(1 for line in f if "ERROR" in line.upper())
    except:
        return 0

def get_last_activity():
    try:
        with open("bot.log", "r") as f:
            lines = f.readlines()
            if lines:
                last_line = lines[-1]
                if "HTTP Request" in last_line:
                    return last_line.split()[0] + " " + last_line.split()[1]
        return "غير معروف"
    except:
        return "غير معروف"

def display_dashboard():
    clear_screen()
    
    print("🎛️" + "="*60 + "🎛️")
    print("         لوحة تحكم البوت المتقدمة - مراقبة 24 ساعة")
    print("🎛️" + "="*60 + "🎛️")
    print()
    
    # معلومات البوت الرئيسي
    bot_info = get_process_info("python3 main.py")
    print("🤖 حالة البوت الرئيسي:")
    if bot_info:
        parts = bot_info.split()
        print(f"   ✅ يعمل - PID: {parts[0]} | وقت التشغيل: {parts[1]} | ذاكرة: {round(int(parts[2])/1024, 1)} MB | CPU: {parts[3]}%")
    else:
        print("   ❌ متوقف")
    
    # معلومات نظام المراقبة
    monitor_info = get_process_info("smart_monitor.py")
    print("\n🔍 نظام المراقبة الذكي:")
    if monitor_info:
        parts = monitor_info.split()
        print(f"   ✅ يعمل - PID: {parts[0]} | وقت التشغيل: {parts[1]} | ذاكرة: {round(int(parts[2])/1024, 1)} MB")
    else:
        print("   ❌ متوقف")
    
    # معلومات نظام التحديث
    update_info = get_process_info("auto_update.py")
    print("\n🔧 نظام التحديث التلقائي:")
    if update_info:
        parts = update_info.split()
        print(f"   ✅ يعمل - PID: {parts[0]} | وقت التشغيل: {parts[1]} | ذاكرة: {round(int(parts[2])/1024, 1)} MB")
    else:
        print("   ❌ متوقف")
    
    print("\n" + "-"*60)
    
    # إحصائيات الأداء
    print("📊 إحصائيات الأداء:")
    api_status = check_bot_api()
    error_count = count_errors()
    bot_log_size = get_file_size("bot.log")
    monitor_log_size = get_file_size("smart_monitor.log")
    last_activity = get_last_activity()
    
    print(f"   🌐 حالة API: {api_status}")
    print(f"   ❌ عدد الأخطاء: {error_count}")
    print(f"   📁 حجم سجل البوت: {bot_log_size} MB")
    print(f"   📁 حجم سجل المراقبة: {monitor_log_size} MB")
    print(f"   ⏰ آخر نشاط: {last_activity}")
    
    print("\n" + "-"*60)
    
    # سجلات حية
    print("📋 آخر السجلات:")
    try:
        with open("bot.log", "r") as f:
            lines = f.readlines()
            for line in lines[-3:]:
                if line.strip():
                    print(f"   {line.strip()[:80]}...")
    except:
        print("   لا توجد سجلات متاحة")
    
    print("\n🎛️" + "="*60 + "🎛️")
    print(f"         آخر تحديث: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("🎛️" + "="*60 + "🎛️")

def main():
    print("🚀 بدء لوحة التحكم المباشرة...")
    print("اضغط Ctrl+C للخروج")
    
    try:
        while True:
            display_dashboard()
            time.sleep(30)  # تحديث كل 30 ثانية
    except KeyboardInterrupt:
        print("\n👋 تم إغلاق لوحة التحكم")

if __name__ == "__main__":
    main()
