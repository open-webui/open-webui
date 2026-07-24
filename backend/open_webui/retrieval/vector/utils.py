from datetime import datetime

from open_webui.utils.misc import sanitize_text_for_db

KEYS_TO_EXCLUDE = ['content', 'pages', 'tables', 'paragraphs', 'sections', 'figures']

# Lucene caps a single keyword term at 32766 bytes; Elasticsearch/OpenSearch map
# metadata strings to keyword and reject longer values with a bulk 400. Metadata
# is used for exact-match filtering, never full-text, so truncating an oversized
# value is safe (the searchable body lives in the separate `text` field).
MAX_METADATA_VALUE_BYTES = 32000


def _truncate_for_keyword(value):
    if isinstance(value, str):
        encoded = value.encode('utf-8')
        if len(encoded) > MAX_METADATA_VALUE_BYTES:
            return encoded[:MAX_METADATA_VALUE_BYTES].decode('utf-8', errors='ignore')
    return value


def filter_metadata(metadata: dict[str, any]) -> dict[str, any]:
    # Removes large/redundant fields from metadata dict.
    metadata = {key: value for key, value in metadata.items() if key not in KEYS_TO_EXCLUDE}
    return metadata


def process_metadata(
    metadata: dict[str, any],
) -> dict[str, any]:
    # Removes large fields, converts non-serializable types (datetime, list, dict) to strings,
    # and sanitizes strings for database storage (strips null bytes and invalid surrogates).
    result = {}
    for key, value in metadata.items():
        # Skip large fields
        if key in KEYS_TO_EXCLUDE:
            continue
        # Convert non-serializable fields to strings
        if isinstance(value, (datetime, list, dict)):
            result[key] = _truncate_for_keyword(sanitize_text_for_db(str(value)))
        else:
            result[key] = _truncate_for_keyword(sanitize_text_for_db(value))
    return result
