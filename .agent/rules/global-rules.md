# Règles Globales du Crew — StoryWeaver

## Principes Fondamentaux

1. **Qualité > Vitesse** : Ne jamais livrer du code qui casse le chat OpenWebUI de base.
   StoryWeaver est une extension — l'hôte doit toujours rester fonctionnel.
2. **Communication explicite** : Chaque agent documente ses décisions, ses doutes et ses blocages.
   Aucun agent ne travaille en isolation silencieuse.
3. **Périmètre strict** : Chaque agent agit dans son périmètre défini. En cas de chevauchement,
   le Lead Agent arbitre. **Ne jamais modifier les fichiers OpenWebUI core sans accord de l'Architecte.**
4. **Traçabilité** : Chaque modification est traçable (commit message Conventional Commits,
   ADR dans `design.md` pour les décisions structurantes).
5. **Itération** : Préférer des livraisons petites et fréquentes (tâches atomiques de 1-2 jours)
   à des livraisons massives qui risquent de casser l'intégration.
6. **Thomas in Control** : L'IA propose, Thomas dispose. Jamais de modification destructive
   (suppression de données, migration irréversible) sans confirmation explicite.

---

## Langue & Communication

- **Langue du code** : Anglais (variables, fonctions, classes, commentaires inline)
- **Langue de la documentation** : Français (tous les `.md` sauf le code lui-même)
- **Langue des commits** : Conventional Commits en anglais
  - `feat:` nouvelles features, `fix:` corrections, `chore:` maintenance, `refactor:` refactoring
- **Format des messages entre agents** : Markdown structuré avec ID de tâche référencé

---

## Conventions de Nommage

- **Fichiers Python** : `snake_case.py`
- **Fichiers Svelte** : `PascalCase.svelte`
- **Variables/fonctions Python** : `snake_case`
- **Variables/fonctions JS/Svelte** : `camelCase`
- **Composants Svelte** : `PascalCase`
- **Constantes** : `SCREAMING_SNAKE_CASE`
- **Branches git** : `feat/[milestone-id]-[description-courte]` (ex: `feat/1.1.1-novel-models`)
- **IDs d'entités StoryWeaver** : UUID v4

---

## Structure Projet StoryWeaver

```
open-webui/ (fork)
├── backend/
│   ├── database/
│   │   ├── models_storyweaver.py     ← NOUVEAU
│   │   └── daos.py                   ← NOUVEAU
│   ├── routes/
│   │   ├── novels.py                 ← NOUVEAU
│   │   ├── knowledge_base.py         ← NOUVEAU
│   │   └── manuscript.py             ← NOUVEAU
│   └── utils/
│       └── prompt_builder.py         ← NOUVEAU
├── tools/                            ← NOUVEAU DOSSIER
│   ├── novel_context_injector.py
│   ├── brainstorm.py
│   ├── coherence_checker.py
│   ├── dialogue_generator.py
│   └── outline_generator.py
├── frontend/
│   └── src/lib/components/           ← NOUVEAUX composants
│       ├── NovelManager.svelte
│       ├── KnowledgeBaseEditor.svelte
│       ├── ManuscriptEditor.svelte
│       └── ToolsPanel.svelte
├── alembic/versions/*storyweaver*    ← NOUVEAUX migrations
├── .agent/                           ← Crew IA Antigravity
├── design.md                         ← Architecture & ADR
├── gemini.md                         ← Carte d'identité projet
└── DEVELOPMENT.md                    ← Guide de setup
```

---

## Standards de Qualité

- **Couverture de tests** : 70% minimum sur les DAOs et Custom Tools Python
- **Typage** : Type hints obligatoires sur toutes les fonctions Python; TypeScript sur les stores Svelte
- **Linting** : Black (Python) + Ruff (Python) + ESLint (Svelte) — zéro warning en CI
- **Performance** : Context injection < 500ms, DB queries < 100ms, UI responsive < 16ms
- **Review** : Tout merge nécessite le verdict ✅ du QA Auditeur
- **Documentation** : Chaque nouveau module Python et composant Svelte a sa docstring/JSDoc

---

## Interdictions Absolues

- ❌ **Committer des secrets, tokens ou credentials** (utiliser `.env.local` exclusivement)
- ❌ **Modifier les tables SQLAlchemy OpenWebUI existantes** sans validation Architecte + backup DB
- ❌ **Merger une migration Alembic** non testée up ET down
- ❌ **Déployer sur le VPS** sans passage par le pipeline CI local
- ❌ **Supprimer des données Novel/KB** sans confirmation explicite de Thomas
- ❌ **Casser le chat OpenWebUI de base** (test de non-régression obligatoire)
- ❌ **Créer des dépendances circulaires** entre modules StoryWeaver

---

## Escalade

Remonter au Lead Agent si :
- Blocage technique > 30 min sans solution
- Conflit de périmètre avec un autre agent
- Décision ayant un impact sur les tables OpenWebUI existantes
- Découverte d'un bug dans OpenWebUI impactant l'intégration StoryWeaver
- Toute opération pouvant entraîner une perte de données de l'auteur
