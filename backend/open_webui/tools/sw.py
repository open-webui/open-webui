"""
StoryWeaver — Creative Tools
=============================

Outils d'aide à l'écriture intégrés nativement à OpenWebUI.
Permet au LLM d'accéder à la Knowledge Base (KB) et de réaliser des tâches spécialisées.
"""

import json
import logging
import time
from typing import Optional, List, Any
from fastapi import Request

from open_webui.models.sw_novels import KnowledgeBases, Chapters, Novels
from open_webui.utils.sw_prompt_builder import build_full_prompt

log = logging.getLogger(__name__)

async def _get_active_context(__request__: Request, __user__: dict) -> dict:
    """Récupère l'ID du roman actif et sa KB pour le contexte des outils."""
    user_id = __user__.get('id')
    if not user_id:
        return {"error": "User ID missing"}

    from open_webui.internal.db import get_session
    with get_session() as db:
        # On récupère le user pour avoir son current_novel_id
        from open_webui.models.users import Users
        user = Users.get_user_by_id(user_id)
        if not user or not user.current_novel_id:
            return {"error": "Aucun roman StoryWeaver n'est actuellement sélectionné."}

        novel = Novels.get_novel_by_id(user.current_novel_id, db=db)
        if not novel:
            return {"error": "Le roman sélectionné est introuvable."}

        kb = KnowledgeBases.get_kb_by_novel_id(novel.id, db=db)
        return {
            "novel": novel,
            "kb": kb,
            "db": db
        }


async def sw_brainstorm(
    topic: str,
    __request__: Request = None,
    __user__: dict = None,
) -> str:
    """
    Génère des idées créatives (scènes, rebondissements, évolution de personnage) 
    en se basant sur la Knowledge Base du roman actuel.

    :param topic: Le sujet spécifique sur lequel brainstormer.
    :return: Un bloc de contexte structuré pour aider le LLM à générer des idées cohérentes.
    """
    ctx = await _get_active_context(__request__, __user__)
    if "error" in ctx:
        return json.dumps(ctx, ensure_ascii=False)

    novel = ctx["novel"]
    kb = ctx["kb"]

    # On prépare un prompt riche pour le LLM appelant
    prompt_context = build_full_prompt(novel, kb)
    
    response = {
        "status": "success",
        "action": "brainstorm",
        "novel_title": novel.title,
        "topic": topic,
        "context_kb": prompt_context,
        "instruction": f"En te basant sur le contexte ci-dessus, propose 3 à 5 idées originales concernant : {topic}. Sois créatif et respecte la cohérence de l'univers."
    }
    
    return json.dumps(response, ensure_ascii=False)


async def sw_coherence(
    text_to_check: str,
    __request__: Request = None,
    __user__: dict = None,
) -> str:
    """
    Vérifie si un texte (extrait de chapitre ou idée) est cohérent avec la Knowledge Base.
    Détecte les contradictions sur les personnages, les lieux ou la timeline.

    :param text_to_check: Le texte ou l'extrait à vérifier.
    :return: Analyse des points de vigilance ou confirmation de cohérence.
    """
    ctx = await _get_active_context(__request__, __user__)
    if "error" in ctx:
        return json.dumps(ctx, ensure_ascii=False)

    kb = ctx["kb"]
    prompt_context = build_full_prompt(ctx["novel"], kb)

    response = {
        "status": "success",
        "action": "coherence_check",
        "text_provided": text_to_check,
        "reference_kb": prompt_context,
        "instruction": "Analyse le texte fourni par rapport à la Knowledge Base (Univers, Personnages, Lieux). Liste toute contradiction flagrante ou erreur de continuité."
    }
    
    return json.dumps(response, ensure_ascii=False)


async def sw_dialogue(
    characters: str,
    scene_context: str,
    __request__: Request = None,
    __user__: dict = None,
) -> str:
    """
    Génère un dialogue entre plusieurs personnages en respectant leur personnalité et leur voix 
    définies dans la Knowledge Base.

    :param characters: Liste des personnages impliqués (ex: 'Thomas, Elara').
    :param scene_context: Ce qui se passe dans la scène ou l'objectif du dialogue.
    :return: Contexte de caractérisation pour générer le dialogue.
    """
    ctx = await _get_active_context(__request__, __user__)
    if "error" in ctx:
        return json.dumps(ctx, ensure_ascii=False)

    kb = ctx["kb"]
    
    # On filtre la KB pour ne donner que les persos concernés si possible, 
    # mais build_full_prompt est plus simple pour la V1.
    prompt_context = build_full_prompt(ctx["novel"], kb)

    response = {
        "status": "success",
        "action": "dialogue_generation",
        "characters": characters,
        "scene_context": scene_context,
        "caracterisation": prompt_context,
        "instruction": f"Rédige une scène de dialogue entre {characters}. Utilise les traits de personnalité et le background fournis dans le contexte pour rendre leurs voix authentiques. Contexte de la scène : {scene_context}."
    }
    
    return json.dumps(response, ensure_ascii=False)


async def sw_outline(
    scope: str = "chapter",
    key_events: str = "",
    __request__: Request = None,
    __user__: dict = None,
) -> str:
    """
    Génère ou affine une structure narrative (plan de roman, arc ou chapitre).
    S'appuie sur la timeline et les enjeux globaux du roman.

    :param scope: Portée du plan ('novel', 'arc', 'chapter').
    :param key_events: Événements clés à inclure impérativement.
    :return: Structure narrative suggérée.
    """
    ctx = await _get_active_context(__request__, __user__)
    if "error" in ctx:
        return json.dumps(ctx, ensure_ascii=False)

    novel = ctx["novel"]
    kb = ctx["kb"]
    prompt_context = build_full_prompt(novel, kb)

    response = {
        "status": "success",
        "action": "outline_generation",
        "scope": scope,
        "key_events": key_events,
        "context": prompt_context,
        "instruction": f"Propose un plan structuré pour un {scope} incluant les éléments suivants : {key_events}. Assure-toi que cela s'insère bien dans la chronologie globale du roman."
    }
    
    return json.dumps(response, ensure_ascii=False)
