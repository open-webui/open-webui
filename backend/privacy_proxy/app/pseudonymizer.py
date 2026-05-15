import re
import hashlib
from langdetect import detect
from presidio_analyzer import AnalyzerEngine
from presidio_analyzer.nlp_engine import NlpEngineProvider
from app.custom_recognizers import (
    email_recognizer_en, email_recognizer_de,
    org_recognizer_en, org_recognizer_de,
    iban_recognizer_en, iban_recognizer_de,
    phone_recognizer_en, phone_recognizer_de,
    id_recognizer_en, id_recognizer_de,
)

EMAIL_REGEX = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b')
ORG_REGEX = re.compile(r'(?:[A-Z][\w-]*\s){1,3}(?:GmbH|Inc|Ltd|AG|Corp|LLC|SE|Co|SA|SAS|SARL|BV|NV|Bank|Group|Partners|Solutions|Technologies)\b')
PHONE_REGEX = re.compile(r'\+\d{1,3}[\s.-]?\d{2,4}[\s.-]?\d{3,4}[\s.-]?\d{0,5}')

def build_analyzer(language: str) -> AnalyzerEngine:
    if language == "de":
        provider = NlpEngineProvider(nlp_configuration={
            "nlp_engine_name": "spacy",
            "models": [{"lang_code": "de", "model_name": "de_core_news_md"}],
        })
        recognizers = [email_recognizer_de, org_recognizer_de, iban_recognizer_de, phone_recognizer_de, id_recognizer_de]
    else:
        provider = NlpEngineProvider(nlp_configuration={
            "nlp_engine_name": "spacy",
            "models": [{"lang_code": "en", "model_name": "en_core_web_md"}],
        })
        recognizers = [email_recognizer_en, org_recognizer_en, iban_recognizer_en, phone_recognizer_en, id_recognizer_en]

    analyzer = AnalyzerEngine(nlp_engine=provider.create_engine())
    for r in recognizers:
        analyzer.registry.add_recognizer(r)
    return analyzer

def strip_markdown(text: str):
   
    result = []
    pos_map = []
    i = 0
    while i < len(text):
        if text[i:i+2] in ('**', '__'):
            i += 2
        elif text[i] in ('*', '_', '`'):
            i += 1
        else:
            result.append(text[i])
            pos_map.append(i)
            i += 1
    return ''.join(result), pos_map

def generate_token(entity_type: str, value: str) -> str:
    h = hashlib.sha256(value.encode()).hexdigest()[:8]
    return f"{entity_type}_{h}"

def trim_org_results(results, text):
    kept = []
    for r in results:
        if r.entity_type == "ORGANIZATION":
            span = text[r.start:r.end]
            m = ORG_REGEX.search(span)
            if m:
                new_start = r.start + m.start()
                new_end = r.start + m.end()
                r.start = new_start
                r.end = new_end
            kept.append(r)  # always keep — spaCy already validated
        else:
            kept.append(r)
    return kept

def filter_overlaps(results):
    regex_types = {"EMAIL_ADDRESS", "IBAN_CODE", "PHONE_NUMBER", "ID", "ORGANIZATION", "LOCATION"}
    results = sorted(results, key=lambda x: (
        0 if x.entity_type in regex_types else 1,
        -(x.end - x.start)
    ))
    filtered = []
    for r in results:
        overlap = False
        for kept in filtered:
            if r.start < kept.end and r.end > kept.start:
                overlap = True
                break
        if not overlap:
            filtered.append(r)
    return filtered

def detect_entities(text: str, language: str = None, enabled_types=None) -> list:
   
    try:
        if language is None:
            language = detect(text)
        if language not in ["en", "de"]:
            language = "en"
    except:
        language = "en"

    original_text = text
    entities = []

    if not enabled_types or "EMAIL_ADDRESS" in enabled_types:
        for match in EMAIL_REGEX.finditer(original_text):
            entities.append({"start": match.start(), "end": match.end(), "type": "EMAIL_ADDRESS"})
    if not enabled_types or "PHONE_NUMBER" in enabled_types:
        for match in PHONE_REGEX.finditer(original_text):
            entities.append({"start": match.start(), "end": match.end(), "type": "PHONE_NUMBER"})

    email_matches = list(EMAIL_REGEX.finditer(original_text))
    phone_matches = list(PHONE_REGEX.finditer(original_text))
    all_matches = sorted(email_matches + phone_matches, key=lambda x: x.start())

    text_copy = original_text
    replacement_info = []
    offset = 0

    for match in all_matches:
        entity_type = "EMAIL_ADDRESS" if match.re == EMAIL_REGEX else "PHONE_NUMBER"
        token = generate_token(entity_type, match.group(0))

        original_start = match.start()
        original_end = match.end()
        token_start = original_start + offset
        token_end = token_start + len(token)

        replacement_info.append((original_start, original_end, token_start, token_end))

        text_copy = text_copy[:original_start + offset] + token + text_copy[original_end + offset:]
        offset += len(token) - (original_end - original_start)

    stripped_text, pos_map = strip_markdown(text_copy)

    analyzer = build_analyzer(language)
    results = analyzer.analyze(
        text=stripped_text,
        language=language,
        entities=["IBAN_CODE", "ORGANIZATION", "PERSON", "LOCATION", "ID"],
        score_threshold=0.3,
    )
    if enabled_types:
        results = [r for r in results if r.entity_type in enabled_types]
    results = trim_org_results(results, stripped_text)
    results = filter_overlaps(results)

    for r in results:
        pos_in_copy_start = pos_map[r.start]
        pos_in_copy_end = pos_map[r.end - 1] + 1

        span_in_copy = text_copy[pos_in_copy_start:pos_in_copy_end]
        if span_in_copy.startswith(("EMAIL_ADDRESS_", "PHONE_NUMBER_")):
            continue

        pos_in_original_start = pos_in_copy_start
        pos_in_original_end = pos_in_copy_end

        for orig_start, orig_end, token_start, token_end in replacement_info:
            if token_end <= pos_in_copy_start:
                original_length = orig_end - orig_start
                token_length = token_end - token_start
                pos_in_original_start -= (token_length - original_length)
                pos_in_original_end -= (token_length - original_length)
            elif token_start < pos_in_copy_end and token_end > pos_in_copy_start:
                pos_in_original_start = None
                break

        if pos_in_original_start is not None:
            entities.append({"start": pos_in_original_start, "end": pos_in_original_end, "type": r.entity_type})

    entities = sorted(entities, key=lambda x: (x["start"], -(x["end"] - x["start"])))
    filtered = []
    for e in entities:
        overlap = False
        for f in filtered:
            if e["start"] < f["end"] and e["end"] > f["start"]:
                overlap = True
                break
        if not overlap:
            filtered.append(e)

    return sorted(filtered, key=lambda x: x["start"])


def pseudonymize(text: str, session_id: str, store: dict, enabled_types=None) -> str:
    try:
        lang = detect(text)
        if lang not in ["en", "de"]:
            lang = "en"
    except:
        lang = "en"

    mapping = store.setdefault(session_id, {})

    entities = detect_entities(text, lang, enabled_types=enabled_types)

    entities = sorted(entities, key=lambda x: x["start"], reverse=True)

    for entity in entities:
        original = text[entity["start"]:entity["end"]]
        token = generate_token(entity["type"], original)
        mapping[token] = original
        text = text[:entity["start"]] + token + text[entity["end"]:]

    return text
