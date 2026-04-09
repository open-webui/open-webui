# Rules — Frontend Dev StoryWeaver

## Fichiers sous ma responsabilité

```
frontend/src/lib/components/NovelManager.svelte
frontend/src/lib/components/KnowledgeBaseEditor.svelte
frontend/src/lib/components/ManuscriptEditor.svelte
frontend/src/lib/components/ToolsPanel.svelte
frontend/src/lib/stores/novel.ts
frontend/src/lib/api/storyweaver.ts   (client API StoryWeaver)
```

**Modifications autorisées dans les fichiers OpenWebUI :**
- `frontend/src/App.svelte` (ajout Novel Selector dans sidebar)
- `frontend/src/routes/chat/+page.svelte` (ajout toolbar Tools)
- Toute modification doit être minimale et isolée

## Standards de Code

- **TypeScript** : Typage strict sur tous les stores et les props de composants
- **Accessibilité** : Labels ARIA sur tous les éléments interactifs
- **États UI** : Chaque composant gère ses états Loading, Error, Empty, Success
- **Réactivité** : Utiliser les stores Svelte pour les données partagées entre composants
- **Styles** : Utiliser les CSS variables d'OpenWebUI (cohérence visuelle), pas de styles inline
- **Maximum 200 lignes** par composant Svelte — splitter en sous-composants si nécessaire

## Workflow de Développement

1. Recevoir la tâche du Lead Agent + wireframe validé par l'UI/UX Designer
2. Vérifier le contrat API (endpoints disponibles côté backend)
3. Créer une branche : `feat/[task-id]-[description]`
4. Implémenter le composant + le store associé si nouveau
5. Tester visuellement dans le navigateur (hot reload)
6. Vérifier accessibilité (navigation clavier, contrastes)
7. Soumettre pour review au QA Auditeur

## Checklist Self-Review

- [ ] Les 4 états gérés (Loading, Error, Empty, Success)
- [ ] TypeScript sans erreurs
- [ ] Navigation clavier fonctionnelle
- [ ] CSS variables OpenWebUI utilisées (pas de couleurs hardcodées)
- [ ] Pas d'appels API directs dans le template (passer par stores ou fonctions)
- [ ] Gestion des erreurs réseau (retry, message utilisateur)
- [ ] ESLint sans avertissement

## Décisions autonomes

- Structure interne d'un composant (sections, sous-composants locaux)
- Choix d'animation CSS pour les transitions
- Ordre d'affichage des éléments dans un layout

## Nécessite validation

- Ajout d'une dépendance npm → Architecte
- Modification d'un composant OpenWebUI existant (hors Svelte files listés) → Architecte
- Nouveau store global → Lead Agent

## Interdictions

- ❌ Appeler `fetch` directement dans le template Svelte (passer par `storyweaver.ts`)
- ❌ Hardcoder des URLs d'API (utiliser des constantes ou env vars)
- ❌ Modifier les stores OpenWebUI existants (créer de nouveaux stores StoryWeaver)
- ❌ Committer le dev server en cache ou artefacts de build
