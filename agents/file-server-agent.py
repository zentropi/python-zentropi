import asyncio
import dbm
import os
import hashlib
import json
import logging
import mimetypes
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import aiofiles
from quart import Quart, request, send_file as quart_send_file

from zentropi import Agent

AGENT_NAME = "file_server"
ENDPOINT = os.environ.get("ENDPOINT")
TOKEN = os.environ.get(f"{AGENT_NAME.upper()}_TOKEN")

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)
logging.getLogger("apscheduler").setLevel(logging.WARNING)
# logger.addHandler(logging.FileHandler(f"{AGENT_NAME}.log"))

agent = Agent(AGENT_NAME)
app = Quart(__name__)


@dataclass
class FileMetadata:
    original_filename: str
    content_type: Optional[str] = None
    upload_timestamp: Optional[float] = None

    def to_json(self) -> str:
        return json.dumps(self.__dict__)

    @classmethod
    def from_json(cls, data: str) -> "FileMetadata":
        return cls(**json.loads(data))


class MetadataStore:
    def __init__(self, db_path: str = "files/metadata.db"):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    def save(self, file_hash: str, metadata: FileMetadata):
        with dbm.open(self.db_path, "c") as db:
            db[file_hash] = metadata.to_json()

    def get(self, file_hash: str) -> Optional[FileMetadata]:
        try:
            with dbm.open(self.db_path, "r") as db:
                if file_hash in db:
                    return FileMetadata.from_json(db[file_hash].decode())
        except Exception:
            return None
        return None


metadata_store = MetadataStore()


@agent.on_event("startup")
async def start(_frame):
    logger.info(f"Starting {AGENT_NAME} agent")
    # Ensure metadata store is initialized
    Path("files").mkdir(exist_ok=True)


@agent.on_event("shutdown")
async def stop(_frame):
    logger.info(f"Stopping {AGENT_NAME} agent")


@app.before_serving
async def before_serving():
    logger.info("Starting file server")
    asyncio.create_task(agent.start(ENDPOINT, token=TOKEN, handle_signals=False))


@app.after_serving
async def after_serving():
    logger.info("Stopping file server")
    agent.stop()


def get_mimetype(filename: str) -> str:
    """Get mimetype based on file extension."""
    mimetype, _ = mimetypes.guess_type(filename)
    return mimetype or "application/octet-stream"


@app.route("/upload/<filename>", methods=["POST"])
async def upload_file(filename):
    """
    Content-addressable file upload.

    Stores on filesystem as `files/<first-char-of-hash>/<first-two-chars-of-hash>/<hash>.<extension>`.
    """
    try:
        files = await request.files
        if "file" not in files:
            return {"status": "error", "message": "No file provided"}, 400

        uploaded_file = files["file"]
        logger.info(f"Uploading file: {filename}")

        # Calculate SHA-256 hash of file content
        content = uploaded_file.read()
        file_hash = hashlib.sha256(content).hexdigest()

        file_extension = filename.split(".")[-1] if "." in filename else None

        # Create directory structure
        base_path = Path("files")
        file_dir = base_path / file_hash[0] / file_hash[1:3]
        file_dir.mkdir(parents=True, exist_ok=True)

        # Save the file
        file_path = file_dir / (
            f"{file_hash}.{file_extension}" if file_extension else file_hash
        )

        async with aiofiles.open(file_path, "wb") as f:
            await f.write(content)

        # Detect mimetype from filename
        content_type = get_mimetype(filename)

        # Save metadata
        metadata = FileMetadata(
            original_filename=filename,
            content_type=content_type,
            upload_timestamp=asyncio.get_event_loop().time(),
        )
        metadata_store.save(file_hash, metadata)

        relative_path = str(file_path.relative_to(base_path))
        logger.info(f"EVENT: file-uploaded: {relative_path} (original: {filename})")
        await agent.emit(
            "file-uploaded",
            filepath=relative_path,
            original_filename=filename,
            content_type=content_type,
        )
        return {
            "status": "ok",
            "file_url": (
                f"http://localhost:6912/{file_hash}.{file_extension}"
                if file_extension
                else f"http://localhost:6912/{file_hash}"
            ),
            "original_filename": filename,
            "content_type": content_type,
        }

    except Exception as e:
        logger.error(f"Upload failed: {str(e)}")
        return {"status": "error", "message": str(e)}, 500


async def send_file_with_original_name(path: str, file_hash: str):
    full_path = os.path.join("files", path)
    if not os.path.exists(full_path):
        return {"status": "error", "message": "File not found"}, 404

    metadata = metadata_store.get(file_hash)
    if metadata is None:
        return {"status": "error", "message": "File metadata not found"}, 404
    return await quart_send_file(
        full_path,
        mimetype=metadata.content_type,
        attachment_filename=metadata.original_filename,
    )


@app.route("/<hash>")
async def send_file_without_extension(hash):
    try:
        path = os.path.join(hash[0], hash[1:3], hash)
        return await send_file_with_original_name(path, hash)
    except Exception as e:
        logger.error(f"File retrieval failed: {str(e)}")
        return {"status": "error", "message": "File not found"}, 404


@app.route("/<hash>.<extension>")
async def send_file_with_extension(hash, extension):
    try:
        # First try with extension
        path = os.path.join(hash[0], hash[1:3], f"{hash}.{extension}")
        if os.path.exists(os.path.join("files", path)):
            return await send_file_with_original_name(path, hash)
        # If not found, try without extension
        return await send_file_without_extension(hash)
    except Exception as e:
        logger.error(f"File retrieval failed: {str(e)}")
        return {"status": "error", "message": "File not found"}, 404


if __name__ == "__main__":
    app.run("0.0.0.0", 6912)
