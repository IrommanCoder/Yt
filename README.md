# YouTube Downloader Web Application

A feature-rich, fast, and retro-styled YouTube downloader web application built with FastAPI and yt-dlp. Returns direct URLs for browser downloads with WebAssembly FFmpeg support for client-side processing.

## Features

✅ **Video Download** - Download videos in multiple qualities (1080p, 720p, 480p, 360p, 240p)
✅ **Audio Extraction** - Extract audio as MP3 from any YouTube video
✅ **Direct URLs** - Get direct download URLs for browser streaming
✅ **Playlist Support** - Download entire playlists (configurable max size)
✅ **YouTube Search** - Search for videos directly from the app
✅ **Statistics Dashboard** - Real-time tracking of downloads, searches, and uptime
✅ **Download History** - View recent downloads with file information
✅ **Retro UI** - Fast, simple old-fashioned UI with modern responsiveness
✅ **Auto Cleanup** - Automatic deletion of old files to save space
✅ **WebAssembly Ready** - Designed for future WebAssembly FFmpeg integration

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
4. Click "Get Info" to preview or "Download" to process
5. Download your file when ready via direct browser download

## Pages

- **Home** (`/`) - Main download page with URL input and quality selection
- **Search** (`/search`) - YouTube search interface
- **History** (`/history`) - Recent downloads list
- **Statistics** (`/stats`) - Real-time stats dashboard with auto-refresh
- **About** (`/about`) - Application information and features

## API Endpoints

- `POST /api/info` - Get video/playlist information (returns direct URLs)
- `POST /api/search` - Search YouTube videos
- `POST /api/download` - Download video/audio and return file URL
- `GET /api/stats` - Get application statistics
- `GET /download/<filename>` - Serve/download processed files

## Project Structure

```
/workspace
├── app.py              # Main FastAPI application
├── templates/          # HTML templates
│   ├── index.html      # Home page
│   ├── stats.html      # Statistics dashboard
│   ├── history.html    # Download history
│   ├── search.html     # Search page
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
- Old-school aesthetic with modern functionality

## Architecture

### Backend (FastAPI + yt-dlp)
- Extracts video information and direct URLs
- Processes downloads server-side when needed
- Manages file storage and cleanup
- Tracks statistics and usage metrics

### Frontend (Vanilla JS)
- Interactive download forms
- Real-time progress updates
- Search results display
- Direct browser downloads
- No framework dependencies for speed

## Future Enhancements

- **WebAssembly FFmpeg Integration**: Client-side video/audio processing
- **Batch Downloads**: Queue multiple videos for sequential processing
- **Format Conversion**: More output formats (MKV, AVI, WAV, etc.)
- **Subtitle Download**: Extract and embed subtitles
- **Quality Comparison**: Preview different quality options

## License

MIT License
