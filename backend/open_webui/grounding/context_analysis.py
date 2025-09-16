"""
Context-Aware Query Analysis for Wiki Grounding

This module provides intelligent analysis of conversation context to generate
better search queries for wiki grounding, addressing the issue where follow-up
questions and conversation context are not properly considered.
"""

import re
import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime

from open_webui.env import SRC_LOG_LEVELS

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["GROUNDING"])


class ConversationContextAnalyzer:
    """
    Analyzes conversation history to generate context-aware search queries
    for wiki grounding, solving the issue of poor follow-up question handling.
    """

    def __init__(self):
        self.max_context_messages = 10  # How many previous messages to consider
        self.max_context_length = 2000  # Max characters for context
        self.current_year = datetime.now().year

    def extract_conversation_context(self, messages: List[Dict]) -> str:
        """
        Extract relevant conversation context from message history.

        Args:
            messages: List of conversation messages in chronological order

        Returns:
            Condensed conversation context string
        """
        if not messages or len(messages) < 2:
            return ""

        # Get recent messages within limits
        recent_messages = messages[-self.max_context_messages :]

        context_parts = []
        total_length = 0

        for message in recent_messages[:-1]:  # Exclude the current message
            if message.get("role") == "user":
                content = message.get("content", "").strip()
                if content and total_length + len(content) < self.max_context_length:
                    context_parts.append(f"User: {content}")
                    total_length += len(content)
            elif message.get("role") == "assistant":
                content = message.get("content", "").strip()
                if content:
                    # Take first 200 chars of assistant response for context
                    summary = content[:200] + "..." if len(content) > 200 else content
                    if total_length + len(summary) < self.max_context_length:
                        context_parts.append(f"Assistant: {summary}")
                        total_length += len(summary)

        return "\n".join(context_parts)

    def _has_pronouns_without_antecedents(self, query: str) -> bool:
        """
        Check if query contains pronouns that likely refer to context.
        Simplified to be language-agnostic.

        Args:
            query: Query text to analyze

        Returns:
            True if pronouns without clear antecedents are found
        """
        query_lower = query.lower()

        # Common pronouns across languages that often refer to previous context
        common_pronouns = [
            "he ",
            "she ",
            "it ",
            "they ",
            "him ",
            "her ",
            "them ",
            "his ",
            "hers ",
            "its ",
            "their ",
            "il ",
            "elle ",
            "ils ",
            "elles ",
            "lui ",
            "eux ",
            "son ",
            "sa ",
            "ses ",
            "leur ",
            "leurs ",
        ]

        return any(pronoun in f" {query_lower} " for pronoun in common_pronouns)

    def _has_demonstratives(self, query: str) -> bool:
        """
        Check if query contains demonstrative words referring to context.
        Simplified to be language-agnostic.

        Args:
            query: Query text to analyze

        Returns:
            True if demonstratives are found
        """
        query_lower = query.lower()

        # Common demonstratives across languages
        common_demonstratives = [
            "this ",
            "that ",
            "these ",
            "those ",
            "ceci ",
            "cela ",
            "ça ",
            "ces ",
            "ceux ",
        ]

        return any(demo in f" {query_lower} " for demo in common_demonstratives)

    def _has_continuation_words(self, query: str) -> bool:
        """
        Check if query contains words that suggest continuation of previous topic.
        Simplified to be language-agnostic.

        Args:
            query: Query text to analyze

        Returns:
            True if continuation indicators are found
        """
        query_lower = query.lower()

        # Common continuation indicators across languages
        common_indicators = [
            "also",
            "too",
            "as well",
            "furthermore",
            "moreover",
            "additionally",
            "more about",
            "tell me more",
            "elaborate",
            "expand",
            "aussi",
            "également",
            "de plus",
            "en outre",
            "de surcroît",
            "plus sur",
            "dis-moi plus",
            "élabore",
            "développe",
        ]

        return any(indicator in query_lower for indicator in common_indicators)

    def _has_question_about_context(self, query: str) -> bool:
        """
        Check if query is asking a question that likely refers to context.
        Simplified to be language-agnostic with basic pattern matching.

        Args:
            query: Query text to analyze

        Returns:
            True if context-referencing question patterns are found
        """
        query_lower = query.lower()

        # Look for question words followed by pronouns or demonstratives - language agnostic patterns
        question_patterns = [
            # English patterns
            r"\b(what|who|when|where|why|how)\s+(is|was|are|were|did|does|do)\s+(he|she|it|they|this|that)\b",
            r"\b(what|why|how)\s+(about|regarding|concerning)\s+(this|that|it|them)\b",
            r"\bwhat\s+(triggered|caused|led|made)\b",
            r"\bhow\s+(did|does)\s+(he|she|it|they)\b",
            # French patterns
            r"\b(qui|que|quoi|quand|où|pourquoi|comment)\s+(est|était|sont|étaient|a|ont)\s+(il|elle|ils|elles|ça|cela)\b",
            r"\b(quoi|pourquoi|comment)\s+(sur|concernant)\s+(ceci|cela|ça)\b",
            r"\bqu\'est-ce\s+qui\s+(a\s+(déclenché|causé|mené))\b",
        ]

        return any(re.search(pattern, query_lower) for pattern in question_patterns)

    def _enhance_query_with_temporal_context(self, query: str) -> str:
        """
        Enhance ALL queries with temporal context to get more recent information.

        This applies temporal enhancement to EVERY query without exception.
        The approach adds the current year naturally to help search algorithms
        prioritize recent information and understand temporal context.

        Args:
            query: Original query

        Returns:
            Enhanced query with temporal context
        """
        enhanced_query = query

        # Universal Strategy: Always add current year if no year is mentioned
        # This helps all search algorithms understand temporal context for ANY query
        if not re.search(r"\b(19|20)\d{2}\b", query):
            enhanced_query = f"{enhanced_query} {self.current_year}"

        log.info(
            f"🕒 Enhanced query with temporal context: '{query}' -> '{enhanced_query}'"
        )
        return enhanced_query

        return "\n".join(context_parts[-5:])  # Last 5 context entries

    def is_follow_up_question(
        self, current_query: str, conversation_context: str
    ) -> bool:
        """
        Determine if the current query is a follow-up question that needs context.
        Uses dynamic analysis instead of hardcoded patterns.

        Args:
            current_query: The current user query
            conversation_context: Previous conversation context

        Returns:
            True if this appears to be a follow-up question
        """
        if not conversation_context:
            return False

        # Check multiple indicators dynamically
        indicators = [
            self._has_pronouns_without_antecedents(current_query),
            self._has_demonstratives(current_query),
            self._has_continuation_words(current_query),
            self._has_question_about_context(current_query),
        ]

        # If any indicator is positive, it's likely a follow-up
        is_followup = any(indicators)

        if is_followup:
            log.info(
                f"🔍 Detected follow-up question with indicators: pronouns={indicators[0]}, demonstratives={indicators[1]}, continuation={indicators[2]}, context_question={indicators[3]}"
            )

        return is_followup

    def extract_key_entities_from_context(self, context: str) -> List[str]:
        """
        Extract key entities (names, places, concepts) from conversation context.

        Args:
            context: Conversation context string

        Returns:
            List of key entities/topics, prioritized by likely importance
        """
        entities = []

        # Clean up the context text - remove user/assistant labels and extra whitespace
        clean_context = context

        # Remove user/assistant prefixes but preserve sentence boundaries
        clean_context = re.sub(
            r"\b(User|Assistant|Utilisateur):\s*", ". ", clean_context
        )

        # Remove extra whitespace and line breaks
        clean_context = " ".join(clean_context.split())

        # Clean up multiple periods
        clean_context = re.sub(r"\.{2,}", ".", clean_context)

        # Dynamic entity extraction using different patterns
        entity_patterns = [
            # Multi-word proper names (likely person names, places, organizations)
            # Updated pattern to handle names like "LeBron James", "McDonald's", "O'Connor"
            (r"\b[A-Z][a-zA-Z]*(?:\s+[A-Z][a-zA-Z]*)+\b", "multi_word"),
            # Single capitalized words that are likely important
            (r"\b[A-Z][a-zA-Z]{2,}\b", "single_word"),
            # Quoted terms (explicit mentions)
            (r'"([^"]+)"', "quoted"),
            (r"'([^']+)'", "quoted"),
            # Acronyms and abbreviations
            (r"\b[A-Z]{2,}\b", "acronym"),
        ]

        # Extract entities by pattern type
        entity_candidates = []

        for pattern, pattern_type in entity_patterns:
            matches = re.findall(pattern, clean_context)
            for match in matches:
                if isinstance(match, tuple):
                    match = match[0] if match[0] else match[1] if len(match) > 1 else ""
                if match:
                    entity_candidates.append(
                        {
                            "text": match,
                            "type": pattern_type,
                            "word_count": len(match.split()),
                            "position": clean_context.find(match),
                        }
                    )

        # Filter out obvious non-entities using dynamic analysis
        def is_likely_common_word(word: str) -> bool:
            """Check if a word is likely a common word rather than an entity."""
            word_lower = word.lower()

            # Very short words are likely not entities
            if len(word) < 3:
                return True

            # Words that are all lowercase in the original context are likely common words
            # (unless they're at start of sentence)
            if word_lower == word and not word[0].isupper():
                return True

            # Dynamic function word detection based on characteristics
            # Instead of hardcoded lists, use linguistic patterns
            if len(word) <= 3:
                # Very short words are often function words
                # Additional heuristics: all lowercase, common patterns
                if word_lower == word and (
                    word_lower.endswith("e")
                    or word_lower.endswith("s")
                    or len(word_lower) <= 2
                    or any(
                        char in word_lower for char in ["th", "an", "ar", "ou", "es"]
                    )
                ):
                    return True

            return False

        # Score and prioritize entities dynamically
        scored_entities = []

        for candidate in entity_candidates:
            text = candidate["text"]

            # Skip common words using dynamic analysis
            if is_likely_common_word(text):
                continue

            # Skip very short entities
            if len(text) < 3:
                continue

            # Calculate a dynamic score based on multiple factors
            score = 0

            # Multi-word entities get higher scores (likely person names, places, orgs)
            if candidate["word_count"] >= 2:
                score += 10

                # Smart person name detection vs organizations/places
                words = text.split()
                if len(words) >= 2:
                    # Check if all words start with capital and are primarily alphabetic
                    is_capitalized_entity = all(
                        word[0].isupper() and word.replace("'", "").isalpha()
                        for word in words
                        if word
                    )

                    if is_capitalized_entity:
                        # All capitalized entities get same base score
                        # Let frequency and context determine importance instead of hardcoded lists
                        if len(words) == 2:
                            score += 15  # Two-word entities (likely important)
                        elif len(words) == 3:
                            score += 18  # Three-word entities
                        else:
                            score += 10  # Other multi-word entities
                    else:
                        # Non-alphabetic multi-word entity
                        score += 5

            # Single words get lower base score
            elif candidate["word_count"] == 1:
                score += 3

                # Check if this single word is part of a person's name mentioned elsewhere
                # Look for patterns like "John Smith" where we're scoring "John" or "Smith"
                full_name_pattern = rf"\b{re.escape(text)}\s+[A-Z][a-z]+\b|\b[A-Z][a-z]+\s+{re.escape(text)}\b"
                if re.search(full_name_pattern, clean_context):
                    score += 15  # High bonus if it's part of a full name

                # Bonus for single words that appear with possessive form (suggests importance)
                context_around = clean_context[
                    max(0, candidate["position"] - 50) : candidate["position"]
                    + len(text)
                    + 50
                ]
                if re.search(rf"\b{re.escape(text)}'s\b", context_around):
                    score += 4

            # Quoted entities are explicitly mentioned, give bonus
            if candidate["type"] == "quoted":
                score += 8

            # Acronyms in all caps might be important organizations
            if candidate["type"] == "acronym":
                score += 2

            # Earlier mentions might be more important (recency bias)
            if candidate["position"] < len(clean_context) * 0.3:  # First 30% of text
                score += 2

            # Avoid duplicate entries
            if not any(
                existing["text"].lower() == text.lower() for existing in scored_entities
            ):
                scored_entities.append(
                    {"text": text, "score": score, "type": candidate["type"]}
                )

        # Sort by score (descending) and return top entities
        scored_entities.sort(key=lambda x: x["score"], reverse=True)

        # Return the text of top-scored entities
        return [entity["text"] for entity in scored_entities[:5]]

    def generate_context_aware_query(
        self, current_query: str, conversation_context: str
    ) -> str:
        """
        Generate an enhanced search query that incorporates conversation context.

        Args:
            current_query: The current user query
            conversation_context: Previous conversation context

        Returns:
            Enhanced search query with context
        """
        if not self.is_follow_up_question(current_query, conversation_context):
            return current_query

        log.info("🔍 Generating context-aware query for follow-up question")

        # Extract key entities from context
        context_entities = self.extract_key_entities_from_context(conversation_context)

        # Debug: Log what entities were extracted
        log.info(f"🔍 Extracted context entities: {context_entities}")

        if not context_entities:
            return current_query

        # Build enhanced query
        enhanced_query = current_query

        # Pattern-based pronoun replacement - detect and replace pronouns contextually
        query_lower = current_query.lower()
        pronoun_replaced = False

        if context_entities:
            # Use regex patterns to find pronouns in context, rather than hardcoded lists
            pronoun_patterns = [
                (r"\b(he|him|his)\b", context_entities[0], "male"),
                (r"\b(she|her)\b", context_entities[0], "female"),
                (r"\b(it|they|them)\b", context_entities[0], "neutral"),
                (r"\b(il|lui)\b", context_entities[0], "french_male"),
                (r"\b(elle)\b", context_entities[0], "french_female"),
            ]

            for pattern, replacement, pronoun_type in pronoun_patterns:
                match = re.search(pattern, query_lower)
                if match:
                    matched_pronoun = match.group(1)

                    # Handle possessive forms
                    if matched_pronoun in ["his", "her"]:
                        enhanced_query = re.sub(
                            f"\\b{matched_pronoun}\\b",
                            f"{replacement}'s",
                            enhanced_query,
                            flags=re.IGNORECASE,
                        )
                    else:
                        enhanced_query = re.sub(
                            f"\\b{matched_pronoun}\\b",
                            replacement,
                            enhanced_query,
                            flags=re.IGNORECASE,
                        )

                    pronoun_replaced = True
                    log.info(
                        f"🔍 Replaced pronoun '{matched_pronoun}' with '{replacement}'"
                    )
                    break

        # If no pronoun was replaced but query is still vague, prepend main entity
        if not pronoun_replaced and len(current_query.split()) < 6:
            main_entity = context_entities[0] if context_entities else ""
            if main_entity and main_entity.lower() not in enhanced_query.lower():
                enhanced_query = f"{main_entity} {enhanced_query}"

        # For ambiguous names, add any additional context entities found in conversation
        if context_entities and len(context_entities) >= 2:
            main_entity = context_entities[0]

            # Simply use additional context entities that were extracted from conversation
            # without any hardcoded filtering - let the entity extraction determine what's relevant
            additional_context = context_entities[
                1:3
            ]  # Take up to 2 additional context entities

            if additional_context and main_entity and len(main_entity.split()) >= 2:
                # Only add context that's not already in the query
                new_context = []
                for ctx in additional_context:
                    if ctx.lower() not in enhanced_query.lower():
                        new_context.append(ctx)

                if new_context:
                    context_str = " ".join(new_context)
                    enhanced_query = f"{context_str} {enhanced_query}"
                    log.info(
                        f"🔍 Added conversation context for disambiguation: '{context_str}'"
                    )

        # Clean up the query - remove any duplicate spaces and trailing issues
        enhanced_query = " ".join(enhanced_query.split())

        log.info(f"🔍 Enhanced query: '{current_query}' -> '{enhanced_query}'")
        return enhanced_query

    def should_use_context_aware_search(
        self, current_query: str, messages: List[Dict]
    ) -> Tuple[bool, str]:
        """
        Determine if context-aware search should be used and return the enhanced query.
        This now includes both conversation context awareness AND universal temporal enhancement.

        Args:
            current_query: The current user query
            messages: Full conversation message history

        Returns:
            Tuple of (should_use_enhancement, enhanced_query)
        """
        enhanced_query = current_query
        is_enhanced = False

        # Step 1: Apply temporal enhancement (this is now applied to ALL queries)
        temporal_enhanced_query = self._enhance_query_with_temporal_context(
            current_query
        )
        if temporal_enhanced_query != current_query:
            enhanced_query = temporal_enhanced_query
            is_enhanced = True
            log.info(f"🕒 Applied universal temporal enhancement to query")

        # Step 2: Apply conversation context enhancement if needed
        if len(messages) >= 2:
            conversation_context = self.extract_conversation_context(messages)

            if conversation_context and self.is_follow_up_question(
                current_query, conversation_context
            ):
                # Apply context-aware enhancement to the temporally enhanced query
                context_enhanced_query = self.generate_context_aware_query(
                    enhanced_query, conversation_context
                )
                if context_enhanced_query != enhanced_query:
                    enhanced_query = context_enhanced_query
                    is_enhanced = True
                    log.info(f"🔍 Applied conversation context enhancement to query")

        return is_enhanced, enhanced_query


# Global instance
context_analyzer = ConversationContextAnalyzer()


def analyze_conversation_context(
    current_query: str, messages: List[Dict]
) -> Tuple[bool, str, Dict]:
    """
    Analyze conversation context and return enhanced query if needed.
    Now includes temporal enhancement for queries that need current information.

    Args:
        current_query: The current user query
        messages: List of conversation messages

    Returns:
        Tuple of (is_enhanced, enhanced_query, analysis_metadata)
    """
    is_enhanced, enhanced_query = context_analyzer.should_use_context_aware_search(
        current_query, messages
    )

    # Determine what type of enhancement was applied
    temporal_enhanced = True  # Always true since we always apply temporal enhancement
    context_aware = False

    if len(messages) >= 2:
        conversation_context = context_analyzer.extract_conversation_context(messages)
        context_aware = context_analyzer.is_follow_up_question(
            current_query, conversation_context
        )

    metadata = {
        "original_query": current_query,
        "enhanced_query": enhanced_query,
        "is_enhanced": is_enhanced,
        "temporal_enhanced": temporal_enhanced,
        "context_aware": context_aware,
        "context_messages_count": len(messages) - 1,  # Exclude current message
        "timestamp": datetime.now().isoformat(),
        "current_year": context_analyzer.current_year,
    }

    if context_aware and len(messages) >= 2:
        conversation_context = context_analyzer.extract_conversation_context(messages)
        context_entities = context_analyzer.extract_key_entities_from_context(
            conversation_context
        )
        metadata.update(
            {
                "conversation_context": (
                    conversation_context[:500] + "..."
                    if len(conversation_context) > 500
                    else conversation_context
                ),
                "context_entities": context_entities,
            }
        )

    return is_enhanced, enhanced_query, metadata
