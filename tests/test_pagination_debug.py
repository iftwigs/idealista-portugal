#!/usr/bin/env python3
"""
Simple debug script to test pagination behavior
"""

import asyncio
import sys
import os

# Add src to path
current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src_path = os.path.join(current_dir, "src")
sys.path.insert(0, src_path)

from models import SearchConfig
from scraper import IdealistaScraper
from unittest.mock import patch, AsyncMock


async def test_pagination_debug():
    """Debug pagination with simple test"""

    print("🔍 Testing Pagination Behavior...")

    # Create test setup
    scraper = IdealistaScraper()
    scraper.seen_listings = {"test_user": set()}
    config = SearchConfig(max_pages=3, city="lisboa")

    # Mock HTML responses
    def create_mock_html(num_listings, page_num):
        html = "<html><body>"
        for i in range(num_listings):
            html += f"""
            <article class="item">
                <a class="item-link" href="/property/listing_{page_num}_{i}">Property {page_num}_{i}</a>
                <div class="description">Description {page_num}_{i}</div>
                <span class="item-price">1000€</span>
                <span class="item-detail">T2</span>
                <span class="item-detail">50m²</span>
                <span class="item-detail">2º</span>
                <span class="item-detail">Mobilado</span>
                <span class="item-detail">Bom estado</span>
            </article>
            """
        html += "</body></html>"
        return html

    # Track which URLs are called
    called_urls = []

    async def mock_fetch_page(session, url, user_id=None):
        called_urls.append(url)
        print(f"📄 Mock fetching: {url}")

        if "pagina=2" in url:
            return create_mock_html(2, 2)
        elif "pagina=3" in url:
            return create_mock_html(1, 3)
        else:  # page 1
            return create_mock_html(3, 1)

    # Test 1: With force_all_pages=True
    print("\n=== TEST 1: force_all_pages=True ===")
    called_urls.clear()

    with patch("scraper.fetch_page", side_effect=mock_fetch_page):
        results = await scraper.scrape_listings(
            config, "test_user", max_pages=3, force_all_pages=True
        )

    print(f"URLs called: {len(called_urls)}")
    for i, url in enumerate(called_urls, 1):
        print(f"  {i}. {url}")
    print(f"Results found: {len(results)}")
    print(f"Expected: 6 listings (3+2+1), Got: {len(results)}")

    # Test 2: With force_all_pages=False (default)
    print("\n=== TEST 2: force_all_pages=False ===")
    called_urls.clear()
    scraper.seen_listings = {"test_user": set()}  # Reset seen listings

    with patch("scraper.fetch_page", side_effect=mock_fetch_page):
        results = await scraper.scrape_listings(
            config, "test_user", max_pages=3, force_all_pages=False
        )

    print(f"URLs called: {len(called_urls)}")
    for i, url in enumerate(called_urls, 1):
        print(f"  {i}. {url}")
    print(f"Results found: {len(results)}")
    print(f"Expected: 6 listings (3+2+1), Got: {len(results)}")

    # Test 3: With some "seen" listings to trigger early stopping
    print("\n=== TEST 3: Early stopping with seen listings ===")
    called_urls.clear()

    # Mark page 2 listings as "seen"
    scraper.seen_listings = {
        "test_user": {
            "https://www.idealista.pt/property/listing_2_0",
            "https://www.idealista.pt/property/listing_2_1",
        }
    }

    with patch("scraper.fetch_page", side_effect=mock_fetch_page):
        results = await scraper.scrape_listings(
            config, "test_user", max_pages=3, force_all_pages=False
        )

    print(f"URLs called: {len(called_urls)}")
    for i, url in enumerate(called_urls, 1):
        print(f"  {i}. {url}")
    print(f"Results found: {len(results)}")
    print(f"Expected: Early stop behavior - should see fewer than 3 pages called")

    # Test 4: URL construction for custom polygon
    print("\n=== TEST 4: Custom polygon URL construction ===")
    called_urls.clear()

    config_polygon = SearchConfig(max_pages=2)
    config_polygon.custom_polygon = "((test_polygon))"

    with patch("scraper.fetch_page", side_effect=mock_fetch_page):
        results = await scraper.scrape_listings(
            config_polygon, "test_user", max_pages=2, force_all_pages=True
        )

    print(f"URLs called: {len(called_urls)}")
    for i, url in enumerate(called_urls, 1):
        print(f"  {i}. {url}")
        if "shape=" in url:
            print(f"     ✅ Contains shape parameter")
        if "pagina=" in url:
            print(f"     ✅ Contains pagina parameter")

    print("\n🎉 Pagination debug tests completed!")


if __name__ == "__main__":
    asyncio.run(test_pagination_debug())
