import asyncio
import json
import logging
import os
from typing import Dict, Optional

import aiohttp
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from ratelimit import limits, sleep_and_retry
from telegram import Bot

from models import SearchConfig, PropertyState, FurnitureType

# Load environment variables
load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Configure logging
logging.basicConfig(level=logging.INFO, format="|%(levelname)s| %(asctime)s - %(message)s")
logger = logging.getLogger(__name__)

# Rate limiting decorator
ONE_MINUTE = 60
MAX_REQUESTS_PER_MINUTE = 2

@sleep_and_retry
@limits(calls=MAX_REQUESTS_PER_MINUTE, period=ONE_MINUTE)
async def fetch_page(session: aiohttp.ClientSession, url: str) -> Optional[str]:
    """Fetch a page with rate limiting"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Cache-Control': 'max-age=0',
        'Referer': 'https://www.idealista.pt/'
    }
    
    try:
        async with session.get(url, headers=headers) as response:
            if response.status == 429:
                raise Exception("Too many requests")
            if response.status == 403:
                logger.warning("Access forbidden (403) - Rate limit exceeded")
                return None
            if response.status != 200:
                logger.error(f"Error fetching page: {response.status}")
                return None
            return await response.text()
    except Exception as e:
        logger.error(f"Error fetching page: {e}")
        raise

class IdealistaScraper:
    def __init__(self):
        self.seen_listings: Dict[str, set] = {}  # user_id -> set of seen listing URLs
        
    async def initialize(self):
        """Initialize the scraper by loading seen listings"""
        try:
            with open("seen_listings.json", "r") as f:
                self.seen_listings = {k: set(v) for k, v in json.load(f).items()}
        except (FileNotFoundError, json.JSONDecodeError):
            self.seen_listings = {}
    
    async def save_seen_listings(self):
        """Save seen listings to file"""
        with open("seen_listings.json", "w") as f:
            json.dump({k: list(v) for k, v in self.seen_listings.items()}, f)
    
    async def send_telegram_message(self, chat_id: str, message: str):
        """Send message via Telegram"""
        try:
            bot = Bot(token=TELEGRAM_BOT_TOKEN)
            await bot.send_message(chat_id=chat_id, text=message, parse_mode="Markdown")
            logger.debug(f"Successfully sent Telegram message to {chat_id}")
        except Exception as e:
            logger.error(f"Failed to send Telegram message: {e}")
    
    async def scrape_listings(self, config: SearchConfig, chat_id: str):
        """Scrape listings based on configuration"""
        # Ensure chat_id is a string
        chat_id = str(chat_id)
        if chat_id not in self.seen_listings:
            self.seen_listings[chat_id] = set()
        
        url = config.get_base_url()
        
        async with aiohttp.ClientSession() as session:
            html = await fetch_page(session, url)
            if not html:
                return
            
            soup = BeautifulSoup(html, "html.parser")
            listings = []
            
            for listing in soup.find_all("article", class_="item" if "item" in html else "listing-item"):
                try:
                    title = listing.find("a", class_="item-link").get_text(strip=True)
                    link = "https://www.idealista.pt" + listing.find("a", class_="item-link")["href"]
                    
                    if link in self.seen_listings[chat_id]:
                        print(f"DEBUG: Skipping {link} because it is already in seen_listings for {chat_id}")
                        continue
                    
                    description = listing.find("div", class_="description").get_text(strip=True) if listing.find("div", class_="description") else "No description"
                    
                    price_element = listing.find("span", class_="item-price")
                    price_text = price_element.get_text(strip=True).split("€")[0].strip() if price_element else "0"
                    price = int(price_text.replace(".", ""))  # Convert to integer
                    
                    details_elements = listing.find_all("span", class_="item-detail")
                    rooms_text = details_elements[0].get_text(strip=True) if len(details_elements) > 0 else "0"
                    
                    # Handle room format like "T2", "T4", etc.
                    try:
                        if rooms_text.startswith('T'):
                            rooms = int(rooms_text[1:])  # Extract number after 'T'
                        else:
                            rooms = int(rooms_text.split()[0]) if rooms_text.split() else 0
                    except (ValueError, IndexError):
                        rooms = 0
                    
                    size_text = details_elements[1].get_text(strip=True) if len(details_elements) > 1 else "0"
                    size = int(size_text.split("m²")[0].strip()) if "m²" in size_text else 0
                    
                    furniture_text = details_elements[3].get_text(strip=True) if len(details_elements) > 3 else ""
                    has_furniture = "Furnished" in furniture_text
                    
                    state_text = details_elements[4].get_text(strip=True) if len(details_elements) > 4 else ""
                    is_good_state = "Good condition" in state_text
                    
                    # Skip if description contains excluded terms
                    excluded_terms = ["curto prazo", "alquiler temporal", "estancia corta", "short term"]
                    if any(term.lower() in description.lower() for term in excluded_terms):
                        print(f"DEBUG: Skipping {link} because description contains excluded terms")
                        continue
                    
                    # Skip if floor is in excluded floors
                    excluded_floors = ["Entreplanta", "Planta 1ᵃ", "Bajo"]
                    floor = details_elements[2].get_text(strip=True) if len(details_elements) > 2 else ""
                    if any(floor_term.lower() in floor.lower() for floor_term in excluded_floors):
                        print(f"DEBUG: Skipping {link} because floor '{floor}' is in excluded floors")
                        continue
                    
                    # Apply filters
                    if price > config.max_price:
                        print(f"DEBUG: Skipping {link} because price {price} > max_price {config.max_price}")
                        continue
                    if rooms < config.min_rooms:
                        print(f"DEBUG: Skipping {link} because rooms {rooms} < min_rooms {config.min_rooms}")
                        continue
                    if size < config.min_size or size > config.max_size:
                        print(f"DEBUG: Skipping {link} because size {size} not in range [{config.min_size}, {config.max_size}]")
                        continue
                    # Apply furniture filter
                    if config.furniture_type == FurnitureType.FURNISHED and not has_furniture:
                        print(f"DEBUG: Skipping {link} because furnished required but not present")
                        continue
                    elif config.furniture_type == FurnitureType.UNFURNISHED and has_furniture:
                        print(f"DEBUG: Skipping {link} because unfurnished required but furnished")
                        continue
                    # Note: KITCHEN_FURNITURE filtering would need more detailed parsing of furniture details
                    
                    # Apply property state filter (check if listing state matches any of the selected states)
                    if not any(state == PropertyState.GOOD and is_good_state for state in config.property_states):
                        # For now, we only handle GOOD state detection. Other states would need parsing enhancement
                        if PropertyState.GOOD in config.property_states and not is_good_state:
                            print(f"DEBUG: Skipping {link} because good state required but not present")
                            continue
                    
                    listings.append({
                        "title": title,
                        "link": link,
                        "description": description,
                        "price": f"{price} €",
                        "rooms": f"{rooms} rooms",
                        "size": f"{size}m²",
                        "floor": floor
                    })
                    
                    self.seen_listings[chat_id].add(link)
                    
                    # Send notification
                    message = f"""🏡 *New Apartment Listing!*\n
📍 {title}\n
💰 {price} €\n🛏️ {rooms} rooms\n📐 {size}m²\n🏢 {floor}\n
🔗 [Click here to view]({link})"""
                    print(f"DEBUG: About to send telegram message for {link}")
                    await self.send_telegram_message(chat_id, message)
                    
                except Exception as e:
                    logger.error(f"Error parsing listing: {e}")
            
            await self.save_seen_listings()
            return listings

async def main():
    """Main function to run the scraper"""
    scraper = IdealistaScraper()
    await scraper.initialize()
    
    while True:
        # Load user configurations
        try:
            with open("user_configs.json", "r") as f:
                user_configs = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            logger.error("No user configurations found")
            await asyncio.sleep(60)
            continue
        
        # Scrape for each user
        for chat_id, config_data in user_configs.items():
            # Handle backwards compatibility
            if 'property_state' in config_data and 'property_states' not in config_data:
                config_data['property_states'] = [PropertyState(config_data['property_state'])]
                config_data.pop('property_state', None)
            elif 'property_states' in config_data:
                config_data['property_states'] = [PropertyState(state) for state in config_data['property_states']]
            
            if 'has_furniture' in config_data and 'furniture_type' not in config_data:
                config_data['furniture_type'] = FurnitureType.FURNISHED if config_data['has_furniture'] else FurnitureType.UNFURNISHED
                config_data.pop('has_furniture', None)
            elif 'furniture_type' in config_data:
                config_data['furniture_type'] = FurnitureType(config_data['furniture_type'])
            
            config = SearchConfig(**config_data)
            await scraper.scrape_listings(config, chat_id)
            
            # Sleep based on user's update frequency
            await asyncio.sleep(config.update_frequency * 60)

if __name__ == "__main__":
    asyncio.run(main())
