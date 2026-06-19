"""Teste do export .pdf (Fatia F2.3).

WeasyPrint tem libs nativas (cairo/pango); o teste so roda onde elas existem
(CI). Localmente, sem WeasyPrint, o modulo e pulado.
"""

import io

import pytest

pytest.importorskip("weasyprint")  # roda no CI (com libs nativas); pula local

from pypdf import PdfReader  # noqa: E402

from open_webui.editorial.export.pdf_export import build_pdf  # noqa: E402
from open_webui.editorial.extractors.docx import extract_docx  # noqa: E402
from open_webui.test.editorial.test_docx_extractor import (  # noqa: E402
    build_docx_with_footnote,
)


def test_pdf_is_valid_and_has_content():
    data = build_pdf(extract_docx(build_docx_with_footnote()))
    assert data[:5] == b"%PDF-", "deveria ser um PDF valido"
    reader = PdfReader(io.BytesIO(data))
    assert len(reader.pages) >= 1
    # A extracao de texto de PDF do WeasyPrint via pypdf pode variar conforme a
    # fonte embutida; quando ha texto extraido, ele deve conter o capitulo.
    text = "".join((p.extract_text() or "") for p in reader.pages)
    if text.strip():
        assert "Capitulo" in text, "o conteudo do capitulo deveria aparecer no PDF"
