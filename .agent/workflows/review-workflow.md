# Workflow — Review & Qualité StoryWeaver
---
description: Processus de revue de code et d'audit qualité pour les features StoryWeaver
---

## Déclencheur
Un agent dev soumet du code pour review au QA Auditeur.

## Agents impliqués
1. **QA Auditeur** (review principale, verdict)
2. **Architecte** (review architecturale si impact structurel)
3. **Dev soumettant** (corrections)
4. **Lead Agent** (escalade si blocage)

## Étapes

### Étape 1 : Triage
- **Agent** : QA Auditeur
- **Action** : Évaluer la taille et l'impact du changement.
  Classer en : Minor (DAO / composant isolé) / Standard (nouveau router) / Major (modification chat.py)
- **Output** : Classification + décision si review architecturale nécessaire
- **Durée** : < 5 minutes

### Étape 2 : Review Code
- **Agent** : QA Auditeur
- **Action** : Appliquer la checklist de review complète (selon backend/frontend)
  Exécuter les tests, vérifier les migrations, tester la non-régression.
- **Output** : Rapport de review structuré (voir format dans `qa-auditeur-rules.md`)

### Étape 3 : Review Architecture (si classification Major)
- **Agent** : Architecte
- **Action** : Valider la cohérence architecturale du changement.
  Vérifier la conformité avec les ADR existants dans `design.md`.
- **Output** : Avis architecture (conforme / ajustements nécessaires)

### Étape 4 : Consolidation
- **Agent** : QA Auditeur
- **Action** : Consolider les retours (QA + Architecture si applicable)
  Produire le verdict final avec liste d'actions priorisée.
- **Output** : Verdict final avec format standard

## Format du Verdict Final

```
## Verdict Review [Task ID]

✅ APPROUVÉ / 🔄 CORRECTIONS REQUISES / ❌ REFUSÉ

[Si ✅] : Merger autorisé. [Commentaire optionnel]

[Si 🔄] : Corrections requises avant merge :
1. [CRITIQUE] [fichier:ligne] Description précise
2. [CRITIQUE] ...
Suggestions (non bloquantes) :
- [OPTIONNEL] ...

[Si ❌] : Refus justifié. Revoir l'approche :
- Raison principale : ...
- Alternative recommandée : ...
```

## Conditions de Sortie
- Verdict final rendu
- Si corrections : le Dev a une liste d'actions claire et priorisée
- Si ✅ : Merge autorisé, Lead Agent notifié

## Gestion des Erreurs
- Si le Dev ne fait pas les corrections après 24h → Lead Agent escalade
- Si désaccord QA / Architecte sur le verdict → Lead Agent arbitre
- Si régression critique découverte → STOP toutes les tâches en cours, hotfix prioritaire
