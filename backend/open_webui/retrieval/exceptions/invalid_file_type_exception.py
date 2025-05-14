from typing import List

class InvalidFileTypeException(ValueError):
    """Raised when attempting to load a file with an unsupported extension."""
    def __init__(self, extension: str):
        self.extension = extension
        super().__init__()