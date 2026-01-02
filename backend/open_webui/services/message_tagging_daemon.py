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


class MessageTaggingDaemon:
    """Background daemon for automatic message tagging."""

    def __init__(self, app):
        self.app = app
        self.running = False
        self.task = None
        self.instance_id = getattr(app.state, "instance_id", "default")

    async def start(self):
        """Start the daemon loop."""
        self.running = True
        self.task = asyncio.create_task(self._run_loop())
        log.info("[MESSAGE TAGGING DAEMON] Started")

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

        try:
            # Get untagged messages from last N days
            cutoff_time = int(time.time()) - (config.lookback_days * 86400)
            untagged_messages = await self._get_untagged_messages(cutoff_time)

            log.info(f"[MESSAGE TAGGING DAEMON] Found {len(untagged_messages)} untagged messages")

            if not untagged_messages:
                TaggingDaemonConfigs.update_last_run(start_time, "success: no messages to tag")
                return

            # Process in batches
            processed = 0
            for i in range(0, len(untagged_messages), 1):
                if untagged_messages[i].get("role") != "user":
                    continue
                batch = untagged_messages[i:i + config.batch_size]
                success = await self._process_batch(batch, config)
                if success:
                    processed += len(batch)

                # Check tag count and consolidate if needed
                tag_count = MessageTagDefinitions.get_count()
                if tag_count >= config.consolidation_threshold:
                    await self._consolidate_tags(config)

                # Small delay between batches to avoid rate limits
                await asyncio.sleep(2)

            # Update last run status
            TaggingDaemonConfigs.update_last_run(start_time, f"success: tagged {processed} messages")
            log.info(f"[MESSAGE TAGGING DAEMON] Tagging run completed: {processed} messages tagged")

        except Exception as e:
            log.error(f"[MESSAGE TAGGING DAEMON] Tagging run failed: {e}")
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
            prompt = self._build_tagging_prompt(batch, existing_tags, config)

            # Call Gemini
            result = service.query(
                question=prompt,
                store_names=[],
                model="gemini-2.0-flash",
                temperature=0.3,
                system_instruction=self._get_system_instruction(config)
            )

            if result.get("success") and result.get("text"):
                await self._parse_and_save_tags(batch, result["text"])
                return True
            else:
                log.error(f"[MESSAGE TAGGING DAEMON] Gemini query failed: {result.get('error')}")
                return False

        except Exception as e:
            log.error(f"[MESSAGE TAGGING DAEMON] Error processing batch: {e}")
            return False

    def _build_tagging_prompt(self, batch: List[Dict], existing_tags: List[str], config=None) -> str:
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

        # Default prompt
        messages_text = "\n\n".join([
            f"Message {i+1} (ID: {m['message_id']}):\n{m['content'][:500]}"
            for i, m in enumerate(batch)
        ])

        existing_tags_text = ", ".join(existing_tags[:50]) if existing_tags else "None yet"

        return f"""Analyze the following user messages and generate tags and summaries.

EXISTING TAGS (prefer reusing these when appropriate):
{existing_tags_text}

MESSAGES TO TAG:
{messages_text}

For each message, provide:
1. tag: A 1-3 word tag ID (lowercase English, use underscore for spaces, e.g., "laplace_transform")
   - Use null if the message is NOT related to mathematics/engineering topics
   - Use null for greetings, small talk, or off-topic messages
2. tag_display: A human-readable display name (Korean with English in parentheses, e.g., "라플라스 변환 (Laplace Transform)")
   - Use null if tag is null
3. summary: A 50-character Korean summary (can still provide summary even if tag is null)

IMPORTANT:
- Only tag messages that are clearly about math/engineering topics
- Reuse existing tags when the topic matches
- Create new tags only for genuinely new topics
- tag should be lowercase English with underscores
- tag_display should be in Korean with English term in parentheses
- If unsure whether to tag, use null (it's better to skip than create irrelevant tags)

Return as JSON array ONLY (no markdown, no explanation):
[
  {{"message_id": "...", "tag": "laplace_transform", "tag_display": "라플라스 변환 (Laplace Transform)", "summary": "50자 이하 요약..."}},
  {{"message_id": "...", "tag": null, "tag_display": null, "summary": "수학 관련 없는 일반 대화"}}
]"""

    def _get_system_instruction(self, config=None) -> str:
        """Get system instruction for tagging."""
        # Use custom system instruction if configured
        if config and config.custom_system_instruction:
            return config.custom_system_instruction

        return """You are a message tagging assistant for an educational math platform. Your job is to:
1. Analyze user messages and assign appropriate topic tags
2. Generate concise 50-character Korean summaries
3. Prefer reusing existing tags when topics match
4. Only create new tags for genuinely novel topics
5. Return valid JSON array only, no markdown formatting, no code blocks"""

    async def _parse_and_save_tags(self, batch: List[Dict], response_text: str):
        """Parse Gemini response and save tags to database."""
        try:
            # Extract JSON from response
            response_text = response_text.strip()
            if response_text.startswith("```"):
                lines = response_text.split("\n")
                start_idx = 1 if lines[0].startswith("```") else 0
                end_idx = len(lines) - 1 if lines[-1].strip() == "```" else len(lines)
                response_text = "\n".join(lines[start_idx:end_idx])
                if response_text.startswith("json"):
                    response_text = response_text[4:]

            results = json.loads(response_text)

            # Create lookup for batch items
            batch_lookup = {m["message_id"]: m for m in batch}

            # Get blacklist from config
            config = TaggingDaemonConfigs.get_config()
            blacklist = set(config.blacklisted_tags or []) if config else set()

            for result in results:
                msg_id = result.get("message_id")
                raw_tag = result.get("tag")

                # Skip if tag is null (message not related to math/engineering)
                if raw_tag is None:
                    log.debug(f"[MESSAGE TAGGING DAEMON] Skipping message {msg_id} - no relevant topic")
                    continue

                tag_id = str(raw_tag).strip().lower().replace(" ", "_")
                tag_display = result.get("tag_display", tag_id)  # Fallback to tag_id if not provided
                summary = result.get("summary", "")[:100]

                if not msg_id or not tag_id or msg_id not in batch_lookup:
                    continue

                # Skip blacklisted tags
                if tag_id in blacklist:
                    log.debug(f"[MESSAGE TAGGING DAEMON] Skipping blacklisted tag '{tag_id}' for message {msg_id}")
                    continue

                msg = batch_lookup[msg_id]
                chapter_id = msg.get("chapter_id")  # Get chapter_id from message

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

                    log.debug(f"[MESSAGE TAGGING DAEMON] Tagged message {msg_id} with '{tag_id}' ({tag_display})")

        except json.JSONDecodeError as e:
            log.error(f"[MESSAGE TAGGING DAEMON] Failed to parse Gemini response: {e}")
            log.debug(f"[MESSAGE TAGGING DAEMON] Response was: {response_text[:500]}")
        except Exception as e:
            log.error(f"[MESSAGE TAGGING DAEMON] Error saving tags: {e}")

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

    async def run_manual(self):
        """Trigger a manual tagging run."""
        config = TaggingDaemonConfigs.get_config()
        self._release_lock()
        if config and self._acquire_lock(config):
            try:
                await self._execute_tagging_run(config)
            finally:
                self._release_lock()
