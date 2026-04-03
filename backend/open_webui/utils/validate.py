"""Validation utilities for user-supplied input."""

# Raster image formats safe to accept as base64 data URIs.
# SVG is intentionally excluded: it can carry embedded scripts.
_SAFE_DATA_IMAGE_PREFIXES = (
    'data:image/png',
    'data:image/jpeg',
    'data:image/gif',
    'data:image/webp',
)


def validate_profile_image_url(url: str) -> str:
    """
    Pydantic-compatible validator for profile image URLs.

    Allowed formats:
    - Empty string (falls back to default avatar)
    - Relative paths starting with ``/`` (internal assets and API routes)
    - ``http://`` and ``https://`` URLs (external avatars, OAuth pictures)
    - ``data:image/{png,jpeg,gif,webp}`` URIs (base64-encoded uploads)

    All other schemes (javascript:, file:, ftp:, etc.) are rejected.
    SVG data URIs are rejected because SVG can contain embedded scripts.
    """
    if not url:
        return url

    # Relative paths: covers /user.png, /static/favicon.png,
    # /api/v1/users/{id}/profile/image, and any future internal routes.
    # Exclude scheme-relative URLs (//host/path) which browsers resolve
    # against the current protocol.
    if url.startswith('/') and not url.startswith('//'):
        return url

    # External images served over HTTP(S), e.g. OAuth provider avatars.
    if url.startswith('https://') or url.startswith('http://'):
        return url

    # Base64-encoded raster images uploaded via the frontend.
    if any(url.startswith(prefix) for prefix in _SAFE_DATA_IMAGE_PREFIXES):
        return url

    raise ValueError(
        'Invalid profile image URL: must be a relative path, an HTTP(S) URL, '
        'or a data:image URI (png/jpeg/gif/webp).'
    )

