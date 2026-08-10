"""Arabic text normalization utilities for search, RAG and transcription.

Arabic script has multiple orthographic variants for the same word (hamza
forms, yaa, teh marbuta, optional diacritics). Normalizing on BOTH the stored
text and the query makes search and retrieval consistent across these
variants, e.g. إ/أ/آ/ا -> ا, ى -> ي, ة -> ه.
"""

from __future__ import annotations

import re

# Combining marks: tashkeel (U+064B–U+065F), superscript alef (U+0670), tatweel (U+0640),
# and Arabic-Indic/other combining marks (U+0610–U+061A)
ARABIC_DIACRITICS_RE = re.compile(r'[\u0610-\u061A\u064B-\u065F\u0670\u0640]+')

# Main Arabic block + extended blocks (Kurdish/Persian/Urdu scripts share these ranges)
ARABIC_SCRIPT_RE = re.compile(r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]')


def is_arabic_text(text: str) -> bool:
    """Return True when the string contains at least one Arabic-script character."""
    if not isinstance(text, str) or not text:
        return False
    return bool(ARABIC_SCRIPT_RE.search(text))


def normalize_arabic_text(text: str) -> str:
    """Normalize common Arabic orthographic variants to canonical forms.

    - Unify hamza: أ/إ/آ -> ا
    - Unify yaa: ى -> ي, ئ -> ي
    - Unify waw-hamza: ؤ -> و
    - Unify teh marbuta: ة -> ه
    - Strip tashkeel (diacritics) and tatweel
    """
    if not isinstance(text, str) or not text:
        return text

    text = text.replace('\u0623', '\u0627')  # أ -> ا
    text = text.replace('\u0625', '\u0627')  # إ -> ا
    text = text.replace('\u0622', '\u0627')  # آ -> ا
    text = text.replace('\u0624', '\u0648')  # ؤ -> و
    text = text.replace('\u0626', '\u064A')  # ئ -> ي
    text = text.replace('\u0649', '\u064A')  # ى -> ي
    text = text.replace('\u0629', '\u0647')  # ة -> ه
    text = ARABIC_DIACRITICS_RE.sub('', text)
    return text
