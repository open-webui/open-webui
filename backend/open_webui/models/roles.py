import time
from typing import Optional

from open_webui.internal.db import Base, JSONField, get_db

from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Column, String, Text

####################
# Role DB Schema
####################


class Role(Base):
    __tablename__ = "roles"

    id = Column(String, primary_key=True)
    name = Column(String)

    updated_at = Column(BigInteger)
    created_at = Column(BigInteger)

class RoleModel(BaseModel):
    id: str
    name: str

    updated_at: int  # timestamp in epoch
    created_at: int  # timestamp in epoch

class RolesTable:
    def insert_new_role(
        self,
        id: str,
        name: str,
    ) -> Optional[RoleModel]:
        with get_db() as db:
            role = RoleModel(
                **{
                    "id": id,
                    "name": name,
                    "created_at": int(time.time()),
                    "updated_at": int(time.time()),
                }
            )
            result = Role(**role.model_dump())
            db.add(result)
            db.commit()
            db.refresh(result)
            if result:
                return role
            else:
                return None

    def get_role_by_id(self, id: str) -> Optional[RoleModel]:
        try:
            with get_db() as db:
                role = db.query(Role).filter_by(id=id).first()
                return RoleModel.model_validate(role)
        except Exception:
            return None

    def get_roles(
        self, skip: Optional[int] = None, limit: Optional[int] = None
    ) -> list[RoleModel]:
        with get_db() as db:

            query = db.query(Role).order_by(Role.created_at.desc())

            if skip:
                query = query.offset(skip)
            if limit:
                query = query.limit(limit)

            roles = query.all()

            return [RoleModel.model_validate(role) for role in roles]

    def get_num_roles(self) -> Optional[int]:
        with get_db() as db:
            return db.query(Role).count()


Roles = RolesTable()
