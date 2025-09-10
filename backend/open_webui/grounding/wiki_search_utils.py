"""
Pure txtai-wikipedia semantic search - absolutely generic
"""

import importlib.util
import logging
import re
from typing import Dict, List, Optional
from datetime import datetime

from .context_analysis import analyze_conversation_context

log = logging.getLogger(__name__)


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


def _check_optional_dependency(module_name: str) -> bool:
    """Check if an optional dependency is available"""
    return importlib.util.find_spec(module_name) is not None


class WikiSearchGrounder:
    """Pure txtai-wikipedia implementation with lazy loading"""

    def __init__(self):
        self.max_content_length = 4000
        self.max_search_results = 5
        self.embeddings = None
        self.translator = None
        self.model_loaded = False
        self.translation_loaded = False
        self._initialized = False

    async def initialize(self) -> bool:
        """Initialize models (call once before using search methods)"""
        if self._initialized:
            return True

        success = True

        # Initialize txtai model
        if not self._load_txtai_model():
            success = False

        # Initialize translation model (optional)
        self._load_translation_model()

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
        """Pure txtai search with translation support"""
        # Ensure models are initialized
        if not await self.ensure_initialized():
            return []

        try:
            # Translate query to English for better search results
            original_query = query
            search_query = self._translate_to_english(query)

            # Use basic search with translated query
            results = self.embeddings.search(search_query)

            # Format results and apply score threshold
            formatted = []
            for result in results[: self.max_search_results * 2]:  # Get more to filter
                if isinstance(result, dict):
                    score = result.get("score", 0)

                    # Only include high-quality results (score > 0.8)
                    if score > 0.8:
                        title = result.get("id", "")
                        content = result.get("text", "")

                        if len(content) > self.max_content_length:
                            content = content[: self.max_content_length] + "..."

                        formatted.append(
                            {
                                "title": title,
                                "content": content,
                                "score": score,
                                "url": f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}",
                                "source": "txtai-wikipedia",
                                "original_query": original_query,
                                "search_query": search_query,
                            }
                        )

                        # Stop when we have enough high-quality results
                        if len(formatted) >= self.max_search_results:
                            break

            return formatted

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
            is_context_aware, enhanced_query, context_metadata = (
                analyze_conversation_context(query, messages)
            )
            if is_context_aware:
                log.info(
                    f"🔍 Using context-aware query: '{query}' -> '{enhanced_query}'"
                )
                query = enhanced_query

        log.info("🔍 Wiki grounding enabled, proceeding with search")
        results = await self.search(query)

        if not results:
            log.info("🔍 No search results found")
            return None

        return {
            "original_query": original_query,
            "search_query": query,  # May be different from original if context-enhanced
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
        first_result = (
            grounding_data["grounding_data"][0]
            if grounding_data["grounding_data"]
            else {}
        )
        if first_result.get("search_query") != first_result.get("original_query"):
            context.append(
                f"Search Query (translated): {first_result.get('search_query', '')}"
            )

        context.append(f"Source: txtai-wikipedia")
        context.append("")

        for i, item in enumerate(grounding_data["grounding_data"], 1):
            title = item.get("title", "Unknown")
            content = item.get("content", "")
            score = item.get("score", 0)

            context.append(f"[{i}] {title}")
            if score > 0:
                context.append(f"Score: {score:.3f}")
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


# Global instance
wiki_search_grounder = WikiSearchGrounder()
