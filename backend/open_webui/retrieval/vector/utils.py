from open_webui.utils.misc import sanitize_text_for_db

KEYS_TO_EXCLUDE = ['content', 'pages', 'tables', 'paragraphs', 'sections', 'figures']


def filter_metadata(metadata: dict[str, any]) -> dict[str, any]:
    # Removes large/redundant fields from metadata dict.
    metadata = {key: value for key, value in metadata.items() if key not in KEYS_TO_EXCLUDE}
    return metadata


def process_metadata(
    metadata: dict[str, any],
) -> dict[str, any]:
    # Returns a dict whose values are only str/int/float/bool, which all supported
    # vector DBs accept (notably ChromaDB's Rust bindings, which reject None and
    # non-primitive types). Drops KEYS_TO_EXCLUDE and None values; coerces any
    # other non-primitive (datetime, list, dict, tuple, bytes, numpy, ...) via str().
    result = {}
    for key, value in metadata.items():
        if key in KEYS_TO_EXCLUDE:
            continue
        if value is None:
            continue
        if isinstance(value, bool) or isinstance(value, (int, float)):
            result[key] = value
        elif isinstance(value, str):
            result[key] = sanitize_text_for_db(value)
        else:
            result[key] = sanitize_text_for_db(str(value))
    return result
