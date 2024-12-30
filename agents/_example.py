import os
import logging
from zentropi import Agent

AGENT_NAME = "example"
ENDPOINT = os.environ.get("ENDPOINT")
TOKEN = os.environ.get(f"{AGENT_NAME.upper()}_TOKEN")

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)
logging.getLogger("apscheduler").setLevel(logging.WARNING)
# logger.addHandler(logging.FileHandler(f"{AGENT_NAME}.log"))

agent = Agent(AGENT_NAME)


@agent.on_event("startup")
async def start(_frame):
    logger.info(f"Starting {AGENT_NAME} agent")


@agent.on_event("shutdown")
async def stop(_frame):
    logger.info(f"Stopping {AGENT_NAME} agent")


@agent.on_event("hello")
async def hello(frame):
    logger.info(f"Hello, {frame.data.get('name', 'world')}!")


agent.run(ENDPOINT, token=TOKEN)
