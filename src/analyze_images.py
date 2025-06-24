#!/usr/bin/env python3
"""
Analyze Idealista HTML structure to understand how images are included
"""

import asyncio
import aiohttp
from bs4 import BeautifulSoup
import random

# List of realistic user agents
USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
]

async def analyze_idealista_images():
    """Analyze how images are structured in Idealista listings"""
    
    # Sample search URL for Lisboa apartments
    test_url = "https://www.idealista.pt/arrendar-casas/lisboa/com-preco-max_2000,tamanho-min_30,t1,t2,t3,arrendamento-longa-duracao/"
    
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9,pt;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Cache-Control": "max-age=0",
    }
    
    async with aiohttp.ClientSession() as session:
        print("Fetching Idealista search page...")
        
        try:
            async with session.get(test_url, headers=headers, timeout=30) as response:
                if response.status != 200:
                    print(f"❌ Failed to fetch page: HTTP {response.status}")
                    return
                
                html = await response.text()
                soup = BeautifulSoup(html, "html.parser")
                
                print("✅ Page fetched successfully!")
                print(f"📄 Page title: {soup.title.string if soup.title else 'No title'}")
                
                # Look for listing elements
                listing_elements = soup.find_all("article", class_="item")
                if not listing_elements:
                    # Try alternative selector
                    listing_elements = soup.find_all("div", class_="listing-item")
                
                if not listing_elements:
                    print("❌ No listing elements found. Let's examine the page structure...")
                    # Print a sample of the HTML to understand structure
                    print("📄 First 2000 characters of HTML:")
                    print(html[:2000])
                    return
                
                print(f"🏠 Found {len(listing_elements)} listings")
                
                # Analyze the first few listings for image structure
                for i, listing in enumerate(listing_elements[:3]):
                    print(f"\n🔍 Analyzing listing #{i+1}:")
                    
                    # Look for images in various ways
                    
                    # Method 1: Look for img tags
                    img_tags = listing.find_all("img")
                    print(f"  📸 Found {len(img_tags)} img tags")
                    for j, img in enumerate(img_tags):
                        src = img.get('src', '')
                        alt = img.get('alt', '')
                        print(f"    {j+1}. src='{src[:100]}...' alt='{alt}'")
                    
                    # Method 2: Look for background images in style attributes
                    elements_with_style = listing.find_all(attrs={"style": True})
                    bg_images = []
                    for elem in elements_with_style:
                        style = elem.get('style', '')
                        if 'background-image' in style:
                            bg_images.append(style)
                    
                    print(f"  🖼️ Found {len(bg_images)} elements with background-image")
                    for j, style in enumerate(bg_images):
                        print(f"    {j+1}. {style[:100]}...")
                    
                    # Method 3: Look for data attributes that might contain image URLs
                    data_attrs = []
                    for attr_name in listing.attrs:
                        if attr_name.startswith('data-') and any(keyword in attr_name.lower() for keyword in ['img', 'image', 'photo', 'pic']):
                            data_attrs.append((attr_name, listing.attrs[attr_name]))
                    
                    if data_attrs:
                        print(f"  📋 Found {len(data_attrs)} relevant data attributes:")
                        for attr_name, attr_value in data_attrs:
                            print(f"    {attr_name}='{str(attr_value)[:100]}...'")
                    
                    # Method 4: Look for common image container classes
                    image_containers = listing.find_all(['div', 'span', 'a'], class_=lambda x: x and any(keyword in str(x).lower() for keyword in ['image', 'photo', 'pic', 'thumb']))
                    if image_containers:
                        print(f"  📦 Found {len(image_containers)} potential image containers")
                        for j, container in enumerate(image_containers):
                            print(f"    {j+1}. class='{container.get('class', [])}'")
                    
                    # Get the listing title for context
                    title_elem = listing.find("a", class_="item-link")
                    if title_elem:
                        title = title_elem.get_text(strip=True)
                        print(f"  🏡 Listing title: {title}")
                    
                    print("-" * 50)
                
        except Exception as e:
            print(f"❌ Error analyzing page: {e}")


if __name__ == "__main__":
    asyncio.run(analyze_idealista_images())