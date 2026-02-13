from open_webui.routers.images import (
    get_image_data,
    upload_image,
)

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    UploadFile,
)
from typing import Optional
from pathlib import Path

from open_webui.storage.provider import Storage

from open_webui.models.chats import Chats
from open_webui.models.files import Files
from open_webui.routers.files import upload_file_handler
from open_webui.retrieval.web.utils import validate_url

import mimetypes
import base64
import io
import re

import requests

BASE64_IMAGE_URL_PREFIX = re.compile(r"data:image/\w+;base64,", re.IGNORECASE)
BASE64_DATA_URI_PATTERN = re.compile(
    r"data:([^;]+)((?:;(?!base64,)[^;]*)*);\s*base64,(.+)", re.DOTALL
)
DATA_URI_FILENAME_RE = re.compile(r";filename=([^;]+)")
MARKDOWN_IMAGE_URL_PATTERN = re.compile(r"!\[(.*?)\]\((.+?)\)", re.IGNORECASE)

# Register common office MIME types that may not be present on all systems
mimetypes.add_type(
    "application/vnd.openxmlformats-officedocument.presentationml.presentation", ".pptx"
)
mimetypes.add_type(
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", ".xlsx"
)
mimetypes.add_type(
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document", ".docx"
)

# Fallback extension map for MIME types that mimetypes.guess_extension() may not resolve
MIME_EXTENSION_FALLBACK = {
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": ".pptx",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/vnd.ms-powerpoint": ".ppt",
    "application/vnd.ms-excel": ".xls",
    "application/vnd.ms-word": ".doc",
    "text/csv": ".csv",
    "application/pdf": ".pdf",
    "application/zip": ".zip",
    "application/json": ".json",
}


def get_image_base64_from_url(url: str) -> Optional[str]:
    try:
        if url.startswith("http"):
            # Validate URL to prevent SSRF attacks against local/private networks
            validate_url(url)
            # Download the image from the URL
            response = requests.get(url)
            response.raise_for_status()
            image_data = response.content
            encoded_string = base64.b64encode(image_data).decode("utf-8")
            content_type = response.headers.get("Content-Type", "image/png")
            return f"data:{content_type};base64,{encoded_string}"
        else:
            file = Files.get_file_by_id(url)

            if not file:
                return None

            file_path = Storage.get_file(file.path)
            file_path = Path(file_path)

            if file_path.is_file():
                with open(file_path, "rb") as image_file:
                    encoded_string = base64.b64encode(image_file.read()).decode("utf-8")
                    content_type, _ = mimetypes.guess_type(file_path.name)
                    return f"data:{content_type};base64,{encoded_string}"
            else:
                return None

    except Exception as e:
        return None


def get_image_url_from_base64(request, base64_image_string, metadata, user):
    if BASE64_IMAGE_URL_PREFIX.match(base64_image_string):
        image_url = ""
        # Extract base64 image data from the line
        image_data, content_type = get_image_data(base64_image_string)
        if image_data is not None:
            _, image_url = upload_image(
                request,
                image_data,
                content_type,
                metadata,
                user,
            )

        return image_url
    return None


def convert_markdown_base64_images(request, content: str, metadata, user):
    def replace(match):
        base64_string = match.group(2)
        MIN_REPLACEMENT_URL_LENGTH = 1024
        if len(base64_string) > MIN_REPLACEMENT_URL_LENGTH:
            url = get_image_url_from_base64(request, base64_string, metadata, user)
            if url:
                return f"![{match.group(1)}]({url})"
        return match.group(0)

    return MARKDOWN_IMAGE_URL_PATTERN.sub(replace, content)


def load_b64_audio_data(b64_str):
    try:
        if "," in b64_str:
            header, b64_data = b64_str.split(",", 1)
        else:
            b64_data = b64_str
            header = "data:audio/wav;base64"
        audio_data = base64.b64decode(b64_data)
        content_type = (
            header.split(";")[0].split(":")[1] if ";" in header else "audio/wav"
        )
        return audio_data, content_type
    except Exception as e:
        print(f"Error decoding base64 audio data: {e}")
        return None, None


def upload_audio(request, audio_data, content_type, metadata, user):
    audio_format = mimetypes.guess_extension(content_type)
    file = UploadFile(
        file=io.BytesIO(audio_data),
        filename=f"generated-{audio_format}",  # will be converted to a unique ID on upload_file
        headers={
            "content-type": content_type,
        },
    )
    file_item = upload_file_handler(
        request,
        file=file,
        metadata=metadata,
        process=False,
        user=user,
    )
    url = request.app.url_path_for("get_file_content_by_id", id=file_item.id)
    return url


def get_audio_url_from_base64(request, base64_audio_string, metadata, user):
    if "data:audio/wav;base64" in base64_audio_string:
        audio_url = ""
        # Extract base64 audio data from the line
        audio_data, content_type = load_b64_audio_data(base64_audio_string)
        if audio_data is not None:
            audio_url = upload_audio(
                request,
                audio_data,
                content_type,
                metadata,
                user,
            )
        return audio_url
    return None


def upload_file_from_base64(request, file_data, content_type, filename, metadata, user):
    """Generic file upload from raw bytes. Follows the pattern of upload_audio()."""
    file = UploadFile(
        file=io.BytesIO(file_data),
        filename=filename,
        headers={
            "content-type": content_type,
        },
    )
    file_item = upload_file_handler(
        request,
        file=file,
        metadata=metadata,
        process=False,
        user=user,
    )
    url = request.app.url_path_for("get_file_content_by_id", id=file_item.id)
    return file_item, url


def get_file_url_from_base64(request, base64_file_string, metadata, user):
    # Preserve existing behavior for images and audio
    if "data:image/" in base64_file_string:
        return get_image_url_from_base64(request, base64_file_string, metadata, user)
    elif "data:audio/" in base64_file_string:
        return get_audio_url_from_base64(request, base64_file_string, metadata, user)

    # Generic handler for all other MIME types (PPTX, PDF, CSV, etc.)
    match = BASE64_DATA_URI_PATTERN.search(base64_file_string)
    if match:
        content_type = match.group(1)
        params = match.group(2) or ""
        b64_data = match.group(3)
        try:
            file_data = base64.b64decode(b64_data)
        except Exception:
            return None
        # Use embedded filename if present, otherwise generate one
        fname_match = DATA_URI_FILENAME_RE.search(params)
        if fname_match:
            filename = fname_match.group(1)
        else:
            ext = mimetypes.guess_extension(content_type) or MIME_EXTENSION_FALLBACK.get(
                content_type, ""
            )
            filename = f"generated-file{ext}"
        _, url = upload_file_from_base64(
            request, file_data, content_type, filename, metadata, user
        )
        return url
    return None


def get_image_base64_from_file_id(id: str) -> Optional[str]:
    file = Files.get_file_by_id(id)
    if not file:
        return None

    try:
        file_path = Storage.get_file(file.path)
        file_path = Path(file_path)

        # Check if the file already exists in the cache
        if file_path.is_file():
            import base64

            with open(file_path, "rb") as image_file:
                encoded_string = base64.b64encode(image_file.read()).decode("utf-8")
                content_type, _ = mimetypes.guess_type(file_path.name)
                return f"data:{content_type};base64,{encoded_string}"
        else:
            return None
    except Exception as e:
        return None
