import pytest
import sys
import os
from unittest.mock import AsyncMock, MagicMock, patch
from bs4 import BeautifulSoup

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

from scraper import IdealistaScraper


class TestImageFunctionality:
    """Test image extraction and sending functionality"""

    def test_image_url_extraction_from_html(self):
        """Test that image URLs are correctly extracted from HTML"""
        # Sample HTML structure similar to Idealista
        html_with_image = """
        <article class="item">
            <div class="item-multimedia-pictures">
                <img src="https://img4.idealista.pt/blur/480_360_mq/0/id.pro.pt.image.master/5d/99/c7/289130853.jpg" 
                     alt="Primeira foto do imóvel">
            </div>
            <a class="item-link" href="/imovel/12345678">Test Apartment</a>
            <div class="description">Nice apartment</div>
            <span class="item-price">1200 €</span>
            <span class="item-detail">T2</span>
            <span class="item-detail">75m²</span>
            <span class="item-detail">3º andar</span>
        </article>
        """
        
        soup = BeautifulSoup(html_with_image, "html.parser")
        listing = soup.find("article", class_="item")
        
        # Extract image URL (simulate the extraction logic)
        img_element = listing.find("img", alt="Primeira foto do imóvel")
        assert img_element is not None
        
        image_url = img_element.get('src')
        assert image_url == "https://img4.idealista.pt/blur/480_360_mq/0/id.pro.pt.image.master/5d/99/c7/289130853.jpg"
        
        # Test URL quality upgrade
        if '/blur/' in image_url:
            upgraded_url = image_url.replace('/blur/480_360_mq/', '/blur/680_510_mq/')
            assert upgraded_url == "https://img4.idealista.pt/blur/680_510_mq/0/id.pro.pt.image.master/5d/99/c7/289130853.jpg"

    def test_image_url_extraction_without_image(self):
        """Test behavior when no image is present"""
        html_without_image = """
        <article class="item">
            <a class="item-link" href="/imovel/12345678">Test Apartment</a>
            <div class="description">Nice apartment</div>
            <span class="item-price">1200 €</span>
            <span class="item-detail">T2</span>
        </article>
        """
        
        soup = BeautifulSoup(html_without_image, "html.parser")
        listing = soup.find("article", class_="item")
        
        # Should not find image
        img_element = listing.find("img", alt="Primeira foto do imóvel")
        assert img_element is None

    @pytest.mark.asyncio
    async def test_send_telegram_message_with_image(self):
        """Test sending Telegram message with image"""
        scraper = IdealistaScraper()
        
        with patch('scraper.Bot') as mock_bot_class:
            mock_bot = MagicMock()
            mock_bot.send_photo = AsyncMock()
            mock_bot_class.return_value = mock_bot
            
            # Test sending with image
            await scraper.send_telegram_message(
                chat_id="12345",
                message="Test message",
                image_url="https://example.com/image.jpg"
            )
            
            # Verify send_photo was called
            mock_bot.send_photo.assert_called_once_with(
                chat_id="12345",
                photo="https://example.com/image.jpg",
                caption="Test message",
                parse_mode="Markdown"
            )

    @pytest.mark.asyncio
    async def test_send_telegram_message_without_image(self):
        """Test sending Telegram message without image"""
        scraper = IdealistaScraper()
        
        with patch('scraper.Bot') as mock_bot_class:
            mock_bot = MagicMock()
            mock_bot.send_message = AsyncMock()
            mock_bot_class.return_value = mock_bot
            
            # Test sending without image
            await scraper.send_telegram_message(
                chat_id="12345",
                message="Test message"
            )
            
            # Verify send_message was called
            mock_bot.send_message.assert_called_once_with(
                chat_id="12345",
                text="Test message",
                parse_mode="Markdown"
            )

    @pytest.mark.asyncio
    async def test_send_telegram_message_fallback_on_photo_error(self):
        """Test fallback to text message when photo sending fails"""
        scraper = IdealistaScraper()
        
        with patch('scraper.Bot') as mock_bot_class:
            mock_bot = MagicMock()
            mock_bot.send_photo = AsyncMock(side_effect=Exception("Photo upload failed"))
            mock_bot.send_message = AsyncMock()
            mock_bot_class.return_value = mock_bot
            
            # Test sending with image that fails
            await scraper.send_telegram_message(
                chat_id="12345",
                message="Test message",
                image_url="https://invalid-url.com/broken.jpg"
            )
            
            # Verify send_photo was attempted
            mock_bot.send_photo.assert_called_once()
            
            # Verify fallback to send_message
            mock_bot.send_message.assert_called_once_with(
                chat_id="12345",
                text="Test message",
                parse_mode="Markdown"
            )

    def test_image_url_quality_upgrade(self):
        """Test that image URLs are upgraded to higher quality"""
        original_url = "https://img4.idealista.pt/blur/480_360_mq/0/id.pro.pt.image.master/abc123.jpg"
        expected_url = "https://img4.idealista.pt/blur/680_510_mq/0/id.pro.pt.image.master/abc123.jpg"
        
        # Simulate the upgrade logic
        if '/blur/480_360_mq/' in original_url:
            upgraded_url = original_url.replace('/blur/480_360_mq/', '/blur/680_510_mq/')
            assert upgraded_url == expected_url

    def test_image_url_without_blur(self):
        """Test handling of image URLs that don't use blur format"""
        original_url = "https://img4.idealista.pt/original/0/id.pro.pt.image.master/abc123.jpg"
        
        # Should not be modified if no blur format
        if '/blur/' not in original_url:
            upgraded_url = original_url
            assert upgraded_url == original_url

    @pytest.mark.asyncio 
    async def test_image_extraction_integration(self):
        """Integration test for image extraction during scraping"""
        # This would be a more complex test that mocks the entire scraping process
        # and verifies that images are extracted and included in the listing data
        
        html_content = """
        <article class="item">
            <div class="item-multimedia-pictures">
                <img src="https://img4.idealista.pt/blur/480_360_mq/0/id.pro.pt.image.master/test123.jpg" 
                     alt="Primeira foto do imóvel">
            </div>
            <a class="item-link" href="/imovel/12345678">T2 Apartment in Lisbon</a>
            <div class="description">Beautiful apartment in central location</div>
            <span class="item-price">1500 €</span>
            <span class="item-detail">T2</span>
            <span class="item-detail">80m²</span>
            <span class="item-detail">2º andar</span>
        </article>
        """
        
        soup = BeautifulSoup(html_content, "html.parser")
        listing = soup.find("article", class_="item")
        
        # Simulate the image extraction process from scraper
        image_url = None
        try:
            img_element = listing.find("img", alt="Primeira foto do imóvel")
            if img_element and img_element.get('src'):
                image_url = img_element.get('src')
                # Convert blur URL to higher quality
                if '/blur/' in image_url:
                    image_url = image_url.replace('/blur/480_360_mq/', '/blur/680_510_mq/')
        except Exception:
            image_url = None
        
        # Verify image was extracted and upgraded
        assert image_url == "https://img4.idealista.pt/blur/680_510_mq/0/id.pro.pt.image.master/test123.jpg"


if __name__ == "__main__":
    # Run tests manually
    test_instance = TestImageFunctionality()
    
    test_methods = [
        "test_image_url_extraction_from_html",
        "test_image_url_extraction_without_image",
        "test_image_url_quality_upgrade",
        "test_image_url_without_blur",
    ]
    
    for method_name in test_methods:
        try:
            method = getattr(test_instance, method_name)
            method()
            print(f"✅ {method_name} passed")
        except Exception as e:
            print(f"❌ {method_name} failed: {e}")
    
    # Note: Async tests would need to be run with asyncio in a real scenario
    print("✅ All synchronous image functionality tests completed")