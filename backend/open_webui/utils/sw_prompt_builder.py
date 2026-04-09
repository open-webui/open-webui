"""
StoryWeaver — Prompt Builder
==============================

Description fonctionnelle:
    Construit le contexte narratif (SYSTEM PROMPT) à injecter dans chaque
    conversation LLM quand un roman est sélectionné. Transforme les données
    structurées de la Knowledge Base en texte Markdown lisible par le modèle.

Règles métier:
    - Si aucun roman n'est sélectionné, retourne une chaîne vide (pas d'injection).
    - Chaque section est optionnelle : si vide, elle est omise du prompt.
    - Le prompt est tronqué si le budget de tokens estimé est dépassé.
      (1 token ≈ 4 caractères — approximation conservative pour Mistral/Llama)
    - L'ordre des sections dans le prompt est fixe :
        1. Identité du roman (titre, description, statut)
        2. Univers / Worldbuilding
        3. Personnages
        4. Lieux
        5. Objets
        6. Chronologie
    - Les items KB sont des dicts libres : le Prompt Builder tente de formater
      les champs courants (name, description, role, traits…) mais reste robuste
      face à des structures inattendues.

Architecture tech:
    - Module Python pur — aucune dépendance FastAPI ou SQLAlchemy.
    - Importable directement dans les routers ou comme dépendance FastAPI.
    - Entrées typées : NovelModel + KnowledgeBaseModel (optionnel).
    - Performance : < 500ms garanti (traitement local, pas d'I/O).

Usage:
    ```python
    from open_webui.utils.sw_prompt_builder import build_system_prompt
    from open_webui.utils.sw_dependencies import get_current_novel

    # Dans un handler de chat :
    novel = await get_current_novel(user=user, db=db)
    kb    = KnowledgeBases.get_kb_by_novel_id(novel.id, db=db) if novel else None
    system_ctx = build_system_prompt(novel=novel, kb=kb)
    ```
"""

from __future__ import annotations

import json
from typing import Any, Optional

from open_webui.models.sw_novels import KnowledgeBaseModel, NovelModel

# ─── Constantes ───────────────────────────────────────────────────────────────

# Budget caractères par défaut (~6 000 tokens × 4 chars/token)
DEFAULT_MAX_CHARS: int = 24_000

# En-tête du bloc StoryWeaver dans le system prompt
_SW_HEADER = "## Contexte Narratif StoryWeaver\n\n"
_SW_FOOTER = "\n\n---\n*[Contexte injecté automatiquement par StoryWeaver]*\n"

# Champs courants à afficher pour chaque type d'item (ordre d'affichage)
_CHARACTER_FIELDS = ["name", "role", "age", "gender", "traits", "description", "backstory", "goals", "notes"]
_LOCATION_FIELDS  = ["name", "type", "region", "description", "atmosphere", "notes"]
_OBJECT_FIELDS    = ["name", "type", "description", "powers", "owner", "notes"]
_TIMELINE_FIELDS  = ["date", "event", "participants", "consequences", "notes"]
_UNIVERSE_FIELDS  = ["title", "name", "type", "description", "notes"]


# ─── Formateurs de sections ────────────────────────────────────────────────────


def _format_item(item: dict[str, Any], priority_fields: list[str]) -> str:
    """
    Formate un item dict en Markdown lisible.

    - Les champs `priority_fields` sont affichés en premier dans l'ordre défini.
    - Les champs inconnus restants sont affichés ensuite en ordre alphabétique.
    - Le champ `id` est toujours omis (métadonnée interne).
    """
    lines: list[str] = []
    seen: set[str] = {"id"}

    # Champs prioritaires
    for field in priority_fields:
        val = item.get(field)
        if val is not None and str(val).strip():
            if isinstance(val, list):
                val_str = ", ".join(str(v) for v in val)
            else:
                val_str = str(val).strip()
            # Le premier champ devient le titre de l'item
            if not lines:
                lines.append(f"**{val_str}**")
            else:
                lines.append(f"  - *{field.replace('_', ' ').capitalize()}* : {val_str}")
            seen.add(field)

    # Champs restants (non prioritaires, non vides)
    for field in sorted(set(item.keys()) - seen):
        val = item.get(field)
        if val is not None and str(val).strip():
            if isinstance(val, list):
                val_str = ", ".join(str(v) for v in val)
            else:
                val_str = str(val).strip()
            lines.append(f"  - *{field.replace('_', ' ').capitalize()}* : {val_str}")

    return "\n".join(lines) if lines else ""


def format_novel(novel: NovelModel) -> str:
    """Formate le bloc d'identité du roman."""
    lines = [f"### Roman : {novel.title}"]
    if novel.description:
        lines.append(f"{novel.description}")
    lines.append(f"*Statut : {novel.status}*")
    return "\n".join(lines)


def format_universe(universe_docs: list[dict]) -> str:
    """Formate les documents de worldbuilding."""
    if not universe_docs:
        return ""
    items = [_format_item(doc, _UNIVERSE_FIELDS) for doc in universe_docs]
    items = [i for i in items if i]
    if not items:
        return ""
    return "### Univers & Worldbuilding\n\n" + "\n\n".join(f"- {i}" for i in items)


def format_characters(characters: list[dict]) -> str:
    """Formate les fiches personnages."""
    if not characters:
        return ""
    items = [_format_item(c, _CHARACTER_FIELDS) for c in characters]
    items = [i for i in items if i]
    if not items:
        return ""
    return "### Personnages\n\n" + "\n\n".join(items)


def format_locations(locations: list[dict]) -> str:
    """Formate les fiches lieux."""
    if not locations:
        return ""
    items = [_format_item(loc, _LOCATION_FIELDS) for loc in locations]
    items = [i for i in items if i]
    if not items:
        return ""
    return "### Lieux\n\n" + "\n\n".join(f"- {i}" for i in items)


def format_objects(objects: list[dict]) -> str:
    """Formate les fiches objets."""
    if not objects:
        return ""
    items = [_format_item(obj, _OBJECT_FIELDS) for obj in objects]
    items = [i for i in items if i]
    if not items:
        return ""
    return "### Objets\n\n" + "\n\n".join(f"- {i}" for i in items)


def format_timeline(timeline: list[dict]) -> str:
    """Formate la chronologie."""
    if not timeline:
        return ""
    items = [_format_item(evt, _TIMELINE_FIELDS) for evt in timeline]
    items = [i for i in items if i]
    if not items:
        return ""
    return "### Chronologie\n\n" + "\n\n".join(f"- {i}" for i in items)


# ─── Assemblage principal ──────────────────────────────────────────────────────


def build_full_prompt(
    novel: NovelModel,
    kb: Optional[KnowledgeBaseModel] = None,
    max_chars: int = DEFAULT_MAX_CHARS,
) -> str:
    """
    Assemble le contexte narratif complet en Markdown.

    Ordre des sections :
        1. Identité du roman
        2. Univers
        3. Personnages
        4. Lieux
        5. Objets
        6. Chronologie

    Si le total dépasse `max_chars`, les sections sont tronquées dans l'ordre
    inverse (chronologie → objets → lieux → personnages → univers → identité)
    préservant ainsi les informations les plus importantes en priorité.

    Args:
        novel   : Le roman courant (obligatoire).
        kb      : La Knowledge Base du roman (optionnelle).
        max_chars: Budget maximal en caractères.

    Returns:
        str: Le contexte Markdown formaté, ou "" si novel est None.
    """
    # ── Sections individuelles
    sections: list[str] = [format_novel(novel)]

    if kb:
        universe_text = format_universe(kb.universe_docs or [])
        characters_text = format_characters(kb.characters or [])
        locations_text = format_locations(kb.locations or [])
        objects_text = format_objects(kb.objects or [])
        timeline_text = format_timeline(kb.timeline or [])

        # Ajout dans l'ordre prioritaire (les moins importantes en dernier)
        for section in [universe_text, characters_text, locations_text, objects_text, timeline_text]:
            if section:
                sections.append(section)

    # ── Assemblage
    body = "\n\n".join(sections)

    # ── Troncation gracieuse si nécessaire
    budget = max_chars - len(_SW_HEADER) - len(_SW_FOOTER)
    if len(body) > budget:
        body = body[:budget]
        # Ne pas couper en plein milieu d'un mot
        last_newline = body.rfind("\n")
        if last_newline > budget * 0.8:  # Couper à une ligne propre
            body = body[:last_newline]
        body += "\n\n*[...contexte tronqué pour respecter le budget de tokens]*"

    return body


def build_system_prompt(
    novel: Optional[NovelModel],
    kb: Optional[KnowledgeBaseModel] = None,
    max_chars: int = DEFAULT_MAX_CHARS,
) -> str:
    """
    Point d'entrée principal — construit le bloc system prompt StoryWeaver
    prêt à être injecté dans la conversation LLM.

    Si `novel` est None (aucun roman sélectionné), retourne une chaîne vide.
    Le bloc vide n'est pas injecté, le chat fonctionne normalement.

    Args:
        novel   : Le roman courant (None = pas d'injection).
        kb      : La Knowledge Base associée.
        max_chars: Budget caractères pour le contexte.

    Returns:
        str: Le bloc system prompt complet, ou "" si novel est None.
    """
    if novel is None:
        return ""

    body = build_full_prompt(novel=novel, kb=kb, max_chars=max_chars)
    return _SW_HEADER + body + _SW_FOOTER
