#!/usr/bin/env python3
"""
Open WebUI Standalone Prune Script

This is a standalone command-line script that replicates the full logic and
configurability of the prune.py API router, but runs independently without
requiring the web server to be running.

Usage:
    python standalone_prune.py --help
    python standalone_prune.py --dry-run  # Preview what will be deleted
    python standalone_prune.py --days 60 --run-vacuum  # Delete chats older than 60 days

Requirements:
    - Must be run from Open WebUI installation directory or have PYTHONPATH set
    - Requires same environment variables as Open WebUI (DATABASE_URL, etc.)
    - Requires same Python dependencies as Open WebUI backend
"""

import sys
import os
import argparse
import logging
from pathlib import Path

# Add parent directory to path to import Open WebUI modules
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(REPO_ROOT))

# Now we can import from Open WebUI backend
try:
    from backend.open_webui.routers.prune import (
        PruneLock,
        JSONFileIDExtractor,
        collect_file_ids_from_dict,
        VectorDatabaseCleaner,
        get_vector_database_cleaner,
        count_inactive_users,
        count_old_chats,
        count_orphaned_records,
        count_orphaned_uploads,
        count_audio_cache_files,
        get_active_file_ids,
        safe_delete_file_by_id,
        cleanup_orphaned_uploads,
        delete_inactive_users,
        cleanup_audio_cache,
        PruneDataForm,
        PrunePreviewResult,
    )
    from backend.open_webui.models.users import Users
    from backend.open_webui.models.chats import Chats
    from backend.open_webui.models.files import Files
    from backend.open_webui.models.notes import Notes
    from backend.open_webui.models.prompts import Prompts
    from backend.open_webui.models.models import Models
    from backend.open_webui.models.knowledge import Knowledges
    from backend.open_webui.models.functions import Functions
    from backend.open_webui.models.tools import Tools
    from backend.open_webui.models.folders import Folders
    from backend.open_webui.internal.db import get_db
    from backend.open_webui.env import SRC_LOG_LEVELS
    from sqlalchemy import text
    import time
    import sqlite3
    from backend.open_webui.routers.prune import ChromaDatabaseCleaner, PGVectorDatabaseCleaner
except ImportError as e:
    print(f"ERROR: Failed to import Open WebUI modules: {e}", file=sys.stderr)
    print("\nThis script must be run with access to Open WebUI's backend modules.", file=sys.stderr)
    print("Try one of the following:", file=sys.stderr)
    print("  1. Run from the Open WebUI installation directory", file=sys.stderr)
    print("  2. Set PYTHONPATH to include the Open WebUI directory", file=sys.stderr)
    print("  3. Install Open WebUI as a package", file=sys.stderr)
    sys.exit(1)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
log = logging.getLogger(__name__)


def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description='Open WebUI Standalone Data Pruning Script',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Preview what will be deleted (safe, no changes)
  %(prog)s --dry-run

  # Delete chats older than 60 days
  %(prog)s --days 60

  # Delete inactive users (90+ days) and their data
  %(prog)s --delete-inactive-users-days 90

  # Full cleanup with VACUUM optimization
  %(prog)s --days 90 --delete-inactive-users-days 180 --run-vacuum

  # Clean orphaned data only (no age-based deletion)
  %(prog)s --delete-orphaned-chats --delete-orphaned-files

  # Audio cache cleanup
  %(prog)s --audio-cache-max-age-days 30

Safety Features:
  - Uses file-based locking to prevent concurrent runs
  - Dry-run mode enabled by default (use --execute to actually delete)
  - Detailed logging of all operations
  - Preserves archived chats and folder-organized chats by default
  - Admin users exempted from deletion by default
        """
    )

    # Execution mode
    parser.add_argument(
        '--dry-run',
        action='store_true',
        default=False,
        help='Preview what will be deleted without making changes (default if --execute not specified)'
    )
    parser.add_argument(
        '--execute',
        action='store_true',
        default=False,
        help='Actually perform deletions (required for real cleanup)'
    )

    # Age-based deletion
    parser.add_argument(
        '--days',
        type=int,
        default=None,
        metavar='N',
        help='Delete chats older than N days (based on last update time)'
    )
    parser.add_argument(
        '--exempt-archived-chats',
        action='store_true',
        default=True,
        help='Keep archived chats even if old (default: True)'
    )
    parser.add_argument(
        '--no-exempt-archived-chats',
        action='store_false',
        dest='exempt_archived_chats',
        help='Include archived chats in age-based deletion'
    )
    parser.add_argument(
        '--exempt-chats-in-folders',
        action='store_true',
        default=False,
        help='Keep chats in folders/pinned even if old'
    )

    # Inactive user deletion
    parser.add_argument(
        '--delete-inactive-users-days',
        type=int,
        default=None,
        metavar='N',
        help='Delete users inactive for more than N days (DESTRUCTIVE)'
    )
    parser.add_argument(
        '--exempt-admin-users',
        action='store_true',
        default=True,
        help='Never delete admin users (default: True, STRONGLY RECOMMENDED)'
    )
    parser.add_argument(
        '--no-exempt-admin-users',
        action='store_false',
        dest='exempt_admin_users',
        help='Include admin users in inactivity deletion (NOT RECOMMENDED)'
    )
    parser.add_argument(
        '--exempt-pending-users',
        action='store_true',
        default=True,
        help='Never delete pending users (default: True)'
    )
    parser.add_argument(
        '--no-exempt-pending-users',
        action='store_false',
        dest='exempt_pending_users',
        help='Include pending users in inactivity deletion'
    )

    # Orphaned data deletion
    parser.add_argument(
        '--delete-orphaned-chats',
        action='store_true',
        default=True,
        help='Delete orphaned chats from deleted users (default: True)'
    )
    parser.add_argument(
        '--no-delete-orphaned-chats',
        action='store_false',
        dest='delete_orphaned_chats',
        help='Skip orphaned chat deletion'
    )
    parser.add_argument(
        '--delete-orphaned-tools',
        action='store_true',
        default=False,
        help='Delete orphaned tools from deleted users'
    )
    parser.add_argument(
        '--delete-orphaned-functions',
        action='store_true',
        default=False,
        help='Delete orphaned functions from deleted users'
    )
    parser.add_argument(
        '--delete-orphaned-prompts',
        action='store_true',
        default=True,
        help='Delete orphaned prompts from deleted users (default: True)'
    )
    parser.add_argument(
        '--delete-orphaned-knowledge-bases',
        action='store_true',
        default=True,
        help='Delete orphaned knowledge bases from deleted users (default: True)'
    )
    parser.add_argument(
        '--delete-orphaned-models',
        action='store_true',
        default=True,
        help='Delete orphaned models from deleted users (default: True)'
    )
    parser.add_argument(
        '--delete-orphaned-notes',
        action='store_true',
        default=True,
        help='Delete orphaned notes from deleted users (default: True)'
    )
    parser.add_argument(
        '--delete-orphaned-folders',
        action='store_true',
        default=True,
        help='Delete orphaned folders from deleted users (default: True)'
    )

    # Audio cache cleanup
    parser.add_argument(
        '--audio-cache-max-age-days',
        type=int,
        default=None,
        metavar='N',
        help='Delete audio cache files (TTS/STT) older than N days'
    )

    # Database optimization
    parser.add_argument(
        '--run-vacuum',
        action='store_true',
        default=False,
        help='Run VACUUM to reclaim disk space (LOCKS DATABASE, use during maintenance)'
    )

    # Logging
    parser.add_argument(
        '--verbose',
        '-v',
        action='store_true',
        default=False,
        help='Enable verbose debug logging'
    )
    parser.add_argument(
        '--quiet',
        '-q',
        action='store_true',
        default=False,
        help='Suppress all output except errors'
    )

    args = parser.parse_args()

    # If neither --dry-run nor --execute specified, default to dry-run
    if not args.dry_run and not args.execute:
        args.dry_run = True
        log.info("No execution mode specified, defaulting to --dry-run (preview mode)")

    # Can't have both dry-run and execute
    if args.dry_run and args.execute:
        parser.error("Cannot specify both --dry-run and --execute")

    return args


def configure_logging(verbose: bool, quiet: bool):
    """Configure logging level based on arguments."""
    if quiet:
        logging.getLogger().setLevel(logging.ERROR)
    elif verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    else:
        logging.getLogger().setLevel(logging.INFO)


def create_prune_form(args) -> PruneDataForm:
    """Create PruneDataForm from command-line arguments."""
    return PruneDataForm(
        days=args.days,
        exempt_archived_chats=args.exempt_archived_chats,
        exempt_chats_in_folders=args.exempt_chats_in_folders,
        delete_orphaned_chats=args.delete_orphaned_chats,
        delete_orphaned_tools=args.delete_orphaned_tools,
        delete_orphaned_functions=args.delete_orphaned_functions,
        delete_orphaned_prompts=args.delete_orphaned_prompts,
        delete_orphaned_knowledge_bases=args.delete_orphaned_knowledge_bases,
        delete_orphaned_models=args.delete_orphaned_models,
        delete_orphaned_notes=args.delete_orphaned_notes,
        delete_orphaned_folders=args.delete_orphaned_folders,
        audio_cache_max_age_days=args.audio_cache_max_age_days,
        delete_inactive_users_days=args.delete_inactive_users_days,
        exempt_admin_users=args.exempt_admin_users,
        exempt_pending_users=args.exempt_pending_users,
        run_vacuum=args.run_vacuum,
        dry_run=args.dry_run,
    )


def print_preview_results(result: PrunePreviewResult):
    """Pretty-print preview results."""
    print("\n" + "="*70)
    print("  PRUNE PREVIEW - What will be deleted")
    print("="*70)

    total_items = 0

    if result.inactive_users > 0:
        print(f"\n👤 Inactive Users:")
        print(f"   {result.inactive_users} user accounts")
        total_items += result.inactive_users

    if result.old_chats > 0 or result.orphaned_chats > 0:
        print(f"\n💬 Chats:")
        if result.old_chats > 0:
            print(f"   {result.old_chats} old chats (age-based)")
        if result.orphaned_chats > 0:
            print(f"   {result.orphaned_chats} orphaned chats")
        total_items += result.old_chats + result.orphaned_chats

    if result.orphaned_files > 0:
        print(f"\n📁 Files:")
        print(f"   {result.orphaned_files} orphaned file records")
        total_items += result.orphaned_files

    workspace_total = (result.orphaned_tools + result.orphaned_functions +
                       result.orphaned_prompts + result.orphaned_knowledge_bases +
                       result.orphaned_models + result.orphaned_notes)
    if workspace_total > 0:
        print(f"\n🔧 Workspace Items:")
        if result.orphaned_tools > 0:
            print(f"   {result.orphaned_tools} orphaned tools")
        if result.orphaned_functions > 0:
            print(f"   {result.orphaned_functions} orphaned functions")
        if result.orphaned_prompts > 0:
            print(f"   {result.orphaned_prompts} orphaned prompts")
        if result.orphaned_knowledge_bases > 0:
            print(f"   {result.orphaned_knowledge_bases} orphaned knowledge bases")
        if result.orphaned_models > 0:
            print(f"   {result.orphaned_models} orphaned models")
        if result.orphaned_notes > 0:
            print(f"   {result.orphaned_notes} orphaned notes")
        total_items += workspace_total

    if result.orphaned_folders > 0:
        print(f"\n📂 Folders:")
        print(f"   {result.orphaned_folders} orphaned folders")
        total_items += result.orphaned_folders

    if result.orphaned_uploads > 0 or result.orphaned_vector_collections > 0:
        print(f"\n💾 Storage:")
        if result.orphaned_uploads > 0:
            print(f"   {result.orphaned_uploads} orphaned upload files")
        if result.orphaned_vector_collections > 0:
            print(f"   {result.orphaned_vector_collections} orphaned vector collections")
        total_items += result.orphaned_uploads + result.orphaned_vector_collections

    if result.audio_cache_files > 0:
        print(f"\n🔊 Audio Cache:")
        print(f"   {result.audio_cache_files} old audio cache files")
        total_items += result.audio_cache_files

    print("\n" + "="*70)
    print(f"  TOTAL ITEMS TO DELETE: {total_items}")
    print("="*70)

    if total_items == 0:
        print("\n✅ Nothing to delete - your database is clean!")
    else:
        print("\n⚠️  Run with --execute to perform actual deletion")
        print("   (This is a preview only, no changes were made)")
    print()


def run_prune(form_data: PruneDataForm):
    """
    Execute the prune operation with the given configuration.
    This replicates the logic from prune.py's prune_data function.
    """
    # Acquire lock to prevent concurrent operations
    if not PruneLock.acquire():
        log.error("A prune operation is already in progress. Please wait for it to complete.")
        return False

    try:
        # Get vector database cleaner based on configuration
        vector_cleaner = get_vector_database_cleaner()

        if form_data.dry_run:
            log.info("Starting data pruning preview (dry run)")

            # Get counts for all enabled operations
            knowledge_bases = Knowledges.get_knowledge_bases()
            all_users = Users.get_users()["users"]
            active_user_ids = {user.id for user in all_users}
            active_kb_ids = {
                kb.id
                for kb in knowledge_bases
                if kb.user_id in active_user_ids
            }
            active_file_ids = get_active_file_ids(knowledge_bases)

            orphaned_counts = count_orphaned_records(form_data, active_file_ids, active_user_ids)

            result = PrunePreviewResult(
                inactive_users=count_inactive_users(
                    form_data.delete_inactive_users_days,
                    form_data.exempt_admin_users,
                    form_data.exempt_pending_users,
                    all_users,
                ),
                old_chats=count_old_chats(
                    form_data.days,
                    form_data.exempt_archived_chats,
                    form_data.exempt_chats_in_folders,
                ),
                orphaned_chats=orphaned_counts["chats"],
                orphaned_files=orphaned_counts["files"],
                orphaned_tools=orphaned_counts["tools"],
                orphaned_functions=orphaned_counts["functions"],
                orphaned_prompts=orphaned_counts["prompts"],
                orphaned_knowledge_bases=orphaned_counts["knowledge_bases"],
                orphaned_models=orphaned_counts["models"],
                orphaned_notes=orphaned_counts["notes"],
                orphaned_folders=orphaned_counts["folders"],
                orphaned_uploads=count_orphaned_uploads(active_file_ids),
                orphaned_vector_collections=vector_cleaner.count_orphaned_collections(
                    active_file_ids, active_kb_ids, active_user_ids
                ),
                audio_cache_files=count_audio_cache_files(
                    form_data.audio_cache_max_age_days
                ),
            )

            log.info("Data pruning preview completed")
            print_preview_results(result)
            return True

        # Actual deletion logic (dry_run=False)
        log.info("Starting data pruning process (ACTUAL DELETION)")

        # Stage 0: Delete inactive users (if enabled)
        deleted_users = 0
        if form_data.delete_inactive_users_days is not None:
            log.info(
                f"Deleting users inactive for more than {form_data.delete_inactive_users_days} days"
            )
            deleted_users = delete_inactive_users(
                form_data.delete_inactive_users_days,
                form_data.exempt_admin_users,
                form_data.exempt_pending_users,
            )
            if deleted_users > 0:
                log.info(f"Deleted {deleted_users} inactive users")
            else:
                log.info("No inactive users found to delete")
        else:
            log.info("Skipping inactive user deletion (disabled)")

        # Stage 1: Delete old chats based on user criteria
        if form_data.days is not None:
            cutoff_time = int(time.time()) - (form_data.days * 86400)
            chats_to_delete = []

            for chat in Chats.get_chats():
                if chat.updated_at < cutoff_time:
                    if form_data.exempt_archived_chats and chat.archived:
                        continue
                    if form_data.exempt_chats_in_folders and (
                        getattr(chat, "folder_id", None) is not None
                        or getattr(chat, "pinned", False)
                    ):
                        continue
                    chats_to_delete.append(chat)

            if chats_to_delete:
                log.info(
                    f"Deleting {len(chats_to_delete)} old chats (older than {form_data.days} days)"
                )
                for chat in chats_to_delete:
                    Chats.delete_chat_by_id(chat.id)
            else:
                log.info(f"No chats found older than {form_data.days} days")
        else:
            log.info("Skipping chat deletion (days parameter is None)")

        # Stage 2: Build preservation set
        log.info("Building preservation set")

        active_user_ids = {user.id for user in Users.get_users()["users"]}
        log.info(f"Found {len(active_user_ids)} active users")

        active_kb_ids = set()
        knowledge_bases = Knowledges.get_knowledge_bases()

        for kb in knowledge_bases:
            if kb.user_id in active_user_ids:
                active_kb_ids.add(kb.id)

        log.info(f"Found {len(active_kb_ids)} active knowledge bases")

        active_file_ids = get_active_file_ids(knowledge_bases)

        # Stage 3: Delete orphaned database records
        log.info("Deleting orphaned database records")

        deleted_files = 0
        for file_record in Files.get_files():
            should_delete = (
                file_record.id not in active_file_ids
                or file_record.user_id not in active_user_ids
            )

            if should_delete:
                if safe_delete_file_by_id(file_record.id):
                    deleted_files += 1

        if deleted_files > 0:
            log.info(f"Deleted {deleted_files} orphaned files")

        deleted_kbs = 0
        if form_data.delete_orphaned_knowledge_bases:
            for kb in knowledge_bases:
                if kb.user_id not in active_user_ids:
                    if vector_cleaner.delete_collection(kb.id):
                        Knowledges.delete_knowledge_by_id(kb.id)
                        deleted_kbs += 1

            if deleted_kbs > 0:
                log.info(f"Deleted {deleted_kbs} orphaned knowledge bases")
        else:
            log.info("Skipping knowledge base deletion (disabled)")

        deleted_others = 0

        if form_data.delete_orphaned_chats:
            chats_deleted = 0
            for chat in Chats.get_chats():
                if chat.user_id not in active_user_ids:
                    Chats.delete_chat_by_id(chat.id)
                    chats_deleted += 1
                    deleted_others += 1
            if chats_deleted > 0:
                log.info(f"Deleted {chats_deleted} orphaned chats")
        else:
            log.info("Skipping orphaned chat deletion (disabled)")

        if form_data.delete_orphaned_tools:
            tools_deleted = 0
            for tool in Tools.get_tools():
                if tool.user_id not in active_user_ids:
                    Tools.delete_tool_by_id(tool.id)
                    tools_deleted += 1
                    deleted_others += 1
            if tools_deleted > 0:
                log.info(f"Deleted {tools_deleted} orphaned tools")
        else:
            log.info("Skipping tool deletion (disabled)")

        if form_data.delete_orphaned_functions:
            functions_deleted = 0
            for function in Functions.get_functions():
                if function.user_id not in active_user_ids:
                    Functions.delete_function_by_id(function.id)
                    functions_deleted += 1
                    deleted_others += 1
            if functions_deleted > 0:
                log.info(f"Deleted {functions_deleted} orphaned functions")
        else:
            log.info("Skipping function deletion (disabled)")

        if form_data.delete_orphaned_notes:
            notes_deleted = 0
            for note in Notes.get_notes():
                if note.user_id not in active_user_ids:
                    Notes.delete_note_by_id(note.id)
                    notes_deleted += 1
                    deleted_others += 1
            if notes_deleted > 0:
                log.info(f"Deleted {notes_deleted} orphaned notes")
        else:
            log.info("Skipping note deletion (disabled)")

        if form_data.delete_orphaned_prompts:
            prompts_deleted = 0
            for prompt in Prompts.get_prompts():
                if prompt.user_id not in active_user_ids:
                    Prompts.delete_prompt_by_command(prompt.command)
                    prompts_deleted += 1
                    deleted_others += 1
            if prompts_deleted > 0:
                log.info(f"Deleted {prompts_deleted} orphaned prompts")
        else:
            log.info("Skipping prompt deletion (disabled)")

        if form_data.delete_orphaned_models:
            models_deleted = 0
            for model in Models.get_all_models():
                if model.user_id not in active_user_ids:
                    Models.delete_model_by_id(model.id)
                    models_deleted += 1
                    deleted_others += 1
            if models_deleted > 0:
                log.info(f"Deleted {models_deleted} orphaned models")
        else:
            log.info("Skipping model deletion (disabled)")

        if form_data.delete_orphaned_folders:
            folders_deleted = 0
            for folder in Folders.get_all_folders():
                if folder.user_id not in active_user_ids:
                    Folders.delete_folder_by_id_and_user_id(
                        folder.id, folder.user_id
                    )
                    folders_deleted += 1
                    deleted_others += 1
            if folders_deleted > 0:
                log.info(f"Deleted {folders_deleted} orphaned folders")
        else:
            log.info("Skipping folder deletion (disabled)")

        if deleted_others > 0:
            log.info(f"Total other orphaned records deleted: {deleted_others}")

        # Stage 4: Clean up orphaned physical files
        log.info("Cleaning up orphaned physical files")

        final_active_file_ids = get_active_file_ids()
        final_active_kb_ids = {kb.id for kb in Knowledges.get_knowledge_bases()}
        final_active_user_ids = {user.id for user in Users.get_users()["users"]}

        cleanup_orphaned_uploads(final_active_file_ids)

        # Audio cache cleanup
        if form_data.audio_cache_max_age_days is not None:
            log.info(f"Cleaning audio cache files older than {form_data.audio_cache_max_age_days} days")
            cleanup_audio_cache(form_data.audio_cache_max_age_days)

        # Use modular vector database cleanup
        warnings = []
        deleted_vector_count, vector_error = vector_cleaner.cleanup_orphaned_collections(
            final_active_file_ids, final_active_kb_ids, final_active_user_ids
        )
        if vector_error:
            warnings.append(f"Vector cleanup warning: {vector_error}")
            log.warning(f"Vector cleanup completed with errors: {vector_error}")

        # Stage 5: Database optimization (optional)
        if form_data.run_vacuum:
            log.info("Optimizing database with VACUUM (this may take a while and lock the database)")

            try:
                with get_db() as db:
                    db.execute(text("VACUUM"))
                    log.info("Vacuumed main database")
            except Exception as e:
                log.error(f"Failed to vacuum main database: {e}")

            # Vector database-specific optimization
            if isinstance(vector_cleaner, ChromaDatabaseCleaner):
                try:
                    with sqlite3.connect(str(vector_cleaner.chroma_db_path)) as conn:
                        conn.execute("VACUUM")
                        log.info("Vacuumed ChromaDB database")
                except Exception as e:
                    log.error(f"Failed to vacuum ChromaDB database: {e}")
            elif (
                isinstance(vector_cleaner, PGVectorDatabaseCleaner)
                and vector_cleaner.session
            ):
                try:
                    vector_cleaner.session.execute(text("VACUUM ANALYZE"))
                    vector_cleaner.session.commit()
                    log.info("Executed VACUUM ANALYZE on PostgreSQL database")
                except Exception as e:
                    log.error(f"Failed to vacuum PostgreSQL database: {e}")
        else:
            log.info("Skipping VACUUM optimization (not enabled)")

        # Log any warnings collected during pruning
        if warnings:
            log.warning(f"Data pruning completed with warnings: {'; '.join(warnings)}")

        log.info("Data pruning completed successfully")
        return True

    except Exception as e:
        log.exception(f"Error during data pruning: {e}")
        return False
    finally:
        # Always release lock, even if operation fails
        PruneLock.release()


def main():
    """Main entry point for standalone prune script."""
    args = parse_arguments()
    configure_logging(args.verbose, args.quiet)

    log.info("="*70)
    log.info("  Open WebUI Standalone Prune Script")
    log.info("="*70)

    # Verify environment
    log.info("Checking environment configuration...")

    # Check if we can access database
    try:
        users = Users.get_users()
        log.info(f"✓ Database connection successful ({len(users['users'])} users found)")
    except Exception as e:
        log.error(f"✗ Failed to connect to database: {e}")
        log.error("  Make sure DATABASE_URL environment variable is set correctly")
        return 1

    # Create prune configuration
    form_data = create_prune_form(args)

    # Log configuration
    log.info("\nPrune Configuration:")
    if form_data.dry_run:
        log.info("  Mode: DRY RUN (preview only, no changes)")
    else:
        log.info("  Mode: EXECUTE (actual deletion)")

    if form_data.days is not None:
        log.info(f"  Delete chats older than: {form_data.days} days")
        log.info(f"    Exempt archived chats: {form_data.exempt_archived_chats}")
        log.info(f"    Exempt chats in folders: {form_data.exempt_chats_in_folders}")

    if form_data.delete_inactive_users_days is not None:
        log.info(f"  Delete inactive users: {form_data.delete_inactive_users_days} days")
        log.info(f"    Exempt admin users: {form_data.exempt_admin_users}")
        log.info(f"    Exempt pending users: {form_data.exempt_pending_users}")

    log.info("  Orphaned data deletion:")
    log.info(f"    Chats: {form_data.delete_orphaned_chats}")
    log.info(f"    Tools: {form_data.delete_orphaned_tools}")
    log.info(f"    Functions: {form_data.delete_orphaned_functions}")
    log.info(f"    Prompts: {form_data.delete_orphaned_prompts}")
    log.info(f"    Knowledge Bases: {form_data.delete_orphaned_knowledge_bases}")
    log.info(f"    Models: {form_data.delete_orphaned_models}")
    log.info(f"    Notes: {form_data.delete_orphaned_notes}")
    log.info(f"    Folders: {form_data.delete_orphaned_folders}")

    if form_data.audio_cache_max_age_days is not None:
        log.info(f"  Audio cache cleanup: {form_data.audio_cache_max_age_days} days")

    if form_data.run_vacuum:
        log.info("  Database VACUUM: ENABLED (will lock database!)")

    log.info("")

    # Run the prune operation
    success = run_prune(form_data)

    if success:
        log.info("\n✓ Prune operation completed successfully")
        return 0
    else:
        log.error("\n✗ Prune operation failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
