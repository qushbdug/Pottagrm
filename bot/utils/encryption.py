"""
نظام التشفير المحسن للبوت
"""

import os
import logging
from typing import Optional
from cryptography.fernet import Fernet
from bot.config import ENCRYPTION_KEY_ENV, ENCRYPTION_KEY_FILE

logger = logging.getLogger(__name__)

class EncryptionManager:
    """مدير التشفير للحفاظ على أمان البيانات"""
    
    def __init__(self):
        self.cipher_suite = self._load_cipher_suite()
    
    def _load_cipher_suite(self) -> Fernet:
        """تحميل مفتاح التشفير من متغير البيئة أو الملف"""
        key_b64: Optional[str] = os.getenv(ENCRYPTION_KEY_ENV)
        
        if key_b64 and key_b64.strip():
            key_bytes = key_b64.strip().encode()
        else:
            key_file = os.path.abspath(ENCRYPTION_KEY_FILE)
            if os.path.exists(key_file):
                with open(key_file, 'rb') as f:
                    key_bytes = f.read().strip()
            else:
                key_bytes = Fernet.generate_key()
                with open(key_file, 'wb') as f:
                    f.write(key_bytes)
                logger.warning(f'تم إنشاء مفتاح تشفير جديد في {key_file}. يُنصح بتعيين {ENCRYPTION_KEY_ENV} في بيئة الإنتاج.')
        
        return Fernet(key_bytes)
    
    def encrypt_data(self, data: str) -> str:
        """تشفير النص"""
        try:
            return self.cipher_suite.encrypt(data.encode()).decode()
        except Exception as e:
            logger.error(f"خطأ في التشفير: {e}")
            raise
    
    def decrypt_data(self, encrypted_data: str) -> str:
        """فك تشفير النص"""
        try:
            return self.cipher_suite.decrypt(encrypted_data.encode()).decode()
        except Exception as e:
            logger.error(f"خطأ في فك التشفير: {e}")
            raise

# إنشاء مثيل عام للتشفير
encryption_manager = EncryptionManager()

# دوال للاستخدام المباشر
def encrypt_data(data: str) -> str:
    """تشفير البيانات"""
    return encryption_manager.encrypt_data(data)

def decrypt_data(encrypted_data: str) -> str:
    """فك تشفير البيانات"""
    return encryption_manager.decrypt_data(encrypted_data)