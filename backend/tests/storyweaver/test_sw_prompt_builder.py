"""
Tests — Prompt Builder (Task 1.3.1)
=====================================

Tests unitaires du module sw_prompt_builder.
Aucune dépendance DB ou FastAPI — tests purs sur les fonctions de formatage.

Couverture:
    - format_novel()        : titre, description, statut
    - format_universe()     : items, liste vide
    - format_characters()   : champs standards, champs inconnus, item vide
    - format_locations()    : idem
    - format_objects()      : idem
    - format_timeline()     : idem
    - build_full_prompt()   : assemblage complet, KB None, troncation budget
    - build_system_prompt() : novel None → "", novel → bloc complet avec header/footer
    - Performance           : < 500ms sur une KB chargée (critère d'acceptation)
"""

import time
import pytest
from open_webui.utils.sw_prompt_builder import (
    build_full_prompt,
    build_system_prompt,
    format_characters,
    format_locations,
    format_novel,
    format_objects,
    format_timeline,
    format_universe,
    _SW_HEADER,
    _SW_FOOTER,
    DEFAULT_MAX_CHARS,
)
from open_webui.models.sw_novels import KnowledgeBaseModel, NovelModel


# ─── Fixtures ──────────────────────────────────────────────────────────────────


def _novel(title: str = "Le Don d'Elosth", description: str = "Une épopée de magie.", status: str = "in-progress") -> NovelModel:
    now = int(time.time())
    return NovelModel(
        id="novel-001",
        user_id="user-001",
        title=title,
        description=description,
        status=status,
        created_at=now,
        updated_at=now,
    )


def _kb(
    characters=None,
    locations=None,
    universe_docs=None,
    objects=None,
    timeline=None,
) -> KnowledgeBaseModel:
    return KnowledgeBaseModel(
        id="kb-001",
        novel_id="novel-001",
        universe_docs=universe_docs or [],
        characters=characters or [],
        locations=locations or [],
        objects=objects or [],
        timeline=timeline or [],
        updated_at=int(time.time()),
    )


# ─── format_novel ──────────────────────────────────────────────────────────────


class TestFormatNovel:
    def test_includes_title(self):
        result = format_novel(_novel(title="Test Roman"))
        assert "Test Roman" in result

    def test_includes_description(self):
        result = format_novel(_novel(description="Un grand récit."))
        assert "Un grand récit." in result

    def test_includes_status(self):
        result = format_novel(_novel(status="completed"))
        assert "completed" in result

    def test_no_description_still_works(self):
        now = int(time.time())
        novel = NovelModel(
            id="n1", user_id="u1", title="Sans Desc",
            status="draft", created_at=now, updated_at=now,
        )
        result = format_novel(novel)
        assert "Sans Desc" in result
        assert result  # Non vide


# ─── format_universe ───────────────────────────────────────────────────────────


class TestFormatUniverse:
    def test_empty_list_returns_empty_string(self):
        assert format_universe([]) == ""

    def test_single_doc(self):
        docs = [{"name": "Magie Horgonienne", "description": "Magie du chaos."}]
        result = format_universe(docs)
        assert "Magie Horgonienne" in result
        assert "Worldbuilding" in result or "Univers" in result

    def test_multiple_docs(self):
        docs = [
            {"name": "Magie de Lumière", "description": "Magie sacrée."},
            {"name": "Magie des Ombres", "description": "Magie interdite."},
        ]
        result = format_universe(docs)
        assert "Magie de Lumière" in result
        assert "Magie des Ombres" in result

    def test_doc_with_only_id_is_omitted(self):
        docs = [{"id": "only-id"}]
        result = format_universe(docs)
        assert result == ""


# ─── format_characters ─────────────────────────────────────────────────────────


class TestFormatCharacters:
    def test_empty_list_returns_empty(self):
        assert format_characters([]) == ""

    def test_standard_character(self):
        chars = [{"id": "c1", "name": "Aela", "role": "héroïne", "age": "24"}]
        result = format_characters(chars)
        assert "Aela" in result
        assert "héroïne" in result
        assert "24" in result
        assert "Personnages" in result

    def test_id_is_not_in_output(self):
        chars = [{"id": "c1", "name": "Aela"}]
        result = format_characters(chars)
        assert "c1" not in result

    def test_unknown_fields_are_included(self):
        chars = [{"id": "c1", "name": "Aela", "custom_field": "valeur custom"}]
        result = format_characters(chars)
        assert "custom_field" in result.lower() or "valeur custom" in result

    def test_traits_as_list(self):
        chars = [{"name": "Bran", "traits": ["courageux", "impulsif"]}]
        result = format_characters(chars)
        assert "courageux" in result
        assert "impulsif" in result

    def test_multiple_characters(self):
        chars = [
            {"id": "c1", "name": "Aela"},
            {"id": "c2", "name": "Bran"},
        ]
        result = format_characters(chars)
        assert "Aela" in result
        assert "Bran" in result

    def test_character_with_only_id_is_omitted(self):
        chars = [{"id": "ghost"}]
        result = format_characters(chars)
        assert result == ""


# ─── format_locations ──────────────────────────────────────────────────────────


class TestFormatLocations:
    def test_empty_list_returns_empty(self):
        assert format_locations([]) == ""

    def test_standard_location(self):
        locs = [{"name": "Forêt d'Elen", "type": "nature", "description": "Forêt enchantée."}]
        result = format_locations(locs)
        assert "Forêt d'Elen" in result
        assert "Lieux" in result

    def test_location_id_not_in_output(self):
        locs = [{"id": "loc-1", "name": "Tour Noire"}]
        result = format_locations(locs)
        assert "loc-1" not in result


# ─── format_objects ────────────────────────────────────────────────────────────


class TestFormatObjects:
    def test_empty_list_returns_empty(self):
        assert format_objects([]) == ""

    def test_standard_object(self):
        objs = [{"name": "Épée d'Elosth", "type": "arme", "description": "Lame légendaire."}]
        result = format_objects(objs)
        assert "Épée d'Elosth" in result
        assert "Objets" in result

    def test_powers_field(self):
        objs = [{"name": "Orbe Noir", "powers": "Absorbe la lumière."}]
        result = format_objects(objs)
        assert "Absorbe la lumière" in result


# ─── format_timeline ───────────────────────────────────────────────────────────


class TestFormatTimeline:
    def test_empty_list_returns_empty(self):
        assert format_timeline([]) == ""

    def test_standard_event(self):
        events = [{"date": "An 432", "event": "Bataille de Rodienne", "consequences": "Chute du roi."}]
        result = format_timeline(events)
        assert "An 432" in result
        assert "Bataille de Rodienne" in result
        assert "Chronologie" in result

    def test_participants_as_list(self):
        events = [{"event": "Alliance", "participants": ["Aela", "Bran", "Keira"]}]
        result = format_timeline(events)
        assert "Aela" in result


# ─── build_full_prompt ─────────────────────────────────────────────────────────


class TestBuildFullPrompt:
    def test_with_novel_only(self):
        result = build_full_prompt(novel=_novel())
        assert "Le Don d'Elosth" in result
        assert result

    def test_with_novel_and_kb(self):
        kb = _kb(
            characters=[{"name": "Aela", "role": "héroïne"}],
            locations=[{"name": "Rodienne", "description": "Capitale."}],
        )
        result = build_full_prompt(novel=_novel(), kb=kb)
        assert "Aela" in result
        assert "Rodienne" in result

    def test_with_empty_kb(self):
        kb = _kb()  # Toutes les sections vides
        result = build_full_prompt(novel=_novel(), kb=kb)
        assert "Le Don d'Elosth" in result
        # Aucune section vide ne doit ajouter de bruit
        assert "Personnages" not in result
        assert "Lieux" not in result

    def test_truncation_respects_max_chars(self):
        # KB avec énormément d'items
        big_chars = [{"name": f"Personnage {i}", "description": "x" * 500} for i in range(50)]
        kb = _kb(characters=big_chars)
        result = build_full_prompt(novel=_novel(), kb=kb, max_chars=2000)
        assert len(result) <= 2200  # Légère tolérance pour le message de troncation

    def test_truncation_adds_notice(self):
        big_chars = [{"name": f"Personnage {i}", "description": "x" * 500} for i in range(50)]
        kb = _kb(characters=big_chars)
        result = build_full_prompt(novel=_novel(), kb=kb, max_chars=1000)
        assert "tronqué" in result

    def test_no_truncation_when_within_budget(self):
        kb = _kb(characters=[{"name": "Aela"}])
        result = build_full_prompt(novel=_novel(), kb=kb, max_chars=DEFAULT_MAX_CHARS)
        assert "tronqué" not in result

    def test_kb_none_works(self):
        result = build_full_prompt(novel=_novel(), kb=None)
        assert "Le Don d'Elosth" in result


# ─── build_system_prompt ───────────────────────────────────────────────────────


class TestBuildSystemPrompt:
    def test_returns_empty_string_when_no_novel(self):
        result = build_system_prompt(novel=None)
        assert result == ""

    def test_contains_header(self):
        result = build_system_prompt(novel=_novel())
        assert _SW_HEADER in result

    def test_contains_footer(self):
        result = build_system_prompt(novel=_novel())
        assert _SW_FOOTER in result

    def test_contains_novel_title(self):
        result = build_system_prompt(novel=_novel(title="L'Ombre de Nimil"))
        assert "L'Ombre de Nimil" in result

    def test_full_kb_injection(self):
        kb = _kb(
            characters=[{"name": "Aela", "role": "héroïne"}],
            universe_docs=[{"name": "Le Don", "description": "Force primordiale."}],
            timeline=[{"date": "An 1", "event": "Réveil du Don"}],
        )
        result = build_system_prompt(novel=_novel(), kb=kb)
        assert "Aela" in result
        assert "Force primordiale" in result
        assert "Réveil du Don" in result

    def test_empty_sections_not_in_output(self):
        kb = _kb(characters=[], locations=[], objects=[])
        result = build_system_prompt(novel=_novel(), kb=kb)
        assert "Personnages" not in result
        assert "Lieux" not in result
        assert "Objets" not in result


# ─── Performance ───────────────────────────────────────────────────────────────


class TestPerformance:
    def test_build_prompt_under_500ms(self):
        """Critère d'acceptation : < 500ms sur une KB réaliste chargée."""
        big_kb = _kb(
            characters=[{"name": f"Personnage {i}", "role": "héros", "description": "Description longue " * 10} for i in range(20)],
            locations=[{"name": f"Lieu {i}", "description": "Description " * 15} for i in range(10)],
            universe_docs=[{"name": f"Lore {i}", "description": "Lore text " * 20} for i in range(10)],
            objects=[{"name": f"Objet {i}", "description": "Desc " * 10} for i in range(10)],
            timeline=[{"date": f"An {i}", "event": f"Événement {i}", "consequences": "Suite " * 5} for i in range(15)],
        )

        start = time.perf_counter()
        for _ in range(10):  # 10 itérations pour une mesure stable
            build_system_prompt(novel=_novel(), kb=big_kb)
        elapsed_ms = (time.perf_counter() - start) * 100  # moyenne sur 10 runs

        assert elapsed_ms < 500, f"Prompt Builder trop lent : {elapsed_ms:.1f}ms (max 500ms)"
