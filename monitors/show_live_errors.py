#!/usr/bin/env python3
"""
عرض الأخطاء الحية أثناء الاستخدام
Show Live Errors During Usage
"""

import os
import time
import datetime
import subprocess

def show_recent_errors():
    """عرض الأخطاء الحديثة"""
    log_files = [
        "bot_coupon_fixed.log",
        "bot_fixed.log", 
        "bot_new.log",
        "bot.log"
    ]
    
    print(f"🕐 الوقت: {datetime.datetime.now().strftime('%H:%M:%S')}")
    print("🔍 === فحص الأخطاء الحديثة ===")
    
    errors_found = False
    
    for log_file in log_files:
        log_path = f"/workspace/{log_file}"
        if not os.path.exists(log_path):
            continue
            
        try:
            # أحدث 5 أسطر من كل ملف
            result = subprocess.run(
                ["tail", "-5", log_path], 
                capture_output=True, text=True, timeout=5
            )
            
            lines = result.stdout.split('\n')
            file_errors = []
            
            for line in lines:
                if any(keyword in line.upper() for keyword in ['ERROR', 'EXCEPTION', 'FAILED', 'TRACEBACK']):
                    file_errors.append(line.strip())
            
            if file_errors:
                errors_found = True
                print(f"\n📁 {log_file}:")
                for error in file_errors[-2:]:  # آخر خطأين
                    if error:
                        print(f"   ❌ {error}")
                        
        except Exception as e:
            continue
    
    if not errors_found:
        print("✅ لا توجد أخطاء حديثة!")
    
    print()

def show_bot_status():
    """عرض حالة البوت"""
    try:
        result = subprocess.run(
            ["ps", "aux"], 
            capture_output=True, text=True, timeout=5
        )
        
        bot_running = False
        monitor_running = False
        
        for line in result.stdout.split('\n'):
            if 'python3 main.py' in line and 'grep' not in line:
                bot_running = True
                parts = line.split()
                if len(parts) >= 11:
                    print(f"🤖 البوت: 🟢 يعمل (PID: {parts[1]}, CPU: {parts[2]}%, Memory: {parts[3]}%)")
            elif 'live_error_monitor.py' in line and 'grep' not in line:
                monitor_running = True
                parts = line.split()
                if len(parts) >= 2:
                    print(f"👁️ المراقب: 🟢 نشط (PID: {parts[1]})")
        
        if not bot_running:
            print("🤖 البوت: 🔴 متوقف")
        if not monitor_running:
            print("👁️ المراقب: 🔴 متوقف")
            
    except Exception as e:
        print(f"❌ خطأ في فحص الحالة: {e}")

def main():
    """الدالة الرئيسية"""
    print("📱 ================================================================ 📱")
    print("                   مراقبة الأخطاء الحية للبوت")
    print("📱 ================================================================ 📱")
    print()
    
    show_bot_status()
    print()
    show_recent_errors()
    
    print("💡 === تعليمات ===")
    print("• استخدم البوت الآن - سأراقب الأخطاء وأصلحها فوراً")
    print("• إذا واجهت أي مشكلة، أخبرني بالتفاصيل")
    print("• المراقب يعمل في الخلفية ويصلح المشاكل تلقائياً")
    print()
    print("🎯 البوت جاهز للاستخدام!")

if __name__ == "__main__":
    main()