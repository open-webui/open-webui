"""Validation utilities for user-supplied input."""

import io
import re
from urllib.parse import urlparse

from open_webui.env import (
    PROFILE_IMAGE_ALLOWED_MIME_TYPES,
    PROFILE_IMAGE_MAX_DATA_URI_SIZE,
)
from PIL import Image

_USER_PROFILE_IMAGE_RE = re.compile(r'^/api/v1/users/[^/?#]+/profile/image$')

# Data-URI prefix validator derived from PROFILE_IMAGE_ALLOWED_MIME_TYPES.
_mime_suffixes = '|'.join(re.escape(t.split('/')[-1]) for t in sorted(PROFILE_IMAGE_ALLOWED_MIME_TYPES))
_SAFE_DATA_URI_RE = re.compile(rf'^data:image/({_mime_suffixes});base64,', re.IGNORECASE)

# Exact relative paths accepted as profile images. These are the only
# static-asset paths OWUI itself assigns; no prefix/wildcard matching is
# used so that arbitrary relative paths cannot trigger authenticated GETs
# against internal endpoints when rendered as ``<img>`` sources.
# LICENSE covers the Open WebUI favicon fallback paths below. Do not alter,
# remove, obscure, or replace them except as LICENSE permits:
# https://docs.openwebui.com/license.
_SAFE_STATIC_PATHS = frozenset(
    {
        '/user.png',
        '/favicon.png',
        '/static/favicon.png',
    }
)


def validate_image_url(url: str, *, file_only: bool = False) -> str:
    """
    Validate profile image URLs or canonical file URLs for model backgrounds.

    With file_only=True, only /api/v1/files/<uuid>/content is accepted.
    This checks the URL only; file access and image bytes are checked when saving.

    Profile formats (the default):
    - Empty string (falls back to default avatar)
    - Known static-asset paths assigned by OWUI (exact match)
    - The OWUI profile-image API route ``/api/v1/users/{id}/profile/image``
    - ``http://`` and ``https://`` URLs with a valid hostname
    - ``data:image/{png,jpeg,gif,webp};base64,...`` URIs

    Everything else is rejected, including:
    - Dangerous schemes (javascript:, file:, ftp:, …)
    - SVG data URIs (can contain embedded scripts)
    - Arbitrary relative paths (prevents authenticated GET triggers)
    - Scheme-relative URLs (``//host/path``)
    - data URIs larger than PROFILE_IMAGE_MAX_DATA_URI_SIZE bytes
    """
    if not isinstance(url, str):
        raise ValueError('Invalid image URL.')

    if file_only:
        if re.fullmatch(r'/api/v1/files/[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}/content', url):
            return url
        raise ValueError('Invalid background image URL: must reference an internal file.')

    # --- Relative paths (exact match + anchored regex only) -----------

    if not url or url in _SAFE_STATIC_PATHS or _USER_PROFILE_IMAGE_RE.match(url):
        return url

    # --- Absolute URLs -------------------------------------------------

    # urlparse normalises the scheme to lowercase, giving us
    # case-insensitive scheme matching for free.
    parsed = urlparse(url)

    # External images served over HTTP(S), e.g. OAuth provider avatars.
    # Require a non-empty hostname (not just netloc, which can be ":80"
    # for a URL like http://:80/path with no actual host).
    if parsed.scheme in ('http', 'https'):
        if not parsed.hostname:
            raise ValueError('Invalid profile image URL: HTTP(S) URLs must include a host.')
        return url

    # Base64-encoded raster images uploaded via the frontend.
    # The regex enforces the ;base64, boundary and is case-insensitive
    # per the data-URI / MIME-type specs.
    if _SAFE_DATA_URI_RE.match(url):
        if PROFILE_IMAGE_MAX_DATA_URI_SIZE and len(url) > PROFILE_IMAGE_MAX_DATA_URI_SIZE:
            raise ValueError(
                f'Invalid profile image URL: data URI exceeds the {PROFILE_IMAGE_MAX_DATA_URI_SIZE}-byte limit.'
            )
        return url

    raise ValueError(
        'Invalid profile image URL: must be a known internal path, '
        'an HTTP(S) URL with a host, or a data:image URI (png/jpeg/gif/webp).'
    )


BACKGROUND_IMAGE_MAX_BYTES = 5 * 1024 * 1024
BACKGROUND_IMAGE_MAX_PIXELS = 25_000_000
BACKGROUND_IMAGE_MIME_TYPES = {'PNG': 'image/png', 'JPEG': 'image/jpeg', 'WEBP': 'image/webp', 'GIF': 'image/gif'}


def validate_background_image(data: bytes) -> str:
    if len(data) > BACKGROUND_IMAGE_MAX_BYTES:
        raise ValueError('Background image must be at most 5 MiB.')
    try:
        with Image.open(io.BytesIO(data)) as image:
            content_type = BACKGROUND_IMAGE_MIME_TYPES.get(image.format)
            if not content_type:
                raise ValueError('Background image must be PNG, JPEG, WebP, or GIF.')
            if image.width * image.height > BACKGROUND_IMAGE_MAX_PIXELS:
                raise ValueError('Background image must be at most 25 megapixels.')
            image.verify()
        # verify() does not decode pixels for every format.
        with Image.open(io.BytesIO(data)) as image:
            image.load()
    except (OSError, SyntaxError, Image.DecompressionBombError) as error:
        raise ValueError('Invalid background image.') from error
    return content_type
