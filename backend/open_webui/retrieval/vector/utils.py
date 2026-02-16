from datetime import datetime

KEYS_TO_EXCLUDE = ["content", "pages", "tables", "paragraphs", "sections", "figures"]


def filter_metadata(metadata: dict[str, any]) -> dict[str, any]:
    # Removes large/redundant fields from metadata dict.
    metadata = {
        key: value for key, value in metadata.items() if key not in KEYS_TO_EXCLUDE
    }
    return metadata


def process_metadata(
    metadata: dict[str, any],
) -> dict[str, any]:
    """
    Process metadata for vector storage.

    - Removes large excluded fields
    - Converts non-JSON-serializable types (datetime, dict) to strings
    - Preserves lists/arrays (Pinecone supports array filtering with $in)
    """
    result = {}
    for key, value in metadata.items():
        # Skip large fields
        if key in KEYS_TO_EXCLUDE:
            continue

        # Convert datetime to ISO string
        if isinstance(value, datetime):
            result[key] = value.isoformat()
        # Convert dict to string (nested objects not supported in most vector DBs)
        elif isinstance(value, dict):
            result[key] = str(value)
        # KEEP lists as-is - Pinecone supports arrays for $in filtering
        # e.g., filter: {"labels": {"$in": ["SENT"]}}
        elif isinstance(value, list):
            result[key] = [
                (
                    str(item)
                    if not isinstance(item, (str, int, float, bool, type(None)))
                    else item
                )
                for item in value
            ]
        else:
            result[key] = value
    return result
