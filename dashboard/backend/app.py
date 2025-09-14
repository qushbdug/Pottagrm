#!/usr/bin/env python3
"""
Yemen Net Bot - Web Dashboard Backend
Flask API Server with Authentication and Bot Integration
"""

import os
import sys
import sqlite3
import secrets
import hashlib
import json
from datetime import datetime, timedelta
from functools import wraps

from flask import Flask, request, jsonify, render_template, session, send_from_directory
from flask_cors import CORS
from flask_jwt_extended import JWTManager, jwt_required, create_access_token, get_jwt_identity
import requests
from cryptography.fernet import Fernet

# Add parent directory to path for bot modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../bot_modules'))

# Import API extensions
from api_extensions import api_bp

try:
    from bot_modules.config import BOT_TOKEN, DB_PATH
    from bot_modules.database import get_db_connection
    from bot_modules.utils import get_user
except ImportError as e:
    print(f"Error importing bot modules: {e}")
    # Fallback values
    BOT_TOKEN = '7766964799:AAHex-hGfjPX6g_R2aZ7-UPrgnFxQKAjSa0'
    DB_PATH = '../../yemen_net.db'

# Initialize Flask app
app = Flask(__name__, 
            template_folder='../templates',
            static_folder='../static')

# Configuration
app.config['SECRET_KEY'] = secrets.token_hex(32)
app.config['JWT_SECRET_KEY'] = secrets.token_hex(32)
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=8)
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=8)

# Initialize extensions
CORS(app, origins=["http://localhost:5000", "http://127.0.0.1:5000"])
jwt = JWTManager(app)

# Register blueprints
app.register_blueprint(api_bp, url_prefix='/api')

# Global variables for OTP storage (in production, use Redis or database)
otp_storage = {}

class DashboardAuth:
    """Authentication system for dashboard"""
    
    @staticmethod
    def generate_otp():
        """Generate 6-digit OTP"""
        return str(secrets.randbelow(900000) + 100000)
    
    @staticmethod
    def send_telegram_otp(telegram_id, otp_code):
        """Send OTP via Telegram bot"""
        try:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
            message = f"""
🔐 **رمز التحقق - لوحة التحكم**

🔢 **رمز التحقق:** `{otp_code}`

⚠️ **تنبيه أمني:**
• هذا الرمز صالح لمدة 5 دقائق فقط
• لا تشارك هذا الرمز مع أي شخص
• إذا لم تطلب هذا الرمز، تجاهل هذه الرسالة

🛡️ **Yemen Net Bot Dashboard**
            """
            
            payload = {
                'chat_id': telegram_id,
                'text': message,
                'parse_mode': 'Markdown'
            }
            
            response = requests.post(url, json=payload, timeout=10)
            return response.status_code == 200
        except Exception as e:
            print(f"Error sending OTP: {e}")
            return False
    
    @staticmethod
    def is_super_admin(telegram_id):
        """Check if user is super admin"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT role FROM users 
                WHERE telegram_id = ? AND role = 'super_admin'
            """, (telegram_id,))
            
            result = cursor.fetchone()
            conn.close()
            
            return result is not None
        except Exception as e:
            print(f"Error checking super admin: {e}")
            return False

# Authentication decorator
def super_admin_required(f):
    @wraps(f)
    @jwt_required()
    def decorated_function(*args, **kwargs):
        current_user_id = get_jwt_identity()
        if not DashboardAuth.is_super_admin(current_user_id):
            return jsonify({'error': 'Super admin access required'}), 403
        return f(*args, **kwargs)
    return decorated_function

# Routes
@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('index.html')

@app.route('/login')
def login_page():
    """Login page"""
    return render_template('login.html')

@app.route('/api/auth/request-otp', methods=['POST'])
def request_otp():
    """Request OTP for authentication"""
    try:
        data = request.get_json()
        telegram_id = data.get('telegram_id')
        
        if not telegram_id:
            return jsonify({'error': 'Telegram ID is required'}), 400
        
        # Check if user is super admin
        if not DashboardAuth.is_super_admin(telegram_id):
            return jsonify({'error': 'Access denied. Super admin only.'}), 403
        
        # Generate OTP
        otp_code = DashboardAuth.generate_otp()
        
        # Store OTP with expiration (5 minutes)
        otp_storage[telegram_id] = {
            'code': otp_code,
            'expires': datetime.now() + timedelta(minutes=5),
            'attempts': 0
        }
        
        # Send OTP via Telegram
        if DashboardAuth.send_telegram_otp(telegram_id, otp_code):
            return jsonify({
                'success': True,
                'message': 'OTP sent successfully to your Telegram'
            })
        else:
            return jsonify({'error': 'Failed to send OTP'}), 500
            
    except Exception as e:
        print(f"Error in request_otp: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/auth/verify-otp', methods=['POST'])
def verify_otp():
    """Verify OTP and create JWT token"""
    try:
        data = request.get_json()
        telegram_id = data.get('telegram_id')
        otp_code = data.get('otp_code')
        
        if not telegram_id or not otp_code:
            return jsonify({'error': 'Telegram ID and OTP are required'}), 400
        
        # Check if OTP exists
        if telegram_id not in otp_storage:
            return jsonify({'error': 'OTP not found or expired'}), 400
        
        otp_data = otp_storage[telegram_id]
        
        # Check expiration
        if datetime.now() > otp_data['expires']:
            del otp_storage[telegram_id]
            return jsonify({'error': 'OTP expired'}), 400
        
        # Check attempts
        if otp_data['attempts'] >= 3:
            del otp_storage[telegram_id]
            return jsonify({'error': 'Too many attempts'}), 400
        
        # Verify OTP
        if otp_code != otp_data['code']:
            otp_storage[telegram_id]['attempts'] += 1
            return jsonify({'error': 'Invalid OTP'}), 400
        
        # OTP verified, create JWT token
        access_token = create_access_token(identity=telegram_id)
        
        # Clean up OTP
        del otp_storage[telegram_id]
        
        return jsonify({
            'success': True,
            'access_token': access_token,
            'message': 'Login successful'
        })
        
    except Exception as e:
        print(f"Error in verify_otp: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/dashboard/stats', methods=['GET'])
@super_admin_required
def get_dashboard_stats():
    """Get dashboard statistics"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get total customers
        cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'customer'")
        total_customers = cursor.fetchone()[0]
        
        # Get total admins
        cursor.execute("SELECT COUNT(*) FROM users WHERE role IN ('admin', 'super_admin')")
        total_admins = cursor.fetchone()[0]
        
        # Get total sales (from transactions)
        cursor.execute("""
            SELECT COALESCE(SUM(amount), 0) 
            FROM transactions 
            WHERE type = 'purchase' AND status = 'completed'
        """)
        total_sales = cursor.fetchone()[0]
        
        # Get total balance
        cursor.execute("SELECT COALESCE(SUM(balance), 0) FROM users")
        total_balance = cursor.fetchone()[0]
        
        # Get recent transactions
        cursor.execute("""
            SELECT t.*, u.full_name 
            FROM transactions t
            JOIN users u ON t.user_id = u.id
            ORDER BY t.created_at DESC
            LIMIT 10
        """)
        recent_transactions = cursor.fetchall()
        
        conn.close()
        
        return jsonify({
            'success': True,
            'stats': {
                'total_customers': total_customers,
                'total_admins': total_admins,
                'total_sales': float(total_sales),
                'total_balance': float(total_balance)
            },
            'recent_transactions': [
                {
                    'id': row[0],
                    'user_name': row[-1],
                    'type': row[3],
                    'amount': float(row[4]),
                    'status': row[5],
                    'created_at': row[7]
                }
                for row in recent_transactions
            ]
        })
        
    except Exception as e:
        print(f"Error getting dashboard stats: {e}")
        return jsonify({'error': 'Failed to get statistics'}), 500

@app.route('/api/users', methods=['GET'])
@super_admin_required
def get_users():
    """Get all users with pagination and search"""
    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 20))
        search = request.args.get('search', '')
        role_filter = request.args.get('role', '')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Build query
        where_clause = "WHERE 1=1"
        params = []
        
        if search:
            where_clause += " AND (full_name LIKE ? OR phone LIKE ? OR telegram_id LIKE ?)"
            search_param = f"%{search}%"
            params.extend([search_param, search_param, search_param])
        
        if role_filter:
            where_clause += " AND role = ?"
            params.append(role_filter)
        
        # Get total count
        cursor.execute(f"SELECT COUNT(*) FROM users {where_clause}", params)
        total_count = cursor.fetchone()[0]
        
        # Get users with pagination
        offset = (page - 1) * per_page
        cursor.execute(f"""
            SELECT id, telegram_id, full_name, phone, role, balance, 
                   status, created_at, last_activity
            FROM users {where_clause}
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        """, params + [per_page, offset])
        
        users = cursor.fetchall()
        conn.close()
        
        return jsonify({
            'success': True,
            'users': [
                {
                    'id': row[0],
                    'telegram_id': row[1],
                    'full_name': row[2],
                    'phone': row[3],
                    'role': row[4],
                    'balance': float(row[5]) if row[5] else 0,
                    'status': row[6],
                    'created_at': row[7],
                    'last_activity': row[8]
                }
                for row in users
            ],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total_count,
                'pages': (total_count + per_page - 1) // per_page
            }
        })
        
    except Exception as e:
        print(f"Error getting users: {e}")
        return jsonify({'error': 'Failed to get users'}), 500

@app.route('/api/users/<int:user_id>', methods=['PUT'])
@super_admin_required
def update_user(user_id):
    """Update user information"""
    try:
        data = request.get_json()
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Update user
        cursor.execute("""
            UPDATE users 
            SET full_name = ?, phone = ?, role = ?, balance = ?, status = ?
            WHERE id = ?
        """, (
            data.get('full_name'),
            data.get('phone'),
            data.get('role'),
            data.get('balance'),
            data.get('status'),
            user_id
        ))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'User updated successfully'})
        
    except Exception as e:
        print(f"Error updating user: {e}")
        return jsonify({'error': 'Failed to update user'}), 500

@app.route('/api/withdrawals', methods=['GET'])
@super_admin_required
def get_withdrawals():
    """Get withdrawal requests"""
    try:
        status_filter = request.args.get('status', '')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        where_clause = ""
        params = []
        
        if status_filter:
            where_clause = "WHERE w.status = ?"
            params.append(status_filter)
        
        cursor.execute(f"""
            SELECT w.*, u.full_name, u.phone
            FROM withdrawal_requests w
            JOIN users u ON w.user_id = u.id
            {where_clause}
            ORDER BY w.created_at DESC
        """, params)
        
        withdrawals = cursor.fetchall()
        conn.close()
        
        return jsonify({
            'success': True,
            'withdrawals': [
                {
                    'id': row[0],
                    'user_id': row[1],
                    'user_name': row[-2],
                    'user_phone': row[-1],
                    'amount': float(row[2]),
                    'status': row[3],
                    'account_info': row[4],
                    'created_at': row[5],
                    'processed_at': row[6],
                    'admin_notes': row[7]
                }
                for row in withdrawals
            ]
        })
        
    except Exception as e:
        print(f"Error getting withdrawals: {e}")
        return jsonify({'error': 'Failed to get withdrawals'}), 500

@app.route('/api/withdrawals/<int:withdrawal_id>', methods=['PUT'])
@super_admin_required
def update_withdrawal(withdrawal_id):
    """Update withdrawal request status"""
    try:
        data = request.get_json()
        new_status = data.get('status')
        admin_notes = data.get('admin_notes', '')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Update withdrawal
        cursor.execute("""
            UPDATE withdrawal_requests 
            SET status = ?, admin_notes = ?, processed_at = ?
            WHERE id = ?
        """, (new_status, admin_notes, datetime.now(), withdrawal_id))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Withdrawal updated successfully'})
        
    except Exception as e:
        print(f"Error updating withdrawal: {e}")
        return jsonify({'error': 'Failed to update withdrawal'}), 500

@app.route('/api/broadcast', methods=['POST'])
@super_admin_required
def broadcast_message():
    """Send broadcast message to all users"""
    try:
        data = request.get_json()
        message = data.get('message')
        target_role = data.get('target_role', 'all')
        
        if not message:
            return jsonify({'error': 'Message is required'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get target users
        if target_role == 'all':
            cursor.execute("SELECT telegram_id FROM users WHERE telegram_id IS NOT NULL")
        else:
            cursor.execute("SELECT telegram_id FROM users WHERE role = ? AND telegram_id IS NOT NULL", (target_role,))
        
        users = cursor.fetchall()
        conn.close()
        
        # Send messages
        success_count = 0
        failed_count = 0
        
        for user in users:
            telegram_id = user[0]
            try:
                url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
                payload = {
                    'chat_id': telegram_id,
                    'text': f"📢 **رسالة من الإدارة**\n\n{message}",
                    'parse_mode': 'Markdown'
                }
                
                response = requests.post(url, json=payload, timeout=5)
                if response.status_code == 200:
                    success_count += 1
                else:
                    failed_count += 1
                    
            except Exception as e:
                print(f"Failed to send to {telegram_id}: {e}")
                failed_count += 1
        
        return jsonify({
            'success': True,
            'message': f'Broadcast completed. Success: {success_count}, Failed: {failed_count}'
        })
        
    except Exception as e:
        print(f"Error in broadcast: {e}")
        return jsonify({'error': 'Failed to send broadcast'}), 500

@app.route('/api/accounting/reports', methods=['GET'])
@super_admin_required
def get_accounting_reports():
    """Get accounting reports"""
    try:
        report_type = request.args.get('type', 'summary')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if report_type == 'summary':
            # Get summary data
            cursor.execute("""
                SELECT 
                    SUM(CASE WHEN type = 'purchase' THEN amount ELSE 0 END) as total_purchases,
                    SUM(CASE WHEN type = 'transfer' THEN amount ELSE 0 END) as total_transfers,
                    SUM(CASE WHEN type = 'coupon_redeem' THEN amount ELSE 0 END) as total_coupons,
                    COUNT(*) as total_transactions
                FROM transactions
                WHERE status = 'completed'
                AND (? IS NULL OR created_at >= ?)
                AND (? IS NULL OR created_at <= ?)
            """, (start_date, start_date, end_date, end_date))
            
            summary = cursor.fetchone()
            
            result = {
                'total_purchases': float(summary[0] or 0),
                'total_transfers': float(summary[1] or 0),
                'total_coupons': float(summary[2] or 0),
                'total_transactions': summary[3]
            }
        
        conn.close()
        
        return jsonify({
            'success': True,
            'report': result
        })
        
    except Exception as e:
        print(f"Error getting accounting reports: {e}")
        return jsonify({'error': 'Failed to get reports'}), 500

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    print("🚀 Starting Yemen Net Bot Dashboard...")
    print("📊 Dashboard will be available at: http://localhost:5000")
    print("🔐 Super admin access required for login")
    
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True,
        threaded=True
    )