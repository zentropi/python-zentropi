import os
import logging
import mimetypes
from io import BytesIO

import httpx
from mastodon import Mastodon

from zentropi import Agent

AGENT_NAME = "mastodon"
ENDPOINT = os.environ.get("ENDPOINT")
TOKEN = os.environ.get(f"{AGENT_NAME.upper()}_TOKEN")
INSTANCE = os.environ.get(f"{AGENT_NAME.upper()}_INSTANCE")
ACCESS_TOKEN = os.environ.get(f"{AGENT_NAME.upper()}_ACCESS_TOKEN")

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)
logging.getLogger("apscheduler").setLevel(logging.WARNING)
# logger.addHandler(logging.FileHandler(f"{AGENT_NAME}.log"))

agent = Agent(AGENT_NAME)
mastodon = Mastodon(
    access_token=ACCESS_TOKEN,
    api_base_url=INSTANCE,
)


@agent.on_event("startup")
async def start(_frame):
    logger.info(f"Starting {AGENT_NAME} agent")


@agent.on_event("shutdown")
async def stop(_frame):
    logger.info(f"Stopping {AGENT_NAME} agent")


@agent.on_request("mastodon-post")
async def post_to_mastodon(frame):
    text = frame.data.get("text")
    mastodon.status_post(text, visibility="unlisted")
    await agent.send(frame.reply("mastodon-posted"))


@agent.on_request("mastodon-post-photo")
async def post_photo_to_mastodon(frame):
    file_url = frame.data["file_url"]
    file_name = file_url.split("/")[-1]
    mime_type = mimetypes.guess_type(file_name)[0]
    caption = frame.data["caption"]
    tags = frame.data["tags"]

    # Download image
    async with httpx.AsyncClient() as client:
        response = await client.get(file_url)
        image_data = BytesIO(response.content)

    # Upload media
    media_dict = mastodon.media_post(
        media_file=image_data,
        description=caption,
        file_name=file_name,
        mime_type=mime_type,
    )

    # Format hashtags
    hashtags = " ".join(f"#{tag}" for tag in tags)
    status_text = f"{hashtags}"

    # Post status with media
    mastodon.status_post(
        status=status_text, media_ids=[media_dict["id"]], visibility="public"
    )

    await agent.send(frame.reply("mastodon-posted-photo"))


agent.run(ENDPOINT, token=TOKEN)
