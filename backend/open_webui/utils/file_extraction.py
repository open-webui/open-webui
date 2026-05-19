"""Chat-attachment text extraction.

Bridges the gap between file uploads and chat-completion content parts: when a
non-image, non-PDF file is attached to a chat, this module is responsible for
running the configured Loader (Docx2txt, Unstructured*, Tika, Docling, etc.)
and caching the extracted text in `file.data.content` so the openai.py
file-part loop can replace the `type: "file"` content part with an inline
`type: "text"` part wrapping a `<document>` envelope.

Two entry points:

- `extract_and_cache_file_content(request, file_id)` — sync, FastAPI
  BackgroundTask. Fires from `upload_file_handler` immediately after the
  file row is created. Idempotent.

- `get_or_extract_file_content(request, file_id, user)` — async, called from
  `generate_chat_completion` in routers/openai.py. Returns cached content if
  available; polls if a background task is in flight; runs synchronously
  inline for old files uploaded before background extraction was wired up.

The Loader-construction block (~40 lines of `request.app.state.config.XXX`
arguments) lived inline in `routers/retrieval.py:process_file`. It now lives
in `_build_loader_from_request_config` here; retrieval.py imports it.
"""

import asyncio
import logging
import time
from typing import Optional

from fastapi import Request

from open_webui.env import SRC_LOG_LEVELS
from open_webui.models.files import Files
from open_webui.retrieval.loaders.main import Loader
from open_webui.storage.provider import Storage
from open_webui.utils.misc import calculate_sha256_string

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS.get("RAG", "INFO"))


_SKIP_EXTRACTION_EXTS = {"pdf"}
_SKIP_EXTRACTION_MIME_PREFIXES = ("image/",)


def file_needs_extraction(
    content_type: Optional[str], file_ext: Optional[str]
) -> bool:
    """Whether this file should have its text extracted into ``file.data.content``.

    False for images (they go through the vision pipeline as ``image_url`` parts)
    and PDFs (they go through OpenRouter's ``file-parser`` plugin path).
    True for everything else, including plain text — extraction is cheap for
    TextLoader and gives us a single populated content field for the lazy
    fallback to read.
    """
    ct = (content_type or "").lower()
    ext = (file_ext or "").lower().lstrip(".")
    if ct == "application/pdf" or ext in _SKIP_EXTRACTION_EXTS:
        return False
    if any(ct.startswith(p) for p in _SKIP_EXTRACTION_MIME_PREFIXES):
        return False
    return True


def format_extracted_document(
    filename: str,
    text: str,
    error: Optional[str] = None,
) -> str:
    """Wrap extracted file content in a ``<document>`` envelope for inline prompt
    injection. Same shape as ``buildTextFileBlocks`` on the frontend so the
    on-prompt format is uniform across browser-side and server-side extraction.

    When ``error`` is set, the envelope includes an ``error`` attribute and a
    fallback body so the model sees an explicit failure marker rather than
    silently missing the file.
    """

    def _esc(s: str) -> str:
        return (
            str(s)
            .replace("&", "&amp;")
            .replace('"', "&quot;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )

    name = _esc(filename or "file")
    if error:
        body = text or "[Could not extract text from this file]"
        return (
            f'<document filename="{name}" error="{_esc(error)}">\n'
            f"{body}\n"
            f"</document>"
        )
    return f'<document filename="{name}">\n{text}\n</document>'


def _build_loader_from_request_config(request: Request) -> Loader:
    """Single source of truth for ``Loader`` construction.

    Mirrors the inline block previously living at
    ``routers/retrieval.py:process_file`` (lines ~1365-1404). Both call sites
    must stay in sync so chat-attachment extraction and explicit
    ``/process`` invocations produce identical output for the same file.
    """
    cfg = request.app.state.config
    return Loader(
        engine=cfg.CONTENT_EXTRACTION_ENGINE,
        DATALAB_MARKER_API_KEY=cfg.DATALAB_MARKER_API_KEY,
        DATALAB_MARKER_API_BASE_URL=cfg.DATALAB_MARKER_API_BASE_URL,
        DATALAB_MARKER_ADDITIONAL_CONFIG=cfg.DATALAB_MARKER_ADDITIONAL_CONFIG,
        DATALAB_MARKER_SKIP_CACHE=cfg.DATALAB_MARKER_SKIP_CACHE,
        DATALAB_MARKER_FORCE_OCR=cfg.DATALAB_MARKER_FORCE_OCR,
        DATALAB_MARKER_PAGINATE=cfg.DATALAB_MARKER_PAGINATE,
        DATALAB_MARKER_STRIP_EXISTING_OCR=cfg.DATALAB_MARKER_STRIP_EXISTING_OCR,
        DATALAB_MARKER_DISABLE_IMAGE_EXTRACTION=cfg.DATALAB_MARKER_DISABLE_IMAGE_EXTRACTION,
        DATALAB_MARKER_FORMAT_LINES=cfg.DATALAB_MARKER_FORMAT_LINES,
        DATALAB_MARKER_USE_LLM=cfg.DATALAB_MARKER_USE_LLM,
        DATALAB_MARKER_OUTPUT_FORMAT=cfg.DATALAB_MARKER_OUTPUT_FORMAT,
        EXTERNAL_DOCUMENT_LOADER_URL=cfg.EXTERNAL_DOCUMENT_LOADER_URL,
        EXTERNAL_DOCUMENT_LOADER_API_KEY=cfg.EXTERNAL_DOCUMENT_LOADER_API_KEY,
        TIKA_SERVER_URL=cfg.TIKA_SERVER_URL,
        DOCLING_SERVER_URL=cfg.DOCLING_SERVER_URL,
        DOCLING_PARAMS={
            "do_ocr": cfg.DOCLING_DO_OCR,
            "force_ocr": cfg.DOCLING_FORCE_OCR,
            "ocr_engine": cfg.DOCLING_OCR_ENGINE,
            "ocr_lang": cfg.DOCLING_OCR_LANG,
            "pdf_backend": cfg.DOCLING_PDF_BACKEND,
            "table_mode": cfg.DOCLING_TABLE_MODE,
            "pipeline": cfg.DOCLING_PIPELINE,
            "do_picture_description": cfg.DOCLING_DO_PICTURE_DESCRIPTION,
            "picture_description_mode": cfg.DOCLING_PICTURE_DESCRIPTION_MODE,
            "picture_description_local": cfg.DOCLING_PICTURE_DESCRIPTION_LOCAL,
            "picture_description_api": cfg.DOCLING_PICTURE_DESCRIPTION_API,
            **cfg.DOCLING_PARAMS,
        },
        PDF_EXTRACT_IMAGES=cfg.PDF_EXTRACT_IMAGES,
        DOCUMENT_INTELLIGENCE_ENDPOINT=cfg.DOCUMENT_INTELLIGENCE_ENDPOINT,
        DOCUMENT_INTELLIGENCE_KEY=cfg.DOCUMENT_INTELLIGENCE_KEY,
        MISTRAL_OCR_API_KEY=cfg.MISTRAL_OCR_API_KEY,
        MINERU_API_MODE=cfg.MINERU_API_MODE,
        MINERU_API_URL=cfg.MINERU_API_URL,
        MINERU_API_KEY=cfg.MINERU_API_KEY,
        MINERU_PARAMS=cfg.MINERU_PARAMS,
    )


def _extract_now(request: Request, file_id: str) -> None:
    """Run the Loader on a file and cache the result. No idempotency check —
    callers should gate on ``file.data.status`` if they want one. Always sets
    status="processing" before running and status="completed"|"failed" after.
    """
    file = Files.get_file_by_id(file_id)
    if not file or not file.path:
        return

    Files.update_file_data_by_id(file_id, {"status": "processing"})

    try:
        file_path = Storage.get_file(file.path)
        loader = _build_loader_from_request_config(request)
        docs = loader.load(
            file.filename,
            (file.meta or {}).get("content_type"),
            file_path,
        )
        text = " ".join([doc.page_content for doc in docs])

        Files.update_file_data_by_id(
            file_id,
            {"content": text, "status": "completed"},
        )
        Files.update_file_hash_by_id(file_id, calculate_sha256_string(text))
    except Exception as e:
        log.exception(
            "file_extraction: failed to extract content from %s: %s", file_id, e
        )
        Files.update_file_data_by_id(
            file_id,
            {"status": "failed", "error": str(e)},
        )


def extract_and_cache_file_content(request: Request, file_id: str) -> None:
    """BackgroundTask entry. Idempotent — does nothing if the file is already
    extracted or currently being extracted by another worker.

    Race window: two callers can both observe ``status="pending"`` and proceed
    to ``_extract_now`` concurrently. Both produce the same content for the
    same input, so the worst case is one wasted extraction; no data corruption.
    """
    file = Files.get_file_by_id(file_id)
    if not file:
        return
    data = file.data or {}
    if data.get("status") == "completed" and data.get("content"):
        return
    if data.get("status") == "processing":
        return
    _extract_now(request, file_id)


async def get_or_extract_file_content(
    request: Request,
    file_id: str,
    user=None,
    *,
    timeout_seconds: int = 60,
) -> str:
    """Lazy entry for chat-completion-time text extraction.

    - Cached content present → return immediately.
    - status="processing" → poll with exponential backoff up to ``timeout_seconds``.
    - status="failed" → return "" (caller wraps in <document error="..."> envelope).
    - status in (None, "pending") → run synchronously in a worker thread so
      old files (uploaded before background extraction was wired up) still
      work on first use.
    """
    file = Files.get_file_by_id(file_id)
    if not file:
        return ""

    data = file.data or {}
    cached = data.get("content")
    if cached:
        return cached

    status = data.get("status")

    if status == "failed":
        return ""

    if status == "processing":
        deadline = time.monotonic() + timeout_seconds
        delay = 0.5
        while time.monotonic() < deadline:
            await asyncio.sleep(delay)
            delay = min(delay * 1.5, 5.0)
            file = Files.get_file_by_id(file_id)
            if not file:
                return ""
            data = file.data or {}
            content = data.get("content")
            if data.get("status") == "completed" and content:
                return content
            if data.get("status") == "failed":
                return ""
        log.warning(
            "file_extraction: polling timeout for file %s; giving up", file_id
        )
        return ""

    # Pending / unknown — run inline in a worker thread.
    await asyncio.to_thread(_extract_now, request, file_id)
    file = Files.get_file_by_id(file_id)
    if not file:
        return ""
    return (file.data or {}).get("content", "") or ""
