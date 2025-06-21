import pytest
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))
from models import SearchConfig


class TestURLGeneration:
    """Test URL generation fixes"""

    def test_room_range_formatting(self):
        """Test that room ranges are formatted correctly"""
        # Test the specific case that was causing 404 errors
        config = SearchConfig(min_rooms=2, max_rooms=5, max_price=2500, city="lisboa")
        url_params = config.to_url_params()
        full_url = config.get_base_url()

        # Should contain t4-t5, not t4,t5
        assert "t4,t5" not in url_params, (
            f"URL should not contain 't4,t5', got: {url_params}"
        )
        assert "t4-t5" in url_params, f"URL should contain 't4-t5', got: {url_params}"

        print(f"✅ Fixed URL: {full_url}")

    def test_room_configurations(self):
        """Test various room configurations"""
        test_cases = [
            # (min_rooms, max_rooms, expected_room_pattern)
            (1, 3, "t1,t2,t3"),  # 3 or fewer rooms - all individual
            (2, 4, "t2,t3,t4"),  # 3 rooms - all individual
            (2, 5, "t2,t3,t4-t5"),  # 4 rooms - last two as range
            (1, 5, "t1,t2,t3,t4-t5"),  # 5 rooms - individual t1,t2,t3 then range t4-t5
            (0, 4, "t0,t1,t2,t3"),  # 4 rooms starting from t0
        ]

        for min_rooms, max_rooms, expected_pattern in test_cases:
            config = SearchConfig(min_rooms=min_rooms, max_rooms=max_rooms)
            url_params = config.to_url_params()

            # Extract room pattern from URL params
            # Find the room types section
            parts = url_params.split(",")
            room_parts = []

            for i, part in enumerate(parts):
                if part.startswith("t"):
                    # Collect all consecutive room-related parts
                    j = i
                    while j < len(parts):
                        current_part = parts[j]
                        if current_part.startswith("t") or "-t" in current_part:
                            room_parts.append(current_part)
                            j += 1
                        else:
                            break
                    break

            actual_pattern = ",".join(room_parts)

            assert expected_pattern in actual_pattern, (
                f"For rooms {min_rooms}-{max_rooms}, expected '{expected_pattern}' in '{actual_pattern}'"
            )

            print(f"✅ Rooms {min_rooms}-{max_rooms}: {actual_pattern}")

    def test_no_comma_between_t4_t5(self):
        """Specifically test that t4,t5 pattern is never generated"""
        # Test various configurations that might generate t4,t5
        configs_to_test = [
            SearchConfig(min_rooms=2, max_rooms=5),
            SearchConfig(min_rooms=1, max_rooms=5),
            SearchConfig(min_rooms=3, max_rooms=5),
            SearchConfig(min_rooms=4, max_rooms=5),
        ]

        for config in configs_to_test:
            url_params = config.to_url_params()

            # The problematic pattern should NEVER appear
            assert "t4,t5" not in url_params, (
                f"Configuration {config.min_rooms}-{config.max_rooms} still generates 't4,t5': {url_params}"
            )

            print(
                f"✅ Config {config.min_rooms}-{config.max_rooms}: No t4,t5 pattern found"
            )


if __name__ == "__main__":
    # Run tests manually
    test = TestURLGeneration()

    try:
        test.test_room_range_formatting()
        print("✅ Room range formatting test passed")
    except Exception as e:
        print(f"❌ Room range formatting test failed: {e}")

    try:
        test.test_room_configurations()
        print("✅ Room configurations test passed")
    except Exception as e:
        print(f"❌ Room configurations test failed: {e}")

    try:
        test.test_no_comma_between_t4_t5()
        print("✅ No t4,t5 pattern test passed")
    except Exception as e:
        print(f"❌ No t4,t5 pattern test failed: {e}")
