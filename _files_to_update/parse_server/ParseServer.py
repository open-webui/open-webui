from __future__ import annotations

import base64
import io
import mimetypes
import os
import re
import socket
import time
from pathlib import Path
from typing import Dict, List, Literal, Optional, Union
from uuid import uuid4

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel

try:
    from pypdf import PdfReader
except Exception:  # pragma: no cover
    PdfReader = None


def get_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(0)
    try:
        # doesn't even have to be reachable
        s.connect(('10.254.254.254', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP


app = FastAPI(title="Mistral OCR Emulator")


UPLOAD_DIR = Path(os.environ.get("OCR_UPLOAD_DIR", "./ocr_uploads")).resolve()
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


class StoredFile(BaseModel):
    id: str
    path: str
    filename: str
    bytes: int
    created_at: int
    purpose: str
    content_type: str


_FILES: Dict[str, StoredFile] = {}

# =========================
# Request Models
# =========================

class ImageURLDocument(BaseModel):
    type: Literal["image_url"]
    image_url: str

class DocumentURLDocument(BaseModel):
    type: Literal["document_url"]
    document_url: str

class ImageB64Document(BaseModel):
    type: Literal["image_b64"]
    b64_data: str


class FileIDDocument(BaseModel):
    type: Literal["file_id"]
    file_id: str

Document = Union[
    ImageURLDocument,
    DocumentURLDocument,
    ImageB64Document,
    FileIDDocument,
]

class OCRRequest(BaseModel):
    model: str
    document: Document


# =========================
# Response Models
# =========================

class OCRPage(BaseModel):
    index: int
    markdown: str

class OCRUsageInfo(BaseModel):
    pages_processed: int

class OCRResponse(BaseModel):
    model: str
    pages: List[OCRPage]
    usage_info: OCRUsageInfo


class FileObject(BaseModel):
    id: str
    object: Literal["file"] = "file"
    bytes: int
    created_at: int
    filename: str
    purpose: str
    status: Literal["uploaded"] = "uploaded"


def _safe_filename(name: str) -> str:
    name = (name or "upload").strip()
    name = name.replace("\x00", "")
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", name)
    return name[:200] or "upload"


def _is_probably_pdf(data: bytes) -> bool:
    return data.startswith(b"%PDF-")


def _normalize_text(text: str) -> str:
    text = text.replace("\x00", "")
    text = re.sub(r"\r\n?", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _pdf_to_markdown(data: bytes) -> List[OCRPage]:
    if PdfReader is None:
        raise HTTPException(
            status_code=500,
            detail="PDF support not available (missing pypdf)",
        )

    reader = PdfReader(io.BytesIO(data))
    pages: List[OCRPage] = []
    for idx, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        text = _normalize_text(text)
        md = f"## Page {idx + 1}\n\n{text}\n" if text else f"## Page {idx + 1}\n\n"
        pages.append(OCRPage(index=idx, markdown=md))
    return pages


# =========================
# OCR Processing Routines
# =========================

def process_image_url(doc: ImageURLDocument) -> OCRPage:
    return OCRPage(
        index=0,
        markdown=(
            "# OCR Result (Image URL)\n\n"
            f"Source URL: `{doc.image_url}`\n\n"
            "🜂 Machine-Spirit reports visible glyphs."
        ),
    )

def process_document_url(doc: DocumentURLDocument) -> OCRPage:
    return OCRPage(
        index=0,
        markdown=(
            "# OCR Result (Document URL)\n\n"
            f"Document: `{doc.document_url}`\n\n"
            "📄 Multi-page scripture detected."
        ),
    )

def process_image_b64(doc: ImageB64Document) -> OCRPage:
    try:
        raw = base64.b64decode(doc.b64_data)
        size = len(raw)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid base64 payload")

    return OCRPage(
        index=0,
        markdown=(
            "# OCR Result (Base64 Image)\n\n"
            f"Decoded image size: `{size}` bytes\n\n"
            "🜁 Binary flesh rendered into sacred text."
        ),
    )


# =========================
# Endpoint
# =========================

@app.post("/v1/files", response_model=FileObject)
async def upload_file(request: Request):
    content_type = request.headers.get("content-type", "")
    print("Upload content-type:", content_type)
    filename = "upload"
    purpose = request.query_params.get("purpose") or "assistants"
    print("Upload purpose:", purpose)
    data: Optional[bytes] = None
    upload_ct = "application/octet-stream"

    # Open WebUI sometimes sends raw bytes (not multipart).
    if content_type.startswith("multipart/form-data"):
        form = await request.form()
        file_obj = form.get("file")
        if file_obj is None:
            raise HTTPException(status_code=400, detail="Missing form field: file")

        # Starlette's UploadFile has .filename/.content_type/.read()
        filename = getattr(file_obj, "filename", None) or filename
        upload_ct = getattr(file_obj, "content_type", None) or upload_ct
        data = await file_obj.read()
        purpose = str(form.get("purpose") or purpose)
    else:
        data = await request.body()
        filename = (
            request.headers.get("x-filename")
            or request.headers.get("x-file-name")
            or filename
        )
        upload_ct = request.headers.get("content-type", upload_ct) or upload_ct

    if not data:
        raise HTTPException(status_code=400, detail="Empty upload")

    safe_name = _safe_filename(str(filename))
    print("Safe filename:", safe_name)
    if "." not in safe_name:
        if _is_probably_pdf(data) or upload_ct == "application/pdf":
            safe_name += ".pdf"

    file_id = str(uuid4())
    stored_path = UPLOAD_DIR / f"{file_id}_{safe_name}"
    stored_path.write_bytes(data)

    created_at = int(time.time())
    stored = StoredFile(
        id=file_id,
        path=str(stored_path),
        filename=safe_name,
        bytes=len(data),
        created_at=created_at,
        purpose=str(purpose),
        content_type=str(upload_ct),
    )
    _FILES[file_id] = stored

    print("Process file")

    return FileObject(
        id=file_id,
        bytes=stored.bytes,
        created_at=stored.created_at,
        filename=stored.filename,
        purpose=stored.purpose,
    )


@app.get("/v1/files/{file_id}/content")
async def get_file_content(file_id: str):
    stored = _FILES.get(file_id)
    if stored is None:
        raise HTTPException(status_code=404, detail="File not found")

    path = Path(stored.path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="File missing on disk")

    media_type = stored.content_type
    if not media_type or media_type == "application/octet-stream":
        guessed, _ = mimetypes.guess_type(stored.filename)
        media_type = guessed or "application/octet-stream"

    return FileResponse(path, media_type=media_type, filename=stored.filename)




@app.post("/v1/ocr", response_model=OCRResponse)
@app.post("/v1/ocr1", response_model=OCRResponse)
async def ocr_endpoint(req: OCRRequest):
    print("Received OCR request:", req)
    doc = req.document

    # Dispatch by document.type
    if doc.type == "image_url":
        page = process_image_url(doc)

    elif doc.type == "document_url":
        page = process_document_url(doc)

    elif doc.type == "image_b64":
        page = process_image_b64(doc)

    elif doc.type == "file_id":
        stored = _FILES.get(doc.file_id)
        if stored is None:
            raise HTTPException(status_code=404, detail="File not found")
        raw = Path(stored.path).read_bytes()

        if stored.filename.lower().endswith(".pdf") or _is_probably_pdf(raw):
            pages = _pdf_to_markdown(raw)
            return OCRResponse(
                model=req.model,
                pages=pages,
                usage_info=OCRUsageInfo(pages_processed=len(pages)),
            )

        # Fallback: treat as text
        text = _normalize_text(raw.decode("utf-8", errors="ignore"))
        return OCRResponse(
            model=req.model,
            pages=[OCRPage(index=0, markdown=text)],
            usage_info=OCRUsageInfo(pages_processed=1),
        )

    else:
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported document type: {doc.type}",
        )

    return OCRResponse(
        model=req.model,
        pages=[page],
        usage_info=OCRUsageInfo(pages_processed=1),
    )


# =========================
# Sanity Check
# =========================

@app.get("/health")
def health():
    return {"status": "Machine Spirit operational"}

if __name__ == "__main__":
    """Запуск uvicorn сервера."""
    ip = str(get_ip())
    uvicorn.run(app, host=ip, port=7770, log_level="info")
