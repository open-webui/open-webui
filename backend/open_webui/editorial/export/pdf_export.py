"""Export da Arvore de Blocos -> .pdf paginado (Fatia F2.3).

Renderiza a obra como HTML semantico e converte com WeasyPrint (BSD), usando
CSS Paged Media: capa, sumario com numero de pagina (target-counter), numeracao
de paginas no rodape e quebra por capitulo. Notas no fim, com marcador
sobrescrito (python/WeasyPrint nao precisa de footnote nativo aqui).

WeasyPrint importado de forma preguicosa (tem libs nativas: cairo/pango).
Sem imports de open_webui alem do style (puro).
"""

from xml.sax.saxutils import escape

from open_webui.editorial.export.style import resolve_style


def _esc(s):
    return escape(s or "")


def _inline(block, counter, notes_out, fn_text):
    parts = []
    for inl in block.get("inlines") or [
        {"t": "text", "s": block.get("text", ""), "marks": []}
    ]:
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
            counter[0] += 1
            notes_out.append((counter[0], fn_text.get(inl.get("id"), "")))
            parts.append(f"<sup>{counter[0]}</sup>")
    return "".join(parts)


def _css(s):
    return f"""
@page {{ size: {s['page']['size']}; margin: {s['page']['margin_mm']}mm;
  @bottom-center {{ content: counter(page); font-size: 9pt; color: #888888; }} }}
@page :first {{ @bottom-center {{ content: none; }} }}
body {{ font-family: '{s['fonts']['body']}', serif; font-size: {s['sizes']['body_pt']}pt;
  line-height: {s['spacing']['line']}; }}
h1, h2, h3, h4 {{ font-family: '{s['fonts']['heading']}', sans-serif; color: #{s['colors']['heading']}; }}
h1 {{ font-size: {s['sizes']['h1_pt']}pt; }}
h2 {{ font-size: {s['sizes']['h2_pt']}pt; }}
h1.chapter {{ break-before: page; }}
.cover {{ text-align: center; margin-top: 35%; break-after: page; }}
.cover h1 {{ font-size: 32pt; }}
.toc {{ break-after: page; }}
.toc ul {{ list-style: none; padding: 0; }}
.toc a {{ text-decoration: none; color: inherit; }}
.toc a::after {{ content: " " target-counter(attr(href url), page); color: #888888; }}
table {{ border-collapse: collapse; }}
td {{ border: 1px solid #ccc; padding: 4px; }}
.notes {{ break-before: page; }}
"""


def _render_html(tree: dict, style: dict) -> str:
    title = _esc((tree.get("metadata") or {}).get("title") or "Documento")
    blocks = tree.get("blocks", [])
    fn_text = {b["id"]: b.get("text", "") for b in blocks if b.get("type") == "footnote"}

    body = []
    chapters = []  # (anchor, title_html)
    counter = [0]
    notes_out = []
    chap_i = 0
    in_list = False

    for b in blocks:
        t = b.get("type")
        if t == "footnote":
            continue
        if t == "list_item":
            if not in_list:
                body.append("<ul>")
                in_list = True
            body.append(f"<li>{_inline(b, counter, notes_out, fn_text)}</li>")
            continue
        if in_list:
            body.append("</ul>")
            in_list = False
        if t == "heading":
            lvl = min(int(b.get("level", 1)), 6)
            html = _inline(b, counter, notes_out, fn_text)
            if lvl == 1:
                chap_i += 1
                anchor = f"chap{chap_i}"
                chapters.append((anchor, html))
                body.append(f'<h1 id="{anchor}" class="chapter">{html}</h1>')
            else:
                body.append(f"<h{lvl}>{html}</h{lvl}>")
        elif t == "table":
            rows = (b.get("table") or {}).get("rows") or []
            cells = "".join(
                "<tr>" + "".join(f"<td>{_esc(c.get('text',''))}</td>" for c in r) + "</tr>"
                for r in rows
            )
            body.append(f"<table>{cells}</table>")
        else:
            body.append(f"<p>{_inline(b, counter, notes_out, fn_text)}</p>")
    if in_list:
        body.append("</ul>")

    notes_html = ""
    if notes_out:
        items = "".join(f"<p>{n}. {_esc(txt)}</p>" for n, txt in notes_out)
        notes_html = (
            f'<section class="notes"><h1>{_esc(style["notes"]["title"])}</h1>{items}</section>'
        )

    toc_items = "".join(
        f'<li><a href="#{a}">{t}</a></li>' for a, t in chapters
    )

    return (
        "<!DOCTYPE html>"
        '<html lang="pt-BR"><head><meta charset="utf-8"/>'
        f"<style>{_css(style)}</style></head><body>"
        f'<div class="cover"><h1>{title}</h1></div>'
        f'<section class="toc"><h1>{_esc(style["toc"]["title"])}</h1><ul>{toc_items}</ul></section>'
        f"{''.join(body)}{notes_html}"
        "</body></html>"
    )


def build_pdf(tree: dict, overrides: dict = None) -> bytes:
    from weasyprint import HTML

    style = resolve_style(overrides)
    html = _render_html(tree, style)
    return HTML(string=html).write_pdf()
