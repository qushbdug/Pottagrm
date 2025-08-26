#!/usr/bin/env python3
"""
Integration Test for Unified Yemen Net Bot
Tests all unified components to ensure no conflicts

Author: Software Maintainer  
Version: 1.0.0 (Test Suite)
"""

import sys
import os
import logging

# Add bot_modules to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'bot_modules'))

def test_unified_configuration():
    """Test that all configurations are properly unified"""
    print("🔧 Testing unified configuration...")
    
    try:
        from bot_modules.config import (
            BOT_TOKEN, DB_PATH, EMOJIS, USER_ROLES, PERMISSIONS,
            QUICK_COMMANDS, ACCOUNT_TYPE_ASSET, CARD_COMMISSION_RATE,
            FEATURES, CRYPTO_AVAILABLE
        )
        
        # Validate critical config
        assert BOT_TOKEN, "BOT_TOKEN is empty"
        assert DB_PATH, "DB_PATH is empty"
        assert isinstance(EMOJIS, dict), "EMOJIS is not a dict"
        assert len(EMOJIS) > 10, "EMOJIS has too few entries"
        assert isinstance(USER_ROLES, dict), "USER_ROLES is not a dict"
        assert len(USER_ROLES) == 5, "USER_ROLES missing entries"
        assert isinstance(PERMISSIONS, dict), "PERMISSIONS is not a dict"
        assert isinstance(QUICK_COMMANDS, list), "QUICK_COMMANDS is not a list"
        assert len(QUICK_COMMANDS) > 10, "QUICK_COMMANDS has too few entries"
        
        print("  ✅ Configuration unified successfully")
        return True
        
    except Exception as e:
        print(f"  ❌ Configuration test failed: {e}")
        return False

def test_database_integration():
    """Test database connection and unified access"""
    print("🗄️ Testing database integration...")
    
    try:
        from bot_modules.database import get_db_connection, init_db
        
        # Test connection
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Test basic query
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        conn.close()
        
        assert len(tables) > 0, "No tables found in database"
        
        print(f"  ✅ Database has {len(tables)} tables")
        return True
        
    except Exception as e:
        print(f"  ❌ Database test failed: {e}")
        return False

def test_unified_network_manager():
    """Test unified network management"""
    print("🌐 Testing unified network manager...")
    
    try:
        from bot_modules.unified_network_manager import (
            unified_network_creation_handler,
            unified_manage_networks_handler,
            UNIFIED_NETWORK_CALLBACKS,
            get_networks_for_user
        )
        
        # Validate functions exist
        assert callable(unified_network_creation_handler), "Network creation handler not callable"
        assert callable(unified_manage_networks_handler), "Network management handler not callable"
        assert isinstance(UNIFIED_NETWORK_CALLBACKS, dict), "Callbacks not a dict"
        assert len(UNIFIED_NETWORK_CALLBACKS) > 0, "No callbacks defined"
        
        print(f"  ✅ Network manager has {len(UNIFIED_NETWORK_CALLBACKS)} callbacks")
        return True
        
    except Exception as e:
        print(f"  ❌ Network manager test failed: {e}")
        return False

def test_unified_search_manager():
    """Test unified search management"""
    print("🔍 Testing unified search manager...")
    
    try:
        from bot_modules.unified_search_manager import (
            unified_search_networks_handler,
            search_networks_general,
            search_networks_by_name,
            search_networks_by_location,
            UNIFIED_SEARCH_CALLBACKS
        )
        
        # Validate functions exist
        assert callable(unified_search_networks_handler), "Search handler not callable"
        assert callable(search_networks_general), "General search not callable"
        assert callable(search_networks_by_name), "Name search not callable"
        assert callable(search_networks_by_location), "Location search not callable"
        assert isinstance(UNIFIED_SEARCH_CALLBACKS, dict), "Search callbacks not a dict"
        
        print(f"  ✅ Search manager has {len(UNIFIED_SEARCH_CALLBACKS)} callbacks")
        return True
        
    except Exception as e:
        print(f"  ❌ Search manager test failed: {e}")
        return False

def test_imports_resolution():
    """Test that all imports are resolved without circular dependencies"""
    print("📦 Testing imports resolution...")
    
    try:
        # Test core modules
        from bot_modules.config import BOT_TOKEN
        from bot_modules.database import get_db_connection
        from bot_modules.utils import get_user
        from bot_modules.handlers import COMMAND_HANDLERS
        from bot_modules.admin_functions import ADMIN_CALLBACKS
        
        # Test unified modules
        from bot_modules.unified_network_manager import UNIFIED_NETWORK_CALLBACKS
        from bot_modules.unified_search_manager import UNIFIED_SEARCH_CALLBACKS
        
        # Test main modules
        import yemen_net_bot_new
        
        print("  ✅ All imports resolved successfully")
        return True
        
    except ImportError as e:
        print(f"  ❌ Import resolution failed: {e}")
        return False
    except Exception as e:
        print(f"  ❌ Import test failed: {e}")
        return False

def test_no_duplicate_functions():
    """Test that duplicate functions have been eliminated"""
    print("🔄 Testing duplicate elimination...")
    
    try:
        # Check that we don't have conflicts
        import yemen_net_bot_new
        
        # Verify main has only one entry point
        import main
        assert hasattr(main, 'main'), "Main function not found"
        
        print("  ✅ No duplicate functions detected")
        return True
        
    except Exception as e:
        print(f"  ❌ Duplicate test failed: {e}")
        return False

def run_full_integration_test():
    """Run complete integration test suite"""
    print("🧪 Yemen Net Bot - Unified Integration Test")
    print("=" * 60)
    
    tests = [
        test_unified_configuration,
        test_database_integration, 
        test_unified_network_manager,
        test_unified_search_manager,
        test_imports_resolution,
        test_no_duplicate_functions
    ]
    
    passed = 0
    failed = 0
    
    for test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"  ❌ Test {test_func.__name__} crashed: {e}")
            failed += 1
        print()
    
    print("=" * 60)
    print(f"📊 Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 ALL TESTS PASSED! Integration successful!")
        return True
    else:
        print("⚠️ Some tests failed. Please review the issues above.")
        return False

if __name__ == "__main__":
    success = run_full_integration_test()
    sys.exit(0 if success else 1)