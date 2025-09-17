"""
Pure txtai-wikipedia semantic search - absolutely generic
"""

import asyncio
import hashlib
import importlib.util
import logging
import re
import time
import weakref
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Optional
from datetime import datetime

from open_webui.env import SRC_LOG_LEVELS
from .context_analysis import analyze_conversation_context

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["GROUNDING"])


def _get_txtai_embeddings():
    """Lazy load txtai.embeddings.Embeddings with clear error message"""
    try:
        from txtai.embeddings import Embeddings

        return Embeddings
    except ImportError:
        raise ImportError(
            "txtai is required for Wikipedia grounding. "
            "Install with: pip install txtai[similarity]"
        )


def _get_transformers_pipeline():
    """Lazy load transformers.pipeline with clear error message"""
    try:
        from transformers import pipeline

        return pipeline
    except ImportError:
        raise ImportError(
            "transformers is required for language detection. "
            "Install with: pip install transformers"
        )


def _get_txtai_reranker():
    """Lazy load txtai.pipeline.Reranker and Similarity with clear error message"""
    try:
        from txtai.pipeline import Reranker, Similarity

        return Reranker, Similarity
    except ImportError:
        raise ImportError(
            "txtai 9.0+ is required for reranking. "
            "Install with: pip install txtai>=9.0"
        )


def _check_optional_dependency(module_name: str) -> bool:
    """Check if an optional dependency is available"""
    return importlib.util.find_spec(module_name) is not None


class WikiSearchGrounder:
    """Pure txtai-wikipedia implementation with lazy loading and concurrency control"""

    # Class-level semaphore for controlling concurrent operations
    # Use limit of 1 to prevent memory exhaustion ("Brian Smash" technique)
    _semaphore = None
    _semaphore_lock = asyncio.Lock()
    MAX_CONCURRENT_OPERATIONS = 1

    # Query-specific locks to prevent concurrent processing of identical queries
    # Using WeakValueDictionary to automatically clean up completed queries
    _query_locks = weakref.WeakValueDictionary()
    _query_locks_lock = asyncio.Lock()

    def __init__(self):
        self.max_content_length = 4000
        self.max_search_results = 5
        self.embeddings = None
        self.translator = None
        self.reranker = None
        self.model_loaded = False
        self.translation_loaded = False
        self.reranker_loaded = False
        self._initialized = False

    @classmethod
    async def _get_semaphore(cls):
        """Get or create the class-level semaphore for concurrency control"""
        if cls._semaphore is None:
            async with cls._semaphore_lock:
                # Double-check pattern
                if cls._semaphore is None:
                    cls._semaphore = asyncio.Semaphore(cls.MAX_CONCURRENT_OPERATIONS)
                    log.info(
                        f"🔒 Wiki grounding semaphore initialized with {cls.MAX_CONCURRENT_OPERATIONS} concurrent operations allowed"
                    )
        return cls._semaphore

    async def _acquire_lock(
        self, operation_name: str
    ) -> tuple[asyncio.Semaphore, float]:
        """Acquire semaphore lock and return semaphore and start time for monitoring"""
        semaphore = await self._get_semaphore()

        # Log queue status before acquiring
        available_permits = (
            semaphore._value if hasattr(semaphore, "_value") else "unknown"
        )
        log.debug(
            f"🚦 [{operation_name}] Requesting semaphore (available: {available_permits})"
        )

        start_time = time.time()
        await semaphore.acquire()

        wait_time = time.time() - start_time
        if wait_time > 0.1:  # Log if we waited more than 100ms
            log.debug(
                f"🔓 [{operation_name}] Acquired semaphore after {wait_time:.2f}s wait"
            )
        else:
            log.debug(f"🔓 [{operation_name}] Acquired semaphore immediately")

        return semaphore, start_time

    def _release_lock(
        self, semaphore: asyncio.Semaphore, operation_name: str, start_time: float
    ):
        """Release semaphore lock and log timing information"""
        total_time = time.time() - start_time
        semaphore.release()
        available_permits = (
            semaphore._value if hasattr(semaphore, "_value") else "unknown"
        )
        log.debug(
            f"🔓 [{operation_name}] Released semaphore after {total_time:.2f}s (available: {available_permits})"
        )

    @classmethod
    async def _get_query_lock(cls, query: str) -> asyncio.Lock:
        """Get or create a query-specific lock to prevent concurrent processing of identical queries"""
        # Create a hash of the query to use as a key
        query_hash = hashlib.md5(query.encode("utf-8")).hexdigest()

        async with cls._query_locks_lock:
            if query_hash not in cls._query_locks:
                # Create a new lock for this query
                query_lock = asyncio.Lock()
                cls._query_locks[query_hash] = query_lock
                log.debug(
                    f"🔐 Created new query lock for: '{query[:50]}...' (hash: {query_hash[:8]})"
                )
            else:
                query_lock = cls._query_locks[query_hash]
                log.debug(
                    f"🔐 Reusing existing query lock for: '{query[:50]}...' (hash: {query_hash[:8]})"
                )

            return query_lock

    async def _acquire_query_lock(
        self, query: str, operation_name: str
    ) -> tuple[asyncio.Lock, str, float]:
        """Acquire query-specific lock and return lock, query hash, and start time"""
        query_lock = await self._get_query_lock(query)
        query_hash = hashlib.md5(query.encode("utf-8")).hexdigest()

        # Log attempt to acquire query lock
        log.debug(
            f"🚦 [{operation_name}] Requesting query lock for: '{query[:50]}...' (hash: {query_hash[:8]})"
        )

        start_time = time.time()
        await query_lock.acquire()

        wait_time = time.time() - start_time
        if wait_time > 0.1:  # Log if we waited more than 100ms
            log.info(
                f"🔐 [{operation_name}] Acquired query lock after {wait_time:.2f}s wait for: '{query[:50]}...'"
            )
        else:
            log.debug(
                f"🔐 [{operation_name}] Acquired query lock immediately for: '{query[:50]}...'"
            )

        return query_lock, query_hash, start_time

    def _release_query_lock(
        self,
        query_lock: asyncio.Lock,
        query_hash: str,
        operation_name: str,
        start_time: float,
        query: str,
    ):
        """Release query-specific lock and log timing information"""
        total_time = time.time() - start_time
        query_lock.release()
        log.debug(
            f"🔐 [{operation_name}] Released query lock after {total_time:.2f}s for: '{query[:50]}...' (hash: {query_hash[:8]})"
        )

    @classmethod
    async def get_queue_status(cls) -> dict:
        """Get current queue status for monitoring"""
        if cls._semaphore is None:
            return {
                "semaphore_initialized": False,
                "available_permits": "N/A",
                "max_concurrent": "N/A",
                "waiting_operations": "N/A",
            }

        available = (
            cls._semaphore._value if hasattr(cls._semaphore, "_value") else "unknown"
        )
        waiters = getattr(cls._semaphore, "_waiters", None)
        waiting = len(waiters) if waiters is not None else "unknown"

        return {
            "semaphore_initialized": True,
            "available_permits": available,
            "max_concurrent": cls.MAX_CONCURRENT_OPERATIONS,
            "waiting_operations": waiting,
            "active_operations": (
                cls.MAX_CONCURRENT_OPERATIONS - available
                if isinstance(available, int)
                else "unknown"
            ),
        }

    async def initialize(self) -> bool:
        """Initialize models (call once before using search methods)"""
        if self._initialized:
            return True

        success = True

        # Initialize txtai model first
        if not self._load_txtai_model():
            success = False

        # Initialize translation model (optional)
        self._load_translation_model()

        # Initialize reranker model (optional) - must be after embeddings
        if self.model_loaded:
            self._load_reranker_model()

        self._initialized = success
        return success

    async def ensure_initialized(self) -> bool:
        """Ensure models are initialized before use"""
        if not self._initialized:
            return await self.initialize()
        return True

    def _load_translation_model(self) -> bool:
        """Load HuggingFace translation pipeline"""
        if self.translation_loaded:
            return True

        if not _check_optional_dependency("transformers"):
            log.warning(
                "transformers not available for translation. Install with: pip install transformers>=4.46.0"
            )
            return False

        try:
            pipeline = _get_transformers_pipeline()

            log.info("Loading French-to-English translation pipeline...")
            # Use a lightweight multilingual translation model
            self.translator = pipeline(
                "translation",
                model="Helsinki-NLP/opus-mt-fr-en",
                device=-1,  # Use CPU to avoid memory issues
            )
            self.translation_loaded = True
            log.info("HuggingFace translation pipeline loaded successfully")
            return True
        except Exception as e:
            log.warning(f"Translation pipeline failed to load: {e}")
            return False

    def _load_reranker_model(self) -> bool:
        """Load txtai reranker pipeline for improved result ranking"""
        if self.reranker_loaded:
            return True

        # Check if reranker is enabled in config
        try:
            from open_webui.config import ENABLE_WIKIPEDIA_GROUNDING_RERANKER

            if not ENABLE_WIKIPEDIA_GROUNDING_RERANKER.value:
                log.info("Wikipedia grounding reranker disabled by configuration")
                return False
        except ImportError:
            log.warning("Could not check reranker configuration, assuming enabled")

        if not _check_optional_dependency("txtai"):
            log.warning(
                "txtai not available for reranking. Install with: pip install txtai[similarity]"
            )
            return False

        # Ensure embeddings are loaded first
        if not self.model_loaded or not self.embeddings:
            log.warning("Embeddings must be loaded before reranker")
            return False

        try:
            Reranker, Similarity = _get_txtai_reranker()

            log.info("Loading txtai reranker pipeline...")
            # Create similarity instance using ColBERT
            similarity = Similarity(path="colbert-ir/colbertv2.0", lateencode=True)

            # Create reranker using embeddings + similarity
            self.reranker = Reranker(self.embeddings, similarity)
            self.reranker_loaded = True
            log.info("txtai reranker pipeline loaded successfully")
            return True
        except Exception as e:
            log.warning(f"Reranker pipeline failed to load: {e}")
            return False

    def _detect_language(self, text: str) -> str:
        """Simple language detection - check for French indicators"""
        french_words = [
            "qui",
            "est",
            "le",
            "la",
            "les",
            "des",
            "du",
            "de",
            "et",
            "ou",
            "que",
            "dans",
            "avec",
            "pour",
            "par",
            "sur",
        ]
        text_lower = text.lower()
        french_count = sum(
            1
            for word in french_words
            if f" {word} " in f" {text_lower} "
            or text_lower.startswith(f"{word} ")
            or text_lower.endswith(f" {word}")
        )

        # If multiple French words detected, likely French
        if french_count >= 2:
            return "fr"
        return "en"

    def _translate_to_english(self, text: str) -> str:
        """Translate text to English if French is detected"""
        if not self.translation_loaded:
            return text

        try:
            detected_lang = self._detect_language(text)
            if detected_lang == "fr":
                # The model expects French input
                translated_result = self.translator(text)
                translated_text = translated_result[0]["translation_text"]
                log.info(f"Translated query: '{text}' -> '{translated_text}'")
                return translated_text
            return text
        except Exception as e:
            log.warning(f"Translation failed, using original query: {e}")
            return text

    def _load_txtai_model(self) -> bool:
        """Load txtai-wikipedia from local filesystem cache or HuggingFace Hub"""
        if self.model_loaded:
            return True

        if not _check_optional_dependency("txtai"):
            log.error(
                "txtai is not available. Please install with: pip install txtai[graph]>=8.6.0"
            )
            return False

        try:
            import os
            import glob

            Embeddings = _get_txtai_embeddings()

            # Import TXTAI_CACHE_DIR from config for proper environment variable support
            from open_webui.config import TXTAI_CACHE_DIR

            # Try loading from local filesystem cache first using configurable cache directory
            cache_base = os.path.join(
                TXTAI_CACHE_DIR, "hub", "models--neuml--txtai-wikipedia"
            )
            snapshots_dir = os.path.join(cache_base, "snapshots")

            if os.path.exists(snapshots_dir):
                # Find the latest snapshot directory
                snapshot_dirs = glob.glob(os.path.join(snapshots_dir, "*"))
                if snapshot_dirs:
                    # Use the first available snapshot (there should typically be only one)
                    latest_snapshot = sorted(snapshot_dirs)[-1]

                    # Check if required files exist
                    embeddings_file = os.path.join(latest_snapshot, "embeddings")
                    documents_file = os.path.join(latest_snapshot, "documents")
                    config_file = os.path.join(latest_snapshot, "config.json")

                    if all(
                        os.path.exists(f)
                        for f in [embeddings_file, documents_file, config_file]
                    ):
                        log.info(
                            f"Loading txtai-wikipedia model from local cache: {latest_snapshot}"
                        )
                        self.embeddings = Embeddings()
                        self.embeddings.load(latest_snapshot)
                        self.model_loaded = True
                        log.info(
                            "txtai-wikipedia model loaded successfully from local cache"
                        )
                        return True
                    else:
                        log.warning(
                            f"Required files missing in cache snapshot: {latest_snapshot}"
                        )
                else:
                    log.debug(f"No snapshots found in: {snapshots_dir}")
            else:
                log.debug(f"Cache directory not found: {snapshots_dir}")

            # Fallback to HuggingFace Hub if local cache is not available
            log.info(
                "Local cache not found, loading txtai-wikipedia model from HuggingFace Hub..."
            )
            self.embeddings = Embeddings()
            self.embeddings.load(
                provider="huggingface-hub", container="neuml/txtai-wikipedia"
            )
            self.model_loaded = True
            log.info("txtai-wikipedia model loaded successfully from HuggingFace Hub")
            return True
        except Exception as e:
            log.error(f"Failed to load txtai-wikipedia: {e}")
            return False

    async def search(self, query: str) -> List[Dict]:
        """Pure txtai search with translation and reranking support"""
        # Ensure models are initialized
        if not await self.ensure_initialized():
            return []

        try:
            # Translate query to English for better search results
            original_query = query
            search_query = self._translate_to_english(query)

            # Apply temporal enhancement AFTER translation to English
            # This ensures decade detection works properly for all languages
            from .context_analysis import ConversationContextAnalyzer

            temp_analyzer = ConversationContextAnalyzer()
            temporal_enhanced_query = (
                temp_analyzer._enhance_query_with_temporal_context(search_query)
            )

            if temporal_enhanced_query != search_query:
                log.info(
                    f"🕒 Applied temporal enhancement after translation: '{search_query}' -> '{temporal_enhanced_query}'"
                )
                search_query = temporal_enhanced_query

            # Use basic search with translated query - get more results for reranking
            initial_results_count = (
                self.max_search_results * 3
            )  # Get 3x more for reranking

            results = self.embeddings.search(search_query, limit=initial_results_count)

            # Format initial results
            formatted = []

            for result in results:
                if isinstance(result, dict):
                    score = result.get("score", 0)

                    # Apply a lower threshold since we'll rerank
                    if score > 0.75:  # Lower threshold for reranking candidates
                        title = result.get("id", "")
                        content = result.get("text", "")

                        if len(content) > self.max_content_length:
                            content = content[: self.max_content_length] + "..."

                        formatted_result = {
                            "title": title,
                            "content": content,
                            "score": score,
                            "url": f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}",
                            "source": "txtai-wikipedia",
                            "original_query": original_query,
                            "search_query": search_query,
                        }

                        formatted.append(formatted_result)

            # Apply reranking if available and we have multiple results
            if self.reranker_loaded and len(formatted) > 1:
                # Acquire semaphore lock to control concurrency during reranking
                semaphore, start_time = await self._acquire_lock("reranking")

                try:
                    log.info(
                        f"🔍 Reranking {len(formatted)} search results using txtai reranker"
                    )

                    # Run reranking on thread pool to prevent blocking event loop
                    def run_reranking():
                        return self.reranker(
                            search_query, limit=self.max_search_results * 2
                        )

                    # Use thread pool executor to prevent blocking K8s health checks
                    with ThreadPoolExecutor(max_workers=1) as executor:
                        loop = asyncio.get_event_loop()
                        reranked_results = await loop.run_in_executor(
                            executor, run_reranking
                        )

                    # Create mapping of our formatted results by title
                    title_to_formatted = {
                        result["title"]: result for result in formatted
                    }

                    # Enhance existing results where reranking improves scores
                    enhanced_count = 0
                    for rerank_result in reranked_results:
                        title = rerank_result.get("id", "")
                        rerank_score = rerank_result.get("score", 0)

                        # Find matching formatted result
                        if title in title_to_formatted:
                            original_result = title_to_formatted[title]
                            original_score = original_result["score"]

                            # Only improve if reranker score is better
                            if rerank_score > original_score:
                                # Enhance with reranker score
                                original_result["rerank_score"] = rerank_score
                                original_result["original_score"] = original_score
                                original_result["enhanced_by_reranker"] = True
                                original_result["ranking_improvement"] = (
                                    rerank_score - original_score
                                )
                                original_result["improvement_percentage"] = (
                                    (rerank_score - original_score) / original_score
                                ) * 100
                                original_result["score"] = (
                                    rerank_score  # Use improved score
                                )
                                enhanced_count += 1
                            else:
                                # Keep original score - reranker didn't improve
                                original_result["rerank_score"] = original_score
                                original_result["original_score"] = original_score
                                original_result["enhanced_by_reranker"] = False
                                original_result["ranking_improvement"] = 0.0
                                original_result["improvement_percentage"] = 0.0

                    # For results not touched by reranker, add metadata
                    for result in formatted:
                        if "enhanced_by_reranker" not in result:
                            result["rerank_score"] = result["score"]
                            result["original_score"] = result["score"]
                            result["enhanced_by_reranker"] = False
                            result["ranking_improvement"] = 0.0
                            result["improvement_percentage"] = 0.0

                    # Re-sort by final scores (some may have been improved)
                    formatted.sort(key=lambda x: x["score"], reverse=True)

                    # Apply temporal relevance boost if search query contains current year
                    current_year = str(datetime.now().year)
                    if current_year in search_query:
                        log.info(
                            f"🕒 Applying temporal relevance boost for {current_year}"
                        )
                        for result in formatted:
                            title = result.get("title", "")
                            if current_year in title:
                                original_score = result["score"]
                                # Apply a significant boost to current year results
                                result["score"] = min(
                                    1.0, original_score * 1.3
                                )  # 30% boost, capped at 1.0
                                result["temporal_boost_applied"] = True
                                result["temporal_boost_amount"] = (
                                    result["score"] - original_score
                                )
                                log.info(
                                    f"🕒 Boosted '{title}' from {original_score:.3f} to {result['score']:.3f}"
                                )
                            else:
                                result["temporal_boost_applied"] = False
                                result["temporal_boost_amount"] = 0.0

                        # Re-sort after temporal boosting
                        formatted.sort(key=lambda x: x["score"], reverse=True)

                    log.info(
                        f"🎯 Intelligent reranking completed: {enhanced_count} results improved, top result: {formatted[0]['title']} (score: {formatted[0].get('score', 'N/A')})"
                    )

                except Exception as e:
                    log.warning(f"🚨 Reranking failed: {e}")
                    # Keep original results if reranking fails
                finally:
                    # Always release the semaphore lock after reranking
                    self._release_lock(semaphore, "reranking", start_time)
            else:
                # No reranking available, but still apply temporal relevance boost
                current_year = str(datetime.now().year)
                if current_year in search_query:
                    log.info(
                        f"🕒 Applying temporal relevance boost for {current_year} (no reranking)"
                    )
                    for result in formatted:
                        title = result.get("title", "")
                        if current_year in title:
                            original_score = result["score"]
                            # Apply a significant boost to current year results
                            result["score"] = min(
                                1.0, original_score * 1.3
                            )  # 30% boost, capped at 1.0
                            result["temporal_boost_applied"] = True
                            result["temporal_boost_amount"] = (
                                result["score"] - original_score
                            )
                            log.info(
                                f"🕒 Boosted '{title}' from {original_score:.3f} to {result['score']:.3f}"
                            )
                        else:
                            result["temporal_boost_applied"] = False
                            result["temporal_boost_amount"] = 0.0

                    # Re-sort after temporal boosting
                    formatted.sort(key=lambda x: x["score"], reverse=True)

            # Return top results
            final_results = formatted[: self.max_search_results]

            # Apply final quality threshold
            high_quality_results = [r for r in final_results if r["score"] > 0.8]

            return (
                high_quality_results if high_quality_results else final_results[:3]
            )  # At least 3 results

        except Exception as e:
            log.error(f"Search failed: {e}")
            return []

    async def ground_query(
        self, query: str, request=None, user=None, messages: List[Dict] = None
    ) -> Optional[Dict]:
        """
        Main grounding method with context awareness.

        When wiki grounding is enabled, this method will:
        1. Analyze conversation context for follow-up questions
        2. Enhance queries with pronoun replacement and entity context
        3. Search Wikipedia for relevant information

        No intelligent filtering - if grounding is enabled, we always attempt to ground.
        """
        # Basic length check
        if len(query.strip()) < 3:
            log.info("🔍 Query too short, skipping grounding")
            return None

        # Analyze conversation context if messages provided
        original_query = query
        context_metadata = {}

        if messages and len(messages) > 1:
            is_enhanced, enhanced_query, context_metadata = (
                analyze_conversation_context(query, messages)
            )
            if is_enhanced:
                enhancement_type = []
                if context_metadata.get("temporal_enhanced"):
                    enhancement_type.append("temporal")
                if context_metadata.get("context_aware"):
                    enhancement_type.append("context")

                enhancement_desc = (
                    " + ".join(enhancement_type) if enhancement_type else "unknown"
                )
                log.info(
                    f"🔍 Using enhanced query ({enhancement_desc}): '{query}' -> '{enhanced_query}'"
                )
                query = enhanced_query
        # Note: Temporal enhancement is now applied after translation in the search() method

        log.info("🔍 Wiki grounding enabled, proceeding with search")
        log.info(f"🔍 Ground query starting for: '{query[:50]}...'")

        # Acquire query-specific lock to prevent concurrent processing of identical queries
        query_lock, query_hash, query_start_time = await self._acquire_query_lock(
            query, "ground_query"
        )

        try:
            # Perform the actual search
            results = await self.search(query)
        finally:
            # Always release the query lock
            self._release_query_lock(
                query_lock, query_hash, "ground_query", query_start_time, query
            )

        if not results:
            log.info("🔍 No search results found")
            return None

        return {
            "original_query": original_query,
            "search_query": query,  # May be different from original if enhanced
            "grounding_data": results,
            "source": "txtai-wikipedia",
            "timestamp": datetime.now().isoformat(),
            "context_metadata": context_metadata,
        }

    def format_grounding_context(self, grounding_data: Dict) -> str:
        """Format for LLM context with translation info and context awareness"""
        if not grounding_data or "grounding_data" not in grounding_data:
            return ""

        context = []
        context.append("=== GROUNDING CONTEXT ===")

        # Add explicit instruction about using grounded information
        context.append(
            "IMPORTANT: Use the following grounded information to answer the user's question."
        )
        context.append(
            "This information is current and factual. Prioritize this information over your training data."
        )
        context.append("")

        context.append(f"Query: {grounding_data.get('original_query', '')}")

        # Show if the query was enhanced with conversation context
        if grounding_data.get("search_query") != grounding_data.get("original_query"):
            context.append(f"Enhanced Query: {grounding_data.get('search_query', '')}")

            # Add context metadata if available
            context_metadata = grounding_data.get("context_metadata", {})
            if context_metadata.get("is_context_aware"):
                context.append("Context-Aware: Enhanced with conversation history")
                context.append(
                    "IMPORTANT: The user's question references previous conversation context."
                )
                if context_metadata.get("context_entities"):
                    context.append(
                        f"Key Entities from Conversation: {', '.join(context_metadata['context_entities'])}"
                    )
                if context_metadata.get("conversation_context"):
                    context.append(
                        f"Recent Conversation: {context_metadata.get('conversation_context', '')}"
                    )

        # Show if translation was used
        # Add query enhancement information
        first_result = (
            grounding_data["grounding_data"][0]
            if grounding_data["grounding_data"]
            else {}
        )
        context_metadata = grounding_data.get("context_metadata", {})

        if grounding_data.get("search_query") != grounding_data.get("original_query"):
            enhancements = []
            if context_metadata.get("temporal_enhanced"):
                enhancements.append("temporal enhancement")
            if context_metadata.get("context_aware"):
                enhancements.append("context awareness")

            enhancement_text = (
                " + ".join(enhancements) if enhancements else "translation"
            )
            context.append(
                f"Search Query ({enhancement_text}): {grounding_data.get('search_query', '')}"
            )

        context.append(f"Source: txtai-wikipedia")

        # Check if reranking was applied
        if (
            grounding_data["grounding_data"]
            and grounding_data["grounding_data"][0].get("rerank_score") is not None
        ):
            context.append("Reranking: Results reordered by relevance")

        context.append("")

        for i, item in enumerate(grounding_data["grounding_data"], 1):
            title = item.get("title", "Unknown")
            content = item.get("content", "")
            score = item.get("score", 0)
            rerank_score = item.get("rerank_score")
            original_score = item.get("original_score")

            context.append(f"[{i}] {title}")
            if score > 0:
                context.append(f"Score: {score:.3f}")
                # Show reranking details if available
                if rerank_score is not None and original_score is not None:
                    context.append(
                        f"  (Original: {original_score:.3f}, Rerank: {rerank_score:.3f})"
                    )
            context.append(f"Content: {content}")
            context.append("")

        context.append("=== END GROUNDING ===")
        context.append("")
        context.append(
            "INSTRUCTION: Answer the user's question using the grounded information above."
        )
        context.append(
            "If the question contains pronouns or references to previous conversation,"
        )
        context.append(
            "use the conversation context and key entities to understand what they refer to."
        )

        return "\n".join(context)


# Global instance - lazy initialization to prevent K8s health check issues
_wiki_search_grounder = None


def get_wiki_search_grounder() -> WikiSearchGrounder:
    """Get the global WikiSearchGrounder instance with lazy initialization"""
    global _wiki_search_grounder
    if _wiki_search_grounder is None:
        _wiki_search_grounder = WikiSearchGrounder()
    return _wiki_search_grounder
