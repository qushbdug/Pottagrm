#!/usr/bin/env python3
"""
فحص سريع لحالة البوت
Quick Bot Status Checker
"""

import subprocess
import psutil
import sqlite3
from datetime import datetime
import json

def check_bot_status():
    """فحص حالة البوت"""
    print("🔍 **فحص حالة البوت** 🔍")
    print("=" * 50)
    
    # فحص العمليات
    bot_processes = []
    monitor_processes = []
    
    for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'memory_percent', 'cpu_percent']):
        try:
            cmdline = proc.info['cmdline']
            if cmdline and len(cmdline) >= 2:
                if 'python' in cmdline[0]:
                    if 'main.py' in cmdline[1]:
                        bot_processes.append(proc.info)
                    elif 'monitor' in cmdline[1] or 'auto_restart' in cmdline[1]:
                        monitor_processes.append(proc.info)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    
    # عرض حالة البوت
    print("🤖 **حالة البوت الأساسي:**")
    if bot_processes:
        for proc in bot_processes:
            print(f"  ✅ يعمل - PID: {proc['pid']}")
            print(f"     💾 الذاكرة: {proc['memory_percent']:.1f}%")
            print(f"     🖥️ المعالج: {proc['cpu_percent']:.1f}%")
    else:
        print("  ❌ البوت متوقف")
    
    print("\n🛡️ **أنظمة المراقبة:**")
    if monitor_processes:
        for proc in monitor_processes:
            script_name = proc['cmdline'][1].split('/')[-1] if '/' in proc['cmdline'][1] else proc['cmdline'][1]
            print(f"  ✅ {script_name} - PID: {proc['pid']}")
    else:
        print("  ⚠️ لا توجد أنظمة مراقبة نشطة")
    
    # فحص قاعدة البيانات
    print("\n🗄️ **حالة قاعدة البيانات:**")
    try:
        conn = sqlite3.connect('/workspace/yemen_net.db', timeout=5)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM users")
        users = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM transactions WHERE DATE(created_at) = DATE('now')")
        today_transactions = cursor.fetchone()[0]
        
        print(f"  ✅ متصلة - المستخدمون: {users}, معاملات اليوم: {today_transactions}")
        
        conn.close()
    except Exception as e:
        print(f"  ❌ خطأ في قاعدة البيانات: {e}")
    
    # فحص الملفات المهمة
    print("\n📁 **الملفات المهمة:**")
    important_files = [
        '/workspace/main.py',
        '/workspace/yemen_net.db',
        '/workspace/monitor_24h.log',
        '/workspace/auto_restart.log'
    ]
    
    for file_path in important_files:
        try:
            import os
            if os.path.exists(file_path):
                size = os.path.getsize(file_path)
                print(f"  ✅ {file_path.split('/')[-1]} - {size} بايت")
            else:
                print(f"  ❌ {file_path.split('/')[-1]} - غير موجود")
        except Exception as e:
            print(f"  ⚠️ {file_path.split('/')[-1]} - خطأ: {e}")
    
    print("\n" + "=" * 50)
    print(f"⏰ **وقت الفحص:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    check_bot_status()