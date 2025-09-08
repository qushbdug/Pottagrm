#!/usr/bin/env python3
"""
Search Utilities for Pottagrm Enhanced Bot
"""

import logging
from src.core.database import get_db_connection

logger = logging.getLogger(__name__)

def search_networks(search_term, user_id=None):
    """Search networks by name or supplier code"""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Search by network name or supplier code
    if user_id:
        # Search user's own networks
        cursor.execute('''
            SELECT n.*, sc.supplier_code, u.full_name as supplier_name
            FROM networks n
            LEFT JOIN supplier_codes sc ON n.supplier_id = sc.supplier_id
            LEFT JOIN users u ON n.supplier_id = u.id
            WHERE n.supplier_id = ? AND (
                n.name LIKE ? OR
                sc.supplier_code LIKE ?
            )
            ORDER BY n.name
        ''', (user_id, f'%{search_term}%', f'%{search_term}%'))
    else:
        # Search all networks (for admins)
        cursor.execute('''
            SELECT n.*, sc.supplier_code, u.full_name as supplier_name
            FROM networks n
            LEFT JOIN supplier_codes sc ON n.supplier_id = sc.supplier_id
            LEFT JOIN users u ON n.supplier_id = u.id
            WHERE n.name LIKE ? OR sc.supplier_code LIKE ?
            ORDER BY n.name
        ''', (f'%{search_term}%', f'%{search_term}%'))

    results = cursor.fetchall()
    conn.close()
    return results

def search_cards_by_category(supplier_id, category=None, network_id=None):
    """Search cards by category and network"""
    conn = get_db_connection()
    cursor = conn.cursor()

    query = '''
        SELECT
            nc.*,
            n.name as network_name,
            ccr.category_name
        FROM network_cards nc
        LEFT JOIN networks n ON nc.network_id = n.id
        LEFT JOIN card_categories_ref ccr ON nc.card_category = ccr.category_value
        WHERE nc.supplier_id = ?
    '''

    params = [supplier_id]

    if category:
        query += ' AND nc.card_category = ?'
        params.append(category)

    if network_id:
        query += ' AND nc.network_id = ?'
        params.append(network_id)

    query += ' ORDER BY nc.card_category, nc.id'

    cursor.execute(query, params)
    results = cursor.fetchall()
    conn.close()
    return results
