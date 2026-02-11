"""Validation utilities for user-supplied input."""

# Known static asset paths used as default profile images
_ALLOWED_STATIC_PATHS = (
    "/user.png",
    "/static/favicon.png",
)


def validate_profile_image_url(url: str) -> str:
    """
    Pydantic-compatible validator for profile image URLs.

    Allowed formats:
    - Empty string (falls back to default avatar)
    - data:image/* URIs (base64-encoded uploads from the frontend)
    - Known static asset paths (/user.png, /static/favicon.png)

    Returns the url unchanged if valid, raises ValueError otherwise.
    """
    if not url:
        return url

    _ALLOWED_DATA_PREFIXES = (
        "data:image/png",
        "data:image/jpeg",
        "data:image/gif",
        "data:image/webp",
    )
    if any(url.startswith(prefix) for prefix in _ALLOWED_DATA_PREFIXES):
        return url

    if url in _ALLOWED_STATIC_PATHS:
        return url

    raise ValueError(
        "Invalid profile image URL: only data URIs and default avatars are allowed."
    )
