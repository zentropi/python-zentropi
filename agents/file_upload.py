import httpx
from pathlib import Path
from typing import Optional, Union, BinaryIO, cast


async def upload_file(
    file: Union[str, Path, BinaryIO],
    name: Optional[str] = None,
    server_url: str = "http://localhost:6912",
    timeout: float = 30.0,
) -> Optional[str]:
    """
    Upload a file to the file server and return the content-addressable filepath.

    Args:
        file: Path to file or file-like object to upload
        name: Name of the file (optional, derived from path if not provided)
        server_url: URL of the file server (default: http://localhost:6912)
        timeout: Request timeout in seconds (default: 30.0)

    Returns:
        str: File URL on success
        None: On failure

    Raises:
        httpx.RequestError: On network/connection errors
        FileNotFoundError: If source file doesn't exist
    """
    if isinstance(file, (str, Path)):
        filepath = Path(file)
        if not filepath.exists():
            raise FileNotFoundError(f"File not found: {filepath}")
        file_obj = open(filepath, "rb")
        if name is None:
            name = filepath.name
    else:
        file_obj = cast(BinaryIO, file)
        if name is None:
            name = "unnamed_file"

    files = {"file": file_obj}

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{server_url}/upload/{name}", files=files, timeout=timeout
            )
            response.raise_for_status()
            result = response.json()
            return result.get("file_url")
    finally:
        if isinstance(file, (str, Path)):
            file_obj.close()


# Example usage:

# import asyncio
# from file_upload import upload_file


# async def main():
#     try:
#         filepath = await upload_file("Procfile")
#         print(f"Uploaded to: {filepath}")
#     except (httpx.RequestError, FileNotFoundError) as e:
#         print(f"Upload failed: {e}")


# asyncio.run(main())
