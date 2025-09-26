import re
import json
from sqlalchemy import types, Text, JSON

def sanitize_data(data):
    """
    Recursively removes null bytes from strings, lists, and dictionaries.
    """
    if isinstance(data, str):
        # Remove the null byte character
        return re.sub(r'\x00', '', data)
    elif isinstance(data, list):
        return [sanitize_data(item) for item in data]
    elif isinstance(data, dict):
        return {key: sanitize_data(value) for key, value in data.items()}
    else:
        return data

class SanitizedText(types.TypeDecorator):
    """
    A custom SQLAlchemy type that sanitizes string data by removing null bytes
    before storing it in the database.
    """
    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None:
            return sanitize_data(value)
        return value

class SanitizedJSON(types.TypeDecorator):
    """
    A custom SQLAlchemy type that sanitizes JSON data by removing null bytes
    from all strings within the JSON structure before storing it.
    """
    impl = JSON
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None:
            return sanitize_data(value)
        return value