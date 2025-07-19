from datetime import datetime


def stringify_nested_datastructures(
    metadatas: list[dict[str, any]],
) -> list[dict[str, any]]:
    for metadata in metadatas:
        for key, value in metadata.items():
            if (
                isinstance(value, datetime)
                or isinstance(value, list)
                or isinstance(value, dict)
            ):
                metadata[key] = str(value)
    return metadatas
