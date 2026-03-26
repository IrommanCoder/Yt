"""
YouTube Downloader Web Application
FastAPI backend with yt-dlp integration
Returns direct URLs for browser download with WebAssembly FFmpeg support
"""

import os
import re
import json
import time
import shutil
import asyncio
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Form, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import yt_dlp

# ============================================================================
# CONFIGURATION
# ============================================================================

class Config:
    """Application configuration with environment variable support."""
    
    PORT: int = int(os.getenv("PORT", "8000"))
    HOST: str = os.getenv("HOST", "0.0.0.0")
    DOWNLOAD_FOLDER: str = os.getenv("DOWNLOAD_FOLDER", "downloads")
    MAX_PLAYLIST_SIZE: int = int(os.getenv("MAX_PLAYLIST_SIZE", "10"))
    FILE_EXPIRY_HOURS: int = int(os.getenv("FILE_EXPIRY_HOURS", "1"))
    ENABLE_PLAYLIST: bool = os.getenv("ENABLE_PLAYLIST", "true").lower() == "true"
    ENABLE_SEARCH: bool = os.getenv("ENABLE_SEARCH", "true").lower() == "true"
    MAX_FILE_SIZE_MB: int = int(os.getenv("MAX_FILE_SIZE_MB", "500"))
    
    # Create directories
    Path(DOWNLOAD_FOLDER).mkdir(parents=True, exist_ok=True)

config = Config()

# ============================================================================
# LOGGING SETUP
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================================
# DATA MODELS
# ============================================================================

@dataclass
class VideoInfo:
    """Video information data model."""
    id: str
    title: str
    duration: int
    view_count: int
    uploader: str
    thumbnail: str
    description: str
    is_playlist: bool = False
    playlist_count: int = 0
    formats: List[Dict[str, Any]] = None
    direct_url: str = ""
    
    def __post_init__(self):
        if self.formats is None:
            self.formats = []

@dataclass
class SearchResult:
    """Search result data model."""
    id: str
    title: str
    duration: int
    view_count: int
    uploader: str
    thumbnail: str
    url: str

@dataclass
class Statistics:
    """Application statistics data model."""
    total_downloads: int = 0
    video_downloads: int = 0
    audio_downloads: int = 0
    playlist_downloads: int = 0
    searches_performed: int = 0
    start_time: float = 0.0
    errors: int = 0
    
    @property
    def uptime(self) -> str:
        """Calculate uptime string."""
        if self.start_time == 0:
            return "0h 0m"
        delta = timedelta(seconds=int(time.time() - self.start_time))
        days = delta.days
        hours = delta.seconds // 3600
        minutes = (delta.seconds % 3600) // 60
        
        if days > 0:
            return f"{days}d {hours}h {minutes}m"
        elif hours > 0:
            return f"{hours}h {minutes}m"
        else:
            return f"{minutes}m"

# Global statistics instance
stats = Statistics()

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def format_filesize(size_bytes: int) -> str:
    """Format file size in human-readable format."""
    if size_bytes <= 0:
        return "Unknown"
    
    units = ['B', 'KB', 'MB', 'GB', 'TB']
    unit_index = 0
    size = float(size_bytes)
    
    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1
    
    return f"{size:.2f} {units[unit_index]}"

def format_duration(seconds: int) -> str:
    """Format duration in HH:MM:SS or MM:SS format."""
    if seconds <= 0:
        return "Unknown"
    
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    
    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes}:{secs:02d}"

def format_views(count: int) -> str:
    """Format view count in human-readable format."""
    if count <= 0:
        return "0"
    
    if count >= 1_000_000_000:
        return f"{count / 1_000_000_000:.2f}B"
    elif count >= 1_000_000:
        return f"{count / 1_000_000:.2f}M"
    elif count >= 1_000:
        return f"{count / 1_000:.2f}K"
    else:
        return str(count)

def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe file system usage."""
    sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)
    if len(sanitized) > 200:
        sanitized = sanitized[:200]
    return sanitized.strip()

def cleanup_old_files():
    """Remove files older than FILE_EXPIRY_HOURS."""
    try:
        download_path = Path(config.DOWNLOAD_FOLDER)
        cutoff_time = time.time() - (config.FILE_EXPIRY_HOURS * 3600)
        
        for file_path in download_path.glob("*"):
            if file_path.is_file() and file_path.stat().st_mtime < cutoff_time:
                file_path.unlink()
                logger.info(f"Cleaned up old file: {file_path.name}")
    except Exception as e:
        logger.error(f"Error during file cleanup: {e}")

# ============================================================================
# YOUTUBE DL HELPERS
# ============================================================================

def get_video_info(url: str) -> VideoInfo:
    """Extract video or playlist information from YouTube URL."""
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
        'noplaylist': False,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            if info is None:
                raise ValueError("No information extracted")
            
            is_playlist = info.get('_type') == 'playlist'
            
            if is_playlist:
                return VideoInfo(
                    id=info.get('id', ''),
                    title=info.get('title', 'Unknown Playlist'),
                    duration=0,
                    view_count=0,
                    uploader=info.get('uploader', 'Unknown'),
                    thumbnail=info.get('thumbnail', ''),
                    description=info.get('description', '')[:500] if info.get('description') else '',
                    is_playlist=True,
                    playlist_count=len(info.get('entries', [])),
                    formats=[],
                    direct_url=""
                )
            else:
                # Get direct URL for best quality
                direct_url = info.get('url', '')
                
                # Extract available formats
                formats = []
                for fmt in info.get('formats', []):
                    if fmt.get('vcodec') != 'none' and fmt.get('acodec') != 'none':
                        quality = fmt.get('format_note', '') or fmt.get('resolution', '')
                        filesize = fmt.get('filesize', 0)
                        format_url = fmt.get('url', '')
                        if quality and format_url:
                            formats.append({
                                'quality': quality,
                                'filesize': filesize,
                                'format_id': fmt.get('format_id', ''),
                                'url': format_url
                            })
                
                # Deduplicate formats by quality
                seen_qualities = set()
                unique_formats = []
                for fmt in formats:
                    if fmt['quality'] not in seen_qualities:
                        seen_qualities.add(fmt['quality'])
                        unique_formats.append(fmt)
                
                return VideoInfo(
                    id=info.get('id', ''),
                    title=info.get('title', 'Unknown Video'),
                    duration=info.get('duration', 0) or 0,
                    view_count=info.get('view_count', 0) or 0,
                    uploader=info.get('uploader', 'Unknown'),
                    thumbnail=info.get('thumbnail', ''),
                    description=info.get('description', '')[:500] if info.get('description') else '',
                    is_playlist=False,
                    playlist_count=0,
                    formats=unique_formats[:10],
                    direct_url=direct_url
                )
    except Exception as e:
        logger.error(f"Error extracting video info: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to extract video info: {str(e)}")

def search_youtube(query: str, limit: int = 12) -> List[SearchResult]:
    """Search YouTube for videos."""
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': True,
        'default_search': 'ytsearch',
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            search_query = f"ytsearch{limit}:{query}"
            info = ydl.extract_info(search_query, download=False)
            
            results = []
            for entry in info.get('entries', []):
                if entry:
                    results.append(SearchResult(
                        id=entry.get('id', ''),
                        title=entry.get('title', 'Unknown'),
                        duration=entry.get('duration', 0) or 0,
                        view_count=entry.get('view_count', 0) or 0,
                        uploader=entry.get('uploader', 'Unknown'),
                        thumbnail=entry.get('thumbnail', ''),
                        url=f"https://www.youtube.com/watch?v={entry.get('id', '')}"
                    ))
            
            return results
    except Exception as e:
        logger.error(f"Error searching YouTube: {e}")
        raise HTTPException(status_code=400, detail=f"Search failed: {str(e)}")

async def download_media(
    url: str,
    quality: str,
    format_type: str,
    output_path: str,
    progress_callback=None
) -> str:
    """Download video or audio from YouTube."""
    
    def progress_hook(d):
        if progress_callback and d.get('status') == 'downloading':
            downloaded = d.get('downloaded_bytes', 0)
            total = d.get('total_bytes', 0) or d.get('total_bytes_estimate', 0)
            if total > 0:
                percent = (downloaded / total) * 100
                speed = d.get('speed', 0)
                eta = d.get('eta', 0)
                progress_callback(percent, speed, eta)
    
    ydl_opts = {
        'outtmpl': output_path,
        'quiet': True,
        'no_warnings': True,
        'progress_hooks': [progress_hook],
        'restrictfilenames': True,
        'noplaylist': True,
    }
    
    if format_type == 'audio':
        ydl_opts.update({
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        })
    else:
        quality_map = {
            '1080p': 'bestvideo[height<=1080]+bestaudio/best[height<=1080]/best',
            '720p': 'bestvideo[height<=720]+bestaudio/best[height<=720]/best',
            '480p': 'bestvideo[height<=480]+bestaudio/best[height<=480]/best',
            '360p': 'bestvideo[height<=360]+bestaudio/best[height<=360]/best',
            '240p': 'bestvideo[height<=240]+bestaudio/best[height<=240]/best',
        }
        ydl_opts['format'] = quality_map.get(quality, 'best')
    
    try:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, lambda: _download_with_ytdl(url, ydl_opts))
        return output_path
    except Exception as e:
        logger.error(f"Download error: {e}")
        raise

def _download_with_ytdl(url: str, opts: dict):
    """Helper to run yt-dlp download synchronously."""
    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.download([url])

async def download_playlist(
    url: str,
    quality: str,
    format_type: str,
    output_dir: str,
    max_videos: int,
    progress_callback=None
) -> List[str]:
    """Download all videos from a playlist."""
    
    downloaded_files = []
    video_count = 0
    
    def progress_hook(d):
        nonlocal video_count
        if d.get('status') == 'finished':
            video_count += 1
            if progress_callback:
                progress_callback(video_count, max_videos)
    
    ydl_opts = {
        'outtmpl': os.path.join(output_dir, '%(title)s.%(ext)s'),
        'quiet': True,
        'no_warnings': True,
        'progress_hooks': [progress_hook],
        'restrictfilenames': True,
        'playlistend': max_videos,
    }
    
    if format_type == 'audio':
        ydl_opts.update({
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        })
    else:
        quality_map = {
            '1080p': 'bestvideo[height<=1080]+bestaudio/best[height<=1080]/best',
            '720p': 'bestvideo[height<=720]+bestaudio/best[height<=720]/best',
            '480p': 'bestvideo[height<=480]+bestaudio/best[height<=480]/best',
            '360p': 'bestvideo[height<=360]+bestaudio/best[height<=360]/best',
            '240p': 'bestvideo[height<=240]+bestaudio/best[height<=240]/best',
        }
        ydl_opts['format'] = quality_map.get(quality, 'best')
    
    try:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, lambda: _download_with_ytdl(url, ydl_opts))
        
        for file_path in Path(output_dir).glob("*"):
            if file_path.is_file():
                downloaded_files.append(str(file_path))
        
        return downloaded_files
    except Exception as e:
        logger.error(f"Playlist download error: {e}")
        raise

# ============================================================================
# FASTAPI APPLICATION
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    stats.start_time = time.time()
    logger.info("YouTube Downloader started")
    yield
    logger.info("YouTube Downloader shutting down")

app = FastAPI(
    title="YouTube Downloader",
    description="Feature-rich YouTube downloader with retro UI",
    version="1.0.0",
    lifespan=lifespan
)

# ============================================================================
# Setup templates and static files
# ============================================================================

templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# ============================================================================
# ROUTES - PAGES
# ============================================================================

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Home page with download form."""
    return templates.TemplateResponse("index.html", {
        "request": request,
        "config": {
            "PORT": config.PORT,
            "HOST": config.HOST,
            "DOWNLOAD_FOLDER": config.DOWNLOAD_FOLDER,
            "MAX_PLAYLIST_SIZE": config.MAX_PLAYLIST_SIZE,
            "FILE_EXPIRY_HOURS": config.FILE_EXPIRY_HOURS,
            "ENABLE_PLAYLIST": config.ENABLE_PLAYLIST,
            "ENABLE_SEARCH": config.ENABLE_SEARCH,
            "MAX_FILE_SIZE_MB": config.MAX_FILE_SIZE_MB
        },
        "stats": asdict(stats)
    })

@app.get("/stats", response_class=HTMLResponse)
async def stats_page(request: Request):
    """Statistics dashboard page."""
    return templates.TemplateResponse("stats.html", {
        "request": request,
        "stats": asdict(stats)
    })

@app.get("/history", response_class=HTMLResponse)
async def history_page(request: Request):
    """Download history page."""
    download_path = Path(config.DOWNLOAD_FOLDER)
    files = []
    
    for file_path in sorted(download_path.glob("*"), key=lambda x: x.stat().st_mtime, reverse=True)[:20]:
        if file_path.is_file():
            stat = file_path.stat()
            files.append({
                'name': file_path.name,
                'size': format_filesize(stat.st_size),
                'created': datetime.fromtimestamp(stat.st_ctime).strftime('%Y-%m-%d %H:%M'),
                'url': f"/download/{file_path.name}"
            })
    
    return templates.TemplateResponse("history.html", {
        "request": request,
        "files": files,
        "stats": asdict(stats),
        "config": {
            "PORT": config.PORT,
            "HOST": config.HOST,
            "DOWNLOAD_FOLDER": config.DOWNLOAD_FOLDER,
            "MAX_PLAYLIST_SIZE": config.MAX_PLAYLIST_SIZE,
            "FILE_EXPIRY_HOURS": config.FILE_EXPIRY_HOURS,
            "ENABLE_PLAYLIST": config.ENABLE_PLAYLIST,
            "ENABLE_SEARCH": config.ENABLE_SEARCH,
            "MAX_FILE_SIZE_MB": config.MAX_FILE_SIZE_MB
        }
    })

@app.get("/search", response_class=HTMLResponse)
async def search_page(request: Request):
    """Search page."""
    return templates.TemplateResponse("search.html", {
        "request": request,
        "stats": asdict(stats)
    })

@app.get("/about", response_class=HTMLResponse)
async def about_page(request: Request):
    """About page."""
    return templates.TemplateResponse("about.html", {
        "request": request,
        "stats": asdict(stats),
        "config": {
            "PORT": config.PORT,
            "HOST": config.HOST,
            "DOWNLOAD_FOLDER": config.DOWNLOAD_FOLDER,
            "MAX_PLAYLIST_SIZE": config.MAX_PLAYLIST_SIZE,
            "FILE_EXPIRY_HOURS": config.FILE_EXPIRY_HOURS,
            "ENABLE_PLAYLIST": config.ENABLE_PLAYLIST,
            "ENABLE_SEARCH": config.ENABLE_SEARCH,
            "MAX_FILE_SIZE_MB": config.MAX_FILE_SIZE_MB
        }
    })

# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.post("/api/info")
async def api_get_info(url: str = Form(...)):
    """Get video or playlist information."""
    try:
        info = get_video_info(url)
        return JSONResponse(content={
            "success": True,
            "data": asdict(info)
        })
    except HTTPException as e:
        return JSONResponse(
            status_code=e.status_code,
            content={"success": False, "error": e.detail}
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )

@app.post("/api/search")
async def api_search(query: str = Form(...)):
    """Search YouTube videos."""
    try:
        stats.searches_performed += 1
        results = search_youtube(query)
        return JSONResponse(content={
            "success": True,
            "data": [asdict(r) for r in results]
        })
    except HTTPException as e:
        return JSONResponse(
            status_code=e.status_code,
            content={"success": False, "error": e.detail}
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )

@app.post("/api/download")
async def api_download(
    url: str = Form(...),
    quality: str = Form(default="720p"),
    format_type: str = Form(default="video")
):
    """Download video or audio and return file URL."""
    try:
        # Get video info first
        info = get_video_info(url)
        
        if info.is_playlist:
            stats.playlist_downloads += 1
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": "Playlist download requires server-side processing"}
            )
        
        # Generate output filename
        safe_title = sanitize_filename(info.title)
        timestamp = int(time.time())
        
        if format_type == 'audio':
            stats.audio_downloads += 1
            output_filename = f"{safe_title}_{timestamp}.mp3"
        else:
            stats.video_downloads += 1
            output_filename = f"{safe_title}_{timestamp}.mp4"
        
        output_path = os.path.join(config.DOWNLOAD_FOLDER, output_filename)
        
        # Download the file
        await download_media(url, quality, format_type, output_path)
        
        stats.total_downloads += 1
        
        return JSONResponse(content={
            "success": True,
            "filename": output_filename,
            "download_url": f"/download/{output_filename}",
            "title": info.title,
            "format": format_type,
            "quality": quality
        })
    except Exception as e:
        stats.errors += 1
        logger.error(f"Download error: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )

@app.get("/api/stats")
async def api_get_stats():
    """Get application statistics."""
    return JSONResponse(content={
        "success": True,
        "data": asdict(stats)
    })

@app.get("/download/{filename}")
async def download_file(filename: str):
    """Serve downloaded file."""
    file_path = Path(config.DOWNLOAD_FOLDER) / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type="application/octet-stream"
    )

# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    print("=" * 60)
    print("YouTube Downloader - Web Application")
    print("=" * 60)
    print(f"Starting server on http://{config.HOST}:{config.PORT}")
    print(f"Download folder: {config.DOWNLOAD_FOLDER}")
    print(f"Max playlist size: {config.MAX_PLAYLIST_SIZE}")
    print(f"File expiry: {config.FILE_EXPIRY_HOURS} hours")
    print("=" * 60)
    
    uvicorn.run(
        "app:app",
        host=config.HOST,
        port=config.PORT,
        reload=False,
        log_level="info"
    )
