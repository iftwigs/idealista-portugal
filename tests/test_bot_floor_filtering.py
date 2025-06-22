import pytest
import sys
import os
from unittest.mock import AsyncMock, MagicMock

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

from bot import (
    button_handler,
    user_configs,
    CHOOSING,
    SETTING_FLOOR,
)
from filters import set_floor
from models import SearchConfig, FloorType


@pytest.fixture
def mock_update():
    """Create a mock update object"""
    update = MagicMock()
    update.effective_user.id = 12345
    update.effective_chat.id = 12345
    update.callback_query = MagicMock()
    update.callback_query.answer = AsyncMock()
    update.callback_query.message.edit_text = AsyncMock()
    update.callback_query.edit_message_text = AsyncMock()
    return update


@pytest.fixture
def mock_context():
    """Create a mock context object"""
    context = MagicMock()
    context.user_data = {}
    return context


class TestFloorFilteringBot:
    """Test floor filtering functionality in bot"""

    @pytest.mark.asyncio
    async def test_set_floor_button(self, mock_update, mock_context):
        """Test the set floor button triggers correct handler"""
        mock_update.callback_query.data = "floor"

        # Clear user configs for clean test
        user_configs.clear()

        result = await set_floor(mock_update, mock_context)
        assert result == SETTING_FLOOR
        mock_update.callback_query.message.edit_text.assert_called_once()

        # Check that user config was created
        assert 12345 in user_configs
        assert isinstance(user_configs[12345], SearchConfig)

    @pytest.mark.asyncio
    async def test_floor_toggle_last_floor(self, mock_update, mock_context):
        """Test toggling last floor option"""
        mock_update.callback_query.data = "floor_toggle_last"

        # Set up user config
        user_configs[12345] = SearchConfig()
        assert FloorType.LAST_FLOOR not in user_configs[12345].floor_types

        result = await button_handler(mock_update, mock_context)
        assert result == SETTING_FLOOR

        # Check that last floor was added
        assert FloorType.LAST_FLOOR in user_configs[12345].floor_types
        mock_update.callback_query.edit_message_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_floor_toggle_middle_floors(self, mock_update, mock_context):
        """Test toggling middle floors option"""
        mock_update.callback_query.data = "floor_toggle_middle"

        # Set up user config
        user_configs[12345] = SearchConfig()
        assert FloorType.MIDDLE_FLOORS not in user_configs[12345].floor_types

        result = await button_handler(mock_update, mock_context)
        assert result == SETTING_FLOOR

        # Check that middle floors was added
        assert FloorType.MIDDLE_FLOORS in user_configs[12345].floor_types

    @pytest.mark.asyncio
    async def test_floor_toggle_ground_floor(self, mock_update, mock_context):
        """Test toggling ground floor option"""
        mock_update.callback_query.data = "floor_toggle_ground"

        # Set up user config
        user_configs[12345] = SearchConfig()
        assert FloorType.GROUND_FLOOR not in user_configs[12345].floor_types

        result = await button_handler(mock_update, mock_context)
        assert result == SETTING_FLOOR

        # Check that ground floor was added
        assert FloorType.GROUND_FLOOR in user_configs[12345].floor_types

    @pytest.mark.asyncio
    async def test_floor_toggle_remove_selection(self, mock_update, mock_context):
        """Test removing a floor selection by toggling it off"""
        mock_update.callback_query.data = "floor_toggle_last"

        # Set up user config with last floor already selected
        user_configs[12345] = SearchConfig()
        user_configs[12345].floor_types = [FloorType.LAST_FLOOR]

        result = await button_handler(mock_update, mock_context)
        assert result == SETTING_FLOOR

        # Check that last floor was removed
        assert FloorType.LAST_FLOOR not in user_configs[12345].floor_types

    @pytest.mark.asyncio
    async def test_floor_multiple_selections(self, mock_update, mock_context):
        """Test selecting multiple floor types"""
        user_configs[12345] = SearchConfig()

        # Select last floor
        mock_update.callback_query.data = "floor_toggle_last"
        await button_handler(mock_update, mock_context)
        assert FloorType.LAST_FLOOR in user_configs[12345].floor_types

        # Select ground floor
        mock_update.callback_query.data = "floor_toggle_ground"
        await button_handler(mock_update, mock_context)
        assert FloorType.GROUND_FLOOR in user_configs[12345].floor_types
        assert FloorType.LAST_FLOOR in user_configs[12345].floor_types

        # Should have both selected
        assert len(user_configs[12345].floor_types) == 2

    @pytest.mark.asyncio
    async def test_floor_keyboard_shows_selections(self, mock_update, mock_context):
        """Test that keyboard shows current floor selections correctly"""
        # Set up user config with some floors selected
        user_configs[12345] = SearchConfig()
        user_configs[12345].floor_types = [FloorType.LAST_FLOOR, FloorType.GROUND_FLOOR]

        result = await set_floor(mock_update, mock_context)
        assert result == SETTING_FLOOR

        # Check that edit_text was called with the correct message
        call_args = mock_update.callback_query.message.edit_text.call_args
        assert call_args is not None

        # The message should contain the floor selection text
        assert "Select floor preferences" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_floor_back_button(self, mock_update, mock_context):
        """Test back button from floor selection"""
        mock_update.callback_query.data = "back"

        # Should return to main menu
        result = await button_handler(mock_update, mock_context)
        assert result == CHOOSING

    def test_floor_config_in_show_settings(self):
        """Test that floor configuration appears in settings display"""
        # Set up user config with floor types
        user_configs[12345] = SearchConfig()
        user_configs[12345].floor_types = [
            FloorType.LAST_FLOOR,
            FloorType.MIDDLE_FLOORS,
        ]

        config = user_configs[12345]

        # Test the floor display logic
        floor_display = (
            ", ".join(
                [floor.name.replace("_", " ").title() for floor in config.floor_types]
            )
            if config.floor_types
            else "Any"
        )
        assert "Last Floor" in floor_display
        assert "Middle Floors" in floor_display

        # Test empty floor types
        config.floor_types = []
        floor_display = (
            ", ".join(
                [floor.name.replace("_", " ").title() for floor in config.floor_types]
            )
            if config.floor_types
            else "Any"
        )
        assert floor_display == "Any"

    def test_floor_config_persistence(self):
        """Test that floor configuration is properly saved and loaded"""
        # Create a config with floor types
        config = SearchConfig()
        config.floor_types = [FloorType.LAST_FLOOR, FloorType.GROUND_FLOOR]

        # Test serialization (what would be saved to JSON)
        config_dict = config.__dict__.copy()
        config_dict["floor_types"] = [
            floor_type.value for floor_type in config_dict["floor_types"]
        ]

        expected_values = ["com-ultimo-andar", "res-do-chao"]
        assert config_dict["floor_types"] == expected_values

        # Test deserialization (loading from JSON)
        restored_floor_types = [FloorType(floor_type) for floor_type in expected_values]
        assert FloorType.LAST_FLOOR in restored_floor_types
        assert FloorType.GROUND_FLOOR in restored_floor_types

    def test_floor_url_integration(self):
        """Test that floor filters are properly integrated into URL generation"""
        config = SearchConfig()
        config.floor_types = [FloorType.LAST_FLOOR, FloorType.MIDDLE_FLOORS]
        config.max_price = 1500
        config.min_rooms = 2
        config.city = "lisboa"

        url = config.get_base_url()

        # Should contain floor parameters
        assert "com-ultimo-andar" in url
        assert "andares-intermedios" in url

        # Should also contain other parameters
        assert "preco-max_1500" in url
        assert "t2" in url
        assert "lisboa" in url


if __name__ == "__main__":
    # Manual test runner
    import asyncio

    async def run_async_tests():
        """Run async tests manually"""
        test_instance = TestFloorFilteringBot()

        # Create mock objects
        mock_update = MagicMock()
        mock_update.effective_user.id = 12345
        mock_update.effective_chat.id = 12345
        mock_update.callback_query = MagicMock()
        mock_update.callback_query.answer = AsyncMock()
        mock_update.callback_query.message.edit_text = AsyncMock()
        mock_update.callback_query.edit_message_text = AsyncMock()

        mock_context = MagicMock()
        mock_context.user_data = {}

        # Clear user configs
        user_configs.clear()

        try:
            await test_instance.test_set_floor_button(mock_update, mock_context)
            print("✅ test_set_floor_button passed")
        except Exception as e:
            print(f"❌ test_set_floor_button failed: {e}")

        try:
            await test_instance.test_floor_toggle_last_floor(mock_update, mock_context)
            print("✅ test_floor_toggle_last_floor passed")
        except Exception as e:
            print(f"❌ test_floor_toggle_last_floor failed: {e}")

        try:
            await test_instance.test_floor_multiple_selections(
                mock_update, mock_context
            )
            print("✅ test_floor_multiple_selections passed")
        except Exception as e:
            print(f"❌ test_floor_multiple_selections failed: {e}")

    # Run sync tests
    test_instance = TestFloorFilteringBot()

    try:
        test_instance.test_floor_config_in_show_settings()
        print("✅ test_floor_config_in_show_settings passed")
    except Exception as e:
        print(f"❌ test_floor_config_in_show_settings failed: {e}")

    try:
        test_instance.test_floor_config_persistence()
        print("✅ test_floor_config_persistence passed")
    except Exception as e:
        print(f"❌ test_floor_config_persistence failed: {e}")

    try:
        test_instance.test_floor_url_integration()
        print("✅ test_floor_url_integration passed")
    except Exception as e:
        print(f"❌ test_floor_url_integration failed: {e}")

    # Run async tests
    asyncio.run(run_async_tests())
