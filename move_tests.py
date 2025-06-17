#!/usr/bin/env python3
"""Script to move all test files to tests/ directory"""

import os
import shutil

# List of test files to move from src/ to tests/
src_test_files = [
    'test_adaptive_rate_limiting.py',
    'test_bot.py', 
    'test_bot_flow.py',
    'test_configuration_validation.py',
    'test_integration_complete.py',
    'test_models.py',
    'test_monitoring_debugging.py',
    'test_new_bot_features.py',
    'test_scraper.py',
    'test_scraper_enhanced.py',
    'test_url_generation.py',
    'test_user_stats.py'
]

# List of test files to move from root to tests/
root_test_files = [
    'test_pagination.py',
    'test_pagination_debug.py', 
    'test_url_fix.py'
]

def move_file_with_path_fix(src_file, dest_file):
    """Move file and fix import paths"""
    if not os.path.exists(src_file):
        print(f"⚠️  File not found: {src_file}")
        return
    
    print(f"📁 Moving {src_file} -> {dest_file}")
    
    # Read the file content
    with open(src_file, 'r') as f:
        content = f.read()
    
    # Fix import paths if needed
    if 'sys.path.append(' in content and 'src' in content:
        # Already has path setup, update it for tests directory
        content = content.replace("sys.path.append('src')", 
                                "current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))\nsrc_path = os.path.join(current_dir, 'src')\nsys.path.insert(0, src_path)")
        
        # Add import os if not present
        if 'import os' not in content:
            content = content.replace('import sys', 'import sys\nimport os')
    
    # Write to destination
    with open(dest_file, 'w') as f:
        f.write(content)
    
    # Remove original
    os.remove(src_file)
    print(f"✅ Moved {os.path.basename(src_file)}")

def main():
    print("🔄 Moving all test files to tests/ directory...\n")
    
    # Ensure tests directory exists
    os.makedirs('tests', exist_ok=True)
    
    # Move files from src/
    print("📦 Moving test files from src/:")
    for test_file in src_test_files:
        src_path = f"src/{test_file}"
        dest_path = f"tests/{test_file}"
        move_file_with_path_fix(src_path, dest_path)
    
    print("\n📦 Moving test files from root:")
    # Move files from root
    for test_file in root_test_files:
        src_path = test_file
        dest_path = f"tests/{test_file}"
        move_file_with_path_fix(src_path, dest_path)
    
    # Remove the old test files that we already moved manually
    old_files = [
        'test_furniture_filtering.py',
        'simple_pagination_test.py',
        'debug_pagination.py'
    ]
    
    print("\n🗑️  Cleaning up old files:")
    for old_file in old_files:
        if os.path.exists(old_file):
            os.remove(old_file)
            print(f"🗑️  Removed {old_file}")
    
    print("\n✅ All test files moved to tests/ directory!")
    print("\n📋 Test files now in tests/:")
    for file in sorted(os.listdir('tests')):
        if file.endswith('.py'):
            print(f"   - {file}")

if __name__ == "__main__":
    main()