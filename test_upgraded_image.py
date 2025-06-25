#!/usr/bin/env python3
"""
Test downloading and sending upgraded quality images
"""

import asyncio
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

from scraper import IdealistaScraper

async def test_upgraded_image():
    """Test downloading upgraded quality image"""
    
    # Original URL from our debug
    original_url = "https://img4.idealista.pt/blur/480_360_mq/0/id.pro.pt.image.master/20/2e/e1/289194023.jpg"
    
    # Upgraded URL
    upgraded_url = original_url.replace('/blur/480_360_mq/', '/blur/680_510_mq/')
    
    print(f"📸 Original URL: {original_url}")
    print(f"🔼 Upgraded URL: {upgraded_url}")
    
    scraper = IdealistaScraper()
    
    print("\n" + "="*50)
    print("Testing original quality download:")
    try:
        original_data = await scraper._download_image(original_url)
        if original_data:
            print(f"✅ Original: {len(original_data)} bytes")
            with open("test_original_quality.jpg", "wb") as f:
                f.write(original_data)
            print("💾 Saved as test_original_quality.jpg")
        else:
            print("❌ Failed to download original")
    except Exception as e:
        print(f"❌ Error downloading original: {e}")
    
    print("\n" + "="*50)
    print("Testing upgraded quality download:")
    try:
        upgraded_data = await scraper._download_image(upgraded_url)
        if upgraded_data:
            print(f"✅ Upgraded: {len(upgraded_data)} bytes")
            with open("test_upgraded_quality.jpg", "wb") as f:
                f.write(upgraded_data)
            print("💾 Saved as test_upgraded_quality.jpg")
        else:
            print("❌ Failed to download upgraded")
    except Exception as e:
        print(f"❌ Error downloading upgraded: {e}")

if __name__ == "__main__":
    asyncio.run(test_upgraded_image())