import time

from typing import Optional
from pydantic import BaseModel, ConfigDict
from sqlalchemy import Boolean, BigInteger, Column, String, Integer, ForeignKey
from sqlalchemy.orm import relationship

from open_webui.internal.db import Base, get_db


####################
# Association table for the many-to-many relationship (role <-> permission) with value
####################
class RolePermission(Base):
    __tablename__ = 'role_permissions'

    role_id = Column(Integer, ForeignKey('roles.id'), primary_key=True)
    permission_id = Column(Integer, ForeignKey('permissions.id'), primary_key=True)
    value = Column(Boolean, default=False)

    # Add relationships to both sides
    role = relationship("Role", back_populates="permission_associations")
    permission = relationship("Permission", back_populates="role_associations")


####################
# Role DB Schema
####################

class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True)
    name = Column(String)
    updated_at = Column(BigInteger)
    created_at = Column(BigInteger)

    permission_associations = relationship("RolePermission", back_populates="role")

    @property
    def permissions(self):
        return [assoc.permission for assoc in self.permission_associations]


class RoleModel(BaseModel):
    id: int
    name: str
    updated_at: int
    created_at: int

    model_config = ConfigDict(from_attributes=True)


####################
# Forms
####################

class RoleForm(BaseModel):
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

    def update_name_by_id(self, role_id: str, name: str) -> Optional[RoleModel]:
        with get_db() as db:
            db.query(Role).filter_by(id=role_id).update(
                {"name": name, "updated_at": int(time.time())}
            )
            db.commit()
            return self.get_role_by_id(role_id)

    def get_roles(self, skip: Optional[int] = None, limit: Optional[int] = None) -> list[RoleModel]:
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

    def add_role_if_role_do_not_exists(self, role_name: str) -> Optional[RoleModel]:
        # Check if role already exists
        existing_role = self.get_role_by_name(role_name)
        if existing_role:
            return existing_role

        # Role is allowed and doesn't exist, so create it
        try:
            return self.insert_new_role(name=role_name)
        except Exception:
            return None

    def exists(self, role_name: str) -> bool:
        return self.get_role_by_name(role_name) is not None


Roles = RolesTable()
