#!/usr/bin/env python3
"""
Notification Utilities for Pottagrm Enhanced Bot
"""

import logging
import json
import uuid
from src.core.database import get_db_connection

logger = logging.getLogger(__name__)

def send_smart_notification(user_id: int, notification_type: str, title: str,
                          message: str, priority: str = 'normal',
                          metadata: dict = None) -> str:
    """Send a smart notification to a user"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Check user notification preferences
        cursor.execute('''
            SELECT * FROM notification_preferences WHERE user_id = ?
        ''', (user_id,))
        prefs = cursor.fetchone()

        # Default preferences if not set
        if not prefs:
            cursor.execute('''
                INSERT INTO notification_preferences (user_id) VALUES (?)
            ''', (user_id,))
            conn.commit()

        notification_id = str(uuid.uuid4())
        metadata_json = json.dumps(metadata) if metadata else None

        cursor.execute('''
            INSERT INTO smart_notifications
            (id, user_id, notification_type, title, message, priority, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (notification_id, user_id, notification_type, title, message,
              priority, metadata_json))

        conn.commit()
        conn.close()
        return notification_id
    except Exception as e:
        logger.error(f"Error sending smart notification: {e}")
        return None
