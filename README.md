# YouTube Downloader Telegram Bot

A feature-rich Telegram bot for downloading YouTube videos in various formats and qualities.

## 🎯 Features

- **Multiple Quality Options**: Download videos in 1080p, 720p, 480p, 360p, or 240p
- **Audio Extraction**: Extract audio-only from YouTube videos
- **Playlist Support**: Download videos from YouTube playlists (configurable limit)
- **User Preferences**: Customize default quality, audio preference, and thumbnail settings
- **Statistics Tracking**: Monitor bot usage, user count, and download statistics
- **Cooldown System**: Prevent abuse with configurable cooldown between downloads
- **Admin Commands**: Broadcast messages to users (requires database for production)
- **Inline Keyboard**: Interactive buttons for easy navigation and downloads

## 📋 Available Commands

| Command | Description |
|---------|-------------|
| `/start` | Start the bot and see welcome message |
| `/help` | Display help message with all commands |
| `/waiting_time` | Check remaining cooldown time |
| `/search <query>` | Search YouTube videos |
| `/playlist <url>` | Download videos from a playlist |
| `/stats` | View bot statistics |
| `/settings` | Manage your preferences |
| `/broadcast` | Admin only: Broadcast message |

## 🚀 Setup

### Prerequisites

- Python 3.8+
- Telegram Bot Token (from [@BotFather](https://t.me/BotFather))
- API ID and API Hash (from [my.telegram.org](https://my.telegram.org))

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd <repository-directory>
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
export API_ID="your_api_id"
export API_HASH="your_api_hash"
export BOT_TOKEN="your_bot_token"
export CHANNEL_USERNAME="your_channel_username"
export ADMIN_IDS="admin_user_id_1,admin_user_id_2"
export MAX_PLAYLIST_SIZE="10"
```

4. Run the bot:
```bash
python bot.py
```

## ⚙️ Configuration

The bot can be configured using environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `API_ID` | Telegram API ID | (required) |
| `API_HASH` | Telegram API Hash | (required) |
| `BOT_TOKEN` | Telegram Bot Token | (required) |
| `CHANNEL_USERNAME` | Channel username for force subscribe | `mugu_bots` |
| `ADMIN_IDS` | Comma-separated admin user IDs | `` |
| `MAX_PLAYLIST_SIZE` | Maximum playlist videos to process | `10` |
| `FORCE_SUBSCRIBE` | Enable force subscribe (`true`/`false`) | `false` |

## 📊 Features in Detail

### User Preferences
Users can customize their experience with:
- Default video quality selection
- Audio extraction preference
- Thumbnail display toggle

### Statistics
The bot tracks:
- Total unique users
- Number of videos processed
- Number of playlists processed
- Bot uptime
- Total downloads

### Callback System
Interactive inline buttons for:
- Quality selection
- Audio download
- Settings management
- Playlist navigation
- Refresh video info

## 🛡️ Rate Limiting

The bot implements a cooldown system to prevent abuse:
- Default cooldown: 2 minutes between downloads
- Users can check remaining time with `/waiting_time`

## 📝 Notes

- The search feature requires additional setup (YouTube Data API or yt-search package)
- For production use, implement persistent storage for user data and statistics
- Consider adding database support for broadcast functionality

## 📄 License

See LICENSE file for details.

## 🤝 Support

For issues and feature requests, please open an issue in the repository.