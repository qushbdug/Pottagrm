#!/usr/bin/env python3
"""
Database migration utility for Yemen Net Bot.

Purpose:
- Create a timestamped backup of the SQLite DB
- Normalize schema for networks, card_categories, and cards
- Keep existing data whenever possible

Notes:
- Reads DB path from env DB_PATH or defaults to ./yemen_net.db
- Does NOT touch bot token or any config files
"""

import os
import shutil
import sqlite3
from datetime import datetime
from typing import Dict, Any, List, Tuple


def get_db_path() -> str:
    return os.getenv('DB_PATH', os.path.abspath('yemen_net.db'))


def backup_db(db_path: str) -> str:
    backups_dir = os.path.abspath('backups')
    os.makedirs(backups_dir, exist_ok=True)
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    base = os.path.basename(db_path)
    dest = os.path.join(backups_dir, f"{base}.{ts}.bak")
    shutil.copy2(db_path, dest)
    return dest


def fetch_table_info(cur: sqlite3.Cursor, table: str) -> List[Tuple[Any, ...]]:
    cur.execute(f"PRAGMA table_info({table})")
    return cur.fetchall()


def column_exists(columns: List[Tuple[Any, ...]], name: str) -> bool:
    return any(col[1] == name for col in columns)


def get_column_type(columns: List[Tuple[Any, ...]], name: str) -> str:
    for col in columns:
        if col[1] == name:
            return (col[2] or '').upper()
    return ''


def ensure_networks_schema(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='networks'")
    if not cur.fetchone():
        # Create fresh with unified schema
        cur.execute(
            '''
            CREATE TABLE IF NOT EXISTS networks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                supplier_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                provider TEXT,
                description TEXT,
                logo_url TEXT,
                city TEXT,
                location TEXT,
                created_by INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1,
                is_approved BOOLEAN DEFAULT 0,
                approved_at TIMESTAMP,
                approved_by INTEGER,
                network_code TEXT UNIQUE
            )
            '''
        )
        return

    cols = fetch_table_info(cur, 'networks')
    id_type = get_column_type(cols, 'id')
    needs_recreate = False
    # Recreate if id not INTEGER or critical columns missing
    required_cols = ['supplier_id', 'name', 'provider', 'city', 'location', 'is_active', 'is_approved', 'network_code']
    if 'INTEGER' not in id_type:
        needs_recreate = True
    for rc in required_cols:
        if not column_exists(cols, rc):
            needs_recreate = True
            break

    if not needs_recreate:
        # Add missing non-critical columns if any
        additions = [
            ('description', 'TEXT'),
            ('logo_url', 'TEXT'),
            ('created_by', 'INTEGER'),
            ('updated_at', "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
            ('approved_at', 'TIMESTAMP'),
            ('approved_by', 'INTEGER'),
        ]
        for name, decl in additions:
            if not column_exists(cols, name):
                try:
                    cur.execute(f"ALTER TABLE networks ADD COLUMN {name} {decl}")
                except sqlite3.OperationalError:
                    pass
        return

    # Recreate table preserving data
    conn.execute('PRAGMA foreign_keys=OFF')
    try:
        cur.execute('''
            CREATE TABLE IF NOT EXISTS networks_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                supplier_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                provider TEXT,
                description TEXT,
                logo_url TEXT,
                city TEXT,
                location TEXT,
                created_by INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1,
                is_approved BOOLEAN DEFAULT 0,
                approved_at TIMESTAMP,
                approved_by INTEGER,
                network_code TEXT UNIQUE
            )
        ''')

        # Map of old id to new id if needed
        id_map: Dict[Any, int] = {}

        # Build select of existing columns
        select_cols = []
        for c in ['id', 'supplier_id', 'name', 'provider', 'description', 'logo_url', 'city', 'location', 'created_by', 'created_at', 'is_active', 'is_approved', 'approved_at', 'approved_by', 'network_code']:
            if column_exists(cols, c):
                select_cols.append(c)
        cur.execute(f"SELECT {', '.join(select_cols)} FROM networks")
        rows = cur.fetchall()

        for row in rows:
            rowd = {select_cols[i]: row[i] for i in range(len(select_cols))}
            # Attempt to keep numeric id
            provided_id = rowd.get('id')
            insert_with_id = None
            if provided_id is not None:
                try:
                    # use same id if numeric and unique
                    insert_with_id = int(provided_id)
                except Exception:
                    insert_with_id = None

            fields = {
                'supplier_id': rowd.get('supplier_id'),
                'name': rowd.get('name'),
                'provider': rowd.get('provider'),
                'description': rowd.get('description'),
                'logo_url': rowd.get('logo_url'),
                'city': rowd.get('city'),
                'location': rowd.get('location'),
                'created_by': rowd.get('created_by'),
                'created_at': rowd.get('created_at'),
                'updated_at': rowd.get('created_at'),
                'is_active': rowd.get('is_active', 1),
                'is_approved': rowd.get('is_approved', 0),
                'approved_at': rowd.get('approved_at'),
                'approved_by': rowd.get('approved_by'),
                'network_code': rowd.get('network_code'),
            }

            cols_part = ','.join(fields.keys())
            placeholders = ','.join(['?'] * len(fields))
            if insert_with_id is not None:
                cur.execute(
                    f"INSERT INTO networks (id,{cols_part}) VALUES (?,{placeholders})",
                    (insert_with_id, *fields.values())
                )
                new_id = insert_with_id
            else:
                cur.execute(
                    f"INSERT INTO networks ({cols_part}) VALUES ({placeholders})",
                    tuple(fields.values())
                )
                new_id = cur.lastrowid

            old_id = rowd.get('id')
            if old_id is not None:
                id_map[old_id] = new_id

        # Replace table
        cur.execute('ALTER TABLE networks RENAME TO networks_old')
        cur.execute('ALTER TABLE networks_new RENAME TO networks')

        # Fix child references where applicable
        # card_categories.network_id
        child_tables = [
            ('card_categories', 'network_id'),
            ('network_cards', 'network_id'),
        ]
        for table, col in child_tables:
            cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
            if cur.fetchone():
                # Update each unique old id
                for old_id, new_id in id_map.items():
                    try:
                        cur.execute(f"UPDATE {table} SET {col} = ? WHERE {col} = ?", (new_id, old_id))
                    except sqlite3.OperationalError:
                        pass

        # Drop old
        cur.execute('DROP TABLE IF EXISTS networks_old')
    finally:
        conn.execute('PRAGMA foreign_keys=ON')


def ensure_card_categories_schema(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='card_categories'")
    if not cur.fetchone():
        cur.execute('''
            CREATE TABLE IF NOT EXISTS card_categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                network_id INTEGER,
                name TEXT,
                value REAL NOT NULL,
                price REAL NOT NULL,
                currency TEXT DEFAULT 'YER',
                is_available BOOLEAN DEFAULT 1,
                stock_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        return

    cols = fetch_table_info(cur, 'card_categories')
    # Add missing columns
    additions = [
        ('name', 'TEXT'),
        ('currency', "TEXT DEFAULT 'YER'"),
        ('stock_count', 'INTEGER DEFAULT 0'),
        ('updated_at', "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
    ]
    for name, decl in additions:
        if not column_exists(cols, name):
            try:
                cur.execute(f"ALTER TABLE card_categories ADD COLUMN {name} {decl}")
            except sqlite3.OperationalError:
                pass


def ensure_cards_schema(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='cards'")
    if not cur.fetchone():
        cur.execute('''
            CREATE TABLE IF NOT EXISTS cards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category_id INTEGER,
                card_number TEXT NOT NULL,
                serial_number TEXT,
                expiry_date TEXT,
                is_sold BOOLEAN DEFAULT 0,
                sold_to INTEGER,
                sold_at TIMESTAMP,
                uploaded_by INTEGER,
                uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        return

    cols = fetch_table_info(cur, 'cards')
    # Old schema detection: presence of 'code' or 'is_used' or TEXT PK id
    id_type = get_column_type(cols, 'id')
    is_old = column_exists(cols, 'code') or column_exists(cols, 'is_used') or ('TEXT' in id_type)
    if not is_old:
        # Ensure columns exist (no-op if already there)
        additions = [
            ('card_number', 'TEXT'),
            ('serial_number', 'TEXT'),
            ('is_sold', 'BOOLEAN DEFAULT 0'),
            ('sold_to', 'INTEGER'),
            ('sold_at', 'TIMESTAMP'),
            ('uploaded_by', 'INTEGER'),
            ('uploaded_at', "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
        ]
        for name, decl in additions:
            if not column_exists(cols, name):
                try:
                    cur.execute(f"ALTER TABLE cards ADD COLUMN {name} {decl}")
                except sqlite3.OperationalError:
                    pass
        return

    conn.execute('PRAGMA foreign_keys=OFF')
    try:
        cur.execute('''
            CREATE TABLE IF NOT EXISTS cards_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category_id INTEGER,
                card_number TEXT NOT NULL,
                serial_number TEXT,
                expiry_date TEXT,
                is_sold BOOLEAN DEFAULT 0,
                sold_to INTEGER,
                sold_at TIMESTAMP,
                uploaded_by INTEGER,
                uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        select_cols = []
        for c in ['id', 'category_id', 'code', 'card_number', 'serial_number', 'expiry_date', 'is_used', 'is_sold', 'sold_to', 'sold_at', 'uploaded_by', 'added_at', 'uploaded_at']:
            if column_exists(cols, c):
                select_cols.append(c)
        cur.execute(f"SELECT {', '.join(select_cols)} FROM cards")
        rows = cur.fetchall()

        for row in rows:
            rowd = {select_cols[i]: row[i] for i in range(len(select_cols))}
            card_number = rowd.get('card_number') or rowd.get('code')
            is_sold = rowd.get('is_sold')
            if is_sold is None:
                is_sold = int(rowd.get('is_used') or 0)
            uploaded_at = rowd.get('uploaded_at') or rowd.get('added_at')
            cur.execute(
                '''INSERT INTO cards_new (category_id, card_number, serial_number, expiry_date, is_sold, sold_to, sold_at, uploaded_by, uploaded_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (
                    rowd.get('category_id'),
                    card_number,
                    rowd.get('serial_number'),
                    rowd.get('expiry_date'),
                    is_sold,
                    rowd.get('sold_to'),
                    rowd.get('sold_at'),
                    rowd.get('uploaded_by'),
                    uploaded_at,
                )
            )

        cur.execute('ALTER TABLE cards RENAME TO cards_old')
        cur.execute('ALTER TABLE cards_new RENAME TO cards')
        cur.execute('DROP TABLE IF EXISTS cards_old')
    finally:
        conn.execute('PRAGMA foreign_keys=ON')


def main() -> None:
    db_path = get_db_path()
    if not os.path.exists(db_path):
        print(f"[ERROR] DB file not found: {db_path}")
        return

    backup = backup_db(db_path)
    print(f"[OK] Backup created: {backup}")

    conn = sqlite3.connect(db_path)
    try:
        ensure_networks_schema(conn)
        ensure_card_categories_schema(conn)
        ensure_cards_schema(conn)
        conn.commit()
        print("[OK] Migration completed successfully.")
    except Exception as e:
        conn.rollback()
        print(f"[ERROR] Migration failed: {e}")
        print(f"[INFO] You can restore from backup: {backup}")
        raise
    finally:
        conn.close()


if __name__ == '__main__':
    main()

