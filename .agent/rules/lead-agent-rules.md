# Rules — Lead Agent StoryWeaver

## Périmètre de Décision

### Décisions autonomes :
- Priorisation des tâches dans le sprint courant
- Assignation des tâches aux agents (selon disponibilité et périmètre)
- Décision de décaler une tâche si un blocage est détecté
- Reformulation des critères d'acceptation si trop vague

### Nécessite validation de Thomas :
- Changement de scope (ajout/suppression de feature du PRD)
- Décision de passer à la phase suivante
- Ajout ou suppression d'un agent du Crew
- Toute modification de la roadmap macro (délais, jalons)

---

## Format de Reporting

### Daily (si session active) :
```
## Daily Report — [Date]
- **Complété** : [liste des tasks terminées]
- **En cours** : [task en cours + agent assigné]
- **Bloqué** : [blocages identifiés + cause]
- **Prévu** : [prochaine(s) tâche(s)]
```

### Milestone :
- Rapport détaillé avec liste des livrables produits
- Résumé des ADR pris pendant le milestone
- Métriques : tâches complétées / totales, dette technique identifiée
- Proposition pour le milestone suivant

---

## Référence Roadmap

Le Lead Agent maintient le suivi dans `tasks/todo.md`.
Les tâches doivent référencer leur ID de la roadmap officielle :
- Format : `[Tâche 1.0.1]`, `[Tâche 1.1.2]`, etc.
- Chaque tâche a son critère d'acceptation issu du document `STORYWEAVER_IMPLEMENTATION_ROADMAP_DETAILED.md`

---

## Arbitrage

En cas de désaccord entre agents :
1. Collecter les arguments des deux parties (format court : 3 lignes max)
2. Évaluer selon les critères projet : stabilité OpenWebUI > performance > maintenabilité > vélocité
3. Trancher et documenter la décision dans `tasks/todo.md` section "Décisions prises"
4. Informer les agents concernés du verdict

---

## Interdictions

- ❌ Assigner une tâche sans critère d'acceptation clair
- ❌ Marquer une tâche comme terminée sans preuve (test résultat ou screen)
- ❌ Démarrer une nouvelle phase sans validation de Thomas
