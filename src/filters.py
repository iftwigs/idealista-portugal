from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from models import SearchConfig, FurnitureType, PropertyState

# Conversation states
CHOOSING, SETTING_ROOMS, SETTING_SIZE, SETTING_PRICE, SETTING_FURNITURE, SETTING_STATE, SETTING_CITY, SETTING_POLYGON, SETTING_FREQUENCY, WAITING_FOR_PRICE, WAITING_FOR_POLYGON_URL = range(11)




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
    """Handle price setting by asking user to input a custom price"""
    import logging
    logger = logging.getLogger(__name__)
    
    query = update.callback_query
    await query.answer()
    
    logger.info("SET_PRICE: Entering set_price function from filters.py")
    logger.info(f"SET_PRICE: Context user_data: {context.user_data}")
    
    keyboard = [
        [InlineKeyboardButton("Back", callback_data='back')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    try:
        await query.edit_message_text(
            "Please enter the maximum price in euros (e.g., 1200):",
            reply_markup=reply_markup
        )
        logger.info("SET_PRICE: Successfully edited message for price input")
    except Exception as e:
        logger.error(f"SET_PRICE: Error editing message: {e}")
        # Fallback: send new message
        await query.message.reply_text(
            "Please enter the maximum price in euros (e.g., 1200):",
            reply_markup=reply_markup
        )
    
    logger.info(f"SET_PRICE: Returning WAITING_FOR_PRICE state: {WAITING_FOR_PRICE}")
    return WAITING_FOR_PRICE

async def set_furniture(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle furniture setting"""
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("Furnished", callback_data='furniture_furnished')],
        [InlineKeyboardButton("Kitchen Furniture Only", callback_data='furniture_kitchen')],
        [InlineKeyboardButton("Unfurnished", callback_data='furniture_unfurnished')],
        [InlineKeyboardButton("Back", callback_data='back')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.edit_text(
        "Select furniture preference:",
        reply_markup=reply_markup
    )
    return SETTING_FURNITURE

async def set_state(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle property state setting with checkbox logic"""
    query = update.callback_query
    await query.answer()
    
    # Get current user config to show selected states
    from bot import user_configs
    from models import SearchConfig
    user_id = update.effective_user.id
    
    # Ensure user config exists
    if user_id not in user_configs:
        user_configs[user_id] = SearchConfig()
    
    config = user_configs[user_id]
    
    # Create checkbox-style buttons
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
    
    await query.message.edit_text(
        "Select property states (you can select multiple):",
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

async def set_polygon(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle custom polygon setting"""
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("Clear Custom Area", callback_data='polygon_clear')],
        [InlineKeyboardButton("Back", callback_data='back')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    message_text = (
        "🗺️ **Custom Area Setup**\n\n"
        "To set a custom search area:\n"
        "1. Go to idealista.pt\n"
        "2. Use the map to draw your custom area\n"
        "3. Copy the entire URL from your browser\n"
        "4. Paste it here as a message\n\n"
        "The URL should contain 'shape=' parameter with your polygon coordinates."
    )
    
    await query.message.edit_text(
        message_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    return WAITING_FOR_POLYGON_URL

