#!/usr/bin/env python3
import os
import sys
import subprocess
import time
import datetime

def log_update(message):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open("updates.log", "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {message}\n")
    print(f"[{timestamp}] {message}")

def check_for_critical_errors():
    """فحص الأخطاء الحرجة التي تحتاج إصلاح فوري"""
    critical_errors = []
    try:
        with open("bot.log", "r", encoding="utf-8") as f:
            lines = f.readlines()
            recent_lines = lines[-50:]
            
            for line in recent_lines:
                if any(keyword in line.upper() for keyword in 
                       ["SQLITE3.OPERATIONALERROR", "NAMENOTDEFINEDERROR", 
                        "IMPORTERROR", "SYNTAXERROR", "INDENTATIONERROR"]):
                    critical_errors.append(line.strip())
    except:
        pass
    
    return critical_errors

def apply_fixes():
    """تطبيق إصلاحات معروفة للأخطاء الشائعة"""
    fixes_applied = []
    
    # إصلاح 1: التأكد من وجود جميع الأعمدة المطلوبة
    try:
        from bot_modules.database import get_db_connection
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # فحص وإضافة الأعمدة المفقودة
        cursor.execute("PRAGMA table_info(users)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'updated_at' not in columns:
            cursor.execute("ALTER TABLE users ADD COLUMN updated_at TEXT")
            cursor.execute("UPDATE users SET updated_at = created_at WHERE updated_at IS NULL")
            fixes_applied.append("إضافة عمود updated_at")
        
        conn.commit()
        conn.close()
    except Exception as e:
        log_update(f"خطأ في إصلاح قاعدة البيانات: {e}")
    
    # إصلاح 2: تنظيف ملفات السجلات الكبيرة
    try:
        if os.path.getsize("bot.log") > 10 * 1024 * 1024:  # أكبر من 10 MB
            subprocess.run(["tail", "-1000", "bot.log"], 
                         stdout=open("bot_temp.log", "w"))
            os.rename("bot_temp.log", "bot.log")
            fixes_applied.append("تنظيف ملف السجلات")
    except:
        pass
    
    return fixes_applied

def monitor_and_update():
    log_update("🔧 بدء نظام التحديث التلقائي")
    
    while True:
        try:
            # فحص الأخطاء الحرجة
            errors = check_for_critical_errors()
            if errors:
                log_update(f"🚨 اكتشاف {len(errors)} أخطاء حرجة")
                for error in errors:
                    log_update(f"خطأ حرج: {error}")
                
                # تطبيق الإصلاحات
                fixes = apply_fixes()
                if fixes:
                    log_update(f"✅ تم تطبيق إصلاحات: {', '.join(fixes)}")
                
            # انتظار 5 دقائق قبل الفحص التالي
            time.sleep(300)
            
        except KeyboardInterrupt:
            log_update("⏹️ تم إيقاف نظام التحديث التلقائي")
            break
        except Exception as e:
            log_update(f"❌ خطأ في نظام التحديث: {e}")
            time.sleep(60)

if __name__ == "__main__":
    monitor_and_update()
