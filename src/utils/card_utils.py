#!/usr/bin/env python3
"""
Card and Inventory Utilities for Pottagrm Enhanced Bot
"""

import logging
import uuid
from src.core.database import get_db_connection

logger = logging.getLogger(__name__)

def validate_card_code(card_code):
    """Validate Yemen network card code (6-14 digits)"""
    if not card_code:
        return False, "رقم الكارت فارغ"

    # Remove any spaces or special characters
    cleaned_code = ''.join(filter(str.isdigit, str(card_code)))

    if len(cleaned_code) < 6:
        return False, "رقم الكارت يجب أن يحتوي على 6 أرقام على الأقل"

    if len(cleaned_code) > 14:
        return False, "رقم الكارت يجب ألا يزيد عن 14 رقم"

    return True, cleaned_code

def process_uploaded_cards(file_content, supplier_id, network_id, batch_id, selected_category=None):
    """Process uploaded cards from text or Excel file with category support"""
    import io

    conn = get_db_connection()
    cursor = conn.cursor()

    successful_cards = 0
    failed_cards = 0
    errors = []

    try:
        # Try to parse as text first
        lines = file_content.strip().split('\n')

        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            if not line:
                continue

            # Try to parse line format: "card_code,value,category" or "card_code,value" or just "card_code"
            parts = line.split(',')
            card_code = parts[0].strip()

            # Default value or from file
            if len(parts) > 1:
                try:
                    card_value = float(parts[1].strip())
                except ValueError:
                    card_value = 0.0
                    errors.append(f"السطر {line_num}: قيمة غير صحيحة '{parts[1]}', تم استخدام 0")
            else:
                card_value = 0.0

            # Category handling
            if len(parts) > 2:
                try:
                    card_category = int(parts[2].strip())
                    # Validate category
                    if card_category not in [200, 300, 500, 1000, 2000, 5000, 10000]:
                        card_category = selected_category or 200
                        errors.append(f"السطر {line_num}: فئة غير صحيحة '{parts[2]}', تم استخدام {card_category}")
                except ValueError:
                    card_category = selected_category or 200
                    errors.append(f"السطر {line_num}: فئة غير صحيحة '{parts[2]}', تم استخدام {card_category}")
            else:
                card_category = selected_category or 200

            # Auto-detect category from value if not specified
            if card_value > 0 and (selected_category is None and len(parts) <= 2):
                if card_value <= 200:
                    card_category = 200
                elif card_value <= 300:
                    card_category = 300
                elif card_value <= 500:
                    card_category = 500
                elif card_value <= 1000:
                    card_category = 1000
                elif card_value <= 2000:
                    card_category = 2000
                elif card_value <= 5000:
                    card_category = 5000
                else:
                    card_category = 10000

            # Validate card code
            is_valid, result = validate_card_code(card_code)
            if not is_valid:
                failed_cards += 1
                errors.append(f"السطر {line_num}: {result} - '{card_code}'")
                continue

            card_code = result

            # Check if card already exists
            cursor.execute('SELECT 1 FROM network_cards WHERE card_code = ?', (card_code,))
            if cursor.fetchone():
                failed_cards += 1
                errors.append(f"السطر {line_num}: الكارت موجود مسبقاً - '{card_code}'")
                continue

            # Insert card
            card_id = str(uuid.uuid4())
            cursor.execute('''
                INSERT INTO network_cards (id, supplier_id, network_id, card_code, card_value, card_category, upload_batch_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (card_id, supplier_id, network_id, card_code, card_value, card_category, batch_id))

            successful_cards += 1

        # Update batch statistics
        cursor.execute('''
            UPDATE card_upload_batches
            SET successful_cards = ?, failed_cards = ?, upload_status = ?, error_details = ?
            WHERE id = ?
        ''', (successful_cards, failed_cards,
              'completed' if failed_cards == 0 else 'completed_with_errors',
              '\n'.join(errors[:50]),  # Limit error details
              batch_id))

        conn.commit()

    except Exception as e:
        logger.error(f"Error processing uploaded cards: {e}")
        cursor.execute('''
            UPDATE card_upload_batches
            SET upload_status = 'failed', error_details = ?
            WHERE id = ?
        ''', (str(e), batch_id))
        conn.commit()
        raise

    finally:
        conn.close()

    return successful_cards, failed_cards, errors

def get_card_categories():
    """Get all available card categories"""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM card_categories_ref WHERE is_active = 1 ORDER BY display_order')
    categories = cursor.fetchall()
    conn.close()
    return categories

def get_cards_stats_by_category(supplier_id):
    """Get card statistics grouped by category"""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT
            nc.card_category,
            ccr.category_name,
            COUNT(*) as total_cards,
            SUM(CASE WHEN nc.is_sold = 0 THEN 1 ELSE 0 END) as available_cards,
            SUM(CASE WHEN nc.is_sold = 1 THEN 1 ELSE 0 END) as sold_cards,
            SUM(CASE WHEN nc.is_sold = 0 THEN nc.card_value ELSE 0 END) as available_value,
            SUM(CASE WHEN nc.is_sold = 1 THEN nc.card_value ELSE 0 END) as sold_value
        FROM network_cards nc
        LEFT JOIN card_categories_ref ccr ON nc.card_category = ccr.category_value
        WHERE nc.supplier_id = ?
        GROUP BY nc.card_category, ccr.category_name
        ORDER BY nc.card_category
    ''', (supplier_id,))

    stats = cursor.fetchall()
    conn.close()
    return stats

def update_inventory_stock(network_id: str, category_id: int, change: int) -> bool:
    """Update inventory stock count"""
    from datetime import datetime
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        inventory_id = f"{network_id}_{category_id}"

        cursor.execute('''
            INSERT OR IGNORE INTO product_inventory
            (id, network_id, category_id, stock_count)
            VALUES (?, ?, ?, 0)
        ''', (inventory_id, network_id, category_id))

        cursor.execute('''
            UPDATE product_inventory
            SET stock_count = stock_count + ?, last_updated = ?
            WHERE id = ?
        ''', (change, datetime.now(), inventory_id))

        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Error updating inventory: {e}")
        return False
