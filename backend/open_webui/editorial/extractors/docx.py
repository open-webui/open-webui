"""Extrator de .docx -> Arvore de Blocos Nidum (Fatia 2).

Sem nenhum import de open_webui de proposito: assim e testavel isoladamente.
Abre o pacote com python-docx (lib aprovada, MIT) e le os elementos via lxml.
As notas de rodape vem de word/footnotes.xml (lido direto do zip) e ficam
LIGADAS a ancora do corpo: cada w:footnoteReference id=N vira um inline
{"t":"footnote_ref","id":"fn-N"} e existe um bloco {"type":"footnote","id":"fn-N"}.

Escopo desta fatia: titulos (hierarquia), paragrafos, marcacao inline
(negrito/italico/sublinhado), itens de lista, tabelas (basico) e notas de rodape.
Numeracao/estilos herdados e refinamento de listas ficam para fatia posterior.
"""

import base64
import io
import re
import zipfile

from lxml import etree

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
_A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
_WP = "{http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing}"
_R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
_PKGREL = "{http://schemas.openxmlformats.org/package/2006/relationships}"
_MIME = {
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "gif": "image/gif",
    "svg": "image/svg+xml",
    "webp": "image/webp",
    "bmp": "image/bmp",
    "tif": "image/tiff",
    "tiff": "image/tiff",
}


def _t(tag: str) -> str:
    return W + tag


def _toggle_on(el) -> bool:
    # Propriedade booleana do OOXML: presente = ligada, salvo val 0/false/off.
    if el is None:
        return False
    val = el.get(_t("val"))
    return val not in ("0", "false", "off")


def _run_inlines(r) -> list:
    inlines = []
    fref = r.find(_t("footnoteReference"))
    if fref is not None:
        fid = fref.get(_t("id"))
        inlines.append({"t": "footnote_ref", "id": "fn-" + str(fid)})
    marks = []
    rpr = r.find(_t("rPr"))
    if rpr is not None:
        if _toggle_on(rpr.find(_t("b"))):
            marks.append("bold")
        if _toggle_on(rpr.find(_t("i"))):
            marks.append("italic")
        if rpr.find(_t("u")) is not None:
            marks.append("underline")
    txt = "".join(t.text or "" for t in r.findall(_t("t")))
    if txt:
        inlines.append({"t": "text", "s": txt, "marks": marks})
    return inlines


def _heading_level(style_val, outline):
    if style_val:
        s = style_val.strip()
        m = re.match(r"(?i)^(?:heading|t[ií]tulo)\s*(\d+)$", s)
        if m:
            return int(m.group(1))
        if re.match(r"(?i)^(?:heading|t[ií]tulo)$", s):
            return 1
    if outline is not None and outline >= 0:
        return outline + 1
    return None


def _para_block(p) -> dict:
    style_val = None
    outline = None
    is_list = False
    ilvl = 0
    ppr = p.find(_t("pPr"))
    if ppr is not None:
        ps = ppr.find(_t("pStyle"))
        if ps is not None:
            style_val = ps.get(_t("val"))
        ol = ppr.find(_t("outlineLvl"))
        if ol is not None:
            try:
                outline = int(ol.get(_t("val")))
            except (TypeError, ValueError):
                outline = None
        npr = ppr.find(_t("numPr"))
        if npr is not None:
            is_list = True
            il = npr.find(_t("ilvl"))
            if il is not None:
                try:
                    ilvl = int(il.get(_t("val")))
                except (TypeError, ValueError):
                    ilvl = 0

    inlines = []
    for r in p.findall(_t("r")):
        inlines.extend(_run_inlines(r))
    text = "".join(i["s"] for i in inlines if i.get("t") == "text")

    level = _heading_level(style_val, outline)
    if level:
        return {"type": "heading", "level": level, "text": text, "inlines": inlines}
    if is_list:
        return {"type": "list_item", "level": ilvl + 1, "text": text, "inlines": inlines}
    return {"type": "paragraph", "text": text, "inlines": inlines}


def _table_block(tbl) -> dict:
    rows = []
    for tr in tbl.findall(_t("tr")):
        cells = []
        for tc in tr.findall(_t("tc")):
            cell_text = " ".join(
                "".join(t.text or "" for t in p.iter(_t("t")))
                for p in tc.findall(_t("p"))
            ).strip()
            cells.append({"text": cell_text})
        rows.append(cells)
    return {"type": "table", "table": {"rows": rows}}


def _extract_footnotes(data: bytes) -> dict:
    notes = {}
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        if "word/footnotes.xml" not in zf.namelist():
            return notes
        root = etree.fromstring(zf.read("word/footnotes.xml"))
    for fn in root.findall(_t("footnote")):
        fid = fn.get(_t("id"))
        ftype = fn.get(_t("type"))
        if ftype in ("separator", "continuationSeparator"):
            continue
        if fid in ("-1", "0", None):
            continue
        text = "".join(t.text or "" for t in fn.iter(_t("t")))
        notes[str(fid)] = {"id": "fn-" + str(fid), "text": text}
    return notes


def _load_media(data: bytes) -> dict:
    """Mapa rId -> {mime, b64} das imagens em word/media, via document.xml.rels."""
    media = {}
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        names = set(zf.namelist())
        if "word/_rels/document.xml.rels" not in names:
            return media
        root = etree.fromstring(zf.read("word/_rels/document.xml.rels"))
        for rel in root.findall(_PKGREL + "Relationship"):
            if not (rel.get("Type") or "").endswith("/image"):
                continue
            rid = rel.get("Id")
            target = (rel.get("Target") or "").lstrip("/")
            path = target if target.startswith("word/") else "word/" + target
            if path in names:
                raw = zf.read(path)
                ext = path.rsplit(".", 1)[-1].lower()
                media[rid] = {
                    "mime": _MIME.get(ext, "application/octet-stream"),
                    "b64": base64.b64encode(raw).decode("ascii"),
                }
    return media


def _images_in_paragraph(p, media) -> list:
    out = []
    for drawing in p.iter(_t("drawing")):
        docpr = next(drawing.iter(_WP + "docPr"), None)
        alt = docpr.get("descr") if docpr is not None else None
        name = docpr.get("name") if docpr is not None else None
        blip = next(drawing.iter(_A + "blip"), None)
        rid = blip.get(_R + "embed") if blip is not None else None
        image = {"alt": (alt or None), "name": name}
        m = media.get(rid) if rid else None
        if m:
            image.update(m)
        out.append(
            {
                "type": "image",
                "text": alt or name or "imagem",
                "inlines": [],
                "image": image,
            }
        )
    return out


def extract_docx(data: bytes) -> dict:
    """Recebe os bytes de um .docx e devolve a Arvore de Blocos Nidum.
    Lanca ValueError com mensagem clara quando o arquivo nao e um docx valido."""
    if not data:
        raise ValueError("arquivo docx vazio")
    try:
        from docx import Document

        doc = Document(io.BytesIO(data))
    except Exception as e:  # python-docx levanta tipos variados em arquivo invalido
        raise ValueError(f"nao foi possivel abrir o .docx: {e}")

    body = doc.element.body
    if body is None:
        raise ValueError("docx invalido: corpo (<w:body>) ausente")

    media = _load_media(data)
    blocks = []
    order = 0
    chapter_index = 0
    chapter_title = None

    for el in body:
        tag = el.tag
        if tag == _t("p"):
            produced = [_para_block(el)] + _images_in_paragraph(el, media)
        elif tag == _t("tbl"):
            produced = [_table_block(el)]
        else:
            continue
        for blk in produced:
            if blk["type"] == "heading" and blk.get("level") == 1:
                chapter_index += 1
                chapter_title = blk["text"]
            order += 1
            blk["id"] = "b-%06d" % order
            blk["order"] = order
            blk["path"] = {
                "chapter_index": chapter_index,
                "chapter_title": chapter_title,
            }
            blocks.append(blk)

    notes = _extract_footnotes(data)
    for fid, n in notes.items():
        order += 1
        blocks.append(
            {
                "id": n["id"],
                "type": "footnote",
                "order": order,
                "text": n["text"],
                "inlines": [{"t": "text", "s": n["text"], "marks": []}],
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
        "source": {"format": "docx"},
        "metadata": {"title": title, "warnings": []},
        "outline": outline,
        "blocks": blocks,
    }
