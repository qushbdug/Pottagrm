#!/usr/bin/env python3
"""
Supplier Utilities for Pottagrm Enhanced Bot
"""

import logging
import random
import uuid
from src.core.database import get_db_connection

logger = logging.getLogger(__name__)

def generate_supplier_code():
    """Generate a unique 6-digit supplier code starting with 80"""
    import random
    conn = get_db_connection()
    cursor = conn.cursor()

    for _ in range(100):  # Try up to 100 times
        # Generate 6-digit code starting with 80
        code = '80' + ''.join(str(random.randint(0, 9)) for _ in range(4))

        # Check if code already exists
        cursor.execute('SELECT 1 FROM supplier_codes WHERE supplier_code = ?', (code,))
        if not cursor.fetchone():
            conn.close()
            return code

    conn.close()
    # If all attempts fail, use timestamp-based approach
    import time
    return '80' + str(int(time.time()))[-4:]

def get_or_create_supplier_code(supplier_id):
    """Get existing supplier code or create new one"""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Check if supplier already has a code
    cursor.execute('SELECT supplier_code FROM supplier_codes WHERE supplier_id = ?', (supplier_id,))
    result = cursor.fetchone()

    if result:
        conn.close()
        return result['supplier_code']

    # Create new code
    code = generate_supplier_code()
    code_id = str(uuid.uuid4())

    cursor.execute('''
        INSERT INTO supplier_codes (id, supplier_id, supplier_code)
        VALUES (?, ?, ?)
    ''', (code_id, supplier_id, code))

    conn.commit()
    conn.close()
    return code
