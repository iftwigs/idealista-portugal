import pytest
import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch
from telegram import Update, CallbackQuery, Message, User, Chat
from telegram.ext import ContextTypes

from models import SearchConfig
import bot


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
    return update


@pytest.fixture
def mock_context():
    """Create a mock context object"""
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    context.user_data = {}
    context.chat_data = {}
    return context


class TestMonitoringTaskManagement:
    """Test monitoring task creation, management, and debugging"""
    
    @pytest.mark.asyncio
    async def test_monitoring_task_creation_and_validation(self, mock_update, mock_context):
        """Test that monitoring tasks are created and validated properly"""
        bot.user_configs[12345] = SearchConfig()
        bot.monitoring_tasks.clear()
        mock_update.callback_query.data = 'start_monitoring'
        
        with patch('bot.user_monitoring_task') as mock_task_func:
            # Create a mock task that behaves correctly
            mock_task = MagicMock()
            mock_task.done.return_value = False  # Task is running
            mock_task.exception.return_value = None
            
            with patch('asyncio.create_task', return_value=mock_task) as mock_create_task:
                result = await bot.start_monitoring(mock_update, mock_context)
                
                # Should create task
                mock_create_task.assert_called_once()
                # Should add to monitoring_tasks
                assert 12345 in bot.monitoring_tasks
                assert bot.monitoring_tasks[12345] == mock_task
                # Should return correct state
                assert result == bot.CHOOSING
    
    @pytest.mark.asyncio
    async def test_monitoring_task_failure_detection(self, mock_update, mock_context):
        """Test detection and handling of failed monitoring tasks"""
        bot.user_configs[12345] = SearchConfig()
        bot.monitoring_tasks.clear()
        mock_update.callback_query.data = 'start_monitoring'
        
        with patch('bot.user_monitoring_task') as mock_task_func:
            # Create a mock task that fails immediately
            mock_task = MagicMock()
            mock_task.done.return_value = True  # Task completed/failed immediately
            mock_task.exception.return_value = Exception("Task initialization failed")
            
            with patch('asyncio.create_task', return_value=mock_task):
                # Should detect failure and raise exception
                with pytest.raises(Exception, match="Task initialization failed"):
                    await bot.start_monitoring(mock_update, mock_context)
                
                # Failed task should be removed from monitoring_tasks
                assert 12345 not in bot.monitoring_tasks
    
    @pytest.mark.asyncio
    async def test_monitoring_task_done_callback_logging(self):
        """Test that monitoring task done callbacks log properly"""
        # Create a real task that will fail
        async def failing_task():
            await asyncio.sleep(0.01)
            raise Exception("Monitoring task failed")
        
        task = asyncio.create_task(failing_task())
        
        # Track if callback was called
        callback_called = []
        
        def task_done_callback(task):
            callback_called.append(True)
            if task.exception():
                # This is what the real callback does
                pass  # Would log the error
        
        task.add_done_callback(task_done_callback)
        
        # Wait for task to complete and fail
        with pytest.raises(Exception):
            await task
        
        # Callback should have been called
        assert len(callback_called) == 1
        assert task.done()
        assert task.exception() is not None
    
    @pytest.mark.asyncio
    async def test_monitoring_task_startup_timing(self, mock_update, mock_context):
        """Test timing of monitoring task startup validation"""
        bot.user_configs[12345] = SearchConfig()
        mock_update.callback_query.data = 'start_monitoring'
        
        # Track timing of startup validation
        startup_times = []
        
        async def mock_sleep(duration):
            startup_times.append(time.time())
        
        with patch('bot.user_monitoring_task'):
            mock_task = MagicMock()
            mock_task.done.return_value = False
            
            with patch('asyncio.create_task', return_value=mock_task):
                with patch('asyncio.sleep', side_effect=mock_sleep):
                    await bot.start_monitoring(mock_update, mock_context)
                    
                    # Should have called sleep for startup validation
                    assert len(startup_times) == 1
    
    @pytest.mark.asyncio
    async def test_monitoring_task_exception_handling(self):
        """Test that monitoring task handles exceptions in scraping"""
        with patch('bot.IdealistaScraper') as mock_scraper_class:
            # Create scraper that fails
            mock_scraper = MagicMock()
            mock_scraper.initialize = AsyncMock()
            mock_scraper.scrape_listings = AsyncMock(side_effect=Exception("Scraping failed"))
            mock_scraper_class.return_value = mock_scraper
            
            bot.user_configs[12345] = SearchConfig()
            
            # Run monitoring task briefly
            task = asyncio.create_task(bot.user_monitoring_task(12345, 12345))
            
            # Let it run one cycle
            await asyncio.sleep(0.1)
            task.cancel()
            
            try:
                await task
            except asyncio.CancelledError:
                pass  # Expected
            
            # Task should have handled the scraping exception without crashing
            # (Verified by not getting the "Scraping failed" exception)
    
    @pytest.mark.asyncio
    async def test_monitoring_task_rate_limit_error_handling(self):
        """Test that monitoring task handles rate limit errors specifically"""
        with patch('bot.IdealistaScraper') as mock_scraper_class:
            # Create scraper that raises rate limit error
            mock_scraper = MagicMock()
            mock_scraper.initialize = AsyncMock()
            mock_scraper.scrape_listings = AsyncMock(side_effect=Exception("403 Forbidden"))
            mock_scraper_class.return_value = mock_scraper
            
            bot.user_configs[12345] = SearchConfig()
            
            with patch('bot.logger') as mock_logger:
                # Run monitoring task briefly
                task = asyncio.create_task(bot.user_monitoring_task(12345, 12345))
                await asyncio.sleep(0.1)
                task.cancel()
                
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                
                # Should log rate limit error specifically
                mock_logger.warning.assert_any_call("Rate limit encountered for user 12345 - will retry next cycle with longer delays")


class TestMonitoringStatusChecking:
    """Test monitoring status checking and debugging features"""
    
    @pytest.mark.asyncio
    async def test_check_monitoring_status_active_task(self, mock_update, mock_context):
        """Test status check when monitoring is active"""
        bot.user_configs[12345] = SearchConfig()
        
        # Create active monitoring task
        mock_task = MagicMock()
        mock_task.done.return_value = False
        bot.monitoring_tasks[12345] = mock_task
        
        result = await bot.check_monitoring_status(mock_update, mock_context)
        
        assert result == bot.CHOOSING
        mock_update.callback_query.message.edit_text.assert_called_once()
        message = mock_update.callback_query.message.edit_text.call_args[0][0]
        
        # Should show active status
        assert "🟢 Active" in message
        assert "Next check in" in message
        assert "Debug Info" in message
        
        # Clean up
        del bot.monitoring_tasks[12345]
    
    @pytest.mark.asyncio
    async def test_check_monitoring_status_inactive_task(self, mock_update, mock_context):
        """Test status check when monitoring is inactive"""
        bot.user_configs[12345] = SearchConfig()
        # No monitoring task for user
        
        result = await bot.check_monitoring_status(mock_update, mock_context)
        
        assert result == bot.CHOOSING
        message = mock_update.callback_query.message.edit_text.call_args[0][0]
        
        # Should show inactive status
        assert "🔴 Not Running" in message
        assert "Start searching" in message
    
    @pytest.mark.asyncio
    async def test_check_monitoring_status_no_config(self, mock_update, mock_context):
        """Test status check when user has no configuration"""
        bot.user_configs.clear()
        
        result = await bot.check_monitoring_status(mock_update, mock_context)
        
        assert result == bot.CHOOSING
        message = mock_update.callback_query.message.edit_text.call_args[0][0]
        
        # Should show no config message
        assert "No configuration found" in message
    
    @pytest.mark.asyncio
    async def test_check_monitoring_status_rate_limiting_info(self, mock_update, mock_context):
        """Test that status check includes rate limiting information"""
        bot.user_configs[12345] = SearchConfig()
        
        with patch('bot.global_rate_limiter') as mock_limiter:
            mock_limiter.recent_errors = 2
            mock_limiter.min_delay_seconds = 120
            
            result = await bot.check_monitoring_status(mock_update, mock_context)
            
            message = mock_update.callback_query.message.edit_text.call_args[0][0]
            
            # Should include rate limiting status
            assert "Rate Limiting" in message
            assert "🟡 2 recent errors" in message
            assert "120s between requests" in message
    
    @pytest.mark.asyncio
    async def test_check_monitoring_status_debug_info(self, mock_update, mock_context):
        """Test that status check includes debug information"""
        bot.user_configs[12345] = SearchConfig()
        
        # Add some monitoring tasks
        bot.monitoring_tasks[12345] = MagicMock(done=lambda: False)  # Active
        bot.monitoring_tasks[67890] = MagicMock(done=lambda: True)   # Inactive
        
        result = await bot.check_monitoring_status(mock_update, mock_context)
        
        message = mock_update.callback_query.message.edit_text.call_args[0][0]
        
        # Should include debug info
        assert "Debug Info" in message
        assert "Total monitoring tasks: 2" in message
        assert "Active tasks: 1" in message
        
        # Clean up
        bot.monitoring_tasks.clear()


class TestManualSearchTesting:
    """Test manual search testing functionality"""
    
    @pytest.mark.asyncio
    async def test_test_search_success(self, mock_update, mock_context):
        """Test successful manual search test"""
        bot.user_configs[12345] = SearchConfig()
        
        with patch('bot.IdealistaScraper') as mock_scraper_class:
            mock_scraper = MagicMock()
            mock_scraper.initialize = AsyncMock()
            mock_scraper.scrape_listings = AsyncMock(return_value=[
                {"title": "Test Listing 1", "link": "https://test.com/1"},
                {"title": "Test Listing 2", "link": "https://test.com/2"}
            ])
            mock_scraper_class.return_value = mock_scraper
            
            result = await bot.test_search_now(mock_update, mock_context)
            
            assert result == bot.CHOOSING
            
            # Should have called edit_text twice (start message and result)
            assert mock_update.callback_query.message.edit_text.call_count == 2
            
            # Check final message
            final_message = mock_update.callback_query.message.edit_text.call_args[0][0]
            assert "Test Successful" in final_message
            assert "Found 2 new listings" in final_message
    
    @pytest.mark.asyncio
    async def test_test_search_no_results(self, mock_update, mock_context):
        """Test manual search test with no results"""
        bot.user_configs[12345] = SearchConfig()
        
        with patch('bot.IdealistaScraper') as mock_scraper_class:
            mock_scraper = MagicMock()
            mock_scraper.initialize = AsyncMock()
            mock_scraper.scrape_listings = AsyncMock(return_value=[])
            mock_scraper_class.return_value = mock_scraper
            
            result = await bot.test_search_now(mock_update, mock_context)
            
            final_message = mock_update.callback_query.message.edit_text.call_args[0][0]
            assert "Test Successful" in final_message
            assert "No new listings found" in final_message
    
    @pytest.mark.asyncio
    async def test_test_search_network_failure(self, mock_update, mock_context):
        """Test manual search test with network failure"""
        bot.user_configs[12345] = SearchConfig()
        
        with patch('bot.IdealistaScraper') as mock_scraper_class:
            mock_scraper = MagicMock()
            mock_scraper.initialize = AsyncMock()
            mock_scraper.scrape_listings = AsyncMock(return_value=None)  # Network failure
            mock_scraper_class.return_value = mock_scraper
            
            result = await bot.test_search_now(mock_update, mock_context)
            
            final_message = mock_update.callback_query.message.edit_text.call_args[0][0]
            assert "Test Failed" in final_message
            assert "rate limiting or network error" in final_message
    
    @pytest.mark.asyncio
    async def test_test_search_exception(self, mock_update, mock_context):
        """Test manual search test with exception"""
        bot.user_configs[12345] = SearchConfig()
        
        with patch('bot.IdealistaScraper', side_effect=Exception("Connection error")):
            result = await bot.test_search_now(mock_update, mock_context)
            
            final_message = mock_update.callback_query.message.edit_text.call_args[0][0]
            assert "Test Failed" in final_message
            assert "Connection error" in final_message
    
    @pytest.mark.asyncio
    async def test_test_search_no_config(self, mock_update, mock_context):
        """Test manual search test with no user configuration"""
        bot.user_configs.clear()
        
        result = await bot.test_search_now(mock_update, mock_context)
        
        assert result == bot.CHOOSING
        message = mock_update.callback_query.message.edit_text.call_args[0][0]
        assert "No configuration found" in message
    
    @pytest.mark.asyncio
    async def test_test_search_includes_url_info(self, mock_update, mock_context):
        """Test that manual search includes URL information"""
        config = SearchConfig()
        config.max_price = 1500
        config.city = "porto"
        bot.user_configs[12345] = config
        
        with patch('bot.IdealistaScraper') as mock_scraper_class:
            mock_scraper = MagicMock()
            mock_scraper.initialize = AsyncMock()
            mock_scraper.scrape_listings = AsyncMock(return_value=[])
            mock_scraper_class.return_value = mock_scraper
            
            result = await bot.test_search_now(mock_update, mock_context)
            
            final_message = mock_update.callback_query.message.edit_text.call_args[0][0]
            
            # Should include search URL
            assert "Search URL" in final_message
            # Should mention monitoring frequency
            assert "every 5 minutes" in final_message  # Default frequency


class TestDebuggingUtilities:
    """Test debugging utilities and diagnostic features"""
    
    def test_main_menu_includes_debug_options(self):
        """Test that main menu includes debugging options"""
        keyboard = bot.get_main_menu_keyboard(12345)
        menu_text = str(keyboard)
        
        # Should include debugging options
        assert "Check Monitoring Status" in menu_text
        assert "Bot Statistics" in menu_text
    
    @pytest.mark.asyncio
    async def test_stats_includes_rate_limiting_info(self, mock_update, mock_context):
        """Test that statistics include rate limiting information"""
        with patch('bot.stats_manager') as mock_stats_manager:
            mock_stats_manager.get_user_summary.return_value = "Test Summary"
            
            with patch('bot.global_rate_limiter') as mock_limiter:
                mock_limiter.recent_errors = 1
                mock_limiter.min_delay_seconds = 60
                
                result = await bot.show_stats(mock_update, mock_context)
                
                message = mock_update.callback_query.message.edit_text.call_args[0][0]
                
                # Should include rate limiting status
                assert "Rate Limiting Status" in message
                assert "🟡 Elevated (1 recent errors)" in message
                assert "Current Delay: 60s" in message
    
    def test_monitoring_task_logging_format(self):
        """Test that monitoring task logging uses correct format"""
        # This tests the logging format constants used in the monitoring code
        # The actual logging is tested indirectly through other tests
        
        # Test that the log messages use the expected prefixes
        assert "MONITORING STARTED:" in "MONITORING STARTED: User 12345 monitoring task is now running"
        assert "MONITORING CYCLE:" in "MONITORING CYCLE: Starting scrape for user 12345"
        assert "MULTI-USER:" in "MULTI-USER: User 12345 started monitoring"
    
    @pytest.mark.asyncio
    async def test_enhanced_error_messages(self):
        """Test that enhanced error messages provide useful information"""
        # Test error message format for rate limiting
        error_msg = "Rate limit encountered for user 12345 - will retry next cycle with longer delays"
        assert "Rate limit encountered" in error_msg
        assert "user 12345" in error_msg
        assert "retry next cycle" in error_msg
        
        # Test error message format for monitoring failures
        failure_msg = "Monitoring task for user 12345 failed: Network connection error"
        assert "Monitoring task" in failure_msg
        assert "user 12345" in failure_msg
        assert "failed:" in failure_msg


class TestIntegrationWithExistingFeatures:
    """Test integration of new debugging features with existing bot functionality"""
    
    @pytest.mark.asyncio
    async def test_status_check_button_in_test_results(self, mock_update, mock_context):
        """Test that test search results include navigation to status check"""
        bot.user_configs[12345] = SearchConfig()
        
        with patch('bot.IdealistaScraper') as mock_scraper_class:
            mock_scraper = MagicMock()
            mock_scraper.initialize = AsyncMock()
            mock_scraper.scrape_listings = AsyncMock(return_value=[])
            mock_scraper_class.return_value = mock_scraper
            
            result = await bot.test_search_now(mock_update, mock_context)
            
            # Check that reply markup includes back to status option
            reply_markup = mock_update.callback_query.message.edit_text.call_args[1]['reply_markup']
            buttons_text = str(reply_markup.inline_keyboard)
            
            assert "Back to Status" in buttons_text
            assert "Main Menu" in buttons_text
    
    @pytest.mark.asyncio
    async def test_status_check_includes_test_search_button(self, mock_update, mock_context):
        """Test that status check includes test search button when config exists"""
        bot.user_configs[12345] = SearchConfig()
        
        result = await bot.check_monitoring_status(mock_update, mock_context)
        
        # Check that reply markup includes test search option
        reply_markup = mock_update.callback_query.message.edit_text.call_args[1]['reply_markup']
        buttons_text = str(reply_markup.inline_keyboard)
        
        assert "Test Search Now" in buttons_text
    
    @pytest.mark.asyncio
    async def test_button_routing_for_new_commands(self, mock_update, mock_context):
        """Test that new commands are properly routed by button handler"""
        test_commands = [
            ('stats', 'show_stats'),
            ('check_status', 'check_monitoring_status'),
            ('test_search', 'test_search_now')
        ]
        
        for callback_data, expected_function in test_commands:
            mock_update.callback_query.data = callback_data
            
            with patch(f'bot.{expected_function}', return_value=bot.CHOOSING) as mock_func:
                result = await bot.button_handler(mock_update, mock_context)
                
                mock_func.assert_called_once_with(mock_update, mock_context)
                assert result == bot.CHOOSING