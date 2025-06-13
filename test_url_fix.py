#!/usr/bin/env python3

# Test script to verify URL generation fix
import sys
sys.path.append('src')

from models import SearchConfig

# Test the problematic case that was causing errors
config = SearchConfig(min_rooms=2, max_rooms=5, max_price=2500, city="lisboa")
url_params = config.to_url_params()
full_url = config.get_base_url()

print("=== URL Generation Test ===")
print(f"Config: min_rooms={config.min_rooms}, max_rooms={config.max_rooms}")
print(f"URL params: {url_params}")
print(f"Full URL: {full_url}")
print()

# Check if the URL contains the problematic pattern
if "t4,t5" in url_params:
    print("❌ ERROR: Still contains t4,t5 (should be t4-t5)")
elif "t4-t5" in url_params:
    print("✅ SUCCESS: Contains t4-t5 (correct format)")
else:
    print("ℹ️  INFO: Neither t4,t5 nor t4-t5 found in URL")

print()

# Test different room configurations
test_cases = [
    (1, 3),  # Should be: t1,t2,t3
    (2, 4),  # Should be: t2,t3,t4 
    (2, 5),  # Should be: t2,t3,t4-t5
    (1, 6),  # Should be: t1,t2,t3-t5 (max is 5 due to limit)
    (0, 3),  # Should be: t0,t1,t2,t3
]

print("=== Testing Different Room Configurations ===")
for min_rooms, max_rooms in test_cases:
    config = SearchConfig(min_rooms=min_rooms, max_rooms=max_rooms)
    url_params = config.to_url_params()
    
    # Extract just the room part for easier reading
    parts = url_params.split(',')
    room_part = None
    for i, part in enumerate(parts):
        if part.startswith('t'):
            # Find all consecutive room parts
            room_parts = []
            j = i
            while j < len(parts) and (parts[j].startswith('t') or '-t' in parts[j]):
                room_parts.append(parts[j])
                j += 1
            room_part = ','.join(room_parts)
            break
    
    print(f"Rooms {min_rooms}-{max_rooms}: {room_part}")