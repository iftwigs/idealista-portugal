#!/usr/bin/env python3
"""Test furniture filtering logic"""

import sys
import os

# Add src to path
current_dir = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(current_dir, 'src')
sys.path.insert(0, src_path)

try:
    from models import SearchConfig, FurnitureType
    
    print("=== Testing Furniture Filter URL Generation ===\n")
    
    # Test 1: Only FURNISHED
    print("1. Only FURNISHED selected:")
    config1 = SearchConfig(furniture_types=[FurnitureType.FURNISHED])
    url1 = config1.get_base_url()
    print(f"   URL: {url1}")
    print(f"   Should contain: equipamento_mobilado")
    print(f"   Contains furniture param: {'equipamento_mobilado' in url1}")
    print()
    
    # Test 2: Only UNFURNISHED
    print("2. Only UNFURNISHED selected:")
    config2 = SearchConfig(furniture_types=[FurnitureType.UNFURNISHED])
    url2 = config2.get_base_url()
    print(f"   URL: {url2}")
    print(f"   Should NOT contain furniture params (will filter client-side)")
    print(f"   Contains furniture param: {'equipamento' in url2}")
    print()
    
    # Test 3: FURNISHED + UNFURNISHED
    print("3. Both FURNISHED and UNFURNISHED selected:")
    config3 = SearchConfig(furniture_types=[FurnitureType.FURNISHED, FurnitureType.UNFURNISHED])
    url3 = config3.get_base_url()
    print(f"   URL: {url3}")
    print(f"   Should contain: equipamento_mobilado")
    print(f"   Contains furniture param: {'equipamento_mobilado' in url3}")
    print()
    
    # Test 4: KITCHEN_FURNITURE only
    print("4. Only KITCHEN_FURNITURE selected:")
    config4 = SearchConfig(furniture_types=[FurnitureType.KITCHEN_FURNITURE])
    url4 = config4.get_base_url()
    print(f"   URL: {url4}")
    print(f"   Should contain: equipamento_so-cozinha-equipada")
    print(f"   Contains kitchen param: {'equipamento_so-cozinha-equipada' in url4}")
    print()
    
    # Test 5: Default configuration
    print("5. Default configuration:")
    config5 = SearchConfig()
    url5 = config5.get_base_url()
    print(f"   Furniture types: {[ft.value for ft in config5.furniture_types]}")
    print(f"   URL: {url5}")
    print(f"   Should contain: equipamento_mobilado (since FURNISHED + UNFURNISHED)")
    print(f"   Contains furniture param: {'equipamento_mobilado' in url5}")
    print()
    
    print("✅ Furniture filtering URL generation test completed!")
    
    # Test furniture detection logic
    print("\n=== Testing Furniture Detection Logic ===\n")
    
    test_cases = [
        ("Mobilado", True, False),
        ("Furnished", True, False),
        ("Cozinha equipada", False, True),
        ("Kitchen equipped", False, True),
        ("Sem mobília", False, False),
        ("Unfurnished", False, False),
        ("", False, False),
        ("Mobilado Cozinha equipada", True, True),
    ]
    
    for furniture_text, expected_furnished, expected_kitchen in test_cases:
        furniture_text_lower = furniture_text.lower()
        
        has_furniture = any(term in furniture_text_lower for term in [
            "furnished", "mobilado", "amueblado", "meublé"
        ])
        has_kitchen_furniture = any(term in furniture_text_lower for term in [
            "kitchen", "cozinha", "cocina equipped", "cozinha equipada"
        ])
        is_unfurnished = any(term in furniture_text_lower for term in [
            "unfurnished", "sem mobília", "sin muebles", "não mobilado"
        ]) or (not has_furniture and not has_kitchen_furniture)
        
        print(f"Text: '{furniture_text}'")
        print(f"  Furnished: {has_furniture} (expected: {expected_furnished}) {'✅' if has_furniture == expected_furnished else '❌'}")
        print(f"  Kitchen: {has_kitchen_furniture} (expected: {expected_kitchen}) {'✅' if has_kitchen_furniture == expected_kitchen else '❌'}")
        print(f"  Unfurnished: {is_unfurnished}")
        print()
    
    print("✅ Furniture detection logic test completed!")
    
except ImportError as e:
    print(f"❌ Import failed: {e}")
    print(f"Current directory: {os.getcwd()}")
    print(f"Src path: {src_path}")
    print(f"Files in src: {os.listdir(src_path) if os.path.exists(src_path) else 'src not found'}")