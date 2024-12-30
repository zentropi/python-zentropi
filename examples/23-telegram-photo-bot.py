import os
import re
from pathlib import Path
from typing import List

from aiogram import Bot, Dispatcher, types
from zentropi import Agent

# Configure your Telegram bot token and channel ID here
TELEGRAM_BOT_TOKEN = ""
ALLOWED_CHAT_ID = ""  # Can be group/channel/user ID

# Configure photo storage path
PHOTO_STORAGE_PATH = Path.cwd() / "static/photos"
PHOTO_STORAGE_PATH.mkdir(parents=True, exist_ok=True)

# Initialize bot and dispatcher
bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()

# Initialize Zentropi agent
agent = Agent("test-agent")


def extract_hashtags(text: str) -> List[str]:
    if not text:
        return []
    # Find all hashtags in the text
    hashtags = re.findall(r"#(\w+)", text)
    return hashtags


@dp.message()
async def handle_photo(message: types.Message):
    if not message.photo:
        return
    # Check if message is from allowed chat
    if str(message.chat.id) != ALLOWED_CHAT_ID:
        return

    # Get photo caption and tags
    caption = message.caption or "Untitled"
    tags = extract_hashtags(message.caption or "")
    tags_str = ", ".join(tags)

    # Get the largest photo size
    photo = message.photo[-1]

    # Generate a unique filename using message ID
    file_ext = "jpg"  # Telegram always converts photos to JPEG
    filename = f"telegram_{message.message_id}.{file_ext}"
    filepath = PHOTO_STORAGE_PATH / filename

    # Download the photo
    photo_file = await bot.get_file(photo.file_id)
    photo_path = Path(photo_file.file_path)
    await bot.download_file(photo_path, str(filepath))

    # Remove hashtags from caption
    clean_caption = re.sub(r"#\w+", "", caption).strip()
    if not clean_caption:
        clean_caption = "Untitled"

    # Emit event to gallery agent with relative path from static directory
    relative_path = f"static/photos/{filename}"
    await agent.event(
        "public-photo-uploaded",
        data={
            "filepath": relative_path,
            "caption": clean_caption,
            "tags": tags_str,  # Send the joined string instead of list
        },
    )

    # Confirm to user
    await message.reply(
        f"Photo saved with caption: {clean_caption}\n" f"Tags: {tags_str or 'No tags'}"
    )


@agent.on_event("startup")
async def startup(frame):
    agent.spawn("tgpolling", dp.start_polling(bot, handle_signals=False), single=True)
    print("Telegram agent started")


@agent.on_event("shutdown")
async def shutdown(frame):
    await dp.stop_polling()
    print("Telegram agent stopped")
    agent.stop()


if __name__ == "__main__":
    agent.run(
        "ws://localhost:26514/",
        "test-token",
        handle_signals=True,
    )
