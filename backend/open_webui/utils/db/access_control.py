from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Boolean, Column, String, Text, JSON
from sqlalchemy.dialects.postgresql import JSONB


from sqlalchemy import or_, func, select, and_, text, cast, or_, and_, func


def has_permission(db, DocumentModel, query, filter: dict, permission: str = "read"):
    group_ids = filter.get("group_ids", [])
    user_id = filter.get("user_id")
    dialect_name = db.bind.dialect.name

    conditions = []

    # Handle read_only permission separately
    if permission == "read_only":
        # For read_only, we want items where:
        # 1. User has explicit read permission (via groups or user-level)
        # 2. BUT does NOT have write permission
        # 3. Public items are NOT considered read_only

        read_conditions = []

        # Group-level read permission
        if group_ids:
            group_read_conditions = []
            for gid in group_ids:
                if dialect_name == "sqlite":
                    group_read_conditions.append(
                        DocumentModel.access_control["read"]["group_ids"].contains(
                            [gid]
                        )
                    )
                elif dialect_name == "postgresql":
                    group_read_conditions.append(
                        cast(
                            DocumentModel.access_control["read"]["group_ids"],
                            JSONB,
                        ).contains([gid])
                    )

            if group_read_conditions:
                read_conditions.append(or_(*group_read_conditions))

        # Combine read conditions
        if read_conditions:
            has_read = or_(*read_conditions)
        else:
            # If no read conditions, return empty result
            return query.filter(False)

        # Now exclude items where user has write permission
        write_exclusions = []

        # Exclude items owned by user (they have implicit write)
        if user_id:
            write_exclusions.append(DocumentModel.user_id != user_id)

        # Exclude items where user has explicit write permission via groups
        if group_ids:
            group_write_conditions = []
            for gid in group_ids:
                if dialect_name == "sqlite":
                    group_write_conditions.append(
                        DocumentModel.access_control["write"]["group_ids"].contains(
                            [gid]
                        )
                    )
                elif dialect_name == "postgresql":
                    group_write_conditions.append(
                        cast(
                            DocumentModel.access_control["write"]["group_ids"],
                            JSONB,
                        ).contains([gid])
                    )

            if group_write_conditions:
                # User should NOT have write permission
                write_exclusions.append(~or_(*group_write_conditions))

        # Exclude public items (items without access_control)
        write_exclusions.append(DocumentModel.access_control.isnot(None))
        write_exclusions.append(cast(DocumentModel.access_control, String) != "null")

        # Combine: has read AND does not have write AND not public
        if write_exclusions:
            query = query.filter(and_(has_read, *write_exclusions))
        else:
            query = query.filter(has_read)

        return query

    # Original logic for other permissions (read, write, etc.)
    # Public access conditions
    if group_ids or user_id:
        conditions.extend(
            [
                DocumentModel.access_control.is_(None),
                cast(DocumentModel.access_control, String) == "null",
            ]
        )

    # User-level permission (owner has all permissions)
    if user_id:
        conditions.append(DocumentModel.user_id == user_id)

    # Group-level permission
    if group_ids:
        group_conditions = []
        for gid in group_ids:
            if dialect_name == "sqlite":
                group_conditions.append(
                    DocumentModel.access_control[permission]["group_ids"].contains(
                        [gid]
                    )
                )
            elif dialect_name == "postgresql":
                group_conditions.append(
                    cast(
                        DocumentModel.access_control[permission]["group_ids"],
                        JSONB,
                    ).contains([gid])
                )
        conditions.append(or_(*group_conditions))

    if conditions:
        query = query.filter(or_(*conditions))

    return query
