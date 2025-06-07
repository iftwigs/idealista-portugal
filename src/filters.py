from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from models import SearchConfig

# Conversation states
CHOOSING, SETTING_ROOMS, SETTING_SIZE, SETTING_PRICE, SETTING_FURNITURE, SETTING_STATE, SETTING_CITY, SETTING_POLYGON, SETTING_FREQUENCY, WAITING_FOR_PRICE = range(10)

# Global keyboard definitions
MAIN_MENU_KEYBOARD = [
    [InlineKeyboardButton("Set number of rooms", callback_data='rooms')],
    [InlineKeyboardButton("Set size in square meters", callback_data='size')],
    [InlineKeyboardButton("Set maximum price", callback_data='price')],
    [InlineKeyboardButton("Set furniture preference", callback_data='furniture')],
    [InlineKeyboardButton("Set state of the property", callback_data='state')],
    [InlineKeyboardButton("Set city", callback_data='city')],
    [InlineKeyboardButton("Set a custom area (polygon)", callback_data='polygon')],
    [InlineKeyboardButton("Set update frequency", callback_data='frequency')],
    [InlineKeyboardButton("Show current settings", callback_data='show')],
    [InlineKeyboardButton("Start searching", callback_data='start_monitoring')]
]



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

