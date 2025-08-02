from datetime import datetime


def stringify_metadata(
    metadata: dict[str, any],
) -> dict[str, any]:
    for key, value in metadata.items():
        if (
            isinstance(value, datetime)
            or isinstance(value, list)
            or isinstance(value, dict)
        ):
            metadata[key] = str(value)
    return metadata
