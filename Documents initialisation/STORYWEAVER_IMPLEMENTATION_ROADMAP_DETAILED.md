# 📋 STORYWEAVER : Roadmap Détaillée - Tâches Sous-Atomiques

**Format:** Chaque tâche = 1-2 jours, indivisible, livrable concret  
**Dépendances:** Explicites pour chaque tâche  
**Critères d'acceptation:** Testable et vérifiable

---

## PHASE 1 : CORE INFRASTRUCTURE (2 semaines)

### Milestone 1.0 : Setup & Fork Initial

#### Task 1.0.1 : Fork OpenWebUI et Setup Git
**Durée:** 2 heures  
**Dépendances:** Compte GitHub  

**Actions:**
1. Créer fork privé de `open-webui/open-webui` sur GitHub
2. Créer `.gitignore` personnalisé (Python + Node)
3. Ajouter `DEVELOPMENT.md` (doc locale)
4. Initialiser branch `feature/storyweaver-core`
5. Cloner localement : `git clone https://github.com/YOUR_USERNAME/open-webui.git`

**Livrable:** Repo prêt, branche feature créée  
**Test:** `git log` affiche commits originaux, `git branch` affiche feature/storyweaver-core

---

#### Task 1.0.2 : Setup Environnement Dev Local
**Durée:** 3-4 heures  
**Dépendances:** Task 1.0.1  

**Actions:**
1. **Backend:**
   - Vérifier Python 3.10+
   - `cd open-webui && poetry install` (ou `pip install -r requirements.txt`)
   - Créer `.env.local` avec variables essentielles
   - Vérifier `poetry run python main.py` lance sans erreur
   - Tester endpoint Ollama/Mistral depuis backend

2. **Frontend:**
   - Vérifier Node.js 18+
   - `cd frontend && npm install`
   - Vérifier `npm run dev` lance dev server
   - Ouvrir `http://localhost:5173` dans navigateur

3. **Documentation:**
   - Noter versions Python/Node utilisées
   - Documenter étapes de setup dans DEVELOPMENT.md

**Livrable:** Dev env fully functional  
**Test:** 
```bash
# Backend
poetry run python main.py  # Doit lancé sans crash
curl http://localhost:8000/api/models  # Doit retourner JSON

# Frontend
npm run dev  # Doit afficher "Local: http://localhost:5173"
# Navigateur: page OpenWebUI chargée
```

---

#### Task 1.0.3 : Analyser Structure OpenWebUI Existante
**Durée:** 4-5 heures  
**Dépendances:** Task 1.0.2  

**Actions:**
1. **Mapping Backend:**
   - Tracer fichier `main.py` → endpoints clés
   - Identifier tous les routers (`routes/chat.py`, `routes/models.py`, etc.)
   - Documenter modèles Pydantic existants (User, Chat, Message)
   - Identifier DB layer (SQLAlchemy models, engine)
   - Noter où les tools sont registrés

2. **Mapping Frontend:**
   - Identifier structure composants (`src/lib/components/`)
   - Localiser store/state management
   - Tracer chat UI flow (input → message display)
   - Documenter navigation routes

3. **Documenter Architecture Existante:**
   - Créer `ARCHITECTURE_EXISTING.md` avec diagrammes textuels
   - Noter patterns utilisés (middleware, dependency injection, etc.)

**Livrable:** `ARCHITECTURE_EXISTING.md` + notes de compréhension  
**Test:** Pouvoir dessiner un diagramme ASCII des flows principaux

---

### Milestone 1.1 : Database Extensions

#### Task 1.1.1 : Créer Models Pydantic (Backend)
**Durée:** 3-4 heures  
**Dépendances:** Task 1.0.3  

**Actions:**
1. Créer fichier `backend/database/models_storyweaver.py`
2. Implémenter classes Pydantic + SQLAlchemy models:

```python
# Models à implémenter:

class Novel(Base):
    __tablename__ = "novels"
    id: UUID = Column(UUID(as_uuid=True), primary_key=True)
    user_id: str = Column(String, ForeignKey("user.id"))
    title: str = Column(String)
    description: str = Column(String, nullable=True)
    status: str = Column(String)  # draft, in-progress, completed, archived
    created_at: datetime = Column(DateTime, default=datetime.utcnow)
    updated_at: datetime = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    # Relationships
    knowledge_base: KnowledgeBase = relationship("KnowledgeBase", uselist=False)
    manuscript: Manuscript = relationship("Manuscript", uselist=False)
    conversations: list[Conversation] = relationship("Conversation")
    versions: list[Version] = relationship("Version")

class KnowledgeBase(Base):
    __tablename__ = "knowledge_bases"
    id: UUID = Column(UUID(as_uuid=True), primary_key=True)
    novel_id: UUID = Column(UUID(as_uuid=True), ForeignKey("novels.id"))
    universe_docs: dict = Column(JSON)  # Règles monde, lore
    characters: list[dict] = Column(JSON)  # Array de character objects
    locations: list[dict] = Column(JSON)  # Array de location objects
    objects: list[dict] = Column(JSON)  # Array d'object objects
    updated_at: datetime = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Manuscript(Base):
    __tablename__ = "manuscripts"
    id: UUID = Column(UUID(as_uuid=True), primary_key=True)
    novel_id: UUID = Column(UUID(as_uuid=True), ForeignKey("novels.id"))
    content: str = Column(Text)  # Markdown content
    chapter_structure: dict = Column(JSON)  # {chapters: [{title, scenes: [...]}]}
    word_count: int = Column(Integer, default=0)
    updated_at: datetime = Column(DateTime)

class Conversation(Base):  # Extension de Chat existant
    __tablename__ = "conversations"
    id: UUID = Column(UUID(as_uuid=True), primary_key=True)
    novel_id: UUID = Column(UUID(as_uuid=True), ForeignKey("novels.id"))
    chat_id: UUID = Column(UUID(as_uuid=True), ForeignKey("chat.id"))
    tags: list[str] = Column(JSON)  # #brainstorm, #structure, etc.
    context_level: str = Column(String)  # full, minimal, none
    linked_entities: dict = Column(JSON)  # {characters: [...], scenes: [...]}

class Version(Base):
    __tablename__ = "versions"
    id: UUID = Column(UUID(as_uuid=True), primary_key=True)
    novel_id: UUID = Column(UUID(as_uuid=True), ForeignKey("novels.id"))
    entity_type: str = Column(String)  # character, location, scene, universe
    entity_id: str = Column(String)
    old_data: dict = Column(JSON, nullable=True)
    new_data: dict = Column(JSON)
    change_type: str = Column(String)  # created, updated, deleted
    change_description: str = Column(String, nullable=True)
    timestamp: datetime = Column(DateTime, default=datetime.utcnow)
    version_number: int = Column(Integer)
    user_action: str = Column(String, nullable=True)  # Contexte utilisateur
```

3. Ajouter Pydantic schemas pour API (create, read, update)
4. Valider imports/syntaxe

**Livrable:** Fichier `models_storyweaver.py` compilable  
**Test:** 
```bash
poetry run python -c "from backend.database.models_storyweaver import Novel, KnowledgeBase; print('OK')"
```

---

#### Task 1.1.2 : Créer Migration DB (Alembic)
**Durée:** 2-3 heures  
**Dépendances:** Task 1.1.1  

**Actions:**
1. Vérifier Alembic déjà setup dans OpenWebUI (`alembic/versions/` exists)
2. Créer migration:
   ```bash
   cd backend
   alembic revision --autogenerate -m "Add novel, knowledge_base, manuscript, conversation, version tables"
   ```
3. Vérifier migration file généré dans `alembic/versions/`
4. **Important:** Éditer migration pour ajouter indexes:
   ```python
   op.create_index('idx_novels_user_id', 'novels', ['user_id'])
   op.create_index('idx_knowledge_bases_novel_id', 'knowledge_bases', ['novel_id'])
   op.create_index('idx_versions_novel_id', 'versions', ['novel_id'])
   op.create_index('idx_versions_entity_id', 'versions', ['entity_id'])
   ```
5. Tester migration localement:
   ```bash
   alembic upgrade head  # Doit réussir
   alembic downgrade -1  # Puis downgrade, doit réussir aussi
   alembic upgrade head  # Re-upgrade
   ```

**Livrable:** Migration file prêt et testé  
**Test:** DB contient tables `novels`, `knowledge_bases`, `manuscripts`, `conversations`, `versions`

---

#### Task 1.1.3 : Ajouter DAOs (Data Access Objects)
**Durée:** 3-4 heures  
**Dépendances:** Task 1.1.2  

**Actions:**
1. Créer `backend/database/daos.py`
2. Implémenter classe DAO pour chaque table:

```python
class NovelDAO:
    """Accès aux novels"""
    
    @staticmethod
    def create(session, user_id: str, title: str, description: str = None) -> Novel:
        novel = Novel(user_id=user_id, title=title, description=description, status="draft")
        session.add(novel)
        session.commit()
        return novel
    
    @staticmethod
    def get_by_id(session, novel_id: UUID) -> Optional[Novel]:
        return session.query(Novel).filter(Novel.id == novel_id).first()
    
    @staticmethod
    def list_by_user(session, user_id: str) -> list[Novel]:
        return session.query(Novel).filter(Novel.user_id == user_id).all()
    
    @staticmethod
    def update(session, novel_id: UUID, **kwargs) -> Novel:
        novel = session.query(Novel).filter(Novel.id == novel_id).first()
        for key, value in kwargs.items():
            setattr(novel, key, value)
        session.commit()
        return novel
    
    @staticmethod
    def delete(session, novel_id: UUID) -> bool:
        session.query(Novel).filter(Novel.id == novel_id).delete()
        session.commit()
        return True

class KnowledgeBaseDAO:
    """Accès à KB"""
    # Similaire...

class ManuscriptDAO:
    # Similaire...

class VersionDAO:
    """Historique des changements"""
    @staticmethod
    def create(session, novel_id: UUID, entity_type: str, entity_id: str, 
               old_data: dict, new_data: dict, change_type: str) -> Version:
        # Calculer version_number
        last_version = session.query(Version)\
            .filter(Version.entity_id == entity_id)\
            .order_by(Version.version_number.desc())\
            .first()
        version_number = (last_version.version_number + 1) if last_version else 1
        
        version = Version(
            novel_id=novel_id,
            entity_type=entity_type,
            entity_id=entity_id,
            old_data=old_data,
            new_data=new_data,
            change_type=change_type,
            version_number=version_number
        )
        session.add(version)
        session.commit()
        return version
    
    @staticmethod
    def get_history(session, entity_id: str, limit: int = 50) -> list[Version]:
        return session.query(Version)\
            .filter(Version.entity_id == entity_id)\
            .order_by(Version.version_number.desc())\
            .limit(limit)\
            .all()
```

3. Valider imports/syntaxe

**Livrable:** `daos.py` avec CRUD pour chaque table  
**Test:** 
```bash
poetry run python -c "from backend.database.daos import NovelDAO; print('OK')"
```

---

### Milestone 1.2 : API Routes Core

#### Task 1.2.1 : Créer Router Novels (CRUD)
**Durée:** 4 heures  
**Dépendances:** Task 1.1.3  

**Actions:**
1. Créer `backend/routes/novels.py`
2. Implémenter endpoints:

```python
from fastapi import APIRouter, Depends, HTTPException
from uuid import UUID
from backend.database.daos import NovelDAO

router = APIRouter(prefix="/api/novels", tags=["novels"])

@router.post("/")
async def create_novel(
    title: str,
    description: str = None,
    current_user: User = Depends(get_current_user),
    db = Depends(get_db)
) -> NovelResponse:
    """Créer un nouveau roman"""
    novel = NovelDAO.create(db, current_user.id, title, description)
    return NovelResponse.from_orm(novel)

@router.get("/")
async def list_novels(
    current_user: User = Depends(get_current_user),
    db = Depends(get_db)
) -> list[NovelResponse]:
    """Lister les romans de l'utilisateur"""
    novels = NovelDAO.list_by_user(db, current_user.id)
    return [NovelResponse.from_orm(n) for n in novels]

@router.get("/{novel_id}")
async def get_novel(
    novel_id: UUID,
    current_user: User = Depends(get_current_user),
    db = Depends(get_db)
) -> NovelResponse:
    """Récupérer détails d'un roman"""
    novel = NovelDAO.get_by_id(db, novel_id)
    if not novel or novel.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Novel not found")
    return NovelResponse.from_orm(novel)

@router.put("/{novel_id}")
async def update_novel(
    novel_id: UUID,
    update: NovelUpdate,
    current_user: User = Depends(get_current_user),
    db = Depends(get_db)
) -> NovelResponse:
    """Mettre à jour un roman"""
    novel = NovelDAO.get_by_id(db, novel_id)
    if not novel or novel.user_id != current_user.id:
        raise HTTPException(status_code=404)
    
    # Create version before update
    VersionDAO.create(db, novel_id, "novel", str(novel_id), 
                     novel.dict(), update.dict(exclude_unset=True), "updated")
    
    novel = NovelDAO.update(db, novel_id, **update.dict(exclude_unset=True))
    return NovelResponse.from_orm(novel)

@router.delete("/{novel_id}")
async def delete_novel(
    novel_id: UUID,
    current_user: User = Depends(get_current_user),
    db = Depends(get_db)
) -> dict:
    """Archiver/supprimer un roman"""
    novel = NovelDAO.get_by_id(db, novel_id)
    if not novel or novel.user_id != current_user.id:
        raise HTTPException(status_code=404)
    
    # Create version before delete
    VersionDAO.create(db, novel_id, "novel", str(novel_id), 
                     novel.dict(), {}, "deleted")
    
    NovelDAO.delete(db, novel_id)
    return {"status": "deleted"}
```

3. Ajouter Pydantic schemas (NovelResponse, NovelUpdate)
4. Ajouter router à `main.py`: `app.include_router(novels.router)`

**Livrable:** Router novels fonctionnel  
**Test:**
```bash
# Lancer serveur
poetry run python main.py

# Dans autre terminal, tester endpoints:
curl -X POST http://localhost:8000/api/novels/ \
  -H "Content-Type: application/json" \
  -d '{"title": "Test Novel", "description": "Test"}'
```

---

#### Task 1.2.2 : Créer Router Knowledge Base (CRUD)
**Durée:** 3-4 heures  
**Dépendances:** Task 1.2.1  

**Actions:**
1. Créer `backend/routes/knowledge_base.py`
2. Implémenter endpoints:

```python
router = APIRouter(prefix="/api/novels/{novel_id}/kb", tags=["knowledge-base"])

@router.get("/")
async def get_kb(
    novel_id: UUID,
    current_user: User = Depends(get_current_user),
    db = Depends(get_db)
) -> KnowledgeBaseResponse:
    """Récupérer KB complet d'un roman"""
    # Vérifier ownership
    novel = NovelDAO.get_by_id(db, novel_id)
    if not novel or novel.user_id != current_user.id:
        raise HTTPException(status_code=404)
    
    kb = KnowledgeBaseDAO.get_by_novel_id(db, novel_id)
    return KnowledgeBaseResponse.from_orm(kb)

@router.put("/universe")
async def update_universe(
    novel_id: UUID,
    universe_data: dict,
    current_user: User = Depends(get_current_user),
    db = Depends(get_db)
) -> KnowledgeBaseResponse:
    """Mettre à jour section Univers"""
    novel = NovelDAO.get_by_id(db, novel_id)
    if not novel or novel.user_id != current_user.id:
        raise HTTPException(status_code=404)
    
    kb = KnowledgeBaseDAO.get_by_novel_id(db, novel_id)
    old_universe = kb.universe_docs
    
    # Create version
    VersionDAO.create(db, novel_id, "kb_universe", str(novel_id),
                     {"universe": old_universe}, {"universe": universe_data}, "updated")
    
    kb.universe_docs = universe_data
    db.commit()
    return KnowledgeBaseResponse.from_orm(kb)

@router.post("/characters")
async def add_character(
    novel_id: UUID,
    character: CharacterInput,
    current_user: User = Depends(get_current_user),
    db = Depends(get_db)
) -> KnowledgeBaseResponse:
    """Ajouter un personnage"""
    kb = KnowledgeBaseDAO.get_by_novel_id(db, novel_id)
    
    # Create version
    VersionDAO.create(db, novel_id, "character", character.id,
                     {}, character.dict(), "created")
    
    kb.characters.append(character.dict())
    db.commit()
    return KnowledgeBaseResponse.from_orm(kb)

@router.put("/characters/{character_id}")
async def update_character(
    novel_id: UUID,
    character_id: str,
    update: CharacterInput,
    current_user: User = Depends(get_current_user),
    db = Depends(get_db)
) -> KnowledgeBaseResponse:
    """Mettre à jour un personnage"""
    kb = KnowledgeBaseDAO.get_by_novel_id(db, novel_id)
    
    # Trouver ancien personnage
    old_char = next((c for c in kb.characters if c["id"] == character_id), None)
    if not old_char:
        raise HTTPException(status_code=404, detail="Character not found")
    
    # Create version
    VersionDAO.create(db, novel_id, "character", character_id,
                     old_char, update.dict(), "updated")
    
    # Remplacer
    kb.characters = [update.dict() if c["id"] == character_id else c for c in kb.characters]
    db.commit()
    return KnowledgeBaseResponse.from_orm(kb)

@router.delete("/characters/{character_id}")
async def delete_character(
    novel_id: UUID,
    character_id: str,
    current_user: User = Depends(get_current_user),
    db = Depends(get_db)
) -> dict:
    """Supprimer un personnage"""
    kb = KnowledgeBaseDAO.get_by_novel_id(db, novel_id)
    
    old_char = next((c for c in kb.characters if c["id"] == character_id), None)
    if not old_char:
        raise HTTPException(status_code=404)
    
    VersionDAO.create(db, novel_id, "character", character_id,
                     old_char, {}, "deleted")
    
    kb.characters = [c for c in kb.characters if c["id"] != character_id]
    db.commit()
    return {"status": "deleted"}

# Répéter pour locations et objects
```

3. Ajouter schemas Pydantic (CharacterInput, LocationInput, etc.)

**Livrable:** Router KB avec CRUD complet  
**Test:** Tester chaque endpoint avec curl/Postman

---

#### Task 1.2.3 : Ajouter Session Management pour Novel Courant
**Durée:** 2-3 heures  
**Dépendances:** Task 1.2.2  

**Actions:**
1. Ajouter table `user_sessions` ou colonne à `user`:
   ```python
   class User(Base):
       current_novel_id: UUID = Column(UUID(as_uuid=True), nullable=True)
   ```
2. Créer endpoint pour "sélectionner" novel courant:
   ```python
   @router.post("/novels/{novel_id}/select")
   async def select_novel(
       novel_id: UUID,
       current_user: User = Depends(get_current_user),
       db = Depends(get_db)
   ) -> dict:
       # Vérifier ownership
       novel = NovelDAO.get_by_id(db, novel_id)
       if not novel or novel.user_id != current_user.id:
           raise HTTPException(status_code=404)
       
       # Update user
       current_user.current_novel_id = novel_id
       db.commit()
       return {"current_novel_id": str(novel_id)}
   ```

3. Créer dépendance pour récupérer novel courant:
   ```python
   async def get_current_novel(
       current_user: User = Depends(get_current_user),
       db = Depends(get_db)
   ) -> Novel:
       if not current_user.current_novel_id:
           raise HTTPException(status_code=400, detail="No novel selected")
       novel = NovelDAO.get_by_id(db, current_user.current_novel_id)
       if not novel or novel.user_id != current_user.id:
           raise HTTPException(status_code=404)
       return novel
   ```

**Livrable:** Session management pour novel courant  
**Test:** Pouvoir sélectionner un novel et l'utiliser comme contexte

---

### Milestone 1.3 : Context Injection System

#### Task 1.3.1 : Créer Prompt Builder
**Durée:** 3-4 heures  
**Dépendances:** Task 1.2.3  

**Actions:**
1. Créer `backend/utils/prompt_builder.py`
2. Implémenter fonction de construction dynamique du prompt:

```python
from backend.database.daos import (
    NovelDAO, KnowledgeBaseDAO, ManuscriptDAO, VersionDAO
)
from typing import Optional

class PromptBuilder:
    """Construit prompts enrichis avec contexte du roman"""
    
    BASE_SYSTEM_PROMPT = """Vous êtes un assistant créatif spécialisé dans l'assistance à la rédaction de roman.
Vous avez accès au contexte complet du projet en cours et devez l'utiliser pour :
1. Maintenir la cohérence narrative
2. Respecter l'univers défini
3. Cohérence des personnages et leurs arcs
4. Proposer des alternatives créatives pertinentes
5. Détecter et signaler les incohérences

Répondez de manière collaborative et constructive."""

    @staticmethod
    def format_universe(universe_docs: dict) -> str:
        """Format section Univers"""
        if not universe_docs:
            return "Aucun document univers défini."
        
        sections = []
        for section_name, section_content in universe_docs.items():
            sections.append(f"**{section_name}:**\n{section_content}")
        return "\n\n".join(sections)
    
    @staticmethod
    def format_characters(characters: list[dict], limit: int = 5) -> str:
        """Format section Personnages (top N by importance)"""
        if not characters:
            return "Aucun personnage défini."
        
        # Trier par importance (si existe), sinon prendre les premiers
        sorted_chars = characters[:limit]
        
        formatted = []
        for char in sorted_chars:
            char_str = f"""**{char.get('name', 'Unknown')}** (ID: {char.get('id')})
- Âge: {char.get('age', 'N/A')}
- Rôle: {char.get('role', 'N/A')}
- Traits: {', '.join(char.get('personality', []))}
- Arc: {char.get('arc_narrative', 'N/A')}
- Relations: {', '.join([r.get('character_id', 'unknown') for r in char.get('relationships', [])])}"""
            formatted.append(char_str)
        
        return "\n\n".join(formatted)
    
    @staticmethod
    def format_recent_scenes(manuscript_content: str, limit_lines: int = 500) -> str:
        """Extrait et formate scènes récentes du manuscrit"""
        if not manuscript_content:
            return "Aucun manuscrit."
        
        # Prendre les dernières N lignes (approximation des scènes récentes)
        lines = manuscript_content.split('\n')
        recent_lines = lines[-limit_lines:]
        recent_text = '\n'.join(recent_lines)
        
        return f"""[Passages récents du manuscrit]\n{recent_text}"""
    
    @staticmethod
    def format_conversation_history(messages: list[dict], limit: int = 8) -> str:
        """Format historique conversation"""
        if not messages:
            return "Pas d'historique de conversation."
        
        recent_messages = messages[-limit:]
        formatted = []
        for msg in recent_messages:
            role = msg.get('role', 'unknown')
            content = msg.get('content', '')[:200]  # Limiter à 200 chars par message
            formatted.append(f"**{role}:** {content}")
        
        return "\n".join(formatted)
    
    @classmethod
    def build_full_prompt(
        cls,
        novel_id: UUID,
        db,
        conversation_history: list[dict] = None,
        context_level: str = "full"  # full, minimal, none
    ) -> str:
        """
        Construit le prompt complet avec contexte injecté.
        context_level: full = tous contexte, minimal = perso + univers, none = juste base
        """
        if context_level == "none":
            return cls.BASE_SYSTEM_PROMPT
        
        # Charger données
        novel = NovelDAO.get_by_id(db, novel_id)
        if not novel:
            return cls.BASE_SYSTEM_PROMPT
        
        kb = KnowledgeBaseDAO.get_by_novel_id(db, novel_id)
        manuscript = ManuscriptDAO.get_by_novel_id(db, novel_id)
        
        # Construire sections
        prompt_parts = [cls.BASE_SYSTEM_PROMPT]
        
        if context_level in ["full", "minimal"]:
            # Univers
            prompt_parts.append(f"""### UNIVERS DU ROMAN : {novel.title}
{cls.format_universe(kb.universe_docs if kb else {})}""")
            
            # Personnages
            prompt_parts.append(f"""### PERSONNAGES CLÉS
{cls.format_characters(kb.characters if kb else [], limit=5)}""")
        
        if context_level == "full":
            # Scènes récentes
            prompt_parts.append(f"""### PASSAGES RÉCENTS DU MANUSCRIT
{cls.format_recent_scenes(manuscript.content if manuscript else "")}""")
            
            # Historique conversation
            if conversation_history:
                prompt_parts.append(f"""### HISTORIQUE CONVERSATION
{cls.format_conversation_history(conversation_history, limit=8)}""")
        
        return "\n\n".join(prompt_parts)
```

3. Tester construction de prompts

**Livrable:** `prompt_builder.py` compilable et testé  
**Test:**
```bash
poetry run python -c "from backend.utils.prompt_builder import PromptBuilder; print(PromptBuilder.BASE_SYSTEM_PROMPT)"
```

---

#### Task 1.3.2 : Intégrer Context Injection dans Route Chat
**Durée:** 4-5 heures  
**Dépendances:** Task 1.3.1  

**Actions:**
1. Localiser `backend/routes/chat.py` (OpenWebUI existant)
2. Modifier le endpoint POST `/api/chat/completions` pour:
   - Récupérer `novel_id` du user courant
   - Appeler `PromptBuilder.build_full_prompt()`
   - Injecter le prompt construit dans la requête Ollama

```python
# Exemple modification (adapter à la structure OpenWebUI existante)

@router.post("/completions")
async def chat_completions(
    request: ChatCompletionRequest,
    current_user: User = Depends(get_current_user),
    db = Depends(get_db)
):
    # Récupérer novel courant
    if not current_user.current_novel_id:
        # Mode normal OpenWebUI
        response = await call_ollama_directly(request)
        return response
    
    # Récupérer historique conversation
    chat_history = db.query(Message)\
        .filter(Message.chat_id == request.chat_id)\
        .order_by(Message.created_at.desc())\
        .limit(10)\
        .all()
    
    conversation_history = [
        {"role": msg.role, "content": msg.content}
        for msg in reversed(chat_history)
    ]
    
    # Construire prompt enrichi
    injected_prompt = PromptBuilder.build_full_prompt(
        current_user.current_novel_id,
        db,
        conversation_history,
        context_level="full"
    )
    
    # Modifier request : remplacer ou préfixer le system message
    modified_request = request.copy()
    modified_request.messages = [
        {"role": "system", "content": injected_prompt}
    ] + request.messages
    
    # Appeler Ollama
    response = await call_ollama(modified_request)
    
    # Sauvegarder snapshot du contexte injecté
    ContextSnapshotDAO.create(
        db,
        request.chat_id,
        current_user.current_novel_id,
        injected_context={"prompt": injected_prompt},
        kb_snapshot=KnowledgeBaseDAO.get_by_novel_id(db, current_user.current_novel_id).dict()
    )
    
    return response
```

3. Créer DAO pour context snapshots:
   ```python
   class ContextSnapshotDAO:
       @staticmethod
       def create(session, chat_id, novel_id, injected_context, kb_snapshot):
           snapshot = ContextSnapshot(...)
           session.add(snapshot)
           session.commit()
           return snapshot
   ```

**Livrable:** Route chat modifiée avec injection contextuelle  
**Test:** 
```bash
# Sélectionner novel, puis faire chat request
# Vérifier que prompt contient infos univers/personnages
```

---

### Milestone 1.4 : Frontend Integration (Novel Manager)

#### Task 1.4.1 : Créer Composant Novel Selector (Svelte)
**Durée:** 3-4 heures  
**Dépendances:** Task 1.2.1  

**Actions:**
1. Créer `frontend/src/lib/components/NovelSelector.svelte`

```svelte
<script>
  import { onMount } from 'svelte';
  import { currentNovel, novels } from '$lib/stores/novels';
  
  let isOpen = false;
  let loading = false;
  let selectedNovelId = null;
  
  onMount(async () => {
    await fetchNovels();
  });
  
  async function fetchNovels() {
    loading = true;
    const response = await fetch('/api/novels/');
    $novels = await response.json();
    loading = false;
  }
  
  async function selectNovel(novelId) {
    const response = await fetch(`/api/novels/${novelId}/select`, {
      method: 'POST'
    });
    const result = await response.json();
    currentNovel.set($novels.find(n => n.id === novelId));
    isOpen = false;
  }
  
  async function createNovel() {
    const title = prompt('Nom du roman:');
    if (!title) return;
    
    const response = await fetch('/api/novels/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title })
    });
    const newNovel = await response.json();
    $novels = [...$novels, newNovel];
  }
</script>

<div class="novel-selector">
  <button 
    on:click={() => isOpen = !isOpen}
    class="selector-button"
  >
    📖 {$currentNovel?.title || 'Select Novel'}
  </button>
  
  {#if isOpen}
    <div class="dropdown-menu">
      <div class="menu-header">Your Novels</div>
      
      {#if loading}
        <div class="loading">Loading...</div>
      {:else}
        {#each $novels as novel (novel.id)}
          <button
            class="novel-item"
            class:active={$currentNovel?.id === novel.id}
            on:click={() => selectNovel(novel.id)}
          >
            <span>{novel.title}</span>
            <span class="status">{novel.status}</span>
          </button>
        {/each}
      {/if}
      
      <button class="create-btn" on:click={createNovel}>
        + New Novel
      </button>
    </div>
  {/if}
</div>

<style>
  .novel-selector {
    position: relative;
    display: inline-block;
  }
  
  .selector-button {
    padding: 8px 16px;
    background: var(--primary-bg);
    border: 1px solid var(--border-color);
    border-radius: 6px;
    cursor: pointer;
    font-size: 14px;
    font-weight: 500;
  }
  
  .dropdown-menu {
    position: absolute;
    top: 100%;
    left: 0;
    background: white;
    border: 1px solid var(--border-color);
    border-radius: 6px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    min-width: 200px;
    z-index: 1000;
    margin-top: 4px;
  }
  
  .menu-header {
    padding: 12px 16px;
    border-bottom: 1px solid var(--border-color);
    font-weight: 600;
    font-size: 12px;
    text-transform: uppercase;
    color: var(--text-secondary);
  }
  
  .novel-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    width: 100%;
    padding: 10px 16px;
    border: none;
    background: none;
    cursor: pointer;
    font-size: 14px;
    text-align: left;
    transition: background 0.2s;
  }
  
  .novel-item:hover {
    background: var(--hover-bg);
  }
  
  .novel-item.active {
    background: var(--primary-light);
    font-weight: 600;
  }
  
  .status {
    font-size: 11px;
    color: var(--text-secondary);
    margin-left: 8px;
  }
  
  .create-btn {
    width: 100%;
    padding: 10px 16px;
    border: none;
    background: var(--primary-bg);
    border-top: 1px solid var(--border-color);
    cursor: pointer;
    font-size: 14px;
    font-weight: 500;
    color: var(--primary-color);
  }
  
  .create-btn:hover {
    background: var(--primary-light);
  }
  
  .loading {
    padding: 16px;
    text-align: center;
    color: var(--text-secondary);
  }
</style>
```

2. Créer `frontend/src/lib/stores/novels.ts`:
```typescript
import { writable } from 'svelte/store';

export const novels = writable([]);
export const currentNovel = writable(null);
```

3. Intégrer NovelSelector dans layout principal (`+layout.svelte`)

**Livrable:** Composant NovelSelector fonctionnel  
**Test:** Novel dropdown apparaît, peut créer/sélectionner novels

---

#### Task 1.4.2 : Modifier Chat UI pour Afficher Contexte Novel
**Durée:** 2-3 heures  
**Dépendances:** Task 1.4.1  

**Actions:**
1. Localiser composant chat principal (`frontend/src/lib/components/Chat.svelte`)
2. Ajouter badge/info affichant novel courant:
```svelte
{#if $currentNovel}
  <div class="chat-context-header">
    <span class="novel-badge">📖 {$currentNovel.title}</span>
    <span class="context-info">
      {$currentNovel.characters?.length || 0} characters · 
      Last updated: {new Date($currentNovel.updated_at).toLocaleDateString()}
    </span>
  </div>
{/if}
```

3. Ajouter info visuelle quand contexte est injecté (optionnel):
   - Petite icône "🔗 Context injected" à côté de assistant message

**Livrable:** Chat UI affiche novel courant et contexte  
**Test:** Quand novel sélectionné, info visible en haut du chat

---

#### Task 1.4.3 : Créer Stub pour Future Knowledge Base Panel
**Durée:** 1-2 heures  
**Dépendances:** Task 1.4.2  

**Actions:**
1. Créer `frontend/src/lib/components/KnowledgeBasePanel.svelte` (skeleton for now):

```svelte
<script>
  import { currentNovel } from '$lib/stores/novels';
</script>

<div class="kb-panel">
  <h3>Knowledge Base</h3>
  
  {#if $currentNovel}
    <div class="kb-tabs">
      <button class="tab active">Universe</button>
      <button class="tab">Characters</button>
      <button class="tab">Locations</button>
      <button class="tab">Objects</button>
      <button class="tab">Timeline</button>
    </div>
    
    <div class="kb-content">
      <p style="color: var(--text-secondary); font-style: italic;">
        Knowledge Base UI coming soon...
      </p>
    </div>
  {:else}
    <p style="color: var(--text-secondary);">Select a novel first</p>
  {/if}
</div>

<style>
  .kb-panel {
    padding: 16px;
    border-left: 1px solid var(--border-color);
    overflow-y: auto;
  }
  
  h3 {
    margin: 0 0 12px 0;
    font-size: 14px;
    font-weight: 600;
  }
  
  .kb-tabs {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
    margin-bottom: 12px;
    border-bottom: 1px solid var(--border-color);
  }
  
  .tab {
    padding: 6px 12px;
    border: none;
    background: none;
    cursor: pointer;
    font-size: 12px;
    font-weight: 500;
    color: var(--text-secondary);
    border-bottom: 2px solid transparent;
    margin-bottom: -1px;
  }
  
  .tab:hover {
    color: var(--text-primary);
  }
  
  .tab.active {
    color: var(--primary-color);
    border-bottom-color: var(--primary-color);
  }
</style>
```

2. Intégrer panel dans layout principal (sidebar droit)

**Livrable:** Placeholder KB panel visible  
**Test:** Panel visible, tabs affichés

---

### Milestone 1.5 : Testing & Polish

#### Task 1.5.1 : Écrire Tests Unitaires DAOs
**Durée:** 3-4 heures  
**Dépendances:** Task 1.1.3  

**Actions:**
1. Créer `backend/tests/test_daos.py`
2. Tester chaque DAO avec SQLite test DB:

```python
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.database.models_storyweaver import Base, Novel, KnowledgeBase
from backend.database.daos import NovelDAO, KnowledgeBaseDAO
from uuid import uuid4

@pytest.fixture
def test_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()

def test_novel_create(test_db):
    novel = NovelDAO.create(test_db, "user_123", "Test Novel", "Description")
    assert novel.title == "Test Novel"
    assert novel.status == "draft"
    
def test_novel_list(test_db):
    NovelDAO.create(test_db, "user_123", "Novel 1")
    NovelDAO.create(test_db, "user_123", "Novel 2")
    novels = NovelDAO.list_by_user(test_db, "user_123")
    assert len(novels) == 2

def test_novel_update(test_db):
    novel = NovelDAO.create(test_db, "user_123", "Original Title")
    NovelDAO.update(test_db, novel.id, title="New Title")
    updated = NovelDAO.get_by_id(test_db, novel.id)
    assert updated.title == "New Title"
```

3. Lancer tests: `poetry run pytest backend/tests/`

**Livrable:** Tests passing pour DAOs  
**Test:** Tous les tests passent

---

#### Task 1.5.2 : Écrire Tests API Endpoints
**Durée:** 3-4 heures  
**Dépendances:** Task 1.2.1  

**Actions:**
1. Créer `backend/tests/test_api_novels.py`
2. Utiliser TestClient de FastAPI:

```python
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_create_novel():
    response = client.post(
        "/api/novels/",
        json={"title": "Test Novel", "description": "Test"}
    )
    assert response.status_code == 200
    assert response.json()["title"] == "Test Novel"

def test_list_novels():
    response = client.get("/api/novels/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_get_novel_not_found():
    response = client.get("/api/novels/nonexistent-id")
    assert response.status_code == 404
```

3. Lancer tests: `poetry run pytest backend/tests/test_api_novels.py`

**Livrable:** Tests API passing  
**Test:** Tous tests passent

---

#### Task 1.5.3 : Documentation Backend
**Durée:** 2 heures  
**Dépendances:** Task 1.3.2  

**Actions:**
1. Créer `backend/STORYWEAVER_API.md` documentant:
   - Endpoints disponibles
   - Paramètres, responses (exemples)
   - Flow d'authentification
   - Gestion des erreurs

2. Exemples:
```markdown
## POST /api/novels/
Créer un nouveau roman.

**Request:**
```json
{
  "title": "My Novel",
  "description": "Optional description"
}
```

**Response (200):**
```json
{
  "id": "uuid",
  "title": "My Novel",
  "status": "draft",
  "created_at": "2024-04-01T10:00:00Z"
}
```

## POST /api/novels/{novel_id}/select
Sélectionner un roman comme contexte courant.
...
```

**Livrable:** API documentation complète  
**Test:** Peut facilement tester chaque endpoint

---

#### Task 1.5.4 : Manual Testing & QA Phase 1
**Durée:** 4 heures  
**Dépendances:** Toutes les tâches précédentes  

**Actions:**
1. **Checklist functionnelle:**
   - [ ] Créer roman → Affiche dans liste
   - [ ] Sélectionner roman → Marque comme courant
   - [ ] Créer personnage dans KB → Sauvegardé
   - [ ] Modifier personnage → Sauvegardé
   - [ ] Chat avec novel sélectionné → Contexte injecté dans prompt
   - [ ] Vérifier version history créée
   - [ ] Vérifier snapshots contexte créés

2. **Tester avec cas réels:**
   - Créer roman "Fantasy World"
   - Ajouter univers rules
   - Ajouter personnages
   - Faire chat avec questions sur univers
   - Vérifier réponses tiennent compte du contexte

3. **Documenter tous les bugs trouvés**

**Livrable:** QA report + bug list  
**Test:** Tous les checks passent (ou bugs documentés)

---

### Milestone 1.6 : Deployment & Documentation

#### Task 1.6.1 : Préparer Deployment sur VPS
**Durée:** 2-3 heures  
**Dépendances:** Task 1.5.4  

**Actions:**
1. Créer `Dockerfile` pour containerize OpenWebUI + modifications:
```dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY backend/ backend/
COPY frontend/ frontend/

# Build frontend
WORKDIR /app/frontend
RUN npm install && npm run build

WORKDIR /app
EXPOSE 8000
CMD ["poetry", "run", "python", "main.py"]
```

2. Créer `docker-compose.yml`:
```yaml
version: '3.8'
services:
  storyweaver:
    build: .
    ports:
      - "8000:8000"
    environment:
      - OLLAMA_URL=http://ollama:11434
      - DATABASE_URL=postgresql://user:pass@db:5432/storyweaver
    depends_on:
      - ollama
      - db
    
  ollama:
    image: ollama/ollama:latest
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama
  
  db:
    image: postgres:15
    environment:
      POSTGRES_DB: storyweaver
      POSTGRES_USER: storyweaver
      POSTGRES_PASSWORD: secure_password
    volumes:
      - db_data:/var/lib/postgresql/data

volumes:
  ollama_data:
  db_data:
```

3. Créer `.env.production` template

**Livrable:** Docker setup ready  
**Test:** `docker-compose up` lance tous services

---

#### Task 1.6.2 : Créer Documentation Setup pour Développeur
**Durée:** 2 heures  
**Dépendances:** Task 1.6.1  

**Actions:**
1. Créer/mettre à jour `DEVELOPMENT.md`:
```markdown
# StoryWeaver Development Guide

## Quick Start

1. Clone repository
2. `poetry install` + `npm install`
3. `poetry run python main.py`
4. `npm run dev`
5. Open http://localhost:5173

## Database

Run migrations:
```bash
cd backend
alembic upgrade head
```

## Testing

```bash
poetry run pytest
```

## Deployment

```bash
docker-compose up
```

See DEPLOYMENT.md for VPS setup.
```

2. Créer `DEPLOYMENT.md` pour setup VPS

**Livrable:** Documentation de dev/deploy  
**Test:** Nouveau dev peut suivre et lancer le projet

---

#### Task 1.6.3 : Commit & Push Phase 1
**Durée:** 1 heure  
**Dépendances:** Task 1.6.2  

**Actions:**
1. Commit all changes:
```bash
git add .
git commit -m "feat: Phase 1 - Core infrastructure

- Novel multi-project management (CRUD)
- Knowledge Base storage (characters, universe, etc.)
- Context injection into LLM prompts
- Versioning system for tracking changes
- Session management for novel selection
- Frontend Novel Selector component
- API endpoints fully tested
- Documentation complete"
```

2. Push to branch:
```bash
git push origin feature/storyweaver-core
```

3. Créer pull request sur GitHub (pour review)

**Livrable:** Phase 1 commitée et pushée  
**Test:** Code visible sur GitHub branch

---

## PHASE 2 : KNOWLEDGE BASE EDITOR (2 semaines)

### Milestone 2.1 : KB UI Components

#### Task 2.1.1 : Créer KnowledgeBaseEditor.svelte Principal
**Durée:** 4-5 heures  
**Dépendances:** Phase 1 complète  

**Actions:**
1. Créer `frontend/src/lib/components/KnowledgeBaseEditor.svelte`
2. Implémenter:
   - Tabs pour Universe/Characters/Locations/Objects/Timeline
   - Tab Universe : éditeur texte enrichi (JSON ou Markdown)
   - Save/Cancel buttons
   - Auto-save (optionnel)

```svelte
<script>
  import { currentNovel } from '$lib/stores/novels';
  import { currentKB, savingKB } from '$lib/stores/knowledgeBase';
  
  let activeTab = 'universe';
  let unsavedChanges = false;
  
  async function loadKB() {
    const response = await fetch(`/api/novels/${$currentNovel.id}/kb/`);
    const kb = await response.json();
    currentKB.set(kb);
  }
  
  async function saveKB() {
    savingKB.set(true);
    const response = await fetch(
      `/api/novels/${$currentNovel.id}/kb/${activeTab}`,
      {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify($currentKB[activeTab])
      }
    );
    savingKB.set(false);
    unsavedChanges = false;
  }
</script>

<div class="kb-editor">
  <div class="kb-header">
    <h2>Knowledge Base</h2>
    {#if unsavedChanges}
      <div class="unsaved-indicator">● Unsaved Changes</div>
    {/if}
  </div>
  
  <div class="kb-tabs">
    <button
      class="tab"
      class:active={activeTab === 'universe'}
      on:click={() => activeTab = 'universe'}
    >
      🌍 Universe
    </button>
    <!-- ... other tabs ... -->
  </div>
  
  <div class="kb-content">
    {#if activeTab === 'universe'}
      <UniverseEditor />
    {/if}
  </div>
  
  <div class="kb-footer">
    <button
      disabled={!unsavedChanges || $savingKB}
      on:click={saveKB}
    >
      {$savingKB ? 'Saving...' : 'Save'}
    </button>
  </div>
</div>
```

3. Créer `KnowledgeBaseStore.ts`:
```typescript
export const currentKB = writable(null);
export const savingKB = writable(false);
```

**Livrable:** KB Editor main component  
**Test:** Peut éditer et sauvegarder univers

---

#### Task 2.1.2 : Créer UniverseEditor Sub-Component
**Durée:** 3-4 heures  
**Dépendances:** Task 2.1.1  

**Actions:**
1. Créer `UniverseEditor.svelte`
2. Utiliser éditeur texte (Monaco ou CodeMirror)
3. Format JSON/Markdown editable
4. Real-time preview

```svelte
<script>
  import { currentKB } from '$lib/stores/knowledgeBase';
  import JSONEditor from 'jsoneditor';
  
  let editor;
  
  function handleChange(content) {
    currentKB.update(kb => ({
      ...kb,
      universe_docs: content
    }));
  }
</script>

<div class="universe-editor">
  <div class="editor-section">
    <div bind:this={editor} />
  </div>
  <div class="preview-section">
    <div class="preview-content">
      <!-- Rendu formaté de universe_docs -->
    </div>
  </div>
</div>
```

**Livrable:** Universe editor fonctionnel  
**Test:** Peut éditer rules, voir preview

---

#### Task 2.1.3 : Créer CharacterManager Sub-Component
**Durée:** 4-5 heures  
**Dépendances:** Task 2.1.1  

**Actions:**
1. Créer `CharacterManager.svelte`
2. Implémenter:
   - Liste personnages (searchable)
   - Character form (créer/éditer)
   - Champs: name, age, appearance, personality, arc, relationships
   - Multi-select pour relationships
   - Delete button
   - Version history button

```svelte
<script>
  import { currentKB } from '$lib/stores/knowledgeBase';
  
  let selectedCharacterId = null;
  let showForm = false;
  let searchQuery = '';
  
  let formData = {
    id: '',
    name: '',
    age: '',
    appearance: '',
    personality: [],
    arc_narrative: '',
    relationships: []
  };
  
  function openCharacterForm(character = null) {
    if (character) {
      formData = { ...character };
      selectedCharacterId = character.id;
    } else {
      formData = { id: generateId(), ...initialForm };
      selectedCharacterId = null;
    }
    showForm = true;
  }
  
  async function saveCharacter() {
    const endpoint = selectedCharacterId ? 'PUT' : 'POST';
    const response = await fetch(
      `/api/novels/${$currentNovel.id}/kb/characters/${formData.id}`,
      {
        method: endpoint,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData)
      }
    );
    const result = await response.json();
    currentKB.set(result);
    showForm = false;
  }
  
  async function deleteCharacter(characterId) {
    if (!confirm('Delete character?')) return;
    const response = await fetch(
      `/api/novels/${$currentNovel.id}/kb/characters/${characterId}`,
      { method: 'DELETE' }
    );
    const result = await response.json();
    currentKB.set(result);
  }
</script>

<div class="character-manager">
  <div class="characters-list">
    <input type="text" placeholder="Search..." bind:value={searchQuery} />
    
    {#each filteredCharacters as char (char.id)}
      <div
        class="character-item"
        class:selected={selectedCharacterId === char.id}
        on:click={() => openCharacterForm(char)}
      >
        <div class="char-name">{char.name}</div>
        <div class="char-role">{char.role}</div>
      </div>
    {/each}
    
    <button class="add-character" on:click={() => openCharacterForm()}>
      + Add Character
    </button>
  </div>
  
  {#if showForm}
    <div class="character-form">
      <input bind:value={formData.name} placeholder="Name" />
      <input bind:value={formData.age} placeholder="Age" />
      <textarea bind:value={formData.appearance} placeholder="Appearance" />
      
      <!-- Traits, Arc, Relationships inputs... -->
      
      <button on:click={saveCharacter}>Save</button>
      <button on:click={() => showForm = false}>Cancel</button>
      
      {#if selectedCharacterId}
        <button on:click={() => deleteCharacter(selectedCharacterId)}>Delete</button>
      {/if}
    </div>
  {/if}
</div>
```

**Livrable:** Character Manager complet  
**Test:** Créer/éditer/supprimer personnages

---

#### Task 2.1.4 : Créer LocationManager & ObjectManager (Similar)
**Durée:** 3 heures  
**Dépendances:** Task 2.1.3  

**Actions:**
1. Créer `LocationManager.svelte` (basé sur CharacterManager)
2. Créer `ObjectManager.svelte`
3. Adaptations minimales (moins de champs)

**Livrable:** Location & Object managers  
**Test:** Créer/éditer/supprimer lieux & objets

---

### Milestone 2.2 : Versioning Frontend

#### Task 2.2.1 : Créer VersionHistory Component
**Durée:** 3-4 heures  
**Dépendances:** Phase 1 + DAOs versioning  

**Actions:**
1. Créer `VersionHistory.svelte`
2. Afficher timeline des changements d'une entité
3. Comparer versions (diff view)
4. Option "Revert to version"

```svelte
<script>
  let entityId = '';
  let versions = [];
  let selectedVersion = null;
  let compareVersion = null;
  
  async function loadVersions() {
    const response = await fetch(
      `/api/novels/${$currentNovel.id}/versions/${entityId}`
    );
    versions = await response.json();
  }
  
  async function revertToVersion(versionNumber) {
    if (!confirm('Revert to this version?')) return;
    const response = await fetch(
      `/api/novels/${$currentNovel.id}/versions/${entityId}/${versionNumber}/revert`,
      { method: 'POST' }
    );
    const result = await response.json();
    // Reload
    loadVersions();
  }
</script>

<div class="version-history">
  <div class="timeline">
    {#each versions as version (version.id)}
      <div class="timeline-item">
        <div class="timestamp">{new Date(version.timestamp).toLocaleString()}</div>
        <div class="change-type">{version.change_type}</div>
        <button on:click={() => selectedVersion = version}>View</button>
        {#if version.change_type !== 'current'}
          <button on:click={() => revertToVersion(version.version_number)}>Revert</button>
        {/if}
      </div>
    {/each}
  </div>
  
  {#if selectedVersion}
    <div class="version-details">
      <h4>Changes in this version</h4>
      <div class="diff-view">
        <!-- Afficher diff old vs new -->
      </div>
    </div>
  {/if}
</div>
```

**Livrable:** Version History UI  
**Test:** Voir historique, revenir à versions antérieures

---

#### Task 2.2.2 : Ajouter Endpoint Versioning Backend
**Durée:** 2-3 heures  
**Dépendances:** Task 2.2.1  

**Actions:**
1. Ajouter à `backend/routes/`:
```python
@router.get("/novels/{novel_id}/versions/{entity_id}")
async def get_entity_versions(
    novel_id: UUID,
    entity_id: str,
    current_user: User = Depends(get_current_user),
    db = Depends(get_db)
) -> list[VersionResponse]:
    versions = VersionDAO.get_history(db, entity_id)
    return [VersionResponse.from_orm(v) for v in versions]

@router.post("/novels/{novel_id}/versions/{entity_id}/{version_number}/revert")
async def revert_to_version(
    novel_id: UUID,
    entity_id: str,
    version_number: int,
    current_user: User = Depends(get_current_user),
    db = Depends(get_db)
) -> dict:
    # Find version
    version = db.query(Version)\
        .filter(Version.entity_id == entity_id, Version.version_number == version_number)\
        .first()
    if not version:
        raise HTTPException(status_code=404)
    
    # Create new version for revert action
    VersionDAO.create(db, novel_id, version.entity_type, entity_id,
                     version.new_data, version.old_data, "reverted")
    
    # Update entity with old data
    # (dépend du type d'entité)
    
    return {"status": "reverted"}
```

**Livrable:** Versioning endpoints  
**Test:** Revert fonctionne

---

### Milestone 2.3 : Search & Linking

#### Task 2.3.1 : Implémenter Full-Text Search KB
**Durée:** 3 heures  
**Dépendances:** Task 2.1.1  

**Actions:**
1. Créer `SearchKB.svelte` component
2. Ajouter endpoint backend:
```python
@router.get("/novels/{novel_id}/kb/search")
async def search_kb(
    novel_id: UUID,
    query: str,
    current_user: User = Depends(get_current_user),
    db = Depends(get_db)
) -> SearchResults:
    """Full-text search dans KB"""
    kb = KnowledgeBaseDAO.get_by_novel_id(db, novel_id)
    query_lower = query.lower()
    
    results = {
        "characters": [c for c in kb.characters if query_lower in c.get("name", "").lower()],
        "locations": [l for l in kb.locations if query_lower in l.get("name", "").lower()],
        "objects": [o for o in kb.objects if query_lower in o.get("name", "").lower()]
    }
    
    return results
```

**Livrable:** Search KB  
**Test:** Rechercher personnages/lieux

---

#### Task 2.3.2 : Créer Auto-Linking (Relationships)
**Durée:** 2-3 heures  
**Dépendances:** Task 2.3.1  

**Actions:**
1. Quand éditer personnage, multi-select pour relationships
2. Pouvoir lier vers autres personnages, lieux, objets
3. Afficher graphe de relations (optionnel)

**Livrable:** Relationships linking  
**Test:** Personnages liés à d'autres

---

### Milestone 2.4 : Testing Phase 2

#### Task 2.4.1 : Tests KB API & UI
**Durée:** 3 heures  
**Dépendances:** Tasks 2.1.x, 2.2.x  

**Actions:**
1. Écrire tests unitaires pour API KB
2. Tests d'intégration pour UI (Vitest/Playwright)
3. QA manual

**Livrable:** Tests passing, KB fully functional  

---

#### Task 2.4.2 : Commit Phase 2
**Durée:** 1 heure  

**Actions:**
```bash
git add .
git commit -m "feat: Phase 2 - Knowledge Base Editor

- Comprehensive KB UI (Universe, Characters, Locations, Objects)
- Full versioning and revert system
- Search and auto-linking
- Tests complete"
git push origin feature/storyweaver-core
```

---

## PHASE 3 : CUSTOM TOOLS & MODULES (2 semaines)

### Milestone 3.1 : Custom Tools Implementation

#### Task 3.1.1 : Implémenter Novel Context Injector Tool
**Durée:** 3-4 heures  
**Dépendances:** Phase 1 complète  

**Actions:**
1. Créer `backend/tools/novel_context_injector.py`
2. (Déjà en partie fait dans Task 1.3.1)
3. Intégrer réellement dans OpenWebUI tools system
4. Tester que contexte bien injecté

**Livrable:** Tool fonctionnel  
**Test:** Context visible dans réponses IA

---

#### Task 3.1.2 : Implémenter Brainstorm Tool
**Durée:** 3-4 heures  
**Dépendances:** Task 3.1.1  

**Actions:**
1. Créer `backend/tools/brainstorm.py`
2. Accessible via `/brainstorm` command dans chat
3. Génère N idées créatives avec contexte

```python
@tool
def brainstorm_ideas(
    novel_id: UUID,
    theme: str,
    count: int = 5
) -> BrainstormResponse:
    """Brainstorm creative ideas for a theme"""
    # Implementation from Task 1.3.1
```

4. Test avec différents thèmes

**Livrable:** Brainstorm tool working  
**Test:** `/brainstorm plot twist` génère idées

---

#### Task 3.1.3 : Implémenter Coherence Checker Tool
**Durée:** 3-4 heures  
**Dépendances:** Task 3.1.1  

**Actions:**
1. Créer `backend/tools/coherence_checker.py`
2. Analyse texte pour incohérences
3. Accessible via `/analyze` command

**Livrable:** Coherence checker working  
**Test:** Détecter contradictions

---

#### Task 3.1.4 : Implémenter Dialogue Generator Tool
**Durée:** 3 heures  
**Dépendances:** Task 3.1.1  

**Actions:**
1. Créer `backend/tools/dialogue_generator.py`
2. Basé sur personnages KB
3. Accessible via `/dialogue` command

**Livrable:** Dialogue tool  
**Test:** Génère dialogues pertinents

---

#### Task 3.1.5 : Implémenter Outline Generator Tool
**Durée:** 3 heures  
**Dépendances:** Task 3.1.1  

**Actions:**
1. Créer `backend/tools/outline_generator.py`
2. Templates 3-act, 5-act, 7-point
3. Accessible via `/outline` command

**Livrable:** Outline tool  
**Test:** Génère outlines structurés

---

### Milestone 3.2 : Tools UI Integration

#### Task 3.2.1 : Créer Tools Toolbar dans Chat
**Durée:** 3 heures  
**Dépendances:** Phase 2 + Tasks 3.1.x  

**Actions:**
1. Créer `ToolsToolbar.svelte`
2. Boutons pour chaque tool (/brainstorm, /analyze, etc.)
3. Intégrer dans chat interface

```svelte
<div class="tools-toolbar">
  <button on:click={() => insertCommand('/brainstorm ')}>💭 Brainstorm</button>
  <button on:click={() => insertCommand('/analyze ')}>🔍 Analyze</button>
  <button on:click={() => insertCommand('/dialogue ')}>💬 Dialogue</button>
  <button on:click={() => insertCommand('/outline ')}>📋 Outline</button>
</div>
```

**Livrable:** Tools accessible from chat  
**Test:** Can click buttons, inserts commands

---

#### Task 3.2.2 : Créer Tool Result Components (Pretty Display)
**Durée:** 2-3 heures  
**Dépendances:** Task 3.2.1  

**Actions:**
1. Créer composants pour afficher résultats tools:
   - BrainstormResult.svelte (liste idées)
   - OutlineResult.svelte (structure chapitres)
   - DialogueResult.svelte (dialogue formaté)
   - AnalysisResult.svelte (issues list)

**Livrable:** Pretty tool result displays  
**Test:** Résultats bien formatés

---

### Milestone 3.3 : Testing Phase 3

#### Task 3.3.1 : Tools Testing
**Durée:** 3 heures  
**Dépendances:** Tasks 3.1.x + 3.2.x  

**Actions:**
1. Test chaque tool manuellement
2. Vérifier contexte bien utilisé
3. QA pour pertinence des résultats

**Livrable:** All tools working  

---

#### Task 3.3.2 : Commit Phase 3
**Durée:** 1 heure  

```bash
git add .
git commit -m "feat: Phase 3 - Custom Tools & Modules

- 5 specialized tools (brainstorm, coherence, dialogue, outline, analyze)
- Tools toolbar in chat UI
- Pretty result displays
- Full integration with context"
git push
```

---

## PHASE 4 : MANUSCRIPT EDITOR & POLISH (1.5 semaines)

### Milestone 4.1 : Manuscript Editor

#### Task 4.1.1 : Créer Manuscript Editor Component
**Durée:** 4-5 heures  
**Dépendances:** Phase 2 + Phase 3  

**Actions:**
1. Créer `ManuscriptEditor.svelte`
2. Éditeur Markdown avec syntax highlighting
3. Arborescence chapitre/scène dans sidebar
4. Word count, status selector

```svelte
<div class="manuscript-editor">
  <div class="sidebar">
    <!-- Chapter/Scene tree -->
  </div>
  <div class="editor">
    <MonacoEditor bind:value={manuscriptContent} />
  </div>
  <div class="toolbar">
    <span>Words: {wordCount}</span>
    <select bind:value={sceneStatus}>
      <option>draft</option>
      <option>editing</option>
      <option>final</option>
    </select>
    <button on:click={saveScene}>Save</button>
  </div>
</div>
```

**Livrable:** Manuscript editor functional  
**Test:** Can edit, save, word count works

---

#### Task 4.1.2 : Ajouter Quick Actions Buttons
**Durée:** 2-3 heures  
**Dépendances:** Task 4.1.1  

**Actions:**
1. Ajouter boutons:
   - "Analyze Passage" → Appelle `/analyze` tool
   - "Continue Scene" → Brainstorm continuation
   - "Generate Dialogue" → `/dialogue` tool
   - "Check Coherence" → `/analyze` tool

**Livrable:** Quick action buttons  
**Test:** Buttons work, launch tools

---

#### Task 4.1.3 : Sync Manuscript avec Chat
**Durée:** 2-3 heures  
**Dépendances:** Task 4.1.2  

**Actions:**
1. Quand user sélectionne texte dans éditeur
2. Peut directement discuter avec IA sur ce passage
3. IA a contexte de la scène

**Livrable:** Selection → Chat context  
**Test:** Can discuss selected text with IA

---

### Milestone 4.2 : UI Polish & Layout

#### Task 4.2.1 : Créer Main Layout (3-Panel)
**Durée:** 3-4 heures  
**Dépendances:** Tasks 4.1.x, Phase 2, Phase 3  

**Actions:**
1. Créer layout tripartite:
   - Left: Chat (80% height) + Tools toolbar
   - Center: Manuscript editor
   - Right: Knowledge Base panel (collapsible)

2. Responsive design (mobile fallback)

```svelte
<div class="storyweaver-layout">
  <header>
    <NovelSelector />
    <!-- Navigation -->
  </header>
  
  <main>
    <div class="left-panel">
      <ChatUI />
    </div>
    <div class="center-panel">
      <ManuscriptEditor />
    </div>
    <div class="right-panel">
      <KnowledgeBasePanel />
    </div>
  </main>
</div>
```

**Livrable:** Full layout implemented  
**Test:** All panels visible, responsive

---

#### Task 4.2.2 : Implement Panel Visibility Toggles
**Durée:** 2 heures  
**Dépendances:** Task 4.2.1  

**Actions:**
1. User can toggle each panel
2. Remember preferences (localStorage)
3. Preset layouts (Full interface, Writer focus, Research mode, Outline view)

**Livrable:** Layout customization  
**Test:** Can toggle panels, layouts switch

---

### Milestone 4.3 : Export & Final Features

#### Task 4.3.1 : Implémenter Export Manuscript
**Durée:** 3-4 heures  
**Dépendances:** Task 4.1.1  

**Actions:**
1. Export options:
   - Markdown (.md)
   - PDF (.pdf)
   - Plain text (.txt)
   - ePub (.epub) optionnel

2. Backend endpoint:
```python
@router.get("/novels/{novel_id}/manuscript/export")
async def export_manuscript(
    novel_id: UUID,
    format: str = "markdown"
) -> FileResponse:
    manuscript = ManuscriptDAO.get_by_novel_id(db, novel_id)
    
    if format == "markdown":
        return create_markdown_file(manuscript)
    elif format == "pdf":
        return create_pdf_file(manuscript)
```

**Livrable:** Export functionality  
**Test:** Can export to different formats

---

#### Task 4.3.2 : Implémenter Project Archive/Restore
**Durée:** 2 heures  
**Dépendances:** Phase 1  

**Actions:**
1. Archive button → Status = "archived"
2. Archived projects:
   - Pas en liste défaut
   - Peut restaurer
   - Peut réutiliser pour nouveau project

```python
@router.post("/novels/{novel_id}/archive")
@router.post("/novels/{novel_id}/restore")
```

**Livrable:** Archive/restore working  
**Test:** Can archive and restore novels

---

### Milestone 4.4 : Final Testing & Polish

#### Task 4.4.1 : Full Integration Testing
**Durée:** 4-5 heures  
**Dépendances:** Toutes les tâches précédentes  

**Actions:**
1. Test complete workflow:
   - Créer roman
   - Ajouter univers/personnages
   - Écrire scène
   - Brainstorm idées
   - Analyser passage
   - Générer dialogue
   - Check cohérence
   - Exporter

2. Test sur different browsers, VPS environment

3. Performance testing (latency, memory)

**Livrable:** Full QA report  
**Test:** Tous les workflows work end-to-end

---

#### Task 4.4.2 : Créer User Guide & Tutorials
**Durée:** 3-4 heures  
**Dépendances:** Task 4.4.1  

**Actions:**
1. Créer `USER_GUIDE.md`
2. Screenshots avec annotations
3. Video tutorials (optionnel)
4. FAQ

**Livrable:** Complete user documentation  

---

#### Task 4.4.3 : Final Deployment
**Durée:** 2 heures  
**Dépendances:** Task 4.4.2  

**Actions:**
1. Faire migrations sur VPS PostgreSQL
2. Build Docker image
3. Deploy via docker-compose
4. Smoke tests sur prod

```bash
# On VPS
docker-compose pull
docker-compose up -d
# Test http://your-vps-ip:8000
```

**Livrable:** StoryWeaver live on VPS  
**Test:** Accessible, fully functional

---

#### Task 4.4.4 : Final Commit & Release
**Durée:** 1 heure  

```bash
git add .
git commit -m "feat: Phase 4 - Manuscript Editor & Final Polish

- Full manuscript editor with Markdown support
- Quick action buttons (analyze, continue, dialogue, etc.)
- 3-panel responsive layout with toggles
- Export to multiple formats
- Project archive/restore
- Complete user guide
- Deployed to VPS"

# Tag release
git tag -a v1.0 -m "StoryWeaver v1.0 - First release"
git push origin --all
git push origin --tags
```

**Livrable:** v1.0 released  
**Test:** Tag visible on GitHub

---

## 📊 RÉSUMÉ PHASES

| Phase | Tâches | Durée | Output |
|-------|--------|-------|--------|
| **Phase 1** | 16 tâches | 2 sem | Core infra + novel management + context injection |
| **Phase 2** | 12 tâches | 2 sem | KB editor complète + versioning |
| **Phase 3** | 8 tâches | 2 sem | 5 tools spécialisés + toolbar |
| **Phase 4** | 8 tâches | 1.5 sem | Manuscript editor + export + polish + deploy |
| **TOTAL** | **44 tâches** | **7.5 sem** | **StoryWeaver v1.0** |

---

## 🎯 CRITÈRES D'ACCEPTATION PAR PHASE

### Phase 1 ✅
- [ ] Novel CRUD fully functional
- [ ] KB storage working (characters, universe)
- [ ] Context injection into prompts verified
- [ ] Versioning system tracking changes
- [ ] Session management selecting novels
- [ ] All API endpoints tested
- [ ] Frontend Novel Selector working
- [ ] Code deployed locally and tested

### Phase 2 ✅
- [ ] KB Editor UI complete (all tabs)
- [ ] Full-text search KB working
- [ ] Character/Location/Object management complete
- [ ] Version history and revert functional
- [ ] Relationships/linking working
- [ ] All CRUD operations tested
- [ ] No data loss on operations

### Phase 3 ✅
- [ ] All 5 tools implemented and tested
- [ ] Tools accessible from chat UI
- [ ] Context properly passed to each tool
- [ ] Results displayed nicely
- [ ] Tools return relevant outputs
- [ ] Performance acceptable

### Phase 4 ✅
- [ ] Manuscript editor functional
- [ ] Quick actions buttons working
- [ ] 3-panel layout responsive
- [ ] Export to multiple formats working
- [ ] Archive/restore projects
- [ ] Full end-to-end workflow tested
- [ ] Deployed to VPS
- [ ] Documentation complete

---

## 🚀 HOW TO USE THIS ROADMAP

1. **Copy each Task checklist** into your project management tool (Jira, Trello, Notion, etc.)
2. **Assign to self** with due dates (2 days per task average)
3. **Track progress** as you go
4. **Cross off** when criteria met
5. **Document blockers** immediately
6. **Commit at end of each Milestone** (not phase)

---

**Next step: Start Phase 1, Task 1.0.1 today! 🚀**
