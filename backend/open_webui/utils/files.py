import asyncio
import base64
import io
import mimetypes
import re
from pathlib import Path
from typing import Optional

import aiofiles
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    UploadFile,
)
from open_webui.env import (
    AIOHTTP_CLIENT_ALLOW_REDIRECTS,
    AIOHTTP_CLIENT_SESSION_SSL,
    ENABLE_IMAGE_CONTENT_TYPE_EXTENSION_FALLBACK,
)
from open_webui.models.chats import Chats
from open_webui.models.files import Files
from open_webui.retrieval.web.utils import get_ssrf_safe_session, validate_url
from open_webui.routers.files import upload_file_handler
from open_webui.utils.access_control.files import has_access_to_file
from open_webui.routers.images import (
    get_image_data,
    upload_image,
)
from open_webui.storage.provider import Storage

BASE64_IMAGE_URL_PREFIX = re.compile(r'data:image/\w+;base64,', re.IGNORECASE)
MARKDOWN_IMAGE_URL_PATTERN = re.compile(r'!\[(.*?)\]\((.+?)\)', re.IGNORECASE)

# Extension-based MIME fallback, only used when ENABLE_IMAGE_CONTENT_TYPE_EXTENSION_FALLBACK is True.
_IMAGE_MIME_FALLBACK = {
    '.webp': 'image/webp',
    '.png': 'image/png',
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.gif': 'image/gif',
    '.svg': 'image/svg+xml',
    '.bmp': 'image/bmp',
    '.tiff': 'image/tiff',
    '.tif': 'image/tiff',
    '.ico': 'image/x-icon',
    '.heic': 'image/heic',
    '.heif': 'image/heif',
    '.avif': 'image/avif',
}


async def get_image_base64_from_url(url: str, user=None) -> Optional[str]:
    try:
        if url.startswith('http'):
            # Validate URL to prevent SSRF attacks against local/private networks.
            # allow_redirects=False prevents redirect-based SSRF: validate_url() is
            # called only on the originally-submitted URL; following 3xx redirects
            # without re-validation would let an attacker reach private IPs via a
            # public host that redirects internally (e.g. cloud-metadata exfil).
            await asyncio.to_thread(validate_url, url)
            # Fetch through an SSRF-safe session that re-checks the connect-time IP, so a
            # rebinding DNS answer that passed validate_url cannot reach an internal address.
            async with get_ssrf_safe_session() as session:
                async with session.get(
                    url, ssl=AIOHTTP_CLIENT_SESSION_SSL, allow_redirects=AIOHTTP_CLIENT_ALLOW_REDIRECTS
                ) as response:
                    response.raise_for_status()
                    image_data = await response.read()
                    encoded_string = base64.b64encode(image_data).decode('utf-8')
                    content_type = response.headers.get('Content-Type', 'image/png')
                    return f'data:{content_type};base64,{encoded_string}'
        else:
            # Non-URL string — treat as file_id. Delegate to the canonical
            # file-ID resolver which enforces ownership/access checks.
            return await get_image_base64_from_file_id(url, user=user)

    except Exception:
        return None


async def get_image_url_from_base64(request, base64_image_string, metadata, user):
    if BASE64_IMAGE_URL_PREFIX.match(base64_image_string):
        image_url = ''
        # Extract base64 image data from the line
        image_data, content_type = await get_image_data(base64_image_string)
        if image_data is not None:
            _, image_url = await upload_image(
                request,
                image_data,
                content_type,
                metadata,
                user,
            )

        return image_url
    return None


async def convert_markdown_base64_images(request, content: str, metadata, user):
    MIN_REPLACEMENT_URL_LENGTH = 1024
    result_parts = []
    last_end = 0

    for match in MARKDOWN_IMAGE_URL_PATTERN.finditer(content):
        result_parts.append(content[last_end : match.start()])
        base64_string = match.group(2)
        if len(base64_string) > MIN_REPLACEMENT_URL_LENGTH:
            url = await get_image_url_from_base64(request, base64_string, metadata, user)
            if url:
                result_parts.append(f'![{match.group(1)}]({url})')
            else:
                result_parts.append(match.group(0))
        else:
            result_parts.append(match.group(0))
        last_end = match.end()

    result_parts.append(content[last_end:])
    return ''.join(result_parts)


def load_b64_audio_data(b64_str):
    try:
        if ',' in b64_str:
            header, b64_data = b64_str.split(',', 1)
        else:
            b64_data = b64_str
            header = 'data:audio/wav;base64'
        audio_data = base64.b64decode(b64_data)
        content_type = header.split(';')[0].split(':')[1] if ';' in header else 'audio/wav'
        return audio_data, content_type
    except Exception as e:
        print(f'Error decoding base64 audio data: {e}')
        return None, None


async def upload_audio(request, audio_data, content_type, metadata, user):
    audio_format = mimetypes.guess_extension(content_type)
    file = UploadFile(
        file=io.BytesIO(audio_data),
        filename=f'generated-{audio_format}',  # will be converted to a unique ID on upload_file
        headers={
            'content-type': content_type,
        },
    )
    file_item = await upload_file_handler(
        request,
        file=file,
        metadata=metadata,
        process=False,
        user=user,
    )
    url = request.app.url_path_for('get_file_content_by_id', id=file_item.id)
    return url


async def get_audio_url_from_base64(request, base64_audio_string, metadata, user):
    if 'data:audio/wav;base64' in base64_audio_string:
        audio_url = ''
        # Extract base64 audio data from the line
        audio_data, content_type = load_b64_audio_data(base64_audio_string)
        if audio_data is not None:
            audio_url = await upload_audio(
                request,
                audio_data,
                content_type,
                metadata,
                user,
            )
        return audio_url
    return None


async def get_file_url_from_base64(request, base64_file_string, metadata, user):
    if BASE64_IMAGE_URL_PREFIX.match(base64_file_string):
        return await get_image_url_from_base64(request, base64_file_string, metadata, user)
    elif 'data:audio/wav;base64' in base64_file_string:
        return await get_audio_url_from_base64(request, base64_file_string, metadata, user)
    return None


async def get_image_base64_from_file_id(id: str, user=None) -> Optional[str]:
    file = await Files.get_file_by_id(id)
    if not file:
        return None

    # Gate file-by-id resolution by ownership to prevent exfiltration.
    # A caller could place another user's file_id in an image_url field;
    # without this check the server reads the file from disk, inlines it
    # base64 into the LLM request, and the content leaks via OCR/describe.
    # Owner, admin, and explicit read-grant holders are allowed.
    if user is None:
        return None
    if file.user_id != user.id and user.role != 'admin' and not await has_access_to_file(file.id, 'read', user):
        return None

    try:
        file_path = await asyncio.to_thread(Storage.get_file, file.path)
        file_path = Path(file_path)

        # Check if the file already exists in the cache
        if file_path.is_file():
            async with aiofiles.open(file_path, 'rb') as image_file:
                encoded_string = base64.b64encode(await image_file.read()).decode('utf-8')
            content_type = mimetypes.guess_type(file_path.name)[0] or (file.meta or {}).get('content_type')
            if not content_type and ENABLE_IMAGE_CONTENT_TYPE_EXTENSION_FALLBACK:
                content_type = _IMAGE_MIME_FALLBACK.get(file_path.suffix.lower())
            if not content_type:
                return None
            return f'data:{content_type};base64,{encoded_string}'
        else:
            return None
    except Exception:
        return None


# OpenAI Responses file-input limits (docs: ~50MB/file, ~50MB total request).
# Base64 expands by 4/3, so keep raw budgets below the wire limit.
NATIVE_FILE_INPUT_MAX_COUNT = 5
NATIVE_FILE_INPUT_MAX_BYTES = 32 * 1024 * 1024  # per file, before base64
NATIVE_FILE_INPUT_MAX_TOTAL_BYTES = 36 * 1024 * 1024  # sum of raw bytes in one request
_NATIVE_PDF_MIME_TYPES = {'application/pdf', 'application/x-pdf'}


def get_native_file_input_enabled(metadata: dict | None, model_info=None) -> bool:
    """
    Resolve native_file_input from the chat-resolved model first.

    Frontend/global capabilities live on metadata['model']; Models DB may be
    missing for provider-discovered models that only have global defaults.
    When the resolved model already carries a capabilities object, missing
    native_file_input means False (do not fall back to a stale DB row).
    """
    model = (metadata or {}).get('model') or {}
    meta = (model.get('info') or {}).get('meta') or {}
    caps = meta.get('capabilities')
    if isinstance(caps, dict):
        return bool(caps.get('native_file_input', False))

    if model_info is not None:
        info_meta = getattr(model_info, 'meta', None)
        if info_meta is not None:
            info_caps = getattr(info_meta, 'capabilities', None) or {}
            if isinstance(info_caps, dict):
                return bool(info_caps.get('native_file_input', False))

    return False


def _is_native_pdf_attachment(item: dict, filename: str, content_type: str | None) -> bool:
    mime = (content_type or item.get('content_type') or '').split(';', 1)[0].strip().lower()
    if mime in _NATIVE_PDF_MIME_TYPES:
        return True
    name = (filename or item.get('name') or item.get('filename') or '').lower()
    return name.endswith('.pdf')


def _estimate_file_size_bytes(file, file_path: Path, item: dict) -> int:
    meta_size = (file.meta or {}).get('size')
    if isinstance(meta_size, int) and meta_size >= 0:
        return meta_size
    item_size = item.get('size')
    if isinstance(item_size, int) and item_size >= 0:
        return item_size
    try:
        return file_path.stat().st_size
    except OSError:
        return 0


async def get_pdf_file_data_uri_from_file_id(
    id: str,
    user=None,
    *,
    item: dict | None = None,
    remaining_total_budget: int | None = None,
) -> tuple[str, str, str, int]:
    """
    Load a PDF attachment as a data URI for native provider file inputs.

    Returns (filename, mime_type, data_uri, raw_size_bytes).
    Raises HTTPException on failure.
    """
    item = item or {}
    if user is None:
        raise HTTPException(status_code=401, detail='Authentication required to read file attachments')

    file = await Files.get_file_by_id(id)
    if not file or not file.path:
        raise HTTPException(status_code=404, detail=f'File not found: {id}')

    if file.user_id != user.id and user.role != 'admin' and not await has_access_to_file(file.id, 'read', user):
        raise HTTPException(status_code=403, detail=f'Access denied to file: {id}')

    filename = (file.meta or {}).get('name') or file.filename or f'{id}.pdf'
    content_type = (file.meta or {}).get('content_type') or mimetypes.guess_type(filename)[0]

    if not _is_native_pdf_attachment({'content_type': content_type, 'name': filename}, filename, content_type):
        raise HTTPException(
            status_code=400,
            detail=(
                f'Native file input currently supports PDF only; received "{filename}" ({content_type or "unknown type"}).'
            ),
        )

    try:
        file_path = await asyncio.to_thread(Storage.get_file, file.path)
        file_path = Path(file_path)
        if not file_path.is_file():
            raise HTTPException(status_code=404, detail=f'File content missing on disk: {id}')

        raw_size = _estimate_file_size_bytes(file, file_path, item)
        if raw_size > NATIVE_FILE_INPUT_MAX_BYTES:
            raise HTTPException(
                status_code=400,
                detail=(
                    f'Native file input exceeds the {NATIVE_FILE_INPUT_MAX_BYTES // (1024 * 1024)}MB per-file limit '
                    f'({filename}: {raw_size} bytes).'
                ),
            )
        if remaining_total_budget is not None and raw_size > remaining_total_budget:
            raise HTTPException(
                status_code=400,
                detail=(
                    f'Native file input exceeds the {NATIVE_FILE_INPUT_MAX_TOTAL_BYTES // (1024 * 1024)}MB '
                    f'total attachment budget for this request ({filename}).'
                ),
            )

        async with aiofiles.open(file_path, 'rb') as pdf_file:
            raw = await pdf_file.read()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Failed to read file {id}: {e}') from e

    if len(raw) > NATIVE_FILE_INPUT_MAX_BYTES:
        raise HTTPException(
            status_code=400,
            detail=(
                f'Native file input exceeds the {NATIVE_FILE_INPUT_MAX_BYTES // (1024 * 1024)}MB per-file limit '
                f'({filename}: {len(raw)} bytes).'
            ),
        )

    mime = 'application/pdf'
    encoded = base64.b64encode(raw).decode('utf-8')
    return filename, mime, f'data:{mime};base64,{encoded}', len(raw)


async def append_native_file_inputs_to_messages(
    payload: dict,
    metadata: dict | None,
    *,
    native_file_input_enabled: bool,
    is_responses: bool,
    user,
) -> dict:
    """
    Append raw PDF attachments as Chat Completions-shaped file parts on the
    latest user message so convert_to_responses_payload can map them to
    Responses API input_file parts.

    Only attachments stamped processed=false are considered. Fail closed when
    the capability is enabled but the connection is not Responses API, or when
    a non-PDF raw attachment is present.
    """
    if not native_file_input_enabled:
        return payload

    raw_files = [
        item
        for item in (metadata or {}).get('files', None) or []
        if item.get('type') == 'file' and item.get('processed') is False and item.get('id')
    ]
    if not raw_files:
        return payload

    if not is_responses:
        raise HTTPException(
            status_code=400,
            detail=('Native file input requires an OpenAI connection with api_type set to "responses".'),
        )

    if len(raw_files) > NATIVE_FILE_INPUT_MAX_COUNT:
        raise HTTPException(
            status_code=400,
            detail=(
                f'Native file input allows at most {NATIVE_FILE_INPUT_MAX_COUNT} raw attachments per request '
                f'(received {len(raw_files)}).'
            ),
        )

    file_parts = []
    remaining_budget = NATIVE_FILE_INPUT_MAX_TOTAL_BYTES
    for item in raw_files:
        filename, _mime, data_uri, raw_size = await get_pdf_file_data_uri_from_file_id(
            item['id'],
            user=user,
            item=item,
            remaining_total_budget=remaining_budget,
        )
        remaining_budget -= raw_size
        display_name = item.get('name') or item.get('filename') or filename
        file_parts.append(
            {
                'type': 'file',
                'file': {
                    'filename': display_name,
                    'file_data': data_uri,
                },
            }
        )

    messages = payload.get('messages') or []
    if not messages:
        raise HTTPException(status_code=400, detail='Cannot attach native files without a user message')

    # Attach to the latest user message (mirror image_url injection).
    target_idx = None
    for idx in range(len(messages) - 1, -1, -1):
        if messages[idx].get('role') == 'user':
            target_idx = idx
            break
    if target_idx is None:
        raise HTTPException(status_code=400, detail='Cannot attach native files without a user message')

    message = messages[target_idx]
    content = message.get('content', '')
    if isinstance(content, str):
        content_parts = [{'type': 'text', 'text': content}] if content else []
    elif isinstance(content, list):
        content_parts = list(content)
    else:
        content_parts = [{'type': 'text', 'text': str(content)}]

    message['content'] = file_parts + content_parts
    messages[target_idx] = message
    payload['messages'] = messages
    return payload
