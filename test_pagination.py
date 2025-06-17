#!/usr/bin/env python3
"""
Simple test script to validate pagination implementation
"""

import sys
sys.path.append('src')

from models import SearchConfig

def test_pagination_config():
    """Test that pagination configuration works correctly"""
    
    # Test default value
    config = SearchConfig()
    print(f"✅ Default max_pages: {config.max_pages}")
    assert config.max_pages == 3, f"Expected 3, got {config.max_pages}"
    
    # Test setting different values
    config.max_pages = 1
    assert config.max_pages == 1
    print(f"✅ Set max_pages to 1: {config.max_pages}")
    
    config.max_pages = 5
    assert config.max_pages == 5
    print(f"✅ Set max_pages to 5: {config.max_pages}")
    
    # Test URL generation with custom polygon
    config.custom_polygon = "((test_polygon))"
    url = config.get_base_url()
    print(f"✅ Custom polygon URL: {url}")
    assert "shape=" in url
    
    # Test URL generation with city
    config.custom_polygon = None
    config.city = "lisboa"
    url = config.get_base_url()
    print(f"✅ City-based URL: {url}")
    assert config.city in url
    
    print("\n🎉 All pagination tests passed!")

if __name__ == "__main__":
    test_pagination_config()