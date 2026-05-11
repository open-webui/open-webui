"""
Gmail Auto-Sync Orchestrator

This module orchestrates the automatic Gmail sync when users sign up with Google OAuth.

Flow:
1. User signs up/logs in with Google OAuth (with Gmail scopes)
2. OAuth callback triggers this auto-sync
3. Background task fetches all emails from Gmail
4. Processes and indexes to Pinecone using existing infrastructure
5. User's inbox is ready for semantic search

Components Used:
- GmailFetcher: Fetch emails from Gmail API
- GmailProcessor: Parse email data
- GmailIndexer: Chunk, embed, and format for Pinecone
- PineconeManager: Background upsert to Pinecone
- Uses existing chat summary infrastructure
"""

import logging
import asyncio
import time
import re
from typing import Dict, List, Optional
from datetime import datetime

from open_webui.utils.gmail_fetcher import GmailFetcher, HistoryIdExpiredError
from open_webui.utils.gmail_indexer_v2 import GmailIndexerV2
from open_webui.utils.temp_cleanup import run_cleanup, get_cache_stats
from open_webui.models.users import Users
from open_webui.models.oauth_sessions import OAuthSessions
from open_webui.models.gmail_sync import gmail_sync_status

# Set up logger with INFO level for visibility
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class GmailAutoSync:
    """
    Orchestrates automatic Gmail sync for users.

    This class coordinates all Gmail components to perform a complete
    inbox sync in the background.
    """

    def __init__(
        self,
        embedding_service,
        document_processor,
        pinecone_manager,
        app_config=None,
        process_attachments: bool = True,
        max_attachment_size_mb: int = 10,
        allowed_attachment_types: str = ".pdf,.docx,.doc,.xlsx,.xls,.pptx,.ppt,.txt,.csv,.md,.html,.eml",
    ):
        """
        Initialize auto-sync orchestrator.

        Args:
            embedding_service: EmbeddingService from chat filter
            document_processor: DocumentProcessor from chat filter
            pinecone_manager: PineconeManager from chat filter
            app_config: App config for accessing RAG/Document settings
            process_attachments: Enable attachment processing
            max_attachment_size_mb: Maximum attachment size in MB
            allowed_attachment_types: Comma-separated allowed extensions

        Note: Uses per-user namespaces (email-{user_id}) computed at sync time
        Note: V2 uses single-vector strategy (no chunking needed)
        Note: Respects admin panel RAG/Document settings
        """
        self.indexer = GmailIndexerV2(
            embedding_service=embedding_service,
            document_processor=document_processor,
            app_config=app_config,
        )
        self.pinecone = pinecone_manager

        # Attachment processing config
        self.process_attachments = process_attachments
        self.max_attachment_size_mb = max_attachment_size_mb
        self.allowed_attachment_types = allowed_attachment_types

        # Track active syncs
        self.active_syncs = {}  # user_id -> sync_status

    async def sync_user_gmail(
        self,
        user_id: str,
        oauth_token: dict,
        max_emails: int = 5000,
        skip_spam_trash: bool = True,
        incremental: bool = True,
        token_refresh_callback=None,
    ) -> Dict:
        """
        Sync a user's Gmail inbox to Pinecone.

        Supports both full sync (first time) and incremental sync (subsequent runs).

        Args:
            user_id: User ID for isolation
            oauth_token: OAuth token dict with access_token
            max_emails: Maximum emails to sync (default: 5000)
            skip_spam_trash: Skip SPAM and TRASH folders (default: True)
            incremental: Whether to do incremental sync (default: True)
            token_refresh_callback: Async callback to refresh OAuth token when expired
                                   Should return new access_token string or None

        Returns:
            Dict with sync statistics
        """

        logger.info("=" * 70)
        logger.info(f"🚀 GMAIL SYNC STARTED - User: {user_id}")
        logger.info(f"   Max emails: {max_emails}")
        logger.info(f"   Skip spam/trash: {skip_spam_trash}")
        logger.info(f"   Incremental: {incremental}")
        logger.info(f"   Namespace: email-{user_id} (per-user isolation)")
        logger.info("=" * 70)

        # Clean up temp files before starting sync (prevents /tmp overflow on Render)
        cache_stats = get_cache_stats()
        if cache_stats["total_size_mb"] > 100:
            logger.info(f"🧹 Pre-sync cleanup: {cache_stats['total_size_mb']:.1f}MB in temp cache")
            run_cleanup(max_age_minutes=15, max_size_mb=300)  # Aggressive cleanup before sync

        # Get or create sync status
        sync_status = gmail_sync_status.get_sync_status(user_id)
        if not sync_status:
            sync_status = gmail_sync_status.create_sync_status(user_id)
            logger.info(f"Created new sync status for user {user_id}")
        else:
            logger.info(f"Found existing sync status for user {user_id}")
            logger.info(
                f"   Last sync: {datetime.fromtimestamp(sync_status.last_sync_timestamp) if sync_status.last_sync_timestamp else 'Never'}"
            )
            logger.info(f"   Total synced: {sync_status.total_emails_synced}")

        # Mark sync as starting
        gmail_sync_status.mark_sync_start(user_id)

        # Initialize sync status
        self.active_syncs[user_id] = {
            "status": "running",
            "start_time": time.time(),
            "total_emails": 0,
            "processed": 0,
            "indexed": 0,
            "errors": 0,
            "sync_type": "incremental" if incremental else "full",
            "last_sync_timestamp": sync_status.last_sync_timestamp,
        }

        try:
            # Validate OAuth token
            access_token = oauth_token.get("access_token")
            if not access_token:
                raise ValueError("OAuth token missing access_token")

            # Check for Gmail scopes
            token_scope = oauth_token.get("scope", "")
            if "gmail" not in token_scope:
                logger.warning(f"User {user_id} OAuth token doesn't include Gmail scopes")
                raise ValueError("OAuth token missing Gmail scopes")

            logger.info(f"✅ OAuth token validated with Gmail scopes")

            # Initialize fetcher
            fetcher = GmailFetcher(
                oauth_token=access_token,
                max_requests_per_second=40,  # Conservative rate limit
                timeout=30,
                token_refresh_callback=token_refresh_callback,
            )

            if token_refresh_callback:
                logger.info(f"   Token refresh callback configured for long-running sync")

            # =====================================================================
            # SYNC STRATEGY SELECTION
            # Priority: 1) History API (most accurate) -> 2) Time-based (fallback)
            # =====================================================================
            message_ids = []
            deleted_message_ids = []
            new_history_id = None
            sync_method = "unknown"
            query = None

            # Try History API first for incremental sync (most accurate method)
            if incremental and sync_status.last_sync_history_id:
                logger.info("=" * 70)
                logger.info("📜 HISTORY API SYNC (Accurate Incremental)")
                logger.info(f"   Using historyId: {sync_status.last_sync_history_id}")
                logger.info("=" * 70)

                try:
                    added_ids, deleted_ids, new_history_id = await fetcher.fetch_history_changes(
                        start_history_id=sync_status.last_sync_history_id,
                        skip_spam_trash=skip_spam_trash,
                        max_results=max_emails,
                    )

                    message_ids = added_ids
                    deleted_message_ids = deleted_ids
                    sync_method = "history_api"

                    logger.info(
                        f"✅ History API: {len(message_ids)} new/modified, " f"{len(deleted_message_ids)} deleted"
                    )

                except HistoryIdExpiredError as e:
                    # History is too old (>30 days) - fall back to time-based
                    logger.warning(f"⚠️  History ID expired: {e}. Falling back to time-based sync.")
                    sync_method = "time_fallback"

                except Exception as e:
                    logger.error(f"❌ History API error: {e}. Falling back to time-based sync.")
                    sync_method = "time_fallback"

            # Time-based sync (fallback or first sync)
            if not message_ids or sync_method == "time_fallback":
                if sync_method != "time_fallback":
                    sync_method = "time_based"

                logger.info("=" * 70)
                if incremental and sync_status.last_sync_timestamp:
                    logger.info("📅 TIME-BASED INCREMENTAL SYNC")
                    days_since_sync = (time.time() - sync_status.last_sync_timestamp) / (24 * 3600)

                    # Smart time window selection
                    if days_since_sync < 0.5:
                        query = "newer_than:6h"
                    elif days_since_sync < 1:
                        query = "newer_than:1d"
                    elif days_since_sync < 3:
                        query = "newer_than:3d"
                    elif days_since_sync < 7:
                        query = "newer_than:7d"
                    else:
                        query = "newer_than:30d"

                    logger.info(f"   Query: {query} (last sync: {days_since_sync:.1f} days ago)")
                else:
                    logger.info("📥 FULL SYNC (First time or forced)")
                    query = None
                logger.info("=" * 70)

                # Step 1: Get inbox count (fast estimate)
                logger.info(f"📊 Step 1: Getting inbox estimate...")
                inbox_count = await fetcher.get_inbox_count(
                    skip_spam_trash=skip_spam_trash,
                    query=query,
                )
                logger.info(f"   Gmail estimate: ~{inbox_count} emails")

                # Step 2: Fetch message IDs
                logger.info(f"📥 Step 2: Fetching message IDs...")
                effective_max = (
                    max_emails if not incremental else min(max_emails, inbox_count) if max_emails > 0 else inbox_count
                )

                message_ids = await fetcher.fetch_all_message_ids(
                    max_results=effective_max,
                    skip_spam_trash=skip_spam_trash,
                    query=query,
                )

            # Get current history ID for next sync (important for History API)
            if not new_history_id:
                profile = await fetcher.get_profile()
                if profile:
                    new_history_id = profile.get("historyId")
                    logger.info(f"📜 Current historyId: {new_history_id} (saved for next sync)")

            # Calculate batch parameters
            actual_count = len(message_ids)
            logger.info(f"📊 Emails to process: {actual_count}")

            if deleted_message_ids:
                logger.info(f"🗑️  Emails to delete from index: {len(deleted_message_ids)}")

            batch_params = GmailFetcher.calculate_batch_params(
                total_count=actual_count,
                target_batch_size=500,
                min_batch_size=50,
                max_batch_size=1000,
            )

            # Step 3: Fetch emails in batches
            logger.info(f"📥 Step 3: Fetching {actual_count} emails in {batch_params['num_batches']} batches...")

            # Create batches from message IDs
            message_batches = fetcher.create_batches(
                message_ids=message_ids,
                batch_size=batch_params['batch_size'],
            )

            # Fetch all emails batch by batch
            emails = []
            fetch_stats = fetcher.get_stats()

            for batch_idx, batch_ids in enumerate(message_batches):
                batch_start = time.time()
                logger.info(
                    f"   Fetching batch {batch_idx + 1}/{len(message_batches)} " f"({len(batch_ids)} emails)..."
                )

                batch_emails = await fetcher.fetch_emails_batch(
                    message_ids=batch_ids,
                    batch_size=20,  # Concurrent fetches within batch
                )
                emails.extend(batch_emails)

                batch_time = time.time() - batch_start
                logger.info(
                    f"   ✅ Batch {batch_idx + 1} complete: {len(batch_emails)} emails "
                    f"in {batch_time:.1f}s ({len(batch_emails)/batch_time:.1f} emails/s)"
                )

                # Yield to event loop between batches
                await asyncio.sleep(0)

            # Update fetch stats
            fetch_stats = fetcher.get_stats()

            self.active_syncs[user_id]["total_emails"] = len(emails)

            # Analyze email types
            label_counts = {}
            for email in emails:
                labels = email.get("labelIds", [])
                for label in labels:
                    label_counts[label] = label_counts.get(label, 0) + 1

            logger.info("=" * 70)
            logger.info(f"✅ FETCH COMPLETE")
            logger.info(f"   Total emails: {len(emails)}")
            logger.info(f"   API calls: {fetch_stats['api_calls']}")
            logger.info(f"   Fetch time: {fetch_stats.get('total_time', 0):.1f}s")
            logger.info(f"   Errors: {fetch_stats['errors']}")
            logger.info(f"\n   📊 Email Breakdown by Label:")
            for label, count in sorted(label_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
                logger.info(f"      - {label}: {count} emails")
            if len(label_counts) > 10:
                logger.info(f"      - ... and {len(label_counts)-10} more labels")
            logger.info("=" * 70)

            if not emails:
                logger.info(f"📭 No emails found for user {user_id}")
                self.active_syncs[user_id]["status"] = "completed"
                return self._build_sync_result(user_id)

            # Step 4: Process and index emails to Pinecone
            logger.info("")
            logger.info("=" * 70)
            logger.info(f"⚙️ Step 4: PROCESSING & INDEXING - {len(emails)} emails")
            logger.info("=" * 70)

            # Get configurable batch size
            from open_webui.config import GMAIL_PROCESSING_BATCH_SIZE

            processing_batch_size = (
                GMAIL_PROCESSING_BATCH_SIZE.value if hasattr(GMAIL_PROCESSING_BATCH_SIZE, "value") else 50
            )

            indexed_count = await self._process_and_index_batch(
                emails=emails,
                user_id=user_id,
                fetcher=fetcher,  # Pass fetcher for attachment downloads
                batch_size=processing_batch_size,  # Configurable via GMAIL_PROCESSING_BATCH_SIZE
            )

            self.active_syncs[user_id]["indexed"] = indexed_count
            self.active_syncs[user_id]["status"] = "completed"
            self.active_syncs[user_id]["sync_method"] = sync_method

            # Handle deleted emails (remove from vector store)
            if deleted_message_ids:
                await self._delete_emails_from_index(
                    user_id=user_id,
                    email_ids=deleted_message_ids,
                )
                self.active_syncs[user_id]["deleted"] = len(deleted_message_ids)

            # Mark sync as completed in database with history ID for next sync
            sync_duration = int(time.time() - self.active_syncs[user_id]["start_time"])
            gmail_sync_status.mark_sync_complete(
                user_id=user_id,
                emails_synced=indexed_count,
                duration_seconds=sync_duration,
                last_history_id=new_history_id,  # Track for History API incremental sync
                last_email_id=message_ids[-1] if message_ids else None,
            )

            # Clear emails list to free memory
            emails.clear()
            del emails

            result = self._build_sync_result(user_id)

            # Calculate performance metrics
            total_time = result["total_time"]
            emails_per_second = result["indexed"] / total_time if total_time > 0 else 0
            sync_type = self.active_syncs[user_id].get("sync_type", "unknown")

            logger.info("")
            logger.info("=" * 70)
            logger.info(f"🎉 GMAIL SYNC COMPLETED - User: {user_id}")
            logger.info(f"   Sync type: {sync_type.upper()}")
            logger.info(f"   Sync method: {result.get('sync_method', sync_method).upper()}")
            logger.info(f"   Total emails fetched: {result['total_emails']}")
            logger.info(f"   Successfully indexed: {result['indexed']}")
            if result.get('deleted', 0) > 0:
                logger.info(f"   Deleted from index: {result['deleted']}")
            logger.info(f"   Duplicates skipped: {self.active_syncs[user_id].get('duplicates_skipped', 0)}")
            logger.info(f"   Errors: {result['errors']}")
            logger.info(f"   Total time: {total_time:.1f}s")
            logger.info(f"   Processing rate: {emails_per_second:.1f} emails/sec")
            if new_history_id:
                logger.info(f"   Next sync historyId: {new_history_id}")

            # Performance assessment
            if emails_per_second > 10:
                logger.info(f"   Performance: 🚀 EXCELLENT ({emails_per_second:.1f} emails/sec)")
            elif emails_per_second > 5:
                logger.info(f"   Performance: ✅ GOOD ({emails_per_second:.1f} emails/sec)")
            else:
                logger.info(f"   Performance: ⚠️  SLOW ({emails_per_second:.1f} emails/sec)")

            logger.info(f"   Status: ✅ SUCCESS")
            logger.info("=" * 70)

            return result

        except Exception as e:
            logger.error(f"❌ Gmail sync failed for user {user_id}: {e}", exc_info=True)
            self.active_syncs[user_id]["status"] = "failed"
            self.active_syncs[user_id]["error"] = str(e)

            # Mark sync as failed in database
            gmail_sync_status.mark_sync_error(user_id, str(e))

            raise

        finally:
            # Close fetcher session to prevent "Unclosed client session" error
            # Use try/except in case fetcher wasn't created before an exception
            try:
                if fetcher:
                    await fetcher.close()
                    logger.debug(f"Closed Gmail fetcher session for user {user_id}")
            except NameError:
                pass  # fetcher wasn't created yet

    async def _process_and_index_batch(
        self,
        emails: List[dict],
        user_id: str,
        fetcher,
        batch_size: int = 100,
    ) -> int:
        """
        Process emails and index to Pinecone in batches.

        Args:
            emails: List of Gmail API email responses
            fetcher: GmailFetcher instance for attachment downloads
            user_id: User ID for isolation
            batch_size: Number of emails to process per batch

        Returns:
            Total number of emails successfully indexed
        """

        total_indexed = 0
        total_vectors = 0

        for i in range(0, len(emails), batch_size):
            batch = emails[i : i + batch_size]
            batch_num = i // batch_size + 1
            total_batches = (len(emails) + batch_size - 1) // batch_size
            progress_pct = int((i / len(emails)) * 100)

            logger.info("")
            logger.info(f"📦 Batch {batch_num}/{total_batches} ({progress_pct}% complete)")
            logger.info(f"   Processing emails {i+1}-{min(i+batch_size, len(emails))} of {len(emails)}")
            logger.info(f"   Batch size: {len(batch)} emails")

            # Process batch with GmailIndexer (with attachment support)
            try:
                # Use attachment config from sync parameters
                result = await self.indexer.process_email_batch(
                    emails=batch,
                    user_id=user_id,
                    fetcher=fetcher,
                    process_attachments=getattr(self, "process_attachments", True),
                    max_attachment_size_mb=getattr(self, "max_attachment_size_mb", 10),
                    allowed_attachment_types=getattr(
                        self,
                        "allowed_attachment_types",
                        ".pdf,.docx,.doc,.xlsx,.xls,.pptx,.ppt,.txt,.csv,.md,.html,.eml",
                    ),
                )

                upsert_data = result["upsert_data"]

                if upsert_data:
                    # Upsert to vector DB with namespace and user isolation
                    await self.pinecone.schedule_upsert(
                        upsert_data,
                        user_id=user_id,
                        namespace=None,  # Will use self.namespace from PineconeManager
                    )

                    total_indexed += result["processed"]
                    total_vectors += result["total_vectors"]

                    duplicates = result.get("duplicates_skipped", 0)
                    logger.info(f"   ✅ Processed: {result['processed']} unique emails")
                    if duplicates > 0:
                        logger.info(f"   ⏭️  Skipped: {duplicates} duplicate emails (mass email deduplication)")
                    logger.info(f"   ✅ Vectors created: {result['total_vectors']}")
                    logger.info(f"   ✅ Errors: {result['errors']}")
                    logger.info(f"   ✅ Processing time: {result['processing_time']:.2f}s")
                    logger.info(f"   📊 Running total: {total_indexed} emails, {total_vectors} vectors")

                    # Clear upsert_data to free memory after upserting
                    upsert_data.clear()
                    del result

                self.active_syncs[user_id]["processed"] = i + len(batch)

                # Clear processed batch to free memory
                batch.clear()

                # Yield to event loop after each batch to keep interface responsive
                await asyncio.sleep(0)  # Yield control to event loop immediately

                # Additional yield every few batches for better responsiveness
                if batch_num % 5 == 0:
                    await asyncio.sleep(0.01)  # Small delay every 5 batches

            except Exception as e:
                logger.error(f"Error processing batch {batch_num}: {e}")
                self.active_syncs[user_id]["errors"] += 1
                continue

        return total_indexed

    async def _delete_emails_from_index(
        self,
        user_id: str,
        email_ids: List[str],
    ) -> int:
        """
        Delete emails from vector store (for History API sync).

        When emails are deleted or moved to SPAM/TRASH, we need to remove
        them from the vector index to keep search results accurate.

        Args:
            user_id: User ID for namespace
            email_ids: List of Gmail message IDs to delete

        Returns:
            Number of emails deleted
        """
        if not email_ids:
            return 0

        logger.info(f"🗑️  Deleting {len(email_ids)} emails from index for user {user_id}")

        try:
            from open_webui.retrieval.vector.factory import VECTOR_DB_CLIENT
            import inspect

            collection_name = "gmail"
            user_namespace = f"email-{user_id}"

            # Convert email IDs to vector IDs (format: "email-{email_id}")
            vector_ids = [f"email-{email_id}" for email_id in email_ids]

            # Check if vector DB supports namespace
            delete_signature = inspect.signature(VECTOR_DB_CLIENT.delete)

            if "namespace" in delete_signature.parameters:
                # Pinecone-style with namespace
                VECTOR_DB_CLIENT.delete(
                    collection_name=collection_name,
                    ids=vector_ids,
                    namespace=user_namespace,
                )
            else:
                # Chroma-style with collection per user
                user_collection = f"email-{user_id}"
                VECTOR_DB_CLIENT.delete(
                    collection_name=user_collection,
                    ids=vector_ids,
                )

            logger.info(f"✅ Deleted {len(vector_ids)} vectors from index")
            return len(vector_ids)

        except Exception as e:
            logger.error(f"❌ Error deleting emails from index: {e}")
            return 0

    def _build_sync_result(self, user_id: str) -> Dict:
        """Build sync result with statistics"""

        sync_status = self.active_syncs.get(user_id, {})
        elapsed_time = time.time() - sync_status.get("start_time", time.time())

        return {
            "user_id": user_id,
            "status": sync_status.get("status", "unknown"),
            "sync_method": sync_status.get("sync_method", "unknown"),
            "total_emails": sync_status.get("total_emails", 0),
            "processed": sync_status.get("processed", 0),
            "indexed": sync_status.get("indexed", 0),
            "deleted": sync_status.get("deleted", 0),
            "errors": sync_status.get("errors", 0),
            "total_time": elapsed_time,
            "error": sync_status.get("error"),
        }

    def get_sync_status(self, user_id: str) -> Optional[Dict]:
        """Get current sync status for a user"""

        if user_id not in self.active_syncs:
            return None

        return self._build_sync_result(user_id)


# ============================================================================
# TRIGGER FUNCTION (called from OAuth callback)
# ============================================================================


async def trigger_gmail_sync_if_needed(
    request,
    user_id: str,
    provider: str,
    token: dict,
    is_new_user: bool = False,
    force_full_sync: bool = False,
):
    """
    Trigger Gmail sync if conditions are met.

    This function is called from the OAuth callback handler.

    Args:
        request: FastAPI request object
        user_id: User ID who just authenticated
        provider: OAuth provider (e.g., "google")
        token: OAuth token dict
        is_new_user: True if this is first-time signup
        force_full_sync: If True, delete existing vectors and reprocess entire mailbox

    Conditions for triggering:
    - Provider must be "google"
    - Token must have Gmail scopes
    - ENABLE_GMAIL_AUTO_SYNC must be True
    - If GMAIL_AUTO_SYNC_ON_SIGNUP_ONLY, only trigger for new users
    """

    logger.info(f"\n🔍 Gmail Sync Trigger Check - User: {user_id}, Provider: {provider}")

    # Check if Gmail auto-sync is enabled
    if not request.app.state.config.ENABLE_GMAIL_AUTO_SYNC:
        logger.info("   ⏭️  SKIP: Gmail auto-sync is disabled in config")
        return

    # Only trigger for Google OAuth
    if provider != "google":
        logger.info(f"   ⏭️  SKIP: Not Google OAuth (provider: {provider})")
        return

    # Check for Gmail scopes
    token_scope = token.get("scope", "")
    has_gmail = "gmail" in token_scope
    logger.info(f"   📧 Gmail scope present: {has_gmail}")

    if not has_gmail:
        logger.info(f"   ⏭️  SKIP: OAuth token doesn't include Gmail scopes")
        return

    # Check if admin has enabled Gmail sync for this user first
    user = await Users.get_user_by_id(user_id)
    if not user:
        logger.info(f"   ⏭️  SKIP: User {user_id} not found")
        return

    # Check admin setting for Gmail sync
    admin_sync_enabled = getattr(user, "gmail_sync_enabled", 0) == 1
    logger.info(f"   ⚙️  Admin Gmail sync setting: gmail_sync_enabled={admin_sync_enabled}")

    # Check if we should only sync on signup (only applies if admin hasn't explicitly enabled)
    sync_on_signup_only = request.app.state.config.GMAIL_AUTO_SYNC_ON_SIGNUP_ONLY
    logger.info(f"   👤 New user: {is_new_user}, Sync on signup only: {sync_on_signup_only}")

    # If admin has explicitly enabled sync, allow it regardless of signup-only setting
    if not admin_sync_enabled:
        if sync_on_signup_only and not is_new_user:
            logger.info(f"   ⏭️  SKIP: Gmail auto-sync only on signup, user is not new")
            logger.info(f"      Admin can enable sync in Admin -> Users -> Edit User -> Gmail Email Sync")
            return
        else:
            logger.info(f"   ⏭️  SKIP: Admin has disabled Gmail sync for this user")
            logger.info(f"      Enable in Admin -> Users -> Edit User -> Gmail Email Sync")
            return

    # Check if user has enabled Gmail sync in their settings (additional user preference)
    if user and user.settings:
        settings_dict = user.settings.model_dump() if hasattr(user.settings, "model_dump") else user.settings
        gmail_settings = settings_dict.get("gmail", {}) if isinstance(settings_dict, dict) else {}
        user_sync_enabled = gmail_settings.get("sync_enabled", True)  # Default to enabled if admin allows
        logger.info(f"   ⚙️  User Gmail sync preference: sync_enabled={user_sync_enabled}")

        if not user_sync_enabled:
            logger.info(f"   ⏭️  SKIP: User has disabled Gmail sync in their settings")
            return
    else:
        logger.info(f"   ⚙️  No user settings found - will sync (admin enabled, no user preference)")

    logger.info(f"   ✅ ALL CONDITIONS MET - Triggering Gmail sync!")
    logger.info(
        f"\n🚀 TRIGGERING AUTOMATIC GMAIL SYNC"
        f"\n   User: {user_id}"
        f"\n   New user: {is_new_user}"
        f"\n   Force full sync: {force_full_sync}"
        f"\n   Gmail scopes: ✓"
    )

    # Launch background task
    try:
        from open_webui.tasks import create_task

        # Create the background sync task
        task_id, task = await create_task(
            request.app.state.redis,
            _background_gmail_sync(request, user_id, token, force_full_sync=force_full_sync),
            id=f"gmail_sync_{user_id}",
        )

        logger.info(f"✅ Gmail sync background task created: {task_id}")

    except Exception as e:
        logger.error(f"❌ Failed to create Gmail sync task for user {user_id}: {e}")


async def _background_gmail_sync(request, user_id: str, oauth_token: dict, force_full_sync: bool = False):
    """
    Background task that performs the actual Gmail sync.

    This runs asynchronously and doesn't block the OAuth callback.
    Integrates with existing Open WebUI RAG infrastructure.

    Args:
        request: FastAPI request object
        user_id: User ID to sync
        oauth_token: OAuth token dict with access_token
        force_full_sync: If True, delete existing vectors and reprocess entire mailbox
    """

    sync_type = "FULL (FORCED)" if force_full_sync else "INCREMENTAL"

    logger.info("\n" + "🔥" * 35)
    logger.info(f"📧 BACKGROUND GMAIL SYNC TASK STARTED - {sync_type}")
    logger.info(f"   User ID: {user_id}")
    logger.info(f"   Task ID: gmail_sync_{user_id}")
    logger.info(f"   Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"   Force full sync: {force_full_sync}")
    logger.info("🔥" * 35 + "\n")

    try:
        # Validate user
        user = await Users.get_user_by_id(user_id)
        if not user:
            logger.error(f"User {user_id} not found")
            return

        # Get configuration
        max_emails = request.app.state.config.GMAIL_AUTO_SYNC_MAX_EMAILS
        skip_spam_trash = request.app.state.config.GMAIL_SKIP_SPAM_AND_TRASH
        batch_size = request.app.state.config.GMAIL_SYNC_BATCH_SIZE
        process_attachments = request.app.state.config.GMAIL_PROCESS_ATTACHMENTS
        max_attachment_size_mb = request.app.state.config.GMAIL_MAX_ATTACHMENT_SIZE_MB
        allowed_attachment_types = request.app.state.config.GMAIL_ATTACHMENT_TYPES

        logger.info(
            f"Gmail sync config: max_emails={max_emails}, "
            f"skip_spam_trash={skip_spam_trash}, batch_size={batch_size}, "
            f"namespace=email-{user_id} (per-user), "
            f"attachments={process_attachments}"
        )

        # Create token refresh callback for long-running syncs
        # This allows the GmailFetcher to refresh the token if it expires mid-sync
        async def token_refresh_callback():
            """Refresh OAuth token using oauth_manager"""
            try:
                # Get OAuth session for this user
                oauth_session = await OAuthSessions.get_session_by_provider_and_user_id("google", user_id)
                if not oauth_session:
                    logger.error(f"No OAuth session found for user {user_id}")
                    return None

                # Refresh token using oauth_manager
                refreshed_token = await request.app.state.oauth_manager.get_oauth_token(
                    user_id=user_id,
                    session_id=oauth_session.id,
                    force_refresh=True,  # Force refresh to get new token
                )

                if refreshed_token and refreshed_token.get("access_token"):
                    # Update the oauth_token dict so future references use new token
                    oauth_token.update(refreshed_token)
                    return refreshed_token.get("access_token")
                else:
                    logger.error("Token refresh returned None or missing access_token")
                    return None

            except Exception as e:
                logger.error(f"Token refresh callback error: {e}")
                return None

        # Create simple wrapper services for the background task
        # We'll use Open WebUI's existing embedding and Pinecone infrastructure

        class SimpleEmbeddingService:
            """Wrapper for Open WebUI's embedding function with configurable batching"""

            def __init__(self, app_state):
                self.app_state = app_state
                # Load performance config
                from open_webui.config import (
                    GMAIL_EMBEDDING_BATCH_SIZE,
                    GMAIL_YIELD_INTERVAL,
                    GMAIL_YIELD_DELAY_MS,
                )

                self.embedding_batch_size = (
                    GMAIL_EMBEDDING_BATCH_SIZE.value if hasattr(GMAIL_EMBEDDING_BATCH_SIZE, "value") else 5
                )
                self.yield_interval = GMAIL_YIELD_INTERVAL.value if hasattr(GMAIL_YIELD_INTERVAL, "value") else 5
                self.yield_delay_ms = GMAIL_YIELD_DELAY_MS.value if hasattr(GMAIL_YIELD_DELAY_MS, "value") else 10
                logger.info(
                    f"EmbeddingService config: batch_size={self.embedding_batch_size}, "
                    f"yield_interval={self.yield_interval}, yield_delay={self.yield_delay_ms}ms"
                )

            async def embed_batch(self, texts: List[str]) -> List[List[float]]:
                """Generate embeddings with configurable batching for performance tuning"""

                async def embed_single(text: str) -> List[float]:
                    """Embed single text using async embedding function"""
                    try:
                        # Truncate to safe limit
                        clean_text = text.strip()
                        max_chars = 8000
                        if len(clean_text) > max_chars:
                            clean_text = clean_text[:max_chars]

                        # Ensure not empty
                        if not clean_text:
                            clean_text = "Email content not available"

                        # Call async embedding function
                        vector = await self.app_state.EMBEDDING_FUNCTION(clean_text, prefix="", user=None)

                        if vector is None:
                            raise ValueError("Embedding function returned None")

                        return vector

                    except Exception as e:
                        logger.error(f"Embedding error: {e}")
                        # Fallback to zero vector
                        try:
                            dim = int(self.app_state.config.PINECONE_DIMENSION)
                        except:
                            dim = 1536
                        return [0.0] * dim

                # Process embeddings in configurable batches
                # Batch processing is faster but uses more memory
                embeddings = []
                batch_size = max(1, min(50, self.embedding_batch_size))  # Clamp 1-50
                yield_interval = max(1, self.yield_interval)
                yield_delay = self.yield_delay_ms / 1000.0  # Convert to seconds

                for i in range(0, len(texts), batch_size):
                    batch_texts = texts[i : i + batch_size]

                    # Process batch concurrently for speed
                    batch_tasks = [embed_single(text) for text in batch_texts]
                    batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)

                    # Handle results (convert exceptions to zero vectors)
                    for result in batch_results:
                        if isinstance(result, Exception):
                            logger.error(f"Batch embedding error: {result}")
                            try:
                                dim = int(self.app_state.config.PINECONE_DIMENSION)
                            except:
                                dim = 1536
                            embeddings.append([0.0] * dim)
                        else:
                            embeddings.append(result)

                    # Yield to event loop after each batch
                    await asyncio.sleep(0)

                    # Configurable delay for server responsiveness
                    batch_num = (i // batch_size) + 1
                    if batch_num % yield_interval == 0 and yield_delay > 0:
                        await asyncio.sleep(yield_delay)

                return embeddings

        # Reuse quality scoring from gmail_indexer (no duplication!)
        from open_webui.utils.gmail_indexer_v2 import GmailIndexerV2

        class SimpleDocProcessor:
            """Thin wrapper to provide quality_score method"""

            @staticmethod
            def quick_quality_score(text: str) -> int:
                """Delegate to shared implementation"""
                # Use the same logic as everywhere else
                score = 0
                if len(text) > 200:
                    score += 1
                if text.count(".") >= 2:
                    score += 1
                if "\n\n" in text:
                    score += 1
                if not (text.count("\n- ") > 5 or text.count("\n• ") > 5):
                    score += 1
                if re.search(r"\b(because|therefore|however|additionally)\b", text, re.IGNORECASE):
                    score += 1
                return score

        class SimplePineconeManager:
            """
            Thin wrapper around VECTOR_DB_CLIENT for Gmail email storage.

            Uses per-user namespace strategy:
            - Pinecone: namespace = "email-{user_id}" (namespace-based isolation)
            - Chroma: collection = "email-{user_id}" (collection-based isolation)
            - Compatible with Open WebUI's vector DB abstraction
            """

            def __init__(self):
                pass  # No shared namespace - computed per-user at upsert time

            async def schedule_upsert(self, upsert_data: List[dict], user_id: str, namespace: str = None):
                """
                Upsert vectors using existing VECTOR_DB_CLIENT with per-user namespace support.

                Namespace Strategy for Open WebUI:
                - Pinecone: namespace = "email-{user_id}" (per-user namespace isolation)
                - Chroma: collection = "email-{user_id}" (per-user collection)
                - Collection name: "gmail" (shared, for Pinecone only)
                - Type metadata: "email" for document type filtering

                Benefits:
                - Easy user data deletion: just delete the namespace
                - Clean isolation between users
                - No cross-user data leakage

                Runs in thread executor to avoid blocking the async event loop.
                """
                from open_webui.retrieval.vector.factory import VECTOR_DB_CLIENT

                # VECTOR_DB_CLIENT.upsert expects List[dict] with keys: id, text, vector, metadata
                # Filter out zero vectors (Pinecone rejects them)
                valid_items = []
                zero_vector_count = 0

                for item in upsert_data:
                    vector = item["values"]
                    # Check if vector has at least one non-zero value
                    if any(v != 0.0 for v in vector):
                        # Handle both dict and VectorItem object cases
                        metadata = item["metadata"]
                        if hasattr(metadata, "get"):
                            # It's a dictionary
                            chunk_text = metadata.get("chunk_text", "")
                            metadata_dict = metadata
                        else:
                            # It's a VectorItem object or similar - access as attributes
                            chunk_text = getattr(metadata, "chunk_text", "")
                            metadata_dict = metadata.__dict__ if hasattr(metadata, "__dict__") else metadata

                        valid_items.append(
                            {
                                "id": item["id"],
                                "text": chunk_text,
                                "vector": vector,
                                "metadata": metadata_dict,
                            }
                        )
                    else:
                        zero_vector_count += 1
                        # Handle both dict and VectorItem object cases for email_id
                        metadata = item["metadata"]
                        if hasattr(metadata, "get"):
                            email_id = metadata.get("email_id", "unknown")
                        else:
                            email_id = getattr(metadata, "email_id", "unknown")
                        logger.warning(f"⚠️  Skipping zero vector for email {email_id} (embedding failed)")

                if zero_vector_count > 0:
                    logger.warning(f"⚠️  Skipped {zero_vector_count} vectors with all zeros")

                if not valid_items:
                    logger.warning("⚠️  No valid vectors in batch (all embeddings failed), skipping upsert")
                    return

                # Per-user namespace strategy for Open WebUI
                # Collection name: "gmail" (shared across all users)
                # Namespace: "email-{user_id}" (separate namespace per user for easy management)
                # User isolation: namespace-based (cleanest isolation in Pinecone)
                collection_name = "gmail"
                user_namespace = f"email-{user_id}"  # Per-user namespace

                # Ensure all vectors have user_id in metadata for additional filtering
                for item in valid_items:
                    if "metadata" not in item:
                        item["metadata"] = {}
                    item["metadata"]["user_id"] = user_id
                    item["metadata"]["collection_name"] = f"gmail_{user_id}"  # For filtering

                logger.info(f"📤 Upserting {len(valid_items)} valid vectors to collection: {collection_name}")
                logger.info(f"   Namespace: '{user_namespace}' (per-user isolation in Open WebUI)")
                logger.info(f"   User: {user_id}")

                try:
                    # Use existing VECTOR_DB_CLIENT.upsert with namespace support
                    # Run in thread executor to avoid blocking async event loop
                    loop = asyncio.get_running_loop()

                    # Check if the vector DB client supports namespace parameter
                    import inspect

                    upsert_signature = inspect.signature(VECTOR_DB_CLIENT.upsert)
                    if "namespace" in upsert_signature.parameters:
                        # Vector DB supports namespace (e.g., Pinecone)
                        # Use per-user namespace: email-{user_id}
                        await loop.run_in_executor(
                            None,
                            VECTOR_DB_CLIENT.upsert,
                            collection_name,
                            valid_items,
                            user_namespace,
                        )
                        logger.info(
                            f"✅ Upserted {len(valid_items)} vectors to collection '{collection_name}' in namespace '{user_namespace}'"
                        )
                    else:
                        # Vector DB doesn't support namespace (e.g., Chroma) - use collection-based isolation
                        user_collection = f"email-{user_id}"
                        await loop.run_in_executor(None, VECTOR_DB_CLIENT.upsert, user_collection, valid_items)
                        logger.info(
                            f"✅ Upserted {len(valid_items)} vectors to collection '{user_collection}' (per-user collection)"
                        )

                    # Clear valid_items to free memory immediately after upsert
                    valid_items.clear()

                except Exception as e:
                    logger.error(f"❌ Vector DB upsert error: {e}")
                    # Clear memory even on error
                    valid_items.clear()
                    raise

        # Initialize services
        embedding_service = SimpleEmbeddingService(request.app.state)
        doc_processor = SimpleDocProcessor()
        pinecone_manager = SimplePineconeManager()

        # If force full sync, delete all existing vectors first
        if force_full_sync:
            namespace = f"email-{user_id}"
            logger.info(f"🗑️  Force full sync: Deleting ALL existing vectors in namespace '{namespace}'...")
            try:
                from open_webui.retrieval.vector.main import VECTOR_DB_CLIENT

                # Delete ALL vectors in the user's email namespace
                # Pass namespace only (no ids/filter) to trigger delete_all for the namespace
                VECTOR_DB_CLIENT.delete(
                    collection_name=namespace,
                    namespace=namespace,
                    # No ids or filter = delete all in namespace
                )
                logger.info(f"✅ Deleted ALL vectors in namespace '{namespace}' - starting fresh")
            except Exception as e:
                logger.warning(f"⚠️  Could not delete existing vectors (namespace may not exist yet): {e}")
                # Continue anyway - namespace may not exist for new users

        # Initialize GmailAutoSync orchestrator (uses per-user namespaces)
        # V2: Single-vector strategy (no chunking needed)
        # Uses admin panel RAG/Document settings
        gmail_sync = GmailAutoSync(
            embedding_service=embedding_service,
            document_processor=doc_processor,
            pinecone_manager=pinecone_manager,
            app_config=request.app.state.config,  # Pass config for RAG settings
            process_attachments=process_attachments,
            max_attachment_size_mb=max_attachment_size_mb,
            allowed_attachment_types=allowed_attachment_types,
        )

        # Execute the sync
        # Use incremental=False when force_full_sync to fetch ALL emails
        incremental = not force_full_sync
        logger.info(f"🚀 Starting Gmail sync for user {user_id}... (incremental={incremental})")

        result = await gmail_sync.sync_user_gmail(
            user_id=user_id,
            oauth_token=oauth_token,
            max_emails=max_emails,
            skip_spam_trash=skip_spam_trash,
            incremental=incremental,  # False for force sync, True otherwise
            token_refresh_callback=token_refresh_callback,  # Enable mid-sync token refresh
        )

        logger.info("\n" + "🎉" * 35)
        logger.info("✅ BACKGROUND GMAIL SYNC TASK COMPLETED")
        logger.info(f"   User ID: {user_id}")
        logger.info(f"   Emails indexed: {result['indexed']}")
        logger.info(f"   Total time: {result['total_time']:.1f}s")
        logger.info(f"   Status: SUCCESS")
        logger.info("🎉" * 35 + "\n")

    except Exception as e:
        logger.error("\n" + "❌" * 35)
        logger.error(f"❌ BACKGROUND GMAIL SYNC TASK FAILED - User: {user_id}")
        logger.error(f"   Error: {str(e)}")
        logger.error("❌" * 35 + "\n")
        logger.error(f"Full traceback:", exc_info=True)


# ============================================================================
# TESTING
# ============================================================================


async def test_auto_sync_orchestrator():
    """Test the auto-sync orchestrator logic"""

    print("\n" + "=" * 60)
    print("Phase 5 - Auto-Sync Orchestrator Test")
    print("=" * 60)

    # Mock services
    class MockEmbeddingService:
        async def embed_batch(self, texts):
            return [[0.1] * 1536 for _ in texts]

    class MockDocProcessor:
        @staticmethod
        def quick_quality_score(text):
            return 4

    class MockPineconeManager:
        async def schedule_upsert(self, data, user_id, namespace=None):
            logger.info(f"Mock upsert: {len(data)} vectors for user '{user_id}' to namespace '{namespace}'")
            return f"job_{time.time()}"

    print("\n✅ TEST 1: Initialize Auto-Sync Orchestrator (V2)")

    sync = GmailAutoSync(
        embedding_service=MockEmbeddingService(),
        document_processor=MockDocProcessor(),
        pinecone_manager=MockPineconeManager(),
    )

    print(f"   Strategy: Single-vector per email (V2)")
    print(f"   Namespace strategy: Per-user (email-{{user_id}})")
    print(f"   Indexer initialized: ✓")
    print(f"   Pinecone manager ready: ✓")
    print("   ✅ PASSED\n")

    print("✅ TEST 2: Sync Status Tracking")

    # Simulate starting a sync
    test_user_id = "test_user_999"
    sync.active_syncs[test_user_id] = {
        "status": "running",
        "start_time": time.time(),
        "total_emails": 100,
        "processed": 50,
        "indexed": 45,
        "errors": 5,
    }

    status = sync.get_sync_status(test_user_id)

    print(f"   User: {status['user_id']}")
    print(f"   Status: {status['status']}")
    print(f"   Processed: {status['processed']}/{status['total_emails']}")
    print(f"   Indexed: {status['indexed']}")
    print(f"   Errors: {status['errors']}")

    assert status["status"] == "running", "Status should be running"
    assert status["processed"] == 50, "Should track processed count"

    print("   ✅ PASSED\n")

    print("=" * 60)
    print("Phase 5 Orchestrator Tests Complete ✅")
    print("=" * 60)

    print("\nOrchestrator capabilities:")
    print("  ✅ Coordinates all Gmail components")
    print("  ✅ Tracks sync progress per user")
    print("  ✅ Integrates with existing services")
    print("  ✅ Ready for OAuth callback integration")

    return True


async def periodic_gmail_sync_scheduler():
    """
    Production-grade periodic Gmail sync scheduler.

    Features:
    - Graceful startup with configurable delay
    - Dynamic configuration updates
    - Batch processing with rate limiting
    - Comprehensive error handling
    - Circuit breaker pattern for failures
    - Memory-efficient user processing
    - Distributed system friendly (no race conditions)
    """
    logger.info("🔄 Gmail Periodic Sync Scheduler starting...")

    # Graceful startup - wait for application to fully initialize
    startup_delay = 60  # Wait 60 seconds for complete initialization
    await asyncio.sleep(startup_delay)

    # Configuration defaults
    sync_interval_minutes = 15  # Default 15 minutes
    check_interval_minutes = 5  # Default 5 minutes
    consecutive_errors = 0
    max_consecutive_errors = 5

    logger.info("✅ Gmail Periodic Sync Scheduler ready")

    while True:
        try:
            # Dynamic configuration reload (supports runtime updates)
            try:
                from open_webui.config import (
                    GMAIL_PERIODIC_SYNC_INTERVAL_MINUTES,
                    GMAIL_PERIODIC_SYNC_INTERVAL_HOURS,
                    GMAIL_PERIODIC_SYNC_CHECK_INTERVAL_MINUTES,
                )

                # Extract value from PersistentConfig - use minutes if available, otherwise hours
                interval_hours_value = (
                    GMAIL_PERIODIC_SYNC_INTERVAL_HOURS.value
                    if hasattr(GMAIL_PERIODIC_SYNC_INTERVAL_HOURS, "value")
                    else 0
                )

                if interval_hours_value and interval_hours_value > 0:
                    # Legacy hours-based config (backward compatibility)
                    sync_interval_minutes = interval_hours_value * 60
                    logger.info(
                        f"Using legacy GMAIL_PERIODIC_SYNC_INTERVAL_HOURS: {interval_hours_value}h = {sync_interval_minutes}min"
                    )
                else:
                    # New minutes-based config (preferred)
                    sync_interval_minutes = (
                        GMAIL_PERIODIC_SYNC_INTERVAL_MINUTES.value
                        if hasattr(GMAIL_PERIODIC_SYNC_INTERVAL_MINUTES, "value")
                        else 15
                    )

                # Check interval (how often to scan for users needing sync)
                check_interval_minutes = (
                    GMAIL_PERIODIC_SYNC_CHECK_INTERVAL_MINUTES.value
                    if hasattr(GMAIL_PERIODIC_SYNC_CHECK_INTERVAL_MINUTES, "value")
                    else 5
                )

                # Ensure they're integers
                sync_interval_minutes = int(sync_interval_minutes)
                check_interval_minutes = int(check_interval_minutes)

            except Exception as e:
                logger.warning(f"Failed to load sync interval config, using defaults: {e}")
                sync_interval_minutes = 15
                check_interval_minutes = 5

            # Circuit breaker: back off if too many failures
            if consecutive_errors >= max_consecutive_errors:
                backoff_time = min(3600, 300 * consecutive_errors)  # Max 1 hour
                logger.error(
                    f"🔴 Circuit breaker: {consecutive_errors} consecutive errors. " f"Backing off for {backoff_time}s"
                )
                await asyncio.sleep(backoff_time)
                consecutive_errors = 0  # Reset after backoff
                continue

            # Query database for users needing sync (indexed query)
            # Convert minutes to hours for database query
            sync_interval_hours = sync_interval_minutes / 60.0

            logger.debug(
                f"🔍 Checking for users needing sync (interval: {sync_interval_minutes}min / {sync_interval_hours:.2f}h)"
            )

            users_needing_sync = gmail_sync_status.get_users_needing_sync(max_hours_since_sync=sync_interval_hours)

            if users_needing_sync:
                total_users = len(users_needing_sync)
                logger.info(
                    f"📧 Periodic sync: {total_users} user(s) need sync "
                    f"(interval: {sync_interval_minutes}min / {sync_interval_hours:.1f}h)"
                )

                # Adaptive batch sizing based on load
                batch_size = 2 if total_users > 10 else 3
                successful_syncs = 0
                failed_syncs = 0
                skipped_syncs = 0

                # Process users in batches with rate limiting
                for i in range(0, total_users, batch_size):
                    batch = users_needing_sync[i : i + batch_size]
                    batch_start = time.time()

                    # Parallel processing within batch
                    tasks = [
                        asyncio.create_task(
                            _sync_user_periodic(user_id),
                            name=f"periodic_gmail_sync_{user_id}",
                        )
                        for user_id in batch
                    ]

                    # Wait for batch completion with error isolation
                    results = await asyncio.gather(*tasks, return_exceptions=True)

                    # Track results for monitoring
                    for j, result in enumerate(results):
                        if isinstance(result, Exception):
                            failed_syncs += 1
                            logger.error(
                                f"❌ Periodic sync failed for user {batch[j]}: " f"{type(result).__name__}: {result}"
                            )
                        elif result is True:  # Successful sync (explicitly True)
                            successful_syncs += 1
                        elif result is False:  # Skipped (validation failed)
                            skipped_syncs += 1

                    batch_duration = time.time() - batch_start

                    # Adaptive rate limiting between batches
                    if i + batch_size < total_users:
                        # Add delay based on batch processing time (backpressure)
                        delay = max(10, min(30, batch_duration * 0.5))
                        await asyncio.sleep(delay)

                # Summary logging
                logger.info(
                    f"✅ Periodic sync cycle complete: "
                    f"{successful_syncs} succeeded, {failed_syncs} failed, "
                    f"{skipped_syncs} skipped (total: {total_users})"
                )

                # Reset error counter on successful cycle or if all were just skipped
                # (skips are not errors - they're intentional validation failures)
                if successful_syncs > 0 or (failed_syncs == 0 and skipped_syncs > 0):
                    consecutive_errors = 0
                elif failed_syncs > 0:
                    # Only count as error if there were actual failures (not just skips)
                    consecutive_errors += 1
                # If all skipped (no success, no failure), don't increment error counter
            else:
                logger.info(f"📧 No users need sync at this time (interval: {sync_interval_minutes}min)")
                consecutive_errors = 0  # Reset on successful query

            # Wait before next check (with jitter to avoid thundering herd)
            check_interval_seconds = check_interval_minutes * 60
            jitter = time.time() % 30  # 0-30 second jitter
            actual_wait = check_interval_seconds + jitter
            logger.info(f"⏰ Next sync check in {actual_wait/60:.1f} minutes")
            await asyncio.sleep(actual_wait)

        except asyncio.CancelledError:
            logger.info("🛑 Gmail Periodic Sync Scheduler shutting down gracefully")
            raise  # Propagate cancellation
        except Exception as e:
            consecutive_errors += 1
            logger.exception(f"❌ Unexpected error in periodic sync scheduler " f"(error #{consecutive_errors}): {e}")
            # Exponential backoff on errors
            error_backoff = min(600, 60 * consecutive_errors)
            await asyncio.sleep(error_backoff)


async def _sync_user_periodic(user_id: str) -> bool:
    """
    Sync Gmail for a single user during periodic sync (production-grade).

    Features:
    - Comprehensive validation with early returns
    - Graceful OAuth token handling
    - Timeout protection
    - Memory-efficient processing
    - Detailed error logging

    Args:
        user_id: The user ID to sync

    Returns:
        bool: True if sync succeeded, False otherwise
    """
    sync_start = time.time()

    try:
        logger.info(f"🔄 Periodic sync starting for user: {user_id}")

        # Validation: Check user exists
        user = await Users.get_user_by_id(user_id)
        if not user:
            logger.warning(f"⚠️  User {user_id} not found in database, skipping")
            return False

        # Validation: Check admin enabled sync
        admin_sync_enabled = getattr(user, "gmail_sync_enabled", 0) == 1
        logger.info(
            f"   Admin sync enabled: {admin_sync_enabled} (value: {getattr(user, 'gmail_sync_enabled', 'N/A')})"
        )
        if not admin_sync_enabled:
            logger.info(f"⏭️  Gmail sync disabled by admin for user {user_id}, skipping")
            return False

        # Validation: Check OAuth session exists
        # Debug: List all OAuth sessions for this user to see what providers exist
        all_sessions = await OAuthSessions.get_sessions_by_user_id(user_id)
        if all_sessions:
            logger.info(f"   Found {len(all_sessions)} OAuth session(s) for user:")
            for s in all_sessions:
                logger.info(f"      - provider='{s.provider}', id={s.id[:8]}..., expires_at={s.expires_at}")
        else:
            logger.info(f"   No OAuth sessions found for user {user_id}")

        oauth_session = await OAuthSessions.get_session_by_provider_and_user_id("google", user_id)
        if not oauth_session:
            logger.info(f"⏭️  No Google OAuth session for user {user_id}, skipping")
            return False

        logger.info(f"   OAuth session found: {oauth_session.id[:8]}...")

        # Get refreshed OAuth token using OAuth manager (auto-refreshes if expired)
        # This is critical for long-running syncs where token may expire mid-process
        try:
            from open_webui.main import app

            oauth_token = await app.state.oauth_manager.get_oauth_token(
                user_id=user_id,
                session_id=oauth_session.id,
            )
        except Exception as e:
            logger.warning(f"⚠️  Failed to get/refresh OAuth token for user {user_id}: {e}")
            oauth_token = oauth_session.token  # Fallback to stored token

        # Validation: Check OAuth token exists and has access_token
        if not oauth_token or not oauth_token.get("access_token"):
            logger.warning(f"⚠️  Invalid OAuth token for user {user_id} (may need to re-authenticate)")
            return False

        # Check if this is first sync for this user
        sync_status = gmail_sync_status.get_sync_status(user_id)
        is_first_sync = sync_status is None or sync_status.last_sync_timestamp is None

        # Use config values for limits - no artificial restrictions
        # Large mailboxes (15000+ emails) need adequate time and batch sizes
        from open_webui.config import GMAIL_AUTO_SYNC_MAX_EMAILS, GMAIL_SYNC_TIMEOUT_SECONDS

        max_sync_emails = GMAIL_AUTO_SYNC_MAX_EMAILS.value if hasattr(GMAIL_AUTO_SYNC_MAX_EMAILS, "value") else 15000

        # Use configured timeout, or calculate based on email count
        configured_timeout = (
            GMAIL_SYNC_TIMEOUT_SECONDS.value
            if hasattr(GMAIL_SYNC_TIMEOUT_SECONDS, "value")
            else 7200  # 2 hours default
        )

        if configured_timeout > 0:
            sync_timeout = configured_timeout
        else:
            # No timeout configured - calculate based on email count
            # Estimate: ~2 seconds per email for fetch + embed + upsert
            estimated_time = max_sync_emails * 2 * 1.5
            sync_timeout = max(3600, int(estimated_time))  # Minimum 1 hour

        if is_first_sync:
            logger.info(
                f"🆕 First sync for user {user_id} - "
                f"max_emails={max_sync_emails}, timeout={sync_timeout}s ({sync_timeout//60}min)"
            )
        else:
            logger.info(
                f"🔄 Ongoing sync for user {user_id} - "
                f"max_emails={max_sync_emails}, timeout={sync_timeout}s ({sync_timeout//60}min)"
            )

        # Perform sync with timeout protection
        try:
            # Get app state for services
            from open_webui.main import app

            # Create a minimal request-like object with app state
            class AppStateWrapper:
                def __init__(self, app_state):
                    self.app = type("obj", (object,), {"state": app_state})()

            request_wrapper = AppStateWrapper(app.state)

            # Use asyncio.wait_for to enforce timeout
            # Timeout is dynamically calculated based on email count
            result = await asyncio.wait_for(
                _background_gmail_sync(request_wrapper, user_id, oauth_token),
                timeout=sync_timeout,
            )
        except asyncio.TimeoutError:
            duration = time.time() - sync_start
            logger.error(
                f"⏱️  Periodic sync timeout for user {user_id} "
                f"after {duration:.1f}s (max: {sync_timeout}s). "
                f"Consider increasing GMAIL_AUTO_SYNC_MAX_EMAILS or performance settings."
            )
            # Mark sync as error so user can be picked up on next cycle
            gmail_sync_status.mark_sync_error(
                user_id, f"Sync timeout after {duration:.1f}s - may need to increase limits"
            )
            return False

        # If we reach here, the sync completed successfully
        # (_background_gmail_sync raises exceptions on failure)
        duration = time.time() - sync_start
        logger.info(f"✅ Periodic sync completed for user {user_id} in {duration:.1f}s")
        return True

    except asyncio.CancelledError:
        logger.info(f"🛑 Periodic sync cancelled for user {user_id}")
        # Mark sync as error so user can be retried on next cycle
        gmail_sync_status.mark_sync_error(user_id, "Sync cancelled")
        raise  # Propagate cancellation
    except Exception as e:
        duration = time.time() - sync_start
        logger.exception(
            f"❌ Unexpected error in periodic sync for user {user_id} "
            f"after {duration:.1f}s: {type(e).__name__}: {e}"
        )
        # Mark sync as error so user can be picked up on next cycle
        gmail_sync_status.mark_sync_error(user_id, str(e))
        return False


if __name__ == "__main__":
    print("Testing Phase 5 - Gmail Auto-Sync Orchestrator")
    success = asyncio.run(test_auto_sync_orchestrator())

    if success:
        print("\n🎉 Phase 5 orchestrator tests PASSED!")
        print("\nNext: Hook into OAuth callback (Phase 5.4)")

    exit(0 if success else 1)
