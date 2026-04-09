# 🏗️ STORYWEAVER : Architecture Diagrams

---

## 1. SYSTEM ARCHITECTURE OVERVIEW

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         STORYWEAVER FULL STACK                             │
└─────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│                           USER BROWSER / MOBILE                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                    FRONTEND (SvelteKit + Vite)                       │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────┐    │   │
│  │  │ Novel    │  │ Chat UI  │  │ Manu-    │  │ Knowledge Base   │    │   │
│  │  │ Selector │  │          │  │ script   │  │ Editor Panel     │    │   │
│  │  │          │  │ - Input  │  │ Editor   │  │                  │    │   │
│  │  │          │  │ - Messages│ │ - Markdown│ │ - Universe       │    │   │
│  │  │          │  │ - Tools  │  │ - Syntax │  │ - Characters     │    │   │
│  │  │          │  │  Toolbar │  │ - Highlighting│ - Locations    │    │   │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────────────┘    │   │
│  │                                                                       │   │
│  │  [State Management: Svelte Stores]                                  │   │
│  │  - currentNovel, novels                                             │   │
│  │  - currentKB, manuscript                                            │   │
│  │  - chatHistory, messages                                            │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                      │                                       │
│                         HTTP REST API + JSON                                 │
│                                      │                                       │
└──────────────────────────────────────┼───────────────────────────────────────┘
                                       │
                  ┌────────────────────┼────────────────────┐
                  │                    │                    │
┌─────────────────▼──────────┐ ┌──────▼────────────┐ ┌────▼──────────────────┐
│   BACKEND API LAYER        │ │  OLLAMA/MISTRAL   │ │  OPENWEBUI CORE      │
│   (FastAPI - Python)       │ │  (Local LLM)      │ │  (Existing)          │
│                            │ │                    │ │                      │
│ ┌────────────────────────┐ │ │ ┌────────────────┐ │ │ ┌──────────────────┐ │
│ │  NOVEL ROUTES         │ │ │ │ Ollama API     │ │ │ │ Auth/User mgmt   │ │
│ │ ├─ POST /novels       │ │ │ │ localhost:     │ │ │ │                  │ │
│ │ ├─ GET /novels        │ │ │ │ 11434          │ │ │ └──────────────────┘ │
│ │ ├─ PUT /novels/{id}   │ │ │ │                │ │ │ ┌──────────────────┐ │
│ │ └─ DELETE /novels/{id}│ │ │ │ Model: Mistral │ │ │ │ Chat management  │ │
│ │                        │ │ │ └────────────────┘ │ │ └──────────────────┘ │
│ │ ┌────────────────────┐ │ │                    │ │                      │
│ │ │ KB ROUTES          │ │ │                    │ │ ┌──────────────────┐ │
│ │ ├─ GET /kb/          │ │ │                    │ │ │ Existing Models  │ │
│ │ ├─ PUT /kb/universe  │ │ │                    │ │ │ & Config         │ │
│ │ ├─ POST /characters  │ │ │                    │ │ └──────────────────┘ │
│ │ └─ DELETE /chars/{id}│ │ │                    │ │                      │
│ │                        │ │                    │ │                      │
│ │ ┌────────────────────┐ │ │                    │ │                      │
│ │ │ CONTEXT INJECTOR   │ │ │                    │ │                      │
│ │ ├─ build_prompt()    │ │ │                    │ │                      │
│ │ ├─ inject_context()  │ │ │                    │ │                      │
│ │ └─ modify_request()  │ │ │                    │ │                      │
│ │                        │ │                    │ │                      │
│ │ ┌────────────────────┐ │ │                    │ │                      │
│ │ │ TOOLS ROUTER       │ │ │                    │ │                      │
│ │ ├─ /brainstorm       │ │ │                    │ │                      │
│ │ ├─ /analyze          │ │ │                    │ │                      │
│ │ ├─ /dialogue         │ │ │                    │ │                      │
│ │ ├─ /outline          │ │ │                    │ │                      │
│ │ └─ /search_kb        │ │ │                    │ │                      │
│ └────────────────────────┘ │                    │ │                      │
└────────────┬─────────────────┴────────────────────┴──────────────────────┘
             │
             │ ORM (SQLAlchemy)
             │
┌────────────▼──────────────────────────────────────────────────────────────┐
│                        DATABASE LAYER (SQLite/PostgreSQL)                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │ OPENWEBUI    │  │ STORYWEAVER  │  │ STORYWEAVER  │  │ STORYWEAVER  │  │
│  │ TABLES       │  │ TABLES       │  │ TABLES       │  │ TABLES       │  │
│  │              │  │              │  │              │  │              │  │
│  │ • users      │  │ • novels     │  │ • knowledge_ │  │ • versions   │  │
│  │ • chats      │  │ • manuscripts│  │   bases      │  │ • context_   │  │
│  │ • messages   │  │              │  │ • conversat- │  │   snapshots  │  │
│  │ • models     │  │              │  │   ions       │  │              │  │
│  │              │  │              │  │              │  │              │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘  │
└────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. DATA FLOW : CHAT WITH NOVEL CONTEXT

```
USER TYPES MESSAGE IN CHAT
        │
        ▼
┌─────────────────────────────────────┐
│  Frontend Chat Component            │
│  ┌─────────────────────────────────┐│
│  │ Input: "Brainstorm plot twist"  ││
│  └─────────────────────────────────┘│
│  current_novel_id = "uuid-xyz"      │
│  Send: POST /api/chat/completions  │
│  Body: {messages, model, temp, ...} │
└────────────┬────────────────────────┘
             │
             ▼
┌──────────────────────────────────────────────────────────────┐
│  Backend: /api/chat/completions Endpoint                    │
│                                                              │
│  1. Get current_user.current_novel_id                       │
│  2. If no novel: return normal OpenWebUI response           │
│     → Skip context injection                                │
│                                                              │
│  3. If novel selected:                                      │
│     ┌──────────────────────────────────────────────────┐   │
│     │ CONTEXT INJECTION PIPELINE                       │   │
│     │                                                  │   │
│     │ a) Load Data:                                   │   │
│     │    └─ KB = KnowledgeBaseDAO.get(novel_id)      │   │
│     │    └─ Manuscript = ManuscriptDAO.get(novel_id) │   │
│     │    └─ ChatHistory = get last 10 messages       │   │
│     │                                                  │   │
│     │ b) Build Prompt:                                │   │
│     │    system_prompt = PromptBuilder.build(        │   │
│     │      novel_id=novel_id,                        │   │
│     │      kb=kb,                                    │   │
│     │      manuscript=manuscript,                    │   │
│     │      chat_history=history,                     │   │
│     │      context_level="full"                      │   │
│     │    )                                            │   │
│     │                                                  │   │
│     │ c) Format Output:                               │   │
│     │    """                                           │   │
│     │    [BASE SYSTEM PROMPT]                        │   │
│     │                                                  │   │
│     │    ### UNIVERS DU ROMAN: [Title]              │   │
│     │    [Universe rules formatted]                  │   │
│     │                                                  │   │
│     │    ### PERSONNAGES CLÉS (top 5)                │   │
│     │    - Kaelith (ID: char_001)                    │   │
│     │      Âge: 27, Role: protagonist                │   │
│     │      Traits: ambitieuse, impulsive, loyal      │   │
│     │      Arc: Découverte de pouvoirs magiques      │   │
│     │    - [Others...]                               │   │
│     │                                                  │   │
│     │    ### PASSAGES RÉCENTS DU MANUSCRIT           │   │
│     │    [Last 500 lines of content]                 │   │
│     │                                                  │   │
│     │    ### HISTORIQUE CONVERSATION (last 8)        │   │
│     │    user: "Brainstorm plot twist"               │   │
│     │    assistant: "Considerez...                   │   │
│     │    """                                          │   │
│     │                                                  │   │
│     │ d) Modify Request:                              │   │
│     │    modified_messages = [                       │   │
│     │      {role: "system", content: system_prompt}, │   │
│     │      ...user_messages                          │   │
│     │    ]                                            │   │
│     │                                                  │   │
│     │ e) Create Context Snapshot:                     │   │
│     │    snapshot = ContextSnapshot(                 │   │
│     │      chat_id, novel_id,                        │   │
│     │      injected_prompt=system_prompt,            │   │
│     │      kb_snapshot=kb.dict()                     │   │
│     │    )                                            │   │
│     │    db.save(snapshot)                           │   │
│     └──────────────────────────────────────────────────┘   │
│                                                              │
│  4. Call Ollama/Mistral:                                    │
│     response = await ollama_client.chat(                   │
│       model="mistral",                                     │
│       messages=modified_messages,                          │
│       ...                                                  │
│     )                                                      │
│                                                              │
│  5. Save Message & Return:                                 │
│     db.save_message(                                       │
│       chat_id, role="assistant",                          │
│       content=response.content                            │
│     )                                                      │
│     return response                                        │
└──────────────────┬───────────────────────────────────────┘
                   │
                   ▼
        ┌──────────────────────┐
        │  Ollama/Mistral      │
        │  Processing          │
        │  (with context!)     │
        └──────────────────────┘
                   │
                   ▼
        ┌──────────────────────┐
        │  LLM Response        │
        │  (contextualisée)    │
        └──────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────┐
│  Frontend: Display Response          │
│  + Show "(🔗 Context Injected)"      │
│                                       │
│  Message appears in chat with:       │
│  - Assistant response                │
│  - Context indicator                 │
│  - Option to view injected context   │
└──────────────────────────────────────┘
```

---

## 3. DATABASE SCHEMA RELATIONSHIP DIAGRAM

```
                    ┌─────────────────┐
                    │     USER        │ (OpenWebUI existing)
                    │─────────────────│
                    │ id (UUID)       │
                    │ username        │
                    │ email           │
                    │ current_novel_id├─────────────┐
                    │ (FK → novels)   │             │
                    └─────────────────┘             │
                            │                       │
                            │ (1:M)                 │
                            │                       │
         ┌──────────────────┴────────┐             │
         │                           │              │
         ▼                           ▼              │
    ┌─────────────────┐      ┌─────────────────┐   │
    │     CHATS       │      │     NOVELS      │◄──┘
    │ (OpenWebUI)     │      │─────────────────│
    │─────────────────│      │ id (UUID)       │
    │ id (UUID)       │      │ user_id (FK)    │
    │ user_id (FK)    │      │ title           │
    │ title           │      │ description     │
    │ model           │      │ status          │
    │ created_at      │      │ created_at      │
    └────────┬────────┘      │ updated_at      │
             │               └────────┬────────┘
             │                        │
     ┌───────┴────────┐      ┌────────┴──────────────┬──────────────┐
     │ (1:M)          │      │ (1:1)                  │ (1:1)        │
     │                │      │                        │              │
     ▼                ▼      ▼                        ▼              ▼
┌──────────────┐ ┌──────────────────────┐  ┌──────────────────┐ ┌────────────┐
│  MESSAGES    │ │ CONVERSATIONS        │  │ KNOWLEDGE_BASES  │ │MANUSCRIPTS │
│ (OpenWebUI)  │ │─────────────────────┐│  │──────────────────│ │────────────│
│──────────────│ │ id (UUID)           ││  │ id (UUID)        │ │ id (UUID)  │
│ id (UUID)    │ │ novel_id (FK)       ││  │ novel_id (FK)    │ │ novel_id   │
│ chat_id (FK) │ │ chat_id (FK)        ││  │ universe_docs    │ │ (FK)       │
│ role         │ │ tags (JSON)         ││  │   (JSON)         │ │ content    │
│ content      │ │ context_level       ││  │ characters       │ │   (TEXT)   │
│ created_at   │ │ linked_entities     ││  │   (JSON array)   │ │ chapter_   │
└──────────────┘ │   (JSON)            ││  │ locations        │ │  structure │
             │    │                     ││  │   (JSON array)   │ │   (JSON)   │
             │    └──────────────────────┘  │ objects          │ │ word_count │
             │                              │   (JSON array)   │ │ updated_at │
             │                              │ updated_at       │ └────────────┘
             │                              └──────────────────┘
             │
             └──────────────────┐
                                │
                    ┌───────────┴──────────┐
                    │ (1:M)                 │
                    │                       │
                    ▼                       ▼
            ┌──────────────────────┐  ┌──────────────────┐
            │ CONTEXT_SNAPSHOTS    │  │    VERSIONS      │
            │──────────────────────│  │──────────────────│
            │ id (UUID)            │  │ id (UUID)        │
            │ chat_id (FK)         │  │ novel_id (FK)    │
            │ novel_id (FK)        │  │ entity_type      │
            │ injected_context     │  │ entity_id        │
            │   (JSON)             │  │ old_data (JSON)  │
            │ kb_snapshot (JSON)   │  │ new_data (JSON)  │
            │ timestamp            │  │ change_type      │
            └──────────────────────┘  │ timestamp        │
                                      │ version_number   │
                                      └──────────────────┘

LEGEND:
─────
(1:1) = One-to-One relationship
(1:M) = One-to-Many relationship
FK   = Foreign Key
UUID = Unique ID field
JSON = JSON document field
TEXT = Large text field
```

---

## 4. API ROUTES TREE

```
/api
├── novels (STORYWEAVER NEW)
│   ├── POST /
│   │   └─ Create novel
│   │     Request: {title, description}
│   │     Response: {id, title, status, created_at}
│   │
│   ├── GET /
│   │   └─ List user's novels
│   │     Response: [{id, title, status, ...}, ...]
│   │
│   ├── GET /{novel_id}
│   │   └─ Get novel details
│   │     Response: {id, title, description, status, ...}
│   │
│   ├── PUT /{novel_id}
│   │   └─ Update novel (title, description, status)
│   │     Request: {title?, description?, status?}
│   │     Response: {id, ...updated fields...}
│   │
│   ├── DELETE /{novel_id}
│   │   └─ Delete/archive novel
│   │     Response: {status: "deleted"}
│   │
│   ├── POST /{novel_id}/select
│   │   └─ Set as current novel for session
│   │     Response: {current_novel_id}
│   │
│   ├── POST /{novel_id}/archive
│   │   └─ Archive novel
│   │     Response: {status: "archived"}
│   │
│   ├── POST /{novel_id}/restore
│   │   └─ Restore archived novel
│   │     Response: {status: "restored"}
│   │
│   ├── kb (STORYWEAVER NEW - Knowledge Base)
│   │   ├── GET /
│   │   │   └─ Get full KB
│   │   │     Response: {universe_docs, characters, locations, objects}
│   │   │
│   │   ├── PUT /universe
│   │   │   └─ Update universe rules
│   │   │     Request: {universe_docs: {...}}
│   │   │     Response: KB updated
│   │   │
│   │   ├── POST /characters
│   │   │   └─ Add character
│   │   │     Request: {id, name, age, appearance, ...}
│   │   │     Response: {status: "created", character}
│   │   │
│   │   ├── PUT /characters/{character_id}
│   │   │   └─ Update character
│   │   │     Request: {name, age, ...}
│   │   │     Response: {status: "updated"}
│   │   │
│   │   ├── DELETE /characters/{character_id}
│   │   │   └─ Delete character
│   │   │     Response: {status: "deleted"}
│   │   │
│   │   ├── POST /locations
│   │   │   └─ Add location
│   │   │
│   │   ├── POST /objects
│   │   │   └─ Add object
│   │   │
│   │   └── GET /search
│   │       └─ Full-text search KB
│   │         Query: ?q=search_term
│   │         Response: {characters: [...], locations: [...], objects: [...]}
│   │
│   ├── versions (STORYWEAVER NEW - Versioning)
│   │   ├── GET /{entity_id}
│   │   │   └─ Get version history of entity
│   │   │     Response: [{id, timestamp, change_type, old_data, new_data}, ...]
│   │   │
│   │   └── POST /{entity_id}/{version_number}/revert
│   │       └─ Revert to specific version
│   │         Response: {status: "reverted"}
│   │
│   └── manuscript (STORYWEAVER NEW - Manuscript Management)
│       ├── GET /
│       │   └─ Get current manuscript content
│       │     Response: {content, word_count, chapter_structure}
│       │
│       ├── PUT /
│       │   └─ Update manuscript content
│       │     Request: {content}
│       │     Response: {word_count, updated_at}
│       │
│       └── GET /export
│           └─ Export manuscript
│             Query: ?format=markdown|pdf|txt|epub
│             Response: File download
│
├── chat (OPENWEBUI EXISTING - MODIFIED)
│   ├── POST /completions
│   │   └─ Original OpenWebUI endpoint
│   │     MODIFICATION:
│   │     - Check for current_novel_id
│   │     - If yes, inject context before calling Ollama
│   │     - Save context snapshot
│   │     - Return response with context marker
│   │
│   └── GET /{chat_id}/messages
│       └─ Get chat history
│
├── models (OPENWEBUI EXISTING)
│   ├── GET /
│   │   └─ List available models
│   │
│   └── POST /
│       └─ Add new model
│
├── users (OPENWEBUI EXISTING)
│   ├── GET /me
│   │   └─ Current user info
│   │
│   └── PUT /me
│       └─ Update profile
│
└── tools (STORYWEAVER NEW - Custom Tools)
    ├── POST /brainstorm
    │   ├─ Input: {novel_id, theme, count}
    │   └─ Output: {ideas: [{title, description}, ...]}
    │
    ├── POST /analyze
    │   ├─ Input: {novel_id, text}
    │   └─ Output: {issues, coherence_score}
    │
    ├── POST /dialogue
    │   ├─ Input: {novel_id, characters: [id1, id2], context}
    │   └─ Output: {dialogue: "formatted dialogue"}
    │
    ├── POST /outline
    │   ├─ Input: {novel_id, structure: "three-act"}
    │   └─ Output: {outline: [...]}
    │
    └── GET /kb/search
        ├─ Input: ?q=query
        └─ Output: {results}
```

---

## 5. CONTEXT INJECTION DETAILED FLOW

```
REQUEST ARRIVES AT /api/chat/completions
│
├─ Extract: current_user, current_novel_id, chat_id, messages
│
├─ IF current_novel_id is NULL or empty
│  │
│  └─▶ SKIP CONTEXT INJECTION (normal OpenWebUI flow)
│      │
│      └─▶ Call Ollama directly
│
└─ IF current_novel_id exists
   │
   ├─ PERMISSION CHECK
   │  └─ Verify user owns this novel
   │     If not: return 404
   │
   ├─ LOAD CONTEXTUAL DATA (parallel if possible)
   │  ├─ novel = NovelDAO.get_by_id(db, novel_id)
   │  ├─ kb = KnowledgeBaseDAO.get_by_novel_id(db, novel_id)
   │  ├─ manuscript = ManuscriptDAO.get_by_novel_id(db, novel_id)
   │  ├─ recent_messages = get_last_n_messages(chat_id, n=10)
   │  └─ Wait for all data
   │
   ├─ BUILD CONTEXT SNAPSHOT
   │  ├─ Format Universe
   │  │  └─ Convert KB.universe_docs to readable text
   │  │     Input: {
   │  │       "magic_system": "Three tiers of magic...",
   │  │       "world_rules": "Technology level: medieval..."
   │  │     }
   │  │     Output: """
   │  │     **Magic System:** Three tiers of magic...
   │  │     **World Rules:** Technology level: medieval...
   │  │     """
   │  │
   │  ├─ Format Characters (top 5 by importance)
   │  │  └─ For each character in KB:
   │  │     Extract: name, age, role, personality, arc, relationships
   │  │     Output: """
   │  │     **Kaelith** (ID: char_001)
   │  │     - Âge: 27, Rôle: protagonist
   │  │     - Traits: ambitieuse, impulsive, loyal
   │  │     - Arc: Découverte de pouvoirs magiques
   │  │     - Relations: [char_002, char_003]
   │  │     """
   │  │
   │  ├─ Extract Recent Scenes
   │  │  └─ Take last 500 lines of manuscript.content
   │  │     Skip metadata, get raw narrative
   │  │
   │  ├─ Format Conversation History (last 8 messages)
   │  │  └─ For each message:
   │  │     Limit to 200 chars (summary if needed)
   │  │
   │  └─ Create System Prompt
   │     └─ Concatenate:
   │        [BASE SYSTEM PROMPT]
   │        + [UNIVERSE SECTION]
   │        + [CHARACTERS SECTION]
   │        + [RECENT SCENES SECTION]
   │        + [CONVERSATION HISTORY SECTION]
   │        = FINAL SYSTEM PROMPT
   │
   ├─ MODIFY REQUEST
   │  └─ Insert system prompt as first message
   │     Before: [user_msg_1, user_msg_2, ...]
   │     After:  [
   │              {role: "system", content: full_injected_prompt},
   │              user_msg_1,
   │              user_msg_2,
   │              ...
   │            ]
   │
   ├─ SAVE CONTEXT SNAPSHOT
   │  └─ Create ContextSnapshot record in DB:
   │     {
   │       chat_id: ...,
   │       novel_id: ...,
   │       injected_context: {
   │         base_prompt: ...,
   │         universe: ...,
   │         characters: ...,
   │         scenes: ...,
   │         history: ...
   │       },
   │       kb_snapshot: {...full KB dump...},
   │       timestamp: now()
   │     }
   │     Save to DB for future reference/debugging
   │
   ├─ CALL OLLAMA/MISTRAL
   │  └─ POST to localhost:11434/api/chat
   │     with modified_messages
   │     IMPORTANT: LLM has FULL CONTEXT now
   │
   ├─ RECEIVE RESPONSE
   │  └─ response.content = LLM's answer
   │     (Already uses our injected context)
   │
   ├─ SAVE MESSAGE
   │  └─ Store in DB:
   │     {
   │       chat_id: ...,
   │       role: "assistant",
   │       content: response.content,
   │       created_at: now()
   │     }
   │
   └─ RETURN TO FRONTEND
     └─ Add metadata:
        {
          content: response.content,
          role: "assistant",
          context_injected: true,
          novel_id: ...,
          snapshot_id: ...
        }

FRONTEND DISPLAYS:
│
├─ Message content
├─ Small indicator: "(🔗 Context Injected)"
├─ Option: "View injected context" (expand snapshot)
└─ Continue conversation...
```

---

## 6. FRONTEND COMPONENT HIERARCHY

```
┌──────────────────────────────────────────────────────────────┐
│                     +layout.svelte                            │
│         (Main layout - wraps all routes)                     │
│                                                               │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  HEADER                                                 │ │
│  │  ├─ Logo                                               │ │
│  │  ├─ NovelSelector (dropdown)                           │ │
│  │  ├─ Settings button                                   │ │
│  │  └─ Help/Docs button                                  │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                               │
│  ┌──────────────────┬──────────────────┬──────────────────┐ │
│  │                  │                  │                  │ │
│  │  LEFT PANEL      │  CENTER PANEL    │  RIGHT PANEL    │ │
│  │  (40%)           │  (40%)           │  (20%)          │ │
│  │                  │                  │                 │ │
│  │  ┌────────────┐ │  ┌────────────┐  │  ┌────────────┐ │ │
│  │  │   ChatUI   │ │  │ Manuscript │  │  │ Knowledge  │ │ │
│  │  │            │ │  │  Editor    │  │  │   Base     │ │ │
│  │  │ ┌────────┐ │ │  │            │  │  │  Panel     │ │ │
│  │  │ │ Message│ │ │  │ ┌────────┐ │  │  │            │ │ │
│  │  │ │ 1      │ │ │  │ │Monaco  │ │  │  │ ┌────────┐ │ │ │
│  │  │ └────────┘ │ │  │ │Editor  │ │  │  │ │Universe│ │ │ │
│  │  │            │ │  │ │        │ │  │  │ │Tab     │ │ │ │
│  │  │ ┌────────┐ │ │  │ │        │ │  │  │ └────────┘ │ │ │
│  │  │ │ Message│ │ │  │ └────────┘ │  │  │            │ │ │
│  │  │ │ 2      │ │ │  │            │  │  │ ┌────────┐ │ │ │
│  │  │ └────────┘ │ │  │ [Quick     │  │  │ │Char.   │ │ │ │
│  │  │            │ │  │  Action    │  │  │ │Manager │ │ │ │
│  │  │ ...        │ │  │  Buttons]  │  │  │ │Tab     │ │ │ │
│  │  │            │ │  │            │  │  │ └────────┘ │ │ │
│  │  │ ┌────────┐ │ │  │            │  │  │            │ │ │
│  │  │ │ Message│ │ │  │            │  │  │ ┌────────┐ │ │ │
│  │  │ │ Input  │ │ │  │            │  │  │ │Locations│ │ │ │
│  │  │ └────────┘ │ │  │            │  │  │ │Tab     │ │ │ │
│  │  │            │ │  │            │  │  │ └────────┘ │ │ │
│  │  │ ┌────────┐ │ │  │            │  │  │            │ │ │
│  │  │ │Tools   │ │ │  │            │  │  │ ┌────────┐ │ │ │
│  │  │ │Toolbar │ │ │  │            │  │  │ │Version │ │ │ │
│  │  │ │ 💭 🔍  │ │ │  │            │  │  │ │History │ │ │ │
│  │  │ │ 💬 📋  │ │ │  │            │  │  │ │Button  │ │ │ │
│  │  │ └────────┘ │ │  │            │  │  │ └────────┘ │ │ │
│  │  │            │ │  │            │  │  │            │ │ │
│  │  └────────────┘ │  └────────────┘  │  └────────────┘ │ │
│  │                  │                  │                  │ │
│  └──────────────────┴──────────────────┴──────────────────┘ │
└──────────────────────────────────────────────────────────────┘

DETAILED COMPONENT TREE:

+layout.svelte
│
├── Header.svelte
│   ├── Logo
│   ├── NovelSelector.svelte
│   │   ├── Button "📖 Current Novel"
│   │   └── Dropdown Menu (on click)
│   │       ├── Novel List (searchable)
│   │       ├── "+" New Novel button
│   │       └── Archived Novels (collapsible)
│   │
│   ├── SettingsButton.svelte
│   └── HelpButton.svelte
│
├── MainLayout.svelte (tripartite)
│   │
│   ├── LeftPanel.svelte (40%)
│   │   │
│   │   └── ChatUI.svelte
│   │       ├── MessageList.svelte
│   │       │   ├── Message.svelte (for each message)
│   │       │   │   ├── Avatar
│   │       │   │   ├── Content (Markdown rendered)
│   │       │   │   └── ContextIndicator (if context injected)
│   │       │   │       └── Show context snapshot on click
│   │       │   │
│   │       │   └── ScrollAnchor (to latest message)
│   │       │
│   │       ├── ToolsToolbar.svelte (horizontal buttons)
│   │       │   ├── Button 💭 Brainstorm
│   │       │   ├── Button 🔍 Analyze
│   │       │   ├── Button 💬 Dialogue
│   │       │   ├── Button 📋 Outline
│   │       │   └── Button 🔎 Search KB
│   │       │
│   │       └── ChatInput.svelte
│   │           ├── Textarea (auto-grow)
│   │           └── Send Button
│   │               └── Disabled while waiting for response
│   │
│   │
│   ├── CenterPanel.svelte (40%)
│   │   │
│   │   └── ManuscriptEditor.svelte
│   │       ├── Header
│   │       │   ├── Chapter Selector (dropdown)
│   │       │   ├── Word Count
│   │       │   └── Status Selector (draft/editing/final)
│   │       │
│   │       ├── Sidebar (left)
│   │       │   └── ChapterTree.svelte
│   │       │       └── Each chapter
│   │       │           └── Scenes under chapter (expandable)
│   │       │
│   │       ├── Editor Area
│   │       │   └── MonacoEditor (Markdown syntax highlighting)
│   │       │       ├── Auto-save on changes
│   │       │       ├── Selection tracking
│   │       │       └── Syntax highlighting
│   │       │
│   │       └── QuickActions (context menu)
│   │           ├── "Analyze This Passage" → /analyze
│   │           ├── "Continue Scene" → /brainstorm
│   │           ├── "Generate Dialogue" → /dialogue
│   │           └── "Check Coherence" → /analyze
│   │
│   │
│   └── RightPanel.svelte (20%, collapsible)
│       │
│       └── KnowledgeBasePanel.svelte
│           ├── KBHeader (title + mode selector)
│           │
│           ├── KBTabs (horizontal)
│           │   ├── 🌍 Universe
│           │   ├── 👥 Characters
│           │   ├── 🗺️  Locations
│           │   ├── 📦 Objects
│           │   └── 📅 Timeline
│           │
│           └── TabContent (switches based on active tab)
│               │
│               ├── If Universe:
│               │   └── UniverseEditor.svelte
│               │       ├── JSON editor
│               │       ├── Save button
│               │       └── Last updated info
│               │
│               ├── If Characters:
│               │   └── CharacterManager.svelte
│               │       ├── Search bar
│               │       ├── CharacterList
│               │       │   └── CharacterItem (selectable)
│               │       │
│               │       ├── CharacterForm (when selected/new)
│               │       │   ├── Name input
│               │       │   ├── Age input
│               │       │   ├── Appearance textarea
│               │       │   ├── Personality multi-select
│               │       │   ├── Arc textarea
│               │       │   ├── Relationships multi-select
│               │       │   ├── Save button
│               │       │   ├── Delete button
│               │       │   └── Version History button
│               │       │
│               │       └── VersionHistory.svelte (modal on click)
│               │           ├── Timeline
│               │           ├── Change browser
│               │           └── Revert button
│               │
│               ├── If Locations:
│               │   └── LocationManager.svelte (similar to Character)
│               │
│               └── If Objects:
│                   └── ObjectManager.svelte (similar to Character)


STATE MANAGEMENT (Svelte Stores):

stores/
├── novels.ts
│   ├── novels: Writable<Novel[]> (all user's novels)
│   └── currentNovel: Writable<Novel | null> (selected)
│
├── knowledgeBase.ts
│   ├── currentKB: Writable<KnowledgeBase> (for selected novel)
│   ├── savingKB: Writable<boolean> (UI state)
│   └── selectedCharacter: Writable<Character | null>
│
├── manuscript.ts
│   ├── currentManuscript: Writable<Manuscript>
│   ├── savedContent: Writable<string> (last saved version)
│   ├── wordCount: Derived<number>
│   └── unsavedChanges: Derived<boolean>
│
└── chat.ts
    ├── messages: Writable<Message[]> (current chat)
    ├── isLoading: Writable<boolean>
    ├── contextInjected: Writable<boolean>
    └── currentSnapshot: Writable<ContextSnapshot | null>
```

---

## 7. TOOLS EXECUTION FLOW

```
USER CLICKS TOOL BUTTON or TYPES /command
│
├─ UI inserts command into message input
│  Example: "/brainstorm " → cursor ready for params
│
├─ User adds parameters and sends
│  Example: "/brainstorm dark twist that shocks readers"
│
├─ Message sent to /api/chat/completions
│  ├─ Content: "/brainstorm dark twist that shocks readers"
│  └─ Special marker: tools_enabled = true
│
├─ Backend receives message
│  │
│  ├─ PARSE COMMAND
│  │  └─ Regex match: /(\w+)\s+(.*)/
│  │     Extracts: command="brainstorm", params="dark twist..."
│  │
│  ├─ IF command recognized (brainstorm, analyze, etc.)
│  │  │
│  │  ├─ ROUTE TO TOOL
│  │  │  │
│  │  │  ├─ BRAINSTORM TOOL (/brainstorm)
│  │  │  │  ├─ Load KB, current novel
│  │  │  │  ├─ Build prompt:
│  │  │  │  │  """
│  │  │  │  │  Univers: [KB.universe]
│  │  │  │  │  Personnages: [top 5 chars]
│  │  │  │  │  Enjeu: [user params]
│  │  │  │  │
│  │  │  │  │  Génère 5 idées créatives pour:
│  │  │  │  │  "dark twist that shocks readers"
│  │  │  │  │
│  │  │  │  │  Format: liste numérotée avec brève description.
│  │  │  │  │  """
│  │  │  │  │
│  │  │  │  ├─ Call Ollama with this prompt
│  │  │  │  ├─ Parse response into {ideas: [{title, desc}, ...]}
│  │  │  │  └─ Return structured result
│  │  │  │
│  │  │  ├─ ANALYZE TOOL (/analyze)
│  │  │  │  ├─ Extract text from message/selection
│  │  │  │  ├─ Check timeline coherence
│  │  │  │  ├─ Check character consistency
│  │  │  │  ├─ Check universe rule compliance
│  │  │  │  ├─ Parse results into:
│  │  │  │  │  {
│  │  │  │  │    issues: [
│  │  │  │  │      {type: "character_inconsistency", detail: "..."},
│  │  │  │  │      ...
│  │  │  │  │    ],
│  │  │  │  │    coherence_score: 0.85
│  │  │  │  │  }
│  │  │  │  └─ Return analysis
│  │  │  │
│  │  │  ├─ DIALOGUE TOOL (/dialogue)
│  │  │  │  ├─ Extract character IDs from params
│  │  │  │  ├─ Load character profiles from KB
│  │  │  │  ├─ Build prompt with context
│  │  │  │  ├─ Call Ollama
│  │  │  │  ├─ Format dialogue:
│  │  │  │  │  > Char1: "dialogue"
│  │  │  │  │  > Char2: "response"
│  │  │  │  └─ Return formatted dialogue
│  │  │  │
│  │  │  ├─ OUTLINE TOOL (/outline)
│  │  │  │  ├─ Get structure from params (3-act, 5-act, etc.)
│  │  │  │  ├─ Load novel + KB context
│  │  │  │  ├─ Build prompt for outline generation
│  │  │  │  ├─ Call Ollama
│  │  │  │  ├─ Parse into:
│  │  │  │  │  {
│  │  │  │  │    chapters: [
│  │  │  │  │      {
│  │  │  │  │        number: 1,
│  │  │  │  │        title: "...",
│  │  │  │  │        key_narrative_points: ["..."],
│  │  │  │  │        scenes: [{scene_num, desc}, ...]
│  │  │  │  │      },
│  │  │  │  │      ...
│  │  │  │  │    ]
│  │  │  │  │  }
│  │  │  │  └─ Return structured outline
│  │  │  │
│  │  │  └─ SEARCH KB (/search)
│  │  │     ├─ Query string from params
│  │  │     ├─ Full-text search across KB
│  │  │     ├─ Return:
│  │  │     │  {
│  │  │     │    characters: [...matches...],
│  │     │    locations: [...matches...],
│  │     │    objects: [...matches...]
│  │     │  }
│  │     └─ Return results
│  │
│  └─ IF command not recognized
│     └─ Treat as normal chat (context injection still applies)
│
├─ Format tool result for display
│  │
│  ├─ BrainstormResult.svelte
│  │  └─ Display ideas as expandable cards
│  │
│  ├─ AnalysisResult.svelte
│  │  └─ Display issues with severity coloring
│  │
│  ├─ DialogueResult.svelte
│  │  └─ Format dialogue in conversation style
│  │
│  ├─ OutlineResult.svelte
│  │  └─ Display chapter structure
│  │
│  └─ SearchResult.svelte
│     └─ Display search results by type
│
└─ Display in chat
   ├─ Tool result component
   ├─ Option to edit/refine in chat
   └─ Continue conversation with AI about results
```

---

## 8. DATABASE QUERY PATTERNS

```
COMMON PATTERNS:

1. GET NOVEL WITH ALL DATA
   ┌────────────────────────────────────────────┐
   │ novel = db.query(Novel)                    │
   │   .filter(Novel.id == novel_id)            │
   │   .first()                                  │
   │                                             │
   │ # Access related data (lazy loaded)        │
   │ novel.knowledge_base                       │
   │ novel.manuscript                           │
   │ novel.conversations                        │
   └────────────────────────────────────────────┘

2. GET KB WITH TOP 5 CHARACTERS
   ┌────────────────────────────────────────────┐
   │ kb = db.query(KnowledgeBase)               │
   │   .filter(KB.novel_id == novel_id)         │
   │   .first()                                  │
   │                                             │
   │ characters = kb.characters[:5]             │
   │ # kb.characters is JSON, load from DB      │
   └────────────────────────────────────────────┘

3. GET VERSION HISTORY FOR ENTITY
   ┌────────────────────────────────────────────┐
   │ versions = db.query(Version)               │
   │   .filter(                                  │
   │     Version.entity_id == "char_001"        │
   │   )                                         │
   │   .order_by(Version.version_number.desc()) │
   │   .limit(50)                               │
   │   .all()                                    │
   └────────────────────────────────────────────┘

4. GET RECENT CHAT MESSAGES
   ┌────────────────────────────────────────────┐
   │ messages = db.query(Message)               │
   │   .filter(Message.chat_id == chat_id)      │
   │   .order_by(Message.created_at.desc())     │
   │   .limit(10)                               │
   │   .all()                                    │
   │                                             │
   │ # Reverse for chronological order         │
   │ messages = list(reversed(messages))        │
   └────────────────────────────────────────────┘

5. CREATE NOVEL + KB + MANUSCRIPT (Transaction)
   ┌────────────────────────────────────────────┐
   │ try:                                        │
   │   novel = Novel(user_id, title, ...)       │
   │   db.add(novel)                            │
   │   db.flush()  # Get novel.id               │
   │                                             │
   │   kb = KnowledgeBase(novel.id, ...)        │
   │   db.add(kb)                               │
   │                                             │
   │   manuscript = Manuscript(novel.id, ...)   │
   │   db.add(manuscript)                       │
   │                                             │
   │   db.commit()  # All or nothing            │
   │ except:                                     │
   │   db.rollback()                            │
   │   raise                                     │
   └────────────────────────────────────────────┘

6. SEARCH CHARACTERS
   ┌────────────────────────────────────────────┐
   │ kb = db.query(KnowledgeBase)               │
   │   .filter(KB.novel_id == novel_id)         │
   │   .first()                                  │
   │                                             │
   │ results = [                                 │
   │   c for c in kb.characters                 │
   │   if query.lower() in c["name"].lower()    │
   │ ]                                           │
   │                                             │
   │ # Note: Uses in-memory search (OK for      │
   │ # small KB, may optimize with PostgreSQL   │
   │ # full-text search if needed)              │
   └────────────────────────────────────────────┘

7. UPDATE CHARACTER + CREATE VERSION
   ┌────────────────────────────────────────────┐
   │ kb = db.query(KnowledgeBase)               │
   │   .filter(KB.novel_id == novel_id)         │
   │   .first()                                  │
   │                                             │
   │ old_char = next(                           │
   │   (c for c in kb.characters                │
   │    if c["id"] == "char_001"),              │
   │   None                                      │
   │ )                                           │
   │                                             │
   │ # Create version record                    │
   │ version = Version(                         │
   │   novel_id, "character", "char_001",      │
   │   old_data=old_char,                      │
   │   new_data=new_char_data,                 │
   │   change_type="updated"                   │
   │ )                                           │
   │ db.add(version)                            │
   │                                             │
   │ # Update KB characters array               │
   │ kb.characters = [                          │
   │   new_char_data if c["id"] == "char_001"  │
   │   else c                                    │
   │   for c in kb.characters                   │
   │ ]                                           │
   │                                             │
   │ db.commit()                                │
   └────────────────────────────────────────────┘

8. CONTEXT SNAPSHOT SAVE
   ┌────────────────────────────────────────────┐
   │ snapshot = ContextSnapshot(                │
   │   chat_id=chat_id,                         │
   │   novel_id=novel_id,                       │
   │   injected_context={                       │
   │     "system_prompt": ...,                  │
   │     "universe": ...,                       │
   │     "characters": ...                      │
   │   },                                        │
   │   kb_snapshot=kb_dict,                     │
   │   timestamp=datetime.utcnow()              │
   │ )                                           │
   │ db.add(snapshot)                           │
   │ db.commit()                                │
   └────────────────────────────────────────────┘
```

---

## 9. ERROR HANDLING FLOWS

```
COMMON ERROR SCENARIOS:

1. USER DOESN'T OWN NOVEL
   ┌─────────────────────────────────┐
   │ GET /novels/{novel_id}          │
   │                                 │
   │ novel = get_novel(novel_id)     │
   │ if not novel:                   │
   │   ▶ 404 "Novel not found"      │
   │                                 │
   │ if novel.user_id != current_user│
   │   ▶ 403 "Forbidden"            │
   │                                 │
   │ return {id, title, ...}        │
   └─────────────────────────────────┘

2. NO NOVEL SELECTED FOR CONTEXT
   ┌─────────────────────────────────┐
   │ POST /api/chat/completions      │
   │                                 │
   │ if not current_user.current_    │
   │       novel_id:                  │
   │   ▶ Skip context injection      │
   │   ▶ Normal OpenWebUI flow       │
   │                                 │
   │ else: do context injection      │
   └─────────────────────────────────┘

3. KB DATA NOT FOUND
   ┌─────────────────────────────────┐
   │ GET /novels/{id}/kb/            │
   │                                 │
   │ kb = get_kb(novel_id)           │
   │ if not kb:                      │
   │   ▶ Create empty KB (auto-      │
   │     initialize on novel create) │
   │                                 │
   │ return kb                       │
   └─────────────────────────────────┘

4. INVALID CHARACTER UPDATE
   ┌─────────────────────────────────┐
   │ PUT /kb/characters/{char_id}    │
   │                                 │
   │ if not character_exists:        │
   │   ▶ 404 "Character not found"  │
   │                                 │
   │ if invalid_schema:              │
   │   ▶ 422 "Validation error"     │
   │     + details on invalid fields │
   │                                 │
   │ update character                │
   └─────────────────────────────────┘

5. CONCURRENT EDITS (Race Condition)
   ┌─────────────────────────────────┐
   │ When:                           │
   │ - Two users edit same KB        │
   │ - Last write wins              │
   │                                 │
   │ Mitigation:                     │
   │ - Version history tracks this  │
   │ - Can revert to prev version   │
   │ - Could add optimistic locking │
   │   (future enhancement)         │
   └─────────────────────────────────┘

6. OLLAMA/MISTRAL UNAVAILABLE
   ┌─────────────────────────────────┐
   │ POST /api/chat/completions      │
   │                                 │
   │ try:                            │
   │   response = ollama.chat(...)   │
   │ except ConnectionError:         │
   │   ▶ 503 "LLM service           │
   │     unavailable"               │
   │   + "Retry in a moment"        │
   │                                 │
   │ return response                 │
   └─────────────────────────────────┘

7. CONTEXT TOO LARGE FOR PROMPT
   ┌─────────────────────────────────┐
   │ When building system prompt:    │
   │ - All context exceeds token    │
   │   limit for Mistral            │
   │                                 │
   │ Strategy:                       │
   │ 1. Truncate scenes (last N     │
   │    lines only)                  │
   │ 2. Reduce characters (top 3    │
   │    instead of 5)                │
   │ 3. Compress universe rules      │
   │ 4. Keep last 5 messages only   │
   │                                 │
   │ Token counting:                 │
   │ - Use tiktoken library         │
   │ - Check before sending        │
   │ - Log if truncated            │
   └─────────────────────────────────┘

8. INVALID EXPORT FORMAT
   ┌─────────────────────────────────┐
   │ GET /manuscript/export?         │
   │     format=pdf                  │
   │                                 │
   │ if format not in allowed:       │
   │   ▶ 400 "Invalid format"       │
   │   ▶ "Allowed: markdown, pdf,   │
   │     txt, epub"                 │
   │                                 │
   │ return file                     │
   └─────────────────────────────────┘
```

---

## 10. DEPLOYMENT ARCHITECTURE

```
VPS DEPLOYMENT STRUCTURE:

┌─────────────────────────────────────────────────────────┐
│                    VPS INSTANCE                         │
│          (e.g., DigitalOcean, Linode, Vultr)          │
│                                                         │
│  ┌───────────────────────────────────────────────────┐ │
│  │         Docker Compose Container Orchestration    │ │
│  │                                                   │ │
│  │  ┌─────────────────┐  ┌─────────────────┐       │ │
│  │  │    StoryWeaver  │  │  Ollama/Mistral │       │ │
│  │  │   Container     │  │   Container     │       │ │
│  │  │                 │  │                 │       │ │
│  │  │ FastAPI         │  │ ollama:11434    │       │ │
│  │  │ :8000 (exposed) │  │ (local only)    │       │ │
│  │  │                 │  │                 │       │ │
│  │  │ + Frontend      │  │ Model: mistral  │       │ │
│  │  │   (built SvelteKit)                          │
│  │  │                 │  │                 │       │ │
│  │  └────────┬────────┘  └────────┬────────┘       │ │
│  │           │                    │               │ │
│  │           │    network          │               │ │
│  │           │    "storyweaver"    │               │ │
│  │           └────────┬──────────┬─┘               │ │
│  │                    │          │                │ │
│  │                    ▼          ▼                │ │
│  │  ┌──────────────────────────────────────┐     │ │
│  │  │      PostgreSQL Container           │     │ │
│  │  │                                      │     │ │
│  │  │  postgres:15                         │     │ │
│  │  │  DB: storyweaver                     │     │ │
│  │  │  Port: 5432 (internal only)         │     │ │
│  │  │                                      │     │ │
│  │  │  Volumes:                            │     │ │
│  │  │  └─ db_data:/var/lib/postgresql     │     │ │
│  │  └──────────────────────────────────────┘     │ │
│  │                                                │ │
│  │  Volumes (persistent):                        │ │
│  │  ├─ ollama_data:/root/.ollama                │ │
│  │  │  (LLM model weights)                       │ │
│  │  ├─ db_data:/var/lib/postgresql/data        │ │
│  │  │  (Novels, KB, manuscripts, versions)      │ │
│  │  └─ app_logs:/var/log/storyweaver           │ │
│  │     (Application logs)                        │ │
│  │                                                │ │
│  └───────────────────────────────────────────────┘ │
│                     │                               │ │
│                     │ Port 80/443 (nginx reverse    │ │
│                     │ proxy optional)              │ │
│                     ▼                               │ │
│  ┌────────────────────────────────────────────┐   │ │
│  │    Nginx Reverse Proxy (optional)          │   │ │
│  │    - SSL/TLS termination                   │   │ │
│  │    - localhost:8000 -> :443                │   │ │
│  │    - Rate limiting                         │   │ │
│  │    - Gzip compression                      │   │ │
│  └────────────────────────────────────────────┘   │ │
│                                                     │ │
│  ENV Variables:                                     │ │
│  - OLLAMA_URL=http://ollama:11434                 │ │
│  - DATABASE_URL=postgresql://...                   │ │
│  - SECRET_KEY=...                                  │ │
│  - DEBUG=false                                     │ │
│                                                     │ │
└─────────────────────────────────────────────────────┘
         │
         │ External Access
         │
         ▼
  ┌─────────────────┐
  │ Browser/Mobile  │
  │ https://vps.ip  │
  │ or domain       │
  └─────────────────┘

STARTUP SEQUENCE:

1. docker-compose up -d

2. PostgreSQL starts
   └─ Waits for DB to be ready

3. Ollama container starts
   └─ Loads mistral model (first time: ~4GB download)

4. StoryWeaver container starts
   ├─ Run alembic migrations (create/update schema)
   ├─ Start FastAPI server
   ├─ Build/serve SvelteKit frontend
   └─ Listening on :8000

5. Nginx (optional) starts
   └─ Routes :443 to localhost:8000

6. Health checks
   ├─ DB connection OK?
   ├─ Ollama responding?
   └─ API endpoints accessible?

MONITORING (optional add-ons):

- Prometheus: Metrics collection
  └─ API response times
  └─ Error rates
  └─ Container health

- Grafana: Dashboards
  └─ Visual monitoring

- ELK Stack: Logs
  └─ Elasticsearch
  └─ Logstash
  └─ Kibana

BACKUP STRATEGY:

Daily:
└─ Backup /db_data volume
   └─ Full database dump
   └─ All novels, KB, versions

Weekly:
└─ Backup /ollama_data (optional, large)
   └─ Or just re-download model if needed

Monthly:
└─ Full system snapshot
```

---

**Next: See TEST CHECKLIST document for detailed test cases.**
