import asyncio
import base64
import mimetypes

import httpx
from fastapi import HTTPException


def parse_data_uri(data_uri: str) -> tuple[str, str]:
    if not data_uri.startswith("data:"):
        raise ValueError("Invalid data URI")
    header, data = data_uri.split(",", 1)
    mime_type = header[5:].split(";")[0]
    return mime_type, data


def build_data_uri(mime_type: str, base64_data: str) -> str:
    return f"data:{mime_type};base64,{base64_data}"

def guess_mime_type(filename: str = None, default="application/octet-stream") -> str:
    if filename:
        mime_type, _ = mimetypes.guess_type(filename)
        if mime_type:
            return mime_type
    return default


def _encode_bytes_to_base64_text(content: bytes) -> str:
    return base64.b64encode(content).decode("utf-8")


async def fetch_url_content(url: str) -> tuple[bytes, str]:
    transport = httpx.AsyncHTTPTransport(http2=True, verify=False, retries=1)
    async with httpx.AsyncClient(transport=transport) as client:
        try:
            response = await client.get(url, timeout=30.0)
            response.raise_for_status()
            content_type = response.headers.get("Content-Type", "").split(";")[0].strip()
            return response.content, content_type
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to fetch file from url: {url}. Error: {str(e)}")


async def get_base64_file(file_url_or_data: str) -> tuple[str, str]:
    """返回 (base64_data_with_prefix, mime_type)"""
    if file_url_or_data.startswith("http://") or file_url_or_data.startswith("https://"):
        content, content_type = await fetch_url_content(file_url_or_data)
        b64_data = await asyncio.to_thread(_encode_bytes_to_base64_text, content)
        if not content_type:
            content_type = guess_mime_type(file_url_or_data)
        return build_data_uri(content_type, b64_data), content_type
    elif file_url_or_data.startswith("data:"):
        mime_type, _ = parse_data_uri(file_url_or_data)
        return file_url_or_data, mime_type
    else:
        return file_url_or_data, "application/octet-stream"
