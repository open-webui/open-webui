from datetime import datetime
import json


def stringify_metadata(
    metadata: dict[str, any],
) -> dict[str, any]:
    for key, value in metadata.items():
        if key == "pii":
            metadata[key] = json.dumps(value)
        elif (
            isinstance(value, datetime)
            or isinstance(value, list)
            or isinstance(value, dict)
        ):
            metadata[key] = str(value)
    return metadata
