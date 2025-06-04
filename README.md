# Idealista Notifier Bot

## Overview

This project is a Telegram bot that automatically scrapes Idealista for new apartment listings in Portugal. It allows users to configure their search preferences and receive real-time notifications via Telegram. The bot supports:

- 📍 City selection 
- 💰 Configurable maximum price
- 🛏️ Minimum room requirements 
- 📏 Minimum size requirements 
- 🏠 Property state (new, good condition, needs remodeling)
- 🪑 Furniture requirements
- ⏰ Customizable update frequency

## Features

- Interactive Telegram bot interface for configuration
- Rate limiting to avoid IP bans (2 requests per minute)
- Persistent user configurations using JSON storage
- Duplicate listing detection
- Automatic error handling and recovery
- Comprehensive test coverage

## Project Structure

```text
idealista-notifier/
│── src/
│   ├── bot.py           # Telegram bot interface and conversation handlers
│   ├── scraper.py       # Idealista scraping logic with rate limiting
│   ├── models.py        # Data models (SearchConfig, PropertyState, SizeRange)
│   ├── test_bot.py      # Bot functionality tests
│   ├── test_scraper.py  # Scraper functionality tests
│── .env                 # Environment variables
│── requirements.txt     # Python dependencies
│── README.md           # Documentation
```

## Setup & Installation

1. Clone the Repository

```bash
git clone https://github.com/iftwigs/idealista-portugal.git
cd idealista-portugal
```

2. Create and activate a virtual environment (recommended)

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install Dependencies

```bash
pip install -r requirements.txt
```

4. Set Up Environment Variables
Create a `.env` file in the root directory and add:

```bash
TELEGRAM_BOT_TOKEN=your_bot_token_here
```

- **TELEGRAM_BOT_TOKEN** → Get this from Telegram's @BotFather

5. Run the Bot

```bash
python src/bot.py
```

## Usage

1. Start the bot by sending `/start` in Telegram
2. Use the interactive menu to configure your search preferences:
   - Set minimum room number
   - Set minimum size
   - Set maximum price 
   - Choose furniture requirements 
   - Select property state 
   - Set city 
   - Configure update frequency

3. View your current settings using "Show Current Settings"
4. Start monitoring by clicking "Start Monitoring"
5. Receive notifications for new listings matching your criteria

## Testing

Run the test suite using pytest:

```bash
python -m pytest src/test_*.py -v
```

The test suite covers:
- Bot conversation flow
- Setting configuration values
- Scraper functionality
- Rate limiting
- Duplicate detection
- Size filtering

## Rate Limiting

The bot implements rate limiting to avoid being blocked by Idealista:
- Maximum 2 requests per minute
- Configurable update frequency per user (5-30 minutes)
- Automatic error handling and recovery
- User-specific configurations

## Contributing

Feel free to open issues or submit pull requests to improve the project!

## License

This project is licensed under the MIT License - see the LICENSE file for details.