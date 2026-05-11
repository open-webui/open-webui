from datetime import datetime

from open_webui.utils.misc import sanitize_text_for_db

KEYS_TO_EXCLUDE = ['content', 'pages', 'tables', 'paragraphs', 'sections', 'figures']


def filter_metadata(metadata: dict[str, any]) -> dict[str, any]:
    # Removes large/redundant fields from metadata dict.
    metadata = {key: value for key, value in metadata.items() if key not in KEYS_TO_EXCLUDE}
    return metadata


def process_metadata(
    metadata: dict[str, any],
) -> dict[str, any]:
    """
    Process metadata for vector storage.

    - Removes large excluded fields
    - Converts datetime to ISO strings
    - Converts dicts to strings (nested objects unsupported in most vector DBs)
    - Preserves lists/arrays so Pinecone $in filtering keeps working
    - Sanitizes scalar strings for database storage (strips null bytes / invalid surrogates)
    """
    result = {}
    for key, value in metadata.items():
        # Skip large fields
        if key in KEYS_TO_EXCLUDE:
            continue

        if isinstance(value, datetime):
            result[key] = value.isoformat()
        elif isinstance(value, dict):
            result[key] = sanitize_text_for_db(str(value))
        elif isinstance(value, list):
            # Preserve arrays for Pinecone $in filtering (e.g., {"labels": {"$in": ["SENT"]}})
            result[key] = [
                (
                    sanitize_text_for_db(item)
                    if isinstance(item, str)
                    else (item if isinstance(item, (int, float, bool, type(None))) else sanitize_text_for_db(str(item)))
                )
                for item in value
            ]
        else:
            result[key] = sanitize_text_for_db(value)
    return result
