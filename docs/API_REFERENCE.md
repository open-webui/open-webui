# API Reference — StoryWeaver

Tous les endpoints sont préfixés par `/api/sw`. L'authentification par `Bearer Token` est obligatoire pour toutes les requêtes.

## 1. Novels — Gestion des Romans

### `GET /novels/`
Récupère tous les romans de l'utilisateur.
- **Réponse** : `Novel[]`

### `POST /novels/create`
Crée un nouveau roman.
- **Payload** : `{ "title": string, "description": string }`
- **Réponse** : `Novel`

### `POST /novels/{id}/select`
Sélectionne un roman comme "actif" pour la session courante (pour l'injection dans le chat).
- **Réponse** : `{ "status": "selected", "novel_id": string }`

---

## 2. Knowledge Base (KB)

### `GET /novels/{id}/kb/`
Récupère la Knowledge Base complète d'un roman.
- **Réponse** : `KBObject` contenant `universe_docs`, `characters`, `locations`, `objects`, `timeline`.

### `POST /novels/{id}/kb/{section}/add`
Ajoute une fiche dans une section spécifique.
- **Payload** : `{ "data": Object }`
- **Réponse** : item créé.

---

## 3. Chapters — Manuscrit

### `GET /{novel_id}/chapters`
Récupère la liste ordonnée des chapitres.
- **Réponse** : `Chapter[]`

### `POST /{novel_id}/chapters`
Crée un nouveau chapitre.
- **Payload** : `{ "title": string, "order": number }`

### `POST /chapters/{chapter_id}/update`
Met à jour le contenu ou le titre d'un chapitre.
- **Payload** : `{ "title": string, "content": string, "status": string }`

### `POST /{novel_id}/chapters/reorder`
Réorganise massivement les chapitres.
- **Payload** : `{ "ordered_ids": string[] }`

---

## 4. Outils Créatifs (Tools)

Ces "outils" sont accessibles via des commandes slash dans l'interface de chat.
- `/brainstorm` : Idées et rebondissements.
- `/coherence` : Vérification des contradictions avec la KB.
- `/dialogue` : Assistance à la rédaction de dialogues.
- `/outline` : Proposition de structure de scène.

*Note : Ces outils sont gérés par le middleware backend qui injecte le contexte de la KB active dans le prompt système.*
