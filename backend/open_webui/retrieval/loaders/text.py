import codecs
from collections.abc import Iterable
from pathlib import Path

CJK_ENCODING_FALLBACKS = (
    'gb18030',
    'gbk',
    'big5',
    'big5hkscs',
    'shift_jis',
    'euc_jp',
    'euc_kr',
)

GB_FAMILY_ENCODINGS = {
    'gb2312',
    'gb_2312',
    'gbk',
    'gb18030',
    'hz',
    'hz-gb-2312',
}


def _normalize_encoding(encoding: str | None) -> str | None:
    if not encoding:
        return None

    try:
        return codecs.lookup(encoding).name
    except LookupError:
        return encoding.lower().replace(' ', '-')


def _dedupe(items: Iterable[str]) -> list[str]:
    seen = set()
    deduped = []

    for item in items:
        normalized = _normalize_encoding(item)
        if not normalized or normalized in seen:
            continue

        seen.add(normalized)
        deduped.append(item)

    return deduped


def _detect_encoding(data: bytes) -> str | None:
    try:
        import chardet
    except ImportError:
        return None

    result = chardet.detect(data)
    encoding = result.get('encoding')

    if encoding:
        return encoding

    return None


def get_text_decoding_candidates(data: bytes) -> list[str]:
    detected_encoding = _detect_encoding(data)
    candidates = ['utf-8-sig', 'utf-8']

    if detected_encoding:
        candidates.append(detected_encoding)

        normalized_detected = _normalize_encoding(detected_encoding)
        if normalized_detected in GB_FAMILY_ENCODINGS:
            candidates.extend(('gb18030', 'gbk'))

    candidates.extend(CJK_ENCODING_FALLBACKS)
    candidates.append('latin-1')

    return _dedupe(candidates)


def read_text_file(file_path: str | Path) -> tuple[str, str]:
    data = Path(file_path).read_bytes()
    decode_errors: list[UnicodeDecodeError] = []

    for encoding in get_text_decoding_candidates(data):
        try:
            return data.decode(encoding), encoding
        except UnicodeDecodeError as e:
            decode_errors.append(e)

    if decode_errors:
        raise decode_errors[-1]

    return data.decode('utf-8'), 'utf-8'
