#!/usr/bin/env python3
"""
مراقب سريع للبوت - يعمل لمدة ساعة
"""
import time
import subprocess
import os
from datetime import datetime, timedelta

def check_bot_status():
    try:
        result = subprocess.run(['pgrep', '-f', 'python.*main.py'], capture_output=True, text=True)
        return len(result.stdout.strip()) > 0
    except:
        return False

def check_recent_errors():
    try:
        if os.path.exists('test_bot.log'):
            with open('test_bot.log', 'r') as f:
                lines = f.readlines()
            recent = lines[-20:] if len(lines) > 20 else lines
            errors = [line for line in recent if any(word in line.lower() for word in ['error', 'exception', 'failed'])]
            return len(errors)
    except:
        return 0

def main():
    start_time = datetime.now()
    end_time = start_time + timedelta(hours=1)
    check_count = 0
    total_errors = 0
    
    print(f"🚀 بدء المراقبة السريعة من {start_time.strftime('%H:%M:%S')}")
    print(f"⏰ ستنتهي في {end_time.strftime('%H:%M:%S')}")
    
    while datetime.now() < end_time:
        check_count += 1
        current_time = datetime.now()
        elapsed = (current_time - start_time).total_seconds() / 60
        
        # فحص البوت
        bot_running = check_bot_status()
        recent_errors = check_recent_errors()
        total_errors += recent_errors
        
        status = "✅ يعمل" if bot_running else "❌ متوقف"
        error_status = f"⚠️ {recent_errors} أخطاء حديثة" if recent_errors > 0 else "✅ لا أخطاء"
        
        print(f"[{current_time.strftime('%H:%M:%S')}] فحص #{check_count} | البوت: {status} | {error_status} | المدة: {elapsed:.1f}د")
        
        # تقرير كل 15 دقيقة
        if check_count % 30 == 0:  # كل 15 دقيقة تقريباً (30 فحص × 30 ثانية)
            print(f"\n📊 تقرير منتصف المدة:")
            print(f"   ⏱️ المدة المنقضية: {elapsed:.1f} دقيقة")
            print(f"   🔍 عدد الفحوصات: {check_count}")
            print(f"   ⚠️ إجمالي الأخطاء: {total_errors}")
            print(f"   🚀 حالة البوت: {'يعمل بنجاح' if bot_running else 'متوقف'}\n")
        
        time.sleep(30)  # فحص كل 30 ثانية
    
    # التقرير النهائي
    final_elapsed = (datetime.now() - start_time).total_seconds() / 60
    print(f"\n🎉 انتهت المراقبة!")
    print(f"📊 التقرير النهائي:")
    print(f"   ⏱️ إجمالي المدة: {final_elapsed:.1f} دقيقة")
    print(f"   🔍 إجمالي الفحوصات: {check_count}")
    print(f"   ⚠️ إجمالي الأخطاء المكتشفة: {total_errors}")
    print(f"   🚀 الحالة النهائية: {'✅ البوت يعمل' if check_bot_status() else '❌ البوت متوقف'}")

if __name__ == "__main__":
    main()