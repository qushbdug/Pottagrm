#!/usr/bin/env python3
"""
Backup Manager - مدير النسخ الاحتياطية التلقائية
يقوم بإنشاء نسخ احتياطية دورية لقاعدة البيانات
"""

import os
import shutil
import sqlite3
import logging
import schedule
import threading
import time
import gzip
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional
from bot_modules.config import DB_PATH

logger = logging.getLogger(__name__)

class BackupManager:
    """مدير النسخ الاحتياطية التلقائية"""
    
    def __init__(self, backup_dir: str = "backups", 
                 max_backups: int = 30,
                 compress_backups: bool = True):
        self.backup_dir = Path(backup_dir)
        self.max_backups = max_backups
        self.compress_backups = compress_backups
        self.backup_thread = None
        self.running = False
        
        # إنشاء مجلد النسخ الاحتياطية
        self.backup_dir.mkdir(exist_ok=True)
        
        # تكوين الجدولة
        self._setup_schedule()
    
    def _setup_schedule(self):
        """تكوين جدولة النسخ الاحتياطية"""
        # نسخة احتياطية كل 6 ساعات
        schedule.every(6).hours.do(self.create_backup)
        
        # نسخة احتياطية يومية في الساعة 2 صباحاً
        schedule.every().day.at("02:00").do(self.create_daily_backup)
        
        # تنظيف النسخ القديمة كل يوم في الساعة 3 صباحاً
        schedule.every().day.at("03:00").do(self.cleanup_old_backups)
    
    def start_scheduler(self):
        """بدء المجدول التلقائي للنسخ الاحتياطية"""
        if self.running:
            return
        
        self.running = True
        self.backup_thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.backup_thread.start()
        logger.info("Backup scheduler started")
    
    def stop_scheduler(self):
        """إيقاف المجدول التلقائي"""
        self.running = False
        if self.backup_thread:
            self.backup_thread.join(timeout=5)
        logger.info("Backup scheduler stopped")
    
    def _run_scheduler(self):
        """تشغيل المجدول في thread منفصل"""
        while self.running:
            try:
                schedule.run_pending()
                time.sleep(60)  # فحص كل دقيقة
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
                time.sleep(60)
    
    def create_backup(self, backup_type: str = "auto") -> Optional[str]:
        """إنشاء نسخة احتياطية"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"yemen_net_backup_{timestamp}_{backup_type}"
            
            if self.compress_backups:
                backup_file = self.backup_dir / f"{backup_name}.db.gz"
                success = self._create_compressed_backup(backup_file)
            else:
                backup_file = self.backup_dir / f"{backup_name}.db"
                success = self._create_regular_backup(backup_file)
            
            if success:
                logger.info(f"Backup created successfully: {backup_file}")
                
                # إضافة معلومات النسخة الاحتياطية
                self._save_backup_info(backup_file, backup_type)
                return str(backup_file)
            else:
                logger.error(f"Failed to create backup: {backup_file}")
                return None
                
        except Exception as e:
            logger.error(f"Error creating backup: {e}")
            return None
    
    def _create_regular_backup(self, backup_file: Path) -> bool:
        """إنشاء نسخة احتياطية عادية"""
        try:
            # استخدام SQLite backup API للنسخ الآمن
            source_conn = sqlite3.connect(DB_PATH)
            backup_conn = sqlite3.connect(str(backup_file))
            
            source_conn.backup(backup_conn)
            
            source_conn.close()
            backup_conn.close()
            
            return True
        except Exception as e:
            logger.error(f"Regular backup failed: {e}")
            return False
    
    def _create_compressed_backup(self, backup_file: Path) -> bool:
        """إنشاء نسخة احتياطية مضغوطة"""
        try:
            # إنشاء نسخة مؤقتة أولاً
            temp_file = backup_file.with_suffix('.tmp')
            
            if not self._create_regular_backup(temp_file):
                return False
            
            # ضغط النسخة
            with open(temp_file, 'rb') as f_in:
                with gzip.open(backup_file, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            
            # حذف النسخة المؤقتة
            temp_file.unlink()
            
            return True
        except Exception as e:
            logger.error(f"Compressed backup failed: {e}")
            return False
    
    def _save_backup_info(self, backup_file: Path, backup_type: str):
        """حفظ معلومات النسخة الاحتياطية"""
        info_file = backup_file.with_suffix('.info')
        
        try:
            # الحصول على إحصائيات قاعدة البيانات
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            stats = {}
            
            # عدد المستخدمين
            cursor.execute('SELECT COUNT(*) FROM users')
            stats['users_count'] = cursor.fetchone()[0]
            
            # عدد المعاملات
            cursor.execute('SELECT COUNT(*) FROM transactions')
            stats['transactions_count'] = cursor.fetchone()[0]
            
            # إجمالي الأرصدة
            cursor.execute('SELECT COALESCE(SUM(balance), 0) FROM users')
            stats['total_balance'] = cursor.fetchone()[0]
            
            # حجم قاعدة البيانات
            stats['db_size'] = os.path.getsize(DB_PATH)
            
            conn.close()
            
            # كتابة معلومات النسخة الاحتياطية
            info = {
                'timestamp': datetime.now().isoformat(),
                'backup_type': backup_type,
                'backup_file': backup_file.name,
                'compressed': self.compress_backups,
                'file_size': backup_file.stat().st_size,
                'statistics': stats
            }
            
            with open(info_file, 'w', encoding='utf-8') as f:
                import json
                json.dump(info, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            logger.error(f"Failed to save backup info: {e}")
    
    def create_daily_backup(self) -> Optional[str]:
        """إنشاء النسخة الاحتياطية اليومية"""
        return self.create_backup("daily")
    
    def create_manual_backup(self) -> Optional[str]:
        """إنشاء نسخة احتياطية يدوية"""
        return self.create_backup("manual")
    
    def cleanup_old_backups(self):
        """تنظيف النسخ الاحتياطية القديمة"""
        try:
            backup_files = []
            
            # جمع جميع ملفات النسخ الاحتياطية
            for file in self.backup_dir.glob("yemen_net_backup_*.db*"):
                if file.suffix in ['.db', '.gz']:
                    backup_files.append(file)
            
            # ترتيب حسب تاريخ الإنشاء
            backup_files.sort(key=lambda f: f.stat().st_ctime, reverse=True)
            
            # حذف النسخ الزائدة
            deleted_count = 0
            for file in backup_files[self.max_backups:]:
                try:
                    file.unlink()
                    # حذف ملف المعلومات المرافق
                    info_file = file.with_suffix('.info')
                    if info_file.exists():
                        info_file.unlink()
                    deleted_count += 1
                except Exception as e:
                    logger.error(f"Failed to delete backup {file}: {e}")
            
            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} old backup files")
                
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")
    
    def list_backups(self) -> List[Dict]:
        """قائمة النسخ الاحتياطية المتاحة"""
        backups = []
        
        try:
            for file in self.backup_dir.glob("yemen_net_backup_*.db*"):
                if file.suffix in ['.db', '.gz']:
                    info_file = file.with_suffix('.info')
                    
                    backup_info = {
                        'filename': file.name,
                        'size': file.stat().st_size,
                        'created': datetime.fromtimestamp(file.stat().st_ctime),
                        'compressed': file.suffix == '.gz'
                    }
                    
                    # قراءة معلومات إضافية إذا توفرت
                    if info_file.exists():
                        try:
                            with open(info_file, 'r', encoding='utf-8') as f:
                                import json
                                extra_info = json.load(f)
                                backup_info.update(extra_info)
                        except:
                            pass
                    
                    backups.append(backup_info)
            
            # ترتيب حسب التاريخ (الأحدث أولاً)
            backups.sort(key=lambda b: b['created'], reverse=True)
            
        except Exception as e:
            logger.error(f"Failed to list backups: {e}")
        
        return backups
    
    def restore_backup(self, backup_filename: str) -> bool:
        """استعادة نسخة احتياطية"""
        try:
            backup_file = self.backup_dir / backup_filename
            
            if not backup_file.exists():
                logger.error(f"Backup file not found: {backup_filename}")
                return False
            
            # إنشاء نسخة احتياطية من قاعدة البيانات الحالية قبل الاستعادة
            current_backup = self.create_backup("pre_restore")
            if not current_backup:
                logger.error("Failed to create pre-restore backup")
                return False
            
            # استعادة النسخة الاحتياطية
            if backup_file.suffix == '.gz':
                success = self._restore_compressed_backup(backup_file)
            else:
                success = self._restore_regular_backup(backup_file)
            
            if success:
                logger.info(f"Database restored from backup: {backup_filename}")
                return True
            else:
                logger.error(f"Failed to restore from backup: {backup_filename}")
                return False
                
        except Exception as e:
            logger.error(f"Restore failed: {e}")
            return False
    
    def _restore_regular_backup(self, backup_file: Path) -> bool:
        """استعادة نسخة احتياطية عادية"""
        try:
            # نسخ ملف النسخة الاحتياطية لتصبح قاعدة البيانات الحالية
            shutil.copy2(backup_file, DB_PATH)
            return True
        except Exception as e:
            logger.error(f"Regular restore failed: {e}")
            return False
    
    def _restore_compressed_backup(self, backup_file: Path) -> bool:
        """استعادة نسخة احتياطية مضغوطة"""
        try:
            # فك ضغط النسخة الاحتياطية
            with gzip.open(backup_file, 'rb') as f_in:
                with open(DB_PATH, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            return True
        except Exception as e:
            logger.error(f"Compressed restore failed: {e}")
            return False
    
    def get_backup_status(self) -> Dict:
        """الحصول على حالة النسخ الاحتياطية"""
        try:
            backups = self.list_backups()
            
            return {
                'scheduler_running': self.running,
                'backup_count': len(backups),
                'latest_backup': backups[0] if backups else None,
                'total_backup_size': sum(b['size'] for b in backups),
                'backup_directory': str(self.backup_dir),
                'max_backups': self.max_backups,
                'compress_enabled': self.compress_backups
            }
        except Exception as e:
            logger.error(f"Failed to get backup status: {e}")
            return {'error': str(e)}

# إنشاء مثيل عام للاستخدام
backup_manager = BackupManager()