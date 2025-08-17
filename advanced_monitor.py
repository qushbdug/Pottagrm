#!/usr/bin/env python3
"""
نظام مراقبة متقدم للبوت - 24 ساعة
Advanced Bot Monitoring System - 24 Hours
"""

import os
import sys
import time
import json
import sqlite3
import subprocess
import datetime
import psutil
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass
import requests

# إعداد السجلات
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/workspace/monitor.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class BotStatus:
    """حالة البوت"""
    pid: Optional[int]
    cpu_percent: float
    memory_mb: float
    uptime: str
    is_running: bool
    last_error: Optional[str]
    telegram_connected: bool
    db_size_mb: float
    error_count: int
    restart_count: int

@dataclass
class SystemMetrics:
    """مقاييس النظام"""
    total_memory: float
    available_memory: float
    cpu_usage: float
    disk_usage: float
    timestamp: datetime.datetime

class AdvancedBotMonitor:
    """نظام مراقبة متقدم للبوت"""
    
    def __init__(self):
        self.bot_token = "7766964799:AAHex-hGfjPX6g_R2aZ7-UPrgnFxQKAjSa0"
        self.workspace = "/workspace"
        self.bot_script = "main.py"
        self.log_file = "bot_fixed.log"
        
        self.monitoring_data = {
            'start_time': datetime.datetime.now(),
            'total_restarts': 0,
            'total_errors': 0,
            'uptime_periods': [],
            'performance_data': [],
            'error_log': []
        }
        
        # إنشاء ملف تقرير يومي
        self.daily_report_file = f"daily_report_{datetime.datetime.now().strftime('%Y%m%d')}.json"
        
    def get_bot_process(self) -> Optional[psutil.Process]:
        """الحصول على عملية البوت"""
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                if proc.info['cmdline'] and any('main.py' in arg for arg in proc.info['cmdline']):
                    return proc
        except Exception as e:
            logger.error(f"خطأ في البحث عن عملية البوت: {e}")
        return None
    
    def get_bot_status(self) -> BotStatus:
        """الحصول على حالة البوت"""
        proc = self.get_bot_process()
        
        if proc:
            try:
                cpu_percent = proc.cpu_percent(interval=1)
                memory_mb = proc.memory_info().rss / (1024 * 1024)
                create_time = datetime.datetime.fromtimestamp(proc.create_time())
                uptime = str(datetime.datetime.now() - create_time)
                
                # فحص الاتصال بـ Telegram
                telegram_connected = self.check_telegram_connection()
                
                # فحص حجم قاعدة البيانات
                db_size_mb = self.get_db_size()
                
                # عدد الأخطاء
                error_count = self.count_recent_errors()
                
                return BotStatus(
                    pid=proc.pid,
                    cpu_percent=cpu_percent,
                    memory_mb=memory_mb,
                    uptime=uptime,
                    is_running=True,
                    last_error=self.get_last_error(),
                    telegram_connected=telegram_connected,
                    db_size_mb=db_size_mb,
                    error_count=error_count,
                    restart_count=self.monitoring_data['total_restarts']
                )
            except Exception as e:
                logger.error(f"خطأ في الحصول على تفاصيل العملية: {e}")
        
        return BotStatus(
            pid=None,
            cpu_percent=0,
            memory_mb=0,
            uptime="0",
            is_running=False,
            last_error="البوت غير يعمل",
            telegram_connected=False,
            db_size_mb=0,
            error_count=0,
            restart_count=self.monitoring_data['total_restarts']
        )
    
    def check_telegram_connection(self) -> bool:
        """فحص الاتصال بـ Telegram API"""
        try:
            response = requests.get(
                f"https://api.telegram.org/bot{self.bot_token}/getMe",
                timeout=10
            )
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"فشل في فحص الاتصال بـ Telegram: {e}")
            return False
    
    def get_db_size(self) -> float:
        """الحصول على حجم قاعدة البيانات"""
        try:
            db_path = os.path.join(self.workspace, "yemen_net.db")
            if os.path.exists(db_path):
                return os.path.getsize(db_path) / (1024 * 1024)
        except Exception as e:
            logger.error(f"خطأ في الحصول على حجم قاعدة البيانات: {e}")
        return 0
    
    def count_recent_errors(self, hours: int = 1) -> int:
        """عدد الأخطاء في الساعات الأخيرة"""
        try:
            log_path = os.path.join(self.workspace, self.log_file)
            if not os.path.exists(log_path):
                return 0
            
            cutoff_time = datetime.datetime.now() - datetime.timedelta(hours=hours)
            error_count = 0
            
            with open(log_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if 'ERROR' in line:
                        try:
                            # استخراج الوقت من السطر
                            time_str = line.split(' - ')[0]
                            log_time = datetime.datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S,%f')
                            if log_time > cutoff_time:
                                error_count += 1
                        except:
                            continue
            
            return error_count
        except Exception as e:
            logger.error(f"خطأ في عدّ الأخطاء: {e}")
            return 0
    
    def get_last_error(self) -> Optional[str]:
        """الحصول على آخر خطأ"""
        try:
            log_path = os.path.join(self.workspace, self.log_file)
            if not os.path.exists(log_path):
                return None
            
            with open(log_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
            for line in reversed(lines):
                if 'ERROR' in line:
                    return line.strip()
        except Exception as e:
            logger.error(f"خطأ في الحصول على آخر خطأ: {e}")
        return None
    
    def get_system_metrics(self) -> SystemMetrics:
        """الحصول على مقاييس النظام"""
        try:
            memory = psutil.virtual_memory()
            cpu_usage = psutil.cpu_percent(interval=1)
            disk_usage = psutil.disk_usage('/').percent
            
            return SystemMetrics(
                total_memory=memory.total / (1024**3),  # GB
                available_memory=memory.available / (1024**3),  # GB
                cpu_usage=cpu_usage,
                disk_usage=disk_usage,
                timestamp=datetime.datetime.now()
            )
        except Exception as e:
            logger.error(f"خطأ في الحصول على مقاييس النظام: {e}")
            return SystemMetrics(0, 0, 0, 0, datetime.datetime.now())
    
    def restart_bot(self) -> bool:
        """إعادة تشغيل البوت"""
        try:
            logger.info("🔄 بدء إعادة تشغيل البوت...")
            
            # إيقاف البوت الحالي
            proc = self.get_bot_process()
            if proc:
                proc.terminate()
                proc.wait(timeout=10)
                logger.info("✅ تم إيقاف البوت القديم")
            
            # انتظار قصير
            time.sleep(3)
            
            # تشغيل البوت الجديد
            log_file = f"bot_restart_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
            cmd = f"cd {self.workspace} && nohup python3 {self.bot_script} > {log_file} 2>&1 &"
            subprocess.run(cmd, shell=True)
            
            # انتظار للتأكد من بدء التشغيل
            time.sleep(5)
            
            # فحص إذا كان البوت يعمل
            new_proc = self.get_bot_process()
            if new_proc:
                self.monitoring_data['total_restarts'] += 1
                logger.info(f"✅ تم إعادة تشغيل البوت بنجاح (PID: {new_proc.pid})")
                return True
            else:
                logger.error("❌ فشل في إعادة تشغيل البوت")
                return False
                
        except Exception as e:
            logger.error(f"خطأ في إعادة تشغيل البوت: {e}")
            return False
    
    def analyze_logs(self) -> Dict:
        """تحليل السجلات"""
        try:
            log_path = os.path.join(self.workspace, self.log_file)
            if not os.path.exists(log_path):
                return {'errors': 0, 'warnings': 0, 'info': 0}
            
            analysis = {
                'errors': 0,
                'warnings': 0,
                'info': 0,
                'recent_errors': [],
                'common_errors': {}
            }
            
            cutoff_time = datetime.datetime.now() - datetime.timedelta(hours=24)
            
            with open(log_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if 'ERROR' in line:
                        analysis['errors'] += 1
                        # استخراج نوع الخطأ
                        if ':' in line:
                            error_type = line.split(':')[-1].strip()
                            analysis['common_errors'][error_type] = analysis['common_errors'].get(error_type, 0) + 1
                        
                        # إضافة الأخطاء الحديثة
                        try:
                            time_str = line.split(' - ')[0]
                            log_time = datetime.datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S,%f')
                            if log_time > cutoff_time:
                                analysis['recent_errors'].append(line.strip())
                        except:
                            pass
                    
                    elif 'WARNING' in line:
                        analysis['warnings'] += 1
                    elif 'INFO' in line:
                        analysis['info'] += 1
            
            return analysis
        except Exception as e:
            logger.error(f"خطأ في تحليل السجلات: {e}")
            return {'errors': 0, 'warnings': 0, 'info': 0}
    
    def save_monitoring_data(self):
        """حفظ بيانات المراقبة"""
        try:
            with open(self.daily_report_file, 'w', encoding='utf-8') as f:
                # تحويل datetime objects إلى strings
                data_to_save = {}
                for key, value in self.monitoring_data.items():
                    if isinstance(value, datetime.datetime):
                        data_to_save[key] = value.isoformat()
                    elif isinstance(value, list):
                        data_to_save[key] = []
                        for item in value:
                            if isinstance(item, datetime.datetime):
                                data_to_save[key].append(item.isoformat())
                            else:
                                data_to_save[key].append(item)
                    else:
                        data_to_save[key] = value
                
                json.dump(data_to_save, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"خطأ في حفظ بيانات المراقبة: {e}")
    
    def generate_status_report(self) -> str:
        """إنشاء تقرير حالة شامل"""
        bot_status = self.get_bot_status()
        system_metrics = self.get_system_metrics()
        log_analysis = self.analyze_logs()
        
        current_time = datetime.datetime.now()
        monitoring_duration = current_time - self.monitoring_data['start_time']
        
        report = f"""
🤖 ═══════════════════════════════════════════════════════════ 🤖
                       تقرير مراقبة البوت المتقدم
🤖 ═══════════════════════════════════════════════════════════ 🤖

📅 وقت التقرير: {current_time.strftime('%Y-%m-%d %H:%M:%S')}
⏱️ مدة المراقبة: {str(monitoring_duration).split('.')[0]}

🚀 === حالة البوت ===
{"🟢 يعمل" if bot_status.is_running else "🔴 متوقف"} الحالة: {"يعمل بنجاح" if bot_status.is_running else "غير يعمل"}
🔢 PID: {bot_status.pid if bot_status.pid else "غير متاح"}
🧮 استهلاك المعالج: {bot_status.cpu_percent:.1f}%
💾 استهلاك الذاكرة: {bot_status.memory_mb:.1f} MB
⏰ وقت التشغيل: {bot_status.uptime}
🌐 اتصال Telegram: {"✅ متصل" if bot_status.telegram_connected else "❌ منقطع"}
📊 حجم قاعدة البيانات: {bot_status.db_size_mb:.2f} MB

📈 === إحصائيات الأداء ===
🔄 عدد إعادات التشغيل: {bot_status.restart_count}
❌ أخطاء الساعة الأخيرة: {bot_status.error_count}
⚠️ إجمالي الأخطاء (24 ساعة): {log_analysis['errors']}
💡 التحذيرات: {log_analysis['warnings']}
📝 رسائل المعلومات: {log_analysis['info']}

🖥️ === مقاييس النظام ===
🧮 استهلاك المعالج: {system_metrics.cpu_usage:.1f}%
💾 إجمالي الذاكرة: {system_metrics.total_memory:.1f} GB
💿 الذاكرة المتاحة: {system_metrics.available_memory:.1f} GB
💽 استهلاك القرص: {system_metrics.disk_usage:.1f}%

{"🔍 === آخر خطأ ===" if bot_status.last_error else ""}
{bot_status.last_error if bot_status.last_error else "✅ لا توجد أخطاء حديثة"}

🎯 === تقييم الحالة العامة ===
"""
        
        # تقييم الحالة
        if bot_status.is_running and bot_status.telegram_connected and bot_status.error_count == 0:
            report += "🟢 **ممتاز:** البوت يعمل بحالة مثالية\n"
        elif bot_status.is_running and bot_status.telegram_connected:
            report += "🟡 **جيد:** البوت يعمل مع بعض التحذيرات\n"
        elif bot_status.is_running:
            report += "🟠 **متوسط:** البوت يعمل لكن يوجد مشاكل في الاتصال\n"
        else:
            report += "🔴 **سيء:** البوت متوقف - يحتاج إعادة تشغيل\n"
        
        report += f"""
═══════════════════════════════════════════════════════════
📊 تقرير إحصائي: {current_time.strftime('%Y-%m-%d %H:%M:%S')}
═══════════════════════════════════════════════════════════
"""
        
        return report
    
    def monitor_24h(self):
        """مراقبة لمدة 24 ساعة"""
        logger.info("🚀 بدء مراقبة البوت لمدة 24 ساعة")
        
        end_time = datetime.datetime.now() + datetime.timedelta(hours=24)
        check_interval = 60  # فحص كل دقيقة
        report_interval = 300  # تقرير كل 5 دقائق
        
        last_report_time = datetime.datetime.now()
        
        try:
            while datetime.datetime.now() < end_time:
                current_time = datetime.datetime.now()
                
                # فحص حالة البوت
                bot_status = self.get_bot_status()
                system_metrics = self.get_system_metrics()
                
                # إضافة البيانات للمراقبة
                self.monitoring_data['performance_data'].append({
                    'timestamp': current_time.isoformat(),
                    'cpu_percent': bot_status.cpu_percent,
                    'memory_mb': bot_status.memory_mb,
                    'is_running': bot_status.is_running,
                    'error_count': bot_status.error_count,
                    'system_cpu': system_metrics.cpu_usage,
                    'system_memory_available': system_metrics.available_memory
                })
                
                # فحص إذا كان البوت متوقف
                if not bot_status.is_running:
                    logger.warning("⚠️ البوت متوقف - محاولة إعادة التشغيل")
                    if self.restart_bot():
                        logger.info("✅ تم إعادة تشغيل البوت بنجاح")
                    else:
                        logger.error("❌ فشل في إعادة تشغيل البوت")
                
                # فحص إذا كان هناك أخطاء كثيرة
                if bot_status.error_count > 10:  # أكثر من 10 أخطاء في الساعة
                    logger.warning(f"⚠️ عدد أخطاء عالي: {bot_status.error_count}")
                    if self.restart_bot():
                        logger.info("✅ تم إعادة تشغيل البوت بسبب كثرة الأخطاء")
                
                # فحص استهلاك الذاكرة
                if bot_status.memory_mb > 500:  # أكثر من 500 MB
                    logger.warning(f"⚠️ استهلاك ذاكرة عالي: {bot_status.memory_mb:.1f} MB")
                
                # إنشاء تقرير دوري
                if (current_time - last_report_time).total_seconds() >= report_interval:
                    report = self.generate_status_report()
                    print(report)
                    
                    # حفظ التقرير في ملف
                    report_filename = f"status_report_{current_time.strftime('%Y%m%d_%H%M')}.txt"
                    with open(report_filename, 'w', encoding='utf-8') as f:
                        f.write(report)
                    
                    last_report_time = current_time
                
                # حفظ بيانات المراقبة
                self.save_monitoring_data()
                
                # انتظار للفحص التالي
                time.sleep(check_interval)
                
        except KeyboardInterrupt:
            logger.info("⏹️ تم إيقاف المراقبة بواسطة المستخدم")
        except Exception as e:
            logger.error(f"خطأ في نظام المراقبة: {e}")
        finally:
            # إنشاء تقرير نهائي
            final_report = self.generate_final_report()
            print(final_report)
            
            with open(f"final_monitoring_report_{datetime.datetime.now().strftime('%Y%m%d')}.txt", 'w', encoding='utf-8') as f:
                f.write(final_report)
            
            logger.info("🎉 انتهت مراقبة البوت لمدة 24 ساعة")
    
    def generate_final_report(self) -> str:
        """إنشاء التقرير النهائي"""
        duration = datetime.datetime.now() - self.monitoring_data['start_time']
        performance_data = self.monitoring_data['performance_data']
        
        if performance_data:
            avg_cpu = sum(p['cpu_percent'] for p in performance_data) / len(performance_data)
            avg_memory = sum(p['memory_mb'] for p in performance_data) / len(performance_data)
            uptime_percentage = (sum(1 for p in performance_data if p['is_running']) / len(performance_data)) * 100
        else:
            avg_cpu = avg_memory = uptime_percentage = 0
        
        report = f"""
🏁 ═══════════════════════════════════════════════════════════ 🏁
                          التقرير النهائي - 24 ساعة
🏁 ═══════════════════════════════════════════════════════════ 🏁

📅 فترة المراقبة: {self.monitoring_data['start_time'].strftime('%Y-%m-%d %H:%M')} - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}
⏱️ إجمالي المدة: {str(duration).split('.')[0]}

📊 === الإحصائيات العامة ===
🔄 إعادات التشغيل: {self.monitoring_data['total_restarts']}
⏱️ نسبة وقت التشغيل: {uptime_percentage:.1f}%
🧮 متوسط استهلاك المعالج: {avg_cpu:.1f}%
💾 متوسط استهلاك الذاكرة: {avg_memory:.1f} MB

🎯 === التقييم النهائي ===
"""
        
        if uptime_percentage > 99:
            report += "🟢 **ممتاز:** البوت حقق استقرار ممتاز\n"
        elif uptime_percentage > 95:
            report += "🟡 **جيد جداً:** البوت حقق استقرار جيد\n"
        elif uptime_percentage > 90:
            report += "🟠 **جيد:** البوت حقق استقرار مقبول\n"
        else:
            report += "🔴 **يحتاج تحسين:** البوت واجه مشاكل في الاستقرار\n"
        
        return report

def main():
    """الدالة الرئيسية"""
    print("🚀 بدء نظام المراقبة المتقدم للبوت - 24 ساعة")
    
    monitor = AdvancedBotMonitor()
    
    # عرض تقرير أولي
    initial_report = monitor.generate_status_report()
    print(initial_report)
    
    # بدء المراقبة
    monitor.monitor_24h()

if __name__ == "__main__":
    main()