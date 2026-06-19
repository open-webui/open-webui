"""Extrator de .pdf -> Arvore de Blocos Nidum (Fatia 3).

Foco desta fatia: extrair o TEXTO REAL e, crucialmente, DISTINGUIR texto de
imagem. Se o PDF nao tem camada de texto (digitalizacao), NAO inventa conteudo:
sinaliza is_scanned/needs_ocr e registra um aviso. OCR de fato fica no roadmap.

Sem imports de open_webui. Usa pdfplumber (MIT). Deteccao de titulos por
heuristica de fonte fica para refinamento posterior; aqui produzimos paragrafos
com a referencia de pagina (path.page).
"""

import io
import logging
import re

log = logging.getLogger(__name__)


def extract_pdf(data: bytes) -> dict:
    if not data:
        raise ValueError("arquivo pdf vazio")

    import pdfplumber  # lazy: so quando ha um PDF para processar

    try:
        pdf = pdfplumber.open(io.BytesIO(data))
    except Exception as e:
        raise ValueError(f"nao foi possivel abrir o .pdf: {e}")

    blocks = []
    warnings = []
    order = 0
    pages_with_text = 0

    with pdf:
        page_count = len(pdf.pages)
        for pidx, page in enumerate(pdf.pages, start=1):
            text = (page.extract_text() or "").strip()
            if not text:
                has_images = bool(getattr(page, "images", None))
                if has_images:
                    warnings.append(
                        f"pagina {pidx}: sem texto extraivel (provavel imagem/digitalizacao)"
                    )
                else:
                    warnings.append(f"pagina {pidx}: sem texto extraivel")
                continue
            pages_with_text += 1
            # Divide em paragrafos por linha em branco.
            for para in re.split(r"\n\s*\n", text):
                para = para.strip()
                if not para:
                    continue
                order += 1
                blocks.append(
                    {
                        "id": "b-%06d" % order,
                        "type": "paragraph",
                        "order": order,
                        "text": para,
                        "inlines": [{"t": "text", "s": para, "marks": []}],
                        "path": {
                            "page": pidx,
                            "chapter_index": None,
                            "chapter_title": None,
                        },
                    }
                )

    is_scanned = page_count > 0 and pages_with_text == 0
    needs_ocr = is_scanned
    if is_scanned:
        warnings.insert(
            0,
            "documento sem camada de texto: parece digitalizacao; requer OCR "
            "(conteudo NAO foi extraido)",
        )

    meta = {
        "format": "pdf",
        "title": None,
        "page_count": page_count,
        "pages_with_text": pages_with_text,
        "is_scanned": is_scanned,
        "needs_ocr": needs_ocr,
        "warnings": warnings,
    }
    return {
        "schema_version": "1.0",
        "source": {"format": "pdf"},
        "metadata": meta,
        "outline": [],
        "blocks": blocks,
    }
