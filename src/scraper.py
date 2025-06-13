import asyncio
import json
import logging
import os
import time
import random
from typing import Dict, Optional, List

import aiohttp
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from telegram import Bot

from models import SearchConfig, PropertyState, FurnitureType

# Load environment variables
load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Configure logging
logging.basicConfig(level=logging.INFO, format="|%(levelname)s| %(asctime)s - %(message)s")
logger = logging.getLogger(__name__)

class AdaptiveRateLimiter:
    """Adaptive rate limiting that adjusts based on server responses"""
    
    def __init__(self):
        self.user_last_request: Dict[str, float] = {}
        self.global_last_request = 0
        self.min_delay_seconds = 60  # Start with 60 seconds between requests per user
        self.global_min_delay = 30   # Minimum 30 seconds between ANY requests
        self.backoff_multiplier = 2  # Multiply delay on 403 errors
        self.max_delay = 300         # Maximum 5 minutes delay
        self.recent_errors = 0       # Track recent 403 errors
        self.last_error_time = 0     # When last error occurred
    
    async def wait_if_needed(self, user_id: str) -> None:
        """Wait if needed with adaptive rate limiting"""
        current_time = time.time()
        user_id_str = str(user_id)
        
        # Adjust delay based on recent errors
        if self.recent_errors > 0 and (current_time - self.last_error_time) < 300:
            # Recent errors - be more conservative
            adjusted_delay = min(self.min_delay_seconds * (self.backoff_multiplier ** self.recent_errors), self.max_delay)
            logger.warning(f"Adaptive rate limiting: Using {adjusted_delay}s delay due to {self.recent_errors} recent errors")
        else:
            # No recent errors - use normal delay
            adjusted_delay = self.min_delay_seconds
            if self.recent_errors > 0:
                # Reset error count if enough time has passed
                self.recent_errors = 0
                logger.info("Rate limit errors cleared - returning to normal delay")
        
        # Per-user delay
        if user_id_str in self.user_last_request:
            time_since_last = current_time - self.user_last_request[user_id_str]
            if time_since_last < adjusted_delay:
                wait_time = adjusted_delay - time_since_last
                logger.info(f"Rate limiting: User {user_id} waiting {wait_time:.1f}s")
                await asyncio.sleep(wait_time)
        
        # Global delay (prevent too many requests overall)
        global_time_since_last = current_time - self.global_last_request
        if global_time_since_last < self.global_min_delay:
            global_wait_time = self.global_min_delay - global_time_since_last
            logger.info(f"Global rate limiting: waiting {global_wait_time:.1f}s")
            await asyncio.sleep(global_wait_time)
        
        # Update timestamps
        self.user_last_request[user_id_str] = time.time()
        self.global_last_request = time.time()
    
    def record_error(self):
        """Record a 403 error to adjust future delays"""
        self.recent_errors += 1
        self.last_error_time = time.time()
        logger.warning(f"Rate limit error recorded (total: {self.recent_errors}). Will increase delays.")

# Global rate limiter instance
global_rate_limiter = AdaptiveRateLimiter()

# List of realistic user agents to rotate
USER_AGENTS = [
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'
]

async def fetch_page(session: aiohttp.ClientSession, url: str, user_id: str = None) -> Optional[str]:
    """Fetch a page with adaptive rate limiting and browser-like headers"""
    # Apply per-user rate limiting if user_id provided
    if user_id:
        await global_rate_limiter.wait_if_needed(user_id)
    
    # Add small random delay to appear more human-like
    human_delay = random.uniform(1, 3)  # 1-3 seconds random delay
    await asyncio.sleep(human_delay)
    
    # Rotate user agent to appear more like different browsers
    user_agent = random.choice(USER_AGENTS)
    
    headers = {
        'User-Agent': user_agent,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Language': 'pt-PT,pt;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Cache-Control': 'max-age=0',
        'Pragma': 'no-cache'
    }
    
    try:
        async with session.get(url, headers=headers) as response:
            if response.status == 429:
                logger.warning(f"Rate limit (429) for URL: {url}")
                global_rate_limiter.record_error()
                return None
            if response.status == 403:
                logger.warning(f"Access forbidden (403) - Rate limit exceeded for URL: {url}")
                global_rate_limiter.record_error()
                # Wait longer before next request
                logger.info("Implementing emergency backoff due to 403 error")
                await asyncio.sleep(120)  # Emergency 2-minute wait
                return None
            if response.status != 200:
                logger.error(f"Error fetching page: {response.status} for URL: {url}")
                return None
            
            # Success - log it
            logger.info(f"Successfully fetched page (HTTP {response.status}) for user {user_id}")
            return await response.text()
    except Exception as e:
        logger.error(f"Error fetching page: {e} for URL: {url}")
        # Don't raise - return None to handle gracefully
        return None

class IdealistaScraper:
    def __init__(self):
        self.seen_listings: Dict[str, set] = {}  # user_id -> set of seen listing URLs
        self.max_seen_per_user = 1000  # Maximum seen listings per user to prevent memory leaks
        
    async def initialize(self):
        """Initialize the scraper by loading seen listings"""
        try:
            with open("seen_listings.json", "r") as f:
                self.seen_listings = {k: set(v) for k, v in json.load(f).items()}
        except (FileNotFoundError, json.JSONDecodeError):
            self.seen_listings = {}
    
    async def cleanup_seen_listings(self, user_id: str):
        """Clean up seen listings for a user to prevent memory leaks"""
        if user_id in self.seen_listings and len(self.seen_listings[user_id]) > self.max_seen_per_user:
            # Keep only the most recent 500 listings
            seen_list = list(self.seen_listings[user_id])
            self.seen_listings[user_id] = set(seen_list[-500:])
            logger.info(f"Cleaned up seen listings for user {user_id}: kept 500 most recent out of {len(seen_list)}")
    
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
            html = await fetch_page(session, url, user_id=chat_id)
            if not html:
                logger.warning(f"Failed to fetch page for user {chat_id} - will retry next cycle")
                return []
            
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
                    has_furniture = "Furnished" in furniture_text or "Mobilado" in furniture_text
                    has_kitchen_furniture = "Kitchen" in furniture_text or "Cozinha" in furniture_text
                    
                    # Parse property state for display purposes (filtering is handled via URL parameters)
                    state_text = details_elements[4].get_text(strip=True) if len(details_elements) > 4 else ""
                    is_good_state = "Good condition" in state_text or "Bom estado" in state_text
                    is_new_state = "New" in state_text or "Novo" in state_text
                    is_remodel_state = "remodel" in state_text.lower() or "reformar" in state_text.lower()
                    
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
                    # Apply furniture filter based on selected furniture types
                    # If UNFURNISHED is the only selection, skip furnished apartments
                    if (len(config.furniture_types) == 1 and 
                        FurnitureType.UNFURNISHED in config.furniture_types and 
                        has_furniture):
                        print(f"DEBUG: Skipping {link} because unfurnished only required but apartment is furnished")
                        continue
                    
                    # If FURNISHED is selected but apartment is not furnished, skip
                    if (FurnitureType.FURNISHED in config.furniture_types and 
                        not has_furniture and 
                        FurnitureType.UNFURNISHED not in config.furniture_types):
                        print(f"DEBUG: Skipping {link} because furnished required but not present")
                        continue
                    
                    # Note: KITCHEN_FURNITURE filtering would need more detailed parsing of furniture details
                    
                    # Property state filtering is now handled via URL parameters - no need to filter here
                    
                    # LOG: This listing matches all criteria and will be sent
                    logger.info(f"MATCH FOUND for user {chat_id}: {title} - {price}€, {rooms} rooms, {size}m², {floor}")
                    logger.info(f"MATCH DETAILS: URL={link}")
                    
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
                    
                    # Determine furniture status
                    if has_furniture:
                        furniture_status = "🪑 Furnished"
                    elif has_kitchen_furniture:
                        furniture_status = "🍽️ Kitchen furnished"
                    else:
                        furniture_status = "🏠 Unfurnished"
                    
                    # Determine property state based on parsed information
                    if is_new_state:
                        state_status = "🆕 New"
                    elif is_good_state:
                        state_status = "✨ Good condition"
                    elif is_remodel_state:
                        state_status = "🔨 Needs remodeling"
                    else:
                        state_status = "❓ State unknown"
                    
                    # Send notification
                    message = f"""🏡 *New Apartment Listing!*\n
📍 {title}\n
💰 {price} €\n🛏️ {rooms} rooms\n📐 {size}m²\n🏢 {floor}\n{furniture_status}\n{state_status}\n
🔗 [Click here to view]({link})"""
                    print(f"DEBUG: About to send telegram message for {link}")
                    await self.send_telegram_message(chat_id, message)
                    
                    # Track listing notification in stats
                    try:
                        from user_stats import stats_manager
                        stats_manager.record_user_activity(chat_id, 'listing_received')
                    except ImportError:
                        pass  # Stats module not available
                    
                except Exception as e:
                    logger.error(f"Error parsing listing: {e}")
            
            # Clean up seen listings to prevent memory leaks
            await self.cleanup_seen_listings(chat_id)
            
            await self.save_seen_listings()
            
            # Log summary of scraping results
            total_processed = len(soup.find_all("article", class_="item" if "item" in html else "listing-item"))
            total_matches = len(listings)
            logger.info(f"SCRAPING SUMMARY for user {chat_id}: Processed {total_processed} listings, found {total_matches} matches")
            
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
            
            if 'has_furniture' in config_data and 'furniture_types' not in config_data:
                config_data['furniture_types'] = [FurnitureType.FURNISHED if config_data['has_furniture'] else FurnitureType.UNFURNISHED]
                config_data.pop('has_furniture', None)
            elif 'furniture_type' in config_data and 'furniture_types' not in config_data:
                config_data['furniture_types'] = [FurnitureType(config_data['furniture_type'])]
                config_data.pop('furniture_type', None)
            elif 'furniture_types' in config_data:
                config_data['furniture_types'] = [FurnitureType(ft) for ft in config_data['furniture_types']]
            
            config = SearchConfig(**config_data)
            await scraper.scrape_listings(config, chat_id)
            
            # Sleep based on user's update frequency
            await asyncio.sleep(config.update_frequency * 60)

if __name__ == "__main__":
    asyncio.run(main())
