import os
import logging
import re
import io
from pathlib import Path
from typing import List

from aiogram import Bot, Dispatcher, types

from zentropi import Agent
from file_upload import upload_file

AGENT_NAME = "telegram"
ENDPOINT = os.environ.get("ENDPOINT")
TOKEN = os.environ.get(f"{AGENT_NAME.upper()}_TOKEN")
BOT_TOKEN = os.environ.get(f"{AGENT_NAME.upper()}_BOT_TOKEN")
CHAT_ID = os.environ.get(f"{AGENT_NAME.upper()}_CHAT_ID")

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)
logging.getLogger("apscheduler").setLevel(logging.WARNING)
logging.getLogger("aiogram").setLevel(logging.WARNING)
# logger.addHandler(logging.FileHandler(f"{AGENT_NAME}.log"))

agent = Agent(AGENT_NAME)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


def extract_hashtags(text: str) -> List[str]:
    if not text:
        return []
    # Find all hashtags in the text
    hashtags = re.findall(r"#(\w+)", text)
    return hashtags


@dp.message()
async def handle_message(message: types.Message):
    if str(message.chat.id) != CHAT_ID:
        logger.info(f"IGNORE: telegram-message: {message}")
        return
    if not message.text and message.photo:
        await handle_photo(message)
        return
    logger.info(f"+MESSAGE: telegram-message: {message.text}")
    await agent.message(
        "telegram-message",
        text=message.text,
        chat_id=message.chat.id,
        message_id=message.message_id,
    )


async def handle_photo(message: types.Message):
    if str(message.chat.id) != CHAT_ID:
        logger.info(f"IGNORE: telegram-photo: {message}")
        return
    if not message.photo:
        logger.info(f"IGNORE: telegram-photo: {message}")
        return

    caption = message.caption or "Untitled"
    tags = extract_hashtags(message.caption or "")

    photo = message.photo[-1]
    photo_file = await bot.get_file(photo.file_id)
    photo_name = Path(photo_file.file_path).name
    logger.warning(f"Photo Filename: {photo_name}")

    # Download to memory buffer
    photo_data = io.BytesIO()
    await bot.download(photo_file, destination=photo_data, seek=True)

    try:
        logger.info(f"+PHOTO: telegram-photo: {caption}")
        file_url = await upload_file(photo_data, name=photo_name)
        if file_url:
            logger.info(f"+PHOTO: uploaded {caption} -> {file_url}")
            await agent.message(
                "telegram-photo",
                file_url=file_url,
                caption=caption,
                tags=tags,
                chat_id=message.chat.id,
                message_id=message.message_id,
            )
        else:
            logger.error(f"Failed to upload photo: {caption}")
    except Exception as e:
        logger.error(f"Error uploading photo: {e}")
        await bot.send_message(
            message.chat.id,
            f"Failed to process photo: {str(e)}",
            reply_to_message_id=message.message_id,
        )


@agent.on_request("telegram-reply")
async def handle_telegram_reply(frame):
    chat_id = frame.data.get("chat_id")
    message_id = frame.data.get("message_id")
    text = frame.data.get("text")
    logger.info(f"+REPLY: telegram-reply: {text}")
    await bot.send_message(chat_id, text, reply_to_message_id=message_id)
    await agent.send(frame.reply(data={"status": "sent"}))


@agent.on_event("startup")
async def start(_frame):
    logger.info(f"Starting {AGENT_NAME} agent")
    agent.spawn(
        "telegram-bot",
        dp.start_polling(bot, handle_signals=False),
        single=True,
    )


@agent.on_event("shutdown")
async def stop(_frame):
    logger.info(f"Stopping {AGENT_NAME} agent")
    await dp.stop_polling()


agent.run(ENDPOINT, token=TOKEN)
