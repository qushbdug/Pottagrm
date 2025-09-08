#!/usr/bin/env python3
"""
Transaction Utilities for Pottagrm Enhanced Bot
"""

import logging
import json
import uuid
from src.core.database import get_db_connection

logger = logging.getLogger(__name__)

def create_wallet_transaction(user_id: int, transaction_type: str, amount: float,
                            balance_before: float, balance_after: float,
                            description: str = None, reference_id: str = None,
                            metadata: dict = None) -> str:
    """Create a wallet transaction record"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        transaction_id = str(uuid.uuid4())
        metadata_json = json.dumps(metadata) if metadata else None

        cursor.execute('''
            INSERT INTO wallet_transactions
            (id, user_id, transaction_type, amount, balance_before, balance_after,
             reference_id, description, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (transaction_id, user_id, transaction_type, amount, balance_before,
              balance_after, reference_id, description, metadata_json))

        conn.commit()
        conn.close()
        return transaction_id
    except Exception as e:
        logger.error(f"Error creating wallet transaction: {e}")
        return None

def create_transaction(from_user: int, to_user: int, amount: float,
                      transaction_type: str, reference_id: str = None,
                      description: str = None, commission_amount: float = 0.0):
    """Create a transaction record"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        transaction_id = str(uuid.uuid4())

        cursor.execute('''
            INSERT INTO transactions
            (id, from_user, to_user, amount, type, reference_id, description, commission_amount)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (transaction_id, from_user, to_user, amount, transaction_type,
              reference_id, description, commission_amount))

        conn.commit()
        conn.close()
        return transaction_id
    except Exception as e:
        logger.error(f"Error creating transaction: {e}")
        return None
