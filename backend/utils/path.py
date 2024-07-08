import os.path

from config import DATA_DIR


def get_relative_data_path(absolute_path: str) -> str:
    return os.path.relpath(absolute_path, DATA_DIR)
