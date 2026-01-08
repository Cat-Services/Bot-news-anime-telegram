# Anime News Telegram Bot

A simple yet powerful Telegram bot that keeps you updated with the latest anime releases from [Kitsu.io](https://kitsu.io). The bot periodically checks for new anime series and also allows users to search for anime directly from Telegram.

## Features

- **Automatic Notifications**: The bot runs an automatic background task every hour to check for the very latest anime series added to Kitsu and sends a notification to a pre-configured Telegram chat.
- **User Commands**: Provides simple commands to interact with the bot and discover anime.

### Available Commands

- `/start`: Displays a welcome message and the list of available commands.
- `/recent`: Shows the 5 most recently added anime series.
- `/trending`: Fetches the top 5 most popular anime that are currently airing.
- `/search <name>`: Searches for an anime series by its name and returns the top 5 matches.

## Tech Stack

- **Language**: Python 3
- **Framework**: `python-telegram-bot`
- **API**: [Kitsu API](https://kitsu.io/api/edge/anime) for anime data.
- **Dependencies**: `requests`, `python-dotenv`

## Setup and Installation

Follow these steps to get your own instance of the bot running.

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/Cat-Services/Bot-news-anime-telegram.git
    cd Bot-news-anime-telegram
    ```

2.  **Create and activate a virtual environment:**
    ```bash
    # For Linux / macOS
    python3 -m venv .venv
    source .venv/bin/activate

    # For Windows
    python -m venv .venv
    .venv\Scripts\activate
    ```

3.  **Install the dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Create the environment file:**
    Create a file named `.env` in the root of the project and add your Telegram credentials:
    ```env
    TELEGRAM_BOT_TOKEN="YOUR_TELEGRAM_BOT_TOKEN"
    TELEGRAM_CHAT_ID="YOUR_TARGET_TELEGRAM_CHAT_ID"
    ```
    - `TELEGRAM_BOT_TOKEN` is the token you get from BotFather.
    - `TELEGRAM_CHAT_ID` is the ID of the chat where the bot will send automatic notifications.

5.  **Run the bot:**
    ```bash
    python bot.py
    ```
    The bot will start polling for updates and the background task will be scheduled.
