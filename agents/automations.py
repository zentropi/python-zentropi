import os
import logging
from zentropi import Agent

AGENT_NAME = "automations"
ENDPOINT = os.environ.get("ENDPOINT")
TOKEN = os.environ.get(f"{AGENT_NAME.upper()}_TOKEN")

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)
logging.getLogger("apscheduler").setLevel(logging.WARNING)
# logger.addHandler(logging.FileHandler(f"{AGENT_NAME}.log"))

agent = Agent(AGENT_NAME)


@agent.on_event("startup")
async def start(_frame):
    logger.info("Starting automations agent")


@agent.on_event("shutdown")
async def stop(_frame):
    logger.info("Stopping automations agent")


@agent.on_message("telegram-message")
async def handle_telegram_message(frame):
    if frame.data["text"] == "/start":
        await agent.request(
            "telegram-reply",
            text="Welcome to Zycelium! Send me a photo with a caption and hashtags.",
            chat_id=frame.data["chat_id"],
            message_id=frame.data["message_id"],
            timeout=3,
        )
    elif frame.data["text"].startswith("/post"):
        try:
            await agent.request(
                "mastodon-post",
                text=frame.data["text"][5:].strip(),
                timeout=3,
            )
            await agent.request(
                "telegram-reply",
                text="Posted to Mastodon...",
                chat_id=frame.data["chat_id"],
                message_id=frame.data["message_id"],
                timeout=3,
            )
        except TimeoutError:
            await agent.request(
                "telegram-reply",
                text="Mastodon is taking too long to respond.",
                chat_id=frame.data["chat_id"],
                message_id=frame.data["message_id"],
                timeout=3,
            )
    else:
        await agent.request(
            "telegram-reply",
            text="I'm sorry, I don't understand that command.",
            chat_id=frame.data["chat_id"],
            message_id=frame.data["message_id"],
            timeout=3,
        )


@agent.on_message("telegram-photo")
async def handle_telegram_photo(frame):
    file_url = frame.data["file_url"]
    caption = frame.data["caption"]
    tags = frame.data["tags"]
    try:
        await agent.request(
            "mastodon-post-photo",
            file_url=file_url,
            caption=caption,
            tags=tags,
            timeout=8,
        )
        await agent.request(
            "telegram-reply",
            text="Photo posted to Mastodon...",
            chat_id=frame.data["chat_id"],
            message_id=frame.data["message_id"],
            timeout=3,
        )
    except TimeoutError:
        await agent.request(
            "telegram-reply",
            text="Mastodon is taking too long to respond.",
            chat_id=frame.data["chat_id"],
            message_id=frame.data["message_id"],
            timeout=3,
        )


agent.run(ENDPOINT, token=TOKEN)
