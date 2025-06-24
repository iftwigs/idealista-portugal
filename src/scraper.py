import asyncio
import json
import logging
import os
import random
import time
from typing import Dict, Optional

import aiohttp
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from telegram import Bot

from models import FurnitureType, PropertyState, SearchConfig

# Load environment variables
load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="|%(levelname)s| %(asctime)s - %(message)s"
)
logger = logging.getLogger(__name__)


class AdaptiveRateLimiter:
    """Adaptive rate limiting that adjusts based on server responses"""

    def __init__(self):
        self.user_last_request: Dict[str, float] = {}
        self.global_last_request = 0
        self.min_delay_seconds = 90  # Increased to 90 seconds between requests per user
        self.global_min_delay = 45  # Increased to 45 seconds between ANY requests
        self.backoff_multiplier = 2.5  # Slightly higher multiplier for pagination
        self.max_delay = 600  # Increased to 10 minutes maximum delay
        self.recent_errors = 0  # Track recent 403 errors
        self.last_error_time = 0  # When last error occurred
        self.pagination_delay_multiplier = 1.5  # Extra delay for pagination requests

    async def wait_if_needed(self, user_id: str) -> None:
        """Wait if needed with adaptive rate limiting"""
        current_time = time.time()
        user_id_str = str(user_id)

        # Adjust delay based on recent errors
        if self.recent_errors > 0 and (current_time - self.last_error_time) < 300:
            # Recent errors - be more conservative
            adjusted_delay = min(
                self.min_delay_seconds * (self.backoff_multiplier**self.recent_errors),
                self.max_delay,
            )
            logger.warning(
                f"Adaptive rate limiting: Using {adjusted_delay}s delay due to {self.recent_errors} recent errors"
            )
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
        logger.warning(
            f"Rate limit error recorded (total: {self.recent_errors}). Will increase delays."
        )


# Global rate limiter instance
global_rate_limiter = AdaptiveRateLimiter()

# List of realistic user agents to rotate
USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
]


async def fetch_page(
    session: aiohttp.ClientSession, url: str, user_id: str = None
) -> Optional[str]:
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
        "User-Agent": user_agent,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Language": "pt-PT,pt;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Cache-Control": "max-age=0",
        "Pragma": "no-cache",
    }

    try:
        async with session.get(url, headers=headers) as response:
            if response.status == 429:
                logger.warning(f"Rate limit (429) for URL: {url}")
                global_rate_limiter.record_error()
                return None
            if response.status == 403:
                logger.warning(
                    f"Access forbidden (403) - Rate limit exceeded for URL: {url}"
                )
                global_rate_limiter.record_error()
                # Wait longer before next request
                logger.info("Implementing emergency backoff due to 403 error")
                await asyncio.sleep(120)  # Emergency 2-minute wait
                return None
            if response.status != 200:
                logger.error(f"Error fetching page: {response.status} for URL: {url}")
                return None

            # Success - log it
            logger.info(
                f"Successfully fetched page (HTTP {response.status}) for user {user_id}"
            )
            return await response.text()
    except Exception as e:
        logger.error(f"Error fetching page: {e} for URL: {url}")
        # Don't raise - return None to handle gracefully
        return None


class IdealistaScraper:
    def __init__(self):
        self.seen_listings: Dict[str, set] = {}  # user_id -> set of seen listing URLs
        self.max_seen_per_user = (
            1000  # Maximum seen listings per user to prevent memory leaks
        )

    async def initialize(self):
        """Initialize the scraper by loading seen listings"""
        try:
            # Use data directory if it exists, otherwise current directory
            listings_file = (
                "data/seen_listings.json"
                if os.path.exists("data")
                else "seen_listings.json"
            )
            with open(listings_file) as f:
                self.seen_listings = {k: set(v) for k, v in json.load(f).items()}
        except (FileNotFoundError, json.JSONDecodeError):
            self.seen_listings = {}

    async def cleanup_seen_listings(self, user_id: str):
        """Clean up seen listings for a user to prevent memory leaks"""
        if (
            user_id in self.seen_listings
            and len(self.seen_listings[user_id]) > self.max_seen_per_user
        ):
            # Keep only the most recent 500 listings
            seen_list = list(self.seen_listings[user_id])
            self.seen_listings[user_id] = set(seen_list[-500:])
            logger.info(
                f"Cleaned up seen listings for user {user_id}: kept 500 most recent out of {len(seen_list)}"
            )

    async def save_seen_listings(self):
        """Save seen listings to file"""
        # Use data directory if it exists, otherwise current directory
        listings_file = (
            "data/seen_listings.json"
            if os.path.exists("data")
            else "seen_listings.json"
        )
        with open(listings_file, "w") as f:
            json.dump({k: list(v) for k, v in self.seen_listings.items()}, f)

    async def send_telegram_message(self, chat_id: str, message: str, image_url: str = None):
        """Send message via Telegram, optionally with an image"""
        try:
            bot = Bot(token=TELEGRAM_BOT_TOKEN)
            
            if image_url:
                # Download image first, then send as file to avoid Telegram access issues
                try:
                    image_data = await self._download_image(image_url)
                    if image_data:
                        await bot.send_photo(
                            chat_id=chat_id, 
                            photo=image_data, 
                            caption=message, 
                            parse_mode="Markdown"
                        )
                        logger.debug(f"Successfully sent Telegram photo message to {chat_id}")
                    else:
                        # Image download failed, send text only
                        logger.warning(f"Failed to download image from {image_url}, sending text only")
                        await bot.send_message(chat_id=chat_id, text=message, parse_mode="Markdown")
                        logger.debug(f"Successfully sent fallback text message to {chat_id}")
                except Exception as photo_error:
                    # If photo sending fails, fall back to text message
                    logger.warning(f"Failed to send photo, falling back to text: {photo_error}")
                    await bot.send_message(chat_id=chat_id, text=message, parse_mode="Markdown")
                    logger.debug(f"Successfully sent fallback text message to {chat_id}")
            else:
                # Send text message only
                await bot.send_message(chat_id=chat_id, text=message, parse_mode="Markdown")
                logger.debug(f"Successfully sent Telegram text message to {chat_id}")
                
        except Exception as e:
            logger.error(f"Failed to send Telegram message: {e}")

    async def _download_image(self, image_url: str) -> Optional[bytes]:
        """Download image from URL and return as bytes for Telegram"""
        try:
            # Use the same headers as for web scraping to ensure access
            headers = {
                "User-Agent": random.choice(USER_AGENTS),
                "Accept": "image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
                "Accept-Language": "pt-PT,pt;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
                "Accept-Encoding": "gzip, deflate, br",
                "DNT": "1",
                "Connection": "keep-alive",
                "Sec-Fetch-Dest": "image",
                "Sec-Fetch-Mode": "no-cors",
                "Sec-Fetch-Site": "cross-site",
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(image_url, headers=headers, timeout=10) as response:
                    if response.status == 200:
                        image_data = await response.read()
                        logger.debug(f"Successfully downloaded image: {len(image_data)} bytes from {image_url}")
                        return image_data
                    else:
                        logger.warning(f"Failed to download image: HTTP {response.status} from {image_url}")
                        return None
                        
        except asyncio.TimeoutError:
            logger.warning(f"Timeout downloading image from {image_url}")
            return None
        except Exception as e:
            logger.warning(f"Error downloading image from {image_url}: {e}")
            return None

    async def scrape_listings(
        self,
        config: SearchConfig,
        chat_id: str,
        max_pages: int = 3,
        force_all_pages: bool = False,
    ):
        """Scrape listings based on configuration with pagination support

        Args:
            config: Search configuration
            chat_id: User's chat ID
            max_pages: Maximum number of pages to scrape (default 3 for safety)
            force_all_pages: If True, scrape all pages even if no new listings found
        """
        # Ensure chat_id is a string
        chat_id = str(chat_id)
        if chat_id not in self.seen_listings:
            self.seen_listings[chat_id] = set()

        all_listings = []
        current_page = 1
        consecutive_empty_pages = 0
        max_consecutive_empty = 2  # Stop if 2 consecutive pages have no new listings

        async with aiohttp.ClientSession() as session:
            while current_page <= max_pages:
                # Build URL for current page
                base_url = config.get_base_url()
                if current_page == 1:
                    url = base_url
                else:
                    # Add pagination parameter
                    separator = "&" if "?" in base_url else "?"
                    url = f"{base_url}{separator}pagina={current_page}"

                logger.info(
                    f"🔍 PAGINATION: Scraping page {current_page}/{max_pages} for user {chat_id}"
                )
                logger.info(f"🔗 URL: {url}")

                # Fetch page with enhanced delays for pagination
                if current_page > 1:
                    # Extra delay between pages to appear more human-like
                    page_delay = random.uniform(5, 12)  # 5-12 seconds between pages
                    logger.info(
                        f"Waiting {page_delay:.1f}s before scraping page {current_page}"
                    )
                    await asyncio.sleep(page_delay)

                html = await fetch_page(session, url, user_id=chat_id)
                if not html:
                    logger.warning(
                        f"Failed to fetch page {current_page} for user {chat_id} - stopping pagination"
                    )
                    break

                soup = BeautifulSoup(html, "html.parser")
                page_listings = []

                # Check if this page has any listings
                listing_elements = soup.find_all(
                    "article", class_="item" if "item" in html else "listing-item"
                )
                if not listing_elements:
                    logger.info(
                        f"No listings found on page {current_page} for user {chat_id}"
                    )
                    consecutive_empty_pages += 1
                    if consecutive_empty_pages >= max_consecutive_empty:
                        logger.info(
                            f"Stopping pagination after {consecutive_empty_pages} consecutive empty pages"
                        )
                        break
                    current_page += 1
                    continue

                # Reset consecutive empty pages counter
                consecutive_empty_pages = 0

                # Process listings on this page
                new_listings_this_page = 0
                page_had_listings = True  # Track if page had any listings
                for listing in listing_elements:
                    try:
                        title = listing.find("a", class_="item-link").get_text(
                            strip=True
                        )
                        link = (
                            "https://www.idealista.pt"
                            + listing.find("a", class_="item-link")["href"]
                        )

                        if link in self.seen_listings[chat_id]:
                            print(
                                f"DEBUG: Skipping {link} because it is already in seen_listings for {chat_id}"
                            )
                            continue

                        description = (
                            listing.find("div", class_="description").get_text(
                                strip=True
                            )
                            if listing.find("div", class_="description")
                            else "No description"
                        )

                        price_element = listing.find("span", class_="item-price")
                        price_text = (
                            price_element.get_text(strip=True).split("€")[0].strip()
                            if price_element
                            else "0"
                        )
                        price = int(price_text.replace(".", ""))  # Convert to integer

                        details_elements = listing.find_all(
                            "span", class_="item-detail"
                        )
                        rooms_text = (
                            details_elements[0].get_text(strip=True)
                            if len(details_elements) > 0
                            else "0"
                        )

                        # Handle room format like "T2", "T4", etc.
                        try:
                            if rooms_text.startswith("T"):
                                rooms = int(rooms_text[1:])  # Extract number after 'T'
                            else:
                                rooms = (
                                    int(rooms_text.split()[0])
                                    if rooms_text.split()
                                    else 0
                                )
                        except (ValueError, IndexError):
                            rooms = 0

                        size_text = (
                            details_elements[1].get_text(strip=True)
                            if len(details_elements) > 1
                            else "0"
                        )
                        size = (
                            int(size_text.split("m²")[0].strip())
                            if "m²" in size_text
                            else 0
                        )

                        # Parse furniture information for display purposes only
                        # (filtering is handled by URL parameters)
                        furniture_text = ""
                        for elem in details_elements[
                            3:
                        ]:  # Check elements from index 3 onwards
                            furniture_text += elem.get_text(strip=True) + " "
                        furniture_text = furniture_text.lower()

                        # Simple detection for display
                        has_furniture = (
                            "mobilado" in furniture_text
                            or "furnished" in furniture_text
                        )
                        has_kitchen_furniture = (
                            "cozinha" in furniture_text and "equipada" in furniture_text
                        )

                        # Parse property state for display purposes (filtering is handled via URL parameters)
                        state_text = (
                            details_elements[4].get_text(strip=True)
                            if len(details_elements) > 4
                            else ""
                        )
                        is_good_state = (
                            "Good condition" in state_text or "Bom estado" in state_text
                        )
                        is_new_state = "New" in state_text or "Novo" in state_text
                        is_remodel_state = (
                            "remodel" in state_text.lower()
                            or "reformar" in state_text.lower()
                        )

                        # Skip if description contains excluded terms
                        excluded_terms = [
                            "curto prazo",
                            "alquiler temporal",
                            "estancia corta",
                            "short term",
                        ]
                        if any(
                            term.lower() in description.lower()
                            for term in excluded_terms
                        ):
                            print(
                                f"DEBUG: Skipping {link} because description contains excluded terms"
                            )
                            continue

                        # Skip if floor is in excluded floors
                        excluded_floors = ["Entreplanta", "Planta 1ᵃ", "Bajo"]
                        floor = (
                            details_elements[2].get_text(strip=True)
                            if len(details_elements) > 2
                            else ""
                        )
                        if any(
                            floor_term.lower() in floor.lower()
                            for floor_term in excluded_floors
                        ):
                            print(
                                f"DEBUG: Skipping {link} because floor '{floor}' is in excluded floors"
                            )
                            continue

                        # Apply filters
                        if price > config.max_price:
                            print(
                                f"DEBUG: Skipping {link} because price {price} > max_price {config.max_price}"
                            )
                            continue
                        if rooms < config.min_rooms:
                            print(
                                f"DEBUG: Skipping {link} because rooms {rooms} < min_rooms {config.min_rooms}"
                            )
                            continue
                        if size < config.min_size or size > config.max_size:
                            print(
                                f"DEBUG: Skipping {link} because size {size} not in range [{config.min_size}, {config.max_size}]"
                            )
                            continue
                        # Furniture filtering is handled by URL parameters - no client-side filtering needed
                        # Property state filtering is also handled via URL parameters

                        # LOG: This listing matches all criteria and will be sent
                        logger.info(
                            f"MATCH FOUND for user {chat_id} (page {current_page}): {title} - {price}€, {rooms} rooms, {size}m², {floor}"
                        )
                        logger.info(f"MATCH DETAILS: URL={link}")

                        listing_data = {
                            "title": title,
                            "link": link,
                            "description": description,
                            "price": f"{price} €",
                            "rooms": f"{rooms} rooms",
                            "size": f"{size}m²",
                            "floor": floor,
                        }

                        # Determine furniture status for display
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

                        # Extract property image URL
                        image_url = None
                        try:
                            # Look for the main property image
                            img_element = listing.find("img", alt="Primeira foto do imóvel")
                            if img_element and img_element.get('src'):
                                image_url = img_element.get('src')
                                # Convert blur URL to higher quality if possible
                                if '/blur/' in image_url:
                                    # Replace blur with higher quality version
                                    image_url = image_url.replace('/blur/480_360_mq/', '/blur/680_510_mq/')
                                logger.debug(f"Found image URL for {title}: {image_url}")
                            else:
                                logger.debug(f"No image found for {title}")
                        except Exception as e:
                            logger.warning(f"Error extracting image for {title}: {e}")
                            image_url = None

                        # Add furniture and state status to listing data
                        listing_data["furniture_status"] = furniture_status
                        listing_data["state_status"] = state_status
                        listing_data["image_url"] = image_url

                        page_listings.append(listing_data)
                        new_listings_this_page += 1
                        self.seen_listings[chat_id].add(link)

                        # Send notification immediately
                        message = f"""🏡 *New Apartment Listing!*\n
📍 {title}\n
💰 {price} €\n🛏️ {rooms} rooms\n📐 {size}m²\n🏢 {floor}\n{furniture_status}\n{state_status}\n
🔗 [Click here to view]({link})"""
                        print(
                            f"DEBUG: About to send telegram message for {link} (page {current_page})"
                        )
                        await self.send_telegram_message(chat_id, message, image_url)

                        # Track listing notification in stats
                        try:
                            from user_stats import stats_manager

                            stats_manager.record_user_activity(
                                chat_id, "listing_received"
                            )
                        except ImportError:
                            pass  # Stats module not available

                    except Exception as e:
                        logger.error(
                            f"Error parsing listing on page {current_page}: {e}"
                        )

                # Add page listings to total
                all_listings.extend(page_listings)

                # Log page summary
                logger.info(
                    f"📊 PAGE {current_page} SUMMARY for user {chat_id}: Processed {len(listing_elements)} listings, found {new_listings_this_page} new matches"
                )

                # Handle pages with no new listings (but had listings)
                if new_listings_this_page == 0 and page_had_listings:
                    consecutive_empty_pages += 1
                    logger.info(
                        f"No new listings found on page {current_page} (had {len(listing_elements)} listings but all were seen)"
                    )
                    if (
                        consecutive_empty_pages >= max_consecutive_empty
                        and not force_all_pages
                    ):
                        logger.info(
                            f"Stopping pagination after {consecutive_empty_pages} consecutive pages with no new listings"
                        )
                        break
                # Reset consecutive empty pages counter if we found new listings
                elif new_listings_this_page > 0:
                    consecutive_empty_pages = 0

                # Move to next page
                current_page += 1

            # Clean up seen listings to prevent memory leaks
            await self.cleanup_seen_listings(chat_id)

            await self.save_seen_listings()

            # Log final summary of scraping results
            total_pages_scraped = (
                current_page - 1 if current_page > max_pages else current_page
            )
            logger.info(
                f"PAGINATION SUMMARY for user {chat_id}: Scraped {total_pages_scraped} pages, found {len(all_listings)} total matches"
            )

            return all_listings


async def main():
    """Main function to run the scraper"""
    scraper = IdealistaScraper()
    await scraper.initialize()

    while True:
        # Load user configurations
        try:
            # Use data directory if it exists, otherwise current directory
            config_file = (
                "data/user_configs.json"
                if os.path.exists("data")
                else "user_configs.json"
            )
            with open(config_file) as f:
                user_configs = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            logger.error("No user configurations found")
            await asyncio.sleep(60)
            continue

        # Scrape for each user
        for chat_id, config_data in user_configs.items():
            # Handle backwards compatibility
            if "property_state" in config_data and "property_states" not in config_data:
                config_data["property_states"] = [
                    PropertyState(config_data["property_state"])
                ]
                config_data.pop("property_state", None)
            elif "property_states" in config_data:
                config_data["property_states"] = [
                    PropertyState(state) for state in config_data["property_states"]
                ]

            if "has_furniture" in config_data and "furniture_type" not in config_data:
                config_data["furniture_type"] = (
                    FurnitureType.FURNISHED
                    if config_data["has_furniture"]
                    else FurnitureType.INDIFFERENT
                )
                config_data.pop("has_furniture", None)
            elif (
                "furniture_types" in config_data and "furniture_type" not in config_data
            ):
                # Convert from old list format to single value (take first item)
                if config_data["furniture_types"]:
                    old_value = config_data["furniture_types"][0]
                    # Map old enum values to new ones
                    if old_value == "mobilado":
                        config_data["furniture_type"] = FurnitureType.FURNISHED
                    elif old_value == "mobilado-cozinha":
                        config_data["furniture_type"] = FurnitureType.KITCHEN_FURNITURE
                    elif old_value == "sem-mobilia":
                        config_data["furniture_type"] = FurnitureType.INDIFFERENT
                    else:
                        config_data["furniture_type"] = FurnitureType.INDIFFERENT
                else:
                    config_data["furniture_type"] = FurnitureType.INDIFFERENT
                config_data.pop("furniture_types", None)
            elif "furniture_type" in config_data:
                # Handle old furniture_type values too
                old_value = config_data["furniture_type"]
                if old_value == "mobilado":
                    config_data["furniture_type"] = FurnitureType.FURNISHED
                elif old_value == "mobilado-cozinha":
                    config_data["furniture_type"] = FurnitureType.KITCHEN_FURNITURE
                elif old_value == "sem-mobilia":
                    config_data["furniture_type"] = FurnitureType.INDIFFERENT
                else:
                    try:
                        config_data["furniture_type"] = FurnitureType(
                            config_data["furniture_type"]
                        )
                    except ValueError:
                        config_data["furniture_type"] = FurnitureType.INDIFFERENT

            config = SearchConfig(**config_data)
            await scraper.scrape_listings(config, chat_id)

            # Sleep based on user's update frequency
            await asyncio.sleep(config.update_frequency * 60)


if __name__ == "__main__":
    asyncio.run(main())
