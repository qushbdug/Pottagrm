#!/usr/bin/env python3
"""
System Utilities for Pottagrm Enhanced Bot
"""

import logging
import json
import uuid
from src.core.database import get_db_connection

logger = logging.getLogger(__name__)

def log_system_action(user_id: int, action: str, details: str):
    """Log system action for audit trail"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO system_logs (user_id, action, details)
            VALUES (?, ?, ?)
        ''', (user_id, action, details))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Error logging system action: {e}")

def log_activity(user_id: int, activity_type: str, description: str, metadata: dict = None):
    """Log user activity for enhanced tracking"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        activity_id = str(uuid.uuid4())
        metadata_json = json.dumps(metadata) if metadata else None

        cursor.execute('''
            INSERT INTO activity_logs (id, user_id, activity_type, description, metadata)
            VALUES (?, ?, ?, ?, ?)
        ''', (activity_id, user_id, activity_type, description, metadata_json))

        conn.commit()
        conn.close()
    except Exception as e:
        # Silently fail for logging to avoid disrupting user experience
        logger.error(f"Error logging activity: {e}")
        pass
