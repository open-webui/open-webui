from datetime import datetime

KEYS_TO_EXCLUDE = ['content', 'pages', 'tables', 'paragraphs', 'sections', 'figures']


def filter_metadata(metadata: dict[str, any]) -> dict[str, any]:
    # Removes large/redundant fields from metadata dict.
    metadata = {key: value for key, value in metadata.items() if key not in KEYS_TO_EXCLUDE}
    return metadata


def process_metadata(
    metadata: dict[str, any],
) -> dict[str, any]:
    # Removes large fields and converts non-serializable types (datetime, list, dict) to strings.
    result = {}
    for key, value in metadata.items():
        # Skip large fields
        if key in KEYS_TO_EXCLUDE:
            continue
        # Convert non-serializable fields to strings
        if isinstance(value, (datetime, list, dict)):
            result[key] = str(value)
        elif isinstance(value, str):
            # Remove null bytes and other control characters that PostgreSQL JSONB cannot handle
            result[key] = ''.join(char for char in value if ord(char) >= 32 or char in '\n\r\t')
        else:
            result[key] = value
    return result
