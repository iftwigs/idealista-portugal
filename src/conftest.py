import pytest
from unittest.mock import MagicMock, AsyncMock
from telegram import Update, CallbackQuery, Message, User
from telegram.ext import CallbackContext
from models import SearchConfig, PropertyState, FurnitureType

@pytest.fixture
def mock_update():
    """Create a mock update object"""
    update = MagicMock(spec=Update)
    update.effective_user = MagicMock(spec=User)
    update.effective_user.id = 123456
    update.effective_chat = MagicMock()
    update.effective_chat.id = 123456
    update.message = MagicMock(spec=Message)
    update.message.reply_text = AsyncMock()
    update.callback_query = MagicMock(spec=CallbackQuery)
    update.callback_query.message = MagicMock(spec=Message)
    update.callback_query.message.edit_text = AsyncMock()
    update.callback_query.message.reply_text = AsyncMock()
    update.callback_query.edit_message_text = AsyncMock()
    update.callback_query.answer = AsyncMock()
    update.callback_query.from_user = MagicMock(spec=User)
    update.callback_query.from_user.id = 123456
    return update

@pytest.fixture
def mock_context():
    """Create a mock context object"""
    context = MagicMock(spec=CallbackContext)
    context.user_data = {}
    context.chat_data = {}
    return context

@pytest.fixture
def mock_config():
    """Create a mock search config"""
    return SearchConfig(
        min_rooms=2,
        max_rooms=10,
        min_size=50,
        max_size=80,
        max_price=1000,
        furniture_types=[FurnitureType.FURNISHED],
        property_states=[PropertyState.GOOD],
        city="lisboa",
        update_frequency=10
    )

@pytest.fixture
def mock_html():
    """Create a mock HTML response"""
    return """
    <div class="item">
        <div class="item-info-container">
            <a class="item-link" href="/123">Apartment 1</a>
            <span class="item-price">900€</span>
            <span class="item-detail">3 rooms</span>
            <span class="item-detail">70m²</span>
            <span class="item-detail">Furnished</span>
            <span class="item-detail">Good condition</span>
        </div>
    </div>
    <div class="item">
        <div class="item-info-container">
            <a class="item-link" href="/456">Apartment 2</a>
            <span class="item-price">1200€</span>
            <span class="item-detail">2 rooms</span>
            <span class="item-detail">60m²</span>
            <span class="item-detail">Unfurnished</span>
            <span class="item-detail">Needs remodeling</span>
        </div>
    </div>
    """ 