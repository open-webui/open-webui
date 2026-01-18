"""
Message Tagging Background Daemon

Automatically tags user messages using AI-generated tags and summaries.
Runs on a configurable schedule (daily/weekly).
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, ValidationError

from open_webui.internal.db import get_db
from open_webui.models.chats import Chat
from open_webui.models.message_tags import (
    MessageTags,
    MessageTagDefinitions,
    TaggingDaemonConfigs,
)
from open_webui.utils.gemini_rag import GeminiRAGService
from open_webui.env import SRC_LOG_LEVELS

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MAIN"])


# ============================================================
# Pydantic Models for Structured Tagging Responses
# ============================================================

class MessageTagResponse(BaseModel):
    """Pydantic model for structured tagging response from Gemini."""
    message_id: str = Field(..., description="Message ID from input")
    tag: Optional[str] = Field(None, description="Tag ID (lowercase with underscores) or null if not math-related")
    tag_display: Optional[str] = Field(None, description="Korean display name with English in parentheses or null")
    summary: str = Field(..., description="50-character Korean summary")
    chapter_id: Optional[str] = Field(None, description="Best matching chapter ID (e.g., 'ch-5') based on content analysis, or null if uncertain")


class BatchTaggingResponse(BaseModel):
    """Container for batch tagging results."""
    results: List[MessageTagResponse]


class MessageTaggingDaemon:
    """Background daemon for automatic message tagging."""

    def __init__(self, app):
        self.app = app
        self.running = False
        self.task = None
        self.instance_id = getattr(app.state, "instance_id", "default")
        # Progress tracking
        self._progress = {
            "is_running": False,
            "status": "idle",  # idle, collecting, processing, consolidating, completed, error
            "started_at": None,
            "total_messages": 0,
            "processed_messages": 0,
            "current_batch": 0,
            "total_batches": 0,
            "last_error": None,
        }

    def get_progress(self) -> dict:
        """Get current daemon progress."""
        return {
            **self._progress,
            "progress_percent": (
                round(self._progress["processed_messages"] / self._progress["total_messages"] * 100, 1)
                if self._progress["total_messages"] > 0 else 0
            )
        }

    def _reset_progress(self):
        """Reset progress tracking."""
        self._progress = {
            "is_running": False,
            "status": "idle",
            "started_at": None,
            "total_messages": 0,
            "processed_messages": 0,
            "current_batch": 0,
            "total_batches": 0,
            "last_error": None,
        }

    async def start(self):
        """Start the daemon loop."""
        self.running = True
        # Clear any stale locks from previous instance (e.g., after server restart)
        self._cleanup_stale_lock()
        self.task = asyncio.create_task(self._run_loop())
        log.info("[MESSAGE TAGGING DAEMON] Started")

    def _cleanup_stale_lock(self):
        """Clear stale locks on startup (e.g., after server restart)."""
        try:
            config = TaggingDaemonConfigs.get_config()
            if config and config.lock_acquired_at:
                now = int(time.time())
                lock_age = now - config.lock_acquired_at
                # Clear lock if it's older than 2 hours (stale from crash/restart)
                if lock_age > 7200:
                    log.warning(f"[MESSAGE TAGGING DAEMON] Clearing stale lock (age: {lock_age}s)")
                    TaggingDaemonConfigs.update_lock(None, None)
        except Exception as e:
            log.error(f"[MESSAGE TAGGING DAEMON] Error cleaning up stale lock: {e}")

    async def stop(self):
        """Stop the daemon."""
        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        log.info("[MESSAGE TAGGING DAEMON] Stopped")

    async def _run_loop(self):
        """Main daemon loop - check schedule and run if needed."""
        # Initial delay to let the app start
        await asyncio.sleep(60)

        while self.running:
            try:
                config = TaggingDaemonConfigs.get_config()

                if config and config.enabled:
                    if self._should_run(config):
                        if self._acquire_lock(config):
                            try:
                                await self._execute_tagging_run(config)
                            finally:
                                self._release_lock()

                # Sleep for 1 hour between checks
                await asyncio.sleep(3600)

            except asyncio.CancelledError:
                break
            except Exception as e:
                log.error(f"[MESSAGE TAGGING DAEMON] Error in run loop: {e}")
                await asyncio.sleep(3600)  # Continue after error

    def _should_run(self, config) -> bool:
        """Check if daemon should run based on schedule."""
        now = datetime.utcnow()

        # Parse configured run time
        try:
            run_hour, run_minute = map(int, config.run_time.split(":"))
        except Exception:
            run_hour, run_minute = 3, 0  # Default to 03:00

        # Check if we're within the run window (within 1 hour of scheduled time)
        if abs(now.hour - run_hour) > 1:
            return False

        # Check last run time
        if config.last_run_at:
            last_run = datetime.fromtimestamp(config.last_run_at)

            if config.schedule == "daily":
                # Run if last run was more than 20 hours ago
                if (now - last_run) < timedelta(hours=20):
                    return False
            elif config.schedule == "weekly":
                # Run if last run was more than 6 days ago
                if (now - last_run) < timedelta(days=6):
                    return False

        return True

    def _acquire_lock(self, config) -> bool:
        """Acquire distributed lock to prevent concurrent runs."""
        now = int(time.time())

        # Check if lock is stale (older than 2 hours)
        if config.lock_acquired_at:
            if (now - config.lock_acquired_at) < 7200:  # 2 hours
                if config.lock_instance_id != self.instance_id:
                    log.debug("[MESSAGE TAGGING DAEMON] Lock held by another instance")
                    return False

        # Acquire lock
        TaggingDaemonConfigs.update_lock(self.instance_id, now)
        log.debug("[MESSAGE TAGGING DAEMON] Lock acquired")
        return True

    def _release_lock(self):
        """Release the distributed lock."""
        TaggingDaemonConfigs.update_lock(None, None)

    async def _execute_tagging_run(self, config):
        """Execute a tagging run."""
        log.info("[MESSAGE TAGGING DAEMON] Starting tagging run")
        start_time = int(time.time())

        # Initialize progress
        self._progress["is_running"] = True
        self._progress["status"] = "collecting"
        self._progress["started_at"] = start_time
        self._progress["last_error"] = None

        try:
            # Get untagged messages from last N days
            cutoff_time = int(time.time()) - (config.lookback_days * 86400)
            untagged_messages = await self._get_untagged_messages(cutoff_time)

            log.info(f"[MESSAGE TAGGING DAEMON] Found {len(untagged_messages)} untagged messages")

            # Filter to only user messages
            user_messages = [m for m in untagged_messages if m.get("role") == "user"]

            if not user_messages:
                self._progress["status"] = "completed"
                self._progress["is_running"] = False
                TaggingDaemonConfigs.update_last_run(start_time, "success: no messages to tag")
                return

            # Update progress with totals
            self._progress["total_messages"] = len(user_messages)
            self._progress["total_batches"] = (len(user_messages) + config.batch_size - 1) // config.batch_size
            self._progress["status"] = "processing"

            # Process in batches
            processed = 0
            batch_num = 0
            for i in range(0, len(user_messages), config.batch_size):
                batch = user_messages[i:i + config.batch_size]
                batch_num += 1

                # Update progress
                self._progress["current_batch"] = batch_num
                self._progress["processed_messages"] = processed

                success = await self._process_batch(batch, config)
                if success:
                    processed += len(batch)

                # Check tag count and consolidate if needed
                tag_count = MessageTagDefinitions.get_count()
                if tag_count >= config.consolidation_threshold:
                    self._progress["status"] = "consolidating"
                    await self._consolidate_tags(config)
                    self._progress["status"] = "processing"

                # Small delay between batches to avoid rate limits
                await asyncio.sleep(2)

            # Update final progress
            self._progress["processed_messages"] = processed
            self._progress["status"] = "completed"
            self._progress["is_running"] = False

            # Update last run status
            TaggingDaemonConfigs.update_last_run(start_time, f"success: tagged {processed} messages")
            log.info(f"[MESSAGE TAGGING DAEMON] Tagging run completed: {processed} messages tagged")

        except Exception as e:
            log.error(f"[MESSAGE TAGGING DAEMON] Tagging run failed: {e}")
            self._progress["status"] = "error"
            self._progress["last_error"] = str(e)[:200]
            self._progress["is_running"] = False
            TaggingDaemonConfigs.update_last_run(start_time, f"error: {str(e)[:100]}")

    async def _get_untagged_messages(self, cutoff_time: int) -> List[Dict]:
        """Get messages that don't have tags yet."""
        untagged = []

        with get_db() as db:
            # Get chats updated after cutoff time
            chats = db.query(Chat).filter(
                Chat.updated_at >= cutoff_time
            ).all()

            for chat in chats:
                if not chat.chat:
                    continue

                messages = chat.chat.get("history", {}).get("messages", {})

                for msg_id, msg in messages.items():
                    # Only tag user messages
                    # if msg.get("role") != "user":
                    #     continue

                    # Skip empty messages
                    content = msg.get("content", "")
                    if not content or len(content.strip()) < 5:
                        continue

                    # Check if already tagged
                    if not MessageTags.has_tags(chat.id, msg_id):
                        untagged.append({
                            "chat_id": chat.id,
                            "message_id": msg_id,
                            "content": content,
                            "user_id": chat.user_id,
                            "chapter_id": chat.chapter_id,  # Include chapter_id from chat
                            "role": msg.get("role", "user")
                        })

        return untagged

    async def _process_batch(self, batch: List[Dict], config) -> bool:
        """Process a batch of messages through Gemini for tagging."""
        if not batch:
            return True

        # Get API key from app config
        api_key = self._get_gemini_api_key()
        if not api_key:
            log.error("[MESSAGE TAGGING DAEMON] No Gemini API key configured")
            return False

        try:
            service = GeminiRAGService(api_key)

            # Prepare batch prompt
            existing_tags = MessageTagDefinitions.get_all_tag_names()

            # Get chapter-store mappings for RAG-based chapter detection
            chapter_mappings = None
            store_names = []

            if config.enable_rag_chapter_detection:
                # Get all chapter-store mappings
                from open_webui.models.textbooks import TextbookChapters
                chapter_mappings = TextbookChapters.get_all_rag_store_mappings()

                if chapter_mappings:
                    # Smart selection: Use keyword-based matching to select top 5 relevant stores
                    # This respects Gemini's 5-store limit while maximizing accuracy
                    store_names = self._select_relevant_stores(batch, chapter_mappings, max_stores=5)
                    if store_names:
                        log.info(f"[TAGGING] Using {len(store_names)} smart-selected chapter stores for RAG-based chapter detection")
                    else:
                        log.warning("[TAGGING] No relevant stores selected, falling back to configured stores")
                        store_names = config.rag_store_names or []
                else:
                    log.warning("[TAGGING] RAG chapter detection enabled but no chapter stores found")
            else:
                # Fallback: Use configured stores only (current behavior)
                store_names = config.rag_store_names or []

            # Build prompt with chapter context (includes valid chapter list)
            prompt = self._build_tagging_prompt(batch, existing_tags, config, chapter_mappings)

            # Use gemini-2.5-flash when using RAG stores or Pydantic schema (FileSearch + Pydantic require 2.5+)
            # Otherwise use gemini-2.0-flash for faster processing
            model = "gemini-2.5-flash" if (store_names or config.enable_rag_chapter_detection) else "gemini-2.0-flash"

            # Determine if we should use Pydantic response schema
            # Use it when RAG chapter detection is enabled for structured output
            response_schema = BatchTaggingResponse if config.enable_rag_chapter_detection else None

            # Call Gemini with optional Pydantic response schema
            result = service.query(
                question=prompt,
                store_names=store_names,
                model=model,
                temperature=0.3,
                system_instruction=self._get_system_instruction(config),
                response_schema=response_schema  # Pydantic model for structured output
            )

            if result.get("success") and result.get("text"):
                await self._parse_and_save_tags(batch, result["text"], use_pydantic=bool(response_schema))
                return True
            else:
                log.error(f"[MESSAGE TAGGING DAEMON] Gemini query failed: {result.get('error')}")
                return False

        except Exception as e:
            log.error(f"[MESSAGE TAGGING DAEMON] Error processing batch: {e}")
            return False

    def _build_tagging_prompt(self, batch: List[Dict], existing_tags: List[str], config=None, chapter_mappings: Optional[Dict] = None) -> str:
        """Build the prompt for Gemini tagging."""
        # Use custom prompt if configured
        if config and config.custom_tagging_prompt:
            messages_text = "\n\n".join([
                f"Message {i+1} (ID: {m['message_id']}):\n{m['content'][:500]}"
                for i, m in enumerate(batch)
            ])
            existing_tags_text = ", ".join(existing_tags[:50]) if existing_tags else "None yet"

            # Replace placeholders in custom prompt
            custom_prompt = config.custom_tagging_prompt
            custom_prompt = custom_prompt.replace("{existing_tags}", existing_tags_text)
            custom_prompt = custom_prompt.replace("{messages}", messages_text)
            return custom_prompt

        # Build chapter context if available
        chapter_context = ""
        if chapter_mappings and config and config.enable_rag_chapter_detection:
            # Get list of valid chapters with their display names
            from open_webui.models.textbooks import TextbookChapters
            all_chapters = TextbookChapters.get_all()
            chapter_list = "\n".join([
                f"  - {ch.id}: {ch.title}"
                for ch in sorted(all_chapters, key=lambda x: x.order)
            ])
            chapter_context = f"""
AVAILABLE CHAPTERS (analyze message content and assign the best matching chapter):
{chapter_list}

"""

        # Default prompt
        messages_text = "\n\n".join([
            f"Message {i+1} (ID: {m['message_id']}):\n{m['content'][:500]}"
            for i, m in enumerate(batch)
        ])

        existing_tags_text = ", ".join(existing_tags[:50]) if existing_tags else "None yet"

        return f"""Analyze the following user messages and generate tags and summaries.

EXISTING TAGS (prefer reusing these when appropriate):
{existing_tags_text}

{chapter_context}MESSAGES TO TAG:
{messages_text}

For each message, provide:
1. tag: A 1-3 word tag ID (lowercase English, use underscore for spaces, e.g., "laplace_transform")
   - Use null if the message is NOT related to mathematics/engineering topics
   - Use null for greetings, small talk, or off-topic messages
2. tag_display: A human-readable display name (Korean with English in parentheses, e.g., "라플라스 변환 (Laplace Transform)")
   - Use null if tag is null
3. summary: A 50-character Korean summary (can still provide summary even if tag is null)
4. chapter_id: The best matching chapter ID based on content analysis (e.g., "ch-5")
   - Use null if uncertain or if message is not math-related
   - Analyze the message content and RAG context to determine the most appropriate chapter

IMPORTANT:
- Only tag messages that are clearly about math/engineering topics
- Reuse existing tags when the topic matches
- Create new tags only for genuinely new topics
- tag should be lowercase English with underscores
- tag_display should be in Korean with English term in parentheses
- chapter_id should match one of the available chapters listed above
- If unsure whether to tag, use null (it's better to skip than create irrelevant tags)

Return as JSON array ONLY (no markdown, no explanation):
[
  {{"message_id": "...", "tag": "laplace_transform", "tag_display": "라플라스 변환 (Laplace Transform)", "summary": "50자 이하 요약...", "chapter_id": "ch-6"}},
  {{"message_id": "...", "tag": null, "tag_display": null, "summary": "수학 관련 없는 일반 대화", "chapter_id": null}}
]"""

    def _get_system_instruction(self, config=None) -> str:
        """Get system instruction for tagging."""
        # Use custom system instruction if configured
        if config and config.custom_system_instruction:
            return config.custom_system_instruction

        # Enhanced instruction when RAG chapter detection is enabled
        if config and config.enable_rag_chapter_detection:
            return """You are a message tagging assistant for an educational math platform. Your job is to:
1. Analyze user messages and assign appropriate topic tags
2. Determine the best matching textbook chapter based on content (use RAG context from retrieved documents)
3. Generate concise 50-character Korean summaries
4. Prefer reusing existing tags when topics match
5. Only create new tags for genuinely novel topics
6. Return valid JSON matching the provided schema (when using structured output)

When determining chapter_id:
- Analyze the message content and retrieved document context
- Match the topic to the most relevant textbook chapter
- Use null if uncertain or if the message is not math-related"""

        # Default instruction (backward compatible)
        return """You are a message tagging assistant for an educational math platform. Your job is to:
1. Analyze user messages and assign appropriate topic tags
2. Generate concise 50-character Korean summaries
3. Prefer reusing existing tags when topics match
4. Only create new tags for genuinely novel topics
5. Return valid JSON array only, no markdown formatting, no code blocks"""

    async def _parse_and_save_tags(self, batch: List[Dict], response_text: str, use_pydantic: bool = False):
        """Parse Gemini response and save tags to database."""
        # Create lookup for batch items
        batch_lookup = {m["message_id"]: m for m in batch}

        # Get blacklist from config
        config = TaggingDaemonConfigs.get_config()
        blacklist = set(config.blacklisted_tags or []) if config else set()

        try:
            # Parse response based on format (Pydantic or plain JSON)
            if use_pydantic:
                # Parse Pydantic-structured response
                try:
                    response_text = response_text.strip()
                    batch_response = BatchTaggingResponse.model_validate_json(response_text)
                    results = [tag_resp.model_dump() for tag_resp in batch_response.results]
                    log.info("[TAGGING] Successfully parsed Pydantic response")
                except ValidationError as e:
                    log.error(f"[TAGGING] Pydantic validation failed: {e}")
                    log.warning("[TAGGING] Falling back to plain JSON parsing")
                    # Fall through to plain JSON parsing
                    use_pydantic = False

            if not use_pydantic:
                # Extract JSON from response (legacy format)
                response_text = response_text.strip()
                if response_text.startswith("```"):
                    lines = response_text.split("\n")
                    start_idx = 1 if lines[0].startswith("```") else 0
                    end_idx = len(lines) - 1 if lines[-1].strip() == "```" else len(lines)
                    response_text = "\n".join(lines[start_idx:end_idx])
                    if response_text.startswith("json"):
                        response_text = response_text[4:]

                results = json.loads(response_text)

            # Process each result
            for result in results:
                msg_id = result.get("message_id")
                raw_tag = result.get("tag")

                # Skip if tag is null (message not related to math/engineering)
                if raw_tag is None:
                    log.debug(f"[TAGGING] Skipping message {msg_id} - no relevant topic")
                    continue

                tag_id = str(raw_tag).strip().lower().replace(" ", "_")
                tag_display = result.get("tag_display", tag_id)  # Fallback to tag_id if not provided
                summary = result.get("summary", "")[:100]

                if not msg_id or not tag_id or msg_id not in batch_lookup:
                    continue

                # Skip blacklisted tags
                if tag_id in blacklist:
                    log.debug(f"[TAGGING] Skipping blacklisted tag '{tag_id}' for message {msg_id}")
                    continue

                msg = batch_lookup[msg_id]

                # Determine chapter_id: RAG-determined (validated) or fallback to chat's chapter_id
                rag_chapter_id = result.get("chapter_id")  # From Gemini response
                if rag_chapter_id:
                    # Validate RAG-determined chapter_id (user preference: validate against valid chapters)
                    validated_chapter_id = self._validate_chapter_id(rag_chapter_id)
                    if validated_chapter_id:
                        chapter_id = validated_chapter_id
                        log.info(f"[TAGGING] Using RAG-determined chapter_id '{chapter_id}' for message {msg_id}")
                    else:
                        # Validation failed, fall back to chat's chapter_id
                        chapter_id = msg.get("chapter_id")
                        log.info(f"[TAGGING] Rejected invalid chapter_id '{rag_chapter_id}', using fallback '{chapter_id}' for message {msg_id}")
                else:
                    # No RAG chapter_id, use chat's chapter_id (backward compatible)
                    chapter_id = msg.get("chapter_id")

                # Get or create tag definition
                tag_def = MessageTagDefinitions.get_by_id(tag_id)
                if not tag_def:
                    # Create with explicit tag_id, display name, and chapter_id
                    tag_def = MessageTagDefinitions.create(
                        name=tag_display,
                        tag_id=tag_id,
                        chapter_id=chapter_id
                    )
                elif chapter_id and tag_def.chapter_id is None:
                    # Update existing tag's chapter_id if it was null
                    MessageTagDefinitions.update_chapter_id(tag_id, chapter_id)

                if tag_def:
                    # Create message tag
                    MessageTags.create(
                        chat_id=msg["chat_id"],
                        message_id=msg_id,
                        tag_id=tag_id,
                        summary=summary,
                        user_id=msg["user_id"]
                    )

                    # Increment usage count
                    MessageTagDefinitions.increment_usage(tag_id)

                    log.debug(f"[TAGGING] Tagged message {msg_id} with '{tag_id}' ({tag_display}) in chapter '{chapter_id}'")

        except json.JSONDecodeError as e:
            log.error(f"[TAGGING] Failed to parse Gemini response: {e}")
            log.debug(f"[TAGGING] Response was: {response_text[:500]}")
        except Exception as e:
            log.error(f"[TAGGING] Error saving tags: {e}")

    async def _consolidate_tags(self, config):
        """Consolidate tags when approaching the limit."""
        log.info("[MESSAGE TAGGING DAEMON] Starting tag consolidation")

        # Get all tags with usage counts
        all_tags = MessageTagDefinitions.get_all_with_usage()

        if len(all_tags) <= config.max_tags - 20:
            return  # No need to consolidate yet

        # Get AI-based similarity analysis
        api_key = self._get_gemini_api_key()
        if not api_key:
            return

        try:
            service = GeminiRAGService(api_key)

            # Filter out protected tags - they should not be merged or deleted
            unprotected_tags = [t for t in all_tags if not t.is_protected]
            protected_tags = [t for t in all_tags if t.is_protected]

            # Sort by usage (consolidate less-used tags first)
            tag_names = [t.name for t in sorted(unprotected_tags, key=lambda x: x.usage_count)]
            protected_tag_names = [t.name for t in protected_tags]

            prompt = f"""Analyze these tags and suggest merges for similar ones.
The goal is to reduce from {len(tag_names)} tags to approximately {config.max_tags - 20 - len(protected_tags)} tags.

TAGS THAT CAN BE MERGED:
{', '.join(tag_names)}

PROTECTED TAGS (DO NOT merge these, but can merge INTO them):
{', '.join(protected_tag_names) if protected_tag_names else 'None'}

Return a JSON array of merge suggestions:
[
  {{"keep": "primary_tag_id", "merge": ["similar_tag_id1", "similar_tag_id2"]}}
]

IMPORTANT:
- Only suggest merges where tags are clearly similar or overlapping
- Use the tag IDs (lowercase with underscores) not display names
- Protected tags can be the "keep" target, but NEVER in the "merge" list"""

            result = service.query(
                question=prompt,
                store_names=[],
                model="gemini-2.0-flash",
                temperature=0.2,
                system_instruction="You are a tag consolidation assistant. Analyze tags and suggest merges for similar ones. Return valid JSON only."
            )

            if result.get("success") and result.get("text"):
                await self._apply_tag_merges(result["text"])

        except Exception as e:
            log.error(f"[MESSAGE TAGGING DAEMON] Error in tag consolidation: {e}")

    async def _apply_tag_merges(self, response_text: str):
        """Apply tag merge suggestions."""
        try:
            response_text = response_text.strip()
            if response_text.startswith("```"):
                lines = response_text.split("\n")
                start_idx = 1 if lines[0].startswith("```") else 0
                end_idx = len(lines) - 1 if lines[-1].strip() == "```" else len(lines)
                response_text = "\n".join(lines[start_idx:end_idx])
                if response_text.startswith("json"):
                    response_text = response_text[4:]

            merges = json.loads(response_text)

            for merge in merges:
                keep_tag = merge.get("keep")
                merge_tags = merge.get("merge", [])

                if not keep_tag or not merge_tags:
                    continue

                # Update all message_tags to use the kept tag
                for old_tag in merge_tags:
                    # Double-check: skip protected tags even if AI suggested them
                    tag_def = MessageTagDefinitions.get_by_id(old_tag)
                    if tag_def and tag_def.is_protected:
                        log.warning(f"[MESSAGE TAGGING DAEMON] Skipping protected tag: {old_tag}")
                        continue

                    MessageTags.update_tag_id(old_tag, keep_tag)
                    MessageTagDefinitions.delete(old_tag)

                log.info(f"[MESSAGE TAGGING DAEMON] Merged {merge_tags} into {keep_tag}")

        except Exception as e:
            log.error(f"[MESSAGE TAGGING DAEMON] Error applying tag merges: {e}")

    def _get_gemini_api_key(self) -> Optional[str]:
        """Get Gemini API key from app config."""
        try:
            base_urls = self.app.state.config.OPENAI_API_BASE_URLS
            api_keys = self.app.state.config.OPENAI_API_KEYS

            for idx, url in enumerate(base_urls):
                if "generativelanguage.googleapis.com" in url:
                    if idx < len(api_keys) and api_keys[idx]:
                        return api_keys[idx]
            return None
        except Exception:
            return None

    def _validate_chapter_id(self, chapter_id: Optional[str]) -> Optional[str]:
        """
        Validate chapter_id against valid textbook chapters.

        Args:
            chapter_id: Chapter ID to validate (e.g., "ch-5")

        Returns:
            Valid chapter_id or None if invalid
        """
        if not chapter_id:
            return None

        try:
            from open_webui.models.textbooks import TextbookChapters
            valid_chapters = TextbookChapters.get_valid_chapter_ids()

            if chapter_id in valid_chapters:
                return chapter_id
            else:
                log.warning(f"[TAGGING] Invalid chapter_id '{chapter_id}' returned by Gemini, rejecting")
                return None
        except Exception as e:
            log.error(f"[TAGGING] Error validating chapter_id: {e}")
            return None

    def _select_relevant_stores(self, batch: List[Dict], chapter_mappings: dict, max_stores: int = 5) -> List[str]:
        """
        Select relevant RAG stores based on message content keywords.

        Args:
            batch: List of messages to analyze
            chapter_mappings: Dictionary mapping chapter_id to store info
            max_stores: Maximum number of stores to return (Gemini limit is 5)

        Returns:
            List of store names (up to max_stores)
        """
        # Keyword-to-chapter mapping (Korean and English)
        keyword_to_chapters = {
            # Part A: ODEs
            "laplace": ["ch-6"],
            "라플라스": ["ch-6"],
            "differential": ["ch-1", "ch-2", "ch-3"],
            "미분방정식": ["ch-1", "ch-2", "ch-3"],
            "ode": ["ch-1", "ch-2", "ch-3", "ch-4"],
            "상미분": ["ch-1", "ch-2", "ch-3", "ch-4"],
            "bessel": ["ch-5"],
            "베셀": ["ch-5"],
            "legendre": ["ch-5"],
            "르장드르": ["ch-5"],
            "series": ["ch-5"],
            "급수": ["ch-5"],

            # Part B: Linear Algebra
            "matrix": ["ch-7", "ch-8"],
            "행렬": ["ch-7", "ch-8"],
            "eigenvalue": ["ch-8"],
            "고유값": ["ch-8"],
            "eigenvector": ["ch-8"],
            "고유벡터": ["ch-8"],
            "determinant": ["ch-7"],
            "행렬식": ["ch-7"],
            "vector": ["ch-7", "ch-9", "ch-10"],
            "벡터": ["ch-7", "ch-9", "ch-10"],
            "gradient": ["ch-9"],
            "그래디언트": ["ch-9"],
            "divergence": ["ch-9"],
            "발산": ["ch-9"],
            "curl": ["ch-9"],
            "회전": ["ch-9"],
            "green": ["ch-10"],
            "그린": ["ch-10"],
            "stokes": ["ch-10"],
            "스토크스": ["ch-10"],

            # Part C: Fourier, PDEs
            "fourier": ["ch-11"],
            "푸리에": ["ch-11"],
            "pde": ["ch-12"],
            "편미분": ["ch-12"],
            "heat": ["ch-12"],
            "열방정식": ["ch-12"],
            "wave": ["ch-12"],
            "파동": ["ch-12"],

            # Part D: Complex Analysis
            "complex": ["ch-13", "ch-14", "ch-15", "ch-16"],
            "복소": ["ch-13", "ch-14", "ch-15", "ch-16"],
            "analytic": ["ch-13"],
            "해석함수": ["ch-13"],
            "cauchy": ["ch-14"],
            "코시": ["ch-14"],
            "residue": ["ch-16"],
            "유수": ["ch-16"],
            "laurent": ["ch-16"],
            "로랑": ["ch-16"],
            "taylor": ["ch-15"],
            "테일러": ["ch-15"],
            "conformal": ["ch-17"],
            "등각": ["ch-17"],

            # Part E: Numerical Analysis
            "numerical": ["ch-19", "ch-20", "ch-21"],
            "수치": ["ch-19", "ch-20", "ch-21"],
            "newton": ["ch-19"],
            "뉴턴": ["ch-19"],
            "gaussian": ["ch-20"],
            "가우스": ["ch-20"],
            "elimination": ["ch-20"],
            "소거": ["ch-20"],
            "euler": ["ch-21"],
            "오일러": ["ch-21"],
            "runge": ["ch-21"],
            "룽게": ["ch-21"],

            # Part F: Optimization
            "optimization": ["ch-22", "ch-23"],
            "최적화": ["ch-22", "ch-23"],
            "linear programming": ["ch-22"],
            "선형계획": ["ch-22"],
            "simplex": ["ch-22"],
            "심플렉스": ["ch-22"],
            "graph": ["ch-23"],
            "그래프": ["ch-23"],

            # Part G: Probability, Statistics
            "probability": ["ch-24", "ch-25"],
            "확률": ["ch-24", "ch-25"],
            "statistics": ["ch-25"],
            "통계": ["ch-25"],
            "bayes": ["ch-24"],
            "베이즈": ["ch-24"],
            "normal": ["ch-24"],
            "정규분포": ["ch-24"],
        }

        # Combine all messages in batch
        combined_content = " ".join([msg.get("content", "").lower() for msg in batch])

        # Find matching chapters based on keywords
        chapter_scores = {}
        for keyword, chapters in keyword_to_chapters.items():
            if keyword.lower() in combined_content:
                for chapter_id in chapters:
                    chapter_scores[chapter_id] = chapter_scores.get(chapter_id, 0) + 1

        # If no keywords matched, return empty list (will use default behavior)
        if not chapter_scores:
            log.info("[TAGGING] No keyword matches found, using fallback chapter selection")
            # Use configured stores or first 5 chapters as fallback
            all_chapter_ids = sorted(chapter_mappings.keys())[:max_stores]
            return [chapter_mappings[ch_id]["store_name"] for ch_id in all_chapter_ids if ch_id in chapter_mappings]

        # Sort chapters by score (most relevant first) and take top max_stores
        top_chapters = sorted(chapter_scores.items(), key=lambda x: x[1], reverse=True)[:max_stores]
        top_chapter_ids = [ch_id for ch_id, _ in top_chapters]

        # Get store names for top chapters
        store_names = []
        for ch_id in top_chapter_ids:
            if ch_id in chapter_mappings:
                store_names.append(chapter_mappings[ch_id]["store_name"])

        log.info(f"[TAGGING] Selected {len(store_names)} relevant stores based on keywords: {top_chapter_ids}")
        return store_names

    async def run_manual(self):
        """Trigger a manual tagging run."""
        config = TaggingDaemonConfigs.get_config()
        
        if config and self._acquire_lock(config):
            try:
                await self._execute_tagging_run(config)
            finally:
                self._release_lock()
