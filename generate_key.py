#!/usr/bin/env python3
"""
سكريبت لإنشاء مفتاح تشفير آمن للبوت
"""

from cryptography.fernet import Fernet
import base64

def generate_encryption_key():
    """إنشاء مفتاح تشفير جديد"""
    # إنشاء مفتاح جديد
    key = Fernet.generate_key()
    
    # تحويل إلى base64
    key_b64 = base64.b64encode(key).decode()
    
    print("🔐 تم إنشاء مفتاح تشفير جديد!")
    print(f"🔑 المفتاح: {key_b64}")
    print("\n📝 أضف هذا المفتاح إلى ملف .env:")
    print(f"ENCRYPTION_KEY_B64={key_b64}")
    
    return key_b64

if __name__ == "__main__":
    generate_encryption_key()