import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from scraper import IdealistaScraper, fetch_page
from models import SearchConfig, PropertyState, FurnitureType, SizeRange
import aiohttp

# Fixtures
@pytest.fixture
def mock_config():
    """Create a mock search config"""
    from models import FurnitureType
    return SearchConfig(
        min_rooms=2,
        max_rooms=10,
        min_size=50,
        max_size=80,
        max_price=1000,
        furniture_types=[FurnitureType.FURNISHED],
        property_states=[PropertyState.GOOD],
        city="lisboa",
        update_frequency=10
    )

@pytest.fixture
def mock_html():
    """Create a mock HTML response"""
    return """
    <article class="item">
        <div class="item-info-container">
            <a class="item-link" href="/123">Apartment 1</a>
            <span class="item-price">900€</span>
            <span class="item-detail">3 rooms</span>
            <span class="item-detail">70m²</span>
            <span class="item-detail">Some floor</span>
            <span class="item-detail">Furnished</span>
            <span class="item-detail">Good condition</span>
            <div class="description">Nice apartment in good condition</div>
        </div>
    </article>
    <article class="item">
        <div class="item-info-container">
            <a class="item-link" href="/456">Apartment 2</a>
            <span class="item-price">1200€</span>
            <span class="item-detail">2 rooms</span>
            <span class="item-detail">60m²</span>
            <span class="item-detail">Some floor</span>
            <span class="item-detail">Unfurnished</span>
            <span class="item-detail">Needs remodeling</span>
            <div class="description">Apartment needs work</div>
        </div>
    </article>
    """

# Test cases
@pytest.mark.asyncio
async def test_fetch_page():
    """Test fetching a page with rate limiting"""
    with patch('aiohttp.ClientSession.get') as mock_get:
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value="<html>Test</html>")
        mock_get.return_value.__aenter__.return_value = mock_response
        
        async with aiohttp.ClientSession() as session:
            result = await fetch_page(session, "https://test.com")
            assert result == "<html>Test</html>"
            mock_get.assert_called_once()

@pytest.mark.asyncio
async def test_fetch_page_error():
    """Test error handling in fetch_page"""
    with patch('aiohttp.ClientSession.get') as mock_get:
        mock_response = AsyncMock()
        mock_response.status = 429  # Too Many Requests
        mock_get.return_value.__aenter__.return_value = mock_response
        
        async with aiohttp.ClientSession() as session:
            with pytest.raises(Exception, match="Too many requests"):
                await fetch_page(session, "https://test.com")

@pytest.mark.asyncio
async def test_scraper_initialization():
    """Test scraper initialization"""
    with patch('builtins.open', MagicMock()) as mock_open:
        mock_open.return_value.__enter__.return_value.read.return_value = '{}'
        scraper = IdealistaScraper()
        await scraper.initialize()  # Call initialize instead of load_seen_listings
        assert scraper.seen_listings == {}

@pytest.mark.asyncio
async def test_scraper_load_seen_listings():
    """Test loading seen listings"""
    with patch('builtins.open', MagicMock()) as mock_open:
        mock_open.return_value.__enter__.return_value.read.return_value = '{"123456": ["https://www.idealista.pt/123", "https://www.idealista.pt/456"]}'
        scraper = IdealistaScraper()
        await scraper.initialize()  # Call initialize instead of load_seen_listings
        assert scraper.seen_listings == {"123456": {"https://www.idealista.pt/123", "https://www.idealista.pt/456"}}

@pytest.mark.asyncio
async def test_scraper_save_seen_listings():
    """Test saving seen listings"""
    with patch('builtins.open', MagicMock()) as mock_open:
        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file
        mock_open.return_value.__enter__.return_value.read.return_value = '{}'
        
        scraper = IdealistaScraper()
        await scraper.initialize()  # Initialize first
        scraper.seen_listings = {"123456": {"https://www.idealista.pt/123", "https://www.idealista.pt/456"}}
        await scraper.save_seen_listings()
        
        # Check that open was called twice - once for reading, once for writing
        assert mock_open.call_count == 2
        mock_open.assert_any_call('seen_listings.json', 'r')
        mock_open.assert_any_call('seen_listings.json', 'w')

@pytest.mark.asyncio
async def test_scraper_process_listings(mock_config, mock_html):
    """Test processing listings"""
    print("\n=== Starting test_scraper_process_listings ===")
    with patch('scraper.fetch_page', new_callable=AsyncMock) as mock_fetch, \
         patch('scraper.IdealistaScraper.send_telegram_message', new_callable=AsyncMock) as mock_send:
        mock_fetch.return_value = mock_html
        scraper = IdealistaScraper()
        await scraper.initialize()
        scraper.user_configs = {"123456": mock_config}  # Use string key
        scraper.seen_listings = {"123456": set()}  # Start with empty seen_listings
        print(f"Initial config: {mock_config}")
        print("Starting scrape_listings...")
        await scraper.scrape_listings(mock_config, "123456")
        print(f"Final seen_listings: {scraper.seen_listings}")
        # Only the first listing matches the criteria
        seen_listings = scraper.seen_listings.get("123456", set())
        assert "https://www.idealista.pt/123" in seen_listings
        assert "https://www.idealista.pt/456" not in seen_listings
        print(f"send_telegram_message call count: {mock_send.call_count}")
        assert mock_send.call_count == 1  # Only one message should be sent for the first listing

@pytest.mark.asyncio
async def test_scraper_duplicate_detection(mock_config, mock_html):
    """Test duplicate listing detection"""
    with patch('scraper.fetch_page', new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = mock_html
        scraper = IdealistaScraper()
        await scraper.initialize()
        scraper.user_configs = {123456: mock_config}
        scraper.seen_listings = {"123456": {"https://www.idealista.pt/123"}}  # First listing is already seen
        
        # Mock the send_telegram_message function
        scraper.send_telegram_message = AsyncMock()
        
        await scraper.scrape_listings(mock_config, 123456)
        
        # Should not send message for seen listing
        scraper.send_telegram_message.assert_not_called()

@pytest.mark.asyncio
async def test_scraper_filter_criteria(mock_config, mock_html):
    """Test filtering based on criteria"""
    print("\n=== Starting test_scraper_filter_criteria ===")
    with patch('scraper.fetch_page', new_callable=AsyncMock) as mock_fetch, \
         patch('scraper.IdealistaScraper.send_telegram_message', new_callable=AsyncMock) as mock_send:
        mock_fetch.return_value = mock_html
        scraper = IdealistaScraper()
        await scraper.initialize()
        scraper.user_configs = {"123456": mock_config}  # Use string key
        scraper.seen_listings = {"123456": set()}  # Start with empty seen_listings
        print(f"Initial config: {mock_config}")
        # Update config to filter out the second listing
        mock_config.max_price = 1000  # Second listing is 1200€
        mock_config.furniture_types = [FurnitureType.FURNISHED]  # Second listing is unfurnished
        mock_config.property_states = [PropertyState.GOOD]  # Second listing needs remodeling
        print(f"Updated config: {mock_config}")
        print("Starting scrape_listings...")
        await scraper.scrape_listings(mock_config, "123456")
        print(f"Final seen_listings: {scraper.seen_listings}")
        # Should only process the first listing as it matches all criteria
        seen_listings = scraper.seen_listings.get("123456", set())
        assert "https://www.idealista.pt/123" in seen_listings
        assert "https://www.idealista.pt/456" not in seen_listings
        print(f"send_telegram_message call count: {mock_send.call_count}")
        assert mock_send.call_count == 1  # Only one message should be sent for the first listing 

@pytest.mark.asyncio
async def test_scraper_size_filtering():
    """Test filtering based on minimum size"""
    print("\n=== Starting test_scraper_size_filtering ===")
    
    # Create test HTML with listings of different sizes
    test_html = """
    <article class="item">
        <div class="item-info-container">
            <a class="item-link" href="/123">Apartment 1</a>
            <span class="item-price">900€</span>
            <span class="item-detail">2 rooms</span>
            <span class="item-detail">45m²</span>
            <span class="item-detail">Some floor</span>
            <span class="item-detail">Furnished</span>
            <span class="item-detail">Good condition</span>
            <div class="description">Nice apartment in good condition</div>
        </div>
    </article>
    <article class="item">
        <div class="item-info-container">
            <a class="item-link" href="/456">Apartment 2</a>
            <span class="item-price">1000€</span>
            <span class="item-detail">2 rooms</span>
            <span class="item-detail">55m²</span>
            <span class="item-detail">Some floor</span>
            <span class="item-detail">Furnished</span>
            <span class="item-detail">Good condition</span>
            <div class="description">Another nice apartment</div>
        </div>
    </article>
    <article class="item">
        <div class="item-info-container">
            <a class="item-link" href="/789">Apartment 3</a>
            <span class="item-price">1100€</span>
            <span class="item-detail">2 rooms</span>
            <span class="item-detail">65m²</span>
            <span class="item-detail">Some floor</span>
            <span class="item-detail">Furnished</span>
            <span class="item-detail">Good condition</span>
            <div class="description">Yet another nice apartment</div>
        </div>
    </article>
    """
    
    with patch('scraper.fetch_page', new_callable=AsyncMock) as mock_fetch, \
         patch('scraper.IdealistaScraper.send_telegram_message', new_callable=AsyncMock) as mock_send:
        mock_fetch.return_value = test_html
        scraper = IdealistaScraper()
        await scraper.initialize()
        
        # Test with SIZE_40_PLUS (at least 40m²)
        config = SearchConfig.from_size_range(
            SizeRange.SIZE_40_PLUS,
            min_rooms=2,
            max_rooms=10,
            max_price=2000,
            furniture_types=[FurnitureType.FURNISHED],
            property_states=[PropertyState.GOOD],
            city="lisboa"
        )
        
        scraper.user_configs = {"123456": config}
        scraper.seen_listings = {"123456": set()}
        
        print(f"Testing with minimum size: {config.min_size}m²")
        await scraper.scrape_listings(config, "123456")
        
        # All listings should be included as they are all above 40m²
        seen_listings = scraper.seen_listings.get("123456", set())
        assert "https://www.idealista.pt/123" in seen_listings  # 45m²
        assert "https://www.idealista.pt/456" in seen_listings  # 55m²
        assert "https://www.idealista.pt/789" in seen_listings  # 65m²
        assert mock_send.call_count == 3
        
        # Reset for next test
        scraper.seen_listings = {"123456": set()}
        mock_send.reset_mock()
        
        # Test with SIZE_50_PLUS (at least 50m²)
        config = SearchConfig.from_size_range(
            SizeRange.SIZE_50_PLUS,
            min_rooms=2,
            max_rooms=10,
            max_price=2000,
            furniture_types=[FurnitureType.FURNISHED],
            property_states=[PropertyState.GOOD],
            city="lisboa"
        )
        
        scraper.user_configs = {"123456": config}
        
        print(f"Testing with minimum size: {config.min_size}m²")
        await scraper.scrape_listings(config, "123456")
        
        # Only listings with 50m² or more should be included
        seen_listings = scraper.seen_listings.get("123456", set())
        assert "https://www.idealista.pt/123" not in seen_listings  # 45m²
        assert "https://www.idealista.pt/456" in seen_listings     # 55m²
        assert "https://www.idealista.pt/789" in seen_listings     # 65m²
        assert mock_send.call_count == 2 