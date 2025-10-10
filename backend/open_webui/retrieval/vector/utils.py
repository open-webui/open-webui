from datetime import datetime

KEYS_TO_EXCLUDE = ["content", "pages", "tables", "paragraphs", "sections", "figures"]


def filter_metadata(metadata: dict[str, any]) -> dict[str, any]:
    metadata = {
        key: value for key, value in metadata.items() if key not in KEYS_TO_EXCLUDE
    }
    return metadata


def clean_text_for_postgres(text: str) -> str:
    """Clean text to remove characters that cause PostgreSQL insertion errors."""
    if not text or not isinstance(text, str):
        return text
    
    # Remove NUL characters (0x00) that PostgreSQL cannot handle
    cleaned = text.replace('\x00', '')
    
    # Remove other problematic control characters but keep common whitespace
    cleaned = ''.join(char for char in cleaned if ord(char) >= 32 or char in '\n\r\t')
    
    return cleaned


def process_metadata(
    metadata: dict[str, any],
) -> dict[str, any]:
    cleaned_metadata = {}
    
    for key, value in metadata.items():
        # Remove large fields
        if key in KEYS_TO_EXCLUDE:
            continue

        # Convert non-serializable fields to strings
        if (
            isinstance(value, datetime)
            or isinstance(value, list)
            or isinstance(value, dict)
        ):
            value = str(value)
        
        # Clean string values to remove NUL characters
        if isinstance(value, str):
            value = clean_text_for_postgres(value)
        
        # Clean the key as well
        if isinstance(key, str):
            key = clean_text_for_postgres(key)
            
        cleaned_metadata[key] = value
    
    return cleaned_metadata
