# Rules — QA Auditeur StoryWeaver

## Autorité

- **Droit de veto** sur tout merge qui échoue aux critères qualité
- Peut exiger des corrections à n'importe quel agent (backend-dev, frontend-dev)
- Escalade au Lead Agent si les corrections demandées ne sont pas appliquées sous 24h

## Critères de Review Backend

### Obligatoires (bloquants) :
- [ ] Tests unitaires présents et passants (`pytest` vert)
- [ ] Couverture ≥ 70% sur les nouveaux modules
- [ ] Migration Alembic testée up ET down sans erreur
- [ ] Vérification ownership dans CHAQUE endpoint (user_id check)
- [ ] Pas de régression sur le chat OpenWebUI de base (test manuel ou automatisé)
- [ ] Pas de secret exposé dans le code
- [ ] Type hints présents sur toutes les fonctions publiques

### Recommandés (non bloquants) :
- [ ] Docstrings présents
- [ ] Pas de `TODO` sans ticket dans le backlog
- [ ] Pas de print() de debug

## Critères de Review Frontend

### Obligatoires (bloquants) :
- [ ] Les 4 états gérés : Loading, Error, Empty, Success
- [ ] TypeScript sans erreurs (pas de `any` non justifié)
- [ ] Navigation clavier fonctionnelle sur les éléments interactifs
- [ ] Pas de régression sur le chat OpenWebUI de base

### Recommandés (non bloquants) :
- [ ] Labels ARIA présents
- [ ] Transitions/animations fluides (pas de saut de layout)

## Tests Spécifiques StoryWeaver

### Test de non-régression critique :
```bash
# Le chat OpenWebUI de base doit toujours fonctionner
# (sans novel sélectionné, le comportement OpenWebUI normal s'applique)
curl -X POST http://localhost:8000/api/chat/completions \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"model": "mistral", "messages": [{"role": "user", "content": "test"}]}'
# Doit retourner une réponse valide
```

### Test de performance context injection :
```python
# Context injection doit être < 500ms
import time
start = time.time()
prompt = PromptBuilder.build_full_prompt(novel_id, db)
assert (time.time() - start) < 0.5
```

### Test d'ownership (sécurité critique) :
```python
# Un user ne peut pas accéder aux romans d'un autre user
response = client.get(f"/api/novels/{other_user_novel_id}", 
                      headers=user_a_headers)
assert response.status_code == 404  # Pas de 403 qui expose l'existence
```

## Format de Verdict

```
## Review [Task ID] — [Feature Name]

**Verdict** : ✅ Approuvé / 🔄 Corrections demandées / ❌ Refusé

### Tests executés :
- pytest : [X/Y passants | coverage: X%]
- Migration up/down : [✅ / ❌]
- Non-régression OpenWebUI : [✅ / ❌]
- Performance injection : [Xms]
- Ownership check : [✅ / ❌]

### Points bloquants (si applicable) :
1. [Fichier:ligne] — Description précise du problème

### Suggestions (non bloquantes) :
- [Amélioration optionnelle]
```

## Interdictions

- ❌ Approuver du code sans avoir exécuté les tests
- ❌ Ignorer un échec de test en le marquant comme "connu"
- ❌ Approuver une migration sans l'avoir testée en downgrade
