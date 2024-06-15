bot_token = '6180531728:AAFZDiE53W7qYj391PYDhwos5xU97UYcWbs'

import asyncio
from pyrogram import Client, filters
from pytube import YouTube
from pytube.exceptions import VideoUnavailable
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from datetime import datetime, timedelta

api_id = 12590615
api_hash = '048a88c8c193063ab850327dbbc25ca5'
#bot_token = '6219469921:AAE6uYHAnpPdfmMaghOYTSz-lEPTrmbhtv0'
channel_username = 'mugu_bots'  # Updated channel name

app = Client("yt_bot", api_id=api_id, api_hash=api_hash, bot_token=bot_token)

# Create a dictionary to store the last message time for each user
cooldowns = {}

@app.on_message(filters.command("start") | filters.command("help"))
async def command_handler(client, message):
    if message.command[0] == "start":
        await message.reply("👋 Welcome to the YouTube Downloader bot! Just send me a YouTube video link, and I'll provide you with download options.")
    elif message.command[0] == "help":
        help_message = "ℹ️ Here's how to use this bot:\n\n" \
                       "1. Send me a YouTube video link.\n" \
                       "2. I'll provide you with download options for the video, including MP4 and audio-only formats.\n" \
                       "3. Choose the format you want and click the respective button to start the download.\n\n" \
                       "Available commands:\n" \
                       "/start - Start the bot\n" \
                       "/help - Display this help message\n" \
                       "/waiting_time - Check remaining waiting time for sending YouTube links"
        await message.reply(help_message)

@app.on_message(filters.command("waiting_time"))
async def waiting_time_command(client, message):
    user_id = message.from_user.id
    time_elapsed = datetime.now() - cooldowns[user_id]
    remaining_time = max(0, 120 - time_elapsed.total_seconds())

    if user_id in cooldowns and int(remaining_time):
        await message.reply(f"⏳ Remaining time for the next URL parsing: {int(remaining_time)} seconds")
    else:
        await message.reply("👍 You can send a YouTube link now, there's no waiting time.")

@app.on_message(filters.regex(r"(https?://(?:www\.)?youtu\.be/|https?://(?:www\.)?youtube\.com/watch\?v=)([0-9A-Za-z_-]{11})"))
async def auto_detect_youtube_url(client, message):
    user_id = message.from_user.id

    if user_id in cooldowns and datetime.now() - cooldowns[user_id] < timedelta(minutes=2):
        # User sent a URL during the waiting time, inform them to wait
        time_elapsed = datetime.now() - cooldowns[user_id]
        remaining_time = max(0, 120 - time_elapsed.total_seconds())
        await message.reply(f"⏳ Please wait for {int(remaining_time)} seconds before sending another YouTube link.")
    else:
        processing_msg = await message.reply("⌛ Processing the video...")
        url = message.matches[0].group(0)
        id = message.id

        try:
            yt = YouTube(url)
            title = yt.title
            thumbnail_url = yt.thumbnail_url
            views = yt.views
            upload_date = yt.publish_date.strftime("%b %d, %Y")
            channel_name = yt.author
            formatted_views = f"{views:,}"  # Use commas to format views

            # Create a formatted caption using Markdown with different icons
            caption = f"🎥 **Title**: {title}\n" \
                      f"👁️ **Views**: {formatted_views}\n" \
                      f"📅 **Upload Date**: {upload_date}\n" \
                      f"👤 **Channel Name**: [{channel_name}]({yt.channel_url})"

            download_buttons = create_download_buttons(yt)

            # Send the video information and download buttons
            await processing_msg.delete()

            download_msg = await message.reply_photo(
                thumbnail_url,
                caption=caption,
                reply_to_message_id=id,
                reply_markup=download_buttons
            )

            # Update the cooldown for the user
            cooldowns[user_id] = datetime.now()
        except VideoUnavailable:
            await processing_msg.edit("⚠️ The provided video is not available.")
        except Exception as e:
            await processing_msg.edit(f"❌ An error occurred: {str(e)}")

def create_download_buttons(yt):
    quality_levels = ["720p", "360p"]
    download_buttons = []

    for quality_level in quality_levels:
        stream = yt.streams.filter(res=quality_level, type="video").first()
        if stream:
            button_text = f"{quality_level} 📥 ({stream.filesize / (1024 * 1024):.2f} MB)"
            button = InlineKeyboardButton(button_text, url=stream.url)
            download_buttons.append([button])

    audio_stream = yt.streams.filter(only_audio=True).first()
    if audio_stream:
        audio_button_text = f"Audio 🎵 ({audio_stream.filesize / (1024 * 1024):.2f} MB)"
        audio_button = InlineKeyboardButton(audio_button_text, url=audio_stream.url)
        download_buttons.append([audio_button])

    return InlineKeyboardMarkup(download_buttons)

app.run()
