from datetime import datetime

KEYS_TO_EXCLUDE = ['content', 'pages', 'tables', 'paragraphs', 'sections', 'figures']


def _clean_string_value(value: str) -> str:
    """Remove null bytes and other invalid Unicode characters that cause issues with PostgreSQL JSONB."""
    if not isinstance(value, str):
        return value
    # Remove null bytes and other control characters that are invalid in JSON
    return ''.join(char for char in value if char >= ' ' or char in '\t\n\r')


def _clean_value(value):
    """Recursively clean strings in nested structures (dict, list)."""
    if isinstance(value, str):
        return _clean_string_value(value)
    elif isinstance(value, dict):
        return {k: _clean_value(v) for k, v in value.items()}
    elif isinstance(value, list):
        return [_clean_value(item) for item in value]
    return value


def filter_metadata(metadata: dict[str, any]) -> dict[str, any]:
    # Removes large/redundant fields from metadata dict and cleans invalid characters.
    metadata = {key: _clean_value(value) for key, value in metadata.items() if key not in KEYS_TO_EXCLUDE}
    return metadata


def process_metadata(
    metadata: dict[str, any],
) -> dict[str, any]:
    # Removes large fields and converts non-serializable types (datetime, list, dict) to strings.
    # Also cleans null bytes and invalid Unicode characters.
    result = {}
    for key, value in metadata.items():
        # Skip large fields
        if key in KEYS_TO_EXCLUDE:
            continue
        # Convert non-serializable fields to strings
        if isinstance(value, (datetime, list, dict)):
            value = str(value)
        # Clean string values from null bytes and invalid characters
        result[key] = _clean_value(value)
    return result
