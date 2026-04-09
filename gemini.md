# gemini.md — Carte d'Identité : StoryWeaver

## Pitch

> **StoryWeaver = OpenWebUI + Domain-Specific Romance Writing Features**
> Une plateforme IA locale dédiée à la rédaction de roman — mémoire persistante,
> knowledge base structurée, outils spécialisés, zéro friction créative.

---

## Identité du Projet

| Champ | Valeur |
|-------|--------|
| **Nom** | StoryWeaver |
| **Type** | Extension/Fork d'OpenWebUI |
| **Utilisateur** | Thomas (auteur solo) |
| **Statut** | En développement — Phase 1 |
| **Démarré** | Avril 2026 |
| **Envergure** | Produit V1 complet (~8 semaines) |

---

## Stack Technique

| Couche | Technologie |
|--------|-------------|
| **Frontend** | SvelteKit (hérité OpenWebUI) |
| **Backend** | Python FastAPI (hérité OpenWebUI) |
| **ORM** | SQLAlchemy + Alembic |
| **Base de données** | SQLite (dev) → PostgreSQL (prod VPS) |
| **LLM** | Ollama + Mistral (local, déjà en place) |
| **State Management** | Svelte stores |
| **Tests** | pytest (backend) + Vitest (frontend) |

---

## Crew IA

| Agent | Rôle | Statut |
|-------|------|--------|
| `lead-agent` | Orchestrateur, backlog, assignation | ✅ Actif |
| `architecte` | Décisions techniques, ADR, validation | ✅ Actif |
| `backend-dev` | FastAPI, DAOs, tools Python | ✅ Actif |
| `frontend-dev` | Composants Svelte, stores | ✅ Actif |
| `ui-ux-designer` | Wireframes, specs UX | ✅ Actif |
| `legacy-specialist` | Analyse code OpenWebUI existant | ✅ Actif |
| `qa-auditeur` | Tests, review, qualité | ✅ Actif |
| `documentaliste` | Documentation, ADR, guides | ✅ Actif |

---

## Roadmap Macro

### Phase 1 — Core Infrastructure (Semaines 1-2)
- [ ] Fork OpenWebUI + Setup environnement
- [ ] Analyse structure OpenWebUI existante
- [ ] Modèles DB + Migrations Alembic
- [ ] DAOs (CRUD Novel, KB, Manuscript, Version)
- [ ] Routers FastAPI (novels, kb, manuscript)
- [ ] Session management (novel courant par user)
- [ ] Prompt Builder (context injection)
- [ ] Intégration dans `chat.py`

### Phase 2 — Knowledge Base (Semaines 3-4)
- [ ] KB Editor UI (5 onglets : Universe, Characters, Locations, Objects, Timeline)
- [ ] Versioning system côté UI
- [ ] Full-text search KB
- [ ] Auto-linking entre entités

### Phase 3 — Tools & Modules (Semaines 5-6)
- [ ] Tool: brainstorm_generator
- [ ] Tool: coherence_checker
- [ ] Tool: dialogue_generator
- [ ] Tool: outline_generator
- [ ] Intégration commandes slash dans le chat
- [ ] Manuscript Editor (éditeur Markdown avec boutons rapides)

### Phase 4 — Polish & Testing (Semaines 7-8)
- [ ] UI/UX refinement (4 layouts : Full, Writer Focus, Research Mode, Outline)
- [ ] Tests complets (unit + intégration)
- [ ] Documentation finalisée
- [ ] Export (Markdown, PDF)
- [ ] Déploiement VPS

---

## Critères de Succès

### Fonctionnels
- Chat avec contexte novel injecté automatiquement ✓
- KB éditable et persistante ✓
- Versioning des changements ✓
- Switch entre romans sans friction ✓
- 5 tools spécialisés opérationnels ✓

### Performance
- Context injection < 500ms
- Réponse Ollama < 3s (dépend VPS)
- DB queries < 100ms
- UI responsive (pas de blocage UI)

### Qualité
- Couverture tests ≥ 70% (DAOs + tools)
- Zéro régression sur le chat OpenWebUI de base
- Migrations Alembic testées up ET down

---

## Documents de Référence

| Document | Description |
|----------|-------------|
| `PRD_NOVEL_AI_SYSTEM.md` | PRD complet — vision, features, architecture |
| `PRD_STORYWEAVER_OPENWEBUI_EXTENDED.md` | Stratégie d'extension OpenWebUI + contrats |
| `STORYWEAVER_IMPLEMENTATION_ROADMAP_DETAILED.md` | Tâches atomiques avec critères d'acceptation |
| `STORYWEAVER_ARCHITECTURE_DIAGRAMS.md` | Diagrammes d'architecture |
| `STORYWEAVER_TEST_CHECKLIST.md` | Checklist de tests fonctionnels |
| `design.md` | ADR et décisions d'architecture |
| `DEVELOPMENT.md` | Guide de setup local *(à créer — Task 1.0.2)* |
| `ARCHITECTURE_EXISTING.md` | Mapping OpenWebUI *(à créer — Task 1.0.3)* |

---

## Philosophie du Projet

> "Ne pas réinventer la roue, construire dessus."
> "L'IA propose, Thomas dispose."
> "Local-first : tout fonctionne sur VPS, zéro dépendance cloud."
> "Context is King : l'IA est aussi bonne que le contexte injecté."

---

## Prochaine Étape Immédiate

**Lancer le `init-workflow`** :
1. Fork `open-webui/open-webui` sur GitHub
2. Cloner localement + créer branche `feature/storyweaver-core`
3. Setup environnement (Python + Node)
4. Analyser structure OpenWebUI (legacy-specialist)
5. Commencer Task 1.1.1 — Créer les modèles Pydantic

> Référence : `STORYWEAVER_IMPLEMENTATION_ROADMAP_DETAILED.md` — Milestone 1.0
