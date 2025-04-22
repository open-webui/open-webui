from enum import Enum
from typing import Optional

from open_webui.internal.db import Base, JSONField, get_db

from pydantic import BaseModel, ConfigDict
from sqlalchemy import Boolean, Column, String, JSON, Enum as SQLAlchemyEnum

####################
# Role DB Schema
####################

class PermissionCategory(str, Enum):
    workspace = "workspace"
    sharing = "sharing"
    chat = "chat"
    features = "features"

class Permission(Base):
    __tablename__ = "permissions"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    # workspace, sharing, chat, features
    category = Column(SQLAlchemyEnum(PermissionCategory), nullable=False)
    description = Column(String)
    default_value = Column(Boolean, default=False)


class PermissionsModel(BaseModel):
    id: int
    name: str
    category: PermissionCategory
    description: str | None
    default_value: bool

    model_config = ConfigDict(from_attributes=True)

####################
# Forms
####################

class PermissionsTable:
    def get_permissions_by_category(self) -> dict[PermissionCategory, list[PermissionsModel]]:
        with get_db() as db:

            query = db.query(Permission).order_by(Permission.id)
            all_permissions = query.all()

            # Group permissions by category
            permissions = {}
            for perm in all_permissions:
                if perm.category not in permissions:
                    permissions[perm.category] = {}

                permissions[perm.category][perm.name] = perm.default_value

            return permissions

Permissions = PermissionsTable()
