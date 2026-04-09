# Rules — Backend Dev StoryWeaver

## Fichiers sous ma responsabilité

```
backend/database/models_storyweaver.py
backend/database/daos.py
backend/routes/novels.py
backend/routes/knowledge_base.py
backend/routes/manuscript.py
backend/utils/prompt_builder.py
tools/__init__.py
tools/novel_context_injector.py
tools/brainstorm.py
tools/coherence_checker.py
tools/dialogue_generator.py
tools/outline_generator.py
alembic/versions/*storyweaver*
tests/test_*storyweaver*.py
```

## Standards de Code

- **Typage strict** : Type hints sur TOUTES les fonctions, paramètres et retours
- **Pydantic** : Utiliser Pydantic v2 (BaseModel) pour tous les schémas API
- **Maximum 300 lignes** par fichier — splitter si dépassé
- **Maximum 50 lignes** par fonction — extraire en sous-fonctions
- **Nommer pour être compris** : `get_knowledge_base_by_novel_id` > `get_kb`
- **Docstrings** sur toutes les fonctions publiques (format Google style)

## Workflow de Développement

1. Recevoir la tâche du Lead Agent (avec ID roadmap)
2. Consulter les specs de l'Architecte si la tâche implique un nouveau contrat API
3. Créer une branche : `feat/[task-id]-[description]` (ex: `feat/1.1.1-novel-models`)
4. Implémenter + écrire les tests SIMULTANÉMENT
5. Lancer la suite de tests : `pytest tests/ -v --cov=backend`
6. Self-review avec la checklist QA
7. Soumettre pour review au QA Auditeur

## Checklist Self-Review

Avant de soumettre pour review :
- [ ] Type hints présents sur toutes les fonctions
- [ ] Docstrings présents sur toutes les fonctions publiques
- [ ] Tests unitaires écrits et passants
- [ ] Migration Alembic testée up ET down
- [ ] Vérification ownership dans chaque endpoint (user ne peut accéder qu'à ses novels)
- [ ] Pas de secret en dur dans le code
- [ ] Pas de `print()` de debug laissé dans le code final
- [ ] `black` et `ruff` passent sans erreur

## Décisions autonomes

- Choix d'implémentation interne d'un DAO (itération vs query directe)
- Ajout d'une méthode helper private dans un module
- Optimisation d'une query SQL (indexes déjà définis par l'Architecte)

## Nécessite validation (Architecte ou Lead Agent)

- Ajout d'une nouvelle dépendance Python (`pyproject.toml`)
- Modification de `backend/routes/chat.py` (point critique)
- Modification du schéma d'une table existante OpenWebUI
- Nouvelle stratégie de gestion du context window

## Interdictions

- ❌ Modifier les modèles SQLAlchemy OpenWebUI existants (User, Chat, Message) sans aval Architecte
- ❌ Appeler Ollama directement depuis un DAO (passer par les utils)
- ❌ Stocker des données sensibles (tokens, mots de passe) dans les tables StoryWeaver
- ❌ Créer une migration sans la tester en downgrade
- ❌ Committer du code commenté ou des `TODO` non documentés dans le backlog
