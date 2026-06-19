"""Manual de estilo Nidum (template parametrizavel de export).

Um dicionario simples descreve fontes, tamanhos, cores, espacamento, pagina,
capa, sumario e secao de notas. O default carrega a identidade da Nidum; o autor
pode sobrescrever campos via merge. Sem imports de open_webui.
"""

import copy

NIDUM_DEFAULT_STYLE = {
    "fonts": {"body": "Calibri", "heading": "Calibri"},
    "sizes": {"body_pt": 11, "h1_pt": 20, "h2_pt": 16, "h3_pt": 13, "h4_pt": 12},
    "colors": {"heading": "2E3A29"},  # verde Nidum
    "spacing": {"line": 1.15, "space_after_pt": 6},
    "page": {"size": "A4", "margin_mm": 25},
    "cover": {"show": True, "subtitle": ""},
    "toc": {"show": True, "title": "Sumario"},
    "notes": {"title": "Notas"},
}


def _deep_merge(base: dict, over: dict) -> dict:
    out = copy.deepcopy(base)
    for k, v in (over or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def resolve_style(overrides: dict = None) -> dict:
    """Template final = default Nidum + overrides do autor."""
    return _deep_merge(NIDUM_DEFAULT_STYLE, overrides or {})
