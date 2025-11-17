"""
Pydantic Models for Prune Operations

This module contains all Pydantic models used by the prune operations,
copied directly from backend/open_webui/routers/prune.py to ensure
consistency and avoid import issues.
"""

from typing import Optional
from pydantic import BaseModel


class PruneDataForm(BaseModel):
    """
    Configuration form for prune operations.

    This model defines all the parameters that can be configured for a prune
    operation, including age-based deletion, orphaned data cleanup, and
    system optimization settings.
    """
    days: Optional[int] = None
    exempt_archived_chats: bool = False
    exempt_chats_in_folders: bool = False
    delete_orphaned_chats: bool = True
    delete_orphaned_tools: bool = False
    delete_orphaned_functions: bool = False
    delete_orphaned_prompts: bool = True
    delete_orphaned_knowledge_bases: bool = True
    delete_orphaned_models: bool = True
    delete_orphaned_notes: bool = True
    delete_orphaned_folders: bool = True
    audio_cache_max_age_days: Optional[int] = 30
    delete_inactive_users_days: Optional[int] = None
    exempt_admin_users: bool = True
    exempt_pending_users: bool = True
    run_vacuum: bool = False
    dry_run: bool = True


class PrunePreviewResult(BaseModel):
    """
    Preview result showing counts of items that would be deleted.

    This model is returned during dry-run operations to show the user
    exactly what will be deleted without making any changes.
    """
    inactive_users: int = 0
    old_chats: int = 0
    orphaned_chats: int = 0
    orphaned_files: int = 0
    orphaned_tools: int = 0
    orphaned_functions: int = 0
    orphaned_prompts: int = 0
    orphaned_knowledge_bases: int = 0
    orphaned_models: int = 0
    orphaned_notes: int = 0
    orphaned_folders: int = 0
    orphaned_uploads: int = 0
    orphaned_vector_collections: int = 0
    audio_cache_files: int = 0

    def total_items(self) -> int:
        """Calculate total items that would be deleted."""
        return (
            self.inactive_users +
            self.old_chats +
            self.orphaned_chats +
            self.orphaned_files +
            self.orphaned_tools +
            self.orphaned_functions +
            self.orphaned_prompts +
            self.orphaned_knowledge_bases +
            self.orphaned_models +
            self.orphaned_notes +
            self.orphaned_folders +
            self.orphaned_uploads +
            self.orphaned_vector_collections +
            self.audio_cache_files
        )

    def has_items(self) -> bool:
        """Check if any items would be deleted."""
        return self.total_items() > 0

    def get_summary_dict(self) -> dict:
        """Get summary as dictionary for display."""
        return {
            "Users": {
                "Inactive users": self.inactive_users,
            },
            "Chats": {
                "Old chats (age-based)": self.old_chats,
                "Orphaned chats": self.orphaned_chats,
            },
            "Files": {
                "Orphaned file records": self.orphaned_files,
                "Orphaned upload files": self.orphaned_uploads,
            },
            "Workspace": {
                "Orphaned tools": self.orphaned_tools,
                "Orphaned functions": self.orphaned_functions,
                "Orphaned prompts": self.orphaned_prompts,
                "Orphaned knowledge bases": self.orphaned_knowledge_bases,
                "Orphaned models": self.orphaned_models,
                "Orphaned notes": self.orphaned_notes,
            },
            "Organization": {
                "Orphaned folders": self.orphaned_folders,
            },
            "Storage": {
                "Orphaned vector collections": self.orphaned_vector_collections,
            },
            "Cache": {
                "Old audio cache files": self.audio_cache_files,
            },
        }
