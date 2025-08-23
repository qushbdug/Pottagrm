#!/usr/bin/env python3
"""
مراقبة سريعة لحالة البوت
Quick Bot Status Monitor
"""

import os
import sys
import time
import subprocess
import datetime
import psutil
import requests

def get_bot_process():
    """البحث عن عملية البوت"""
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if proc.info['cmdline'] and any('main.py' in arg for arg in proc.info['cmdline']):
                return proc
        except:
            continue
    return None

def check_telegram_connection():
    """فحص الاتصال بـ Telegram"""
    try:
        response = requests.get(
            "https://api.telegram.org/bot7766964799:AAHex-hGfjPX6g_R2aZ7-UPrgnFxQKAjSa0/getMe",
            timeout=5
        )
        return response.status_code == 200
    except:
        return False

def get_db_size():
    """حجم قاعدة البيانات"""
    try:
        if os.path.exists('/workspace/yemen_net.db'):
            return os.path.getsize('/workspace/yemen_net.db') / (1024*1024)
    except:
        pass
    return 0

def count_recent_errors():
    """عدد الأخطاء الحديثة"""
    try:
        log_files = ['bot_fixed.log', 'bot_new.log', 'bot.log']
        for log_file in log_files:
            if os.path.exists(f'/workspace/{log_file}'):
                with open(f'/workspace/{log_file}', 'r') as f:
                    lines = f.readlines()
                    recent_errors = [line for line in lines[-100:] if 'ERROR' in line]
                    return len(recent_errors)
    except:
        pass
    return 0

def main():
    """عرض حالة البوت"""
    print("🔍 ═══════════════════════════════════════ 🔍")
    print("             فحص سريع لحالة البوت")
    print("🔍 ═══════════════════════════════════════ 🔍")
    print(f"⏰ الوقت: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # فحص عملية البوت
    bot_proc = get_bot_process()
    if bot_proc:
        try:
            cpu = bot_proc.cpu_percent()
            memory = bot_proc.memory_info().rss / (1024*1024)
            create_time = datetime.datetime.fromtimestamp(bot_proc.create_time())
            uptime = datetime.datetime.now() - create_time
            
            print("🚀 === حالة البوت ===")
            print(f"🟢 الحالة: يعمل بنجاح")
            print(f"🔢 PID: {bot_proc.pid}")
            print(f"🧮 استهلاك المعالج: {cpu:.1f}%")
            print(f"💾 استهلاك الذاكرة: {memory:.1f} MB")
            print(f"⏰ وقت التشغيل: {str(uptime).split('.')[0]}")
        except Exception as e:
            print("🟡 === حالة البوت ===")
            print(f"🟡 الحالة: يعمل مع مشاكل")
            print(f"❌ خطأ في القراءة: {e}")
    else:
        print("🚀 === حالة البوت ===")
        print("🔴 الحالة: متوقف")
        print("❌ لم يتم العثور على عملية البوت")
    
    print()
    
    # فحص الاتصال
    telegram_connected = check_telegram_connection()
    print("🌐 === حالة الاتصال ===")
    print(f"📡 Telegram API: {'✅ متصل' if telegram_connected else '❌ منقطع'}")
    
    # فحص قاعدة البيانات
    db_size = get_db_size()
    print(f"📊 حجم قاعدة البيانات: {db_size:.2f} MB")
    
    # فحص الأخطاء
    error_count = count_recent_errors()
    print(f"❌ أخطاء حديثة: {error_count}")
    
    print()
    
    # فحص نظام المراقبة
    monitor_running = False
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if proc.info['cmdline'] and any('advanced_monitor.py' in arg for arg in proc.info['cmdline']):
                monitor_running = True
                break
        except:
            continue
    
    print("🔧 === حالة نظام المراقبة ===")
    print(f"👁️ نظام المراقبة: {'🟢 يعمل' if monitor_running else '🔴 متوقف'}")
    
    # فحص ملفات التقارير
    report_files = [f for f in os.listdir('/workspace') if f.startswith('status_report_')]
    if report_files:
        latest_report = max(report_files)
        print(f"📋 آخر تقرير: {latest_report}")
    
    print()
    print("🎯 === التقييم العام ===")
    
    if bot_proc and telegram_connected and error_count == 0:
        print("🟢 **ممتاز:** جميع الأنظمة تعمل بحالة مثالية")
    elif bot_proc and telegram_connected:
        print("🟡 **جيد:** البوت يعمل مع بعض التحذيرات")
    elif bot_proc:
        print("🟠 **متوسط:** البوت يعمل لكن هناك مشاكل")
    else:
        print("🔴 **سيء:** البوت متوقف")
    
    print("🔍 ═══════════════════════════════════════ 🔍")

if __name__ == "__main__":
    main()