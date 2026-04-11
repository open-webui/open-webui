import logging
import time
import uuid
from typing import Optional

from sqlalchemy.orm import Session
from open_webui.internal.db import Base, get_db_context

from pydantic import BaseModel, ConfigDict
from sqlalchemy import (
    BigInteger,
    Column,
    Text,
    Index,
    func,
)

log = logging.getLogger(__name__)

####################
# UsageLedger DB Schema
####################


class UsageLedgerEntry(Base):
    __tablename__ = 'usage_ledger'

    id = Column(Text, primary_key=True)
    user_id = Column(Text, nullable=False, index=True)
    model_id = Column(Text, nullable=True)
    input_tokens = Column(BigInteger, default=0)
    output_tokens = Column(BigInteger, default=0)
    created_at = Column(BigInteger, nullable=False, index=True)

    __table_args__ = (
        Index('usage_ledger_user_created_idx', 'user_id', 'created_at'),
    )


####################
# Pydantic Models
####################


class UsageLedgerModel(BaseModel):
    id: str
    user_id: str
    model_id: Optional[str] = None
    input_tokens: int = 0
    output_tokens: int = 0
    created_at: int

    model_config = ConfigDict(from_attributes=True)


####################
# UsageLedger Table Operations
####################


class UsageLedgerTable:
    def log_usage(
        self,
        user_id: str,
        model_id: Optional[str] = None,
        input_tokens: int = 0,
        output_tokens: int = 0,
        db: Optional[Session] = None,
    ) -> Optional[UsageLedgerModel]:
        """Append an immutable usage record. This is never deleted by user actions."""
        try:
            with get_db_context(db) as db:
                entry = UsageLedgerEntry(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    model_id=model_id,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    created_at=int(time.time()),
                )
                db.add(entry)
                db.commit()
                db.refresh(entry)
                return UsageLedgerModel.model_validate(entry)
        except Exception as e:
            log.warning(f'Failed to log usage: {e}')
            return None

    def get_user_usage_since(
        self,
        user_id: str,
        since: int,
        db: Optional[Session] = None,
    ) -> dict:
        """Get total token usage for a user since a given timestamp."""
        with get_db_context(db) as db:
            result = db.query(
                func.coalesce(func.sum(UsageLedgerEntry.input_tokens), 0).label('input_tokens'),
                func.coalesce(func.sum(UsageLedgerEntry.output_tokens), 0).label('output_tokens'),
            ).filter(
                UsageLedgerEntry.user_id == user_id,
                UsageLedgerEntry.created_at >= since,
            ).first()

            input_tokens = int(result.input_tokens) if result else 0
            output_tokens = int(result.output_tokens) if result else 0

            return {
                'input_tokens': input_tokens,
                'output_tokens': output_tokens,
                'total_tokens': input_tokens + output_tokens,
            }

    def get_user_usage_by_model_since(
        self,
        user_id: str,
        since: int,
        db: Optional[Session] = None,
    ) -> list[dict]:
        """Get token usage for a user broken down by model since a given timestamp."""
        with get_db_context(db) as db:
            results = db.query(
                UsageLedgerEntry.model_id,
                func.coalesce(func.sum(UsageLedgerEntry.input_tokens), 0).label('input_tokens'),
                func.coalesce(func.sum(UsageLedgerEntry.output_tokens), 0).label('output_tokens'),
            ).filter(
                UsageLedgerEntry.user_id == user_id,
                UsageLedgerEntry.created_at >= since,
            ).group_by(
                UsageLedgerEntry.model_id
            ).all()

            return [
                {
                    'model_id': r.model_id,
                    'input_tokens': int(r.input_tokens),
                    'output_tokens': int(r.output_tokens),
                    'total_tokens': int(r.input_tokens) + int(r.output_tokens),
                }
                for r in results
            ]


UsageLedger = UsageLedgerTable()
