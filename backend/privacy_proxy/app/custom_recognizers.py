from presidio_analyzer import PatternRecognizer, Pattern

# --- EMAIL (en + de) ---
email_patterns = [
    Pattern("EMAIL", r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", 0.99),
]
email_recognizer_en = PatternRecognizer(
    supported_entity="EMAIL_ADDRESS", patterns=email_patterns, supported_language="en",
    context=[],
)
email_recognizer_de = PatternRecognizer(
    supported_entity="EMAIL_ADDRESS", patterns=email_patterns, supported_language="de",
    context=[],
)

# --- ORG (en + de) ---
org_patterns = [
    Pattern("ORG_SUFFIX", r"\b(?:[A-Z][\w-]*\s){1,3}(?:GmbH|Inc|Ltd|AG|Corp|LLC|SE|Co|SA|SAS|SARL|BV|NV|Bank|Group|Partners|Solutions|Technologies|Foundation|Institute|Association)\b", 0.90),
]
org_recognizer_en = PatternRecognizer(
    supported_entity="ORGANIZATION", patterns=org_patterns, supported_language="en",
    context=[],
)
org_recognizer_de = PatternRecognizer(
    supported_entity="ORGANIZATION", patterns=org_patterns, supported_language="de",
    context=[],
)

# --- IBAN (en + de) ---
iban_patterns = [
    Pattern("IBAN", r"\b[A-Z]{2}\d{2}\s?\d{4}\s?\d{4}\s?\d{4}\s?\d{4}\s?\d{0,2}\b", 0.95),
]
iban_recognizer_en = PatternRecognizer(
    supported_entity="IBAN_CODE", patterns=iban_patterns, supported_language="en",
    context=[],
)
iban_recognizer_de = PatternRecognizer(
    supported_entity="IBAN_CODE", patterns=iban_patterns, supported_language="de",
    context=[],
)

# --- PHONE (en + de) ---
phone_patterns = [
    Pattern("PHONE_INTL", r"\b\+\d{1,3}[\s.-]?\d{2,4}[\s.-]?\d{3,10}\b", 0.85),
]
phone_recognizer_en = PatternRecognizer(
    supported_entity="PHONE_NUMBER", patterns=phone_patterns, supported_language="en",
    context=[],
)
phone_recognizer_de = PatternRecognizer(
    supported_entity="PHONE_NUMBER", patterns=phone_patterns, supported_language="de",
    context=[],
)

# --- ID (en + de) ---
id_patterns = [
    Pattern("PASSPORT", r"\b[A-Z][0-9]{2}[A-Z0-9]{5,7}\b", 0.6),
    Pattern("ID_NUMBER", r"\b\d{2,4}[-/]\d{4,8}[-/]\d{2,4}\b", 0.6),
]
id_recognizer_en = PatternRecognizer(
    supported_entity="ID", patterns=id_patterns, supported_language="en",
    context=[],
)
id_recognizer_de = PatternRecognizer(
    supported_entity="ID", patterns=id_patterns, supported_language="de",
    context=[],
)
