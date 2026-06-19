"""Export da Arvore de Blocos -> .epub (EPUB3) (Fatia F2.2).

Monta o pacote com zipfile (mimetype primeiro e STORED), container.xml, OPF
(EPUB3 com dcterms:modified), nav.xhtml (sumario), uma capa e um XHTML por
capitulo, com CSS vindo do manual de estilo Nidum. SEM ebooklib (AGPL). Notas
de rodape: <a epub:type="noteref"> no corpo <-> <aside epub:type="footnote">.

Sem imports de open_webui alem do style (puro).
"""

import io
import time
import uuid
import zipfile
from xml.sax.saxutils import escape

from open_webui.editorial.export.style import resolve_style


def _esc(s):
    return escape(s or "")


def _inline_html(block, note_numbers):
    """HTML inline de um bloco, com marcacao e ancoras de nota."""
    parts = []
    inlines = block.get("inlines") or [
        {"t": "text", "s": block.get("text", ""), "marks": []}
    ]
    for inl in inlines:
        if inl.get("t") == "text":
            s = _esc(inl.get("s", ""))
            marks = inl.get("marks") or []
            if "bold" in marks:
                s = f"<strong>{s}</strong>"
            if "italic" in marks:
                s = f"<em>{s}</em>"
            if "underline" in marks:
                s = f"<u>{s}</u>"
            parts.append(s)
        elif inl.get("t") == "footnote_ref":
            fid = inl.get("id")
            n = note_numbers.get(fid)
            if n:
                parts.append(
                    f'<sup><a epub:type="noteref" href="#{_esc(fid)}">{n}</a></sup>'
                )
    return "".join(parts)


def _split_chapters(blocks):
    """Agrupa blocos em capitulos (novo capitulo a cada heading nivel 1)."""
    notes = {b["id"]: b.get("text", "") for b in blocks if b.get("type") == "footnote"}
    chapters = []
    current = None

    def new_chapter(title):
        ch = {"title": title, "blocks": []}
        chapters.append(ch)
        return ch

    for b in blocks:
        if b.get("type") == "footnote":
            continue
        if b.get("type") == "heading" and int(b.get("level", 1)) == 1:
            current = new_chapter(b.get("text", "Capitulo"))
            current["blocks"].append(b)
        else:
            if current is None:
                current = new_chapter("Inicio")
            current["blocks"].append(b)
    return chapters, notes


def _chapter_xhtml(chapter, notes, lang="pt-BR"):
    # numera as notas referenciadas neste capitulo, na ordem de aparicao
    note_numbers = {}
    for b in chapter["blocks"]:
        for inl in b.get("inlines") or []:
            if inl.get("t") == "footnote_ref" and inl.get("id") not in note_numbers:
                note_numbers[inl["id"]] = len(note_numbers) + 1

    body = []
    in_list = False
    for b in chapter["blocks"]:
        t = b.get("type")
        if t == "list_item":
            if not in_list:
                body.append("<ul>")
                in_list = True
            body.append(f"<li>{_inline_html(b, note_numbers)}</li>")
            continue
        if in_list:
            body.append("</ul>")
            in_list = False
        if t == "heading":
            lvl = min(int(b.get("level", 1)), 6)
            body.append(f"<h{lvl}>{_inline_html(b, note_numbers)}</h{lvl}>")
        elif t == "table":
            rows = (b.get("table") or {}).get("rows") or []
            cells = "".join(
                "<tr>" + "".join(f"<td>{_esc(c.get('text',''))}</td>" for c in r) + "</tr>"
                for r in rows
            )
            body.append(f"<table>{cells}</table>")
        else:
            body.append(f"<p>{_inline_html(b, note_numbers)}</p>")
    if in_list:
        body.append("</ul>")

    # notas referenciadas neste capitulo
    for fid, n in note_numbers.items():
        body.append(
            f'<aside epub:type="footnote" id="{_esc(fid)}"><p>{n}. {_esc(notes.get(fid, ""))}</p></aside>'
        )

    return (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<!DOCTYPE html>\n'
        f'<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" lang="{lang}" xml:lang="{lang}">'
        f"<head><meta charset=\"utf-8\"/><title>{_esc(chapter['title'])}</title>"
        '<link rel="stylesheet" type="text/css" href="style.css"/></head>'
        f"<body>{''.join(body)}</body></html>"
    )


def _cover_xhtml(title, lang="pt-BR"):
    return (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<!DOCTYPE html>\n'
        f'<html xmlns="http://www.w3.org/1999/xhtml" lang="{lang}" xml:lang="{lang}">'
        f"<head><meta charset=\"utf-8\"/><title>{_esc(title)}</title>"
        '<link rel="stylesheet" type="text/css" href="style.css"/></head>'
        f'<body><div class="cover"><h1>{_esc(title)}</h1></div></body></html>'
    )


def _nav_xhtml(chapters, lang="pt-BR"):
    items = "".join(
        f'<li><a href="chap{i}.xhtml">{_esc(ch["title"])}</a></li>'
        for i, ch in enumerate(chapters, start=1)
    )
    return (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<!DOCTYPE html>\n'
        f'<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" lang="{lang}" xml:lang="{lang}">'
        '<head><meta charset="utf-8"/><title>Sumario</title></head>'
        '<body><nav epub:type="toc" id="toc"><h1>Sumario</h1><ol>'
        f"{items}</ol></nav></body></html>"
    )


def _css(style):
    s = style
    return (
        f"body{{font-family:'{s['fonts']['body']}',serif;font-size:{s['sizes']['body_pt']}pt;"
        f"line-height:{s['spacing']['line']};margin:1em;}}"
        f"h1,h2,h3,h4{{font-family:'{s['fonts']['heading']}',sans-serif;color:#{s['colors']['heading']};}}"
        f"h1{{font-size:{s['sizes']['h1_pt']}pt;}}h2{{font-size:{s['sizes']['h2_pt']}pt;}}"
        ".cover{text-align:center;margin-top:30%;}"
    )


def _opf(title, chapters, ident, modified, lang="pt-BR"):
    manifest = [
        '<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>',
        '<item id="css" href="style.css" media-type="text/css"/>',
        '<item id="cover" href="cover.xhtml" media-type="application/xhtml+xml"/>',
    ]
    spine = ['<itemref idref="cover"/>']
    for i in range(1, len(chapters) + 1):
        manifest.append(
            f'<item id="chap{i}" href="chap{i}.xhtml" media-type="application/xhtml+xml"/>'
        )
        spine.append(f'<itemref idref="chap{i}"/>')
    return (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="bookid">'
        '<metadata xmlns:dc="http://purl.org/dc/elements/1.1/">'
        f'<dc:identifier id="bookid">{ident}</dc:identifier>'
        f"<dc:title>{_esc(title)}</dc:title>"
        f"<dc:language>{lang}</dc:language>"
        f'<meta property="dcterms:modified">{modified}</meta>'
        "</metadata>"
        f"<manifest>{''.join(manifest)}</manifest>"
        f"<spine>{''.join(spine)}</spine>"
        "</package>"
    )


def build_epub(tree: dict, overrides: dict = None) -> bytes:
    style = resolve_style(overrides)
    title = (tree.get("metadata") or {}).get("title") or "Documento"
    chapters, notes = _split_chapters(tree.get("blocks", []))
    if not chapters:
        chapters = [{"title": title, "blocks": []}]

    ident = "urn:uuid:" + str(uuid.uuid4())
    modified = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        # mimetype PRIMEIRO e SEM compressao (exigencia do EPUB)
        z.writestr(
            zipfile.ZipInfo("mimetype"), "application/epub+zip", compress_type=zipfile.ZIP_STORED
        )
        z.writestr(
            "META-INF/container.xml",
            '<?xml version="1.0" encoding="utf-8"?>\n'
            '<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">'
            '<rootfiles><rootfile full-path="OEBPS/content.opf" '
            'media-type="application/oebps-package+xml"/></rootfiles></container>',
        )
        z.writestr("OEBPS/content.opf", _opf(title, chapters, ident, modified))
        z.writestr("OEBPS/nav.xhtml", _nav_xhtml(chapters))
        z.writestr("OEBPS/style.css", _css(style))
        z.writestr("OEBPS/cover.xhtml", _cover_xhtml(title))
        for i, ch in enumerate(chapters, start=1):
            z.writestr(f"OEBPS/chap{i}.xhtml", _chapter_xhtml(ch, notes))
    return buf.getvalue()
