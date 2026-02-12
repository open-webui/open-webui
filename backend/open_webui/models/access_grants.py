import logging
import time
import uuid
from typing import Optional

from sqlalchemy.orm import Session
from open_webui.internal.db import Base, get_db_context

from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Column, Text, UniqueConstraint, or_, and_
from sqlalchemy.dialects.postgresql import JSONB

log = logging.getLogger(__name__)


####################
# AccessGrant DB Schema
####################


class AccessGrant(Base):
    __tablename__ = "access_grant"

    id = Column(Text, primary_key=True)
    resource_type = Column(
        Text, nullable=False
    )  # "knowledge", "model", "prompt", "tool", "note", "channel", "file"
    resource_id = Column(Text, nullable=False)
    principal_type = Column(Text, nullable=False)  # "user" or "group"
    principal_id = Column(
        Text, nullable=False
    )  # user_id, group_id, or "*" (wildcard for public)
    permission = Column(Text, nullable=False)  # "read" or "write"
    created_at = Column(BigInteger, nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "resource_type",
            "resource_id",
            "principal_type",
            "principal_id",
            "permission",
            name="uq_access_grant_grant",
        ),
    )


class AccessGrantModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    resource_type: str
    resource_id: str
    principal_type: str
    principal_id: str
    permission: str
    created_at: int


class AccessGrantResponse(BaseModel):
    """Slim grant model for API responses — resource context is implicit from the parent."""

    id: str
    principal_type: str
    principal_id: str
    permission: str

    @classmethod
    def from_grant(cls, grant: "AccessGrantModel") -> "AccessGrantResponse":
        return cls(
            id=grant.id,
            principal_type=grant.principal_type,
            principal_id=grant.principal_id,
            permission=grant.permission,
        )


####################
# Conversion utilities
####################


def access_control_to_grants(
    resource_type: str,
    resource_id: str,
    access_control: Optional[dict],
) -> list[dict]:
    """
    Convert an old-style access_control JSON dict to a flat list of grant dicts.

    Semantics:
    - None  → public read (user:* read) — except files which are private
    - {}    → private/owner-only (no grants)
    - {read: {group_ids, user_ids}, write: {group_ids, user_ids}} → specific grants

    Returns a list of dicts with keys: resource_type, resource_id, principal_type, principal_id, permission
    """
    grants = []

    if access_control is None:
        # NULL → public read (user:* for read)
        # Exception: files with NULL are private (owner-only), no grants needed
        if resource_type != "file":
            grants.append(
                {
                    "resource_type": resource_type,
                    "resource_id": resource_id,
                    "principal_type": "user",
                    "principal_id": "*",
                    "permission": "read",
                }
            )
        return grants

    # {} → private/owner-only, no grants
    if not access_control:
        return grants

    # Parse structured permissions
    for permission in ["read", "write"]:
        perm_data = access_control.get(permission, {})
        if not perm_data:
            continue

        for group_id in perm_data.get("group_ids", []):
            grants.append(
                {
                    "resource_type": resource_type,
                    "resource_id": resource_id,
                    "principal_type": "group",
                    "principal_id": group_id,
                    "permission": permission,
                }
            )

        for user_id in perm_data.get("user_ids", []):
            grants.append(
                {
                    "resource_type": resource_type,
                    "resource_id": resource_id,
                    "principal_type": "user",
                    "principal_id": user_id,
                    "permission": permission,
                }
            )

    return grants


def normalize_access_grants(access_grants: Optional[list]) -> list[dict]:
    """
    Normalize direct access_grants payloads from API forms.

    Keeps only valid grants and removes duplicates by
    (principal_type, principal_id, permission).
    """
    if not access_grants:
        return []

    deduped = {}
    for grant in access_grants:
        if isinstance(grant, BaseModel):
            grant = grant.model_dump()
        if not isinstance(grant, dict):
            continue

        principal_type = grant.get("principal_type")
        principal_id = grant.get("principal_id")
        permission = grant.get("permission")

        if principal_type not in ("user", "group"):
            continue
        if permission not in ("read", "write"):
            continue
        if not isinstance(principal_id, str) or not principal_id:
            continue

        key = (principal_type, principal_id, permission)
        deduped[key] = {
            "id": (
                grant.get("id")
                if isinstance(grant.get("id"), str) and grant.get("id")
                else str(uuid.uuid4())
            ),
            "principal_type": principal_type,
            "principal_id": principal_id,
            "permission": permission,
        }

    return list(deduped.values())


def has_public_read_access_grant(access_grants: Optional[list]) -> bool:
    """
    Returns True when a direct grant list includes wildcard public-read.
    """
    for grant in normalize_access_grants(access_grants):
        if (
            grant["principal_type"] == "user"
            and grant["principal_id"] == "*"
            and grant["permission"] == "read"
        ):
            return True
    return False


def grants_to_access_control(grants: list) -> Optional[dict]:
    """
    Convert a list of grant objects (AccessGrantModel or AccessGrantResponse)
    back to the old-style access_control JSON dict for backward compatibility.

    Semantics:
    - [] (empty) → {} (private/owner-only)
    - Contains user:*:read → None (public), but write grants are preserved
    - Otherwise → {read: {group_ids, user_ids}, write: {group_ids, user_ids}}

    Note: "public" (user:*:read) still allows additional write permissions
    to coexist.  When the wildcard read is present the function returns None
    for the legacy dict, so callers that need write info should inspect the
    grants list directly.
    """
    if not grants:
        return {}  # No grants = private/owner-only

    result = {
        "read": {"group_ids": [], "user_ids": []},
        "write": {"group_ids": [], "user_ids": []},
    }

    is_public = False
    for grant in grants:
        if (
            grant.principal_type == "user"
            and grant.principal_id == "*"
            and grant.permission == "read"
        ):
            is_public = True
            continue  # Don't add wildcard to user_ids list

        if grant.permission not in ("read", "write"):
            continue

        if grant.principal_type == "group":
            if grant.principal_id not in result[grant.permission]["group_ids"]:
                result[grant.permission]["group_ids"].append(grant.principal_id)
        elif grant.principal_type == "user":
            if grant.principal_id not in result[grant.permission]["user_ids"]:
                result[grant.permission]["user_ids"].append(grant.principal_id)

    if is_public:
        return None  # Public read access

    return result


####################
# Table Operations
####################


class AccessGrantsTable:
    def grant_access(
        self,
        resource_type: str,
        resource_id: str,
        principal_type: str,
        principal_id: str,
        permission: str,
        db: Optional[Session] = None,
    ) -> Optional[AccessGrantModel]:
        """Add a single access grant. Idempotent (ignores duplicates)."""
        with get_db_context(db) as db:
            # Check for existing grant
            existing = (
                db.query(AccessGrant)
                .filter_by(
                    resource_type=resource_type,
                    resource_id=resource_id,
                    principal_type=principal_type,
                    principal_id=principal_id,
                    permission=permission,
                )
                .first()
            )
            if existing:
                return AccessGrantModel.model_validate(existing)

            grant = AccessGrant(
                id=str(uuid.uuid4()),
                resource_type=resource_type,
                resource_id=resource_id,
                principal_type=principal_type,
                principal_id=principal_id,
                permission=permission,
                created_at=int(time.time()),
            )
            db.add(grant)
            db.commit()
            db.refresh(grant)
            return AccessGrantModel.model_validate(grant)

    def revoke_access(
        self,
        resource_type: str,
        resource_id: str,
        principal_type: str,
        principal_id: str,
        permission: str,
        db: Optional[Session] = None,
    ) -> bool:
        """Remove a single access grant."""
        with get_db_context(db) as db:
            deleted = (
                db.query(AccessGrant)
                .filter_by(
                    resource_type=resource_type,
                    resource_id=resource_id,
                    principal_type=principal_type,
                    principal_id=principal_id,
                    permission=permission,
                )
                .delete()
            )
            db.commit()
            return deleted > 0

    def revoke_all_access(
        self,
        resource_type: str,
        resource_id: str,
        db: Optional[Session] = None,
    ) -> int:
        """Remove all access grants for a resource."""
        with get_db_context(db) as db:
            deleted = (
                db.query(AccessGrant)
                .filter_by(
                    resource_type=resource_type,
                    resource_id=resource_id,
                )
                .delete()
            )
            db.commit()
            return deleted

    def set_access_control(
        self,
        resource_type: str,
        resource_id: str,
        access_control: Optional[dict],
        db: Optional[Session] = None,
    ) -> list[AccessGrantModel]:
        """
        Replace all grants for a resource from an access_control JSON dict.
        This is the primary bridge for backward compat with the frontend.
        """
        with get_db_context(db) as db:
            # Delete all existing grants for this resource
            db.query(AccessGrant).filter_by(
                resource_type=resource_type,
                resource_id=resource_id,
            ).delete()

            # Convert JSON to grant dicts
            grant_dicts = access_control_to_grants(
                resource_type, resource_id, access_control
            )

            # Insert new grants
            results = []
            for grant_dict in grant_dicts:
                grant = AccessGrant(
                    id=str(uuid.uuid4()),
                    **grant_dict,
                    created_at=int(time.time()),
                )
                db.add(grant)
                results.append(grant)

            db.commit()

            return [AccessGrantModel.model_validate(g) for g in results]

    def set_access_grants(
        self,
        resource_type: str,
        resource_id: str,
        access_grants: Optional[list],
        db: Optional[Session] = None,
    ) -> list[AccessGrantModel]:
        """
        Replace all grants for a resource from a direct access_grants list.
        """
        with get_db_context(db) as db:
            db.query(AccessGrant).filter_by(
                resource_type=resource_type,
                resource_id=resource_id,
            ).delete()

            normalized_grants = normalize_access_grants(access_grants)

            results = []
            for grant_dict in normalized_grants:
                grant = AccessGrant(
                    id=grant_dict["id"],
                    resource_type=resource_type,
                    resource_id=resource_id,
                    principal_type=grant_dict["principal_type"],
                    principal_id=grant_dict["principal_id"],
                    permission=grant_dict["permission"],
                    created_at=int(time.time()),
                )
                db.add(grant)
                results.append(grant)

            db.commit()
            return [AccessGrantModel.model_validate(g) for g in results]

    def get_access_control(
        self,
        resource_type: str,
        resource_id: str,
        db: Optional[Session] = None,
    ) -> Optional[dict]:
        """
        Reconstruct the old-style access_control JSON dict from grants.
        For backward compat with the frontend.
        """
        with get_db_context(db) as db:
            grants = (
                db.query(AccessGrant)
                .filter_by(
                    resource_type=resource_type,
                    resource_id=resource_id,
                )
                .all()
            )
            grant_models = [AccessGrantModel.model_validate(g) for g in grants]
            return grants_to_access_control(grant_models)

    def get_grants_by_resource(
        self,
        resource_type: str,
        resource_id: str,
        db: Optional[Session] = None,
    ) -> list[AccessGrantModel]:
        """Get all grants for a specific resource."""
        with get_db_context(db) as db:
            grants = (
                db.query(AccessGrant)
                .filter_by(
                    resource_type=resource_type,
                    resource_id=resource_id,
                )
                .all()
            )
            return [AccessGrantModel.model_validate(g) for g in grants]

    def has_access(
        self,
        user_id: str,
        resource_type: str,
        resource_id: str,
        permission: str = "read",
        user_group_ids: Optional[set[str]] = None,
        db: Optional[Session] = None,
    ) -> bool:
        """
        Check if a user has the specified permission on a resource.

        Access is granted if any of the following is true:
        - There's a grant for user:* (public) with the requested permission
        - There's a grant for the specific user with the requested permission
        - There's a grant for any of the user's groups with the requested permission
        """
        with get_db_context(db) as db:
            # Build conditions for matching grants
            conditions = [
                # Public access
                and_(
                    AccessGrant.principal_type == "user",
                    AccessGrant.principal_id == "*",
                ),
                # Direct user access
                and_(
                    AccessGrant.principal_type == "user",
                    AccessGrant.principal_id == user_id,
                ),
            ]

            # Group access
            if user_group_ids is None:
                from open_webui.models.groups import Groups

                user_groups = Groups.get_groups_by_member_id(user_id, db=db)
                user_group_ids = {group.id for group in user_groups}

            if user_group_ids:
                conditions.append(
                    and_(
                        AccessGrant.principal_type == "group",
                        AccessGrant.principal_id.in_(user_group_ids),
                    )
                )

            exists = (
                db.query(AccessGrant)
                .filter(
                    AccessGrant.resource_type == resource_type,
                    AccessGrant.resource_id == resource_id,
                    AccessGrant.permission == permission,
                    or_(*conditions),
                )
                .first()
            )
            return exists is not None

    def get_users_with_access(
        self,
        resource_type: str,
        resource_id: str,
        permission: str = "read",
        db: Optional[Session] = None,
    ) -> list:
        """
        Get all users who have the specified permission on a resource.
        Returns a list of UserModel instances.
        """
        from open_webui.models.users import Users, UserModel
        from open_webui.models.groups import Groups

        with get_db_context(db) as db:
            grants = (
                db.query(AccessGrant)
                .filter_by(
                    resource_type=resource_type,
                    resource_id=resource_id,
                    permission=permission,
                )
                .all()
            )

            # Check for public access
            for grant in grants:
                if grant.principal_type == "user" and grant.principal_id == "*":
                    result = Users.get_users(filter={"roles": ["!pending"]}, db=db)
                    return result.get("users", [])

            user_ids_with_access = set()

            for grant in grants:
                if grant.principal_type == "user":
                    user_ids_with_access.add(grant.principal_id)
                elif grant.principal_type == "group":
                    group_user_ids = Groups.get_group_user_ids_by_id(
                        grant.principal_id, db=db
                    )
                    if group_user_ids:
                        user_ids_with_access.update(group_user_ids)

            if not user_ids_with_access:
                return []

            return Users.get_users_by_user_ids(list(user_ids_with_access), db=db)

    def has_permission_filter(
        self,
        db,
        query,
        DocumentModel,
        filter: dict,
        resource_type: str,
        permission: str = "read",
    ):
        """
        Apply access control filtering to a SQLAlchemy query by JOINing with access_grant.

        This replaces the old JSON-column-based filtering with a proper relational JOIN.
        """
        group_ids = filter.get("group_ids", [])
        user_id = filter.get("user_id")

        if permission == "read_only":
            return self._has_read_only_permission_filter(
                db, query, DocumentModel, filter, resource_type
            )

        # Build principal conditions
        principal_conditions = []

        if group_ids or user_id:
            # Public access: user:* read
            principal_conditions.append(
                and_(
                    AccessGrant.principal_type == "user",
                    AccessGrant.principal_id == "*",
                )
            )

        if user_id:
            # Owner always has access
            principal_conditions.append(DocumentModel.user_id == user_id)

            # Direct user grant
            principal_conditions.append(
                and_(
                    AccessGrant.principal_type == "user",
                    AccessGrant.principal_id == user_id,
                )
            )

        if group_ids:
            # Group grants
            principal_conditions.append(
                and_(
                    AccessGrant.principal_type == "group",
                    AccessGrant.principal_id.in_(group_ids),
                )
            )

        if not principal_conditions:
            return query

        # LEFT JOIN access_grant and filter
        # We use a subquery approach to avoid duplicates from multiple matching grants
        from sqlalchemy import exists as sa_exists, select

        grant_exists = (
            select(AccessGrant.id)
            .where(
                AccessGrant.resource_type == resource_type,
                AccessGrant.resource_id == DocumentModel.id,
                AccessGrant.permission == permission,
                or_(
                    and_(
                        AccessGrant.principal_type == "user",
                        AccessGrant.principal_id == "*",
                    ),
                    *(
                        [
                            and_(
                                AccessGrant.principal_type == "user",
                                AccessGrant.principal_id == user_id,
                            )
                        ]
                        if user_id
                        else []
                    ),
                    *(
                        [
                            and_(
                                AccessGrant.principal_type == "group",
                                AccessGrant.principal_id.in_(group_ids),
                            )
                        ]
                        if group_ids
                        else []
                    ),
                ),
            )
            .correlate(DocumentModel)
            .exists()
        )

        # Owner OR has a matching grant
        owner_or_grant = [grant_exists]
        if user_id:
            owner_or_grant.append(DocumentModel.user_id == user_id)

        query = query.filter(or_(*owner_or_grant))
        return query

    def _has_read_only_permission_filter(
        self,
        db,
        query,
        DocumentModel,
        filter: dict,
        resource_type: str,
    ):
        """
        Filter for items where user has read BUT NOT write access.
        Public items are NOT considered read_only.
        """
        group_ids = filter.get("group_ids", [])
        user_id = filter.get("user_id")

        from sqlalchemy import exists as sa_exists, select

        # Has read grant (not public)
        read_grant_exists = (
            select(AccessGrant.id)
            .where(
                AccessGrant.resource_type == resource_type,
                AccessGrant.resource_id == DocumentModel.id,
                AccessGrant.permission == "read",
                or_(
                    *(
                        [
                            and_(
                                AccessGrant.principal_type == "user",
                                AccessGrant.principal_id == user_id,
                            )
                        ]
                        if user_id
                        else []
                    ),
                    *(
                        [
                            and_(
                                AccessGrant.principal_type == "group",
                                AccessGrant.principal_id.in_(group_ids),
                            )
                        ]
                        if group_ids
                        else []
                    ),
                ),
            )
            .correlate(DocumentModel)
            .exists()
        )

        # Does NOT have write grant
        write_grant_exists = (
            select(AccessGrant.id)
            .where(
                AccessGrant.resource_type == resource_type,
                AccessGrant.resource_id == DocumentModel.id,
                AccessGrant.permission == "write",
                or_(
                    *(
                        [
                            and_(
                                AccessGrant.principal_type == "user",
                                AccessGrant.principal_id == user_id,
                            )
                        ]
                        if user_id
                        else []
                    ),
                    *(
                        [
                            and_(
                                AccessGrant.principal_type == "group",
                                AccessGrant.principal_id.in_(group_ids),
                            )
                        ]
                        if group_ids
                        else []
                    ),
                ),
            )
            .correlate(DocumentModel)
            .exists()
        )

        # Is NOT public
        public_grant_exists = (
            select(AccessGrant.id)
            .where(
                AccessGrant.resource_type == resource_type,
                AccessGrant.resource_id == DocumentModel.id,
                AccessGrant.permission == "read",
                AccessGrant.principal_type == "user",
                AccessGrant.principal_id == "*",
            )
            .correlate(DocumentModel)
            .exists()
        )

        conditions = [read_grant_exists, ~write_grant_exists, ~public_grant_exists]

        # Not owner
        if user_id:
            conditions.append(DocumentModel.user_id != user_id)

        query = query.filter(and_(*conditions))
        return query


AccessGrants = AccessGrantsTable()
