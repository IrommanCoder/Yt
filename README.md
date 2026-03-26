# YouTube Downloader Web Application

A feature-rich, fast, and retro-styled YouTube downloader web application built with FastAPI and yt-dlp.

## Features

✅ **Video Download** - Download videos in multiple qualities (1080p, 720p, 480p, 360p, 240p)
✅ **Audio Extraction** - Extract audio as MP3 from any YouTube video
✅ **Playlist Support** - Download entire playlists (configurable max size)
✅ **YouTube Search** - Search for videos directly from the app
✅ **Statistics Dashboard** - Real-time tracking of downloads, searches, and uptime
✅ **Download History** - View recent downloads with file information
✅ **Retro UI** - Fast, simple old-fashioned UI with modern responsiveness
✅ **Auto Cleanup** - Automatic deletion of old files to save space

## Installation

### Requirements
- Python 3.8+
- FFmpeg (for audio extraction)

### Setup

```bash
# Install dependencies
pip install fastapi uvicorn yt-dlp jinja2 python-multipart

# Run the application
python app.py
```

Or using uvicorn directly:
```bash
uvicorn app:app --host 0.0.0.0 --port 8000
```

## Configuration

Set environment variables to customize the application:

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | 8000 | Server port |
| `HOST` | 0.0.0.0 | Server host |
| `DOWNLOAD_FOLDER` | downloads | Directory for downloaded files |
| `MAX_PLAYLIST_SIZE` | 10 | Maximum videos per playlist download |
| `FILE_EXPIRY_HOURS` | 1 | Hours before auto-deletion |
| `ENABLE_PLAYLIST` | true | Enable/disable playlist downloads |
| `ENABLE_SEARCH` | true | Enable/disable YouTube search |
| `MAX_FILE_SIZE_MB` | 500 | Maximum file size limit |

Example:
```bash
export PORT=5000
export MAX_PLAYLIST_SIZE=20
export FILE_EXPIRY_HOURS=2
python app.py
```

## Usage

1. Open your browser and navigate to `http://localhost:8000`
2. Paste a YouTube URL or search for videos
3. Select quality (1080p-240p) and format (Video/Audio)
4. Click Download and wait for processing
5. Download your file when ready

## Pages

- **Home** (`/`) - Main download page
- **Search** (`/search`) - YouTube search interface
- **History** (`/history`) - Recent downloads
- **Statistics** (`/stats`) - Real-time stats dashboard
- **About** (`/about`) - Application information

## API Endpoints

- `POST /api/info` - Get video/playlist information
- `POST /api/search` - Search YouTube
- `POST /api/download` - Download video/audio
- `GET /api/stats` - Get statistics
- `GET /download/<filename>` - Serve downloaded files

## Project Structure

```
/workspace
├── app.py              # Main FastAPI application
├── templates/          # HTML templates
│   ├── index.html      # Home page
│   ├── stats.html      # Statistics dashboard
│   ├── history.html    # Download history
│   └── about.html      # About page
├── static/             # Static assets
│   ├── css/
│   │   └── style.css   # Retro-style CSS
│   └── js/
│       └── main.js     # Frontend JavaScript
├── downloads/          # Downloaded files (auto-created)
└── README.md           # This file
```

## UI Design

The application features a **retro-style UI** with:
- Dark theme with neon accents
- Scanline effects for vintage feel
- Card-based layout
- Responsive design for mobile/desktop
- Fast loading with minimal dependencies

## License

MIT License
