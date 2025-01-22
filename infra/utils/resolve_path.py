import os


def resolve_path(file: str, *path_segments: list[str]) -> str:
    return os.path.join(os.path.dirname(file), *path_segments)
