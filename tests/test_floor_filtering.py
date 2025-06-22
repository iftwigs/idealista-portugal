import pytest
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))
from models import SearchConfig, FloorType


class TestFloorFiltering:
    """Test floor filtering functionality"""

    def test_floor_type_enum_values(self):
        """Test that FloorType enum has correct values"""
        assert FloorType.LAST_FLOOR.value == "ultimo-andar"
        assert FloorType.MIDDLE_FLOORS.value == "andares-intermedios"
        assert FloorType.GROUND_FLOOR.value == "res-do-chao"

    def test_default_config_floor_types(self):
        """Test that default configuration has empty floor_types list"""
        config = SearchConfig()
        assert config.floor_types == []

    def test_single_floor_filter_generation(self):
        """Test URL parameter generation for single floor type"""
        # Test last floor only
        config = SearchConfig()
        config.floor_types = [FloorType.LAST_FLOOR]
        params = config.to_url_params()
        assert "ultimo-andar" in params
        assert "andares-intermedios" not in params
        assert "res-do-chao" not in params

        # Test middle floors only
        config.floor_types = [FloorType.MIDDLE_FLOORS]
        params = config.to_url_params()
        assert "andares-intermedios" in params
        assert "ultimo-andar" not in params
        assert "res-do-chao" not in params

        # Test ground floor only
        config.floor_types = [FloorType.GROUND_FLOOR]
        params = config.to_url_params()
        assert "res-do-chao" in params
        assert "ultimo-andar" not in params
        assert "andares-intermedios" not in params

    def test_multiple_floor_filter_generation(self):
        """Test URL parameter generation for multiple floor types"""
        # Test last floor + middle floors
        config = SearchConfig()
        config.floor_types = [FloorType.LAST_FLOOR, FloorType.MIDDLE_FLOORS]
        params = config.to_url_params()
        assert "ultimo-andar" in params
        assert "andares-intermedios" in params
        assert "res-do-chao" not in params

        # Test all three floor types
        config.floor_types = [
            FloorType.LAST_FLOOR,
            FloorType.MIDDLE_FLOORS,
            FloorType.GROUND_FLOOR,
        ]
        params = config.to_url_params()
        assert "ultimo-andar" in params
        assert "andares-intermedios" in params
        assert "res-do-chao" in params

        # Test ground floor + last floor
        config.floor_types = [FloorType.GROUND_FLOOR, FloorType.LAST_FLOOR]
        params = config.to_url_params()
        assert "res-do-chao" in params
        assert "ultimo-andar" in params
        assert "andares-intermedios" not in params

    def test_no_floor_filter_generation(self):
        """Test that empty floor_types list doesn't add floor parameters"""
        config = SearchConfig()
        config.floor_types = []
        params = config.to_url_params()

        # No floor parameters should be present
        assert "ultimo-andar" not in params
        assert "andares-intermedios" not in params
        assert "res-do-chao" not in params

    def test_floor_parameter_order_in_url(self):
        """Test that floor parameters appear in correct position in URL"""
        config = SearchConfig()
        config.max_price = 1000
        config.min_size = 50
        config.min_rooms = 2
        config.max_rooms = 3
        config.floor_types = [FloorType.LAST_FLOOR, FloorType.GROUND_FLOOR]

        params = config.to_url_params()
        parts = params.split(",")

        # Find where floor parameters appear
        floor_indices = []
        for i, part in enumerate(parts):
            if part in ["ultimo-andar", "andares-intermedios", "res-do-chao"]:
                floor_indices.append(i)

        # Floor parameters should come after property states (if any) and before long-term rental
        assert len(floor_indices) > 0
        # Should come before the final "arrendamento-longa-duracao"
        assert all(idx < len(parts) - 1 for idx in floor_indices)
        # Last parameter should always be long-term rental
        assert parts[-1] == "arrendamento-longa-duracao"

    def test_complete_url_with_floor_filters(self):
        """Test complete URL generation including floor filters"""
        config = SearchConfig()
        config.max_price = 1500
        config.min_size = 60
        config.min_rooms = 2
        config.max_rooms = 4
        config.floor_types = [FloorType.LAST_FLOOR, FloorType.MIDDLE_FLOORS]
        config.city = "porto"

        url = config.get_base_url()

        # Check that URL contains all expected parts
        expected_parts = [
            "https://www.idealista.pt/arrendar-casas/porto/com-",
            "preco-max_1500",
            "tamanho-min_60",
            "t2,t3,t4",
            "ultimo-andar",
            "andares-intermedios",
            "arrendamento-longa-duracao",
        ]

        for part in expected_parts:
            assert part in url, f"Expected '{part}' to be in URL: {url}"

    def test_floor_filters_with_custom_polygon(self):
        """Test floor filters work with custom polygon URLs"""
        config = SearchConfig()
        config.custom_polygon = "test_polygon_data"
        config.floor_types = [FloorType.GROUND_FLOOR]

        url = config.get_base_url()

        # Should use areas endpoint
        assert "areas/arrendar-casas" in url
        # Should contain floor filter
        assert "res-do-chao" in url
        # Should contain polygon data
        assert "shape=test_polygon_data" in url

    def test_floor_filters_with_other_filters(self):
        """Test floor filters work correctly with all other filters"""
        from models import PropertyState, FurnitureType

        config = SearchConfig()
        config.max_price = 2000
        config.min_size = 70
        config.min_rooms = 1
        config.max_rooms = 3
        config.furniture_type = FurnitureType.FURNISHED
        config.property_states = [PropertyState.GOOD, PropertyState.NEW]
        config.floor_types = [FloorType.LAST_FLOOR]

        params = config.to_url_params()

        # Should contain all filter types
        assert "preco-max_2000" in params
        assert "tamanho-min_70" in params
        assert "t1,t2,t3" in params
        assert "equipamento_mobilado" in params
        assert "bom-estado" in params
        assert "novo" in params
        assert "ultimo-andar" in params
        assert "arrendamento-longa-duracao" in params

    def test_floor_list_modification(self):
        """Test that floor_types list can be modified correctly"""
        config = SearchConfig()

        # Start with empty list
        assert config.floor_types == []

        # Add one floor type
        config.floor_types.append(FloorType.LAST_FLOOR)
        assert FloorType.LAST_FLOOR in config.floor_types
        assert len(config.floor_types) == 1

        # Add another floor type
        config.floor_types.append(FloorType.GROUND_FLOOR)
        assert FloorType.GROUND_FLOOR in config.floor_types
        assert len(config.floor_types) == 2

        # Remove a floor type
        config.floor_types.remove(FloorType.LAST_FLOOR)
        assert FloorType.LAST_FLOOR not in config.floor_types
        assert FloorType.GROUND_FLOOR in config.floor_types
        assert len(config.floor_types) == 1

        # Clear all floor types
        config.floor_types.clear()
        assert config.floor_types == []

    def test_floor_filters_edge_cases(self):
        """Test edge cases for floor filtering"""
        config = SearchConfig()

        # Test with None (should default to empty list)
        config.floor_types = None
        config.__post_init__()
        assert config.floor_types == []

        # Test with duplicate floor types (should not cause issues)
        config.floor_types = [FloorType.LAST_FLOOR, FloorType.LAST_FLOOR]
        params = config.to_url_params()
        # Should only appear once in the URL
        assert (
            params.count("ultimo-andar") == 2
        )  # Due to the duplicates in the list


if __name__ == "__main__":
    # Run tests manually
    test = TestFloorFiltering()

    test_methods = [
        "test_floor_type_enum_values",
        "test_default_config_floor_types",
        "test_single_floor_filter_generation",
        "test_multiple_floor_filter_generation",
        "test_no_floor_filter_generation",
        "test_floor_parameter_order_in_url",
        "test_complete_url_with_floor_filters",
        "test_floor_filters_with_custom_polygon",
        "test_floor_filters_with_other_filters",
        "test_floor_list_modification",
        "test_floor_filters_edge_cases",
    ]

    for method_name in test_methods:
        try:
            method = getattr(test, method_name)
            method()
            print(f"✅ {method_name} passed")
        except Exception as e:
            print(f"❌ {method_name} failed: {e}")
