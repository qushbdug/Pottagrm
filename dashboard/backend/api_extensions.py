#!/usr/bin/env python3
"""
Yemen Net Bot Dashboard - API Extensions
Additional API endpoints for advanced dashboard functionality
"""

import os
import sys
import sqlite3
import json
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify
from functools import wraps

# Add parent directory to path for bot modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../bot_modules'))

try:
    from bot_modules.config import BOT_TOKEN, DB_PATH
    from bot_modules.database import get_db_connection
except ImportError:
    # Fallback values
    BOT_TOKEN = '7766964799:AAHex-hGfjPX6g_R2aZ7-UPrgnFxQKAjSa0'
    DB_PATH = '../../yemen_net.db'

# Create blueprint
api_bp = Blueprint('api_extensions', __name__)

class DashboardAnalytics:
    """Analytics and reporting functions"""
    
    @staticmethod
    def get_user_growth_stats(days=30):
        """Get user growth statistics"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Get daily user registrations for the last N days
            cursor.execute("""
                SELECT 
                    DATE(created_at) as date,
                    COUNT(*) as new_users
                FROM users 
                WHERE created_at >= datetime('now', '-{} days')
                GROUP BY DATE(created_at)
                ORDER BY date
            """.format(days))
            
            growth_data = cursor.fetchall()
            conn.close()
            
            return [
                {
                    'date': row[0],
                    'new_users': row[1]
                }
                for row in growth_data
            ]
        except Exception as e:
            print(f"Error getting user growth stats: {e}")
            return []
    
    @staticmethod
    def get_revenue_stats(days=30):
        """Get revenue statistics"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Get daily revenue for the last N days
            cursor.execute("""
                SELECT 
                    DATE(created_at) as date,
                    SUM(amount) as daily_revenue,
                    COUNT(*) as transaction_count
                FROM transactions 
                WHERE created_at >= datetime('now', '-{} days')
                    AND type = 'purchase' 
                    AND status = 'completed'
                GROUP BY DATE(created_at)
                ORDER BY date
            """.format(days))
            
            revenue_data = cursor.fetchall()
            conn.close()
            
            return [
                {
                    'date': row[0],
                    'revenue': float(row[1]) if row[1] else 0,
                    'transactions': row[2]
                }
                for row in revenue_data
            ]
        except Exception as e:
            print(f"Error getting revenue stats: {e}")
            return []
    
    @staticmethod
    def get_top_customers(limit=10):
        """Get top customers by spending"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    u.full_name,
                    u.phone,
                    SUM(t.amount) as total_spent,
                    COUNT(t.id) as transaction_count
                FROM users u
                JOIN transactions t ON u.id = t.user_id
                WHERE t.type = 'purchase' AND t.status = 'completed'
                GROUP BY u.id, u.full_name, u.phone
                ORDER BY total_spent DESC
                LIMIT ?
            """, (limit,))
            
            top_customers = cursor.fetchall()
            conn.close()
            
            return [
                {
                    'name': row[0],
                    'phone': row[1],
                    'total_spent': float(row[2]),
                    'transaction_count': row[3]
                }
                for row in top_customers
            ]
        except Exception as e:
            print(f"Error getting top customers: {e}")
            return []

@api_bp.route('/analytics/growth', methods=['GET'])
def get_growth_analytics():
    """Get user growth analytics"""
    try:
        days = int(request.args.get('days', 30))
        growth_data = DashboardAnalytics.get_user_growth_stats(days)
        
        return jsonify({
            'success': True,
            'data': growth_data
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api_bp.route('/analytics/revenue', methods=['GET'])
def get_revenue_analytics():
    """Get revenue analytics"""
    try:
        days = int(request.args.get('days', 30))
        revenue_data = DashboardAnalytics.get_revenue_stats(days)
        
        return jsonify({
            'success': True,
            'data': revenue_data
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api_bp.route('/analytics/top-customers', methods=['GET'])
def get_top_customers():
    """Get top customers"""
    try:
        limit = int(request.args.get('limit', 10))
        top_customers = DashboardAnalytics.get_top_customers(limit)
        
        return jsonify({
            'success': True,
            'data': top_customers
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api_bp.route('/system/health', methods=['GET'])
def system_health():
    """Get system health status"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check database connectivity
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]
        
        # Check recent activity
        cursor.execute("""
            SELECT COUNT(*) FROM transactions 
            WHERE created_at >= datetime('now', '-1 hour')
        """)
        recent_transactions = cursor.fetchone()[0]
        
        # Check bot status (simplified)
        bot_status = "online"  # You can implement actual bot status check
        
        conn.close()
        
        health_status = {
            'database': 'healthy',
            'bot_status': bot_status,
            'user_count': user_count,
            'recent_activity': recent_transactions,
            'last_check': datetime.now().isoformat()
        }
        
        return jsonify({
            'success': True,
            'health': health_status
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'health': {
                'database': 'error',
                'bot_status': 'unknown',
                'last_check': datetime.now().isoformat()
            }
        }), 500

@api_bp.route('/users/<int:user_id>/transactions', methods=['GET'])
def get_user_transactions(user_id):
    """Get transactions for a specific user"""
    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 20))
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get total count
        cursor.execute("SELECT COUNT(*) FROM transactions WHERE user_id = ?", (user_id,))
        total_count = cursor.fetchone()[0]
        
        # Get transactions with pagination
        offset = (page - 1) * per_page
        cursor.execute("""
            SELECT id, type, amount, status, description, created_at
            FROM transactions 
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        """, (user_id, per_page, offset))
        
        transactions = cursor.fetchall()
        conn.close()
        
        return jsonify({
            'success': True,
            'transactions': [
                {
                    'id': row[0],
                    'type': row[1],
                    'amount': float(row[2]),
                    'status': row[3],
                    'description': row[4],
                    'created_at': row[5]
                }
                for row in transactions
            ],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total_count,
                'pages': (total_count + per_page - 1) // per_page
            }
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api_bp.route('/cards/inventory', methods=['GET'])
def get_cards_inventory():
    """Get cards inventory status"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get card inventory by network
        cursor.execute("""
            SELECT 
                n.name as network_name,
                COUNT(c.id) as total_cards,
                SUM(CASE WHEN c.status = 'available' THEN 1 ELSE 0 END) as available_cards,
                SUM(CASE WHEN c.status = 'sold' THEN 1 ELSE 0 END) as sold_cards,
                AVG(c.price) as avg_price
            FROM networks n
            LEFT JOIN cards c ON n.id = c.network_id
            GROUP BY n.id, n.name
            ORDER BY n.name
        """)
        
        inventory_data = cursor.fetchall()
        conn.close()
        
        return jsonify({
            'success': True,
            'inventory': [
                {
                    'network_name': row[0],
                    'total_cards': row[1] or 0,
                    'available_cards': row[2] or 0,
                    'sold_cards': row[3] or 0,
                    'avg_price': float(row[4]) if row[4] else 0
                }
                for row in inventory_data
            ]
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api_bp.route('/settings/bot-config', methods=['GET', 'POST'])
def bot_configuration():
    """Get or update bot configuration"""
    try:
        if request.method == 'GET':
            # Get current configuration
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT key, value FROM settings")
            settings = cursor.fetchall()
            conn.close()
            
            config = {}
            for setting in settings:
                try:
                    config[setting[0]] = json.loads(setting[1])
                except:
                    config[setting[0]] = setting[1]
            
            return jsonify({
                'success': True,
                'config': config
            })
            
        else:  # POST - Update configuration
            data = request.get_json()
            
            conn = get_db_connection()
            cursor = conn.cursor()
            
            for key, value in data.items():
                # Convert value to JSON string if it's not a string
                if isinstance(value, (dict, list)):
                    value_str = json.dumps(value)
                else:
                    value_str = str(value)
                
                cursor.execute("""
                    INSERT OR REPLACE INTO settings (key, value, updated_at)
                    VALUES (?, ?, ?)
                """, (key, value_str, datetime.now()))
            
            conn.commit()
            conn.close()
            
            return jsonify({
                'success': True,
                'message': 'Configuration updated successfully'
            })
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api_bp.route('/logs/recent', methods=['GET'])
def get_recent_logs():
    """Get recent system logs"""
    try:
        limit = int(request.args.get('limit', 50))
        level = request.args.get('level', 'all')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        where_clause = ""
        params = []
        
        if level != 'all':
            where_clause = "WHERE level = ?"
            params.append(level)
        
        cursor.execute(f"""
            SELECT timestamp, level, message, details
            FROM system_logs 
            {where_clause}
            ORDER BY timestamp DESC 
            LIMIT ?
        """, params + [limit])
        
        logs = cursor.fetchall()
        conn.close()
        
        return jsonify({
            'success': True,
            'logs': [
                {
                    'timestamp': row[0],
                    'level': row[1],
                    'message': row[2],
                    'details': row[3]
                }
                for row in logs
            ]
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api_bp.route('/backup/create', methods=['POST'])
def create_backup():
    """Create database backup"""
    try:
        backup_name = f"yemen_net_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        backup_path = f"../../{backup_name}"
        
        # Copy database file
        import shutil
        shutil.copy2(DB_PATH, backup_path)
        
        return jsonify({
            'success': True,
            'message': 'Backup created successfully',
            'backup_file': backup_name
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api_bp.route('/maintenance/cleanup', methods=['POST'])
def maintenance_cleanup():
    """Perform database maintenance and cleanup"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Clean up old logs (older than 30 days)
        cursor.execute("""
            DELETE FROM system_logs 
            WHERE timestamp < datetime('now', '-30 days')
        """)
        deleted_logs = cursor.rowcount
        
        # Clean up old temporary data
        cursor.execute("""
            DELETE FROM wallet_transactions 
            WHERE created_at < datetime('now', '-90 days') 
            AND status = 'failed'
        """)
        deleted_transactions = cursor.rowcount
        
        # Vacuum database to reclaim space
        cursor.execute("VACUUM")
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Maintenance completed successfully',
            'cleanup_stats': {
                'deleted_logs': deleted_logs,
                'deleted_transactions': deleted_transactions
            }
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500