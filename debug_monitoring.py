#!/usr/bin/env python3
"""
Debug script to check monitoring status and user configurations
"""
import json
import sys
import os

sys.path.append('src')

def debug_monitoring():
    """Debug monitoring status"""
    print("🔍 Debugging Bot Monitoring Status\n")
    
    # Check user configs
    try:
        with open('user_configs.json', 'r') as f:
            configs = json.load(f)
        print(f"📊 Found {len(configs)} user configurations:")
        for user_id, config in configs.items():
            print(f"  User {user_id}:")
            print(f"    - Max Price: {config.get('max_price')}€")
            print(f"    - Rooms: {config.get('min_rooms')}-{config.get('max_rooms')}")
            print(f"    - Size: {config.get('min_size')}-{config.get('max_size')}m²")
            print(f"    - City: {config.get('city')}")
            print(f"    - Update Frequency: {config.get('update_frequency')} minutes")
            print(f"    - Furniture: {config.get('furniture_types')}")
            print(f"    - Property States: {config.get('property_states')}")
            print()
    except FileNotFoundError:
        print("❌ user_configs.json not found")
        return
    except json.JSONDecodeError:
        print("❌ Invalid JSON in user_configs.json")
        return
    
    # Check seen listings
    try:
        with open('seen_listings.json', 'r') as f:
            seen = json.load(f)
        print(f"👁️  Seen Listings Status:")
        for user_id, listings in seen.items():
            print(f"  User {user_id}: {len(listings)} seen listings")
        print()
    except FileNotFoundError:
        print("⚠️  seen_listings.json not found - will be created")
    except json.JSONDecodeError:
        print("❌ Invalid JSON in seen_listings.json")
    
    # Test URL generation for all users
    print("🔗 Testing URL Generation:")
    sys.path.append('src')
    try:
        from models import SearchConfig, PropertyState, FurnitureType
        
        for user_id, config_data in configs.items():
            try:
                # Handle backwards compatibility
                if 'property_state' in config_data and 'property_states' not in config_data:
                    config_data['property_states'] = [PropertyState(config_data['property_state'])]
                    config_data.pop('property_state', None)
                elif 'property_states' in config_data:
                    config_data['property_states'] = [PropertyState(state) for state in config_data['property_states']]
                
                if 'has_furniture' in config_data and 'furniture_types' not in config_data:
                    config_data['furniture_types'] = [FurnitureType.FURNISHED if config_data['has_furniture'] else FurnitureType.UNFURNISHED]
                    config_data.pop('has_furniture', None)
                elif 'furniture_type' in config_data and 'furniture_types' not in config_data:
                    config_data['furniture_types'] = [FurnitureType(config_data['furniture_type'])]
                    config_data.pop('furniture_type', None)
                elif 'furniture_types' in config_data:
                    config_data['furniture_types'] = [FurnitureType(ft) for ft in config_data['furniture_types']]
                
                config = SearchConfig(**config_data)
                url = config.get_base_url()
                print(f"  User {user_id}: ✅ {url}")
            except Exception as e:
                print(f"  User {user_id}: ❌ Error generating URL: {e}")
        
    except ImportError as e:
        print(f"❌ Could not import models: {e}")
    
    # Check if bot token is set
    from dotenv import load_dotenv
    load_dotenv()
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if token:
        print(f"🤖 Bot token: ✅ Set (length: {len(token)})")
    else:
        print("🤖 Bot token: ❌ Not set")
    
    print("\n💡 Tips:")
    print("1. Make sure only ONE bot instance is running")
    print("2. Check bot logs for 'Starting monitoring for user X'")
    print("3. Look for 'Generated search URL for user X' in logs")
    print("4. Check for rate limiting warnings in logs")
    print("5. Verify user started monitoring via 'Start searching' button")

if __name__ == "__main__":
    debug_monitoring()