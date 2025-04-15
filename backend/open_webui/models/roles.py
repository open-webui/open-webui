import time
from typing import Optional

from pprint import pprint

from open_webui.internal.db import Base, JSONField, get_db

from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Column, String, Integer

####################
# Role DB Schema
####################


class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True)
    name = Column(String)

    updated_at = Column(BigInteger)
    created_at = Column(BigInteger)

class RoleModel(BaseModel):
    id: int
    name: str

    updated_at: int  # timestamp in epoch
    created_at: int  # timestamp in epoch

    model_config = ConfigDict(from_attributes=True)

####################
# Forms
####################

class RoleAddForm(BaseModel):
    role: str

class RolesTable:
    def insert_new_role(
        self,
        name: str,
    ) -> Optional[RoleModel]:
        with get_db() as db:
            result = Role(
                name=name,
                created_at=int(time.time()),
                updated_at=int(time.time())
            )
            db.add(result)
            db.commit()
            db.refresh(result)
            if result:
                return RoleModel.model_validate(result)
            else:
                return None

    def get_role_by_id(self, id: str) -> Optional[RoleModel]:
        try:
            with get_db() as db:
                role = db.query(Role).filter_by(id=id).first()
                return RoleModel.model_validate(role)
        except Exception:
            return None

    def get_role_by_name(self, name: str) -> Optional[RoleModel]:
        try:
            with get_db() as db:
                role = db.query(Role).filter_by(name=name).first()
                return RoleModel.model_validate(role)
        except Exception:
            return None

    def get_roles(
        self, skip: Optional[int] = None, limit: Optional[int] = None
    ) -> list[RoleModel]:
        with get_db() as db:

            query = db.query(Role).order_by(Role.id)

            if skip:
                query = query.offset(skip)
            if limit:
                query = query.limit(limit)

            roles = query.all()

            return [RoleModel.model_validate(role) for role in roles]

    def get_num_roles(self) -> Optional[int]:
        with get_db() as db:
            return db.query(Role).count()

    def delete_by_id(self, role_id: str) -> bool:
        try:
            with get_db() as db:
                db.query(Role).filter_by(id=role_id).delete()
                db.commit()

            return True
        except Exception:
            return False

Roles = RolesTable()
