from enum import Enum


class TaskStatus(str, Enum):
    FAILURE = "FAILURE"
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    SUCCESS = "SUCCESS"

    def __str__(self) -> str:
        return str(self.value)
