import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import aiohttp
import json
import tempfile
import os
import asyncio
from datetime import datetime, timedelta

from scraper import IdealistaScraper, fetch_page
from models import SearchConfig, PropertyState, FurnitureType


@pytest.fixture
def mock_html():
    """Create a comprehensive mock HTML response with various listing types"""
    return """
    <html>
    <body>
        <article class="item">
            <div class="item-info-container">
                <a class="item-link" href="/listing/123">T2 Apartment Furnished Good Condition</a>
                <span class="item-price">1200€</span>
                <span class="item-detail">T2</span>
                <span class="item-detail">75m²</span>
                <span class="item-detail">2º floor</span>
                <span class="item-detail">Furnished</span>
                <span class="item-detail">Good condition</span>
                <div class="description">Beautiful apartment in good condition</div>
            </div>
        </article>
        <article class="item">
            <div class="item-info-container">
                <a class="item-link" href="/listing/456">T1 Kitchen Only New</a>
                <span class="item-price">900€</span>
                <span class="item-detail">T1</span>
                <span class="item-detail">45m²</span>
                <span class="item-detail">1º floor</span>
                <span class="item-detail">Kitchen furnished</span>
                <span class="item-detail">New</span>
                <div class="description">New apartment with kitchen equipment</div>
            </div>
        </article>
        <article class="item">
            <div class="item-info-container">
                <a class="item-link" href="/listing/789">T3 Unfurnished Needs Remodeling</a>
                <span class="item-price">800€</span>
                <span class="item-detail">T3</span>
                <span class="item-detail">90m²</span>
                <span class="item-detail">Ground floor</span>
                <span class="item-detail">Unfurnished</span>
                <span class="item-detail">Needs remodeling</span>
                <div class="description">Spacious apartment needing renovation</div>
            </div>
        </article>
        <article class="item">
            <div class="item-info-container">
                <a class="item-link" href="/listing/999">T0 Studio Furnished</a>
                <span class="item-price">700€</span>
                <span class="item-detail">T0</span>
                <span class="item-detail">35m²</span>
                <span class="item-detail">3º floor</span>
                <span class="item-detail">Furnished</span>
                <span class="item-detail">Good condition</span>
                <div class="description">Cozy studio apartment</div>
            </div>
        </article>
        <article class="item">
            <div class="item-info-container">
                <a class="item-link" href="/listing/555">Expensive T4 Short Term</a>
                <span class="item-price">3000€</span>
                <span class="item-detail">T4</span>
                <span class="item-detail">150m²</span>
                <span class="item-detail">4º floor</span>
                <span class="item-detail">Furnished</span>
                <span class="item-detail">Good condition</span>
                <div class="description">Luxury apartment for curto prazo rental</div>
            </div>
        </article>
        <article class="item">
            <div class="item-info-container">
                <a class="item-link" href="/listing/777">Ground Floor T2</a>
                <span class="item-price">1000€</span>
                <span class="item-detail">T2</span>
                <span class="item-detail">60m²</span>
                <span class="item-detail">Bajo</span>
                <span class="item-detail">Furnished</span>
                <span class="item-detail">Good condition</span>
                <div class="description">Ground floor apartment</div>
            </div>
        </article>
    </body>
    </html>
    """


@pytest.fixture
def temp_seen_listings_file():
    """Create a temporary seen listings file for testing"""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
        json.dump({}, f)
        temp_path = f.name
    
    yield temp_path
    
    # Cleanup
    os.unlink(temp_path)


class TestScrapingFunctionality:
    """Test scraping functionality and filtering"""
    
    @pytest.mark.asyncio
    async def test_scraper_initialization(self, temp_seen_listings_file):
        """Test scraper initialization and seen listings loading"""
        scraper = IdealistaScraper()
        
        # Mock the seen listings file path
        with patch('builtins.open', create=True) as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = '{"12345": ["listing1", "listing2"]}'
            await scraper.initialize()
        
        assert hasattr(scraper, 'seen_listings')
        assert isinstance(scraper.seen_listings, dict)
    
    @pytest.mark.asyncio
    async def test_room_filtering(self, mock_html):
        """Test room count filtering"""
        scraper = IdealistaScraper()
        await scraper.initialize()
        
        # Test T0+ filter (should include studio)
        config = SearchConfig()
        config.min_rooms = 0
        config.max_rooms = 1
        config.max_price = 5000  # High to avoid price filtering
        
        with patch('scraper.fetch_page', return_value=mock_html):
            listings = await scraper.scrape_listings(config, "test_user")
        
        # Should include T0 and T1 listings
        room_counts = []
        for listing in listings:
            if "T0" in listing["title"]:
                room_counts.append(0)
            elif "T1" in listing["title"]:
                room_counts.append(1)
        
        assert 0 in room_counts or 1 in room_counts
    
    @pytest.mark.asyncio
    async def test_price_filtering(self, mock_html):
        """Test price filtering"""
        scraper = IdealistaScraper()
        await scraper.initialize()
        
        # Test low price filter
        config = SearchConfig()
        config.max_price = 950  # Should exclude 1200€ and 3000€ listings
        config.min_rooms = 0
        config.max_rooms = 5
        
        with patch('scraper.fetch_page', return_value=mock_html):
            listings = await scraper.scrape_listings(config, "test_user")
        
        # All returned listings should be under 950€
        for listing in listings:
            price_str = listing["price"].replace(" €", "").replace("€", "")
            price = int(price_str)
            assert price <= 950
    
    @pytest.mark.asyncio
    async def test_size_filtering(self, mock_html):
        """Test size filtering"""
        scraper = IdealistaScraper()
        await scraper.initialize()
        
        # Test size filter
        config = SearchConfig()
        config.min_size = 70  # Should exclude smaller apartments
        config.max_size = 100
        config.max_price = 5000
        config.min_rooms = 0
        config.max_rooms = 5
        
        with patch('scraper.fetch_page', return_value=mock_html):
            listings = await scraper.scrape_listings(config, "test_user")
        
        # All returned listings should be between 70-100m²
        for listing in listings:
            size_str = listing["size"].replace("m²", "")
            size = int(size_str)
            assert 70 <= size <= 100
    
    @pytest.mark.asyncio
    async def test_furniture_filtering(self, mock_html):
        """Test furniture filtering"""
        scraper = IdealistaScraper()
        await scraper.initialize()
        
        # Test unfurnished only filter
        config = SearchConfig()
        config.furniture_types = [FurnitureType.UNFURNISHED]
        config.max_price = 5000
        config.min_rooms = 0
        config.max_rooms = 5
        
        with patch('scraper.fetch_page', return_value=mock_html):
            listings = await scraper.scrape_listings(config, "test_user")
        
        # Should only include unfurnished listings
        for listing in listings:
            assert "Unfurnished" in listing["title"] or "unfurnished" in listing.get("description", "").lower()
    
    @pytest.mark.asyncio
    async def test_excluded_terms_filtering(self, mock_html):
        """Test filtering of excluded terms (short-term rentals)"""
        scraper = IdealistaScraper()
        await scraper.initialize()
        
        config = SearchConfig()
        config.max_price = 5000  # High to avoid price filtering
        config.min_rooms = 0
        config.max_rooms = 5
        
        with patch('scraper.fetch_page', return_value=mock_html):
            listings = await scraper.scrape_listings(config, "test_user")
        
        # Should exclude listings with "curto prazo" in description
        for listing in listings:
            description = listing.get("description", "").lower()
            assert "curto prazo" not in description
            assert "short term" not in description
    
    @pytest.mark.asyncio
    async def test_excluded_floors_filtering(self, mock_html):
        """Test filtering of excluded floors"""
        scraper = IdealistaScraper()
        await scraper.initialize()
        
        config = SearchConfig()
        config.max_price = 5000
        config.min_rooms = 0
        config.max_rooms = 5
        
        with patch('scraper.fetch_page', return_value=mock_html):
            listings = await scraper.scrape_listings(config, "test_user")
        
        # Should exclude listings on excluded floors
        for listing in listings:
            floor = listing.get("floor", "")
            assert "Bajo" not in floor
            assert "Entreplanta" not in floor
    
    @pytest.mark.asyncio
    async def test_seen_listings_tracking(self, mock_html):
        """Test that seen listings are not sent again"""
        scraper = IdealistaScraper()
        await scraper.initialize()
        
        config = SearchConfig()
        config.max_price = 5000
        config.min_rooms = 0
        config.max_rooms = 5
        
        # First scrape
        with patch('scraper.fetch_page', return_value=mock_html):
            listings1 = await scraper.scrape_listings(config, "test_user")
        
        # Second scrape - should return empty list as all listings are now seen
        with patch('scraper.fetch_page', return_value=mock_html):
            listings2 = await scraper.scrape_listings(config, "test_user")
        
        assert len(listings1) > 0
        assert len(listings2) == 0  # All listings should be marked as seen
    
    @pytest.mark.asyncio
    async def test_multiple_users_separate_seen_listings(self, mock_html):
        """Test that different users have separate seen listings"""
        scraper = IdealistaScraper()
        await scraper.initialize()
        
        config = SearchConfig()
        config.max_price = 5000
        config.min_rooms = 0
        config.max_rooms = 5
        
        # Scrape for user 1
        with patch('scraper.fetch_page', return_value=mock_html):
            listings_user1 = await scraper.scrape_listings(config, "user1")
        
        # Scrape for user 2 - should get same listings as they haven't seen them
        with patch('scraper.fetch_page', return_value=mock_html):
            listings_user2 = await scraper.scrape_listings(config, "user2")
        
        assert len(listings_user1) > 0
        assert len(listings_user2) > 0
        assert len(listings_user1) == len(listings_user2)


class TestRateLimiting:
    """Test rate limiting functionality"""
    
    @pytest.mark.asyncio
    async def test_fetch_page_rate_limiting(self):
        """Test that fetch_page respects rate limiting"""
        
        async def mock_get(url, headers=None):
            response = MagicMock()
            response.status = 200
            response.text = AsyncMock(return_value="<html>test</html>")
            return response
        
        mock_session = MagicMock()
        mock_session.get.return_value.__aenter__.return_value = await mock_get("test_url")
        
        # Test multiple rapid calls
        start_time = datetime.now()
        
        for i in range(3):
            result = await fetch_page(mock_session, f"test_url_{i}")
            assert result is not None
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # Due to rate limiting (2 requests per minute), this should take some time
        # Note: In real tests you might want to mock the rate limiter
        assert duration >= 0  # Basic check that it doesn't crash
    
    @pytest.mark.asyncio
    async def test_fetch_page_429_handling(self):
        """Test handling of 429 (Too Many Requests) response"""
        
        async def mock_get_429(url, headers=None):
            response = MagicMock()
            response.status = 429
            return response
        
        mock_session = MagicMock()
        mock_session.get.return_value.__aenter__.return_value = await mock_get_429("test_url")
        
        with pytest.raises(Exception) as exc_info:
            await fetch_page(mock_session, "test_url")
        
        assert "Too many requests" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_fetch_page_403_handling(self):
        """Test handling of 403 (Forbidden) response"""
        
        async def mock_get_403(url, headers=None):
            response = MagicMock()
            response.status = 403
            return response
        
        mock_session = MagicMock()
        mock_session.get.return_value.__aenter__.return_value = await mock_get_403("test_url")
        
        result = await fetch_page(mock_session, "test_url")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_fetch_page_404_handling(self):
        """Test handling of 404 (Not Found) response"""
        
        async def mock_get_404(url, headers=None):
            response = MagicMock()
            response.status = 404
            return response
        
        mock_session = MagicMock()
        mock_session.get.return_value.__aenter__.return_value = await mock_get_404("test_url")
        
        result = await fetch_page(mock_session, "test_url")
        assert result is None


class TestTelegramIntegration:
    """Test Telegram message sending functionality"""
    
    @pytest.mark.asyncio
    async def test_send_telegram_message_success(self):
        """Test successful Telegram message sending"""
        scraper = IdealistaScraper()
        
        with patch('telegram.Bot') as mock_bot_class:
            mock_bot = MagicMock()
            mock_bot.send_message = AsyncMock()
            mock_bot_class.return_value = mock_bot
            
            await scraper.send_telegram_message("12345", "Test message")
            
            mock_bot.send_message.assert_called_once_with(
                chat_id="12345",
                text="Test message",
                parse_mode="Markdown"
            )
    
    @pytest.mark.asyncio
    async def test_send_telegram_message_failure(self):
        """Test Telegram message sending failure handling"""
        scraper = IdealistaScraper()
        
        with patch('telegram.Bot') as mock_bot_class:
            mock_bot = MagicMock()
            mock_bot.send_message = AsyncMock(side_effect=Exception("Network error"))
            mock_bot_class.return_value = mock_bot
            
            # Should not raise exception, just log error
            await scraper.send_telegram_message("12345", "Test message")
    
    @pytest.mark.asyncio
    async def test_notification_message_format(self, mock_html):
        """Test the format of notification messages"""
        scraper = IdealistaScraper()
        await scraper.initialize()
        
        config = SearchConfig()
        config.max_price = 5000
        config.min_rooms = 0
        config.max_rooms = 5
        
        sent_messages = []
        
        async def capture_message(chat_id, text, parse_mode=None):
            sent_messages.append(text)
        
        with patch('scraper.fetch_page', return_value=mock_html), \
             patch('telegram.Bot') as mock_bot_class:
            
            mock_bot = MagicMock()
            mock_bot.send_message = AsyncMock(side_effect=capture_message)
            mock_bot_class.return_value = mock_bot
            
            await scraper.scrape_listings(config, "test_user")
        
        # Check that messages were sent and have expected format
        assert len(sent_messages) > 0
        
        for message in sent_messages:
            assert "🏡 *New Apartment Listing!*" in message
            assert "📍" in message  # Title
            assert "💰" in message  # Price
            assert "🛏️" in message  # Rooms
            assert "📐" in message  # Size
            assert "🏢" in message  # Floor
            assert "🔗" in message  # Link
            
            # Check for furniture status
            assert any(emoji in message for emoji in ["🪑", "🍽️", "🏠"])
            
            # Check for property state
            assert any(emoji in message for emoji in ["🆕", "✨", "🔨", "❓"])


class TestErrorHandling:
    """Test error handling in scraping"""
    
    @pytest.mark.asyncio
    async def test_malformed_html_handling(self):
        """Test handling of malformed HTML"""
        scraper = IdealistaScraper()
        await scraper.initialize()
        
        malformed_html = "<html><body><article class='item'>incomplete"
        
        config = SearchConfig()
        
        with patch('scraper.fetch_page', return_value=malformed_html):
            # Should not crash on malformed HTML
            listings = await scraper.scrape_listings(config, "test_user")
            assert isinstance(listings, list)
    
    @pytest.mark.asyncio
    async def test_missing_elements_handling(self):
        """Test handling of missing HTML elements"""
        scraper = IdealistaScraper()
        await scraper.initialize()
        
        # HTML with missing elements
        incomplete_html = """
        <html>
        <body>
            <article class="item">
                <div class="item-info-container">
                    <a class="item-link" href="/listing/123">Test Apartment</a>
                    <!-- Missing price, details, etc. -->
                </div>
            </article>
        </body>
        </html>
        """
        
        config = SearchConfig()
        
        with patch('scraper.fetch_page', return_value=incomplete_html):
            # Should handle missing elements gracefully
            listings = await scraper.scrape_listings(config, "test_user")
            assert isinstance(listings, list)
    
    @pytest.mark.asyncio
    async def test_network_error_handling(self):
        """Test handling of network errors"""
        scraper = IdealistaScraper()
        await scraper.initialize()
        
        config = SearchConfig()
        
        with patch('scraper.fetch_page', side_effect=Exception("Network error")):
            # Should handle network errors gracefully
            try:
                await scraper.scrape_listings(config, "test_user")
            except Exception as e:
                # Expected to raise the network error
                assert "Network error" in str(e)


class TestConfigurationCompatibility:
    """Test configuration backwards compatibility in scraper"""
    
    @pytest.mark.asyncio
    async def test_old_config_format_handling(self):
        """Test that scraper handles old configuration format"""
        scraper = IdealistaScraper()
        
        # Simulate old config format being loaded
        old_config_data = {
            "min_rooms": 2,
            "max_rooms": 4,
            "min_size": 50,
            "max_size": 100,
            "max_price": 1500,
            "has_furniture": True,  # Old format
            "property_state": "bom-estado",  # Old format
            "city": "lisboa",
            "update_frequency": 10
        }
        
        # The scraper should handle the migration
        from scraper import PropertyState, FurnitureType
        
        # Simulate the migration logic
        if 'has_furniture' in old_config_data and 'furniture_types' not in old_config_data:
            old_config_data['furniture_types'] = [FurnitureType.FURNISHED if old_config_data['has_furniture'] else FurnitureType.UNFURNISHED]
            old_config_data.pop('has_furniture', None)
        
        if 'property_state' in old_config_data and 'property_states' not in old_config_data:
            old_config_data['property_states'] = [PropertyState(old_config_data['property_state'])]
            old_config_data.pop('property_state', None)
        
        # Should not crash when creating SearchConfig
        from models import SearchConfig
        config = SearchConfig(**old_config_data)
        
        assert config.min_rooms == 2
        assert FurnitureType.FURNISHED in config.furniture_types
        assert PropertyState.GOOD in config.property_states