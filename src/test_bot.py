import pytest
from bot import (
    start, button_handler,
    CHOOSING, SETTING_ROOMS, SETTING_SIZE, SETTING_PRICE,
    SETTING_FURNITURE, SETTING_STATE, SETTING_CITY, SETTING_FREQUENCY,
    WAITING_FOR_PRICE
)
from filters import set_rooms, set_size, set_price, set_furniture, set_state, set_city, set_frequency

# Test cases
@pytest.mark.asyncio
async def test_start_command(mock_update, mock_context):
    """Test the /start command"""
    result = await start(mock_update, mock_context)
    assert result == CHOOSING
    mock_update.message.reply_text.assert_called_once()

@pytest.mark.asyncio
async def test_set_rooms(mock_update, mock_context):
    """Test setting room numbers"""
    mock_update.callback_query.data = 'rooms'
    result = await set_rooms(mock_update, mock_context)
    assert result == SETTING_ROOMS
    mock_update.callback_query.message.edit_text.assert_called_once()

@pytest.mark.asyncio
async def test_set_size(mock_update, mock_context):
    """Test setting size range"""
    mock_update.callback_query.data = 'size'
    result = await set_size(mock_update, mock_context)
    assert result == SETTING_SIZE
    mock_update.callback_query.message.edit_text.assert_called_once()

@pytest.mark.asyncio
async def test_set_price(mock_update, mock_context):
    """Test setting price"""
    mock_update.callback_query.data = 'price'
    result = await set_price(mock_update, mock_context)
    assert result == WAITING_FOR_PRICE
    # Check that either edit_message_text or edit_text was called (depending on implementation)
    assert (mock_update.callback_query.edit_message_text.called or 
            mock_update.callback_query.message.edit_text.called)

@pytest.mark.asyncio
async def test_set_furniture(mock_update, mock_context):
    """Test setting furniture preference"""
    mock_update.callback_query.data = 'furniture'
    result = await set_furniture(mock_update, mock_context)
    assert result == SETTING_FURNITURE
    mock_update.callback_query.message.edit_text.assert_called_once()

@pytest.mark.asyncio
async def test_set_state(mock_update, mock_context):
    """Test setting property state"""
    mock_update.callback_query.data = 'state'
    result = await set_state(mock_update, mock_context)
    assert result == SETTING_STATE
    mock_update.callback_query.message.edit_text.assert_called_once()

@pytest.mark.asyncio
async def test_set_city(mock_update, mock_context):
    """Test setting city"""
    mock_update.callback_query.data = 'city'
    result = await set_city(mock_update, mock_context)
    assert result == SETTING_CITY
    mock_update.callback_query.message.edit_text.assert_called_once()

@pytest.mark.asyncio
async def test_set_frequency(mock_update, mock_context):
    """Test setting update frequency"""
    mock_update.callback_query.data = 'frequency'
    result = await set_frequency(mock_update, mock_context)
    assert result == SETTING_FREQUENCY
    mock_update.callback_query.message.edit_text.assert_called_once()

@pytest.mark.asyncio
async def test_back_button(mock_update, mock_context):
    """Test back button functionality"""
    # Set initial state
    mock_context.user_data['current_state'] = SETTING_ROOMS
    mock_update.callback_query.data = 'back'
    
    result = await button_handler(mock_update, mock_context)
    assert result == CHOOSING
    # Check that either edit_message_text or edit_text was called
    assert (mock_update.callback_query.edit_message_text.called or 
            mock_update.callback_query.message.edit_text.called)

@pytest.mark.asyncio
async def test_room_selection(mock_update, mock_context):
    """Test room selection and saving"""
    mock_update.callback_query.data = 'rooms_2'
    result = await button_handler(mock_update, mock_context)
    assert result == CHOOSING
    assert mock_update.callback_query.message.edit_text.call_count == 2
    calls = mock_update.callback_query.message.edit_text.call_args_list
    assert calls[0][0][0] == 'Minimum rooms set to 2+!'
    assert 'Welcome to Idealista Monitor Bot!' in calls[1][0][0]

@pytest.mark.asyncio
async def test_size_selection(mock_update, mock_context):
    """Test size selection and saving"""
    mock_update.callback_query.data = 'size_50'
    result = await button_handler(mock_update, mock_context)
    assert result == CHOOSING
    assert mock_update.callback_query.message.edit_text.call_count == 2
    calls = mock_update.callback_query.message.edit_text.call_args_list
    assert calls[0][0][0] == 'Minimum size set to 50m²+!'
    assert 'Welcome to Idealista Monitor Bot!' in calls[1][0][0]

@pytest.mark.asyncio
async def test_price_selection(mock_update, mock_context):
    """Test price selection and saving"""
    mock_update.callback_query.data = 'price_1000'
    result = await button_handler(mock_update, mock_context)
    assert result == CHOOSING
    assert mock_update.callback_query.message.edit_text.call_count == 2
    calls = mock_update.callback_query.message.edit_text.call_args_list
    assert calls[0][0][0] == 'Maximum price updated!'
    assert 'Welcome to Idealista Monitor Bot!' in calls[1][0][0]

@pytest.mark.asyncio
async def test_furniture_selection(mock_update, mock_context):
    """Test furniture selection and saving"""
    mock_update.callback_query.data = 'furniture_toggle_furnished'
    result = await button_handler(mock_update, mock_context)
    assert result == SETTING_FURNITURE  # Toggle operations stay in furniture setting mode
    # Check that edit_message_text was called
    assert mock_update.callback_query.edit_message_text.call_count > 0

@pytest.mark.asyncio
async def test_state_selection(mock_update, mock_context):
    """Test property state selection and saving"""
    mock_update.callback_query.data = 'state_toggle_good'
    result = await button_handler(mock_update, mock_context)
    assert result == SETTING_STATE  # Toggle operations stay in state setting mode
    # Check that edit_message_text was called
    assert mock_update.callback_query.edit_message_text.call_count > 0

@pytest.mark.asyncio
async def test_city_selection(mock_update, mock_context):
    """Test city selection and saving"""
    mock_update.callback_query.data = 'city_lisboa'
    result = await button_handler(mock_update, mock_context)
    assert result == CHOOSING
    assert mock_update.callback_query.message.edit_text.call_count == 2
    calls = mock_update.callback_query.message.edit_text.call_args_list
    assert calls[0][0][0] == 'City updated!'
    assert 'Welcome to Idealista Monitor Bot!' in calls[1][0][0]

@pytest.mark.asyncio
async def test_frequency_selection(mock_update, mock_context):
    """Test update frequency selection and saving"""
    mock_update.callback_query.data = 'freq_10'
    result = await button_handler(mock_update, mock_context)
    assert result == CHOOSING
    assert mock_update.callback_query.message.edit_text.call_count == 2
    calls = mock_update.callback_query.message.edit_text.call_args_list
    assert calls[0][0][0] == 'Update frequency updated!'
    assert 'Welcome to Idealista Monitor Bot!' in calls[1][0][0]

@pytest.mark.asyncio
async def test_show_settings(mock_update, mock_context):
    """Test showing current settings"""
    mock_update.callback_query.data = 'show'
    result = await button_handler(mock_update, mock_context)
    assert result == CHOOSING
    mock_update.callback_query.message.reply_text.assert_called_once()

@pytest.mark.asyncio
async def test_setting_value_returns_to_main_menu(mock_update, mock_context):
    """Test that setting any value returns to the main menu"""
    # Test with size setting
    mock_update.callback_query.data = 'size_50'
    result = await button_handler(mock_update, mock_context)
    assert result == CHOOSING
    assert mock_update.callback_query.message.edit_text.call_count == 2
    calls = mock_update.callback_query.message.edit_text.call_args_list
    assert calls[0][0][0] == 'Minimum size set to 50m²+!'
    assert 'Welcome to Idealista Monitor Bot!' in calls[1][0][0]
    
    # Reset mocks
    mock_update.callback_query.message.edit_text.reset_mock()
    
    # Test with price setting
    mock_update.callback_query.data = 'price_1000'
    result = await button_handler(mock_update, mock_context)
    assert result == CHOOSING
    assert mock_update.callback_query.message.edit_text.call_count == 2
    calls = mock_update.callback_query.message.edit_text.call_args_list
    assert calls[0][0][0] == 'Maximum price updated!'
    assert 'Welcome to Idealista Monitor Bot!' in calls[1][0][0] 