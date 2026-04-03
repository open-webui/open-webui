"""Validation utilities for user-supplied input."""


def validate_profile_image_url(url: str) -> str:
    """
    Pydantic-compatible validator for profile image URLs.

    Allowed formats:
    - Empty string (falls back to default avatar)
    - Relative paths starting with ``/`` (internal assets and API routes)
    - ``http://`` and ``https://`` URLs (external avatars, OAuth pictures)
    - ``data:image/*`` URIs (base64-encoded uploads from the frontend)

    All other schemes (javascript:, file:, ftp:, etc.) are rejected.
    """
    if not url:
        return url

    # Relative paths: covers /user.png, /static/favicon.png,
    # /api/v1/users/{id}/profile/image, and any future internal routes.
    if url.startswith('/'):
        return url

    # External images served over HTTP(S), e.g. OAuth provider avatars.
    if url.startswith('https://') or url.startswith('http://'):
        return url

    # Base64-encoded images uploaded via the frontend.
    if url.startswith('data:image/'):
        return url

    raise ValueError(
        'Invalid profile image URL: must be a relative path, an HTTP(S) URL, '
        'or a data:image URI.'
    )
