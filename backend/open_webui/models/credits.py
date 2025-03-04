import time
import uuid
from decimal import Decimal
from typing import List, Optional

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import BigInteger, Column, Numeric, String

from open_webui.internal.db import Base, get_db

####################
# User Credit DB Schema
####################


class Credit(Base):
    __tablename__ = "credit"

    id = Column(String, primary_key=True)
    user_id = Column(String, unique=True, nullable=False)
    credit = Column(Numeric(precision=24, scale=12))

    updated_at = Column(BigInteger)
    created_at = Column(BigInteger)


####################
# Forms
####################


class CreditModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    user_id: str
    credit: Decimal = Field(default_factory=lambda: Decimal("0"))
    updated_at: int = Field(default_factory=lambda: int(time.time()))
    created_at: int = Field(default_factory=lambda: int(time.time()))


####################
# Tables
####################


class CreditsTable:
    def insert_new_credit(self, user_id: str) -> Optional[CreditModel]:
        try:
            credit = CreditModel(user_id=user_id)
            with get_db() as db:
                result = Credit(**credit.model_dump())
                db.add(result)
                db.commit()
                db.refresh(result)
                if credit:
                    return credit
                return None
        except Exception:
            return None

    def init_credit_by_user_id(self, user_id: str) -> Optional[CreditModel]:
        credit = self.get_credit_by_user_id(user_id=user_id) or self.insert_new_credit(user_id=user_id)
        if credit is not None:
            return credit
        raise HTTPException(status_code=500, detail="credit initialize failed")

    def get_credit_by_user_id(self, user_id: str) -> Optional[CreditModel]:
        try:
            with get_db() as db:
                credit = db.query(Credit).filter(Credit.user_id == user_id).first()
                return CreditModel.model_validate(credit)
        except Exception:
            return None

    def get_credits(self, user_ids: List[str]) -> List[CreditModel]:
        try:
            with get_db() as db:
                credits = db.query(Credit).filter(Credit.user_id.in_(user_ids)).all()
                return [CreditModel.model_validate(credit) for credit in credits]
        except Exception:
            return []

    def add_credit_by_user_id(self, user_id: str, amount: Decimal) -> Optional[CreditModel]:
        with get_db() as db:
            db.query(Credit).filter(Credit.user_id == user_id).update(
                {"credit": Credit.credit + amount, "updated_at": int(time.time())}, synchronize_session=False
            )
            db.commit()
        return self.get_credit_by_user_id(user_id=user_id)


Credits = CreditsTable()
