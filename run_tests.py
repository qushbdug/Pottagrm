#!/usr/bin/env python3
"""
Test Runner for Yemen Net Bot
تشغيل الاختبارات لبوت شبكات اليمن
"""

import subprocess
import sys
import os
from pathlib import Path


def run_command(command, description):
    """Run a command and display results."""
    print(f"\n{'='*60}")
    print(f"🔍 {description}")
    print(f"{'='*60}")
    
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            encoding='utf-8'
        )
        
        if result.stdout:
            print("✅ Output:")
            print(result.stdout)
        
        if result.stderr:
            print("⚠️ Errors/Warnings:")
            print(result.stderr)
        
        if result.returncode == 0:
            print(f"✅ {description} completed successfully!")
        else:
            print(f"❌ {description} failed with return code {result.returncode}")
            
        return result.returncode == 0
        
    except Exception as e:
        print(f"❌ Error running {description}: {e}")
        return False


def main():
    """Main test runner function."""
    print("🚀 Yemen Net Bot - Test Runner")
    print("🌟 Professional Edition v3.0.0")
    print("🇾🇪 Made with ❤️ for Yemen")
    
    # Check if we're in the right directory
    if not Path("src").exists():
        print("❌ Error: Please run this script from the project root directory")
        print("   Make sure you have a 'src' folder in the current directory")
        sys.exit(1)
    
    # Check if requirements are installed
    print("\n📦 Checking dependencies...")
    try:
        import pytest
        import flake8
        import black
        print("✅ All required packages are installed")
    except ImportError as e:
        print(f"❌ Missing package: {e}")
        print("   Please install development requirements:")
        print("   pip install -r requirements-dev.txt")
        sys.exit(1)
    
    success_count = 0
    total_tests = 0
    
    # Run code quality checks
    print("\n🔧 Running Code Quality Checks...")
    
    # Flake8 (code style)
    total_tests += 1
    if run_command("flake8 src/ --max-line-length=100 --ignore=E203,W503", "Flake8 Code Style Check"):
        success_count += 1
    
    # Black (code formatting)
    total_tests += 1
    if run_command("black --check src/", "Black Code Formatting Check"):
        success_count += 1
    
    # Isort (import sorting)
    total_tests += 1
    if run_command("isort --check-only src/", "Isort Import Sorting Check"):
        success_count += 1
    
    # Run tests
    print("\n🧪 Running Tests...")
    
    # Unit tests
    total_tests += 1
    if run_command("python -m pytest tests/ -v --tb=short", "Unit Tests"):
        success_count += 1
    
    # Test coverage
    total_tests += 1
    if run_command("python -m pytest tests/ --cov=src --cov-report=html --cov-report=term", "Test Coverage"):
        success_count += 1
    
    # Security checks
    print("\n🔒 Running Security Checks...")
    
    # Bandit (security)
    total_tests += 1
    if run_command("bandit -r src/ -f json -o bandit-report.json", "Bandit Security Check"):
        success_count += 1
    
    # Safety (dependency vulnerabilities)
    total_tests += 1
    if run_command("safety check", "Safety Dependency Check"):
        success_count += 1
    
    # Performance tests (if available)
    print("\n⚡ Running Performance Tests...")
    
    # Memory profiling
    total_tests += 1
    if run_command("python -m memory_profiler tests/test_performance.py", "Memory Profiling"):
        success_count += 1
    
    # Results summary
    print(f"\n{'='*60}")
    print("📊 TEST RESULTS SUMMARY")
    print(f"{'='*60}")
    print(f"✅ Passed: {success_count}")
    print(f"❌ Failed: {total_tests - success_count}")
    print(f"📈 Success Rate: {(success_count/total_tests)*100:.1f}%")
    
    if success_count == total_tests:
        print("\n🎉 All tests passed! The code is ready for production.")
        print("🌟 Professional quality achieved!")
    else:
        print(f"\n⚠️ {total_tests - success_count} test(s) failed. Please fix the issues before proceeding.")
        print("🔧 Check the output above for details.")
    
    # Generate reports
    print("\n📋 Generating Reports...")
    
    if Path("htmlcov").exists():
        print("✅ Coverage report: htmlcov/index.html")
    
    if Path("bandit-report.json").exists():
        print("✅ Security report: bandit-report.json")
    
    print("\n🚀 Test runner completed!")
    
    return success_count == total_tests


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⚠️ Test runner interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)