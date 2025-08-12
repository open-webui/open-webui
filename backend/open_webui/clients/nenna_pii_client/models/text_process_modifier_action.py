from enum import Enum


class TextProcessModifierAction(str, Enum):
    IGNORE = "ignore"
    STRING_MASK = "string-mask"
    WORD_MASK = "word-mask"

    def __str__(self) -> str:
        return str(self.value)
