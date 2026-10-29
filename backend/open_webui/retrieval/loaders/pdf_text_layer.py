"""Decide per PDF whether Docling has to run OCR on it.

``DOCLING_PARAMS`` is passed to Docling unchanged, so ``do_ocr`` is one switch
for every upload: off keeps the text layer of a digital PDF and leaves a scan
empty, on makes Docling OCR pages whose bitmap covers most of the page area -
including pages that already carry readable text (a scan with an invisible OCR
layer, a page with a scanned background). That OCR pass is the slow part of an
extraction and its output lands next to text the file already contains.

With ``DOCLING_OCR_MODE=auto`` the text layer of the uploaded PDF is read here
instead, and ``do_ocr`` is set for that one file: off while the document has a
text layer, on when it is a scan. Only a sample of the pages is read, so the
probe stays cheap next to the extraction it guards.
"""

from __future__ import annotations

import logging
import os

from pypdf import PdfReader

log = logging.getLogger(__name__)

# Pages read per file: enough to tell a scan from a digital document, few
# enough that the probe costs a fraction of the extraction itself.
MAX_PROBED_PAGES = 25

# Characters a page has to yield to count as text. A page number or a running
# header alone is not a usable text layer.
MIN_TEXT_CHARS_PER_PAGE = 32

# Share of probed pages without any text from which the whole file is treated
# as a scan and handed to OCR.
SCAN_PAGE_RATIO = 0.2


def _sample_pages(page_count: int, limit: int = MAX_PROBED_PAGES) -> list[int]:
    """Spread the probe over the document instead of reading its first pages."""
    if page_count <= limit:
        return list(range(page_count))
    step = page_count / limit
    return sorted({int(index * step) for index in range(limit)})


def text_layer_coverage(path: str | os.PathLike[str]) -> tuple[int, int] | None:
    """Count probed pages and those carrying text, or return None if unreadable."""
    try:
        reader = PdfReader(str(path))
        if reader.is_encrypted and not reader.decrypt(''):
            return None
        page_count = len(reader.pages)
        if page_count == 0:
            return None

        text_pages = 0
        probed_pages = 0
        for number in _sample_pages(page_count):
            try:
                text = reader.pages[number].extract_text() or ''
            except Exception:
                # A page that can't be read is no evidence for a text layer.
                continue
            probed_pages += 1
            if len(''.join(text.split())) >= MIN_TEXT_CHARS_PER_PAGE:
                text_pages += 1
    except Exception as e:
        log.warning('Could not read the text layer of %s: %s', os.path.basename(str(path)), e)
        return None

    if probed_pages == 0:
        return None
    return text_pages, probed_pages


def needs_ocr(path: str | os.PathLike[str]) -> bool | None:
    """Return True for a scan, False for a text-layer document, None if undecided."""
    coverage = text_layer_coverage(path)
    if coverage is None:
        return None

    text_pages, probed_pages = coverage
    scanned_share = (probed_pages - text_pages) / probed_pages
    return scanned_share >= SCAN_PAGE_RATIO
