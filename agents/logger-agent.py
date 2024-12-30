import os
import logging
import logging.handlers
from pathlib import Path
from zentropi import Agent

AGENT_NAME = "file_logger"
ENDPOINT = os.environ.get("ENDPOINT")
TOKEN = os.environ.get(f"{AGENT_NAME.upper()}_TOKEN")

logger = logging.getLogger(__name__)
logging.getLogger("apscheduler").setLevel(logging.WARNING)

file_formatter = logging.Formatter("%(asctime)s %(message)s")
# console_formatter = logging.Formatter("%(name)-15s %(levelname)-8s %(message)s")
file_size = 10 * 1024 * 1024  # 10 MB
keep_logs = 10

log_file_path = Path("frames.log")
log_file_path.parent.mkdir(parents=True, exist_ok=True)
fh = logging.handlers.RotatingFileHandler(log_file_path, "a", file_size, keep_logs)
fh.setFormatter(file_formatter)
fh.setLevel(logging.INFO)

ch = logging.StreamHandler()
# ch.setFormatter(console_formatter)
ch.setLevel(logging.INFO)

logger.addHandler(fh)
logger.addHandler(ch)
logger.setLevel(logging.INFO)

agent = Agent(AGENT_NAME)


@agent.on_event("startup")
async def start(_frame):
    logger.info(f"Starting {AGENT_NAME} agent")


@agent.on_event("shutdown")
async def stop(_frame):
    logger.info(f"Stopping {AGENT_NAME} agent")


@agent.on_event("*")
async def log_event(frame):
    logger.info(f"EVENT: {frame.name}: {frame.data} | {frame.meta}")


@agent.on_message("*")
async def log_message(frame):
    logger.info(f"MESSAGE: {frame.name}: {frame.data} | {frame.meta}")


@agent.on_request("*")
async def log_request(frame):
    logger.info(f"REQUEST: {frame.name}: {frame.data} | {frame.meta}")


agent.run(ENDPOINT, token=TOKEN)
