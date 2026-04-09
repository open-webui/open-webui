# ARCHITECTURE_EXISTING.md — Mapping OpenWebUI

*(Ce rapport a été généré dans le cadre de la Task 1.0.3 par `@legacy-specialist` afin de cartographier la codebase existante d'OpenWebUI pour faciliter l'incrustation de la logique StoryWeaver.)*

---

## 1. Vue d'Ensemble

OpenWebUI repose sur une architecture monolithique scindée en deux grands blocs :
- **Backend** : FastAPI (Python) avec SQLAlchemy (ORM) et auto-génération de BDD via SQLite/PostgreSQL.
- **Frontend** : SvelteKit avec TailwindCSS et un système de "Stores" Svelte très centralisé.

Le workflow d'API est très standard : `Frontend (Svelte)` → `API Fetch (src/lib/apis/)` → `FastAPI Router (routers/)` → `DB Model (models/)`.

---

## 2. Structure Backend (FastAPI)

Le code source du backend ne se situe pas à la racine de `backend/`, mais dans le package **`backend/open_webui/`**.

### Composants Clés
1. **Entry Point** : `backend/open_webui/main.py`
   - C'est ici que sont enregistrés tous les routers via `.include_router()`.
   - Charge les dépendances, le socket IO et les modèles IA configurés via variables d'environnements (dont celles dans `.env.local`).

2. **Routers (Controllers FastAPI)** : `backend/open_webui/routers/`
   - Concentre toute la logique d'exposition API (`/api/v1/chats`, `/api/v1/users`, etc.).
   - Fichiers notables : `chats.py` (logique d'échange avec le LLM et sauvegarde locale), `models.py`, `users.py`, `knowledge.py` (RAG existant).

3. **Modèles DB (SQLAlchemy) et DAOs** : `backend/open_webui/models/`
   - Concentre la logique de persistance. Note importante : chaque fichier de modèle (ex: `chats.py`) inclut souvent directement les DAOs (Data Access Objects) comme des méthodes de classe ou des helpers (ex: `Chats.insert_new_chat(...)`).
   - Moteur DB géré par `backend/open_webui/internal/db.py`.

4. **Migrations** : `backend/open_webui/migrations/`
   - Utilise Alembic. Il faudra créer de nouvelles révisions Alembic pour injecter les tables StoryWeaver (Novels, Chapters, KnowledgeBase).

---

## 3. Structure Frontend (SvelteKit)

Localisé dans **`src/`**. C'est une architecture CSR (Client-Side Rendering) lourde connectée au Backend FastApi local.

### Composants Clés
1. **Views (Routes SvelteKit)** : `src/routes/`
   - `src/routes/(app)/` : Contient l'interface principale après connexion.
   - `src/routes/(app)/+page.svelte` : Sûrement la zone de Chat principale par défaut.
   - `src/routes/(app)/c/[id]/` : Représente la vue focus d'un chat spécifique. L'interface Novel/Manuscript de StoryWeaver pourra s'injecter sous la forme d'un side-panel ou d'une vue séparée.

2. **Global State (Store Svelte)** : `src/lib/stores/index.ts`
   - Fichier gigantesque contenant toute la vérité absolue de l'interface ("The only truth the house knows").
   - Contient `chats`, `user`, `models`, `config`, etc.
   - *Intégration StoryWeaver* : C'est ici qu'il faudra ajouter les Writable Stores pour `currentNovel`, `knowledgeBase`, `manuscript`.

3. **API Clients** : `src/lib/apis/`
   - Fonctions de mapping fetch vers le backend.
   - *Intégration StoryWeaver* : Créer un sous-dossier `src/lib/apis/storyweaver/` contenant les wrappers (ex. `getNovels()`, `saveManuscript()`).

---

## 4. Stratégie d'Incrustation StoryWeaver (Recommandations Architecte)

Pour éviter de briser la base existante (`open-webui`) tout en permettant les fusions de futures MÀJ (merges de l'upstream) :

- **Backend** : 
  - Placer les routes StoryWeaver dans de nouveaux fichiers `routers/sw_novels.py`, `routers/sw_kb.py` et les appeler depuis `main.py`.
  - Placer les modèles SQLAlchemy de StoryWeaver dans `models/sw_novels.py` et l'enregistrer dans la base Alembic existante via une migration `alembic revision --autogenerate -m "Add StoryWeaver tables"`.
  - Accroche du contexte : Il faudra probablement intercepter le middleware de chat (`utils/middleware.py`) ou le corps de la route dans `routers/chats.py` pour injecter automatiquement le résumé/la KB du roman actif.

- **Frontend** :
  - Ajouter un layout contextuel à "l'espace auteur" ou modifier `+layout.svelte` pour afficher la sélection du roman (un `select` en haut de la sidebar).
  - Injecter `window.location` ou router vers une nouvelle page de type "Éditeur de manuscrit" (`src/routes/(app)/novel/[id]/`).

### Approche Validation Qualité (QA)
Étant donné la nature intriquée d'OpenWebUI :
1. Aucune modification du fichier Svelte coeur du layout sans isoler au test.
2. Protéger impérativement les tests Vitest/Pytest existants (ne pas casser les mocks de l'API standard d'Open WebUI).
