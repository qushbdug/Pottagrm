#!/usr/bin/env python3
"""
User Utilities for Pottagrm Enhanced Bot
"""

import logging
from datetime import datetime
from typing import List, Dict
from src.core.database import get_db_connection
from src.utils.system_utils import log_activity

logger = logging.getLogger(__name__)

def get_user(telegram_id: int):
    """Get user by telegram ID"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE telegram_id = ?', (telegram_id,))
        user = cursor.fetchone()
        conn.close()
        return user
    except Exception as e:
        logger.error(f"Error getting user: {e}")
        return None

def get_user_by_id(user_id: int):
    """Get user by internal database ID"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
        user = cursor.fetchone()
        conn.close()
        return user
    except Exception as e:
        logger.error(f"Error getting user by ID: {e}")
        return None

def update_user_activity(user_id: int):
    """Update user's last activity timestamp"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET last_activity = ? WHERE id = ?',
                      (datetime.now(), user_id))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Error updating user activity: {e}")

def get_user_permissions(user_id: int) -> List[str]:
    """Get user permissions list"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT permission_name FROM user_permissions
            WHERE user_id = ? AND is_active = 1
            AND (expires_at IS NULL OR expires_at > ?)
        ''', (user_id, datetime.now()))

        permissions = [row[0] for row in cursor.fetchall()]
        conn.close()
        return permissions
    except Exception as e:
        logger.error(f"Error getting user permissions: {e}")
        return []

def has_permission(user_id: int, permission: str) -> bool:
    """Check if user has specific permission"""
    permissions = get_user_permissions(user_id)
    return permission in permissions

def grant_user_permission(user_id: int, permission: str, granted_by: int, expires_at: datetime = None) -> bool:
    """Grant a permission to a user"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if permission already exists
        cursor.execute('''
            SELECT id FROM user_permissions
            WHERE user_id = ? AND permission_name = ? AND is_active = 1
        ''', (user_id, permission))

        if cursor.fetchone():
            conn.close()
            return False  # Permission already exists

        cursor.execute('''
            INSERT INTO user_permissions (user_id, permission_name, granted_by, expires_at)
            VALUES (?, ?, ?, ?)
        ''', (user_id, permission, granted_by, expires_at))

        conn.commit()
        conn.close()

        # Log the permission grant
        log_activity(granted_by, 'permission_grant', f'Granted permission {permission} to user {user_id}')

        return True
    except Exception as e:
        logger.error(f"Error granting permission: {e}")
        return False

def is_super_admin(user_id: int) -> bool:
    """Check if user is super admin"""
    user = get_user_by_id(user_id)
    return user and user['role'] == 'super_admin'

def is_admin(user_id: int) -> bool:
    """Check if user is admin or super admin"""
    user = get_user_by_id(user_id)
    return user and user['role'] in ['admin', 'super_admin']

def recalc_and_set_user_balance(user_id: int):
    """Recalculate and update user balance"""
    import time
    max_retries = 3
    retry_delay = 0.1

    for attempt in range(max_retries):
        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            # Calculate balance from transactions
            cursor.execute('''
                SELECT
                    COALESCE(SUM(CASE WHEN to_user = ? THEN amount ELSE 0 END), 0) as credits,
                    COALESCE(SUM(CASE WHEN from_user = ? THEN amount ELSE 0 END), 0) as debits
                FROM transactions
                WHERE to_user = ? OR from_user = ?
            ''', (user_id, user_id, user_id, user_id))

            result = cursor.fetchone()
            credits = result[0] if result[0] else 0
            debits = result[1] if result[1] else 0
            new_balance = credits - debits

            # Update user balance
            cursor.execute('UPDATE users SET balance = ? WHERE id = ?', (new_balance, user_id))

            conn.commit()
            conn.close()
            return new_balance

        except Exception as e:
            try:
                if 'conn' in locals():
                    conn.close()
            except:
                pass

            if "database is locked" in str(e).lower() and attempt < max_retries - 1:
                time.sleep(retry_delay)
                retry_delay = min(retry_delay * 1.5, 0.5)
                continue
            else:
                if attempt == max_retries - 1:
                    logger.debug(f"Balance calculation skipped for user {user_id} (database busy)")
                return 0

    return 0

def calculate_user_rating(user_id: int) -> Dict:
    """Calculate and update user rating summary"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT rating, COUNT(*) as count FROM ratings
            WHERE rated_user_id = ? AND is_visible = 1
            GROUP BY rating
        ''', (user_id,))

        rating_counts = {i: 0 for i in range(1, 6)}
        total_ratings = 0
        total_score = 0

        for rating, count in cursor.fetchall():
            rating_counts[rating] = count
            total_ratings += count
            total_score += rating * count

        average_rating = total_score / total_ratings if total_ratings > 0 else 0.0

        cursor.execute('''
            INSERT OR REPLACE INTO user_ratings_summary
            (user_id, total_ratings, average_rating, rating_1_count, rating_2_count,
             rating_3_count, rating_4_count, rating_5_count, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, total_ratings, average_rating, rating_counts[1],
              rating_counts[2], rating_counts[3], rating_counts[4],
              rating_counts[5], datetime.now()))

        conn.commit()
        conn.close()

        return {
            'total_ratings': total_ratings,
            'average_rating': round(average_rating, 2),
            'rating_distribution': rating_counts
        }
    except Exception as e:
        logger.error(f"Error calculating user rating: {e}")
        return {'total_ratings': 0, 'average_rating': 0.0, 'rating_distribution': {}}
