"""
Pure txtai-wikipedia semantic search - absolutely generic
"""

import logging
import re
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

    def _should_ground_query(self, query: str) -> bool:
        """
        Intelligent determination of whether a query needs factual/recent information.
        Supports both English and French queries.

        Returns True for queries that likely need factual information,
        False for creative/personal tasks that don't benefit from grounding.
        """
        query_lower = query.lower().strip()

        # Skip very short queries
        if len(query_lower) < 10:
            return False

        # English patterns that DON'T need grounding (creative/personal tasks)
        creative_patterns_en = [
            # Greeting/message creation
            r"\b(write|create|make|generate|compose|draft)\s+(a\s+)?(greeting|message|email|letter|note|memo|invitation)",
            r"\b(help\s+me\s+)?(write|create|make|compose)\s+(something|anything)",
            r"\bgreet(ing)?\s+(message|email|text)",
            # Creative content
            r"\b(tell\s+me\s+a\s+)?(joke|story|riddle|poem)",
            r"\b(write|create|make|generate)\s+(a\s+)?(story|poem|song|lyrics|script|dialogue)",
            r"\bcreative\s+(writing|content|ideas)",
            r"\bbrainstorm(ing)?",
            # Personal/opinion requests
            r"\bgive\s+me\s+(your\s+)?(opinion|thoughts|advice|suggestions)",
            r"\bwhat\s+(do\s+you\s+)?(think|feel|believe|recommend)",
            r"\byour\s+(opinion|thoughts|recommendation|suggestion)",
            # Task/instructional requests
            r"\b(help\s+me\s+)?(do|complete|finish|solve)",
            r"\bhow\s+(do\s+i\s+|can\s+i\s+|to\s+)?(make|create|build|fix|repair)",
            r"\bstep\s+by\s+step",
            r"\btutorial",
            r"\bguide\s+me",
            # Code/technical creation
            r"\b(write|create|generate|build)\s+(code|program|script|function|class)",
            r"\bhelp\s+(me\s+)?(code|program|debug)",
            # Explanations of concepts (without "latest" or "current")
            r"\bexplain\s+(?!.*\b(latest|current|recent|today|now|2024|2025)\b)",
            r"\btell\s+me\s+about\s+(?!.*\b(latest|current|recent|today|now|2024|2025)\b)",
            # Role playing
            r"\bact\s+(like|as)\s+",
            r"\bpretend\s+(you\s+are|to\s+be)",
            r"\brole\s*play",
            # Format/style requests
            r"\bformat\s+(this|it|that)",
            r"\brewrite\s+(this|it|that)",
            r"\bsummariz(e|ing)\s+(this|it|that)",
            r"\btranslate\s+(this|it|that)",
        ]

        # French patterns that DON'T need grounding
        creative_patterns_fr = [
            # Greeting/message creation
            r"\b(écri(s|vez)|créer?|fair(e|es?)|générer?|composer|rédiger)\s+(un\s+)?(message|email|lettre|note|mémo|invitation)",
            r"\b(aide?z?(-moi)?\s+)?(écri(s|vez)|créer?|composer)\s+(quelque\s+chose|quelque\s+chose)",
            r"\bmessage\s+(de\s+)?(salutation|accueil)",
            # Creative content
            r"\b(racont(e|ez)(-moi)?\s+)?(une\s+)?(blague|histoire|devinette|poème)",
            r"\b(écri(s|vez)|créer?|fair(e|es?)|générer?)\s+(un(e)?\s+)?(histoire|poème|chanson|paroles|script|dialogue)",
            r"\bcréati(f|ve|on)\s+(littéraire|contenu|idées)",
            r"\bremue(-|\s+)méninges",
            # Personal/opinion requests
            r"\bdonne(z)?(-moi)?\s+(votre\s+|ton\s+)?(avis|opinion|conseil|suggestion)",
            r"\bque\s+(pense(z|s)(-vous|-tu)|ressent(ez|s)(-vous|-tu)|croi(ez|s)(-vous|-tu)|recommande(z|s)(-vous|-tu))",
            r"\b(votre|ton)\s+(avis|opinion|recommandation|suggestion)",
            # Task/instructional requests
            r"\b(aide(z)?(-moi)?\s+)?(fair(e|es?)|terminer|finir|résoudre)",
            r"\bcomment\s+(puis(-je)|faire|créer|construire|réparer)",
            r"\bétape\s+par\s+étape",
            r"\btutoriel",
            r"\bguide(z)?(-moi)",
            # Code/technical creation
            r"\b(écri(s|vez)|créer?|générer?|construire)\s+(code|programme|script|fonction|classe)",
            r"\baide(z)?(-moi)?\s+(coder|programmer|déboguer)",
            # Explanations of concepts (without "dernier/actuel/récent")
            r"\bexpliqu(e|ez)(-moi)?\s+(?!.*(dernier|actuel|récent|aujourd\'hui|maintenant|2024|2025))",
            r"\bparle(z)?(-moi)?\s+de\s+(?!.*(dernier|actuel|récent|aujourd\'hui|maintenant|2024|2025))",
            # Role playing
            r"\b(agis|agisse(z)?|comporte(-toi|-vous))\s+(comme|en\s+tant\s+que)",
            r"\bfais\s+(semblant|comme\s+si)",
            r"\bjeu\s+de\s+rôle",
            # Format/style requests
            r"\bformat(e|ez)\s+(ceci|cela|ça)",
            r"\brééc(ris|rive(z)?)\s+(ceci|cela|ça)",
            r"\brésume(z)?\s+(ceci|cela|ça)",
            r"\btradui(s|se(z)?)\s+(ceci|cela|ça)",
        ]

        # Check creative patterns first (these should NOT be grounded)
        for pattern in creative_patterns_en + creative_patterns_fr:
            if re.search(pattern, query_lower):
                log.info(
                    f"🔍 Query matches creative pattern, skipping grounding: {pattern}"
                )
                return False

        # English patterns that SHOULD be grounded (factual/recent information needs)
        factual_patterns_en = [
            # Current events / news
            r"\b(latest|current|recent|new|today|this\s+(week|month|year)|2024|2025)",
            r"\b(what\'s\s+happening|news|events|updates)",
            r"\bhappening\s+(now|today|recently)",
            # Factual queries
            r"\b(when\s+(did|was|were)|what\s+(happened|is\s+the|was\s+the)|where\s+(is|was|are|were)|who\s+(is|was|are|were))",
            r"\b(how\s+many|how\s+much|statistics|data|facts|information\s+about)",
            r"\b(population|temperature|weather|price|cost|rate)",
            # Research/lookup queries
            r"\b(find\s+(information|data)|research|look\s+up|search\s+for)",
            r"\b(definition\s+of|meaning\s+of|what\s+(does|is)|explain\s+what)",
            # Specific entities (likely need current info)
            r"\b(company|organization|government|politics|economy|market)",
            r"\b(celebrity|politician|scientist|author|artist)",
            # Location/geography
            r"\b(country|city|state|province|region|capital|location)",
            # Technology/science (likely evolving)
            r"\b(technology|software|AI|artificial\s+intelligence|machine\s+learning|research)",
            # Comparative queries
            r"\b(better|worse|best|worst|compare|comparison|versus|vs\.?)",
            r"\b(difference\s+between|similarities\s+between)",
        ]

        # French patterns that SHOULD be grounded
        factual_patterns_fr = [
            # Current events / news
            r"\b(dernier|dernière|actuel|récent|récente|nouveau|nouvelle|aujourd\'hui|cette\s+(semaine|mois|année)|2024|2025)",
            r"\b(qu\'est(-ce\s+qui|ce\s+que)\s+se\s+passe|nouvelles|événements|actualités|mises\s+à\s+jour)",
            r"\bse\s+passe\s+(maintenant|aujourd\'hui|récemment)",
            # Factual queries
            r"\b(quand\s+(a|est|était|sont|étaient)|qu\'est(-ce\s+qui|ce\s+que)\s+(s\'est\s+passé|est|était)|où\s+(est|était|sont|étaient)|qui\s+(est|était|sont|étaient))",
            r"\bquand\s+.*?\s+(a|ont)\s+(commencé|débuté)",
            r"\bquand\s+.*commencé",
            r"\b(combien\s+(de|d\')|statistiques|données|faits|informations\s+sur)",
            r"\b(population|température|météo|prix|coût|taux)",
            # Research/lookup queries
            r"\b(trouver?\s+(informations?|données)|recherch(e|er)|chercher)",
            r"\b(définition\s+(de|d\')|signification\s+(de|d\')|qu\'est(-ce\s+que|ce\s+qui)|expliqu(e|ez)\s+ce\s+que)",
            # Specific entities
            r"\b(entreprise|organisation|gouvernement|politique|économie|marché)",
            r"\b(célébrité|politicien|scientifique|auteur|artiste)",
            # Location/geography
            r"\b(pays|ville|état|province|région|capitale|lieu|endroit)",
            # Technology/science
            r"\b(technologie|logiciel|IA|intelligence\s+artificielle|apprentissage\s+(automatique|machine)|recherche)",
            # Comparative queries
            r"\b(meilleur|pire|mieux|comparer|comparaison|contre|vs\.?)",
            r"\b(différence\s+entre|similitudes\s+entre)",
        ]

        # Check factual patterns
        for pattern in factual_patterns_en + factual_patterns_fr:
            if re.search(pattern, query_lower):
                log.info(f"🔍 Query matches factual pattern, should ground: {pattern}")
                return True

        # Default: if no clear pattern matches, lean towards NOT grounding
        # This prevents over-grounding and respects user intent for creative tasks
        log.info("🔍 Query doesn't match clear factual patterns, skipping grounding")
        return False

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
        """Main grounding method with intelligent query filtering"""

        # Basic length check
        if len(query.strip()) < 3:
            log.info("🔍 Query too short, skipping grounding")
            return None

        # Intelligent filtering: check if this query actually needs factual information
        if not self._should_ground_query(query):
            log.info(
                "🔍 Query doesn't need factual grounding based on content analysis"
            )
            return None

        log.info(
            "🔍 Query determined to need factual grounding, proceeding with search"
        )
        results = await self.search(query)

        if not results:
            log.info("🔍 No search results found")
            return None

        return {
            "original_query": query,
            "grounding_data": results,
            "source": "txtai-wikipedia",
            "timestamp": datetime.now().isoformat(),
        }

    async def ground_query_always(
        self, query: str, request=None, user=None
    ) -> Optional[Dict]:
        """Ground query without intelligent filtering (always mode)"""

        # Basic length check only
        if len(query.strip()) < 3:
            log.info("🔍 Query too short, skipping grounding")
            return None

        log.info("🔍 Always mode: grounding without content analysis")
        results = await self.search(query)

        if not results:
            log.info("🔍 No search results found")
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
