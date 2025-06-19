def chunk_text(text: str, chunk_size: int = 512, chunk_overlap: int = 50) -> list[str]:
    if not text:
        return []

    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        if end >= len(text):
            break
        start += chunk_size - chunk_overlap
        if start >= len(text): # Ensure overlap doesn't push start beyond text length
             break
    return chunks
