#!/usr/bin/env python3
"""
خدمة إعادة التشغيل التلقائي للبوت
Auto-Restart Daemon for Bot
"""

import time
import subprocess
import psutil
import logging
import os
import signal
import sys
from datetime import datetime

# إعداد التسجيل
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/workspace/auto_restart.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class AutoRestartDaemon:
    """خدمة إعادة التشغيل التلقائي"""
    
    def __init__(self):
        self.bot_command = ['python3', '/workspace/main.py']
        self.check_interval = 30  # فحص كل 30 ثانية
        self.max_restart_attempts = 5
        self.restart_count = 0
        self.last_restart_time = None
        self.running = True
    
    def is_bot_running(self):
        """التحقق من تشغيل البوت"""
        try:
            # البحث عن العملية
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    cmdline = proc.info['cmdline']
                    if cmdline and len(cmdline) >= 2:
                        if 'python' in cmdline[0] and 'main.py' in cmdline[1]:
                            return True, proc.info['pid']
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            return False, None
            
        except Exception as e:
            logger.error(f"خطأ في فحص البوت: {e}")
            return False, None
    
    def start_bot(self):
        """تشغيل البوت"""
        try:
            logger.info("🚀 تشغيل البوت...")
            
            # تنظيف العمليات المعلقة أولاً
            subprocess.run(['pkill', '-f', 'python.*main.py'], 
                         stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
            time.sleep(2)
            
            # تشغيل البوت
            process = subprocess.Popen(
                self.bot_command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd='/workspace'
            )
            
            # انتظار للتأكد من التشغيل
            time.sleep(5)
            
            if process.poll() is None:
                logger.info(f"✅ تم تشغيل البوت - PID: {process.pid}")
                self.restart_count += 1
                self.last_restart_time = datetime.now()
                return True
            else:
                stdout, stderr = process.communicate()
                logger.error(f"❌ فشل تشغيل البوت: {stderr.decode('utf-8', errors='ignore')}")
                return False
                
        except Exception as e:
            logger.error(f"خطأ في تشغيل البوت: {e}")
            return False
    
    def run(self):
        """تشغيل الخدمة"""
        logger.info("🤖 بدء خدمة إعادة التشغيل التلقائي")
        
        consecutive_failures = 0
        
        while self.running:
            try:
                is_running, pid = self.is_bot_running()
                
                if is_running:
                    logger.debug(f"✅ البوت يعمل - PID: {pid}")
                    consecutive_failures = 0
                else:
                    logger.warning("⚠️ البوت متوقف")
                    consecutive_failures += 1
                    
                    if consecutive_failures >= 2:  # تأكيد التوقف
                        if self.restart_count < self.max_restart_attempts:
                            logger.info(f"🔄 محاولة إعادة التشغيل ({self.restart_count + 1}/{self.max_restart_attempts})")
                            
                            if self.start_bot():
                                consecutive_failures = 0
                            else:
                                logger.error("❌ فشل في إعادة التشغيل")
                                time.sleep(60)  # انتظار أطول بعد الفشل
                        else:
                            logger.error(f"❌ تم الوصول للحد الأقصى من المحاولات ({self.max_restart_attempts})")
                            logger.info("⏸️ إيقاف خدمة إعادة التشغيل")
                            break
                
                time.sleep(self.check_interval)
                
            except KeyboardInterrupt:
                logger.info("🛑 تم إيقاف الخدمة بواسطة المستخدم")
                break
            except Exception as e:
                logger.error(f"خطأ في الخدمة: {e}")
                time.sleep(30)
        
        logger.info("✅ انتهت خدمة إعادة التشغيل التلقائي")
    
    def stop(self):
        """إيقاف الخدمة"""
        self.running = False

def signal_handler(signum, frame):
    """معالج إشارة الإيقاف"""
    logger.info("🛑 تم تلقي إشارة الإيقاف")
    daemon.stop()

if __name__ == "__main__":
    # تسجيل معالج الإشارات
    daemon = AutoRestartDaemon()
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # تشغيل الخدمة
    daemon.run()