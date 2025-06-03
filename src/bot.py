from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, ConversationHandler
from models import SearchConfig, PropertyState
import json
import os
from typing import Dict
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Conversation states
CHOOSING, SETTING_ROOMS, SETTING_SIZE, SETTING_PRICE, SETTING_FURNITURE, SETTING_STATE, SETTING_CITY, SETTING_POLYGON, SETTING_FREQUENCY = range(9)

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
    user_id = update.effective_user.id
    if user_id not in user_configs:
        user_configs[user_id] = SearchConfig()
    
    keyboard = [
        [InlineKeyboardButton("Set Rooms", callback_data='rooms')],
        [InlineKeyboardButton("Set Size", callback_data='size')],
        [InlineKeyboardButton("Set Price", callback_data='price')],
        [InlineKeyboardButton("Set Furniture", callback_data='furniture')],
        [InlineKeyboardButton("Set Property State", callback_data='state')],
        [InlineKeyboardButton("Set City", callback_data='city')],
        [InlineKeyboardButton("Set Custom Area", callback_data='polygon')],
        [InlineKeyboardButton("Set Update Frequency", callback_data='frequency')],
        [InlineKeyboardButton("Show Current Settings", callback_data='show')],
        [InlineKeyboardButton("Start Monitoring", callback_data='start_monitoring')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "Welcome to Idealista Monitor Bot! Please choose an option:",
        reply_markup=reply_markup
    )
    return CHOOSING

async def set_rooms(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle room number setting"""
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("1+ rooms", callback_data='rooms_1')],
        [InlineKeyboardButton("2+ rooms", callback_data='rooms_2')],
        [InlineKeyboardButton("3+ rooms", callback_data='rooms_3')],
        [InlineKeyboardButton("4+ rooms", callback_data='rooms_4')],
        [InlineKeyboardButton("5+ rooms", callback_data='rooms_5')],
        [InlineKeyboardButton("Back", callback_data='back')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.edit_text(
        "Select the minimum number of rooms you want:",
        reply_markup=reply_markup
    )
    return SETTING_ROOMS

async def set_size(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle size setting"""
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("30m²+", callback_data='size_30')],
        [InlineKeyboardButton("40m²+", callback_data='size_40')],
        [InlineKeyboardButton("50m²+", callback_data='size_50')],
        [InlineKeyboardButton("60m²+", callback_data='size_60')],
        [InlineKeyboardButton("70m²+", callback_data='size_70')],
        [InlineKeyboardButton("80m²+", callback_data='size_80')],
        [InlineKeyboardButton("90m²+", callback_data='size_90')],
        [InlineKeyboardButton("100m²+", callback_data='size_100')],
        [InlineKeyboardButton("110m²+", callback_data='size_110')],
        [InlineKeyboardButton("120m²+", callback_data='size_120')],
        [InlineKeyboardButton("130m²+", callback_data='size_130')],
        [InlineKeyboardButton("140m²+", callback_data='size_140')],
        [InlineKeyboardButton("150m²+", callback_data='size_150')],
        [InlineKeyboardButton("Back", callback_data='back')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.edit_text(
        "Select the minimum size you want:",
        reply_markup=reply_markup
    )
    return SETTING_SIZE

async def set_price(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle price setting"""
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("Up to 800€", callback_data='price_800')],
        [InlineKeyboardButton("Up to 1000€", callback_data='price_1000')],
        [InlineKeyboardButton("Up to 1200€", callback_data='price_1200')],
        [InlineKeyboardButton("Up to 1500€", callback_data='price_1500')],
        [InlineKeyboardButton("Up to 2000€", callback_data='price_2000')],
        [InlineKeyboardButton("Back", callback_data='back')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.edit_text(
        "Select the maximum price:",
        reply_markup=reply_markup
    )
    return SETTING_PRICE

async def set_furniture(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle furniture setting"""
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("Furnished", callback_data='furniture_true')],
        [InlineKeyboardButton("Unfurnished", callback_data='furniture_false')],
        [InlineKeyboardButton("Back", callback_data='back')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.edit_text(
        "Select furniture preference:",
        reply_markup=reply_markup
    )
    return SETTING_FURNITURE

async def set_state(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle property state setting"""
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("Good Condition", callback_data='state_good')],
        [InlineKeyboardButton("Needs Remodeling", callback_data='state_remodel')],
        [InlineKeyboardButton("New", callback_data='state_new')],
        [InlineKeyboardButton("Back", callback_data='back')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.edit_text(
        "Select property state:",
        reply_markup=reply_markup
    )
    return SETTING_STATE

async def set_city(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle city setting"""
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("Lisboa", callback_data='city_lisboa')],
        [InlineKeyboardButton("Porto", callback_data='city_porto')],
        [InlineKeyboardButton("Back", callback_data='back')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.edit_text(
        "Select city:",
        reply_markup=reply_markup
    )
    return SETTING_CITY

async def set_frequency(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle update frequency setting"""
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("Every 5 minutes", callback_data='freq_5')],
        [InlineKeyboardButton("Every 10 minutes", callback_data='freq_10')],
        [InlineKeyboardButton("Every 15 minutes", callback_data='freq_15')],
        [InlineKeyboardButton("Every 30 minutes", callback_data='freq_30')],
        [InlineKeyboardButton("Back", callback_data='back')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.edit_text(
        "Select update frequency:",
        reply_markup=reply_markup
    )
    return SETTING_FREQUENCY

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle button presses"""
    query = update.callback_query
    await query.answer()
    
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
        # Get current state from context
        current_state = context.user_data.get('current_state', CHOOSING)
        
        # If we're in a setting state, go back to filter menu
        if current_state in [SETTING_ROOMS, SETTING_SIZE, SETTING_PRICE, SETTING_FURNITURE, 
                           SETTING_STATE, SETTING_CITY, SETTING_POLYGON, SETTING_FREQUENCY]:
            # Show filter menu
            keyboard = [
                [InlineKeyboardButton("Set Rooms", callback_data='rooms')],
                [InlineKeyboardButton("Set Size", callback_data='size')],
                [InlineKeyboardButton("Set Price", callback_data='price')],
                [InlineKeyboardButton("Set Furniture", callback_data='furniture')],
                [InlineKeyboardButton("Set Property State", callback_data='state')],
                [InlineKeyboardButton("Set City", callback_data='city')],
                [InlineKeyboardButton("Set Custom Area", callback_data='polygon')],
                [InlineKeyboardButton("Set Update Frequency", callback_data='frequency')],
                [InlineKeyboardButton("Show Current Settings", callback_data='show')],
                [InlineKeyboardButton("Start Monitoring", callback_data='start_monitoring')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.message.edit_text(
                "Please choose an option:",
                reply_markup=reply_markup
            )
            context.user_data['current_state'] = CHOOSING
            return CHOOSING
        
        # If we're in main menu, stay there
        return CHOOSING
    
    # Handle main menu options
    if query.data == 'rooms':
        context.user_data['current_state'] = SETTING_ROOMS
        return await set_rooms(update, context)
    elif query.data == 'size':
        context.user_data['current_state'] = SETTING_SIZE
        return await set_size(update, context)
    elif query.data == 'price':
        context.user_data['current_state'] = SETTING_PRICE
        return await set_price(update, context)
    elif query.data == 'furniture':
        context.user_data['current_state'] = SETTING_FURNITURE
        return await set_furniture(update, context)
    elif query.data == 'state':
        context.user_data['current_state'] = SETTING_STATE
        return await set_state(update, context)
    elif query.data == 'city':
        context.user_data['current_state'] = SETTING_CITY
        return await set_city(update, context)
    elif query.data == 'frequency':
        context.user_data['current_state'] = SETTING_FREQUENCY
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
        keyboard = [
            [InlineKeyboardButton("Set Rooms", callback_data='rooms')],
            [InlineKeyboardButton("Set Size", callback_data='size')],
            [InlineKeyboardButton("Set Price", callback_data='price')],
            [InlineKeyboardButton("Set Furniture", callback_data='furniture')],
            [InlineKeyboardButton("Set Property State", callback_data='state')],
            [InlineKeyboardButton("Set City", callback_data='city')],
            [InlineKeyboardButton("Set Custom Area", callback_data='polygon')],
            [InlineKeyboardButton("Set Update Frequency", callback_data='frequency')],
            [InlineKeyboardButton("Show Current Settings", callback_data='show')],
            [InlineKeyboardButton("Start Monitoring", callback_data='start_monitoring')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
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
        keyboard = [
            [InlineKeyboardButton("Set Rooms", callback_data='rooms')],
            [InlineKeyboardButton("Set Size", callback_data='size')],
            [InlineKeyboardButton("Set Price", callback_data='price')],
            [InlineKeyboardButton("Set Furniture", callback_data='furniture')],
            [InlineKeyboardButton("Set Property State", callback_data='state')],
            [InlineKeyboardButton("Set City", callback_data='city')],
            [InlineKeyboardButton("Set Custom Area", callback_data='polygon')],
            [InlineKeyboardButton("Set Update Frequency", callback_data='frequency')],
            [InlineKeyboardButton("Show Current Settings", callback_data='show')],
            [InlineKeyboardButton("Start Monitoring", callback_data='start_monitoring')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
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
        keyboard = [
            [InlineKeyboardButton("Set Rooms", callback_data='rooms')],
            [InlineKeyboardButton("Set Size", callback_data='size')],
            [InlineKeyboardButton("Set Price", callback_data='price')],
            [InlineKeyboardButton("Set Furniture", callback_data='furniture')],
            [InlineKeyboardButton("Set Property State", callback_data='state')],
            [InlineKeyboardButton("Set City", callback_data='city')],
            [InlineKeyboardButton("Set Custom Area", callback_data='polygon')],
            [InlineKeyboardButton("Set Update Frequency", callback_data='frequency')],
            [InlineKeyboardButton("Show Current Settings", callback_data='show')],
            [InlineKeyboardButton("Start Monitoring", callback_data='start_monitoring')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
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
        keyboard = [
            [InlineKeyboardButton("Set Rooms", callback_data='rooms')],
            [InlineKeyboardButton("Set Size", callback_data='size')],
            [InlineKeyboardButton("Set Price", callback_data='price')],
            [InlineKeyboardButton("Set Furniture", callback_data='furniture')],
            [InlineKeyboardButton("Set Property State", callback_data='state')],
            [InlineKeyboardButton("Set City", callback_data='city')],
            [InlineKeyboardButton("Set Custom Area", callback_data='polygon')],
            [InlineKeyboardButton("Set Update Frequency", callback_data='frequency')],
            [InlineKeyboardButton("Show Current Settings", callback_data='show')],
            [InlineKeyboardButton("Start Monitoring", callback_data='start_monitoring')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
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
        keyboard = [
            [InlineKeyboardButton("Set Rooms", callback_data='rooms')],
            [InlineKeyboardButton("Set Size", callback_data='size')],
            [InlineKeyboardButton("Set Price", callback_data='price')],
            [InlineKeyboardButton("Set Furniture", callback_data='furniture')],
            [InlineKeyboardButton("Set Property State", callback_data='state')],
            [InlineKeyboardButton("Set City", callback_data='city')],
            [InlineKeyboardButton("Set Custom Area", callback_data='polygon')],
            [InlineKeyboardButton("Set Update Frequency", callback_data='frequency')],
            [InlineKeyboardButton("Show Current Settings", callback_data='show')],
            [InlineKeyboardButton("Start Monitoring", callback_data='start_monitoring')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
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
        keyboard = [
            [InlineKeyboardButton("Set Rooms", callback_data='rooms')],
            [InlineKeyboardButton("Set Size", callback_data='size')],
            [InlineKeyboardButton("Set Price", callback_data='price')],
            [InlineKeyboardButton("Set Furniture", callback_data='furniture')],
            [InlineKeyboardButton("Set Property State", callback_data='state')],
            [InlineKeyboardButton("Set City", callback_data='city')],
            [InlineKeyboardButton("Set Custom Area", callback_data='polygon')],
            [InlineKeyboardButton("Set Update Frequency", callback_data='frequency')],
            [InlineKeyboardButton("Show Current Settings", callback_data='show')],
            [InlineKeyboardButton("Start Monitoring", callback_data='start_monitoring')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
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
        keyboard = [
            [InlineKeyboardButton("Set Rooms", callback_data='rooms')],
            [InlineKeyboardButton("Set Size", callback_data='size')],
            [InlineKeyboardButton("Set Price", callback_data='price')],
            [InlineKeyboardButton("Set Furniture", callback_data='furniture')],
            [InlineKeyboardButton("Set Property State", callback_data='state')],
            [InlineKeyboardButton("Set City", callback_data='city')],
            [InlineKeyboardButton("Set Custom Area", callback_data='polygon')],
            [InlineKeyboardButton("Set Update Frequency", callback_data='frequency')],
            [InlineKeyboardButton("Show Current Settings", callback_data='show')],
            [InlineKeyboardButton("Start Monitoring", callback_data='start_monitoring')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.edit_text(
            "Welcome to Idealista Monitor Bot! Please choose an option:",
            reply_markup=reply_markup
        )
        return CHOOSING
    
    return CHOOSING

def main():
    """Start the bot"""
    # Load saved configurations
    load_configs()
    
    # Create the Application
    application = Application.builder().token(os.getenv('TELEGRAM_BOT_TOKEN')).build()
    
    # Add conversation handler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            CHOOSING: [CallbackQueryHandler(button_handler)],
            SETTING_ROOMS: [CallbackQueryHandler(button_handler)],
            SETTING_SIZE: [CallbackQueryHandler(button_handler)],
            SETTING_PRICE: [CallbackQueryHandler(button_handler)],
            SETTING_FURNITURE: [CallbackQueryHandler(button_handler)],
            SETTING_STATE: [CallbackQueryHandler(button_handler)],
            SETTING_CITY: [CallbackQueryHandler(button_handler)],
            SETTING_FREQUENCY: [CallbackQueryHandler(button_handler)]
        },
        fallbacks=[CommandHandler('start', start)]
    )
    
    application.add_handler(conv_handler)
    
    # Start the Bot
    application.run_polling()

if __name__ == '__main__':
    main() 