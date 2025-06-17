import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import aiohttp
from bs4 import BeautifulSoup

from models import SearchConfig
from scraper import IdealistaScraper


class TestPaginationBehavior:
    """Test pagination behavior and early stopping logic"""
    
    @pytest.fixture
    def scraper(self):
        """Create a scraper instance for testing"""
        scraper = IdealistaScraper()
        scraper.seen_listings = {"test_user": set()}
        return scraper
    
    @pytest.fixture
    def config(self):
        """Create a basic search config"""
        return SearchConfig(max_pages=5, city="lisboa")
    
    def create_mock_html_with_listings(self, num_listings: int, page_num: int = 1):
        """Create mock HTML with specified number of listings"""
        html = "<html><body>"
        for i in range(num_listings):
            listing_id = f"listing_{page_num}_{i}"
            html += f'''
            <article class="item">
                <a class="item-link" href="/property/{listing_id}">Test Property {listing_id}</a>
                <div class="description">Test description {listing_id}</div>
                <span class="item-price">1000€</span>
                <span class="item-detail">T2</span>
                <span class="item-detail">50m²</span>
                <span class="item-detail">2º</span>
                <span class="item-detail">Mobilado</span>
                <span class="item-detail">Bom estado</span>
            </article>
            '''
        html += "</body></html>"
        return html
    
    def create_mock_html_empty(self):
        """Create mock HTML with no listings"""
        return "<html><body></body></html>"
    
    @pytest.mark.asyncio
    async def test_pagination_scrapes_all_pages_with_force_all_pages(self, scraper, config):
        """Test that all pages are scraped when force_all_pages=True"""
        
        # Mock fetch_page to return different content for each page
        async def mock_fetch_page(session, url, user_id=None):
            if "pagina=2" in url:
                return self.create_mock_html_with_listings(2, page_num=2)
            elif "pagina=3" in url:
                return self.create_mock_html_with_listings(3, page_num=3) 
            elif "pagina=4" in url:
                return self.create_mock_html_with_listings(1, page_num=4)
            elif "pagina=5" in url:
                return self.create_mock_html_with_listings(2, page_num=5)
            else:  # page 1
                return self.create_mock_html_with_listings(5, page_num=1)
        
        with patch('scraper.fetch_page', side_effect=mock_fetch_page):
            results = await scraper.scrape_listings(config, "test_user", max_pages=5, force_all_pages=True)
        
        # Should scrape all 5 pages and find all listings (5+2+3+1+2 = 13 total)
        assert len(results) == 13
        
        # Verify listings from different pages are included
        page_1_listings = [r for r in results if "listing_1_" in r["link"]]
        page_2_listings = [r for r in results if "listing_2_" in r["link"]]
        page_5_listings = [r for r in results if "listing_5_" in r["link"]]
        
        assert len(page_1_listings) == 5
        assert len(page_2_listings) == 2
        assert len(page_5_listings) == 2
    
    @pytest.mark.asyncio
    async def test_pagination_stops_early_without_force_all_pages(self, scraper, config):
        """Test that pagination stops early when no new listings found and force_all_pages=False"""
        
        # First, add some "seen" listings to simulate previously scraped content
        scraper.seen_listings["test_user"].add("https://www.idealista.pt/property/listing_2_0")
        scraper.seen_listings["test_user"].add("https://www.idealista.pt/property/listing_2_1")
        
        async def mock_fetch_page(session, url, user_id=None):
            if "pagina=2" in url:
                # Page 2 has listings but they're all "seen" (already in seen_listings)
                return self.create_mock_html_with_listings(2, page_num=2)
            elif "pagina=3" in url:
                # This should not be reached due to early stopping
                return self.create_mock_html_with_listings(3, page_num=3)
            else:  # page 1
                return self.create_mock_html_with_listings(5, page_num=1)
        
        with patch('scraper.fetch_page', side_effect=mock_fetch_page):
            results = await scraper.scrape_listings(config, "test_user", max_pages=5, force_all_pages=False)
        
        # Should only get listings from page 1 (5 listings)
        # Page 2 listings are "seen" so count as 0 new listings, triggering early stop
        assert len(results) == 5
        
        # All results should be from page 1
        page_1_listings = [r for r in results if "listing_1_" in r["link"]]
        assert len(page_1_listings) == 5
    
    @pytest.mark.asyncio
    async def test_pagination_continues_past_empty_pages_early_in_sequence(self, scraper, config):
        """Test that pagination continues if early pages (1-2) have no new listings"""
        
        # Mark page 1 and 2 listings as seen
        scraper.seen_listings["test_user"].add("https://www.idealista.pt/property/listing_1_0")
        scraper.seen_listings["test_user"].add("https://www.idealista.pt/property/listing_2_0")
        
        async def mock_fetch_page(session, url, user_id=None):
            if "pagina=2" in url:
                return self.create_mock_html_with_listings(1, page_num=2)  # Seen listing
            elif "pagina=3" in url:
                return self.create_mock_html_with_listings(2, page_num=3)  # New listings
            elif "pagina=4" in url:
                return self.create_mock_html_with_listings(1, page_num=4)  # New listing
            else:  # page 1
                return self.create_mock_html_with_listings(1, page_num=1)  # Seen listing
        
        with patch('scraper.fetch_page', side_effect=mock_fetch_page):
            results = await scraper.scrape_listings(config, "test_user", max_pages=4, force_all_pages=False)
        
        # Should continue to page 3 and 4 despite pages 1-2 having no new listings
        # Should get 2 + 1 = 3 new listings from pages 3-4
        assert len(results) == 3
        
        # Verify we got listings from pages 3 and 4
        page_3_listings = [r for r in results if "listing_3_" in r["link"]]
        page_4_listings = [r for r in results if "listing_4_" in r["link"]]
        assert len(page_3_listings) == 2
        assert len(page_4_listings) == 1
    
    @pytest.mark.asyncio
    async def test_pagination_stops_on_consecutive_empty_pages(self, scraper, config):
        """Test that pagination stops after consecutive empty pages"""
        
        async def mock_fetch_page(session, url, user_id=None):
            if "pagina=2" in url:
                return self.create_mock_html_empty()  # No listings
            elif "pagina=3" in url:
                return self.create_mock_html_empty()  # No listings  
            elif "pagina=4" in url:
                # Should not reach here due to consecutive empty pages
                return self.create_mock_html_with_listings(1, page_num=4)
            else:  # page 1
                return self.create_mock_html_with_listings(3, page_num=1)
        
        with patch('scraper.fetch_page', side_effect=mock_fetch_page):
            results = await scraper.scrape_listings(config, "test_user", max_pages=5, force_all_pages=False)
        
        # Should only get page 1 listings, stop after 2 consecutive empty pages
        assert len(results) == 3
        
        # All should be from page 1
        page_1_listings = [r for r in results if "listing_1_" in r["link"]]
        assert len(page_1_listings) == 3
    
    @pytest.mark.asyncio
    async def test_pagination_url_construction_city_based(self, scraper, config):
        """Test that pagination URLs are constructed correctly for city-based searches"""
        
        expected_urls = []
        
        async def mock_fetch_page(session, url, user_id=None):
            expected_urls.append(url)
            return self.create_mock_html_with_listings(1, page_num=len(expected_urls))
        
        with patch('scraper.fetch_page', side_effect=mock_fetch_page):
            await scraper.scrape_listings(config, "test_user", max_pages=3, force_all_pages=True)
        
        # Verify URL construction
        assert len(expected_urls) == 3
        assert "pagina=" not in expected_urls[0]  # Page 1 should not have pagina parameter
        assert "pagina=2" in expected_urls[1]
        assert "pagina=3" in expected_urls[2]
        
        # Verify base URL structure
        for url in expected_urls:
            assert "idealista.pt/arrendar-casas/lisboa/com-" in url
    
    @pytest.mark.asyncio
    async def test_pagination_url_construction_custom_polygon(self, scraper):
        """Test that pagination URLs are constructed correctly for custom polygon searches"""
        
        config = SearchConfig(max_pages=3)
        config.custom_polygon = "((test_polygon_coords))"
        
        expected_urls = []
        
        async def mock_fetch_page(session, url, user_id=None):
            expected_urls.append(url)
            return self.create_mock_html_with_listings(1, page_num=len(expected_urls))
        
        with patch('scraper.fetch_page', side_effect=mock_fetch_page):
            await scraper.scrape_listings(config, "test_user", max_pages=3, force_all_pages=True)
        
        # Verify URL construction for custom polygon
        assert len(expected_urls) == 3
        
        # Page 1 should have shape parameter but no pagina parameter
        assert "shape=" in expected_urls[0]
        assert "pagina=" not in expected_urls[0]
        
        # Pages 2-3 should have both shape and pagina parameters
        assert "shape=" in expected_urls[1] and "pagina=2" in expected_urls[1]
        assert "shape=" in expected_urls[2] and "pagina=3" in expected_urls[2]
        
        # Verify base URL structure for polygon
        for url in expected_urls:
            assert "idealista.pt/areas/arrendar-casas/com-" in url
    
    @pytest.mark.asyncio
    async def test_pagination_respects_max_pages_limit(self, scraper, config):
        """Test that pagination respects the max_pages limit"""
        
        page_count = 0
        
        async def mock_fetch_page(session, url, user_id=None):
            nonlocal page_count
            page_count += 1
            return self.create_mock_html_with_listings(2, page_num=page_count)
        
        # Set max_pages to 2
        config.max_pages = 2
        
        with patch('scraper.fetch_page', side_effect=mock_fetch_page):
            results = await scraper.scrape_listings(config, "test_user", max_pages=2, force_all_pages=True)
        
        # Should only scrape 2 pages, not more
        assert page_count == 2
        assert len(results) == 4  # 2 listings per page * 2 pages
    
    @pytest.mark.asyncio
    async def test_pagination_handles_fetch_errors_gracefully(self, scraper, config):
        """Test that pagination handles page fetch errors gracefully"""
        
        async def mock_fetch_page(session, url, user_id=None):
            if "pagina=2" in url:
                return None  # Simulate fetch failure
            elif "pagina=3" in url:
                return self.create_mock_html_with_listings(2, page_num=3)
            else:  # page 1
                return self.create_mock_html_with_listings(3, page_num=1)
        
        with patch('scraper.fetch_page', side_effect=mock_fetch_page):
            results = await scraper.scrape_listings(config, "test_user", max_pages=3, force_all_pages=True)
        
        # Should get page 1 results, skip page 2 due to error, and not reach page 3
        assert len(results) == 3  # Only page 1 listings
        
        # All results should be from page 1
        page_1_listings = [r for r in results if "listing_1_" in r["link"]]
        assert len(page_1_listings) == 3
    
    @pytest.mark.asyncio
    async def test_pagination_seen_listings_tracking_across_pages(self, scraper, config):
        """Test that seen listings are properly tracked across multiple pages"""
        
        async def mock_fetch_page(session, url, user_id=None):
            if "pagina=2" in url:
                return self.create_mock_html_with_listings(2, page_num=2)
            else:  # page 1
                return self.create_mock_html_with_listings(3, page_num=1)
        
        with patch('scraper.fetch_page', side_effect=mock_fetch_page):
            # First scrape
            results1 = await scraper.scrape_listings(config, "test_user", max_pages=2, force_all_pages=True)
            
            # Second scrape (should find all listings as "seen")
            results2 = await scraper.scrape_listings(config, "test_user", max_pages=2, force_all_pages=True)
        
        # First scrape should find all listings
        assert len(results1) == 5  # 3 + 2 listings
        
        # Second scrape should find no new listings (all are seen)
        assert len(results2) == 0
        
        # Verify seen listings were tracked
        assert len(scraper.seen_listings["test_user"]) == 5


if __name__ == "__main__":
    # Run tests manually
    import sys
    
    test_instance = TestPaginationBehavior()
    
    # Create fixtures manually
    scraper = IdealistaScraper()
    scraper.seen_listings = {"test_user": set()}
    config = SearchConfig(max_pages=5, city="lisboa")
    
    async def run_test(test_func, *args):
        """Helper to run async tests"""
        try:
            await test_func(*args)
            print(f"✅ {test_func.__name__} passed")
        except Exception as e:
            print(f"❌ {test_func.__name__} failed: {e}")
            import traceback
            traceback.print_exc()
    
    async def run_all_tests():
        """Run all tests"""
        print("🧪 Running Pagination Behavior Tests...\n")
        
        # Reset scraper for each test
        scraper.seen_listings = {"test_user": set()}
        await run_test(test_instance.test_pagination_scrapes_all_pages_with_force_all_pages, scraper, config)
        
        scraper.seen_listings = {"test_user": set()}
        await run_test(test_instance.test_pagination_stops_early_without_force_all_pages, scraper, config)
        
        scraper.seen_listings = {"test_user": set()}
        await run_test(test_instance.test_pagination_continues_past_empty_pages_early_in_sequence, scraper, config)
        
        scraper.seen_listings = {"test_user": set()}
        await run_test(test_instance.test_pagination_stops_on_consecutive_empty_pages, scraper, config)
        
        scraper.seen_listings = {"test_user": set()}
        await run_test(test_instance.test_pagination_url_construction_city_based, scraper, config)
        
        scraper.seen_listings = {"test_user": set()}
        await run_test(test_instance.test_pagination_url_construction_custom_polygon, scraper)
        
        scraper.seen_listings = {"test_user": set()}
        await run_test(test_instance.test_pagination_respects_max_pages_limit, scraper, config)
        
        scraper.seen_listings = {"test_user": set()}
        await run_test(test_instance.test_pagination_handles_fetch_errors_gracefully, scraper, config)
        
        scraper.seen_listings = {"test_user": set()}
        await run_test(test_instance.test_pagination_seen_listings_tracking_across_pages, scraper, config)
        
        print(f"\n🏁 All pagination tests completed!")
    
    # Run the tests
    asyncio.run(run_all_tests())