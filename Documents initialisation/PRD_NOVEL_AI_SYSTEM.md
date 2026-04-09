# 📖 PRD : StoryWeaver - Système d'Assistance IA pour la Rédaction de Roman

**Version:** 1.0  
**Date:** Avril 2026  
**Auteur:** Projet Personnel  
**Status:** En cours de définition

---

## 1. VISION & OBJECTIFS STRATÉGIQUES

### Vision
Créer une **plateforme personnalisée d'assistance IA conversationnelle** dédiée à la rédaction de roman, intégrant gestion du contexte narratif, base de connaissances structurée et outils spécialisés, fonctionnant sur une infrastructure locale (Ollama + Mistral).

### Objectifs Principaux
- ✅ **Réduire la friction créative** : chat IA avec mémoire complète du roman et univers
- ✅ **Assurer la cohérence narrative** : contexte persistant avec versioning/historique
- ✅ **Gérer la complexité multi-projet** : support multi-roman avec archivage et réutilisation
- ✅ **Structurer l'univers fictionnel** : knowledge base des personnages, lieux, objets, règles du monde
- ✅ **Faciliter le flux d'écriture** : interface flexible (chat + éditeur + modules spécialisés)

---

## 2. USER PERSONAS

### Persona 1 : L'Auteur Holistique
- **Nom** : Thomas (Vous !)
- **Besoins** :
  - Brainstorming en conversation naturelle avec IA
  - Gestion cohérente de scénarios complexes
  - Structuration de mondes imaginaires
  - Révision/amélioration du contenu
  - Gestion de plusieurs romans en parallèle
- **Douleurs** : OpenWebUI trop générique, pas adapté au contexte narratif
- **Succès** : Rédiger plus vite avec moins de discontinuités narratives

### Persona 2 : Le Novice (Future)
- Auteur débutant cherchant aide structurée
- Aurait besoin de guides/templates
- Focus sur génération d'idées

### Persona 3 : L'Auteur Professionnel (Future)
- Gestion de projets importants
- Besoin de collaboration/partage de contexte
- Export professionnel (ePub, etc.)

---

## 3. PÉRIMÈTRE & FEATURES (MVP → V2)

### 3.1 PHASE 1 : MVP (Core Features)

#### **A. Gestionnaire de Projets Romains**
```
Fonctionnalités :
□ Créer/ouvrir/supprimer/archiver un projet roman
□ Vue liste avec metadata (titre, status, dernière modif, nb chapitres)
□ Basculer entre projets
□ Export/import de projets (pour réutilisation)
```

#### **B. Chat IA Contextualisé (Cœur du système)**
```
Fonctionnalités :
□ Interface chat conversationnel (style OpenWebUI)
□ Injection automatique du contexte du roman :
  - Univers (règles du monde, lore)
  - Personnages actifs
  - Scènes/passages récents
  - Historique de conversation (session)
□ Mémoire persistante entre sessions (conversation + contexte)
□ Versioning de la conversation (historique des changements)
□ Tags système pour catégoriser les messages
  (#brainstorm, #structure, #revision, #dialogue, etc.)
```

#### **C. Knowledge Base Structurée (Univers du Roman)**
```
Sections :

1. UNIVERS
   ├─ Règles du monde (magie, technologie, physique)
   ├─ Lore général (histoire, mythologie)
   ├─ Géographie (cartes textuelles, lieux)
   └─ Timeline (événements importants)

2. PERSONNAGES
   ├─ Fiche par personnage :
   │  ├─ Nom, âge, apparence
   │  ├─ Personnalité & arcs
   │  ├─ Relations (liens croisés vers autres personnages)
   │  ├─ Objectifs/motivations
   │  ├─ Statut (vivant, décédé, en cours, archived)
   │  └─ Scènes associées
   └─ Historique des changements de personnage

3. LIEUX & OBJETS
   ├─ Descriptions structurées
   ├─ Relations/mentions
   └─ Métadonnées (importance, fréquence)

4. TRAME NARRATIVE
   ├─ Actes/chapitres
   ├─ Scènes avec statut (draft, in-progress, review, final)
   ├─ Clés de scène (POV, enjeux, révélations)
   └─ Dépendances entre scènes
```

#### **D. Éditeur Intégré (Markdown)**
```
Fonctionnalités :
□ Éditeur texte avec syntax highlighting Markdown
□ Arborescence chapitre/scène dans sidebar
□ Compteur de mots / statistiques
□ Synchronisation avec chat (context awareness)
□ Boutons rapides :
  - "Analyser ce passage"
  - "Continuer cette scène"
  - "Critiquer le style"
  - "Générer dialogues pour cette scène"
```

#### **E. Modules Spécialisés (Outils)**
```
1. BRAINSTORM
   - Génération d'idées (plots, twists, scènes)
   - Mind map textuelle
   - Randomisateur de prompts créatifs

2. OUTLINE / STRUCTURATION
   - Template d'actes (3-act, 5-act, 7-point)
   - Création automatique de chapitres
   - Visualisation de l'arc narratif

3. GÉNÉRATEUR DE DIALOGUES
   - Basé sur les personnages de la KB
   - Injection de contexte (relation, enjeux)

4. ANALYSEUR DE RÉVISION
   - Analyse de style (longueur phrases, répétitions)
   - Vérification de cohérence (timeline, noms personnages)
   - Feedback sur tensions narratives

5. RECHERCHE / DOCUMENTATION
   - Recherche dans la KB (full-text + tags)
   - Liens croisés automatiques
```

---

### 3.2 PHASE 2 : V1 (Enhanced)
- [ ] Export en formats (Markdown, PDF, ePub)
- [ ] Système de tags avancé
- [ ] Graphes de relations (personnages, lieux)
- [ ] Intégration de sources externes (recherche web)
- [ ] Templates de projets (Fantasy, SF, Romance, etc.)

### 3.3 PHASE 3 : V2+ (Future)
- [ ] Collaboration temps réel (multi-user)
- [ ] API pour plugins tiers
- [ ] Mobile app (compagnon)
- [ ] Sync cloud (optionnel)

---

## 4. ARCHITECTURE TECHNIQUE

### 4.1 Stack
```
Frontend:
├─ React/Vue.js (interface principale)
├─ Monaco Editor ou CodeMirror (éditeur Markdown)
├─ TailwindCSS (styling)
└─ Zustand/Pinia (state management)

Backend:
├─ Node.js/Express ou Python/FastAPI
├─ SQLite ou PostgreSQL (base données locale)
├─ LangChain (gestion contexte + prompts)
└─ Connexion Ollama/Mistral (local)

Infrastructure:
├─ VPS existant
├─ Ollama + Mistral (local LLM)
└─ Stockage local (fichiers + DB)
```

### 4.2 Modèle de Données Simplifié

```
Projects
├─ id, name, description, status
├─ created_at, updated_at
└─ knowledge_base_id (FK)

KnowledgeBase
├─ id, project_id
├─ universe_docs (JSON)
├─ characters (JSON array)
├─ locations (JSON array)
├─ objects (JSON array)
└─ updated_at

Manuscript
├─ id, project_id
├─ content (Markdown)
├─ word_count, status
├─ chapters (structure JSON)
└─ updated_at

Conversations
├─ id, project_id
├─ messages (JSON array)
├─ context_snapshot (JSON)
├─ tags (#brainstorm, #revision, etc.)
└─ version_history (array de snapshots)

VersionHistory
├─ id, entity_type, entity_id
├─ old_data, new_data
├─ change_type (created, updated, deleted)
├─ timestamp
└─ user_action (optional)
```

### 4.3 Flow d'Interaction Chaîne Contexte

```
User Input (Chat)
    ↓
[Context Injection]
├─ Récupère projet courant
├─ Charge KB (personnages, univers)
├─ Récupère dernières scènes du manuscrit
├─ Ajoute historique conversation
└─ Construit prompt système enrichi
    ↓
[Ollama/Mistral]
    ↓
Response + Save
├─ Sauvegarde message en DB
├─ Met à jour conversation version
└─ Affiche réponse à user
```

---

## 5. SPECIFICATIONS FONCTIONNELLES DÉTAILLÉES

### 5.1 Gestionnaire de Contexte IA

**Prompt System:**
```
SYSTEM PROMPT DYNAMIQUE:

Vous êtes un assistant IA spécialisé dans l'assistance créative à la rédaction de roman.
Vous avez accès au contexte complet du roman en cours :

[UNIVERS]
{univers_context}

[PERSONNAGES ACTIFS]
{characters_context}

[SCÈNES RÉCENTES]
{recent_scenes}

[HISTORIQUE CONVERSATION]
{conversation_history}

[DIRECTIVES SPÉCIFIQUES]
- Référencez la KB quand pertinent
- Maintenez la cohérence narrative
- Proposez des alternatives créatives
- Signalez les incohérences détectées
```

**Modes de Conversation:**
1. **Mode Brainstorm** : Créatif, divergent, idées libres
2. **Mode Structure** : Logique, cohérence, vérification
3. **Mode Révision** : Critique, amélioration, style
4. **Mode Recherche** : Consultation KB, linking

### 5.2 Knowledge Base

**Stockage et Accès:**
- Sections structurées en JSON/YAML (éditable)
- Full-text search avec tags
- Versioning des documents KB
- Auto-linking entre sections (via mentions)

**Exemple Personnage:**
```json
{
  "id": "char_001",
  "name": "Kaelith",
  "status": "alive",
  "role": "protagonist",
  "age": "27",
  "appearance": "cheveux noirs, yeux gris, cicatrice joue gauche",
  "personality": ["ambitieuse", "impulsive", "loyal"],
  "arc_narrative": "Découverte de ses pouvoirs magiques",
  "motivations": ["venger sa famille", "trouver sa place dans le monde"],
  "relationships": [
    { "character_id": "char_002", "type": "allié", "tension": "modérée" }
  ],
  "scenes": ["scene_034", "scene_067"],
  "history": [
    { "version": 1, "change": "création", "date": "2024-01-15" },
    { "version": 2, "change": "arc ajouté", "date": "2024-02-20" }
  ]
}
```

### 5.3 Système de Versioning

**Tri-Level Versioning:**
```
1. Document Level
   └─ Chaque section KB, chapitre, scène
   └─ Snapshot à chaque modification

2. Conversation Level
   └─ Sauvegarde état conversation + contexte injecté
   └─ Permet de rejouer/comparer versions

3. Project Level
   └─ Snapshots complets du projet
   └─ Export/archivage
```

**Timeline de Révision:**
- Visualiser historique changement d'un personnage
- Diff entre versions de passages
- Annotation des changements

---

## 6. USER INTERFACE - Layout Proposé

### 6.1 Layout Principal (Tripartite)

```
┌─────────────────────────────────────────────────────┐
│  HEADER: Logo | Project Selector | Settings | Help  │
├──────────────────┬──────────────────┬───────────────┤
│   SIDEBAR LEFT   │   MAIN EDITOR    │ SIDEBAR RIGHT │
│                  │                  │               │
│ □ Chat Window    │ Éditeur Markdown │ □ Knowledge   │
│   (contexte)     │ avec preview      │   Base Panel  │
│                  │                  │               │
│ Historique       │ Chapitre 1       │ ├─ Univers    │
│ conversations    │ Scène 1          │ ├─ Perso.     │
│ avec tags        │                  │ ├─ Lieux      │
│                  │ [Boutons rapides]│ ├─ Objets     │
│ □ Modules        │  - Analyser      │ └─ Timeline   │
│   (Brainstorm,   │  - Continuer     │               │
│   Outline,       │  - Générer       │ □ Version     │
│   etc.)          │  - Critiquer     │   History     │
│                  │                  │               │
└──────────────────┴──────────────────┴───────────────┘
```

### 6.2 États Modulaires

**Option A: Full Interface** (Défaut)
- Tous les panneaux visibles

**Option B: Writer Focus**
- Chat + Éditeur uniquement (masquer KB)

**Option C: Research Mode**
- Chat + KB panel (masquer éditeur)

**Option D: Outline View**
- Module Outline en plein écran

---

## 7. SCENARIOS D'USAGE

### Scénario 1 : Brainstorming d'Arc Narratif
```
1. User clique "Brainstorm" → Modal/Module s'ouvre
2. User décrit situation initiale
3. IA génère 5 directions narratives possibles
4. User explore avec questions supp. → Raffinage
5. Accepte option → Sauvegarde dans historique + KB
```

### Scénario 2 : Vérification de Cohérence
```
1. User rédige dialogue Kaelith
2. Clique "Analyser ce passage"
3. IA compare avec KB :
   - Vérifie traits de caractère cohérents
   - Detects incohérences timeline
   - Suggère améliorations
4. Affiche feedback + propositions
```

### Scénario 3 : Continuation de Scène
```
1. User sélectionne passage incomplet
2. Clique "Continuer cette scène"
3. IA injecte contexte :
   - POV character + sa psychology
   - Scènes précédentes
   - Enjeux narratifs
4. Génère 2-3 continuations
5. User accepte + édite
```

### Scénario 4 : Multi-Projet
```
1. User a 3 romans en cours
2. Clique "Switcher Projet" → dropdown
3. Interface reload avec contexte du nouveau projet
4. KB, historique conversations, manuscrits changent
5. Possible archiver un projet (réutilisable plus tard)
```

---

## 8. CRITÈRES DE SUCCESS

### KPIs
- **Vélocité rédaction** : X% augmentation mots/session
- **Cohérence** : % incohérences détectées vs. laissées passer
- **Retention** : Utilisation quotidienne / engagement
- **Quality** : Score satisfaction utilisateur (auto-critique)

### Métriques Techniques
- Temps réponse IA : < 3s (sur VPS)
- Uptime : 99%
- Taille DB : < 1GB (pour projet moyen)
- Latence chat : < 500ms UI

### Métriques Créatives
- % passages générés acceptés (≥70% cible)
- Nb idées brainstorm explorées/session
- Feedback sur utilité contexte KB (score 1-10)

---

## 9. ROADMAP

### Sprint 1 (Semaines 1-2) : Setup & Core Chat
- [ ] Architecture backend / DB setup
- [ ] Interface chat basique
- [ ] Injection contexte simple (KB + derniers messages)
- [ ] Gestion multi-projet basique

### Sprint 2 (Semaines 3-4) : Knowledge Base
- [ ] Éditeur KB structuré
- [ ] Full-text search
- [ ] Versioning KB
- [ ] Auto-linking personnages/lieux

### Sprint 3 (Semaines 5-6) : Éditeur + Modules
- [ ] Intégration éditeur Markdown
- [ ] Module Brainstorm MVP
- [ ] Module Outline basique
- [ ] Synchronisation chat ↔ éditeur

### Sprint 4 (Semaines 7-8) : Polish + Testing
- [ ] Modules avancés (dialogue, analyse)
- [ ] UI/UX refinement
- [ ] Testing complet
- [ ] Export (Markdown, PDF)

---

## 10. RESSOURCES & DÉPENDANCES

### Tech Debt / Risques
- Performance Ollama sur VPS limité → Monitorer latence
- Gestion mémoire contexte (prompt size limit Mistral)
- Incohérences IA → Besoin validation utilisateur

### Dépendances Externes
- Ollama / Mistral (déjà en place ✓)
- PostgreSQL ou SQLite (choix à faire)
- Bibliotèques : LangChain, FastAPI/Express, React

### Effort Estimé
- **MVP (Core Chat + KB)** : 3-4 semaines (solo dev)
- **V1 (+ Modules + Polish)** : +3-4 semaines
- **V2+ (Collaboration, API, Mobile)** : +6-8 semaines

---

## 11. GLOSSAIRE

| Terme | Définition |
|-------|-----------|
| **KB** | Knowledge Base = univers structuré du roman |
| **Context Injection** | Ajout automatique KB + historique au prompt IA |
| **Versioning** | Historique des changements d'une entité |
| **POV** | Point of View = perspective narrative |
| **Coherence Check** | Vérification incohérences via IA |
| **Brainstorm Mode** | Mode conversation créatif/divergent |

---

## 12. NOTES & CONSIDERATIONS

### Philosophie de Design
- **Local-first** : Tout fonctionne sur VPS (pas dépendance cloud)
- **Flexible UI** : Adaptable au workflow (chat-only, editor-only, etc.)
- **Context is King** : IA aussi bonne que le contexte injecté
- **User in Control** : IA propose, user dispose

### Next Steps
1. ✓ Valider ce PRD avec vous
2. [ ] Affiner DB schema
3. [ ] Prototype interface
4. [ ] Setup infrastructure
5. [ ] Commence développement Sprint 1

---

**Questions / Feedback bienvenu ! 📝**
