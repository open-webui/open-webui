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

import asyncio
import mimetypes
import base64
import io
import re

from open_webui.env import AIOHTTP_CLIENT_SESSION_SSL, ENABLE_IMAGE_CONTENT_TYPE_EXTENSION_FALLBACK
from open_webui.utils.session_pool import get_session

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


async def get_image_base64_from_url(url: str) -> Optional[str]:
    try:
        if url.startswith('http'):
            # Validate URL to prevent SSRF attacks against local/private networks
            validate_url(url)
            # Download the image from the URL
            session = await get_session()
            async with session.get(url, ssl=AIOHTTP_CLIENT_SESSION_SSL) as response:
                response.raise_for_status()
                image_data = await response.read()
                encoded_string = base64.b64encode(image_data).decode('utf-8')
                content_type = response.headers.get('Content-Type', 'image/png')
                return f'data:{content_type};base64,{encoded_string}'
        else:
            file = await Files.get_file_by_id(url)

            if not file:
                return None

            file_path = await asyncio.to_thread(Storage.get_file, file.path)
            file_path = Path(file_path)

            if file_path.is_file():
                with open(file_path, 'rb') as image_file:
                    encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
                    content_type = mimetypes.guess_type(file_path.name)[0] or (file.meta or {}).get('content_type')
                    if not content_type and ENABLE_IMAGE_CONTENT_TYPE_EXTENSION_FALLBACK:
                        content_type = _IMAGE_MIME_FALLBACK.get(file_path.suffix.lower())
                    if not content_type:
                        return None
                    return f'data:{content_type};base64,{encoded_string}'
            else:
                return None

    except Exception as e:
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


async def get_image_base64_from_file_id(id: str) -> Optional[str]:
    file = await Files.get_file_by_id(id)
    if not file:
        return None

    try:
        file_path = await asyncio.to_thread(Storage.get_file, file.path)
        file_path = Path(file_path)

        # Check if the file already exists in the cache
        if file_path.is_file():
            with open(file_path, 'rb') as image_file:
                encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
                content_type = mimetypes.guess_type(file_path.name)[0] or (file.meta or {}).get('content_type')
                if not content_type and ENABLE_IMAGE_CONTENT_TYPE_EXTENSION_FALLBACK:
                    content_type = _IMAGE_MIME_FALLBACK.get(file_path.suffix.lower())
                if not content_type:
                    return None
                return f'data:{content_type};base64,{encoded_string}'
        else:
            return None
    except Exception as e:
        return None


# Text-based file extensions that should have their content injected into chat messages
TEXT_FILE_EXTENSIONS = {
    # Plain text
    '.txt', '.md', '.markdown', '.csv', '.log', '.ini', '.cfg', '.conf', '.env',
    # Data formats
    '.json', '.yaml', '.yml', '.toml', '.xml', '.html', '.htm',
    # Code files
    '.py', '.js', '.ts', '.tsx', '.jsx', '.java', '.cpp', '.c', '.h', '.hpp',
    '.cs', '.go', '.rs', '.rb', '.php', '.swift', '.kt', '.kts', '.scala',
    '.sh', '.bash', '.zsh', '.fish', '.ps1', '.bat', '.cmd', '.vbs',
    '.sql', '.r', '.dart', '.lua', '.perl', '.pl', '.pm', '.hs', '.lhs',
    '.vue', '.svelte', '.css', '.scss', '.sass', '.less',
    '.dockerfile', '.makefile', '.cmake',
    '.ex', '.exs', '.erl', '.hrl', '.m', '.mm', '.plsql', '.db2',
    # Documents (will be extracted via loaders)
    '.pdf', '.docx', '.xlsx', '.xls',
}

# Image extensions to skip (already handled by vision models)
IMAGE_EXTENSIONS = {
    '.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp', '.svg', '.ico', '.tiff', '.tif',
}

# Audio extensions to skip
AUDIO_EXTENSIONS = {
    '.mp3', '.wav', '.ogg', '.flac', '.aac', '.m4a', '.wma',
}

# Video extensions to skip
VIDEO_EXTENSIONS = {
    '.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv', '.wmv',
}

# Maximum characters to inject per file to prevent context window overflow
MAX_FILE_CONTENT_CHARS = 500000


def _is_text_file(filename: str) -> bool:
    """Check if a file is a text-based file that should have content injected."""
    ext = Path(filename).suffix.lower()
    return ext in TEXT_FILE_EXTENSIONS


def _is_binary_file(filename: str) -> bool:
    """Check if a file is binary (image, audio, video) that should be skipped."""
    ext = Path(filename).suffix.lower()
    return ext in IMAGE_EXTENSIONS | AUDIO_EXTENSIONS | VIDEO_EXTENSIONS


def _extract_text_from_file(file_path: str, filename: str) -> Optional[str]:
    """Extract text content from a file using the appropriate loader."""
    try:
        file_path = str(file_path)
        ext = Path(filename).suffix.lower()

        # Try to read directly for plain text files
        if ext in {'.txt', '.md', '.markdown', '.json', '.yaml', '.yml', '.toml',
                    '.xml', '.html', '.htm', '.csv', '.log', '.ini', '.cfg', '.conf',
                    '.env', '.sql', '.css', '.scss', '.sass', '.less'}:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                return f.read()

        # For code files, try reading as text
        if ext in {'.py', '.js', '.ts', '.tsx', '.jsx', '.java', '.cpp', '.c', '.h', '.hpp',
                    '.cs', '.go', '.rs', '.rb', '.php', '.swift', '.kt', '.kts', '.scala',
                    '.sh', '.bash', '.zsh', '.fish', '.ps1', '.bat', '.cmd', '.vbs',
                    '.r', '.dart', '.lua', '.perl', '.pl', '.pm', '.hs', '.lhs',
                    '.vue', '.svelte', '.dockerfile', '.makefile', '.cmake',
                    '.ex', '.exs', '.erl', '.hrl', '.m', '.mm', '.plsql', '.db2'}:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                return f.read()

        # For PDF, use PyPDFLoader
        if ext == '.pdf':
            from open_webui.retrieval.loaders.main import PyPDFLoader
            loader = PyPDFLoader(file_path)
            docs = loader.load()
            return '\n\n'.join(doc.page_content for doc in docs)

        # For DOCX, use Docx2txtLoader
        if ext == '.docx':
            from open_webui.retrieval.loaders.main import Docx2txtLoader
            loader = Docx2txtLoader(file_path)
            docs = loader.load()
            return '\n\n'.join(doc.page_content for doc in docs)

        # For Excel files, use ExcelLoader
        if ext in {'.xlsx', '.xls'}:
            from open_webui.retrieval.loaders.main import ExcelLoader
            loader = ExcelLoader(file_path)
            docs = loader.load()
            return '\n\n'.join(doc.page_content for doc in docs)

        # Fallback: try reading as text
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            return f.read()

    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f'Failed to extract text from {filename}: {e}')
        return None


def inject_file_content_into_messages(messages: list, files_metadata: list, request: Request) -> None:
    """
    Inject text file content into the last user message in the messages list.

    This function reads attached text-based files and appends their content
    to the last user message so the model can see and process the file contents.

    Args:
        messages: List of message dicts with 'role' and 'content' keys
        files_metadata: List of file metadata dicts from the chat attachment
        request: FastAPI request object (for app state access)
    """
    from open_webui.config import ENABLE_FILE_CONTENT_INJECTION

    if not ENABLE_FILE_CONTENT_INJECTION.value:
        return

    if not files_metadata or not messages:
        return

    # Find the last user message
    last_user_msg = None
    for msg in reversed(messages):
        if msg.get('role') == 'user':
            last_user_msg = msg
            break

    if last_user_msg is None:
        return

    content_parts = []

    # Get the original content
    original_content = last_user_msg.get('content', '')
    if isinstance(original_content, list):
        # Handle multi-modal content (list of content parts)
        text_parts = [part.get('text', '') for part in original_content if isinstance(part, dict) and part.get('type') == 'text']
        original_content = '\n'.join(text_parts)

    if original_content:
        content_parts.append(original_content)

    # Process each attached file
    for file_meta in files_metadata:
        file_id = file_meta.get('id', '')
        filename = file_meta.get('filename', file_meta.get('name', 'unknown'))
        file_type = file_meta.get('type', '')

        # Skip images (handled by vision models)
        if file_type == 'image' or _is_binary_file(filename):
            continue

        # Only process text-based files
        if not _is_text_file(filename):
            continue

        try:
            # Get file record from database
            file_record = Files.get_file_by_id(file_id)
            if not file_record:
                continue

            # Try to use pre-extracted content first (stored during upload)
            content = None
            if file_record.data and isinstance(file_record.data, dict):
                content = file_record.data.get('content')

            # If no pre-extracted content, extract from file
            if not content and file_record.path:
                file_path = Storage.get_file(file_record.path)
                content = _extract_text_from_file(file_path, filename)

            if content:
                # Truncate if too large
                if len(content) > MAX_FILE_CONTENT_CHARS:
                    content = content[:MAX_FILE_CONTENT_CHARS] + f'\n\n... (content truncated, {len(content) - MAX_FILE_CONTENT_CHARS} characters omitted)'

                content_parts.append(f'\n\n--- Attached File: {filename} ---\n{content}\n--- End of {filename} ---')

        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f'Failed to process attached file {filename}: {e}')
            continue

    # Update the last user message with injected content
    if len(content_parts) > 1:
        last_user_msg['content'] = '\n'.join(content_parts)


# Text-based file extensions that should have their content injected into chat messages
TEXT_FILE_EXTENSIONS = {
    # Plain text
    '.txt', '.md', '.markdown', '.csv', '.log', '.ini', '.cfg', '.conf', '.env',
    # Data formats
    '.json', '.yaml', '.yml', '.toml', '.xml', '.html', '.htm',
    # Code files
    '.py', '.js', '.ts', '.tsx', '.jsx', '.java', '.cpp', '.c', '.h', '.hpp',
    '.cs', '.go', '.rs', '.rb', '.php', '.swift', '.kt', '.kts', '.scala',
    '.sh', '.bash', '.zsh', '.fish', '.ps1', '.bat', '.cmd', '.vbs',
    '.sql', '.r', '.dart', '.lua', '.perl', '.pl', '.pm', '.hs', '.lhs',
    '.vue', '.svelte', '.css', '.scss', '.sass', '.less',
    '.dockerfile', '.makefile', '.cmake',
    '.ex', '.exs', '.erl', '.hrl', '.m', '.mm', '.plsql', '.db2',
    # Documents (will be extracted via loaders)
    '.pdf', '.docx', '.xlsx', '.xls',
}

# Image extensions to skip (already handled by vision models)
IMAGE_EXTENSIONS = {
    '.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp', '.svg', '.ico', '.tiff', '.tif',
}

# Audio extensions to skip
AUDIO_EXTENSIONS = {
    '.mp3', '.wav', '.ogg', '.flac', '.aac', '.m4a', '.wma',
}

# Video extensions to skip
VIDEO_EXTENSIONS = {
    '.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv', '.wmv',
}

# Maximum characters to inject per file to prevent context window overflow
MAX_FILE_CONTENT_CHARS = 500000


def _is_text_file(filename: str) -> bool:
    """Check if a file is a text-based file that should have content injected."""
    ext = Path(filename).suffix.lower()
    return ext in TEXT_FILE_EXTENSIONS


def _is_binary_file(filename: str) -> bool:
    """Check if a file is binary (image, audio, video) that should be skipped."""
    ext = Path(filename).suffix.lower()
    return ext in IMAGE_EXTENSIONS | AUDIO_EXTENSIONS | VIDEO_EXTENSIONS


def _extract_text_from_file(file_path: str, filename: str) -> Optional[str]:
    """Extract text content from a file using the appropriate loader."""
    try:
        file_path = str(file_path)
        ext = Path(filename).suffix.lower()

        # Try to read directly for plain text files
        if ext in {'.txt', '.md', '.markdown', '.json', '.yaml', '.yml', '.toml',
                    '.xml', '.html', '.htm', '.csv', '.log', '.ini', '.cfg', '.conf',
                    '.env', '.sql', '.css', '.scss', '.sass', '.less'}:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                return f.read()

        # For code files, try reading as text
        if ext in {'.py', '.js', '.ts', '.tsx', '.jsx', '.java', '.cpp', '.c', '.h', '.hpp',
                    '.cs', '.go', '.rs', '.rb', '.php', '.swift', '.kt', '.kts', '.scala',
                    '.sh', '.bash', '.zsh', '.fish', '.ps1', '.bat', '.cmd', '.vbs',
                    '.r', '.dart', '.lua', '.perl', '.pl', '.pm', '.hs', '.lhs',
                    '.vue', '.svelte', '.dockerfile', '.makefile', '.cmake',
                    '.ex', '.exs', '.erl', '.hrl', '.m', '.mm', '.plsql', '.db2'}:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                return f.read()

        # For PDF, use PyPDFLoader
        if ext == '.pdf':
            from open_webui.retrieval.loaders.main import PyPDFLoader
            loader = PyPDFLoader(file_path)
            docs = loader.load()
            return '\n\n'.join(doc.page_content for doc in docs)

        # For DOCX, use Docx2txtLoader
        if ext == '.docx':
            from open_webui.retrieval.loaders.main import Docx2txtLoader
            loader = Docx2txtLoader(file_path)
            docs = loader.load()
            return '\n\n'.join(doc.page_content for doc in docs)

        # For Excel files, use ExcelLoader
        if ext in {'.xlsx', '.xls'}:
            from open_webui.retrieval.loaders.main import ExcelLoader
            loader = ExcelLoader(file_path)
            docs = loader.load()
            return '\n\n'.join(doc.page_content for doc in docs)

        # Fallback: try reading as text
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            return f.read()

    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f'Failed to extract text from {filename}: {e}')
        return None


def inject_file_content_into_messages(messages: list, files_metadata: list, request: Request) -> None:
    """
    Inject text file content into the last user message in the messages list.

    This function reads attached text-based files and appends their content
    to the last user message so the model can see and process the file contents.

    Args:
        messages: List of message dicts with 'role' and 'content' keys
        files_metadata: List of file metadata dicts from the chat attachment
        request: FastAPI request object (for app state access)
    """
    from open_webui.config import ENABLE_FILE_CONTENT_INJECTION

    if not ENABLE_FILE_CONTENT_INJECTION.value:
        return

    if not files_metadata or not messages:
        return

    # Find the last user message
    last_user_msg = None
    for msg in reversed(messages):
        if msg.get('role') == 'user':
            last_user_msg = msg
            break

    if last_user_msg is None:
        return

    content_parts = []

    # Get the original content
    original_content = last_user_msg.get('content', '')
    if isinstance(original_content, list):
        # Handle multi-modal content (list of content parts)
        text_parts = [part.get('text', '') for part in original_content if isinstance(part, dict) and part.get('type') == 'text']
        original_content = '\n'.join(text_parts)

    if original_content:
        content_parts.append(original_content)

    # Process each attached file
    for file_meta in files_metadata:
        file_id = file_meta.get('id', '')
        filename = file_meta.get('filename', file_meta.get('name', 'unknown'))
        file_type = file_meta.get('type', '')

        # Skip images (handled by vision models)
        if file_type == 'image' or _is_binary_file(filename):
            continue

        # Only process text-based files
        if not _is_text_file(filename):
            continue

        try:
            # Get file record from database
            file_record = Files.get_file_by_id(file_id)
            if not file_record:
                continue

            # Try to use pre-extracted content first (stored during upload)
            content = None
            if file_record.data and isinstance(file_record.data, dict):
                content = file_record.data.get('content')

            # If no pre-extracted content, extract from file
            if not content and file_record.path:
                file_path = Storage.get_file(file_record.path)
                content = _extract_text_from_file(file_path, filename)

            if content:
                # Truncate if too large
                if len(content) > MAX_FILE_CONTENT_CHARS:
                    content = content[:MAX_FILE_CONTENT_CHARS] + f'\n\n... (content truncated, {len(content) - MAX_FILE_CONTENT_CHARS} characters omitted)'

                content_parts.append(f'\n\n--- Attached File: {filename} ---\n{content}\n--- End of {filename} ---')

        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f'Failed to process attached file {filename}: {e}')
            continue

    # Update the last user message with injected content
    if len(content_parts) > 1:
        last_user_msg['content'] = '\n'.join(content_parts)
