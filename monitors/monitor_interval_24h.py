#!/usr/bin/env python3
"""
نظام مراقبة البوت لمدة 24 ساعة كاملة
24-Hour Bot Monitoring System
"""

import time
import subprocess
import psutil
import logging
import sqlite3
from datetime import datetime, timedelta
import json
import os
import signal
import sys

# إعداد نظام التسجيل
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/workspace/monitor_24h.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

class Bot24HMonitor:
    """مراقب البوت لمدة 24 ساعة"""
    
    def __init__(self):
        self.start_time = datetime.now()
        self.end_time = self.start_time + timedelta(hours=24)
        self.bot_process = None
        self.restart_count = 0
        self.error_count = 0
        self.last_health_check = datetime.now()
        self.stats = {
            'uptime_total': 0,
            'downtime_total': 0,
            'restarts': 0,
            'errors': [],
            'performance': [],
            'database_stats': [],
            'memory_usage': [],
            'cpu_usage': []
        }
    
    def start_bot(self):
        """تشغيل البوت"""
        try:
            if self.bot_process and self.bot_process.poll() is None:
                logger.info("البوت يعمل بالفعل")
                return True
            
            logger.info("🚀 بدء تشغيل البوت...")
            
            # تشغيل البوت في الخلفية
            self.bot_process = subprocess.Popen([
                'python3', 'main.py'
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd='/workspace')
            
            # انتظار للتأكد من التشغيل
            time.sleep(5)
            
            if self.bot_process.poll() is None:
                logger.info(f"✅ تم تشغيل البوت بنجاح - PID: {self.bot_process.pid}")
                return True
            else:
                stdout, stderr = self.bot_process.communicate()
                logger.error(f"❌ فشل تشغيل البوت: {stderr.decode('utf-8', errors='ignore')}")
                return False
                
        except Exception as e:
            logger.error(f"خطأ في تشغيل البوت: {e}")
            return False
    
    def check_bot_health(self):
        """فحص صحة البوت"""
        try:
            if not self.bot_process or self.bot_process.poll() is not None:
                return False
            
            # فحص استخدام الذاكرة والمعالج
            try:
                process = psutil.Process(self.bot_process.pid)
                memory_percent = process.memory_percent()
                cpu_percent = process.cpu_percent()
                
                self.stats['memory_usage'].append({
                    'timestamp': datetime.now().isoformat(),
                    'memory_percent': memory_percent
                })
                
                self.stats['cpu_usage'].append({
                    'timestamp': datetime.now().isoformat(),
                    'cpu_percent': cpu_percent
                })
                
                # تحذير إذا كان الاستخدام عالي
                if memory_percent > 80:
                    logger.warning(f"⚠️ استخدام ذاكرة عالي: {memory_percent:.1f}%")
                
                if cpu_percent > 90:
                    logger.warning(f"⚠️ استخدام معالج عالي: {cpu_percent:.1f}%")
                
            except psutil.NoSuchProcess:
                return False
            
            # فحص قاعدة البيانات
            if self.check_database_health():
                self.last_health_check = datetime.now()
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"خطأ في فحص صحة البوت: {e}")
            return False
    
    def check_database_health(self):
        """فحص صحة قاعدة البيانات"""
        try:
            conn = sqlite3.connect('/workspace/yemen_net.db', timeout=10)
            cursor = conn.cursor()
            
            # فحص الجداول الأساسية
            cursor.execute("SELECT COUNT(*) FROM users")
            users_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM transactions")
            transactions_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM networks WHERE is_active = 1")
            active_networks = cursor.fetchone()[0]
            
            # حفظ إحصائيات قاعدة البيانات
            db_stats = {
                'timestamp': datetime.now().isoformat(),
                'users_count': users_count,
                'transactions_count': transactions_count,
                'active_networks': active_networks
            }
            
            self.stats['database_stats'].append(db_stats)
            
            conn.close()
            
            logger.info(f"📊 إحصائيات قاعدة البيانات - المستخدمون: {users_count}, المعاملات: {transactions_count}, الشبكات النشطة: {active_networks}")
            
            return True
            
        except Exception as e:
            logger.error(f"خطأ في فحص قاعدة البيانات: {e}")
            self.stats['errors'].append({
                'timestamp': datetime.now().isoformat(),
                'type': 'database_error',
                'message': str(e)
            })
            return False
    
    def restart_bot(self, reason="غير محدد"):
        """إعادة تشغيل البوت"""
        try:
            logger.info(f"🔄 إعادة تشغيل البوت - السبب: {reason}")
            
            # إيقاف البوت الحالي
            if self.bot_process:
                try:
                    self.bot_process.terminate()
                    self.bot_process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    self.bot_process.kill()
                    self.bot_process.wait()
            
            # تنظيف العمليات المعلقة
            subprocess.run(['pkill', '-f', 'python.*main.py'], stderr=subprocess.DEVNULL)
            time.sleep(3)
            
            # إعادة التشغيل
            if self.start_bot():
                self.restart_count += 1
                self.stats['restarts'] += 1
                
                # تسجيل سبب إعادة التشغيل
                self.stats['errors'].append({
                    'timestamp': datetime.now().isoformat(),
                    'type': 'restart',
                    'reason': reason,
                    'restart_count': self.restart_count
                })
                
                logger.info(f"✅ تم إعادة تشغيل البوت بنجاح - العدد: {self.restart_count}")
                return True
            else:
                logger.error("❌ فشل في إعادة تشغيل البوت")
                return False
                
        except Exception as e:
            logger.error(f"خطأ في إعادة تشغيل البوت: {e}")
            return False
    
    def generate_hourly_report(self):
        """إنشاء تقرير كل ساعة"""
        try:
            current_time = datetime.now()
            uptime = current_time - self.start_time
            
            # حساب الإحصائيات
            avg_memory = 0
            avg_cpu = 0
            
            if self.stats['memory_usage']:
                recent_memory = self.stats['memory_usage'][-60:]  # آخر 60 قراءة
                avg_memory = sum(m['memory_percent'] for m in recent_memory) / len(recent_memory)
            
            if self.stats['cpu_usage']:
                recent_cpu = self.stats['cpu_usage'][-60:]
                avg_cpu = sum(c['cpu_percent'] for c in recent_cpu) / len(recent_cpu)
            
            report = f"""
📊 **تقرير كل ساعة - البوت يعمل منذ {uptime}**

🚀 **حالة التشغيل:**
• البوت: {'🟢 يعمل' if self.check_bot_health() else '🔴 متوقف'}
• إعادات التشغيل: {self.restart_count}
• الأخطاء: {len(self.stats['errors'])}

💻 **الأداء:**
• متوسط استخدام الذاكرة: {avg_memory:.1f}%
• متوسط استخدام المعالج: {avg_cpu:.1f}%

📊 **قاعدة البيانات:**
"""
            
            if self.stats['database_stats']:
                latest_db = self.stats['database_stats'][-1]
                report += f"""• المستخدمون: {latest_db['users_count']}
• المعاملات: {latest_db['transactions_count']}
• الشبكات النشطة: {latest_db['active_networks']}"""
            
            logger.info(report)
            
            # حفظ التقرير في ملف
            with open(f'/workspace/hourly_report_{current_time.strftime("%Y%m%d_%H")}.txt', 'w', encoding='utf-8') as f:
                f.write(report)
                
        except Exception as e:
            logger.error(f"خطأ في إنشاء التقرير الساعي: {e}")
    
    def save_final_report(self):
        """حفظ التقرير النهائي"""
        try:
            total_runtime = datetime.now() - self.start_time
            
            # حساب إحصائيات شاملة
            total_errors = len(self.stats['errors'])
            
            avg_memory = 0
            if self.stats['memory_usage']:
                avg_memory = sum(m['memory_percent'] for m in self.stats['memory_usage']) / len(self.stats['memory_usage'])
            
            avg_cpu = 0
            if self.stats['cpu_usage']:
                avg_cpu = sum(c['cpu_percent'] for c in self.stats['cpu_usage']) / len(self.stats['cpu_usage'])
            
            final_report = {
                'monitoring_period': {
                    'start_time': self.start_time.isoformat(),
                    'end_time': datetime.now().isoformat(),
                    'total_runtime_hours': total_runtime.total_seconds() / 3600
                },
                'bot_performance': {
                    'total_restarts': self.restart_count,
                    'total_errors': total_errors,
                    'average_memory_usage': avg_memory,
                    'average_cpu_usage': avg_cpu,
                    'uptime_percentage': ((total_runtime.total_seconds() - self.stats.get('downtime_total', 0)) / total_runtime.total_seconds()) * 100
                },
                'detailed_stats': self.stats
            }
            
            # حفظ التقرير النهائي
            with open('/workspace/final_24h_report.json', 'w', encoding='utf-8') as f:
                json.dump(final_report, f, ensure_ascii=False, indent=2)
            
            # تقرير نصي مبسط
            summary = f"""
🎉 **تقرير المراقبة النهائي - 24 ساعة** 🎉

⏰ **فترة المراقبة:** {total_runtime}
🔄 **إعادات التشغيل:** {self.restart_count}
❌ **إجمالي الأخطاء:** {total_errors}
💾 **متوسط استخدام الذاكرة:** {avg_memory:.1f}%
🖥️ **متوسط استخدام المعالج:** {avg_cpu:.1f}%

📊 **معدل التشغيل:** {((total_runtime.total_seconds() - self.stats.get('downtime_total', 0)) / total_runtime.total_seconds()) * 100:.1f}%

✅ **تم حفظ التقرير التفصيلي في:** final_24h_report.json
"""
            
            logger.info(summary)
            
            with open('/workspace/final_24h_summary.txt', 'w', encoding='utf-8') as f:
                f.write(summary)
                
        except Exception as e:
            logger.error(f"خطأ في حفظ التقرير النهائي: {e}")
    
    def run_24h_monitoring(self):
        """تشغيل المراقبة لمدة 24 ساعة"""
        logger.info("🚀 بدء مراقبة البوت لمدة 24 ساعة")
        logger.info(f"⏰ وقت البداية: {self.start_time}")
        logger.info(f"⏰ وقت النهاية المتوقع: {self.end_time}")
        
        # تشغيل البوت أولاً
        if not self.start_bot():
            logger.error("❌ فشل في تشغيل البوت الأولي")
            return
        
        last_hourly_report = datetime.now()
        
        try:
            while datetime.now() < self.end_time:
                current_time = datetime.now()
                
                # فحص صحة البوت كل دقيقة
                if not self.check_bot_health():
                    logger.warning("⚠️ البوت لا يعمل بشكل صحيح")
                    
                    # محاولة إعادة التشغيل
                    if not self.restart_bot("فشل في فحص الصحة"):
                        logger.error("❌ فشل في إعادة تشغيل البوت")
                        time.sleep(60)  # انتظار قبل المحاولة مرة أخرى
                        continue
                
                # تقرير كل ساعة
                if current_time - last_hourly_report >= timedelta(hours=1):
                    self.generate_hourly_report()
                    last_hourly_report = current_time
                
                # انتظار دقيقة واحدة
                time.sleep(60)
                
        except KeyboardInterrupt:
            logger.info("🛑 تم إيقاف المراقبة بواسطة المستخدم")
        except Exception as e:
            logger.error(f"خطأ في المراقبة: {e}")
        finally:
            # حفظ التقرير النهائي
            self.save_final_report()
            logger.info("✅ انتهت فترة المراقبة 24 ساعة")

def signal_handler(signum, frame):
    """معالج إشارة الإيقاف"""
    logger.info("🛑 تم تلقي إشارة الإيقاف")
    sys.exit(0)

if __name__ == "__main__":
    # تسجيل معالج الإشارات
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # بدء المراقبة
    monitor = Bot24HMonitor()
    monitor.run_24h_monitoring()