from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ConversationHandler, MessageHandler, filters
from models import SearchConfig, PropertyState, FurnitureType
import json
import os
from typing import Dict
import logging
import asyncio
from dotenv import load_dotenv
from filters import set_rooms, set_size, set_price, set_furniture, set_state, set_city, set_frequency, set_polygon
from scraper import IdealistaScraper
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

# Load environment variables
load_dotenv()

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Conversation states
CHOOSING, SETTING_ROOMS, SETTING_SIZE, SETTING_PRICE, SETTING_FURNITURE, SETTING_STATE, SETTING_CITY, SETTING_POLYGON, SETTING_FREQUENCY, WAITING_FOR_PRICE, WAITING_FOR_POLYGON_URL = range(11)

# Store user configurations and monitoring tasks
user_configs: Dict[int, SearchConfig] = {}
monitoring_tasks: Dict[int, asyncio.Task] = {}  # user_id -> monitoring task

def get_main_menu_keyboard(user_id: int) -> list:
    """Get the main menu keyboard with dynamic monitoring button"""
    base_keyboard = [
        [InlineKeyboardButton("Set number of rooms", callback_data='rooms')],
        [InlineKeyboardButton("Set size in square meters", callback_data='size')],
        [InlineKeyboardButton("Set maximum price", callback_data='price')],
        [InlineKeyboardButton("Set furniture preference", callback_data='furniture')],
        [InlineKeyboardButton("Set state of the property", callback_data='state')],
        [InlineKeyboardButton("Set city", callback_data='city')],
        [InlineKeyboardButton("Set a custom area (polygon)", callback_data='polygon')],
        [InlineKeyboardButton("Set update frequency", callback_data='frequency')],
        [InlineKeyboardButton("Show current settings", callback_data='show')],
        [InlineKeyboardButton("🔄 Reset settings", callback_data='reset_settings')]
    ]
    
    # Add monitoring button based on current status
    is_monitoring = user_id in monitoring_tasks and not monitoring_tasks[user_id].done()
    if is_monitoring:
        base_keyboard.append([InlineKeyboardButton("🛑 Stop monitoring", callback_data='stop_monitoring')])
    else:
        base_keyboard.append([InlineKeyboardButton("🚀 Start searching", callback_data='start_monitoring')])
    
    return base_keyboard

def load_configs():
    """Load saved configurations from file"""
    try:
        with open('user_configs.json', 'r') as f:
            configs = json.load(f)
            for user_id, config in configs.items():
                # Handle backwards compatibility for property_state -> property_states
                if 'property_state' in config and 'property_states' not in config:
                    config['property_states'] = [PropertyState(config['property_state'])]
                    config.pop('property_state', None)  # Remove old field
                elif 'property_states' in config:
                    config['property_states'] = [PropertyState(state) for state in config['property_states']]
                
                # Handle backwards compatibility for furniture setting
                if 'has_furniture' in config and 'furniture_types' not in config:
                    config['furniture_types'] = [FurnitureType.FURNISHED if config['has_furniture'] else FurnitureType.UNFURNISHED]
                    config.pop('has_furniture', None)  # Remove old field
                elif 'furniture_type' in config and 'furniture_types' not in config:
                    config['furniture_types'] = [FurnitureType(config['furniture_type'])]
                    config.pop('furniture_type', None)  # Remove old field
                elif 'furniture_types' in config:
                    config['furniture_types'] = [FurnitureType(ft) for ft in config['furniture_types']]
                
                user_configs[int(user_id)] = SearchConfig(**config)
    except FileNotFoundError:
        # Create empty config file if it doesn't exist
        save_configs()
    except json.JSONDecodeError:
        logger.warning("Invalid JSON in user_configs.json, creating new file")
        save_configs()

def save_configs():
    """Save configurations to file"""
    try:
        configs = {}
        for user_id, config in user_configs.items():
            config_dict = config.__dict__.copy()
            # Convert PropertyState list to string values
            config_dict['property_states'] = [state.value for state in config_dict['property_states']]
            # Convert FurnitureType list to string values
            config_dict['furniture_types'] = [ft.value for ft in config_dict['furniture_types']]
            configs[str(user_id)] = config_dict
        
        with open('user_configs.json', 'w') as f:
            json.dump(configs, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving configurations: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the conversation and show main menu"""
    logger.info(f"START: Command received from user {update.effective_user.id}")
    logger.info(f"START: Context user_data before: {context.user_data}")
    
    # Check if this is a private chat
    if update.effective_chat.id < 0:
        await update.message.reply_text(
            "This bot only works in private chats. Please message me directly!"
        )
        return -1  # ConversationHandler.END
    
    user_id = update.effective_user.id
    if user_id not in user_configs:
        user_configs[user_id] = SearchConfig()
        logger.info(f"Created new config for user {user_id}")
    
    reply_markup = InlineKeyboardMarkup(get_main_menu_keyboard(update.effective_user.id))
    
    await update.message.reply_text(
        "Welcome to Idealista Monitor Bot! Please choose an option:",
        reply_markup=reply_markup
    )
    logger.info(f"START: Returning CHOOSING state ({CHOOSING})")
    return CHOOSING


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle button presses"""
    query = update.callback_query
    await query.answer()
    
    logger.info(f"BUTTON: Handler called with data: {query.data}")
    logger.info(f"BUTTON: Context user_data: {context.user_data}")
    logger.info(f"BUTTON: User {update.effective_user.id}")
    
    if query.data == 'show':
        user_id = update.effective_user.id
        if user_id not in user_configs:
            user_configs[user_id] = SearchConfig()
        config = user_configs[user_id]
        await query.message.reply_text(
            f"Current settings:\n"
            f"Minimum rooms: {config.min_rooms}+\n"
            f"Size: {config.min_size}-{config.max_size}m²\n"
            f"Max Price: {config.max_price}€\n"
            f"Furniture: {', '.join([ft.name.replace('_', ' ').title() for ft in config.furniture_types])}\n"
            f"State: {', '.join([state.name.replace('_', ' ').title() for state in config.property_states])}\n"
            f"{'Custom Area: Set' if config.custom_polygon else f'City: {config.city}'}\n"
            f"Update Frequency: {config.update_frequency} minutes"
        )
        return CHOOSING
    
    # Handle back button
    if query.data == 'back':
        logger.info("Back button pressed, returning to main menu")
        
        # Show main menu
        reply_markup = InlineKeyboardMarkup(get_main_menu_keyboard(update.effective_user.id))
        
        await query.edit_message_text(
            "Please choose an option:",
            reply_markup=reply_markup
        )
        logger.info("Returning to CHOOSING state")
        return CHOOSING
    
    # Handle main menu options
    if query.data == 'rooms':
        return await set_rooms(update, context)
    elif query.data == 'size':
        return await set_size(update, context)
    elif query.data == 'price':
        logger.info("Price button pressed, transitioning to set_price")
        return await set_price(update, context)
    elif query.data == 'furniture':
        return await set_furniture(update, context)
    elif query.data == 'state':
        return await set_state(update, context)
    elif query.data == 'city':
        return await set_city(update, context)
    elif query.data == 'frequency':
        return await set_frequency(update, context)
    elif query.data == 'polygon':
        return await set_polygon(update, context)
    elif query.data == 'start_monitoring':
        return await start_monitoring(update, context)
    elif query.data == 'stop_monitoring':
        return await stop_monitoring(update, context)
    elif query.data == 'reset_settings':
        return await reset_settings(update, context)
    
    # Handle setting values
    if query.data.startswith('rooms_'):
        _, min_rooms = query.data.split('_')
        user_id = update.effective_user.id
        if user_id not in user_configs:
            user_configs[user_id] = SearchConfig()
        config = user_configs[user_id]
        config.min_rooms = int(min_rooms)
        config.max_rooms = 10  # Set a high maximum to include all rooms above minimum
        save_configs()
        await query.message.edit_text(f"Minimum rooms set to {min_rooms}+!")
        
        # Show main menu
        reply_markup = InlineKeyboardMarkup(get_main_menu_keyboard(update.effective_user.id))
        await query.message.edit_text(
            "Welcome to Idealista Monitor Bot! Please choose an option:",
            reply_markup=reply_markup
        )
        return CHOOSING
    
    elif query.data.startswith('size_'):
        _, min_size = query.data.split('_')
        user_id = update.effective_user.id
        if user_id not in user_configs:
            user_configs[user_id] = SearchConfig()
        config = user_configs[user_id]
        config.min_size = int(min_size)
        config.max_size = 200  # Set a high maximum to include all sizes above minimum
        save_configs()
        await query.message.edit_text(f"Minimum size set to {min_size}m²+!")
        
        # Show main menu
        reply_markup = InlineKeyboardMarkup(get_main_menu_keyboard(update.effective_user.id))
        await query.message.edit_text(
            "Welcome to Idealista Monitor Bot! Please choose an option:",
            reply_markup=reply_markup
        )
        return CHOOSING
    
    elif query.data.startswith('price_'):
        _, max_price = query.data.split('_')
        user_id = update.effective_user.id
        if user_id not in user_configs:
            user_configs[user_id] = SearchConfig()
        config = user_configs[user_id]
        config.max_price = int(max_price)
        save_configs()
        await query.message.edit_text("Maximum price updated!")
        
        # Show main menu
        reply_markup = InlineKeyboardMarkup(get_main_menu_keyboard(update.effective_user.id))
        await query.message.edit_text(
            "Welcome to Idealista Monitor Bot! Please choose an option:",
            reply_markup=reply_markup
        )
        return CHOOSING
    
    elif query.data.startswith('furniture_toggle_'):
        _, _, furniture_type = query.data.split('_')
        user_id = update.effective_user.id
        
        # Ensure user config exists
        if user_id not in user_configs:
            user_configs[user_id] = SearchConfig()
        
        config = user_configs[user_id]
        
        # Toggle the furniture type in the list
        if furniture_type == 'furnished':
            target_furniture = FurnitureType.FURNISHED
        elif furniture_type == 'kitchen':
            target_furniture = FurnitureType.KITCHEN_FURNITURE
        elif furniture_type == 'unfurnished':
            target_furniture = FurnitureType.UNFURNISHED
        else:
            return SETTING_FURNITURE
            
        if target_furniture in config.furniture_types:
            # Remove if already selected (but keep at least one)
            if len(config.furniture_types) > 1:
                config.furniture_types.remove(target_furniture)
        else:
            # Add if not selected
            config.furniture_types.append(target_furniture)
            
        save_configs()
        
        # Debug: Log the current furniture selection
        logger.info(f"Furniture types updated for user {user_id}: {[ft.name for ft in config.furniture_types]}")
        
        # Manually refresh the keyboard to show updated checkboxes
        keyboard = []
        
        # Furnished
        is_furnished_selected = FurnitureType.FURNISHED in config.furniture_types
        furnished_text = "✅ Furnished" if is_furnished_selected else "☐ Furnished"
        keyboard.append([InlineKeyboardButton(furnished_text, callback_data='furniture_toggle_furnished')])
        
        # Kitchen Furniture Only
        is_kitchen_selected = FurnitureType.KITCHEN_FURNITURE in config.furniture_types
        kitchen_text = "✅ Kitchen Furniture Only" if is_kitchen_selected else "☐ Kitchen Furniture Only"
        keyboard.append([InlineKeyboardButton(kitchen_text, callback_data='furniture_toggle_kitchen')])
        
        # Unfurnished
        is_unfurnished_selected = FurnitureType.UNFURNISHED in config.furniture_types
        unfurnished_text = "✅ Unfurnished" if is_unfurnished_selected else "☐ Unfurnished"
        keyboard.append([InlineKeyboardButton(unfurnished_text, callback_data='furniture_toggle_unfurnished')])
        
        keyboard.append([InlineKeyboardButton("Back", callback_data='back')])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "Select furniture preferences (you can select multiple):",
            reply_markup=reply_markup
        )
        return SETTING_FURNITURE
    
    elif query.data.startswith('state_toggle_'):
        _, _, state = query.data.split('_')
        user_id = update.effective_user.id
        
        # Ensure user config exists
        if user_id not in user_configs:
            user_configs[user_id] = SearchConfig()
        
        config = user_configs[user_id]
        
        # Toggle the state in the list
        if state == 'good':
            target_state = PropertyState.GOOD
        elif state == 'remodel':
            target_state = PropertyState.NEEDS_REMODELING
        elif state == 'new':
            target_state = PropertyState.NEW
        else:
            return SETTING_STATE
            
        if target_state in config.property_states:
            # Remove if already selected (but keep at least one)
            if len(config.property_states) > 1:
                config.property_states.remove(target_state)
        else:
            # Add if not selected
            config.property_states.append(target_state)
            
        save_configs()
        
        # Debug: Log the current state selection
        logger.info(f"Property states updated for user {user_id}: {[state.name for state in config.property_states]}")
        
        # Manually refresh the keyboard without calling set_state to avoid recursion
        keyboard = []
        
        # Good Condition
        is_good_selected = PropertyState.GOOD in config.property_states
        good_text = "✅ Good Condition" if is_good_selected else "☐ Good Condition"
        keyboard.append([InlineKeyboardButton(good_text, callback_data='state_toggle_good')])
        
        # Needs Remodeling
        is_remodel_selected = PropertyState.NEEDS_REMODELING in config.property_states
        remodel_text = "✅ Needs Remodeling" if is_remodel_selected else "☐ Needs Remodeling"
        keyboard.append([InlineKeyboardButton(remodel_text, callback_data='state_toggle_remodel')])
        
        # New
        is_new_selected = PropertyState.NEW in config.property_states
        new_text = "✅ New" if is_new_selected else "☐ New"
        keyboard.append([InlineKeyboardButton(new_text, callback_data='state_toggle_new')])
        
        keyboard.append([InlineKeyboardButton("Back", callback_data='back')])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "Select property states (you can select multiple):",
            reply_markup=reply_markup
        )
        return SETTING_STATE
    
    elif query.data.startswith('city_'):
        _, city = query.data.split('_')
        user_id = update.effective_user.id
        if user_id not in user_configs:
            user_configs[user_id] = SearchConfig()
        config = user_configs[user_id]
        config.city = city
        save_configs()
        await query.message.edit_text("City updated!")
        
        # Show main menu
        reply_markup = InlineKeyboardMarkup(get_main_menu_keyboard(update.effective_user.id))
        await query.message.edit_text(
            "Welcome to Idealista Monitor Bot! Please choose an option:",
            reply_markup=reply_markup
        )
        return CHOOSING
    
    elif query.data.startswith('freq_'):
        _, minutes = query.data.split('_')
        user_id = update.effective_user.id
        if user_id not in user_configs:
            user_configs[user_id] = SearchConfig()
        config = user_configs[user_id]
        config.update_frequency = int(minutes)
        save_configs()
        await query.message.edit_text("Update frequency updated!")
        
        # Show main menu
        reply_markup = InlineKeyboardMarkup(get_main_menu_keyboard(update.effective_user.id))
        await query.message.edit_text(
            "Welcome to Idealista Monitor Bot! Please choose an option:",
            reply_markup=reply_markup
        )
        return CHOOSING
    
    elif query.data == 'polygon_clear':
        user_id = update.effective_user.id
        if user_id not in user_configs:
            user_configs[user_id] = SearchConfig()
        config = user_configs[user_id]
        config.custom_polygon = None
        save_configs()
        await query.message.edit_text("Custom area cleared!")
        
        # Show main menu
        reply_markup = InlineKeyboardMarkup(get_main_menu_keyboard(update.effective_user.id))
        await query.message.edit_text(
            "Welcome to Idealista Monitor Bot! Please choose an option:",
            reply_markup=reply_markup
        )
        return CHOOSING
    
    return CHOOSING

async def handle_price_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the user's price input"""
    user_input = update.message.text.strip()
    logger.info(f"HANDLE_PRICE_INPUT: Received price input: '{user_input}' from user {update.effective_user.id}")
    logger.info(f"HANDLE_PRICE_INPUT: Current user_data: {context.user_data}")
    logger.info(f"HANDLE_PRICE_INPUT: In conversation handler")
    
    try:
        # Remove any non-digit characters except for spaces and common separators
        cleaned_input = ''.join(c for c in user_input if c.isdigit())
        if not cleaned_input:
            raise ValueError("No digits found in input")
            
        price = int(cleaned_input)
        logger.info(f"Parsed price as integer: {price}")
        
        if price <= 0:
            logger.warning(f"Invalid price value: {price} (must be positive)")
            raise ValueError("Price must be positive")
        
        user_id = update.effective_user.id
        if user_id not in user_configs:
            user_configs[user_id] = SearchConfig()
        config = user_configs[user_id]
        config.max_price = price
        save_configs()
        logger.info(f"Successfully updated price to {price}€ for user {update.effective_user.id}")
        
        reply_markup = InlineKeyboardMarkup(get_main_menu_keyboard(update.effective_user.id))
        await update.message.reply_text(
            f"Maximum price set to {price}€!",
            reply_markup=reply_markup
        )
        return CHOOSING
        
    except ValueError as e:
        logger.error(f"Error processing price input '{user_input}': {str(e)}")
        keyboard = [
            [InlineKeyboardButton("Back", callback_data='back')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "Please enter a valid positive number for the price (e.g., 1200):",
            reply_markup=reply_markup
        )
        return WAITING_FOR_PRICE

async def handle_polygon_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the user's polygon URL input"""
    user_input = update.message.text.strip()
    logger.info(f"HANDLE_POLYGON_INPUT: Received URL input: '{user_input}' from user {update.effective_user.id}")
    
    try:
        # Basic URL validation
        if not user_input.startswith(('http://', 'https://')):
            raise ValueError("Invalid URL format")
        
        if 'idealista.pt' not in user_input:
            raise ValueError("URL must be from idealista.pt")
        
        if 'shape=' not in user_input:
            raise ValueError("URL must contain 'shape=' parameter")
        
        # Extract the shape parameter
        import urllib.parse
        parsed_url = urllib.parse.urlparse(user_input)
        query_params = urllib.parse.parse_qs(parsed_url.query)
        
        if 'shape' not in query_params:
            raise ValueError("No 'shape' parameter found in URL")
        
        shape_value = query_params['shape'][0]
        logger.info(f"Extracted shape parameter: {shape_value}")
        
        user_id = update.effective_user.id
        if user_id not in user_configs:
            user_configs[user_id] = SearchConfig()
        
        config = user_configs[user_id]
        config.custom_polygon = shape_value
        save_configs()
        logger.info(f"Successfully updated custom polygon for user {update.effective_user.id}")
        
        reply_markup = InlineKeyboardMarkup(get_main_menu_keyboard(update.effective_user.id))
        await update.message.reply_text(
            "✅ Custom area set successfully! The bot will now search within your defined polygon.",
            reply_markup=reply_markup
        )
        return CHOOSING
        
    except ValueError as e:
        logger.error(f"Error processing polygon URL '{user_input}': {str(e)}")
        keyboard = [
            [InlineKeyboardButton("Back", callback_data='back')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            f"❌ Error: {str(e)}\n\nPlease make sure you're copying the full URL from idealista.pt after drawing your custom area on the map.",
            reply_markup=reply_markup
        )
        return WAITING_FOR_POLYGON_URL

async def user_monitoring_task(user_id: int, chat_id: int):
    """Background monitoring task for a specific user"""
    scraper = IdealistaScraper()
    await scraper.initialize()
    
    logger.info(f"Starting monitoring for user {user_id}")
    
    try:
        while True:
            if user_id not in user_configs:
                logger.warning(f"User {user_id} no longer has config, stopping monitoring")
                break
                
            config = user_configs[user_id]
            logger.info(f"Scraping for user {user_id} with frequency {config.update_frequency} minutes")
            
            # Debug: Log the URL being used
            search_url = config.get_base_url()
            logger.info(f"Generated search URL for user {user_id}: {search_url}")
            
            try:
                await scraper.scrape_listings(config, str(chat_id))
            except Exception as e:
                logger.error(f"Error during scraping for user {user_id}: {e}")
                # Send error notification to user
                try:
                    from telegram import Bot
                    bot = Bot(token=os.getenv('TELEGRAM_BOT_TOKEN'))
                    await bot.send_message(
                        chat_id=chat_id, 
                        text=f"⚠️ Monitoring error: {str(e)}\n\nWill retry in {config.update_frequency} minutes."
                    )
                except Exception as send_error:
                    logger.error(f"Failed to send error message to user {user_id}: {send_error}")
                # Continue monitoring even if one scrape fails
            
            # Wait for the user's configured frequency
            await asyncio.sleep(config.update_frequency * 60)
            
    except asyncio.CancelledError:
        logger.info(f"Monitoring cancelled for user {user_id}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error in monitoring task for user {user_id}: {e}")

async def start_monitoring(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start monitoring for the user"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    # Ensure user config exists
    if user_id not in user_configs:
        user_configs[user_id] = SearchConfig()
    
    # Check if already monitoring
    if user_id in monitoring_tasks and not monitoring_tasks[user_id].done():
        await query.message.edit_text("✅ Monitoring is already active!")
        reply_markup = InlineKeyboardMarkup(get_main_menu_keyboard(update.effective_user.id))
        await query.message.edit_text(
            "Welcome to Idealista Monitor Bot! Please choose an option:",
            reply_markup=reply_markup
        )
        return CHOOSING
    
    # Debug: Test URL generation before starting monitoring
    config = user_configs[user_id]
    test_url = config.get_base_url()
    logger.info(f"DEBUG: Generated URL for user {user_id}: {test_url}")
    
    # Start monitoring task
    task = asyncio.create_task(user_monitoring_task(user_id, chat_id))
    monitoring_tasks[user_id] = task
    
    await query.message.edit_text(f"🚀 Monitoring started! You'll receive notifications when new listings match your criteria.\n\n🔍 Search URL: {test_url}")
    
    # Show main menu
    reply_markup = InlineKeyboardMarkup(get_main_menu_keyboard(update.effective_user.id))
    await query.message.edit_text(
        "Welcome to Idealista Monitor Bot! Please choose an option:",
        reply_markup=reply_markup
    )
    return CHOOSING

async def stop_monitoring(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stop monitoring for the user"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    
    # Check if monitoring exists
    if user_id not in monitoring_tasks or monitoring_tasks[user_id].done():
        await query.message.edit_text("❌ No active monitoring found!")
    else:
        # Cancel the monitoring task
        monitoring_tasks[user_id].cancel()
        try:
            await monitoring_tasks[user_id]
        except asyncio.CancelledError:
            pass
        del monitoring_tasks[user_id]
        
        await query.message.edit_text("🛑 Monitoring stopped!")
    
    # Show main menu
    reply_markup = InlineKeyboardMarkup(get_main_menu_keyboard(update.effective_user.id))
    await query.message.edit_text(
        "Welcome to Idealista Monitor Bot! Please choose an option:",
        reply_markup=reply_markup
    )
    return CHOOSING

async def reset_settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Reset all settings to default values"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    
    # Reset to default configuration
    user_configs[user_id] = SearchConfig()
    save_configs()
    
    logger.info(f"Settings reset to defaults for user {user_id}")
    
    await query.message.edit_text("🔄 All settings have been reset to default values!")
    
    # Show main menu
    reply_markup = InlineKeyboardMarkup(get_main_menu_keyboard(update.effective_user.id))
    await query.message.edit_text(
        "Welcome to Idealista Monitor Bot! Please choose an option:",
        reply_markup=reply_markup
    )
    return CHOOSING

def main():
    """Start the bot"""
    # Load saved configurations
    load_configs()
    
    # Check if token exists
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN not found in environment variables")
        return
    
    logger.info("Starting bot with token...")
    
    # Create the Application
    application = Application.builder().token(token).build()
    
    # Add conversation handler with explicit configuration
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            CHOOSING: [CallbackQueryHandler(button_handler)],
            SETTING_ROOMS: [CallbackQueryHandler(button_handler)],
            SETTING_SIZE: [CallbackQueryHandler(button_handler)],
            SETTING_FURNITURE: [CallbackQueryHandler(button_handler)],
            SETTING_STATE: [CallbackQueryHandler(button_handler)],
            SETTING_CITY: [CallbackQueryHandler(button_handler)],
            SETTING_FREQUENCY: [CallbackQueryHandler(button_handler)],
            WAITING_FOR_PRICE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_price_input),
                CallbackQueryHandler(button_handler)
            ],
            WAITING_FOR_POLYGON_URL: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_polygon_input),
                CallbackQueryHandler(button_handler)
            ]
        },
        fallbacks=[CommandHandler('start', start)],
        per_chat=True,
        per_user=True,
        per_message=False,
        allow_reentry=True,
        name="idealista_conv"
    )
    
    # Add debug logging for conversation handler
    logger.info("Setting up conversation handler with states:")
    for state, handlers in conv_handler.states.items():
        logger.info(f"State {state}: {[type(h).__name__ for h in handlers]}")
    
    # Add debug handler to catch ALL messages before conversation handler
    async def debug_all_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.message and update.message.text:
            chat_type = "private" if update.effective_chat.id > 0 else "group"
            logger.info(f"DEBUG_ALL: Message '{update.message.text}' from user {update.effective_user.id}")
            logger.info(f"DEBUG_ALL: Chat ID: {update.effective_chat.id} (TYPE: {chat_type})")
            logger.info(f"DEBUG_ALL: User_data: {context.user_data}")
            logger.info(f"DEBUG_ALL: Chat_data: {context.chat_data}")
            # Check if this is in a conversation
            conv_key = (update.effective_chat.id, update.effective_user.id)
            logger.info(f"DEBUG_ALL: Conversation key would be: {conv_key}")
            logger.info(f"DEBUG_ALL: Message will be processed by conversation handler")
    
    # Add this BEFORE conversation handler
    application.add_handler(MessageHandler(filters.ALL, debug_all_messages), group=-1)
    
    
    application.add_handler(conv_handler)
    
    # Add a simple test handler to debug
    async def test_handler(update: Update, _: ContextTypes.DEFAULT_TYPE):
        logger.info(f"Test command received from user {update.effective_user.id}")
        await update.message.reply_text("Test command works!")
    
    application.add_handler(CommandHandler('test', test_handler))
    
    # Start the Bot
    logger.info("Starting polling...")
    application.run_polling()

if __name__ == '__main__':
    main() 