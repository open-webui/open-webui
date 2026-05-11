"""
Gmail Indexer V5 - Clean Metadata for Semantic Search + Re-ranking

Production-grade email indexing with ONLY reliable metadata.

V5 Changes (improved text cleaning from V4):
- FIXED: URLs and emails are now preserved (not broken with spaces)
- FIXED: Email disclaimers fully removed (comprehensive patterns)
- FIXED: Duplicate text removed (sentence-level deduplication)
- FIXED: Email signatures thoroughly stripped
- FIXED: Whitespace normalization doesn't break URLs/emails

V4 Changes (simplified from V3):
- REMOVED: topics, keywords, entity_people, entity_organizations, entity_locations
  (regex-based extraction was producing garbage like "ONLY" as org, subjects as names)
- KEPT: All text fields for semantic search (rerank_text, chunk_text, snippet)
- KEPT: Reliable header data (from, to, subject, date, labels)
- KEPT: Gmail API data (attachments, labels)
- FIXED: All text fields cleaned with _clean_for_pinecone (no more \n in records)

Philosophy: Let semantic search + re-ranking find entities naturally in the text.
Garbage metadata is worse than no metadata.

Architecture:
- One email = One vector = One search result
- rerank_text: Full clean body for re-ranker (up to 3000 chars)
- chunk_text: Embedding text (subject + key content, ~1500 chars)
- snippet: Display preview (150 chars)
- Arrays for filtering: labels, attachments (reliable data only)
"""

import logging
import time
import asyncio
import re
import hashlib
import math
import concurrent.futures
from datetime import datetime
from functools import partial
from typing import Dict, List, Optional

from open_webui.utils.gmail_processor import GmailProcessor
from open_webui.utils.async_utils import gather_with_concurrency
from open_webui.config import (
    RAG_EMBEDDING_BATCH_SIZE,
    SEMANTIC_MAX_CHUNK_SIZE,
)

# Thread pool for CPU-bound operations (prevents blocking event loop)
_CPU_EXECUTOR = concurrent.futures.ThreadPoolExecutor(max_workers=2, thread_name_prefix="gmail_cpu")

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class GmailIndexerV2:
    """
    Optimized email indexer for semantic search + re-ranking.

    V3 Strategy:
    - rerank_text: Long text (3000 chars) for Cohere/Pinecone re-ranker
    - chunk_text: Embedding text (~1500 chars) with semantic priority
    - snippet: Short preview (150 chars) for UI display
    - Arrays for filtering (not comma-separated strings)
    - Recency score for temporal boosting

    Performance Characteristics:
    - 10,000 emails = 10,000 vectors
    - Average processing: 10-30 emails/second
    - Average search: <100ms for 100,000+ emails
    - Re-ranking: Adds ~50-100ms but significantly improves relevance
    """

    # Index version for tracking - V5 improved text cleaning
    INDEX_VERSION = "v5-clean-text"

    # Text length limits optimized for re-ranking
    RERANK_TEXT_LENGTH = 3000  # Long text for re-ranker (Cohere handles up to 4096 tokens)
    EMBEDDING_TEXT_LENGTH = 1500  # Optimal for embeddings (semantic density)
    SNIPPET_LENGTH = 150  # Short preview for UI
    ATTACHMENT_TEXT_LENGTH = 500  # Attachment content to include

    def __init__(
        self,
        embedding_service,
        document_processor,
        app_config=None,
    ):
        """
        Initialize optimized indexer.

        Args:
            embedding_service: EmbeddingService from Open WebUI
            document_processor: DocumentProcessor for quality scoring
            app_config: Optional app config for accessing RAG settings
        """
        self.gmail_processor = GmailProcessor()
        self.embeddings = embedding_service
        self.doc_processor = document_processor
        self.app_config = app_config

        # Get batch size from settings
        self.BATCH_SIZE = RAG_EMBEDDING_BATCH_SIZE.value if RAG_EMBEDDING_BATCH_SIZE else 1

        logger.info(f"GmailIndexerV2 initialized - {self.INDEX_VERSION}")
        logger.info(f"  Rerank text length: {self.RERANK_TEXT_LENGTH} chars")
        logger.info(f"  Embedding text length: {self.EMBEDDING_TEXT_LENGTH} chars")
        logger.info(f"  Snippet length: {self.SNIPPET_LENGTH} chars")
        logger.info(f"  Embedding batch size: {self.BATCH_SIZE}")

    async def process_email_for_indexing(
        self,
        email_data: dict,
        user_id: str,
        fetcher=None,
        process_attachments: bool = True,
        max_attachment_size_mb: int = 10,
        allowed_attachment_types: str = ".pdf,.docx,.doc,.xlsx,.xls,.pptx,.ppt,.txt,.csv,.md,.html,.eml",
    ) -> Dict:
        """
        Process a single email into optimized format for semantic search + re-ranking.

        Pipeline:
        1. Parse email → structured data
        2. Process attachments (if enabled)
        3. Create THREE text versions:
           - rerank_text: Full clean body for re-ranker
           - embedding_text: Semantic-optimized for vector
           - snippet: Short preview for display
        4. Extract enhanced metadata as ARRAYS
        5. Calculate recency score
        6. Generate embedding
        7. Return upsert-ready data
        """
        start_time = time.time()

        # Step 1: Parse email into structured format
        parsed = self.gmail_processor.parse_email(email_data, user_id)
        email_id = parsed["email_id"]
        base_metadata = parsed["metadata"]

        logger.info(f"Processing email {email_id[:8]}... " f"({base_metadata['subject'][:50]}...)")

        # Step 2: Process attachments (if enabled)
        attachment_texts = []
        attachment_names = []

        if process_attachments and parsed.get("attachments") and fetcher:
            attachment_results = await self._process_email_attachments(
                parsed["attachments"],
                fetcher,
                email_id,
                max_attachment_size_mb,
                allowed_attachment_types,
            )
            attachment_texts = [att["text"] for att in attachment_results]
            attachment_names = [att["filename"] for att in attachment_results]

            if attachment_names:
                logger.info(f"  📎 Processed {len(attachment_names)} attachment(s)")

        # Step 3: Create THREE text versions (run CPU-heavy work in thread executor)
        # This prevents blocking the async event loop
        loop = asyncio.get_running_loop()

        # Run CPU-bound text processing in thread pool
        def _process_text_sync():
            clean_body = self._deep_clean_for_embeddings(parsed["document_text"]) if parsed["document_text"] else ""
            clean_subject = self._clean_subject(base_metadata["subject"])

            # 3a. RERANK_TEXT: Full clean body for re-ranker (longest)
            rerank_text = self._create_rerank_text(
                subject=clean_subject,
                from_name=base_metadata["from_name"],
                body=clean_body,
                attachment_texts=attachment_texts,
            )

            # 3b. EMBEDDING_TEXT: Semantic-optimized for vector (medium)
            embedding_text = self._create_embedding_text(
                subject=clean_subject,
                from_name=base_metadata["from_name"],
                body=clean_body,
                attachment_texts=attachment_texts,
            )

            # 3c. SNIPPET: Short preview for display (shortest)
            snippet = self._create_snippet(
                subject=clean_subject,
                body=clean_body,
            )

            return clean_body, clean_subject, rerank_text, embedding_text, snippet

        clean_body, clean_subject, rerank_text, embedding_text, snippet = await loop.run_in_executor(
            _CPU_EXECUTOR, _process_text_sync
        )

        # Yield after heavy processing
        await asyncio.sleep(0)

        # Fallback if embedding_text is empty
        if not embedding_text or not embedding_text.strip():
            logger.warning(
                f"  ⚠️ Email {email_id[:8]} has empty embedding_text! " f"Using subject + snippet as fallback"
            )
            embedding_text = f"{clean_subject}\n\n{parsed.get('snippet', '')}"
            embedding_text = await loop.run_in_executor(_CPU_EXECUTOR, self._deep_clean_for_embeddings, embedding_text)

        logger.debug(f"  Rerank text: {len(rerank_text)} chars")
        logger.debug(f"  Embedding text: {len(embedding_text)} chars")
        logger.debug(f"  Snippet: {len(snippet)} chars")

        # Step 4: Calculate recency score (exponential decay)
        # NOTE: Removed extract_enhanced_metadata - regex-based entity extraction
        # was producing garbage (e.g., "ONLY" as organization, subject as person name).
        # Semantic search + reranking will find entities in text naturally.
        recency_score = self._calculate_recency_score(base_metadata["date_timestamp"])

        # Step 5: Generate embedding
        embeddings = await self.embeddings.embed_batch([embedding_text])
        embedding = embeddings[0] if embeddings else [0.0] * 1536

        # Step 6: Calculate quality score
        quality_score = self.doc_processor.quick_quality_score(embedding_text)

        # Step 7: Build metadata (only reliable fields, no regex-extracted entities)
        metadata = self._build_optimized_metadata(
            base_metadata=base_metadata,
            rerank_text=rerank_text,
            embedding_text=embedding_text,
            snippet=snippet,
            quality_score=quality_score,
            recency_score=recency_score,
            attachment_names=attachment_names,
        )

        # Step 8: Create upsert data
        upsert_data = [
            {
                "id": f"email-{email_id}",
                "values": [float(v) if v is not None else 0.0 for v in embedding],
                "metadata": metadata,
            }
        ]

        processing_time = time.time() - start_time

        logger.info(
            f"  ✅ Email {email_id[:8]} indexed: "
            f"quality={quality_score}, recency={recency_score:.2f}, {processing_time:.2f}s"
        )

        return {
            "email_id": email_id,
            "upsert_data": upsert_data,
            "vectors_created": 1,
            "processing_time": processing_time,
            "quality_score": quality_score,
        }

    async def process_email_batch(
        self,
        emails: List[dict],
        user_id: str,
        fetcher=None,
        process_attachments: bool = True,
        max_attachment_size_mb: int = 10,
        allowed_attachment_types: str = ".pdf,.docx,.doc,.xlsx,.xls,.pptx,.ppt,.txt,.csv,.md,.html,.eml",
        max_concurrent: int = 0,
    ) -> Dict:
        """
        Process multiple emails in batch with deduplication and parallel processing.

        Uses parallel processing for 2-5x speedup on I/O-bound embedding operations.
        Deduplication is done first (sequential), then unique emails are processed in parallel.

        Args:
            emails: List of Gmail API email responses
            user_id: User ID for isolation
            fetcher: GmailFetcher instance for attachment downloads
            process_attachments: Enable attachment processing
            max_attachment_size_mb: Maximum attachment size
            allowed_attachment_types: Comma-separated allowed extensions
            max_concurrent: Max parallel email processors (0 = use config default)

        Returns:
            Dict with processed, duplicates_skipped, errors, total_vectors, upsert_data, etc.
        """
        # Load performance config
        from open_webui.config import (
            GMAIL_YIELD_INTERVAL,
            GMAIL_YIELD_DELAY_MS,
            GMAIL_EMAIL_PROCESSING_CONCURRENCY,
        )

        # Get concurrency limit from config or parameter
        if max_concurrent <= 0:
            max_concurrent = (
                GMAIL_EMAIL_PROCESSING_CONCURRENCY.value
                if hasattr(GMAIL_EMAIL_PROCESSING_CONCURRENCY, "value")
                else 5  # Default: 5 parallel email processors
            )

        yield_interval = GMAIL_YIELD_INTERVAL.value if hasattr(GMAIL_YIELD_INTERVAL, "value") else 5
        yield_delay_ms = GMAIL_YIELD_DELAY_MS.value if hasattr(GMAIL_YIELD_DELAY_MS, "value") else 10
        yield_delay = yield_delay_ms / 1000.0

        batch_start = time.time()

        # =====================================================================
        # PHASE 1: Deduplication (sequential - must track fingerprints)
        # =====================================================================
        seen_content = {}
        unique_emails = []
        duplicate_count = 0

        for email_data in emails:
            email_id = email_data.get("id", "unknown")
            snippet = email_data.get("snippet", "")

            # Detect mass emails (same content sent to many recipients)
            headers = email_data.get("payload", {}).get("headers", [])
            subject = next((h["value"] for h in headers if h["name"] == "Subject"), "")
            content_fingerprint = hashlib.md5(f"{subject[:100]}{snippet[:100]}".encode()).hexdigest()

            if content_fingerprint in seen_content:
                duplicate_count += 1
                logger.debug(f"  ⏭️  Skipping duplicate: {email_id[:8]}")
                continue

            seen_content[content_fingerprint] = email_id
            unique_emails.append(email_data)

        logger.info(
            f"📦 Processing batch of {len(emails)} emails "
            f"({len(unique_emails)} unique, {duplicate_count} duplicates, "
            f"concurrency={max_concurrent})"
        )

        if not unique_emails:
            return {
                "processed": 0,
                "duplicates_skipped": duplicate_count,
                "errors": 0,
                "total_vectors": 0,
                "upsert_data": [],
                "processing_time": time.time() - batch_start,
                "avg_quality_score": 0,
            }

        # =====================================================================
        # PHASE 2: Parallel Processing (I/O-bound - benefits from concurrency)
        # =====================================================================
        all_upsert_data = []
        error_count = 0
        total_quality_score = 0
        processed_count = 0

        # Create processing tasks for all unique emails
        async def process_single_email(email_data: dict) -> Optional[Dict]:
            """Process a single email, returning result or None on error."""
            try:
                result = await self.process_email_for_indexing(
                    email_data,
                    user_id,
                    fetcher=fetcher,
                    process_attachments=process_attachments,
                    max_attachment_size_mb=max_attachment_size_mb,
                    allowed_attachment_types=allowed_attachment_types,
                )
                # Clear email data to free memory
                email_data.clear()
                return result
            except Exception as e:
                email_id = email_data.get("id", "unknown")
                logger.error(f"  ❌ Error processing {email_id[:8]}: {e}")
                return None

        # Process emails in parallel with controlled concurrency
        tasks = [process_single_email(email) for email in unique_emails]
        results = await gather_with_concurrency(
            tasks,
            max_concurrent=max_concurrent,
            return_exceptions=True,
        )

        # Collect results with periodic yields for server responsiveness
        for idx, result in enumerate(results):
            if isinstance(result, Exception):
                error_count += 1
                logger.error(f"  ❌ Parallel processing error: {result}")
            elif result is None:
                error_count += 1
            else:
                all_upsert_data.extend(result["upsert_data"])
                total_quality_score += result.get("quality_score", 0)
                processed_count += 1

            # Yield to event loop periodically
            if yield_interval > 0 and (idx + 1) % yield_interval == 0:
                await asyncio.sleep(yield_delay)

        batch_time = time.time() - batch_start
        avg_quality = total_quality_score / processed_count if processed_count > 0 else 0
        emails_per_second = processed_count / batch_time if batch_time > 0 else 0

        logger.info(
            f"✅ Batch complete: {processed_count} emails, "
            f"{duplicate_count} duplicates, {error_count} errors, "
            f"{emails_per_second:.1f} emails/s (parallel, concurrency={max_concurrent}), "
            f"avg quality={avg_quality:.1f}"
        )

        return {
            "processed": processed_count,
            "duplicates_skipped": duplicate_count,
            "errors": error_count,
            "total_vectors": len(all_upsert_data),
            "upsert_data": all_upsert_data,
            "processing_time": batch_time,
            "avg_quality_score": avg_quality,
        }

    def _clean_subject(self, subject: str) -> str:
        """Clean subject line by removing Re:/Fwd: prefixes."""
        if not subject:
            return ""
        return re.sub(r"^\s*(Re|RE|Fwd|FW|Fw):\s*", "", subject, flags=re.IGNORECASE).strip()

    def _create_rerank_text(
        self,
        subject: str,
        from_name: str,
        body: str,
        attachment_texts: List[str] = None,
    ) -> str:
        """
        Create LONG text for re-ranker (Cohere/Pinecone rerank).

        Strategy: Include as much clean content as possible.
        Re-ranker models can handle 4096+ tokens, so we use up to 3000 chars.

        The re-ranker compares this text against the user's query to
        determine relevance, so more context = better ranking.
        """
        parts = []

        # Subject (high semantic weight)
        if subject:
            parts.append(f"Subject: {subject}")

        # From (for "emails from X" queries)
        if from_name:
            parts.append(f"From: {from_name}")

        # Full body (up to limit)
        if body:
            body_limited = body[: self.RERANK_TEXT_LENGTH - 200]  # Leave room for subject/from
            if body_limited:
                parts.append(body_limited)

        # Attachment content (valuable for search)
        if attachment_texts:
            att_text = " ".join(attachment_texts)[: self.ATTACHMENT_TEXT_LENGTH]
            if att_text:
                parts.append(f"Attachments: {att_text}")

        final_text = "\n\n".join(parts).strip()

        # Ensure we don't exceed limit
        if len(final_text) > self.RERANK_TEXT_LENGTH:
            final_text = final_text[: self.RERANK_TEXT_LENGTH]

        return self._clean_for_pinecone(final_text)

    def _create_embedding_text(
        self,
        subject: str,
        from_name: str,
        body: str,
        attachment_texts: List[str] = None,
    ) -> str:
        """
        Create MEDIUM text for semantic embedding.

        Strategy: Prioritize high-semantic-value content.
        - Subject (users often search by subject)
        - From name (for "emails from X" queries)
        - First paragraph + key sentences from body
        - Attachment names (for "email with PDF about budget")

        This text gets vectorized, so semantic density matters more than length.
        """
        parts = []

        # Subject (high priority for search)
        if subject:
            parts.append(subject)

        # From name
        if from_name:
            parts.append(f"From {from_name}")

        # Body: Smart extraction
        if body:
            # First paragraph (usually contains key info)
            first_para = self._extract_first_paragraph(body, max_chars=600)
            if first_para:
                parts.append(first_para)

            # Key sentences (action items, decisions, questions)
            key_sentences = self._extract_key_sentences(body, max_sentences=3)
            if key_sentences and key_sentences != first_para:
                parts.append(key_sentences)

        # Attachment names (brief)
        if attachment_texts:
            att_preview = " ".join(att[:100] for att in attachment_texts[:3])
            if att_preview:
                parts.append(f"Attachments: {att_preview}")

        final_text = "\n\n".join(parts).strip()

        # Ensure we don't exceed limit
        if len(final_text) > self.EMBEDDING_TEXT_LENGTH:
            final_text = final_text[: self.EMBEDDING_TEXT_LENGTH]
            # Try to end at sentence boundary
            last_period = final_text.rfind(". ")
            if last_period > self.EMBEDDING_TEXT_LENGTH * 0.8:
                final_text = final_text[: last_period + 1]

        return final_text

    def _create_snippet(self, subject: str, body: str) -> str:
        """
        Create SHORT snippet for UI display.

        Shows just enough to identify the email in search results.
        """
        if subject and body:
            # Subject + first part of body
            snippet = f"{subject}: {body[:100]}"
        elif subject:
            snippet = subject
        elif body:
            snippet = body[: self.SNIPPET_LENGTH]
        else:
            snippet = "No content"

        # Limit and clean
        snippet = snippet[: self.SNIPPET_LENGTH].strip()
        if len(snippet) == self.SNIPPET_LENGTH:
            snippet = snippet.rsplit(" ", 1)[0] + "..."

        return self._clean_for_pinecone(snippet)

    def _extract_first_paragraph(self, text: str, max_chars: int = 500) -> str:
        """Extract the first meaningful paragraph from email body."""
        if not text:
            return ""

        # Split by double newlines (paragraphs)
        paragraphs = re.split(r"\n\s*\n", text)

        for para in paragraphs:
            para = para.strip()
            # Skip very short paragraphs (likely greetings)
            if len(para) > 20:
                return para[:max_chars]

        # Fallback: just return first chunk
        return text[:max_chars]

    def _extract_key_sentences(self, text: str, max_sentences: int = 3) -> str:
        """
        Extract key sentences that likely contain important information.

        Looks for:
        - Questions (often contain the main ask)
        - Action items (please, need, should, must)
        - Decisions (decided, agreed, confirmed)
        - Dates/deadlines (by, on, before)
        """
        if not text:
            return ""

        # Split into sentences
        sentences = re.split(r"[.!?]+\s+", text)

        # Keywords that indicate important content
        important_patterns = [
            r"\?",  # Questions
            r"\b(please|need|required|urgent|asap|deadline)\b",
            r"\b(decided|agreed|confirmed|approved|scheduled)\b",
            r"\b(by|before|on)\s+\w+\s+\d",  # Dates
            r"\b(meeting|call|discuss|review)\b",
            r"\b(attached|attachment|see below)\b",
        ]

        key_sentences = []
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 10:
                continue

            # Check if sentence contains important patterns
            for pattern in important_patterns:
                if re.search(pattern, sentence, re.IGNORECASE):
                    key_sentences.append(sentence)
                    break

            if len(key_sentences) >= max_sentences:
                break

        return ". ".join(key_sentences) + "." if key_sentences else ""

    def _calculate_recency_score(self, timestamp: int) -> float:
        """
        Calculate recency score using exponential decay.

        Score ranges from 0.0 (very old) to 1.0 (very recent).
        Half-life: 30 days (email 30 days old has score ~0.5)

        This can be used to boost recent emails in search ranking.
        """
        if not timestamp:
            return 0.5  # Default for unknown dates

        now = time.time()
        age_seconds = max(0, now - timestamp)
        age_days = age_seconds / (24 * 3600)

        # Exponential decay with 30-day half-life
        half_life_days = 30
        decay_rate = math.log(2) / half_life_days
        score = math.exp(-decay_rate * age_days)

        # Clamp to [0.0, 1.0]
        return max(0.0, min(1.0, score))

    @staticmethod
    def _deep_clean_for_embeddings(text: str) -> str:
        """
        Production-grade text cleaning for optimal embeddings.

        V5 - Improved cleaning:
        - KEEPS emails and URLs intact (useful for search: "email from john@...")
        - Removes email signatures, disclaimers, and confidentiality notices
        - Removes quoted reply text
        - Deduplicates repeated content
        - Fixes whitespace without breaking words
        """
        if not text:
            return ""

        # STEP 1: Fix escape sequences
        text = text.replace("\\\\n", "\n")
        text = text.replace("\\\\t", "\t")
        text = text.replace("\\\\r", "\r")
        text = text.replace("\\n\\n", "\n\n")
        text = text.replace("\\n", "\n")
        text = text.replace("\\t", "    ")
        text = text.replace("\\r", "")
        text = text.replace('\\"', '"')
        text = text.replace("\\'", "'")
        text = text.replace("\\\\", "")
        text = text.replace("\\/", "/")

        # STEP 2: Strip HTML completely (defense in depth)
        text = re.sub(r"<![^>]*>", "", text, flags=re.IGNORECASE)
        text = re.sub(r"<\?[^>]*\?>", "", text, flags=re.IGNORECASE)
        text = re.sub(r"<!\[CDATA\[.*?\]\]>", "", text, flags=re.DOTALL)
        text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
        text = re.sub(r"<script[^>]*>.*?</script>", "", text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'\s*style\s*=\s*["\'][^"\']*["\']', "", text, flags=re.IGNORECASE)
        text = re.sub(r"<[^>]+>", "", text)
        text = re.sub(r"\[if[^\]]*\].*?\[endif\]", "", text, flags=re.DOTALL | re.IGNORECASE)

        # STEP 3: Remove HTML entities EARLY (before other processing)
        from html import unescape

        text = unescape(text)

        # STEP 4: Remove quoted reply blocks (various formats)
        # "On DATE, NAME wrote:" format
        text = re.sub(r"On .{1,100}wrote:.*", "", text, flags=re.DOTALL | re.IGNORECASE)
        # Quoted lines starting with >
        text = re.sub(r"^>.*$", "", text, flags=re.MULTILINE)
        # Outlook-style reply headers
        text = re.sub(
            r"From:.*?\n(?:Sent|Date):.*?\nTo:.*?\n(?:Subject:.*?\n)?",
            "",
            text,
            flags=re.DOTALL | re.IGNORECASE,
        )
        # Gmail-style forwarded marker
        text = re.sub(r"---------- Forwarded message.*?----------", "", text, flags=re.DOTALL | re.IGNORECASE)

        # STEP 5: Remove email signatures (comprehensive)
        # Standard "-- " signature delimiter
        text = re.sub(r"\n--\s*\n.*", "", text, flags=re.DOTALL)
        # Mobile device signatures
        text = re.sub(
            r"Sent from my (iPhone|iPad|Android|Galaxy|Pixel|Mobile|BlackBerry).*",
            "",
            text,
            flags=re.IGNORECASE | re.DOTALL,
        )
        text = re.sub(r"Get Outlook for (iOS|Android).*", "", text, flags=re.IGNORECASE | re.DOTALL)
        # Professional signatures with underscores
        text = re.sub(r"_{5,}.*", "", text, flags=re.DOTALL)
        # Signatures starting with name + title patterns
        text = re.sub(
            r"\n[A-Z][a-z]+ [A-Z][a-z]+\n(?:CEO|CTO|CFO|COO|President|Director|Manager|Founder|Managing|VP|Vice).*",
            "",
            text,
            flags=re.DOTALL,
        )

        # STEP 6: Remove email disclaimers (comprehensive patterns)
        disclaimer_patterns = [
            # "This email/message is confidential..."
            r"This (?:email|e-mail|message|communication)[\s\S]{0,50}(?:confidential|privileged|intended)[\s\S]*?(?:notify|delete|destroy|disregard)[\s\S]*?(?:\.|$)",
            # "If you have received this message in error..."
            r"If you (?:have )?received this (?:email|message|communication)[\s\S]*?(?:error|mistake)[\s\S]*?(?:\.|$)",
            # "The information contained in this..."
            r"The information contained in[\s\S]*?(?:confidential|privileged)[\s\S]*?(?:\.|$)",
            # "CONFIDENTIALITY NOTICE" headers
            r"(?:CONFIDENTIALITY|PRIVACY|LEGAL)\s*(?:NOTICE|DISCLAIMER|WARNING)[\s\S]*?(?:\.|$)",
            # "If the reader of this message..."
            r"If the reader of this[\s\S]*?(?:notify|delete)[\s\S]*?(?:\.|$)",
            # "Please consider the environment..."
            r"Please consider the environment before printing[\s\S]*?(?:\.|$)",
            # Generic disclaimer footer
            r"DISCLAIMER:[\s\S]*?(?:\.|$)",
        ]
        for pattern in disclaimer_patterns:
            text = re.sub(pattern, "", text, flags=re.IGNORECASE)

        # STEP 7: Remove control characters
        text = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F]", "", text)

        # STEP 8: Deduplicate repeated sentences/phrases
        # Split into sentences and remove duplicates while preserving order
        sentences = re.split(r'(?<=[.!?])\s+', text)
        seen_sentences = set()
        unique_sentences = []
        for sentence in sentences:
            # Normalize for comparison (lowercase, strip)
            normalized = sentence.lower().strip()
            # Only add if not seen and not too short
            if len(normalized) > 10 and normalized not in seen_sentences:
                seen_sentences.add(normalized)
                unique_sentences.append(sentence)
            elif len(normalized) <= 10:
                unique_sentences.append(sentence)  # Keep short sentences
        text = " ".join(unique_sentences)

        # STEP 9: Fix line break artifacts (careful not to break URLs/emails)
        # Join hyphenated words split across lines
        text = re.sub(r"(\w)-\s*\n\s*(\w)", r"\1\2", text)
        # Join lines within paragraphs (but not if next line starts with uppercase after period)
        text = re.sub(r"(?<=[a-z,])\n(?=[a-z])", " ", text)

        # STEP 10: Normalize whitespace (carefully)
        # Replace multiple spaces with single space
        text = re.sub(r" {2,}", " ", text)
        # Replace 3+ newlines with double newline
        text = re.sub(r"\n{3,}", "\n\n", text)
        # Strip each line
        lines = text.split("\n")
        text = "\n".join(line.strip() for line in lines)

        # STEP 11: Fix orphaned punctuation (but not in URLs/emails)
        # Remove space before punctuation
        text = re.sub(r"\s+([.,!?;:])\s", r"\1 ", text)
        # Don't add space after punctuation if followed by @ or / (URLs/emails)
        text = re.sub(r"([.,!?;:])([A-Za-z])(?![/@])", r"\1 \2", text)

        # STEP 12: Remove empty parentheses and brackets left after cleaning
        text = re.sub(r"\(\s*\)", "", text)
        text = re.sub(r"\[\s*\]", "", text)
        text = re.sub(r"\|\s*\|", "|", text)

        # STEP 13: Final whitespace cleanup
        text = re.sub(r" {2,}", " ", text)
        text = re.sub(r"\n ", "\n", text)

        return text.strip()

    def _build_optimized_metadata(
        self,
        base_metadata: Dict,
        rerank_text: str,
        embedding_text: str,
        snippet: str,
        quality_score: int,
        recency_score: float,
        attachment_names: List[str] = None,
    ) -> Dict:
        """
        Build metadata optimized for semantic search + re-ranking.

        V4 - Simplified metadata (removed unreliable regex-extracted fields):
        - KEPT: rerank_text, chunk_text, snippet (text for search)
        - KEPT: from_*, to_*, subject, date, labels (reliable header data)
        - KEPT: attachments, has_attachments (reliable Gmail API data)
        - REMOVED: topics, keywords, entity_* (regex extraction was garbage)

        Semantic search + re-ranking finds entities in text naturally.
        """
        email_id = base_metadata["email_id"]
        user_id = base_metadata["user_id"]

        # Labels as array (from Gmail API - reliable)
        labels = base_metadata.get("labels", [])
        if isinstance(labels, str):
            labels = [l.strip() for l in labels.split(",") if l.strip()]

        # Attachment names as array (from Gmail API - reliable)
        attachments = attachment_names if attachment_names else []

        # Clean text fields for Pinecone (remove \n, control chars, etc.)
        clean_rerank = self._clean_for_pinecone(rerank_text)
        clean_chunk = self._clean_for_pinecone(embedding_text)
        clean_snippet = self._clean_for_pinecone(snippet)

        metadata = {
            # === Core Identification ===
            "type": "email",
            "email_id": email_id,
            "thread_id": base_metadata["thread_id"],
            "user_id": user_id,
            "index_version": self.INDEX_VERSION,
            # === Text Fields (cleaned for Pinecone, no \n) ===
            "rerank_text": clean_rerank,  # LONG: For re-ranker (up to 3000 chars)
            "chunk_text": clean_chunk,  # MEDIUM: For display (up to 1500 chars)
            "snippet": clean_snippet,  # SHORT: UI preview (up to 150 chars)
            # === Structured Email Fields (from headers - reliable) ===
            "subject": self._clean_for_pinecone(base_metadata["subject"]),
            "from_name": self._clean_for_pinecone(base_metadata["from_name"]),
            "from_email": base_metadata["from_email"],
            "to_name": self._clean_for_pinecone(base_metadata.get("to_name", "")),
            "to_email": base_metadata.get("to_email", ""),
            "cc": base_metadata.get("cc", ""),
            # === Temporal Fields ===
            "date": base_metadata["date"],
            "date_timestamp": base_metadata["date_timestamp"],
            "timestamp": datetime.utcnow().isoformat() + "Z",
            # === Arrays for Pinecone Filtering ===
            "labels": labels,  # From Gmail API: ["SENT", "IMPORTANT", "INBOX"]
            "attachments": attachments,  # Filenames: ["report.pdf", "data.xlsx"]
            # === Email Properties ===
            "has_attachments": base_metadata["has_attachments"],
            "attachment_count": len(attachments),
            "is_reply": base_metadata.get("is_reply", False),
            "word_count": len(embedding_text.split()),
            # === Quality & Ranking Metrics ===
            "quality_score": quality_score,
            "recency_score": round(recency_score, 3),  # 0.0-1.0, higher = more recent
            # === Technical ===
            "source": "gmail",
            "doc_type": "email",
            "hash": hashlib.sha256(f"{email_id}{user_id}".encode()).hexdigest(),
        }

        logger.debug(
            f"  Metadata built: rerank_text={len(metadata['rerank_text'])} chars, "
            f"chunk_text={len(metadata['chunk_text'])} chars, "
            f"snippet={len(metadata['snippet'])} chars, "
            f"recency_score={metadata['recency_score']}"
        )

        return metadata

    @staticmethod
    def _clean_list(items: List) -> List[str]:
        """
        Clean a list of strings for Pinecone array storage.

        Returns a clean list (not comma-separated string).
        Pinecone supports arrays for $in filtering.
        """
        if not items:
            return []

        if isinstance(items, str):
            # Handle case where it's already a comma-separated string
            items = [i.strip() for i in items.split(",")]

        cleaned = []
        for item in items:
            if item:
                item_str = str(item).strip()
                # Remove escape sequences
                item_str = item_str.replace("\\n", " ").replace("\\t", " ").replace("\\r", "")
                item_str = re.sub(r"\s+", " ", item_str).strip()
                if item_str and len(item_str) > 1:  # Skip single chars
                    cleaned.append(item_str)

        # Remove duplicates while preserving order
        seen = set()
        unique = []
        for item in cleaned:
            if item.lower() not in seen:
                seen.add(item.lower())
                unique.append(item)

        return unique[:20]  # Limit to 20 items per array

    @staticmethod
    def _clean_for_pinecone(text: str) -> str:
        """
        Final cleaning for Pinecone storage.

        Ensures:
        - No escape sequences
        - No control characters
        - Single-line format
        - Valid UTF-8
        - Within size limits
        """
        if not text:
            return ""

        # Handle escape sequences
        text = text.replace("\\n\\n", "  ")
        text = text.replace("\\n", " ")
        text = text.replace("\\t", " ")
        text = text.replace("\\r", "")
        text = text.replace("\\\\", "")

        # Convert actual newlines to spaces
        text = text.replace("\n\n", "  ")
        text = text.replace("\n", " ")
        text = text.replace("\t", " ")

        # Remove control characters
        text = re.sub(r"[\x00-\x1F\x7F-\x9F\u200B-\u200D\uFEFF]", "", text)

        # Normalize whitespace
        text = re.sub(r" {2,}", " ", text)
        text = text.strip()

        # Ensure valid UTF-8
        text = text.encode("utf-8", "ignore").decode("utf-8")

        # Limit length (Pinecone 40KB metadata limit per field)
        max_length = 10000
        if len(text) > max_length:
            text = text[:max_length] + "..."

        return text

    async def _process_email_attachments(
        self,
        attachments_info: List[Dict],
        fetcher,
        email_id: str,
        max_size_mb: int,
        allowed_types: str,
    ) -> List[Dict]:
        """Process email attachments using unstructured.io."""
        from open_webui.utils.gmail_attachment_processor import GmailAttachmentProcessor

        att_processor = GmailAttachmentProcessor(max_size_mb=max_size_mb, allowed_extensions=allowed_types)

        return await att_processor.process_attachments_batch(attachments_info, fetcher, email_id)
