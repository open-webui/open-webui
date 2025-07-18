import logging
from typing import Optional

from open_webui.env import SRC_LOG_LEVELS
from open_webui.internal.db import Base, get_db
from pydantic import BaseModel, ConfigDict, field_validator
from sqlalchemy import Boolean, Column, Integer, String
from sqlalchemy.exc import IntegrityError

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])


class Charity(Base):
    __tablename__ = "charity"

    id = Column(Integer, primary_key=True, autoincrement=True)
    charity_id = Column(Integer, unique=True, nullable=True)
    name = Column(String(512), index=True, nullable=False)
    website = Column(String, nullable=True)
    email = Column(String, nullable=True)
    is_imported = Column(Boolean, default=False)


class CharityModel(BaseModel):
    id: Optional[int] = None
    name: str
    charity_id: Optional[int] = None
    website: Optional[str] = None
    email: Optional[str] = None
    is_imported: bool = False

    model_config = ConfigDict(from_attributes=True)


class CharityResponse(BaseModel):
    id: int
    name: str
    charity_id: Optional[int] = None
    website: Optional[str] = None
    email: Optional[str] = None
    is_imported: bool = False


class CharityForm(BaseModel):
    name: str
    charity_id: Optional[int] = None
    website: Optional[str] = None
    email: Optional[str] = None
    is_imported: bool = False

    @field_validator("charity_id", mode="before")
    @classmethod
    def empty_str_to_none(cls, v):
        # Convert empty string to None
        if v is None or v == "":
            return None
        return v


class CharityListResponse(BaseModel):
    charities: list[CharityModel]
    total: int


class CharitiesTable:
    def add(
        self,
        form_data: CharityForm,
    ) -> Optional[CharityModel]:
        with get_db() as db:
            charity = CharityModel(
                **{
                    **form_data.model_dump(exclude_none=True),
                }
            )
            result = Charity(**charity.model_dump())
            db.add(result)
            db.commit()
            db.refresh(result)
            if result:
                return charity.copy(update={"id": result.id})
            else:
                return None

    def get_charity_by_id(self, id: int) -> Optional[CharityModel]:
        try:
            with get_db() as db:
                charity = db.query(Charity).filter_by(id=id).first()
                return CharityModel.model_validate(charity)
        except Exception:
            return None

    def get_charities(
        self,
        filter: Optional[dict] = None,
        skip: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> dict:
        with get_db() as db:
            query = db.query(Charity)

            if filter:
                query_key = filter.get("query")
                if query_key:
                    query = query.filter(Charity.name.ilike(f"%{query_key}%"))

                order_by = filter.get("order_by")
                direction = filter.get("direction")

                if order_by == "name":
                    if direction == "asc":
                        query = query.order_by(Charity.name.asc())
                    else:
                        query = query.order_by(Charity.name.desc())
                elif order_by == "email":
                    if direction == "asc":
                        query = query.order_by(Charity.email.asc())
                    else:
                        query = query.order_by(Charity.email.desc())
                elif order_by == "charity_id":
                    if direction == "asc":
                        query = query.order_by(Charity.charity_id.asc())
                    else:
                        query = query.order_by(Charity.charity_id.desc())
                elif order_by == "website":
                    if direction == "asc":
                        query = query.order_by(Charity.website.asc())
                    else:
                        query = query.order_by(Charity.website.desc())
                elif order_by == "is_imported":
                    if direction == "asc":
                        query = query.order_by(Charity.is_imported.asc())
                    else:
                        query = query.order_by(Charity.is_imported.desc())

            else:
                query = query.order_by(Charity.name.asc())

            if skip:
                query = query.offset(skip)
            if limit:
                query = query.limit(limit)

            charities = query.all()
            return {
                "charities": [CharityModel.model_validate(c) for c in charities],
                "total": db.query(Charity).count(),
            }

    def update_charity_by_id(
        self,
        id: str,
        form_data: CharityForm,
    ) -> Optional[CharityModel]:
        try:
            with get_db() as db:
                db.query(Charity).filter_by(id=id).update(
                    {
                        **form_data.model_dump(exclude_none=True),
                    }
                )
                db.commit()
                return self.get_charity_by_id(id=id)
        except IntegrityError:
            with get_db() as db:
                db.rollback()
            raise
        except Exception as e:
            log.exception(e)
            with get_db() as db:
                db.rollback()
            raise

    def delete_charity_by_id(self, id: str) -> bool:
        try:
            with get_db() as db:
                db.query(Charity).filter_by(id=id).delete()
                db.commit()
                return True
        except Exception:
            return False


Charities = CharitiesTable()
