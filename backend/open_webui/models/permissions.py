from enum import Enum
from typing import Dict, Any

from open_webui.internal.db import Base, JSONField, get_db

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Boolean, Column, String, Integer, Enum as SQLAlchemyEnum

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

    id = Column(Integer, primary_key=True,  autoincrement=True)
    name = Column(String, nullable=False)
    # workspace, sharing, chat, features
    category = Column(SQLAlchemyEnum(PermissionCategory), nullable=False)
    description = Column(String)
    default_value = Column(Boolean, default=False)


class PermissionModel(BaseModel):
    id: int = Field(default=None, exclude=True)
    name: str
    category: PermissionCategory
    description: str | None
    default_value: bool

    model_config = ConfigDict(from_attributes=True)

####################
# Forms
####################

class PermissionsTable:
    def get_by_category(self) -> dict[PermissionCategory, dict[str, bool]]:
        with get_db() as db:

            query = db.query(Permission).order_by(Permission.id)
            all_permissions = query.all()

            # Group permissions by category
            permissions = {}
            for perm in all_permissions:
                if perm.category.value not in permissions:
                    permissions[perm.category.value] = {}

                permissions[perm.category.value][perm.name] = perm.default_value

            return permissions

    # TODO: if config is not persistent enabled, just return default permissions
    def get_or_create(self, default_permissions: dict[PermissionCategory, dict[str, bool]]) -> dict[PermissionCategory, dict[str, bool]]:
        with get_db() as db:
            # Check if any permissions exist
            existing_count = db.query(Permission).count()

            if existing_count == 0:
                # No permissions exist, initialize with defaults
                for category_str, perms in default_permissions.items():
                    # Convert string category to enum
                    try:
                        category = PermissionCategory(category_str)
                    except ValueError:
                        continue  # Skip invalid categories

                    for perm_name, default_value in perms.items():
                        new_permission = Permission(
                            name=perm_name,
                            category=category,
                            default_value=default_value,
                            description=f"Default {category.value} permission for {perm_name}"
                        )
                        db.add(new_permission)

                try:
                    db.commit()
                except Exception as e:
                    db.rollback()
                    raise e

            # Return current permissions structure
            return self.get_by_category()

    def add(self, permission: PermissionModel) -> PermissionModel | None:
        from pprint import pprint
        pprint(permission)
        with get_db() as db:
            result = Permission(
                name=permission['name'],
                category=permission['category'],
                description=permission['description'],
                default_value=permission['default_value']
            )
            db.add(result)
            db.commit()
            db.refresh(result)
            if result:
                return PermissionModel.model_validate(result)
            else:
                return None

    def update(self, permission: PermissionModel) -> PermissionModel | None:
        with get_db() as db:
            try:
                db_permission = db.query(Permission).filter_by(
                    name=permission['name'],
                    category=permission['category']
                ).first()

                if not db_permission:
                    return None

                db_permission.default_value = permission['default_value']
                if 'description' in permission:
                    db_permission.description = permission['description']

                db.commit()
                db.refresh(db_permission)

                return PermissionModel.model_validate(db_permission)

            except Exception:
                    db.rollback()
                    return None

    def exists(self, permission: PermissionModel) -> bool:
        with get_db() as db:
            result = db.query(Permission).filter_by(name=permission['name'], category=permission['category']).first()
            return result is not None

Permissions = PermissionsTable()
