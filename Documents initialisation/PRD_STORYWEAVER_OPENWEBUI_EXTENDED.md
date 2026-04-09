# 📖 PRD : StoryWeaver - Extension OpenWebUI pour Rédaction de Roman

**Version:** 1.0 (Build-on-top Strategy)  
**Date:** Avril 2026  
**Base:** OpenWebUI (open-webui/open-webui)  
**Stratégie:** Extension modulaire, custom tools, DB augmentée

---

## 1. VISION & APPROCHE STRATÉGIQUE

### Concept
**Forker OpenWebUI** et ajouter couches spécialisées pour la rédaction de roman :
- ✅ Réutiliser chat conversationnel, gestion modèles, interface base
- ✅ Ajouter KB structurée (univers, perso, lieux, etc.)
- ✅ Implémenter versioning + multi-projet
- ✅ Créer modules spécialisés comme **Custom Tools** OpenWebUI
- ✅ Enrichir système de prompts avec injection contexte

### Philosophie
> "Ne pas réinventer la roue, construire dessus." 
- Keep OpenWebUI's core strength = chat naturel
- Extend with domain-specific features = roman writing
- Modulaire, maintenable, scalable

---

## 2. ARCHITECTURE : OpenWebUI + Couches Additionnelles

### 2.1 Stack OpenWebUI (Existing)
```
Frontend (SvelteKit)
├─ Chat UI (réutilisé as-is)
├─ Model selector
├─ Settings panel
└─ Message history

Backend (Python FastAPI)
├─ Ollama integration
├─ Database (SQLite/PostgreSQL)
├─ User management
└─ API endpoints

LLM Layer
└─ Ollama + Mistral (local)
```

### 2.2 Couches Ajoutées (Custom)

```
┌─────────────────────────────────────────┐
│        STORYWEAVER CUSTOM LAYER         │
├─────────────────────────────────────────┤
│ ├─ KB Manager (univers, personnages)   │
│ ├─ Versioning System (historique)      │
│ ├─ Project Manager (multi-projet)      │
│ ├─ Context Injector (prompts enrichis) │
│ ├─ Custom Tools (brainstorm, outline)  │
│ └─ Manuscript Editor (Markdown sync)   │
├─────────────────────────────────────────┤
│  OpenWebUI Core (Chat, API, Models)    │
├─────────────────────────────────────────┤
│  Ollama + Mistral                      │
└─────────────────────────────────────────┘
```

### 2.3 Base de Données Étendue

```
OpenWebUI Tables (existants):
├─ users
├─ chats
├─ messages
└─ models

StoryWeaver Tables (nouveaux):
├─ novels (projects)
│  ├─ id, user_id, title, description
│  ├─ status (draft, in-progress, completed, archived)
│  ├─ created_at, updated_at
│  └─ metadata (JSON)
│
├─ knowledge_base (KB par novel)
│  ├─ id, novel_id
│  ├─ universe_docs (JSON)
│  ├─ characters (JSON array)
│  ├─ locations (JSON array)
│  ├─ objects (JSON array)
│  └─ updated_at
│
├─ manuscripts (contenu roman)
│  ├─ id, novel_id
│  ├─ content (Markdown)
│  ├─ chapter_structure (JSON)
│  └─ updated_at
│
├─ versions
│  ├─ id, entity_type (character, location, scene, etc.)
│  ├─ entity_id
│  ├─ novel_id
│  ├─ old_data, new_data (JSON)
│  ├─ change_type, timestamp
│  └─ version_number
│
├─ context_snapshots
│  ├─ id, chat_id, novel_id
│  ├─ injected_context (JSON)
│  ├─ timestamp
│  └─ kb_snapshot (JSON)
│
└─ chat_metadata
   ├─ id, chat_id, novel_id
   ├─ tags (#brainstorm, #structure, etc.)
   ├─ linked_entities (characters, scenes)
   └─ context_level (full, minimal, none)
```

---

## 3. CUSTOM TOOLS (Extension Model)

OpenWebUI supporte les **Custom Tools** = fonctions Python injectable. Utiliser ce mécanisme pour :

### 3.1 Tool: Novel Context Injector
```python
# tools/novel_context_injector.py

@tool
def inject_novel_context(chat_id: str, novel_id: str) -> dict:
    """
    Construit contexte enrichi pour le prompt IA.
    Appelé automatiquement avant chaque réponse.
    """
    novel = db.get_novel(novel_id)
    kb = db.get_knowledge_base(novel_id)
    recent_messages = db.get_chat_messages(chat_id, limit=10)
    manuscript = db.get_manuscript(novel_id)
    
    context = {
        "universe": kb.universe_docs,
        "active_characters": kb.characters[:5],  # Top 5
        "recent_scenes": extract_scenes(manuscript),
        "conversation_history": recent_messages,
        "novel_metadata": novel.metadata
    }
    
    return context

# Usage: Ajouter au SYSTEM PROMPT dynamiquement
```

### 3.2 Tool: Brainstorm Generator
```python
# tools/brainstorm.py

@tool
def brainstorm_ideas(novel_id: str, theme: str, count: int = 5) -> list:
    """
    Génère N idées créatives pour un thème donné.
    Utilise contexte du roman.
    """
    kb = db.get_knowledge_base(novel_id)
    novel_rules = kb.universe_docs
    
    prompt = f"""
    Univers du roman: {novel_rules}
    Thème: {theme}
    
    Génère {count} idées créatives pour continuer cette histoire.
    Formats: liste numérotée avec brève description.
    """
    
    response = call_ollama(prompt)
    ideas = parse_response(response)
    
    # Sauvegarde dans historique
    db.save_brainstorm_session(novel_id, ideas)
    
    return ideas
```

### 3.3 Tool: Coherence Checker
```python
# tools/coherence_checker.py

@tool
def check_narrative_coherence(novel_id: str, text: str) -> dict:
    """
    Vérifie incohérences : timeline, personnages, univers.
    """
    kb = db.get_knowledge_base(novel_id)
    manuscript = db.get_manuscript(novel_id)
    
    # Extraire mentions du texte
    mentioned_entities = extract_entities(text)
    
    # Vérifications
    checks = {
        "timeline_conflicts": check_timeline(text, manuscript),
        "character_inconsistencies": check_characters(text, kb.characters),
        "universe_rule_violations": check_universe_rules(text, kb.universe_docs),
        "repeated_names": check_name_duplicates(text, kb)
    }
    
    # Scorer et retourner
    issues = [check for check in checks.values() if check["issues"]]
    
    return {
        "total_issues": len(issues),
        "issues": issues,
        "coherence_score": calculate_score(issues)
    }
```

### 3.4 Tool: Dialogue Generator
```python
# tools/dialogue_generator.py

@tool
def generate_dialogue(novel_id: str, character_ids: list, context: str) -> str:
    """
    Génère dialogue basé sur personnages KB.
    """
    kb = db.get_knowledge_base(novel_id)
    characters = [kb.characters[cid] for cid in character_ids]
    
    char_description = format_character_profiles(characters)
    
    prompt = f"""
    Personnages:
    {char_description}
    
    Contexte de la scène:
    {context}
    
    Génère un dialogue naturel entre ces personnages.
    Format: 
    > Character_Name: "dialogue"
    """
    
    response = call_ollama(prompt)
    return response
```

### 3.5 Tool: Outline Generator
```python
# tools/outline_generator.py

@tool
def generate_outline(novel_id: str, structure: str = "three-act") -> dict:
    """
    Génère outline narrative (3-act, 5-act, etc.)
    """
    kb = db.get_knowledge_base(novel_id)
    
    outline_templates = {
        "three-act": TEMPLATE_3_ACT,
        "five-act": TEMPLATE_5_ACT,
        "seven-point": TEMPLATE_7_POINT
    }
    
    prompt = f"""
    Univers: {kb.universe_docs}
    Personnages: {format_characters(kb.characters)}
    
    Crée un outline {structure} pour ce roman.
    Format: chapitres avec clés narratives.
    """
    
    response = call_ollama(prompt)
    outline = parse_outline(response)
    
    # Sauvegarde
    db.save_outline(novel_id, outline, structure)
    
    return outline
```

---

## 4. INTÉGRATION AVEC OPENWEBUI

### 4.1 Modification Minimale Core

```
openwbui/
├─ backend/
│  ├─ routes/ (modifier pour multi-project)
│  │  └─ chat.py (ajouter novel_id param)
│  ├─ database/
│  │  ├─ models.py (ajouter Novel, KB, Version models)
│  │  └─ migrations/ (migrations pour new tables)
│  └─ dependencies/
│     └─ context_injector.py (nouveau)
│
├─ tools/ (NOUVEAU DOSSIER)
│  ├─ __init__.py
│  ├─ novel_context_injector.py
│  ├─ brainstorm.py
│  ├─ coherence_checker.py
│  ├─ dialogue_generator.py
│  └─ outline_generator.py
│
└─ frontend/
   └─ lib/components/ (ajouter Novel Manager UI)
```

### 4.2 Flow Modifié : Chat avec Novel Context

```
User Message (Chat)
    ↓
[Novel Selector] ← Nouveau
├─ Récupère novel_id de la session
├─ Charge KB du novel
└─ Prépare context snapshot
    ↓
[Context Injection] ← Nouveau (via tool)
├─ Appelle inject_novel_context()
├─ Construit SYSTEM PROMPT enrichi
└─ Ajoute contexte au request Ollama
    ↓
[Ollama + Mistral] (Existant)
    ↓
[Response + Versioning] ← Nouveau
├─ Sauvegarde message
├─ Crée version snapshot
└─ Retourne réponse
```

### 4.3 Prompt System Dynamique

```python
# backend/utils/prompt_builder.py

def build_system_prompt(novel_id: str, chat_id: str) -> str:
    """
    Construit SYSTEM PROMPT enrichi avec contexte novel.
    """
    kb = db.get_knowledge_base(novel_id)
    novel = db.get_novel(novel_id)
    manuscript = db.get_manuscript(novel_id)
    recent_messages = db.get_chat_messages(chat_id, limit=8)
    
    base_prompt = """
    Vous êtes un assistant créatif spécialisé dans l'écriture de roman.
    Vous avez accès au contexte complet du projet en cours.
    """
    
    # Ajouter contexte dynamiquement
    universe_prompt = format_universe_context(kb.universe_docs)
    characters_prompt = format_characters_context(kb.characters)
    scenes_prompt = format_recent_scenes(manuscript)
    history_prompt = format_conversation_history(recent_messages)
    
    full_prompt = f"""
    {base_prompt}
    
    ### UNIVERS DU ROMAN
    {universe_prompt}
    
    ### PERSONNAGES CLÉS
    {characters_prompt}
    
    ### SCÈNES RÉCENTES
    {scenes_prompt}
    
    ### HISTORIQUE CONVERSATION
    {history_prompt}
    
    ### DIRECTIVES
    - Maintenez la cohérence narrative
    - Référencez la KB quand pertinent
    - Signalez les incohérences détectées
    - Proposez des alternatives créatives
    """
    
    return full_prompt
```

---

## 5. NOUVELLES FEATURES

### 5.1 Novel Manager (UI OpenWebUI)

```
Interface:
└─ Sidebar: "Projects" section
   ├─ Bouton "+ New Novel"
   ├─ Liste des novels actuels
   │  ├─ Novel Title
   │  ├─ Status badge (draft, in-progress, etc.)
   │  ├─ Last modified
   │  └─ Actions (Open, Rename, Archive, Delete)
   └─ Archived Novels (collapse)

Modal: Create New Novel
├─ Title input
├─ Description textarea
├─ Template selector (Fantasy, Sci-Fi, Romance, etc.)
└─ Create button
```

### 5.2 Knowledge Base Editor (Modal/Panel)

```
UI:
└─ Tab bar: Universe | Characters | Locations | Objects | Timeline
   └─ Universe Tab:
      ├─ Rich text editor (ou JSON)
      ├─ Add/Edit rules
      ├─ Version history button
      └─ Save button
      
   └─ Characters Tab:
      ├─ Character list (searchable)
      ├─ Character form:
      │  ├─ Name, Age, Appearance
      │  ├─ Personality traits
      │  ├─ Relationships (multi-select)
      │  ├─ Arc narratif
      │  └─ Save
      ├─ Version history per character
      └─ Add new character button
      
   └─ Timeline Tab:
      ├─ Visual timeline (ou liste)
      ├─ Add event
      ├─ Link to characters/locations
      └─ Sort chronologically
```

### 5.3 Manuscript Editor (Panel ou Modal)

```
UI:
└─ Editor Panel:
   ├─ Chapter selector (dropdown)
   ├─ Scene list (left sidebar)
   ├─ Markdown editor (main)
   │  ├─ Syntax highlighting
   │  ├─ Word count
   │  ├─ Status selector (draft, editing, final)
   │  └─ Auto-save
   ├─ Quick action buttons:
   │  ├─ "Analyze Passage"
   │  ├─ "Continue Scene"
   │  ├─ "Generate Dialogue"
   │  └─ "Check Coherence"
   └─ Preview pane (toggle)
```

### 5.4 Tools/Modules Access

```
UI: Depuis chat OpenWebUI
└─ Boutons/Commands:
   ├─ /brainstorm - Lance brainstorm generator
   ├─ /outline - Génère outline
   ├─ /dialogue - Génère dialogue
   ├─ /analyze - Coherence check
   └─ /research - Search KB

Alternative: Toolbar en haut du chat avec icônes
```

---

## 6. IMPLÉMENTATION PRATIQUE

### 6.1 Steps pour Fork & Customiser

```
1. Fork open-webui/open-webui sur GitHub

2. Clone local:
   git clone https://github.com/YOUR_USERNAME/open-webui.git
   cd open-webui

3. Créer branch feature:
   git checkout -b feature/storyweaver-core

4. Setup environnement:
   poetry install (ou pip install -r requirements.txt)
   npm install (frontend)

5. Ajouter migrations DB:
   alembic revision --autogenerate -m "Add novel, kb, versions tables"
   alembic upgrade head

6. Implémenter tools (tools/*.py)

7. Modifier chat routes (backend/routes/chat.py)

8. Ajouter composants UI (frontend/src/lib/components/)

9. Test local:
   poetry run python main.py
   npm run dev

10. Deploy sur VPS (docker ou standard)
```

### 6.2 Dépendances Supplémentaires

```
Python:
├─ SQLAlchemy (ORM) - probablement déjà présent
├─ Pydantic (validation) - probablement déjà présent
├─ python-dateutil (versioning timestamps)
└─ markdown2 (parsing Markdown)

Frontend (Svelte):
├─ marked (Markdown parsing)
├─ highlight.js (syntax highlighting)
├─ svelte-icons (UI icons)
└─ date-fns (date formatting)
```

### 6.3 Configuration/Environment

```
.env additions:
├─ STORYWEAVER_ENABLED=true
├─ KB_MAX_SIZE=10000 (characters)
├─ VERSION_HISTORY_RETENTION=100 (versions to keep)
├─ AUTO_CONTEXT_INJECTION=true
└─ CONTEXT_WINDOW_SIZE=4000 (tokens for injected context)
```

---

## 7. ROADMAP D'IMPLÉMENTATION

### Phase 1 : Core Infrastructure (Weeks 1-2)
- [ ] Fork OpenWebUI
- [ ] DB migrations (Novel, KB, Version tables)
- [ ] Novel Manager (create, list, switch)
- [ ] Basic context injection
- [ ] Tool: novel_context_injector

### Phase 2 : Knowledge Base (Weeks 3-4)
- [ ] KB Editor UI (characters, universe, locations)
- [ ] KB storage in DB
- [ ] Versioning system
- [ ] Search/query KB

### Phase 3 : Tools & Modules (Weeks 5-6)
- [ ] Tool: brainstorm_generator
- [ ] Tool: coherence_checker
- [ ] Tool: dialogue_generator
- [ ] Tool: outline_generator
- [ ] Tools integration with chat UI

### Phase 4 : Polish & Testing (Weeks 7-8)
- [ ] Manuscript editor integration
- [ ] UI/UX refinement
- [ ] Testing (unit + integration)
- [ ] Documentation
- [ ] Deploy to VPS

---

## 8. ARCHITECTURE DÉCISIONS

### Decision 1: Où ajouter la KB au prompt?
- ✅ **SYSTEM PROMPT dynamique** (recommandé)
  - Context injecté avant chaque réponse
  - Flexible, facile à ajuster
  - Consomme tokens du context window

- ❌ In-context examples
  - Moins flexible
  - Consomme plus de tokens

### Decision 2: Storage des versions
- ✅ **Full snapshots** (recommandé pour MVP)
  - Simpler, rapide à implémenter
  - Consomme plus de space DB
  - Facile à comparer/reverter

- ❌ Diffs/patches
  - Optimal storage-wise
  - Plus complexe à gérer

### Decision 3: Multi-projet dans chat
- ✅ **Session-level novel selection**
  - Sélectionner novel une fois
  - Tous les messages de cette session = contexte ce novel
  - Switcher = nouvelle session

- ❌ Per-message novel selection
  - Plus flexible mais confus pour utilisateur

---

## 9. SUCCESS CRITERIA

### Functional
- Chat fonctionne avec contexte novel injecté ✓
- KB éditable et persistante ✓
- Versioning capture changes ✓
- Multi-project switch seamless ✓
- Tools (brainstorm, analyze, etc.) retournent résultats pertinents ✓

### Performance
- Context injection < 500ms ✓
- Ollama response < 3s (dépend VPS) ✓
- DB queries < 100ms ✓
- UI remain responsive ✓

### UX
- Zero friction pour switcher projects ✓
- KB editor intuitive ✓
- Tools accessible en 1 click ✓
- Novel context visible/navigable ✓

---

## 10. RISQUES & MITIGATION

| Risque | Mitigation |
|--------|-----------|
| **Context window overflow** | Sélectionner top-K personnages/scènes plutôt que tous |
| **Ollama latency** | Monitorer, utiliser queue si needed |
| **DB migration complexity** | Test migrations thoroughly, backup before deploy |
| **UI/Backend mismatch** | Clear API contracts, API documentation |
| **Incohérences IA** | User remains final validator, suggest édits not replacements |

---

## 11. FICHIERS À MODIFIER/CRÉER

### Créer (nouveaux)
```
tools/
├─ __init__.py
├─ novel_context_injector.py
├─ brainstorm.py
├─ coherence_checker.py
├─ dialogue_generator.py
└─ outline_generator.py

frontend/src/lib/components/
├─ NovelManager.svelte
├─ KnowledgeBaseEditor.svelte
├─ ManuscriptEditor.svelte
└─ ToolsPanel.svelte

backend/database/migrations/
└─ versions/
   └─ 2024_04_storyweaver_initial.py
```

### Modifier (existants OpenWebUI)
```
backend/
├─ main.py (ajouter tools routes)
├─ routes/chat.py (novel_id parameter, context injection)
├─ database/models.py (ajouter Novel, KB, Version models)
└─ dependencies/__init__.py (ajouter context_injector)

frontend/
├─ src/App.svelte (ajouter Novel selector)
└─ src/routes/chat/+page.svelte (ajouter Tools toolbar)
```

---

## 12. NEXT STEPS CONCRETS

1. **✓ Valider cette approche** → PRD revisité
2. **[ ] Créer fork private** sur GitHub
3. **[ ] Setup local dev environment** (clone, poetry install, npm install)
4. **[ ] Implémenter Phase 1** (infrastructure core)
5. **[ ] Daily progress** (sprints de 2 semaines)

---

## ANNEXE : OpenWebUI Architecture Overview

OpenWebUI c'est:
- **Frontend:** SvelteKit (reactive, fast)
- **Backend:** Python FastAPI (async, extensible)
- **Database:** SQLite (default) ou PostgreSQL (production)
- **LLM Integration:** Via Ollama API calls
- **Extensibility:** 
  - Tools (functions callable from chat)
  - Plugins (UI extensions)
  - Custom routes

**Avantage:** Architecture déjà pensée pour extensibility. On va juste ajouter nos features en suivant ses patterns.

---

## CONCLUSION

**StoryWeaver = OpenWebUI + Domain-Specific Features**

✅ Pragmatique (réutilise bon code)  
✅ Maintenable (suit OpenWebUI patterns)  
✅ Scalable (couches isolées)  
✅ Rapide à implémenter (~4-8 semaines)  

**Prêt à commencer l'implémentation Phase 1 ?** 🚀
