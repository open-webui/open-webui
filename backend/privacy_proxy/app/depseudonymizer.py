LEAK_PATTERNS = [
    "refers to",
    "stands for",
    "is actually",
    "real name is",
    "which is",
    "also known as",
    "means",
]


def check_leakage(text: str, mapping: dict) -> str:
    for pattern in LEAK_PATTERNS:
        if pattern in text.lower():
            for original in mapping.values():
                if original in text:
                    text = text.replace(original, "[REDACTED]")
    return text


def depseudonymize(text: str, session_id: str, store: dict) -> str:
    mapping = store.get(session_id, {})

    text = check_leakage(text, mapping)

    for token in sorted(mapping.keys(), key=len, reverse=True):
        text = text.replace(token, mapping[token])

    return text