"""Testes dos extratores .pdf / .epub / .odt (Fatia 3). Puros, sem Redis/DB.

PDF: texto real extraido + DETECCAO de escaneado (needs_ocr, sem fabricar).
EPUB/ODT: hierarquia + ancora<->nota.
"""

import io
import zipfile

import pytest

from open_webui.editorial.extractors.epub import extract_epub
from open_webui.editorial.extractors.odt import extract_odt
from open_webui.editorial.extractors.pdf import extract_pdf


# --------------------------------------------------------------------------- PDF
def _text_pdf() -> bytes:
    from fpdf import FPDF

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("helvetica", size=16)
    pdf.cell(0, 10, "Capitulo 1")
    pdf.ln(12)
    pdf.set_font("helvetica", size=12)
    pdf.multi_cell(0, 8, "O ninho do joao e resistente.")
    return bytes(pdf.output())


def _no_text_pdf() -> bytes:
    from fpdf import FPDF

    pdf = FPDF()
    pdf.add_page()  # pagina sem nenhum texto -> simula falta de camada de texto
    return bytes(pdf.output())


def test_pdf_extracts_real_text_with_page_ref():
    tree = extract_pdf(_text_pdf())
    assert tree["metadata"]["is_scanned"] is False
    assert tree["metadata"]["needs_ocr"] is False
    assert tree["blocks"], "deveria extrair texto"
    assert any("resistente" in b["text"] for b in tree["blocks"])
    assert all(b["path"]["page"] == 1 for b in tree["blocks"])


def test_pdf_scanned_signals_ocr_and_does_not_fabricate():
    tree = extract_pdf(_no_text_pdf())
    assert tree["metadata"]["is_scanned"] is True
    assert tree["metadata"]["needs_ocr"] is True
    assert tree["blocks"] == [], "nao deve fabricar conteudo sem camada de texto"
    assert tree["metadata"]["warnings"], "deveria avisar que precisa de OCR"


def test_pdf_clear_error_on_invalid():
    with pytest.raises(ValueError):
        extract_pdf(b"isto nao e pdf")


# -------------------------------------------------------------------------- EPUB
_CONTAINER = '<?xml version="1.0"?><container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container"><rootfiles><rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/></rootfiles></container>'
_OPF = '<?xml version="1.0"?><package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="b"><metadata/><manifest><item id="c1" href="chap1.xhtml" media-type="application/xhtml+xml"/></manifest><spine><itemref idref="c1"/></spine></package>'
_XHTML = '<?xml version="1.0" encoding="utf-8"?><html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops"><body><h1>Capitulo 1</h1><p>O ninho do joao e resistente<a epub:type="noteref" href="#fn1">1</a>.</p><aside epub:type="footnote" id="fn1"><p>Ver Documento Fundador, p.4.</p></aside></body></html>'


def _build_epub() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("mimetype", "application/epub+zip")
        z.writestr("META-INF/container.xml", _CONTAINER)
        z.writestr("OEBPS/content.opf", _OPF)
        z.writestr("OEBPS/chap1.xhtml", _XHTML)
    return buf.getvalue()


def test_epub_structure_and_footnote_link():
    tree = extract_epub(_build_epub())
    blocks = tree["blocks"]
    assert any(
        b["type"] == "heading" and b["level"] == 1 and b["text"] == "Capitulo 1"
        for b in blocks
    )
    refs = [
        i["id"]
        for b in blocks
        for i in b.get("inlines", [])
        if i.get("t") == "footnote_ref"
    ]
    notes = {b["id"] for b in blocks if b["type"] == "footnote"}
    assert refs and refs[0] in notes


# --------------------------------------------------------------------------- ODT
_ODT_CONTENT = """<?xml version="1.0" encoding="UTF-8"?>
<office:document-content
 xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0"
 xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0">
<office:body><office:text>
<text:h text:outline-level="1">Capitulo 1</text:h>
<text:p>O ninho do joao e resistente<text:note text:id="ftn1" text:note-class="footnote"><text:note-citation>1</text:note-citation><text:note-body><text:p>Ver Documento Fundador, p.4.</text:p></text:note-body></text:note>.</text:p>
<text:list><text:list-item><text:p>primeiro item</text:p></text:list-item></text:list>
</office:text></office:body></office:document-content>"""


def _build_odt() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("mimetype", "application/vnd.oasis.opendocument.text")
        z.writestr("content.xml", _ODT_CONTENT)
    return buf.getvalue()


def test_odt_structure_footnote_link_and_no_note_leak():
    tree = extract_odt(_build_odt())
    blocks = tree["blocks"]
    assert any(
        b["type"] == "heading" and b["level"] == 1 and b["text"] == "Capitulo 1"
        for b in blocks
    )
    para = [b for b in blocks if b["type"] == "paragraph"][0]
    assert "Documento Fundador" not in para["text"], "texto da nota vazou no paragrafo"
    assert any(
        b["type"] == "list_item" and b["text"] == "primeiro item" for b in blocks
    )
    refs = [
        i["id"]
        for b in blocks
        for i in b.get("inlines", [])
        if i.get("t") == "footnote_ref"
    ]
    notes = {b["id"]: b for b in blocks if b["type"] == "footnote"}
    assert refs == ["fn-ftn1"]
    assert notes["fn-ftn1"]["text"] == "Ver Documento Fundador, p.4."
