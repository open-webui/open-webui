"""Headless LibreOffice conversion for the "Convert to PDF" attachment mode.

When the user picks PDF mode on a non-PDF attachment (docx, pptx, xlsx, odt,
rtf, html, epub, etc.), this module shells out to LibreOffice headless to
produce a sibling .pdf file. The converted PDF is persisted as its own
`FileModel` row (so it has a proper id/path/meta) and linked back to the
original via `file.data.pdf_file_id`. The chat-completion path in
`routers/openai.py` then reads that linked PDF, base64-encodes it, and
forwards it to OpenRouter with the existing `file-parser` plugin block —
zero new chat-completion code, just a new file artifact.

State machine on the *source* file's `file.data`:

    pdf_status: "pending" → "processing" → "completed" | "failed"
    pdf_file_id: <uuid of converted file> (set on completed)
    pdf_error:   <message> (set on failed)

`pdf_status` is intentionally separate from the text-extraction `status` so
text extraction and PDF conversion can run concurrently without clobbering
each other's state.
"""

import asyncio
import logging
import os
import subprocess
import tempfile
import time
import uuid
from typing import Optional

from fastapi import Request

from open_webui.env import SRC_LOG_LEVELS
from open_webui.models.files import FileForm, FileModel, Files
from open_webui.storage.provider import Storage

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS.get("RAG", "INFO"))


# Real-world docx → PDF is 2-8s. Anything past 120s is almost certainly a hung
# LibreOffice (corrupt input, exotic XML, font-substitution loop).
_CONVERSION_TIMEOUT_SECONDS = 120


def _get_libreoffice_bin(request: Request) -> Optional[str]:
    """Resolve the LibreOffice binary path. Probed once at startup in
    ``main.py`` and exposed via ``app.state.LIBREOFFICE_BIN``.
    """
    return getattr(request.app.state, "LIBREOFFICE_BIN", None)


def _convert_now(request: Request, file_id: str) -> None:
    """Run LibreOffice on a file and cache the result. No idempotency check —
    callers should gate on ``file.data.pdf_status`` if they want one.
    """
    file = Files.get_file_by_id(file_id)
    if not file or not file.path:
        return

    libreoffice_bin = _get_libreoffice_bin(request)
    if not libreoffice_bin:
        Files.update_file_data_by_id(
            file_id,
            {
                "pdf_status": "failed",
                "pdf_error": "LibreOffice is not installed on the server. PDF conversion is unavailable.",
            },
        )
        return

    Files.update_file_data_by_id(file_id, {"pdf_status": "processing"})

    try:
        input_path = Storage.get_file(file.path)
        with tempfile.TemporaryDirectory(prefix="ow_libreoffice_") as workdir:
            # Each conversion gets its own UserInstallation so concurrent
            # LibreOffice invocations don't fight over the same profile lock.
            profile_dir = os.path.join(workdir, "lo_profile")
            os.makedirs(profile_dir, exist_ok=True)

            outdir = os.path.join(workdir, "out")
            os.makedirs(outdir, exist_ok=True)

            cmd = [
                libreoffice_bin,
                f"-env:UserInstallation=file://{profile_dir}",
                "--headless",
                "--norestore",
                "--nolockcheck",
                "--convert-to",
                "pdf",
                "--outdir",
                outdir,
                input_path,
            ]

            result = subprocess.run(
                cmd,
                timeout=_CONVERSION_TIMEOUT_SECONDS,
                capture_output=True,
                check=False,
            )

            if result.returncode != 0:
                stderr = result.stderr.decode("utf-8", errors="replace")[:500]
                raise Exception(
                    f"LibreOffice exited with code {result.returncode}: {stderr}"
                )

            input_basename = os.path.basename(input_path)
            input_stem = os.path.splitext(input_basename)[0]
            pdf_filename_on_disk = f"{input_stem}.pdf"
            pdf_path_in_workdir = os.path.join(outdir, pdf_filename_on_disk)

            if not os.path.exists(pdf_path_in_workdir):
                raise Exception(
                    f"LibreOffice did not produce expected file {pdf_filename_on_disk}"
                )

            # Persist the converted PDF as its own FileModel, mirroring the
            # shape of upload_file_handler so downstream code (chat-attachment
            # base64, the file detail endpoint, etc.) treats it identically
            # to an uploaded PDF.
            new_id = str(uuid.uuid4())
            original_stem = os.path.splitext(file.filename)[0]
            display_name = f"{original_stem}.pdf"
            storage_name = f"{new_id}_{display_name}"

            with open(pdf_path_in_workdir, "rb") as f:
                size, stored_path = Storage.upload_file(
                    f,
                    storage_name,
                    {
                        "OpenWebUI-User-Id": file.user_id,
                        "OpenWebUI-File-Id": new_id,
                        "OpenWebUI-Source-File-Id": file_id,
                    },
                )

            new_file_item = Files.insert_new_file(
                file.user_id,
                FileForm(
                    id=new_id,
                    filename=display_name,
                    path=stored_path,
                    data={
                        "status": "completed",
                        "source_file_id": file_id,
                    },
                    meta={
                        "name": display_name,
                        "content_type": "application/pdf",
                        "size": size,
                    },
                ),
            )

            if not new_file_item:
                raise Exception("Failed to persist converted PDF file row")

            Files.update_file_data_by_id(
                file_id,
                {
                    "pdf_status": "completed",
                    "pdf_file_id": new_id,
                },
            )

    except subprocess.TimeoutExpired:
        log.warning("LibreOffice conversion timed out for file %s", file_id)
        Files.update_file_data_by_id(
            file_id,
            {
                "pdf_status": "failed",
                "pdf_error": f"PDF conversion timed out after {_CONVERSION_TIMEOUT_SECONDS}s",
            },
        )
    except Exception as e:
        log.exception(
            "file_conversion: failed to convert %s to PDF: %s", file_id, e
        )
        Files.update_file_data_by_id(
            file_id,
            {"pdf_status": "failed", "pdf_error": str(e)},
        )


def convert_and_cache_file_to_pdf(request: Request, file_id: str) -> None:
    """BackgroundTask entry. Idempotent — skips if already converted or
    currently running. Triggered by the ``/process-mode`` endpoint when the
    user picks PDF mode on a file chip.
    """
    file = Files.get_file_by_id(file_id)
    if not file:
        return
    data = file.data or {}
    if data.get("pdf_file_id"):
        return
    if data.get("pdf_status") == "processing":
        return
    _convert_now(request, file_id)


async def get_or_convert_to_pdf(
    request: Request,
    file_id: str,
    user=None,
    *,
    timeout_seconds: int = 180,
) -> Optional[FileModel]:
    """Lazy async entry. Returns the converted PDF's FileModel, or None on
    failure. Same state-machine pattern as
    :func:`open_webui.utils.file_extraction.get_or_extract_file_content`:
    cached → return; processing → poll; pending → run inline.
    """
    file = Files.get_file_by_id(file_id)
    if not file:
        return None

    data = file.data or {}
    pdf_file_id = data.get("pdf_file_id")
    if pdf_file_id:
        return Files.get_file_by_id(pdf_file_id)

    pdf_status = data.get("pdf_status")

    if pdf_status == "failed":
        return None

    if pdf_status == "processing":
        deadline = time.monotonic() + timeout_seconds
        delay = 0.5
        while time.monotonic() < deadline:
            await asyncio.sleep(delay)
            delay = min(delay * 1.5, 5.0)
            file = Files.get_file_by_id(file_id)
            if not file:
                return None
            data = file.data or {}
            new_pdf_id = data.get("pdf_file_id")
            if new_pdf_id:
                return Files.get_file_by_id(new_pdf_id)
            if data.get("pdf_status") == "failed":
                return None
        log.warning(
            "file_conversion: polling timeout for file %s; giving up", file_id
        )
        return None

    # Pending / unknown — run inline in a worker thread.
    await asyncio.to_thread(_convert_now, request, file_id)
    file = Files.get_file_by_id(file_id)
    if not file:
        return None
    pdf_file_id = (file.data or {}).get("pdf_file_id")
    return Files.get_file_by_id(pdf_file_id) if pdf_file_id else None
