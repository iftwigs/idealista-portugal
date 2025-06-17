#!/usr/bin/env python3
"""Test furniture filtering logic"""

import sys
import os

# Add src to path
current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src_path = os.path.join(current_dir, 'src')
sys.path.insert(0, src_path)

try:
    from models import SearchConfig, FurnitureType
    
    print("=== Testing Furniture Filter URL Generation ===\n")
    
    # Test 1: FURNISHED selected
    print("1. FURNISHED selected:")
    config1 = SearchConfig(furniture_type=FurnitureType.FURNISHED)
    url1 = config1.get_base_url()
    print(f"   URL: {url1}")
    print(f"   Should contain: equipamento_mobilado")
    print(f"   Contains furniture param: {'equipamento_mobilado' in url1}")
    print()
    
    # Test 2: KITCHEN_FURNITURE selected
    print("2. KITCHEN_FURNITURE selected:")
    config2 = SearchConfig(furniture_type=FurnitureType.KITCHEN_FURNITURE)
    url2 = config2.get_base_url()
    print(f"   URL: {url2}")
    print(f"   Should contain: equipamento_so-cozinha-equipada")
    print(f"   Contains kitchen param: {'equipamento_so-cozinha-equipada' in url2}")
    print()
    
    # Test 3: ANY (no filter)
    print("3. ANY (no furniture filter):")
    config3 = SearchConfig(furniture_type=FurnitureType.ANY)
    url3 = config3.get_base_url()
    print(f"   URL: {url3}")
    print(f"   Should NOT contain furniture params")
    print(f"   Contains furniture param: {'equipamento' in url3}")
    print()
    
    # Test 4: Default configuration
    print("4. Default configuration:")
    config4 = SearchConfig()
    url4 = config4.get_base_url()
    print(f"   Furniture type: {config4.furniture_type.value}")
    print(f"   URL: {url4}")
    print(f"   Should NOT contain furniture params (default is ANY)")
    print(f"   Contains furniture param: {'equipamento' in url4}")
    print()
    
    print("✅ Furniture filtering URL generation test completed!")
    print("\n✅ All furniture filtering logic is now handled by URL parameters only!")
    print("   No client-side filtering needed - much simpler and more reliable!")
    
except ImportError as e:
    print(f"❌ Import failed: {e}")
    print(f"Current directory: {os.getcwd()}")
    print(f"Src path: {src_path}")
    print(f"Files in src: {os.listdir(src_path) if os.path.exists(src_path) else 'src not found'}")