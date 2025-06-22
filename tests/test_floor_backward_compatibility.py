import json
import os
import tempfile
import pytest
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

from bot import load_configs, user_configs
from models import FloorType, PropertyState, FurnitureType


class TestFloorBackwardCompatibility:
    """Test backward compatibility for floor type configuration loading"""

    def test_load_old_floor_type_values(self):
        """Test loading config files with old floor type values"""
        # Create a temporary config with old floor values
        old_config = {
            "12345": {
                "min_rooms": 2,
                "max_rooms": 4,
                "max_price": 1500,
                "furniture_type": "indifferent",
                "property_states": ["bom-estado"],
                "floor_types": ["com-ultimo-andar", "andares-intermedios"],  # Old values
                "city": "lisboa",
                "update_frequency": 10,
            }
        }

        # Use a temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp_file:
            json.dump(old_config, tmp_file)
            tmp_file_path = tmp_file.name

        try:
            # Backup original config if exists
            original_config_path = "user_configs.json"
            backup_exists = os.path.exists(original_config_path)
            if backup_exists:
                os.rename(original_config_path, f"{original_config_path}.test_backup")

            # Copy temporary config to expected location
            os.rename(tmp_file_path, original_config_path)

            # Clear existing configs
            user_configs.clear()

            # Load configs with backward compatibility
            load_configs()

            # Verify the config was loaded correctly
            assert 12345 in user_configs
            config = user_configs[12345]

            # Check that old floor values were converted to new enum values
            expected_floors = [FloorType.LAST_FLOOR, FloorType.MIDDLE_FLOORS]
            assert config.floor_types == expected_floors

            # Check that the enum values are the new correct ones
            floor_values = [floor.value for floor in config.floor_types]
            assert "ultimo-andar" in floor_values
            assert "andares-intermedios" in floor_values
            assert "com-ultimo-andar" not in floor_values  # Old value should not be present

            # Verify other fields were loaded correctly
            assert config.min_rooms == 2
            assert config.max_price == 1500
            assert config.city == "lisboa"

        finally:
            # Cleanup: restore original config
            if os.path.exists(original_config_path):
                os.remove(original_config_path)
            if backup_exists:
                os.rename(f"{original_config_path}.test_backup", original_config_path)

    def test_load_mixed_old_and_new_floor_values(self):
        """Test loading config with mix of old and new floor values"""
        mixed_config = {
            "67890": {
                "min_rooms": 1,
                "max_price": 2000,
                "furniture_type": "equipamento_mobilado",
                "property_states": ["bom-estado", "com-novo"],
                "floor_types": [
                    "com-ultimo-andar",  # Old value
                    "res-do-chao",       # Correct value
                    "andares-intermedios"  # Correct value
                ],
                "city": "porto",
                "update_frequency": 5,
            }
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp_file:
            json.dump(mixed_config, tmp_file)
            tmp_file_path = tmp_file.name

        try:
            original_config_path = "user_configs.json"
            backup_exists = os.path.exists(original_config_path)
            if backup_exists:
                os.rename(original_config_path, f"{original_config_path}.test_backup")

            os.rename(tmp_file_path, original_config_path)
            user_configs.clear()
            load_configs()

            assert 67890 in user_configs
            config = user_configs[67890]

            # Should have all three floor types, with old value converted
            expected_floors = [
                FloorType.LAST_FLOOR,    # Converted from com-ultimo-andar
                FloorType.GROUND_FLOOR,  # res-do-chao
                FloorType.MIDDLE_FLOORS  # andares-intermedios
            ]
            assert set(config.floor_types) == set(expected_floors)

        finally:
            if os.path.exists(original_config_path):
                os.remove(original_config_path)
            if backup_exists:
                os.rename(f"{original_config_path}.test_backup", original_config_path)

    def test_load_invalid_floor_values_are_skipped(self):
        """Test that invalid floor values are skipped with warning"""
        invalid_config = {
            "11111": {
                "min_rooms": 1,
                "max_price": 1000,
                "furniture_type": "indifferent",
                "property_states": ["bom-estado"],
                "floor_types": [
                    "ultimo-andar",        # Valid
                    "invalid-floor-type",  # Invalid - should be skipped
                    "res-do-chao"         # Valid
                ],
                "city": "lisboa",
                "update_frequency": 15,
            }
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp_file:
            json.dump(invalid_config, tmp_file)
            tmp_file_path = tmp_file.name

        try:
            original_config_path = "user_configs.json"
            backup_exists = os.path.exists(original_config_path)
            if backup_exists:
                os.rename(original_config_path, f"{original_config_path}.test_backup")

            os.rename(tmp_file_path, original_config_path)
            user_configs.clear()
            load_configs()

            assert 11111 in user_configs
            config = user_configs[11111]

            # Should only have the valid floor types
            expected_floors = [FloorType.LAST_FLOOR, FloorType.GROUND_FLOOR]
            assert set(config.floor_types) == set(expected_floors)

        finally:
            if os.path.exists(original_config_path):
                os.remove(original_config_path)
            if backup_exists:
                os.rename(f"{original_config_path}.test_backup", original_config_path)

    def test_new_floor_values_load_correctly(self):
        """Test that new floor values load without any conversion needed"""
        new_config = {
            "22222": {
                "min_rooms": 3,
                "max_price": 1800,
                "furniture_type": "equipamento_so-cozinha-equipada",
                "property_states": ["para-reformar"],
                "floor_types": [
                    "ultimo-andar",
                    "andares-intermedios",
                    "res-do-chao"
                ],
                "city": "porto",
                "update_frequency": 20,
            }
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp_file:
            json.dump(new_config, tmp_file)
            tmp_file_path = tmp_file.name

        try:
            original_config_path = "user_configs.json"
            backup_exists = os.path.exists(original_config_path)
            if backup_exists:
                os.rename(original_config_path, f"{original_config_path}.test_backup")

            os.rename(tmp_file_path, original_config_path)
            user_configs.clear()
            load_configs()

            assert 22222 in user_configs
            config = user_configs[22222]

            # Should have all three floor types
            expected_floors = [
                FloorType.LAST_FLOOR,
                FloorType.MIDDLE_FLOORS,
                FloorType.GROUND_FLOOR
            ]
            assert set(config.floor_types) == set(expected_floors)

            # Verify the values are correct
            floor_values = [floor.value for floor in config.floor_types]
            assert "ultimo-andar" in floor_values
            assert "andares-intermedios" in floor_values
            assert "res-do-chao" in floor_values

        finally:
            if os.path.exists(original_config_path):
                os.remove(original_config_path)
            if backup_exists:
                os.rename(f"{original_config_path}.test_backup", original_config_path)


if __name__ == "__main__":
    # Run tests manually
    test_instance = TestFloorBackwardCompatibility()
    
    test_methods = [
        "test_load_old_floor_type_values",
        "test_load_mixed_old_and_new_floor_values", 
        "test_load_invalid_floor_values_are_skipped",
        "test_new_floor_values_load_correctly",
    ]
    
    for method_name in test_methods:
        try:
            method = getattr(test_instance, method_name)
            method()
            print(f"✅ {method_name} passed")
        except Exception as e:
            print(f"❌ {method_name} failed: {e}")
            import traceback
            traceback.print_exc()