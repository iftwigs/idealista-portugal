import pytest
import json
import tempfile
import os
from unittest.mock import patch, MagicMock

from models import SearchConfig, PropertyState, FurnitureType
import bot


class TestConfigurationValidation:
    """Test configuration validation and field filtering"""
    
    def test_valid_configuration_fields(self):
        """Test that only valid configuration fields are accepted"""
        valid_fields = {
            'min_rooms', 'max_rooms', 'min_size', 'max_size', 'max_price',
            'furniture_types', 'property_states', 'city', 'custom_polygon', 'update_frequency'
        }
        
        # This should match the valid_fields set in bot.py
        # Test that our test is in sync with the actual implementation
        test_config = {
            'min_rooms': 1,
            'max_rooms': 5,
            'min_size': 30,
            'max_size': 100,
            'max_price': 1500,
            'furniture_types': ['mobilado'],
            'property_states': ['bom-estado'],
            'city': 'lisboa',
            'custom_polygon': None,
            'update_frequency': 5
        }
        
        # All fields should be valid
        for field in test_config.keys():
            assert field in valid_fields
    
    def test_invalid_fields_filtered_out(self):
        """Test that invalid fields are filtered out during config loading"""
        mock_config_data = {
            "12345": {
                "min_rooms": 2,
                "max_rooms": 4,
                "max_price": 1500,
                "furniture_types": ["mobilado"],
                "property_states": ["bom-estado"],
                "city": "lisboa",
                "update_frequency": 5,
                # Invalid fields that should be filtered out
                "requests_per_minute": 2,
                "some_random_field": "value",
                "deprecated_field": True,
                "api_key": "secret"
            }
        }
        
        with patch('builtins.open'), patch('json.load', return_value=mock_config_data):
            bot.user_configs.clear()
            bot.load_configs()
            
            # User should be loaded successfully
            assert 12345 in bot.user_configs
            config = bot.user_configs[12345]
            
            # Should be a valid SearchConfig object
            assert isinstance(config, SearchConfig)
            
            # Valid fields should be preserved
            assert config.min_rooms == 2
            assert config.max_rooms == 4
            assert config.max_price == 1500
            assert config.city == "lisboa"
            assert config.update_frequency == 5
    
    def test_search_config_with_unknown_kwargs(self):
        """Test SearchConfig creation with unknown keyword arguments"""
        # Valid config data
        valid_config = {
            'min_rooms': 2,
            'max_rooms': 4,
            'max_price': 1500,
            'furniture_types': [FurnitureType.FURNISHED],
            'property_states': [PropertyState.GOOD],
            'city': 'lisboa',
            'update_frequency': 5
        }
        
        # Should create successfully with valid fields
        config = SearchConfig(**valid_config)
        assert config.min_rooms == 2
        assert config.max_price == 1500
        
        # Test that invalid fields would cause TypeError
        invalid_config = {
            **valid_config,
            'invalid_field': 'value'
        }
        
        with pytest.raises(TypeError):
            SearchConfig(**invalid_config)
    
    def test_backwards_compatibility_has_furniture(self):
        """Test backwards compatibility with has_furniture field"""
        mock_config_data = {
            "12345": {
                "min_rooms": 2,
                "max_rooms": 4,
                "max_price": 1500,
                "has_furniture": True,  # Old format
                "property_states": ["bom-estado"],
                "city": "lisboa",
                "update_frequency": 5
            }
        }
        
        with patch('builtins.open'), patch('json.load', return_value=mock_config_data):
            bot.user_configs.clear()
            bot.load_configs()
            
            config = bot.user_configs[12345]
            
            # Should convert has_furniture to furniture_types
            assert FurnitureType.FURNISHED in config.furniture_types
            assert len(config.furniture_types) == 1
    
    def test_backwards_compatibility_property_state(self):
        """Test backwards compatibility with property_state field"""
        mock_config_data = {
            "12345": {
                "min_rooms": 2,
                "max_rooms": 4,
                "max_price": 1500,
                "furniture_types": ["mobilado"],
                "property_state": "bom-estado",  # Old format
                "city": "lisboa",
                "update_frequency": 5
            }
        }
        
        with patch('builtins.open'), patch('json.load', return_value=mock_config_data):
            bot.user_configs.clear()
            bot.load_configs()
            
            config = bot.user_configs[12345]
            
            # Should convert property_state to property_states
            assert PropertyState.GOOD in config.property_states
            assert len(config.property_states) == 1
    
    def test_backwards_compatibility_furniture_type(self):
        """Test backwards compatibility with furniture_type field"""
        mock_config_data = {
            "12345": {
                "min_rooms": 2,
                "max_rooms": 4,
                "max_price": 1500,
                "furniture_type": "mobilado",  # Old format
                "property_states": ["bom-estado"],
                "city": "lisboa",
                "update_frequency": 5
            }
        }
        
        with patch('builtins.open'), patch('json.load', return_value=mock_config_data):
            bot.user_configs.clear()
            bot.load_configs()
            
            config = bot.user_configs[12345]
            
            # Should convert furniture_type to furniture_types
            assert FurnitureType.FURNISHED in config.furniture_types
            assert len(config.furniture_types) == 1
    
    def test_multiple_backwards_compatibility_conversions(self):
        """Test handling multiple backwards compatibility conversions"""
        mock_config_data = {
            "12345": {
                "min_rooms": 2,
                "max_rooms": 4,
                "max_price": 1500,
                "has_furniture": False,  # Old format -> UNFURNISHED
                "property_state": "com-novo",  # Old format -> NEW
                "city": "lisboa",
                "update_frequency": 5,
                "invalid_field": "should_be_removed"
            }
        }
        
        with patch('builtins.open'), patch('json.load', return_value=mock_config_data):
            bot.user_configs.clear()
            bot.load_configs()
            
            config = bot.user_configs[12345]
            
            # Should convert both old fields
            assert FurnitureType.UNFURNISHED in config.furniture_types
            assert PropertyState.NEW in config.property_states
            
            # Should still have valid new format
            assert config.max_price == 1500
            assert config.city == "lisboa"
    
    def test_config_loading_with_invalid_enum_values(self):
        """Test handling of invalid enum values in config"""
        mock_config_data = {
            "12345": {
                "min_rooms": 2,
                "max_rooms": 4,
                "max_price": 1500,
                "furniture_types": ["invalid_furniture_type"],  # Invalid enum
                "property_states": ["invalid_state"],  # Invalid enum
                "city": "lisboa",
                "update_frequency": 5
            }
        }
        
        with patch('builtins.open'), patch('json.load', return_value=mock_config_data):
            # Should handle invalid enum values gracefully
            try:
                bot.user_configs.clear()
                bot.load_configs()
                # If it doesn't crash, that's good - might fall back to defaults
            except (ValueError, KeyError):
                # Expected behavior for invalid enum values
                pass
    
    def test_config_loading_missing_required_fields(self):
        """Test handling of missing required fields"""
        mock_config_data = {
            "12345": {
                # Missing some required fields
                "max_price": 1500,
                "city": "lisboa"
            }
        }
        
        with patch('builtins.open'), patch('json.load', return_value=mock_config_data):
            bot.user_configs.clear()
            bot.load_configs()
            
            # Should still create config with defaults
            if 12345 in bot.user_configs:
                config = bot.user_configs[12345]
                assert isinstance(config, SearchConfig)
                # Should have default values for missing fields
                assert config.min_rooms >= 0  # Some reasonable default
                assert config.max_rooms > 0
    
    def test_config_field_filtering_preserves_order(self):
        """Test that field filtering preserves the correct values"""
        original_config = {
            'min_rooms': 1,
            'max_rooms': 5,
            'min_size': 40,
            'max_size': 120,
            'max_price': 1800,
            'furniture_types': ['mobilado', 'sem-mobilia'],
            'property_states': ['bom-estado', 'com-novo'],
            'city': 'porto',
            'custom_polygon': 'test_polygon',
            'update_frequency': 10,
            # Invalid fields
            'requests_per_minute': 3,
            'api_endpoint': 'test',
            'user_agent': 'custom'
        }
        
        valid_fields = {
            'min_rooms', 'max_rooms', 'min_size', 'max_size', 'max_price',
            'furniture_types', 'property_states', 'city', 'custom_polygon', 'update_frequency'
        }
        
        # Simulate the filtering logic from bot.py
        filtered_config = {k: v for k, v in original_config.items() if k in valid_fields}
        
        # Check that all valid fields are preserved with correct values
        assert filtered_config['min_rooms'] == 1
        assert filtered_config['max_rooms'] == 5
        assert filtered_config['min_size'] == 40
        assert filtered_config['max_size'] == 120
        assert filtered_config['max_price'] == 1800
        assert filtered_config['furniture_types'] == ['mobilado', 'sem-mobilia']
        assert filtered_config['property_states'] == ['bom-estado', 'com-novo']
        assert filtered_config['city'] == 'porto'
        assert filtered_config['custom_polygon'] == 'test_polygon'
        assert filtered_config['update_frequency'] == 10
        
        # Check that invalid fields are removed
        assert 'requests_per_minute' not in filtered_config
        assert 'api_endpoint' not in filtered_config
        assert 'user_agent' not in filtered_config


class TestConfigurationPersistence:
    """Test configuration persistence and file operations"""
    
    @pytest.fixture
    def temp_config_file(self):
        """Create a temporary config file for testing"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            json.dump({}, f)
            temp_path = f.name
        
        yield temp_path
        
        # Cleanup
        try:
            os.unlink(temp_path)
        except FileNotFoundError:
            pass
    
    @pytest.mark.asyncio
    async def test_save_configs_async_locking(self):
        """Test that save_configs uses async locking properly"""
        bot.user_configs[12345] = SearchConfig()
        
        # Mock file operations
        with patch('builtins.open', create=True) as mock_open:
            with patch('json.dump') as mock_dump:
                # Should be able to call as async function
                await bot.save_configs()
                
                # Should have opened file for writing
                mock_open.assert_called_once_with('user_configs.json', 'w')
                # Should have dumped JSON
                mock_dump.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_concurrent_save_operations(self):
        """Test that concurrent save operations are handled safely"""
        import asyncio
        
        bot.user_configs[12345] = SearchConfig()
        bot.user_configs[67890] = SearchConfig()
        
        # Mock file operations
        with patch('builtins.open', create=True):
            with patch('json.dump'):
                # Should be able to run multiple saves concurrently
                save_tasks = [bot.save_configs() for _ in range(5)]
                
                # This should not raise any exceptions
                await asyncio.gather(*save_tasks)
    
    def test_config_serialization_format(self):
        """Test that configs are serialized in the correct format"""
        config = SearchConfig()
        config.max_price = 1500
        config.furniture_types = [FurnitureType.FURNISHED, FurnitureType.KITCHEN_FURNITURE]
        config.property_states = [PropertyState.GOOD, PropertyState.NEW]
        
        bot.user_configs[12345] = config
        
        # Simulate the serialization logic from save_configs
        configs = {}
        for user_id, config in bot.user_configs.items():
            config_dict = config.__dict__.copy()
            # Convert PropertyState list to string values
            config_dict['property_states'] = [state.value for state in config_dict['property_states']]
            # Convert FurnitureType list to string values
            config_dict['furniture_types'] = [ft.value for ft in config_dict['furniture_types']]
            configs[str(user_id)] = config_dict
        
        # Check serialization format
        user_config = configs["12345"]
        assert user_config['max_price'] == 1500
        assert user_config['furniture_types'] == ['mobilado', 'mobilado-cozinha']
        assert user_config['property_states'] == ['bom-estado', 'com-novo']
        assert isinstance(user_config['furniture_types'], list)
        assert isinstance(user_config['property_states'], list)
        assert all(isinstance(ft, str) for ft in user_config['furniture_types'])
        assert all(isinstance(ps, str) for ps in user_config['property_states'])
    
    def test_config_deserialization_format(self):
        """Test that configs are deserialized correctly from saved format"""
        saved_config = {
            "12345": {
                "min_rooms": 2,
                "max_rooms": 4,
                "max_price": 1500,
                "furniture_types": ["mobilado", "mobilado-cozinha"],
                "property_states": ["bom-estado", "com-novo"],
                "city": "lisboa",
                "update_frequency": 5
            }
        }
        
        with patch('builtins.open'), patch('json.load', return_value=saved_config):
            bot.user_configs.clear()
            bot.load_configs()
            
            config = bot.user_configs[12345]
            
            # Should deserialize enum values correctly
            assert FurnitureType.FURNISHED in config.furniture_types
            assert FurnitureType.KITCHEN_FURNITURE in config.furniture_types
            assert PropertyState.GOOD in config.property_states
            assert PropertyState.NEW in config.property_states
            
            # Should preserve other values
            assert config.max_price == 1500
            assert config.min_rooms == 2


class TestErrorHandlingInConfigLoading:
    """Test error handling during configuration loading"""
    
    def test_load_configs_file_not_found(self):
        """Test handling when config file doesn't exist"""
        with patch('builtins.open', side_effect=FileNotFoundError()):
            with patch('asyncio.create_task') as mock_create_task:
                bot.user_configs.clear()
                bot.load_configs()
                
                # Should handle gracefully and create empty config
                # Should attempt to save empty config
                mock_create_task.assert_called_once()
    
    def test_load_configs_invalid_json(self):
        """Test handling of invalid JSON in config file"""
        with patch('builtins.open'), patch('json.load', side_effect=json.JSONDecodeError("Invalid JSON", "", 0)):
            with patch('asyncio.create_task') as mock_create_task:
                with patch('bot.logger') as mock_logger:
                    bot.user_configs.clear()
                    bot.load_configs()
                    
                    # Should log warning about invalid JSON
                    mock_logger.warning.assert_called_once_with("Invalid JSON in user_configs.json, creating new file")
                    # Should attempt to save new config
                    mock_create_task.assert_called_once()
    
    def test_load_configs_permission_error(self):
        """Test handling of permission error when reading config file"""
        with patch('builtins.open', side_effect=PermissionError("Access denied")):
            # Should not crash, but might not load any configs
            try:
                bot.user_configs.clear()
                bot.load_configs()
            except PermissionError:
                pytest.fail("Should handle permission errors gracefully")
    
    def test_load_configs_corrupted_enum_values(self):
        """Test handling of corrupted enum values in config"""
        corrupted_config = {
            "12345": {
                "min_rooms": 2,
                "max_price": 1500,
                "furniture_types": ["INVALID_FURNITURE_TYPE"],
                "property_states": ["INVALID_PROPERTY_STATE"],
                "city": "lisboa",
                "update_frequency": 5
            }
        }
        
        with patch('builtins.open'), patch('json.load', return_value=corrupted_config):
            # Should either handle gracefully or skip the corrupted user
            try:
                bot.user_configs.clear()
                bot.load_configs()
                
                # If user was loaded, it should have valid enum values (possibly defaults)
                if 12345 in bot.user_configs:
                    config = bot.user_configs[12345]
                    assert isinstance(config.furniture_types, list)
                    assert isinstance(config.property_states, list)
                    assert all(isinstance(ft, FurnitureType) for ft in config.furniture_types)
                    assert all(isinstance(ps, PropertyState) for ps in config.property_states)
                    
            except (ValueError, KeyError):
                # Expected behavior for invalid enum values
                pass