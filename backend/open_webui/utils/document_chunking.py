def chunk_text(text: str, max_chars: int = 2500, overlap: int = 200) -> list[str]:
    if not text:
        return []

    chunks = []
    start = 0
    text_len = len(text)

    while start < text_len:
        end = min(start + max_chars, text_len)
        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        if end >= text_len:
            break

        start = max(end - overlap, 0)

    return chunks