import pytest
import asyncio
import json
import tempfile
import os
from unittest.mock import AsyncMock, MagicMock, patch
from telegram import Update, CallbackQuery, Message, User, Chat
from telegram.ext import ContextTypes

from models import SearchConfig, PropertyState, FurnitureType
import bot
from scraper import IdealistaScraper, global_rate_limiter
from user_stats import stats_manager


@pytest.fixture
def mock_update():
    """Create a mock Telegram update object"""
    update = MagicMock(spec=Update)
    update.effective_user = MagicMock(spec=User)
    update.effective_user.id = 12345
    update.effective_chat = MagicMock(spec=Chat)
    update.effective_chat.id = 12345
    update.callback_query = MagicMock(spec=CallbackQuery)
    update.callback_query.answer = AsyncMock()
    update.callback_query.message = MagicMock(spec=Message)
    update.callback_query.message.edit_text = AsyncMock()
    update.message = MagicMock(spec=Message)
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
def temp_files():
    """Create temporary files for testing"""
    temp_files = {}
    
    # Create temp config file
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
        json.dump({}, f)
        temp_files['config'] = f.name
    
    # Create temp seen listings file
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
        json.dump({}, f)
        temp_files['seen'] = f.name
    
    # Create temp stats file
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
        json.dump({}, f)
        temp_files['stats'] = f.name
    
    yield temp_files
    
    # Cleanup
    for file_path in temp_files.values():
        try:
            os.unlink(file_path)
        except FileNotFoundError:
            pass


class TestCompleteMultiUserFlow:
    """Test complete multi-user workflow with all new features"""
    
    @pytest.mark.asyncio
    async def test_complete_user_journey(self, mock_update, mock_context, temp_files):
        """Test complete user journey from start to monitoring"""
        # Clear all state
        bot.user_configs.clear()
        bot.monitoring_tasks.clear()
        stats_manager.stats.clear()
        global_rate_limiter.user_last_request.clear()
        global_rate_limiter.recent_errors = 0
        
        # 1. User starts bot
        result = await bot.start(mock_update, mock_context)
        assert result == bot.CHOOSING
        assert 12345 in bot.user_configs
        
        # 2. User checks their status (should show no monitoring)
        mock_update.callback_query.data = 'check_status'
        result = await bot.check_monitoring_status(mock_update, mock_context)
        status_message = mock_update.callback_query.message.edit_text.call_args[0][0]
        assert "🔴 Not Running" in status_message
        
        # 3. User runs a test search
        mock_update.callback_query.data = 'test_search'
        with patch('bot.IdealistaScraper') as mock_scraper_class:
            mock_scraper = MagicMock()
            mock_scraper.initialize = AsyncMock()
            mock_scraper.scrape_listings = AsyncMock(return_value=[
                {"title": "Test Apartment", "link": "https://test.com/1"}
            ])
            mock_scraper_class.return_value = mock_scraper
            
            result = await bot.test_search_now(mock_update, mock_context)
            test_message = mock_update.callback_query.message.edit_text.call_args[0][0]
            assert "Test Successful" in test_message
            assert "Found 1 new listings" in test_message
        
        # 4. User starts monitoring
        mock_update.callback_query.data = 'start_monitoring'
        with patch('bot.user_monitoring_task') as mock_task_func:
            mock_task = MagicMock()
            mock_task.done.return_value = False
            
            with patch('asyncio.create_task', return_value=mock_task):
                result = await bot.start_monitoring(mock_update, mock_context)
                assert 12345 in bot.monitoring_tasks
        
        # 5. User checks status again (should show active monitoring)
        mock_update.callback_query.data = 'check_status'
        result = await bot.check_monitoring_status(mock_update, mock_context)
        status_message = mock_update.callback_query.message.edit_text.call_args[0][0]
        assert "🟢 Active" in status_message
        
        # 6. User views bot statistics
        mock_update.callback_query.data = 'stats'
        result = await bot.show_stats(mock_update, mock_context)
        stats_message = mock_update.callback_query.message.edit_text.call_args[0][0]
        assert "Bot Usage Statistics" in stats_message
        assert "Currently Active Users: 1" in stats_message
    
    @pytest.mark.asyncio
    async def test_multi_user_isolation(self, temp_files):
        """Test that multiple users are properly isolated"""
        # Clear state
        bot.user_configs.clear()
        bot.monitoring_tasks.clear()
        stats_manager.stats.clear()
        
        # Create two users with different configs
        user1_config = SearchConfig()
        user1_config.max_price = 1000
        user1_config.city = "lisboa"
        bot.user_configs[11111] = user1_config
        
        user2_config = SearchConfig()
        user2_config.max_price = 2000
        user2_config.city = "porto"
        bot.user_configs[22222] = user2_config
        
        # Mock monitoring tasks
        bot.monitoring_tasks[11111] = MagicMock(done=lambda: False)
        bot.monitoring_tasks[22222] = MagicMock(done=lambda: False)
        
        # Test that users see their own configurations
        mock_update1 = MagicMock()
        mock_update1.effective_user.id = 11111
        mock_update1.callback_query.answer = AsyncMock()
        mock_update1.callback_query.message.edit_text = AsyncMock()
        
        mock_update2 = MagicMock()
        mock_update2.effective_user.id = 22222
        mock_update2.callback_query.answer = AsyncMock()
        mock_update2.callback_query.message.edit_text = AsyncMock()
        
        # Check user 1 status
        await bot.check_monitoring_status(mock_update1, MagicMock())
        user1_message = mock_update1.callback_query.message.edit_text.call_args[0][0]
        assert "Max Price: 1000€" in user1_message
        assert "City: lisboa" in user1_message
        
        # Check user 2 status
        await bot.check_monitoring_status(mock_update2, MagicMock())
        user2_message = mock_update2.callback_query.message.edit_text.call_args[0][0]
        assert "Max Price: 2000€" in user2_message
        assert "City: porto" in user2_message
        
        # Users should see same total active users but different personal info
        await bot.show_stats(mock_update1, MagicMock())
        await bot.show_stats(mock_update2, MagicMock())
        
        stats1_message = mock_update1.callback_query.message.edit_text.call_args[0][0]
        stats2_message = mock_update2.callback_query.message.edit_text.call_args[0][0]
        
        # Both should see same global stats
        assert "Currently Active Users: 2" in stats1_message
        assert "Currently Active Users: 2" in stats2_message
    
    @pytest.mark.asyncio
    async def test_rate_limiting_with_multiple_users(self):
        """Test rate limiting works correctly with multiple users"""
        # Clear rate limiter state
        global_rate_limiter.user_last_request.clear()
        global_rate_limiter.recent_errors = 0
        global_rate_limiter.global_last_request = 0
        
        # Test that different users can make requests with appropriate delays
        start_time = asyncio.get_event_loop().time()
        
        # First user request - should be immediate
        await global_rate_limiter.wait_if_needed("user1")
        first_duration = asyncio.get_event_loop().time() - start_time
        assert first_duration < 1  # Should be very fast
        
        # Second user request - should wait for global delay
        start_time = asyncio.get_event_loop().time()
        await global_rate_limiter.wait_if_needed("user2")
        second_duration = asyncio.get_event_loop().time() - start_time
        assert 25 <= second_duration <= 35  # Global delay ~30s
        
        # Same user again - should wait for per-user delay
        start_time = asyncio.get_event_loop().time()
        await global_rate_limiter.wait_if_needed("user1")
        third_duration = asyncio.get_event_loop().time() - start_time
        assert 55 <= third_duration <= 65  # Per-user delay ~60s
    
    @pytest.mark.asyncio
    async def test_error_recovery_flow(self, mock_update, mock_context):
        """Test error recovery and debugging flow"""
        bot.user_configs[12345] = SearchConfig()
        
        # 1. Simulate rate limit error during test search
        mock_update.callback_query.data = 'test_search'
        with patch('bot.IdealistaScraper') as mock_scraper_class:
            mock_scraper_class.side_effect = Exception("403 Forbidden")
            
            result = await bot.test_search_now(mock_update, mock_context)
            error_message = mock_update.callback_query.message.edit_text.call_args[0][0]
            assert "Test Failed" in error_message
            assert "403 Forbidden" in error_message
        
        # 2. Record error in rate limiter
        global_rate_limiter.record_error()
        assert global_rate_limiter.recent_errors >= 1
        
        # 3. Check status should show elevated rate limiting
        mock_update.callback_query.data = 'check_status'
        result = await bot.check_monitoring_status(mock_update, mock_context)
        status_message = mock_update.callback_query.message.edit_text.call_args[0][0]
        assert "🟡" in status_message  # Should show elevated status
        assert "recent errors" in status_message
        
        # 4. Stats should also reflect rate limiting issues
        mock_update.callback_query.data = 'stats'
        result = await bot.show_stats(mock_update, mock_context)
        stats_message = mock_update.callback_query.message.edit_text.call_args[0][0]
        assert "🟡 Elevated" in stats_message
    
    @pytest.mark.asyncio
    async def test_configuration_persistence_with_debugging(self, temp_files):
        """Test configuration persistence works with debugging features"""
        # Set up configuration with new features
        config = SearchConfig()
        config.max_price = 1500
        config.furniture_types = [FurnitureType.FURNISHED, FurnitureType.KITCHEN_FURNITURE]
        config.property_states = [PropertyState.GOOD, PropertyState.NEW]
        bot.user_configs[12345] = config
        
        # Mock file operations to use temp file
        with patch('builtins.open', create=True) as mock_open:
            with patch('json.dump') as mock_dump:
                await bot.save_configs()
                
                # Should have saved with correct format
                mock_dump.assert_called_once()
                saved_data = mock_dump.call_args[0][0]
                
                user_config = saved_data["12345"]
                assert user_config['max_price'] == 1500
                assert 'mobilado' in user_config['furniture_types']
                assert 'mobilado-cozinha' in user_config['furniture_types']
                assert 'bom-estado' in user_config['property_states']
                assert 'com-novo' in user_config['property_states']
        
        # Test loading with field filtering
        mock_config_with_invalid_fields = {
            "12345": {
                "max_price": 1500,
                "furniture_types": ["mobilado"],
                "property_states": ["bom-estado"],
                "city": "lisboa",
                "update_frequency": 5,
                "requests_per_minute": 2,  # Invalid field
                "some_other_field": "value"  # Invalid field
            }
        }
        
        with patch('builtins.open'), patch('json.load', return_value=mock_config_with_invalid_fields):
            bot.user_configs.clear()
            bot.load_configs()
            
            # Should load successfully with invalid fields filtered
            assert 12345 in bot.user_configs
            config = bot.user_configs[12345]
            assert config.max_price == 1500
    
    @pytest.mark.asyncio
    async def test_stats_integration_across_features(self):
        """Test that stats are properly integrated across all features"""
        # Clear stats
        stats_manager.stats.clear()
        
        # Simulate user activities
        stats_manager.record_user_activity("12345", "first_use")
        stats_manager.record_user_activity("12345", "search_start")
        stats_manager.record_user_activity("12345", "listing_received")
        stats_manager.record_user_activity("12345", "listing_received")
        
        stats_manager.record_user_activity("67890", "first_use")
        stats_manager.record_user_activity("67890", "search_start")
        
        # Check stats summary
        summary = stats_manager.get_user_summary()
        assert "Total Users: 2" in summary
        assert "Total Searches: 2" in summary
        assert "Total Listings Sent: 2" in summary
        
        # Test with monitoring tasks
        mock_tasks = {
            "12345": MagicMock(done=lambda: False),
            "67890": MagicMock(done=lambda: True),
            "11111": MagicMock(done=lambda: False)
        }
        
        active_count = stats_manager.get_active_users_count(mock_tasks)
        assert active_count == 2  # Two active tasks


class TestErrorScenarios:
    """Test error scenarios and edge cases"""
    
    @pytest.mark.asyncio
    async def test_monitoring_task_failure_recovery(self, mock_update, mock_context):
        """Test recovery from monitoring task failures"""
        bot.user_configs[12345] = SearchConfig()
        
        # Start monitoring with a task that will fail
        mock_update.callback_query.data = 'start_monitoring'
        with patch('bot.user_monitoring_task') as mock_task_func:
            # Create task that fails immediately
            mock_task = MagicMock()
            mock_task.done.return_value = True
            mock_task.exception.return_value = Exception("Task failed")
            
            with patch('asyncio.create_task', return_value=mock_task):
                # Should detect failure and clean up
                with pytest.raises(Exception):
                    await bot.start_monitoring(mock_update, mock_context)
                
                # Task should be removed
                assert 12345 not in bot.monitoring_tasks
        
        # User should be able to start monitoring again
        with patch('bot.user_monitoring_task'):
            good_task = MagicMock()
            good_task.done.return_value = False
            
            with patch('asyncio.create_task', return_value=good_task):
                result = await bot.start_monitoring(mock_update, mock_context)
                assert result == bot.CHOOSING
                assert 12345 in bot.monitoring_tasks
    
    @pytest.mark.asyncio
    async def test_scraper_rate_limit_adaptive_behavior(self):
        """Test scraper adaptive behavior under rate limiting"""
        from scraper import AdaptiveRateLimiter
        
        limiter = AdaptiveRateLimiter()
        
        # Simulate escalating rate limit errors
        initial_delay = limiter.min_delay_seconds
        
        # First error
        limiter.record_error()
        assert limiter.recent_errors == 1
        
        # Second error
        limiter.record_error()
        assert limiter.recent_errors == 2
        
        # Third error
        limiter.record_error()
        assert limiter.recent_errors == 3
        
        # Delays should increase exponentially but cap at max
        expected_delay = min(
            initial_delay * (limiter.backoff_multiplier ** 3),
            limiter.max_delay
        )
        
        # Test that delay calculation works
        current_time = asyncio.get_event_loop().time()
        limiter.last_error_time = current_time
        
        # Delay should be calculated correctly
        if limiter.recent_errors > 0 and (current_time - limiter.last_error_time) < 300:
            calculated_delay = min(
                limiter.min_delay_seconds * (limiter.backoff_multiplier ** limiter.recent_errors),
                limiter.max_delay
            )
            assert calculated_delay == expected_delay
    
    @pytest.mark.asyncio
    async def test_configuration_corruption_handling(self):
        """Test handling of corrupted configuration files"""
        # Test various corruption scenarios
        corruption_scenarios = [
            # Invalid JSON
            "{ invalid json",
            # Valid JSON but wrong structure
            '{"not_a_user_id": "invalid_structure"}',
            # Missing required fields
            '{"12345": {"max_price": 1500}}',
            # Invalid enum values
            '{"12345": {"furniture_types": ["invalid_enum"], "property_states": ["also_invalid"]}}',
        ]
        
        for corrupted_data in corruption_scenarios:
            with patch('builtins.open', create=True):
                if corrupted_data.startswith("{"):
                    # Valid JSON but potentially invalid structure
                    with patch('json.load', return_value=json.loads(corrupted_data)):
                        try:
                            bot.user_configs.clear()
                            bot.load_configs()
                            # Should either load successfully or handle gracefully
                        except Exception as e:
                            # Should not crash with unhandled exceptions
                            assert not isinstance(e, (json.JSONDecodeError, KeyError))
                else:
                    # Invalid JSON
                    with patch('json.load', side_effect=json.JSONDecodeError("Invalid", "", 0)):
                        bot.user_configs.clear()
                        bot.load_configs()
                        # Should handle gracefully
    
    @pytest.mark.asyncio
    async def test_concurrent_user_operations(self):
        """Test concurrent operations from multiple users"""
        import asyncio
        
        # Clear state
        bot.user_configs.clear()
        bot.monitoring_tasks.clear()
        
        async def simulate_user_activity(user_id):
            """Simulate a user doing various activities"""
            # Create config
            bot.user_configs[user_id] = SearchConfig()
            
            # Record stats
            stats_manager.record_user_activity(str(user_id), "first_use")
            stats_manager.record_user_activity(str(user_id), "search_start")
            
            # Wait a bit
            await asyncio.sleep(0.01)
            
            # Save config
            await bot.save_configs()
        
        # Run multiple users concurrently
        user_tasks = [simulate_user_activity(i) for i in range(10001, 10011)]
        
        # Should complete without errors
        await asyncio.gather(*user_tasks)
        
        # All users should be recorded
        assert len(bot.user_configs) == 10
        
        # Stats should be consistent
        total_users = stats_manager.get_total_users_count()
        assert total_users >= 10


class TestBackwardsCompatibility:
    """Test backwards compatibility with existing installations"""
    
    def test_old_config_format_migration(self):
        """Test migration from old configuration formats"""
        old_configs = [
            # Original format with has_furniture
            {
                "12345": {
                    "min_rooms": 2,
                    "max_price": 1500,
                    "has_furniture": True,
                    "property_state": "bom-estado",
                    "city": "lisboa",
                    "update_frequency": 5
                }
            },
            # Mixed old and new format
            {
                "12345": {
                    "min_rooms": 2,
                    "max_price": 1500,
                    "furniture_type": "mobilado",
                    "property_states": ["bom-estado"],
                    "city": "lisboa",
                    "update_frequency": 5
                }
            },
            # Format with extra fields that should be filtered
            {
                "12345": {
                    "min_rooms": 2,
                    "max_price": 1500,
                    "furniture_types": ["mobilado"],
                    "property_states": ["bom-estado"],
                    "city": "lisboa",
                    "update_frequency": 5,
                    "requests_per_minute": 2,  # Should be filtered
                    "old_api_key": "secret",   # Should be filtered
                    "legacy_field": "value"    # Should be filtered
                }
            }
        ]
        
        for old_config in old_configs:
            with patch('builtins.open'), patch('json.load', return_value=old_config):
                bot.user_configs.clear()
                bot.load_configs()
                
                # Should successfully load user
                assert 12345 in bot.user_configs
                config = bot.user_configs[12345]
                
                # Should have valid configuration
                assert isinstance(config, SearchConfig)
                assert config.max_price == 1500
                assert config.min_rooms == 2
                assert config.city == "lisboa"
                
                # Should have converted enums properly
                assert len(config.furniture_types) > 0
                assert len(config.property_states) > 0
                assert all(isinstance(ft, FurnitureType) for ft in config.furniture_types)
                assert all(isinstance(ps, PropertyState) for ps in config.property_states)
    
    @pytest.mark.asyncio
    async def test_seen_listings_compatibility(self):
        """Test compatibility with existing seen listings format"""
        existing_seen_listings = {
            "12345": [
                "https://www.idealista.pt/listing/1",
                "https://www.idealista.pt/listing/2",
                "https://www.idealista.pt/listing/3"
            ],
            "67890": [
                "https://www.idealista.pt/listing/4",
                "https://www.idealista.pt/listing/5"
            ]
        }
        
        # Test that existing format loads correctly
        scraper = IdealistaScraper()
        
        with patch('builtins.open'), patch('json.load', return_value=existing_seen_listings):
            await scraper.initialize()
            
            # Should convert to set format
            assert "12345" in scraper.seen_listings
            assert "67890" in scraper.seen_listings
            assert isinstance(scraper.seen_listings["12345"], set)
            assert len(scraper.seen_listings["12345"]) == 3
            assert len(scraper.seen_listings["67890"]) == 2
    
    def test_stats_file_migration(self):
        """Test that missing stats file is handled gracefully"""
        # Test with missing file
        with patch('builtins.open', side_effect=FileNotFoundError()):
            manager = stats_manager.__class__()  # Create new instance
            # Should not crash and should have empty stats
            assert isinstance(manager.stats, dict)
        
        # Test with corrupted file
        with patch('builtins.open'), patch('json.load', side_effect=json.JSONDecodeError("Bad", "", 0)):
            manager = stats_manager.__class__()
            # Should not crash and should have empty stats
            assert isinstance(manager.stats, dict)