from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ConversationHandler, MessageHandler, filters
from models import SearchConfig, PropertyState
import json
import os
from typing import Dict
import logging
from dotenv import load_dotenv
from filters import MAIN_MENU_KEYBOARD, set_rooms, set_size, set_price, set_furniture, set_state, set_city, set_frequency
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
CHOOSING, SETTING_ROOMS, SETTING_SIZE, SETTING_PRICE, SETTING_FURNITURE, SETTING_STATE, SETTING_CITY, SETTING_POLYGON, SETTING_FREQUENCY, WAITING_FOR_PRICE = range(10)

# Store user configurations
user_configs: Dict[int, SearchConfig] = {}

def load_configs():
    """Load saved configurations from file"""
    try:
        with open('user_configs.json', 'r') as f:
            configs = json.load(f)
            for user_id, config in configs.items():
                # Convert string value back to PropertyState enum
                if 'property_state' in config:
                    config['property_state'] = PropertyState(config['property_state'])
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
            # Convert PropertyState enum to string value
            config_dict['property_state'] = config_dict['property_state'].value
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
    
    reply_markup = InlineKeyboardMarkup(MAIN_MENU_KEYBOARD)
    
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
        config = user_configs[update.effective_user.id]
        await query.message.reply_text(
            f"Current settings:\n"
            f"Minimum rooms: {config.min_rooms}+\n"
            f"Size: {config.min_size}-{config.max_size}m²\n"
            f"Max Price: {config.max_price}€\n"
            f"Furniture: {'Yes' if config.has_furniture else 'No'}\n"
            f"State: {config.property_state.name}\n"
            f"City: {config.city}\n"
            f"Update Frequency: {config.update_frequency} minutes"
        )
        return CHOOSING
    
    # Handle back button
    if query.data == 'back':
        logger.info("Back button pressed, returning to main menu")
        
        # Show main menu
        reply_markup = InlineKeyboardMarkup(MAIN_MENU_KEYBOARD)
        
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
    
    # Handle setting values
    if query.data.startswith('rooms_'):
        _, min_rooms = query.data.split('_')
        config = user_configs[update.effective_user.id]
        config.min_rooms = int(min_rooms)
        config.max_rooms = 10  # Set a high maximum to include all rooms above minimum
        save_configs()
        await query.message.edit_text(f"Minimum rooms set to {min_rooms}+!")
        
        # Show main menu
        reply_markup = InlineKeyboardMarkup(MAIN_MENU_KEYBOARD)
        await query.message.edit_text(
            "Welcome to Idealista Monitor Bot! Please choose an option:",
            reply_markup=reply_markup
        )
        return CHOOSING
    
    elif query.data.startswith('size_'):
        _, min_size = query.data.split('_')
        config = user_configs[update.effective_user.id]
        config.min_size = int(min_size)
        config.max_size = 200  # Set a high maximum to include all sizes above minimum
        save_configs()
        await query.message.edit_text(f"Minimum size set to {min_size}m²+!")
        
        # Show main menu
        reply_markup = InlineKeyboardMarkup(MAIN_MENU_KEYBOARD)
        await query.message.edit_text(
            "Welcome to Idealista Monitor Bot! Please choose an option:",
            reply_markup=reply_markup
        )
        return CHOOSING
    
    elif query.data.startswith('price_'):
        _, max_price = query.data.split('_')
        config = user_configs[update.effective_user.id]
        config.max_price = int(max_price)
        save_configs()
        await query.message.edit_text("Maximum price updated!")
        
        # Show main menu
        reply_markup = InlineKeyboardMarkup(MAIN_MENU_KEYBOARD)
        await query.message.edit_text(
            "Welcome to Idealista Monitor Bot! Please choose an option:",
            reply_markup=reply_markup
        )
        return CHOOSING
    
    elif query.data.startswith('furniture_'):
        _, has_furniture = query.data.split('_')
        config = user_configs[update.effective_user.id]
        config.has_furniture = has_furniture == 'true'
        save_configs()
        await query.message.edit_text("Furniture preference updated!")
        
        # Show main menu
        reply_markup = InlineKeyboardMarkup(MAIN_MENU_KEYBOARD)
        await query.message.edit_text(
            "Welcome to Idealista Monitor Bot! Please choose an option:",
            reply_markup=reply_markup
        )
        return CHOOSING
    
    elif query.data.startswith('state_'):
        _, state = query.data.split('_')
        config = user_configs[update.effective_user.id]
        if state == 'good':
            config.property_state = PropertyState.GOOD
        elif state == 'remodel':
            config.property_state = PropertyState.NEEDS_REMODELING
        elif state == 'new':
            config.property_state = PropertyState.NEW
        save_configs()
        await query.message.edit_text("Property state updated!")
        
        # Show main menu
        reply_markup = InlineKeyboardMarkup(MAIN_MENU_KEYBOARD)
        await query.message.edit_text(
            "Welcome to Idealista Monitor Bot! Please choose an option:",
            reply_markup=reply_markup
        )
        return CHOOSING
    
    elif query.data.startswith('city_'):
        _, city = query.data.split('_')
        config = user_configs[update.effective_user.id]
        config.city = city
        save_configs()
        await query.message.edit_text("City updated!")
        
        # Show main menu
        reply_markup = InlineKeyboardMarkup(MAIN_MENU_KEYBOARD)
        await query.message.edit_text(
            "Welcome to Idealista Monitor Bot! Please choose an option:",
            reply_markup=reply_markup
        )
        return CHOOSING
    
    elif query.data.startswith('freq_'):
        _, minutes = query.data.split('_')
        config = user_configs[update.effective_user.id]
        config.update_frequency = int(minutes)
        save_configs()
        await query.message.edit_text("Update frequency updated!")
        
        # Show main menu
        reply_markup = InlineKeyboardMarkup(MAIN_MENU_KEYBOARD)
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
        
        config = user_configs[update.effective_user.id]
        config.max_price = price
        save_configs()
        logger.info(f"Successfully updated price to {price}€ for user {update.effective_user.id}")
        
        reply_markup = InlineKeyboardMarkup(MAIN_MENU_KEYBOARD)
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
            WAITING_FOR_PRICE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_price_input),
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
    
    # Add debug handler AFTER conversation handler to catch unhandled messages  
    async def debug_unhandled_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.message and update.message.text:
            logger.info(f"DEBUG_UNHANDLED: Message '{update.message.text}' from user {update.effective_user.id}")
            logger.info(f"DEBUG_UNHANDLED: This message was NOT handled by conversation")
            await update.message.reply_text("Message received but not handled by conversation.")
    
    # Add this AFTER conversation handler
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, debug_unhandled_messages), group=1)
    
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