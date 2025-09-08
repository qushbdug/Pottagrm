#!/usr/bin/env python3
"""
Crypto Utilities for Pottagrm Enhanced Bot
"""

import logging
import os
import base64
from typing import Optional
from cryptography.fernet import Fernet

# It's better to get the logger in the file that uses it.
logger = logging.getLogger(__name__)

# This constant is not defined anywhere, I will assume it's True and that the library is available.
CRYPTO_AVAILABLE = True

def _load_cipher_suite():
    """Load or generate encryption key for secure data storage"""
    if not CRYPTO_AVAILABLE:
        logger.warning("Cryptography library not available - using basic encoding")
        return None

    key_b64: Optional[str] = os.getenv('ENCRYPTION_KEY_B64')
    if key_b64 and key_b64.strip():
        key_bytes = key_b64.strip().encode()
    else:
        key_file = os.path.abspath('encryption.key')
        if os.path.exists(key_file):
            with open(key_file, 'rb') as f:
                key_bytes = f.read().strip()
        else:
            key_bytes = Fernet.generate_key()
            with open(key_file, 'wb') as f:
                f.write(key_bytes)
            logger.warning('Generated new encryption.key (development only). Set ENCRYPTION_KEY_B64 in production.')
    return Fernet(key_bytes)

cipher_suite = _load_cipher_suite()

def encrypt_data(data: str) -> str:
    """Encrypt sensitive data"""
    try:
        if cipher_suite:
            return cipher_suite.encrypt(data.encode()).decode()
        else:
            # Fallback to base64 encoding if crypto not available
            return base64.b64encode(data.encode()).decode()
    except Exception as e:
        logger.error(f"Encryption error: {e}")
        return data

def decrypt_data(encrypted_data: str) -> str:
    """Decrypt sensitive data"""
    try:
        if cipher_suite:
            return cipher_suite.decrypt(encrypted_data.encode()).decode()
        else:
            # Fallback to base64 decoding if crypto not available
            return base64.b64decode(encrypted_data.encode()).decode()
    except Exception as e:
        logger.error(f"Decryption error: {e}")
        return encrypted_data
