import pytest
import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch
import aiohttp

from scraper import AdaptiveRateLimiter, global_rate_limiter, fetch_page, USER_AGENTS


class TestAdaptiveRateLimiter:
    """Test adaptive rate limiting functionality"""
    
    def test_rate_limiter_initialization(self):
        """Test rate limiter initializes with correct defaults"""
        limiter = AdaptiveRateLimiter()
        
        assert limiter.min_delay_seconds == 60
        assert limiter.global_min_delay == 30
        assert limiter.backoff_multiplier == 2
        assert limiter.max_delay == 300
        assert limiter.recent_errors == 0
        assert len(limiter.user_last_request) == 0
    
    @pytest.mark.asyncio
    async def test_per_user_rate_limiting(self):
        """Test per-user rate limiting works correctly"""
        limiter = AdaptiveRateLimiter()
        
        # First request should go through immediately
        start_time = time.time()
        await limiter.wait_if_needed("user1")
        first_duration = time.time() - start_time
        
        # Should be very fast (< 1 second)
        assert first_duration < 1
        
        # Second request should be delayed
        start_time = time.time()
        await limiter.wait_if_needed("user1")
        second_duration = time.time() - start_time
        
        # Should wait close to min_delay_seconds (allowing some tolerance)
        assert 55 <= second_duration <= 65  # 60s +/- 5s tolerance
    
    @pytest.mark.asyncio
    async def test_different_users_independent_limits(self):
        """Test different users have independent rate limits"""
        limiter = AdaptiveRateLimiter()
        
        # User 1 makes a request
        await limiter.wait_if_needed("user1")
        
        # User 2 should be able to make request immediately
        start_time = time.time()
        await limiter.wait_if_needed("user2")
        duration = time.time() - start_time
        
        # Should be fast, only limited by global delay
        assert 25 <= duration <= 35  # 30s global delay +/- 5s tolerance
    
    @pytest.mark.asyncio
    async def test_global_rate_limiting(self):
        """Test global rate limiting prevents too frequent requests"""
        limiter = AdaptiveRateLimiter()
        
        # Make first request
        await limiter.wait_if_needed("user1")
        
        # Different user should still be limited by global delay
        start_time = time.time()
        await limiter.wait_if_needed("user2")
        duration = time.time() - start_time
        
        assert 25 <= duration <= 35  # 30s global delay +/- 5s tolerance
    
    def test_error_recording(self):
        """Test error recording and backoff calculation"""
        limiter = AdaptiveRateLimiter()
        
        # Initially no errors
        assert limiter.recent_errors == 0
        
        # Record first error
        limiter.record_error()
        assert limiter.recent_errors == 1
        assert limiter.last_error_time > 0
        
        # Record second error
        limiter.record_error()
        assert limiter.recent_errors == 2
    
    @pytest.mark.asyncio
    async def test_adaptive_delay_after_errors(self):
        """Test that delays increase after errors"""
        limiter = AdaptiveRateLimiter()
        
        # Record some errors
        limiter.record_error()
        limiter.record_error()
        
        # Delay should be increased
        start_time = time.time()
        await limiter.wait_if_needed("user1")
        duration = time.time() - start_time
        
        # Should be very fast for first request even with errors
        assert duration < 1
        
        # Second request should have increased delay
        start_time = time.time()
        await limiter.wait_if_needed("user1")  
        duration = time.time() - start_time
        
        # Should be longer than base delay due to backoff
        expected_delay = limiter.min_delay_seconds * (limiter.backoff_multiplier ** 2)
        assert duration >= expected_delay * 0.9  # Allow some tolerance


class TestFetchPageWithRateLimiting:
    """Test fetch_page function with adaptive rate limiting"""
    
    @pytest.mark.asyncio
    async def test_fetch_page_success(self):
        """Test successful page fetch"""
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value="<html>Test content</html>")
        mock_session.get.return_value.__aenter__.return_value = mock_response
        
        result = await fetch_page(mock_session, "https://test.com", "user1")
        
        assert result == "<html>Test content</html>"
        mock_session.get.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_fetch_page_403_error(self):
        """Test handling of 403 error"""
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status = 403
        mock_session.get.return_value.__aenter__.return_value = mock_response
        
        result = await fetch_page(mock_session, "https://test.com", "user1")
        
        assert result is None
        # Should record error in global rate limiter
        assert global_rate_limiter.recent_errors >= 1
    
    @pytest.mark.asyncio
    async def test_fetch_page_429_error(self):
        """Test handling of 429 error"""
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status = 429
        mock_session.get.return_value.__aenter__.return_value = mock_response
        
        result = await fetch_page(mock_session, "https://test.com", "user1")
        
        assert result is None
        # Should record error in global rate limiter
        assert global_rate_limiter.recent_errors >= 1
    
    @pytest.mark.asyncio
    async def test_fetch_page_other_error(self):
        """Test handling of other HTTP errors"""
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status = 500
        mock_session.get.return_value.__aenter__.return_value = mock_response
        
        result = await fetch_page(mock_session, "https://test.com", "user1")
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_fetch_page_network_error(self):
        """Test handling of network errors"""
        mock_session = MagicMock()
        mock_session.get.side_effect = Exception("Network error")
        
        result = await fetch_page(mock_session, "https://test.com", "user1")
        
        assert result is None
    
    def test_user_agent_rotation(self):
        """Test that user agents are rotated"""
        # Should have multiple user agents
        assert len(USER_AGENTS) >= 5
        
        # All should be valid user agent strings
        for ua in USER_AGENTS:
            assert "Mozilla" in ua
            assert "AppleWebKit" in ua or "Gecko" in ua
    
    @pytest.mark.asyncio
    async def test_human_like_delays(self):
        """Test that human-like delays are applied"""
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value="<html>Test</html>")
        mock_session.get.return_value.__aenter__.return_value = mock_response
        
        start_time = time.time()
        await fetch_page(mock_session, "https://test.com", "user1")
        duration = time.time() - start_time
        
        # Should include 1-3 second human delay plus any rate limiting
        assert duration >= 1  # At least 1 second human delay


class TestRateLimitingIntegration:
    """Test integration of rate limiting with scraper"""
    
    @pytest.mark.asyncio
    async def test_rate_limiter_error_recovery(self):
        """Test that rate limiter recovers from errors over time"""
        limiter = AdaptiveRateLimiter()
        
        # Simulate errors
        limiter.record_error()
        limiter.record_error()
        initial_errors = limiter.recent_errors
        
        # Simulate time passing (5+ minutes)
        limiter.last_error_time = time.time() - 400  # 400 seconds ago
        
        # Make a request - should reset errors
        await limiter.wait_if_needed("user1")
        
        # Errors should be cleared
        assert limiter.recent_errors == 0
    
    @pytest.mark.asyncio
    async def test_max_delay_limit(self):
        """Test that delay doesn't exceed maximum"""
        limiter = AdaptiveRateLimiter()
        
        # Record many errors to trigger max delay
        for _ in range(10):
            limiter.record_error()
        
        # Calculate what delay should be
        start_time = time.time()
        await limiter.wait_if_needed("user1")
        first_duration = time.time() - start_time
        
        # Second request to test actual delay
        start_time = time.time()
        await limiter.wait_if_needed("user1")
        duration = time.time() - start_time
        
        # Should not exceed max_delay
        assert duration <= limiter.max_delay + 5  # Allow 5s tolerance


class TestSeenListingsCleanup:
    """Test seen listings cleanup functionality"""
    
    @pytest.mark.asyncio
    async def test_cleanup_seen_listings(self):
        """Test that seen listings are cleaned up properly"""
        from scraper import IdealistaScraper
        
        scraper = IdealistaScraper()
        await scraper.initialize()
        
        user_id = "test_user"
        scraper.seen_listings[user_id] = set()
        
        # Add many listings to trigger cleanup
        for i in range(1200):  # More than max_seen_per_user (1000)
            scraper.seen_listings[user_id].add(f"https://test.com/listing_{i}")
        
        # Cleanup should trigger
        await scraper.cleanup_seen_listings(user_id)
        
        # Should be reduced to 500
        assert len(scraper.seen_listings[user_id]) == 500
    
    @pytest.mark.asyncio
    async def test_cleanup_preserves_recent_listings(self):
        """Test that cleanup keeps most recent listings"""
        from scraper import IdealistaScraper
        
        scraper = IdealistaScraper()
        await scraper.initialize()
        
        user_id = "test_user"
        scraper.seen_listings[user_id] = set()
        
        # Add listings in order
        listings = []
        for i in range(600):
            listing = f"https://test.com/listing_{i:04d}"
            listings.append(listing)
            scraper.seen_listings[user_id].add(listing)
        
        # Cleanup should trigger when we reach max
        await scraper.cleanup_seen_listings(user_id)
        
        # Should keep the last 500 listings
        remaining = scraper.seen_listings[user_id]
        assert len(remaining) == 500
        
        # Most recent listings should be preserved
        for i in range(100, 600):  # Last 500
            assert f"https://test.com/listing_{i:04d}" in remaining


class TestErrorHandlingImproved:
    """Test improved error handling in scraper"""
    
    @pytest.mark.asyncio
    async def test_scraper_handles_failed_fetch(self):
        """Test that scraper handles failed page fetch gracefully"""
        from scraper import IdealistaScraper
        from models import SearchConfig
        
        scraper = IdealistaScraper()
        await scraper.initialize()
        
        config = SearchConfig()
        
        # Mock fetch_page to return None (failed fetch)
        with patch('scraper.fetch_page', return_value=None):
            result = await scraper.scrape_listings(config, "test_user")
        
        # Should return empty list, not crash
        assert result == []
    
    @pytest.mark.asyncio
    async def test_scraper_handles_malformed_response(self):
        """Test that scraper handles malformed HTML response"""
        from scraper import IdealistaScraper
        from models import SearchConfig
        
        scraper = IdealistaScraper()
        await scraper.initialize()
        
        config = SearchConfig()
        
        # Mock fetch_page to return malformed HTML
        with patch('scraper.fetch_page', return_value="<html>incomplete"):
            result = await scraper.scrape_listings(config, "test_user")
        
        # Should return empty list, not crash
        assert isinstance(result, list)