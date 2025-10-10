import time
import uuid
from typing import Optional

from open_webui.internal.db import Base, get_db
from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Column, String, Text, JSON, Index

####################
# TEXT SELECTION: Database schema for storing user text selections
# - Stores selected text from chat messages for analysis and moderation
# - Links selections to users, chats, and specific messages
# - Supports both user prompts and assistant responses
####################

class Selection(Base):
    __tablename__ = "selection"
    
    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False)  # Link to user
    chat_id = Column(String, nullable=False)  # Link to chat
    message_id = Column(String, nullable=False)  # Link to specific message
    role = Column(String, nullable=False)  # 'user' or 'assistant'
    selected_text = Column(Text, nullable=False)  # The actual selected text
    child_id = Column(String, nullable=True)  # Link to child profile for kids mode
    context = Column(Text, nullable=True)  # Surrounding context for analysis
    meta = Column(JSON, nullable=True)  # Additional metadata (model used, timestamp, etc.)
    
    created_at = Column(BigInteger)  # When selection was made
    updated_at = Column(BigInteger)

    # Indexes for efficient querying
    __table_args__ = (
        Index('idx_selection_user_id', 'user_id'),
        Index('idx_selection_chat_id', 'chat_id'),
        Index('idx_selection_message_id', 'message_id'),
        Index('idx_selection_created_at', 'created_at'),
    )

class SelectionModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    user_id: str
    chat_id: str
    message_id: str
    role: str
    selected_text: str
    child_id: Optional[str] = None
    context: Optional[str] = None
    meta: Optional[dict] = None
    created_at: int
    updated_at: int

class SelectionForm(BaseModel):
    chat_id: str
    message_id: str
    role: str
    selected_text: str
    child_id: Optional[str] = None
    context: Optional[str] = None
    meta: Optional[dict] = None

class SelectionTable:
    def insert_new_selection(
        self, form_data: SelectionForm, user_id: str
    ) -> Optional[SelectionModel]:
        """Insert a new selection into the database"""
        with get_db() as db:
            id = str(uuid.uuid4())
            ts = int(time.time_ns())
            
            selection = SelectionModel(
                **{
                    "id": id,
                    "user_id": user_id,
                    "chat_id": form_data.chat_id,
                    "message_id": form_data.message_id,
                    "role": form_data.role,
                    "selected_text": form_data.selected_text,
                    "child_id": form_data.child_id,
                    "context": form_data.context,
                    "meta": form_data.meta,
                    "created_at": ts,
                    "updated_at": ts,
                }
            )
            
            result = Selection(**selection.model_dump())
            db.add(result)
            db.commit()
            db.refresh(result)
            return SelectionModel.model_validate(result) if result else None

    def get_selections_by_user(self, user_id: str, limit: int = 100) -> list[SelectionModel]:
        """Get all selections for a specific user"""
        with get_db() as db:
            selections = db.query(Selection).filter(
                Selection.user_id == user_id
            ).order_by(Selection.created_at.desc()).limit(limit).all()
            
            return [SelectionModel.model_validate(selection) for selection in selections]

    def get_selections_by_chat(self, chat_id: str) -> list[SelectionModel]:
        """Get all selections for a specific chat"""
        with get_db() as db:
            selections = db.query(Selection).filter(
                Selection.chat_id == chat_id
            ).order_by(Selection.created_at.asc()).all()
            
            return [SelectionModel.model_validate(selection) for selection in selections]

    def get_selections_for_analysis(
        self, 
        start_date: Optional[int] = None,
        end_date: Optional[int] = None,
        role: Optional[str] = None,
        limit: int = 1000
    ) -> list[SelectionModel]:
        """Get selections for cross-user analysis (admin only)"""
        with get_db() as db:
            query = db.query(Selection)
            
            if start_date:
                query = query.filter(Selection.created_at >= start_date)
            if end_date:
                query = query.filter(Selection.created_at <= end_date)
            if role:
                query = query.filter(Selection.role == role)
                
            selections = query.order_by(Selection.created_at.desc()).limit(limit).all()
            return [SelectionModel.model_validate(selection) for selection in selections]

    def delete_selection(self, selection_id: str, user_id: str) -> bool:
        """Delete a specific selection (user can only delete their own)"""
        with get_db() as db:
            selection = db.query(Selection).filter(
                Selection.id == selection_id,
                Selection.user_id == user_id
            ).first()
            
            if selection:
                db.delete(selection)
                db.commit()
                return True
            return False

    def get_selection_stats(self) -> dict:
        """Get statistics about selections for analytics"""
        with get_db() as db:
            total_selections = db.query(Selection).count()
            user_selections = db.query(Selection.user_id).distinct().count()
            assistant_selections = db.query(Selection).filter(Selection.role == 'assistant').count()
            user_role_selections = db.query(Selection).filter(Selection.role == 'user').count()
            
            return {
                "total_selections": total_selections,
                "unique_users": user_selections,
                "assistant_selections": assistant_selections,
                "user_selections": user_role_selections,
            }

# Global instance
Selections = SelectionTable()
