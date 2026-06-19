"""Aceite da Fatia 1/4: .docx de ~80k palavras sem perder capitulos nem notas.

Gera um docx grande (20 capitulos x 40 paragrafos x ~100 palavras = ~80k) com
1 nota por capitulo, extrai e verifica: todos os capitulos, todas as notas
ligadas a sua ancora, contagem de palavras preservada e chunking sem perda.
"""

import io
import zipfile

from open_webui.editorial.chunking import chunk_tree
from open_webui.editorial.extractors.docx import extract_docx
from open_webui.test.editorial.test_docx_extractor import (
    _CT,
    _DOC_RELS,
    _RELS,
    _STYLES,
)

_W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def _build_large_docx(chapters=20, paras=40, words=100, notes_per_chapter=1):
    body = []
    fns = [
        '<w:footnote w:type="separator" w:id="-1"><w:p><w:r><w:separator/></w:r></w:p></w:footnote>',
        '<w:footnote w:type="continuationSeparator" w:id="0"><w:p><w:r><w:continuationSeparator/></w:r></w:p></w:footnote>',
    ]
    fid = 0
    filler = ("palavra " * words).strip()
    for c in range(1, chapters + 1):
        body.append(
            f'<w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr>'
            f"<w:r><w:t>Capitulo {c}</w:t></w:r></w:p>"
        )
        for p in range(paras):
            run = f'<w:r><w:t xml:space="preserve">{filler}</w:t></w:r>'
            if p < notes_per_chapter:
                fid += 1
                run += f'<w:r><w:footnoteReference w:id="{fid}"/></w:r>'
                fns.append(
                    f'<w:footnote w:id="{fid}"><w:p><w:r><w:t>Nota {fid}</w:t></w:r></w:p></w:footnote>'
                )
            body.append(f"<w:p>{run}</w:p>")

    document = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<w:document xmlns:w="{_W}"><w:body>{"".join(body)}</w:body></w:document>'
    )
    footnotes = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<w:footnotes xmlns:w="{_W}">{"".join(fns)}</w:footnotes>'
    )
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", _CT)
        z.writestr("_rels/.rels", _RELS)
        z.writestr("word/document.xml", document)
        z.writestr("word/_rels/document.xml.rels", _DOC_RELS)
        z.writestr("word/styles.xml", _STYLES)
        z.writestr("word/footnotes.xml", footnotes)
    return buf.getvalue()


def test_large_docx_preserves_chapters_notes_and_words():
    tree = extract_docx(_build_large_docx())
    blocks = tree["blocks"]

    headings = [b for b in blocks if b["type"] == "heading"]
    assert len(headings) == 20
    assert [h["text"] for h in headings] == [f"Capitulo {i}" for i in range(1, 21)]

    notes = {b["id"] for b in blocks if b["type"] == "footnote"}
    refs = {
        i["id"]
        for b in blocks
        for i in b.get("inlines", [])
        if i.get("t") == "footnote_ref"
    }
    assert len(notes) == 20
    assert refs == notes, "toda ancora deve casar com uma nota (e vice-versa)"

    words = sum(
        len(b["text"].split()) for b in blocks if b["type"] in ("heading", "paragraph")
    )
    assert words >= 70000, f"esperava ~80k palavras, veio {words}"


def test_large_docx_chunking_loses_nothing():
    tree = extract_docx(_build_large_docx())
    chunks = chunk_tree(tree)
    collected = [bid for c in chunks for bid in c["block_ids"]]
    assert collected == [b["id"] for b in tree["blocks"]]
