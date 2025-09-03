import logging
import time
from typing import List, Dict
from sqlalchemy.orm import attributes
from open_webui.internal.db import get_db
from open_webui.models.groups import Group, GroupModel
from open_webui.models.users import User, Users

log = logging.getLogger(__name__)

# Import socket utilities for real-time updates
try:
    from open_webui.socket.main import sio

    SOCKET_AVAILABLE = True
except ImportError:
    log.warning("Socket.IO not available - real-time updates disabled")
    SOCKET_AVAILABLE = False


class DomainGroupAssignment:
    """
    Service for automatically assigning users to groups based on their email domains.
    """

    def is_group_being_edited(self, group_id: str) -> bool:
        """Check if a group is currently being edited via the frontend modal"""
        try:
            from open_webui.routers.groups import is_group_being_edited

            return is_group_being_edited(group_id)
        except ImportError:
            return False

    async def emit_group_update(
        self,
        group_id: str,
        group_name: str,
        user_count: int,
        action: str,
        users_affected: List[str] = None,
    ):
        """Emit real-time group membership updates via Socket.IO"""
        if not SOCKET_AVAILABLE:
            return

        try:
            event_data = {
                "group_id": group_id,
                "group_name": group_name,
                "user_count": user_count,
                "action": action,
                "timestamp": int(time.time()),
            }

            if users_affected:
                event_data["users_affected"] = users_affected
                event_data["users_count"] = len(users_affected)

            await sio.emit("group-membership-update", event_data)
        except Exception as e:
            log.warning(f"Failed to emit group update: {e}")

    def get_groups_with_allowed_domains(self) -> List[GroupModel]:
        """
        Get all groups that have allowed_domains configured.

        Returns:
            List of GroupModel objects that have non-empty allowed_domains
        """
        try:
            with get_db() as db:
                groups = db.query(Group).filter(Group.allowed_domains.isnot(None)).all()
                # Convert to GroupModel and filter out groups with empty domain lists
                group_models = []
                for group in groups:
                    if group.allowed_domains and len(group.allowed_domains) > 0:
                        group_models.append(GroupModel(**group.__dict__))
                return group_models
        except Exception as e:
            log.exception(f"Error getting groups with allowed domains: {e}")
            return []

    def get_all_users(self) -> List[Dict]:
        """
        Get all users that should be considered for domain-based group assignment.
        Only includes users with role='user' to exclude admins and analysts.

        Returns:
            List of user dictionaries with id, email, and role
        """
        try:
            # Get all users from the database
            all_db_users = Users.get_users()

            # Filter to only include users with role='user'
            filtered_users = []
            for user in all_db_users:
                # Only include users with 'user' role for automatic domain assignment
                if user.role == "user":
                    filtered_users.append(
                        {"id": user.id, "email": user.email, "role": user.role}
                    )

            return filtered_users

        except Exception as e:
            log.exception(f"Error getting users for domain assignment: {e}")
            return []

    def get_user_email_domain(self, email: str) -> str:
        """Extract domain from email address."""
        if "@" not in email:
            return ""
        return email.split("@")[1].lower()

    def is_group_recently_edited(self, group, cooldown_minutes: int = 2) -> bool:
        """
        Check if a group was recently manually edited.
        Groups that were edited within the cooldown period are skipped
        to prevent race conditions with manual frontend operations.

        Args:
            group: The group object to check
            cooldown_minutes: Minutes to wait after manual edit before auto-processing

        Returns:
            True if group was recently edited and should be skipped
        """
        if not hasattr(group, "updated_at") or not group.updated_at:
            return False

        # Check if updated within the cooldown period
        current_time = int(time.time())
        time_since_update = current_time - group.updated_at
        cooldown_seconds = cooldown_minutes * 60

        if time_since_update < cooldown_seconds:
            return True

        return False

    def should_user_be_in_group(
        self, user_email: str, group_domains: List[str]
    ) -> bool:
        """Check if user's email domain matches any of the group's allowed domains."""
        if not user_email or not group_domains:
            return False

        user_domain = self.get_user_email_domain(user_email)
        return user_domain in [domain.lower() for domain in group_domains]

    def add_user_to_group(self, group_id: str, user_id: str) -> bool:
        """Add user to group if not already present."""
        with get_db() as db:
            try:
                group = db.query(Group).filter_by(id=group_id).first()
                if not group:
                    log.warning(f"Group {group_id} not found")
                    return False

                # Get current user_ids, handle None case
                current_user_ids = group.user_ids or []

                # Check if user is already in group
                if user_id not in current_user_ids:
                    # Create a new list to ensure SQLAlchemy detects the change
                    new_user_ids = current_user_ids.copy()
                    new_user_ids.append(user_id)

                    # Assign the new list and mark as modified to ensure SQLAlchemy detects the change
                    group.user_ids = new_user_ids
                    attributes.flag_modified(group, "user_ids")

                    # Update timestamp
                    group.updated_at = int(time.time())

                    db.commit()
                    return True
                else:
                    return False  # User already in group

            except Exception as e:
                log.exception(f"Error adding user {user_id} to group {group_id}: {e}")
                try:
                    db.rollback()
                except:
                    pass
                return False

    def remove_user_from_group(self, group_id: str, user_id: str) -> bool:
        """Remove user from group if present and their domain no longer matches."""
        with get_db() as db:
            try:
                group = db.query(Group).filter_by(id=group_id).first()
                if not group:
                    log.warning(f"Group {group_id} not found")
                    return False

                # Get current user_ids, handle None case
                current_user_ids = group.user_ids or []

                # Remove user if present in group
                if user_id in current_user_ids:
                    # Create a new list to ensure SQLAlchemy detects the change
                    new_user_ids = current_user_ids.copy()
                    new_user_ids.remove(user_id)

                    # Assign the new list to trigger SQLAlchemy change detection
                    group.user_ids = new_user_ids
                    attributes.flag_modified(group, "user_ids")

                    # Update timestamp
                    group.updated_at = int(time.time())

                    db.commit()
                    return True
                else:
                    return False

            except Exception as e:
                log.exception(
                    f"Error removing user {user_id} from group {group_id}: {e}"
                )
                try:
                    db.rollback()
                except:
                    pass
                return False

    async def process_domain_assignments(self) -> Dict[str, int]:
        """
        Main method to process all users and assign them to groups based on email domains.
        This method will add users to groups they should be in and remove them from groups
        they no longer match, emitting real-time updates via Socket.IO.

        Returns statistics about the operation.
        """
        stats = {
            "users_processed": 0,
            "groups_processed": 0,
            "users_added": 0,
            "users_removed": 0,
            "errors": 0,
            "groups_skipped_editing": 0,
            "groups_skipped_recent": 0,
        }

        try:
            # Get all groups with domain restrictions
            groups_with_domains = self.get_groups_with_allowed_domains()
            stats["groups_processed"] = len(groups_with_domains)

            if not groups_with_domains:
                return stats

            # Get all users
            users = self.get_all_users()
            stats["users_processed"] = len(users)

            if not users:
                return stats

            log.info(
                f"Processing domain assignments for {len(users)} users and {len(groups_with_domains)} groups"
            )

            # Process each group
            for group in groups_with_domains:
                if not group.allowed_domains:
                    continue

                # Skip groups that are currently being edited via frontend modal
                if self.is_group_being_edited(group.id):
                    stats["groups_skipped_editing"] += 1
                    continue

                # Skip groups that were recently manually edited to prevent race conditions
                if self.is_group_recently_edited(group):
                    stats["groups_skipped_recent"] += 1
                    continue

                # Track changes for this group
                users_added_to_group = []
                users_removed_from_group = []

                # Process each user for this group
                for user in users:
                    try:
                        user_should_be_in_group = self.should_user_be_in_group(
                            user["email"], group.allowed_domains
                        )
                        user_is_in_group = user["id"] in (group.user_ids or [])

                        if user_should_be_in_group and not user_is_in_group:
                            # Add user to group
                            if self.add_user_to_group(group.id, user["id"]):
                                stats["users_added"] += 1
                                users_added_to_group.append(user["email"])
                        elif not user_should_be_in_group and user_is_in_group:
                            # Remove user from group if their domain no longer matches
                            if self.remove_user_from_group(group.id, user["id"]):
                                stats["users_removed"] += 1
                                users_removed_from_group.append(user["email"])

                    except Exception as e:
                        log.exception(
                            f"Error processing user {user['id']} for group {group.id}: {e}"
                        )
                        stats["errors"] += 1

                # Emit real-time updates for this group if there were changes
                current_user_count = (
                    len(group.user_ids or [])
                    + len(users_added_to_group)
                    - len(users_removed_from_group)
                )

                if users_added_to_group:
                    await self.emit_group_update(
                        group.id,
                        group.name,
                        current_user_count,
                        "added",
                        users_added_to_group,
                    )

                if users_removed_from_group:
                    await self.emit_group_update(
                        group.id,
                        group.name,
                        current_user_count,
                        "removed",
                        users_removed_from_group,
                    )

            log.info(f"Domain assignment processing completed: {stats}")

        except Exception as e:
            log.exception(f"Error during domain assignment processing: {e}")
            stats["errors"] += 1

        return stats


# Singleton instance
domain_assignment_service = DomainGroupAssignment()


def run_domain_assignment_job():
    """
    Entry point for the domain assignment background job.
    This function can be called by a scheduler or cron job.
    """
    stats = domain_assignment_service.process_domain_assignments()
    return stats
