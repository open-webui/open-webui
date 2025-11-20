from datetime import datetime

KEYS_TO_EXCLUDE = ["content", "pages", "tables", "paragraphs", "sections", "figures"]


def filter_metadata(metadata: dict[str, any]) -> dict[str, any]:
    metadata = {
        key: value for key, value in metadata.items() if key not in KEYS_TO_EXCLUDE
    }
    return metadata


def process_metadata(
    metadata: dict[str, any],
) -> dict[str, any]:
    for key, value in metadata.items():
        # Remove large fields
        if key in KEYS_TO_EXCLUDE:
            del metadata[key]

        # Convert non-serializable fields to strings
        if (
            isinstance(value, datetime)
            or isinstance(value, list)
            or isinstance(value, dict)
        ):
            metadata[key] = str(value)
    return metadata
