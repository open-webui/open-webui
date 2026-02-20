"""
Role-Based Access Control (RBAC) Models

This module provides custom role management with:
- Role: Named permission sets (admin, auditor, model-manager, etc.)
- RoleCapability: Admin-tier capabilities assigned to roles

The role system extends the existing group-based permissions by adding:
1. Named roles that can be assigned to users
2. Role-level capabilities for admin-tier actions
3. Permission hierarchy: Role (base) + Groups (additive overrides)
"""

import logging
import time
import uuid
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import BigInteger, Boolean, Column, Text, ForeignKey, JSON, Index

from open_webui.internal.db import Base, get_db_context
from pydantic import BaseModel, ConfigDict

log = logging.getLogger(__name__)


####################
# System Capabilities
####################

# These are the admin-tier capabilities that can be assigned to roles
# Derived from ~200 hardcoded `user.role == "admin"` checks in the codebase
SYSTEM_CAPABILITIES = {
    # User & System Management (from current admin checks)
    "admin.manage_users": "Create, update, delete users and change their roles",
    "admin.manage_groups": "Create, update, delete groups and manage memberships",
    "admin.manage_roles": "Create, update, delete custom roles and assign capabilities",
    "admin.manage_connections": "Configure Ollama, OpenAI, Anthropic connections",
    "admin.manage_config": "Access and modify system-wide configuration",
    "admin.manage_pipelines": "Create, update, delete pipelines",
    "admin.manage_functions": "Create, update, delete functions",
    "admin.manage_evaluations": "Manage arena models and leaderboards",
    "admin.bypass_access_control": "Access workspace content (models, knowledge, tools) regardless of ownership",
    # Audit & Compliance (new capabilities for enterprise use cases)
    "audit.read_user_chats": "Read-only access to all user chat conversations",
    "audit.view_analytics": "Access analytics dashboard and usage statistics",
    "audit.export_data": "Export chats, analytics, and system data",
    # Delegated Workspace Management (for team leads / managers)
    "workspace.manage_all_models": "Manage all models regardless of ownership",
    "workspace.manage_all_knowledge": "Manage all knowledge bases regardless of ownership",
    "workspace.manage_all_tools": "Manage all tools regardless of ownership",
    "workspace.manage_all_prompts": "Manage all prompts regardless of ownership",
    "workspace.manage_all_skills": "Manage all skills regardless of ownership",
    "workspace.manage_all_spaces": "Manage all spaces regardless of ownership",
    "workspace.manage_all_files": "Manage all files regardless of ownership",
    "workspace.manage_all_channels": "Manage all channels regardless of ownership",
}


####################
# Role DB Schema
####################


class Role(Base):
    """
    Role represents a named permission set that can be assigned to users.

    Each role has:
    - permissions: JSON matching the Group.permissions schema (user-facing features)
    - capabilities: Linked via RoleCapability for admin-tier actions
    - priority: Higher priority wins when resolving conflicts
    - is_system: Protected system roles (admin, user, pending) cannot be deleted
    """

    __tablename__ = "role"

    id = Column(Text, primary_key=True)
    name = Column(Text, unique=True, nullable=False)
    description = Column(Text, nullable=True)

    # Permissions JSON - same schema as Group.permissions
    # Controls user-facing feature toggles (workspace, sharing, chat, features, settings)
    permissions = Column(JSON, nullable=True)

    # System role flag - protected from deletion/modification
    is_system = Column(Boolean, default=False, nullable=False)

    # Priority for conflict resolution (higher wins)
    # System roles: admin=1000, user=100, pending=0
    priority = Column(BigInteger, default=0, nullable=False)

    created_at = Column(BigInteger, nullable=False)
    updated_at = Column(BigInteger, nullable=False)

    __table_args__ = (
        Index("role_name_idx", "name"),
        Index("role_priority_idx", "priority"),
    )


class RoleModel(BaseModel):
    """Pydantic model for Role."""

    id: str
    name: str
    description: Optional[str] = None
    permissions: Optional[dict] = None
    is_system: bool = False
    priority: int = 0
    created_at: int
    updated_at: int

    model_config = ConfigDict(from_attributes=True)


####################
# RoleCapability DB Schema
####################


class RoleCapability(Base):
    """
    RoleCapability links admin-tier capabilities to roles.

    Capabilities are distinct from permissions:
    - Permissions: User-facing feature toggles (can user use chat TTS? can user share?)
    - Capabilities: Admin-tier actions (can role manage users? can role read all chats?)

    This separation allows creating roles like "Compliance Auditor" that can
    read user chats (capability) without having full admin access.
    """

    __tablename__ = "role_capability"

    id = Column(Text, primary_key=True)
    role_id = Column(
        Text,
        ForeignKey("role.id", ondelete="CASCADE"),
        nullable=False,
    )
    capability = Column(Text, nullable=False)
    created_at = Column(BigInteger, nullable=False)

    __table_args__ = (
        Index("role_capability_role_id_idx", "role_id"),
        Index("role_capability_capability_idx", "capability"),
        # Unique constraint: each role can only have a capability once
        Index("role_capability_unique_idx", "role_id", "capability", unique=True),
    )


class RoleCapabilityModel(BaseModel):
    """Pydantic model for RoleCapability."""

    id: str
    role_id: str
    capability: str
    created_at: int

    model_config = ConfigDict(from_attributes=True)


####################
# Forms
####################


class RoleForm(BaseModel):
    """Form for creating/updating a role."""

    name: str
    description: Optional[str] = None
    permissions: Optional[dict] = None
    priority: int = 0


class RoleUpdateForm(BaseModel):
    """Form for updating a role (all fields optional)."""

    name: Optional[str] = None
    description: Optional[str] = None
    permissions: Optional[dict] = None
    priority: Optional[int] = None


class RoleResponse(RoleModel):
    """Response model with capabilities included."""

    capabilities: list[str] = []


class RoleListResponse(BaseModel):
    """Response for listing roles."""

    items: list[RoleResponse] = []
    total: int = 0


class CapabilityForm(BaseModel):
    """Form for adding/removing capabilities."""

    capabilities: list[str]


####################
# Default System Roles
####################

# These are seeded on first run and protected from deletion
SYSTEM_ROLES = {
    "admin": {
        "name": "admin",
        "description": "Full system administrator with all capabilities",
        "permissions": None,  # Admins bypass permissions
        "is_system": True,
        "priority": 1000,
        "capabilities": list(SYSTEM_CAPABILITIES.keys()),  # All capabilities
    },
    "user": {
        "name": "user",
        "description": "Standard user with default permissions",
        "permissions": None,  # Uses DEFAULT_USER_PERMISSIONS
        "is_system": True,
        "priority": 100,
        "capabilities": [],  # No admin capabilities
    },
    "pending": {
        "name": "pending",
        "description": "User awaiting approval with minimal access",
        "permissions": {
            "workspace": {
                "models": False,
                "knowledge": False,
                "prompts": False,
                "tools": False,
                "skills": False,
            },
            "chat": {
                "delete": False,
                "share": False,
                "export": False,
            },
            "features": {
                "api_keys": False,
                "channels": False,
            },
        },
        "is_system": True,
        "priority": 0,
        "capabilities": [],
    },
}


####################
# Role Table Operations
####################


class RoleTable:
    """Table operations for Role model."""

    def insert_new_role(
        self,
        form_data: RoleForm,
        db: Optional[Session] = None,
    ) -> Optional[RoleModel]:
        """Create a new role."""
        with get_db_context(db) as db:
            try:
                now = int(time.time())
                role = Role(
                    id=str(uuid.uuid4()),
                    name=form_data.name,
                    description=form_data.description,
                    permissions=form_data.permissions,
                    is_system=False,  # User-created roles are never system roles
                    priority=form_data.priority,
                    created_at=now,
                    updated_at=now,
                )
                db.add(role)
                db.commit()
                db.refresh(role)
                return RoleModel.model_validate(role)
            except Exception as e:
                log.exception(f"Failed to create role: {e}")
                db.rollback()
                return None

    def get_all_roles(self, db: Optional[Session] = None) -> list[RoleModel]:
        """Get all roles ordered by priority (highest first)."""
        with get_db_context(db) as db:
            roles = db.query(Role).order_by(Role.priority.desc()).all()
            return [RoleModel.model_validate(role) for role in roles]

    def get_role_by_id(
        self, id: str, db: Optional[Session] = None
    ) -> Optional[RoleModel]:
        """Get a role by ID."""
        with get_db_context(db) as db:
            role = db.query(Role).filter_by(id=id).first()
            return RoleModel.model_validate(role) if role else None

    def get_role_by_name(
        self, name: str, db: Optional[Session] = None
    ) -> Optional[RoleModel]:
        """Get a role by name."""
        with get_db_context(db) as db:
            role = db.query(Role).filter_by(name=name).first()
            return RoleModel.model_validate(role) if role else None

    def update_role_by_id(
        self,
        id: str,
        form_data: RoleUpdateForm,
        db: Optional[Session] = None,
    ) -> Optional[RoleModel]:
        """Update a role by ID."""
        with get_db_context(db) as db:
            try:
                role = db.query(Role).filter_by(id=id).first()
                if not role:
                    return None

                # Don't allow modifying system role names
                if role.is_system and form_data.name and form_data.name != role.name:
                    log.warning(f"Cannot rename system role: {role.name}")
                    return None

                update_data = form_data.model_dump(exclude_none=True)
                update_data["updated_at"] = int(time.time())

                for key, value in update_data.items():
                    setattr(role, key, value)

                db.commit()
                db.refresh(role)
                return RoleModel.model_validate(role)
            except Exception as e:
                log.exception(f"Failed to update role: {e}")
                db.rollback()
                return None

    def delete_role_by_id(self, id: str, db: Optional[Session] = None) -> bool:
        """Delete a role by ID. System roles cannot be deleted."""
        with get_db_context(db) as db:
            try:
                role = db.query(Role).filter_by(id=id).first()
                if not role:
                    return False

                if role.is_system:
                    log.warning(f"Cannot delete system role: {role.name}")
                    return False

                db.delete(role)
                db.commit()
                return True
            except Exception as e:
                log.exception(f"Failed to delete role: {e}")
                db.rollback()
                return False

    def seed_system_roles(self, db: Optional[Session] = None) -> None:
        """
        Seed system roles (admin, user, pending) if they don't exist.
        Called on application startup.
        """
        with get_db_context(db) as db:
            for role_name, role_data in SYSTEM_ROLES.items():
                existing = db.query(Role).filter_by(name=role_name).first()
                if existing:
                    continue

                now = int(time.time())
                role = Role(
                    id=str(uuid.uuid4()),
                    name=role_data["name"],
                    description=role_data["description"],
                    permissions=role_data["permissions"],
                    is_system=role_data["is_system"],
                    priority=role_data["priority"],
                    created_at=now,
                    updated_at=now,
                )
                db.add(role)
                db.flush()

                # Add capabilities for this role
                for capability in role_data.get("capabilities", []):
                    cap = RoleCapability(
                        id=str(uuid.uuid4()),
                        role_id=role.id,
                        capability=capability,
                        created_at=now,
                    )
                    db.add(cap)

                log.info(f"Seeded system role: {role_name}")

            db.commit()


####################
# RoleCapability Table Operations
####################


class RoleCapabilityTable:
    """Table operations for RoleCapability model."""

    def add_capability(
        self,
        role_id: str,
        capability: str,
        db: Optional[Session] = None,
    ) -> Optional[RoleCapabilityModel]:
        """Add a capability to a role. Idempotent."""
        if capability not in SYSTEM_CAPABILITIES:
            log.warning(f"Unknown capability: {capability}")
            return None

        with get_db_context(db) as db:
            try:
                # Check if already exists
                existing = (
                    db.query(RoleCapability)
                    .filter_by(
                        role_id=role_id,
                        capability=capability,
                    )
                    .first()
                )

                if existing:
                    return RoleCapabilityModel.model_validate(existing)

                now = int(time.time())
                cap = RoleCapability(
                    id=str(uuid.uuid4()),
                    role_id=role_id,
                    capability=capability,
                    created_at=now,
                )
                db.add(cap)
                db.commit()
                db.refresh(cap)
                return RoleCapabilityModel.model_validate(cap)
            except Exception as e:
                log.exception(f"Failed to add capability: {e}")
                db.rollback()
                return None

    def remove_capability(
        self,
        role_id: str,
        capability: str,
        db: Optional[Session] = None,
    ) -> bool:
        """Remove a capability from a role."""
        with get_db_context(db) as db:
            try:
                deleted = (
                    db.query(RoleCapability)
                    .filter_by(
                        role_id=role_id,
                        capability=capability,
                    )
                    .delete()
                )
                db.commit()
                return deleted > 0
            except Exception as e:
                log.exception(f"Failed to remove capability: {e}")
                db.rollback()
                return False

    def set_capabilities(
        self,
        role_id: str,
        capabilities: list[str],
        db: Optional[Session] = None,
    ) -> list[RoleCapabilityModel]:
        """Replace all capabilities for a role."""
        # Filter to valid capabilities
        valid_capabilities = [c for c in capabilities if c in SYSTEM_CAPABILITIES]

        with get_db_context(db) as db:
            try:
                # Remove all existing capabilities
                db.query(RoleCapability).filter_by(role_id=role_id).delete()

                # Add new capabilities
                now = int(time.time())
                results = []
                for capability in valid_capabilities:
                    cap = RoleCapability(
                        id=str(uuid.uuid4()),
                        role_id=role_id,
                        capability=capability,
                        created_at=now,
                    )
                    db.add(cap)
                    results.append(cap)

                db.commit()
                return [RoleCapabilityModel.model_validate(c) for c in results]
            except Exception as e:
                log.exception(f"Failed to set capabilities: {e}")
                db.rollback()
                return []

    def get_capabilities_by_role_id(
        self,
        role_id: str,
        db: Optional[Session] = None,
    ) -> list[str]:
        """Get all capability names for a role."""
        with get_db_context(db) as db:
            caps = db.query(RoleCapability).filter_by(role_id=role_id).all()
            return [cap.capability for cap in caps]

    def has_capability(
        self,
        role_id: str,
        capability: str,
        db: Optional[Session] = None,
    ) -> bool:
        """Check if a role has a specific capability."""
        with get_db_context(db) as db:
            exists = (
                db.query(RoleCapability)
                .filter_by(
                    role_id=role_id,
                    capability=capability,
                )
                .first()
            )
            return exists is not None


# Singleton instances
Roles = RoleTable()
RoleCapabilities = RoleCapabilityTable()
