"""
Pure txtai-wikipedia semantic search - absolutely generic
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime

log = logging.getLogger(__name__)

try:
    from txtai.embeddings import Embeddings

    TXTAI_AVAILABLE = True
except ImportError:
    TXTAI_AVAILABLE = False

try:
    from transformers import pipeline

    TRANSLATION_AVAILABLE = True
except ImportError:
    TRANSLATION_AVAILABLE = False


class WebSearchGrounder:
    """Pure txtai-wikipedia implementation"""

    def __init__(self):
        self.max_content_length = 4000
        self.max_search_results = 5
        self.embeddings = None
        self.translator = None
        self.model_loaded = False
        self.translation_loaded = False

    def _initialize_translation(self):
        """Initialize HuggingFace translation pipeline"""
        if self.translation_loaded:
            return True

        if not TRANSLATION_AVAILABLE:
            log.warning(
                "transformers not available for translation. Install with: pip install transformers>=4.46.0"
            )
            return False

        try:
            from transformers import pipeline

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
        if not self.translation_loaded and not self._initialize_translation():
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

    def _initialize_txtai(self):
        """Load txtai-wikipedia from HuggingFace Hub"""
        if self.model_loaded:
            return True

        if not TXTAI_AVAILABLE:
            log.error(
                "txtai is not available. Please install with: pip install txtai[graph]>=8.6.0"
            )
            return False

        try:
            from txtai.embeddings import Embeddings

            log.info("Loading txtai-wikipedia model from HuggingFace Hub...")
            self.embeddings = Embeddings()
            self.embeddings.load(
                provider="huggingface-hub", container="neuml/txtai-wikipedia"
            )
            self.model_loaded = True
            log.info("txtai-wikipedia model loaded successfully")
            return True
        except Exception as e:
            log.error(f"Failed to load txtai-wikipedia: {e}")
            return False

    async def search(self, query: str) -> List[Dict]:
        """Pure txtai search with translation support"""
        if not self.model_loaded and not self._initialize_txtai():
            return []

        # Initialize translation if available
        self._initialize_translation()

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

    async def ground_query(self, query: str, request=None, user=None) -> Optional[Dict]:
        """Main grounding method"""
        if len(query.strip()) < 3:
            return None

        results = await self.search(query)

        if not results:
            return None

        return {
            "original_query": query,
            "grounding_data": results,
            "source": "txtai-wikipedia",
            "timestamp": datetime.now().isoformat(),
        }

    def format_grounding_context(self, grounding_data: Dict) -> str:
        """Format for LLM context with translation info"""
        if not grounding_data or "grounding_data" not in grounding_data:
            return ""

        context = []
        context.append("=== GROUNDING CONTEXT ===")
        context.append(f"Query: {grounding_data.get('original_query', '')}")

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
        return "\n".join(context)


# Global instance
web_search_grounder = WebSearchGrounder()


async def search_web(query: str, request=None, user=None) -> Optional[Dict]:
    """Main entry point"""
    return await web_search_grounder.ground_query(query, request, user)


async def web_search(query: str, request=None, user=None) -> Optional[Dict]:
    """Legacy support"""
    return await search_web(query, request, user)
