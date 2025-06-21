import pytest
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

from bot import (
    start,
    button_handler,
    CHOOSING,
    SETTING_ROOMS,
    SETTING_SIZE,
    SETTING_PRICE,
    SETTING_FURNITURE,
    SETTING_STATE,
    SETTING_CITY,
    SETTING_FREQUENCY,
    WAITING_FOR_PRICE,
)
from filters import (
    set_rooms,
    set_size,
    set_price,
    set_furniture,
    set_state,
    set_city,
    set_frequency,
)


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
    mock_update.callback_query.data = "rooms"
    result = await set_rooms(mock_update, mock_context)
    assert result == SETTING_ROOMS
    mock_update.callback_query.message.edit_text.assert_called_once()


@pytest.mark.asyncio
async def test_set_size(mock_update, mock_context):
    """Test setting size range"""
    mock_update.callback_query.data = "size"
    result = await set_size(mock_update, mock_context)
    assert result == SETTING_SIZE
    mock_update.callback_query.message.edit_text.assert_called_once()


@pytest.mark.asyncio
async def test_set_price(mock_update, mock_context):
    """Test setting price"""
    mock_update.callback_query.data = "price"
    result = await set_price(mock_update, mock_context)
    assert result == WAITING_FOR_PRICE
    # Check that either edit_message_text or edit_text was called (depending on implementation)
    assert (
        mock_update.callback_query.edit_message_text.called
        or mock_update.callback_query.message.edit_text.called
    )


@pytest.mark.asyncio
async def test_set_furniture(mock_update, mock_context):
    """Test setting furniture preference"""
    mock_update.callback_query.data = "furniture"
    result = await set_furniture(mock_update, mock_context)
    assert result == SETTING_FURNITURE
    mock_update.callback_query.message.edit_text.assert_called_once()


@pytest.mark.asyncio
async def test_set_state(mock_update, mock_context):
    """Test setting property state"""
    mock_update.callback_query.data = "state"
    result = await set_state(mock_update, mock_context)
    assert result == SETTING_STATE
    mock_update.callback_query.message.edit_text.assert_called_once()


@pytest.mark.asyncio
async def test_set_city(mock_update, mock_context):
    """Test setting city"""
    mock_update.callback_query.data = "city"
    result = await set_city(mock_update, mock_context)
    assert result == SETTING_CITY
    mock_update.callback_query.message.edit_text.assert_called_once()


@pytest.mark.asyncio
async def test_set_frequency(mock_update, mock_context):
    """Test setting update frequency"""
    mock_update.callback_query.data = "frequency"
    result = await set_frequency(mock_update, mock_context)
    assert result == SETTING_FREQUENCY
    mock_update.callback_query.message.edit_text.assert_called_once()


@pytest.mark.asyncio
async def test_button_handler_unknown_action(mock_update, mock_context):
    """Test button handler with unknown action"""
    mock_update.callback_query.data = "unknown_action"
    result = await button_handler(mock_update, mock_context)
    # Should handle unknown actions gracefully
    assert result is not None
