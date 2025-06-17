#!/usr/bin/env python3
"""Clean up old test files that have been moved"""

import os

# Files to remove from root
old_files = [
    'test_furniture_filtering.py',
    'simple_pagination_test.py', 
    'debug_pagination.py',
    'test_pagination_debug.py',
    'test_pagination.py',
    'test_url_fix.py',
    'move_tests.py'
]

# Files to remove from src/
src_test_files = [
    'src/test_adaptive_rate_limiting.py',
    'src/test_bot.py',
    'src/test_bot_flow.py', 
    'src/test_configuration_validation.py',
    'src/test_integration_complete.py',
    'src/test_models.py',
    'src/test_monitoring_debugging.py',
    'src/test_new_bot_features.py',
    'src/test_pagination_behavior.py',
    'src/test_scraper.py',
    'src/test_scraper_enhanced.py',
    'src/test_url_generation.py',
    'src/test_user_stats.py'
]

print("🗑️  Cleaning up old test files...")

for file_path in old_files + src_test_files:
    if os.path.exists(file_path):
        os.remove(file_path)
        print(f"✅ Removed {file_path}")
    else:
        print(f"⚠️  File not found: {file_path}")

print("\n📁 Current tests directory structure:")
for file in sorted(os.listdir('tests')):
    if file.endswith('.py'):
        print(f"   - tests/{file}")

print("\n✅ Cleanup completed!")