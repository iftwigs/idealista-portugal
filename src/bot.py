import asyncio
import json
import logging
import os
from typing import Dict

from dotenv import load_dotenv
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)

from models import FloorType, FurnitureType, PropertyState, SearchConfig

# Configuration file locking for multi-user safety
config_lock = asyncio.Lock()
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from filters import (
    set_city,
    set_floor,
    set_frequency,
    set_furniture,
    set_pagination,
    set_polygon,
    set_price,
    set_rooms,
    set_size,
    set_state,
)
from scraper import IdealistaScraper
from user_stats import stats_manager

# Load environment variables
load_dotenv()

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Conversation states
(
    CHOOSING,
    SETTING_ROOMS,
    SETTING_SIZE,
    SETTING_PRICE,
    SETTING_FURNITURE,
    SETTING_STATE,
    SETTING_CITY,
    SETTING_POLYGON,
    SETTING_FREQUENCY,
    SETTING_PAGES,
    SETTING_FLOOR,
    WAITING_FOR_PRICE,
    WAITING_FOR_POLYGON_URL,
) = range(13)

# Store user configurations and monitoring tasks
user_configs: Dict[int, SearchConfig] = {}
monitoring_tasks: Dict[int, asyncio.Task] = {}  # user_id -> monitoring task


def get_main_menu_keyboard(user_id: int) -> list:
    """Get the main menu keyboard with dynamic monitoring button"""
    base_keyboard = [
        [InlineKeyboardButton("Set number of rooms", callback_data="rooms")],
        [InlineKeyboardButton("Set size in square meters", callback_data="size")],
        [InlineKeyboardButton("Set maximum price", callback_data="price")],
        [InlineKeyboardButton("Set furniture preference", callback_data="furniture")],
        [InlineKeyboardButton("Set state of the property", callback_data="state")],
        [InlineKeyboardButton("Set floor preference", callback_data="floor")],
        [InlineKeyboardButton("Set city", callback_data="city")],
        [InlineKeyboardButton("Set a custom area (polygon)", callback_data="polygon")],
        [InlineKeyboardButton("Set update frequency", callback_data="frequency")],
        [InlineKeyboardButton("📄 Pagination settings", callback_data="pagination")],
        [InlineKeyboardButton("Show current settings", callback_data="show")],
        [InlineKeyboardButton("📊 Bot Statistics", callback_data="stats")],
        [
            InlineKeyboardButton(
                "🔍 Check Monitoring Status", callback_data="check_status"
            )
        ],
        [InlineKeyboardButton("🔄 Reset settings", callback_data="reset_settings")],
    ]

    # Add monitoring button based on current status
    is_monitoring = user_id in monitoring_tasks and not monitoring_tasks[user_id].done()
    if is_monitoring:
        base_keyboard.append(
            [
                InlineKeyboardButton(
                    "🛑 Stop monitoring", callback_data="stop_monitoring"
                )
            ]
        )
    else:
        base_keyboard.append(
            [
                InlineKeyboardButton(
                    "🚀 Start searching", callback_data="start_monitoring"
                )
            ]
        )

    return base_keyboard


def load_configs():
    """Load saved configurations from file"""
    try:
        # Use data directory if it exists, otherwise current directory
        config_file = (
            "data/user_configs.json" if os.path.exists("data") else "user_configs.json"
        )
        with open(config_file) as f:
            configs = json.load(f)
            for user_id, config in configs.items():
                # Handle backwards compatibility for property_state -> property_states
                if "property_state" in config and "property_states" not in config:
                    config["property_states"] = [
                        PropertyState(config["property_state"])
                    ]
                    config.pop("property_state", None)  # Remove old field
                elif "property_states" in config:
                    config["property_states"] = [
                        PropertyState(state) for state in config["property_states"]
                    ]

                # Handle floor_types conversion if needed
                if "floor_types" in config:
                    config["floor_types"] = [
                        FloorType(floor_type) for floor_type in config["floor_types"]
                    ]

                # Handle backwards compatibility for furniture setting
                if "has_furniture" in config and "furniture_type" not in config:
                    config["furniture_type"] = (
                        FurnitureType.FURNISHED
                        if config["has_furniture"]
                        else FurnitureType.INDIFFERENT
                    )
                    config.pop("has_furniture", None)  # Remove old field
                elif "furniture_types" in config and "furniture_type" not in config:
                    # Convert from old list format to single value (take first item)
                    if config["furniture_types"]:
                        old_value = config["furniture_types"][0]
                        # Map old enum values to new ones
                        if old_value == "mobilado":
                            config["furniture_type"] = FurnitureType.FURNISHED
                        elif old_value == "mobilado-cozinha":
                            config["furniture_type"] = FurnitureType.KITCHEN_FURNITURE
                        elif old_value == "sem-mobilia":
                            config["furniture_type"] = (
                                FurnitureType.INDIFFERENT
                            )  # Unfurnished becomes "indifferent"
                        else:
                            config["furniture_type"] = FurnitureType.INDIFFERENT
                    else:
                        config["furniture_type"] = FurnitureType.INDIFFERENT
                    config.pop("furniture_types", None)  # Remove old field
                elif "furniture_type" in config:
                    # Handle old furniture_type values too
                    old_value = config["furniture_type"]
                    if old_value == "mobilado":
                        config["furniture_type"] = FurnitureType.FURNISHED
                    elif old_value == "mobilado-cozinha":
                        config["furniture_type"] = FurnitureType.KITCHEN_FURNITURE
                    elif old_value == "sem-mobilia":
                        config["furniture_type"] = FurnitureType.INDIFFERENT
                    else:
                        try:
                            config["furniture_type"] = FurnitureType(
                                config["furniture_type"]
                            )
                        except ValueError:
                            config["furniture_type"] = FurnitureType.INDIFFERENT

                # Remove any unknown fields that might cause errors
                valid_fields = {
                    "min_rooms",
                    "max_rooms",
                    "min_size",
                    "max_size",
                    "max_price",
                    "furniture_type",
                    "property_states",
                    "floor_types",
                    "city",
                    "custom_polygon",
                    "update_frequency",
                }
                config = {k: v for k, v in config.items() if k in valid_fields}

                user_configs[int(user_id)] = SearchConfig(**config)
                logger.info(f"Loaded config for user {user_id}: {config}")
    except FileNotFoundError:
        # Create empty config file if it doesn't exist
        logger.info("user_configs.json not found, will create on first save")
    except json.JSONDecodeError:
        logger.warning("Invalid JSON in user_configs.json, will recreate on next save")
    except (PermissionError, OSError) as e:
        logger.warning(f"Could not read config file: {e}")
        logger.info("Starting with empty configuration, will create on first save")


async def save_configs():
    """Save configurations to file with locking for multi-user safety"""
    async with config_lock:
        try:
            configs = {}
            for user_id, config in user_configs.items():
                config_dict = config.__dict__.copy()
                # Convert PropertyState list to string values
                config_dict["property_states"] = [
                    state.value for state in config_dict["property_states"]
                ]
                # Convert FurnitureType to string value
                config_dict["furniture_type"] = config_dict["furniture_type"].value
                # Convert FloorType list to string values
                config_dict["floor_types"] = [
                    floor_type.value for floor_type in config_dict["floor_types"]
                ]
                configs[str(user_id)] = config_dict

            # Use data directory if it exists, otherwise current directory
            config_file = (
                "data/user_configs.json"
                if os.path.exists("data")
                else "user_configs.json"
            )
            with open(config_file, "w") as f:
                json.dump(configs, f, indent=2)
            logger.info(f"Saved configurations for {len(configs)} users")
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
        stats_manager.record_user_activity(user_id, "first_use")
        logger.info(
            f"MULTI-USER: Created new config for user {user_id} (Total users: {len(user_configs)})"
        )
    else:
        stats_manager.record_user_activity(user_id, "bot_access")
        logger.info(
            f"MULTI-USER: Existing user {user_id} accessing bot (Total users: {len(user_configs)})"
        )

    reply_markup = InlineKeyboardMarkup(
        get_main_menu_keyboard(update.effective_user.id)
    )

    try:
        await update.message.reply_text(
            "Welcome to Idealista Monitor Bot! Please choose an option:",
            reply_markup=reply_markup,
        )
    except Exception as e:
        logger.error(f"Network error sending start message to user {user_id}: {e}")
        # Try to send a simpler message without keyboard
        try:
            await update.message.reply_text(
                "Welcome to Idealista Monitor Bot! There seems to be a network issue. Please try again in a moment."
            )
        except Exception as e2:
            logger.error(f"Failed to send any message to user {user_id}: {e2}")
            # Still return CHOOSING so the conversation handler continues
            pass
    logger.info(f"START: Returning CHOOSING state ({CHOOSING})")
    return CHOOSING


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle button presses"""
    query = update.callback_query
    await query.answer()

    logger.info(f"BUTTON: Handler called with data: {query.data}")
    logger.info(f"BUTTON: Context user_data: {context.user_data}")
    logger.info(f"BUTTON: User {update.effective_user.id}")

    if query.data == "show":
        user_id = update.effective_user.id
        if user_id not in user_configs:
            user_configs[user_id] = SearchConfig()
        config = user_configs[user_id]
        await query.message.reply_text(
            f"Current settings:\n"
            f"Minimum rooms: {config.min_rooms}+\n"
            f"Size: {config.min_size}-{config.max_size}m²\n"
            f"Max Price: {config.max_price}€\n"
            f"Furniture: {config.furniture_type.name.replace('_', ' ').title()}\n"
            f"State: {', '.join([state.name.replace('_', ' ').title() for state in config.property_states])}\n"
            f"Floor: {', '.join([floor.name.replace('_', ' ').title() for floor in config.floor_types]) if config.floor_types else 'Any'}\n"
            f"{'Custom Area: Set' if config.custom_polygon else f'City: {config.city}'}\n"
            f"Update Frequency: {config.update_frequency} minutes\n"
            f"Pages per search: {config.max_pages} (~{config.max_pages * 30} listings)"
        )
        return CHOOSING

    # Handle back button
    if query.data == "back":
        logger.info("Back button pressed, returning to main menu")

        # Show main menu
        reply_markup = InlineKeyboardMarkup(
            get_main_menu_keyboard(update.effective_user.id)
        )

        await query.edit_message_text(
            "Please choose an option:", reply_markup=reply_markup
        )
        logger.info("Returning to CHOOSING state")
        return CHOOSING

    # Handle main menu options
    if query.data == "rooms":
        return await set_rooms(update, context)
    elif query.data == "size":
        return await set_size(update, context)
    elif query.data == "price":
        logger.info("Price button pressed, transitioning to set_price")
        return await set_price(update, context)
    elif query.data == "furniture":
        return await set_furniture(update, context)
    elif query.data == "state":
        return await set_state(update, context)
    elif query.data == "floor":
        return await set_floor(update, context)
    elif query.data == "city":
        return await set_city(update, context)
    elif query.data == "frequency":
        return await set_frequency(update, context)
    elif query.data == "pagination":
        return await set_pagination(update, context)
    elif query.data == "polygon":
        return await set_polygon(update, context)
    elif query.data == "start_monitoring":
        return await start_monitoring(update, context)
    elif query.data == "stop_monitoring":
        return await stop_monitoring(update, context)
    elif query.data == "reset_settings":
        return await reset_settings(update, context)
    elif query.data == "stats":
        return await show_stats(update, context)
    elif query.data == "check_status":
        return await check_monitoring_status(update, context)
    elif query.data == "test_search":
        return await test_search_now(update, context)

    # Handle setting values
    if query.data.startswith("rooms_"):
        _, min_rooms = query.data.split("_")
        user_id = update.effective_user.id
        if user_id not in user_configs:
            user_configs[user_id] = SearchConfig()
        config = user_configs[user_id]
        config.min_rooms = int(min_rooms)
        config.max_rooms = 10  # Set a high maximum to include all rooms above minimum
        await save_configs()
        await query.message.edit_text(f"Minimum rooms set to {min_rooms}+!")

        # Show main menu
        reply_markup = InlineKeyboardMarkup(
            get_main_menu_keyboard(update.effective_user.id)
        )
        await query.message.edit_text(
            "Welcome to Idealista Monitor Bot! Please choose an option:",
            reply_markup=reply_markup,
        )
        return CHOOSING

    elif query.data.startswith("size_"):
        _, min_size = query.data.split("_")
        user_id = update.effective_user.id
        if user_id not in user_configs:
            user_configs[user_id] = SearchConfig()
        config = user_configs[user_id]
        config.min_size = int(min_size)
        config.max_size = 200  # Set a high maximum to include all sizes above minimum
        await save_configs()
        await query.message.edit_text(f"Minimum size set to {min_size}m²+!")

        # Show main menu
        reply_markup = InlineKeyboardMarkup(
            get_main_menu_keyboard(update.effective_user.id)
        )
        await query.message.edit_text(
            "Welcome to Idealista Monitor Bot! Please choose an option:",
            reply_markup=reply_markup,
        )
        return CHOOSING

    elif query.data.startswith("price_"):
        _, max_price = query.data.split("_")
        user_id = update.effective_user.id
        if user_id not in user_configs:
            user_configs[user_id] = SearchConfig()
        config = user_configs[user_id]
        config.max_price = int(max_price)
        await save_configs()
        await query.message.edit_text("Maximum price updated!")

        # Show main menu
        reply_markup = InlineKeyboardMarkup(
            get_main_menu_keyboard(update.effective_user.id)
        )
        await query.message.edit_text(
            "Welcome to Idealista Monitor Bot! Please choose an option:",
            reply_markup=reply_markup,
        )
        return CHOOSING

    elif query.data.startswith("furniture_toggle_"):
        _, _, furniture_type = query.data.split("_")
        user_id = update.effective_user.id

        # Ensure user config exists
        if user_id not in user_configs:
            user_configs[user_id] = SearchConfig()

        config = user_configs[user_id]

        # Set the furniture type (single choice now)
        if furniture_type == "furnished":
            target_furniture = FurnitureType.FURNISHED
        elif furniture_type == "kitchen":
            target_furniture = FurnitureType.KITCHEN_FURNITURE
        elif furniture_type == "indifferent":
            target_furniture = FurnitureType.INDIFFERENT
        else:
            return SETTING_FURNITURE

        # Set the single furniture type
        config.furniture_type = target_furniture

        await save_configs()

        # Debug: Log the current furniture selection
        logger.info(
            f"Furniture type updated for user {user_id}: {config.furniture_type.name}"
        )

        # Manually refresh the keyboard to show updated radio buttons (single choice)
        keyboard = []

        # Furnished
        is_furnished_selected = config.furniture_type == FurnitureType.FURNISHED
        furnished_text = "🔘 Furnished" if is_furnished_selected else "⚪ Furnished"
        keyboard.append(
            [
                InlineKeyboardButton(
                    furnished_text, callback_data="furniture_toggle_furnished"
                )
            ]
        )

        # Kitchen Furniture Only
        is_kitchen_selected = config.furniture_type == FurnitureType.KITCHEN_FURNITURE
        kitchen_text = (
            "🔘 Kitchen Furniture Only"
            if is_kitchen_selected
            else "⚪ Kitchen Furniture Only"
        )
        keyboard.append(
            [
                InlineKeyboardButton(
                    kitchen_text, callback_data="furniture_toggle_kitchen"
                )
            ]
        )

        # Indifferent
        is_indifferent_selected = config.furniture_type == FurnitureType.INDIFFERENT
        indifferent_text = (
            "🔘 Indifferent" if is_indifferent_selected else "⚪ Indifferent"
        )
        keyboard.append(
            [
                InlineKeyboardButton(
                    indifferent_text, callback_data="furniture_toggle_indifferent"
                )
            ]
        )

        keyboard.append([InlineKeyboardButton("Back", callback_data="back")])

        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            "Select furniture preference (single choice):", reply_markup=reply_markup
        )
        return SETTING_FURNITURE

    elif query.data.startswith("state_toggle_"):
        _, _, state = query.data.split("_")
        user_id = update.effective_user.id

        # Ensure user config exists
        if user_id not in user_configs:
            user_configs[user_id] = SearchConfig()

        config = user_configs[user_id]

        # Toggle the state in the list
        if state == "good":
            target_state = PropertyState.GOOD
        elif state == "remodel":
            target_state = PropertyState.NEEDS_REMODELING
        elif state == "new":
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

        await save_configs()

        # Debug: Log the current state selection
        logger.info(
            f"Property states updated for user {user_id}: {[state.name for state in config.property_states]}"
        )

        # Manually refresh the keyboard without calling set_state to avoid recursion
        keyboard = []

        # Good Condition
        is_good_selected = PropertyState.GOOD in config.property_states
        good_text = "✅ Good Condition" if is_good_selected else "☐ Good Condition"
        keyboard.append(
            [InlineKeyboardButton(good_text, callback_data="state_toggle_good")]
        )

        # Needs Remodeling
        is_remodel_selected = PropertyState.NEEDS_REMODELING in config.property_states
        remodel_text = (
            "✅ Needs Remodeling" if is_remodel_selected else "☐ Needs Remodeling"
        )
        keyboard.append(
            [InlineKeyboardButton(remodel_text, callback_data="state_toggle_remodel")]
        )

        # New
        is_new_selected = PropertyState.NEW in config.property_states
        new_text = "✅ New" if is_new_selected else "☐ New"
        keyboard.append(
            [InlineKeyboardButton(new_text, callback_data="state_toggle_new")]
        )

        keyboard.append([InlineKeyboardButton("Back", callback_data="back")])

        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            "Select property states (you can select multiple):",
            reply_markup=reply_markup,
        )
        return SETTING_STATE

    elif query.data.startswith("floor_toggle_"):
        _, _, floor = query.data.split("_")
        user_id = update.effective_user.id

        # Ensure user config exists
        if user_id not in user_configs:
            user_configs[user_id] = SearchConfig()

        config = user_configs[user_id]

        # Toggle the floor type in the list
        if floor == "last":
            target_floor = FloorType.LAST_FLOOR
        elif floor == "middle":
            target_floor = FloorType.MIDDLE_FLOORS
        elif floor == "ground":
            target_floor = FloorType.GROUND_FLOOR
        else:
            return SETTING_FLOOR

        if target_floor in config.floor_types:
            # Remove if already selected
            config.floor_types.remove(target_floor)
        else:
            # Add if not selected
            config.floor_types.append(target_floor)

        await save_configs()

        # Debug: Log the current floor selection
        logger.info(
            f"Floor types updated for user {user_id}: {[floor.name for floor in config.floor_types]}"
        )

        # Manually refresh the keyboard to show updated checkboxes
        keyboard = []

        # Last Floor
        is_last_selected = FloorType.LAST_FLOOR in config.floor_types
        last_text = "✅ Last Floor" if is_last_selected else "☐ Last Floor"
        keyboard.append(
            [InlineKeyboardButton(last_text, callback_data="floor_toggle_last")]
        )

        # Middle Floors
        is_middle_selected = FloorType.MIDDLE_FLOORS in config.floor_types
        middle_text = "✅ Middle Floors" if is_middle_selected else "☐ Middle Floors"
        keyboard.append(
            [InlineKeyboardButton(middle_text, callback_data="floor_toggle_middle")]
        )

        # Ground Floor
        is_ground_selected = FloorType.GROUND_FLOOR in config.floor_types
        ground_text = "✅ Ground Floor" if is_ground_selected else "☐ Ground Floor"
        keyboard.append(
            [InlineKeyboardButton(ground_text, callback_data="floor_toggle_ground")]
        )

        keyboard.append([InlineKeyboardButton("Back", callback_data="back")])

        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            "Select floor preferences (you can select multiple, or none for no filtering):",
            reply_markup=reply_markup,
        )
        return SETTING_FLOOR

    elif query.data.startswith("city_"):
        _, city = query.data.split("_")
        user_id = update.effective_user.id
        if user_id not in user_configs:
            user_configs[user_id] = SearchConfig()
        config = user_configs[user_id]
        config.city = city
        await save_configs()
        await query.message.edit_text("City updated!")

        # Show main menu
        reply_markup = InlineKeyboardMarkup(
            get_main_menu_keyboard(update.effective_user.id)
        )
        await query.message.edit_text(
            "Welcome to Idealista Monitor Bot! Please choose an option:",
            reply_markup=reply_markup,
        )
        return CHOOSING

    elif query.data.startswith("freq_"):
        _, minutes = query.data.split("_")
        user_id = update.effective_user.id
        if user_id not in user_configs:
            user_configs[user_id] = SearchConfig()
        config = user_configs[user_id]
        config.update_frequency = int(minutes)
        await save_configs()
        await query.message.edit_text("Update frequency updated!")

        # Show main menu
        reply_markup = InlineKeyboardMarkup(
            get_main_menu_keyboard(update.effective_user.id)
        )
        await query.message.edit_text(
            "Welcome to Idealista Monitor Bot! Please choose an option:",
            reply_markup=reply_markup,
        )
        return CHOOSING

    elif query.data.startswith("pages_"):
        _, max_pages = query.data.split("_")
        user_id = update.effective_user.id
        if user_id not in user_configs:
            user_configs[user_id] = SearchConfig()
        config = user_configs[user_id]
        config.max_pages = int(max_pages)
        await save_configs()

        # Show confirmation with appropriate warning
        if int(max_pages) >= 4:
            warning = "\n⚠️ High page count increases IP blocking risk!"
        else:
            warning = ""

        await query.message.edit_text(
            f"Pagination set to {max_pages} pages (~{int(max_pages) * 30} listings)!{warning}"
        )

        # Show main menu
        reply_markup = InlineKeyboardMarkup(
            get_main_menu_keyboard(update.effective_user.id)
        )
        await query.message.edit_text(
            "Welcome to Idealista Monitor Bot! Please choose an option:",
            reply_markup=reply_markup,
        )
        return CHOOSING

    elif query.data == "polygon_clear":
        user_id = update.effective_user.id
        if user_id not in user_configs:
            user_configs[user_id] = SearchConfig()
        config = user_configs[user_id]
        config.custom_polygon = None
        await save_configs()
        await query.message.edit_text("Custom area cleared!")

        # Show main menu
        reply_markup = InlineKeyboardMarkup(
            get_main_menu_keyboard(update.effective_user.id)
        )
        await query.message.edit_text(
            "Welcome to Idealista Monitor Bot! Please choose an option:",
            reply_markup=reply_markup,
        )
        return CHOOSING

    return CHOOSING


async def handle_price_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the user's price input"""
    user_input = update.message.text.strip()
    logger.info(
        f"HANDLE_PRICE_INPUT: Received price input: '{user_input}' from user {update.effective_user.id}"
    )
    logger.info(f"HANDLE_PRICE_INPUT: Current user_data: {context.user_data}")
    logger.info("HANDLE_PRICE_INPUT: In conversation handler")

    try:
        # Remove any non-digit characters except for spaces and common separators
        cleaned_input = "".join(c for c in user_input if c.isdigit())
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
        await save_configs()
        logger.info(
            f"Successfully updated price to {price}€ for user {update.effective_user.id}"
        )

        reply_markup = InlineKeyboardMarkup(
            get_main_menu_keyboard(update.effective_user.id)
        )
        await update.message.reply_text(
            f"Maximum price set to {price}€!", reply_markup=reply_markup
        )
        return CHOOSING

    except ValueError as e:
        logger.error(f"Error processing price input '{user_input}': {e!s}")
        keyboard = [[InlineKeyboardButton("Back", callback_data="back")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "Please enter a valid positive number for the price (e.g., 1200):",
            reply_markup=reply_markup,
        )
        return WAITING_FOR_PRICE


async def handle_polygon_input(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Handle the user's polygon URL input"""
    user_input = update.message.text.strip()
    logger.info(
        f"HANDLE_POLYGON_INPUT: Received URL input: '{user_input}' from user {update.effective_user.id}"
    )

    try:
        # Basic URL validation
        if not user_input.startswith(("http://", "https://")):
            raise ValueError("Invalid URL format")

        if "idealista.pt" not in user_input:
            raise ValueError("URL must be from idealista.pt")

        if "shape=" not in user_input:
            raise ValueError("URL must contain 'shape=' parameter")

        # Extract the shape parameter
        import urllib.parse

        parsed_url = urllib.parse.urlparse(user_input)
        query_params = urllib.parse.parse_qs(parsed_url.query)

        if "shape" not in query_params:
            raise ValueError("No 'shape' parameter found in URL")

        shape_value = query_params["shape"][0]
        logger.info(f"Extracted shape parameter: {shape_value}")

        user_id = update.effective_user.id
        if user_id not in user_configs:
            user_configs[user_id] = SearchConfig()

        config = user_configs[user_id]
        config.custom_polygon = shape_value
        await save_configs()
        logger.info(
            f"Successfully updated custom polygon for user {update.effective_user.id}"
        )

        reply_markup = InlineKeyboardMarkup(
            get_main_menu_keyboard(update.effective_user.id)
        )
        await update.message.reply_text(
            "✅ Custom area set successfully! The bot will now search within your defined polygon.",
            reply_markup=reply_markup,
        )
        return CHOOSING

    except ValueError as e:
        logger.error(f"Error processing polygon URL '{user_input}': {e!s}")
        keyboard = [[InlineKeyboardButton("Back", callback_data="back")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            f"❌ Error: {e!s}\n\nPlease make sure you're copying the full URL from idealista.pt after drawing your custom area on the map.",
            reply_markup=reply_markup,
        )
        return WAITING_FOR_POLYGON_URL


async def user_monitoring_task(user_id: int, chat_id: int):
    """Background monitoring task for a specific user"""
    scraper = IdealistaScraper()
    await scraper.initialize()

    logger.info(f"MONITORING STARTED: User {user_id} monitoring task is now running")

    try:
        while True:
            if user_id not in user_configs:
                logger.warning(
                    f"User {user_id} no longer has config, stopping monitoring"
                )
                break

            config = user_configs[user_id]
            logger.info(
                f"MONITORING CYCLE: Starting scrape for user {user_id} (frequency: {config.update_frequency} minutes)"
            )

            # Debug: Log the URL being used
            search_url = config.get_base_url()
            logger.info(f"Generated search URL for user {user_id}: {search_url}")

            try:
                results = await scraper.scrape_listings(
                    config, str(chat_id), max_pages=config.max_pages
                )
                if results is None or len(results) == 0:
                    logger.info(f"No new listings found for user {user_id} this cycle")
                else:
                    logger.info(f"Found {len(results)} new listings for user {user_id}")
            except Exception as e:
                logger.error(f"Error during scraping for user {user_id}: {e}")

                # For rate limit errors, don't notify user - just log and continue
                if "403" in str(e) or "rate limit" in str(e).lower():
                    logger.warning(
                        f"Rate limit encountered for user {user_id} - will retry next cycle with longer delays"
                    )
                else:
                    # For other errors, notify user
                    try:
                        from telegram import Bot

                        bot = Bot(token=os.getenv("TELEGRAM_BOT_TOKEN"))
                        await bot.send_message(
                            chat_id=chat_id,
                            text=f"⚠️ Monitoring error: {e!s}\n\nWill retry in {config.update_frequency} minutes.",
                        )
                    except Exception as send_error:
                        logger.error(
                            f"Failed to send error message to user {user_id}: {send_error}"
                        )
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
        reply_markup = InlineKeyboardMarkup(
            get_main_menu_keyboard(update.effective_user.id)
        )
        await query.message.edit_text(
            "Welcome to Idealista Monitor Bot! Please choose an option:",
            reply_markup=reply_markup,
        )
        return CHOOSING

    # Debug: Test URL generation before starting monitoring
    config = user_configs[user_id]
    test_url = config.get_base_url()
    logger.info(f"DEBUG: Generated URL for user {user_id}: {test_url}")

    # Start monitoring task with error handling
    try:
        task = asyncio.create_task(user_monitoring_task(user_id, chat_id))
        monitoring_tasks[user_id] = task

        # Add callback to log if task fails
        def task_done_callback(task):
            try:
                exception = task.exception()
                if exception is not None:
                    logger.error(
                        f"Monitoring task for user {user_id} failed: {type(exception).__name__}: {exception!s}"
                    )
                else:
                    logger.info(
                        f"Monitoring task for user {user_id} completed normally"
                    )
            except Exception as callback_error:
                logger.error(
                    f"Error in task_done_callback for user {user_id}: {callback_error}"
                )

        task.add_done_callback(task_done_callback)

        stats_manager.record_user_activity(user_id, "search_start")
        active_users = len(
            [task for task in monitoring_tasks.values() if not task.done()]
        )
        logger.info(
            f"MULTI-USER: User {user_id} started monitoring (Active monitoring tasks: {active_users})"
        )
        logger.info(
            f"DEBUG: Monitoring task created for user {user_id}, task ID: {id(task)}"
        )

        # Give the task a moment to start
        await asyncio.sleep(0.1)

        if task.done():
            logger.error(
                f"ERROR: Monitoring task for user {user_id} failed immediately!"
            )
            exception = task.exception()
            if exception and isinstance(exception, BaseException):
                raise exception
            elif exception is not None:
                raise Exception(f"Monitoring task failed: {exception}")
        else:
            logger.info(
                f"SUCCESS: Monitoring task for user {user_id} is running properly"
            )

    except Exception as e:
        logger.error(f"Failed to start monitoring for user {user_id}: {e}")
        # Remove failed task from monitoring_tasks
        monitoring_tasks.pop(user_id, None)
        raise

    # Show success message with menu
    reply_markup = InlineKeyboardMarkup(
        get_main_menu_keyboard(update.effective_user.id)
    )
    await query.message.edit_text(
        f"🚀 Monitoring started! You'll receive notifications when new listings match your criteria.\n\n🔍 Search URL: {test_url}\n\nNext check in {config.update_frequency} minutes.",
        reply_markup=reply_markup,
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
    reply_markup = InlineKeyboardMarkup(
        get_main_menu_keyboard(update.effective_user.id)
    )
    await query.message.edit_text(
        "Welcome to Idealista Monitor Bot! Please choose an option:",
        reply_markup=reply_markup,
    )
    return CHOOSING


async def reset_settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Reset all settings to default values"""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id

    # Reset to default configuration
    user_configs[user_id] = SearchConfig()
    await save_configs()

    logger.info(f"Settings reset to defaults for user {user_id}")

    await query.message.edit_text("🔄 All settings have been reset to default values!")

    # Show main menu
    reply_markup = InlineKeyboardMarkup(
        get_main_menu_keyboard(update.effective_user.id)
    )
    await query.message.edit_text(
        "Welcome to Idealista Monitor Bot! Please choose an option:",
        reply_markup=reply_markup,
    )
    return CHOOSING


async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show bot usage statistics"""
    query = update.callback_query
    await query.answer()

    # Get statistics
    stats_summary = stats_manager.get_user_summary()
    active_users = len([task for task in monitoring_tasks.values() if not task.done()])

    # Get rate limiting info
    from scraper import global_rate_limiter

    recent_errors = global_rate_limiter.recent_errors
    last_error_time = global_rate_limiter.last_error_time
    current_delay = global_rate_limiter.min_delay_seconds

    rate_status = (
        "🟢 Normal"
        if recent_errors == 0
        else f"🟡 Elevated ({recent_errors} recent errors)"
    )

    message = f"""{stats_summary}
🔄 Currently Active Users: {active_users}

🚦 **Rate Limiting Status**: {rate_status}
⏱️ Current Delay: {current_delay}s between requests
📊 Recent Errors: {recent_errors}

💡 This bot uses adaptive rate limiting to avoid being blocked by Idealista!"""

    # Show stats with back button
    reply_markup = InlineKeyboardMarkup(
        [[InlineKeyboardButton("🔙 Back to Menu", callback_data="back")]]
    )

    await query.message.edit_text(
        message, reply_markup=reply_markup, parse_mode="Markdown"
    )
    return CHOOSING


async def check_monitoring_status(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Check detailed monitoring status for the user"""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id

    # Check if user has configuration
    if user_id not in user_configs:
        message = (
            "❌ No configuration found. Please set up your search preferences first."
        )
    else:
        config = user_configs[user_id]

        # Check monitoring status
        is_monitoring = (
            user_id in monitoring_tasks and not monitoring_tasks[user_id].done()
        )

        if is_monitoring:
            task = monitoring_tasks[user_id]
            status = "🟢 Active"
            next_check = f"Next check in ≤{config.update_frequency} minutes"
        else:
            status = "🔴 Not Running"
            next_check = "Click 'Start searching' to begin monitoring"

        # Get rate limiting info
        from scraper import global_rate_limiter

        rate_errors = global_rate_limiter.recent_errors
        delay_seconds = global_rate_limiter.min_delay_seconds
        if rate_errors == 0:
            rate_status = f"🟢 Normal ({delay_seconds}s between requests)"
        else:
            rate_status = (
                f"🟡 {rate_errors} recent errors ({delay_seconds}s between requests)"
            )

        # Generate current search URL
        search_url = config.get_base_url()

        message = f"""🔍 **Monitoring Status for User {user_id}**

🔄 **Status**: {status}
⏰ **Next Check**: {next_check}
🚦 **Rate Limiting**: {rate_status}

⚙️ **Current Settings**:
💰 Max Price: {config.max_price}€
🛏️ Rooms: {config.min_rooms}-{config.max_rooms}
📐 Size: {config.min_size}-{config.max_size}m²
🏢 City: {config.city}
🔄 Frequency: {config.update_frequency} minutes

🔗 **Search URL**: {search_url[:100]}...

📊 **Debug Info**:
Total monitoring tasks: {len(monitoring_tasks)}
Active tasks: {len([t for t in monitoring_tasks.values() if not t.done()])}"""

    # Show status with back button and test option
    buttons = [[InlineKeyboardButton("🔙 Back to Menu", callback_data="back")]]
    if user_id in user_configs:
        buttons.insert(
            0, [InlineKeyboardButton("🧪 Test Search Now", callback_data="test_search")]
        )
    reply_markup = InlineKeyboardMarkup(buttons)

    await query.message.edit_text(
        message, reply_markup=reply_markup, parse_mode="Markdown"
    )
    return CHOOSING


async def test_search_now(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Test search functionality immediately for debugging"""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    if user_id not in user_configs:
        await query.message.edit_text(
            "❌ No configuration found. Please set up your search preferences first."
        )
        return CHOOSING

    config = user_configs[user_id]

    await query.message.edit_text(
        "🧪 **Test Search Started**\n\nSearching for listings now... This may take 1-2 minutes due to rate limiting."
    )

    try:
        # Initialize scraper and run test search
        scraper = IdealistaScraper()
        await scraper.initialize()

        logger.info(f"TEST SEARCH: Manual test search initiated by user {user_id}")

        results = await scraper.scrape_listings(
            config, str(chat_id), max_pages=3, force_all_pages=True
        )

        if results is None:
            message = "❌ **Test Failed**: Could not fetch data from Idealista (rate limiting or network error)"
        elif len(results) == 0:
            message = "✅ **Test Successful**: No new listings found matching your criteria (this is normal if you've seen all current listings)"
        else:
            message = f"✅ **Test Successful**: Found {len(results)} new listings! Check your chat for notifications."

        # Add technical details
        search_url = config.get_base_url()
        message += f"\n\n🔗 **Search URL**: {search_url[:100]}...\n\n💡 **Note**: If monitoring is active, this same search runs automatically every {config.update_frequency} minutes."

    except Exception as e:
        logger.error(f"TEST SEARCH ERROR for user {user_id}: {e}")
        message = f"❌ **Test Failed**: {e!s}\n\nThis helps debug the issue. Check with the bot administrator."

    # Show result with back button
    reply_markup = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🔙 Back to Status", callback_data="check_status")],
            [InlineKeyboardButton("🏠 Main Menu", callback_data="back")],
        ]
    )

    await query.message.edit_text(
        message, reply_markup=reply_markup, parse_mode="Markdown"
    )
    return CHOOSING


def main():
    """Start the bot"""
    # Load saved configurations
    load_configs()

    # Check if token exists
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN not found in environment variables")
        return

    logger.info("Starting bot with token...")

    # Create the Application
    application = Application.builder().token(token).build()

    # Add conversation handler with explicit configuration
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CHOOSING: [CallbackQueryHandler(button_handler)],
            SETTING_ROOMS: [CallbackQueryHandler(button_handler)],
            SETTING_SIZE: [CallbackQueryHandler(button_handler)],
            SETTING_FURNITURE: [CallbackQueryHandler(button_handler)],
            SETTING_STATE: [CallbackQueryHandler(button_handler)],
            SETTING_FLOOR: [CallbackQueryHandler(button_handler)],
            SETTING_CITY: [CallbackQueryHandler(button_handler)],
            SETTING_FREQUENCY: [CallbackQueryHandler(button_handler)],
            SETTING_PAGES: [CallbackQueryHandler(button_handler)],
            WAITING_FOR_PRICE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_price_input),
                CallbackQueryHandler(button_handler),
            ],
            WAITING_FOR_POLYGON_URL: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_polygon_input),
                CallbackQueryHandler(button_handler),
            ],
        },
        fallbacks=[CommandHandler("start", start)],
        per_chat=True,
        per_user=True,
        per_message=False,
        allow_reentry=True,
        name="idealista_conv",
    )

    # Add debug logging for conversation handler
    logger.info("Setting up conversation handler with states:")
    for state, handlers in conv_handler.states.items():
        logger.info(f"State {state}: {[type(h).__name__ for h in handlers]}")

    # Add debug handler to catch ALL messages before conversation handler
    async def debug_all_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.message and update.message.text:
            chat_type = "private" if update.effective_chat.id > 0 else "group"
            logger.info(
                f"DEBUG_ALL: Message '{update.message.text}' from user {update.effective_user.id}"
            )
            logger.info(
                f"DEBUG_ALL: Chat ID: {update.effective_chat.id} (TYPE: {chat_type})"
            )
            logger.info(f"DEBUG_ALL: User_data: {context.user_data}")
            logger.info(f"DEBUG_ALL: Chat_data: {context.chat_data}")
            # Check if this is in a conversation
            conv_key = (update.effective_chat.id, update.effective_user.id)
            logger.info(f"DEBUG_ALL: Conversation key would be: {conv_key}")
            logger.info("DEBUG_ALL: Message will be processed by conversation handler")

    # Add this BEFORE conversation handler
    application.add_handler(MessageHandler(filters.ALL, debug_all_messages), group=-1)

    application.add_handler(conv_handler)

    # Add a simple test handler to debug
    async def test_handler(update: Update, _: ContextTypes.DEFAULT_TYPE):
        logger.info(f"Test command received from user {update.effective_user.id}")
        await update.message.reply_text("Test command works!")

    application.add_handler(CommandHandler("test", test_handler))

    # Start the Bot
    logger.info("Starting polling...")
    application.run_polling()


if __name__ == "__main__":
    main()
