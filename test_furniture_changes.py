#!/usr/bin/env python3
"""Test script to validate furniture_type changes"""

import sys
sys.path.append('/Users/apple/projects/idealista-notifier/src')

from models import SearchConfig, FurnitureType

def test_furniture_changes():
    """Test that furniture_type changes work correctly"""
    print("Testing furniture_type changes...")
    
    # Test 1: Default configuration
    config = SearchConfig()
    print(f"✓ Default furniture_type: {config.furniture_type}")
    assert hasattr(config, 'furniture_type'), "SearchConfig should have furniture_type attribute"
    
    # Test 2: All furniture types available
    print("✓ Available furniture types:")
    for furniture_type in FurnitureType:
        print(f"  - {furniture_type.name}: {furniture_type.value}")
    
    # Test 3: Can set different furniture types
    config.furniture_type = FurnitureType.FURNISHED
    print(f"✓ Set to FURNISHED: {config.furniture_type}")
    
    config.furniture_type = FurnitureType.KITCHEN_FURNITURE
    print(f"✓ Set to KITCHEN_FURNITURE: {config.furniture_type}")
    
    config.furniture_type = FurnitureType.UNFURNISHED
    print(f"✓ Set to UNFURNISHED: {config.furniture_type}")
    
    config.furniture_type = FurnitureType.ANY
    print(f"✓ Set to ANY: {config.furniture_type}")
    
    # Test 4: URL generation works
    test_url = config.get_base_url()
    print(f"✓ Generated URL: {test_url}")
    
    # Test 5: Check that furniture_types attribute doesn't exist
    assert not hasattr(config, 'furniture_types'), "SearchConfig should NOT have furniture_types attribute"
    print("✓ Confirmed furniture_types attribute removed")
    
    print("\n🎉 All tests passed! The furniture_type changes are working correctly.")

if __name__ == "__main__":
    test_furniture_changes()