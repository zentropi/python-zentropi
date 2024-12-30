import asyncio
import os
import logging

import dotenv
from quart import Quart, request

from zentropi import Agent


dotenv.load_dotenv()
AGENT_NAME = "example"
ENDPOINT = os.environ.get("ENDPOINT")
TOKEN = os.environ.get(f"{AGENT_NAME.upper()}_TOKEN")

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)
logging.getLogger("apscheduler").setLevel(logging.WARNING)
# logger.addHandler(logging.FileHandler(f"{AGENT_NAME}.log"))

agent = Agent(AGENT_NAME)
app = Quart(__name__)


@agent.on_event("startup")
async def start(_frame):
    logger.info(f"Starting {AGENT_NAME} agent")
    await agent.emit("ohai")


@agent.on_event("shutdown")
async def stop(_frame):
    logger.info(f"Stopping {AGENT_NAME} agent")


@agent.on_event("hello")
async def hello(frame):
    response = f"Hello, {frame.data.get('name', 'world')}!"
    logger.info(response)
    await agent.emit(response)


@app.before_serving
async def startup():
    asyncio.create_task(agent.start(ENDPOINT, token=TOKEN, handle_signals=False))


@app.after_serving
async def shutdown():
    agent.stop()


app.run(host="0.0.0.0", port=5000)
