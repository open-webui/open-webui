# Workflow — Initialisation du Projet StoryWeaver
---
description: Bootstrap complet du fork OpenWebUI et configuration de l'environnement de dev
---

## Déclencheur
Commande : "Lancer l'initialisation du projet" ou début de Phase 1 (Task 1.0.x)
Exécuté une seule fois au démarrage du projet.

## Agents impliqués
1. **Lead Agent** (orchestre et valide)
2. **Legacy Specialist** (analyse structure existante)
3. **Architecte** (valide les décisions de setup)
4. **Documentaliste** (produit DEVELOPMENT.md)

## Étapes

### Étape 1 : Validation du Contexte (Lead Agent)
- **Agent** : Lead Agent
- **Action** : Relire `gemini.md` et `design.md`, vérifier que les PRDs sont cohérents
  avec l'architecture validée.
- **Output** : Checklist de validation ✅/❌
- **Validation** : Tous les points verts avant de continuer

### Étape 2 : Fork et Setup Git (Task 1.0.1)
- **Agent** : Lead Agent (puis Thomas exécute)
- **Actions** :
  1. Créer fork privé de `open-webui/open-webui` sur GitHub
  2. Cloner localement
  3. Créer branche `feature/storyweaver-core`
  4. Initialiser `.gitignore` personnalisé
- **Output** : Repo cloné, branche créée
- **Validation** : `git log` montre les commits originaux ; `git branch` montre `feature/storyweaver-core`

### Étape 3 : Setup Environnement Dev (Task 1.0.2)
- **Agent** : Backend Dev (installe backend) + Frontend Dev (installe frontend)
- **Actions Backend** :
  1. Vérifier Python 3.10+
  2. `poetry install` (ou `pip install -r requirements.txt`)
  3. Créer `.env.local` avec les variables minimales
  4. Vérifier `poetry run python main.py` lance sans erreur
- **Actions Frontend** :
  1. Vérifier Node.js 18+
  2. `cd frontend && npm install`
  3. Vérifier `npm run dev` lance le dev server
- **Output** : Dev env fonctionnel
- **Validation** : `curl http://localhost:8000/api/models` retourne JSON ; browser affiche OpenWebUI

### Étape 4 : Analyse Structure Existante (Task 1.0.3)
- **Agent** : Legacy Specialist
- **Action** : Mapper backend (routes, modèles, dépendances) et frontend (composants, stores, routing)
- **Output** : `ARCHITECTURE_EXISTING.md` avec diagrammes ASCII
- **Validation** : L'Architecte approuve le rapport avant de passer à la Phase 1.1

### Étape 5 : Premier Backlog
- **Agent** : Lead Agent
- **Action** : Créer `tasks/todo.md` avec les tasks atomiques de Phase 1
  basé sur `STORYWEAVER_IMPLEMENTATION_ROADMAP_DETAILED.md`
- **Output** : `tasks/todo.md` avec Milestone 1.1 décomposé
- **Validation** : Au moins 5 tâches atomiques avec critères d'acceptation

### Étape 6 : Documentation Setup
- **Agent** : Documentaliste
- **Action** : Créer `DEVELOPMENT.md` avec les étapes de setup validées (versions, commandes)
- **Output** : `DEVELOPMENT.md` complet et testé

## Conditions de Sortie
- Fork cloné et branche feature créée
- Backend et frontend démarrables en local
- `ARCHITECTURE_EXISTING.md` produit et validé par l'Architecte
- `tasks/todo.md` initialisé
- `DEVELOPMENT.md` disponible

## Gestion des Erreurs
- Si poetry install échoue → Backend Dev diagnostique les conflits de dépendances, note dans DEVELOPMENT.md
- Si OpenWebUI ne démarre pas → Legacy Specialist analyse les logs, Architecte propose un fix
- Si l'analyse OpenWebUI est trop complexe → Legacy Specialist décompose en sous-analyses par module
