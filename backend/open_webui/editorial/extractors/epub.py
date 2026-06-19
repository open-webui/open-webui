"""Extrator de .epub -> Arvore de Blocos Nidum (Fatia 3).

EPUB e um ZIP de XHTML + um OPF. Lido com zipfile + BeautifulSoup (bs4, MIT),
SEM ebooklib (AGPL). Le a ordem de leitura pelo spine do OPF e percorre cada
documento. Notas de rodape (EPUB3): <a epub:type="noteref" href="#id"> no corpo
e <aside epub:type="footnote" id="id"> -> ligadas como footnote_ref <-> footnote.

Sem imports de open_webui.
"""

import io
import logging
import posixpath
import zipfile

from lxml import etree

log = logging.getLogger(__name__)

_CONTAINER_NS = {"c": "urn:oasis:names:tc:opendocument:xmlns:container"}
_OPF_NS = {"opf": "http://www.idpf.org/2007/opf"}
_HEADINGS = {"h1": 1, "h2": 2, "h3": 3, "h4": 4, "h5": 5, "h6": 6}


def _opf_path(zf: zipfile.ZipFile) -> str:
    root = etree.fromstring(zf.read("META-INF/container.xml"))
    el = root.find(".//c:rootfile", _CONTAINER_NS)
    if el is None or not el.get("full-path"):
        raise ValueError("epub invalido: container.xml sem rootfile")
    return el.get("full-path")


def _spine_hrefs(zf: zipfile.ZipFile, opf_path: str) -> list:
    root = etree.fromstring(zf.read(opf_path))
    manifest = {}
    for item in root.findall(".//opf:manifest/opf:item", _OPF_NS):
        manifest[item.get("id")] = item.get("href")
    base = posixpath.dirname(opf_path)
    hrefs = []
    for itemref in root.findall(".//opf:spine/opf:itemref", _OPF_NS):
        href = manifest.get(itemref.get("idref"))
        if href:
            hrefs.append(posixpath.normpath(posixpath.join(base, href)))
    return hrefs


def _noteref_id(a) -> str:
    # <a epub:type="noteref" href="#fn1"> ou role="doc-noteref"
    et = (a.get("epub:type") or "") + " " + (a.get("role") or "")
    href = a.get("href") or ""
    if "noteref" in et and href.startswith("#"):
        return "fn-" + href[1:]
    return ""


def extract_epub(data: bytes) -> dict:
    if not data:
        raise ValueError("arquivo epub vazio")
    try:
        from bs4 import BeautifulSoup
    except Exception as e:  # pragma: no cover
        raise ValueError(f"dependencia ausente para epub: {e}")

    try:
        zf = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile:
        raise ValueError("arquivo nao e um .epub valido (zip corrompido)")

    blocks = []
    notes = {}
    order = 0
    chapter_index = 0
    chapter_title = None

    with zf:
        names = set(zf.namelist())
        if "META-INF/container.xml" not in names:
            raise ValueError("epub invalido: META-INF/container.xml ausente")
        opf_path = _opf_path(zf)
        hrefs = _spine_hrefs(zf, opf_path)
        if not hrefs:
            raise ValueError("epub invalido: spine vazio (nada para ler)")

        for href in hrefs:
            if href not in names:
                continue
            soup = BeautifulSoup(zf.read(href), "lxml")
            body = soup.body or soup

            # Notas (aside/div epub:type=footnote) deste documento.
            for aside in body.find_all(["aside", "div"]):
                et = aside.get("epub:type") or aside.get("role") or ""
                if "footnote" in et and aside.get("id"):
                    fid = "fn-" + aside.get("id")
                    notes[fid] = aside.get_text(" ", strip=True)

            for el in body.find_all(list(_HEADINGS.keys()) + ["p", "li"]):
                # ignora paragrafos que sao a propria nota (ja capturados)
                parent_types = " ".join(
                    (p.get("epub:type") or "") for p in el.parents if p.name in ("aside", "div")
                )
                if "footnote" in parent_types:
                    continue
                text = el.get_text(" ", strip=True)
                inlines = []
                for a in el.find_all("a"):
                    nid = _noteref_id(a)
                    if nid:
                        inlines.append({"t": "footnote_ref", "id": nid})
                if text:
                    inlines.append({"t": "text", "s": text, "marks": []})
                if not inlines:
                    continue
                name = el.name
                if name in _HEADINGS:
                    level = _HEADINGS[name]
                    if level == 1:
                        chapter_index += 1
                        chapter_title = text
                    blk = {"type": "heading", "level": level}
                elif name == "li":
                    blk = {"type": "list_item", "level": 1}
                else:
                    blk = {"type": "paragraph"}
                order += 1
                blk.update(
                    {
                        "id": "b-%06d" % order,
                        "order": order,
                        "text": text,
                        "inlines": inlines,
                        "path": {
                            "chapter_index": chapter_index,
                            "chapter_title": chapter_title,
                        },
                    }
                )
                blocks.append(blk)

    for fid, text in notes.items():
        order += 1
        blocks.append(
            {
                "id": fid,
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
        "source": {"format": "epub"},
        "metadata": {"title": title, "warnings": []},
        "outline": outline,
        "blocks": blocks,
    }
