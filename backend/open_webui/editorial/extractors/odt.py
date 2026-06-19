"""Extrator de .odt -> Arvore de Blocos Nidum (Fatia 3).

ODT e um ZIP com content.xml (OpenDocument). Lido com zipfile + lxml, sem
dependencia de terceiros (evita a duvida de licenca do odfpy). Notas de rodape
no ODT sao INLINE (<text:note> dentro do paragrafo, com <text:note-body>), entao
a ligacao ancora<->nota e natural: cada note vira footnote_ref + bloco footnote.

Sem imports de open_webui.
"""

import io
import logging
import zipfile

from lxml import etree

log = logging.getLogger(__name__)

_TEXT = "{urn:oasis:names:tc:opendocument:xmlns:text:1.0}"
_OFFICE = "{urn:oasis:names:tc:opendocument:xmlns:office:1.0}"


def _tx(tag):
    return _TEXT + tag


def _para_text(el):
    """Texto do paragrafo EXCLUINDO o conteudo das notas (text:note)."""
    parts = []

    def rec(node):
        if node.text:
            parts.append(node.text)
        for ch in node:
            if ch.tag == _tx("note"):
                if ch.tail:
                    parts.append(ch.tail)
                continue
            rec(ch)
            if ch.tail:
                parts.append(ch.tail)

    rec(el)
    return "".join(parts).strip()


def _notes_in(el):
    """Lista (id, texto) das notas de rodape dentro do elemento."""
    out = []
    for i, note in enumerate(el.iter(_tx("note")), start=1):
        if note.get(_tx("note-class")) not in (None, "footnote"):
            continue
        nid = note.get(_tx("id")) or f"auto{i}"
        body = note.find(_tx("note-body"))
        text = "".join(body.itertext()).strip() if body is not None else ""
        out.append(("fn-" + nid, text))
    return out


def extract_odt(data: bytes) -> dict:
    if not data:
        raise ValueError("arquivo odt vazio")
    try:
        zf = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile:
        raise ValueError("arquivo nao e um .odt valido (zip corrompido)")

    with zf:
        if "content.xml" not in zf.namelist():
            raise ValueError("odt invalido: content.xml ausente")
        root = etree.fromstring(zf.read("content.xml"))

    office_text = root.find(".//" + _OFFICE + "body/" + _OFFICE + "text")
    if office_text is None:
        raise ValueError("odt invalido: <office:text> ausente")

    blocks = []
    notes_collected = {}
    order = 0
    chapter_index = 0
    chapter_title = None

    def emit_para(el, kind, level=None):
        nonlocal order, chapter_index, chapter_title
        text = _para_text(el)
        inlines = []
        for nid, ntext in _notes_in(el):
            inlines.append({"t": "footnote_ref", "id": nid})
            notes_collected[nid] = ntext
        if text:
            inlines.append({"t": "text", "s": text, "marks": []})
        if not inlines:
            return
        if kind == "heading":
            if level == 1:
                chapter_index += 1
                chapter_title = text
            blk = {"type": "heading", "level": level or 1}
        elif kind == "list_item":
            blk = {"type": "list_item", "level": level or 1}
        else:
            blk = {"type": "paragraph"}
        order += 1
        blk.update(
            {
                "id": "b-%06d" % order,
                "order": order,
                "text": text,
                "inlines": inlines,
                "path": {"chapter_index": chapter_index, "chapter_title": chapter_title},
            }
        )
        blocks.append(blk)

    def walk(parent, list_level=0):
        for el in parent:
            if el.tag == _tx("h"):
                try:
                    lvl = int(el.get(_tx("outline-level")) or 1)
                except (TypeError, ValueError):
                    lvl = 1
                emit_para(el, "heading", lvl)
            elif el.tag == _tx("p"):
                if list_level > 0:
                    emit_para(el, "list_item", list_level)
                else:
                    emit_para(el, "paragraph")
            elif el.tag == _tx("list"):
                for li in el.findall(_tx("list-item")):
                    walk(li, list_level + 1)

    walk(office_text)

    for nid, text in notes_collected.items():
        order += 1
        blocks.append(
            {
                "id": nid,
                "type": "footnote",
                "order": order,
                "text": text,
                "inlines": [{"t": "text", "s": text, "marks": []}],
                "path": {"chapter_index": chapter_index, "chapter_title": chapter_title},
            }
        )

    outline = [
        {"block_id": b["id"], "level": b["level"], "title": b["text"]}
        for b in blocks
        if b["type"] == "heading"
    ]
    title = outline[0]["title"] if outline else None
    return {
        "schema_version": "1.0",
        "source": {"format": "odt"},
        "metadata": {"title": title, "warnings": []},
        "outline": outline,
        "blocks": blocks,
    }
