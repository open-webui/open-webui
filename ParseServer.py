from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Literal, Union, List, Optional
import base64
import uuid
from fastapi import FastAPI, Body, Request
import socket
import uvicorn


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

Document = Union[
    ImageURLDocument,
    DocumentURLDocument,
    ImageB64Document,
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

@app.post("/v1/ocr", response_model=OCRResponse)
async def ocr_endpoint(req: OCRRequest):

    doc = req.document

    # Dispatch by document.type
    if doc.type == "image_url":
        page = process_image_url(doc)

    elif doc.type == "document_url":
        page = process_document_url(doc)

    elif doc.type == "image_b64":
        page = process_image_b64(doc)

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
    uvicorn.run(app, host=ip, port=7778, log_level="info")
