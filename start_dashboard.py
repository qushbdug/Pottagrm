#!/usr/bin/env python3
"""
Yemen Net Bot Dashboard - Quick Start Script
Simple script to start the web dashboard
"""

import os
import sys
import subprocess

def main():
    """Start the dashboard"""
    print("🤖 Yemen Net Bot Dashboard")
    print("="*40)
    print("🚀 Starting dashboard server...")
    
    # Get the dashboard directory
    dashboard_dir = os.path.join(os.path.dirname(__file__), 'dashboard', 'backend')
    
    if not os.path.exists(dashboard_dir):
        print("❌ Dashboard directory not found!")
        return 1
    
    # Change to dashboard directory
    original_dir = os.getcwd()
    os.chdir(dashboard_dir)
    
    try:
        print("📊 Dashboard URL: http://localhost:5000")
        print("🔐 Login URL: http://localhost:5000/login")
        print("⚠️  Super admin access required")
        print("\nPress Ctrl+C to stop the server")
        print("="*40)
        
        # Start the Flask app
        subprocess.run([sys.executable, 'app.py'])
        
    except KeyboardInterrupt:
        print("\n\n🛑 Dashboard stopped")
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1
    finally:
        os.chdir(original_dir)
    
    return 0

if __name__ == '__main__':
    sys.exit(main())