#!/usr/bin/env python3
"""Test furniture filtering logic"""

import pytest
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

from models import SearchConfig, FurnitureType


class TestFurnitureFiltering:
    """Test furniture filtering URL generation"""

    def test_furnished_filter(self):
        """Test FURNISHED furniture filter"""
        config = SearchConfig(furniture_type=FurnitureType.FURNISHED)
        url = config.get_base_url()

        # Should contain furnished parameter
        assert "equipamento_mobilado" in url

    def test_kitchen_furniture_filter(self):
        """Test KITCHEN_FURNITURE filter"""
        config = SearchConfig(furniture_type=FurnitureType.KITCHEN_FURNITURE)
        url = config.get_base_url()

        # Should contain kitchen furniture parameter
        assert "equipamento_so-cozinha-equipada" in url

    def test_indifferent_filter(self):
        """Test INDIFFERENT (no furniture filter)"""
        config = SearchConfig(furniture_type=FurnitureType.INDIFFERENT)
        url = config.get_base_url()

        # Should NOT contain any furniture parameters
        assert "equipamento_mobilado" not in url
        assert "equipamento_so-cozinha-equipada" not in url

    def test_default_configuration(self):
        """Test default furniture configuration"""
        config = SearchConfig()
        url = config.get_base_url()

        # Default should be INDIFFERENT
        assert config.furniture_type == FurnitureType.INDIFFERENT

        # Should NOT contain furniture parameters
        assert "equipamento_mobilado" not in url
        assert "equipamento_so-cozinha-equipada" not in url

    def test_furniture_type_enum_values(self):
        """Test that all expected furniture type enum values exist"""
        # Test that the enum values we expect exist
        assert hasattr(FurnitureType, "INDIFFERENT")
        assert hasattr(FurnitureType, "FURNISHED")
        assert hasattr(FurnitureType, "KITCHEN_FURNITURE")

        # Test their string values
        assert FurnitureType.INDIFFERENT.value == "indifferent"
        assert FurnitureType.FURNISHED.value == "equipamento_mobilado"
        assert (
            FurnitureType.KITCHEN_FURNITURE.value == "equipamento_so-cozinha-equipada"
        )


if __name__ == "__main__":
    # Run as script for debugging
    test = TestFurnitureFiltering()

    print("=== Testing Furniture Filter URL Generation ===\n")

    try:
        test.test_furnished_filter()
        print("✓ FURNISHED filter test passed")

        test.test_kitchen_furniture_filter()
        print("✓ KITCHEN_FURNITURE filter test passed")

        test.test_indifferent_filter()
        print("✓ INDIFFERENT filter test passed")

        test.test_default_configuration()
        print("✓ Default configuration test passed")

        test.test_furniture_type_enum_values()
        print("✓ Enum values test passed")

        print("\n✅ All furniture filtering tests passed!")
        print("✅ All furniture filtering logic is now handled by URL parameters only!")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
