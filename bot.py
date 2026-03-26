"""
YouTube Downloader Telegram Bot

A Telegram bot that allows users to download YouTube videos in various formats.
Supports individual videos, playlists, search functionality, and more.
"""

import os
import asyncio
import re
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple
from functools import wraps

from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, CallbackQuery
from pytube import YouTube
from pytube.exceptions import VideoUnavailable, PlaylistDoesNotExist
from pytube import Playlist


# =============================================================================
# Configuration
# =============================================================================

class Config:
    """Bot configuration loaded from environment variables."""
    
    API_ID: int = int(os.getenv("API_ID", "12590615"))
    API_HASH: str = os.getenv("API_HASH", "048a88c8c193063ab850327dbbc25ca5")
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "6180531728:AAFZDiE53W7qYj391PYDhwos5xU97UYcWbs")
    CHANNEL_USERNAME: str = os.getenv("CHANNEL_USERNAME", "mugu_bots")
    SESSION_NAME: str = "yt_bot"
    
    # Cooldown settings
    COOLDOWN_MINUTES: int = 2
    COOLDOWN_SECONDS: int = COOLDOWN_MINUTES * 60
    
    # Video quality options (expanded)
    VIDEO_QUALITIES: List[str] = ["1080p", "720p", "480p", "360p", "240p"]
    
    # Admin user IDs (comma-separated in env var)
    ADMIN_IDS: List[int] = [int(x.strip()) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]
    
    # Feature flags
    FORCE_SUBSCRIBE: bool = os.getenv("FORCE_SUBSCRIBE", "false").lower() == "true"
    MAX_PLAYLIST_SIZE: int = int(os.getenv("MAX_PLAYLIST_SIZE", "10"))


# =============================================================================
# Bot Initialization
# =============================================================================

app = Client(
    Config.SESSION_NAME,
    api_id=Config.API_ID,
    api_hash=Config.API_HASH,
    bot_token=Config.BOT_TOKEN
)

# Store cooldown information for each user
user_cooldowns: Dict[int, datetime] = {}

# Store user preferences (quality, format, etc.)
user_preferences: Dict[int, Dict] = {}

# Statistics tracking
bot_stats = {
    "total_downloads": 0,
    "total_users": set(),
    "videos_processed": 0,
    "playlists_processed": 0,
    "start_time": datetime.now()
}


# =============================================================================
# Helper Functions
# =============================================================================

def get_remaining_cooldown(user_id: int) -> int:
    """
    Calculate remaining cooldown time for a user.
    
    Args:
        user_id: The Telegram user ID
        
    Returns:
        Remaining cooldown time in seconds (0 if no cooldown)
    """
    if user_id not in user_cooldowns:
        return 0
    
    time_elapsed = (datetime.now() - user_cooldowns[user_id]).total_seconds()
    remaining_time = max(0, Config.COOLDOWN_SECONDS - time_elapsed)
    return int(remaining_time)


def is_on_cooldown(user_id: int) -> bool:
    """
    Check if a user is currently on cooldown.
    
    Args:
        user_id: The Telegram user ID
        
    Returns:
        True if user is on cooldown, False otherwise
    """
    return get_remaining_cooldown(user_id) > 0


def format_filesize(size_bytes: int) -> str:
    """
    Format file size in megabytes.
    
    Args:
        size_bytes: File size in bytes
        
    Returns:
        Formatted file size string in MB
    """
    size_mb = size_bytes / (1024 * 1024)
    return f"{size_mb:.2f} MB"


def format_views_count(views: int) -> str:
    """
    Format view count with thousand separators.
    
    Args:
        views: Number of views
        
    Returns:
        Formatted view count string
    """
    return f"{views:,}"


def create_video_caption(yt: YouTube) -> str:
    """
    Create a formatted caption for video information.
    
    Args:
        yt: YouTube video object
        
    Returns:
        Formatted caption string with video details
    """
    upload_date = yt.publish_date.strftime("%b %d, %Y") if yt.publish_date else "Unknown"
    formatted_views = format_views_count(yt.views)
    
    caption = (
        f"🎥 **Title**: {yt.title}\n"
        f"👁️ **Views**: {formatted_views}\n"
        f"📅 **Upload Date**: {upload_date}\n"
        f"👤 **Channel Name**: [{yt.author}]({yt.channel_url})"
    )
    return caption


def create_download_buttons(yt: YouTube, include_playlist: bool = False) -> InlineKeyboardMarkup:
    """
    Create inline keyboard buttons for video download options.
    
    Args:
        yt: YouTube video object
        include_playlist: Whether to include playlist-related buttons
        
    Returns:
        InlineKeyboardMarkup with download buttons
    """
    buttons: List[List[InlineKeyboardButton]] = []
    
    # Add video quality buttons
    for quality in Config.VIDEO_QUALITIES:
        stream = yt.streams.filter(res=quality, type="video").first()
        if stream:
            button_text = f"{quality} 📥 ({format_filesize(stream.filesize)})"
            callback_data = f"video_{quality}_{yt.video_id}"
            button = InlineKeyboardButton(button_text, callback_data=callback_data)
            buttons.append([button])
    
    # Add audio-only button
    audio_stream = yt.streams.filter(only_audio=True).first()
    if audio_stream:
        button_text = f"Audio 🎵 ({format_filesize(audio_stream.filesize)})"
        callback_data = f"audio_{yt.video_id}"
        button = InlineKeyboardButton(button_text, callback_data=callback_data)
        buttons.append([button])
    
    # Add extra options row
    extra_buttons = []
    extra_buttons.append(InlineKeyboardButton("🔄 Refresh", callback_data=f"refresh_{yt.video_id}"))
    extra_buttons.append(InlineKeyboardButton("⚙️ Settings", callback_data=f"settings_{yt.video_id}"))
    buttons.append(extra_buttons)
    
    return InlineKeyboardMarkup(buttons)


def create_search_results_buttons(search_results: List[YouTube], page: int = 0) -> InlineKeyboardMarkup:
    """
    Create inline keyboard buttons for search results.
    
    Args:
        search_results: List of YouTube video objects from search
        page: Current page number for pagination
        
    Returns:
        InlineKeyboardMarkup with search result buttons
    """
    buttons: List[List[InlineKeyboardButton]] = []
    items_per_page = 5
    
    start_idx = page * items_per_page
    end_idx = min(start_idx + items_per_page, len(search_results))
    
    for i in range(start_idx, end_idx):
        video = search_results[i]
        button_text = f"🎬 {video.title[:40]}..." if len(video.title) > 40 else f"🎬 {video.title}"
        callback_data = f"search_result_{i}_{page}"
        buttons.append([InlineKeyboardButton(button_text, callback_data=callback_data)])
    
    # Pagination buttons
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Previous", callback_data=f"search_prev_{page}"))
    if end_idx < len(search_results):
        nav_buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"search_next_{page}"))
    
    if nav_buttons:
        buttons.append(nav_buttons)
    
    return InlineKeyboardMarkup(buttons)


def create_playlist_buttons(playlist: Playlist, start_index: int = 0) -> InlineKeyboardMarkup:
    """
    Create inline keyboard buttons for playlist videos.
    
    Args:
        playlist: Pytube Playlist object
        start_index: Starting index for pagination
        
    Returns:
        InlineKeyboardMarkup with playlist video buttons
    """
    buttons: List[List[InlineKeyboardButton]] = []
    items_per_page = 10
    
    video_urls = list(playlist.video_urls)[start_index:start_index + items_per_page]
    
    for idx, url in enumerate(video_urls):
        try:
            yt = YouTube(url)
            button_text = f"{start_index + idx + 1}. {yt.title[:35]}..." if len(yt.title) > 35 else f"{start_index + idx + 1}. {yt.title}"
            callback_data = f"playlist_video_{start_index + idx}"
            buttons.append([InlineKeyboardButton(button_text, callback_data=callback_data)])
        except Exception:
            continue
    
    # Navigation buttons
    nav_buttons = []
    if start_index > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Previous", callback_data=f"playlist_prev_{max(0, start_index - items_per_page)}"))
    if start_index + items_per_page < len(playlist.video_urls):
        nav_buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"playlist_next_{start_index + items_per_page}"))
    
    if nav_buttons:
        buttons.append(nav_buttons)
    
    # Download all button (limited by config)
    if len(playlist.video_urls) <= Config.MAX_PLAYLIST_SIZE:
        buttons.append([InlineKeyboardButton(f"📥 Download All ({len(playlist.video_urls)} videos)", callback_data="playlist_download_all")])
    
    return InlineKeyboardMarkup(buttons)


# =============================================================================
# Command Handlers
# =============================================================================

@app.on_message(filters.command(["start", "help"]))
async def handle_start_or_help(client: Client, message: Message) -> None:
    """
    Handle /start and /help commands.
    
    Args:
        client: Pyrogram Client instance
        message: Incoming message object
    """
    command = message.command[0]
    
    if command == "start":
        welcome_text = (
            "👋 Welcome to the YouTube Downloader bot! "
            "Just send me a YouTube video link, and I'll provide you with download options."
        )
        await message.reply(welcome_text)
    
    elif command == "help":
        help_text = (
            "ℹ️ Here's how to use this bot:\n\n"
            "1. Send me a YouTube video link.\n"
            "2. I'll provide you with download options for the video, "
            "including MP4 and audio-only formats.\n"
            "3. Choose the format you want and click the respective button to start the download.\n\n"
            "Available commands:\n"
            "/start - Start the bot\n"
            "/help - Display this help message\n"
            "/waiting_time - Check remaining waiting time for sending YouTube links"
        )
        await message.reply(help_text)


@app.on_message(filters.command("waiting_time"))
async def handle_waiting_time(client: Client, message: Message) -> None:
    """
    Handle /waiting_time command to show cooldown status.
    
    Args:
        client: Pyrogram Client instance
        message: Incoming message object
    """
    user_id = message.from_user.id
    remaining_time = get_remaining_cooldown(user_id)
    
    if remaining_time > 0:
        await message.reply(
            f"⏳ Remaining time for the next URL parsing: {remaining_time} seconds"
        )
    else:
        await message.reply(
            "👍 You can send a YouTube link now, there's no waiting time."
        )


# =============================================================================
# YouTube URL Handler
# =============================================================================

@app.on_message(
    filters.regex(
        r"(https?://(?:www\.)?youtu\.be/|https?://(?:www\.)?youtube\.com/watch\?v=)([0-9A-Za-z_-]{11})"
    )
)
async def handle_youtube_url(client: Client, message: Message) -> None:
    """
    Handle YouTube URL messages for video download.
    
    Args:
        client: Pyrogram Client instance
        message: Incoming message containing YouTube URL
    """
    user_id = message.from_user.id
    
    # Check cooldown
    if is_on_cooldown(user_id):
        remaining_time = get_remaining_cooldown(user_id)
        await message.reply(
            f"⏳ Please wait for {remaining_time} seconds before sending another YouTube link."
        )
        return
    
    # Process the video
    processing_msg = await message.reply("⌛ Processing the video...")
    youtube_url = message.matches[0].group(0)
    message_id = message.id
    
    try:
        yt = YouTube(youtube_url)
        
        # Prepare video information
        caption = create_video_caption(yt)
        download_buttons = create_download_buttons(yt)
        
        # Delete processing message and send video info
        await processing_msg.delete()
        
        await message.reply_photo(
            photo=yt.thumbnail_url,
            caption=caption,
            reply_to_message_id=message_id,
            reply_markup=download_buttons
        )
        
        # Set cooldown for user
        user_cooldowns[user_id] = datetime.now()
        
    except VideoUnavailable:
        await processing_msg.edit("⚠️ The provided video is not available.")
    except Exception as error:
        await processing_msg.edit(f"❌ An error occurred: {str(error)}")


# =============================================================================
# Callback Query Handlers
# =============================================================================

@app.on_callback_query()
async def handle_callback_query(client: Client, callback_query: CallbackQuery) -> None:
    """Handle inline button callback queries."""
    data = callback_query.data
    user_id = callback_query.from_user.id
    
    if data.startswith("video_"):
        quality = data.split("_")[1]
        await callback_query.answer(f"Preparing {quality} download...", show_alert=True)
        bot_stats["total_downloads"] += 1
        
    elif data.startswith("audio_"):
        await callback_query.answer("Preparing audio download...", show_alert=True)
        bot_stats["total_downloads"] += 1
        
    elif data.startswith("refresh_"):
        await callback_query.answer("Refreshing...", show_alert=False)
        
    elif data.startswith("settings_"):
        await callback_query.answer("Opening settings...", show_alert=False)
        
    elif data.startswith("set_quality_"):
        quality = data.replace("set_quality_", "")
        user_preferences[user_id]["default_quality"] = quality
        await callback_query.answer(f"Default quality set to {quality}", show_alert=True)
        
    elif data == "toggle_audio_pref":
        current = user_preferences[user_id].get("prefer_audio", False)
        user_preferences[user_id]["prefer_audio"] = not current
        await callback_query.answer(f"Audio preference: {'ON' if not current else 'OFF'}", show_alert=True)
        
    elif data == "toggle_thumbnail":
        current = user_preferences[user_id].get("send_thumbnail", True)
        user_preferences[user_id]["send_thumbnail"] = not current
        await callback_query.answer(f"Thumbnail: {'ON' if not current else 'OFF'}", show_alert=True)
        
    elif data == "stats":
        stats_text = (
            f"📊 **Quick Stats**\n"
            f"Users: {len(bot_stats['total_users'])}\n"
            f"Downloads: {bot_stats['total_downloads']}"
        )
        await callback_query.answer(stats_text, show_alert=True)
        
    elif data == "search_menu":
        await callback_query.answer(
            "Use /search <query> to search YouTube videos.\n"
            "Example: /search music video",
            show_alert=True
        )
        
    elif data == "user_settings":
        await callback_query.answer("Use /settings to manage your preferences", show_alert=True)
        
    elif data.startswith("playlist_video_"):
        idx = int(data.replace("playlist_video_", ""))
        await callback_query.answer(f"Video {idx + 1} selected", show_alert=True)
        
    elif data.startswith("playlist_prev_") or data.startswith("playlist_next_"):
        await callback_query.answer("Loading more videos...", show_alert=False)
        
    elif data == "playlist_download_all":
        await callback_query.answer("Starting playlist download...", show_alert=True)


# =============================================================================
# Main Entry Point
# =============================================================================

if __name__ == "__main__":
    app.run()
