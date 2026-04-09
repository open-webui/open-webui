# Workflow — Ajout d'un Custom Tool StoryWeaver
---
description: Processus de création d'un nouveau Custom Tool Python (brainstorm, coherence, dialogue, outline)
---

## Déclencheur
Le Lead Agent assigne la création d'un nouveau Custom Tool à partir de la Phase 3 de la roadmap.

## Agents impliqués
1. **Backend Dev** (implémentation)
2. **Architecte** (validation du contrat du tool)
3. **QA Auditeur** (review + tests avec mock Ollama)

## Étapes

### Étape 1 : Définir le Contrat du Tool
- **Agent** : Architecte (valide) + Backend Dev (propose)
- **Action** : Spécifier le contrat du tool:
  - Nom de la fonction
  - Paramètres d'entrée (typés)
  - Structure du retour (Pydantic model)
  - Données KB nécessaires (characters ? universe ? manuscript ?)
- **Output** : Contrat validé en 10 lignes max

### Étape 2 : Écrire les Tests d'Abord (TDD)
- **Agent** : Backend Dev
- **Action** :
  1. Créer `tests/test_tools_[nom].py`
  2. Écrire les cas de test avec mock Ollama (réponse simulée)
  3. Les tests doivent échouer à ce stade (normal en TDD)
- **Output** : Fichier de tests prêt

### Étape 3 : Implémenter le Tool
- **Agent** : Backend Dev
- **Action** :
  1. Créer `tools/[nom].py`
  2. Implémenter la fonction avec le contrat validé
  3. Charger KB depuis les DAOs
  4. Construire le prompt + appeler Ollama
  5. Parser et retourner la réponse formatée
  6. Sauvegarder en DB si applicable (brainstorm sessions, etc.)
- **Output** : Tool fonctionnel, tests au vert

### Étape 4 : Intégrer dans le Chat
- **Agent** : Backend Dev
- **Action** : Enregistrer le tool dans le registre OpenWebUI
  Pour activer via les commandes slash (`/brainstorm`, `/outline`, etc.)
- **Output** : Tool accessible depuis le chat

### Étape 5 : Review QA
- **Agent** : QA Auditeur
- **Action** : Vérifier les tests, la gestion d'erreur si Ollama est down,
  la gestion du context window overflow, la sauvegarde en DB
- **Output** : Verdict ✅ / 🔄

## Template de Tool à Respecter

```python
# tools/[nom].py

from typing import Optional
from ..database.daos import KnowledgeBaseDAO, NovelDAO
from ..utils.ollama_client import call_ollama
from ..database.models_storyweaver import Novel

def [tool_name](
    novel_id: str,
    # paramètres spécifiques au tool
    db  # session SQLAlchemy injectée
) -> dict:  # ou list selon le tool
    """
    [Description du tool en une phrase].
    
    Args:
        novel_id: UUID du roman courant
        db: Session SQLAlchemy
    
    Returns:
        [Description de la structure de retour]
    """
    # 1. Vérifier le novel existe
    novel = NovelDAO.get_by_id(db, novel_id)
    if not novel:
        raise ValueError(f"Novel {novel_id} not found")
    
    # 2. Charger les données KB nécessaires
    kb = KnowledgeBaseDAO.get_by_novel_id(db, novel_id)
    
    # 3. Construire le prompt (limité à CONTEXT_WINDOW_SIZE tokens)
    prompt = _build_prompt(novel, kb, ...)
    
    # 4. Appeler Ollama avec gestion d'erreur
    response = call_ollama(prompt)
    
    # 5. Parser et retourner
    return _parse_response(response)
```

## Conditions de Sortie
- Tool fonctionnel avec tests passants (mock Ollama)
- Gestion d'erreur si Ollama est indisponible
- Commande slash enregistrée et accessible depuis le chat
- Review QA ✅

## Gestion des Erreurs
- Si Ollama timeout → Retourner une erreur explicite (pas un crash silencieux)
- Si context window overflow → Tronquer la KB avec un warning loggé
- Si DB vide (novel sans KB) → Retourner un message d'aide à l'utilisateur
