"""Testes do extrator .docx (Fatia 2). Puros: nao precisam de Redis nem DB.

Criterio VINCULANTE: a ancora da nota no corpo continua ligada ao texto da nota
(footnote_ref.id no corpo == id de um bloco footnote, com o texto certo).
"""

import io
import zipfile

import pytest

from open_webui.editorial.extractors.docx import extract_docx

_CT = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
<Override PartName="/word/footnotes.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footnotes+xml"/>
</Types>"""

_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>"""

_DOC_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/footnotes" Target="footnotes.xml"/>
</Relationships>"""

_STYLES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
<w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/></w:style>
</w:styles>"""

_DOCXML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
<w:body>
<w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr><w:r><w:t>Capitulo 1</w:t></w:r></w:p>
<w:p>
<w:r><w:t xml:space="preserve">O ninho do joao e </w:t></w:r>
<w:r><w:rPr><w:b/></w:rPr><w:t>resistente</w:t></w:r>
<w:r><w:rPr><w:rStyle w:val="FootnoteReference"/></w:rPr><w:footnoteReference w:id="2"/></w:r>
<w:r><w:t>.</w:t></w:r>
</w:p>
</w:body>
</w:document>"""

_FOOTNOTES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:footnotes xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
<w:footnote w:type="separator" w:id="-1"><w:p><w:r><w:separator/></w:r></w:p></w:footnote>
<w:footnote w:type="continuationSeparator" w:id="0"><w:p><w:r><w:continuationSeparator/></w:r></w:p></w:footnote>
<w:footnote w:id="2"><w:p><w:r><w:t>Ver Documento Fundador, p.4.</w:t></w:r></w:p></w:footnote>
</w:footnotes>"""


def build_docx_with_footnote() -> bytes:
    """Monta, em memoria, um .docx minimo valido com 1 nota de rodape."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", _CT)
        z.writestr("_rels/.rels", _RELS)
        z.writestr("word/document.xml", _DOCXML)
        z.writestr("word/_rels/document.xml.rels", _DOC_RELS)
        z.writestr("word/styles.xml", _STYLES)
        z.writestr("word/footnotes.xml", _FOOTNOTES)
    return buf.getvalue()


def test_extract_docx_basic_structure():
    tree = extract_docx(build_docx_with_footnote())
    assert tree["schema_version"] == "1.0"
    assert tree["metadata"]["title"] == "Capitulo 1"

    headings = [b for b in tree["blocks"] if b["type"] == "heading"]
    assert headings and headings[0]["level"] == 1
    assert headings[0]["text"] == "Capitulo 1"

    paras = [b for b in tree["blocks"] if b["type"] == "paragraph"]
    assert any(
        i.get("marks") == ["bold"] and i["s"] == "resistente"
        for i in paras[0]["inlines"]
    ), "marca de negrito deveria ser preservada"


def test_extract_docx_links_footnote_anchor_to_note():
    """Criterio de aceite: a ancora no corpo continua ligada ao texto da nota."""
    tree = extract_docx(build_docx_with_footnote())
    blocks = tree["blocks"]

    ref_ids = [
        i["id"]
        for b in blocks
        for i in b.get("inlines", [])
        if i.get("t") == "footnote_ref"
    ]
    assert ref_ids == ["fn-2"], f"ancora no corpo: {ref_ids}"

    notes = {b["id"]: b for b in blocks if b["type"] == "footnote"}
    assert "fn-2" in notes, f"bloco de nota ausente: {list(notes)}"
    assert notes["fn-2"]["text"] == "Ver Documento Fundador, p.4."


def test_extract_docx_clear_error_on_invalid():
    with pytest.raises(ValueError):
        extract_docx(b"isto nao e um docx")
    with pytest.raises(ValueError):
        extract_docx(b"")
