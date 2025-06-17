#!/usr/bin/env python3
"""
Debug script to test pagination URL generation
"""

import sys
sys.path.append('src')

from models import SearchConfig

def test_pagination_urls():
    """Test that pagination URLs are generated correctly"""
    
    print("=== Testing Pagination URL Generation ===\n")
    
    # Test with city-based search
    print("1. City-based search:")
    config = SearchConfig(city="lisboa", max_pages=3)
    base_url = config.get_base_url()
    print(f"   Base URL: {base_url}")
    
    # Simulate pagination URL generation (like in scraper.py)
    for page in range(1, 4):
        if page == 1:
            url = base_url
        else:
            separator = "&" if "?" in base_url else "?"
            url = f"{base_url}{separator}pagina={page}"
        print(f"   Page {page}: {url}")
    
    print()
    
    # Test with custom polygon
    print("2. Custom polygon search:")
    config_polygon = SearchConfig(max_pages=3)
    config_polygon.custom_polygon = "((test_polygon_coords))"
    base_url_polygon = config_polygon.get_base_url()
    print(f"   Base URL: {base_url_polygon}")
    
    for page in range(1, 4):
        if page == 1:
            url = base_url_polygon
        else:
            separator = "&" if "?" in base_url_polygon else "?"
            url = f"{base_url_polygon}{separator}pagina={page}"
        print(f"   Page {page}: {url}")

if __name__ == "__main__":
    test_pagination_urls()