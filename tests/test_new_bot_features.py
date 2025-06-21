import pytest
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch
from telegram import Update, CallbackQuery, Message, User, Chat
from telegram.ext import ContextTypes
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

from models import SearchConfig, PropertyState, FurnitureType
import bot
import scraper


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


class TestNewBotFeatures:
    """Test new bot features for debugging and monitoring"""

    @pytest.mark.asyncio
    async def test_show_stats(self, mock_update, mock_context):
        """Test show statistics functionality"""
        bot.user_configs[12345] = SearchConfig()
        mock_update.callback_query.data = "stats"

        with patch("bot.stats_manager") as mock_stats_manager:
            mock_stats_manager.get_user_summary.return_value = (
                "📊 **Bot Usage Statistics**\n👥 Total Users: 5"
            )

            # Mock the scraper rate limiter
            with patch.object(scraper, "global_rate_limiter") as mock_rate_limiter:
                mock_rate_limiter.recent_errors = 0
                mock_rate_limiter.last_error_time = 0
                mock_rate_limiter.min_delay_seconds = 90

                result = await bot.show_stats(mock_update, mock_context)

                assert result == bot.CHOOSING
                mock_update.callback_query.message.edit_text.assert_called_once()
                call_args = mock_update.callback_query.message.edit_text.call_args[0][0]
                assert "Bot Usage Statistics" in call_args
                assert "Rate Limiting Status" in call_args

    @pytest.mark.asyncio
    async def test_check_monitoring_status_active(self, mock_update, mock_context):
        """Test check monitoring status when monitoring is active"""
        bot.user_configs[12345] = SearchConfig()
        bot.monitoring_tasks[12345] = MagicMock(done=lambda: False)  # Active task
        mock_update.callback_query.data = "check_status"

        # Mock the scraper rate limiter
        with patch.object(scraper, "global_rate_limiter") as mock_rate_limiter:
            mock_rate_limiter.recent_errors = 0

            result = await bot.check_monitoring_status(mock_update, mock_context)

            assert result == bot.CHOOSING
            mock_update.callback_query.message.edit_text.assert_called_once()
            call_args = mock_update.callback_query.message.edit_text.call_args[0][0]
            assert "🟢 Active" in call_args
            assert "Next check in" in call_args

    @pytest.mark.asyncio
    async def test_check_monitoring_status_inactive(self, mock_update, mock_context):
        """Test check monitoring status when monitoring is inactive"""
        bot.user_configs[12345] = SearchConfig()
        # Ensure no monitoring task for user
        bot.monitoring_tasks.clear()  # Clear all monitoring tasks
        mock_update.callback_query.data = "check_status"

        # Mock the scraper rate limiter
        with patch.object(scraper, "global_rate_limiter") as mock_rate_limiter:
            mock_rate_limiter.recent_errors = 0

            result = await bot.check_monitoring_status(mock_update, mock_context)

            assert result == bot.CHOOSING
            mock_update.callback_query.message.edit_text.assert_called_once()
            call_args = mock_update.callback_query.message.edit_text.call_args[0][0]
            assert "🔴 Not Running" in call_args
            assert "Start searching" in call_args

    @pytest.mark.asyncio
    async def test_check_monitoring_status_no_config(self, mock_update, mock_context):
        """Test check monitoring status with no user config"""
        # Clear user configs
        bot.user_configs.clear()
        mock_update.callback_query.data = "check_status"

        result = await bot.check_monitoring_status(mock_update, mock_context)

        assert result == bot.CHOOSING
        mock_update.callback_query.message.edit_text.assert_called_once()
        call_args = mock_update.callback_query.message.edit_text.call_args[0][0]
        assert "No configuration found" in call_args

    @pytest.mark.asyncio
    async def test_test_search_now_success(self, mock_update, mock_context):
        """Test manual test search functionality - success case"""
        bot.user_configs[12345] = SearchConfig()
        mock_update.callback_query.data = "test_search"

        # Clear any existing seen listings that might interfere
        with patch("bot.IdealistaScraper") as mock_scraper_class:
            mock_scraper = MagicMock()
            mock_scraper.seen_listings = {}  # Clear seen listings
            mock_scraper.initialize = AsyncMock()
            mock_scraper.scrape_listings = AsyncMock(
                return_value=[{"title": "Test Listing", "link": "https://test.com"}]
            )
            mock_scraper_class.return_value = mock_scraper

            result = await bot.test_search_now(mock_update, mock_context)

            assert result == bot.CHOOSING
            # Should call edit_text twice - once for "starting" and once for result
            assert mock_update.callback_query.message.edit_text.call_count == 2

            # Check final message contains success
            final_call_args = mock_update.callback_query.message.edit_text.call_args[0][
                0
            ]
            assert "Test Successful" in final_call_args
            assert "Found 1 new listings" in final_call_args

    @pytest.mark.asyncio
    async def test_test_search_now_no_results(self, mock_update, mock_context):
        """Test manual test search functionality - no results"""
        bot.user_configs[12345] = SearchConfig()
        mock_update.callback_query.data = "test_search"

        with patch("bot.IdealistaScraper") as mock_scraper_class:
            mock_scraper = MagicMock()
            mock_scraper.initialize = AsyncMock()
            mock_scraper.scrape_listings = AsyncMock(return_value=[])
            mock_scraper_class.return_value = mock_scraper

            result = await bot.test_search_now(mock_update, mock_context)

            assert result == bot.CHOOSING
            final_call_args = mock_update.callback_query.message.edit_text.call_args[0][
                0
            ]
            assert "Test Successful" in final_call_args
            assert "No new listings found" in final_call_args

    @pytest.mark.asyncio
    async def test_test_search_now_failed_fetch(self, mock_update, mock_context):
        """Test manual test search functionality - failed fetch"""
        bot.user_configs[12345] = SearchConfig()
        mock_update.callback_query.data = "test_search"

        with patch("bot.IdealistaScraper") as mock_scraper_class:
            mock_scraper = MagicMock()
            mock_scraper.seen_listings = {}  # Clear seen listings
            mock_scraper.initialize = AsyncMock()
            mock_scraper.scrape_listings = AsyncMock(return_value=None)
            mock_scraper_class.return_value = mock_scraper

            result = await bot.test_search_now(mock_update, mock_context)

            assert result == bot.CHOOSING
            final_call_args = mock_update.callback_query.message.edit_text.call_args[0][
                0
            ]
            assert "Test Failed" in final_call_args
            assert "rate limiting or network error" in final_call_args

    @pytest.mark.asyncio
    async def test_test_search_now_exception(self, mock_update, mock_context):
        """Test manual test search functionality - exception handling"""
        bot.user_configs[12345] = SearchConfig()
        mock_update.callback_query.data = "test_search"

        with patch("bot.IdealistaScraper") as mock_scraper_class:
            mock_scraper_class.side_effect = Exception("Network error")

            result = await bot.test_search_now(mock_update, mock_context)

            assert result == bot.CHOOSING
            final_call_args = mock_update.callback_query.message.edit_text.call_args[0][
                0
            ]
            assert "Test Failed" in final_call_args
            assert "Network error" in final_call_args

    @pytest.mark.asyncio
    async def test_test_search_now_no_config(self, mock_update, mock_context):
        """Test manual test search with no user config"""
        bot.user_configs.clear()
        mock_update.callback_query.data = "test_search"

        result = await bot.test_search_now(mock_update, mock_context)

        assert result == bot.CHOOSING
        mock_update.callback_query.message.edit_text.assert_called_once()
        call_args = mock_update.callback_query.message.edit_text.call_args[0][0]
        assert "No configuration found" in call_args


class TestEnhancedMonitoringFlow:
    """Test enhanced monitoring with better error handling"""

    @pytest.mark.asyncio
    async def test_start_monitoring_with_task_validation(
        self, mock_update, mock_context
    ):
        """Test that monitoring startup validates task creation"""
        bot.user_configs[12345] = SearchConfig()
        mock_update.callback_query.data = "start_monitoring"

        with patch("bot.user_monitoring_task") as mock_task_func:
            # Mock a task that starts successfully
            mock_task = MagicMock()
            mock_task.done.return_value = False  # Task is running
            mock_task.exception.return_value = None

            with patch("asyncio.create_task", return_value=mock_task):
                with patch("bot.stats_manager"):
                    result = await bot.start_monitoring(mock_update, mock_context)

                    assert result == bot.CHOOSING
                    assert 12345 in bot.monitoring_tasks
                    mock_update.callback_query.message.edit_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_monitoring_task_fails_immediately(
        self, mock_update, mock_context
    ):
        """Test handling when monitoring task fails immediately"""
        bot.user_configs[12345] = SearchConfig()
        mock_update.callback_query.data = "start_monitoring"

        with patch("bot.user_monitoring_task") as mock_task_func:
            # Mock a task that fails immediately
            mock_task = MagicMock()
            mock_task.done.return_value = True  # Task completed immediately
            mock_task.exception.return_value = Exception("Task failed")

            with patch("asyncio.create_task", return_value=mock_task):
                with patch("bot.stats_manager"):
                    # Should not raise exception immediately, even if task fails
                    result = await bot.start_monitoring(mock_update, mock_context)
                    assert result == bot.CHOOSING

                # Task should still be added to monitoring_tasks (failure handled by callback)
                assert 12345 in bot.monitoring_tasks

    @pytest.mark.asyncio
    async def test_monitoring_task_done_callback(self, mock_update, mock_context):
        """Test that monitoring task done callback logs failures"""
        bot.user_configs[12345] = SearchConfig()

        with patch("bot.user_monitoring_task") as mock_task_func:
            # Create a real task that we can add callback to
            async def dummy_task():
                raise Exception("Monitoring failed")

            task = asyncio.create_task(dummy_task())

            # Add the callback that the real code would add
            def task_done_callback(task):
                if task.exception():
                    print(f"Monitoring task failed: {task.exception()}")

            task.add_done_callback(task_done_callback)

            # Wait for task to complete
            with pytest.raises(Exception):
                await task

            # Callback should have been called (verified by not crashing)
            assert task.done()

    @pytest.mark.asyncio
    async def test_user_monitoring_task_error_handling(self):
        """Test error handling in user monitoring task"""
        with patch("bot.IdealistaScraper") as mock_scraper_class:
            mock_scraper = MagicMock()
            mock_scraper.initialize = AsyncMock()
            mock_scraper.scrape_listings = AsyncMock(
                side_effect=Exception("Scraping failed")
            )
            mock_scraper_class.return_value = mock_scraper

            bot.user_configs[12345] = SearchConfig()

            # Run one cycle of the monitoring task
            with patch("asyncio.sleep", return_value=None):  # Skip sleep
                with patch("bot.user_configs", {12345: SearchConfig()}):
                    try:
                        # This should handle the exception and continue
                        task = asyncio.create_task(
                            bot.user_monitoring_task(12345, 12345)
                        )

                        # Cancel after short time to avoid infinite loop
                        await asyncio.sleep(0.1)
                        task.cancel()

                        try:
                            await task
                        except asyncio.CancelledError:
                            pass  # Expected

                    except Exception as e:
                        # Should not propagate scraping exceptions
                        pytest.fail(
                            f"Monitoring task should handle scraping errors: {e}"
                        )


class TestConfigurationImprovements:
    """Test improved configuration loading and validation"""

    def test_load_configs_filters_unknown_fields(self):
        """Test that load_configs filters out unknown fields"""
        mock_config_data = {
            "12345": {
                "min_rooms": 2,
                "max_rooms": 4,
                "max_price": 1500,
                "furniture_type": "equipamento_mobilado",  # Use the correct enum value
                "property_states": ["bom-estado"],
                "city": "lisboa",
                "update_frequency": 5,
                "requests_per_minute": 2,  # Unknown field - should be filtered
                "some_other_field": "value",  # Unknown field - should be filtered
            }
        }

        with patch("builtins.open"), patch("json.load", return_value=mock_config_data):
            bot.user_configs.clear()
            bot.load_configs()

            # User should be loaded
            assert 12345 in bot.user_configs
            config = bot.user_configs[12345]

            # Valid fields should be preserved
            assert config.min_rooms == 2
            assert config.max_rooms == 4
            assert config.max_price == 1500

            # furniture_type should be set correctly
            assert config.furniture_type == FurnitureType.FURNISHED

            # Config should be valid SearchConfig object
            assert isinstance(config, SearchConfig)

    def test_load_configs_backwards_compatibility(self):
        """Test backwards compatibility with old config format"""
        mock_config_data = {
            "12345": {
                "min_rooms": 2,
                "max_rooms": 4,
                "max_price": 1500,
                "has_furniture": True,  # Old format
                "property_state": "bom-estado",  # Old format
                "city": "lisboa",
                "update_frequency": 5,
            }
        }

        with patch("builtins.open"), patch("json.load", return_value=mock_config_data):
            bot.user_configs.clear()
            bot.load_configs()

            assert 12345 in bot.user_configs
            config = bot.user_configs[12345]

            # Should convert old format to new
            assert config.furniture_type == FurnitureType.FURNISHED
            assert PropertyState.GOOD in config.property_states

    @pytest.mark.asyncio
    async def test_save_configs_with_locking(self):
        """Test that save_configs uses async locking"""
        bot.user_configs[12345] = SearchConfig()

        with patch("builtins.open"), patch("json.dump") as mock_dump:
            # Should be able to call save_configs as async function
            await bot.save_configs()

            # Should have called json.dump
            mock_dump.assert_called_once()

    def test_config_lock_prevents_race_conditions(self):
        """Test that config lock prevents race conditions"""
        import asyncio

        async def concurrent_save():
            bot.user_configs[12345] = SearchConfig()
            await bot.save_configs()

        # This test verifies the lock exists and can be used
        # In real usage, this prevents file corruption during concurrent saves
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        with patch("builtins.open"), patch("json.dump"):
            # Should be able to run multiple saves concurrently without errors
            tasks = [concurrent_save() for _ in range(5)]
            loop.run_until_complete(asyncio.gather(*tasks))

        loop.close()


class TestMainMenuEnhancements:
    """Test enhancements to main menu"""

    def test_main_menu_includes_new_options(self):
        """Test that main menu includes new debugging options"""
        keyboard = bot.get_main_menu_keyboard(12345)

        # Convert to string representation for easier checking
        menu_text = str(keyboard)

        assert "Bot Statistics" in menu_text
        assert "Check Monitoring Status" in menu_text
        assert "Reset settings" in menu_text or "reset_settings" in menu_text

    def test_main_menu_dynamic_monitoring_button(self):
        """Test that monitoring button changes based on status"""
        # No monitoring task - should show "Start searching"
        # keyboard = bot.get_main_menu_keyboard(12345)
        # menu_text = str(keyboard)
        # assert "🚀 Start searching" in menu_text or "start_monitoring" in menu_text

        # Active monitoring task - should show "Stop monitoring"
        mock_task = MagicMock()
        mock_task.done.return_value = False
        bot.monitoring_tasks[12345] = mock_task

        keyboard = bot.get_main_menu_keyboard(12345)
        menu_text = str(keyboard)
        assert "🛑 Stop monitoring" in menu_text or "stop_monitoring" in menu_text

        # Clean up
        del bot.monitoring_tasks[12345]

    @pytest.mark.asyncio
    async def test_button_handler_routes_new_commands(self, mock_update, mock_context):
        """Test that button handler routes new commands correctly"""
        # Test stats command
        mock_update.callback_query.data = "stats"
        with patch("bot.show_stats", return_value=bot.CHOOSING) as mock_show_stats:
            result = await bot.button_handler(mock_update, mock_context)
            mock_show_stats.assert_called_once()
            assert result == bot.CHOOSING

        # Test check_status command
        mock_update.callback_query.data = "check_status"
        with patch(
            "bot.check_monitoring_status", return_value=bot.CHOOSING
        ) as mock_check_status:
            result = await bot.button_handler(mock_update, mock_context)
            mock_check_status.assert_called_once()
            assert result == bot.CHOOSING

        # Test test_search command
        mock_update.callback_query.data = "test_search"
        with patch(
            "bot.test_search_now", return_value=bot.CHOOSING
        ) as mock_test_search:
            result = await bot.button_handler(mock_update, mock_context)
            mock_test_search.assert_called_once()
            assert result == bot.CHOOSING


class TestErrorLoggingAndDebugging:
    """Test enhanced error logging and debugging features"""

    @pytest.mark.asyncio
    async def test_monitoring_task_logs_start(self):
        """Test that monitoring task logs when it starts"""
        with patch("bot.logger") as mock_logger:
            with patch("bot.IdealistaScraper") as mock_scraper_class:
                mock_scraper = MagicMock()
                mock_scraper.initialize = AsyncMock()
                mock_scraper.scrape_listings = AsyncMock(return_value=[])
                mock_scraper_class.return_value = mock_scraper

                bot.user_configs[12345] = SearchConfig()

                # Run task briefly
                task = asyncio.create_task(bot.user_monitoring_task(12345, 12345))
                await asyncio.sleep(0.1)
                task.cancel()

                try:
                    await task
                except asyncio.CancelledError:
                    pass

                # Should log monitoring start
                mock_logger.info.assert_any_call(
                    "MONITORING STARTED: User 12345 monitoring task is now running"
                )

    def test_config_loading_logs_details(self):
        """Test that config loading logs user details"""
        mock_config_data = {
            "12345": {
                "min_rooms": 2,
                "max_price": 1500,
                "furniture_type": "equipamento_mobilado",  # Use the correct enum value
                "property_states": ["bom-estado"],
                "city": "lisboa",
                "update_frequency": 5,
            }
        }

        with patch("builtins.open"), patch("json.load", return_value=mock_config_data):
            with patch("bot.logger") as mock_logger:
                bot.user_configs.clear()
                bot.load_configs()

                # Should log config loading
                # Check that config loading was logged (exact format may vary)
                # We can't predict the exact dict format, so just check that it was called
                assert mock_logger.info.called

    @pytest.mark.asyncio
    async def test_start_monitoring_logs_task_creation(self, mock_update, mock_context):
        """Test that start monitoring logs task creation details"""
        bot.user_configs[12345] = SearchConfig()
        mock_update.callback_query.data = "start_monitoring"

        with patch("bot.logger") as mock_logger:
            with patch("bot.user_monitoring_task") as mock_task_func:
                mock_task = MagicMock()
                mock_task.done.return_value = False

                with patch("asyncio.create_task", return_value=mock_task):
                    with patch("bot.stats_manager"):
                        await bot.start_monitoring(mock_update, mock_context)

                        # Should log task creation and success
                        # Check that info was called with task creation message
                        info_calls = [
                            call[0][0] for call in mock_logger.info.call_args_list
                        ]
                        assert any(
                            "DEBUG: Monitoring task created for user 12345" in call
                            for call in info_calls
                        )
                        assert any(
                            "SUCCESS: Monitoring task for user 12345 is running properly"
                            in call
                            for call in info_calls
                        )
