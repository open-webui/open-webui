# 🏗️ STORYWEAVER : Architecture Diagrams

---

## 1. ARCHITECTURE SYSTÈME GLOBAL

### 1.1 Vue d'Ensemble : 4 Couches

```
┌──────────────────────────────────────────────────────────────────┐
│                        CLIENT BROWSER                             │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │                   FRONTEND (Svelte/SvelteKit)              │  │
│  │ ┌──────────┐ ┌─────────────┐ ┌─────────────┐ ┌──────────┐ │  │
│  │ │   Chat   │ │  Manuscript │ │     KB      │ │  Tools   │ │  │
│  │ │   UI     │ │   Editor    │ │   Panel     │ │ Toolbar  │ │  │
│  │ └──────────┘ └─────────────┘ └─────────────┘ └──────────┘ │  │
│  └────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
                              ▲
                              │ HTTP/WS
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│                    API LAYER (FastAPI)                            │
│ ┌────────────────┐ ┌─────────────┐ ┌──────────┐ ┌────────────┐  │
│ │ Routes:        │ │ Routes:     │ │ Routes:  │ │ Routes:    │  │
│ │ • /novels      │ │ • /kb/*     │ │ • /chat/ │ │ • /tools/* │  │
│ │ • /select      │ │ • /search   │ │ • /comp. │ │ • /brain.. │  │
│ │ • /archive     │ │ • /versions │ │          │ │ • /outline │  │
│ └────────────────┘ └─────────────┘ └──────────┘ └────────────┘  │
│                                                                    │
│ ┌──────────────────────────────────────────────────────────────┐ │
│ │         BUSINESS LOGIC LAYER                                 │ │
│ │ ┌──────────────────────────────────────────────────────────┐ │ │
│ │ │  • Prompt Builder (context injection)                    │ │ │
│ │ │  • Versioning Logic (create snapshots)                   │ │ │
│ │ │  • Search & Filter (KB queries)                          │ │ │
│ │ │  • Tool Orchestration (call LLM with context)            │ │ │
│ │ └──────────────────────────────────────────────────────────┘ │ │
│ │                                                                │ │
│ │ ┌──────────────────────────────────────────────────────────┐ │ │
│ │ │  DATA ACCESS LAYER (DAOs)                                │ │ │
│ │ │ • NovelDAO        • ManuscriptDAO                         │ │ │
│ │ │ • KnowledgeBaseDAO • VersionDAO                           │ │ │
│ │ │ • ConversationDAO  • ContextSnapshotDAO                   │ │ │
│ │ └──────────────────────────────────────────────────────────┘ │ │
│ └──────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
                              ▲
                              │ SQL
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│              DATABASE LAYER (PostgreSQL/SQLite)                   │
│ ┌──────────────────────────────────────────────────────────────┐ │
│ │  OpenWebUI Tables:                    StoryWeaver Tables:   │ │
│ │  • users              • messages       • novels              │ │
│ │  • chats              • models         • knowledge_bases     │ │
│ │                       • sessions       • manuscripts          │ │
│ │                                        • versions             │ │
│ │                                        • context_snapshots    │ │
│ │                                        • chat_metadata        │ │
│ └──────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
                              ▲
                              │ REST API
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│                   EXTERNAL SERVICES                               │
│ ┌────────────────────────┐      ┌──────────────────────────────┐ │
│ │   OLLAMA (Local LLM)   │      │   Mistral Model              │ │
│ │   http://localhost:    │      │   (Running in Ollama)        │ │
│ │   11434                │      │                              │ │
│ │                        │      │   • Processes prompts        │ │
│ │   • Hosts models       │      │   • Returns completions      │ │
│ │   • Manages context    │      │   • Streaming capable        │ │
│ └────────────────────────┘      └──────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
```

---

## 2. DATABASE SCHEMA DIAGRAM

### 2.1 Entities & Relationships

```
┌────────────────────┐
│   users (OpenWebUI)│
├────────────────────┤
│ id (PK)            │
│ username           │
│ current_novel_id◄──┼──────────────────┐
│ created_at         │                  │ FK
└────────────────────┘                  │
                                        │
┌────────────────────┐                  │
│   novels           │◄─────────────────┘
├────────────────────┤
│ id (PK)            │
│ user_id (FK)───────┼────┐
│ title              │    │
│ description        │    │
│ status             │    │
│ created_at         │    │
│ updated_at         │    │
└────────────────────┘    │
        │                 │
        │ 1:1             │ User has many Novels
        │                 │
        ├─────────────────┴─────────────────┐
        │                                   │
        ▼                                   │
┌────────────────────────────┐             │
│   knowledge_bases          │             │
├────────────────────────────┤             │
│ id (PK)                    │             │
│ novel_id (FK)◄─────────────┘             │
│ universe_docs (JSON)                     │
│ characters (JSON[])                      │
│ locations (JSON[])                       │
│ objects (JSON[])                         │
│ updated_at                               │
└────────────────────────────┘

        ▼ (1:1)

┌────────────────────────────┐
│   manuscripts              │
├────────────────────────────┤
│ id (PK)                    │
│ novel_id (FK)◄─────────────┘
│ content (TEXT)                          
│ chapter_structure (JSON)
│ word_count                 
│ updated_at                 
└────────────────────────────┘

        ▼ (1:N)
        
┌────────────────────────────┐
│   versions                 │
├────────────────────────────┤
│ id (PK)                    │
│ novel_id (FK)◄─────────────┘
│ entity_type (STR)          
│  ├─ "character"            
│  ├─ "location"             
│  ├─ "kb_universe"          
│  └─ "scene"                
│ entity_id (STR)            
│ old_data (JSON)            
│ new_data (JSON)            
│ change_type (STR)          
│  ├─ "created"              
│  ├─ "updated"              
│  ├─ "deleted"              
│  └─ "reverted"             
│ version_number (INT)       
│ timestamp (DATETIME)       
│ change_description (STR)   
└────────────────────────────┘

        ▼ (1:N)

┌────────────────────────────┐
│   chats (OpenWebUI)        │
├────────────────────────────┤
│ id (PK)                    │
│ user_id (FK)               │
│ created_at                 │
└────────────────────────────┘
        │
        │ (1:N)
        ▼
┌────────────────────────────┐
│   messages (OpenWebUI)     │
├────────────────────────────┤
│ id (PK)                    │
│ chat_id (FK)               │
│ role (STR: user/assistant) │
│ content (TEXT)             │
│ created_at                 │
└────────────────────────────┘
        │
        │ (via chat_id)
        ▼
┌────────────────────────────┐
│   chat_metadata            │
├────────────────────────────┤
│ id (PK)                    │
│ chat_id (FK)               │
│ novel_id (FK◄──────┐       │
│ tags (JSON[])      │       │
│ context_level      │       │
│ linked_entities    │       │
│ (JSON)             │       │
└────────────────────┴───────┘
                              
        ▼ (1:N via novel_id)
┌────────────────────────────┐
│   context_snapshots        │
├────────────────────────────┤
│ id (PK)                    │
│ chat_id (FK)               │
│ novel_id (FK)              │
│ injected_context (JSON)    │
│ kb_snapshot (JSON)         │
│ timestamp                  │
└────────────────────────────┘
```

### 2.2 JSON Structures

```json
// Knowledge Base - Universe Section
{
  "universe_docs": {
    "magic_system": "Description of how magic works...",
    "world_rules": "Physics, geography, technology level...",
    "history": "Timeline of major events...",
    "factions": "Groups, organizations, politics..."
  }
}

// Knowledge Base - Character
{
  "id": "char_001",
  "name": "Kaelith",
  "age": 27,
  "role": "protagonist",
  "appearance": "cheveux noirs, yeux gris, cicatrice joue gauche",
  "personality": ["ambitieuse", "impulsive", "loyal"],
  "arc_narrative": "Découverte de ses pouvoirs magiques",
  "motivations": ["venger sa famille", "trouver sa place"],
  "relationships": [
    {
      "character_id": "char_002",
      "type": "ally",
      "tension": "moderate"
    }
  ],
  "scenes": ["scene_034", "scene_067"],
  "status": "alive"
}

// Version Record
{
  "entity_type": "character",
  "entity_id": "char_001",
  "old_data": { "name": "Kaeli", "age": 26 },
  "new_data": { "name": "Kaelith", "age": 27 },
  "change_type": "updated",
  "version_number": 3,
  "timestamp": "2024-04-06T10:30:00Z",
  "change_description": "Updated name spelling and age after Chapter 5 rewrite"
}

// Context Snapshot
{
  "injected_context": {
    "universe": { /* full universe_docs */ },
    "active_characters": [ /* top 5 chars */ ],
    "recent_scenes": "Last 500 lines of manuscript",
    "conversation_history": [ /* last 8 messages */ ]
  },
  "kb_snapshot": { /* full KB state at this moment */ },
  "timestamp": "2024-04-06T10:35:15Z"
}
```

---

## 3. CHAT FLOW WITH CONTEXT INJECTION

### 3.1 Complete Chat Request Flow

```
USER TYPES MESSAGE IN CHAT
         │
         ▼
┌──────────────────────────────────────┐
│  Frontend: ChatUI.svelte              │
│  ├─ Captures user input               │
│  ├─ Validates message not empty       │
│  └─ Sends via POST /api/chat/         │
└──────────────────────────────────────┘
                 │
                 │ HTTP POST
                 ▼
┌──────────────────────────────────────┐
│  Backend: routes/chat.py              │
│  ├─ Authenticate user                 │
│  ├─ Get current_user.current_novel_id │
│  └─ If no novel selected:             │
│     └─ Route to normal OpenWebUI chat │
│     (no context injection)             │
└──────────────────────────────────────┘
         │
         │ novel_id available
         ▼
┌──────────────────────────────────────┐
│  Backend: utils/prompt_builder.py     │
│  ┌────────────────────────────────────┤
│  │ CONTEXT ASSEMBLY PHASE              │
│  │                                     │
│  │ 1. Load Novel Metadata              │
│  │    └─ SELECT * FROM novels          │
│  │       WHERE id = novel_id           │
│  │                                     │
│  │ 2. Load Knowledge Base              │
│  │    └─ SELECT * FROM knowledge_bases │
│  │       WHERE novel_id = ?            │
│  │                                     │
│  │ 3. Load Manuscript (recent)         │
│  │    └─ SELECT content FROM           │
│  │       manuscripts                   │
│  │       WHERE novel_id = ?            │
│  │    └─ Extract last 500 lines        │
│  │                                     │
│  │ 4. Load Chat History                │
│  │    └─ SELECT * FROM messages        │
│  │       WHERE chat_id = ?             │
│  │       ORDER BY created DESC         │
│  │       LIMIT 10                      │
│  │    └─ Convert to format:            │
│  │       [{"role": "user", ...}, ...]  │
│  │                                     │
│  │ 5. Format & Truncate                │
│  │    ├─ Universe text (truncate)      │
│  │    ├─ Top 5 characters (by mention) │
│  │    └─ Recent scenes (last 500 chars)│
│  │                                     │
│  │ 6. Build System Prompt              │
│  │    └─ BASE_PROMPT                   │
│  │       + ### UNIVERSE SECTION        │
│  │       + ### CHARACTERS SECTION      │
│  │       + ### RECENT SCENES           │
│  │       + ### CHAT HISTORY            │
│  │                                     │
│  └────────────────────────────────────┘
│
│ Returns: injected_system_prompt (String)
└──────────────────────────────────────┘
                 │
                 ▼
┌──────────────────────────────────────┐
│  Backend: routes/chat.py (continued)  │
│  ┌────────────────────────────────────┤
│  │ REQUEST MODIFICATION                │
│  │                                     │
│  │ Original request messages:          │
│  │ [                                   │
│  │   {"role": "user", "content": "..."} │
│  │ ]                                   │
│  │                                     │
│  │ Modified request messages:          │
│  │ [                                   │
│  │   {                                 │
│  │     "role": "system",               │
│  │     "content": injected_prompt      │
│  │   },                                │
│  │   {"role": "user", "content": "..."} │
│  │ ]                                   │
│  │                                     │
│  └────────────────────────────────────┘
└──────────────────────────────────────┘
                 │
                 ▼
┌──────────────────────────────────────┐
│  Backend → Ollama API                │
│  POST http://localhost:11434/api/    │
│  ├─ model: "mistral"                 │
│  ├─ messages: [system + user input]  │
│  ├─ temperature: 0.7                 │
│  └─ stream: true                     │
└──────────────────────────────────────┘
                 │
                 │ (streaming tokens)
                 ▼
┌──────────────────────────────────────┐
│  Ollama + Mistral Model              │
│  ├─ Process system prompt with context│
│  ├─ Process user message              │
│  ├─ Generate response token by token │
│  └─ Stream back via HTTP             │
└──────────────────────────────────────┘
                 │
                 │ (response tokens)
                 ▼
┌──────────────────────────────────────┐
│  Backend: routes/chat.py (response)  │
│  ├─ Collect streamed response        │
│  ├─ Save message to DB:              │
│  │  INSERT INTO messages (...)       │
│  ├─ Create version snapshot:         │
│  │  INSERT INTO context_snapshots(...)│
│  └─ Stream response to frontend      │
└──────────────────────────────────────┘
                 │
                 │ HTTP streaming
                 ▼
┌──────────────────────────────────────┐
│  Frontend: ChatUI.svelte              │
│  ├─ Display assistant message        │
│  ├─ Scroll to latest message         │
│  ├─ Show loading indicator done      │
│  └─ Ready for next message           │
└──────────────────────────────────────┘
```

---

## 4. CONTEXT INJECTION DETAILED

### 4.1 Prompt Builder Algorithm

```
┌─────────────────────────────────────┐
│ build_full_prompt(novel_id, db)     │
└─────────────────────────────────────┘
         │
         ▼
    ┌─────────────────┐
    │ Start with BASE │
    │ SYSTEM PROMPT   │
    └─────────────────┘
    "You are an AI assistant..."
         │
         ▼
    ┌─────────────────────────────────────────────┐
    │ Is context_level == "none" ?                │
    │ if YES → Return BASE_PROMPT only            │
    │ if NO → Continue                            │
    └─────────────────────────────────────────────┘
         │
         ▼ (context_level = "minimal" or "full")
    ┌─────────────────────────────────────────────┐
    │ LOAD UNIVERSE DOCS                          │
    │ SELECT universe_docs FROM knowledge_bases   │
    │ WHERE novel_id = ?                          │
    │                                             │
    │ Format for display:                         │
    │ ###┃ UNIVERS DU ROMAN                       │
    │ **Magic System:**                           │
    │ {universe_docs["magic_system"]}             │
    │ **World Rules:**                            │
    │ {universe_docs["world_rules"]}              │
    │ ...                                         │
    └─────────────────────────────────────────────┘
         │
         ▼
    ┌─────────────────────────────────────────────┐
    │ LOAD TOP 5 CHARACTERS                       │
    │ SELECT characters FROM knowledge_bases      │
    │ WHERE novel_id = ?                          │
    │                                             │
    │ FOR EACH character (limit 5):               │
    │ ├─ Name, Age, Role                          │
    │ ├─ Personality traits (comma-separated)     │
    │ ├─ Arc narrative                            │
    │ └─ Relationships (refs to other chars)      │
    │                                             │
    │ ### PERSONNAGES CLÉS                        │
    │ **{char.name}** (ID: {char.id})             │
    │ - Rôle: {char.role}                         │
    │ - Traits: {', '.join(char.personality)}     │
    │ - Arc: {char.arc_narrative}                 │
    │ - Relations: {', '.join(relations)}         │
    └─────────────────────────────────────────────┘
         │
         ▼ (if context_level == "full" only)
    ┌─────────────────────────────────────────────┐
    │ LOAD RECENT MANUSCRIPT PASSAGES             │
    │ SELECT content FROM manuscripts             │
    │ WHERE novel_id = ?                          │
    │                                             │
    │ Extract last 500 characters of content      │
    │                                             │
    │ ### PASSAGES RÉCENTS DU MANUSCRIT           │
    │ [Recent 500 chars shown here]               │
    └─────────────────────────────────────────────┘
         │
         ▼ (if context_level == "full" only)
    ┌─────────────────────────────────────────────┐
    │ LOAD CONVERSATION HISTORY                   │
    │ SELECT * FROM messages                      │
    │ WHERE chat_id = ?                           │
    │ ORDER BY created_at DESC                    │
    │ LIMIT 8                                     │
    │                                             │
    │ FOR EACH message (in chronological order):  │
    │ {message.role}: {message.content[:200]}     │
    │                                             │
    │ ### HISTORIQUE CONVERSATION                 │
    │ **user:** "Question about magic?"           │
    │ **assistant:** "Magic in this world..."     │
    │ ...                                         │
    └─────────────────────────────────────────────┘
         │
         ▼
    ┌─────────────────────────────────────────────┐
    │ COMBINE ALL SECTIONS                        │
    │                                             │
    │ final_prompt = [                            │
    │   BASE_SYSTEM_PROMPT,                       │
    │   UNIVERSE_SECTION,                         │
    │   CHARACTERS_SECTION,                       │
    │   RECENT_SCENES_SECTION,    (if full)       │
    │   CONVERSATION_HISTORY      (if full)       │
    │ ].join("\n\n")                              │
    │                                             │
    └─────────────────────────────────────────────┘
         │
         ▼
    ┌─────────────────────────────────────────────┐
    │ SAVE CONTEXT SNAPSHOT                       │
    │ INSERT INTO context_snapshots               │
    │ ├─ chat_id                                  │
    │ ├─ novel_id                                 │
    │ ├─ injected_context (JSON of prompt parts)  │
    │ ├─ kb_snapshot (full KB state)              │
    │ └─ timestamp                                │
    │                                             │
    └─────────────────────────────────────────────┘
         │
         ▼
    RETURN final_prompt (String)
```

---

## 5. KNOWLEDGE BASE EDITING FLOW

### 5.1 Character Editor Complete Flow

```
USER CLICKS "EDIT CHARACTER" / "ADD CHARACTER"
         │
         ▼
    ┌──────────────────────────┐
    │ Frontend: CharacterEditor │
    │ ├─ Modal opens           │
    │ ├─ Load existing char    │
    │ │ (if editing)           │
    │ └─ Show form with fields:│
    │   ├─ Name                │
    │   ├─ Age                 │
    │   ├─ Appearance          │
    │   ├─ Personality         │
    │   ├─ Arc narrative       │
    │   ├─ Relationships       │
    │   │ (multi-select other) │
    │   └─ Status              │
    └──────────────────────────┘
         │
         │ User fills form & clicks SAVE
         ▼
    ┌──────────────────────────────────────┐
    │ Frontend: Validation                 │
    │ ├─ Name not empty ✓                  │
    │ ├─ Age is valid integer ✓            │
    │ ├─ Personality is array ✓            │
    │ └─ No validation errors → proceed    │
    └──────────────────────────────────────┘
         │
         ▼ POST /api/novels/{id}/kb/characters
    ┌──────────────────────────────────────┐
    │ Backend: API Route                   │
    │ ├─ Authenticate user                 │
    │ ├─ Verify ownership of novel         │
    │ └─ Load current KB                   │
    │   SELECT * FROM knowledge_bases      │
    │   WHERE novel_id = ?                 │
    └──────────────────────────────────────┘
         │
         ▼
    ┌──────────────────────────────────────┐
    │ Backend: Is CREATE or UPDATE?        │
    │ ├─ CREATE (new ID):                  │
    │ │  └─ Character doesn't exist in KB  │
    │ └─ UPDATE (existing ID):             │
    │    └─ Find old_character in KB       │
    │       characters array               │
    └──────────────────────────────────────┘
         │
         ├─ CREATE BRANCH        │       UPDATE BRANCH
         │                       │
         ▼                       ▼
    ┌──────────────┐    ┌──────────────────┐
    │ old_data =   │    │ old_character = │
    │ {}           │    │ kb.characters    │
    │              │    │ [find by ID]     │
    │ change_type =│    │                  │
    │ "created"    │    │ change_type =    │
    │              │    │ "updated"        │
    └──────────────┘    │                  │
    │                   │ old_data =       │
    │                   │ old_character    │
    │                   └──────────────────┘
    │                       │
    └───────────┬───────────┘
                │
                ▼
    ┌──────────────────────────────────────┐
    │ Backend: CREATE VERSION RECORD       │
    │ INSERT INTO versions                 │
    │ ├─ entity_type = "character"         │
    │ ├─ entity_id = character.id          │
    │ ├─ novel_id = novel_id               │
    │ ├─ old_data = old_character          │
    │ ├─ new_data = character (from form)  │
    │ ├─ change_type = "created"/"updated" │
    │ ├─ version_number = auto-increment   │
    │ └─ timestamp = NOW()                 │
    └──────────────────────────────────────┘
         │
         ▼
    ┌──────────────────────────────────────┐
    │ Backend: UPDATE KB IN DATABASE       │
    │ ├─ If CREATE:                        │
    │ │  └─ Append to characters array:    │
    │ │     kb.characters.push(character)  │
    │ ├─ If UPDATE:                        │
    │ │  └─ Replace in array:              │
    │ │     kb.characters = [new if        │
    │ │     c.id==id, else c               │
    │ │     for c in kb.characters]        │
    │ ├─ UPDATE knowledge_bases            │
    │ │  SET characters = ?                │
    │ │  WHERE novel_id = ?                │
    │ └─ Set updated_at = NOW()            │
    └──────────────────────────────────────┘
         │
         ▼
    ┌──────────────────────────────────────┐
    │ Backend: RESPONSE                    │
    │ ├─ Return updated KB object          │
    │ └─ Include version_number created    │
    └──────────────────────────────────────┘
         │
         ▼ JSON response
    ┌──────────────────────────────────────┐
    │ Frontend: UI Update                  │
    │ ├─ Close modal                       │
    │ ├─ Update characters list display    │
    │ ├─ Show toast: "Character saved ✓"   │
    │ ├─ Disable "Unsaved Changes" button  │
    │ └─ Update local character in store   │
    └──────────────────────────────────────┘
```

### 5.2 Version History & Revert Flow

```
USER CLICKS "VERSION HISTORY" on Character
         │
         ▼
    ┌──────────────────────────────────────┐
    │ Frontend: VersionHistory Modal       │
    │ GET /api/novels/{id}/versions/{cid}  │
    └──────────────────────────────────────┘
         │
         ▼
    ┌──────────────────────────────────────┐
    │ Backend: VersionDAO.get_history()    │
    │ SELECT * FROM versions               │
    │ WHERE entity_id = ?                  │
    │ ORDER BY version_number DESC         │
    │ LIMIT 50                             │
    │                                      │
    │ Returns: List[Version]               │
    │ ├─ Version 1: created               │
    │ ├─ Version 2: updated (age)         │
    │ ├─ Version 3: updated (personality)│
    │ └─ ...                              │
    └──────────────────────────────────────┘
         │
         ▼
    ┌──────────────────────────────────────┐
    │ Frontend: Display Timeline           │
    │ FOR EACH version:                    │
    │ ├─ Timestamp                         │
    │ ├─ Change type (created/updated/...)│
    │ ├─ [View] button                     │
    │ ├─ [Compare] button                  │
    │ └─ [Revert] button (if not current)  │
    └──────────────────────────────────────┘
         │
         │ User clicks [View]
         ▼
    ┌──────────────────────────────────────┐
    │ Frontend: Show Diff                  │
    │ ├─ old_data                          │
    │ ├─ new_data                          │
    │ ├─ Highlight differences             │
    │ └─ Side-by-side or inline view      │
    └──────────────────────────────────────┘
         │
         │ User clicks [Revert to this]
         ▼
    ┌──────────────────────────────────────┐
    │ Frontend: Confirmation Dialog        │
    │ "Revert to version X?"               │
    │ [Cancel] [Confirm Revert]            │
    └──────────────────────────────────────┘
         │ User clicks [Confirm]
         ▼
    POST /api/novels/{id}/versions/{cid}/{vnum}/revert
         │
         ▼
    ┌──────────────────────────────────────┐
    │ Backend: Revert Logic                │
    │ ├─ GET target version by entity_id   │
    │ │  & version_number                  │
    │ ├─ Load current KB                   │
    │ ├─ Find character in KB              │
    │ │  current_data = old_char           │
    │ ├─ Set character to old_data         │
    │ └─ new_data = version.old_data       │
    │    (because we're reverting)         │
    └──────────────────────────────────────┘
         │
         ▼
    ┌──────────────────────────────────────┐
    │ Backend: CREATE REVERT VERSION       │
    │ INSERT INTO versions                 │
    │ ├─ entity_id = same                  │
    │ ├─ old_data = current (before revert)│
    │ ├─ new_data = version.old_data       │
    │ ├─ change_type = "reverted"          │
    │ ├─ version_number = max + 1          │
    │ └─ change_description = "Reverted    │
    │    from version X"                   │
    └──────────────────────────────────────┘
         │
         ▼
    ┌──────────────────────────────────────┐
    │ Backend: UPDATE KB                   │
    │ Replace character in KB with         │
    │ version.old_data                     │
    └──────────────────────────────────────┘
         │
         ▼
    ┌──────────────────────────────────────┐
    │ Frontend: Success                    │
    │ ├─ Close modal                       │
    │ ├─ Refresh character form            │
    │ ├─ Toast: "Reverted to version X ✓" │
    │ └─ Update version history display    │
    └──────────────────────────────────────┘
```

---

## 6. MULTI-PROJECT SWITCHING

### 6.1 Novel Selection Flow

```
USER CLICKS "NOVEL SELECTOR" DROPDOWN
         │
         ▼
    ┌──────────────────────────────────────┐
    │ Frontend: NovelSelector.svelte        │
    │ ├─ Load from store: $novels           │
    │ ├─ Filter archived (if option)        │
    │ └─ Display list:                      │
    │   ├─ Novel Title                      │
    │   ├─ Status badge (draft/in-prog)     │
    │   ├─ Last modified date               │
    │   └─ [Open] button                    │
    └──────────────────────────────────────┘
         │
         │ User clicks a novel
         ▼
    ┌──────────────────────────────────────┐
    │ Frontend: selectNovel(novelId)        │
    │ POST /api/novels/{novelId}/select     │
    └──────────────────────────────────────┘
         │
         ▼
    ┌──────────────────────────────────────┐
    │ Backend: routes/novels.py             │
    │ ├─ Authenticate user                 │
    │ ├─ VERIFY OWNERSHIP:                 │
    │ │  SELECT * FROM novels               │
    │ │  WHERE id = ? AND user_id = ?       │
    │ ├─ If not owned → 404 error           │
    │ ├─ UPDATE user                        │
    │ │  SET current_novel_id = ?           │
    │ │  WHERE id = user_id                 │
    │ └─ Return {"status": "selected"}      │
    └──────────────────────────────────────┘
         │
         ▼
    ┌──────────────────────────────────────┐
    │ Frontend: Update Store                │
    │ currentNovel.set(selectedNovel)       │
    │ └─ Triggers reactive UI updates       │
    └──────────────────────────────────────┘
         │
         ├─ Update NovelSelector badge       
         │  (show selected novel name)       
         │                                   
         ├─ Update ChatUI context header    
         │  (show novel + char count)        
         │                                   
         ├─ RELOAD Knowledge Base Panel      
         │  (fetch new novel's KB)           
         │  GET /api/novels/{id}/kb/         
         │                                   
         ├─ RELOAD Manuscript Editor         
         │  (fetch new novel's manuscript)   
         │  GET /api/novels/{id}/manuscript  
         │                                   
         └─ CLEAR Chat History               
            (new conversation context)      
                 │
                 ▼
    ┌──────────────────────────────────────┐
    │ UI Ready for New Novel               │
    │ ├─ All panels show data for novel_2  │
    │ ├─ Chat context will use this novel  │
    │ │  (next message will have this      │
    │ │   novel's KB injected)             │
    │ └─ Toast: "Switched to Novel X ✓"    │
    └──────────────────────────────────────┘
```

---

## 7. TOOLS INVOCATION FLOW

### 7.1 Example: /brainstorm Command

```
USER TYPES: "/brainstorm plot twist for chapter 3"
AND PRESSES ENTER
         │
         ▼
    ┌──────────────────────────────────────┐
    │ Frontend: Parse Command               │
    │ ├─ Detect prefix: /brainstorm         │
    │ ├─ Extract args: "plot twist for Ch3" │
    │ └─ Send as:                           │
    │   {                                   │
    │     "role": "user",                   │
    │     "content": "/brainstorm plot...   │
    │     "tool_metadata": {                │
    │       "tool": "brainstorm",           │
    │       "args": "plot twist for Ch3"    │
    │     }                                 │
    │   }                                   │
    └──────────────────────────────────────┘
         │
         ▼ POST /api/chat/completions
    ┌──────────────────────────────────────┐
    │ Backend: Chat Route                  │
    │ ├─ Detect /brainstorm command        │
    │ ├─ Extract novel_id from session     │
    │ ├─ Extract args: "plot twist..."     │
    │ └─ Route to TOOL execution           │
    │   (don't call Ollama directly)       │
    └──────────────────────────────────────┘
         │
         ▼
    ┌──────────────────────────────────────┐
    │ Backend: tools/brainstorm.py          │
    │ @tool                                 │
    │ def brainstorm_ideas(                 │
    │   novel_id, theme, count=5            │
    │ )                                     │
    │ ├─ Load KB                            │
    │ │ SELECT * FROM knowledge_bases       │
    │ ├─ Build prompt:                      │
    │ │ Universe: {kb.universe_docs}        │
    │ │ Characters: {kb.characters}         │
    │ │ Theme: plot twist for chapter 3     │
    │ │ "Generate 5 creative plot twists"   │
    │ └─ Call Ollama                        │
    │   POST http://localhost:11434/api... │
    └──────────────────────────────────────┘
         │
         ▼
    ┌──────────────────────────────────────┐
    │ Ollama: Process Tool Prompt           │
    │ ├─ Input: prompt with context +      │
    │ │          theme + count              │
    │ ├─ Generate: 5 plot twist ideas      │
    │ └─ Return: formatted list             │
    │   Idea 1: {description}               │
    │   Idea 2: {description}               │
    │   ...                                 │
    └──────────────────────────────────────┘
         │
         ▼
    ┌──────────────────────────────────────┐
    │ Backend: tools/brainstorm.py (cont)  │
    │ ├─ Parse response from Ollama        │
    │ ├─ Extract 5 ideas                   │
    │ ├─ Save to DB (optional):            │
    │ │ INSERT INTO brainstorm_sessions     │
    │ │ (novel_id, theme, ideas, timestamp) │
    │ └─ Return:                            │
    │   {                                   │
    │     "tool": "brainstorm",             │
    │     "ideas": [                        │
    │       "Idea 1 with context...",       │
    │       "Idea 2...",                    │
    │       ...                             │
    │     ]                                 │
    │   }                                   │
    └──────────────────────────────────────┘
         │
         ▼
    ┌──────────────────────────────────────┐
    │ Backend: Format Response              │
    │ ├─ Create message:                   │
    │ │  {                                  │
    │ │    "role": "assistant",             │
    │ │    "content": formatted_ideas       │
    │ │  }                                  │
    │ ├─ Save to messages table             │
    │ └─ Stream to frontend                 │
    └──────────────────────────────────────┘
         │
         ▼
    ┌──────────────────────────────────────┐
    │ Frontend: Display Results             │
    │ ├─ Detect tool response               │
    │ ├─ Use BrainstormResult.svelte       │
    │ ├─ Render as:                         │
    │ │  💭 BRAINSTORM RESULTS               │
    │ │  Theme: plot twist...               │
    │ │  ┌─────────────────────┐             │
    │ │  │ 1. Idea 1 here...   │             │
    │ │  │    [Use this idea]  │             │
    │ │  ├─────────────────────┤             │
    │ │  │ 2. Idea 2 here...   │             │
    │ │  │    [Use this idea]  │             │
    │ │  ├─────────────────────┤             │
    │ │  │ 3. Idea 3...        │             │
    │ │  │    [Use this idea]  │             │
    │ │  └─────────────────────┘             │
    │ └─ Ready for next interaction         │
    └──────────────────────────────────────┘
```

---

## 8. COMPLETE SYSTEM INTERACTION DIAGRAM

### 8.1 All Components Connected

```
┌─────────────────────────────────────────────────────────────────┐
│                      CLIENT (Browser)                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────┐  ┌─────────────┐  ┌──────────┐  ┌──────────┐ │
│  │  Chat UI     │  │ Manuscript  │  │    KB    │  │  Tools   │ │
│  │              │  │   Editor    │  │  Panel   │  │ Toolbar  │ │
│  │ ├─ Input box │  │ ├─ Monaco   │  │├─Universe│  │├─Brainstorm
│  │ ├─ Messages  │  │ ├─ Chapters │  │├─Chars   │  │├─Outline │
│  │ └─ Tools btn │  │ └─ Auto-save│  │└─Linking │  │└─Dialogue │
│  └──────────────┘  └─────────────┘  └──────────┘  └──────────┘
│         │                 │                │             │        
│         └─────────────────┴────────────────┴─────────────┘        
│                         (HTTP/WS)                                  
│                           │                                        
└───────────────────────────┼──────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FASTAPI BACKEND                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌─────────────┐ ┌──────────────┐ ┌────────────┐ ┌────────────┐ │
│  │  /novels    │ │  /kb/*       │ │  /chat/    │ │  /tools/*  │ │
│  │  Routes     │ │  Routes      │ │  Routes    │ │  Routes    │ │
│  └─────────────┘ └──────────────┘ └────────────┘ └────────────┘ │
│         │               │               │              │          │
│  ┌──────┴───────────────┴───────────────┴──────────────┴────────┐ │
│  │              BUSINESS LOGIC LAYER                            │ │
│  │ ┌──────────────┐ ┌──────────────┐ ┌──────────────────────┐  │ │
│  │ │ Prompt       │ │  Versioning  │ │  Tool Orchestration  │  │ │
│  │ │ Builder      │ │  Logic       │ │  (brainstorm, etc)   │  │ │
│  │ └──────────────┘ └──────────────┘ └──────────────────────┘  │ │
│  │                                                               │ │
│  ├──────────────────────────────────────────────────────────────┤ │
│  │              DATA ACCESS LAYER (DAOs)                        │ │
│  │ ┌─────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────┐  │ │
│  │ │NovelDAO │ │KnowledgeB │ │VersionDAO│ │ContextSnapshot  │  │ │
│  │ │         │ │BaseDAO    │ │          │ │DAO               │  │ │
│  │ └─────────┘ └──────────┘ └──────────┘ └──────────────────┘  │ │
│  │                                                               │ │
│  └──────────────────────────────────────────────────────────────┘ │
│                           │                                        │
└───────────────────────────┼────────────────────────────────────────┘
                            │ (SQL)
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                      DATABASE                                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐   │
│  │ OpenWebUI    │  │ StoryWeaver  │  │    Relationships     │   │
│  │ Tables:      │  │ Tables:      │  │                      │   │
│  │ • users      │  │ • novels     │  │  users           │   │   │
│  │ • chats      │  │ • knowledge  │  │    ├─ novels     │   │   │
│  │ • messages   │  │   _bases     │  │    │  ├─ KB      │   │   │
│  │ • models     │  │ • manuscripts│  │    │  ├─ MS      │   │   │
│  │              │  │ • versions   │  │    │  └─ chats   │   │   │
│  │              │  │ • context_   │  │    │     └─msgs  │   │   │
│  │              │  │   snapshots  │  │    │             │   │   │
│  │              │  │ • chat_meta  │  │    └─────────────┘   │   │
│  │              │  │   data       │  │                      │   │
│  └──────────────┘  └──────────────┘  └──────────────────────┘   │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
                            │ (REST API)
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                   EXTERNAL SERVICES                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  OLLAMA (http://localhost:11434)                         │   │
│  │  ├─ Hosts Mistral model                                  │   │
│  │  ├─ Processes prompts (with context injection)           │   │
│  │  ├─ Streams completions back                             │   │
│  │  └─ Handles temperature, token limits, etc               │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 9. ERROR HANDLING FLOW

### 9.1 Example: Authorization Error

```
USER (not owning novel) TRIES TO ACCESS NOVEL
         │
         ▼
    ┌──────────────────────────────────────┐
    │ Frontend: selectNovel(other_user_id) │
    │ POST /api/novels/{novel_id}/select   │
    └──────────────────────────────────────┘
         │
         ▼
    ┌──────────────────────────────────────┐
    │ Backend: Authenticate                │
    │ ├─ Get current user from JWT token   │
    │ └─ current_user = USER_A              │
    └──────────────────────────────────────┘
         │
         ▼
    ┌──────────────────────────────────────┐
    │ Backend: Check Ownership             │
    │ SELECT * FROM novels                 │
    │ WHERE id = ? AND user_id = ?         │
    │                                      │
    │ Result: NOT FOUND                    │
    │ (novel belongs to USER_B, not USER_A)│
    └──────────────────────────────────────┘
         │
         ▼
    ┌──────────────────────────────────────┐
    │ Backend: Raise HTTPException          │
    │ HTTPException(                        │
    │   status_code=404,                   │
    │   detail="Novel not found"            │
    │ )                                     │
    └──────────────────────────────────────┘
         │
         ▼ HTTP 404 Response
    ┌──────────────────────────────────────┐
    │ Frontend: Handle Error                │
    │ catch (error) {                       │
    │   if (error.status === 404) {        │
    │     showToast("Novel not found")      │
    │     closeModal()                      │
    │   }                                   │
    │ }                                     │
    └──────────────────────────────────────┘
         │
         ▼
    ┌──────────────────────────────────────┐
    │ UI: Show Error Toast                  │
    │ "❌ Novel not found"                  │
    │                                      │
    │ User stays on previous page           │
    │ Current novel unchanged               │
    └──────────────────────────────────────┘
```

---

## 10. SEQUENCE DIAGRAM: Complete Chat Interaction

```
┌─────────────┐              ┌────────────┐              ┌──────────┐
│   Browser   │              │  Backend   │              │  Ollama  │
│             │              │            │              │          │
└──────┬──────┘              └────────────┘              └──────────┘
       │                                                      │
       │ 1. User types "/brainstorm"                          │
       │ + "plot twist"                                       │
       │ + presses ENTER                                      │
       │                                                      │
       ├──────── POST /api/chat/completions ────────────────>│
       │         {                                            │
       │           "chat_id": "...",                          │
       │           "content": "/brainstorm plot twist",       │
       │           "novel_id": (from session)                 │
       │         }                                            │
       │                                                      │
       │                  2. Authenticate + Load Novel       │
       │                     + Load KB                       │
       │                     + Load Manuscript               │
       │<───────────── 200 OK (start streaming) ─────────────│
       │                                                      │
       │                  3. Detect /brainstorm              │
       │                     command, prepare tool request   │
       │                                                      │
       │                  4. Call brainstorm tool             │
       │                     Load kb + build prompt           │
       │                                                      │
       │                  5. POST to Ollama                   │
       │                                                      │
       │                                          ┌──────────┐
       │                                          │ Process  │
       │                                          │ prompt   │
       │                                          │ with     │
       │                                          │ Mistral  │
       │                                          │          │
       │                                          │ Generate │
       │                                          │ 5 ideas  │
       │                                          └──────────┘
       │                                                      │
       │                  6. Receive & parse response        │
       │                                                      │
       │<────── stream: {"role": "assistant", "content": "..."}
       │                                                      │
       │ 7. Display idea 1                                    │
       │ 8. Display idea 2                                    │
       │ 9. Display idea 3                                    │
       │ 10. Display idea 4                                   │
       │ 11. Display idea 5                                   │
       │                                                      │
       │                  12. Save messages to DB             │
       │                  13. Create context snapshot         │
       │                  14. End stream                      │
       │                                                      │
       │<──────────────── end stream ──────────────────────────
       │                                                      │
       │ 15. Display [Use this idea] buttons                  │
       │ 16. Show toast: "Brainstorm complete ✓"             │
       │ 17. Ready for next interaction                       │
       │                                                      │
       └──────────────────────────────────────────────────────┘
```

---

Ce diagramme est complet et prêt à être utilisé pour la compréhension du système !
