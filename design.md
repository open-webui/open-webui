# design.md — Architecture & Décisions Techniques StoryWeaver

## Vision Architecturale

StoryWeaver = OpenWebUI + Domain-Specific Layers.
Stratégie : **extension harmonieuse**, pas réinvention. On construit sur les patterns
d'OpenWebUI et on ajoute nos couches en suivant ses conventions.

```
┌─────────────────────────────────────────┐
│        STORYWEAVER CUSTOM LAYER         │
├─────────────────────────────────────────┤
│ ├─ KB Manager (univers, personnages)   │
│ ├─ Versioning System (historique)      │
│ ├─ Project Manager (multi-projet)      │
│ ├─ Context Injector (prompts enrichis) │
│ ├─ Custom Tools (brainstorm, outline)  │
│ └─ Manuscript Editor (Markdown sync)   │
├─────────────────────────────────────────┤
│  OpenWebUI Core (Chat, API, Models)    │
├─────────────────────────────────────────┤
│  Ollama + Mistral (local VPS)          │
└─────────────────────────────────────────┘
```

---

## ADR-001 : Stratégie d'Injection du Contexte Novel dans les Prompts

- **Contexte** : L'IA doit connaître l'univers du roman, les personnages et les scènes
  récentes pour fournir une assistance cohérente. Comment injecter ce contexte ?
- **Options évaluées** :
  - A) SYSTEM PROMPT dynamique (reconstruit à chaque requête)
  - B) In-context examples (exemples dans le corps du message)
  - C) RAG (vector search sur la KB)
- **Décision** : **Option A — SYSTEM PROMPT dynamique**
- **Justification** : Plus flexible, facile à ajuster sans infrastructure supplémentaire (pas de vector DB), suffit pour le volume de données d'un roman solo. Compatible avec le context window de Mistral.
- **Conséquences** : Limiter la KB injectée via `top-K` sélection (5 personnages max, 500 dernières lignes manuscrit) pour éviter l'overflow.

---

## ADR-002 : Stratégie de Versioning des Entités

- **Contexte** : L'auteur doit pouvoir retrouver l'historique des changements (personnages, univers, scènes).
- **Options évaluées** :
  - A) Full snapshots (copie complète de l'état à chaque modification)
  - B) Diffs/patches (stocke uniquement le delta)
- **Décision** : **Option A — Full snapshots (MVP)**
- **Justification** : Beaucoup plus simple à implémenter et à inspecter. La taille des données d'un roman reste modeste (< 1GB). Facilite la restauration.
- **Conséquences** : La table `versions` peut grossir vite → ajouter un système de purge des versions > 100 par entité (configurable via `VERSION_HISTORY_RETENTION`).

---

## ADR-003 : Sélection du Novel Courant (Session vs Per-Message)

- **Contexte** : Comment associer un roman à une session de chat ?
- **Options évaluées** :
  - A) Session-level : sélectionner le novel une fois, tous les messages utilisent ce contexte
  - B) Per-message : choisir le novel à chaque message
- **Décision** : **Option A — Session-level novel selection**
- **Justification** : Plus naturel pour l'auteur (flux continu d'écriture), moins de friction. Un changement de roman = nouvelle session.
- **Conséquences** : Stocker `current_novel_id` sur le modèle `User` (colonne nullable additionnelle).

---

## ADR-004 : Base de Données — SQLite vs PostgreSQL

- **Contexte** : OpenWebUI utilise SQLite par défaut. StoryWeaver ajoute des tables.
- **Options évaluées** :
  - A) SQLite (défaut OpenWebUI) pour dev + prod
  - B) SQLite dev, PostgreSQL prod
  - C) PostgreSQL dès le départ
- **Décision** : **Option B — SQLite dev, PostgreSQL prod**
- **Justification** : SQLite suffit pour le développement local et les tests. PostgreSQL pour la production VPS garantit la performance avec des données croissantes.
- **Conséquences** : Les migrations Alembic doivent être compatibles avec les deux. Éviter les types SQLite-only.

---

## ADR-005 : Intégration des Custom Tools dans OpenWebUI

- **Contexte** : OpenWebUI a un système de Custom Tools (fonctions Python callable depuis le chat).
- **Options évaluées** :
  - A) Utiliser le système de tools natif OpenWebUI
  - B) Créer des routes API séparées et des boutons frontend dédiés
- **Décision** : **Option A — Système de tools natif + Commands Slash** pour le MVP, option B en complément pour les boutons rapides de l'éditeur.
- **Justification** : Réutilise l'infrastructure existante d'OpenWebUI. Les commandes slash (`/brainstorm`, `/outline`) sont naturelles dans l'interface chat.

---

## Structure des Fichiers StoryWeaver

```
open-webui/                              ← Fork OpenWebUI
│
├── backend/
│   ├── database/
│   │   ├── models_storyweaver.py        ← Modèles SQLAlchemy StoryWeaver
│   │   └── daos.py                      ← DAOs (NovelDAO, KBDAO, VersionDAO...)
│   ├── routes/
│   │   ├── novels.py                    ← CRUD novels + session management
│   │   ├── knowledge_base.py            ← CRUD KB (chars, lieux, univers)
│   │   └── manuscript.py               ← CRUD manuscrit
│   └── utils/
│       └── prompt_builder.py            ← Construction du SYSTEM PROMPT enrichi
│
├── tools/                               ← Custom Tools Python OpenWebUI
│   ├── novel_context_injector.py
│   ├── brainstorm.py
│   ├── coherence_checker.py
│   ├── dialogue_generator.py
│   └── outline_generator.py
│
├── frontend/src/lib/
│   ├── components/
│   │   ├── NovelManager.svelte          ← Sidebar: liste et gestion des romans
│   │   ├── KnowledgeBaseEditor.svelte   ← Modal: éditeur KB (5 onglets)
│   │   ├── ManuscriptEditor.svelte      ← Panel: éditeur Markdown
│   │   └── ToolsPanel.svelte            ← Toolbar: accès aux tools slash
│   ├── stores/
│   │   └── novel.ts                     ← Store: novel courant + KB réactive
│   └── api/
│       └── storyweaver.ts              ← Client API: toutes les calls StoryWeaver
│
└── alembic/versions/
    └── *_storyweaver_initial.py         ← Migration initiale StoryWeaver
```

---

## Schéma de Données StoryWeaver

```
novels
├── id (UUID PK)
├── user_id (FK → user.id)
├── title (String)
├── description (String nullable)
├── status (draft|in-progress|completed|archived)
├── created_at, updated_at

knowledge_bases
├── id (UUID PK)
├── novel_id (UUID FK → novels.id, UNIQUE)
├── universe_docs (JSON)
├── characters (JSON array)
├── locations (JSON array)
├── objects (JSON array)
├── updated_at

manuscripts
├── id (UUID PK)
├── novel_id (UUID FK → novels.id, UNIQUE)
├── content (Text Markdown)
├── chapter_structure (JSON)
├── word_count (Integer)
├── updated_at

versions
├── id (UUID PK)
├── novel_id (UUID FK)
├── entity_type (character|location|scene|universe|novel)
├── entity_id (String)
├── old_data (JSON nullable)
├── new_data (JSON)
├── change_type (created|updated|deleted)
├── version_number (Integer)
├── timestamp

context_snapshots
├── id (UUID PK)
├── chat_id (UUID FK → chat.id)
├── novel_id (UUID FK → novels.id)
├── injected_context (JSON)
├── kb_snapshot (JSON)
├── timestamp
```

---

## Variables d'Environnement StoryWeaver

Ajouter dans `.env.local` :

```bash
STORYWEAVER_ENABLED=true
KB_MAX_SIZE=10000              # Nb caractères max par section KB
VERSION_HISTORY_RETENTION=100  # Nb de versions à conserver par entité
AUTO_CONTEXT_INJECTION=true    # Injection automatique du contexte
CONTEXT_WINDOW_SIZE=4000       # Tokens alloués au contexte injecté
OLLAMA_BASE_URL=http://localhost:11434
```

---

## Points d'Intégration avec OpenWebUI (Fichiers à Modifier)

| Fichier OpenWebUI | Modification | Risque |
|-------------------|--------------|--------|
| `backend/main.py` | Inclure les nouveaux routers StoryWeaver | Faible |
| `backend/routes/chat.py` | Injecter le SYSTEM PROMPT enrichi | **Élevé** — point critique |
| `backend/database/models.py` | Ajouter `current_novel_id` à `User` | Moyen |
| `frontend/src/App.svelte` | Ajouter Novel Selector dans sidebar | Faible |
| `frontend/src/routes/chat/+page.svelte` | Ajouter toolbar Tools | Moyen |

> ⚠️ **`backend/routes/chat.py`** : Toute modification de ce fichier requiert une review
> architecturale ET un test de non-régression du chat OpenWebUI de base.

---

## Risques et Mitigations

| Risque | Probabilité | Impact | Mitigation |
|--------|-------------|--------|------------|
| Context window overflow | Élevée | Moyen | top-K sélection + warning loggé |
| Ollama latency (VPS limité) | Moyenne | Élevé | Monitoring + queue asynchrone si besoin |
| Migration Alembic casse DB OpenWebUI | Faible | Critique | Test up+down obligatoire avant merge |
| Régression chat de base | Faible | Critique | Test de non-régression dans chaque PR |
| Incohérences IA | Élevée | Faible | L'auteur reste validateur final |
