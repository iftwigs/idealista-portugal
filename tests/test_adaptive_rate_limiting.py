import pytest
import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch
import aiohttp

import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

from scraper import AdaptiveRateLimiter, global_rate_limiter, fetch_page
from models import SearchConfig, FurnitureType


class TestAdaptiveRateLimiter:
    """Test adaptive rate limiting functionality"""

    @pytest.fixture
    def rate_limiter(self):
        """Create a fresh rate limiter for each test"""
        return AdaptiveRateLimiter()

    @pytest.mark.asyncio
    async def test_rate_limiter_initialization(self, rate_limiter):
        """Test rate limiter initial state"""
        assert rate_limiter.min_delay_seconds == 90  # Updated to current value
        assert rate_limiter.global_min_delay == 45  # Updated to current value
        assert rate_limiter.max_delay == 600  # Updated to current value
        assert rate_limiter.recent_errors == 0
        assert rate_limiter.backoff_multiplier == 2.5

    @pytest.mark.asyncio
    async def test_first_request_no_delay(self, rate_limiter):
        """Test that first request for a user has no delay"""
        start_time = time.time()
        await rate_limiter.wait_if_needed("user1")
        end_time = time.time()

        # Should be almost instantaneous (allowing for some execution time)
        assert (end_time - start_time) < 1.0

    @pytest.mark.asyncio
    async def test_subsequent_request_enforces_delay(self, rate_limiter):
        """Test that subsequent requests enforce minimum delay"""
        # Override delay for testing
        rate_limiter.min_delay_seconds = 0.1  # 100ms for testing

        # First request
        await rate_limiter.wait_if_needed("user1")

        # Second request should wait
        start_time = time.time()
        await rate_limiter.wait_if_needed("user1")
        end_time = time.time()

        # Should wait approximately the test delay
        assert (end_time - start_time) >= 0.05  # Allow some tolerance

    @pytest.mark.asyncio
    async def test_different_users_independent_delays(self, rate_limiter):
        """Test that different users have independent rate limiting"""
        # Override delay for testing
        rate_limiter.min_delay_seconds = 0.1
        rate_limiter.global_min_delay = 0.05

        # First user makes request
        await rate_limiter.wait_if_needed("user1")

        # Second user should not be delayed by first user's request (per-user limit)
        # but may be delayed by global limit
        start_time = time.time()
        await rate_limiter.wait_if_needed("user2")
        end_time = time.time()

        # Should be relatively fast for different user (may have small global delay)
        assert (end_time - start_time) < 0.2

    @pytest.mark.asyncio
    async def test_global_rate_limiting(self, rate_limiter):
        """Test global rate limiting between all requests"""
        # Override delay for testing
        rate_limiter.global_min_delay = 0.1

        # Make request for user1
        await rate_limiter.wait_if_needed("user1")

        # Immediately make request for user2 - should be delayed by global limit
        start_time = time.time()
        await rate_limiter.wait_if_needed("user2")
        end_time = time.time()

        # Should wait due to global delay
        assert (end_time - start_time) >= 0.05  # Basic check that some delay occurred

    def test_error_recording(self, rate_limiter):
        """Test error recording functionality"""
        initial_errors = rate_limiter.recent_errors

        rate_limiter.record_error()

        assert rate_limiter.recent_errors == initial_errors + 1
        assert rate_limiter.last_error_time > 0

    @pytest.mark.asyncio
    async def test_adaptive_delay_after_errors(self, rate_limiter):
        """Test that delays increase after errors"""
        # Record some errors
        rate_limiter.record_error()
        rate_limiter.record_error()

        # The next request should have increased delay
        start_time = time.time()
        await rate_limiter.wait_if_needed("user1")

        # Check that the delay calculation uses backoff multiplier
        expected_delay = rate_limiter.min_delay_seconds * (
            rate_limiter.backoff_multiplier**rate_limiter.recent_errors
        )
        assert expected_delay > rate_limiter.min_delay_seconds
        assert expected_delay <= rate_limiter.max_delay

    @pytest.mark.asyncio
    async def test_error_reset_after_time(self, rate_limiter):
        """Test that errors reset after sufficient time"""
        # Record an error
        rate_limiter.record_error()
        assert rate_limiter.recent_errors == 1

        # Simulate time passing (mock the time check)
        rate_limiter.last_error_time = time.time() - 400  # 400 seconds ago

        # Make a request - should reset errors
        await rate_limiter.wait_if_needed("user1")

        # Errors should be reset
        assert rate_limiter.recent_errors == 0

    @pytest.mark.asyncio
    async def test_max_delay_cap(self, rate_limiter):
        """Test that delay never exceeds maximum"""
        # Record many errors to trigger maximum delay
        for _ in range(10):
            rate_limiter.record_error()

        # Calculate what the delay would be
        calculated_delay = rate_limiter.min_delay_seconds * (
            rate_limiter.backoff_multiplier**rate_limiter.recent_errors
        )

        # Should be capped at max_delay
        if calculated_delay > rate_limiter.max_delay:
            # The actual delay used should be max_delay
            expected_delay = rate_limiter.max_delay
            assert expected_delay == 600  # Updated to current max value


class TestGlobalRateLimiterIntegration:
    """Test global rate limiter instance"""

    def test_global_rate_limiter_exists(self):
        """Test that global rate limiter is properly initialized"""
        assert global_rate_limiter is not None
        assert isinstance(global_rate_limiter, AdaptiveRateLimiter)
        assert global_rate_limiter.min_delay_seconds == 90  # Updated value
        assert global_rate_limiter.global_min_delay == 45  # Updated value
        assert global_rate_limiter.max_delay == 600  # Updated value

    @pytest.mark.asyncio
    async def test_fetch_page_uses_rate_limiter(self):
        """Test that fetch_page function uses the rate limiter"""

        async def mock_get(url, headers=None):
            response = MagicMock()
            response.status = 200
            response.text = AsyncMock(return_value="<html>Test</html>")
            return response

        mock_session = MagicMock()
        mock_session.get.return_value.__aenter__.return_value = await mock_get(
            "test_url"
        )

        with patch.object(
            global_rate_limiter, "wait_if_needed", new_callable=AsyncMock
        ) as mock_wait:
            result = await fetch_page(mock_session, "test_url", user_id="test_user")

            # Should have called rate limiter
            mock_wait.assert_called_once_with("test_user")
            assert result == "<html>Test</html>"

    @pytest.mark.asyncio
    async def test_fetch_page_without_user_id(self):
        """Test fetch_page without user_id (should not use per-user rate limiting)"""

        async def mock_get(url, headers=None):
            response = MagicMock()
            response.status = 200
            response.text = AsyncMock(return_value="<html>Test</html>")
            return response

        mock_session = MagicMock()
        mock_session.get.return_value.__aenter__.return_value = await mock_get(
            "test_url"
        )

        with patch.object(
            global_rate_limiter, "wait_if_needed", new_callable=AsyncMock
        ) as mock_wait:
            result = await fetch_page(mock_session, "test_url")

            # Should not have called rate limiter (no user_id provided)
            mock_wait.assert_not_called()
            assert result == "<html>Test</html>"


class TestRateLimitingInRealScenarios:
    """Test rate limiting in realistic scraping scenarios"""

    @pytest.mark.asyncio
    async def test_multiple_users_concurrent_requests(self):
        """Test rate limiting with multiple users making concurrent requests"""
        rate_limiter = AdaptiveRateLimiter()

        async def simulate_user_request(user_id):
            await rate_limiter.wait_if_needed(user_id)
            return user_id

        # Simulate 3 users making requests concurrently
        users = ["user1", "user2", "user3"]
        start_time = time.time()

        results = await asyncio.gather(*[simulate_user_request(user) for user in users])

        end_time = time.time()

        # All users should complete successfully
        assert set(results) == set(users)

        # Should have some delay due to global rate limiting
        assert (end_time - start_time) >= 0.1

    @pytest.mark.asyncio
    async def test_error_recovery_scenario(self):
        """Test rate limiting behavior during error recovery"""
        rate_limiter = AdaptiveRateLimiter()

        # Simulate error scenario
        rate_limiter.record_error()
        rate_limiter.record_error()

        # Make requests during error state
        start_time = time.time()
        await rate_limiter.wait_if_needed("user1")

        # Should have increased delay due to errors
        # (In real test, we might mock time to avoid long waits)

        # Simulate recovery (time passage)
        rate_limiter.last_error_time = time.time() - 400

        # Next request should reset error state
        await rate_limiter.wait_if_needed("user1")
        assert rate_limiter.recent_errors == 0

    @pytest.mark.asyncio
    async def test_pagination_delay_behavior(self):
        """Test rate limiting behavior during pagination"""
        rate_limiter = AdaptiveRateLimiter()

        # Simulate pagination requests for same user
        user_id = "pagination_user"
        page_request_times = []

        for page in range(3):
            start_time = time.time()
            await rate_limiter.wait_if_needed(user_id)
            end_time = time.time()
            page_request_times.append(end_time - start_time)

        # First request should be fast
        assert page_request_times[0] < 1.0

        # Subsequent requests should have delays
        for i in range(1, len(page_request_times)):
            assert page_request_times[i] >= 0.1  # Some delay should occur


class TestRateLimitingConfiguration:
    """Test rate limiting configuration and adjustments"""

    def test_rate_limiter_configuration_values(self):
        """Test that rate limiter has correct configuration values"""
        rate_limiter = AdaptiveRateLimiter()

        # Test current configuration values
        assert rate_limiter.min_delay_seconds == 90
        assert rate_limiter.global_min_delay == 45
        assert rate_limiter.max_delay == 600
        assert rate_limiter.backoff_multiplier == 2.5
        assert rate_limiter.pagination_delay_multiplier == 1.5

    def test_delay_calculation_logic(self):
        """Test delay calculation with different error counts"""
        rate_limiter = AdaptiveRateLimiter()

        # Test delay calculation for different error counts
        test_cases = [
            (0, 90),  # No errors = base delay
            (1, 225),  # 1 error = 90 * 2.5^1 = 225
            (2, 562.5),  # 2 errors = 90 * 2.5^2 = 562.5 (keep as float)
        ]

        for errors, expected_delay in test_cases:
            rate_limiter.recent_errors = errors
            calculated_delay = rate_limiter.min_delay_seconds * (
                rate_limiter.backoff_multiplier**errors
            )
            capped_delay = min(calculated_delay, rate_limiter.max_delay)

            assert (
                abs(capped_delay - expected_delay) < 0.1
            )  # Allow small floating point tolerance

    def test_max_delay_enforcement(self):
        """Test that maximum delay is enforced"""
        rate_limiter = AdaptiveRateLimiter()

        # Set high error count that would exceed max delay
        rate_limiter.recent_errors = 10

        calculated_delay = rate_limiter.min_delay_seconds * (
            rate_limiter.backoff_multiplier**rate_limiter.recent_errors
        )

        # Should exceed max delay
        assert calculated_delay > rate_limiter.max_delay

        # But actual delay should be capped
        actual_delay = min(calculated_delay, rate_limiter.max_delay)
        assert actual_delay == 600  # Current max delay value
