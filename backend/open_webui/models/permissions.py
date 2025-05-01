from enum import Enum

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import relationship
from sqlalchemy import Column, String, Integer, Enum as SQLAlchemyEnum

from open_webui.internal.db import Base, get_db
from open_webui.models.roles import RolePermission, Role


####################
# Role DB Schema
####################

class PermissionCategory(str, Enum):
    workspace = "workspace"
    sharing = "sharing"
    chat = "chat"
    features = "features"


class RolePermissionModel(BaseModel):
    role_id: int
    permission_id: int
    value: bool = False

    model_config = ConfigDict(from_attributes=True)


class Permission(Base):
    __tablename__ = "permissions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    label = Column(String, nullable=False)
    category = Column(SQLAlchemyEnum(PermissionCategory), nullable=False)
    description = Column(String)

    role_associations = relationship("RolePermission", back_populates="permission")

    # Convenience property to access roles directly if needed
    @property
    def roles(self):
        return [assoc.role for assoc in self.role_associations]


class PermissionModel(BaseModel):
    id: int = Field(default=None)
    name: str
    label: str
    category: PermissionCategory
    description: str | None
    value: bool = False

    model_config = ConfigDict(from_attributes=True)

class PermissionEmptyModel(BaseModel):
    id: int = Field(default=None)
    name: str
    label: str
    category: PermissionCategory
    description: str | None

    model_config = ConfigDict(from_attributes=True)

class PermissionCreateModel(BaseModel):
    name: str
    label: str
    category: PermissionCategory
    description: str | None = None

    model_config = ConfigDict(from_attributes=True)

####################
# Forms
####################

class PermissionRoleForm(BaseModel):
    permission_name: str
    category: PermissionCategory
    value: bool = False

class PermissionAddForm(BaseModel):
    name: str
    label: str
    category: PermissionCategory
    description: str | None = None

####################
# Database operations
####################


class PermissionsTable:

    def get_ordre_by_category(self, role_name: str = "user") -> dict[PermissionCategory, dict[str, bool]]:
        with get_db() as db:
            result = {}

            # First, get the user role permissions as defaults if requesting permissions for a different role
            if role_name != "user":
                user_role = db.query(Role).filter_by(name="user").first()
                if user_role:
                    # Query the RolePermission association objects for the user role
                    user_role_permissions = db.query(RolePermission).filter_by(role_id=user_role.id).all()

                    # Create a mapping of permission_id to value for user role
                    user_permission_values = {rp.permission_id: rp.value for rp in user_role_permissions}

                    # Get all permissions associated with user role
                    user_permissions = db.query(Permission).filter(
                        Permission.id.in_([rp.permission_id for rp in user_role_permissions])
                    ).all()

                    # Build default permissions dictionary
                    for perm in user_permissions:
                        category = perm.category.value
                        if category not in result:
                            result[category] = {}

                        result[category][perm.name] = user_permission_values[perm.id]

            # Now get the specified role's permissions
            target_role = db.query(Role).filter_by(name=role_name).first()
            if not target_role:
                # Return user defaults if target role doesn't exist
                return result

            target_role_permissions = db.query(RolePermission).filter_by(role_id=target_role.id).all()
            target_permission_values = {rp.permission_id: rp.value for rp in target_role_permissions}
            target_permissions = db.query(Permission).filter(
                Permission.id.in_([rp.permission_id for rp in target_role_permissions])
            ).all()

            # Merge target role permissions with defaults
            for perm in target_permissions:
                category = perm.category.value
                if category not in result:
                    result[category] = {}

                # Override default with target role's value
                result[category][perm.name] = target_permission_values[perm.id]

            # Add all permissions from the permission table that are missing in the result
            # with a default value of False
            all_permissions = db.query(Permission).all()
            for perm in all_permissions:
                category = perm.category.value
                if category not in result:
                    result[category] = {}

                # Only add if not already in result
                if perm.name not in result[category]:
                    result[category][perm.name] = False

            return result

    # TODO: if config is not persistent enabled, just override permissions given
    def set_initial_permissions(self,
        default_permissions: dict[PermissionCategory, dict[str, bool]],
        default_labels: dict[PermissionCategory, dict[str, str]],
        role_name: str = "user"
    ) -> dict[PermissionCategory, dict[str, bool]]:
        with get_db() as db:
            # Check if any permissions exist
            existing_count = db.query(Permission).count()

            if existing_count == 0:
                role = db.query(Role).filter_by(name=role_name).order_by(Role.id).first()

                # No permissions exist, initialize with defaults
                for category_str, perms in default_permissions.items():
                    # Convert string category to enum
                    try:
                        category = PermissionCategory(category_str)
                    except ValueError:
                        continue  # Skip invalid categories

                    for perm_name, value in perms.items():
                        new_permission = Permission(
                            name=perm_name,
                            category=category,
                            label=default_labels[category_str][perm_name],
                            description=f"Default {category.value} permission for {perm_name}"
                        )
                        db.add(new_permission)
                        db.flush()

                        # Create the association with the value
                        role_permission = RolePermission(
                            role_id=role.id,
                            permission_id=new_permission.id,
                            value=value
                        )
                        db.add(role_permission)

                try:
                    db.commit()
                except Exception as e:
                    db.rollback()
                    raise e

            # Return current permissions structure
            return self.get_ordre_by_category()

    def get(self, permission_name: str, category: PermissionCategory):
        with get_db() as db:
            try:
                # Find the permission
                db_permission = db.query(Permission).filter_by(
                    name=permission_name,
                    category=category
                ).first()

                if not db_permission:
                    return None

                # Create and return a PermissionModel instance
                return PermissionModel(
                    id=db_permission.id,
                    name=db_permission.name,
                    label=db_permission.label,
                    category=db_permission.category,
                    description=db_permission.description,
                    # Default value to False as we don't have a role context
                    value=False
                )

            except Exception as e:
                print(f"Error getting permission: {e}")
                return None


    def get_all(self) -> list[PermissionEmptyModel]:
        with get_db() as db:
            try:
                # Query all permissions from the database
                db_permissions = db.query(Permission).all()

                # Convert database objects to PermissionModel instances
                permissions = [
                    PermissionEmptyModel(
                        id=p.id,
                        name=p.name,
                        label=p.label,
                        category=p.category,
                        description=p.description,
                    ) for p in db_permissions
                ]

                return permissions

            except Exception as e:
                print(f"Error getting all permissions: {e}")
                return []


    def add(self, permission: PermissionCreateModel) -> PermissionEmptyModel | None:
        with get_db() as db:
            try:
                existing_permission = db.query(Permission).filter_by(
                    name=permission.name,
                    category=permission.category
                ).first()

                if existing_permission:
                    # Permission exists.
                    return None

                new_permission = Permission(
                    name=permission.name,
                    label=permission.label,
                    category=permission.category,
                    description=permission.description,
                )
                db.add(new_permission)
                db.commit()
                db.refresh(new_permission)

                return PermissionEmptyModel.model_validate(new_permission)

            except Exception as e:
                print(f"Error adding permission: {e}")
                db.rollback()
                return None

    def update(self, permission: PermissionEmptyModel) -> PermissionEmptyModel | None:
        with get_db() as db:
            try:
                db_permission = db.query(Permission).filter_by(
                    name=permission['name'],
                    category=permission['category']
                ).first()

                if not db_permission:
                    return None

                if 'description' in permission:
                    db_permission.description = permission['description']

                db.commit()
                db.refresh(db_permission)

                return PermissionEmptyModel.model_validate(db_permission)

            except Exception as e:
                print(f"Error updating permission: {e}")
                db.rollback()
                return None

    def delete(self, permission_name: str, category: PermissionCategory) -> bool:
        with get_db() as db:
            try:
                # Find the permission
                db_permission = db.query(Permission).filter_by(
                    name=permission_name,
                    category=category
                ).first()

                if not db_permission:
                    return False

                # Delete all role associations first to avoid foreign key constraints
                db.query(RolePermission).filter_by(
                    permission_id=db_permission.id
                ).delete()

                # Then delete the permission itself
                db.delete(db_permission)
                db.commit()
                return True

            except Exception as e:
                print(f"Error deleting permission: {e}")
                db.rollback()
                return False

    def link(self, permission_id: int, role_id: int, value: bool = False) -> RolePermissionModel | None:
        with get_db() as db:
            try:
                # Check if permission exists
                permission = db.query(Permission).filter_by(id=permission_id).first()
                if not permission:
                    return None

                # Check if role exists
                role = db.query(Role).filter_by(id=role_id).first()
                if not role:
                    return None

                # Check if the link already exists
                existing_link = db.query(RolePermission).filter_by(
                    role_id=role_id,
                    permission_id=permission_id
                ).first()

                if existing_link:
                    # If link already exists, update its value
                    existing_link.value = value
                    db.commit()
                    return RolePermissionModel.model_validate(existing_link)

                # Create new association
                role_permission = RolePermission(
                    role_id=role_id,
                    permission_id=permission_id,
                    value=value
                )
                from pprint import pprint
                pprint(role_permission)

                db.add(role_permission)
                db.commit()
                db.refresh(role_permission)

                return RolePermissionModel.model_validate(role_permission)

            except Exception as e:
                print(f"Error linking permission to role: {e}")
                db.rollback()
                return None

    def unlink(self, permission_id: int, role_id: int) -> bool:
        with get_db() as db:
            try:
                # Find the association
                deleted = db.query(RolePermission).filter_by(
                    role_id=role_id,
                    permission_id=permission_id
                ).delete()

                db.commit()
                return deleted > 0

            except Exception as e:
                print(f"Error unlinking permission from role: {e}")
                db.rollback()
                return False

    def exists(self, permission: PermissionModel, role_name: str = "user") -> bool:
        with get_db() as db:
            # First find the role
            role = db.query(Role).filter_by(name=role_name).first()
            if not role:
                return False

            # Then check if there's a permission with this name and category
            db_permission = db.query(Permission).filter_by(
                name=permission['name'],
                category=permission['category']
            ).first()

            if not db_permission:
                return False

            # Finally, check if there's an association between them
            association = db.query(RolePermission).filter_by(
                role_id=role.id,
                permission_id=db_permission.id
            ).first()

            return association is not None


Permissions = PermissionsTable()
