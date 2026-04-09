# Workflow — Développement Standard StoryWeaver
---
description: Boucle de développement standard pour chaque feature/tâche atomique
---

## Déclencheur
Le Lead Agent assigne une tâche atomique à un agent dev (backend ou frontend).

## Agents impliqués
1. **Lead Agent** (assigne, valide la complétion)
2. **Backend Dev** OU **Frontend Dev** (implémente)
3. **Architecte** (consulté si la tâche implique une décision d'architecture)
4. **QA Auditeur** (review finale)

## Étapes

### Étape 1 : Prise en Charge
- **Agent** : Dev assigné
- **Action** : Lire la spec de la tâche, vérifier les dépendances (tâches préalables),
  estimer la complexité, signaler tout blocage immédiat.
- **Output** : Confirmation de prise en charge ou demande de clarification (< 15 min)
- **Validation** : L'agent comprend les critères d'acceptation

### Étape 2 : Conception (si tâche complexe ou nouveau contrat API)
- **Agent** : Dev assigné + Architecte
- **Action** : Proposer une approche technique (mini-spec en 5-10 lignes).
  L'Architecte valide la cohérence avec l'architecture existante.
- **Output** : Mini-spec technique approuvée (ou task redéfinie)
- **Skip si** : La tâche est une implémentation directe d'un DAO ou d'un composant déjà spécifié

### Étape 3 : Implémentation
- **Agent** : Dev assigné
- **Action** :
  1. Créer branche `feat/[task-id]-[description]`
  2. Implémenter la feature
  3. Écrire les tests simultanément
  4. Respecter les rules de l'agent et les global-rules
- **Output** : Code + tests passants sur la branche
- **Validation** : Linting OK, tests passants, couverture ≥ 70%

### Étape 4 : Self-Review
- **Agent** : Dev assigné
- **Action** : Appliquer la checklist self-review du fichier de rules de son agent.
  Corriger les problèmes évidents avant soumission.
- **Output** : Code nettoyé, prêt pour review QA

### Étape 5 : Review QA
- **Agent** : QA Auditeur
- **Action** : Appliquer la checklist de review complète (backend ou frontend selon la tâche)
- **Output** : ✅ Approuvé / 🔄 Corrections demandées / ❌ Refusé (avec liste)
- **Délai** : Le QA rend son verdict dans la même session

### Étape 6 : Corrections (si 🔄)
- **Agent** : Dev assigné
- **Action** : Appliquer les corrections demandées par le QA Auditeur
- **Output** : Code corrigé → Retour à Étape 5
- **Maximum** : 2 cycles de correction avant escalade au Lead Agent

### Étape 7 : Merge & Report
- **Agent** : Dev assigné
- **Action** :
  1. Merger la branche sur `feature/storyweaver-core`
  2. Marquer la tâche `[x]` dans `tasks/todo.md`
  3. Notifier le Lead Agent avec le résumé de complétion
- **Output** : Feature mergée, backlog mis à jour
- **Message de commit** : Conventional Commits (ex: `feat(novels): add Novel CRUD router`)

## Conditions de Sortie
- Code mergé sur `feature/storyweaver-core`
- Tests passants sur la branche mergée
- Tâche marquée complète dans `tasks/todo.md`
- Lead Agent informé

## Gestion des Erreurs
- **Blocage technique > 30 min** → Escalade à l'Architecte
- **Review refusée 2 fois** → Lead Agent arbitre
- **Conflit de merge** → Dev résout, Architecte arbitre si conflit complexe
- **Régression détectée** → STOP, priorité absolue sur le fix avant toute nouvelle tâche
