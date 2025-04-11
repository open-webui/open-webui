import json

from sqlalchemy import text, Column
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.sql import and_, or_
from sqlalchemy.sql.elements import ColumnElement


class FilterUtils:
    """
    FilterUtils is a utility class that provides methods to create filter clauses for
    PGVECTOR queries based on user authentication metadata.
    """

    def create_auth_filter_clause(
        self,
        user_mail: str,
        user_entra_groups: list[str],
        metadata_column: Column[MutableDict],
        group_field_name: str = "groups",
        user_field_name: str = "users",
    ) -> ColumnElement:
        """
        Create a filter clause that allows access if:
        - metadata is NULL (no restrictions)
        - both groups and users arrays are empty (public)
        - user_mail is in the users array
        - ANY of user_entra_groups is in the groups array
        """
        conditions = []

        # Check for NULL metadata or empty arrays (public access)
        public_access = self.filter_for_empty_auth(
            metadata_column,
            group_field_name=group_field_name,
            user_field_name=user_field_name,
        )
        conditions.append(public_access)

        # Check for user email in users array
        if user_mail:
            user_access = metadata_column[user_field_name].contains(
                json.dumps(user_mail.lower())
            )
            conditions.append(user_access)

        # Check for any group match using ?| operator
        if user_entra_groups:
            # Convert the Python list to a PostgreSQL array literal string
            pg_array_str = (
                "ARRAY["
                + ", ".join([f"'{g}'" for g in user_entra_groups])
                + "]::text[]"
            )

            # Create raw SQL expression with the array literal directly embedded
            group_access = text(
                f"({metadata_column.key}->'{group_field_name}') ?| {pg_array_str}"
            )
            conditions.append(group_access)

        # Combine all access conditions with OR
        return or_(*conditions)

    @staticmethod
    def filter_for_empty_auth(
        metadata: Column[MutableDict],
        group_field_name: str = "group_ids",
        user_field_name: str = "user_ids",
    ) -> ColumnElement:
        """
        This function creates a filter clause that allows all documents with blank auth metadata.
        The filter clause is created by checking if both the group_ids and
        user_ids fields are empty.
        The subclauses are joined using an AND operator.

        Args:
            metadata: The column containing the auth metadata.
            group_field_name: The name of the field in the metadata that contains the group ids.
            user_field_name: The name of the field in the metadata that contains the user ids.

        Returns:
            A ColumnElement containing a filter clause that allows all documents with blank
            auth metadata.
        """
        return or_(
            metadata.is_(None),
            and_(
                metadata[group_field_name] == json.dumps([]),
                metadata[user_field_name] == json.dumps([]),
            ),
        )
