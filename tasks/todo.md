# StoryWeaver — Backlog & Suivi d'Avancement

**Lead Agent** | Mis à jour : Avril 2026  
**Phase courante** : PROJET TERMINÉ — Production Ready ✅

---

## 🚀 Phase 1 — Core Infrastructure (Semaines 1-2)

### Milestone 1.0 : Setup & Fork Initial

- [x] **Task 1.0.1** — Fork OpenWebUI et Setup Git
  - Fork privé `open-webui/open-webui` sur GitHub *(Fait : DarkPoussinOf666)*
  - Créer `.gitignore` personnalisé *(Fait)*
  - Initialiser branche `feature/storyweaver-core` *(Fait)*
  - **Durée estimée** : 2h | **Agent** : Thomas (humain) | **Critère** : `git branch` montre la feature branch

- [x] **Task 1.0.2** — Setup Environnement Dev Local
  - Backend : Python 3.10+, poetry install, `.env.local`, test `http://localhost:8000` *(Fait)*
  - Frontend : Node.js 18+, npm install, test `http://localhost:5173` *(Fait)*
  - **Durée estimée** : 3-4h | **Agents** : backend-dev + frontend-dev | **Critère** : Les deux serveurs démarrent sans erreur

- [x] **Task 1.0.3** — Analyser Structure OpenWebUI Existante
  - Mapping backend (routes, modèles, dépendances auth) *(Fait)*
  - Mapping frontend (composants, stores, chat flow) *(Fait)*
  - Produire `ARCHITECTURE_EXISTING.md` *(Fait)*
  - **Durée estimée** : 4-5h | **Agent** : legacy-specialist | **Critère** : Architecte approuve le rapport

### Milestone 1.1 : Database Extensions

- [x] **Task 1.1.1** — Créer Models Pydantic (Backend)
  - `backend/open_webui/models/sw_novels.py` avec Novel, KnowledgeBase, Manuscript, Version *(Fait)*
  - **Durée estimée** : 3-4h | **Agent** : backend-dev | **Critère** : Structure SQLAlchemy et Pydantic créées

- [x] **Task 1.1.2** — Créer Migration DB (Alembic)
  - Migration avec toutes les nouvelles tables
  - Indexes sur user_id, novel_id, entity_id (Géré par PK/UniqueConstraints)
  - Test up ET down *(Fait)*
  - **Durée estimée** : 2-3h | **Agent** : backend-dev | **Critère** : Migration up+down sans erreur, tables présentes en DB

- [x] **Task 1.1.3** — Ajouter DAOs (Data Access Objects)
  - Intégré directement dans `backend/open_webui/models/sw_novels.py` (NovelsTable, KnowledgeBasesTable, ManuscriptsTable, VersionsTable) *(Fait)*
  - **Durée estimée** : 3-4h | **Agent** : backend-dev | **Critère** : DAOs implémentés selon conventions OpenWebUI

### Milestone 1.2 : API Routes Core

- [x] **Task 1.2.1** — Créer Router Novels (CRUD)
  - `backend/open_webui/routers/sw_novels.py` avec POST /create, GET /, GET /{id}, POST /{id}/update, DELETE /{id}/delete
  - Monté sur `/api/sw/novels` dans `main.py` (tag: `storyweaver`)
  - Tests : `backend/tests/storyweaver/test_sw_novels_router.py` — **20/20 PASSED**
  - **Durée réelle** : ~1h | **Agent** : backend-dev | **Critère** : Tests passants ✅

- [x] **Task 1.2.2** — Créer Router Knowledge Base (CRUD)
  - `backend/open_webui/routers/sw_kb.py` : GET /, GET /{section}, POST /{section}/add, POST /{section}/{id}/update, DELETE /{section}/{id}/delete, PUT /{section}/replace
  - Monté sur `/api/sw/novels/{novel_id}/kb` dans `main.py`
  - Lazy init KB + ownership check via novel parent
  - Tests : `backend/tests/storyweaver/test_sw_kb_router.py` — **29/29 PASSED**
  - **Durée réelle** : ~1h | **Agent** : backend-dev | **Critère** : CRUD complet testé ✅

- [x] **Task 1.2.3** — Session Management Novel Courant
  - `current_novel_id` sur User déjà présent (colonne + Pydantic + migration Alembic)
  - Endpoints ajoutés dans `sw_novels.py` : GET /current, POST /{id}/select, POST /deselect
  - Dépendance injectable `get_current_novel()` dans `backend/open_webui/utils/sw_dependencies.py`
  - Auto-reset silencieux si le roman référencé est supprimé ou orphelin
  - Tests : `backend/tests/storyweaver/test_sw_session.py` — **17/17 PASSED**
  - Suite complète : **66/66 PASSED** (zéro régression) ✅
  - **Durée réelle** : ~45min | **Agent** : backend-dev | **Critère** : Sélection + dépendance opérationnelles ✅

### Milestone 1.3 : Context Injection System

- [x] **Task 1.3.1** — Créer Prompt Builder
  - `backend/open_webui/utils/sw_prompt_builder.py` : format_novel, format_universe, format_characters, format_locations, format_objects, format_timeline, build_full_prompt, build_system_prompt
  - Troncation gracieuse configurable (défaut 24 000 chars ≈ 6 000 tokens)
  - Tests : `backend/tests/storyweaver/test_sw_prompt_builder.py` — **38/38 PASSED**
  - Perf : **< 500ms** validé (10 runs sur KB chargée 65 items) ✅
  - Suite complète : **104/104 PASSED** ✅
  - **Durée réelle** : ~30min | **Agent** : backend-dev | **Critère** : Prompt < 500ms ✅

- [x] **Task 1.3.2** — Intégrer Context Injection dans Route Chat
  - Injection dans `process_chat_payload()` de `backend/open_webui/utils/middleware.py`
  - Point d'injection : après `apply_system_prompt_to_body`, append non-destructif via `add_or_update_system_message(..., append=True)`
  - Guard de sécurité : vérifie `user.id == novel.user_id` avant injection
  - Bloc `try/except` silencieux — l'erreur n'est jamais propagée au chat
  - Zéro régression : **104/104 tests PASSED** ✅
  - **Durée réelle** : ~30min | **Agent** : backend-dev | **Critère** : Chat avec et sans novel fonctionne ✅

---

### Milestone 2.1 : Fondations Frontend

- [x] **Task 2.1.1** — API Client TypeScript StoryWeaver
  - `src/lib/apis/sw.ts` : wrapper fetch typé (Novels CRUD + Session + KB CRUD)
  - Types TS : `Novel`, `NovelCreateForm`, `KBSection`, `KBItem`, `KnowledgeBase`, etc.
  - **Durée réelle** : ~15min | **Agent** : frontend-dev ✅

- [x] **Task 2.1.2** — Svelte Stores StoryWeaver
  - `src/lib/stores/sw.ts` : `novels`, `currentNovel`, `activeKB`, `swLoading`, `swError`
  - Derived stores : `hasCurrentNovel`, `currentNovelId`, `draftNovels`, `activeNovels`
  - Actions async : `loadNovels`, `loadCurrentNovel`, `selectNovel`, `deselectNovel`, `createNovel`, `updateNovel`, `deleteNovel`, `loadActiveKB`, `addKBItem`, `updateKBItem`, `deleteKBItem`
  - **Durée réelle** : ~20min | **Agent** : frontend-dev ✅

### Milestone 2.2 : Novel Manager UI

- [x] **Task 2.2.1** — Layout StoryWeaver
  - `src/routes/(app)/storyweaver/+layout.svelte`
  - Nav avec onglets Romans / KB, badge roman actif, chargement initial des stores
  - **Durée réelle** : ~15min | **Agent** : frontend-dev ✅

- [x] **Task 2.2.2** — Novel Manager Page
  - `src/routes/(app)/storyweaver/+page.svelte`
  - Grille de cards novels, CRUD complet (create/edit/delete), sélection de session
  - Modal création/édition, badge roman actif, état vide, spinner de chargement
  - **Durée réelle** : ~25min | **Agent** : frontend-dev ✅

### Milestone 2.3 : KB Editor UI

- [x] **Task 2.3.1** — KB Editor (5 onglets)
  - `src/routes/(app)/storyweaver/[id]/kb/+page.svelte`
  - Onglets : Univers 🌍, Personnages 👤, Lieux 🗺️, Objets ⚔️, Chronologie 📅
  - Grille cards par section, compteurs, recherche temps réel
  - Modal création/édition avec schéma de champs spécifiques par onglet
  - Gestion traits/participants en liste (split virgule)
  - **Durée réelle** : ~30min | **Agent** : frontend-dev ✅

---

## 📋 Phase 3 — Tools & Modules (Semaines 5-6)

### Milestone 3.1 : Creative Tools Backend
- [x] **Task 3.1.1** — Implémenter le module `sw_tools.py` ✅
- [x] **Task 3.1.2** — Enregistrement des Tools Natifs ✅
- [x] **Task 3.1.3** — Handler de Slash Commands (Middleware) ✅

### Milestone 3.2 : Manuscript Editor (Chapter-based)
- [x] **Task 3.2.0** — Models & DB (Chapters) ✅
- [x] **Task 3.2.1** — API Endpoints Chapters ✅
- [x] **Task 3.2.2** — Manuscript Editor Frontend ✅

---

## 📋 Phase 4 — Polish & Testing (Semaines 7-8)

### Milestone 4.1 : UI/UX Refinement
- [x] **Task 4.1.1** — Store `editorMode` & Persistance ✅
- [x] **Task 4.1.2** — Layout "Focus" ✅
- [x] **Task 4.1.3** — Layout "Research" ✅
- [x] **Task 4.1.4** — Layout "Outline" ✅

### Milestone 4.2 : Export System
- [x] **Task 4.2.1** — Export Utility `export.ts` ✅
- [x] **Task 4.2.2** — Export PDF "Format Livre" ✅
- [x] **Task 4.2.3** — Export Markdown (.md) ✅
- [x] **Task 4.2.4** — Intégration UI dans l'éditeur ✅

### Milestone 4.3 : Polish & Validation
- [x] **Task 4.3.1** — Animations de transition & Micro-interactions ✅
- [x] **Task 4.3.2** — Tooltips & Aide contextuelle ✅
- [x] **Task 4.3.3** — État de chargement (Skeletons) ✅
- [x] **Task 4.3.4** — Audit final & Correction bugs UI ✅

---

## 📋 Phase 5 — Documentation & Finalisation

### Milestone 5.1 : Documentation Technique
- [x] **Task 5.1.1** — Documentation Technique (`ARCHITECTURE_STORYWEAVER.md`) ✅
- [x] **Task 5.1.2** — Référence API (`API_REFERENCE.md`) ✅

### Milestone 5.2 : Documentation Utilisateur
- [x] **Task 5.2.1** — Guide de l'Utilisateur (`USER_GUIDE.md`) ✅

### Milestone 5.3 : Finalisation
- [x] **Task 5.3.1** — Guide de Déploiement Docker (`DEPLOYMENT.md`) ✅
- [x] **Task 5.3.2** — Mise à jour des README & Clean-up ✅

---

## ✅ Complété

*Projet StoryWeaver entièrement complété et prêt pour la production.*

---

## 🔧 Décisions Prises

| Date | Décision | Contexte | ADR |
|------|----------|----------|-----|
| Avril 2026 | SYSTEM PROMPT dynamique pour context injection | Plus flexible, pas besoin de vector DB | ADR-001 |
| Avril 2026 | Full snapshots pour versioning | Simplifié MVP | ADR-002 |
| Avril 2026 | Session-level novel selection | Flux naturel auteur | ADR-003 |
| Avril 2026 | SQLite dev + PostgreSQL prod | Standard OpenWebUI + scalabilité | ADR-004 |
| Avril 2026 | Custom Tools natifs OpenWebUI | Réutilise l'infrastructure existante | ADR-005 |

---

## 🚧 Blocages Actifs

*Aucun — En attente du fork initial (Task 1.0.1)*

---

## 📊 Métriques de la Phase

- **Phase 1** : 0/9 tâches complétées
- **Phase 2** : Non démarrée
- **Phase 3** : Non démarrée
- **Phase 4** : Non démarrée

---

## 💡 Lessons Learned

*Ce fichier sera alimenté au fil des sessions de développement*
