# Idealista Notifier Bot

## Overview

This project is a Telegram bot that automatically scrapes Idealista for new apartment listings in Portugal. It allows users to configure their search preferences and receive real-time notifications via Telegram. The bot supports:

- 📍 Custom location selection (city or custom area polygon)
- 💰 Configurable price range
- 🛏️ Room number preferences
- 📏 Size requirements
- 🏠 Property state (new, good condition, needs remodeling)
- 🪑 Furniture requirements
- ⏰ Customizable update frequency

## Features

- Interactive Telegram bot interface for configuration
- Rate limiting to avoid IP bans
- Persistent user configurations
- Duplicate listing detection
- Beautiful message formatting
- Automatic error handling and recovery

## Project Structure

```text
idealista-notifier/
│── src/
│   ├── bot.py           # Telegram bot interface
│   ├── scraper.py       # Idealista scraping logic
│   ├── models.py        # Data models and configuration
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

2. Install Dependencies

```bash
pip install -r requirements.txt
```

3. Set Up Environment Variables
Create a `.env` file in the root directory and add:

```bash
TELEGRAM_BOT_TOKEN=your_bot_token_here
```

- **TELEGRAM_BOT_TOKEN** → Get this from Telegram's @BotFather

4. Run the Bot

```bash
python src/bot.py
```

## Usage

1. Start the bot by sending `/start` in Telegram
2. Use the interactive menu to configure your search preferences:
   - Set room numbers
   - Set size range
   - Set maximum price
   - Choose furniture requirements
   - Select property state
   - Set location (city or custom area)
   - Configure update frequency

3. Start monitoring by clicking "Start Monitoring"
4. Receive notifications for new listings matching your criteria

## Rate Limiting

The bot implements rate limiting to avoid being blocked by Idealista:
- Maximum 2 requests per minute
- Configurable update frequency per user
- Automatic error handling and recovery

## Contributing

Feel free to open issues or submit pull requests to improve the project!

## License

This project is licensed under the MIT License - see the LICENSE file for details.