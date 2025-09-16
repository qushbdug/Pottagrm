#!/usr/bin/env python3
"""
Yemen Net Bot Dashboard - Startup Script
This script starts the web dashboard for the Yemen Net Bot
"""

import os
import sys
import subprocess
import time

def check_requirements():
    """Check if all required packages are installed"""
    required_packages = [
        'flask',
        'flask-cors',
        'flask-jwt-extended',
        'requests',
        'cryptography'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print("❌ Missing required packages:")
        for package in missing_packages:
            print(f"   - {package}")
        print("\n📦 Installing missing packages...")
        
        # Install missing packages
        for package in missing_packages:
            try:
                subprocess.check_call([sys.executable, '-m', 'pip', 'install', package])
                print(f"✅ Installed {package}")
            except subprocess.CalledProcessError:
                print(f"❌ Failed to install {package}")
                return False
    
    return True

def check_bot_database():
    """Check if bot database exists and is accessible"""
    db_paths = [
        '../../yemen_net.db',
        '../yemen_net.db',
        './yemen_net.db'
    ]
    
    for db_path in db_paths:
        if os.path.exists(db_path):
            print(f"✅ Found bot database at: {db_path}")
            return True
    
    print("⚠️  Bot database not found. Make sure the bot is set up properly.")
    return True  # Don't fail, just warn

def start_dashboard():
    """Start the dashboard server"""
    print("🚀 Starting Yemen Net Bot Dashboard...")
    print("📊 Dashboard will be available at: http://localhost:5000")
    print("🔐 Login page: http://localhost:5000/login")
    print("⚠️  Super admin access required")
    print("\n" + "="*50)
    
    # Change to backend directory
    backend_dir = os.path.join(os.path.dirname(__file__), 'backend')
    os.chdir(backend_dir)
    
    # Start Flask app
    try:
        subprocess.run([sys.executable, 'app.py'], check=True)
    except KeyboardInterrupt:
        print("\n\n🛑 Dashboard stopped by user")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error starting dashboard: {e}")
        return False
    
    return True

def main():
    """Main function"""
    print("🤖 Yemen Net Bot Dashboard Startup")
    print("="*40)
    
    # Check requirements
    print("📋 Checking requirements...")
    if not check_requirements():
        print("❌ Failed to install required packages")
        return 1
    
    # Check bot database
    print("🗄️  Checking bot database...")
    check_bot_database()
    
    # Start dashboard
    if not start_dashboard():
        return 1
    
    return 0

if __name__ == '__main__':
    sys.exit(main())