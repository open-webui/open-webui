"""F3 - ficha do projeto como contexto de conversa.

Formata a ficha viva (tone/glossario/personagens/decisoes/terminologia) num bloco
de contexto que sera injetado no inicio das conversas daquele projeto. O vinculo
conversa<->projeto sera "um modelo por projeto" (manifold) - peca de deploy; aqui
fica a logica testavel de montar o contexto a partir da versao atual da ficha.
"""


def format_sheet_as_context(data: dict) -> str:
    if not data:
        return ""
    parts = ["[FICHA DO PROJETO - use para manter consistencia editorial]"]

    if data.get("tone_of_voice"):
        parts.append("Tom de voz: " + str(data["tone_of_voice"]))

    glossary = data.get("glossary") or []
    if glossary:
        parts.append("Glossario:")
        for g in glossary:
            line = "- " + str(g.get("term", ""))
            if g.get("definition"):
                line += ": " + str(g["definition"])
            parts.append(line)

    characters = data.get("characters") or []
    if characters:
        parts.append("Personagens:")
        for c in characters:
            line = "- " + str(c.get("name", ""))
            if c.get("description"):
                line += ": " + str(c["description"])
            parts.append(line)

    decisions = data.get("style_decisions") or []
    if decisions:
        parts.append("Decisoes de estilo:")
        for s in decisions:
            parts.append(
                "- " + str(s.get("topic", "")) + ": " + str(s.get("decision", ""))
            )

    terminology = data.get("terminology") or []
    if terminology:
        parts.append("Terminologia:")
        for t in terminology:
            line = "- usar '" + str(t.get("preferred", "")) + "'"
            avoid = t.get("avoid") or []
            if avoid:
                line += " (evitar: " + ", ".join(str(a) for a in avoid) + ")"
            parts.append(line)

    if data.get("free_notes"):
        parts.append("Notas: " + str(data["free_notes"]))

    return "\n".join(parts)


async def build_project_context(project_id: str) -> str:
    """Monta o contexto a partir da versao ATUAL da ficha do projeto."""
    from open_webui.models.editorial import Sheets

    sheet = await Sheets.get_current(project_id)
    if not sheet:
        return ""
    return format_sheet_as_context(sheet.data or {})
