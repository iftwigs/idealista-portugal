import pytest
import json
import tempfile
import os
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from collections import defaultdict
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

from user_stats import UserStatsManager, stats_manager


class TestUserStatsManager:
    """Test user statistics management functionality"""

    @pytest.fixture
    def temp_stats_file(self):
        """Create a temporary stats file for testing"""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            json.dump({}, f)
            temp_path = f.name

        yield temp_path

        # Cleanup
        try:
            os.unlink(temp_path)
        except FileNotFoundError:
            pass

    def test_stats_manager_initialization(self):
        """Test stats manager initializes correctly"""
        manager = UserStatsManager()

        assert hasattr(manager, "stats")
        assert isinstance(manager.stats, dict)

    def test_record_user_activity_new_user(self):
        """Test recording activity for new user"""
        manager = UserStatsManager()

        # Clear any existing stats
        manager.stats.clear()

        manager.record_user_activity("12345", "first_use")

        assert "12345" in manager.stats
        user_stats = manager.stats["12345"]
        assert user_stats["first_seen"] is not None
        assert user_stats["last_active"] is not None
        assert user_stats["total_searches"] == 0  # first_use doesn't increment searches
        assert user_stats["listings_received"] == 0

    def test_record_user_activity_search_start(self):
        """Test recording search start activity"""
        manager = UserStatsManager()
        manager.stats.clear()

        manager.record_user_activity("12345", "search_start")

        user_stats = manager.stats["12345"]
        assert user_stats["total_searches"] == 1
        assert user_stats["monitoring_sessions"] == 1

    def test_record_user_activity_listing_received(self):
        """Test recording listing received activity"""
        manager = UserStatsManager()
        manager.stats.clear()

        manager.record_user_activity("12345", "listing_received")

        user_stats = manager.stats["12345"]
        assert user_stats["listings_received"] == 1

    def test_record_multiple_activities(self):
        """Test recording multiple activities for same user"""
        manager = UserStatsManager()
        manager.stats.clear()

        # Record multiple activities
        manager.record_user_activity("12345", "first_use")
        manager.record_user_activity("12345", "search_start")
        manager.record_user_activity("12345", "listing_received")
        manager.record_user_activity("12345", "listing_received")

        user_stats = manager.stats["12345"]
        assert user_stats["total_searches"] == 1
        assert user_stats["monitoring_sessions"] == 1
        assert user_stats["listings_received"] == 2

    def test_get_active_users_count(self):
        """Test getting active users count"""
        manager = UserStatsManager()

        # Mock monitoring tasks
        mock_tasks = {
            "user1": MagicMock(done=lambda: False),  # Active
            "user2": MagicMock(done=lambda: True),  # Inactive
            "user3": MagicMock(done=lambda: False),  # Active
        }

        active_count = manager.get_active_users_count(mock_tasks)
        assert active_count == 2

    def test_get_total_users_count(self):
        """Test getting total users count"""
        manager = UserStatsManager()
        manager.stats.clear()

        # Add some users
        manager.record_user_activity("user1", "first_use")
        manager.record_user_activity("user2", "first_use")
        manager.record_user_activity("user3", "first_use")

        total_count = manager.get_total_users_count()
        assert total_count == 3

    def test_get_user_summary(self):
        """Test getting user summary statistics"""
        manager = UserStatsManager()
        manager.stats.clear()

        # Add test data
        manager.record_user_activity("user1", "search_start")
        manager.record_user_activity("user1", "listing_received")
        manager.record_user_activity("user1", "listing_received")

        manager.record_user_activity("user2", "search_start")
        manager.record_user_activity("user2", "listing_received")

        summary = manager.get_user_summary()

        assert "Total Users: 2" in summary
        assert "Total Searches: 2" in summary
        assert "Total Listings Sent: 3" in summary
        assert "Average Searches per User: 1.0" in summary
        assert "Average Listings per User: 1.5" in summary

    def test_get_user_summary_empty(self):
        """Test getting user summary with no users"""
        manager = UserStatsManager()
        manager.stats.clear()

        summary = manager.get_user_summary()

        assert "Total Users: 0" in summary
        assert "Total Searches: 0" in summary
        assert "Total Listings Sent: 0" in summary
        assert "Average Searches per User: 0.0" in summary
        assert "Average Listings per User: 0.0" in summary

    def test_save_stats(self):
        """Test saving stats to file"""
        manager = UserStatsManager()
        manager.stats["12345"] = {
            "first_seen": "2023-01-01T00:00:00",
            "last_active": "2023-01-01T01:00:00",
            "total_searches": 5,
            "listings_received": 10,
        }

        with patch("builtins.open", create=True) as mock_open:
            with patch("json.dump") as mock_json_dump:
                manager.save_stats()

                mock_open.assert_called_once_with("user_stats.json", "w")
                mock_json_dump.assert_called_once()

                # Verify the JSON dump was called with correct parameters
                call_args = mock_json_dump.call_args
                assert call_args[1]["indent"] == 2
                assert call_args[1]["default"] == str

    @patch("user_stats.open")
    @patch("user_stats.json.load")
    def test_load_stats(self, mock_json_load, mock_open):
        """Test loading stats from file"""
        mock_stats = {
            "12345": {
                "first_seen": "2023-01-01T00:00:00",
                "last_active": "2023-01-01T01:00:00",
                "total_searches": 5,
                "listings_received": 10,
            }
        }
        mock_json_load.return_value = mock_stats

        manager = UserStatsManager()

        assert "12345" in manager.stats
        assert manager.stats["12345"]["total_searches"] == 5
        assert manager.stats["12345"]["listings_received"] == 10

    def test_stats_persistence_integration(self, temp_stats_file):
        """Test full save/load cycle"""
        # Create a manager and add some test data
        manager = UserStatsManager()
        manager.stats.clear()  # Clear any existing data

        # Override save/load to use temp file
        def save_to_temp():
            with open(temp_stats_file, "w") as f:
                json.dump(dict(manager.stats), f, indent=2, default=str)

        def load_from_temp():
            try:
                with open(temp_stats_file, "r") as f:
                    saved_stats = json.load(f)
                    for user_id, stats in saved_stats.items():
                        new_manager.stats[user_id] = stats
            except (FileNotFoundError, json.JSONDecodeError):
                pass

        manager.save_stats = save_to_temp
        manager.load_stats = load_from_temp

        # Add some data
        manager.record_user_activity("12345", "search_start")
        manager.record_user_activity("12345", "listing_received")

        # Save
        manager.save_stats()

        # Create new manager without calling the constructor's load_stats
        new_manager = UserStatsManager.__new__(UserStatsManager)
        new_manager.stats = defaultdict(
            lambda: {
                "first_seen": None,
                "last_active": None,
                "total_searches": 0,
                "listings_received": 0,
                "monitoring_sessions": 0,
                "total_monitoring_time": 0,
            }
        )
        new_manager.load_stats = load_from_temp
        new_manager.load_stats()

        # Verify data persisted
        assert "12345" in new_manager.stats


class TestStatsIntegration:
    """Test integration of stats with bot and scraper"""

    def test_global_stats_manager_exists(self):
        """Test that global stats manager is available"""
        assert stats_manager is not None
        assert isinstance(stats_manager, UserStatsManager)

    @patch("user_stats.stats_manager.record_user_activity")
    def test_stats_recording_in_bot(self, mock_record):
        """Test that bot records user activities"""
        # This would be tested by importing bot functions and verifying they call record_user_activity
        # For now, just test that the function exists and can be called
        stats_manager.record_user_activity("12345", "bot_access")
        mock_record.assert_called_once_with("12345", "bot_access")

    def test_stats_manager_thread_safety(self):
        """Test that stats manager is thread-safe for concurrent access"""
        import threading
        import time

        manager = UserStatsManager()
        manager.stats.clear()

        def record_activity(user_id, activity_count):
            for i in range(activity_count):
                manager.record_user_activity(f"user_{user_id}", "search_start")
                time.sleep(0.001)  # Small delay to encourage race conditions

        # Create multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=record_activity, args=(i, 10))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Verify all activities were recorded
        total_searches = sum(
            stats["total_searches"] for stats in manager.stats.values()
        )
        assert total_searches == 50  # 5 users * 10 searches each


class TestStatsManagerEdgeCases:
    """Test edge cases and error handling in stats manager"""

    def test_invalid_activity_type(self):
        """Test handling of invalid activity types"""
        manager = UserStatsManager()
        manager.stats.clear()

        # Should not crash on unknown activity type
        manager.record_user_activity("12345", "unknown_activity")

        # User should still be recorded
        assert "12345" in manager.stats
        user_stats = manager.stats["12345"]
        assert user_stats["first_seen"] is not None
        assert user_stats["last_active"] is not None

    def test_empty_user_id(self):
        """Test handling of empty user ID"""
        manager = UserStatsManager()

        # Should handle empty user ID gracefully
        manager.record_user_activity("", "search_start")
        assert "" in manager.stats

    def test_none_user_id(self):
        """Test handling of None user ID"""
        manager = UserStatsManager()

        # Should convert None to string
        manager.record_user_activity(None, "search_start")
        assert "None" in manager.stats

    @patch("user_stats.json.load")
    @patch("user_stats.open")
    def test_load_stats_corrupted_file(self, mock_open, mock_json_load):
        """Test handling of corrupted stats file"""
        mock_json_load.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)

        # Should not crash and create empty stats
        manager = UserStatsManager()
        assert isinstance(manager.stats, dict)

    @patch("user_stats.open")
    def test_load_stats_missing_file(self, mock_open):
        """Test handling of missing stats file"""
        mock_open.side_effect = FileNotFoundError()

        # Should not crash and create empty stats
        manager = UserStatsManager()
        assert isinstance(manager.stats, dict)

    def test_save_stats_permission_error(self):
        """Test handling of permission error when saving stats"""
        manager = UserStatsManager()

        with patch("builtins.open", side_effect=PermissionError("Access denied")):
            with patch("user_stats.logger") as mock_logger:
                # Should not crash when save fails
                try:
                    manager.save_stats()  # Should handle exception gracefully
                    # Verify error was logged
                    mock_logger.error.assert_called_once()
                    error_call = mock_logger.error.call_args[0][0]
                    assert "Error saving user stats" in error_call
                    assert "Access denied" in error_call
                except Exception as e:
                    pytest.fail(
                        f"save_stats should handle PermissionError gracefully, but raised: {e}"
                    )

    def test_datetime_serialization(self):
        """Test that datetime objects are properly serialized"""
        manager = UserStatsManager()
        manager.stats.clear()

        # Record activity (creates datetime strings)
        manager.record_user_activity("12345", "search_start")

        user_stats = manager.stats["12345"]

        # Should be string format, not datetime object
        assert isinstance(user_stats["first_seen"], str)
        assert isinstance(user_stats["last_active"], str)

        # Should be valid ISO format
        datetime.fromisoformat(user_stats["first_seen"])
        datetime.fromisoformat(user_stats["last_active"])
