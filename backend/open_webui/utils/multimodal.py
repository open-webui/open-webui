"""Mapping between uploaded files and OpenAI-compatible multimodal content parts.

Uploaded files that a model can consume natively are forwarded as typed content
parts (``image_url``, ``video_url``) instead of being handed to retrieval as
plain attachments. This module is intentionally dependency-free so the mapping
stays reusable and unit-testable without importing the middleware stack.
"""

from typing import Any

# Ordered mapping of natively supported media kinds.
# Each entry is (uploaded-file ``type`` value, ``content_type`` prefix, content part type).
MEDIA_CONTENT_PARTS: tuple[tuple[str, str, str], ...] = (
    ('image', 'image/', 'image_url'),
    ('video', 'video/', 'video_url'),
)

MEDIA_CONTENT_PART_TYPES: tuple[str, ...] = tuple(part_type for _, _, part_type in MEDIA_CONTENT_PARTS)


def get_media_content_part_type(file: Any) -> str | None:
    """Return the content part type for an uploaded file, or None if it is not native media."""
    if not isinstance(file, dict):
        return None

    file_type = file.get('type')
    content_type = file.get('content_type') or ''

    for kind, mime_prefix, part_type in MEDIA_CONTENT_PARTS:
        if file_type == kind or content_type.startswith(mime_prefix):
            return part_type

    return None


def build_media_content_parts(files: Any) -> list[dict]:
    """Build OpenAI-compatible media content parts for the given uploaded files.

    Files without a resolvable URL are skipped. Parts are grouped by media kind so
    the emitted order stays stable regardless of the order the files were attached in.
    """
    parts_by_type: dict[str, list[dict]] = {part_type: [] for part_type in MEDIA_CONTENT_PART_TYPES}

    for file in files or []:
        part_type = get_media_content_part_type(file)
        if part_type is None:
            continue

        url = file.get('url')
        if not url:
            continue

        parts_by_type[part_type].append({'type': part_type, part_type: {'url': url}})

    return [part for part_type in MEDIA_CONTENT_PART_TYPES for part in parts_by_type[part_type]]


def get_media_content_part_url(item: Any) -> tuple[str, str] | None:
    """Return ``(part_type, url)`` for a media content part, or None for any other part."""
    if not isinstance(item, dict):
        return None

    part_type = item.get('type')
    if part_type not in MEDIA_CONTENT_PART_TYPES:
        return None

    value = item.get(part_type)
    if not isinstance(value, dict):
        return None

    return part_type, value.get('url') or ''


def is_inline_media_data_url(part_type: str, url: str) -> bool:
    """Return True when the URL is already an inline data URL for that media kind."""
    for _, mime_prefix, candidate_part_type in MEDIA_CONTENT_PARTS:
        if candidate_part_type == part_type:
            return url.startswith(f'data:{mime_prefix}')

    return False
