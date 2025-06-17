#!/usr/bin/env python3
"""Simple test to verify pagination URL construction"""

import sys
import os

# Add src to path
current_dir = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(current_dir, 'src')
sys.path.insert(0, src_path)

try:
    from models import SearchConfig
    print("✅ Successfully imported SearchConfig")
    
    # Test URL construction for city-based search
    print("\n=== Testing City-based Search URLs ===")
    config = SearchConfig(city="lisboa", max_pages=3)
    base_url = config.get_base_url()
    print(f"Base URL: {base_url}")
    
    # Test pagination URL construction
    for page in range(1, 4):
        if page == 1:
            url = base_url
        else:
            separator = "&" if "?" in base_url else "?"
            url = f"{base_url}{separator}pagina={page}"
        print(f"Page {page}: {url}")
    
    # Test custom polygon URLs
    print("\n=== Testing Custom Polygon URLs ===")
    config_polygon = SearchConfig(max_pages=3)
    config_polygon.custom_polygon = "((test_polygon))"
    base_url_polygon = config_polygon.get_base_url()
    print(f"Polygon Base URL: {base_url_polygon}")
    
    for page in range(1, 4):
        if page == 1:
            url = base_url_polygon
        else:
            separator = "&" if "?" in base_url_polygon else "?"
            url = f"{base_url_polygon}{separator}pagina={page}"
        print(f"Polygon Page {page}: {url}")
    
    print("\n✅ URL construction test completed successfully!")
    
except ImportError as e:
    print(f"❌ Import failed: {e}")
    print(f"Current directory: {os.getcwd()}")
    print(f"Src path: {src_path}")
    print(f"Files in src: {os.listdir(src_path) if os.path.exists(src_path) else 'src not found'}")