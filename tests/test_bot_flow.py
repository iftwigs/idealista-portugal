import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json
import tempfile
import os
import asyncio

from telegram import Update, CallbackQuery, Message, User, Chat
from telegram.ext import ContextTypes
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

from models import SearchConfig, PropertyState, FurnitureType
import bot


@pytest.fixture
def mock_update():
    """Create a mock Telegram update object"""
    update = MagicMock(spec=Update)
    update.effective_user = MagicMock(spec=User)
    update.effective_user.id = 12345
    update.effective_chat = MagicMock(spec=Chat)
    update.effective_chat.id = 12345
    update.message = MagicMock(spec=Message)
    update.callback_query = MagicMock(spec=CallbackQuery)
    update.callback_query.answer = AsyncMock()
    update.callback_query.edit_message_text = AsyncMock()
    update.callback_query.message = MagicMock(spec=Message)
    update.callback_query.message.edit_text = AsyncMock()
    update.callback_query.message.reply_text = AsyncMock()
    update.message.reply_text = AsyncMock()
    return update


@pytest.fixture
def mock_context():
    """Create a mock context object"""
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    context.user_data = {}
    context.chat_data = {}
    return context


@pytest.fixture
def temp_config_file():
    """Create a temporary config file for testing"""
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
        f.write("{}")
        temp_path = f.name

    # Patch the config file path
    original_load = bot.load_configs
    original_save = bot.save_configs

    def mock_load():
        try:
            with open(temp_path, "r") as f:
                configs = json.load(f)
                for user_id, config in configs.items():
                    # Handle backwards compatibility for property_state -> property_states
                    if "property_state" in config and "property_states" not in config:
                        config["property_states"] = [
                            PropertyState(config["property_state"])
                        ]
                        config.pop("property_state", None)  # Remove old field
                    elif "property_states" in config:
                        config["property_states"] = [
                            PropertyState(state) for state in config["property_states"]
                        ]

                    # Handle backwards compatibility for furniture setting
                    if "has_furniture" in config and "furniture_type" not in config:
                        config["furniture_type"] = (
                            FurnitureType.FURNISHED
                            if config["has_furniture"]
                            else FurnitureType.INDIFFERENT
                        )
                        config.pop("has_furniture", None)  # Remove old field
                    elif "furniture_types" in config and "furniture_type" not in config:
                        config["furniture_type"] = (
                            FurnitureType(config["furniture_types"][0])
                            if config["furniture_types"]
                            else FurnitureType.INDIFFERENT
                        )
                        config.pop("furniture_types", None)  # Remove old field
                    elif "furniture_type" in config:
                        config["furniture_type"] = FurnitureType(
                            config["furniture_type"]
                        )

                    bot.user_configs[int(user_id)] = SearchConfig(**config)
        except (FileNotFoundError, json.JSONDecodeError):
            pass

    def mock_save():
        configs = {}
        for user_id, config in bot.user_configs.items():
            config_dict = config.__dict__.copy()
            config_dict["property_states"] = [
                state.value for state in config_dict["property_states"]
            ]
            config_dict["furniture_type"] = config_dict["furniture_type"].value
            configs[str(user_id)] = config_dict

        with open(temp_path, "w") as f:
            json.dump(configs, f, indent=2)

    bot.load_configs = mock_load
    bot.save_configs = mock_save

    yield temp_path

    # Cleanup
    os.unlink(temp_path)
    bot.load_configs = original_load
    bot.save_configs = original_save


class TestBotConversationFlow:
    """Test bot conversation flow and navigation"""

    @pytest.mark.asyncio
    async def test_start_command(self, mock_update, mock_context):
        """Test /start command creates user config and shows main menu"""
        bot.user_configs.clear()

        result = await bot.start(mock_update, mock_context)

        assert result == bot.CHOOSING
        assert 12345 in bot.user_configs
        assert isinstance(bot.user_configs[12345], SearchConfig)
        mock_update.message.reply_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_command_group_chat(self, mock_update, mock_context):
        """Test /start command in group chat (should be rejected)"""
        mock_update.effective_chat.id = -123  # Negative ID for group

        result = await bot.start(mock_update, mock_context)

        assert result == -1
        mock_update.message.reply_text.assert_called_once()
        assert "private chats" in mock_update.message.reply_text.call_args[0][0]

    @pytest.mark.asyncio
    async def test_show_settings(self, mock_update, mock_context):
        """Test show current settings functionality"""
        bot.user_configs[12345] = SearchConfig()
        mock_update.callback_query.data = "show"

        result = await bot.button_handler(mock_update, mock_context)

        assert result == bot.CHOOSING
        mock_update.callback_query.message.reply_text.assert_called_once()
        call_args = mock_update.callback_query.message.reply_text.call_args[0][0]
        assert "Current settings:" in call_args
        assert "Minimum rooms:" in call_args
        assert "Size:" in call_args
        assert "Max Price:" in call_args

    @pytest.mark.asyncio
    async def test_back_button_navigation(self, mock_update, mock_context):
        """Test back button returns to main menu"""
        mock_update.callback_query.data = "back"

        result = await bot.button_handler(mock_update, mock_context)

        assert result == bot.CHOOSING
        mock_update.callback_query.edit_message_text.assert_called_once()
        call_args = mock_update.callback_query.edit_message_text.call_args[0][0]
        assert "Please choose an option:" in call_args

    @pytest.mark.asyncio
    async def test_room_setting_flow(self, mock_update, mock_context):
        """Test room setting conversation flow"""
        bot.user_configs[12345] = SearchConfig()

        # Test entering room setting
        mock_update.callback_query.data = "rooms"
        result = await bot.button_handler(mock_update, mock_context)
        assert result == bot.SETTING_ROOMS

        # Test selecting room count
        mock_update.callback_query.data = "rooms_2"
        result = await bot.button_handler(mock_update, mock_context)
        assert result == bot.CHOOSING
        assert bot.user_configs[12345].min_rooms == 2

    @pytest.mark.asyncio
    async def test_furniture_toggle_flow(self, mock_update, mock_context):
        """Test furniture checkbox toggle functionality"""
        bot.user_configs[12345] = SearchConfig()
        original_furniture = bot.user_configs[12345].furniture_type

        # Test toggling furnished option
        mock_update.callback_query.data = "furniture_toggle_furnished"
        result = await bot.button_handler(mock_update, mock_context)

        assert result == bot.SETTING_FURNITURE
        # Should have a valid furniture type
        assert isinstance(bot.user_configs[12345].furniture_type, FurnitureType)

    @pytest.mark.asyncio
    async def test_property_state_toggle_flow(self, mock_update, mock_context):
        """Test property state checkbox toggle functionality"""
        bot.user_configs[12345] = SearchConfig()

        # Test adding a new state
        mock_update.callback_query.data = "state_toggle_new"
        result = await bot.button_handler(mock_update, mock_context)

        assert result == bot.SETTING_STATE
        assert PropertyState.NEW in bot.user_configs[12345].property_states

        # Test removing a state (but keeping at least one)
        mock_update.callback_query.data = "state_toggle_good"
        result = await bot.button_handler(mock_update, mock_context)

        assert result == bot.SETTING_STATE
        # Should still have at least one state
        assert len(bot.user_configs[12345].property_states) >= 1

    @pytest.mark.asyncio
    async def test_price_input_flow(self, mock_update, mock_context):
        """Test price input conversation flow"""
        bot.user_configs[12345] = SearchConfig()

        # Test entering price setting
        mock_update.callback_query.data = "price"
        with patch("filters.set_price") as mock_set_price:
            mock_set_price.return_value = bot.WAITING_FOR_PRICE
            result = await bot.button_handler(mock_update, mock_context)
            assert result == bot.WAITING_FOR_PRICE

        # Test valid price input
        mock_update.message.text = "1500"
        result = await bot.handle_price_input(mock_update, mock_context)

        assert result == bot.CHOOSING
        assert bot.user_configs[12345].max_price == 1500

    @pytest.mark.asyncio
    async def test_invalid_price_input(self, mock_update, mock_context):
        """Test invalid price input handling"""
        bot.user_configs[12345] = SearchConfig()

        # Test invalid price input
        mock_update.message.text = "invalid_price"
        result = await bot.handle_price_input(mock_update, mock_context)

        assert result == bot.WAITING_FOR_PRICE
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "valid positive number" in call_args

    @pytest.mark.asyncio
    async def test_polygon_input_flow(self, mock_update, mock_context):
        """Test custom polygon URL input flow"""
        bot.user_configs[12345] = SearchConfig()

        # Test valid polygon URL
        valid_url = "https://www.idealista.pt/arrendar-casas/lisboa/?shape=test_polygon_data&ordem=atualizado-desc"
        mock_update.message.text = valid_url

        result = await bot.handle_polygon_input(mock_update, mock_context)

        assert result == bot.CHOOSING
        assert bot.user_configs[12345].custom_polygon == "test_polygon_data"

    @pytest.mark.asyncio
    async def test_invalid_polygon_input(self, mock_update, mock_context):
        """Test invalid polygon URL input handling"""
        bot.user_configs[12345] = SearchConfig()

        # Test invalid URL
        mock_update.message.text = "invalid_url"
        result = await bot.handle_polygon_input(mock_update, mock_context)

        assert result == bot.WAITING_FOR_POLYGON_URL
        mock_update.message.reply_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_reset_settings(self, mock_update, mock_context):
        """Test reset settings functionality"""
        # Set up custom config
        bot.user_configs[12345] = SearchConfig()
        bot.user_configs[12345].max_price = 1500
        bot.user_configs[12345].min_rooms = 3

        mock_update.callback_query.data = "reset_settings"
        result = await bot.button_handler(mock_update, mock_context)

        assert result == bot.CHOOSING
        # Should be reset to defaults
        config = bot.user_configs[12345]
        assert config.max_price == 2000  # Default
        assert config.min_rooms == 1  # Default


class TestConfigurationPersistence:
    """Test configuration saving and loading"""

    def test_config_save_load(self, temp_config_file):
        """Test saving and loading configurations"""
        # Create test config
        config = SearchConfig()
        config.max_price = 1500
        config.min_rooms = 2
        config.furniture_type = FurnitureType.FURNISHED
        config.property_states = [PropertyState.GOOD, PropertyState.NEW]

        bot.user_configs[12345] = config
        bot.save_configs()

        # Clear and reload
        bot.user_configs.clear()
        bot.load_configs()

        # Verify loaded config
        loaded_config = bot.user_configs[12345]
        assert loaded_config.max_price == 1500
        assert loaded_config.min_rooms == 2
        assert loaded_config.furniture_type == FurnitureType.FURNISHED
        assert PropertyState.GOOD in loaded_config.property_states
        assert PropertyState.NEW in loaded_config.property_states

    def test_backwards_compatibility(self, temp_config_file):
        """Test backwards compatibility with old config format"""
        # Create old format config
        old_config = {
            "12345": {
                "min_rooms": 2,
                "max_rooms": 10,
                "min_size": 50,
                "max_size": 200,
                "max_price": 1500,
                "has_furniture": True,  # Old format
                "property_state": "bom-estado",  # Old format
                "city": "lisboa",
                "update_frequency": 10,
            }
        }

        with open(temp_config_file, "w") as f:
            json.dump(old_config, f)

        bot.user_configs.clear()
        bot.load_configs()

        # Verify migration
        config = bot.user_configs[12345]
        assert config.max_price == 1500
        assert config.furniture_type == FurnitureType.FURNISHED
        assert PropertyState.GOOD in config.property_states


class TestMonitoringFlow:
    """Test monitoring start/stop functionality"""

    @pytest.mark.asyncio
    async def test_start_monitoring(self, mock_update, mock_context):
        """Test starting monitoring"""
        bot.user_configs[12345] = SearchConfig()
        bot.monitoring_tasks.clear()

        mock_update.callback_query.data = "start_monitoring"

        with patch("asyncio.create_task") as mock_create_task:
            mock_task = MagicMock()
            mock_task.done.return_value = False
            mock_task.exception.return_value = None
            mock_task.add_done_callback = MagicMock()
            mock_create_task.return_value = mock_task

            with patch("bot.stats_manager"):  # Mock stats manager
                result = await bot.button_handler(mock_update, mock_context)

            assert result == bot.CHOOSING
            assert 12345 in bot.monitoring_tasks
            mock_create_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_monitoring(self, mock_update, mock_context):
        """Test stopping monitoring"""

        # Create a real task that we can cancel and await
        async def dummy_task():
            await asyncio.sleep(1000)  # Task that would run forever

        task = asyncio.create_task(dummy_task())
        bot.monitoring_tasks[12345] = task

        mock_update.callback_query.data = "stop_monitoring"
        result = await bot.button_handler(mock_update, mock_context)

        assert result == bot.CHOOSING
        assert task.cancelled()  # Task should be cancelled

        # Clean up
        if 12345 in bot.monitoring_tasks:
            del bot.monitoring_tasks[12345]

    def test_dynamic_menu_generation(self):
        """Test dynamic main menu keyboard generation"""
        # Clear any existing monitoring for this user
        if 12345 in bot.monitoring_tasks:
            del bot.monitoring_tasks[12345]

        # Test without monitoring
        keyboard = bot.get_main_menu_keyboard(12345)
        start_button_found = any(
            "🚀 Start searching" in str(button) for row in keyboard for button in row
        )
        assert start_button_found

        # Test with active monitoring
        mock_task = MagicMock()
        mock_task.done.return_value = False
        bot.monitoring_tasks[12345] = mock_task

        keyboard = bot.get_main_menu_keyboard(12345)
        stop_button_found = any(
            "🛑 Stop monitoring" in str(button) for row in keyboard for button in row
        )
        assert stop_button_found
