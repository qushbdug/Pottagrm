#!/usr/bin/env python3
"""
UNIFIED MAIN ENTRY POINT for Yemen Net Bot
This is the SINGLE entry point for the entire application

Author: Software Maintainer
Version: 1.0.0 (Unified)
"""

import sys
import os
import logging
from datetime import datetime

# Add bot_modules to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'bot_modules'))

def setup_unified_logging():
    """Setup unified logging for the entire application"""
    from bot_modules.config import LOGGING_FORMAT, LOGGING_LEVEL
    
    # Create logs directory if it doesn't exist
    os.makedirs('logs', exist_ok=True)
    
    # Configure root logger
    logging.basicConfig(
        format=LOGGING_FORMAT,
        level=getattr(logging, LOGGING_LEVEL),
        handlers=[
            logging.FileHandler(f'logs/bot_unified_{datetime.now().strftime("%Y%m%d")}.log'),
            logging.StreamHandler()
        ]
    )
    
    return logging.getLogger(__name__)

def validate_environment():
    """Validate that all required components are available"""
    logger = logging.getLogger(__name__)
    
    try:
        # Test configuration import
        from bot_modules.config import BOT_TOKEN, DB_PATH
        if not BOT_TOKEN:
            raise ValueError("BOT_TOKEN is not configured")
        
        # Test database connection
        from bot_modules.database import get_db_connection
        conn = get_db_connection()
        conn.close()
        
        # Test core modules
        from bot_modules.utils import get_user
        from bot_modules.handlers import COMMAND_HANDLERS
        
        logger.info("✅ Environment validation successful")
        return True
        
    except Exception as e:
        logger.error(f"❌ Environment validation failed: {e}")
        return False

def main():
    """
    UNIFIED MAIN FUNCTION
    Single entry point that handles all bot initialization
    """
    print("🤖 Yemen Net Bot - Unified Version")
    print("=" * 50)
    
    # Setup logging
    logger = setup_unified_logging()
    logger.info("Starting Yemen Net Bot (Unified Version)")
    
    # Validate environment
    if not validate_environment():
        print("❌ Environment validation failed. Exiting...")
        sys.exit(1)
    
    print("✅ Environment validation successful")
    
    try:
        # Import and run the unified bot
        print("🚀 Starting unified bot...")
        
        # Import from the enhanced bot (yemen_net_bot_new.py is the main implementation)
        import yemen_net_bot_new
        yemen_net_bot_new.main()
        
    except KeyboardInterrupt:
        logger.info("Bot stopped by user (Ctrl+C)")
        print("\n👋 Bot stopped by user")
    except Exception as e:
        logger.error(f"Critical error in main: {e}")
        print(f"❌ Critical error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()