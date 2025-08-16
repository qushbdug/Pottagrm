#!/usr/bin/env python3
"""
Performance Tests for Yemen Net Bot
اختبارات الأداء لبوت شبكات اليمن
"""

import time
import asyncio
import unittest
from unittest.mock import Mock, patch
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from core.database import DatabaseManager
from core.utils import RateLimiter, SecurityManager


class PerformanceTest(unittest.TestCase):
    """Performance testing suite."""
    
    def setUp(self):
        """Set up test environment."""
        self.db_manager = DatabaseManager()
        self.rate_limiter = RateLimiter()
        self.security_manager = SecurityManager()
    
    def test_database_connection_performance(self):
        """Test database connection performance."""
        print("\n🔍 Testing database connection performance...")
        
        # Test connection speed
        start_time = time.time()
        
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                
            connection_time = time.time() - start_time
            
            print(f"✅ Database connection time: {connection_time:.4f} seconds")
            
            # Assert reasonable performance
            self.assertLess(connection_time, 0.1, "Database connection too slow")
            
        except Exception as e:
            print(f"❌ Database connection failed: {e}")
            self.fail(f"Database connection failed: {e}")
    
    def test_query_performance(self):
        """Test database query performance."""
        print("\n🔍 Testing database query performance...")
        
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                # Test simple query performance
                start_time = time.time()
                cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
                result = cursor.fetchone()
                query_time = time.time() - start_time
                
                print(f"✅ Simple query time: {query_time:.4f} seconds")
                self.assertLess(query_time, 0.01, "Simple query too slow")
                
        except Exception as e:
            print(f"❌ Query performance test failed: {e}")
            self.fail(f"Query performance test failed: {e}")
    
    def test_rate_limiter_performance(self):
        """Test rate limiter performance."""
        print("\n🔍 Testing rate limiter performance...")
        
        user_id = 12345
        action = "test_action"
        
        # Test rate limiter speed
        start_time = time.time()
        
        for i in range(100):
            self.rate_limiter.can_perform_action(user_id, action)
        
        total_time = time.time() - start_time
        avg_time = total_time / 100
        
        print(f"✅ Rate limiter average time: {avg_time:.6f} seconds per check")
        self.assertLess(avg_time, 0.001, "Rate limiter too slow")
    
    def test_security_validation_performance(self):
        """Test security validation performance."""
        print("\n🔍 Testing security validation performance...")
        
        # Test phone number validation
        test_phones = [
            "+967123456789",
            "967123456789", 
            "123456789",
            "invalid_phone"
        ]
        
        start_time = time.time()
        
        for phone in test_phones:
            self.security_manager.validate_phone_number(phone)
        
        total_time = time.time() - start_time
        avg_time = total_time / len(test_phones)
        
        print(f"✅ Phone validation average time: {avg_time:.6f} seconds per validation")
        self.assertLess(avg_time, 0.001, "Phone validation too slow")
        
        # Test input sanitization
        test_inputs = [
            "normal text",
            "text with <script>alert('xss')</script>",
            "text with 'quotes' and \"double quotes\"",
            "very long text " * 100
        ]
        
        start_time = time.time()
        
        for text in test_inputs:
            try:
                self.security_manager.sanitize_input(text)
            except:
                pass  # Expected for some inputs
        
        total_time = time.time() - start_time
        avg_time = total_time / len(test_inputs)
        
        print(f"✅ Input sanitization average time: {avg_time:.6f} seconds per sanitization")
        self.assertLess(avg_time, 0.001, "Input sanitization too slow")
    
    def test_memory_usage(self):
        """Test memory usage patterns."""
        print("\n🔍 Testing memory usage...")
        
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        print(f"✅ Initial memory usage: {initial_memory:.2f} MB")
        
        # Perform some operations
        for i in range(1000):
            self.rate_limiter.can_perform_action(i, f"action_{i}")
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        print(f"✅ Final memory usage: {final_memory:.2f} MB")
        print(f"✅ Memory increase: {memory_increase:.2f} MB")
        
        # Assert reasonable memory usage
        self.assertLess(memory_increase, 50, "Memory usage increased too much")
    
    def test_concurrent_operations(self):
        """Test concurrent operations performance."""
        print("\n🔍 Testing concurrent operations...")
        
        async def concurrent_rate_limit_check(user_id, action):
            """Simulate concurrent rate limit checks."""
            return self.rate_limiter.can_perform_action(user_id, action)
        
        async def run_concurrent_tests():
            """Run concurrent tests."""
            tasks = []
            for i in range(100):
                task = concurrent_rate_limit_check(i, f"action_{i}")
                tasks.append(task)
            
            start_time = time.time()
            results = await asyncio.gather(*tasks)
            total_time = time.time() - start_time
            
            print(f"✅ Concurrent operations time: {total_time:.4f} seconds")
            print(f"✅ Operations per second: {len(tasks)/total_time:.2f}")
            
            return total_time
        
        # Run concurrent test
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            total_time = loop.run_until_complete(run_concurrent_tests())
            self.assertLess(total_time, 1.0, "Concurrent operations too slow")
        finally:
            loop.close()
    
    def test_database_stress(self):
        """Test database under stress."""
        print("\n🔍 Testing database stress...")
        
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                # Create temporary table for stress testing
                cursor.execute("""
                    CREATE TEMPORARY TABLE stress_test (
                        id INTEGER PRIMARY KEY,
                        data TEXT,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Insert many records
                start_time = time.time()
                
                for i in range(1000):
                    cursor.execute(
                        "INSERT INTO stress_test (id, data) VALUES (?, ?)",
                        (i, f"test_data_{i}")
                    )
                
                insert_time = time.time() - start_time
                print(f"✅ Insert 1000 records time: {insert_time:.4f} seconds")
                
                # Query with different conditions
                start_time = time.time()
                
                cursor.execute("SELECT COUNT(*) FROM stress_test WHERE data LIKE ?", ("test_data_%",))
                count = cursor.fetchone()[0]
                
                query_time = time.time() - start_time
                print(f"✅ Query 1000 records time: {query_time:.4f} seconds")
                print(f"✅ Records found: {count}")
                
                # Assert reasonable performance
                self.assertLess(insert_time, 5.0, "Bulk insert too slow")
                self.assertLess(query_time, 1.0, "Bulk query too slow")
                self.assertEqual(count, 1000, "Record count mismatch")
                
        except Exception as e:
            print(f"❌ Database stress test failed: {e}")
            self.fail(f"Database stress test failed: {e}")


def run_performance_tests():
    """Run all performance tests."""
    print("🚀 Yemen Net Bot - Performance Test Suite")
    print("🌟 Professional Edition v3.0.0")
    print("🇾🇪 Made with ❤️ for Yemen")
    
    # Create test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(PerformanceTest)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print(f"\n{'='*60}")
    print("📊 PERFORMANCE TEST RESULTS")
    print(f"{'='*60}")
    print(f"✅ Tests run: {result.testsRun}")
    print(f"❌ Failures: {len(result.failures)}")
    print(f"⚠️ Errors: {len(result.errors)}")
    
    if result.failures:
        print("\n❌ Failures:")
        for test, traceback in result.failures:
            print(f"  - {test}: {traceback}")
    
    if result.errors:
        print("\n⚠️ Errors:")
        for test, traceback in result.errors:
            print(f"  - {test}: {traceback}")
    
    if result.wasSuccessful():
        print("\n🎉 All performance tests passed!")
        print("🌟 Performance meets professional standards!")
    else:
        print(f"\n⚠️ {len(result.failures) + len(result.errors)} test(s) failed.")
        print("🔧 Check the output above for performance issues.")
    
    return result.wasSuccessful()


if __name__ == "__main__":
    try:
        success = run_performance_tests()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⚠️ Performance tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)